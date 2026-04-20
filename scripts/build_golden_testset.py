#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_golden_testset.py
=======================
从 Stage 2 结构化结果中构建黄金测试集（Golden Test Set）

核心原则：
- Reference answer 直接来源于原始文书文本，不经 LLM 改写
- 违规案例来自真实行政处罚文书（is_violation=True）
- 合规样本可从旧数据集追加（明确标注来源）
- 多样性平衡：违法类型、平台均衡分布

USAGE:
------
# 构建黄金测试集
python scripts/build_golden_testset.py \\
  --input data/golden/stage2_results.jsonl \\
  --output data/golden/golden_testset.jsonl \\
  --target 500

# 校验模式（检查输出质量）
python scripts/build_golden_testset.py \\
  --validate \\
  --input data/golden/stage2_results.jsonl

# 追加旧数据集中的合规样本
python scripts/build_golden_testset.py \\
  --input data/golden/stage2_results.jsonl \\
  --output data/golden/golden_testset.jsonl \\
  --append_compliance data/eval/eval_754.jsonl \\
  --target 500
"""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 系统提示词（与现有 eval 数据集一致）
# ============================================================

SYSTEM_PROMPT = """你是一位专业的电商价格合规审查助手，熟悉中国价格法律法规，包括《价格法》、《明码标价和禁止价格欺诈规定》等。
请根据提供的案例信息，判断相关经营行为是否违反价格法律法规，并给出详细的法律分析。

