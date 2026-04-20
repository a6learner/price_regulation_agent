"""生成应用案例详细展示

功能:
1. 选择5个典型案例（覆盖不同复杂度和场景）
2. 加载三方法的输出结果
3. 生成markdown格式的对比报告
4. 包含推理过程、指标评分、可视化

运行:
    # 使用默认案例ID
    python scripts/generate_case_showcase.py

    # 指定自定义案例ID
    python scripts/generate_case_showcase.py --case-ids eval_001,eval_074,eval_148

    # 指定输出路径
    python scripts/generate_case_showcase.py --output docs/case_showcase.md
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="生成应用案例详细展示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--case-ids',
        type=str,
        default='eval_001,eval_074,eval_148,eval_031,eval_155',
        help='案例ID列表（逗号分隔）'
    )

    parser.add_argument(
        '--baseline-result',
        type=str,
        default='results/baseline/qwen-8b_results.json',
        help='Baseline结果文件路径'
    )

    parser.add_argument(
        '--rag-result',
        type=str,
        default='results/rag/qwen-8b-rag_results.json',
        help='RAG结果文件路径'
    )

    parser.add_argument(
        '--agent-result',
        type=str,
        default='results/agent/full_eval_results.json',
        help='Agent结果文件路径'
    )

    parser.add_argument(
        '--eval-data',
        type=str,
        default='data/eval/eval_159.jsonl',
        help='评估数据文件路径'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='docs/case_showcase.md',
        help='输出文件路径'
    )

    return parser.parse_args()


def load_eval_data(eval_path: str) -> Dict[str, Any]:
    """加载评估数据，构建case_id索引"""
    eval_path = Path(eval_path)
    if not eval_path.exists():
        print(f"[错误] 评估数据不存在: {eval_path}")
        return {}

    cases = {}
    with open(eval_path, 'r', encoding='utf-8') as f:
        for line in f:
            case = json.loads(line)
            case_id = case['meta']['case_id']
            cases[case_id] = case

    return cases


def load_results(result_path: str) -> Dict[str, Any]:
    """加载评估结果，构建case_id索引"""
    result_path = Path(result_path)
    if not result_path.exists():
        print(f"[警告] 结果文件不存在: {result_path}")
        return {}

    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 构建case_id -> result映射
    results_by_id = {}
    for result in data.get('results', []):
        case_id = result.get('case_id')
        if case_id:
            results_by_id[case_id] = result

    return results_by_id


def format_case_description(case: Dict[str, Any]) -> str:
    """格式化案例描述"""
    meta = case['meta']
    user_content = case['messages'][1]['content']

    description = f"""### 案例信息

- **案例ID**: {meta['case_id']}
- **平台**: {meta.get('platform', 'N/A')}
- **场景**: {meta.get('scenario', 'N/A')}
- **复杂度**: {meta.get('complexity', 'N/A')}
- **Ground Truth**: {'违规' if meta['is_violation'] else '合规'} - {meta.get('violation_type', meta.get('compliance_type', 'N/A'))}

### 案例描述

{user_content}

"""
    return description


def format_method_output(method_name: str, result: Dict[str, Any], include_remediation: bool = False) -> str:
    """格式化单个方法的输出"""
    if not result:
        return f"### {method_name}输出\n\n（结果未找到）\n\n"

    output = f"### {method_name}输出\n\n"

    # 判断结果
    is_violation = result.get('is_violation')
    violation_type = result.get('violation_type', 'N/A')
    confidence = result.get('confidence', 0.0)

    output += f"**判断**: {'违规' if is_violation else '合规'} - {violation_type}\n\n"
    output += f"**置信度**: {confidence:.2%}\n\n"

    # 法律依据
    legal_basis = result.get('output', {}).get('legal_basis', '') or result.get('legal_basis', '')
    if legal_basis:
        output += f"**法律依据**: {legal_basis[:200]}{'...' if len(legal_basis) > 200 else ''}\n\n"

    # 推理过程
    reasoning_chain = result.get('output', {}).get('reasoning_chain', []) or result.get('reasoning_chain', [])
    if reasoning_chain:
        output += f"**推理过程**:\n\n"
        for i, step in enumerate(reasoning_chain[:3], 1):  # 只显示前3步
            output += f"{i}. {step}\n"
        if len(reasoning_chain) > 3:
            output += f"   ... (共{len(reasoning_chain)}步)\n"
        output += "\n"
    else:
        reasoning = result.get('output', {}).get('reasoning', '') or result.get('reasoning', '')
        if reasoning:
            output += f"**推理**: {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}\n\n"

    # Remediation（仅Agent有）
    if include_remediation:
        remediation = result.get('output', {}).get('remediation', {}) or result.get('remediation', {})
        if remediation and remediation.get('has_violation'):
            output += f"**整改建议**:\n\n"
            steps = remediation.get('remediation_steps', [])
            for step in steps[:3]:  # 显示前3条
                output += f"- [{step.get('priority', 'N/A').upper()}] {step.get('action', 'N/A')}\n"
            output += "\n"

    return output


def format_metric_comparison(case_id: str, baseline_result: Dict, rag_result: Dict, agent_result: Dict) -> str:
    """格式化指标对比表格"""
    comparison = f"""### 指标对比

