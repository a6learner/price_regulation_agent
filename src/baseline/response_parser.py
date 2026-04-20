"""
响应解析器
从LLM的响应中提取结构化信息，并评估法律依据准确性和推理质量
"""

import json
import re
from typing import Dict, Any, Optional, List

from .violation_type_config import SYNONYM_GROUPS, HIERARCHY_MAPPING, MatchConfig


class ViolationTypeMatcher:
    """违规类型智能匹配器"""

    def __init__(self, config: MatchConfig = MatchConfig()):
        self.config = config
        self.synonym_map = self._build_synonym_map()
        self.hierarchy_map = HIERARCHY_MAPPING

    def _build_synonym_map(self) -> dict:
        """构建同义词映射表"""
        synonym_map = {}
        for group in SYNONYM_GROUPS:
            for word in group:
                synonym_map[word] = group
        return synonym_map

    def match(self, predicted: str, ground_truth: str) -> dict:
        """
        智能匹配违规类型

        Returns:
            {
                'matched': bool,
                'match_type': str,  # exact/normalized/synonym/multi_label/superclass/none
                'confidence': float,
                'details': str
            }
        """
        if not self.config.ENABLE_SMART_MATCHING:
            # 回退到简单匹配
            return self._exact_match(predicted, ground_truth)

        # 策略1: 精确匹配
        result = self._exact_match(predicted, ground_truth)
        if result['matched']:
            return result

        # 策略2: 标准化匹配
        result = self._normalized_match(predicted, ground_truth)
        if result['matched']:
            return result

        # 策略3: 同义词匹配
        result = self._synonym_match(predicted, ground_truth)
        if result['matched']:
            return result

        # 策略4: 多标签匹配
        result = self._multi_label_match(predicted, ground_truth)
        if result['matched']:
            return result

        # 策略5: 上位概念匹配
        if self.config.ACCEPT_SUPERCLASS:
            result = self._superclass_match(predicted, ground_truth)
            if result['matched']:
                return result

        # 无匹配
        return {
            'matched': False,
            'match_type': 'none',
            'confidence': 0.0,
            'details': f"预测'{predicted}' 与 真值'{ground_truth}' 不匹配"
        }

    def _exact_match(self, pred: str, truth: str) -> dict:
        """精确匹配"""
        if pred == truth:
            return {
                'matched': True,
                'match_type': 'exact',
                'confidence': 1.0,
                'details': f"精确匹配: '{pred}' == '{truth}'"
            }
        return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

    def _normalized_match(self, pred: str, truth: str) -> dict:
        """标准化匹配（去除标点、空格）"""
        def normalize(text):
            # 去除所有标点和空格
            return re.sub(r'[,，;；、\s]+', '', text.strip())

        pred_norm = normalize(pred)
        truth_norm = normalize(truth)

        if pred_norm == truth_norm:
            return {
                'matched': True,
                'match_type': 'normalized',
                'confidence': self.config.CONFIDENCE_THRESHOLDS['normalized'],
                'details': f"标准化匹配: '{pred}' → '{pred_norm}' == '{truth_norm}' ← '{truth}'"
            }
        return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

    def _synonym_match(self, pred: str, truth: str) -> dict:
        """同义词匹配"""
        pred_group = self.synonym_map.get(pred.strip())
        truth_group = self.synonym_map.get(truth.strip())

        # 两者都在同一个同义词组中
        if pred_group and truth_group and pred_group == truth_group:
            return {
                'matched': True,
                'match_type': 'synonym',
                'confidence': self.config.CONFIDENCE_THRESHOLDS['synonym'],
                'details': f"同义词匹配: '{pred}' ≈ '{truth}' (同义词组: {pred_group})"
            }
        return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

    def _multi_label_match(self, pred: str, truth: str) -> dict:
        """多标签匹配"""
        # 分割预测中的多个标签
        pred_labels = self._split_labels(pred)

        if len(pred_labels) <= 1:
            return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

        # 检查真值是否在预测标签中（精确或同义）
        for pred_label in pred_labels:
            # 精确包含
            if pred_label.strip() == truth.strip():
                return {
                    'matched': True,
                    'match_type': 'multi_label',
                    'confidence': self.config.CONFIDENCE_THRESHOLDS['multi_label'],
                    'details': f"多标签包含: '{truth}' in {pred_labels}"
                }

            # 同义词包含
            pred_group = self.synonym_map.get(pred_label.strip())
            truth_group = self.synonym_map.get(truth.strip())
            if pred_group and truth_group and pred_group == truth_group:
                return {
                    'matched': True,
                    'match_type': 'multi_label_synonym',
                    'confidence': self.config.CONFIDENCE_THRESHOLDS['multi_label'] - 0.05,
                    'details': f"多标签同义词包含: '{truth}' ≈ '{pred_label}' in {pred_labels}"
                }

        return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

    def _superclass_match(self, pred: str, truth: str) -> dict:
        """上位概念匹配"""
        pred_clean = pred.strip()
        truth_clean = truth.strip()

        # 检查预测是否是真值的上位概念
        if pred_clean in self.hierarchy_map:
            children = self.hierarchy_map[pred_clean]
            if truth_clean in children:
                return {
                    'matched': True,
                    'match_type': 'superclass',
                    'confidence': self.config.CONFIDENCE_THRESHOLDS['superclass'],
                    'details': f"上位概念匹配: '{pred}' 包含 '{truth}'"
                }

        return {'matched': False, 'match_type': 'none', 'confidence': 0.0, 'details': ''}

    def _split_labels(self, text: str) -> list:
        """分割多标签文本"""
        # 使用所有可能的分隔符
        pattern = '|'.join(re.escape(sep) for sep in self.config.MULTI_LABEL_SEPARATORS)
        labels = re.split(pattern, text)
        return [label.strip() for label in labels if label.strip()]


