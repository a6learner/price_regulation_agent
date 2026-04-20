#!/usr/bin/env python3
"""
build_eval_dataset_v3.py — 从 scan_results_v2.jsonl 构建黄金测试集
==================================================================

用法:
  # Pilot 验证（前20条，验证 pipeline 是否正确）
  python scripts/build_eval_dataset_v3.py --pilot

  # 全量处理（Tier 1 + Tier 2）
  python scripts/build_eval_dataset_v3.py

  # 处理指定 Tier
  python scripts/build_eval_dataset_v3.py --tiers 1,2

输出:
  results/eval_dataset_v3_pilot.jsonl   (pilot 模式)
  results/eval_dataset_v3.jsonl          (全量)
  results/dataset_statistics.json        (统计报告)
"""

import json
import re
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. 法条分类规则（来自 CC_PHASE2_GUIDE.md）
# ============================================================

# 定性法条：定义违法行为本身 → 评测 ground truth
QUALIFYING_PREFIXES = [
    "价格法_十二",
    "价格法_十三",
    "价格法_十四",
    "明码标价和禁止价格欺诈规定_",
    "禁止价格欺诈行为的规定_",
    "电子商务法_",
    "消费者权益保护法_",
    "反不正当竞争法_",
]

# 处罚法条：量刑依据 → 不纳入评测 ground truth
PENALTY_PREFIXES = [
    "价格法_三十",
    "价格法_四十",
    "价格违法行为行政处罚规定_",
]

# 双重用途：既定义违法行为，又是处罚依据 → 同时纳入两个列表
DUAL_PURPOSE_KEYS = {
    "价格违法行为行政处罚规定_四",
    "价格违法行为行政处罚规定_五",
    "价格违法行为行政处罚规定_六",
    "价格违法行为行政处罚规定_七",
    "价格违法行为行政处罚规定_八",
}

# article_key → (law简称, 中文条款名) 的映射，用于生成可读的 article 字段
KEY_TO_READABLE = {
    "价格法_十二": ("价格法", "第十二条"),
    "价格法_十三": ("价格法", "第十三条"),
    "价格法_十三_一": ("价格法", "第十三条第一款"),
    "价格法_十三_二": ("价格法", "第十三条第二款"),
    "价格法_十四": ("价格法", "第十四条"),
    "价格法_十四_一": ("价格法", "第十四条第一项"),
    "价格法_十四_二": ("价格法", "第十四条第二项"),
    "价格法_十四_三": ("价格法", "第十四条第三项"),
    "价格法_十四_四": ("价格法", "第十四条第四项"),
    "价格法_十四_五": ("价格法", "第十四条第五项"),
    "价格法_十四_六": ("价格法", "第十四条第六项"),
    "价格法_十四_七": ("价格法", "第十四条第七项"),
    "价格法_十四_八": ("价格法", "第十四条第八项"),
    "价格法_三十九": ("价格法", "第三十九条"),
    "价格法_四十": ("价格法", "第四十条"),
    "价格法_四十一": ("价格法", "第四十一条"),
    "价格法_四十二": ("价格法", "第四十二条"),
    "价格违法行为行政处罚规定_四": ("价格违法行为行政处罚规定", "第四条"),
    "价格违法行为行政处罚规定_五": ("价格违法行为行政处罚规定", "第五条"),
    "价格违法行为行政处罚规定_六": ("价格违法行为行政处罚规定", "第六条"),
    "价格违法行为行政处罚规定_七": ("价格违法行为行政处罚规定", "第七条"),
    "价格违法行为行政处罚规定_八": ("价格违法行为行政处罚规定", "第八条"),
    "价格违法行为行政处罚规定_九": ("价格违法行为行政处罚规定", "第九条"),
    "价格违法行为行政处罚规定_十": ("价格违法行为行政处罚规定", "第十条"),
    "价格违法行为行政处罚规定_十一": ("价格违法行为行政处罚规定", "第十一条"),
    "价格违法行为行政处罚规定_十三": ("价格违法行为行政处罚规定", "第十三条"),
    "价格违法行为行政处罚规定_十六": ("价格违法行为行政处罚规定", "第十六条"),
    "价格违法行为行政处罚规定_十八": ("价格违法行为行政处罚规定", "第十八条"),
    "价格违法行为行政处罚规定_二十一": ("价格违法行为行政处罚规定", "第二十一条"),
}


# ============================================================
# 2. 泄露模式（从 case_description 中删除法律结论词）
# ============================================================

LEAKAGE_PATTERNS = [
    r"违反了《[^》]+》[^。；]*?(?:规定|条款|条文)[^。；]*[。；]?",
    r"违反《[^》]+》[^。；]*?(?:规定|条款|条文)[^。；]*[。；]?",
    r"构成[^，。；]{2,20}违法行为[^。；]*[。；]?",
    r"属于[^，。；]{2,20}价格(?:欺诈|违法)[^。；]*[。；]?",
    r"本局认为[^。]*[。]?",
    r"依据[^，。；]{2,30}规定[^。]*[。]?",
    r"涉嫌违反了《[^》]+》[^。；]*[。；]?",
]


