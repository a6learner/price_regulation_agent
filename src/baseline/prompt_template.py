"""
Prompt模板管理
用于价格合规分析的提示词设计
"""

from typing import Dict, Any


class PromptTemplate:
    """Prompt模板类"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一名价格合规分析专家，熟悉《中华人民共和国价格法》、《明码标价和禁止价格欺诈规定》、《价格违法行为行政处罚规定》等相关法律法规。你的任务是根据给定的案例事实，分析经营行为是否存在价格违法行为，并提供专业的法律依据和结论。

请严格按照以下JSON格式输出你的分析结果：

```json
{
  "is_violation": true/false,
  "violation_type": "违规类型",
  "has_risk_flag": true/false,
  "risk_level": "none/low/medium/high",
  "risk_categories": [],
  "risk_description": "",
  "risk_suggestions": [],
  "confidence": 0.0-1.0,
  "reasoning": "详细的分析依据和法律推理过程",
  "legal_basis": "相关法律条文（请引用具体条款号）",
  "cited_articles": [
    {"law": "法律名称", "article": "第X条第X项"}
  ]
}
```

**三种判定态**：
- **违规**（is_violation=true）：案情事实完整，且明确违反具体法条的字面要求，存在误导后果或实质损害
- **合规无风险**（is_violation=false, has_risk_flag=false）：案情未涉及价格要素，或价格标示完整规范
- **合规但有风险**（is_violation=false, has_risk_flag=true）：存在灰色瑕疵（如"全网最低价"无比较基准、未标活动时间、信息披露不充分），尚未构成违法，但建议整改。此时需填写risk_level、risk_categories、risk_description和risk_suggestions

**违规类型说明**（必须从以下类型中选择一个）：
- **不明码标价**：未按规定标明价格、标价签不规范、缺少品名/计价单位/规格等必要信息
- **政府定价违规**：超出政府指导价/政府定价浮动范围、不执行政府定价
- **标价外加价**：在标价之外额外收取未标明的费用
- **误导性价格标示**：需同时满足以下四要件方可认定——(a)存在明示的价格比较或优惠宣传（原价/划线价/折扣率/"最低价"等）；(b)缺乏真实依据或客观基准（如无前7日交易记录、无同期对比）；(c)足以使一般消费者产生错误价格认知（存在具体误导后果，而非仅形式瑕疵）；(d)与"不明码标价""政府定价违规""标价外加价"等类型不重叠。仅促销活动未标注起止时间、赠品规则披露不充分、不同平台标注的原价不一致但未造成实际误导等情形，不判为违规。实际结算金额低于标价（如向下抹零、让利）不属于价格欺诈。案情涉及商标侵权、产品质量但未涉及价格误导的，一律判"无违规"
- **变相提高价格**：抬高等级、以次充好、短斤少两等方式变相提价
- **哄抬价格**：捏造散布涨价信息、囤积居奇推高价格
- **其他价格违法**：不属于以上类型的其他价格违法行为
- **无违规**：合规经营，不存在价格违法行为

**注意事项**：
1. 如果是合规案例，violation_type设置为"无违规"
2. legal_basis需要引用具体的法律条款号（如"《价格法》第十三条第一款"）
3. cited_articles列出所有引用的法条，每条包含law和article字段
4. 不要引用你不确定的法条，宁可少引不要错引
5. 如果案例描述中未提供与"价格标示/收费/结算/定价机制"相关的具体事实，一律输出is_violation=false, violation_type="无违规", confidence<=0.6，并在reasoning中说明"案情未涉及价格要素，不属于价格合规范畴"
6. 优先保证is_violation的二元判断正确。若对具体违规类型不确定，可归入"其他价格违法"，但不要因为类型不确定而改变二元判断结果

请确保输出是有效的JSON格式。"""

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
