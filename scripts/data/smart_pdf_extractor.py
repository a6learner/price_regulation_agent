#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smart_pdf_extractor.py
======================
电商价格合规分析系统 — 市场监管处罚文书智能提取工具
Market Regulation Penalty Document Intelligent Extractor

用于从中国市场监管局行政处罚文书PDF中提取结构化信息，
构建无同源污染的黄金测试集。

USAGE / 使用方法:
-----------------

1. 测试单个PDF（验证提取效果）:
   python smart_pdf_extractor.py --mode test --pdf_dir ./sample_pdfs/

2. 批量Stage 1提取（纯规则，无LLM）:
   python smart_pdf_extractor.py \\
     --mode batch_stage1 \\
     --pdf_dir data/cases/791处罚文书/files/ \\
     --output data/golden/stage1_results.jsonl \\
     --min_score 0 \\
     --report data/golden/stage1_report.json

3. 批量Stage 2提取（LLM精细结构化，使用项目MaaS API）:
   python smart_pdf_extractor.py \\
     --mode batch_stage2 \\
     --input data/golden/stage1_results.jsonl \\
     --min_score 3 \\
     --output data/golden/stage2_results.jsonl \\
     --api_key YOUR_XUNFEI_MAAS_API_KEY \\
     --api_base https://maas-api.cn-huabei-1.xf-yun.com/v2 \\
     --model_id xopqwen35397b \\
     --report data/golden/stage2_report.json

   注意：Stage 2必须使用qwen 397B（xopqwen35397b），
         禁止使用qwen-8b（xop3qwen8b），因为qwen-8b是Baseline模型，
         用它生成测试集会引入同源污染。

4. 生成统计报告:
   python smart_pdf_extractor.py \\
     --mode report \\
     --input data/golden/stage1_results.jsonl \\
     --report data/golden/stage1_report.json

REQUIREMENTS / 依赖:
--------------------
Python 3.8+
pip install pdfplumber

Optional for Stage 2 (LLM API):
pip install requests

DESIGN NOTES / 设计说明:
-------------------------
- Stage 1: 纯规则提取，pdfplumber + 正则表达式，无API调用
  目标：快速获取结构骨架，评估质量，筛选合格文书

- Stage 2: LLM辅助精细结构化，调用讯飞星辰MaaS API
  目标：提取价格信息、违法类型分类、摘要生成
  注意：LLM只做结构化，不改写原始文本（避免同源污染）
  使用qwen 397B而非qwen-8b（后者是Baseline模型）

- 输出格式：JSONL（每行一个JSON对象，便于流式处理）
- Stage 1输出保留full_text字段（用于构建reference answer）

KNOWN LIMITATIONS / 已知局限:
------------------------------
- 扫描件PDF（非文字层）无法处理，需要OCR预处理
- PDF3类冗长法条重复格式：LLM摘要质量可能下降
- 极少数文书使用非标准段落标题，可能降低结构识别率
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 依赖检查 / Dependency check
# ============================================================
try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber未安装。请执行：pip install pdfplumber")
    print("[ERROR] pdfplumber not found. Run: pip install pdfplumber")
    sys.exit(1)

# ============================================================
# 常量定义 / Constants
# ============================================================

# 已知电商/O2O平台名称词典（用于平台识别）
KNOWN_PLATFORMS = [
    "拼多多", "淘宝", "天猫", "京东", "抖音", "抖音小店",
    "快手小店", "美团", "饿了么", "大众点评", "苏宁易购",
    "唯品会", "亚马逊", "当当", "微信小程序", "微店",
    "闲鱼", "转转", "贝壳", "链家", "58同城", "赶集网",
    "携程", "飞猪", "去哪儿",
]

# 违法行为类型关键词词典（用于初步分类）
VIOLATION_TYPE_KEYWORDS = {
    "虚构原价": [
        "虚构原价", "虚构市场价格", "虚构曾经价格",
        "从未以", "原价.*从未", "历史最低价",
        "无销售记录", "未曾以该价格", "虚假标价",
    ],
    "价格标示不实": [
        "首页.*标示.*价格", "主图.*价格.*低于", "详情页.*实际价格",
        "展示价格.*不一致", "标示价格.*高于", "付款.*实际价格",
        "标价.*不符", "价格不一致",
    ],
    "不明码标价": [
        "未明码标价", "不明码标价", "未按规定明码标价",
        "价格标签", "未标明", "未标注价格",
    ],
    "捆绑销售": [
        "强制搭售", "捆绑销售", "强制购买", "搭售",
    ],
    "价格欺诈": [
        "价格欺诈", "欺骗消费者", "虚假优惠", "虚假折扣",
        "谎称", "欺诈性价格", "误导消费者",
    ],
}

# 法律法规名称识别词典
LEGAL_ACTS = [
    r"《价格法》",
    r"《明码标价和禁止价格欺诈规定》",
    r"《价格违法行为行政处罚规定》",
    r"《消费者权益保护法》",
    r"《反不正当竞争法》",
    r"《行政处罚法》",
    r"《电子商务法》",
    r"《市场监督管理行政处罚程序规定》",
]

