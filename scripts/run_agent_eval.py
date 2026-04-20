"""Agent系统完整评估脚本

评估Agent系统在所有159个评估案例上的性能
支持与Baseline和RAG的结果对比

使用示例:
    # 运行完整评估（159 cases）
    python scripts/run_agent_eval.py

    # 测试前5个案例
    python scripts/run_agent_eval.py --limit 5
"""

import sys
import json
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import AgentCoordinator
from src.baseline.response_parser import ResponseParser
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
        description="Agent系统完整评估",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--eval-data',
        type=str,
        default='data/eval/eval_dataset_v4_final.jsonl',
        help='评估数据路径（默认: data/eval/eval_dataset_v4_final.jsonl）'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制评估案例数量（用于测试，默认评估所有）'
    )

    parser.add_argument(
        '--save-interval',
        type=int,
        default=20,
        help='进度保存间隔（默认每20个案例保存一次）'
    )

    parser.add_argument(
        '--compare-only',
        action='store_true',
        help='仅记录一次对比/检查（不运行评估，写run_info并指向最近一次Agent结果）'
    )

    parser.add_argument(
        '--note',
        type=str,
        default=None,
        help='本次运行说明（记录修改了什么、为什么跑这次测试）'
    )

    return parser.parse_args()


def find_latest_agent_result(results_dir: str = "results/agent") -> Path | None:
    base = Path(results_dir)
    matches = sorted(base.glob("*/results.json"), reverse=True)
    return matches[0] if matches else None


