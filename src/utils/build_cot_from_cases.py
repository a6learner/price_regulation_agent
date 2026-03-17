"""
根据从 PDF 抽取出的结构化案例（extracted_cases.jsonl），
自动生成适合微调用的 CoT 样本（input / thought / output）。

设计目标：
- 不要求你是价格合规领域专家，主要利用已有字段（违法类型、价格信息、引用法条等）
  通过模板生成一版“合格且一致”的分析和结论。
- 生成的 CoT 再配合 `build_sft_dataset.py` 转成 chat messages 训练格式。

默认读取：
    data/processed/extracted_cases.jsonl
默认输出：
    data/training/cases_cot.jsonl

用法示例（在项目根目录）::

    python -m src.utils.build_cot_from_cases ^
        --source "data/processed/extracted_cases.jsonl" ^
        --out "data/training/cases_cot.jsonl"
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # 非法行直接跳过，避免中断整体流程
                continue
    return rows


def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def clean_text(text: Optional[str], max_len: int = 400) -> str:
    """简单清洗文本：去掉多余换行、空白，控制长度。"""
    if not text:
        return ""
    s = " ".join(text.split())
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def pick_main_law_refs(law_refs: Optional[List[str]], max_num: int = 3) -> List[str]:
    """从 law_references 中挑几条与价格/明码标价高相关的法条。"""
    if not law_refs:
        return []
    # 简单规则：优先包含含有这些关键词的法条
    keywords = ["价格法", "明码标价", "价格违法行为行政处罚", "禁止价格欺诈"]
    scored: List[tuple[int, str]] = []
    for ref in law_refs:
        ref_clean = " ".join(ref.split())
        score = 0
        for kw in keywords:
            if kw in ref_clean:
                score += 1
        scored.append((score, ref_clean))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [ref for score, ref in scored[:max_num] if ref]
    # 去重
    seen = set()
    result: List[str] = []
    for r in picked:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result


def build_input(case: Dict[str, Any]) -> str:
    """
    构造给模型看的“案件描述”（input），尽量从消费者/监管视角描述事实。
    不直接使用整篇 full_text，避免太长。
    """
    company = clean_text(case.get("company_name"))
    platform = clean_text(case.get("platform"))
    violation_type = clean_text(case.get("violation_type"))
    desc = clean_text(case.get("violation_description"), max_len=260)
    price_info = clean_text(case.get("price_info"), max_len=260)
    date = clean_text(case.get("date"))
    region = clean_text(case.get("region"), max_len=80)

    parts: List[str] = []
    if company:
        parts.append(f"某监管部门在{region or '某地'}查处了{company}的一起价格违法案件。")
    else:
        parts.append(f"某地市场监管部门查处了一起疑似“{violation_type or '价格违法'}”的案件。")

    if platform:
        parts.append(f"该经营者通过{platform}平台开展经营活动。")

    if desc:
        parts.append(f"案情概述：{desc}")

    if price_info:
        parts.append(f"与价格相关的关键事实包括：{price_info}")

    if violation_type:
        parts.append(f"监管机关认定的违法类型为：{violation_type}。")

    if date:
        parts.append(f"案件发生或查处时间大致为：{date}。")

    parts.append("请根据上述事实，从价格合规的角度分析该经营行为是否违规，并给出依据和结论。")

    return "\n".join(parts)


def build_thought(case: Dict[str, Any], main_laws: List[str]) -> str:
    """
    构造一个模板化的思维链分析，分步骤说明：
    1）识别问题类型；2）匹配法律条款；3）结合事实比对；4）得出结论。
    """
    violation_type = clean_text(case.get("violation_type"))
    price_info = clean_text(case.get("price_info"), max_len=260)
    law_part = "、".join(main_laws) if main_laws else "价格法及明码标价、禁止价格欺诈等相关规定"

    step1 = f"步骤1：识别问题类型。根据案件描述，监管机关将本案归类为“{violation_type or '价格违法行为'}”。"

    step2 = (
        "步骤2：检索并匹配相关法条。"
        f"本案涉及的核心法律依据主要包括：{law_part}。"
        "这些条款通常规范经营者在价格标示、价格比较、促销宣传等方面不得使用虚假或足以引人误解的价格手段。"
    )

    if price_info:
        step3 = (
            "步骤3：结合价格事实进行比对分析。"
            f"从案件记录可以看出，与价格相关的关键事实包括：{price_info}。"
            "对比这些事实与上述法律条款的要求，可以判断经营者是否存在虚构原价、虚假折扣、价格误导、"
            "未明示价格条件或在标价之外加价收取费用等情形。"
        )
    else:
        step3 = (
            "步骤3：结合案件事实进行比对分析。"
            "综合案件记载的促销方式、价格标示方式以及交易实际发生情况，"
            "判断经营者是否存在利用虚假的或者使人误解的价格手段诱骗消费者的情形。"
        )

    step4 = (
        "步骤4：综合认定结论。"
        "如果经营者存在虚构或夸大原价、随意设置划线价、未按规定明码标价、"
        "线上线下实行不同价格但未标明交易条件，或者以“特价”“最低价”等方式误导消费者，"
        "则可以认定其构成价格违法行为，应当依据上述法律条款予以查处。"
    )

    return "\n".join([step1, step2, step3, step4])


def build_output(case: Dict[str, Any], main_laws: List[str]) -> str:
    """
    输出简洁结论：是否违规 + 核心依据 + 简要说明。
    这些行政处罚文书本身就是“已认定违规”的，所以统一给出“违规”结论。
    """
    violation_type = clean_text(case.get("violation_type"))
    company = clean_text(case.get("company_name"))
    platform = clean_text(case.get("platform"))

    law_text = "、".join(main_laws) if main_laws else "《中华人民共和国价格法》及《明码标价和禁止价格欺诈规定》等"

    subject = "该经营者"
    if company:
        subject = f"{company}"
    if platform:
        subject += f"在{platform}平台上的经营行为"
    else:
        subject += "的经营行为"

    return (
        f"违规。根据案件资料记载，可以认定{subject}构成{violation_type or '价格违法行为'}。"
        f"主要依据包括：{law_text}。"
        "综合案件中记载的价格标示方式、促销用语和实际成交价格，"
        "可以看出其存在利用虚假的或者足以使人误解的价格手段诱导交易，"
        "不符合价格法和明码标价、禁止价格欺诈相关规定，应当依法予以行政处罚。"
    )


def case_to_cot(case: Dict[str, Any]) -> Dict[str, Any]:
    """将一条结构化案例转换为一个 CoT 样本。"""
    laws = case.get("law_references") or []
    main_laws = pick_main_law_refs(laws)

    return {
        "case_id": case.get("case_id"),
        "violation_type": case.get("violation_type"),
        "law_references": main_laws,
        "input": build_input(case),
        "thought": build_thought(case, main_laws),
        "output": build_output(case, main_laws),
    }


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    default_source = project_root / "data" / "processed" / "extracted_cases.jsonl"
    default_out = project_root / "data" / "training" / "cases_cot.jsonl"

    parser = argparse.ArgumentParser(
        description="根据抽取的案例结构化数据，模板化生成 CoT 样本（input/thought/output）。"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(default_source),
        help="结构化案例 JSONL 文件路径（默认：data/processed/extracted_cases.jsonl）",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(default_out),
        help="CoT 样本输出 JSONL 文件路径（默认：data/training/cases_cot.jsonl）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    out_path = Path(args.out)

    cases = load_jsonl(source_path)
    if not cases:
        raise ValueError(f"源文件中没有任何有效案例：{source_path}")

    cot_samples: List[Dict[str, Any]] = []
    for case in cases:
        try:
            cot_samples.append(case_to_cot(case))
        except Exception:
            # 单条出错不影响整体，简单跳过
            continue

    if not cot_samples:
        raise ValueError("没有成功生成任何 CoT 样本，请检查源数据格式。")

    save_jsonl(out_path, cot_samples)

    print(f"读取案例条数：{len(cases)}")
    print(f"成功生成 CoT 样本：{len(cot_samples)} 条")
    print(f"已保存到：{out_path}")
    print("接下来可使用 build_sft_dataset.py 将该文件转换为 chat messages 训练/验证集。")


if __name__ == "__main__":
    main()


