#!/usr/bin/env python3
"""
violation_type_discovery.py — 从700+处罚文书PDF中自动发现和分类违规类型
========================================================================

功能：
  1. scan   — 批量扫描所有PDF，提取法律依据条文引用 + 关键词信号（零API成本）
  2. cluster — 基于法条引用和关键词聚类，生成初步违规类型分布
  3. sample  — 按聚类结果分层采样，输出典型案例供人工审核或LLM精细分类
  4. llm_classify — 用LLM对采样案例做精细违规类型标注（需API）

用法：
  # Step 1: 扫描全部PDF，零成本
  python violation_type_discovery.py scan --pdf_dir ./penalty_pdfs --output scan_results.jsonl
  
  # Step 2: 聚类分析，生成违规类型分布报告
  python violation_type_discovery.py cluster --input scan_results.jsonl --output cluster_report.json
  
  # Step 3: 分层采样，每类抽5-10份典型案例
  python violation_type_discovery.py sample --input scan_results.jsonl --clusters cluster_report.json --per_cluster 8 --output sampled_cases.jsonl
  
  # Step 4: 用LLM精细分类（可选，需配置API）
  python violation_type_discovery.py llm_classify --input sampled_cases.jsonl --output classified_cases.jsonl

依赖: pip install pdfplumber
作者: Auto-generated for 价格合规分析系统
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
import random

try:
    import pdfplumber
except ImportError:
    print("请安装 pdfplumber: pip install pdfplumber")
    sys.exit(1)


# ============================================================
# 1. 法条引用模式 — 用于从PDF中识别引用了哪些法律条文
# ============================================================

# 主要法律法规及其条款模式
LAW_PATTERNS = {
    "价格法": {
        "regex": r"《(?:中华人民共和国)?价格法》第(\w+)条(?:第(\w+)(?:项|款))?",
        "key_articles": {
            "十四": "不正当价格行为（总则）",
            "十四.*?第.*?一": "串通操纵市场价格",
            "十四.*?第.*?二": "低价倾销",
            "十四.*?第.*?三": "捏造散布涨价信息/哄抬价格",
            "十四.*?第.*?四": "虚假或使人误解的价格手段（价格欺诈）",
            "十四.*?第.*?五": "价格歧视",
            "十四.*?第.*?六": "变相提高或压低价格",
            "十四.*?第.*?七": "牟取暴利",
            "十三": "明码标价义务",
            "四十": "经营者行政处罚",
            "四十一": "价格行政处罚",
            "四十二": "价格违法行政处罚",
        },
    },
    "价格违法行为行政处罚规定": {
        "regex": r"《价格违法行为行政处罚规定》第(\w+)条",
        "key_articles": {
            "四": "串通操纵/低价倾销/价格歧视",
            "五": "串通操纵（造成价格大幅上涨）",
            "六": "哄抬价格/囤积居奇",
            "七": "价格欺诈",
            "八": "变相提高或压低价格",
            "九": "不执行政府指导价/定价",
            "十": "不执行价格干预/紧急措施",
            "十一": "个人处罚标准",
            "十三": "明码标价违规",
        },
    },
    "明码标价和禁止价格欺诈规定": {
        "regex": r"《明码标价和禁止价格欺诈规定》第(\w+)条",
        "key_articles": {
            "十九": "七种价格欺诈行为",
            "二十": "网络交易价格违规",
            "十六": "价格比较违规",
            "七": "明码标价要素",
            "八": "标价外加价",
        },
    },
    "禁止价格欺诈行为的规定": {
        "regex": r"《禁止价格欺诈行为的规定》第(\w+)条",
        "key_articles": {
            "六": "标价欺诈行为（9种）",
            "七": "价格手段欺诈行为（6种）",
        },
    },
    "电子商务法": {
        "regex": r"《(?:中华人民共和国)?电子商务法》第(\w+)条",
        "key_articles": {},
    },
    "消费者权益保护法": {
        "regex": r"《(?:中华人民共和国)?消费者权益保护法》第(\w+)条",
        "key_articles": {},
    },
    "反不正当竞争法": {
        "regex": r"《(?:中华人民共和国)?反不正当竞争法》第(\w+)条",
        "key_articles": {},
    },
}


# ============================================================
# 2. 违规行为关键词信号 — 用于辅助分类
# ============================================================

VIOLATION_KEYWORDS = {
    "虚构原价": [
        "虚构原价", "原价.*?无.*?交易", "原价.*?无.*?销售", "从未以.*?价格.*?销售",
        "虚假原价", "标注.*?原价.*?无依据", "原价.*?不真实",
        "无.*?以该价格.*?交易", "无.*?以.*?原价.*?成交", "不存在.*?原价",
    ],
    "虚假折扣": [
        "虚假折扣", "虚假优惠", "折扣.*?与实际不符", "打折.*?不实",
        "虚假.*?减价", "虚假.*?折价", "折扣幅度.*?不符",
    ],
    "价格标示不一致": [
        "首页.*?价格.*?低于.*?详情", "主图.*?价格.*?低于", "标示.*?价格.*?不一致",
        "展示.*?价格.*?结算.*?不一致", "页面.*?价格.*?不同", "低价诱骗.*?高价结算",
        "标价.*?与.*?结算.*?不一致", "标示价格.*?低于", "标价.*?不一致",
        "首页.*?标示.*?低于", "显著位置.*?低于",
    ],
    "不明码标价": [
        "未明码标价", "不标明价格", "未标示价格", "未标明.*?计价单位",
        "明码标价.*?不规范", "不按规定.*?标价", "标价签.*?不规范",
        # 补充高频表述
        "未按规定执行明码标价", "未按规定明码标价", "未执行明码标价",
        "未按.*?明码标价.*?规定", "违反.*?明码标价.*?规定",
        "应当明码标价.*?未.*?标", "未进行明码标价",
    ],
    "标价外加价": [
        "标价之外.*?加价", "收取未标明.*?费用", "额外收费.*?未标示",
        "隐形收费", "未标明.*?附加条件",
        # 补充高频表述（反向抹零/多收价款）
        "反向抹零", "多收.*?价款", "多收.*?费用", "收取.*?高于.*?标价",
        "结算.*?高于.*?标价", "实收.*?高于.*?应收",
    ],
    "误导性价格标示": [
        "误导性.*?标价", "欺骗性.*?标价", "使人误解.*?价格",
        "最低价.*?无依据", "特价.*?无依据", "出厂价.*?无依据",
        "误导.*?消费者", "欺骗性.*?语言.*?标价",
        "虚假.*?使人误解.*?价格手段", "利用虚假.*?价格",
    ],
    "虚假价格比较": [
        "虚假.*?价格比较", "比较价格.*?不真实", "被比较价格.*?无依据",
        "划线价.*?虚假", "价格对比.*?不实",
    ],
    "不履行价格承诺": [
        "不履行.*?价格承诺", "价格承诺.*?不兑现", "拒绝.*?价格承诺",
        "承诺.*?优惠.*?不执行",
    ],
    "哄抬价格": [
        "哄抬价格", "囤积居奇", "捏造.*?涨价", "散布.*?涨价",
        "推动.*?价格.*?过快.*?上涨", "大幅度提高.*?价格",
    ],
    "低价倾销": [
        "低于成本.*?倾销", "低价倾销", "排挤竞争.*?低价",
    ],
    "串通操纵": [
        "串通.*?操纵.*?价格", "价格同盟", "联合定价",
    ],
    "价格歧视": [
        "价格歧视", "同等交易.*?不同价格", "差别定价.*?歧视",
    ],
    "政府定价违规": [
        "不执行.*?政府.*?定价", "超出.*?政府指导价", "违反.*?政府定价",
        "不执行.*?政府指导价",
        # 补充高频表述
        "超出.*?浮动幅度", "超出.*?指导价.*?范围", "高于.*?政府.*?指导价",
        "超过.*?政府规定.*?价格", "不执行.*?价格.*?规定", "超出.*?最高限价",
        "未执行.*?政府.*?定价",
    ],
    "促销活动违规": [
        "促销.*?规则.*?不一致", "促销.*?范围.*?不一致",
        "活动.*?规则.*?与实际.*?不符",
    ],
    "代金券/积分违规": [
        "代金券.*?不.*?折抵", "积分.*?不.*?折抵", "兑换券.*?拒绝",
    ],
    "谎称政府定价": [
        "谎称.*?政府定价", "谎称.*?政府指导价", "冒充.*?政府.*?价格",
    ],
    "变相提高价格": [
        "变相.*?提高.*?价格", "抬高等级.*?销售", "以次充好", "短斤少两",
        "缺斤少两", "掺杂掺假",
    ],
}


# ============================================================
# 3. PDF文本提取器
# ============================================================

class PDFTextExtractor:
    """从处罚文书PDF中提取关键文本段落"""

    @staticmethod
    def extract_full_text(pdf_path: str) -> Optional[str]:
        """提取PDF全文"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                return "\n".join(texts) if texts else None
        except Exception as e:
            return None

    @staticmethod
    def extract_key_sections(full_text: str) -> Dict[str, str]:
        """提取关键段落：经查段、本局认为段、处罚决定段"""
        sections = {}

        # 经查段 — 违法事实描述
        jingcha = re.search(
            r"经查[，,：:\s](.+?)(?=(?:以上事实|上述事实|证据如下|以上违法事实|本局认为|综上))",
            full_text, re.DOTALL
        )
        if jingcha:
            sections["violation_facts"] = jingcha.group(1).strip()[:3000]

        # 本局认为段 — 法律分析
        benjurenwei = re.search(
            r"本局认为[，,：:\s](.+?)(?=(?:依据|根据|综上|鉴于|现依据|按照))",
            full_text, re.DOTALL
        )
        if not benjurenwei:
            benjurenwei = re.search(
                r"本局认为[，,：:\s](.+?)(?=(?:处罚如下|处罚决定|行政处罚))",
                full_text, re.DOTALL
            )
        if benjurenwei:
            sections["legal_analysis"] = benjurenwei.group(1).strip()[:3000]

        # 处罚决定段
        chufa = re.search(
            r"(?:处罚如下|处罚决定如下|决定如下)[：:\s](.+?)(?=(?:如不服|当事人如|以上|$))",
            full_text, re.DOTALL
        )
        if chufa:
            sections["penalty_decision"] = chufa.group(1).strip()[:1500]

        return sections


