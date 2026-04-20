import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.evaluator import RAGEvaluator
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
    parser = argparse.ArgumentParser(description="RAG系统评估")

    parser.add_argument(
        '--model',
        type=str,
        default='qwen-8b',
        help='使用的模型（推荐qwen-8b）'
    )

    parser.add_argument(
        '--eval-data',
        type=str,
        default='data/eval/eval_dataset_v4_final.jsonl',
        help='评估数据路径'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制评估案例数量（用于测试）'
    )

    parser.add_argument(
        '--compare-with-baseline',
        action='store_true',
        help='评估完成后生成与baseline的对比报告'
    )

    parser.add_argument(
        '--compare-only',
        action='store_true',
        help='仅生成与baseline的对比报告（不运行评估，使用最近一次RAG结果）'
    )

    parser.add_argument(
        '--note',
        type=str,
        default=None,
        help='本次运行说明（记录修改了什么、为什么跑这次测试）'
    )

    return parser.parse_args()


def find_latest_rag_result(model_key: str, results_dir: str = "results/rag") -> Path | None:
    """查找某模型最近一次RAG运行结果文件（新格式优先）"""
    base = Path(results_dir)

    matches = sorted(base.glob("*/results.json"), reverse=True)
    if matches:
        return matches[0]

    old_path = base / f"{model_key}-rag_results.json"
    if old_path.exists():
        return old_path

    return None


def generate_comparison_report(rag_result_path, run_dir, model_key):
    """生成 RAG vs Baseline 对比报告"""
    with open(rag_result_path, 'r', encoding='utf-8') as f:
        rag_results = json.load(f)

    # 从最新的 baseline 结果中查找
    from src.baseline import ModelRegistry
    registry = ModelRegistry(config_path="configs/model_config.yaml")
    baseline_path = registry.find_latest_result(model_key, "results/baseline")

    if not baseline_path:
        print(f"[警告] 未找到 baseline 结果: {model_key}，跳过对比报告")
        return

    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline_results = json.load(f)

    # baseline 结果是列表格式，需要计算 metrics
    if isinstance(baseline_results, list):
        from src.baseline.evaluator import BaselineEvaluator
        evaluator = BaselineEvaluator()
        baseline_metrics = evaluator.calculate_metrics(baseline_results)
    else:
        baseline_metrics = baseline_results.get('metrics', {})

    # RAG 结果也可能是列表
    if isinstance(rag_results, list):
        from src.baseline.evaluator import BaselineEvaluator
        evaluator = BaselineEvaluator()
        rag_metrics = evaluator.calculate_metrics(rag_results)
    else:
        rag_metrics = rag_results.get('metrics', {})

    comparison = {
        'Baseline': {
            'Accuracy': baseline_metrics.get('accuracy', 0),
            'Legal Basis Quality': baseline_metrics.get('quality_metrics', {}).get('avg_legal_basis_score', 0),
            'Reasoning Quality': baseline_metrics.get('quality_metrics', {}).get('avg_reasoning_score', 0)
        },
        'RAG': {
            'Accuracy': rag_metrics.get('accuracy', 0),
            'Legal Basis Quality': rag_metrics.get('quality_metrics', {}).get('avg_legal_basis_score', 0),
            'Reasoning Quality': rag_metrics.get('quality_metrics', {}).get('avg_reasoning_score', 0)
        }
    }

    report = f"""# RAG vs Baseline 对比报告

**模型**: {model_key}
**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Baseline结果来源**: {baseline_path}

## 核心指标对比

| Metric                  | Baseline | RAG      | Improvement |
|-------------------------|----------|----------|-------------|
| Accuracy                | {comparison['Baseline']['Accuracy']:.2%} | {comparison['RAG']['Accuracy']:.2%} | {(comparison['RAG']['Accuracy'] - comparison['Baseline']['Accuracy']):.2%} |
| Legal Basis Quality     | {comparison['Baseline']['Legal Basis Quality']:.2%} | {comparison['RAG']['Legal Basis Quality']:.2%} | **{(comparison['RAG']['Legal Basis Quality'] - comparison['Baseline']['Legal Basis Quality']):.2%}** |
| Reasoning Quality       | {comparison['Baseline']['Reasoning Quality']:.2%} | {comparison['RAG']['Reasoning Quality']:.2%} | **{(comparison['RAG']['Reasoning Quality'] - comparison['Baseline']['Reasoning Quality']):.2%}** |

## 结论

{'✅ 目标达成：Legal Basis Quality提升至95%+' if comparison['RAG']['Legal Basis Quality'] >= 0.95 else '⚠️ 需要优化：Legal Basis Quality未达95%目标'}
"""

    report_path = Path(run_dir) / 'comparison_with_baseline.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n对比报告已生成: {report_path}")


