import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.evaluator import RAGEvaluator


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
        default='data/eval/eval_159.jsonl',
        help='评估数据路径'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制评估案例数量（用于测试）'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='results/rag/qwen-8b-rag_results.json',
        help='结果输出路径'
    )

    parser.add_argument(
        '--compare-with-baseline',
        action='store_true',
        help='评估完成后生成与baseline的对比报告'
    )

    return parser.parse_args()


def generate_comparison_report(model_key):
    with open(f'results/rag/{model_key}-rag_results.json', 'r', encoding='utf-8') as f:
        rag_results = json.load(f)
    with open(f'results/baseline/{model_key}_results.json', 'r', encoding='utf-8') as f:
        baseline_results = json.load(f)

    comparison = {
        'Baseline': {
            'Accuracy': baseline_results['metrics']['accuracy'],
            'Legal Basis Quality': baseline_results['quality_metrics']['avg_legal_basis_score'],
            'Reasoning Quality': baseline_results['quality_metrics']['avg_reasoning_score']
        },
        'RAG': {
            'Accuracy': rag_results['metrics']['accuracy'],
            'Legal Basis Quality': rag_results['quality_metrics']['avg_legal_basis_score'],
            'Reasoning Quality': rag_results['quality_metrics']['avg_reasoning_score']
        }
    }

    report = f"""# RAG vs Baseline 对比报告

**模型**: {model_key}
**评估时间**: {rag_results['metadata']['timestamp']}

## 核心指标对比

| Metric                  | Baseline | RAG      | Improvement |
|-------------------------|----------|----------|-------------|
| Accuracy                | {comparison['Baseline']['Accuracy']:.2%} | {comparison['RAG']['Accuracy']:.2%} | {(comparison['RAG']['Accuracy'] - comparison['Baseline']['Accuracy']):.2%} |
| Legal Basis Quality     | {comparison['Baseline']['Legal Basis Quality']:.2%} | {comparison['RAG']['Legal Basis Quality']:.2%} | **{(comparison['RAG']['Legal Basis Quality'] - comparison['Baseline']['Legal Basis Quality']):.2%}** |
| Reasoning Quality       | {comparison['Baseline']['Reasoning Quality']:.2%} | {comparison['RAG']['Reasoning Quality']:.2%} | **{(comparison['RAG']['Reasoning Quality'] - comparison['Baseline']['Reasoning Quality']):.2%}** |

## 结论

{'✅ 目标达成：Legal Basis Quality提升至95%+' if comparison['RAG']['Legal Basis Quality'] >= 0.95 else '⚠️ 需要优化：Legal Basis Quality未达95%目标'}
"""

    with open('results/rag/comparison_with_baseline.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print("\n对比报告已生成: results/rag/comparison_with_baseline.md")


def main():
    args = parse_args()

    evaluator = RAGEvaluator()

    eval_cases = evaluator.load_eval_data(args.eval_data, limit=args.limit)

    print(f"\n开始评估 {len(eval_cases)} 个案例...")
    results = evaluator.evaluate_batch(eval_cases, model_key=args.model)

    evaluator.save_results(results, args.model, args.output)

    if args.compare_with_baseline:
        generate_comparison_report(args.model)


if __name__ == '__main__':
    main()