# ============================================================
# 4. 法条引用提取器
# ============================================================

class LawCitationExtractor:
    """从文本中提取所有法律条文引用"""

    @staticmethod
    def extract_citations(text: str) -> List[Dict]:
        """提取所有法条引用"""
        citations = []

        for law_name, config in LAW_PATTERNS.items():
            for match in re.finditer(config["regex"], text):
                article = match.group(1)
                sub = match.group(2) if match.lastindex >= 2 else None
                citation = {
                    "law": law_name,
                    "article": article,
                    "sub_article": sub,
                    "full_match": match.group(0),
                }
                citations.append(citation)

        # 补充：检测没有书名号的常见简称引用
        simple_patterns = [
            (r"价格法第(\w+)条", "价格法"),
            (r"处罚规定第(\w+)条", "价格违法行为行政处罚规定"),
        ]
        for pattern, law_name in simple_patterns:
            for match in re.finditer(pattern, text):
                citation = {
                    "law": law_name,
                    "article": match.group(1),
                    "sub_article": None,
                    "full_match": match.group(0),
                }
                # 去重
                if not any(c["law"] == law_name and c["article"] == match.group(1)
                          for c in citations):
                    citations.append(citation)

        return citations

    @staticmethod
    def citation_to_key(citation: Dict) -> str:
        """将法条引用转为标准化key"""
        key = f"{citation['law']}_{citation['article']}"
        if citation.get("sub_article"):
            key += f"_{citation['sub_article']}"
        return key


