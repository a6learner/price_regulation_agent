"""
多模型对比器 - 生成N个模型的对比报告
支持任意数量模型的性能对比和可视化
"""

import json
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime


class MultiModelComparator:
    """多模型对比器"""

    def __init__(self, registry):
        """
        初始化对比器

        Args:
            registry: ModelRegistry实例
        """
        self.registry = registry

    def load_results(self, model_keys: List[str], results_dir: str = "results/baseline") -> Dict[str, Any]:
        """
        加载多个模型的评估结果

        Args:
            model_keys: 模型key列表
            results_dir: 结果目录

        Returns:
            {model_key: {'results': [...], 'metrics': {...}}}
        """
        all_results = {}

        for model_key in model_keys:
            result_path = self.registry.find_latest_result(model_key, results_dir)

            if not result_path:
                print(f"[警告] 未找到模型结果: {model_key}")
                continue

            with open(result_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # 如果results是列表（新格式），需要计算metrics
            if isinstance(results, list):
                from .evaluator import BaselineEvaluator
                evaluator = BaselineEvaluator()
                metrics = evaluator.calculate_metrics(results)
                all_results[model_key] = {
                    'results': results,
                    'metrics': metrics
                }
            else:
                # 旧格式：已包含metrics
                all_results[model_key] = results

        return all_results

    def generate_comparison_table(self, all_results: Dict[str, Any]) -> str:
        """
        生成对比表格（Markdown格式）

        Args:
            all_results: 所有模型的结果

        Returns:
            Markdown表格字符串
        """
        if not all_results:
            return "没有可对比的结果"

        model_keys = list(all_results.keys())
        model_names = [self.registry.get_model(k)['name'] for k in model_keys]

        # 表头
        header = "| 指标 | " + " | ".join(model_names) + " |"
        separator = "|" + "|".join(["------"] * (len(model_keys) + 1)) + "|"

        # 准确率指标
        rows = []
        metrics_to_compare = [
            ('accuracy', 'Accuracy'),
            ('precision', 'Precision'),
            ('recall', 'Recall'),
            ('f1_score', 'F1-Score'),
            ('type_accuracy', 'Type Accuracy')
        ]

        for metric_key, metric_name in metrics_to_compare:
            values = []
            for model_key in model_keys:
                metrics = all_results[model_key]['metrics']
                value = metrics.get(metric_key, 0)
                values.append(f"{value:.2%}")

            rows.append(f"| {metric_name} | " + " | ".join(values) + " |")

        # 质量指标
        if any('quality_metrics' in all_results[k]['metrics'] for k in model_keys):
            rows.append("| **质量指标** | " + " | ".join([" "] * len(model_keys)) + " |")

            quality_metrics = [
                ('avg_legal_basis_score', '法律依据质量'),
                ('avg_reasoning_score', '推理质量'),
                ('legal_basis_coverage', '法律依据覆盖率'),
                ('reasoning_coverage', '推理覆盖率')
            ]

            for metric_key, metric_name in quality_metrics:
                values = []
                for model_key in model_keys:
                    qm = all_results[model_key]['metrics'].get('quality_metrics', {})
                    value = qm.get(metric_key, 0)
                    values.append(f"{value:.2%}")

                rows.append(f"| {metric_name} | " + " | ".join(values) + " |")

        return "\n".join([header, separator] + rows)

    def generate_performance_table(self, all_results: Dict[str, Any]) -> str:
        """
        生成性能对比表格

        Args:
            all_results: 所有模型的结果

        Returns:
            Markdown表格字符串
        """
        model_keys = list(all_results.keys())
        model_names = [self.registry.get_model(k)['name'] for k in model_keys]

        header = "| 指标 | " + " | ".join(model_names) + " |"
        separator = "|" + "|".join(["------"] * (len(model_keys) + 1)) + "|"

        # 性能指标
        rows = []
        perf_metrics = [
            ('avg_response_time', '平均响应时间', 's'),
            ('total_tokens', '总Token数', ''),
            ('total_input_tokens', '输入Token', ''),
            ('total_output_tokens', '输出Token', '')
        ]

        for metric_key, metric_name, unit in perf_metrics:
            values = []
            for model_key in model_keys:
                perf = all_results[model_key]['metrics']['performance']
                value = perf.get(metric_key, 0)

                if 'token' in metric_key.lower():
                    values.append(f"{value:,}{unit}")
                else:
                    values.append(f"{value}{unit}")

            rows.append(f"| {metric_name} | " + " | ".join(values) + " |")

        return "\n".join([header, separator] + rows)

    def generate_confusion_matrices(self, all_results: Dict[str, Any]) -> str:
        """
        生成所有模型的混淆矩阵

        Args:
            all_results: 所有模型的结果

        Returns:
            Markdown格式的混淆矩阵
        """
        sections = []

        for model_key, data in all_results.items():
            model_name = self.registry.get_model(model_key)['name']
            cm = data['metrics']['confusion_matrix']

            matrix = f"""### {model_name}
```
              预测违规    预测合规
实际违规        {cm['TP']:<5}       {cm['FN']:<5}
实际合规        {cm['FP']:<5}       {cm['TN']:<5}
```
"""
            sections.append(matrix)

        return "\n".join(sections)

    def generate_ranking(self, all_results: Dict[str, Any]) -> str:
        """
        生成模型排名

        Args:
            all_results: 所有模型的结果

        Returns:
            排名文本
        """
        # 综合评分：准确率40% + F1 30% + 法律质量15% + 推理质量15%
        scores = {}

        for model_key, data in all_results.items():
            metrics = data['metrics']
            score = (
                metrics.get('accuracy', 0) * 0.4 +
                metrics.get('f1_score', 0) * 0.3
            )

            # 质量指标（如果有）
            if 'quality_metrics' in metrics:
                qm = metrics['quality_metrics']
                score += qm.get('avg_legal_basis_score', 0) * 0.15
                score += qm.get('avg_reasoning_score', 0) * 0.15

            scores[model_key] = score

        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        lines = []
        for rank, (model_key, score) in enumerate(ranked, 1):
            model_name = self.registry.get_model(model_key)['name']
            medal = ["[金牌]", "[银牌]", "[铜牌]"][rank-1] if rank <= 3 else ""
            lines.append(f"{rank}. {model_name}: {score:.2%} {medal}")

        return "\n".join(lines)

    def generate_report(
        self,
        model_keys: List[str],
        output_path: str = "results/baseline/multi_model_comparison.md",
        results_dir: str = "results/baseline"
    ):
        """
        生成多模型对比报告

        Args:
            model_keys: 要对比的模型key列表
            output_path: 输出文件路径
            results_dir: 结果目录
        """
        # 加载结果
        all_results = self.load_results(model_keys, results_dir)

        if not all_results:
            print("[错误] 没有找到任何模型结果")
            return

        # 生成报告
        report = f"""# 多模型评估对比报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**对比模型**: {', '.join([self.registry.get_model(k)['name'] for k in all_results.keys()])}
**评估数据集**: data/eval/eval_159.jsonl (159个案例)

---

## 1. 综合排名

{self.generate_ranking(all_results)}

**评分说明**: 综合分数 = Accuracy×40% + F1×30% + 法律依据质量×15% + 推理质量×15%

---

## 2. 准确率与质量指标对比

{self.generate_comparison_table(all_results)}

---

## 3. 性能指标对比

{self.generate_performance_table(all_results)}

---

## 4. 混淆矩阵

{self.generate_confusion_matrices(all_results)}

---

## 5. 详细分析

### 最佳模型特征

"""

        # 找到最佳模型
        best_model = max(
            all_results.items(),
            key=lambda x: x[1]['metrics'].get('f1_score', 0)
        )
        best_key, best_data = best_model
        best_name = self.registry.get_model(best_key)['name']

        report += f"""**{best_name}** 在F1-Score上表现最佳:
- Accuracy: {best_data['metrics']['accuracy']:.2%}
- F1-Score: {best_data['metrics']['f1_score']:.2%}
- 平均响应时间: {best_data['metrics']['performance']['avg_response_time']}s

"""

        # 成本效率分析
        report += """### 成本效率分析

"""
        for model_key, data in sorted(
            all_results.items(),
            key=lambda x: x[1]['metrics']['performance']['total_tokens']
        ):
            model_name = self.registry.get_model(model_key)['name']
            tokens = data['metrics']['performance']['total_tokens']
            accuracy = data['metrics']['accuracy']

            report += f"- **{model_name}**: {tokens:,} tokens (准确率: {accuracy:.2%})\n"

        # 建议
        report += """

---

## 6. 下一步建议

1. **Baseline已完成**: 大模型准确率接近100%，但成本高
2. **考虑小模型**: 尝试7B模型建立新baseline，为RAG/Agent提供对比空间
3. **实现RAG系统**: 预期提升法律依据准确性和引用质量
4. **实现Agent系统**: 预期提升推理可解释性和多步推理能力

---

*本报告由多模型评估系统自动生成*
"""

        # 保存报告
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n[成功] 对比报告已生成: {output_path}")

    def print_summary(self, model_keys: List[str], results_dir: str = "results/baseline"):
        """
        在控制台打印对比摘要

        Args:
            model_keys: 模型key列表
            results_dir: 结果目录
        """
        all_results = self.load_results(model_keys, results_dir)

        if not all_results:
            print("[错误] 没有找到任何模型结果")
            return

        print("\n" + "="*70)
        print("多模型对比摘要")
        print("="*70)

        print(f"\n对比模型数量: {len(all_results)}")
        for key in all_results.keys():
            model_name = self.registry.get_model(key)['name']
            print(f"  - {model_name} ({key})")

        print(f"\n{self.generate_comparison_table(all_results)}")

        print("\n" + "="*70)