class ResponseParser:
    """响应解析器类"""

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取JSON内容

        Args:
            text: 包含JSON的文本

        Returns:
            解析后的字典，失败返回None
        """
        # 尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 尝试从Markdown代码块中提取
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个{}内容
        brace_pattern = r'\{[\s\S]*\}'
        match = re.search(brace_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def validate_prediction(prediction: Dict[str, Any]) -> bool:
        """
        验证预测结果是否包含必要字段

        Args:
            prediction: 预测结果字典

        Returns:
            是否有效
        """
        required_fields = ['is_violation', 'violation_type']
        return all(field in prediction for field in required_fields)

    @staticmethod
    def normalize_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化预测结果

        Args:
            prediction: 原始预测结果

        Returns:
            标准化后的预测结果
        """
        normalized = {
            'is_violation': prediction.get('is_violation', None),
            'violation_type': prediction.get('violation_type', '未知'),
            'has_risk_flag': prediction.get('has_risk_flag', False),
            'risk_level': prediction.get('risk_level', 'none'),
            'risk_categories': prediction.get('risk_categories', []),
            'risk_description': prediction.get('risk_description', ''),
            'risk_suggestions': prediction.get('risk_suggestions', []),
            'confidence': prediction.get('confidence', 0.0),
            'reasoning': prediction.get('reasoning', ''),
            'legal_basis': prediction.get('legal_basis', '')
        }

        # 标准化violation_type - 处理list或str类型
        vtype = normalized['violation_type']
        if isinstance(vtype, list):
            normalized['violation_type'] = vtype[0].strip() if vtype and vtype[0] else '未知'
        elif isinstance(vtype, str):
            normalized['violation_type'] = vtype.strip()
        else:
            normalized['violation_type'] = '未知'

        # 标准化reasoning - 处理list或str类型
        reasoning = normalized['reasoning']
        if isinstance(reasoning, list):
            normalized['reasoning'] = ' '.join(str(r) for r in reasoning if r) if reasoning else ''
        elif not isinstance(reasoning, str):
            normalized['reasoning'] = str(reasoning) if reasoning else ''

        # 标准化legal_basis - 处理list或str类型
        legal_basis = normalized['legal_basis']
        if isinstance(legal_basis, list):
            normalized['legal_basis'] = ' '.join(str(lb) for lb in legal_basis if lb) if legal_basis else ''
        elif not isinstance(legal_basis, str):
            normalized['legal_basis'] = str(legal_basis) if legal_basis else ''

        return normalized

    @classmethod
    def parse_response(cls, response_text: str) -> Optional[Dict[str, Any]]:
        """
        解析LLM响应

        Args:
            response_text: LLM返回的文本

        Returns:
            解析并标准化后的预测结果，失败返回None
        """
        if not response_text:
            return None

        # 提取JSON
        prediction = cls.extract_json_from_text(response_text)
        if not prediction:
            print(f"无法从响应中提取JSON: {response_text[:200]}...")
            return None

        # 验证必要字段
        if not cls.validate_prediction(prediction):
            print(f"预测结果缺少必要字段: {prediction}")
            return None

        # 标准化
        return cls.normalize_prediction(prediction)

    @staticmethod
    def extract_ground_truth(eval_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        从评估案例中提取ground truth

        Args:
            eval_case: 评估案例字典

        Returns:
            ground truth字典
        """
        meta = eval_case.get('meta', {})

        return {
            'is_violation': meta.get('is_violation', None),
            'violation_type': meta.get('violation_type', '未知'),
            'platform': meta.get('platform', '未知'),
            'scenario': meta.get('scenario', '未知'),
            'complexity': meta.get('complexity', 'medium')
        }

    @staticmethod
    def compare_prediction_with_truth(
        prediction: Dict[str, Any],
        ground_truth: Dict[str, Any],
        use_smart_matching: bool = True
    ) -> Dict[str, Any]:
        """
        比较预测结果与ground truth

        Args:
            prediction: 预测结果
            ground_truth: ground truth
            use_smart_matching: 是否使用智能匹配（默认True）

        Returns:
            比较结果字典（新增match_details字段）
        """
        is_correct = prediction['is_violation'] == ground_truth['is_violation']
        type_correct = False
        match_details = {}

        # 只有当违规判断正确时，才比较违规类型
        if is_correct:
            # 处理prediction的violation_type（已在normalize中处理，应该是str）
            pred_type = prediction['violation_type'].strip() if isinstance(prediction['violation_type'], str) and prediction['violation_type'] else ''

            # 处理ground_truth的violation_type（可能是str或list）
            truth_vtype = ground_truth['violation_type']
            if isinstance(truth_vtype, list):
                truth_type = truth_vtype[0].strip() if truth_vtype and truth_vtype[0] else ''
            elif isinstance(truth_vtype, str):
                truth_type = truth_vtype.strip()
            else:
                truth_type = ''

            if use_smart_matching:
                # 使用智能匹配器
                matcher = ViolationTypeMatcher()
                match_result = matcher.match(pred_type, truth_type)
                type_correct = match_result['matched']
                match_details = match_result
            else:
                # 回退到简单匹配
                type_correct = pred_type == truth_type
                match_details = {
                    'matched': type_correct,
                    'match_type': 'exact' if type_correct else 'none',
                    'confidence': 1.0 if type_correct else 0.0,
                    'details': ''
                }

        return {
            'is_correct': is_correct,
            'type_correct': type_correct,
            'match_details': match_details
        }

    @staticmethod
    def evaluate_legal_basis_accuracy(prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估法律依据的准确性和完整性

        评估维度：
        1. 是否引用了法律依据
        2. 法条引用是否具体（包含法律名称、条款号）
        3. 引用的法律数量

        Args:
            prediction: 预测结果字典

        Returns:
            评估结果字典
        """
        legal_basis = prediction.get('legal_basis', '')

        # 检查是否为空
        has_legal_basis = bool(legal_basis and legal_basis.strip())

        # 关键法律关键词
        key_laws = [
            '价格法', '禁止价格欺诈', '明码标价', '价格违法行为',
            '消费者权益', '反不正当竞争', '网络交易监督管理',
            '规范促销行为', '互联网平台价格行为'
        ]

        # 统计引用的法律数量
        laws_mentioned = sum(1 for law in key_laws if law in legal_basis)

        # 检查是否包含具体条款（如"第X条"）
        has_specific_article = bool(re.search(r'第[一二三四五六七八九十\d]+条', legal_basis))

        # 计算法律依据质量分数 (0-1)
        score = 0.0
        if has_legal_basis:
            score += 0.3  # 基础分：有引用
            score += min(laws_mentioned * 0.2, 0.5)  # 引用法律数量
            if has_specific_article:
                score += 0.2  # 有具体条款

        return {
            'has_legal_basis': has_legal_basis,
            'laws_mentioned_count': laws_mentioned,
            'has_specific_article': has_specific_article,
            'legal_basis_score': min(score, 1.0),
            'legal_basis_length': len(legal_basis)
        }

    @staticmethod
    def evaluate_reasoning_quality(prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估推理过程的质量和可解释性

        评估维度：
        1. 推理过程是否存在
        2. 推理是否包含事实陈述
        3. 推理是否包含法律分析
        4. 推理是否包含逻辑链条
        5. 推理的完整性（长度）

        Args:
            prediction: 预测结果字典

        Returns:
            评估结果字典
        """
        reasoning = prediction.get('reasoning', '')

        # 检查是否为空
        has_reasoning = bool(reasoning and reasoning.strip())

        # 检查是否包含事实陈述关键词
        fact_keywords = ['经查', '查实', '调查', '事实', '案情', '经营者', '商品']
        has_facts = any(keyword in reasoning for keyword in fact_keywords)

        # 检查是否包含法律分析关键词
        legal_keywords = ['根据', '违反', '符合', '构成', '属于', '法规', '规定']
        has_legal_analysis = any(keyword in reasoning for keyword in legal_keywords)

        # 检查是否包含逻辑连接词
        logic_keywords = ['因此', '所以', '由于', '因为', '导致', '从而', '故而']
        has_logic_chain = any(keyword in reasoning for keyword in logic_keywords)

        # 检查推理的结构完整性（是否包含多个句子）
        sentence_count = len(re.findall(r'[。！？]', reasoning))
        has_structure = sentence_count >= 3

        # 计算推理质量分数 (0-1)
        score = 0.0
        if has_reasoning:
            score += 0.2  # 基础分：有推理
            if has_facts:
                score += 0.25  # 包含事实
            if has_legal_analysis:
                score += 0.25  # 包含法律分析
            if has_logic_chain:
                score += 0.15  # 包含逻辑链
            if has_structure:
                score += 0.15  # 结构完整

        return {
            'has_reasoning': has_reasoning,
            'has_facts': has_facts,
            'has_legal_analysis': has_legal_analysis,
            'has_logic_chain': has_logic_chain,
            'sentence_count': sentence_count,
            'reasoning_score': min(score, 1.0),
            'reasoning_length': len(reasoning)
        }
