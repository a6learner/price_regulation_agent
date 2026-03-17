"""
Polish a chat-format SFT dataset (JSONL with {"messages": [...], "meta": {...}}).

This script rewrites the assistant message for the first N samples to be:
  - more case-specific (based on user content)
  - more structured (事实要点/合规分析/结论与依据/整改建议)
  - law references cleaned + de-duplicated (based on meta.law_references)

Usage:
  # Polish first 30 samples (in place)
  python -m src.utils.polish_chat_dataset --file data/training/train_chat_from_cases.jsonl --n 30

  # Polish the entire file (n=0 means all)
  python -m src.utils.polish_chat_dataset --file data/training/train_chat_from_cases.jsonl --n 0
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _clean_text(s: str) -> str:
    s = s.replace("\u3000", " ")
    # collapse weird whitespace
    s = re.sub(r"[ \t]+", " ", s)
    # normalize common broken strings
    s = s.replace("规 定", "规定").replace("处 罚", "处罚").replace("欺 诈", "欺诈").replace("价 格", "价格")
    s = s.replace("《中华 人民共和国价格法》", "《中华人民共和国价格法》")
    s = s.replace("《中 华人民共和国价格法》", "《中华人民共和国价格法》")
    s = s.replace("《中华人 民共和国价格法》", "《中华人民共和国价格法》")
    s = s.replace("《中华人民共和国价格法法》", "《中华人民共和国价格法》")
    s = s.replace("《 5 中华人民共和国价格法》", "《中华人民共和国价格法》")
    s = s.replace("《明码标价和禁止价格欺 骗规定》", "《明码标价和禁止价格欺诈规定》")
    return s.strip()


def _unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if not it:
            continue
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


def _clean_law_refs(raw_refs: List[str] | None) -> List[str]:
    if not raw_refs:
        return []
    cleaned = []
    for r in raw_refs:
        r = _clean_text(str(r))
        # Keep only reasonable-looking refs; still allow "《XXX》" w/o article.
        if "《" not in r or "》" not in r:
            continue
        # Drop obviously garbled duplicates like "《明 码标价和禁《明码..."
        if r.count("《") > 2 or "《明 码标价" in r:
            continue
        # Drop extremely long / commentary-like strings that are not citations
        if len(r) > 60 or "根据" in r or "第第" in r:
            continue
        cleaned.append(r)
    cleaned = _unique_keep_order(cleaned)

    # Prefer refs with explicit articles
    with_article = [r for r in cleaned if "第" in r and "条" in r]
    without_article = [r for r in cleaned if r not in with_article]
    cleaned = with_article + without_article

    # Cap length to avoid overly long citations in assistant output
    return cleaned[:4]


def _extract_platform(user_text: str) -> str | None:
    m = re.search(r"通过([^\s。；;，,\n]{1,10})平台", user_text)
    if m:
        return m.group(1)
    return None


def _extract_key_prices(user_text: str, limit: int = 6) -> List[str]:
    t = user_text.replace("￥", "￥")
    prices = []
    for m in re.finditer(r"(￥\s*)?(\d+(?:\.\d+)?)\s*元(?:/[\w\u4e00-\u9fff]+)?", t):
        val = m.group(2)
        if val:
            prices.append(val + "元")
        if len(prices) >= limit:
            break
    return _unique_keep_order(prices)


def _pick_fact_snippets(user_text: str, max_snippets: int = 3) -> List[str]:
    # pick short sentences containing strong signal keywords
    text = _clean_text(user_text)
    parts = re.split(r"[。\n]", text)
    keywords = [
        "划线价",
        "原价",
        "到手价",
        "结算",
        "实际支付",
        "扣款",
        "未标明",
        "限时",
        "限量",
        "优惠券",
        "首页图片",
        "主图",
        "无",
        "不存在",
        "标价之外",
        "加价",
        "打包费",
        "搭售",
        "捆绑",
    ]
    scored: List[Tuple[int, str]] = []
    for p in parts:
        p = p.strip()
        if len(p) < 10:
            continue
        # Skip boilerplate header-like sentences when possible
        if any(x in p for x in ["行政处罚决定书", "查处了", "某监管部门在", "主体资格证照名称", "统一社会信用"]):
            # only keep if it contains strong signals (numbers + mismatch words)
            if not (re.search(r"\d", p) and any(k in p for k in ["实际", "结算", "扣款", "无", "不存在", "未标明", "划线价", "原价"])):
                continue
        score = sum(1 for k in keywords if k in p)
        # encourage sentences with numbers
        if re.search(r"\d", p):
            score += 1
        if score <= 0:
            continue
        # cap length for readability
        if len(p) > 140:
            p = p[:140].rstrip() + "…"
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_snippets]]


def _detect_issue(user_text: str, violation_type: str | None) -> str:
    t = user_text
    vt = violation_type or ""
    # Highest priority: what the regulator labeled
    if "虚构原价" in vt:
        return "price_comparison"
    if "虚假折扣" in vt:
        return "fake_discount"
    if "要素缺失" in vt:
        return "missing_terms"

    # Then infer from facts (priority order matters)
    if "结算" in t or "实际支付" in t or "扣款" in t or "支付界面" in t:
        return "settlement_mismatch"
    if "标价之外" in t or "加价" in t:
        return "extra_charge"
    if "打包费" in t:
        return "packaging_fee"
    if "未标明" in t and ("期限" in t or "起止" in t or "时间" in t or "数量" in t):
        return "missing_terms"
    if "原价" in t or "划线价" in t:
        return "price_comparison"
    if "折扣" in t or "折价" in t or "特惠" in t or "限时低价" in t:
        return "fake_discount"
    return "generic_misleading"


def _compose_assistant(user_text: str, meta: Dict[str, Any]) -> str:
    violation_type = _clean_text(str(meta.get("violation_type", ""))) if meta else ""
    law_refs = _clean_law_refs(meta.get("law_references", []) if meta else [])
    platform = _extract_platform(user_text) or "线上平台"

    issue = _detect_issue(user_text, violation_type)
    prices = _extract_key_prices(user_text)
    facts = _pick_fact_snippets(user_text)

    fact_lines = []
    if facts:
        for f in facts:
            fact_lines.append(f"- {f}")
    else:
        # minimal fallback
        if prices:
            fact_lines.append(f"- 文本中出现的价格要素包括：{', '.join(prices[:4])}。")
        else:
            fact_lines.append("- 案件材料显示存在价格展示/促销信息与实际交易条件不一致的情况。")

    analysis_lines: List[str] = []
    if issue == "price_comparison":
        analysis_lines += [
            "- 经营者采用“原价/划线价/参考价”进行价格比较时，被比较价格应当真实、准确，并有可核验的交易记录或形成机制支撑。",
            "- 若线上线下从未以划线价（或宣称的原价）成交，或无法提供近期成交凭证，则该比较价格缺乏依据，容易使消费者对优惠幅度产生误解。",
        ]
    elif issue == "fake_discount":
        analysis_lines += [
            "- 标注“限时低价/特惠/折扣”等促销信息，应当以真实的价格变动为基础，不能在价格未实质下降或优惠条件不存在的情况下制造“优惠”印象。",
            "- 若促销期间价格长期维持不变、或“优惠价”与实际可获得价格不一致，属于以足以使人误解的方式进行价格促销。",
        ]
    elif issue == "missing_terms":
        analysis_lines += [
            "- 经营者开展限时/限量等价格促销，应当显著标明期限、数量、适用条件等关键要素，避免消费者误解优惠的可得性。",
            "- 未标明促销期限/数量等要素，会导致消费者无法判断优惠是否有效及何时有效，属于价格促销信息要素不完整。",
        ]
    elif issue == "settlement_mismatch":
        analysis_lines += [
            "- 页面宣传价（主图/首页/标题）应与结算价及可选规格对应一致；以低价宣传吸引点击但结算按更高价格收取，容易构成价格误导/价格欺诈。",
            "- 即使部分情形源于优惠券到期、活动结束未更新页面，经营者仍负有及时更正展示信息的义务。",
        ]
    elif issue == "extra_charge":
        analysis_lines += [
            "- 经营者应当按标示价格销售商品或提供服务；在标价之外加价收取费用，属于违反明码标价/标价一致性的典型风险点。",
            "- 若确需另行收取费用，应当事先明示收费项目、标准及条件，并在消费者下单前可清晰识别。",
        ]
    elif issue == "packaging_fee":
        analysis_lines += [
            "- 平台收取打包费应当与实际提供的打包材料相匹配；如以“必选项”等形式强制收取但不提供对应物料，属于收费与服务不匹配，容易误导消费者。",
            "- 收费项目、标准、对应服务内容应在下单前清晰、完整展示，避免“二次收费/重复收费”的误解。",
        ]
    else:
        analysis_lines += [
            "- 价格展示信息应当真实、准确、可核验，不能以足以使人误解的标示方式诱导交易。",
            "- 促销/优惠/对比价格一旦展示，应确保消费者在实际购买路径中能够以展示条件完成交易；否则应及时更正或撤下。",
        ]

    refs_text = "；".join(law_refs) if law_refs else "《中华人民共和国价格法》及《明码标价和禁止价格欺诈规定》等"

    # Keep conclusion aligned with监管机关定性：在训练数据中统一按“构成/属于”表达
    conclusion = (
        f"结论：违规。综合上述事实与规则，可以认定该经营者在{platform}上的相关价格展示/促销行为"
        f"构成“{violation_type or '价格违法'}”。主要依据：{refs_text}。"
    )

    advice_lines = [
        "- 立即下架或更正不准确的主图/标题/详情页价格信息，确保展示价与可成交价一致。",
        "- 对“划线价/原价/参考价”保留形成依据与近期交易凭证；限时限量活动显著标明期限、数量与适用条件。",
    ]

    content = "\n".join(
        [
            "事实要点：",
            *fact_lines,
            "",
            "合规分析：",
            *analysis_lines,
            "",
            conclusion,
            "",
            "整改建议：",
            *advice_lines,
        ]
    )
    return _clean_text(content)


def _compose_thought(user_text: str, meta: Dict[str, Any]) -> str:
    """
    Produce a compact, case-specific reasoning trace for (input, thought, output) style SFT data.
    Keep it structured but not overly long.
    """
    violation_type = _clean_text(str(meta.get("violation_type", ""))) if meta else ""
    platform = _extract_platform(user_text) or "线上平台"
    issue = _detect_issue(user_text, violation_type)
    prices = _extract_key_prices(user_text)
    facts = _pick_fact_snippets(user_text, max_snippets=2)
    law_refs = _clean_law_refs(meta.get("law_references", []) if meta else [])
    refs_text = "；".join(law_refs) if law_refs else "《中华人民共和国价格法》《明码标价和禁止价格欺诈规定》"

    issue_map = {
        "price_comparison": "虚构原价/划线价或不实价格比较",
        "fake_discount": "虚假折扣/虚假促销",
        "missing_terms": "促销要素不完整（期限/数量/条件未明示）",
        "settlement_mismatch": "宣传价与结算价/可得条件不一致",
        "extra_charge": "标价之外加价/另行收费未明示",
        "packaging_fee": "打包费/附加收费不清晰或不匹配",
        "generic_misleading": "价格标示足以引人误解",
    }
    issue_label = issue_map.get(issue, "价格标示问题")

    fact_text = "；".join(facts) if facts else ("；".join(prices[:3]) if prices else "案件文本中存在价格展示与交易条件不一致的线索")

    return _clean_text(
        "\n".join(
            [
                f"步骤1：定性问题。根据案情要点，主要风险为：{issue_label}（平台：{platform}）。",
                f"步骤2：提取关键事实。{fact_text}。",
                f"步骤3：匹配规则。依据{refs_text}，价格标示应真实准确，促销/比较价格需有依据且与可成交条件一致。",
                "步骤4：形成判断。上述事实足以导致消费者对价格或优惠幅度产生误解，符合价格误导/价格欺诈的构成要件。",
            ]
        )
    )


def polish_file(path: Path, n: int, backup: bool = False) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if backup:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    n_effective = len(lines) if n == 0 else n
    out_lines: List[str] = []
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        obj = json.loads(line)
        if idx < n_effective:
            # Chat-style: {"messages":[...], "meta":{...}}
            if isinstance(obj, dict) and "messages" in obj:
                msgs: List[Dict[str, Any]] = obj.get("messages", [])
                meta: Dict[str, Any] = obj.get("meta", {}) or {}
                user_text = ""
                for m in msgs:
                    if m.get("role") == "user":
                        user_text = str(m.get("content", ""))
                        break
                assistant_idx = None
                for j, m in enumerate(msgs):
                    if m.get("role") == "assistant":
                        assistant_idx = j
                        break
                if assistant_idx is not None:
                    msgs[assistant_idx]["content"] = _compose_assistant(user_text, meta)
                obj["messages"] = msgs

            # SFT-style: {"input": "...", "thought": "...", "output": "...", ...}
            elif isinstance(obj, dict) and "input" in obj and "output" in obj:
                user_text = str(obj.get("input", ""))
                meta = obj  # may include violation_type/law_references/case_id
                obj["output"] = _compose_assistant(user_text, meta)
                if "thought" in obj:
                    obj["thought"] = _compose_thought(user_text, meta)
        out_lines.append(json.dumps(obj, ensure_ascii=False))
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Input JSONL file to polish (in place).")
    parser.add_argument("--n", type=int, default=0, help="Polish first N samples. Use 0 to polish all.")
    parser.add_argument("--backup", action="store_true", help="Write a .bak copy once before modifying the file.")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise FileNotFoundError(path)
    if args.n < 0:
        raise ValueError("--n must be >= 0")

    polish_file(path, args.n, backup=bool(args.backup))


if __name__ == "__main__":
    main()


