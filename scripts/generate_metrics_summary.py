"""
生成三方法指标汇总对比报告

从Baseline、RAG、Agent的结果文件中提取所有指标，
生成Markdown格式的对比表格和分析报告。

使用示例:
    python scripts/generate_metrics_summary.py

    # 指定自定义路径
    python scripts/generate_metrics_summary.py \
        --baseline results/baseline_754/qwen-8b_results.json \
        --rag results/rag_754/qwen-8b-rag_results.json \
        --agent results/agent_754/full_eval_results.json \
        --output results/comparison_754/metrics_summary.md
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args():
    parser = argparse.ArgumentParser(description="生成三方法指标汇总对比")

    parser.add_argument(
        '--baseline',
        type=str,
        default='results/baseline_754/qwen-8b_results.json',
        help='Baseline结果文件'
    )

    parser.add_argument(
        '--rag',
        type=str,
        default='results/rag_754/qwen-8b-rag_results.json',
        help='RAG结果文件'
    )

    parser.add_argument(
        '--agent',
        type=str,
        default='results/agent_754/full_eval_results.json',
        help='Agent结果文件'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='results/comparison_754/metrics_summary.md',
        help='输出报告路径'
    )

    return parser.parse_args()


def load_results(file_path: str) -> dict:
    """加载结果文件并提取指标"""
    if not Path(file_path).exists():
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理不同格式
    if isinstance(data, list):
        # Baseline/RAG格式
        results = data
        metrics_data = {}
    else:
        # Agent格式
        results = data.get('results', [])
        metrics_data = data.get('metrics', {})

    # 计算基础指标
    success_results = [r for r in results if r.get('success', True)]
    total = len(success_results)

    if total == 0:
        return None

    # 二分类指标
    tp = sum(1 for r in success_results if r.get('metrics', {}).get('is_correct') and r.get('ground_truth', {}).get('is_violation'))
    tn = sum(1 for r in success_results if r.get('metrics', {}).get('is_correct') and not r.get('ground_truth', {}).get('is_violation'))
    fp = sum(1 for r in success_results if not r.get('metrics', {}).get('is_correct') and not r.get('ground_truth', {}).get('is_violation'))
    fn = sum(1 for r in success_results if not r.get('metrics', {}).get('is_correct') and r.get('ground_truth', {}).get('is_violation'))

    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # 违规类型准确率
    type_correct = sum(1 for r in success_results if r.get('metrics', {}).get('type_correct', False))
    type_accuracy = type_correct / total if total > 0 else 0

    # 质量指标
    legal_scores = []
    reasoning_scores = []
    for r in success_results:
        qm = r.get('quality_metrics', {})
        if isinstance(qm, dict):
            lb = qm.get('legal_basis', {})
            rs = qm.get('reasoning', {})
            if isinstance(lb, dict):
                legal_scores.append(lb.get('legal_basis_score', 0))
            if isinstance(rs, dict):
                reasoning_scores.append(rs.get('reasoning_score', 0))

    avg_legal = sum(legal_scores) / len(legal_scores) if legal_scores else 0
    avg_reasoning = sum(reasoning_scores) / len(reasoning_scores) if reasoning_scores else 0

    # 高级指标
    adv_evidence = []
    adv_citation = []
    adv_remediation = []
    adv_explainability = []
    adv_structured = []

    for r in success_results:
        am = r.get('advanced_metrics', {})
        summary = am.get('summary', {})
        adv_evidence.append(summary.get('evidence_chain_score', 0))
        adv_citation.append(summary.get('legal_citation_score', 0))
        adv_remediation.append(summary.get('remediation_score', 0))
        adv_explainability.append(summary.get('explainability_score', 0))
        adv_structured.append(summary.get('structured_output_score', 0))

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    # 性能指标
    response_times = []
    input_tokens = []
    output_tokens = []

    for r in success_results:
        perf = r.get('performance', {})
        if perf.get('response_time'):
            response_times.append(perf['response_time'])
        if perf.get('input_tokens'):
            input_tokens.append(perf['input_tokens'])
        if perf.get('output_tokens'):
            output_tokens.append(perf['output_tokens'])

    return {
        'total': total,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'type_accuracy': type_accuracy,
        'confusion': {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn},
        'quality': {
            'legal_basis': avg_legal,
            'reasoning': avg_reasoning
        },
        'advanced': {
            'evidence_chain': avg(adv_evidence),
            'legal_citation': avg(adv_citation),
            'remediation': avg(adv_remediation),
            'explainability': avg(adv_explainability),
            'structured_output': avg(adv_structured),
            'overall': avg([avg(adv_evidence), avg(adv_citation), avg(adv_remediation),
                           avg(adv_explainability), avg(adv_structured)])
        },
        'performance': {
            'avg_response_time': avg(response_times),
            'total_input_tokens': sum(input_tokens),
            'total_output_tokens': sum(output_tokens),
            'total_tokens': sum(input_tokens) + sum(output_tokens)
        }
    }


def generate_report(baseline: dict, rag: dict, agent: dict, output_path: str):
    """生成Markdown报告"""

    def fmt_pct(v):
        return f"{v*100:.2f}%" if v else "N/A"

    def fmt_score(v):
        return f"{v:.3f}" if v else "N/A"

    def fmt_diff(new, old):
        if old is None or new is None:
            return "N/A"
        diff = new - old
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff*100:.2f}%"

    def fmt_diff_score(new, old):
        if old is None or new is None:
            return "N/A"
        diff = new - old
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.3f}"

    # 生成报告
    report = f"""# 三方法评估指标汇总对比报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据集**: eval_754.jsonl (753条案例)
