#!/usr/bin/env python3
"""
enrich_eval_dataset.py — LLM 补充提取，确保 eval 数据集达到 500 条
=================================================================

两阶段处理：
  Stage 1: 对 eval_dataset_v3.jsonl 中 qualifying_articles 为空的案例，
           用 LLM 从 legal_analysis_reference 中提取定性法条
  Stage 2: 对 Tier 3 案例（有引用但无违法事实段），
           用 pdfplumber 读 PDF 全文，再用 LLM 提取 case_description + qualifying_articles

用法：
  # 仅 Stage 1（补充现有370条的qualifying_articles）
  python scripts/enrich_eval_dataset.py --stage 1

  # Stage 1 + Stage 2（补充至500条）
  python scripts/enrich_eval_dataset.py --stage 1,2

  # 测试模式（每个Stage只处理5条）
  python scripts/enrich_eval_dataset.py --stage 1,2 --dry-run

输出：
  results/eval_dataset_v3_final.jsonl   最终合并结果
  results/enrich_log.jsonl              处理日志
"""

import json
import re
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pdfplumber
except ImportError:
    print("请安装 pdfplumber: pip install pdfplumber")
    sys.exit(1)

from src.baseline.maas_client import MaaSClient


# ============================================================
# 法条分类规则（与 build_eval_dataset_v3.py 保持一致）
# ============================================================

QUALIFYING_PREFIXES = [
    "价格法_十二", "价格法_十三", "价格法_十四",
    "明码标价和禁止价格欺诈规定_",
    "禁止价格欺诈行为的规定_",
    "电子商务法_", "消费者权益保护法_", "反不正当竞争法_",
]

PENALTY_PREFIXES = [
    "价格法_三十", "价格法_四十",
    "价格违法行为行政处罚规定_",
]

DUAL_PURPOSE_KEYS = {
    "价格违法行为行政处罚规定_四",
    "价格违法行为行政处罚规定_五",
    "价格违法行为行政处罚规定_六",
    "价格违法行为行政处罚规定_七",
    "价格违法行为行政处罚规定_八",
}

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
# LLM 提示词
# ============================================================

SYSTEM_PROMPT = "你是中国市场监管领域的价格法律专家，擅长分析行政处罚文书中的法律依据。"

# Stage 1: 从法律分析文本提取定性法条
EXTRACT_QUALIFYING_PROMPT = """请从以下行政处罚文书的法律分析文本中，提取被认定为违法行为依据的"定性法条"。

**定性法条**：定义了哪些行为属于违法的条款（如价格法第12条、第13条、第14条，明码标价规定各条）
**处罚法条**：规定如何处罚的条款（如价格法第39-42条，价格违法行为行政处罚规定各条）→ 不要输出

article_key 格式规则（必须严格遵守）：
- 价格法第十二条 → "价格法_十二"
- 价格法第十三条 → "价格法_十三"
- 价格法第十三条第一款 → "价格法_十三_一"
- 价格法第十三条第二款 → "价格法_十三_二"
- 价格法第十四条 → "价格法_十四"
- 价格法第十四条第四项 → "价格法_十四_四"
- 明码标价和禁止价格欺诈规定第十九条 → "明码标价和禁止价格欺诈规定_十九"
- 明码标价和禁止价格欺诈规定第十九条第三项 → "明码标价和禁止价格欺诈规定_十九_三"

**法律分析文本**：
{legal_analysis}

请严格按以下JSON格式输出，不要输出其他内容：
{{"qualifying_articles": [{{"law": "法律简称", "article": "第X条第X款/项", "article_key": "标准化key"}}]}}

如果文本中没有定性法条（只有处罚条款），输出：{{"qualifying_articles": []}}"""


# Stage 2: 从PDF全文提取案件事实
EXTRACT_FACTS_PROMPT = """请从以下行政处罚文书全文中，提取违法行为的客观事实描述（"经查"段内容）。

要求：
1. 只保留客观事实：时间、地点、经营者、违法行为的具体表现（如标价金额、涉及商品、操作方式）
2. 删除所有法律分析、法条引用、定性结论（"违反了《》""构成违法"等）
3. 不超过400字，尽量保留关键事实细节

**文书全文**：
{full_text}

直接输出事实描述文本，不加任何说明或前缀。"""


