"""Grader - 质量评分器

多维度评分检索文档并过滤低质量结果
"""


class Grader:
    """质量评分器 - 相关性+覆盖度+时效性"""

    def __init__(self,
                 relevance_weight=0.6,
                 coverage_weight=0.3,
                 freshness_weight=0.1,
                 min_score=0.5):
        self.relevance_weight = relevance_weight
        self.coverage_weight = coverage_weight
        self.freshness_weight = freshness_weight
        self.min_score = min_score

    def grade(self, query, retrieved_docs, intent):
        """为检索文档评分并过滤

        Args:
            query: 原始查询
            retrieved_docs: 检索结果（包含laws和cases）
            intent: 意图分析结果

        Returns:
            dict: 包含graded_laws和graded_cases
        """
        # 提取关键词
        keywords = self._extract_keywords(query, intent)

        # 评分
        laws = retrieved_docs.get('laws', [])
        cases = retrieved_docs.get('cases', [])

        graded_laws = [self._score_doc(doc, keywords) for doc in laws]
        graded_laws.sort(key=lambda x: x['final_score'], reverse=True)
        filtered_laws = self._filter_docs(graded_laws, min_keep=2)

        # cases 为空时直接短路，不走评分/排序/过滤
        if cases:
            graded_cases = [self._score_doc(doc, keywords) for doc in cases]
            graded_cases.sort(key=lambda x: x['final_score'], reverse=True)
            filtered_cases = self._filter_docs(graded_cases, min_keep=2)
            cases_stats = {
                "cases_before": len(cases),
                "cases_after": len(filtered_cases),
            }
        else:
            filtered_cases = []
            cases_stats = {"cases_disabled": True}

        return {
            "graded_laws": filtered_laws,
            "graded_cases": filtered_cases,
            "filtering_stats": {
                "laws_before": len(laws),
                "laws_after": len(filtered_laws),
                **cases_stats,
                "filtered_count": len(laws) - len(filtered_laws)
            }
        }

    def _extract_keywords(self, query, intent):
        """提取关键词用于覆盖度计算"""
        keywords = []

        # 从intent的key_entities提取
        entities = intent.get('key_entities', {})
        for value in entities.values():
            if isinstance(value, str):
                keywords.append(value)

        # 从违规类型提示提取
        keywords.extend(intent.get('violation_type_hints', []))

        # 常见价格关键词
        price_keywords = ['原价', '划线价', '折扣', '优惠', '促销', '成交', '交易', '记录', '历史']
        for kw in price_keywords:
            if kw in query:
                keywords.append(kw)

        return list(set(keywords))

    def _score_doc(self, doc, keywords):
        """计算单个文档的评分"""
        content = doc.get('content', '')
        metadata = doc.get('metadata', {})

        # 1. Relevance（相关性）
        relevance = doc.get('rerank_score', max(0, 1 - doc.get('distance', 0.5)))

        # 2. Coverage（覆盖度）
        if keywords:
            matched = sum(1 for kw in keywords if kw in content)
            coverage = matched / len(keywords)
        else:
            coverage = 0.5

        # 3. Freshness（时效性）
        year = metadata.get('year', 2020)
        freshness = 1.0 if year >= 2024 else (0.8 if year >= 2020 else 0.6)

        # 加权综合评分
        final_score = (
            self.relevance_weight * relevance +
            self.coverage_weight * coverage +
            self.freshness_weight * freshness
        )

        # 添加评分信息到文档
        doc['relevance_score'] = round(relevance, 3)
        doc['coverage_score'] = round(coverage, 3)
        doc['freshness_score'] = round(freshness, 3)
        doc['final_score'] = round(final_score, 3)
        doc['grade'] = 'high' if final_score >= 0.75 else ('medium' if final_score >= 0.5 else 'low')

        return doc

    def _filter_docs(self, docs, min_keep=2):
        """过滤低分文档"""
        # 保留final_score >= min_score的文档
        filtered = [d for d in docs if d['final_score'] >= self.min_score]

        # 确保至少保留min_keep个
        if len(filtered) < min_keep and len(docs) >= min_keep:
            filtered = docs[:min_keep]

        return filtered
