#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从133个PDF提取的原始案例中识别多场景，生成更多独立评估案例

核心策略：
1. 识别多商品违规（商品A虚构原价 + 商品B虚假折扣）
2. 识别复合违规（同一商品：虚构原价 + 虚假折扣）
3. 识别多时间段违规（Q1虚构原价 + Q2要素缺失）

输入：data/sft/processed/extracted_cases.jsonl（133个原始案例）
输出：data/eval/eval_from_pdfs.jsonl（150-180个评估案例）
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
import uuid

# 添加src到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from baseline.maas_client import MaaSClient


# 系统提示词
SYSTEM_PROMPT = "你是一名电商平台价格合规审查助手，熟悉《价格法》《明码标价和禁止价格欺诈规定》及相关配套规章。你需要根据给定的案件事实，做出法律分析并给出是否违规的结论和依据。"


class PDFCaseExpander:
    """从PDF提取案例的多场景扩展器"""

    def __init__(self, llm_client: MaaSClient):
        self.llm_client = llm_client
        self.case_id_counter = 200  # 从eval_200开始，避免与现有159案例冲突

    def analyze_multi_scenarios(self, extracted_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析一个PDF案例是否包含多个可独立提取的场景

        Args:
            extracted_case: 从extracted_cases.jsonl读取的原始案例

        Returns:
            场景列表，每个场景包含：
            {
                "scenario_type": "multi_product" | "composite" | "multi_period",
                "scenario_description": "...",
                "violation_type": "...",
                "key_facts": [...]
            }
        """
        violation_description = extracted_case.get('violation_description', '')
        full_text = extracted_case.get('full_text', '')

        # 使用LLM分析多场景
        analysis_prompt = f"""
请分析以下价格违法案件，识别是否包含多个可独立提取的违规场景。

# 案件违规描述
{violation_description[:1000]}

# 分析任务
请识别以下三种多场景情况：

1. **多商品违规**：同一商家销售多个不同商品，每个商品有不同的违规行为
   示例：商品A虚构原价，商品B虚假折扣

2. **复合违规**：同一商品/活动存在多种违规行为组合
   示例：既虚构原价，又虚假折扣

3. **多时间段违规**：不同时间段有不同的违规行为
   示例：1-3月虚构原价，4-6月要素缺失

# 输出格式（JSON）
{{
  "has_multi_scenarios": true/false,
  "scenarios": [
    {{
      "scenario_type": "multi_product" | "composite" | "multi_period",
      "violation_type": "虚构原价" | "虚假折扣" | "价格误导" | "要素缺失" | "其他",
      "scenario_description": "简要描述该场景的违规行为（50字内）",
      "key_facts": ["关键事实1", "关键事实2", "关键事实3"]
    }}
  ]
}}

如果只有一个主要违规场景，返回：
{{
  "has_multi_scenarios": false,
  "scenarios": []
}}

请直接输出JSON，不要包含其他文字。
"""

        try:
            response = self.llm_client.call_api(
                user_prompt=analysis_prompt,
                system_prompt="你是一个专业的法律文书分析助手，擅长识别复杂案件中的多个违规场景。",
                max_tokens=1500,
                temperature=0.3
            )

            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get('scenarios', []) if result.get('has_multi_scenarios') else []
            else:
                return []

        except Exception as e:
            print(f"[警告] LLM分析失败: {e}")
            return []

    def generate_eval_case_from_scenario(
        self,
        original_case: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据识别出的场景生成独立的评估案例

        Args:
            original_case: 原始PDF提取案例
            scenario: 分析出的场景信息

        Returns:
            eval_159.jsonl格式的评估案例
        """
        case_id = f"eval_{str(self.case_id_counter).zfill(3)}"
        self.case_id_counter += 1

        # 构建案例描述
        case_description_prompt = f"""
基于以下场景生成一个完整的电商价格违规案例描述。

# 场景信息
- 违规类型：{scenario.get('violation_type')}
- 场景描述：{scenario.get('scenario_description')}
- 关键事实：{', '.join(scenario.get('key_facts', []))}

# 原始案例背景
- 地区：{original_case.get('region', '某地')}
- 平台：{original_case.get('platform', '某电商平台')}
- 商家：{original_case.get('company_name', '某商家')}

# 要求
生成一个符合eval_159.jsonl格式的案例描述（user字段内容），包括：
1. 开头：某监管部门查处了一起电商价格违法案件
2. 平台信息
3. 案情概述（200-300字）
4. 关键事实总结
5. 结尾：请根据上述事实，从价格合规的角度分析该经营行为是否违规，并给出依据和结论。

请直接输出案例描述文本，不要包含JSON或其他格式。
"""

        try:
            case_description = self.llm_client.call_api(
                user_prompt=case_description_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=800,
                temperature=0.6
            )

            # 生成分析回复（assistant字段内容）
            analysis_prompt = f"""
{case_description}
"""

            analysis_response = self.llm_client.call_api(
                user_prompt=analysis_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=1200,
                temperature=0.5
            )

            # 提取platform（如果LLM生成的描述中包含）
            platform_mapping = {
                '淘宝': '淘宝', '天猫': '天猫', '京东': '京东',
                '拼多多': '拼多多', '美团': '美团', '抖音': '抖音',
                '快手': '快手', '小红书': '小红书'
            }
            detected_platform = None
            for keyword, platform_name in platform_mapping.items():
                if keyword in case_description:
                    detected_platform = platform_name
                    break

            # 构建完整案例
            eval_case = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": case_description},
                    {"role": "assistant", "content": analysis_response}
                ],
                "meta": {
                    "case_id": case_id,
                    "is_violation": True,  # 从PDF提取的都是违规案例
                    "violation_type": scenario.get('violation_type'),
                    "platform": detected_platform or original_case.get('platform', '淘宝'),
                    "scenario": self._infer_scenario(scenario.get('scenario_description', '')),
                    "complexity": "medium",  # 从PDF提取的一般为medium
                    "compliance_type": None,
                    "source": f"expanded_from_{original_case.get('case_id', 'unknown')}"
                }
            }

            return eval_case

        except Exception as e:
            print(f"[错误] 生成评估案例失败: {e}")
            return None

    def _infer_scenario(self, scenario_description: str) -> str:
        """从场景描述推断促销场景类型"""
        scenario_keywords = {
            "限时折扣": ["限时", "特惠", "折扣", "降价"],
            "满减活动": ["满减", "满", "减"],
            "会员专享": ["会员", "VIP"],
            "拼团优惠": ["拼团", "团购"],
            "秒杀活动": ["秒杀", "抢购"],
            "优惠券": ["优惠券", "券", "代金"],
            "大促活动": ["618", "双11", "双12", "大促"]
        }

        for scenario, keywords in scenario_keywords.items():
            if any(kw in scenario_description for kw in keywords):
                return scenario

        return "限时折扣"  # 默认

    def expand_dataset(
        self,
        input_file: Path,
        output_file: Path,
        max_cases_per_pdf: int = 3,
        limit: int = None
    ) -> None:
        """
        批量扩展数据集

        Args:
            input_file: extracted_cases.jsonl文件路径
            output_file: 输出文件路径
            max_cases_per_pdf: 每个PDF最多提取的案例数
            limit: 限制处理的PDF数量（用于测试）
        """
        print(f"[INFO] 开始从PDF提取多场景案例...")
        print(f"[INFO] 输入文件: {input_file}")
        print(f"[INFO] 输出文件: {output_file}")
        print(f"[INFO] 每个PDF最多提取: {max_cases_per_pdf}个场景")

        # 读取原始案例
        original_cases = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    original_cases.append(json.loads(line))

        if limit:
            original_cases = original_cases[:limit]
            print(f"[INFO] 测试模式：仅处理前{limit}个PDF")

        print(f"[INFO] 读取到{len(original_cases)}个原始PDF案例")

        # 扩展案例
        expanded_cases = []
        single_scenario_count = 0
        multi_scenario_count = 0

        for i, original_case in enumerate(original_cases, 1):
            print(f"\n[{i}/{len(original_cases)}] 处理: {original_case.get('case_id', 'unknown')}")

            # 分析多场景
            scenarios = self.analyze_multi_scenarios(original_case)

            if not scenarios:
                single_scenario_count += 1
                print(f"  - 单一场景，跳过")
                continue

            print(f"  + 识别到{len(scenarios)}个场景")
            multi_scenario_count += 1

            # 限制每个PDF的案例数
            scenarios = scenarios[:max_cases_per_pdf]

            # 为每个场景生成评估案例
            for j, scenario in enumerate(scenarios, 1):
                print(f"    [{j}/{len(scenarios)}] 生成场景: {scenario.get('violation_type')} - {scenario.get('scenario_type')}")

                eval_case = self.generate_eval_case_from_scenario(original_case, scenario)

                if eval_case:
                    expanded_cases.append(eval_case)
                    print(f"      OK 生成成功: {eval_case['meta']['case_id']}")
                else:
                    print(f"      FAIL 生成失败")

        # 保存结果
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for case in expanded_cases:
                f.write(json.dumps(case, ensure_ascii=False) + '\n')

        # 统计报告
        print(f"\n{'='*60}")
        print(f"[完成] 数据扩展完成")
        print(f"{'='*60}")
        print(f"处理PDF数量: {len(original_cases)}")
        print(f"  - 单一场景: {single_scenario_count} ({single_scenario_count/len(original_cases)*100:.1f}%)")
        print(f"  - 多场景: {multi_scenario_count} ({multi_scenario_count/len(original_cases)*100:.1f}%)")
        print(f"生成评估案例: {len(expanded_cases)}个")
        print(f"平均每个PDF: {len(expanded_cases)/len(original_cases):.2f}个案例")
        print(f"输出文件: {output_file}")
        print(f"{'='*60}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='从PDF提取多场景案例')
    parser.add_argument('--input', type=str,
                       default='data/sft/processed/extracted_cases.jsonl',
                       help='输入文件路径（extracted_cases.jsonl）')
    parser.add_argument('--output', type=str,
                       default='data/eval/eval_from_pdfs.jsonl',
                       help='输出文件路径')
    parser.add_argument('--max-cases-per-pdf', type=int, default=3,
                       help='每个PDF最多提取的案例数（默认3）')
    parser.add_argument('--limit', type=int, default=None,
                       help='限制处理的PDF数量（用于测试，默认全部）')
    parser.add_argument('--model', type=str, default='qwen-8b',
                       help='使用的LLM模型（默认qwen-8b，节省成本）')

    args = parser.parse_args()

    # 初始化LLM客户端
    config_file = Path(__file__).parent.parent / 'configs' / 'model_config.yaml'
    llm_client = MaaSClient(config_file=str(config_file), model_key=args.model)

    # 创建扩展器
    expander = PDFCaseExpander(llm_client)

    # 执行扩展
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent.parent / input_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent.parent / output_path

    expander.expand_dataset(
        input_file=input_path,
        output_file=output_path,
        max_cases_per_pdf=args.max_cases_per_pdf,
        limit=args.limit
    )


if __name__ == '__main__':
    main()