**模型**: Qwen3-8B

---

## 1. 核心指标对比

### 1.1 二分类准确性

| 指标 | Baseline | RAG | Agent | RAG vs Baseline | Agent vs Baseline |
|------|----------|-----|-------|-----------------|-------------------|
| **Accuracy** | {fmt_pct(baseline['accuracy'] if baseline else None)} | {fmt_pct(rag['accuracy'] if rag else None)} | {fmt_pct(agent['accuracy'] if agent else None)} | {fmt_diff(rag['accuracy'] if rag else None, baseline['accuracy'] if baseline else None)} | {fmt_diff(agent['accuracy'] if agent else None, baseline['accuracy'] if baseline else None)} |
| Precision | {fmt_pct(baseline['precision'] if baseline else None)} | {fmt_pct(rag['precision'] if rag else None)} | {fmt_pct(agent['precision'] if agent else None)} | {fmt_diff(rag['precision'] if rag else None, baseline['precision'] if baseline else None)} | {fmt_diff(agent['precision'] if agent else None, baseline['precision'] if baseline else None)} |
| Recall | {fmt_pct(baseline['recall'] if baseline else None)} | {fmt_pct(rag['recall'] if rag else None)} | {fmt_pct(agent['recall'] if agent else None)} | {fmt_diff(rag['recall'] if rag else None, baseline['recall'] if baseline else None)} | {fmt_diff(agent['recall'] if agent else None, baseline['recall'] if baseline else None)} |
| F1-Score | {fmt_pct(baseline['f1'] if baseline else None)} | {fmt_pct(rag['f1'] if rag else None)} | {fmt_pct(agent['f1'] if agent else None)} | {fmt_diff(rag['f1'] if rag else None, baseline['f1'] if baseline else None)} | {fmt_diff(agent['f1'] if agent else None, baseline['f1'] if baseline else None)} |
| **违规类型准确率** | {fmt_pct(baseline['type_accuracy'] if baseline else None)} | {fmt_pct(rag['type_accuracy'] if rag else None)} | {fmt_pct(agent['type_accuracy'] if agent else None)} | {fmt_diff(rag['type_accuracy'] if rag else None, baseline['type_accuracy'] if baseline else None)} | {fmt_diff(agent['type_accuracy'] if agent else None, baseline['type_accuracy'] if baseline else None)} |

### 1.2 混淆矩阵

| 方法 | TP | TN | FP | FN |
|------|----|----|----|----|
| Baseline | {baseline['confusion']['tp'] if baseline else 'N/A'} | {baseline['confusion']['tn'] if baseline else 'N/A'} | {baseline['confusion']['fp'] if baseline else 'N/A'} | {baseline['confusion']['fn'] if baseline else 'N/A'} |
| RAG | {rag['confusion']['tp'] if rag else 'N/A'} | {rag['confusion']['tn'] if rag else 'N/A'} | {rag['confusion']['fp'] if rag else 'N/A'} | {rag['confusion']['fn'] if rag else 'N/A'} |
| Agent | {agent['confusion']['tp'] if agent else 'N/A'} | {agent['confusion']['tn'] if agent else 'N/A'} | {agent['confusion']['fp'] if agent else 'N/A'} | {agent['confusion']['fn'] if agent else 'N/A'} |

---

## 2. 质量指标对比

### 2.1 传统质量指标

