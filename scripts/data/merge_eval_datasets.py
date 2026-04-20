#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集合并脚本
合并多个eval格式的JSONL文件，并去重
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import Counter


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    加载JSONL文件

    Args:
        file_path: 文件路径

    Returns:
        案例列表
    """
    cases = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误 ({file_path}): {e}")
                    continue
    return cases


def deduplicate_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    去重（基于user_message内容）

    Args:
        cases: 案例列表

    Returns:
        去重后的案例列表
    """
    seen_content: Set[str] = set()
    unique_cases = []

    for case in cases:
        try:
            # 提取user消息作为去重依据
            user_message = case["messages"][1]["content"]

            # 简化内容作为指纹（去除空白符）
            fingerprint = "".join(user_message.split())

            if fingerprint not in seen_content:
                seen_content.add(fingerprint)
                unique_cases.append(case)
            else:
                print(f"[去重] 移除重复案例: {case['meta']['case_id']}")
        except (KeyError, IndexError) as e:
            print(f"[警告] 案例格式错误，跳过: {e}")
            continue

    return unique_cases


def reassign_case_ids(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    重新分配连续的case_id

    Args:
        cases: 案例列表

    Returns:
        重新分配ID后的案例列表
    """
    for idx, case in enumerate(cases, 1):
        case["meta"]["case_id"] = f"eval_{idx:03d}"

    return cases


def print_statistics(cases: List[Dict[str, Any]]):
    """
    打印数据集统计信息

    Args:
        cases: 案例列表
    """
    print(f"\n=== 数据集统计 ===")
    print(f"总数: {len(cases)}")

    # 违规/合规分布
    violation_count = sum(1 for c in cases if c["meta"]["is_violation"])
    compliance_count = len(cases) - violation_count
    print(f"\n违规/合规分布:")
    print(f"  违规: {violation_count} ({violation_count/len(cases)*100:.1f}%)")
    print(f"  合规: {compliance_count} ({compliance_count/len(cases)*100:.1f}%)")

    # 违规类型分布
    violation_types = Counter()
    for c in cases:
        if c["meta"]["is_violation"]:
            violation_types[c["meta"]["violation_type"]] += 1

    print(f"\n违规类型分布（仅违规案例）:")
    for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
        print(f"  {vtype}: {count} ({count/violation_count*100:.1f}%)")

    # 合规类型分布
    compliance_types = Counter()
    for c in cases:
        if not c["meta"]["is_violation"]:
            ctype = c["meta"].get("compliance_type", "未知")
            compliance_types[ctype] += 1

    if compliance_types:
        print(f"\n合规类型分布（原违规类型）:")
        for ctype, count in sorted(compliance_types.items(), key=lambda x: -x[1]):
            print(f"  {ctype}: {count}")

    # 复杂度分布
    complexity_counts = Counter(c["meta"]["complexity"] for c in cases)
    print(f"\n复杂度分布:")
    for comp in ["simple", "medium", "complex"]:
        count = complexity_counts.get(comp, 0)
        print(f"  {comp}: {count} ({count/len(cases)*100:.1f}%)")

    # 平台分布（Top 10）
    platform_counts = Counter(c["meta"]["platform"] for c in cases)
    print(f"\n平台分布（Top 10）:")
    for platform, count in platform_counts.most_common(10):
        print(f"  {platform}: {count}")


def main():
    parser = argparse.ArgumentParser(description="合并多个eval数据集")
    parser.add_argument(
        "--inputs",
        nargs='+',
        required=True,
        help="输入的JSONL文件路径（空格分隔）"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出的JSONL文件路径"
    )
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        help="是否去重"
    )
    parser.add_argument(
        "--reassign-ids",
        action="store_true",
        default=True,
        help="是否重新分配case_id（默认True）"
    )

    args = parser.parse_args()

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)

    print(f"输入文件: {', '.join(args.inputs)}")
    print(f"输出文件: {args.output}")
    print(f"去重: {args.deduplicate}")
    print(f"重新分配ID: {args.reassign_ids}")
    print()

    # 加载所有输入文件
    all_cases = []
    for input_file in args.inputs:
        cases = load_jsonl(input_file)
        print(f"加载 {input_file}: {len(cases)} 条")
        all_cases.extend(cases)

    print(f"\n合并前总数: {len(all_cases)}")

    # 去重
    if args.deduplicate:
        all_cases = deduplicate_cases(all_cases)
        print(f"去重后总数: {len(all_cases)}")

    # 重新分配case_id
    if args.reassign_ids:
        all_cases = reassign_case_ids(all_cases)
        print(f"重新分配了case_id (eval_001 ~ eval_{len(all_cases):03d})")

    # 打印统计
    print_statistics(all_cases)

    # 保存
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"\n保存到: {output_path}")
    print(f"完成！合并了 {len(all_cases)} 条案例")


if __name__ == "__main__":
    main()