def load_eval_cases(file_path, limit=None):
    """加载评估数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        cases = [json.loads(line) for line in f]

    if limit:
        cases = cases[:limit]

    print(f"加载了 {len(cases)} 个评估案例")
    return cases


def evaluate_single_case(coordinator, parser, eval_case, case_idx, total, gt_extractor, advanced_evaluator):
    """评估单个案例"""
    case_id = eval_case['meta']['case_id']
    query = eval_case['messages'][1]['content']

    print(f"\n[{case_idx}/{total}] {case_id}")
    print("-" * 80)

    start_time = time.time()

    try:
        # 运行Agent工作流
        result = coordinator.process(query, return_trace=True)
        response_time = time.time() - start_time

        # 提取ground truth
        is_violation = eval_case['meta']['is_violation']
        violation_type = eval_case['meta'].get('violation_type', '无违规')

        # 提取预测结果
        predicted_violation = result.get('is_violation')
        predicted_type = result.get('violation_type', '')

        # 使用智能匹配器判断是否匹配
        prediction_dict = {
            'is_violation': predicted_violation,
            'violation_type': predicted_type
        }
        ground_truth_dict = {
            'is_violation': is_violation,
            'violation_type': violation_type
        }
        comparison = parser.compare_prediction_with_truth(
            prediction_dict,
            ground_truth_dict,
            use_smart_matching=True
        )
        match = comparison['is_correct']
        type_correct = comparison['type_correct']
        match_details = comparison.get('match_details', {})

        # 评估法律依据质量（使用Baseline的评估方法）
        legal_basis = result.get('legal_basis', '') or ' '.join(result.get('reasoning_chain', []))
        legal_quality = parser.evaluate_legal_basis_accuracy({'legal_basis': legal_basis})

        # 评估推理质量
        reasoning = result.get('reasoning', '') or '\n'.join(result.get('reasoning_chain', []))
        reasoning_quality = parser.evaluate_reasoning_quality({'reasoning': reasoning})

        # 计算新增的高级指标
        ground_truth_laws = []
        if gt_extractor:
            gt = gt_extractor.get_ground_truth(case_id)
            if gt:
                ground_truth_laws = gt.get('ground_truth_laws', [])

        # 准备输出（包含remediation）
        output = {
            'is_violation': predicted_violation,
            'violation_type': predicted_type,
            'legal_basis': legal_basis,
            'reasoning_chain': result.get('reasoning_chain', []),
            'confidence': result.get('confidence', 0),
            'remediation': result.get('remediation', {})  # Agent特有
        }

        # 计算高级指标（没有retrieved_laws，但有remediation）
        advanced_result = advanced_evaluator.evaluate(
            output,
            ground_truth_laws=ground_truth_laws,
            retrieved_laws=None  # Agent没有直接的retrieved_laws
        )

        print(f"\nGround Truth: {is_violation} - {violation_type}")
        print(f"Prediction:   {predicted_violation} - {predicted_type}")
        print(f"Match: {'PASS' if match else 'FAIL'} | Type: {'PASS' if type_correct else 'FAIL'}")
        if match_details:
            print(f"  匹配类型: {match_details.get('match_type', 'N/A')} (置信度: {match_details.get('confidence', 0):.2f})")
        print(f"Legal Quality: {legal_quality['legal_basis_score']:.2f}")
        print(f"Reasoning Quality: {reasoning_quality['reasoning_score']:.2f}")
        print(f"Advanced: {advanced_result['summary']['average_score']:.3f}")

        return {
            'case_id': case_id,
            'success': result.get('success', True),
            'is_violation': predicted_violation,
            'violation_type': predicted_type,
            'confidence': result.get('confidence', 0),
            'reasoning_chain': result.get('reasoning_chain', []),
            'legal_basis': legal_basis[:400],  # 保存前500字符
            'validation_passed': result.get('validation_passed', False),
            'reflection_count': result.get('reflection_count', 0),
            'remediation': result.get('remediation', {}),  # 保存整改建议
            'agent_trace': result.get('agent_trace'),
            'ground_truth': {
                'is_violation': is_violation,
                'violation_type': violation_type
            },
            'match': match,
            'type_correct': type_correct,  # 新增：智能匹配结果
            'match_details': match_details,  # 新增：匹配详情
            'quality_metrics': {
                'legal_basis': legal_quality,
                'reasoning': reasoning_quality
            },
            'advanced_metrics': advanced_result,  # 新增高级指标
            'performance': {
                'response_time': round(response_time, 2)
            }
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'case_id': case_id,
            'success': False,
            'error': str(e),
            'ground_truth': {
                'is_violation': eval_case['meta']['is_violation'],
                'violation_type': eval_case['meta'].get('violation_type', '无违规')
            }
        }


def calculate_metrics(results):
    """计算整体指标"""
    successful = [r for r in results if r.get('success')]
    total = len(results)
    successful_count = len(successful)

    if successful_count == 0:
        return {
            'total': total,
            'successful': 0,
            'error_rate': 1.0,
            'accuracy': 0.0
        }

    # Binary classification metrics
    matched = sum(1 for r in successful if r.get('match'))
    accuracy = matched / successful_count

    # Violation type accuracy (using smart matching results)
    tp_cases = [r for r in successful if r.get('match') and r.get('ground_truth', {}).get('is_violation')]
    type_matched = sum(1 for r in tp_cases if r.get('type_correct', False))
    type_accuracy = type_matched / len(tp_cases) if tp_cases else 0

    # Quality metrics
    legal_scores = [r['quality_metrics']['legal_basis']['legal_basis_score'] for r in successful if 'quality_metrics' in r]
    reasoning_scores = [r['quality_metrics']['reasoning']['reasoning_score'] for r in successful if 'quality_metrics' in r]

    avg_legal = sum(legal_scores) / len(legal_scores) if legal_scores else 0
    avg_reasoning = sum(reasoning_scores) / len(reasoning_scores) if reasoning_scores else 0

    # Advanced metrics
    evidence_scores = [r['advanced_metrics']['summary']['evidence_chain_score'] for r in successful if 'advanced_metrics' in r]
    citation_scores = [r['advanced_metrics']['summary']['legal_citation_score'] for r in successful if 'advanced_metrics' in r]
    remediation_scores = [r['advanced_metrics']['summary']['remediation_score'] for r in successful if 'advanced_metrics' in r]
    explainability_scores = [r['advanced_metrics']['summary']['explainability_score'] for r in successful if 'advanced_metrics' in r]
    structured_scores = [r['advanced_metrics']['summary']['structured_output_score'] for r in successful if 'advanced_metrics' in r]

    avg_evidence = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0
    avg_citation = sum(citation_scores) / len(citation_scores) if citation_scores else 0
    avg_remediation = sum(remediation_scores) / len(remediation_scores) if remediation_scores else 0
    avg_explainability = sum(explainability_scores) / len(explainability_scores) if explainability_scores else 0
    avg_structured = sum(structured_scores) / len(structured_scores) if structured_scores else 0

    # Validation metrics
    validated = sum(1 for r in successful if r.get('validation_passed'))
    reflected = sum(1 for r in successful if r.get('reflection_count', 0) > 0)

    # Performance metrics
    response_times = [r['performance']['response_time'] for r in successful if 'performance' in r]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    node_keys = [
        'intent_analyzer', 'adaptive_retriever', 'grader',
        'reasoning_engine', 'reflector', 'remediation_advisor',
    ]
    node_timings_avg_ms = {}
    traces = [r.get('agent_trace') for r in successful if r.get('agent_trace')]
    if traces:
        for k in node_keys:
            vals = [t['timings_ms'].get(k, 0) for t in traces if t.get('timings_ms')]
            if vals:
                node_timings_avg_ms[k] = round(sum(vals) / len(vals), 2)
        tot_vals = [t.get('total_pipeline_ms', 0) for t in traces]
        if tot_vals:
            node_timings_avg_ms['total_pipeline_ms'] = round(sum(tot_vals) / len(tot_vals), 2)

    return {
        'total': total,
        'successful': successful_count,
        'error_rate': (total - successful_count) / total,
        'accuracy': accuracy,
        'violation_type_accuracy': type_accuracy,
        'validation_passed_rate': validated / successful_count,
        'reflection_triggered_rate': reflected / successful_count,
        'quality_metrics': {
            'avg_legal_basis_score': avg_legal,
            'avg_reasoning_score': avg_reasoning
        },
        'advanced_metrics_summary': {
            'evidence_chain_avg': round(avg_evidence, 3),
            'legal_citation_avg': round(avg_citation, 3),
            'remediation_avg': round(avg_remediation, 3),
            'explainability_avg': round(avg_explainability, 3),
            'structured_output_avg': round(avg_structured, 3),
            'overall_avg': round((avg_evidence + avg_citation + avg_remediation + avg_explainability + avg_structured) / 5, 3)
        },
        'performance': {
            'avg_response_time': round(avg_response_time, 2)
        },
        'node_timings_avg_ms': node_timings_avg_ms,
    }


def save_results(results, metrics, output_path):
    """保存评估结果"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        'metadata': {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_cases': len(results),
            'method': 'Agent (6-node workflow, with agent_trace)'
        },
        'metrics': metrics,
        'results': results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_path}")


