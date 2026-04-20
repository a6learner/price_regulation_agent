#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合规案例生成脚本
基于违规案例通过LLM生成合规变体
"""
import json
import argparse
import random
import time
from pathlib import Path
from typing import Dict, Any, List
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.baseline.maas_client import MaaSClient


# 系统提示词
SYSTEM_PROMPT = "你是一名电商平台价格合规审查助手,熟悉《价格法》《明码标价和禁止价格欺诈规定》及相关配套规章。你需要根据给定的案件事实,做出法律分析并给出是否违规的结论和依据。"


def generate_compliance_prompt(violation_case: Dict[str, Any]) -> str:
    """
    生成合规案例的prompt

    Args:
        violation_case: 违规案例（eval格式）

    Returns:
        生成prompt
    """
    meta = violation_case["meta"]
    violation_type = meta["violation_type"]
    platform = meta["platform"]
    scenario = meta["scenario"]

    # 原违规案例的用户消息
    user_message = violation_case["messages"][1]["content"]

    # 根据违规类型定制转换策略
    type_to_compliance = {
        "虚构原价": "请将上述违规案例改写为合规版本。要求：原价标注有真实的历史成交记录支撑（例如：提供上架前7日以该价格成交的记录），价格比较真实可信。",
        "虚假折扣": "请将上述违规案例改写为合规版本。要求：折扣比例与实际优惠一致，折扣计算基准真实准确，无夸大折扣幅度的行为。",
        "价格误导": "请将上述违规案例改写为合规版本。要求：价格标注清晰准确，不使用误导性表述，确保消费者能够正确理解真实价格。",
        "要素缺失": "请将上述违规案例改写为合规版本。要求：在醒目位置完整标注商品价格及必要要素（原价、活动价、活动期限、优惠条件等）。",
        "其他": "请将上述违规案例改写为合规版本。要求：经营者诚信标注价格，符合价格法律法规要求，不存在价格违法行为。",
    }

    conversion_instruction = type_to_compliance.get(violation_type, type_to_compliance["其他"])

    prompt = f"""你的任务是基于一个价格违规案例，生成一个合规的变体案例。

原始违规案例：
{user_message}

{conversion_instruction}

**输出格式要求**（必须严格遵守）：
请按照以下JSON格式输出（不要有任何其他文字）：
{{
    "user_message": "某监管部门查处了...（完整的案例描述）",
    "assistant_message": "事实要点：\\n- ...\\n\\n合规分析：\\n...\\n\\n结论：...\\n\\n整改建议：\\n...",
    "scenario": "{scenario}"
}}

**重要说明**：
1. user_message：改写后的合规案例描述，保持与原案例相似的结构，但修改关键事实使其不构成违规
2. assistant_message：必须包含四个部分：
   - 事实要点（列举3-4条关键事实）
   - 合规分析（说明为何该行为合规）
   - 结论（明确指出"不违规"或"合规"，并说明符合的法律规定）
   - 整改建议（可以是"无需整改"或"建议继续保持"）
3. scenario：保持与原案例相同的场景"{scenario}"

