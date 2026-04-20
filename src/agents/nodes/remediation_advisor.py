"""
RemediationAdvisor节点 - 整改建议生成器

为违规案例生成具体的整改建议，支持：
1. 快速模式（规则模板生成，0 tokens）
2. 详细模式（LLM生成，+500 tokens，可选）
"""

from typing import Dict, Any, List
from src.baseline.maas_client import MaaSClient
from src.agents.audience_remediation import (
    build_compliant_remediation,
    build_consumer_violation_advice,
    build_regulator_violation_advice,
    normalize_audience,
)
import json
import re


class RemediationAdvisor:
    """整改建议生成器"""

    # 预设规则模板（使用标准违规类型作为键名）
    REMEDIATION_TEMPLATES = {
        "不明码标价": {
            "steps": [
                {
                    "step": 1,
                    "action": "补充缺失的价格要素信息（品名、规格、计价单位、价格等）",
                    "legal_basis": "《价格法》第13条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "确保所有商品价格标注完整规范，标价签信息齐全",
                    "legal_basis": "《明码标价和禁止价格欺诈规定》第4-6条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 3,
                    "action": "建立价格信息审核checklist，避免遗漏关键要素",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家审核部门"
                }
            ],
            "checklist": [
                "商品规格明确标注",
                "计量单位标注清晰",
                "标价签包含品名、产地、规格等必要信息",
                "服务项目收费标准公示"
            ],
            "penalty_range": "500-20000元"
        },
        "政府定价违规": {
            "steps": [
                {
                    "step": 1,
                    "action": "立即将收费标准调整至政府指导价/政府定价范围内",
                    "legal_basis": "《价格法》第12条",
                    "priority": "high",
                    "responsible_party": "商家定价部门"
                },
                {
                    "step": 2,
                    "action": "核查所有受政府定价管控的服务项目，确保无超标收费",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家合规部门"
                },
                {
                    "step": 3,
                    "action": "建立政府定价跟踪机制，及时更新收费标准",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家合规部门"
                }
            ],
            "checklist": [
                "收费标准在政府指导价范围内",
                "已获取最新政府定价文件",
                "收费公示牌内容与政府定价一致",
                "定期核查政府定价调整"
            ],
            "penalty_range": "5000-200000元"
        },
        "标价外加价": {
            "steps": [
                {
                    "step": 1,
                    "action": "停止在标价之外收取未标明的额外费用",
                    "legal_basis": "《价格法》第13条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "将所有附加费用纳入标价体系，公开透明标注",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家定价部门"
                },
                {
                    "step": 3,
                    "action": "审核所有收费项目，确保标价与实收一致",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家审核部门"
                }
            ],
            "checklist": [
                "所有费用已在标价中体现",
                "无未标明的额外收费项目",
                "标价与实际结算金额一致",
                "附加服务费用已明确标注"
            ],
            "penalty_range": "1000-50000元"
        },
        "误导性价格标示": {
            "steps": [
                {
                    "step": 1,
                    "action": "立即删除虚构的原价/划线价标注，仅展示有真实交易依据的价格",
                    "legal_basis": "《禁止价格欺诈行为规定》第7条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "提供前7日内实际成交记录作为原价依据，或调整为合规的标注方式",
                    "legal_basis": "《价格法》第14条",
                    "priority": "high",
                    "responsible_party": "商家定价部门"
                },
                {
                    "step": 3,
                    "action": "建立价格档案管理制度，培训运营人员了解原价标注规范",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家培训部门"
                }
            ],
            "checklist": [
                "检查前7日内是否有实际成交记录",
                "原价标注需提供交易凭证",
                "确保所有渠道价格标注一致",
                "折扣计算基于真实基准价"
            ],
            "penalty_range": "1000-50000元"
        },
        "变相提高价格": {
            "steps": [
                {
                    "step": 1,
                    "action": "停止以次充好、短斤少两等变相提价行为",
                    "legal_basis": "《价格法》第14条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "核查商品规格、等级与标注是否一致",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家质量部门"
                },
                {
                    "step": 3,
                    "action": "建立商品质量与价格对应的审核机制",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家合规部门"
                }
            ],
            "checklist": [
                "商品实际规格与标注一致",
                "计量器具经过校准",
                "等级标注真实准确",
                "不存在掺杂掺假行为"
            ],
            "penalty_range": "5000-100000元"
        },
        "哄抬价格": {
            "steps": [
                {
                    "step": 1,
                    "action": "立即将价格恢复至合理水平，停止散布涨价信息",
                    "legal_basis": "《价格法》第14条",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "释放囤积商品，恢复正常供应",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家供应链部门"
                },
                {
                    "step": 3,
                    "action": "配合价格监管部门调查，提供进销存记录",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家合规部门"
                }
            ],
            "checklist": [
                "商品价格恢复至合理水平",
                "不再散布涨价信息",
                "库存正常周转",
                "进销存记录完整"
            ],
            "penalty_range": "10000-300000元"
        },
        "其他价格违法": {
            "steps": [
                {
                    "step": 1,
                    "action": "根据具体违规情况，立即停止违规行为",
                    "legal_basis": "《价格法》",
                    "priority": "high",
                    "responsible_party": "商家运营团队"
                },
                {
                    "step": 2,
                    "action": "咨询法务部门或价格监管部门，确认合规要求",
                    "legal_basis": "",
                    "priority": "high",
                    "responsible_party": "商家法务部门"
                },
                {
                    "step": 3,
                    "action": "建立价格合规自查机制，定期审核",
                    "legal_basis": "",
                    "priority": "medium",
                    "responsible_party": "商家合规部门"
                }
            ],
            "checklist": [
                "停止违规行为",
                "咨询专业意见",
                "建立合规机制",
                "加强员工培训"
            ],
            "penalty_range": "视具体情况而定"
        }
    }

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        """
        初始化整改建议生成器

        Args:
            config_path: 配置文件路径（用于LLM模式）
        """
        self.config_path = config_path
        self.client = None  # 延迟加载，仅在详细模式时初始化

    def generate_remediation(self, query: str,
                            reasoning_result: Dict[str, Any],
                            graded_docs: Dict[str, Any] = None,
                            mode: str = "fast",
                            audience: str = "merchant") -> Dict[str, Any]:
        """
        生成整改建议

        Args:
            query: 原始案例查询
            reasoning_result: 推理引擎的输出结果
            graded_docs: Grader评分后的文档（可选）
            mode: 生成模式 ("fast" - 规则模板, "detailed" - LLM生成)
            audience: consumer | regulator | merchant，决定建议视角

        Returns:
            整改建议字典
        """
        aud = normalize_audience(audience)

        # 如果不是违规，直接返回（按受众说明）
        if not reasoning_result.get("is_violation", False):
            return build_compliant_remediation(aud)

        # 提取违规类型
        violation_type = reasoning_result.get("violation_type", "其他")

        # 消费者 / 监管：规则化受众建议（不走商家整改模板与商家向 LLM）
        if aud == "consumer":
            return build_consumer_violation_advice(violation_type, reasoning_result)
        if aud == "regulator":
            return build_regulator_violation_advice(violation_type, reasoning_result)

        # 商家：原快速 / 详细（LLM）路径
        if mode == "fast":
            return self._rule_based_remediation(violation_type, reasoning_result)

        return self._llm_based_remediation(query, reasoning_result, graded_docs)

    def _rule_based_remediation(self, violation_type: str,
                                reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于规则模板生成整改建议（快速模式，0 tokens）

        Args:
            violation_type: 违规类型
            reasoning_result: 推理结果

        Returns:
            整改建议字典
        """
        # 获取模板（兼容旧类型名称）
        template = self.REMEDIATION_TEMPLATES.get(
            violation_type,
            self.REMEDIATION_TEMPLATES.get("其他价格违法", self.REMEDIATION_TEMPLATES["其他价格违法"])
        )

        # 提取法律依据
        legal_basis = reasoning_result.get("legal_basis", "")

        # 如果有明确的法律依据，更新步骤中的legal_basis
        if legal_basis:
            for step in template["steps"]:
                if not step["legal_basis"]:
                    step["legal_basis"] = legal_basis

        return {
            "has_violation": True,
            "audience": "merchant",
            "panel_title": "整改建议",
            "violation_type": violation_type,
            "remediation_steps": template["steps"],
            "compliance_checklist": template["checklist"],
            "estimated_penalty_range": template["penalty_range"],
            "prevention_tips": self._get_prevention_tips(violation_type),
            "generation_mode": "rule_based"
        }

    def _llm_based_remediation(self, query: str,
                               reasoning_result: Dict[str, Any],
                               graded_docs: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于LLM生成整改建议（详细模式，+500 tokens）

        Args:
            query: 原始查询
            reasoning_result: 推理结果
            graded_docs: 评分后的文档

        Returns:
            整改建议字典
        """
        # 延迟初始化MaaS客户端
        if self.client is None:
            self.client = MaaSClient(self.config_path)

        # 构建Prompt
        system_prompt = """你是一名价格合规整改顾问，专门为经营者（商家）提供针对具体案情的整改建议。

**核心要求**：整改建议必须紧密结合本案的具体事实，不能是泛化的模板建议。每一项整改动作都要指向案例中的具体问题。

输出JSON格式，包含以下字段：
- remediation_steps: 整改步骤列表（3-5步），每步必须引用案情中的具体事实
  - step: 步骤编号
  - action: 针对本案具体事实的整改动作（不能是泛化建议）
  - legal_basis: 法律依据
  - priority: 优先级（high/medium/low）
  - responsible_party: 责任主体
- compliance_checklist: 针对本案的合规检查清单（3-5项）
- estimated_penalty_range: 预估处罚范围
- prevention_tips: 预防措施（2-3条）

请确保输出是有效的JSON格式。"""

        violation_type = reasoning_result.get("violation_type", "未知")
        legal_basis = reasoning_result.get("legal_basis", "")
        reasoning_chain = reasoning_result.get("reasoning_chain", [])
        cited_articles = reasoning_result.get("cited_articles", [])
        cited_str = '; '.join(f"《{a.get('law', '')}》{a.get('article', '')}" for a in cited_articles) if cited_articles else legal_basis

        user_prompt = f"""请为以下违规案例生成**针对本案具体事实**的整改建议：

【案例描述】
{query}

【违规类型】
{violation_type}

【适用法条】
{cited_str}

【违规事实要点】
{' '.join(reasoning_chain[:3]) if reasoning_chain else '无'}

**要求**：整改动作必须具体到本案（如涉及的商品名称、价格金额、平台等），不要输出"立即停止违规行为"这类泛化建议。

请输出JSON格式的整改建议。"""

        # 调用LLM
        api_response = self.client.call_model(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_key='qwen-8b'
        )

        if api_response is None:
            # API调用失败，回退到规则模板
            print("[Warning] LLM remediation failed, falling back to rule-based mode")
            return self._rule_based_remediation(violation_type, reasoning_result)

        # 解析响应
        response_text = self.client.extract_response_text(api_response)

        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            remediation = json.loads(json_str)

            # 补充字段
            remediation["has_violation"] = True
            remediation["violation_type"] = violation_type
            remediation["audience"] = "merchant"
            remediation["panel_title"] = "整改建议"
            remediation["generation_mode"] = "llm_based"

            return remediation

        except Exception as e:
            print(f"[Warning] Failed to parse LLM response: {e}, falling back to rule-based mode")
            return self._rule_based_remediation(violation_type, reasoning_result)

    def _get_prevention_tips(self, violation_type: str) -> List[str]:
        """
        获取预防措施提示

        Args:
            violation_type: 违规类型

        Returns:
            预防措施列表
        """
        tips_map = {
            "不明码标价": [
                "建立价格信息审核checklist",
                "确保规格、单位、有效期等要素完整",
                "加强上架前的合规性审核"
            ],
            "政府定价违规": [
                "建立政府定价跟踪机制",
                "定期核查最新政府定价文件",
                "收费标准变更需经合规审批"
            ],
            "标价外加价": [
                "将所有收费项目纳入标价体系",
                "建立收费项目清单并定期审核",
                "确保标价与实收金额一致"
            ],
            "误导性价格标示": [
                "建立价格档案管理制度，保留历史交易记录",
                "定期审核促销活动的原价标注依据",
                "培训运营人员了解价格法相关规定"
            ],
            "变相提高价格": [
                "建立商品质量与标注一致性检查机制",
                "定期校准计量器具",
                "加强商品等级标注审核"
            ],
            "哄抬价格": [
                "建立价格异常波动预警机制",
                "保持正常库存周转",
                "不散布未经核实的涨价信息"
            ],
        }
        default_tips = [
            "建立价格合规自查机制",
            "定期培训员工价格法知识",
            "咨询专业法务意见"
        ]

        return tips_map.get(violation_type, default_tips)


if __name__ == "__main__":
    # 测试整改建议生成器（无需MaaS客户端，仅测试规则模板）
    import sys
    import os
    # 添加项目根目录到Python路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    sys.path.insert(0, project_root)

    advisor = RemediationAdvisor()

    # 测试案例
    test_reasoning_result = {
        "is_violation": True,
        "violation_type": "虚构原价",
        "legal_basis": "《禁止价格欺诈行为规定》第7条",
        "confidence": 0.95,
        "reasoning_chain": [
            "步骤1: 提取案例关键事实 - 商家标注划线价3000元，实际销售价198元",
            "步骤2: 检查历史数据 - 前7日内无成交记录",
            "步骤3: 匹配法律条款 - 根据《禁止价格欺诈规定》第7条，禁止虚构原价"
        ]
    }

    # 快速模式
    print("=== 快速模式（规则模板）===")
    result_fast = advisor.generate_remediation(
        query="某酒店在携程标注划线价3000元，实际预订价198元，无前7日成交记录",
        reasoning_result=test_reasoning_result,
        mode="fast"
    )

    print(f"违规类型: {result_fast['violation_type']}")
    print(f"整改步骤数量: {len(result_fast['remediation_steps'])}")
    print("\n整改步骤:")
    for step in result_fast['remediation_steps']:
        print(f"  {step['step']}. [{step['priority'].upper()}] {step['action']}")
        print(f"     责任方: {step['responsible_party']}")

    print("\n合规检查清单:")
    for item in result_fast['compliance_checklist']:
        print(f"  - {item}")

    print(f"\n预估处罚范围: {result_fast['estimated_penalty_range']}")

    print("\n预防措施:")
    for tip in result_fast['prevention_tips']:
        print(f"  - {tip}")
