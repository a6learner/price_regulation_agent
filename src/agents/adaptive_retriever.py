"""Adaptive Retriever - 自适应检索器

基于意图分析结果动态调整检索策略和TopK
"""
from src.rag.retriever import HybridRetriever


class AdaptiveRetriever:
    """自适应检索器 - 动态TopK检索"""

    def __init__(self, db_path="data/rag/chroma_db"):
        self.retriever = HybridRetriever(db_path)

    def retrieve(self, query, intent):
        """自适应检索

        Args:
            query: 原始查询
            intent: Intent Analyzer的输出

        Returns:
            dict: 包含laws和cases的检索结果
        """
        # 从intent获取动态TopK
        laws_k = intent.get('suggested_laws_k', 3)
        cases_k = intent.get('suggested_cases_k', 5)

        # 调用Phase 3的HybridRetriever
        result = self.retriever.retrieve(
            query=query,
            laws_k=laws_k,
            cases_k=cases_k,
            distance_threshold=0.15,  # Phase 3最优值
            min_k=2
        )

        # 记录检索元数据
        if 'metadata' not in result:
            result['metadata'] = {}

        result['metadata']['laws_requested'] = laws_k
        result['metadata']['cases_requested'] = cases_k

        return result