def print_summary(metrics):
    """打印评估摘要"""
    print("\n" + "=" * 80)
    print("评估摘要")
    print("=" * 80)

    print(f"\n总案例数: {metrics['total']}")
    print(f"成功数: {metrics['successful']}/{metrics['total']}")
    print(f"错误率: {metrics['error_rate']:.2%}")

    print(f"\n二分类准确率: {metrics['accuracy']:.2%}")
    print(f"违规类型准确率 (TP cases): {metrics['violation_type_accuracy']:.2%}")

    print(f"\n质量指标:")
    print(f"  - 法律依据质量: {metrics['quality_metrics']['avg_legal_basis_score']:.2%}")
    print(f"  - 推理质量: {metrics['quality_metrics']['avg_reasoning_score']:.2%}")

    print(f"\n高级评估指标:")
    adv = metrics['advanced_metrics_summary']
    print(f"  - 证据链完整性: {adv['evidence_chain_avg']:.3f}")
    print(f"  - 法律引用准确性: {adv['legal_citation_avg']:.3f}")
    print(f"  - 整改建议可操作性: {adv['remediation_avg']:.3f}")
    print(f"  - 可解释性: {adv['explainability_avg']:.3f}")
    print(f"  - 结构化输出质量: {adv['structured_output_avg']:.3f}")
    print(f"  - 综合平均分: {adv['overall_avg']:.3f}")

    print(f"\nAgent特性:")
    print(f"  - 验证通过率: {metrics['validation_passed_rate']:.2%}")
    print(f"  - 反思触发率: {metrics['reflection_triggered_rate']:.2%}")

    print(f"\n性能指标:")
    print(f"  - 平均响应时间: {metrics['performance']['avg_response_time']:.2f}s")
    nt = metrics.get('node_timings_avg_ms') or {}
    if nt:
        print(f"\n各节点平均耗时 (ms, 不含网络排队):")
        for k, v in nt.items():
            print(f"  - {k}: {v}")