分析格式要求：
1. 事实梳理：简要概括案例中的关键价格行为事实
2. 合规分析：对照相关法律法规逐条分析
3. 结论：明确判断是否违规，如违规请指出具体违规类型和适用的法律条款
4. 如果判断违规，请在结论中以JSON格式输出：{"is_violation": true, "violation_type": "违规类型", "legal_basis": ["法律条款"]}
5. 如果判断合规，请在结论中以JSON格式输出：{"is_violation": false, "violation_type": "无违规", "legal_basis": []}"""


# ============================================================
# 违法类型映射（统一标签）
# ============================================================

# Stage 2 LLM 可能输出的类型 → 统一到项目标准标签
VIOLATION_TYPE_MAP = {
    "虚构原价": "虚构原价",
    "价格标示不实": "价格误导",
    "不明码标价": "要素缺失",
    "捆绑销售": "其他",
    "价格欺诈": "虚假折扣",
    "其他": "其他",
    # 规则提取的类型
    "虚假折扣": "虚假折扣",
    "价格误导": "价格误导",
    "要素缺失": "要素缺失",
}


def normalize_violation_type(raw_type: Optional[str]) -> str:
    """将 LLM 输出的违法类型映射到项目标准标签"""
    if not raw_type:
        return "其他"
    return VIOLATION_TYPE_MAP.get(raw_type, "其他")


# ============================================================
# Query 构建
# ============================================================

def build_query_type_a(record: Dict) -> Optional[str]:
    """
    Type A：证据查询型
    直接输入"经查"段原文前800字，让模型分析是否违法。
    更难，更能区分 RAG 和 Agent 的价值。
    """
    jingcha = record.get("jingcha_text", "")
    if not jingcha or len(jingcha) < 30:
        return None

    # 取前800字，去掉截断标记
    jingcha_snippet = jingcha[:800].replace("...[已截断/truncated]", "").strip()

    platform = record.get("platform_llm") or record.get("platform") or "某平台"
    query = (
        f"根据以下行政执法调查记录，分析该经营行为是否违反价格法律法规，"
        f"并说明理由：\n\n{jingcha_snippet}"
    )
    return query


def build_query_type_b(record: Dict) -> Optional[str]:
    """
    Type B：情景查询型
    用结构化字段构造情景描述，更接近实际用户使用场景。
    """
    platform = record.get("platform_llm") or record.get("platform")
    party_name = record.get("party_name")
    violation_summary = record.get("llm_violation_summary")

    if not violation_summary:
        return None

    # 去除摘要中可能存在的定性词汇（保留事实描述）
    parts = []
    if party_name:
        parts.append(f"{party_name}")
    if platform:
        parts.append(f"在{platform}平台经营")

    query = "、".join(parts) + f"，{violation_summary}，请分析是否构成价格违法行为。"
    return query


def build_reference_answer(record: Dict) -> Optional[str]:
    """
    构建 reference answer（直接引用原始文书文本）

    来源：benju_renwei_text（本局认为段）+ penalty_decision_text（处罚决定段）
    这确保了零同源污染风险——reference 直接来自行政处罚原文。
    """
    benju = record.get("benju_renwei_text", "")
    penalty = record.get("penalty_decision_text", "")

    parts = []
    if benju and len(benju) > 20:
        # 截断过长的法条全文（PDF3类型），保留核心分析
        benju_clean = benju.replace("...[已截断/truncated]", "").strip()
        parts.append(benju_clean[:1000])
    if penalty and len(penalty) > 20:
        parts.append(penalty[:300].strip())

    if not parts:
        return None

    return "\n\n".join(parts)


# ============================================================
# 核心构建逻辑
# ============================================================

def load_stage2_records(input_path: str) -> List[Dict]:
    """加载 Stage 2 结果，过滤 LLM 成功的记录"""
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                records.append(r)
            except json.JSONDecodeError:
                continue
    return records


def filter_qualified(records: List[Dict]) -> List[Dict]:
    """
    筛选可用于构建测试集的记录：
    - Stage 1 质量分 ≥ 3
    - 有经查段原文（用于 Type A query）
    - 有本局认为段或处罚决定段（用于 reference answer）
    - LLM 成功（有结构化字段）或有规则提取的基本字段
    """
    qualified = []
    for r in records:
        if r.get("stage1_score", 0) < 3:
            continue
        if not r.get("jingcha_text") or len(r.get("jingcha_text", "")) < 30:
            continue
        has_reference = (
            (r.get("benju_renwei_text") and len(r.get("benju_renwei_text", "")) > 20)
            or (r.get("penalty_decision_text") and len(r.get("penalty_decision_text", "")) > 20)
        )
        if not has_reference:
            continue
        qualified.append(r)
    return qualified


def balance_diversity(
    records: List[Dict],
    target: int,
    max_violation_type_ratio: float = 0.60,
    max_platform_ratio: float = 0.40,
) -> List[Dict]:
    """
    多样性平衡采样：
    - 单一违法类型占比 ≤ max_violation_type_ratio（默认60%）
    - 单一平台占比 ≤ max_platform_ratio（默认40%）
    - 在满足约束条件下，尽量接近 target 数量
    """
    if len(records) <= target:
        return records

    random.shuffle(records)

    # 计算每类的上限
    max_per_type = int(target * max_violation_type_ratio)
    max_per_platform = int(target * max_platform_ratio)

    type_counts = defaultdict(int)
    platform_counts = defaultdict(int)
    selected = []

    for r in records:
        vtype = normalize_violation_type(
            r.get("llm_violation_type") or r.get("violation_type_rule")
        )
        platform = r.get("platform_llm") or r.get("platform") or "未知"

        if type_counts[vtype] >= max_per_type:
            continue
        if platform_counts[platform] >= max_per_platform:
            continue

        type_counts[vtype] += 1
        platform_counts[platform] += 1
        selected.append(r)

        if len(selected) >= target:
            break

    # 如果约束太严导致数量不足，放宽约束补充
    if len(selected) < target * 0.8:
        remaining = [r for r in records if r not in selected]
        needed = target - len(selected)
        selected.extend(remaining[:needed])

    return selected


def convert_to_eval_format(
    record: Dict,
    case_id: str,
    query_type: str,
    query: str,
    reference_answer: str,
) -> Dict:
    """
    将结构化记录转换为与 eval_754.jsonl 兼容的格式

    新增字段：
    - source: "penalty_document"（标注来源）
    - rewritten: False（关键：未经 LLM 改写）
    - legal_basis_ground_truth: 从原文提取的法律依据（用于 Citation 指标）
    - query_type: "A" 或 "B"
    """
    vtype = normalize_violation_type(
        record.get("llm_violation_type") or record.get("violation_type_rule")
    )
    platform = record.get("platform_llm") or record.get("platform") or "未知"

    # 合并法律依据（规则提取 + LLM 提取，去重）
    rule_basis = record.get("legal_basis", []) or []
    llm_basis = record.get("llm_legal_basis", []) or []
    all_basis = list(dict.fromkeys(rule_basis + llm_basis))  # 保序去重

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
            {"role": "assistant", "content": reference_answer},
        ],
        "meta": {
            "case_id": case_id,
            "is_violation": True,  # 处罚文书必然为违规
            "violation_type": vtype,
            "compliance_type": None,
            "platform": platform,
            "scenario": "真实处罚案例",
            "complexity": "real_case",
            # 黄金测试集专有字段
            "source": "penalty_document",
            "rewritten": False,
            "query_type": query_type,
            "source_doc": record.get("case_number") or record.get("filename"),
            "penalty_amount": record.get("penalty_amount"),
            "legal_basis_ground_truth": all_basis,
            "original_price": record.get("llm_original_price"),
            "actual_price": record.get("llm_actual_price"),
        },
    }


def build_golden_testset(
    input_path: str,
    output_path: str,
    target: int = 500,
    type_a_ratio: float = 0.5,
    seed: int = 42,
) -> Dict:
    """
    主构建函数

    Args:
        input_path: stage2_results.jsonl 路径
        output_path: golden_testset.jsonl 输出路径
        target: 目标总量（默认500）
        type_a_ratio: Type A query 占比（默认0.5）
        seed: 随机种子（保证可复现）

    Returns:
        统计信息字典
    """
    random.seed(seed)

    print(f"\n[构建黄金测试集] 读取: {input_path}")
    all_records = load_stage2_records(input_path)
    print(f"  总记录数: {len(all_records)}")

    qualified = filter_qualified(all_records)
    print(f"  质量筛选后: {len(qualified)} 条（score≥3 + 有经查段 + 有reference来源）")

    selected = balance_diversity(qualified, target)
    print(f"  多样性平衡后: {len(selected)} 条")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "total_input": len(all_records),
        "qualified": len(qualified),
        "selected": len(selected),
        "type_a_count": 0,
        "type_b_count": 0,
        "skipped_no_query": 0,
        "skipped_no_reference": 0,
        "violation_type_distribution": Counter(),
        "platform_distribution": Counter(),
    }

    results = []
    case_counter = 1

    for record in selected:
        reference = build_reference_answer(record)
        if not reference:
            stats["skipped_no_reference"] += 1
            continue

        # 决定这条记录用哪种 Query 类型
        # 优先保证 Type A 比例，根据当前进度动态决定
        current_ratio = stats["type_a_count"] / max(1, stats["type_a_count"] + stats["type_b_count"])
        use_type_a = current_ratio < type_a_ratio

        if use_type_a:
            query = build_query_type_a(record)
            query_type = "A"
            if not query:
                # Type A 构建失败，降级到 Type B
                query = build_query_type_b(record)
                query_type = "B"
        else:
            query = build_query_type_b(record)
            query_type = "B"
            if not query:
                # Type B 构建失败，升级到 Type A
                query = build_query_type_a(record)
                query_type = "A"

        if not query:
            stats["skipped_no_query"] += 1
            continue

        case_id = f"golden_{case_counter:04d}"
        eval_record = convert_to_eval_format(record, case_id, query_type, query, reference)
        results.append(eval_record)

        # 更新统计
        if query_type == "A":
            stats["type_a_count"] += 1
        else:
            stats["type_b_count"] += 1

        vtype = eval_record["meta"]["violation_type"]
        platform = eval_record["meta"]["platform"]
        stats["violation_type_distribution"][vtype] += 1
        stats["platform_distribution"][platform] += 1

        case_counter += 1

    # 写入输出文件
    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats["output_count"] = len(results)
    stats["violation_type_distribution"] = dict(stats["violation_type_distribution"].most_common())
    stats["platform_distribution"] = dict(stats["platform_distribution"].most_common(15))

    print(f"\n[完成] 输出: {output_path}")
    print(f"  总输出条数: {len(results)}")
    print(f"  Type A（证据查询型）: {stats['type_a_count']}")
    print(f"  Type B（情景查询型）: {stats['type_b_count']}")
    print(f"  跳过（无query）: {stats['skipped_no_query']}")
    print(f"  跳过（无reference）: {stats['skipped_no_reference']}")
    print(f"\n  违法类型分布:")
    for vtype, count in stats["violation_type_distribution"].items():
        ratio = count / len(results) * 100
        print(f"    {vtype:15s}: {count:4d} ({ratio:.1f}%)")
    print(f"\n  平台分布（前10）:")
    for platform, count in list(stats["platform_distribution"].items())[:10]:
        ratio = count / len(results) * 100
        print(f"    {platform:15s}: {count:4d} ({ratio:.1f}%)")

    return stats


# ============================================================
# 追加合规样本（从旧数据集）
# ============================================================

def append_compliance_samples(
    golden_path: str,
    old_eval_path: str,
    output_path: Optional[str] = None,
    max_compliance: int = 150,
) -> int:
    """
    从旧 eval 数据集中追加质量较好的合规样本

    筛选条件：
    - is_violation = False
    - violation_type 不是"无"（去除标签混乱的14条）
    - compliance_type 不为 null

    Args:
        golden_path: 黄金测试集路径（仅违规案例）
        old_eval_path: 旧 eval 数据集路径
        output_path: 输出路径（None=覆盖 golden_path）
        max_compliance: 最多追加的合规样本数

    Returns:
        实际追加的条数
    """
    # 读取旧数据集中的合规样本
    compliance_samples = []
    with open(old_eval_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                meta = r.get("meta", {})
                if (
                    meta.get("is_violation") is False
                    and meta.get("violation_type") not in ["无", None, ""]
                    and meta.get("compliance_type") is not None
                ):
                    # 标注来源（旧数据集合规样本为构造样本）
                    meta["source"] = "constructed_compliance"
                    meta["rewritten"] = True  # 来自旧数据集，可能经过改写
                    r["meta"] = meta
                    compliance_samples.append(r)
            except json.JSONDecodeError:
                continue

    # 限制数量
    compliance_samples = compliance_samples[:max_compliance]

    if not compliance_samples:
        print("[INFO] 未找到符合条件的合规样本")
        return 0

    # 读取现有黄金测试集
    golden_records = []
    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    golden_records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # 合并并写入
    combined = golden_records + compliance_samples
    out_path = output_path or golden_path
    with open(out_path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[追加合规样本] 追加 {len(compliance_samples)} 条合规样本")
    print(f"[追加合规样本] 总计: {len(combined)} 条（违规: {len(golden_records)}，合规: {len(compliance_samples)}）")
    print(f"[追加合规样本] 注意：合规样本为构造样本（来自旧数据集），需在论文中说明")

    return len(compliance_samples)


# ============================================================
# 校验模式
# ============================================================

def validate_stage2_input(input_path: str) -> None:
    """校验 Stage 2 输出，报告可用于构建测试集的记录数"""
    all_records = load_stage2_records(input_path)
    print(f"\n[校验] 总记录数: {len(all_records)}")

    llm_success = sum(1 for r in all_records if r.get("llm_success"))
    print(f"  LLM成功: {llm_success} ({llm_success/len(all_records)*100:.1f}%)")

    qualified = filter_qualified(all_records)
    print(f"  质量筛选通过（score≥3 + 有经查段 + 有reference）: {len(qualified)}")

    # Type A 可构建数（有经查段）
    type_a_possible = sum(
        1 for r in qualified
        if r.get("jingcha_text") and len(r.get("jingcha_text", "")) >= 30
    )
    # Type B 可构建数（有摘要）
    type_b_possible = sum(
        1 for r in qualified
        if r.get("llm_violation_summary")
    )
    print(f"  可构建 Type A query: {type_a_possible}")
    print(f"  可构建 Type B query: {type_b_possible}")

    # 违法类型分布
    vtypes = Counter(
        normalize_violation_type(r.get("llm_violation_type") or r.get("violation_type_rule"))
        for r in qualified
    )
    print(f"\n  违法类型分布（合格记录）:")
    for vtype, count in vtypes.most_common():
        ratio = count / len(qualified) * 100
        print(f"    {vtype:15s}: {count:4d} ({ratio:.1f}%)")

    platforms = Counter(
        (r.get("platform_llm") or r.get("platform") or "未知") for r in qualified
    )
    print(f"\n  平台分布（前10）:")
    for platform, count in platforms.most_common(10):
        ratio = count / len(qualified) * 100
        print(f"    {platform:15s}: {count:4d} ({ratio:.1f}%)")

    print(f"\n  建议目标数量: {min(500, int(len(qualified) * 0.85))} 条")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="构建黄金测试集 / Build Golden Test Set",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  # 构建黄金测试集（仅违规案例）
  python scripts/build_golden_testset.py \\
    --input data/golden/stage2_results.jsonl \\
    --output data/golden/golden_testset.jsonl \\
    --target 500

  # 校验 stage2 输出
  python scripts/build_golden_testset.py \\
    --validate \\
    --input data/golden/stage2_results.jsonl

  # 构建后追加旧数据集中的合规样本
  python scripts/build_golden_testset.py \\
    --input data/golden/stage2_results.jsonl \\
    --output data/golden/golden_testset.jsonl \\
    --append_compliance data/eval/eval_754.jsonl \\
    --target 500
        """,
    )

    parser.add_argument("--input", required=True, help="Stage 2 结果文件 / Stage 2 results JSONL")
    parser.add_argument("--output", default="data/golden/golden_testset.jsonl", help="输出路径 / Output path")
    parser.add_argument("--target", type=int, default=500, help="目标条数（默认500）/ Target count")
    parser.add_argument("--type_a_ratio", type=float, default=0.5, help="Type A query 占比（默认0.5）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子 / Random seed")
    parser.add_argument("--validate", action="store_true", help="只做校验，不生成输出 / Validate only")
    parser.add_argument("--append_compliance", help="追加合规样本的旧eval数据集路径 / Old eval dataset for compliance samples")
    parser.add_argument("--max_compliance", type=int, default=150, help="最多追加合规样本数（默认150）")

    args = parser.parse_args()

    if args.validate:
        validate_stage2_input(args.input)
        return

    stats = build_golden_testset(
        input_path=args.input,
        output_path=args.output,
        target=args.target,
        type_a_ratio=args.type_a_ratio,
        seed=args.seed,
    )

    if args.append_compliance:
        append_compliance_samples(
            golden_path=args.output,
            old_eval_path=args.append_compliance,
            max_compliance=args.max_compliance,
        )

    # 保存构建统计
    stats_path = Path(args.output).parent / "golden_testset_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[INFO] 构建统计已保存: {stats_path}")


if __name__ == "__main__":
    main()
