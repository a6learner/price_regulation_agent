"""
Baseline评估器
在评估数据集上运行模型并计算指标
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .maas_client import MaaSClient
from .prompt_template import PromptTemplate
from .response_parser import ResponseParser


class BaselineEvaluator:
    """Baseline评估器"""

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        """
        初始化评估器

        Args:
            config_path: 配置文件路径
        """
        self.client = MaaSClient(config_path)
        self.prompt_template = PromptTemplate()
        self.parser = ResponseParser()

        # 加载配置
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.eval_config = config.get('evaluation', {})
        self.output_config = config.get('output', {})

        # 结果存储
        self.results = []

    def load_eval_data(self, eval_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        加载评估数据

        Args:
            eval_path: 评估数据文件路径
            limit: 限制加载的案例数量，None表示全部加载

        Returns:
            评估案例列表
        """
        eval_cases = []
        with open(eval_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                case = json.loads(line.strip())
                eval_cases.append(case)

        print(f"加载了 {len(eval_cases)} 个评估案例")
        return eval_cases

    def evaluate_single_case(
        self,
        eval_case: Dict[str, Any],
        model_key: str = 'qwen'
    ) -> Dict[str, Any]:
        """
        评估单个案例

        Args:
            eval_case: 评估案例
            model_key: 模型键名

        Returns:
            评估结果字典
        """
        case_id = eval_case.get('meta', {}).get('case_id', 'unknown')

        # 构建提示词
        prompts = self.prompt_template.build_prompts_from_eval(eval_case)

        # 调用模型
        start_time = time.time()
        api_response = self.client.call_model(
            system_prompt=prompts['system_prompt'],
            user_prompt=prompts['user_prompt'],
            model_key=model_key
        )
        response_time = time.time() - start_time

        # 解析响应
        if api_response is None:
            return {
                'case_id': case_id,
                'model': model_key,
                'success': False,
                'error': 'API调用失败'
            }

        response_text = self.client.extract_response_text(api_response)
        if response_text is None:
            return {
                'case_id': case_id,
                'model': model_key,
                'success': False,
                'error': '无法提取响应文本'
            }

        prediction = self.parser.parse_response(response_text)
        if prediction is None:
            return {
                'case_id': case_id,
                'model': model_key,
                'success': False,
                'error': '无法解析响应',
                'raw_response': response_text[:500]
            }

        # 提取ground truth
        ground_truth = self.parser.extract_ground_truth(eval_case)

        # 比较结果
        comparison = self.parser.compare_prediction_with_truth(prediction, ground_truth)

        # 评估法律依据准确性
        legal_eval = self.parser.evaluate_legal_basis_accuracy(prediction)

        # 评估推理质量
        reasoning_eval = self.parser.evaluate_reasoning_quality(prediction)

        # 构建结果
        result = {
            'case_id': case_id,
            'model': model_key,
            'success': True,
            'prediction': prediction,
            'ground_truth': ground_truth,
            'metrics': comparison,
            'quality_metrics': {
                'legal_basis': legal_eval,
                'reasoning': reasoning_eval
            },
            'performance': {
                'response_time': round(response_time, 2),
                'input_tokens': api_response.get('usage', {}).get('prompt_tokens', 0),
                'output_tokens': api_response.get('usage', {}).get('completion_tokens', 0)
            },
            'llm_response': response_text
        }

        return result

    def evaluate_batch(
        self,
        eval_cases: List[Dict[str, Any]],
        model_key: str = 'qwen',
        save_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量评估案例

        Args:
            eval_cases: 评估案例列表
            model_key: 模型键名
            save_progress: 是否保存进度

        Returns:
            评估结果列表
        """
        results = []
        total = len(eval_cases)
        save_interval = self.eval_config.get('save_interval', 10)
        request_interval = self.eval_config.get('request_interval', 0.5)

        print(f"\n开始评估 {total} 个案例 (模型: {model_key})")
        print("=" * 60)

        for i, case in enumerate(eval_cases, 1):
            case_id = case.get('meta', {}).get('case_id', f'case_{i}')
            print(f"\n[{i}/{total}] 评估案例: {case_id}")

            # 评估单个案例
            result = self.evaluate_single_case(case, model_key)
            results.append(result)

            # 打印结果
            if result['success']:
                pred = result['prediction']
                truth = result['ground_truth']
                metrics = result['metrics']
                print(f"  预测: {'违规' if pred['is_violation'] else '合规'} - {pred['violation_type']}")
                print(f"  真值: {'违规' if truth['is_violation'] else '合规'} - {truth['violation_type']}")
                print(f"  判断: {'[正确]' if metrics['is_correct'] else '[错误]'} | "
                      f"类型: {'[正确]' if metrics['type_correct'] else '[错误]'}")
                print(f"  耗时: {result['performance']['response_time']}s")
            else:
                print(f"  错误: {result.get('error', '未知错误')}")

            # 保存中间结果
            if save_progress and i % save_interval == 0:
                self._save_intermediate_results(results, model_key, i, total)

            # 请求间隔
            if i < total:
                time.sleep(request_interval)

        print("\n" + "=" * 60)
        print(f"评估完成！")

        return results

    def _save_intermediate_results(
        self,
        results: List[Dict[str, Any]],
        model_key: str,
        current: int,
        total: int
    ):
        """保存中间结果"""
        output_dir = Path(self.output_config.get('results_dir', 'results/baseline'))
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_key}_progress_{current}of{total}_{timestamp}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n  [进度保存] {filepath}")

    def save_results(
        self,
        results: List[Dict[str, Any]],
        model_key: str,
        output_path: Optional[str] = None
    ):
        """
        保存最终结果

        Args:
            results: 评估结果列表
            model_key: 模型键名
            output_path: 输出路径，None则使用默认路径
        """
        if output_path is None:
            output_dir = Path(self.output_config.get('results_dir', 'results/baseline'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{model_key}_results.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存到: {output_path}")

    def calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算评估指标

        Args:
            results: 评估结果列表

        Returns:
            指标字典
        """
        # 过滤成功的结果
        success_results = [r for r in results if r.get('success', False)]
        total = len(success_results)

        if total == 0:
            return {
                'error': '没有成功的评估结果',
                'total_cases': len(results),
                'success_cases': 0,
                'failed_cases': len(results),
                'accuracy': 0,
                'precision': 0,
                'recall': 0,
                'f1_score': 0,
                'type_accuracy': 0,
                'confusion_matrix': {'TP': 0, 'FP': 0, 'FN': 0, 'TN': 0},
                'quality_metrics': {
                    'avg_legal_basis_score': 0,
                    'avg_reasoning_score': 0,
                    'legal_basis_coverage': 0,
                    'reasoning_coverage': 0
                },
                'performance': {
                    'avg_response_time': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_tokens': 0
                }
            }

        # 统计
        correct_count = sum(1 for r in success_results if r['metrics']['is_correct'])
        type_correct_count = sum(1 for r in success_results if r['metrics']['type_correct'])

        # 计算违规/合规的准确率
        violation_cases = [r for r in success_results if r['ground_truth']['is_violation']]
        compliance_cases = [r for r in success_results if not r['ground_truth']['is_violation']]

        tp = sum(1 for r in violation_cases
                 if r['prediction']['is_violation'] and r['metrics']['is_correct'])
        fp = sum(1 for r in compliance_cases if r['prediction']['is_violation'])
        fn = sum(1 for r in violation_cases if not r['prediction']['is_violation'])
        tn = sum(1 for r in compliance_cases
                 if not r['prediction']['is_violation'] and r['metrics']['is_correct'])

        # 计算性能指标
        total_time = sum(r['performance']['response_time'] for r in success_results)
        total_input_tokens = sum(r['performance']['input_tokens'] for r in success_results)
        total_output_tokens = sum(r['performance']['output_tokens'] for r in success_results)

        # 计算准确率、精确率、召回率、F1
        accuracy = correct_count / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # 计算质量指标（法律依据和推理）
        avg_legal_score = 0
        avg_reasoning_score = 0
        has_legal_count = 0
        has_reasoning_count = 0

        for r in success_results:
            if 'quality_metrics' in r:
                legal_eval = r['quality_metrics'].get('legal_basis', {})
                reasoning_eval = r['quality_metrics'].get('reasoning', {})

                avg_legal_score += legal_eval.get('legal_basis_score', 0)
                avg_reasoning_score += reasoning_eval.get('reasoning_score', 0)

                if legal_eval.get('has_legal_basis', False):
                    has_legal_count += 1
                if reasoning_eval.get('has_reasoning', False):
                    has_reasoning_count += 1

        avg_legal_score = avg_legal_score / total if total > 0 else 0
        avg_reasoning_score = avg_reasoning_score / total if total > 0 else 0

        metrics = {
            'total_cases': len(results),
            'success_cases': total,
            'failed_cases': len(results) - total,
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1_score, 4),
            'type_accuracy': round(type_correct_count / total, 4) if total > 0 else 0,
            'confusion_matrix': {
                'TP': tp,
                'FP': fp,
                'FN': fn,
                'TN': tn
            },
            'quality_metrics': {
                'avg_legal_basis_score': round(avg_legal_score, 4),
                'avg_reasoning_score': round(avg_reasoning_score, 4),
                'legal_basis_coverage': round(has_legal_count / total, 4) if total > 0 else 0,
                'reasoning_coverage': round(has_reasoning_count / total, 4) if total > 0 else 0
            },
            'performance': {
                'avg_response_time': round(total_time / total, 2) if total > 0 else 0,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_tokens': total_input_tokens + total_output_tokens
            }
        }

        return metrics

    def print_metrics(self, metrics: Dict[str, Any], model_name: str):
        """打印指标"""
        print(f"\n{'='*60}")
        print(f"模型: {model_name}")
        print(f"{'='*60}")
        print(f"总案例数: {metrics['total_cases']}")
        print(f"成功案例: {metrics['success_cases']}")
        print(f"失败案例: {metrics['failed_cases']}")
        print(f"\n准确率指标:")
        print(f"  Accuracy:        {metrics['accuracy']:.2%}")
        print(f"  Precision:       {metrics['precision']:.2%}")
        print(f"  Recall:          {metrics['recall']:.2%}")
        print(f"  F1-Score:        {metrics['f1_score']:.2%}")
        print(f"  Type Accuracy:   {metrics['type_accuracy']:.2%}")
        print(f"\n混淆矩阵:")
        cm = metrics['confusion_matrix']
        print(f"  TP: {cm['TP']}  FP: {cm['FP']}")
        print(f"  FN: {cm['FN']}  TN: {cm['TN']}")

        # 打印质量指标
        if 'quality_metrics' in metrics:
            print(f"\n质量指标:")
            qm = metrics['quality_metrics']
            print(f"  法律依据质量分:  {qm['avg_legal_basis_score']:.2%}")
            print(f"  推理质量分:      {qm['avg_reasoning_score']:.2%}")
            print(f"  法律依据覆盖率:  {qm['legal_basis_coverage']:.2%}")
            print(f"  推理覆盖率:      {qm['reasoning_coverage']:.2%}")

        print(f"\n性能指标:")
        perf = metrics['performance']
        print(f"  平均响应时间:    {perf['avg_response_time']}s")
        print(f"  总Token数:       {perf['total_tokens']}")
        print(f"    输入:          {perf['total_input_tokens']}")
        print(f"    输出:          {perf['total_output_tokens']}")
        print(f"{'='*60}\n")
