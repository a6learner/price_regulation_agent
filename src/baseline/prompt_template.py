"""
Prompt模板管理
用于价格合规分析的提示词设计
"""

from typing import Dict, Any


class PromptTemplate:
    """Prompt模板类"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一名电商平台价格合规分析专家，熟悉《价格法》、《禁止价格欺诈行为规定》等相关法律法规和典型案例。你的任务是根据给定的案例事实，从价格合规的角度分析经营行为是否违规，并提供专业的法律依据和结论。

请严格按照以下JSON格式输出你的分析结果：

```json
{
  "is_violation": true/false,
  "violation_type": "违规类型",
  "confidence": 0.0-1.0,
  "reasoning": "详细的分析依据和法律推理过程",
  "legal_basis": "相关法律条文或案例"
}
```

**违规类型说明**：
- 虚构原价：虚构原价、虚高原价、未实际交易的原价
- 价格误导：虚假优惠、误导性价格表述
- 虚假折扣：折扣计算错误、虚假折扣力度
- 要素缺失：缺少必要的价格说明、未标注关键信息
- 其他：其他价格违规行为
- 无违规：合规经营

**注意事项**：
1. 如果是合规案例，violation_type设置为"无违规"
2. confidence表示你对判断的置信度（0-1之间的小数）
3. reasoning必须包含详细的事实分析和法律推理
4. legal_basis需要引用具体的法律条款或类似案例
5. violation_type可能不唯一，请根据实际情况判断，可以同时包含多个违规类型

请确保输出是有效的JSON格式，不要包含任何其他文本。"""

    # 用户提示词模板
    USER_PROMPT_TEMPLATE = """请分析以下电商价格案例的合规性：

{case_description}

请根据以上案例，严格按照要求的JSON格式输出你的分析结果。"""

    @classmethod
    def build_user_prompt(cls, case_description: str) -> str:
        """
        构建用户提示词

        Args:
            case_description: 案例描述文本

        Returns:
            完整的用户提示词
        """
        return cls.USER_PROMPT_TEMPLATE.format(case_description=case_description)

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统提示词"""
        return cls.SYSTEM_PROMPT

    @classmethod
    def extract_case_description_from_eval(cls, eval_case: Dict[str, Any]) -> str:
        """
        从评估案例中提取案例描述

        Args:
            eval_case: 评估案例字典（包含messages字段）

        Returns:
            案例描述文本
        """
        # 从messages中提取user角色的content
        for message in eval_case.get('messages', []):
            if message.get('role') == 'user':
                return message.get('content', '')

        return ""

    @classmethod
    def build_prompts_from_eval(cls, eval_case: Dict[str, Any]) -> Dict[str, str]:
        """
        从评估案例构建完整的提示词

        Args:
            eval_case: 评估案例字典

        Returns:
            包含system_prompt和user_prompt的字典
        """
        case_description = cls.extract_case_description_from_eval(eval_case)
        user_prompt = cls.build_user_prompt(case_description)

        return {
            'system_prompt': cls.get_system_prompt(),
            'user_prompt': user_prompt
        }