# ============================================================
# 3. Key 格式归一化
# ============================================================

def normalize_key(key: str) -> str:
    """去除 citation_key 中可能带的'条'字后缀等噪音"""
    # "明码标价和禁止价格欺诈规定_十六条" → "明码标价和禁止价格欺诈规定_十六"
    key = re.sub(r"条$", "", key)
    # 去除重复下划线
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


# ============================================================
# 4. 法条拆分
# ============================================================

def classify_key(key: str):
    """返回 ('qualifying', 'penalty', 'both', 'unknown') 之一"""
    if key in DUAL_PURPOSE_KEYS:
        return "both"
    for prefix in QUALIFYING_PREFIXES:
        if key.startswith(prefix):
            return "qualifying"
    for prefix in PENALTY_PREFIXES:
        if key.startswith(prefix):
            return "penalty"
    return "unknown"


def split_citations(citation_keys: list):
    """
    将 citation_keys 拆分为 qualifying_articles 和 penalty_articles。
    返回 (qualifying_list, penalty_list)，每项是 {law, article, article_key}。
    """
    seen_q, seen_p = set(), set()
    qualifying, penalty = [], []

    for raw_key in citation_keys:
        key = normalize_key(raw_key)
        if not key:
            continue

        label = classify_key(key)
        law, article = _key_to_law_article(key)

        entry = {"law": law, "article": article, "article_key": key}

        if label in ("qualifying", "both") and key not in seen_q:
            seen_q.add(key)
            qualifying.append(entry)

        if label in ("penalty", "both") and key not in seen_p:
            seen_p.add(key)
            penalty.append(entry)

    return qualifying, penalty


def _key_to_law_article(key: str):
    """从 article_key 生成可读的 law 和 article 字段"""
    if key in KEY_TO_READABLE:
        return KEY_TO_READABLE[key]

    # 通用降级处理：从 key 推断
    parts = key.split("_", 1)
    law = parts[0]
    article = f"第{parts[1]}条" if len(parts) > 1 else "未知条款"
    return law, article


# ============================================================
# 5. 去泄露
# ============================================================

def strip_leakage(text: str) -> tuple:
    """
    去除文本中的法律结论词。
    返回 (cleaned_text, leakage_found: bool)
    """
    original = text
    for pattern in LEAKAGE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    # 清理多余空白
    text = re.sub(r"\s{2,}", " ", text).strip()
    leakage_found = len(text) < len(original) - 5  # 删了超过5字才算有泄露
    return text, leakage_found


# ============================================================
# 6. Tier 分级
# ============================================================

def compute_tier(record: dict, has_qualifying: bool) -> int:
    facts_len = len(record.get("violation_facts_preview", ""))
    has_any_citation = bool(record.get("citation_keys"))

    if has_qualifying and facts_len > 50:
        return 1
    if has_any_citation and facts_len > 50:
        return 2
    if has_any_citation and record.get("text_length", 0) > 500:
        return 3
    return 4  # 不纳入


# ============================================================
# 7. 单条记录处理
# ============================================================

def process_record(record: dict, case_id: str) -> dict:
    citation_keys = list(dict.fromkeys(record.get("citation_keys", [])))  # 去重保序
    qualifying, penalty = split_citations(citation_keys)

    has_qualifying = bool(qualifying)
    tier = compute_tier(record, has_qualifying)

    # 构建 case_description
    raw_facts = record.get("violation_facts_preview", "")
    if raw_facts:
        case_description, leakage_found = strip_leakage(raw_facts)
        desc_source = "violation_facts"
    else:
        case_description = ""
        leakage_found = False
        desc_source = "empty"

    # 如果去泄露后太短，用 legal_analysis 作 fallback（标记，不参与评测）
    desc_too_short = len(case_description) < 80
    if desc_too_short and record.get("legal_analysis_preview"):
        case_description = record["legal_analysis_preview"][:150]
        desc_source = "legal_analysis_fallback"

    # 平台
    platforms = record.get("platforms", [])
    platform = platforms[0] if platforms else None

    # 罚款金额
    amount = record.get("penalty_amount")
    penalty_result = f"罚款{amount:.0f}元" if amount else None

    result = {
        "id": case_id,
        "source_pdf": record.get("file", ""),
        "region": record.get("diqu"),
        "tier": tier,
        "input": {
            "case_description": case_description,
            "platform": platform,
            "goods_or_service": None,  # 规则提取困难，留 null，后续 LLM 补充
        },
        "ground_truth": {
            "is_violation": True,  # 处罚文书全部为违规
            "violation_type": record.get("primary_type", "未识别"),
            "qualifying_articles": qualifying,
            "penalty_articles": penalty,
            "legal_analysis_reference": record.get("legal_analysis_preview", ""),
            "penalty_result": penalty_result,
        },
        # 调试字段（不影响评测，方便人工检查）
        "_debug": {
            "desc_source": desc_source,
            "leakage_found": leakage_found,
            "desc_too_short": desc_too_short,
            "raw_citation_keys": citation_keys,
            "sections_found": record.get("sections_found", []),
            "text_length": record.get("text_length", 0),
        },
    }
    return result