请确保输出是有效的JSON格式。
"""

    return prompt


def parse_llm_response(response: str) -> Dict[str, str]:
    """
    解析LLM返回的JSON

    Args:
        response: LLM响应

    Returns:
        解析后的字典
    """
    # 尝试提取JSON
    response = response.strip()

    # 移除可能的markdown代码块标记
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]

    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    try:
        data = json.loads(response)
        return data
    except json.JSONDecodeError as e:
        print(f"[警告] JSON解析失败: {e}")
        print(f"原始响应: {response[:200]}...")
        return None


def create_compliance_case(
    violation_case: Dict[str, Any],
    llm_response: Dict[str, str],
    case_id: str
) -> Dict[str, Any]:
    """
    创建合规案例

    Args:
        violation_case: 原违规案例
        llm_response: LLM生成的响应
        case_id: 新case_id

    Returns:
        合规案例（eval格式）
    """
    meta = violation_case["meta"]

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": llm_response["user_message"]},
            {"role": "assistant", "content": llm_response["assistant_message"]},
        ],
        "meta": {
            "case_id": case_id,
            "is_violation": False,
            "violation_type": "无违规",
            "compliance_type": meta["violation_type"],  # 记录原违规类型作为合规类型
            "platform": meta["platform"],
            "scenario": llm_response.get("scenario", meta["scenario"]),
            "complexity": meta["complexity"],
        }
    }


def main():
    parser = argparse.ArgumentParser(description="生成合规案例变体")
    parser.add_argument(
        "--input",
        required=True,
        help="输入的违规案例JSONL文件"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出的合规案例JSONL文件"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="生成数量"
    )
    parser.add_argument(
        "--model",
        default="qwen-8b",
        help="使用的模型（默认qwen-8b）"
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=560,
        help="起始case_id编号（默认560，接续violations_new_395的eval_559）"
    )
    parser.add_argument(
        "--request-interval",
        type=float,
        default=1.0,
        help="请求间隔（秒）"
    )

    args = parser.parse_args()

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)

    print(f"输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"生成数量: {args.count}")
    print(f"使用模型: {args.model}")
    print(f"起始编号: eval_{args.start_id:03d}")
    print()

    # 初始化客户端
    config_path = "configs/model_config.yaml"
    client = MaaSClient(config_path=config_path)

    # 读取违规案例
    violations = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    violations.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    continue

    print(f"读取了 {len(violations)} 条违规案例")

    # 随机采样
    if len(violations) > args.count:
        sampled = random.sample(violations, args.count)
    else:
        sampled = violations

    print(f"采样了 {len(sampled)} 条用于生成")
    print()

    # 批量生成
    compliance_cases = []
    current_id = args.start_id
    success_count = 0
    fail_count = 0

    for idx, violation_case in enumerate(sampled, 1):
        print(f"[{idx}/{len(sampled)}] 处理 {violation_case['meta']['case_id']}...")

        try:
            # 生成prompt
            prompt = generate_compliance_prompt(violation_case)

            # 调用LLM
            api_response = client.call_model(
                system_prompt="",
                user_prompt=prompt,
                model_key=args.model,
                retry=True
            )

            if not api_response:
                print(f"  [FAIL] API调用失败，跳过")
                fail_count += 1
                continue

            response = client.extract_response_text(api_response)

            # 解析响应
            llm_data = parse_llm_response(response)

            if llm_data and "user_message" in llm_data and "assistant_message" in llm_data:
                # 创建合规案例
                case_id = f"eval_{current_id:03d}"
                compliance_case = create_compliance_case(violation_case, llm_data, case_id)
                compliance_cases.append(compliance_case)
                current_id += 1
                success_count += 1
                print(f"  [OK] 生成成功 -> {case_id}")
            else:
                print(f"  [FAIL] LLM响应格式错误，跳过")
                fail_count += 1

        except Exception as e:
            print(f"  [ERROR] 生成失败: {e}")
            fail_count += 1

        # 请求间隔
        if idx < len(sampled):
            time.sleep(args.request_interval)

    print()
    print(f"=== 生成统计 ===")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"总计: {len(compliance_cases)}")

    # 统计分布
    compliance_type_counts = {}
    platform_counts = {}
    complexity_counts = {}
    scenario_counts = {}

    for case in compliance_cases:
        meta = case["meta"]
        ctype = meta["compliance_type"]
        compliance_type_counts[ctype] = compliance_type_counts.get(ctype, 0) + 1
        platform_counts[meta["platform"]] = platform_counts.get(meta["platform"], 0) + 1
        complexity_counts[meta["complexity"]] = complexity_counts.get(meta["complexity"], 0) + 1
        scenario_counts[meta["scenario"]] = scenario_counts.get(meta["scenario"], 0) + 1

    print(f"\n合规类型分布（原违规类型）:")
    for ctype, count in sorted(compliance_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {ctype}: {count} ({count/len(compliance_cases)*100:.1f}%)")

    print(f"\n平台分布:")
    for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  {platform}: {count}")

    print(f"\n复杂度分布:")
    for comp, count in sorted(complexity_counts.items()):
        print(f"  {comp}: {count}")

    # 保存
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for case in compliance_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"\n保存到: {output_path}")
    print(f"完成！生成了 {len(compliance_cases)} 条合规案例")


if __name__ == "__main__":
    main()