# ============================================================
# Stage 1: 规则提取模块 / Rule-based Extraction Module
# ============================================================

class PDFExtractor:
    """
    基于规则的PDF提取器 / Rule-based PDF extractor
    负责从PDF文本中识别结构、提取关键字段
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

        # 段落边界模式（按优先级排序）
        self.section_patterns = {
            "party_info": [
                r"当事人[:：]",
                r"名\s*称[:：]",
                r"被处罚当事人",
            ],
            "case_source": [
                r"(?:经|于)\s*\d{4}\s*年.{0,20}(?:接到|收到|接受)",
                r"(?:投诉|举报|转办|移送|检查发现)",
                r"案件来源",
                r"立案原因",
            ],
            "jingcha": [
                r"经\s*查[，,：:]",
                r"经\s*调\s*查[，,：:]",
                r"经\s*检\s*查[，,：:]",
                r"经\s*核\s*查[，,：:]",
            ],
            "evidence": [
                r"上述事实.{0,15}有以下证据",
                r"上述违法事实.{0,15}证据",
                r"以下证据.*证明",
                r"证据材料如下",
            ],
            "benju_renwei": [
                r"本局认为[，,：:]",
                r"本机关认为[，,：:]",
                r"执法机关认为[，,：:]",
            ],
            "sentencing": [
                r"鉴于当事人",
                r"考虑到当事人",
                r"从轻.{0,20}情节",
                r"减轻.{0,20}情节",
                r"从重.{0,20}情节",
                r"裁量基准",
            ],
            "penalty_decision": [
                r"依据.{5,80}决定.{0,10}(?:给予|作出|处以)",
                r"决定给予.*行政处罚",
                r"作出如下行政处罚决定",
                r"现依法处罚如下",
            ],
        }

    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int, bool]:
        """使用pdfplumber提取PDF全文"""
        try:
            full_text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text_parts.append(text)
            full_text = "\n".join(full_text_parts)

            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', full_text))
            if not has_chinese:
                if self.verbose:
                    print(f"  [WARN] {pdf_path}: 未检测到中文字符，可能是扫描件")
                return "", page_count, False

            return full_text, page_count, True

        except Exception as e:
            if self.verbose:
                print(f"  [ERROR] 提取失败 {pdf_path}: {e}")
            return "", 0, False

    def find_section(self, text: str, section_key: str) -> Optional[int]:
        """在文本中查找指定段落的起始位置"""
        patterns = self.section_patterns.get(section_key, [])
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.start()
        return None

    def extract_section_text(
        self, text: str, start_key: str, end_keys: List[str], max_length: int = 3000
    ) -> Optional[str]:
        """
        提取两个段落标题之间的文本内容

        注意：PDF3类型文书的"本局认为"段可能极长（法条全文重复多次），
        max_length参数可以防止提取过多冗余内容。
        """
        start_pos = self.find_section(text, start_key)
        if start_pos is None:
            return None

        end_pos = len(text)
        for end_key in end_keys:
            pos = self.find_section(text[start_pos + 10:], end_key)
            if pos is not None:
                candidate_end = start_pos + 10 + pos
                if candidate_end < end_pos:
                    end_pos = candidate_end

        section_text = text[start_pos:end_pos].strip()

        if len(section_text) > max_length:
            if self.verbose:
                print(f"  [INFO] 段落 '{start_key}' 被截断: {len(section_text)} -> {max_length} 字符")
            section_text = section_text[:max_length] + "...[已截断/truncated]"

        return section_text if section_text else None

    def extract_case_number(self, text: str) -> Optional[str]:
        """提取文书文号"""
        patterns = [
            r"[^\n]{2,20}(?:市监|监管|监察|市场).{0,10}[〔\[（(]\d{4}[〕\]）)]\d+号",
            r"[^\n]{2,20}处罚决定书\s*(?:文号)?[：:]\s*([^\n]+号)",
            r"[^\n]{2,20}[〔\[（(]\d{4}[〕\]）)][^\n]{1,10}号",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()[:80]
        return None

    def extract_party_name(self, text: str) -> Optional[str]:
        """提取当事人名称"""
        patterns = [
            r"名\s*称[：:]\s*([^\n\r，,]{3,50}(?:公司|商店|店铺|经营部|工作室|个人))",
            r"当事人[：:]\s*([^\n\r，,]{3,50}(?:公司|商店|店铺|经营部|工作室|个人))",
            r"被处罚(?:人|单位)[：:]\s*([^\n\r，,]{3,50})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def extract_credit_code(self, text: str) -> Optional[str]:
        """提取统一社会信用代码"""
        pattern = r"统一社会信用代码[：:]\s*([A-Z0-9]{18})"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        pattern2 = r"\b([A-Z][0-9A-Z]{17})\b"
        matches = re.findall(pattern2, text)
        if matches:
            return matches[0]
        return None

    def extract_legal_representative(self, text: str) -> Optional[str]:
        """提取法定代表人/负责人"""
        patterns = [
            r"法定代表人[（(]负责人[)）][：:]\s*([^\n\r，,；;]{2,20})",
            r"法定代表人[：:]\s*([^\n\r，,；;]{2,20})",
            r"负责人[：:]\s*([^\n\r，,；;]{2,20})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def extract_address(self, text: str) -> Optional[str]:
        """提取经营地址"""
        patterns = [
            r"(?:住所|地址|经营地址)[：:]\s*([^\n\r]{5,100}(?:号|楼|室|店))",
            r"(?:住所|地址|经营地址)[：:]\s*([^\n\r]{5,100})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()[:100]
        return None

    def extract_penalty_amount(self, text: str) -> Optional[str]:
        """提取罚款金额"""
        patterns = [
            r"罚款(?:人民币)?(\d{1,10}(?:\.\d{1,2})?)元",
            r"处(?:人民币)?(\d{1,10}(?:\.\d{1,2})?)元罚款",
            r"罚款(?:金额)?(?:人民币)?(\d{1,10}(?:,\d{3})*(?:\.\d{1,2})?)元",
        ]
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            amounts.extend(matches)

        if not amounts:
            return None

        try:
            max_amount = max(float(a.replace(",", "")) for a in amounts)
            return f"{max_amount:.2f}元" if "." in str(max_amount) else f"{int(max_amount)}元"
        except ValueError:
            return amounts[-1] + "元" if amounts else None

    def extract_confiscation_amount(self, text: str) -> Optional[str]:
        """提取没收违法所得金额"""
        patterns = [
            r"没收违法所得(?:人民币)?(\d{1,10}(?:\.\d{1,2})?)元",
            r"没收.{0,10}所得(?:人民币)?(\d{1,10}(?:\.\d{1,2})?)元",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) + "元"
        return None

    def extract_platform(self, text: str) -> Optional[str]:
        """提取涉及的电商/O2O平台"""
        for platform in KNOWN_PLATFORMS:
            if platform in text:
                return platform

        match = re.search(r"([\u4e00-\u9fff]{2,8}(?:网络)?平台)", text)
        if match:
            return match.group(1)

        return None

    def extract_legal_basis(self, text: str) -> List[str]:
        """
        提取法律依据引用

        注意：只提取条款引用（名称+条款号），不提取全文内容，
        防止PDF3类型冗长法条引起的冗余。
        """
        results = []
        pattern = r"《([^》]+)》第([一二三四五六七八九十百\d]+)条(?:第([一二三四五六七八九十\d]+)款)?"
        matches = re.finditer(pattern, text)
        seen = set()
        for m in matches:
            citation = m.group(0)
            if citation not in seen:
                seen.add(citation)
                results.append(citation)

        return results[:10]

    def extract_case_source(self, text: str) -> Optional[str]:
        """提取案件来源类型"""
        source_keywords = {
            "投诉": ["投诉", "消费者投诉", "接到投诉"],
            "举报": ["举报", "接到举报", "群众举报"],
            "主动检查": ["主动检查", "执法检查", "日常检查", "网络巡查", "专项检查"],
            "转办": ["转办", "移送", "上级交办", "交办"],
        }
        for source_type, keywords in source_keywords.items():
            for kw in keywords:
                if kw in text[:500]:
                    return source_type
        return "其他"

    def extract_mitigation_factors(self, text: str) -> Optional[str]:
        """提取量刑情节"""
        explicit_pattern = r"(?:鉴于|考虑到|考量)当事人.{10,300}(?:从轻|减轻|从重)处[罚理]"
        match = re.search(explicit_pattern, text, re.DOTALL)
        if match:
            return match.group(0)[:500]

        implicit_patterns = [
            r"(?:从轻|减轻).{0,50}处罚",
            r"(?:从重).{0,50}处罚",
        ]
        for pattern in implicit_patterns:
            match = re.search(pattern, text)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                return text[start:end].strip()

        return None

    def identify_violation_type_rule(self, text: str) -> str:
        """基于关键词规则初步判断违法行为类型（供Stage 2 LLM细化）"""
        scores = defaultdict(int)
        for vtype, keywords in VIOLATION_TYPE_KEYWORDS.items():
            for kw in keywords:
                if re.search(kw, text):
                    scores[vtype] += 1

        if not scores:
            return "其他"
        return max(scores, key=scores.get)

    def compute_quality_score(self, record: Dict) -> Tuple[int, List[str]]:
        """
        计算文书提取质量评分（0-5分）

        +1: 成功提取"经查"段（最重要的字段）
        +1: 成功提取"本局认为"段
        +1: 成功提取处罚决定段或罚款金额
        +1: 成功提取当事人名称
        +1: 成功提取法律依据
        """
        score = 0
        notes = []

        if record.get("jingcha_text") and len(record["jingcha_text"]) > 30:
            score += 1
        else:
            notes.append("缺少/过短: 经查段")

        if record.get("benju_renwei_text") and len(record["benju_renwei_text"]) > 30:
            score += 1
        else:
            notes.append("缺少/过短: 本局认为段")

        if record.get("penalty_amount") or (
            record.get("penalty_decision_text") and len(record["penalty_decision_text"]) > 20
        ):
            score += 1
        else:
            notes.append("缺少: 处罚决定/罚款金额")

        if record.get("party_name"):
            score += 1
        else:
            notes.append("缺少: 当事人名称")

        if record.get("legal_basis") and len(record["legal_basis"]) > 0:
            score += 1
        else:
            notes.append("缺少: 法律依据")

        return score, notes

    def extract_stage1(self, pdf_path: str) -> Dict[str, Any]:
        """Stage 1完整提取流程：文本提取 + 结构识别 + 字段提取 + 质量评分"""
        record: Dict[str, Any] = {
            "source_file": str(pdf_path),
            "filename": Path(pdf_path).name,
            "extraction_stage": 1,
            "extraction_success": False,
            "page_count": 0,
            "full_text": None,
            # 结构段落原文
            "party_info_text": None,
            "jingcha_text": None,
            "evidence_text": None,
            "benju_renwei_text": None,
            "sentencing_text": None,
            "penalty_decision_text": None,
            # 提取的结构化字段
            "case_number": None,
            "party_name": None,
            "credit_code": None,
            "legal_representative": None,
            "address": None,
            "platform": None,
            "penalty_amount": None,
            "confiscation_amount": None,
            "legal_basis": [],
            "case_source": None,
            "mitigation_factors": None,
            "violation_type_rule": None,
            # 质量评估
            "stage1_score": 0,
            "quality_notes": [],
            "extraction_errors": [],
        }

        full_text, page_count, success = self.extract_text_from_pdf(str(pdf_path))
        record["page_count"] = page_count

        if not success:
            record["extraction_errors"].append("PDF文本提取失败（可能是扫描件或加密文件）")
            return record

        record["full_text"] = full_text
        record["extraction_success"] = True

        # 段落结构识别与提取
        section_end_order = {
            "party_info": ["jingcha", "case_source", "evidence", "benju_renwei", "penalty_decision"],
            "jingcha": ["evidence", "benju_renwei", "sentencing", "penalty_decision"],
            "evidence": ["benju_renwei", "sentencing", "penalty_decision"],
            "benju_renwei": ["sentencing", "penalty_decision"],
            "sentencing": ["penalty_decision"],
            "penalty_decision": [],
        }

        for section, end_keys in section_end_order.items():
            max_len = 3000 if section == "benju_renwei" else 5000
            section_text = self.extract_section_text(full_text, section, end_keys, max_length=max_len)
            record[f"{section}_text"] = section_text

        # 结构化字段提取
        record["case_number"] = self.extract_case_number(full_text)
        record["party_name"] = self.extract_party_name(full_text)
        record["credit_code"] = self.extract_credit_code(full_text)
        record["legal_representative"] = self.extract_legal_representative(full_text)
        record["address"] = self.extract_address(full_text)
        record["platform"] = self.extract_platform(full_text)
        record["penalty_amount"] = self.extract_penalty_amount(full_text)
        record["confiscation_amount"] = self.extract_confiscation_amount(full_text)
        record["legal_basis"] = self.extract_legal_basis(full_text)
        record["case_source"] = self.extract_case_source(full_text)
        record["mitigation_factors"] = self.extract_mitigation_factors(full_text)
        record["violation_type_rule"] = self.identify_violation_type_rule(full_text)

        # 质量评分
        score, notes = self.compute_quality_score(record)
        record["stage1_score"] = score
        record["quality_notes"] = notes

        return record


# ============================================================
# Stage 2: LLM辅助精细提取 / LLM-assisted Fine Extraction
# ============================================================

def call_llm_api(
    prompt: str,
    api_key: str,
    api_base: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2",
    model: str = "xopqwen35397b",
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> Optional[str]:
    """
    调用讯飞星辰MaaS API进行LLM推理

    默认使用 qwen 397B（xopqwen35397b），禁止用 qwen-8b（xop3qwen8b），
    因为 qwen-8b 是 Baseline 模型，用它生成测试集会引入同源污染。

    Args:
        prompt: 完整的提示词
        api_key: API密钥
        api_base: API基础URL（默认讯飞MaaS）
        model: 模型ID（默认qwen 397B）
        temperature: 温度参数（低值=更稳定的JSON输出）
        max_tokens: 最大输出token数

    Returns:
        LLM响应文本，失败返回None
    """
    try:
        import requests
    except ImportError:
        print("[ERROR] requests库未安装。请执行：pip install requests")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一位专业的市场监管法律文书分析助手。"
                    "请严格按照JSON格式输出，不要添加额外说明。"
                    "提取的内容必须忠实于原文，不得改写或添加原文中没有的信息。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return None


def build_llm_prompt(record: Dict) -> str:
    """
    构建发送给LLM的结构化提取Prompt

    关键原则：LLM只做结构化，不改写原文。
    """
    jingcha = record.get("jingcha_text", "")[:1500] or "（未找到经查段）"
    benju_renwei = record.get("benju_renwei_text", "")[:800] or "（未找到本局认为段）"
    penalty_decision = record.get("penalty_decision_text", "")[:500] or "（未找到处罚决定段）"

    prompt = f"""请从以下行政处罚文书的关键段落中，提取结构化信息。