# Stage 2: 从PDF全文同时提取事实 + 定性法条
EXTRACT_BOTH_PROMPT = """请从以下行政处罚文书全文中提取两类信息。

**文书全文**：
{full_text}

请严格按以下JSON格式输出，不要输出其他内容：
{{
  "case_description": "违法行为客观事实描述（不超过400字，不含法条引用和定性结论）",
  "qualifying_articles": [
    {{"law": "法律简称", "article": "第X条第X款/项", "article_key": "标准化key"}}
  ]
}}

case_description 要求：只保留客观事实（时间地点人物违法行为），删除所有法律分析结论。
qualifying_articles 要求：只提取定性法条（价格法第12/13/14条，明码标价规定等），不要处罚法条（价格法第39-42条，处罚规定各条）。

article_key 格式：价格法_十三、价格法_十四_四、明码标价和禁止价格欺诈规定_十九_三 等。"""


# ============================================================
# 工具函数
# ============================================================

def classify_key(key: str) -> str:
    """返回 qualifying / penalty / both / unknown"""
    if key in DUAL_PURPOSE_KEYS:
        return "both"
    for p in QUALIFYING_PREFIXES:
        if key.startswith(p):
            return "qualifying"
    for p in PENALTY_PREFIXES:
        if key.startswith(p):
            return "penalty"
    return "unknown"


def normalize_key(key: str) -> str:
    key = re.sub(r"条$", "", key)
    return re.sub(r"_+", "_", key).strip("_")


def build_article_entry(key: str) -> dict:
    """从 article_key 生成完整的 article 对象"""
    parts = key.split("_", 1)
    law = parts[0]
    article = f"第{parts[1]}条" if len(parts) > 1 else "未知条款"
    return {"law": law, "article": article, "article_key": key}


def parse_llm_json(text: str) -> dict:
    """从 LLM 输出中解析 JSON，支持多种格式"""
    # 先尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 提取 ```json ... ``` 代码块
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 提取第一个 { ... }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def strip_leakage(text: str) -> str:
    for p in LEAKAGE_PATTERNS:
        text = re.sub(p, "", text, flags=re.DOTALL)
    return re.sub(r"\s{2,}", " ", text).strip()


