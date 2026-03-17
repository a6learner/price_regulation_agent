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
import argparse
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.baseline import (
    BaselineEvaluator,
    ModelRegistry,
    MultiModelComparator
)


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
        default='data/eval/eval_159.jsonl',
        help='评估数据集路径（默认: data/eval/eval_159.jsonl）'
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

    return parser.parse_args()


def evaluate_model(
    evaluator: BaselineEvaluator,
    registry: ModelRegistry,
    model_key: str,
    eval_cases: list,
    results_dir: str
):
    """
    评估单个模型

    Args:
        evaluator: 评估器实例
        registry: 模型注册表
        model_key: 模型键名
        eval_cases: 评估案例列表
        results_dir: 结果目录

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

        # 计算指标
        metrics = evaluator.calculate_metrics(results)
        evaluator.print_metrics(metrics, model['name'])

        # 保存结果
        result_path = registry.get_result_path(model_key, results_dir)
        result_path.parent.mkdir(parents=True, exist_ok=True)

        import json
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
    print(f"结果目录: {args.results_dir}")

    # 仅对比模式
    if args.compare_only:
        print("\n[模式] 仅生成对比报告")
        comparator = MultiModelComparator(registry)
        comparator.generate_report(
            model_keys,
            output_path=f"{args.results_dir}/multi_model_comparison.md",
            results_dir=args.results_dir
        )
        comparator.print_summary(model_keys, results_dir=args.results_dir)
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
        print("或使用 --compare-only 生成对比报告")

        # 生成对比报告
        comparator = MultiModelComparator(registry)
        comparator.generate_report(
            model_keys,
            output_path=f"{args.results_dir}/multi_model_comparison.md",
            results_dir=args.results_dir
        )
        return

    # 加载评估数据
    evaluator = BaselineEvaluator(config_path="configs/model_config.yaml")
    eval_cases = evaluator.load_eval_data(args.eval_path, limit=args.limit)

    if not eval_cases:
        print("[错误] 无法加载评估数据")
        return

    print(f"\n加载了 {len(eval_cases)} 个评估案例")

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

    # 评估所有模型
    for i, model_key in enumerate(models_to_evaluate, 1):
        print(f"\n进度: [{i}/{len(models_to_evaluate)}]")
        evaluate_model(evaluator, registry, model_key, eval_cases, args.results_dir)

        # 重置统计（避免累积）
        if hasattr(evaluator.client, 'reset_statistics'):
            evaluator.client.reset_statistics()

    # 生成对比报告
    print("\n" + "="*60)
    print("生成多模型对比报告")
    print("="*60)

    comparator = MultiModelComparator(registry)

    # 对所有模型生成报告（包括跳过的）
    all_models_for_comparison = models_to_evaluate + models_skipped

    comparator.generate_report(
        all_models_for_comparison,
        output_path=f"{args.results_dir}/multi_model_comparison.md",
        results_dir=args.results_dir
    )

    comparator.print_summary(all_models_for_comparison, results_dir=args.results_dir)

    # 完成总结
    print("\n" + "="*60)
    print("评估完成！")
    print("="*60)
    print(f"\n生成的文件:")
    for model_key in all_models_for_comparison:
        result_path = registry.get_result_path(model_key, args.results_dir)
        print(f"  - {result_path}")
    print(f"  - {args.results_dir}/multi_model_comparison.md")

    print("\n下一步:")
    print(f"  1. 查看对比报告: cat {args.results_dir}/multi_model_comparison.md")
    print("  2. 添加新模型: 编辑 configs/model_config.yaml")
    print("  3. 重新运行: python scripts/run_baseline_eval.py --models <new_model>")
    print("="*60)


if __name__ == "__main__":
    main()
