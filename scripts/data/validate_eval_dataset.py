#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估数据集质量验证脚本
检查数据集格式、完整性、平衡性等
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter


STANDARD_VIOLATION_TYPES = ["虚构原价", "虚假折扣", "价格误导", "要素缺失", "其他", "无违规", "不违规", "无"]


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """加载JSONL文件"""
    cases = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Line {line_num}: JSON解析错误: {e}")
    return cases


def validate_format(cases: List[Dict[str, Any]]) -> bool:
    """
    验证格式正确性

    Returns:
        是否通过验证
    """
    print("\n[检查1] 格式正确性")
    errors = []

    for idx, case in enumerate(cases, 1):
        case_id = case.get("meta", {}).get("case_id", f"unknown_{idx}")

        # 检查messages字段
        if "messages" not in case:
            errors.append(f"{case_id}: 缺少messages字段")
            continue

        messages = case["messages"]
        if not isinstance(messages, list) or len(messages) != 3:
            errors.append(f"{case_id}: messages应为包含3个元素的列表")
            continue

        # 检查messages内容
        if messages[0].get("role") != "system":
            errors.append(f"{case_id}: messages[0]角色应为system")
        if messages[1].get("role") != "user":
            errors.append(f"{case_id}: messages[1]角色应为user")
        if messages[2].get("role") != "assistant":
            errors.append(f"{case_id}: messages[2]角色应为assistant")

        # 检查meta字段
        if "meta" not in case:
            errors.append(f"{case_id}: 缺少meta字段")
            continue

        meta = case["meta"]
        required_meta_fields = ["case_id", "is_violation", "violation_type", "platform", "scenario", "complexity"]
        for field in required_meta_fields:
            if field not in meta:
                errors.append(f"{case_id}: meta缺少{field}字段")

    if errors:
        print(f"  [FAIL] 发现 {len(errors)} 个错误:")
        for error in errors[:10]:  # 只显示前10个
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 还有 {len(errors)-10} 个错误")
        return False
    else:
        print(f"  [OK] 所有 {len(cases)} 个案例格式正确")
        return True


def validate_content(cases: List[Dict[str, Any]]) -> bool:
    """
    验证内容完整性

    Returns:
        是否通过验证
    """
    print("\n[检查2] 内容完整性")
    errors = []

    for case in cases:
        case_id = case["meta"]["case_id"]
        assistant_msg = case["messages"][2]["content"]

        # 检查推理链
        required_sections = ["事实要点", "分析", "结论"]
        for section in required_sections:
            if section not in assistant_msg:
                errors.append(f"{case_id}: assistant消息缺少'{section}'部分")

        # 检查违规类型
        violation_type = case["meta"]["violation_type"]
        if violation_type not in STANDARD_VIOLATION_TYPES:
            errors.append(f"{case_id}: violation_type '{violation_type}' 不在标准类型列表中")

    if errors:
        print(f"  [WARNING] 发现 {len(errors)} 个内容问题:")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 还有 {len(errors)-10} 个问题")
        return False
    else:
        print(f"  [OK] 所有案例内容完整")
        return True


def validate_uniqueness(cases: List[Dict[str, Any]]) -> bool:
    """
    验证case_id唯一性和连续性

    Returns:
        是否通过验证
    """
    print("\n[检查3] case_id唯一性和连续性")
    case_ids = [case["meta"]["case_id"] for case in cases]

    # 检查唯一性
    duplicates = [id for id, count in Counter(case_ids).items() if count > 1]
    if duplicates:
        print(f"  [FAIL] 发现重复的case_id: {duplicates[:10]}")
        return False

    # 检查连续性
    expected_ids = [f"eval_{i:03d}" for i in range(1, len(cases) + 1)]
    if case_ids != expected_ids:
        print(f"  [WARNING] case_id不连续或格式不符")
        print(f"    期望: eval_001 ~ eval_{len(cases):03d}")
        print(f"    实际: {case_ids[0]} ~ {case_ids[-1]}")
        return False

    print(f"  [OK] 所有case_id唯一且连续 (eval_001 ~ eval_{len(cases):03d})")
    return True