| 指标 | Baseline | RAG | Agent |
|------|----------|-----|-------|
"""

    # 提取高级指标
    def get_advanced_metrics(result):
        if not result:
            return {}
        return result.get('advanced_metrics', {}).get('summary', {})

    baseline_adv = get_advanced_metrics(baseline_result)
    rag_adv = get_advanced_metrics(rag_result)
    agent_adv = get_advanced_metrics(agent_result)

    # 添加各项指标
    metrics = [
        ('Binary Accuracy', 'match'),
        ('Evidence Chain', 'evidence_chain_score'),
        ('Legal Citation', 'legal_citation_score'),
        ('Remediation', 'remediation_score'),
        ('Explainability', 'explainability_score'),
        ('Structured Output', 'structured_output_score')
    ]

    for metric_name, metric_key in metrics:
        baseline_val = baseline_adv.get(metric_key, 0.0) if baseline_adv else 0.0
        rag_val = rag_adv.get(metric_key, 0.0) if rag_adv else 0.0
        agent_val = agent_adv.get(metric_key, 0.0) if agent_adv else 0.0

        # 特殊处理Binary Accuracy
        if metric_key == 'match':
            baseline_val = '✅' if baseline_result.get('match') else '❌'
            rag_val = '✅' if rag_result.get('match') else '❌'
            agent_val = '✅' if agent_result.get('match') else '❌'
            comparison += f"| {metric_name} | {baseline_val} | {rag_val} | {agent_val} |\n"
        else:
            comparison += f"| {metric_name} | {baseline_val:.3f} | {rag_val:.3f} | {agent_val:.3f} |\n"

    comparison += "\n"
    return comparison


def format_key_insights(case: Dict, baseline_result: Dict, rag_result: Dict, agent_result: Dict) -> str:
    """生成关键洞察"""
    insights = "### 关键洞察\n\n"

    # 判断哪个方法表现最好
    baseline_match = baseline_result.get('match', False) if baseline_result else False
    rag_match = rag_result.get('match', False) if rag_result else False
    agent_match = agent_result.get('match', False) if agent_result else False

    all_correct = baseline_match and rag_match and agent_match
    all_wrong = not (baseline_match or rag_match or agent_match)

    if all_correct:
        insights += "✅ **三种方法均正确判断**\n\n"
        insights += "- 此案例为三方法都能准确识别的典型案例\n"
        insights += "- Agent的优势体现在推理过程的完整性和整改建议的可操作性\n\n"
    elif all_wrong:
        insights += "❌ **三种方法均判断错误**\n\n"
        insights += "- 此案例为高难度案例，需要进一步优化\n"
        insights += "- 可能的原因：案例描述不清晰、法律条款复杂、边界情况\n\n"
    else:
        insights += "⚠️ **方法间存在差异**\n\n"
        if agent_match and not baseline_match:
            insights += "- Agent成功识别，Baseline失败 → 多步推理优势明显\n"
        if agent_match and not rag_match:
            insights += "- Agent成功识别，RAG失败 → 可能因为检索噪声影响\n"
        if rag_match and not baseline_match:
            insights += "- RAG成功识别，Baseline失败 → 外部知识检索有效\n"
        insights += "\n"

    # 高级指标分析
    if agent_result:
        agent_adv = agent_result.get('advanced_metrics', {}).get('summary', {})
        if agent_adv:
            evidence_score = agent_adv.get('evidence_chain_score', 0)
            remediation_score = agent_adv.get('remediation_score', 0)

            if evidence_score > 0.8:
                insights += f"- **证据链完整性高** ({evidence_score:.3f}): Agent的5步推理链清晰完整\n"
            if remediation_score > 0.7:
                insights += f"- **整改建议可操作** ({remediation_score:.3f}): 提供了具体的整改步骤\n"

    insights += "\n"
    return insights


def generate_case_showcase(case_ids: List[str],
                           eval_data: Dict,
                           baseline_results: Dict,
                           rag_results: Dict,
                           agent_results: Dict) -> str:
    """生成完整的案例展示报告"""
    report = f"""# 应用案例详细展示