def main():
    args = parse_args()

    print("=" * 80)
    print("Agent系统完整评估")
    print("=" * 80)

    # 收集运行备注（必填）
    note = collect_required_note(args.note)

    # 创建本次运行文件夹（备注+日期）
    run_dir = create_run_dir("results/agent", note)
    print(f"本次运行目录: {run_dir}")

    # 仅对比模式：不运行评估，记录run_info并输出最近一次结果位置
    if args.compare_only:
        latest = find_latest_agent_result("results/agent")
        run_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "agent",
            "mode": "compare_only",
            "models": ["agent"],
            "latest_result_source": str(latest) if latest else None,
            "eval_data": args.eval_data,
            "limit": args.limit,
            "note": note
        }
        with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
            json.dump(run_info, f, ensure_ascii=False, indent=2)

        note_path = Path(run_dir) / "comparison_note.md"
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write("# Agent compare-only 记录\n\n")
            f.write("本次未运行评估，仅创建运行记录，便于追溯。\n\n")
            f.write(f"- 最新一次Agent结果: `{latest}`\n" if latest else "- 未找到历史Agent结果（results/agent/*/results.json）\n")
            f.write("- 建议：如需生成正式结果，请去掉 `--compare-only` 并运行评测。\n")

        print("\n" + "=" * 80)
        print("compare-only 完成（未运行评估）")
        print("=" * 80)
        print(f"本次运行目录: {run_dir}")
        print("生成的文件:")
        print(f"  - {run_dir}/run_info.json")
        print(f"  - {run_dir}/comparison_note.md")
        if note:
            print(f"\n运行备注: {note}")
        return

    output_path = str(Path(run_dir) / "results.json")

    # 加载评估数据（v4格式适配）
    from src.evaluation.dataset_adapter import DatasetAdapter
    adapter = DatasetAdapter(args.eval_data)
    eval_cases = adapter.to_legacy_format(limit=args.limit)
    gt_map = adapter.get_ground_truth_map()

    stats = adapter.get_statistics()
    print(f"数据集: {stats['total']} 条 ({stats['violations']} 违规 + {stats['compliants']} 合规)")
    print(f"加载了 {len(eval_cases)} 个评估案例")

    # 写 run_info.json
    run_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "agent",
        "models": ["agent"],
        "eval_data": args.eval_data,
        "eval_cases": len(eval_cases),
        "limit": args.limit,
        "note": note
    }
    with open(Path(run_dir) / "run_info.json", 'w', encoding='utf-8') as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    # 初始化组件
    print("\n初始化Agent系统...")
    coordinator = AgentCoordinator()
    parser = ResponseParser()  # 复用Baseline的质量评估方法

    # 初始化Ground Truth提取器和高级评估器
    print("\n[初始化] 加载Ground Truth...")
    gt_extractor = GroundTruthExtractor(gt_map=gt_map)
    print(f"[完成] 加载了 {len(gt_extractor.ground_truths)} 个案例的Ground Truth")

    advanced_evaluator = AdvancedMetricsEvaluator()

    # 运行评估
    results = []
    total = len(eval_cases)

    print(f"\n开始评估 {total} 个案例...")
    print(f"预计时间: {total * 8 / 60:.1f} 分钟 (按每案例8秒估算)")

    for idx, eval_case in enumerate(eval_cases, 1):
        result = evaluate_single_case(coordinator, parser, eval_case, idx, total, gt_extractor, advanced_evaluator)
        results.append(result)

        # 定期保存进度
        if idx % args.save_interval == 0:
            temp_metrics = calculate_metrics(results)
            temp_output = output_path.replace('.json', f'_progress_{idx}.json')
            save_results(results, temp_metrics, temp_output)
            print(f"\n进度已保存 ({idx}/{total})")

    # 计算最终指标
    print("\n计算最终指标...")
    metrics = calculate_metrics(results)

    # 保存最终结果
    save_results(results, metrics, output_path)

    # 法条检索F1评测（v4新增）
    from src.evaluation.legal_retrieval_evaluator import LegalRetrievalEvaluator, print_evaluation_summary
    legal_evaluator = LegalRetrievalEvaluator(gt_map)
    legal_summary = legal_evaluator.evaluate_batch(results)
    print_evaluation_summary(legal_summary, method_name="Agent")

    # 打印摘要
    print_summary(metrics)

    print("\n" + "=" * 80)
    print("评估完成！")
    print("=" * 80)
    print(f"本次运行目录: {run_dir}")
    print(f"生成的文件:")
    print(f"  - {output_path}")
    print(f"  - {run_dir}/run_info.json")
    if note:
        print(f"\n运行备注: {note}")


if __name__ == "__main__":
    main()