# ============================================================
# 5. 违规类型信号检测器
# ============================================================

class ViolationSignalDetector:
    """基于关键词匹配检测违规行为类型信号"""

    @staticmethod
    def detect_signals(text: str) -> Dict[str, float]:
        """返回每种违规类型的匹配置信度 (0-1)"""
        scores = {}
        text_lower = text.lower()

        for vtype, keywords in VIOLATION_KEYWORDS.items():
            match_count = 0
            for kw in keywords:
                if re.search(kw, text_lower):
                    match_count += 1
            if match_count > 0:
                # 置信度 = 匹配关键词数 / 总关键词数，最高1.0
                scores[vtype] = min(match_count / max(len(keywords) * 0.3, 1), 1.0)

        return scores

    @staticmethod
    def get_top_signals(scores: Dict[str, float], top_k: int = 3) -> List[Tuple[str, float]]:
        """返回置信度最高的top_k个违规类型"""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]


# ============================================================
# 6. 涉及平台检测
# ============================================================

PLATFORM_KEYWORDS = [
    "拼多多", "淘宝", "天猫", "京东", "美团", "大众点评", "抖音", "快手",
    "饿了么", "闲鱼", "苏宁", "唯品会", "小红书", "得物", "微信小程序",
    "微信商城", "支付宝", "百度", "1688", "亚马逊", "shopee", "虾皮",
]