| 指标 | Baseline | RAG | Agent | RAG vs Baseline | Agent vs Baseline |
|------|----------|-----|-------|-----------------|-------------------|
| **法律依据质量** | {fmt_pct(baseline['quality']['legal_basis'] if baseline else None)} | {fmt_pct(rag['quality']['legal_basis'] if rag else None)} | {fmt_pct(agent['quality']['legal_basis'] if agent else None)} | {fmt_diff(rag['quality']['legal_basis'] if rag else None, baseline['quality']['legal_basis'] if baseline else None)} | {fmt_diff(agent['quality']['legal_basis'] if agent else None, baseline['quality']['legal_basis'] if baseline else None)} |
| **推理质量** | {fmt_pct(baseline['quality']['reasoning'] if baseline else None)} | {fmt_pct(rag['quality']['reasoning'] if rag else None)} | {fmt_pct(agent['quality']['reasoning'] if agent else None)} | {fmt_diff(rag['quality']['reasoning'] if rag else None, baseline['quality']['reasoning'] if baseline else None)} | {fmt_diff(agent['quality']['reasoning'] if agent else None, baseline['quality']['reasoning'] if baseline else None)} |

### 2.2 高级质量指标

| 指标 | Baseline | RAG | Agent | RAG vs Baseline | Agent vs Baseline |
|------|----------|-----|-------|-----------------|-------------------|
| 证据链完整性 | {fmt_score(baseline['advanced']['evidence_chain'] if baseline else None)} | {fmt_score(rag['advanced']['evidence_chain'] if rag else None)} | {fmt_score(agent['advanced']['evidence_chain'] if agent else None)} | {fmt_diff_score(rag['advanced']['evidence_chain'] if rag else None, baseline['advanced']['evidence_chain'] if baseline else None)} | {fmt_diff_score(agent['advanced']['evidence_chain'] if agent else None, baseline['advanced']['evidence_chain'] if baseline else None)} |
| 法律引用准确性 | {fmt_score(baseline['advanced']['legal_citation'] if baseline else None)} | {fmt_score(rag['advanced']['legal_citation'] if rag else None)} | {fmt_score(agent['advanced']['legal_citation'] if agent else None)} | {fmt_diff_score(rag['advanced']['legal_citation'] if rag else None, baseline['advanced']['legal_citation'] if baseline else None)} | {fmt_diff_score(agent['advanced']['legal_citation'] if agent else None, baseline['advanced']['legal_citation'] if baseline else None)} |
| 整改建议可操作性 | {fmt_score(baseline['advanced']['remediation'] if baseline else None)} | {fmt_score(rag['advanced']['remediation'] if rag else None)} | {fmt_score(agent['advanced']['remediation'] if agent else None)} | {fmt_diff_score(rag['advanced']['remediation'] if rag else None, baseline['advanced']['remediation'] if baseline else None)} | {fmt_diff_score(agent['advanced']['remediation'] if agent else None, baseline['advanced']['remediation'] if baseline else None)} |
| 可解释性 | {fmt_score(baseline['advanced']['explainability'] if baseline else None)} | {fmt_score(rag['advanced']['explainability'] if rag else None)} | {fmt_score(agent['advanced']['explainability'] if agent else None)} | {fmt_diff_score(rag['advanced']['explainability'] if rag else None, baseline['advanced']['explainability'] if baseline else None)} | {fmt_diff_score(agent['advanced']['explainability'] if agent else None, baseline['advanced']['explainability'] if baseline else None)} |
| 结构化输出质量 | {fmt_score(baseline['advanced']['structured_output'] if baseline else None)} | {fmt_score(rag['advanced']['structured_output'] if rag else None)} | {fmt_score(agent['advanced']['structured_output'] if agent else None)} | {fmt_diff_score(rag['advanced']['structured_output'] if rag else None, baseline['advanced']['structured_output'] if baseline else None)} | {fmt_diff_score(agent['advanced']['structured_output'] if agent else None, baseline['advanced']['structured_output'] if baseline else None)} |
| **综合平均分** | **{fmt_score(baseline['advanced']['overall'] if baseline else None)}** | **{fmt_score(rag['advanced']['overall'] if rag else None)}** | **{fmt_score(agent['advanced']['overall'] if agent else None)}** | **{fmt_diff_score(rag['advanced']['overall'] if rag else None, baseline['advanced']['overall'] if baseline else None)}** | **{fmt_diff_score(agent['advanced']['overall'] if agent else None, baseline['advanced']['overall'] if baseline else None)}** |

---

## 3. 性能指标对比

