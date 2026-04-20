"""
Baseline评估脚本 - 灵活的多模型评估系统
支持命令行参数选择模型、增量评估和多模型对比

使用示例:
    # 评估单个模型
    python scripts/run_baseline_eval.py --models qwen

    # 评估多个模型
    python scripts/run_baseline_eval.py --models qwen,minimax

    # 跳过已有结果，只评估新模型
    python scripts/run_baseline_eval.py --models qwen,minimax,qwen7b --skip-existing

    # 仅生成对比报告（不评估）
    python scripts/run_baseline_eval.py --compare-only --models qwen,minimax

    # 强制重新评估所有模型
    python scripts/run_baseline_eval.py --models qwen,minimax --force

    # 列出所有可用模型
    python scripts/run_baseline_eval.py --list-models
"""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.baseline import (
    BaselineEvaluator,
    ModelRegistry,
    MultiModelComparator
)
from src.evaluation.advanced_metrics import AdvancedMetricsEvaluator
from src.evaluation.ground_truth_extractor import GroundTruthExtractor


def collect_required_note(cli_note: str | None) -> str:
    """收集必填备注：优先--note，其次交互输入，不能为空"""
    if cli_note and cli_note.strip():
        return cli_note.strip()

    if sys.stdin.isatty():
        while True:
            note = input("本次运行说明（必填）: ").strip()
            if note:
                return note
            print("备注不能为空，请重新输入。")

    print("[错误] 必须提供 --note（当前为非交互环境，无法输入备注）")
    sys.exit(1)


def create_run_dir(base_dir: str, note: str) -> str:
    """按 备注+日期 创建运行目录，自动清洗并避免重名"""
    slug = re.sub(r'[\\/:*?"<>|]+', '', note)
    slug = re.sub(r'\s+', '_', slug).strip('._')
    slug = re.sub(r'[^0-9A-Za-z_\-\u4e00-\u9fff]+', '', slug)
    if not slug:
        slug = "run"

    date_tag = datetime.now().strftime("%m-%d")
    base_name = f"{slug}__{date_tag}"

    run_path = Path(base_dir) / base_name
    suffix = 2
    while run_path.exists():
        run_path = Path(base_dir) / f"{base_name}__v{suffix}"
        suffix += 1

    run_path.mkdir(parents=True, exist_ok=True)
    return str(run_path)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Baseline多模型评估系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--models',
        type=str,
        help='要评估的模型列表（逗号分隔），如: qwen,minimax,qwen7b'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='评估所有已配置的模型'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已有结果的模型（增量评估）'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新评估，即使已有结果'
    )

    parser.add_argument(
        '--compare-only',
        action='store_true',
        help='仅生成对比报告，不运行评估'
    )

    parser.add_argument(
        '--list-models',
        action='store_true',
        help='列出所有可用模型'
    )

    parser.add_argument(
        '--eval-path',
        type=str,
        default='data/eval/eval_dataset_v4_final.jsonl',
        help='评估数据集路径（默认: data/eval/eval_dataset_v4_final.jsonl）'
    )

    parser.add_argument(
        '--results-dir',
        type=str,
        default='results/baseline',
        help='结果保存目录（默认: results/baseline）'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='限制评估案例数量（用于测试）'
    )

    parser.add_argument(
        '--note',
        type=str,
        default=None,
        help='本次运行说明（记录修改了什么、为什么跑这次测试）'
    )

    return parser.parse_args()