# ============================================================
# 8. 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="从 scan_results_v2.jsonl 构建 eval_dataset_v3")
    parser.add_argument("--pilot", action="store_true", help="只处理前20条（验证 pipeline）")
    parser.add_argument("--tiers", default="1,2", help="纳入的 Tier 列表，逗号分隔，默认 1,2")
    parser.add_argument(
        "--input", default="results/scan_results_v2.jsonl", help="输入文件路径"
    )
    parser.add_argument("--output_dir", default="results", help="输出目录")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    allowed_tiers = set(int(t.strip()) for t in args.tiers.split(","))

    # 读取输入
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if args.pilot:
        records = records[:20]
        output_path = output_dir / "eval_dataset_v3_pilot.jsonl"
        print(f"[PILOT MODE] 处理前 20 条 → {output_path}\n")
    else:
        output_path = output_dir / "eval_dataset_v3.jsonl"
        print(f"[FULL MODE] 处理全部 {len(records)} 条 → {output_path}\n")

    # 处理
    results = []
    tier_counter = Counter()
    leakage_counter = 0
    no_qualifying_counter = 0
    no_facts_counter = 0

    for i, record in enumerate(records):
        case_id = f"CASE_{i+1:04d}"
        processed = process_record(record, case_id)
        results.append(processed)

        tier = processed["tier"]
        tier_counter[tier] += 1

        dbg = processed["_debug"]
        has_q = bool(processed["ground_truth"]["qualifying_articles"])
        if not has_q:
            no_qualifying_counter += 1
        if not processed["input"]["case_description"]:
            no_facts_counter += 1
        if dbg["leakage_found"]:
            leakage_counter += 1

        # 逐条打印（pilot 模式详细，全量只打摘要）
        if args.pilot:
            q_count = len(processed["ground_truth"]["qualifying_articles"])
            p_count = len(processed["ground_truth"]["penalty_articles"])
            desc_len = len(processed["input"]["case_description"])
            leakage_flag = "YES" if dbg["leakage_found"] else "NO"
            no_facts_flag = " [NO_FACTS]" if not processed["input"]["case_description"] else ""
            print(
                f"  [{case_id}] Tier:{tier}  qualifying:{q_count}  penalty:{p_count}"
                f"  desc_len:{desc_len:>4}  leakage:{leakage_flag}  src:{dbg['desc_source']}{no_facts_flag}"
            )
        elif (i + 1) % 100 == 0:
            print(f"  已处理 {i+1}/{len(records)} 条...")

    # 过滤（pilot 不过滤，全量只保留 allowed_tiers）
    if not args.pilot:
        results = [r for r in results if r["tier"] in allowed_tiers]
        print(f"\n  过滤后保留 Tier {args.tiers}: {len(results)} 条")

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 统计报告
    total = len(records)
    saved = len(results)
    stats = {
        "total_input": total,
        "total_output": saved,
        "pilot_mode": args.pilot,
        "tier_distribution": dict(tier_counter.most_common()),
        "qualifying_articles_coverage": f"{(total - no_qualifying_counter) / total * 100:.1f}%",
        "case_description_coverage": f"{(total - no_facts_counter) / total * 100:.1f}%",
        "leakage_detected": leakage_counter,
        "leakage_rate": f"{leakage_counter / total * 100:.1f}%",
    }

    print(f"\n{'='*55}")
    print("SUMMARY")
    print(f"{'='*55}")
    print(f"  输入总量       : {total}")
    print(f"  输出数量       : {saved}")
    print(f"  Tier 分布      : {dict(tier_counter.most_common())}")
    print(f"  qualifying 覆盖: {stats['qualifying_articles_coverage']}")
    print(f"  case_desc 覆盖 : {stats['case_description_coverage']}")
    print(f"  泄露检测       : {leakage_counter} 条 ({stats['leakage_rate']})")
    print(f"  输出文件       : {output_path}")

    if not args.pilot:
        stats_path = output_dir / "dataset_statistics.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"  统计报告       : {stats_path}")

    # Pilot 模式额外提示
    if args.pilot:
        print(f"\n{'='*55}")
        print("PILOT 验证检查清单")
        print(f"{'='*55}")
        print("  请人工抽查以下 3 点：")
        print("  1. qualifying_articles 是否是定性法条（非处罚条款）")
        print("  2. case_description 是否不含'违反了《》''构成违法'等词")
        print("  3. Tier 1 占比是否合理（预期 30-50%）")
        print(f"\n  查看输出: type {output_path}")


if __name__ == "__main__":
    main()
