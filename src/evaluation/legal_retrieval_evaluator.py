"""
法条检索评测器
基于 eval_dataset_v4 的 qualifying_articles.article_key 计算 Precision / Recall / F1

用法:
    evaluator = LegalRetrievalEvaluator(gt_map)
    predicted_keys = evaluator.extract_article_keys_from_output(llm_output_text)
    score = evaluator.evaluate_single(case_id, predicted_keys)
    batch_scores = evaluator.evaluate_batch(results_list)
"""
import re
import json
from typing import List, Dict, Set, Optional


class LegalRetrievalEvaluator:
    """法条检索评测器"""

    def __init__(self, gt_map: Dict[str, Dict]):
        """
        Args:
            gt_map: DatasetAdapter.get_ground_truth_map() 的输出
                    {case_id: {"qualifying_article_keys": [...], ...}}
        """
        self.gt_map = gt_map
        self.gt_keys_map = {}
        for case_id, gt in gt_map.items():
            raw_keys = gt.get('qualifying_article_keys', [])
            self.gt_keys_map[case_id] = self._normalize_keys(raw_keys)

    # ========================================================
    # 1. 从LLM输出中提取法条引用
    # ========================================================

    def extract_article_keys_from_output(self, output_text: str) -> List[str]:
        """从LLM的自然语言输出中提取法条引用，转换为标准化article_key

        支持两种输入:
        1. 结构化JSON中的 cited_articles 字段
        2. 自然语言中的 《法律名》第X条 模式
        """
        keys = set()

        # 方式1: 尝试从JSON中提取 cited_articles
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', output_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{[^{}]*"cited_articles"[^{}]*\}', output_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if '```' in json_match.group(0) else json_match.group(0)
                parsed = json.loads(json_str)
                for article in parsed.get('cited_articles', []):
                    law = article.get('law', '')
                    art = article.get('article', '')
                    key = self._law_article_to_key(law, art)
                    if key:
                        keys.add(key)
        except (json.JSONDecodeError, AttributeError):
            pass

        # 方式2: 正则提取 《法律名》第X条
        pattern = r'《([^》]+)》\s*第([一二三四五六七八九十百零\d]+)条(?:\s*第([一二三四五六七八九十百零\d]+)(?:款|项))?'
        for match in re.finditer(pattern, output_text):
            law_name = self._normalize_law_name(match.group(1))
            article = match.group(2)
            sub = match.group(3) if match.lastindex >= 3 and match.group(3) else None
            key = f"{law_name}_{article}"
            if sub:
                key += f"_{sub}"
            keys.add(key)

        # 方式3: 尝试从顶层JSON的 legal_basis 字段提取
        try:
            if output_text.strip().startswith('{'):
                parsed = json.loads(output_text)
                lb = parsed.get('legal_basis', '')
                for match in re.finditer(pattern, lb):
                    law_name = self._normalize_law_name(match.group(1))
                    article = match.group(2)
                    sub = match.group(3) if match.lastindex >= 3 and match.group(3) else None
                    key = f"{law_name}_{article}"
                    if sub:
                        key += f"_{sub}"
                    keys.add(key)
        except (json.JSONDecodeError, AttributeError):
            pass

        return self._normalize_keys(list(keys))

    def _law_article_to_key(self, law: str, article: str) -> Optional[str]:
        """将 law + article 转换为 article_key 格式"""
        law_name = self._normalize_law_name(law)
        if not law_name:
            return None
        # 从 "第十三条" 提取 "十三"
        art_match = re.search(r'第([一二三四五六七八九十百零\d]+)条', article)
        if art_match:
            return f"{law_name}_{art_match.group(1)}"
        # 如果 article 本身就是条号（不含"第"和"条"）
        if article and not article.startswith('第'):
            return f"{law_name}_{article}"
        return None

    # ========================================================
    # 2. 单条评分
    # ========================================================

    def evaluate_single(self, case_id: str, predicted_keys: List[str], mode: str = 'both') -> Dict:
        """评估单条case的法条检索质量

        Args:
            case_id: 案例ID
            predicted_keys: 模型预测的法条key列表
            mode: 'strict' | 'relaxed' | 'both'
        """
        gt_keys = self.gt_keys_map.get(case_id, [])

        if not gt_keys:
            return {
                'case_id': case_id,
                'skipped': True,
                'reason': 'no_qualifying_articles_in_ground_truth'
            }

        pred_normalized = self._normalize_keys(predicted_keys)
        gt_normalized = gt_keys

        result = {'case_id': case_id, 'skipped': False}

        if mode in ('strict', 'both'):
            result['strict'] = self._compute_prf(set(pred_normalized), set(gt_normalized))

        if mode in ('relaxed', 'both'):
            pred_relaxed = set(self._to_article_level(k) for k in pred_normalized)
            gt_relaxed = set(self._to_article_level(k) for k in gt_normalized)
            result['relaxed'] = self._compute_prf(pred_relaxed, gt_relaxed)

        result['predicted_keys'] = pred_normalized
        result['ground_truth_keys'] = gt_normalized

        return result

    # ========================================================
    # 3. 批量评分
    # ========================================================

    def evaluate_batch(self, results: List[Dict]) -> Dict:
        """批量评估所有case

        Args:
            results: 评测结果列表，每条需包含:
                     - 'case_id': str
                     - 'llm_response' 或 'raw_response' 或 'output': str (LLM原始输出)
                     或
                     - 'predicted_keys': List[str] (已提取的法条keys)
        """
        case_scores = []

        for result in results:
            case_id = result.get('case_id', '')

            if 'predicted_keys' in result:
                pred_keys = result['predicted_keys']
            else:
                output_text = (
                    result.get('llm_response', '') or
                    result.get('raw_response', '') or
                    json.dumps(result.get('output', {}), ensure_ascii=False)
                )
                pred_keys = self.extract_article_keys_from_output(output_text)

            score = self.evaluate_single(case_id, pred_keys)
            case_scores.append(score)

        evaluated = [s for s in case_scores if not s.get('skipped')]
        skipped = [s for s in case_scores if s.get('skipped')]

        summary = {
            'total_cases': len(results),
            'evaluated_cases': len(evaluated),
            'skipped_cases': len(skipped),
        }

        for mode in ('strict', 'relaxed'):
            scores = [s[mode] for s in evaluated if mode in s]
            if scores:
                summary[f'{mode}_macro_precision'] = round(
                    sum(s['precision'] for s in scores) / len(scores), 4
                )
                summary[f'{mode}_macro_recall'] = round(
                    sum(s['recall'] for s in scores) / len(scores), 4
                )
                summary[f'{mode}_macro_f1'] = round(
                    sum(s['f1'] for s in scores) / len(scores), 4
                )
                total_tp = sum(s['tp'] for s in scores)
                total_fp = sum(s['fp'] for s in scores)
                total_fn = sum(s['fn'] for s in scores)
                micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
                micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
                micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0
                summary[f'{mode}_micro_precision'] = round(micro_p, 4)
                summary[f'{mode}_micro_recall'] = round(micro_r, 4)
                summary[f'{mode}_micro_f1'] = round(micro_f1, 4)

        summary['case_scores'] = case_scores
        return summary

    # ========================================================
    # 4. 内部辅助方法
    # ========================================================

    def _compute_prf(self, pred_set: Set[str], gt_set: Set[str]) -> Dict:
        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'tp': tp, 'fp': fp, 'fn': fn,
        }

    def _normalize_law_name(self, name: str) -> str:
        name = name.replace('中华人民共和国', '')
        aliases = {
            '价格法': '价格法',
            '禁止价格欺诈行为规定': '禁止价格欺诈行为的规定',
            '禁止价格欺诈行为的规定': '禁止价格欺诈行为的规定',
            '明码标价和禁止价格欺诈规定': '明码标价和禁止价格欺诈规定',
            '价格违法行为行政处罚规定': '价格违法行为行政处罚规定',
            '电子商务法': '电子商务法',
            '消费者权益保护法': '消费者权益保护法',
        }
        return aliases.get(name, name)

    def _normalize_keys(self, keys: List[str]) -> List[str]:
        normalized = []
        for key in keys:
            key = key.replace('、', '_')
            key = key.rstrip('_').rstrip('、')
            if key:
                normalized.append(key)
        return list(set(normalized))

    def _to_article_level(self, key: str) -> str:
        """转换到条级别（忽略款/项）: "价格法_十四_四" → "价格法_十四" """
        parts = key.split('_')
        if len(parts) >= 3:
            return '_'.join(parts[:2])
        return key


def print_evaluation_summary(summary: Dict, method_name: str = ""):
    print(f"\n{'='*60}")
    print(f"法条检索评测结果 {f'({method_name})' if method_name else ''}")
    print(f"{'='*60}")
    print(f"总案例: {summary['total_cases']}")
    print(f"评测案例(有ground truth法条): {summary['evaluated_cases']}")
    print(f"跳过(合规/无法条): {summary['skipped_cases']}")

    for mode in ('strict', 'relaxed'):
        macro_f1 = summary.get(f'{mode}_macro_f1', 0)
        micro_f1 = summary.get(f'{mode}_micro_f1', 0)
        if macro_f1 or micro_f1:
            print(f"\n  [{mode.upper()}]")
            print(f"    Macro  P={summary.get(f'{mode}_macro_precision',0):.2%}  "
                  f"R={summary.get(f'{mode}_macro_recall',0):.2%}  "
                  f"F1={macro_f1:.2%}")
            print(f"    Micro  P={summary.get(f'{mode}_micro_precision',0):.2%}  "
                  f"R={summary.get(f'{mode}_micro_recall',0):.2%}  "
                  f"F1={micro_f1:.2%}")
    print(f"{'='*60}")