def main():
    args = parse_args()

    # 收集运行备注（必填）
    note = collect_required_note(args.note)

    # 创建本次运行文件夹（备注+日期）
    run_dir = create_run_dir("results/rag", note)
    print(f"本次运行目录: {run_dir}")

    # 仅对比模式：不运行评估，直接使用最近一次RAG结果生成对比报告
    if args.compare_only:
        rag_result_path = find_latest_rag_result(args.model, "results/rag")
        if not rag_result_path:
            print(f"[错误] 未找到任何RAG结果，无法生成对比报告: model={args.model}")
            return

        run_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "rag",
            "mode": "compare_only",
            "models": [args.model],
            "rag_result_source": str(rag_result_path),
            "eval_data": args.eval_data,
            "limit": args.limit,
            "note": note
        }
        with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
            json.dump(run_info, f, ensure_ascii=False, indent=2)

        generate_comparison_report(str(rag_result_path), run_dir, args.model)

        print("\n" + "="*60)
        print("对比报告生成完成")
        print("="*60)
        print(f"\n本次运行目录: {run_dir}")
        print(f"生成的文件:")
        print(f"  - {run_dir}/comparison_with_baseline.md")
        print(f"  - {run_dir}/run_info.json")
        if note:
            print(f"\n运行备注: {note}")
        print("="*60)
        return

    output_path = str(Path(run_dir) / "results.json")

    evaluator = RAGEvaluator()

    # 设置中间进度保存目录为 run_dir
    evaluator.output_config['results_dir'] = run_dir

    # 加载评估数据（v4格式适配）
    from src.evaluation.dataset_adapter import DatasetAdapter
    adapter = DatasetAdapter(args.eval_data)
    eval_cases = adapter.to_legacy_format(limit=args.limit)
    gt_map = adapter.get_ground_truth_map()

    stats = adapter.get_statistics()
    print(f"数据集: {stats['total']} 条 ({stats['violations']} 违规 + {stats['compliants']} 合规)")

    # 写 run_info.json
    run_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "rag",
        "models": [args.model],
        "eval_data": args.eval_data,
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

    print(f"\n开始评估 {len(eval_cases)} 个案例...")
    results = evaluator.evaluate_batch(eval_cases, model_key=args.model)

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

        # RAG结果在prediction字段中，转换为高级指标期望的格式
        prediction = result.get('prediction', {})
        output = {
            'is_violation': prediction.get('is_violation'),
            'violation_type': prediction.get('violation_type'),
            'confidence': prediction.get('confidence'),
            'legal_basis': prediction.get('legal_basis', ''),
            'reasoning_chain': [prediction.get('reasoning', '')] if prediction.get('reasoning') else []
        }

        # 获取Ground Truth
        ground_truth_laws = []
        if gt_extractor:
            gt = gt_extractor.get_ground_truth(case_id)
            if gt:
                ground_truth_laws = gt.get('ground_truth_laws', [])

        # 获取检索到的法律（RAG特有）
        retrieved_laws = result.get('retrieved_laws', None)

        # 计算高级指标
        advanced_result = advanced_evaluator.evaluate(
            output,
            ground_truth_laws=ground_truth_laws,
            retrieved_laws=retrieved_laws  # RAG有检索结果
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

    # 打印高级指标
    print("\n高级评估指标:")
    print(f"  证据链完整性: {advanced_metrics_avg['evidence_chain_avg']:.3f}")
    print(f"  法律引用准确性: {advanced_metrics_avg['legal_citation_avg']:.3f}")
    print(f"  整改建议可操作性: {advanced_metrics_avg['remediation_avg']:.3f}")
    print(f"  可解释性: {advanced_metrics_avg['explainability_avg']:.3f}")
    print(f"  结构化输出质量: {advanced_metrics_avg['structured_output_avg']:.3f}")
    print(f"  综合平均分: {advanced_metrics_avg['overall_avg']:.3f}")

    evaluator.save_results(results, args.model, output_path)

    # 法条检索F1评测（v4新增）
    from src.evaluation.legal_retrieval_evaluator import LegalRetrievalEvaluator, print_evaluation_summary
    legal_evaluator = LegalRetrievalEvaluator(gt_map)
    legal_summary = legal_evaluator.evaluate_batch(results)
    print_evaluation_summary(legal_summary, method_name=f"RAG-{args.model}")

    if args.compare_with_baseline:
        generate_comparison_report(output_path, run_dir, args.model)

    # 完成总结
    print("\n" + "="*60)
    print("评估完成！")
    print("="*60)
    print(f"本次运行目录: {run_dir}")
    print(f"生成的文件:")
    print(f"  - {output_path}")
    print(f"  - {run_dir}/run_info.json")
    if note:
        print(f"\n运行备注: {note}")
    print("="*60)


if __name__ == '__main__':
    main()
