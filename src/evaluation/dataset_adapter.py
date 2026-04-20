"""
数据集适配器 — 将 eval_dataset_v4 格式转换为各评测脚本期望的格式
同时提供直接读取v4字段的工具函数
"""
import json
from typing import List, Dict, Any, Optional
from collections import Counter


class DatasetAdapter:
    """v4数据集适配器"""

    def __init__(self, eval_path: str):
        self.eval_path = eval_path
        self.cases = self._load_v4(eval_path)

    def _load_v4(self, path: str) -> List[Dict]:
        cases = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
        return cases

    def to_legacy_format(self, limit: Optional[int] = None) -> List[Dict]:
        """转换为旧格式，兼容现有 BaselineEvaluator / RAGEvaluator / AgentCoordinator

        旧格式:
        {
          "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "案例描述"}
          ],
          "meta": {
            "case_id": "CASE_0001",
            "is_violation": true,
            "violation_type": "不明码标价",
            "qualifying_articles": [...],
            "penalty_articles": [...],
            "platform": "..."
          }
        }
        """
        cases = self.cases[:limit] if limit else self.cases
        legacy = []
        for case in cases:
            gt = case['ground_truth']
            legacy.append({
                "messages": [
                    {"role": "system", "content": "你是一名价格合规分析专家。"},
                    {"role": "user", "content": case['input']['case_description']}
                ],
                "meta": {
                    "case_id": case['id'],
                    "is_violation": gt['is_violation'],
                    "violation_type": gt.get('violation_type') or '无违规',
                    "qualifying_articles": gt.get('qualifying_articles', []),
                    "penalty_articles": gt.get('penalty_articles', []),
                    "platform": case['input'].get('platform'),
                    "source_type": case.get('source_type'),
                }
            })
        return legacy

    def get_ground_truth_map(self) -> Dict[str, Dict]:
        """构建 case_id → ground_truth 的映射，供 GroundTruthExtractor 和 LegalRetrievalEvaluator 使用"""
        gt_map = {}
        for case in self.cases:
            case_id = case['id']
            gt = case['ground_truth']
            gt_map[case_id] = {
                'is_violation': gt['is_violation'],
                'violation_type': gt.get('violation_type'),
                'qualifying_article_keys': [
                    a['article_key'] for a in gt.get('qualifying_articles', [])
                ],
                'qualifying_articles_full': gt.get('qualifying_articles', []),
                'penalty_article_keys': [
                    a['article_key'] for a in gt.get('penalty_articles', [])
                ],
            }
        return gt_map

    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        for case in self.cases:
            if case['id'] == case_id:
                return case
        return None

    def get_statistics(self) -> Dict:
        violations = [c for c in self.cases if c['ground_truth']['is_violation']]
        compliants = [c for c in self.cases if not c['ground_truth']['is_violation']]

        vtype_dist = Counter(
            c['ground_truth'].get('violation_type', '?') for c in violations
        )
        qual_counts = [
            len(c['ground_truth'].get('qualifying_articles', []))
            for c in violations
        ]

        return {
            'total': len(self.cases),
            'violations': len(violations),
            'compliants': len(compliants),
            'violation_type_distribution': dict(vtype_dist.most_common()),
            'avg_qualifying_articles': sum(qual_counts) / len(qual_counts) if qual_counts else 0,
            'violations_with_qualifying_articles': sum(1 for q in qual_counts if q > 0),
        }