def validate_balance(cases: List[Dict[str, Any]]) -> bool:
    """
    验证数据集平衡性

    Returns:
        是否通过验证
    """
    print("\n[检查4] 数据集平衡性")

    # 违规/合规比例
    violation_count = sum(1 for c in cases if c["meta"]["is_violation"])
    compliance_count = len(cases) - violation_count
    violation_ratio = violation_count / len(cases)

    print(f"  违规案例: {violation_count} ({violation_ratio*100:.1f}%)")
    print(f"  合规案例: {compliance_count} ({(1-violation_ratio)*100:.1f}%)")

    if violation_ratio < 0.6 or violation_ratio > 0.8:
        print(f"  [WARNING] 违规/合规比例不在60-80%范围内")
        return False

    # 违规类型分布
    violation_types = Counter()
    for c in cases:
        if c["meta"]["is_violation"]:
            violation_types[c["meta"]["violation_type"]] += 1

    print(f"\n  违规类型分布:")
    min_count = min(violation_types.values()) if violation_types else 0
    max_count = max(violation_types.values()) if violation_types else 0
    for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
        print(f"    {vtype}: {count} ({count/violation_count*100:.1f}%)")

    # 检查是否有类型过少
    threshold = violation_count * 0.05  # 至少5%
    low_types = {vtype: count for vtype, count in violation_types.items() if count < threshold}
    if low_types:
        print(f"  [WARNING] 以下类型样本过少(<5%):")
        for vtype, count in low_types.items():
            print(f"    {vtype}: {count}")
        return False

    print(f"  [OK] 数据集基本平衡")
    return True


def generate_report(cases: List[Dict[str, Any]], output_path: str):
    """
    生成详细验证报告

    Args:
        cases: 案例列表
        output_path: 报告输出路径
    """
    report = []
    report.append("# 评估数据集验证报告\n")
    report.append(f"**总案例数**: {len(cases)}\n")

    # 违规/合规分布
    violation_count = sum(1 for c in cases if c["meta"]["is_violation"])
    compliance_count = len(cases) - violation_count
    report.append(f"\n## 违规/合规分布\n")
    report.append(f"- 违规: {violation_count} ({violation_count/len(cases)*100:.1f}%)\n")
    report.append(f"- 合规: {compliance_count} ({compliance_count/len(cases)*100:.1f}%)\n")

    # 违规类型分布
    violation_types = Counter()
    for c in cases:
        if c["meta"]["is_violation"]:
            violation_types[c["meta"]["violation_type"]] += 1

    report.append(f"\n## 违规类型分布\n")
    report.append("| 类型 | 数量 | 占比 |\n")
    report.append("|------|------|------|\n")
    for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
        report.append(f"| {vtype} | {count} | {count/violation_count*100:.1f}% |\n")

    # 复杂度分布
    complexity_counts = Counter(c["meta"]["complexity"] for c in cases)
    report.append(f"\n## 复杂度分布\n")
    report.append("| 复杂度 | 数量 | 占比 |\n")
    report.append("|--------|------|------|\n")
    for comp in ["simple", "medium", "complex"]:
        count = complexity_counts.get(comp, 0)
        report.append(f"| {comp} | {count} | {count/len(cases)*100:.1f}% |\n")

    # 平台分布
    platform_counts = Counter(c["meta"]["platform"] for c in cases)
    report.append(f"\n## 平台分布（Top 10）\n")
    report.append("| 平台 | 数量 |\n")
    report.append("|------|------|\n")
    for platform, count in platform_counts.most_common(10):
        report.append(f"| {platform} | {count} |\n")

    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(report)

    print(f"\n[报告] 已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="验证评估数据集质量")
    parser.add_argument(
        "--input",
        required=True,
        help="输入的JSONL文件路径"
    )
    parser.add_argument(
        "--check-format",
        action="store_true",
        default=True,
        help="检查格式正确性"
    )
    parser.add_argument(
        "--check-content",
        action="store_true",
        default=True,
        help="检查内容完整性"
    )
    parser.add_argument(
        "--check-uniqueness",
        action="store_true",
        default=True,
        help="检查唯一性"
    )
    parser.add_argument(
        "--check-balance",
        action="store_true",
        default=True,
        help="检查平衡性"
    )
    parser.add_argument(
        "--generate-report",
        type=str,
        help="生成详细报告（指定输出路径）"
    )

    args = parser.parse_args()

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)

    print(f"验证文件: {args.input}")

    # 加载数据
    cases = load_jsonl(args.input)
    print(f"\n加载了 {len(cases)} 个案例")

    # 执行检查
    results = []

    if args.check_format:
        results.append(validate_format(cases))

    if args.check_content:
        results.append(validate_content(cases))

    if args.check_uniqueness:
        results.append(validate_uniqueness(cases))

    if args.check_balance:
        results.append(validate_balance(cases))

    # 总结
    print("\n" + "=" * 50)
    if all(results):
        print("[SUCCESS] 所有检查通过！")
    else:
        failed_count = sum(1 for r in results if not r)
        print(f"[WARNING] {failed_count} 项检查未通过")

    # 生成报告
    if args.generate_report:
        generate_report(cases, args.generate_report)


if __name__ == "__main__":
    main()