## 经查段（违法事实）:
{jingcha}

## 本局认为段（法律分析）:
{benju_renwei}

## 处罚决定段:
{penalty_decision}

请以JSON格式严格输出以下字段（所有值必须来源于原文，禁止改写或编造）：

{{
  "violation_type": "虚构原价|价格标示不实|不明码标价|捆绑销售|价格欺诈|其他",
  "original_price": "虚构原价金额（数字字符串）或null",
  "actual_price": "实际销售价格（数字字符串）或null",
  "discount_rate": "折扣率（如0.12表示1.2折）或null",
  "product_service": "涉案商品或服务名称（直接引用原文）",
  "platform": "涉及的电商或O2O平台名称",
  "violation_summary": "50-100字的违法行为摘要（必须使用原文语言，不得改写成口语化表述）",
  "legal_basis": ["引用的法律名称+条款，格式如：《价格法》第十四条第四项"],
  "mitigation_factors": "从轻或减轻处罚的情节描述（原文引用）或null",
  "aggravation_factors": "从重处罚的情节描述（原文引用）或null",
  "has_explicit_sentencing_section": true或false
}}

重要提示：
1. violation_summary必须是原文的精炼，不能是全新创作的表述
2. 如果某字段原文中没有明确信息，填null，不要推测
3. 只输出JSON，不要输出其他文字"""

    return prompt


def parse_llm_response(response_text: str) -> Optional[Dict]:
    """
    解析LLM返回的JSON响应（容错处理）

    LLM有时会在JSON外添加markdown代码块标记或多余文字，
    此函数处理这些常见的格式问题。
    """
    if not response_text:
        return None

    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def enrich_with_llm(
    record: Dict,
    api_key: str,
    api_base: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2",
    model_id: str = "xopqwen35397b",
    retry_count: int = 2,
    retry_delay: float = 1.0,
) -> Dict:
    """
    Stage 2: 用LLM精细结构化一条Stage 1记录

    Args:
        record: Stage 1输出的记录
        api_key: LLM API密钥
        api_base: API基础URL
        model_id: 模型ID（必须用qwen 397B，不能用qwen-8b）
        retry_count: 失败时重试次数
        retry_delay: 重试间隔秒数
    """
    record = record.copy()
    record["extraction_stage"] = 2
    record["llm_success"] = False
    record["llm_error"] = None

    prompt = build_llm_prompt(record)

    for attempt in range(retry_count + 1):
        response = call_llm_api(prompt, api_key, api_base=api_base, model=model_id)
        if response is None:
            if attempt < retry_count:
                time.sleep(retry_delay)
                continue
            record["llm_error"] = "API调用失败（超时或网络错误）"
            return record

        parsed = parse_llm_response(response)
        if parsed is None:
            if attempt < retry_count:
                time.sleep(retry_delay)
                continue
            record["llm_error"] = f"JSON解析失败，原始响应：{response[:200]}"
            return record

        llm_fields = [
            "violation_type", "original_price", "actual_price", "discount_rate",
            "product_service", "violation_summary", "mitigation_factors",
            "aggravation_factors", "has_explicit_sentencing_section",
        ]
        for field in llm_fields:
            if field in parsed:
                record[f"llm_{field}"] = parsed[field]

        if "legal_basis" in parsed and parsed["legal_basis"]:
            record["llm_legal_basis"] = parsed["legal_basis"]

        if "platform" in parsed and parsed["platform"]:
            record["platform_llm"] = parsed["platform"]

        record["llm_success"] = True
        record["llm_raw_response"] = response[:500]
        return record

    return record


# ============================================================
# 批量处理模块 / Batch Processing Module
# ============================================================

class BatchProcessor:
    """批量PDF处理器，支持Stage 1（纯规则）和Stage 2（LLM辅助）两种模式"""

    def __init__(self, verbose: bool = False):
        self.extractor = PDFExtractor(verbose=verbose)
        self.verbose = verbose

    def find_pdfs(self, pdf_dir: str) -> List[Path]:
        """递归查找目录下所有PDF文件"""
        pdf_path = Path(pdf_dir)
        if not pdf_path.exists():
            raise FileNotFoundError(f"目录不存在 / Directory not found: {pdf_dir}")

        pdfs = list(pdf_path.rglob("*.pdf")) + list(pdf_path.rglob("*.PDF"))
        pdfs.sort()
        return pdfs

    def batch_stage1(
        self,
        pdf_dir: str,
        output_path: str,
        min_score: int = 0,
        max_files: Optional[int] = None,
    ) -> Dict:
        """
        批量执行Stage 1提取

        注意：full_text 字段被保留在输出中，用于后续构建 reference answer。
        Stage 1 JSONL 文件会比较大（每份PDF约2-10KB全文），约5-50MB总量。
        """
        pdfs = self.find_pdfs(pdf_dir)
        if max_files:
            pdfs = pdfs[:max_files]

        total = len(pdfs)
        print(f"\n[Stage 1] 开始批量提取 / Starting batch extraction")
        print(f"[Stage 1] 发现PDF文件 / Found PDF files: {total}")
        print(f"[Stage 1] 输出文件 / Output file: {output_path}")
        print(f"[Stage 1] 最低分数过滤 / Min score filter: {min_score}")
        print("-" * 60)

        stats = {
            "total_pdfs": total,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "filtered_out": 0,
            "written": 0,
            "score_distribution": {str(i): 0 for i in range(6)},
            "field_fill_counts": defaultdict(int),
            "platform_distribution": Counter(),
            "violation_type_distribution": Counter(),
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, pdf_path in enumerate(pdfs, 1):
                if self.verbose or (i % 50 == 0):
                    print(f"  [{i}/{total}] 处理 / Processing: {pdf_path.name}")

                try:
                    record = self.extractor.extract_stage1(str(pdf_path))
                    stats["processed"] += 1

                    if record["extraction_success"]:
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1

                    score = record["stage1_score"]
                    stats["score_distribution"][str(score)] += 1

                    key_fields = [
                        "case_number", "party_name", "credit_code", "platform",
                        "penalty_amount", "jingcha_text", "benju_renwei_text",
                        "penalty_decision_text", "legal_basis",
                    ]
                    for field in key_fields:
                        val = record.get(field)
                        if val and val != [] and val != "":
                            stats["field_fill_counts"][field] += 1

                    if record.get("platform"):
                        stats["platform_distribution"][record["platform"]] += 1
                    if record.get("violation_type_rule"):
                        stats["violation_type_distribution"][record["violation_type_rule"]] += 1

                    if score < min_score:
                        stats["filtered_out"] += 1
                        continue

                    # 保留 full_text 字段（用于构建 reference answer）
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stats["written"] += 1

                except Exception as e:
                    stats["failed"] += 1
                    if self.verbose:
                        print(f"  [ERROR] 处理异常 {pdf_path.name}: {e}")
                        traceback.print_exc()

        if stats["success"] > 0:
            stats["field_fill_rates"] = {
                field: count / stats["success"]
                for field, count in stats["field_fill_counts"].items()
            }
        else:
            stats["field_fill_rates"] = {}

        stats["qualified_count"] = stats["written"]
        stats["platform_distribution"] = dict(stats["platform_distribution"].most_common(20))
        stats["violation_type_distribution"] = dict(
            stats["violation_type_distribution"].most_common()
        )
        del stats["field_fill_counts"]

        return stats

    def batch_stage2(
        self,
        input_path: str,
        output_path: str,
        api_key: str,
        api_base: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2",
        model_id: str = "xopqwen35397b",
        min_score: int = 3,
        delay_between_calls: float = 0.5,
    ) -> Dict:
        """
        批量执行Stage 2 LLM精细提取

        重要：必须使用 qwen 397B（xopqwen35397b），不能用 qwen-8b（xop3qwen8b）。
        qwen-8b 是 Baseline 模型，用它处理测试集会引入同源污染。

        Args:
            input_path: Stage 1输出的JSONL文件
            output_path: Stage 2输出的JSONL文件
            api_key: LLM API密钥
            api_base: API基础URL
            model_id: 模型ID（默认qwen 397B）
            min_score: 只处理score≥min_score的记录
            delay_between_calls: API调用间隔秒数
        """
        records = []
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        qualified = [r for r in records if r.get("stage1_score", 0) >= min_score]
        total = len(qualified)

        print(f"\n[Stage 2] 开始LLM精细提取 / Starting LLM fine extraction")
        print(f"[Stage 2] 合格记录数 / Qualified records: {total}")
        print(f"[Stage 2] 使用模型 / Model: {model_id}")
        print(f"[Stage 2] API端点 / API base: {api_base}")
        if "xop3qwen8b" in model_id:
            print(f"[Stage 2] ⚠️  警告：检测到qwen-8b模型！这会引入同源污染！")
            print(f"[Stage 2] ⚠️  请使用 --model_id xopqwen35397b")
        print("-" * 60)

        stats = {
            "total_input": len(records),
            "qualified": total,
            "llm_success": 0,
            "llm_failed": 0,
            "violation_type_distribution": Counter(),
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, record in enumerate(qualified, 1):
                if i % 20 == 0 or self.verbose:
                    print(f"  [{i}/{total}] LLM处理: {record.get('filename', 'unknown')}")

                enriched = enrich_with_llm(
                    record, api_key,
                    api_base=api_base,
                    model_id=model_id,
                )

                if enriched.get("llm_success"):
                    stats["llm_success"] += 1
                    vtype = enriched.get("llm_violation_type", "其他")
                    stats["violation_type_distribution"][vtype] += 1
                else:
                    stats["llm_failed"] += 1
                    if self.verbose:
                        print(f"  [WARN] LLM失败: {enriched.get('llm_error', '未知错误')}")

                f.write(json.dumps(enriched, ensure_ascii=False) + "\n")

                if delay_between_calls > 0 and i < total:
                    time.sleep(delay_between_calls)

        stats["llm_success_rate"] = stats["llm_success"] / total if total > 0 else 0
        stats["violation_type_distribution"] = dict(
            stats["violation_type_distribution"].most_common()
        )

        return stats


# ============================================================
# 统计报告模块 / Statistics Report Module
# ============================================================

def generate_statistics_report(input_path: str, output_path: Optional[str] = None) -> Dict:
    """对JSONL提取结果生成详细统计报告"""
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not records:
        print("[WARN] 输入文件为空")
        return {}

    total = len(records)
    stage = records[0].get("extraction_stage", 1)

    print(f"\n{'='*60}")
    print(f"  提取结果统计报告 / Extraction Statistics Report")
    print(f"  Stage {stage} | 记录总数 / Total records: {total}")
    print(f"{'='*60}")

    score_dist = Counter(r.get("stage1_score", 0) for r in records)
    print("\n[质量分数分布 / Quality Score Distribution]")
    for score in range(6):
        count = score_dist.get(score, 0)
        bar = "█" * int(count / total * 40) if total > 0 else ""
        print(f"  {score}分: {count:4d} ({count/total*100:5.1f}%) {bar}")

    qualified = sum(1 for r in records if r.get("stage1_score", 0) >= 3)
    print(f"\n  Score≥3合格数 / Qualified (score≥3): {qualified} ({qualified/total*100:.1f}%)")

    key_fields = {
        "case_number": "文书文号",
        "party_name": "当事人名称",
        "credit_code": "统一社会信用代码",
        "platform": "涉及平台",
        "penalty_amount": "罚款金额",
        "jingcha_text": "经查段",
        "benju_renwei_text": "本局认为段",
        "penalty_decision_text": "处罚决定段",
    }

    print("\n[字段填充率 / Field Fill Rates]")
    for field, label in key_fields.items():
        filled = sum(1 for r in records if r.get(field) and r[field] != [])
        rate = filled / total * 100
        bar = "█" * int(rate / 100 * 30)
        print(f"  {label:20s}: {filled:4d}/{total} ({rate:5.1f}%) {bar}")

    platforms = Counter(r.get("platform") for r in records if r.get("platform"))
    print("\n[平台分布 / Platform Distribution]")
    for platform, count in platforms.most_common(10):
        print(f"  {platform:15s}: {count:4d} ({count/total*100:.1f}%)")

    vtypes = Counter(r.get("violation_type_rule") for r in records if r.get("violation_type_rule"))
    print("\n[违法类型分布（规则判断）/ Violation Type Distribution (Rule-based)]")
    for vtype, count in vtypes.most_common():
        print(f"  {vtype:20s}: {count:4d} ({count/total*100:.1f}%)")

    if stage == 2:
        llm_success = sum(1 for r in records if r.get("llm_success"))
        print(f"\n[LLM精细提取成功率 / LLM Fine Extraction Success Rate]")
        print(f"  成功 / Success: {llm_success}/{total} ({llm_success/total*100:.1f}%)")

        llm_vtypes = Counter(
            r.get("llm_violation_type") for r in records if r.get("llm_violation_type")
        )
        print("\n[违法类型分布（LLM判断）/ Violation Type Distribution (LLM-based)]")
        for vtype, count in llm_vtypes.most_common():
            print(f"  {vtype:20s}: {count:4d} ({count/total*100:.1f}%)")

    print(f"\n{'='*60}\n")

    report = {
        "input_file": input_path,
        "total_records": total,
        "extraction_stage": stage,
        "qualified_count": qualified,
        "qualified_rate": qualified / total if total > 0 else 0,
        "score_distribution": dict(score_dist),
        "platform_distribution": dict(platforms.most_common(20)),
        "violation_type_distribution": dict(vtypes.most_common()),
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 报告已保存 / Report saved: {output_path}")

    return report


# ============================================================
# 测试模式 / Test Mode
# ============================================================

def run_test_mode(pdf_dir: str, output_path: str = "./test_output.jsonl"):
    """测试模式：对少量样本PDF进行详细输出"""
    extractor = PDFExtractor(verbose=True)
    pdfs = list(Path(pdf_dir).glob("*.pdf")) + list(Path(pdf_dir).glob("*.PDF"))

    if not pdfs:
        print(f"[ERROR] 目录中未找到PDF文件 / No PDF files found in: {pdf_dir}")
        return

    print(f"\n[TEST MODE] 测试 {len(pdfs)} 个PDF文件")
    print("=" * 60)

    results = []
    for pdf_path in pdfs[:5]:  # 测试模式最多处理5个
        print(f"\n处理 / Processing: {pdf_path.name}")
        print("-" * 40)

        record = extractor.extract_stage1(str(pdf_path))
        results.append(record)

        print(f"  页数 / Pages: {record['page_count']}")
        print(f"  提取成功 / Extraction success: {record['extraction_success']}")
        print(f"  质量分数 / Quality score: {record['stage1_score']}/5")
        print(f"  质量说明 / Quality notes: {record['quality_notes']}")
        print(f"  当事人 / Party: {record.get('party_name', 'N/A')}")
        print(f"  文书文号 / Case number: {record.get('case_number', 'N/A')}")
        print(f"  涉及平台 / Platform: {record.get('platform', 'N/A')}")
        print(f"  罚款金额 / Penalty: {record.get('penalty_amount', 'N/A')}")
        print(f"  法律依据 / Legal basis: {record.get('legal_basis', [])[:3]}")
        print(f"  违法类型（规则）/ Violation type (rule): {record.get('violation_type_rule', 'N/A')}")

        jc = record.get("jingcha_text")
        if jc:
            print(f"  经查段（前200字）/ Jingcha text (first 200 chars):")
            print(f"    {jc[:200]}...")
        else:
            print(f"  经查段 / Jingcha text: [未找到 / Not found]")

    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n[TEST MODE] 结果已保存 / Results saved: {output_path}")
    print(f"[TEST MODE] 成功提取 / Successfully extracted: "
          f"{sum(1 for r in results if r['extraction_success'])}/{len(results)}")


# ============================================================
# 命令行入口 / Command Line Interface
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="市场监管处罚文书PDF智能提取工具 / Market Regulation Penalty Document PDF Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  # 测试模式（单目录）
  python smart_pdf_extractor.py --mode test --pdf_dir data/cases/791处罚文书/files/

  # 批量Stage 1（输出保留full_text，用于reference answer）
  python smart_pdf_extractor.py --mode batch_stage1 \\
    --pdf_dir data/cases/791处罚文书/files/ \\
    --output data/golden/stage1_results.jsonl \\
    --min_score 0 --report data/golden/stage1_report.json

  # 批量Stage 2（必须用qwen 397B！）
  python smart_pdf_extractor.py --mode batch_stage2 \\
    --input data/golden/stage1_results.jsonl \\
    --output data/golden/stage2_results.jsonl \\
    --api_key YOUR_KEY \\
    --api_base https://maas-api.cn-huabei-1.xf-yun.com/v2 \\
    --model_id xopqwen35397b \\
    --report data/golden/stage2_report.json

  # 统计报告
  python smart_pdf_extractor.py --mode report --input data/golden/stage1_results.jsonl
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["test", "batch_stage1", "batch_stage2", "report"],
        required=True,
        help="运行模式 / Run mode",
    )
    parser.add_argument("--pdf_dir", help="PDF文件目录 / PDF files directory")
    parser.add_argument("--input", help="输入JSONL文件（Stage 2和report模式）/ Input JSONL file")
    parser.add_argument("--output", default="./extracted_output.jsonl", help="输出文件路径 / Output file path")
    parser.add_argument("--report", help="统计报告输出路径 / Statistics report output path")
    parser.add_argument("--min_score", type=int, default=3, help="最低质量分数过滤（默认3）/ Min quality score (default: 3)")
    parser.add_argument("--api_key", help="LLM API密钥（Stage 2必需）/ LLM API key (required for Stage 2)")
    parser.add_argument(
        "--api_base",
        default="https://maas-api.cn-huabei-1.xf-yun.com/v2",
        help="API基础URL（默认讯飞MaaS）/ API base URL (default: iFlytek MaaS)"
    )
    parser.add_argument(
        "--model_id",
        default="xopqwen35397b",
        help="LLM模型ID（默认qwen 397B，禁止用qwen-8b）/ Model ID (default: qwen 397B, do NOT use qwen-8b)"
    )
    parser.add_argument("--max_files", type=int, help="最多处理文件数（用于测试）/ Max files to process")
    parser.add_argument("--delay", type=float, default=0.5, help="API调用间隔秒数（默认0.5）/ Delay between API calls (default: 0.5)")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志 / Show verbose logs")

    args = parser.parse_args()

    if args.mode == "test":
        if not args.pdf_dir:
            parser.error("--mode test 需要 --pdf_dir 参数")
        run_test_mode(args.pdf_dir, args.output)

    elif args.mode == "batch_stage1":
        if not args.pdf_dir:
            parser.error("--mode batch_stage1 需要 --pdf_dir 参数")
        processor = BatchProcessor(verbose=args.verbose)
        stats = processor.batch_stage1(
            pdf_dir=args.pdf_dir,
            output_path=args.output,
            min_score=args.min_score,
            max_files=args.max_files,
        )
        print("\n[Stage 1完成 / Stage 1 Complete]")
        print(f"  总处理 / Total processed: {stats['processed']}")
        print(f"  成功 / Success: {stats['success']}")
        print(f"  失败 / Failed: {stats['failed']}")
        print(f"  写入记录 / Written records: {stats['written']}")
        print(f"  分数分布 / Score distribution: {stats['score_distribution']}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n[INFO] 统计报告已保存 / Statistics report saved: {args.report}")

    elif args.mode == "batch_stage2":
        if not args.input:
            parser.error("--mode batch_stage2 需要 --input 参数")
        if not args.api_key:
            parser.error("--mode batch_stage2 需要 --api_key 参数")
        processor = BatchProcessor(verbose=args.verbose)
        stats = processor.batch_stage2(
            input_path=args.input,
            output_path=args.output,
            api_key=args.api_key,
            api_base=args.api_base,
            model_id=args.model_id,
            min_score=args.min_score,
            delay_between_calls=args.delay,
        )
        print("\n[Stage 2完成 / Stage 2 Complete]")
        print(f"  LLM成功率 / LLM success rate: {stats['llm_success_rate']*100:.1f}%")
        print(f"  违法类型分布 / Violation type distribution: {stats['violation_type_distribution']}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n[INFO] 统计报告已保存 / Statistics report saved: {args.report}")

    elif args.mode == "report":
        if not args.input:
            parser.error("--mode report 需要 --input 参数")
        generate_statistics_report(args.input, args.report)


if __name__ == "__main__":
    main()
