"""Reasoning Engine - 推理引擎

Chain-of-Thought推理，基于高质量文档生成分析结果
"""
from src.baseline.maas_client import MaaSClient
import json
import re


class ReasoningEngine:
    """推理引擎 - 5步Chain-of-Thought推理"""

    def __init__(self, config_path="configs/model_config.yaml"):
        self.client = MaaSClient(config_path)

    def reason(self, query, graded_docs, intent, feedback=None):
        """执行Chain-of-Thought推理

        Args:
            query: 原始查询
            graded_docs: Grader的输出（高质量文档）
            intent: Intent Analyzer的输出
            feedback: 反思反馈（重新推理时使用）

        Returns:
            dict: 推理结果
        """
        system_prompt = self._build_system_prompt(graded_docs, feedback)
        user_prompt = self._build_user_prompt(query, intent)

        response = self.client.call_model(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_key='qwen-8b'
        )

        if not response:
            return {"success": False, "error": "API调用失败"}

        response_text = self.client.extract_response_text(response)

        try:
            result = self._parse_response(response_text)
            result['success'] = True
            result['raw_response'] = response_text[:500]
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"解析失败: {e}",
                "raw_response": response_text[:500]
            }

    def _build_system_prompt(self, graded_docs, feedback):
        """构建System Prompt"""
        laws = graded_docs.get('graded_laws', [])
        cases = graded_docs.get('graded_cases', [])
        has_cases = len(cases) > 0

        laws_text = self._format_laws(laws)

        prompt = f"""你是电商平台价格合规分析专家，熟悉《价格法》、《禁止价格欺诈行为规定》等相关法律法规。

**重要参考资料**（已评分筛选的高质量文档）：

【相关法律条文】
{laws_text}"""

        if has_cases:
            cases_text = self._format_cases(cases)
            prompt += f"""

【相似处罚案例】
{cases_text}"""

        if feedback:
            prompt += f"\n\n**重要反馈**：\n{feedback}\n"

        if has_cases:
            reasoning_steps = """
**推理要求**：
1. 按照5个步骤进行推理，输出完整的reasoning_chain
2. 每一步基于事实和法律依据，不要凭空推测
3. 仅引用上述高质量法律条文（标注了评分），不要引用其他法律
4. legal_basis应明确指出具体法律条款和条款号"""
            cot_template = """
**输出格式**（JSON）：
```json
{{
  "reasoning_chain": [
    "步骤1: 提取案例关键事实 - ...",
    "步骤2: 检查价格要素 - ...",
    "步骤3: 匹配法律条款 - ...",
    "步骤4: 参考相似案例 - ...",
    "步骤5: 得出结论 - ..."
  ],
  "is_violation": true/false,
  "violation_type": "必须是上述类型之一",
  "has_risk_flag": true/false,
  "risk_level": "none/low/medium/high",
  "risk_categories": [],
  "risk_description": "",
  "risk_suggestions": [],
  "legal_basis": "《法律名称》第X条",
  "cited_articles": [
    {{"law": "价格法", "article": "第十三条"}}
  ],
  "confidence": 0.0-1.0
}}
```

**三种判定态**：
- **违规**（is_violation=true）：案情事实完整，且明确违反具体法条的字面要求，存在误导后果或实质损害
- **合规无风险**（is_violation=false, has_risk_flag=false）：案情未涉及价格要素，或价格标示完整规范
- **合规但有风险**（is_violation=false, has_risk_flag=true）：存在灰色瑕疵，尚未构成违法，但建议整改"""
        else:
            reasoning_steps = """
**推理要求**：
1. 按照4个步骤进行推理，输出完整的reasoning_chain
2. 每一步基于事实和法律依据，不要凭空推测
3. 仅引用上述高质量法律条文（标注了评分），不要引用其他法律
4. legal_basis应明确指出具体法律条款和条款号
5. 禁止引用上下文未提供的历史案例或处罚判例。不得在推理链、legal_basis或reasoning中出现"类似案例""历史案例""处罚判例"等表述"""
            cot_template = """
**输出格式**（JSON）：
```json
{{
  "reasoning_chain": [
    "步骤1: 提取案例关键事实 - ...",
    "步骤2: 检查价格要素 - ...",
    "步骤3: 匹配法律条款 - ...",
    "步骤4: 得出结论 - ..."
  ],
  "is_violation": true/false,
  "violation_type": "必须是上述类型之一",
  "has_risk_flag": true/false,
  "risk_level": "none/low/medium/high",
  "risk_categories": [],
  "risk_description": "",
  "risk_suggestions": [],
  "legal_basis": "《法律名称》第X条",
  "cited_articles": [
    {{"law": "价格法", "article": "第十三条"}}
  ],
  "confidence": 0.0-1.0
}}
```

**三种判定态**：
- **违规**（is_violation=true）：案情事实完整，且明确违反具体法条的字面要求，存在误导后果或实质损害
- **合规无风险**（is_violation=false, has_risk_flag=false）：案情未涉及价格要素，或价格标示完整规范
- **合规但有风险**（is_violation=false, has_risk_flag=true）：存在灰色瑕疵，尚未构成违法，但建议整改"""

        prompt += reasoning_steps

        prompt += """

**违规类型分类**（必须从以下类型中选择一个）：
- **不明码标价**：未按规定标明价格、标价签不规范、缺少品名/计价单位/规格等必要信息
- **政府定价违规**：超出政府指导价/政府定价浮动范围、不执行政府定价
- **标价外加价**：在标价之外额外收取未标明的费用
- **误导性价格标示**：需同时满足以下四要件方可认定——(a)存在明示的价格比较或优惠宣传（原价/划线价/折扣率/"最低价"等）；(b)缺乏真实依据或客观基准（如无前7日交易记录、无同期对比）；(c)足以使一般消费者产生错误价格认知（存在具体误导后果，而非仅形式瑕疵）；(d)与"不明码标价""政府定价违规""标价外加价"等类型不重叠。仅促销活动未标注起止时间、赠品规则披露不充分、不同平台标注的原价不一致但未造成实际误导等情形，不判为违规。实际结算金额低于标价（如向下抹零、让利）不属于价格欺诈。案情涉及商标侵权、产品质量但未涉及价格误导的，一律判"无违规"
- **变相提高价格**：抬高等级、以次充好、短斤少两等方式变相提价
- **哄抬价格**：捏造散布涨价信息、囤积居奇推高价格
- **其他价格违法**：不属于以上类型的其他价格违法行为
- **无违规**：符合价格合规要求，不存在违规行为

**判断示例**：
1. "超市货架上7瓶洗手液未标明价格" → 不明码标价
2. "停车场收费超出政府指导价标准" → 政府定价违规
3. "收取未标明的50元包装费" → 标价外加价
4. "标注原价1680元但从未以此价格销售" → 误导性价格标示
5. "注水肉冒充正常肉销售" → 变相提高价格"""

        prompt += cot_template

        prompt += """

**重要提醒**：
- violation_type必须精确匹配上述类型之一
- 不要输出"价格欺诈"、"虚假宣传"、"要素缺失"等旧标准类型
- 如果是无违规案例，violation_type应为"无违规"
- cited_articles只列出最相关的法条，宁可少引不要错引
- 如果案例描述中未提供与"价格标示/收费/结算/定价机制"相关的具体事实，一律输出is_violation=false, violation_type="无违规", confidence<=0.6，并在reasoning_chain中说明"案情未涉及价格要素，不属于价格合规范畴"
- 优先保证is_violation的二元判断正确。若对具体违规类型不确定，可归入"其他价格违法"，但不要因为类型不确定而改变二元判断结果

请确保输出是有效的JSON格式。"""

        return prompt

    def _build_user_prompt(self, query, intent):
        """构建User Prompt"""
        hints = intent.get('reasoning_hints', [])

        prompt = f"请分析以下价格案例：\n\n{query}"

        if hints:
            prompt += "\n\n**分析提示**：\n"
            for hint in hints:
                prompt += f"- {hint}\n"

        prompt += "\n请按照要求输出JSON格式的推理结果。"
        return prompt

    def _format_laws(self, laws):
        """格式化法律条文"""
        if not laws:
            return "（暂无相关法律条文）"

        formatted = []
        for i, law in enumerate(laws, 1):
            content = law['content']
            score = law.get('final_score', 0)
            grade = law.get('grade', 'unknown')
            formatted.append(f"{i}. {content}\n   [评分: {score:.2f}, 等级: {grade}]")

        return "\n\n".join(formatted)

    def _format_cases(self, cases):
        """格式化案例"""
        if not cases:
            return "（暂无相似案例）"

        formatted = []
        for i, case in enumerate(cases, 1):
            content = case['content'][:300]  # 限制长度
            score = case.get('final_score', 0)
            formatted.append(f"{i}. {content}...\n   [评分: {score:.2f}]")

        return "\n\n".join(formatted)

    def _parse_response(self, text):
        """解析LLM响应"""
        # 提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        json_str = json_match.group(1) if json_match else text

        result = json.loads(json_str)

        # 确保必要字段存在
        if 'reasoning_chain' not in result:
            result['reasoning_chain'] = ["（推理链解析失败）"]

        if 'is_violation' not in result:
            result['is_violation'] = None

        # risk flag 字段默认值
        result.setdefault('has_risk_flag', False)
        result.setdefault('risk_level', 'none')
        result.setdefault('risk_categories', [])
        result.setdefault('risk_description', '')
        result.setdefault('risk_suggestions', [])

        return result
