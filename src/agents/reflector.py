"""Reflector - 自我反思验证器

验证推理结果的准确性和逻辑一致性，必要时触发重新推理
"""
from src.baseline.maas_client import MaaSClient
import json
import re


class Reflector:
    """自我反思验证器 - 验证并纠错"""

    # 违规类型 → 预期法条关键词映射
    VIOLATION_LAW_MAP = {
        '不明码标价': ['价格法.*第十三条', '明码标价'],
        '政府定价违规': ['价格法.*第十二条', '价格法.*第十一条', '价格法.*第三十九条'],
        '误导性价格标示': ['禁止价格欺诈', '价格法.*第十四条'],
        '标价外加价': ['价格法.*第十三条', '明码标价'],
        '变相提高价格': ['价格法.*第十四条'],
        '哄抬价格': ['价格法.*第十四条'],
    }

    # 违规类型 → 推理链中应包含的事实要素关键词
    REQUIRED_FACT_KEYWORDS = {
        '不明码标价': ['未标', '缺失', '缺少', '未注明', '未标注', '未标明', '标价签', '品名', '计价单位', '规格', '价格'],
        '政府定价违规': ['政府指导价', '政府定价', '定价标准', '超出', '超标', '收费标准'],
        '标价外加价': ['标价', '额外', '加收', '多收', '另行收取'],
        '误导性价格标示': ['原价', '划线价', '折扣', '成交', '交易记录', '比较', '误导'],
        '变相提高价格': ['以次充好', '短斤少两', '等级', '掺杂'],
        '哄抬价格': ['哄抬', '囤积', '涨价', '推高'],
    }

    # 非价格领域关键词
    NON_PRICE_KEYWORDS = ['商标侵权', '商标专用权', '食品安全', '产品质量', '广告违法', '虚假广告',
                          '营业执照', '资质证照', '卫生许可', '食品经营许可']

    def __init__(self, config_path="configs/model_config.yaml", max_reflection=1):
        self.client = MaaSClient(config_path)
        self.max_reflection = max_reflection

    def reflect(self, reasoning_result, graded_docs, query, intent):
        """验证推理结果

        Args:
            reasoning_result: Reasoning Engine的输出
            graded_docs: Grader的输出
            query: 原始查询
            intent: Intent Analyzer的输出

        Returns:
            dict: 验证后的结果（可能已纠正）
        """
        # 初始化reflection_count
        if 'reflection_count' not in reasoning_result:
            reasoning_result['reflection_count'] = 0

        # 启发式验证（零成本）
        issues = self._heuristic_validation(reasoning_result, graded_docs, query)

        reasoning_result['issues_found'] = issues

        # 判断是否需要重新推理
        critical_issues = [i for i in issues if i.get('severity') == 'critical']

        if critical_issues and reasoning_result['reflection_count'] < self.max_reflection:
            print(f"[Reflection] Found {len(critical_issues)} critical issues, triggering re-reasoning...")

            # 触发重新推理
            from src.agents.reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()

            reasoning_result['reflection_count'] += 1

            # 构建反馈
            feedback = self._build_feedback(critical_issues)

            # 重新推理
            corrected = engine.reason(
                query=query,
                graded_docs=graded_docs,
                intent=intent,
                feedback=feedback
            )

            corrected['reflection_count'] = reasoning_result['reflection_count']
            return corrected

        # 没有严重问题或已达最大重试次数
        if issues:
            # 根据问题严重度调整置信度
            penalty = len(issues) * 0.1
            original_conf = reasoning_result.get('confidence', 0.5)
            reasoning_result['adjusted_confidence'] = max(0.3, original_conf - penalty)
        else:
            reasoning_result['adjusted_confidence'] = reasoning_result.get('confidence', 0.5)

        reasoning_result['validation_passed'] = len(critical_issues) == 0

        return reasoning_result

    def _heuristic_validation(self, reasoning_result, graded_docs, query):
        """启发式验证（零成本）"""
        issues = []

        # 验证1: 检查是否引用了法律依据
        legal_basis = reasoning_result.get('legal_basis', '')
        reasoning_chain = reasoning_result.get('reasoning_chain', [])

        if not legal_basis and reasoning_chain:
            chain_text = ' '.join(reasoning_chain)
            legal_basis = self._extract_law_title(chain_text)

        if not legal_basis:
            issues.append({
                "type": "missing_legal_basis",
                "severity": "warning",
                "description": "未找到法律依据引用",
                "suggestion": "建议引用相关法律条文"
            })

        # 验证2: 检查reasoning_chain是否为空
        if not reasoning_chain:
            issues.append({
                "type": "empty_reasoning",
                "severity": "warning",
                "description": "推理链为空",
                "suggestion": "请输出完整的推理链"
            })

        # 验证3: is_violation 和 violation_type 一致性（双向检查）
        is_violation = reasoning_result.get('is_violation')
        violation_type = reasoning_result.get('violation_type', '')

        if is_violation and violation_type in ['无违规', '合规', 'None', '']:
            issues.append({
                "type": "logic_inconsistency",
                "severity": "critical",
                "description": f"is_violation={is_violation}但violation_type='{violation_type}'",
                "suggestion": "请确保is_violation和violation_type一致"
            })

        if not is_violation and is_violation is not None and violation_type not in ['无违规', '合规', 'None', '', '未知']:
            issues.append({
                "type": "logic_inconsistency_reverse",
                "severity": "critical",
                "description": f"is_violation=false但violation_type='{violation_type}'",
                "suggestion": "合规判定时violation_type应为'无违规'"
            })

        # 验证4: 法条适用性检查
        issues.extend(self._validate_law_applicability(reasoning_result))

        # 验证5: 事实要素完备性检查
        issues.extend(self._validate_fact_completeness(reasoning_result))

        # 验证6: 非价格领域排除
        issues.extend(self._validate_price_domain(reasoning_result, query))

        return issues

    def _validate_law_applicability(self, reasoning_result):
        """校验引用法条是否与违规类型匹配"""
        issues = []
        is_violation = reasoning_result.get('is_violation')
        violation_type = reasoning_result.get('violation_type', '')

        if not is_violation or violation_type not in self.VIOLATION_LAW_MAP:
            return issues

        # 收集所有法律引用文本
        cited_articles = reasoning_result.get('cited_articles', [])
        legal_basis = reasoning_result.get('legal_basis', '')
        chain_text = ' '.join(reasoning_result.get('reasoning_chain', []))
        all_legal_text = legal_basis + ' ' + chain_text
        for article in cited_articles:
            all_legal_text += f" {article.get('law', '')} {article.get('article', '')}"

        # 检查是否命中预期法条
        expected_patterns = self.VIOLATION_LAW_MAP[violation_type]
        matched = any(re.search(pattern, all_legal_text) for pattern in expected_patterns)

        if not matched and all_legal_text.strip():
            issues.append({
                "type": "law_type_mismatch",
                "severity": "warning",
                "description": f"引用的法条与违规类型'{violation_type}'不匹配",
                "suggestion": f"'{violation_type}'通常应引用：{', '.join(expected_patterns)}"
            })

        return issues

    def _validate_fact_completeness(self, reasoning_result):
        """校验推理链中是否包含该违规类型所需的事实要素"""
        issues = []
        is_violation = reasoning_result.get('is_violation')
        violation_type = reasoning_result.get('violation_type', '')

        if not is_violation or violation_type not in self.REQUIRED_FACT_KEYWORDS:
            return issues

        chain_text = ' '.join(reasoning_result.get('reasoning_chain', []))
        required_keywords = self.REQUIRED_FACT_KEYWORDS[violation_type]

        matched_count = sum(1 for kw in required_keywords if kw in chain_text)

        if matched_count == 0:
            issues.append({
                "type": "missing_fact_elements",
                "severity": "critical",
                "description": f"推理链中未包含'{violation_type}'所需的事实要素",
                "suggestion": f"判定'{violation_type}'需包含以下要素之一：{', '.join(required_keywords[:5])}"
            })

        return issues

    def _validate_price_domain(self, reasoning_result, query):
        """校验案例是否属于价格合规领域"""
        issues = []
        is_violation = reasoning_result.get('is_violation')

        if not is_violation:
            return issues

        # 检查 query 是否涉及非价格领域
        non_price_matched = [kw for kw in self.NON_PRICE_KEYWORDS if kw in query]

        if non_price_matched:
            # 同时检查是否有价格相关要素
            price_keywords = ['价格', '标价', '收费', '定价', '原价', '折扣', '促销']
            has_price_element = any(kw in query for kw in price_keywords)

            if not has_price_element:
                issues.append({
                    "type": "non_price_domain",
                    "severity": "critical",
                    "description": f"案例涉及非价格领域（{', '.join(non_price_matched)}）且无价格要素，不应判为价格违规",
                    "suggestion": "请重新审视案例是否属于价格合规范畴，若不属于应判定为'无违规'"
                })

        return issues

    def _extract_law_title(self, content):
        """提取法律标题"""
        match = re.search(r'《([^》]+)》', content)
        return f"《{match.group(1)}》" if match else ""

    def _build_feedback(self, issues):
        """构建反馈信息"""
        lines = ["上一次推理存在以下问题，请修正：\n"]

        for issue in issues:
            lines.append(f"- {issue['description']}")
            lines.append(f"  建议：{issue['suggestion']}")

        return "\n".join(lines)
