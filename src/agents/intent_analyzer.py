"""Intent Analyzer - 意图分析器

分析查询意图，提取关键实体，动态决定检索TopK
优化版：使用规则based方法，避免LLM调用
"""
import re


class IntentAnalyzer:
    """意图分析器 - 规则based快速分析（不调用LLM）"""

    def __init__(self, config_path="configs/model_config.yaml"):
        # 保留参数兼容性，但不再使用
        pass

    def analyze(self, query):
        """分析查询意图（规则based，无LLM调用）

        Args:
            query: 用户查询字符串

        Returns:
            dict: 包含violation_type_hints, key_entities, complexity等字段
        """
        # 1. 检测可能的违规类型
        violation_hints = self._detect_violation_types(query)

        # 2. 提取关键实体
        key_entities = self._extract_entities(query)

        # 3. 判断复杂度
        complexity = self._assess_complexity(query, violation_hints)

        # 4. 动态决定TopK
        laws_k, cases_k = self._decide_topk(complexity)

        # 5. 生成推理提示
        reasoning_hints = self._generate_hints(violation_hints, key_entities)

        return {
            "violation_type_hints": violation_hints,
            "key_entities": key_entities,
            "complexity": complexity,
            "retrieval_strategy": "keyword+semantic",
            "suggested_laws_k": laws_k,
            "suggested_cases_k": cases_k,
            "reasoning_hints": reasoning_hints
        }

    def _detect_violation_types(self, query):
        """规则based检测违规类型（覆盖v4数据集类型分布）"""
        hints = []

        # 不明码标价 (v4中占45.6%)
        if any(kw in query for kw in [
            '未标明价格', '未明码标价', '标价签', '未标注', '未标示',
            '未按规定', '计价单位', '不标明', '没有标价', '未张贴',
            '价格标示', '价格公示', '明码标价', '未说明', '缺失', '未明示'
        ]):
            hints.append('不明码标价')

        # 政府定价违规 (v4中占24.0%)
        if any(kw in query for kw in [
            '政府指导价', '政府定价', '浮动幅度', '发改委', '物价局',
            '核定价格', '限价', '最高限价', '政府.*?价格', '超标准收费'
        ]):
            hints.append('政府定价违规')

        # 标价外加价 (v4中占14.6%)
        if any(kw in query for kw in [
            '额外收取', '加收', '另行收取', '标价之外', '多收',
            '反向抹零', '包装费', '服务费', '手续费', '工本费', '运费', '税费', '附加费'
        ]):
            hints.append('标价外加价')

        # 误导性价格标示（收紧规则：需同时有价格比较 + 反面证据）
        misleading_strong = ['从未成交', '无交易记录', '无销售记录', '虚构', '虚标']
        if any(kw in query for kw in misleading_strong):
            hints.append('误导性价格标示')

        misleading_weak = ['原价', '划线价']
        misleading_evidence = ['未实际成交', '无成交', '虚假', '不实', '虚标', '不符', '无依据']
        if any(kw in query for kw in misleading_weak) and any(kw in query for kw in misleading_evidence):
            if '误导性价格标示' not in hints:
                hints.append('误导性价格标示')

        if any(kw in query for kw in ['折扣', '打折', '优惠', '促销', '活动价', '限时', '特价']):
            if any(kw in query for kw in ['虚假', '误导', '不实', '欺骗']):
                if '误导性价格标示' not in hints:
                    hints.append('误导性价格标示')

        # 变相提高价格
        if any(kw in query for kw in [
            '以次充好', '短斤少两', '缺斤少两', '抬高等级', '掺杂掺假', '注水', '变相提价'
        ]):
            hints.append('变相提高价格')

        # 哄抬价格
        if any(kw in query for kw in ['哄抬', '囤积', '涨价信息', '大幅提价', '推高价格']):
            hints.append('哄抬价格')

        # 去重并保留顺序
        seen = set()
        deduped = []
        for h in hints:
            if h not in seen:
                seen.add(h)
                deduped.append(h)

        if not deduped:
            deduped.append('需进一步分析')

        return deduped[:3]  # 最多3个

    def _extract_entities(self, query):
        """提取关键实体"""
        entities = {}

        # 提取平台
        platforms = ['淘宝', '天猫', '京东', '拼多多', '美团', '抖音', '小红书', '携程', '微信']
        for platform in platforms:
            if platform in query:
                entities['platform'] = platform
                break

        # 提取金额（简单正则）
        amounts = re.findall(r'(\d+\.?\d*)元', query)
        if amounts:
            entities['amounts'] = amounts[:3]  # 最多3个

        # 提取价格类型关键词
        price_types = ['原价', '活动价', '促销价', '日常价', '划线价', '到手价']
        for ptype in price_types:
            if ptype in query:
                if 'price_types' not in entities:
                    entities['price_types'] = []
                entities['price_types'].append(ptype)

        return entities

    def _assess_complexity(self, query, violation_hints):
        """评估案例复杂度"""
        # 复杂度指标
        complexity_score = 0

        # 长度因素
        if len(query) > 300:
            complexity_score += 1
        elif len(query) > 150:
            complexity_score += 0.5

        # 多个违规类型
        if len(violation_hints) >= 2:
            complexity_score += 1

        # 涉及历史数据对比
        if any(kw in query for kw in ['历史', '过去', '此前', '以往', '对比', '实际', '经查']):
            complexity_score += 0.5

        # 涉及多个价格
        price_count = len(re.findall(r'\d+\.?\d*元', query))
        if price_count >= 4:
            complexity_score += 1
        elif price_count >= 2:
            complexity_score += 0.5

        # 决定复杂度等级
        if complexity_score >= 2:
            return 'complex'
        elif complexity_score >= 1:
            return 'medium'
        else:
            return 'simple'

    def _decide_topk(self, complexity):
        """根据复杂度决定TopK，cases_k固定为0避免案例同源污染"""
        if complexity == 'complex':
            return 5, 0  # laws_k, cases_k
        elif complexity == 'medium':
            return 4, 0
        else:  # simple
            return 3, 0

    def _generate_hints(self, violation_hints, entities):
        """生成推理提示"""
        hints = []

        hint_map = {
            '不明码标价': '检查是否按规定明码标价，标价签是否包含品名、计价单位、价格等要素',
            '政府定价违规': '核查收费标准是否在政府指导价/定价范围内',
            '标价外加价': '检查是否存在在标价之外额外收取未标明费用的情况',
            '误导性价格标示': '若涉及价格比较，请依次核查四要件：(1)是否存在明示的比较价格标注；(2)该标注价格是否缺乏真实依据或客观基准；(3)是否足以使消费者产生错误价格认知；(4)是否与其他违规类型重叠。四要件缺一不可方可认定',
            '变相提高价格': '检查是否存在抬高等级、以次充好等变相提价行为',
            '哄抬价格': '核查是否存在捏造散布涨价信息、囤积居奇等行为',
        }

        for vtype in violation_hints:
            if vtype in hint_map:
                hints.append(hint_map[vtype])

        return hints
