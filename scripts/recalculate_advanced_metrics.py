"""
重新计算高级评估指标脚本

用于已完成的评估结果，无需重跑整个eval流程。
支持Baseline、RAG、Agent三种结果格式。

使用示例:
    # 重算RAG结果的高级指标
    python scripts/recalculate_advanced_metrics.py --input results/rag_754/qwen-8b-rag_results.json --method rag

    # 重算Baseline结果
    python scripts/recalculate_advanced_metrics.py --input results/baseline_754/qwen-8b_results.json --method baseline

    # 重算Agent结果
    python scripts/recalculate_advanced_metrics.py --input results/agent_754/full_eval_results.json --method agent
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.advanced_metrics import AdvancedMetricsEvaluator
from src.evaluation.ground_truth_extractor import GroundTruthExtractor


def parse_args():
    parser = argparse.ArgumentParser(description="重新计算高级评估指标")

    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='输入结果文件路径'
    )

    parser.add_argument(
        '--method',
        type=str,
        choices=['baseline', 'rag', 'agent'],
        required=True,
        help='评估方法类型'
    )

    parser.add_argument(
        '--eval-data',
        type=str,
        default='data/eval/eval_754.jsonl',
        help='评估数据路径（用于提取Ground Truth）'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出文件路径（默认覆盖原文件）'
    )

    return parser.parse_args()


def convert_to_output_format(result: dict, method: str) -> dict:
    """
    将不同方法的结果转换为高级指标评估器期望的格式

    高级指标需要的字段:
    - is_violation: bool
    - violation_type: str
    - confidence: float
    - legal_basis: str
    - reasoning_chain: List[str]
    - remediation: dict (可选)
    """
    if method == 'baseline':
        # Baseline结果在prediction字段中
        prediction = result.get('prediction', {})
        reasoning = prediction.get('reasoning', '')
        return {
            'is_violation': prediction.get('is_violation'),
            'violation_type': prediction.get('violation_type'),
            'confidence': prediction.get('confidence'),
            'legal_basis': prediction.get('legal_basis', ''),
            'reasoning_chain': [reasoning] if reasoning else []
        }

    elif method == 'rag':
        # RAG结果在prediction字段中
        prediction = result.get('prediction', {})
        reasoning = prediction.get('reasoning', '')
        return {
            'is_violation': prediction.get('is_violation'),
            'violation_type': prediction.get('violation_type'),
            'confidence': prediction.get('confidence'),
            'legal_basis': prediction.get('legal_basis', ''),
            'reasoning_chain': [reasoning] if reasoning else []
        }

    elif method == 'agent':
        # Agent结果直接包含所需字段
        return {
            'is_violation': result.get('is_violation'),
            'violation_type': result.get('violation_type'),
            'confidence': result.get('confidence', 0),
            'legal_basis': result.get('legal_basis', ''),
            'reasoning_chain': result.get('reasoning_chain', []),
            'remediation': result.get('remediation', {})
        }

    return {}


def main():
    args = parse_args()

    print("=" * 60)
    print("重新计算高级评估指标")
    print("=" * 60)
    print(f"输入文件: {args.input}")
    print(f"评估方法: {args.method}")

    # 加载结果文件
    print("\n[1/4] 加载结果文件...")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理不同的结果格式
    if isinstance(data, list):
        # Baseline/RAG格式：直接是结果列表
        results = data
        metadata = None
    elif isinstance(data, dict) and 'results' in data:
        # Agent格式：包含metadata和results
        results = data['results']
        metadata = data.get('metadata')
    else:
        print("[错误] 无法识别的结果格式")
        return

    print(f"  加载了 {len(results)} 条结果")

    # 加载Ground Truth
    print("\n[2/4] 加载Ground Truth...")
    gt_extractor = GroundTruthExtractor(eval_data_path=args.eval_data)
    gt_extractor.build_ground_truth_dict()
    print(f"  加载了 {len(gt_extractor.ground_truths)} 条Ground Truth")

    # 计算高级指标
    print("\n[3/4] 计算高级指标...")
    advanced_evaluator = AdvancedMetricsEvaluator()

    advanced_metrics_summary = {
        "evidence_chain_scores": [],
        "legal_citation_scores": [],
        "remediation_scores": [],
        "explainability_scores": [],
        "structured_output_scores": []
    }

    for i, result in enumerate(results):
        if not result.get('success', True):
            # 跳过失败的结果
            continue

        case_id = result.get('case_id', f'unknown_{i}')

        # 转换为高级指标期望的格式
        output = convert_to_output_format(result, args.method)

        # 获取Ground Truth
        ground_truth_laws = []
        gt = gt_extractor.get_ground_truth(case_id)
        if gt:
            ground_truth_laws = gt.get('ground_truth_laws', [])

        # 获取检索到的法律（仅RAG有）
        retrieved_laws = result.get('retrieved_laws', None)

        # 计算高级指标
        advanced_result = advanced_evaluator.evaluate(
            output,
            ground_truth_laws=ground_truth_laws,
            retrieved_laws=retrieved_laws
        )

        # 更新结果
        result['advanced_metrics'] = advanced_result

        # 累积统计
        summary = advanced_result.get('summary', {})
        advanced_metrics_summary['evidence_chain_scores'].append(summary.get('evidence_chain_score', 0))
        advanced_metrics_summary['legal_citation_scores'].append(summary.get('legal_citation_score', 0))
        advanced_metrics_summary['remediation_scores'].append(summary.get('remediation_score', 0))
        advanced_metrics_summary['explainability_scores'].append(summary.get('explainability_score', 0))
        advanced_metrics_summary['structured_output_scores'].append(summary.get('structured_output_score', 0))

        if (i + 1) % 100 == 0:
            print(f"  已处理 {i + 1}/{len(results)} 条")

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

    # 打印结果
    print("\n" + "=" * 60)
    print("高级评估指标（重新计算）")
    print("=" * 60)
    print(f"  证据链完整性:     {advanced_metrics_avg['evidence_chain_avg']:.3f}")
    print(f"  法律引用准确性:   {advanced_metrics_avg['legal_citation_avg']:.3f}")
    print(f"  整改建议可操作性: {advanced_metrics_avg['remediation_avg']:.3f}")
    print(f"  可解释性:         {advanced_metrics_avg['explainability_avg']:.3f}")
    print(f"  结构化输出质量:   {advanced_metrics_avg['structured_output_avg']:.3f}")
    print(f"  综合平均分:       {advanced_metrics_avg['overall_avg']:.3f}")

    # 保存结果
    print("\n[4/4] 保存结果...")
    output_path = args.output or args.input

    # 重建输出数据
    if metadata is not None:
        # Agent格式
        output_data = {
            'metadata': metadata,
            'metrics': data.get('metrics', {}),
            'advanced_metrics_summary': advanced_metrics_avg,
            'results': results
        }
    else:
        # Baseline/RAG格式：添加summary到第一个元素或单独保存
        output_data = results
        # 同时保存一个summary文件
        summary_path = Path(output_path).with_suffix('.summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'advanced_metrics_summary': advanced_metrics_avg,
                'total_cases': len(results)
            }, f, ensure_ascii=False, indent=2)
        print(f"  Summary已保存: {summary_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"  结果已保存: {output_path}")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
