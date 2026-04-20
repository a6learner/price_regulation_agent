"""
高级评估指标实现

实现5个新的评估指标:
1. EvidenceChainMetric - 证据链完整性
2. LegalCitationMetric - 法律引用准确性
3. RemediationMetric - 整改建议可操作性
4. ExplainabilityMetric - 可解释性评分
5. StructuredOutputMetric - 结构化输出质量

所有指标使用启发式方法（规则+关键词匹配），零成本计算。
"""

import re
from typing import Dict, Any, List


class EvidenceChainMetric:
    """证据链完整性指标"""

    def __init__(self):
        # 关键词字典
        self.fact_keywords = ["提取", "事实", "关键", "信息", "案例描述"]
        self.check_keywords = ["检查", "历史", "记录", "数据", "成交", "价格"]
        self.legal_keywords = ["法律", "条款", "规定", "法规", "禁止", "价格法"]
        self.case_keywords = ["案例", "相似", "参考", "处罚", "判例"]
        self.conclusion_keywords = ["结论", "判断", "构成", "认定", "违规", "合规"]

    def calculate(self, reasoning_chain: List[str], output: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算证据链完整性评分

        评分维度:
        1. 步骤数量 (0.3分):
           - 5步完整: 1.0
           - 3-4步: 0.7
           - 1-2步: 0.3
           - 0步: 0.0

        2. 逻辑连贯性 (0.4分):
           - 包含事实提取: +0.1
           - 包含数据检查: +0.1
           - 包含法律匹配: +0.15
           - 包含案例参考: +0.05
           - 包含结论: +0.1

        3. 引用质量 (0.3分):
           - 引用了法律条款: +0.2 (检测《xxx》格式)
           - 引用了案例: +0.1
        """
        # 1. 步骤数量评分
        step_count = len(reasoning_chain)
        if step_count >= 5:
            step_score = 1.0
        elif step_count >= 3:
            step_score = 0.7
        elif step_count >= 1:
            step_score = 0.3
        else:
            step_score = 0.0

        step_score_weighted = step_score * 0.3

        # 2. 逻辑连贯性评分
        reasoning_text = " ".join(reasoning_chain)

        has_fact_extraction = any(kw in reasoning_text for kw in self.fact_keywords)
        has_data_check = any(kw in reasoning_text for kw in self.check_keywords)
        has_legal_match = any(kw in reasoning_text for kw in self.legal_keywords)
        has_case_reference = any(kw in reasoning_text for kw in self.case_keywords)
        has_conclusion = any(kw in reasoning_text for kw in self.conclusion_keywords)

        coherence_score = (
            (0.1 if has_fact_extraction else 0) +
            (0.1 if has_data_check else 0) +
            (0.15 if has_legal_match else 0) +
            (0.05 if has_case_reference else 0) +
            (0.1 if has_conclusion else 0)
        )

        coherence_score_weighted = coherence_score * 0.4

        # 3. 引用质量评分
        # 检测《xxx》格式的法律引用
        law_citations = re.findall(r'《([^》]+)》', reasoning_text)
        has_law_citation = len(law_citations) > 0

        # 检测案例引用
        has_case_citation = "案例" in reasoning_text and ("相似" in reasoning_text or "参考" in reasoning_text)

        citation_score = (
            (0.2 if has_law_citation else 0) +
            (0.1 if has_case_citation else 0)
        )

        citation_score_weighted = citation_score * 0.3

        # 总分
        final_score = step_score_weighted + coherence_score_weighted + citation_score_weighted

        return {
            "score": round(final_score, 3),
            "details": {
                "step_count": step_count,
                "step_score": round(step_score_weighted, 3),
                "coherence_score": round(coherence_score_weighted, 3),
                "citation_score": round(citation_score_weighted, 3),
                "has_fact_extraction": has_fact_extraction,
                "has_data_check": has_data_check,
                "has_legal_match": has_legal_match,
                "has_case_reference": has_case_reference,
                "has_conclusion": has_conclusion,
                "law_citations_count": len(law_citations),
                "has_case_citation": has_case_citation
            }
        }


class LegalCitationMetric:
    """法律引用准确性指标"""

    def __init__(self):
        pass

    def calculate(self, legal_basis: str,
                 reasoning_chain: List[str],
                 ground_truth_laws: List[str],
                 retrieved_laws: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        计算法律引用准确性评分

        评分维度:
        1. 引用完整性 (0.4分):
           - 有《法律名》: +0.2
           - 有条款号: +0.2 (如"第14条")

        2. 引用正确性 (0.4分):
           - 与ground truth完全匹配: 1.0
           - 部分匹配: 0.5 (引用了相关法律但条款不同)
           - 完全不匹配: 0.0

        3. 来源可追溯 (0.2分):
           - 法律在检索结果中: 1.0 (Agent特有优势)
           - 法律不在检索结果中: 0.0 (可能是幻觉)
        """
        # 1. 引用完整性评分
        # 从legal_basis和reasoning_chain中提取法律引用
        all_text = legal_basis + " " + " ".join(reasoning_chain)

        # 检测《法律名》
        law_names = re.findall(r'《([^》]+)》', all_text)
        has_law_name = len(law_names) > 0

        # 检测条款号
        article_numbers = re.findall(r'第[一二三四五六七八九十\d]+条', all_text)
        has_article = len(article_numbers) > 0

        completeness_score = (
            (0.2 if has_law_name else 0) +
            (0.2 if has_article else 0)
        )

        completeness_score_weighted = completeness_score * 0.4

        # 2. 引用正确性评分
        correctness_score = 0.0
        matched = False
        partially_matched = False

        if ground_truth_laws:
            # 检查是否与ground truth匹配
            for gt_law in ground_truth_laws:
                # 完全匹配
                if gt_law in all_text:
                    correctness_score = 1.0
                    matched = True
                    break

                # 部分匹配（法律名称匹配但条款不同）
                gt_law_name_match = re.search(r'《([^》]+)》', gt_law)
                if gt_law_name_match:
                    gt_law_name = gt_law_name_match.group(1)
                    if gt_law_name in all_text:
                        correctness_score = max(correctness_score, 0.5)
                        partially_matched = True

        correctness_score_weighted = correctness_score * 0.4

        # 3. 来源可追溯性评分
        traceable_score = 0.0
        is_traceable = False

        if retrieved_laws is not None:
            # 检查引用的法律是否在检索结果中
            retrieved_texts = [law.get('content', '') for law in retrieved_laws]
            retrieved_combined = " ".join(retrieved_texts)

            for law_name in law_names:
                if law_name in retrieved_combined:
                    traceable_score = 1.0
                    is_traceable = True
                    break

        traceable_score_weighted = traceable_score * 0.2

        # 总分
        final_score = completeness_score_weighted + correctness_score_weighted + traceable_score_weighted

        return {
            "score": round(final_score, 3),
            "matched": matched,
            "partially_matched": partially_matched,
            "details": {
                "completeness_score": round(completeness_score_weighted, 3),
                "correctness_score": round(correctness_score_weighted, 3),
                "traceable_score": round(traceable_score_weighted, 3),
                "law_names_found": law_names,
                "article_numbers_found": article_numbers,
                "is_traceable": is_traceable,
                "ground_truth_laws": ground_truth_laws if ground_truth_laws else []
            }
        }


class RemediationMetric:
    """整改建议可操作性指标"""

    def __init__(self):
        self.action_keywords = ["修改", "调整", "删除", "补充", "下架", "更新", "提供", "培训"]
        self.time_keywords = ["立即", "3日内", "尽快", "及时", "马上", "当日", "本周"]
        self.responsible_keywords = ["商家", "平台", "运营", "团队", "负责人", "管理员"]
        self.example_keywords = ["应改为", "正确做法", "示例", "参考", "改成"]

    def calculate(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算整改建议可操作性评分

        评分维度:
        1. 是否有remediation字段 (0.3分):
           - 有: 1.0
           - 无: 0.0

        2. 建议具体性 (0.4分):
           - 包含具体操作: +0.15
           - 包含时间要求: +0.1
           - 包含责任主体: +0.15

        3. 参考信息 (0.3分):
           - 引用法律依据: +0.15
           - 提供正确示例: +0.15
        """
        # 1. 检查是否有remediation字段
        has_remediation = "remediation" in output or "remediation_steps" in output
        existence_score = 1.0 if has_remediation else 0.0
        existence_score_weighted = existence_score * 0.3

        # 2. 建议具体性评分
        specificity_score = 0.0
        has_action = False
        has_time = False
        has_responsible = False

        if has_remediation:
            # 提取remediation内容
            remediation_data = output.get('remediation', output.get('remediation_steps', {}))

            if isinstance(remediation_data, dict):
                remediation_text = str(remediation_data)
            elif isinstance(remediation_data, list):
                remediation_text = " ".join([str(item) for item in remediation_data])
            else:
                remediation_text = str(remediation_data)

            # 检查关键词
            has_action = any(kw in remediation_text for kw in self.action_keywords)
            has_time = any(kw in remediation_text for kw in self.time_keywords)
            has_responsible = any(kw in remediation_text for kw in self.responsible_keywords)

            specificity_score = (
                (0.15 if has_action else 0) +
                (0.1 if has_time else 0) +
                (0.15 if has_responsible else 0)
            )

        specificity_score_weighted = specificity_score * 0.4

        # 3. 参考信息评分
        reference_score = 0.0
        has_legal_basis = False
        has_example = False

        if has_remediation:
            remediation_data = output.get('remediation', output.get('remediation_steps', {}))
            remediation_text = str(remediation_data)

            # 检查法律依据
            has_legal_basis = bool(re.search(r'《([^》]+)》', remediation_text))

            # 检查正确示例
            has_example = any(kw in remediation_text for kw in self.example_keywords)

            reference_score = (
                (0.15 if has_legal_basis else 0) +
                (0.15 if has_example else 0)
            )

        reference_score_weighted = reference_score * 0.3

        # 总分
        final_score = existence_score_weighted + specificity_score_weighted + reference_score_weighted

        return {
            "score": round(final_score, 3),
            "has_remediation": has_remediation,
            "details": {
                "existence_score": round(existence_score_weighted, 3),
                "specificity_score": round(specificity_score_weighted, 3),
                "reference_score": round(reference_score_weighted, 3),
                "has_action": has_action,
                "has_time": has_time,
                "has_responsible": has_responsible,
                "has_legal_basis": has_legal_basis,
                "has_example": has_example
            }
        }


class ExplainabilityMetric:
    """可解释性评分指标"""

    def __init__(self):
        pass

    def calculate(self, reasoning_chain: List[str],
                 legal_basis: str,
                 output: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算可解释性评分

        评分维度:
        1. 推理步骤清晰度 (0.3分):
           - 每步有明确主题: +0.1 (如"步骤1: xxx")
           - 每步长度适中: +0.1 (50-200字)
           - 避免专业术语堆砌: +0.1 (法律术语密度<30%)

        2. 证据可追溯性 (0.4分):
           - 引用具体法律条文: +0.2
           - 引用具体案例: +0.1
           - 标注证据来源: +0.1 (如"根据《xxx》第x条")

        3. 结论明确性 (0.3分):
           - 有明确结论: +0.15 (is_violation=True/False)
           - 有置信度: +0.05 (confidence字段存在)
           - 有违规类型: +0.1 (violation_type明确)
        """
        # 1. 推理步骤清晰度评分
        clarity_score = 0.0

        # 检查是否有明确步骤标题
        has_step_titles = any(
            re.search(r'步骤\d+[:：]', step) or re.search(r'\d+[\.、]', step[:5])
            for step in reasoning_chain
        )
        clarity_score += 0.1 if has_step_titles else 0

        # 检查步骤长度是否适中
        if reasoning_chain:
            avg_length = sum(len(step) for step in reasoning_chain) / len(reasoning_chain)
            length_appropriate = 50 <= avg_length <= 200
            clarity_score += 0.1 if length_appropriate else 0

        # 检查法律术语密度
        all_text = " ".join(reasoning_chain)
        legal_terms = ["法律", "条款", "规定", "违反", "禁止", "法规", "处罚", "罚款"]
        term_count = sum(all_text.count(term) for term in legal_terms)
        term_density = term_count / len(all_text) if len(all_text) > 0 else 0
        low_term_density = term_density < 0.3
        clarity_score += 0.1 if low_term_density else 0

        clarity_score_weighted = clarity_score * 0.3

        # 2. 证据可追溯性评分
        traceability_score = 0.0

        # 引用具体法律条文
        has_law_citation = bool(re.search(r'《([^》]+)》', all_text + " " + legal_basis))
        traceability_score += 0.2 if has_law_citation else 0

        # 引用具体案例
        has_case_citation = "案例" in all_text or "相似" in all_text
        traceability_score += 0.1 if has_case_citation else 0

        # 标注证据来源
        has_source_label = bool(re.search(r'根据《.*?》', all_text)) or bool(re.search(r'依据《.*?》', all_text))
        traceability_score += 0.1 if has_source_label else 0

        traceability_score_weighted = traceability_score * 0.4

        # 3. 结论明确性评分
        conclusion_score = 0.0

        # 有明确结论
        has_violation = "is_violation" in output and output["is_violation"] is not None
        conclusion_score += 0.15 if has_violation else 0

        # 有置信度
        has_confidence = "confidence" in output and output["confidence"] is not None
        conclusion_score += 0.05 if has_confidence else 0

        # 有违规类型
        has_violation_type = "violation_type" in output and output["violation_type"] not in [None, "", "unknown"]
        conclusion_score += 0.1 if has_violation_type else 0

        conclusion_score_weighted = conclusion_score * 0.3

        # 总分
        final_score = clarity_score_weighted + traceability_score_weighted + conclusion_score_weighted

        return {
            "score": round(final_score, 3),
            "details": {
                "clarity_score": round(clarity_score_weighted, 3),
                "traceability_score": round(traceability_score_weighted, 3),
                "conclusion_score": round(conclusion_score_weighted, 3),
                "has_step_titles": has_step_titles,
                "avg_step_length": round(sum(len(s) for s in reasoning_chain) / len(reasoning_chain), 1) if reasoning_chain else 0,
                "term_density": round(term_density, 3),
                "has_law_citation": has_law_citation,
                "has_case_citation": has_case_citation,
                "has_source_label": has_source_label,
                "has_violation": has_violation,
                "has_confidence": has_confidence,
                "has_violation_type": has_violation_type
            }
        }


class StructuredOutputMetric:
    """结构化输出质量指标"""

    def __init__(self):
        # 核心字段
        self.core_fields = ["is_violation", "violation_type", "legal_basis", "confidence"]

        # 扩展字段（Agent特有）
        self.extended_fields = [
            "cited_laws", "cited_cases", "validation_passed",
            "reflection_count", "remediation", "reasoning_chain"
        ]

    def calculate(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算结构化输出质量评分

        评分维度:
        1. 核心字段完整性 (0.5分):
           - is_violation: +0.125
           - violation_type: +0.125
           - legal_basis: +0.125
           - confidence: +0.125

        2. 扩展字段 (0.3分):
           - cited_laws: +0.05
           - cited_cases: +0.05
           - validation_passed: +0.05
           - reflection_count: +0.05
           - remediation: +0.05
           - reasoning_chain: +0.05

        3. 格式规范性 (0.2分):
           - 字段类型正确: +0.1
           - 无None/null值: +0.1
        """
        # 1. 核心字段完整性评分
        core_score = 0.0
        missing_core = []

        for field in self.core_fields:
            if field in output and output[field] is not None:
                core_score += 0.125
            else:
                missing_core.append(field)

        core_score_weighted = core_score * 0.5

        # 2. 扩展字段评分
        extended_score = 0.0
        present_extended = []

        for field in self.extended_fields:
            if field in output:
                extended_score += 0.05
                present_extended.append(field)

        extended_score_weighted = extended_score * 0.3

        # 3. 格式规范性评分
        format_score = 0.0

        # 检查字段类型
        type_correct = True
        if "is_violation" in output:
            type_correct &= isinstance(output["is_violation"], bool)
        if "confidence" in output and output["confidence"] is not None:
            type_correct &= isinstance(output["confidence"], (int, float))

        format_score += 0.1 if type_correct else 0

        # 检查核心字段是否有None
        no_none_in_core = all(
            output.get(field) is not None
            for field in self.core_fields
            if field in output
        )
        format_score += 0.1 if no_none_in_core else 0

        format_score_weighted = format_score * 0.2

        # 总分
        final_score = core_score_weighted + extended_score_weighted + format_score_weighted

        return {
            "score": round(final_score, 3),
            "missing_fields": missing_core,
            "details": {
                "core_score": round(core_score_weighted, 3),
                "extended_score": round(extended_score_weighted, 3),
                "format_score": round(format_score_weighted, 3),
                "core_fields_count": len(self.core_fields) - len(missing_core),
                "extended_fields_count": len(present_extended),
                "present_extended_fields": present_extended,
                "type_correct": type_correct,
                "no_none_in_core": no_none_in_core
            }
        }


# 综合评估器
class AdvancedMetricsEvaluator:
    """综合高级指标评估器"""

    def __init__(self):
        self.evidence_chain = EvidenceChainMetric()
        self.legal_citation = LegalCitationMetric()
        self.remediation = RemediationMetric()
        self.explainability = ExplainabilityMetric()
        self.structured_output = StructuredOutputMetric()

    def evaluate(self, output: Dict[str, Any],
                ground_truth_laws: List[str] = None,
                retrieved_laws: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        综合评估单个输出的所有高级指标

        Args:
            output: 模型输出结果
            ground_truth_laws: Ground truth法律依据列表
            retrieved_laws: 检索到的法律文档（仅Agent有）

        Returns:
            所有高级指标的评分结果
        """
        # 提取推理链
        reasoning_chain = output.get("reasoning_chain", [])
        if isinstance(reasoning_chain, str):
            # 如果是字符串，尝试按换行拆分
            reasoning_chain = [reasoning_chain]
        elif not reasoning_chain:
            # 如果没有reasoning_chain，尝试使用reasoning字段
            reasoning = output.get("reasoning", "")
            if reasoning:
                reasoning_chain = [reasoning]

        # 提取法律依据
        legal_basis = output.get("legal_basis", "")

        # 1. 证据链完整性
        evidence_result = self.evidence_chain.calculate(reasoning_chain, output)

        # 2. 法律引用准确性
        citation_result = self.legal_citation.calculate(
            legal_basis, reasoning_chain, ground_truth_laws, retrieved_laws
        )

        # 3. 整改建议可操作性
        remediation_result = self.remediation.calculate(output)

        # 4. 可解释性
        explainability_result = self.explainability.calculate(reasoning_chain, legal_basis, output)

        # 5. 结构化输出质量
        structured_result = self.structured_output.calculate(output)

        return {
            "evidence_chain_completeness": evidence_result,
            "legal_citation_accuracy": citation_result,
            "remediation_actionability": remediation_result,
            "explainability": explainability_result,
            "structured_output_quality": structured_result,
            "summary": {
                "evidence_chain_score": evidence_result["score"],
                "legal_citation_score": citation_result["score"],
                "remediation_score": remediation_result["score"],
                "explainability_score": explainability_result["score"],
                "structured_output_score": structured_result["score"],
                "average_score": round(
                    (evidence_result["score"] +
                     citation_result["score"] +
                     remediation_result["score"] +
                     explainability_result["score"] +
                     structured_result["score"]) / 5,
                    3
                )
            }
        }


# ============================================================
# 新增：三方法对比用的统计指标（Macro-F1, Type Accuracy, etc.）
# 用于黄金测试集上对 Baseline / RAG / Agent 做公平对比
# ============================================================

import numpy as np

try:
    from sklearn.metrics import classification_report, f1_score
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

_COMPLIANCE_NORM = {"不违规": "无违规", "无": "无违规", "合规": "无违规", "": "无违规"}
_STD_LABELS = ["虚构原价", "虚假折扣", "价格误导", "要素缺失", "其他", "无违规"]


def _norm(label):
    if label is None:
        return "无违规"
    return _COMPLIANCE_NORM.get(label, label)


def _extract_citations(text: str) -> List[str]:
    """从模型输出文本中提取法律条款引用"""
    return list(set(re.findall(r"《[^》]+》第[一二三四五六七八九十百\d]+条(?:第[一二三四五六七八九十\d]+款)?", text)))


def _norm_citation(c: str) -> str:
    """归一化中英文数字混用的条款号"""
    cn = {"二十二":"22","二十一":"21","二十":"20","十九":"19","十八":"18","十七":"17",
          "十六":"16","十五":"15","十四":"14","十三":"13","十二":"12","十一":"11",
          "十":"10","九":"9","八":"8","七":"7","六":"6","五":"5","四":"4",
          "三":"3","二":"2","一":"1"}
    r = c
    for k, v in cn.items():
        r = r.replace(k, v)
    return r


class AdvancedMetrics:
    """
    三方法对比专用统计指标（用于黄金测试集评估）

    指标1 - Macro-F1：6类违规类型的宏平均F1（取代饱和的Binary Accuracy）
    指标2 - Type Accuracy：违规案例中违规类型命中率
    指标3 - Legal Citation Accuracy：与黄金测试集 ground truth 对比的法律引用准确率
    指标4 - Weighted Accuracy：FN代价=3×FP（漏判违规比误判合规更严重）

    USAGE:
        metrics = AdvancedMetrics()
        results = metrics.compute_all(
            y_true_binary=[True, False, ...],
            y_pred_binary=[True, True, ...],
            y_true_types=["虚构原价", "无违规", ...],
            y_pred_types=["虚构原价", "无违规", ...],
        )
        print(metrics.format_report(results))
    """

    def compute_macro_f1(self, y_true_types, y_pred_types, labels=None):
        labels = labels or _STD_LABELS
        yt = [_norm(x) for x in y_true_types]
        yp = [_norm(x) for x in y_pred_types]
        if _SKLEARN:
            mf1 = f1_score(yt, yp, labels=labels, average="macro", zero_division=0)
            rpt = classification_report(yt, yp, labels=labels, zero_division=0, output_dict=True)
            per_class = {l: round(rpt[l]["f1-score"], 4) for l in labels if l in rpt}
            full = classification_report(yt, yp, labels=labels, zero_division=0)
        else:
            per_class = {}
            for l in labels:
                tp = sum(1 for a, b in zip(yt, yp) if a == l and b == l)
                fp = sum(1 for a, b in zip(yt, yp) if a != l and b == l)
                fn = sum(1 for a, b in zip(yt, yp) if a == l and b != l)
                p = tp / (tp + fp) if (tp + fp) else 0.0
                r = tp / (tp + fn) if (tp + fn) else 0.0
                per_class[l] = round(2*p*r/(p+r) if (p+r) else 0.0, 4)
            mf1 = sum(per_class.values()) / len(labels) if labels else 0.0
            full = "\n".join(f"  {l}: {f}" for l, f in per_class.items())
        return {"macro_f1": round(float(mf1), 4), "per_class_f1": per_class, "full_report": full}

    def compute_type_accuracy(self, y_true_types, y_pred_types, is_violation_mask):
        correct = total = 0
        for t, p, v in zip(y_true_types, y_pred_types, is_violation_mask):
            if not v:
                continue
            total += 1
            if _norm(t) == _norm(p):
                correct += 1
        return round(correct / total, 4) if total else 0.0

    def compute_legal_citation_accuracy(self, ground_truth_laws, predicted_laws):
        prec, rec, n = [], [], 0
        for gt, pred in zip(ground_truth_laws, predicted_laws):
            if not gt:
                continue
            gs = set(_norm_citation(c) for c in gt)
            ps = set(_norm_citation(c) for c in (pred or []))
            inter = gs & ps
            prec.append(len(inter) / len(ps) if ps else 0.0)
            rec.append(len(inter) / len(gs) if gs else 1.0)
            n += 1
        if not prec:
            return {"citation_precision": 0.0, "citation_recall": 0.0, "citation_f1": 0.0, "evaluated_samples": 0}
        ap, ar = float(np.mean(prec)), float(np.mean(rec))
        f1 = 2*ap*ar/(ap+ar) if (ap+ar) else 0.0
        return {"citation_precision": round(ap, 4), "citation_recall": round(ar, 4), "citation_f1": round(f1, 4), "evaluated_samples": n}

    def compute_weighted_accuracy(self, y_true, y_pred, fn_weight=3.0, fp_weight=1.0):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
        tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
        fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
        d = tp + tn + fn_weight * fn + fp_weight * fp
        return {"weighted_accuracy": round((tp + tn) / d, 4) if d else 0.0,
                "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                "fn_weight": fn_weight, "fp_weight": fp_weight}

    def compute_all(self, y_true_binary, y_pred_binary, y_true_types, y_pred_types,
                    ground_truth_laws=None, predicted_laws=None, fn_weight=3.0):
        r = {}
        r["macro_f1_result"] = self.compute_macro_f1(y_true_types, y_pred_types)
        r["macro_f1"] = r["macro_f1_result"]["macro_f1"]
        r["type_accuracy"] = self.compute_type_accuracy(y_true_types, y_pred_types, y_true_binary)
        r["weighted_accuracy_result"] = self.compute_weighted_accuracy(y_true_binary, y_pred_binary, fn_weight)
        r["weighted_accuracy"] = r["weighted_accuracy_result"]["weighted_accuracy"]
        n = len(y_true_binary)
        r["binary_accuracy"] = round(sum(t == p for t, p in zip(y_true_binary, y_pred_binary)) / n, 4) if n else 0.0
        if ground_truth_laws is not None and predicted_laws is not None:
            r["citation_metrics"] = self.compute_legal_citation_accuracy(ground_truth_laws, predicted_laws)
        else:
            r["citation_metrics"] = None
        return r

    @staticmethod
    def extract_citations_from_text(text: str) -> List[str]:
        """辅助方法：从模型输出文本中提取法律引用，供 compute_legal_citation_accuracy 使用"""
        return _extract_citations(text)

    def format_report(self, results: Dict) -> str:
        lines = ["=" * 60, "  评估指标报告 / Evaluation Metrics Report", "=" * 60]
        lines.append(f"\n[Binary Classification]")
        lines.append(f"  Binary Accuracy  : {results.get('binary_accuracy', 0):.4f}")
        wa = results.get("weighted_accuracy_result", {})
        lines.append(f"  Weighted Accuracy: {results.get('weighted_accuracy', 0):.4f} (FN×{wa.get('fn_weight',3)})")
        lines.append(f"  TP={wa.get('tp','?')}, TN={wa.get('tn','?')}, FP={wa.get('fp','?')}, FN={wa.get('fn','?')}")
        lines.append(f"\n[Violation Type Classification]")
        lines.append(f"  Macro-F1     : {results.get('macro_f1', 0):.4f}")
        lines.append(f"  Type Accuracy: {results.get('type_accuracy', 0):.4f} (violation cases only)")
        mf1 = results.get("macro_f1_result", {})
        if mf1.get("per_class_f1"):
            lines.append(f"\n  Per-class F1:")
            for label, f1 in mf1["per_class_f1"].items():
                lines.append(f"    {label:15s}: {f1:.4f}")
        cm = results.get("citation_metrics")
        if cm:
            lines.append(f"\n[Legal Citation Accuracy] (n={cm.get('evaluated_samples',0)})")
            lines.append(f"  Precision: {cm.get('citation_precision',0):.4f}")
            lines.append(f"  Recall   : {cm.get('citation_recall',0):.4f}")
            lines.append(f"  F1       : {cm.get('citation_f1',0):.4f}")
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试示例
    test_output = {
        "is_violation": True,
        "violation_type": "虚构原价",
        "legal_basis": "《禁止价格欺诈规定》第7条",
        "confidence": 0.95,
        "reasoning_chain": [
            "步骤1: 提取案例关键事实 - 商家标注划线价3000元，实际销售价198元",
            "步骤2: 检查历史数据 - 前7日内无成交记录",
            "步骤3: 匹配法律条款 - 根据《禁止价格欺诈规定》第7条，禁止虚构原价",
            "步骤4: 参考相似案例 - 案例045同样因无成交记录被处罚",
            "步骤5: 得出结论 - 构成虚构原价违规"
        ],
        "cited_laws": [{"title": "《禁止价格欺诈规定》第7条"}],
        "validation_passed": True
    }

    evaluator = AdvancedMetricsEvaluator()
    result = evaluator.evaluate(test_output, ground_truth_laws=["《禁止价格欺诈规定》第7条"])

    print("=== 高级指标评估结果 ===")
    print(f"证据链完整性: {result['summary']['evidence_chain_score']}")
    print(f"法律引用准确性: {result['summary']['legal_citation_score']}")
    print(f"整改建议可操作性: {result['summary']['remediation_score']}")
    print(f"可解释性: {result['summary']['explainability_score']}")
    print(f"结构化输出质量: {result['summary']['structured_output_score']}")
    print(f"平均分: {result['summary']['average_score']}")