def detect_platform(text: str) -> List[str]:
    """检测涉及的电商/服务平台"""
    found = []
    for p in PLATFORM_KEYWORDS:
        if p in text:
            found.append(p)
    return found


# ============================================================
# 7. 罚款金额提取
# ============================================================

def extract_penalty_amount(text: str) -> Optional[float]:
    """提取罚款金额（元）"""
    patterns = [
        r"罚款(?:人民币)?(\d[\d,]*\.?\d*)(?:万)?元",
        r"处(?:以)?(?:人民币)?(\d[\d,]*\.?\d*)(?:万)?元(?:的)?罚款",
        r"罚款.*?(\d[\d,]*\.?\d*)(?:万)?元",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            amount = float(match.group(1).replace(",", ""))
            if "万" in match.group(0):
                amount *= 10000
            return amount
    return None


# ============================================================
# 8. 主处理流程
# ============================================================

def scan_single_pdf(pdf_path: str) -> Optional[Dict]:
    """扫描单个PDF，提取所有信号"""
    full_text = PDFTextExtractor.extract_full_text(pdf_path)
    if not full_text or len(full_text) < 100:
        return None

    sections = PDFTextExtractor.extract_key_sections(full_text)
    citations = LawCitationExtractor.extract_citations(full_text)
    citation_keys = [LawCitationExtractor.citation_to_key(c) for c in citations]

    # 用全文来检测违规类型信号（确保不遗漏段落提取失败的案例）
    signal_text = (sections.get("violation_facts", "") + " "
                   + sections.get("legal_analysis", "") + " "
                   + sections.get("penalty_decision", ""))
    # 如果关键段落都没提取到，退回到全文
    if not signal_text.strip():
        signal_text = full_text[:3000]
    signals = ViolationSignalDetector.detect_signals(signal_text)
    top_signals = ViolationSignalDetector.get_top_signals(signals)

    # 法条引用兜底推断：若关键词匹配为空，通过法条推断主类型
    if not top_signals:
        citation_set = set(citation_keys)
        if any("处罚规定_七" in ck or "明码标价.*欺诈.*十九" in ck for ck in citation_set):
            top_signals = [("误导性价格标示", 0.4)]
        elif any("处罚规定_九" in ck or "价格法_十二" in ck or "价格法_三十九" in ck for ck in citation_set):
            top_signals = [("政府定价违规", 0.4)]
        elif any("处罚规定_十三" in ck or "价格法_十三" in ck for ck in citation_set):
            top_signals = [("不明码标价", 0.3)]
        elif any("处罚规定_八" in ck or "价格法_十四_六" in ck for ck in citation_set):
            top_signals = [("变相提高价格", 0.3)]
        elif any("价格法_十四" in ck for ck in citation_set):
            top_signals = [("误导性价格标示", 0.3)]

    platforms = detect_platform(full_text)
    penalty = extract_penalty_amount(full_text)

    # 提取文书文号
    wenhao_match = re.search(
        r"[（(]?\s*[\u4e00-\u9fa5]+(?:市监|市场监管|发改|物价)[\u4e00-\u9fa5]*(?:处|罚|决|字)?\s*[〔\[（(]\s*\d{4}\s*[〕\]）)]\s*\d+\s*号",
        full_text
    )
    wenhao = wenhao_match.group(0).strip() if wenhao_match else None

    # 提取地区信息
    diqu_match = re.search(r"([\u4e00-\u9fa5]{2,6}(?:市|县|区|州|盟))", full_text[:200])
    diqu = diqu_match.group(1) if diqu_match else None

    result = {
        "file": os.path.basename(pdf_path),
        "file_path": pdf_path,
        "text_length": len(full_text),
        "wenhao": wenhao,
        "diqu": diqu,
        "sections_found": list(sections.keys()),
        "citations": [c["full_match"] for c in citations],
        "citation_keys": citation_keys,
        "violation_signals": {k: round(v, 3) for k, v in signals.items()},
        "top_signals": [(s[0], round(s[1], 3)) for s in top_signals],
        "primary_type": top_signals[0][0] if top_signals else "未识别",
        "platforms": platforms,
        "penalty_amount": penalty,
        "violation_facts_preview": sections.get("violation_facts", "")[:500],
        "legal_analysis_preview": sections.get("legal_analysis", "")[:500],
    }

    return result


def cmd_scan(args):
    """批量扫描PDF目录"""
    pdf_dir = Path(args.pdf_dir)
    output_path = args.output

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        # 也搜索子目录
        pdf_files = sorted(pdf_dir.rglob("*.pdf"))

    print(f"找到 {len(pdf_files)} 个PDF文件")
    print(f"开始扫描...\n")

    results = []
    failed = []
    for i, pdf_path in enumerate(pdf_files):
        try:
            result = scan_single_pdf(str(pdf_path))
            if result:
                results.append(result)
                status = f"OK [{result['primary_type']}]"
                if result['platforms']:
                    status += f" 平台:{','.join(result['platforms'])}"
            else:
                failed.append(str(pdf_path))
                status = "FAIL 提取失败"
        except Exception as e:
            failed.append(str(pdf_path))
            status = f"ERR 异常: {str(e)[:50]}"

        # 进度条
        pct = (i + 1) / len(pdf_files) * 100
        print(f"  [{i+1:>4}/{len(pdf_files)}] {pct:5.1f}% {status}  {pdf_path.name[:40]}")

    # 保存结果
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n扫描完成:")
    print(f"  成功: {len(results)}")
    print(f"  失败: {len(failed)}")
    print(f"  输出: {output_path}")

    if failed:
        fail_path = output_path.replace(".jsonl", "_failed.txt")
        with open(fail_path, "w") as f:
            f.write("\n".join(failed))
        print(f"  失败列表: {fail_path}")


def cmd_cluster(args):
    """聚类分析，生成违规类型分布"""
    # 读取扫描结果
    results = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            results.append(json.loads(line.strip()))

    print(f"加载 {len(results)} 条扫描结果\n")

    # === 1. 按primary_type统计 ===
    type_counter = Counter(r["primary_type"] for r in results)

    # === 2. 按法条引用统计 ===
    citation_counter = Counter()
    for r in results:
        for ck in r["citation_keys"]:
            citation_counter[ck] += 1

    # === 3. 按平台统计 ===
    platform_counter = Counter()
    for r in results:
        for p in r["platforms"]:
            platform_counter[p] += 1

    # === 4. 交叉分析：法条 × 违规类型 ===
    cross_tab = defaultdict(lambda: Counter())
    for r in results:
        for ck in r["citation_keys"]:
            cross_tab[ck][r["primary_type"]] += 1

    # === 5. 未识别案例分析 ===
    unrecognized = [r for r in results if r["primary_type"] == "未识别"]
    unrecognized_citations = Counter()
    for r in unrecognized:
        for ck in r["citation_keys"]:
            unrecognized_citations[ck] += 1

    # 生成报告
    report = {
        "total_scanned": len(results),
        "violation_type_distribution": dict(type_counter.most_common()),
        "citation_frequency": dict(citation_counter.most_common(20)),
        "platform_distribution": dict(platform_counter.most_common()),
        "unrecognized_count": len(unrecognized),
        "unrecognized_top_citations": dict(unrecognized_citations.most_common(10)),
        "cross_analysis": {
            ck: dict(types.most_common(3))
            for ck, types in sorted(cross_tab.items(), key=lambda x: sum(x[1].values()), reverse=True)[:15]
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print("=" * 60)
    print("违规类型分布")
    print("=" * 60)
    for vtype, count in type_counter.most_common():
        bar = "#" * (count * 40 // max(type_counter.values()))
        pct = count / len(results) * 100
        print(f"  {vtype:20s} {count:>4} ({pct:5.1f}%) {bar}")

    print(f"\n{'=' * 60}")
    print("法条引用TOP 10")
    print("=" * 60)
    for citation, count in citation_counter.most_common(10):
        pct = count / len(results) * 100
        print(f"  {citation:45s} {count:>4} ({pct:5.1f}%)")

    print(f"\n{'=' * 60}")
    print("平台分布")
    print("=" * 60)
    for platform, count in platform_counter.most_common():
        pct = count / len(results) * 100
        print(f"  {platform:15s} {count:>4} ({pct:5.1f}%)")

    if unrecognized:
        print(f"\nWARN {len(unrecognized)} 份文书未能自动识别违规类型")
        print("  这些案例的法条引用:")
        for ck, cnt in unrecognized_citations.most_common(5):
            print(f"    {ck}: {cnt}")
        print("  -> 建议用 sample 命令采样后用LLM辅助分类")

    print(f"\n报告已保存至: {args.output}")


def cmd_sample(args):
    """分层采样，每类抽取典型案例"""
    results = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            results.append(json.loads(line.strip()))

    # 按primary_type分组
    groups = defaultdict(list)
    for r in results:
        groups[r["primary_type"]].append(r)

    per_cluster = args.per_cluster
    sampled = []

    print(f"分层采样 (每类 ≤ {per_cluster} 份):\n")
    for vtype, cases in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
        n = min(per_cluster, len(cases))
        # 优先选法条引用多、信号强的案例
        cases_sorted = sorted(cases, key=lambda x: (
            len(x["citation_keys"]),
            max(dict(x["top_signals"]).values()) if x["top_signals"] else 0,
        ), reverse=True)

        selected = cases_sorted[:n]
        sampled.extend(selected)
        print(f"  {vtype:20s}: {len(cases):>4} 总量 -> 抽样 {n}")

    # 保存
    with open(args.output, "w", encoding="utf-8") as f:
        for s in sampled:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\n共采样 {len(sampled)} 份案例 -> {args.output}")
    print("下一步: 用 llm_classify 命令或人工审核来确认/修正违规类型")


def cmd_llm_classify(args):
    """用LLM精细分类（讯飞星辰API占位）"""

    # === LLM API 调用接口 (占位，需替换为实际API) ===
    def call_llm(prompt: str) -> str:
        """
        调用讯飞星辰MaaS API
        替换为你的实际API调用代码
        
        示例（讯飞星辰）:
        import requests
        resp = requests.post(
            "https://maas-api.cn-huabei-1.xf-yun.com/v1/chat/completions",
            headers={"Authorization": "Bearer YOUR_API_KEY"},
            json={
                "model": "xdeepseekv3",  # 或 qwen3-8b, qwen3.5-397b, minimax-m2.5
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
        )
        return resp.json()["choices"][0]["message"]["content"]
        """
        raise NotImplementedError(
            "请在此函数中配置你的LLM API调用代码（讯飞星辰/其他）"
        )

    # 分类prompt模板
    CLASSIFY_PROMPT = """你是一位中国市场监管领域的价格合规专家。请根据以下处罚文书内容，判断该案件的违规类型。

## 违规类型分类体系

### A. 价格欺诈类
A1. 虚构原价 — 标注的原价无真实交易记录
A2. 虚假折扣/减价 — 折扣幅度与实际不符
A3. 虚假价格比较 — 被比较价格无依据
A4. 低价诱骗高价结算 — 标示低价实际结算高价
A5. 误导性价格标示 — 使用欺骗性语言/图片标价
A6. 不履行价格承诺 — 拒绝兑现价格优惠
A7. 隐藏不利价格条件 — 弱化标示附加条件
A8. 代金券/积分不兑现 — 拒不按约折抵
A9. 谎称政府定价 — 冒充政府定价/指导价

### B. 明码标价违规类
B1. 未明码标价 — 不标明价格
B2. 标价要素不全 — 品名/计价单位/规格缺失
B3. 标价外加价 — 收取未标明的费用
B4. 标价不一致 — 同一商品多处标价不同

### C. 网络交易价格违规类
C1. 首页/详情页价格不一致 — 首页低价详情页高价
C2. 促销规则不一致 — 公布与实际活动不符
C3. 平台强制价格标示 — 平台利用技术手段强制虚假标价

### D. 市场秩序类
D1. 哄抬价格 — 捏造散布涨价信息/囤积居奇
D2. 低价倾销 — 以低于成本价排挤竞争对手
D3. 串通操纵价格 — 多方串通控制市场价格
D4. 价格歧视 — 同等条件不同价格
D5. 变相提高价格 — 抬高等级/以次充好

### E. 政府定价违规类
E1. 超政府指导价 — 超出政府指导价浮动范围
E2. 违反政府定价 — 高于或低于政府定价
E3. 自立收费项目 — 未经批准自设收费

### Z. 其他/复合
Z1. 多种违规复合 — 同时涉及多种违规类型
Z2. 其他价格违法 — 不属于以上任何类型

## 案件信息

### 违法事实:
{violation_facts}

### 法律分析:
{legal_analysis}

### 引用法条:
{citations}

## 请输出JSON格式:
{{
  "primary_type": "类型编码，如A1",
  "primary_type_name": "类型名称，如虚构原价",
  "secondary_types": ["如有其他涉及的违规类型编码"],
  "confidence": 0.95,
  "reasoning": "简要说明判断依据（50字以内）"
}}

仅输出JSON，不要其他内容。"""

    # 读取待分类案例
    results = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            results.append(json.loads(line.strip()))

    print(f"待分类案例: {len(results)}")
    classified = []

    for i, r in enumerate(results):
        prompt = CLASSIFY_PROMPT.format(
            violation_facts=r.get("violation_facts_preview", "（无）"),
            legal_analysis=r.get("legal_analysis_preview", "（无）"),
            citations=", ".join(r.get("citations", [])),
        )

        try:
            response = call_llm(prompt)
            # 尝试解析JSON
            json_match = re.search(r"\{[^{}]+\}", response, re.DOTALL)
            if json_match:
                classification = json.loads(json_match.group(0))
                r["llm_classification"] = classification
                print(f"  [{i+1}/{len(results)}] {r['file'][:30]} -> {classification.get('primary_type_name', '?')}")
            else:
                r["llm_classification"] = {"error": "无法解析LLM输出", "raw": response[:200]}
                print(f"  [{i+1}/{len(results)}] {r['file'][:30]} -> WARN 解析失败")
        except NotImplementedError:
            print("\nWARN LLM API 未配置！请编辑 call_llm() 函数")
            print("  或者将采样结果导出后手动分类")
            break
        except Exception as e:
            r["llm_classification"] = {"error": str(e)}
            print(f"  [{i+1}/{len(results)}] {r['file'][:30]} -> FAIL {str(e)[:50]}")

        classified.append(r)

    if classified:
        with open(args.output, "w", encoding="utf-8") as f:
            for c in classified:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"\n分类结果已保存至: {args.output}")


# ============================================================
# 9. CLI入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="从处罚文书PDF中发现和分类违规类型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # scan
    p_scan = subparsers.add_parser("scan", help="批量扫描PDF，提取法条引用和违规信号")
    p_scan.add_argument("--pdf_dir", required=True, help="PDF文件目录")
    p_scan.add_argument("--output", default="scan_results.jsonl", help="输出文件路径")

    # cluster
    p_cluster = subparsers.add_parser("cluster", help="聚类分析，生成违规类型分布")
    p_cluster.add_argument("--input", required=True, help="scan输出的JSONL文件")
    p_cluster.add_argument("--output", default="cluster_report.json", help="聚类报告输出路径")

    # sample
    p_sample = subparsers.add_parser("sample", help="分层采样典型案例")
    p_sample.add_argument("--input", required=True, help="scan输出的JSONL文件")
    p_sample.add_argument("--clusters", help="cluster报告（可选）")
    p_sample.add_argument("--per_cluster", type=int, default=8, help="每类抽样数量")
    p_sample.add_argument("--output", default="sampled_cases.jsonl", help="采样结果输出路径")

    # llm_classify
    p_llm = subparsers.add_parser("llm_classify", help="用LLM精细分类")
    p_llm.add_argument("--input", required=True, help="采样JSONL文件")
    p_llm.add_argument("--output", default="classified_cases.jsonl", help="分类结果输出路径")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "cluster":
        cmd_cluster(args)
    elif args.command == "sample":
        cmd_sample(args)
    elif args.command == "llm_classify":
        cmd_llm_classify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