**生成时间**: {Path().absolute()}
**案例数量**: {len(case_ids)} 个

本文档展示了5个典型案例在三种方法（Baseline, RAG, Agent）上的表现对比，涵盖不同复杂度和场景。

---

"""

    for idx, case_id in enumerate(case_ids, 1):
        case = eval_data.get(case_id)
        if not case:
            print(f"[警告] 案例不存在: {case_id}")
            continue

        baseline_result = baseline_results.get(case_id)
        rag_result = rag_results.get(case_id)
        agent_result = agent_results.get(case_id)

        report += f"## 案例{idx}: {case_id}\n\n"

        # 案例描述
        report += format_case_description(case)

        # 三方法输出
        report += "## 三方法对比\n\n"
        report += format_method_output("Baseline", baseline_result)
        report += format_method_output("RAG", rag_result)
        report += format_method_output("Agent", agent_result, include_remediation=True)

        # 指标对比
        report += format_metric_comparison(case_id, baseline_result, rag_result, agent_result)

        # 关键洞察
        report += format_key_insights(case, baseline_result, rag_result, agent_result)

        report += "---\n\n"

    # 添加总结
    report += """## 总结

通过对5个典型案例的详细分析，我们可以得出以下结论：

### 1. Baseline方法
- **优势**: 实现简单，成本低，适合快速原型
- **劣势**: 推理过程不透明，缺乏证据链
- **适用场景**: 简单案例、批量快速处理

### 2. RAG方法
- **优势**: 引入外部知识，法律引用更准确
- **劣势**: 可能引入检索噪声，影响判断
- **适用场景**: 需要准确法律依据的场景

### 3. Agent方法
- **优势**: 推理透明、结构化输出、提供整改建议
- **劣势**: 成本较高，响应时间较长
- **适用场景**: 商家自查、监管报告、需要详细分析

### 核心发现

- **准确率**: Agent在复杂案例上的优势更明显
- **可解释性**: Agent的5步推理链显著提升了可解释性
- **实用价值**: Agent的整改建议功能为商家提供了实际操作指导
- **成本权衡**: Agent的成本增加是可接受的，质量提升显著

"""

    return report


def main():
    args = parse_args()

    print("="*80)
    print("生成应用案例详细展示")
    print("="*80)

    # 解析案例ID
    case_ids = [cid.strip() for cid in args.case_ids.split(',')]
    print(f"\n选择的案例: {', '.join(case_ids)}")

    # 加载数据
    print("\n[1/4] 加载评估数据...")
    eval_data = load_eval_data(args.eval_data)
    print(f"  - 加载了 {len(eval_data)} 个案例")

    print("\n[2/4] 加载三方法结果...")
    baseline_results = load_results(args.baseline_result)
    rag_results = load_results(args.rag_result)
    agent_results = load_results(args.agent_result)
    print(f"  - Baseline: {len(baseline_results)} 个结果")
    print(f"  - RAG: {len(rag_results)} 个结果")
    print(f"  - Agent: {len(agent_results)} 个结果")

    # 生成报告
    print("\n[3/4] 生成案例展示报告...")
    report = generate_case_showcase(
        case_ids,
        eval_data,
        baseline_results,
        rag_results,
        agent_results
    )

    # 保存报告
    print("\n[4/4] 保存报告...")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✓ 案例展示报告已生成: {output_path}")

    print("\n" + "="*80)
    print("生成完成！")
    print("="*80)

    print("\n下一步:")
    print(f"  1. 查看报告: cat {output_path}")
    print("  2. 整理论文材料: 将案例分析整合到论文实验章节")
    print("  3. 准备答辩PPT: 使用案例展示作为演示素材")


if __name__ == "__main__":
    main()