| 指标 | Baseline | RAG | Agent |
|------|----------|-----|-------|
| 平均响应时间 (s) | {baseline['performance']['avg_response_time']:.2f if baseline else 'N/A'} | {rag['performance']['avg_response_time']:.2f if rag else 'N/A'} | {agent['performance']['avg_response_time']:.2f if agent else 'N/A'} |
| 总Token消耗 | {baseline['performance']['total_tokens']:,} | {rag['performance']['total_tokens']:,} | {agent['performance']['total_tokens']:,} |
| 输入Token | {baseline['performance']['total_input_tokens']:,} | {rag['performance']['total_input_tokens']:,} | {agent['performance']['total_input_tokens']:,} |
| 输出Token | {baseline['performance']['total_output_tokens']:,} | {rag['performance']['total_output_tokens']:,} | {agent['performance']['total_output_tokens']:,} |

---

## 4. 核心发现

"""

    # 添加核心发现（基于实际数据）
    if baseline and rag:
        acc_diff = (rag['accuracy'] - baseline['accuracy']) * 100
        if acc_diff > 0:
            report += f"1. **RAG准确率提升**: RAG比Baseline准确率提升了{acc_diff:.2f}%\n"
        elif acc_diff < 0:
            report += f"1. **RAG准确率下降**: RAG比Baseline准确率下降了{-acc_diff:.2f}%\n"
        else:
            report += f"1. **RAG准确率持平**: RAG与Baseline准确率相同\n"

    if baseline and agent:
        acc_diff = (agent['accuracy'] - baseline['accuracy']) * 100 if agent else 0
        if acc_diff > 0:
            report += f"2. **Agent准确率提升**: Agent比Baseline准确率提升了{acc_diff:.2f}%\n"
        elif acc_diff < 0:
            report += f"2. **Agent准确率下降**: Agent比Baseline准确率下降了{-acc_diff:.2f}%\n"

    if baseline and rag:
        adv_diff = rag['advanced']['overall'] - baseline['advanced']['overall']
        if adv_diff > 0:
            report += f"3. **RAG高级指标**: 综合得分比Baseline高{adv_diff:.3f}\n"
        else:
            report += f"3. **RAG高级指标**: 综合得分比Baseline低{-adv_diff:.3f}\n"

    if agent and baseline:
        if agent['advanced']['remediation'] > 0:
            report += f"4. **Agent整改建议**: Agent提供了可操作的整改建议（得分{agent['advanced']['remediation']:.3f}），Baseline和RAG均无此功能\n"

    report += """
---

## 5. 结论与建议

### 5.1 方法选择建议

| 场景 | 推荐方法 | 原因 |
|------|----------|------|
| 快速批量筛查 | Baseline | 响应最快，成本最低 |
| 需要准确分类 | RAG | 结合外部知识，减少误判 |
| 商家自查/监管报告 | Agent | 提供整改建议，推理过程透明 |

### 5.2 改进方向

1. **RAG优化**: 提高检索质量，减少噪声干扰
2. **Agent优化**: 优化多步推理效率，降低响应时间
3. **评估指标**: 引入人工评估验证自动指标的有效性

---

*报告由 generate_metrics_summary.py 自动生成*
"""

    # 保存报告
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"报告已生成: {output_path}")

    # 同时保存JSON格式的数据
    json_path = output_path.with_suffix('.json')
    summary_data = {
        'generated_at': datetime.now().isoformat(),
        'baseline': baseline,
        'rag': rag,
        'agent': agent
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"JSON数据已保存: {json_path}")


def main():
    args = parse_args()

    print("=" * 60)
    print("三方法指标汇总对比")
    print("=" * 60)

    # 加载各方法结果
    print("\n加载结果文件...")

    baseline = None
    rag = None
    agent = None

    if Path(args.baseline).exists():
        baseline = load_results(args.baseline)
        print(f"  Baseline: {baseline['total']} 条结果" if baseline else "  Baseline: 文件不存在或加载失败")
    else:
        print(f"  Baseline: 文件不存在 ({args.baseline})")

    if Path(args.rag).exists():
        rag = load_results(args.rag)
        print(f"  RAG: {rag['total']} 条结果" if rag else "  RAG: 文件不存在或加载失败")
    else:
        print(f"  RAG: 文件不存在 ({args.rag})")

    if Path(args.agent).exists():
        agent = load_results(args.agent)
        print(f"  Agent: {agent['total']} 条结果" if agent else "  Agent: 文件不存在或加载失败")
    else:
        print(f"  Agent: 文件不存在 ({args.agent})")

    if not any([baseline, rag, agent]):
        print("\n[错误] 没有有效的结果文件")
        return

    # 生成报告
    print("\n生成对比报告...")
    generate_report(baseline, rag, agent, args.output)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