def evaluate_model(
    evaluator: BaselineEvaluator,
    registry: ModelRegistry,
    model_key: str,
    eval_cases: list,
    results_dir: str,
    ground_truth_extractor: GroundTruthExtractor = None
):
    """
    评估单个模型

    Args:
        evaluator: 评估器实例
        registry: 模型注册表
        model_key: 模型键名
        eval_cases: 评估案例列表
        results_dir: 结果目录
        ground_truth_extractor: Ground Truth提取器（可选）

    Returns:
        评估结果列表
    """
    model = registry.get_model(model_key)
    if not model:
        print(f"[错误] 模型不存在: {model_key}")
        return None

    print(f"\n{'='*60}")
    print(f"评估模型: {model['name']} ({model_key})")
    print(f"{'='*60}")

    try:
        # 运行评估
        results = evaluator.evaluate_batch(
            eval_cases,
            model_key=model_key,
            save_progress=True
        )

        # 计算传统指标
        metrics = evaluator.calculate_metrics(results)
        evaluator.print_metrics(metrics, model['name'])

        # 计算新增的高级指标
        print("\n[新增] 计算高级评估指标...")
        advanced_evaluator = AdvancedMetricsEvaluator()

        # 初始化统计
        advanced_metrics_summary = {
            "evidence_chain_scores": [],
            "legal_citation_scores": [],
            "remediation_scores": [],
            "explainability_scores": [],
            "structured_output_scores": []
        }

        # 为每个结果计算高级指标
        for i, result in enumerate(results):
            case_id = result.get('case_id', f'unknown_{i}')
            output = result.get('output', {})

            # 获取Ground Truth
            ground_truth_laws = []
            if ground_truth_extractor:
                gt = ground_truth_extractor.get_ground_truth(case_id)
                if gt:
                    ground_truth_laws = gt.get('ground_truth_laws', [])

            # 计算高级指标
            advanced_result = advanced_evaluator.evaluate(
                output,
                ground_truth_laws=ground_truth_laws,
                retrieved_laws=None  # Baseline没有检索结果
            )

            # 保存到result中
            result['advanced_metrics'] = advanced_result

            # 累积统计
            summary = advanced_result.get('summary', {})
            advanced_metrics_summary['evidence_chain_scores'].append(summary.get('evidence_chain_score', 0))
            advanced_metrics_summary['legal_citation_scores'].append(summary.get('legal_citation_score', 0))
            advanced_metrics_summary['remediation_scores'].append(summary.get('remediation_score', 0))
            advanced_metrics_summary['explainability_scores'].append(summary.get('explainability_score', 0))
            advanced_metrics_summary['structured_output_scores'].append(summary.get('structured_output_score', 0))

        # 计算平均分
        def avg(scores):
            return sum(scores) / len(scores) if scores else 0

        advanced_metrics_avg = {
            "evidence_chain_avg": round(avg(advanced_metrics_summary['evidence_chain_scores']), 3),
            "legal_citation_avg": round(avg(advanced_metrics_summary['legal_citation_scores']), 3),
            "remediation_avg": round(avg(advanced_metrics_summary['remediation_scores']), 3),
            "explainability_avg": round(avg(advanced_metrics_summary['explainability_scores']), 3),
            "structured_output_avg": round(avg(advanced_metrics_summary['structured_output_scores']), 3),
            "overall_avg": round(avg([
                avg(advanced_metrics_summary['evidence_chain_scores']),
                avg(advanced_metrics_summary['legal_citation_scores']),
                avg(advanced_metrics_summary['remediation_scores']),
                avg(advanced_metrics_summary['explainability_scores']),
                avg(advanced_metrics_summary['structured_output_scores'])
            ]), 3)
        }

        # 注意：advanced_metrics_avg仅用于打印，不保存到results中
        # results是列表，不能直接添加键值对
        # 每个result已经包含advanced_metrics字段

        # 打印高级指标
        print("\n高级评估指标:")
        print(f"  证据链完整性: {advanced_metrics_avg['evidence_chain_avg']:.3f}")
        print(f"  法律引用准确性: {advanced_metrics_avg['legal_citation_avg']:.3f}")
        print(f"  整改建议可操作性: {advanced_metrics_avg['remediation_avg']:.3f}")
        print(f"  可解释性: {advanced_metrics_avg['explainability_avg']:.3f}")
        print(f"  结构化输出质量: {advanced_metrics_avg['structured_output_avg']:.3f}")
        print(f"  综合平均分: {advanced_metrics_avg['overall_avg']:.3f}")

        # 法条检索F1评测（v4新增）
        if ground_truth_extractor and hasattr(ground_truth_extractor, 'ground_truths'):
            from src.evaluation.legal_retrieval_evaluator import LegalRetrievalEvaluator, print_evaluation_summary
            legal_evaluator = LegalRetrievalEvaluator(ground_truth_extractor.ground_truths)
            legal_summary = legal_evaluator.evaluate_batch(results)
            print_evaluation_summary(legal_summary, method_name=f"Baseline-{model_key}")
            # 附加到第一条result的metadata，便于后续对比（不修改results结构）
            if results:
                results[0]['_legal_retrieval_metrics'] = {
                    k: v for k, v in legal_summary.items() if k != 'case_scores'
                }

        # 保存结果到 run 文件夹
        result_path = Path(results_dir) / f"{model_key}_results.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n[成功] 结果已保存: {result_path}")

        return results

    except Exception as e:
        print(f"\n[错误] 模型评估失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    args = parse_args()

    # 初始化注册表
    registry = ModelRegistry(config_path="configs/model_config.yaml")

    # 列出模型
    if args.list_models:
        registry.print_registry()
        return

    # 确定要评估的模型
    if args.all:
        model_keys = registry.list_models()
    elif args.models:
        model_keys = [m.strip() for m in args.models.split(',')]
    else:
        print("[错误] 请指定要评估的模型（--models）或使用 --all 评估所有模型")
        print("使用 --list-models 查看可用模型")
        return

    # 验证模型存在
    valid_models = []
    for key in model_keys:
        if registry.get_model(key):
            valid_models.append(key)
        else:
            print(f"[警告] 模型不存在: {key}，已跳过")

    if not valid_models:
        print("[错误] 没有有效的模型可评估")
        return

    model_keys = valid_models

    print("="*60)
    print("Baseline多模型评估系统")
    print("="*60)
    print(f"\n待评估模型: {', '.join([registry.get_model(k)['name'] for k in model_keys])}")
    print(f"评估数据集: {args.eval_path}")
    print(f"结果根目录: {args.results_dir}")

    # 仅对比模式：创建 run 文件夹，记录备注与参数
    if args.compare_only:
        print("\n[模式] 仅生成对比报告")

        # 收集运行备注（必填）
        note = collect_required_note(args.note)

        # 创建本次运行文件夹（备注+日期）
        run_dir = create_run_dir(args.results_dir, note)
        print(f"\n本次运行目录: {run_dir}")

        # 读取数据集统计（不加载完整样本）
        from src.evaluation.dataset_adapter import DatasetAdapter
        adapter = DatasetAdapter(args.eval_path)
        stats = adapter.get_statistics()
        eval_cases_count = min(args.limit, stats['total']) if args.limit else stats['total']

        # 写 run_info.json
        run_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "baseline",
            "mode": "compare_only",
            "models": model_keys,
            "eval_data": args.eval_path,
            "eval_cases": eval_cases_count,
            "limit": args.limit,
            "note": note
        }
        with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
            json.dump(run_info, f, ensure_ascii=False, indent=2)

        comparator = MultiModelComparator(registry)
        comparator.generate_report(
            model_keys,
            output_path=f"{run_dir}/multi_model_comparison.md",
            results_dir=args.results_dir
        )
        comparator.print_summary(model_keys, results_dir=args.results_dir)

        print("\n" + "="*60)
        print("对比报告生成完成")
        print("="*60)
        print(f"\n本次运行目录: {run_dir}")
        print(f"生成的文件:")
        print(f"  - {run_dir}/multi_model_comparison.md")
        print(f"  - {run_dir}/run_info.json")
        if note:
            print(f"\n运行备注: {note}")
        print("="*60)
        return

    # 检查已有结果
    models_to_evaluate = []
    models_skipped = []

    for model_key in model_keys:
        has_result = registry.has_result(model_key, args.results_dir)

        if has_result and args.skip_existing and not args.force:
            models_skipped.append(model_key)
            print(f"[跳过] {registry.get_model(model_key)['name']} - 已有结果")
        else:
            if has_result and args.force:
                print(f"[重评] {registry.get_model(model_key)['name']} - 强制重新评估")
            models_to_evaluate.append(model_key)

    if not models_to_evaluate:
        print("\n所有模型都已有结果，使用 --force 强制重新评估")
        print("将仅生成对比报告并记录本次运行信息")

        # 收集运行备注（必填）
        note = collect_required_note(args.note)

        # 创建本次运行文件夹（备注+日期）
        run_dir = create_run_dir(args.results_dir, note)
        print(f"\n本次运行目录: {run_dir}")

        # 读取数据集统计（不加载完整样本）
        from src.evaluation.dataset_adapter import DatasetAdapter
        adapter = DatasetAdapter(args.eval_path)
        stats = adapter.get_statistics()
        eval_cases_count = min(args.limit, stats['total']) if args.limit else stats['total']

        # 写 run_info.json
        run_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "baseline",
            "models": [],
            "models_skipped": model_keys,
            "eval_data": args.eval_path,
            "eval_cases": eval_cases_count,
            "limit": args.limit,
            "note": note
        }
        with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
            json.dump(run_info, f, ensure_ascii=False, indent=2)

        # 生成对比报告（从 results_dir 根目录读取最新结果，报告写入 run_dir）
        comparator = MultiModelComparator(registry)
        comparator.generate_report(
            model_keys,
            output_path=f"{run_dir}/multi_model_comparison.md",
            results_dir=args.results_dir
        )
        comparator.print_summary(model_keys, results_dir=args.results_dir)

        print("\n" + "="*60)
        print("对比报告生成完成")
        print("="*60)
        print(f"\n本次运行目录: {run_dir}")
        print(f"生成的文件:")
        print(f"  - {run_dir}/multi_model_comparison.md")
        print(f"  - {run_dir}/run_info.json")
        if note:
            print(f"\n运行备注: {note}")
        print("="*60)
        return

    # 收集运行备注（必填）
    note = collect_required_note(args.note)

    # 创建本次运行文件夹（备注+日期）
    run_dir = create_run_dir(args.results_dir, note)
    print(f"\n本次运行目录: {run_dir}")

    # 加载评估数据（v4格式适配）
    from src.evaluation.dataset_adapter import DatasetAdapter
    evaluator = BaselineEvaluator(config_path="configs/model_config.yaml")
    adapter = DatasetAdapter(args.eval_path)
    eval_cases = adapter.to_legacy_format(limit=args.limit)
    gt_map = adapter.get_ground_truth_map()

    if not eval_cases:
        print("[错误] 无法加载评估数据")
        return

    stats = adapter.get_statistics()
    print(f"\n数据集: {stats['total']} 条 ({stats['violations']} 违规 + {stats['compliants']} 合规)")
    print(f"加载了 {len(eval_cases)} 个评估案例")

    # 写 run_info.json
    run_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "baseline",
        "models": models_to_evaluate,
        "eval_data": args.eval_path,
        "eval_cases": len(eval_cases),
        "limit": args.limit,
        "note": note
    }
    with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    # 初始化Ground Truth提取器
    print("\n[初始化] 加载Ground Truth...")
    gt_extractor = GroundTruthExtractor(gt_map=gt_map)
    print(f"[完成] 加载了 {len(gt_extractor.ground_truths)} 个案例的Ground Truth")

    # 确认评估
    if not args.limit:  # 完整评估需要确认
        print(f"\n[警告] 将调用API约 {len(eval_cases) * len(models_to_evaluate)} 次")
        print("请确保:")
        print("  1. API密钥配置正确")
        print("  2. 账户余额充足")
        print("\n是否继续？(y/n): ", end='')
        choice = input().strip().lower()

        if choice != 'y':
            print("已取消评估")
            return

    # 设置中间进度保存目录为 run_dir
    evaluator.output_config['results_dir'] = run_dir

    # 评估所有模型
    for i, model_key in enumerate(models_to_evaluate, 1):
        print(f"\n进度: [{i}/{len(models_to_evaluate)}]")
        evaluate_model(evaluator, registry, model_key, eval_cases, run_dir, gt_extractor)

        # 重置统计（避免累积）
        if hasattr(evaluator.client, 'reset_statistics'):
            evaluator.client.reset_statistics()

    # 生成对比报告（保存在 run_dir 内）
    print("\n" + "="*60)
    print("生成多模型对比报告")
    print("="*60)

    comparator = MultiModelComparator(registry)

    # 对所有模型生成报告（包括跳过的）
    all_models_for_comparison = models_to_evaluate + models_skipped

    comparator.generate_report(
        all_models_for_comparison,
        output_path=f"{run_dir}/multi_model_comparison.md",
        results_dir=run_dir
    )

    comparator.print_summary(all_models_for_comparison, results_dir=run_dir)

    # 完成总结
    print("\n" + "="*60)
    print("评估完成！")
    print("="*60)
    print(f"\n本次运行目录: {run_dir}")
    print(f"生成的文件:")
    for model_key in models_to_evaluate:
        print(f"  - {run_dir}/{model_key}_results.json")
    print(f"  - {run_dir}/multi_model_comparison.md")
    print(f"  - {run_dir}/run_info.json")
    if note:
        print(f"\n运行备注: {note}")
    print("="*60)


if __name__ == "__main__":
    main()