def read_pdf_text(pdf_path: str, max_chars: int = 3000) -> str:
    """读 PDF 全文，最多返回 max_chars 字符"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
            return "\n".join(texts)[:max_chars]
    except Exception:
        return ""


# ============================================================
# LLM 调用封装
# ============================================================

def llm_extract_qualifying(client: MaaSClient, legal_analysis: str, model_key: str) -> list:
    """从法律分析文本提取 qualifying_articles"""
    if not legal_analysis or len(legal_analysis) < 20:
        return []

    prompt = EXTRACT_QUALIFYING_PROMPT.format(legal_analysis=legal_analysis[:1000])
    resp = client.call_model(SYSTEM_PROMPT, prompt, model_key=model_key)
    if not resp:
        return []

    text = client.extract_response_text(resp) or ""
    parsed = parse_llm_json(text)
    articles = parsed.get("qualifying_articles", [])

    # 过滤：只保留真正的定性法条
    result = []
    seen = set()
    for a in articles:
        key = normalize_key(a.get("article_key", ""))
        if not key or key in seen:
            continue
        label = classify_key(key)
        if label in ("qualifying", "both", "unknown"):
            # unknown 也保留（可能是 LLM 识别出新法条）
            entry = {"law": a.get("law", key.split("_")[0]),
                     "article": a.get("article", f"第{key.split('_',1)[-1]}条"),
                     "article_key": key}
            result.append(entry)
            seen.add(key)
    return result


def llm_extract_both(client: MaaSClient, full_text: str, model_key: str) -> dict:
    """从 PDF 全文提取 case_description + qualifying_articles"""
    if not full_text or len(full_text) < 100:
        return {}

    prompt = EXTRACT_BOTH_PROMPT.format(full_text=full_text[:2500])
    resp = client.call_model(SYSTEM_PROMPT, prompt, model_key=model_key)
    if not resp:
        return {}

    text = client.extract_response_text(resp) or ""
    parsed = parse_llm_json(text)

    # 处理 qualifying_articles
    articles = parsed.get("qualifying_articles", [])
    clean_articles = []
    seen = set()
    for a in articles:
        key = normalize_key(a.get("article_key", ""))
        if not key or key in seen:
            continue
        label = classify_key(key)
        if label in ("qualifying", "both", "unknown"):
            entry = {"law": a.get("law", key.split("_")[0]),
                     "article": a.get("article", f"第{key.split('_',1)[-1]}条"),
                     "article_key": key}
            clean_articles.append(entry)
            seen.add(key)

    # 处理 case_description（去泄露）
    desc = parsed.get("case_description", "")
    if desc:
        desc = strip_leakage(desc)

    return {
        "case_description": desc,
        "qualifying_articles": clean_articles,
    }


# ============================================================
# Stage 1: 补充现有 eval 数据集的 qualifying_articles
# ============================================================

def stage1_enrich(
    client: MaaSClient,
    eval_path: Path,
    model_key: str,
    dry_run: bool,
    log_path: Path,
) -> list:
    """
    对 qualifying_articles 为空的案例，
    用 LLM 从 legal_analysis_reference 中提取。
    返回补充后的完整 records 列表。
    """
    records = []
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    need_enrich = [r for r in records if not r["ground_truth"]["qualifying_articles"]]
    print(f"\n[Stage 1] 需补充 qualifying_articles: {len(need_enrich)}/{len(records)} 条")

    if dry_run:
        need_enrich = need_enrich[:5]
        print(f"  [dry-run] 仅处理前 {len(need_enrich)} 条")

    enriched_count = 0
    log_entries = []

    for i, record in enumerate(need_enrich):
        legal_text = record["ground_truth"].get("legal_analysis_reference", "")
        case_id = record["id"]

        print(f"  [{i+1}/{len(need_enrich)}] {case_id}  legal_text_len:{len(legal_text)}", end="")

        if not legal_text or len(legal_text) < 20:
            print(" → SKIP (无法律分析文本)")
            log_entries.append({"id": case_id, "stage": 1, "result": "skip_no_text"})
            continue

        articles = llm_extract_qualifying(client, legal_text, model_key)
        time.sleep(0.5)  # 避免限速

        if articles:
            # 同时补充到原 records 中
            for r in records:
                if r["id"] == case_id:
                    r["ground_truth"]["qualifying_articles"] = articles
                    r["_debug"]["enriched_stage1"] = True
                    break
            enriched_count += 1
            print(f" → OK ({len(articles)} 条定性法条): {[a['article_key'] for a in articles]}")
            log_entries.append({"id": case_id, "stage": 1, "result": "ok",
                                 "articles": [a["article_key"] for a in articles]})
        else:
            print(f" → FAIL (LLM 未提取到定性法条)")
            log_entries.append({"id": case_id, "stage": 1, "result": "fail_no_articles"})

    print(f"\n  Stage 1 完成: 成功补充 {enriched_count}/{len(need_enrich)} 条")

    # 写日志
    with open(log_path, "a", encoding="utf-8") as f:
        for entry in log_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return records


# ============================================================
# Stage 2: 从 Tier 3 案例扩充数据集
# ============================================================

def stage2_expand(
    client: MaaSClient,
    scan_path: Path,
    existing_records: list,
    model_key: str,
    target: int,
    dry_run: bool,
    log_path: Path,
) -> list:
    """
    从 scan_results_v2.jsonl 的 Tier 3 案例中，
    用 LLM 读 PDF 全文提取 case_description + qualifying_articles，
    补充到 existing_records 直到达到 target 条。
    """
    current_count = len(existing_records)
    need_more = target - current_count
    print(f"\n[Stage 2] 当前 {current_count} 条，目标 {target} 条，需新增 {need_more} 条")

    if need_more <= 0:
        print("  已达目标，跳过 Stage 2")
        return existing_records

    # 读取 scan_results，筛选 Tier 3（有引用、violation_facts 为空、text_length > 500）
    existing_pdfs = {r["source_pdf"] for r in existing_records}
    scan_records = []
    with open(scan_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                scan_records.append(json.loads(line))

    tier3_candidates = []
    for r in scan_records:
        if r.get("file") in existing_pdfs:
            continue  # 已经处理过
        has_citation = bool(r.get("citation_keys"))
        no_facts = len(r.get("violation_facts_preview", "")) <= 50
        long_enough = r.get("text_length", 0) > 500
        if has_citation and no_facts and long_enough:
            tier3_candidates.append(r)

    # 按文本长度降序（越长越可能提取到内容）
    tier3_candidates.sort(key=lambda x: x.get("text_length", 0), reverse=True)
    print(f"  找到 Tier 3 候选: {len(tier3_candidates)} 条")

    if dry_run:
        tier3_candidates = tier3_candidates[:5]
        print(f"  [dry-run] 仅处理前 {len(tier3_candidates)} 条")

    new_records = []
    log_entries = []
    start_id = len(existing_records) + 1

    for i, scan_rec in enumerate(tier3_candidates):
        if len(new_records) >= need_more and not dry_run:
            break

        pdf_path = scan_rec.get("file_path", "")
        filename = scan_rec.get("file", "")
        print(f"  [{i+1}] {filename[:50]}  text_len:{scan_rec.get('text_length', 0)}", end="")

        # 读 PDF 全文
        full_text = read_pdf_text(pdf_path)
        if not full_text:
            print(" → SKIP (PDF 读取失败)")
            log_entries.append({"file": filename, "stage": 2, "result": "skip_pdf_fail"})
            continue

        # LLM 提取
        extracted = llm_extract_both(client, full_text, model_key)
        time.sleep(0.5)

        desc = extracted.get("case_description", "")
        articles = extracted.get("qualifying_articles", [])

        if not desc or len(desc) < 50:
            print(f" → SKIP (case_description 太短: {len(desc)}字)")
            log_entries.append({"file": filename, "stage": 2, "result": "skip_short_desc"})
            continue

        if not articles:
            print(f" → SKIP (无定性法条)")
            log_entries.append({"file": filename, "stage": 2, "result": "skip_no_articles"})
            continue

        # 构建新记录
        case_id = f"CASE_{start_id + len(new_records):04d}"
        platforms = scan_rec.get("platforms", [])
        amount = scan_rec.get("penalty_amount")
        penalty_result = f"罚款{amount:.0f}元" if amount else None

        # penalty_articles：从 citation_keys 的处罚法条
        penalty_keys = []
        seen_p = set()
        for raw_key in scan_rec.get("citation_keys", []):
            key = normalize_key(raw_key)
            label = classify_key(key)
            if label in ("penalty", "both") and key not in seen_p:
                seen_p.add(key)
                penalty_keys.append(build_article_entry(key))

        new_rec = {
            "id": case_id,
            "source_pdf": filename,
            "region": scan_rec.get("diqu"),
            "tier": 3,
            "input": {
                "case_description": desc,
                "platform": platforms[0] if platforms else None,
                "goods_or_service": None,
            },
            "ground_truth": {
                "is_violation": True,
                "violation_type": scan_rec.get("primary_type", "未识别"),
                "qualifying_articles": articles,
                "penalty_articles": penalty_keys,
                "legal_analysis_reference": scan_rec.get("legal_analysis_preview", ""),
                "penalty_result": penalty_result,
            },
            "_debug": {
                "desc_source": "llm_pdf_extraction",
                "leakage_found": False,
                "desc_too_short": False,
                "raw_citation_keys": scan_rec.get("citation_keys", []),
                "sections_found": scan_rec.get("sections_found", []),
                "text_length": scan_rec.get("text_length", 0),
                "enriched_stage2": True,
            },
        }
        new_records.append(new_rec)
        print(f" → OK  desc:{len(desc)}字  qualifying:{[a['article_key'] for a in articles]}")
        log_entries.append({"file": filename, "stage": 2, "result": "ok",
                             "case_id": case_id,
                             "articles": [a["article_key"] for a in articles]})

    print(f"\n  Stage 2 完成: 新增 {len(new_records)} 条")

    # 写日志
    with open(log_path, "a", encoding="utf-8") as f:
        for entry in log_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return existing_records + new_records


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="LLM 补充提取，确保 eval 数据集达到 500 条")
    parser.add_argument("--stage", default="1,2",
                        help="执行的阶段，逗号分隔（1=补充qualifying，2=扩充Tier3），默认 1,2")
    parser.add_argument("--target", type=int, default=500, help="目标数据集大小，默认 500")
    parser.add_argument("--model", default="qwen-8b", help="使用的模型 key，默认 qwen-8b")
    parser.add_argument("--dry-run", action="store_true", help="测试模式，每阶段只处理5条")
    parser.add_argument("--eval-input", default="results/eval_dataset_v3.jsonl",
                        help="Stage 1 输入文件")
    parser.add_argument("--scan-input", default="results/scan_results_v2.jsonl",
                        help="Stage 2 输入文件（scan结果）")
    parser.add_argument("--output-dir", default="results", help="输出目录")
    args = parser.parse_args()

    stages = set(int(s.strip()) for s in args.stage.split(","))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    log_path = output_dir / "enrich_log.jsonl"
    final_path = output_dir / ("eval_dataset_v3_dry.jsonl" if args.dry_run
                               else "eval_dataset_v3_final.jsonl")

    # 初始化 MaaS 客户端
    client = MaaSClient(config_path="configs/model_config.yaml")
    print(f"模型: {args.model}  目标: {args.target} 条  dry-run: {args.dry_run}")

    records = []

    # Stage 1
    if 1 in stages:
        records = stage1_enrich(
            client=client,
            eval_path=Path(args.eval_input),
            model_key=args.model,
            dry_run=args.dry_run,
            log_path=log_path,
        )
    else:
        # 直接加载
        with open(args.eval_input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        print(f"[跳过 Stage 1] 加载 {len(records)} 条已有记录")

    # Stage 2
    if 2 in stages:
        records = stage2_expand(
            client=client,
            scan_path=Path(args.scan_input),
            existing_records=records,
            model_key=args.model,
            target=args.target,
            dry_run=args.dry_run,
            log_path=log_path,
        )

    # 保存最终结果
    # 只保留 eval 必要字段（去掉 _debug），可选
    with open(final_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 统计
    total = len(records)
    has_q = sum(1 for r in records if r["ground_truth"]["qualifying_articles"])
    has_desc = sum(1 for r in records if r["input"]["case_description"])
    eval_ready = sum(1 for r in records
                     if r["ground_truth"]["qualifying_articles"] and r["input"]["case_description"])

    stats = client.get_statistics()

    print(f"\n{'='*55}")
    print("最终统计")
    print(f"{'='*55}")
    print(f"  总条数              : {total}")
    print(f"  qualifying_articles  : {has_q}/{total} ({has_q/total*100:.1f}%)")
    print(f"  case_description     : {has_desc}/{total} ({has_desc/total*100:.1f}%)")
    print(f"  完全 eval-ready      : {eval_ready}/{total} ({eval_ready/total*100:.1f}%)")
    print(f"  API 请求次数         : {stats['total_requests']}")
    print(f"  Token 消耗           : {stats['total_tokens']:,}")
    print(f"  输出文件             : {final_path}")
    print(f"  日志文件             : {log_path}")

    if total < args.target and not args.dry_run:
        print(f"\n  [WARNING] 未达到目标 {args.target} 条（当前 {total} 条）")
        print("  建议：检查 enrich_log.jsonl，或增加 Tier 3 候选范围")


if __name__ == "__main__":
    main()
