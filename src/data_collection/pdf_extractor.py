"""
PDF处罚文书结构化信息提取工具
从PDF文件中提取：违规类型、法条引用、事实描述、处罚结果等结构化信息
"""

try:
    import pdfplumber
except ImportError:
    print("警告: 未安装pdfplumber，请运行: pip install pdfplumber")
    pdfplumber = None

import argparse
import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CaseInfo:
    """案例结构化信息"""
    case_id: str  # 案例编号/文件名
    case_number: Optional[str] = None  # 处罚决定书编号
    company_name: Optional[str] = None  # 被处罚企业名称
    violation_type: Optional[str] = None  # 违规类型
    violation_description: Optional[str] = None  # 违规事实描述
    law_references: List[str] = None  # 法律条文引用列表
    evidence: Optional[str] = None  # 证据描述
    penalty_amount: Optional[str] = None  # 处罚金额
    penalty_type: Optional[str] = None  # 处罚类型（罚款/警告等）
    region: Optional[str] = None  # 地区
    date: Optional[str] = None  # 处罚日期
    platform: Optional[str] = None  # 涉及平台（淘宝/京东/美团等）
    product_info: Optional[str] = None  # 涉及商品/服务信息
    price_info: Optional[str] = None  # 价格信息（划线价、现价、成交价等）
    full_text: Optional[str] = None  # 完整文本（用于后续处理）
    
    def __post_init__(self):
        if self.law_references is None:
            self.law_references = []


class PDFExtractor:
    """PDF文本提取和结构化解析"""
    
    def __init__(self, pdf_dir: str, output_dir: str = None, csv_file: str = None):
        """
        Args:
            pdf_dir: PDF文件目录
            output_dir: 输出目录
            csv_file: CSV基本信息文件（可选，用于补充信息）
        """
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir) if output_dir else self.pdf_dir.parent / "processed"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载CSV基本信息（如果提供）
        self.csv_info = {}
        if csv_file and Path(csv_file).exists():
            self._load_csv_info(csv_file)
        
        # 法律条文模式
        self.law_patterns = [
            r'《([^》]+)》第([一二三四五六七八九十百]+|[0-9]+)条',
            r'《([^》]+)》第([0-9]+)条第([一二三四五六七八九十]+|[0-9]+)项',
            r'《([^》]+)》第([0-9]+)款',
            r'《([^》]+)》',
        ]
        
        # 违规类型关键词
        self.violation_keywords = {
            '虚构原价': ['虚构原价', '虚标原价', '虚构划线价', '虚标划线价', '被比较价格不真实', '无成交记录'],
            '虚假折扣': ['虚假折扣', '虚假优惠', '虚假促销', '虚假降价', '虚假折价'],
            '价格误导': ['价格误导', '价格欺诈', '误导性价格', '虚假价格比较'],
            '要素缺失': ['未明码标价', '未标示', '要素不全', '价格要素缺失', '未标明'],
            '其他': []
        }
        
        # 平台关键词
        self.platform_keywords = {
            '淘宝': ['淘宝', '天猫', 'taobao'],
            '京东': ['京东', 'jd.com', 'JD'],
            '美团': ['美团', 'meituan'],
            '携程': ['携程', 'ctrip'],
            '拼多多': ['拼多多', 'pdd'],
            '抖音': ['抖音', 'douyin', 'TikTok'],
            '快手': ['快手', 'kuaishou']
        }
    
    def _load_csv_info(self, csv_file: str):
        """从CSV文件加载基本信息"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    case_number = row.get('文书编号', '').strip()
                    if case_number:
                        self.csv_info[case_number] = {
                            'company_name': row.get('当事人名称', '').strip(),
                            'penalty_content': row.get('处罚内容', '').strip(),
                            'penalty_date': row.get('处罚日期', '').strip(),
                            'penalty_org': row.get('处罚机关', '').strip(),
                        }
            logger.info(f"从CSV加载了{len(self.csv_info)}条基本信息")
        except Exception as e:
            logger.warning(f"加载CSV信息失败: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """从PDF提取文本"""
        if pdfplumber is None:
            logger.error("pdfplumber未安装，无法提取PDF文本")
            return ""
        
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"提取PDF文本失败 {pdf_path}: {str(e)}")
            return ""
    
    def extract_law_references(self, text: str) -> List[str]:
        """提取法律条文引用"""
        references = []
        
        for pattern in self.law_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                ref = match.group(0)
                if ref not in references:
                    references.append(ref)
        
        return references
    
    def classify_violation_type(self, text: str) -> str:
        """分类违规类型"""
        text_lower = text.lower()
        
        for vtype, keywords in self.violation_keywords.items():
            if vtype == '其他':
                continue
            for keyword in keywords:
                if keyword in text:
                    return vtype
        
        return '其他'
    
    def extract_platform(self, text: str) -> Optional[str]:
        """提取涉及平台"""
        for platform, keywords in self.platform_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return platform
        return None
    
    def extract_case_number(self, text: str) -> Optional[str]:
        """提取处罚决定书编号"""
        # 常见格式：XX市监处罚〔2024〕XX号
        patterns = [
            r'[^市监]*市监[^〔]*〔[0-9]{4}〕[0-9]+号',
            r'处罚[^〔]*〔[0-9]{4}〕[0-9]+号',
            r'〔[0-9]{4}〕[0-9]+号',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:500])  # 在前500字符中查找
            if match:
                return match.group(0)
        return None
    
    def extract_company_name(self, text: str) -> Optional[str]:
        """提取被处罚企业名称"""
        # 常见格式：当事人：XXX公司
        patterns = [
            r'当事人[：:]\s*([^\n]+)',
            r'被处罚人[：:]\s*([^\n]+)',
            r'当事人名称[：:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:1000])
            if match:
                name = match.group(1).strip()
                # 清理常见后缀
                name = re.sub(r'[（(].*?[）)]', '', name)
                return name[:50]  # 限制长度
        return None
    
    def extract_penalty_info(self, text: str) -> tuple:
        """提取处罚信息"""
        # 处罚金额
        penalty_patterns = [
            r'罚款[人民币]*([0-9,，]+)[元万元]',
            r'处罚款[人民币]*([0-9,，]+)[元万元]',
            r'([0-9,，]+)[元万元]的罚款',
        ]
        
        penalty_amount = None
        for pattern in penalty_patterns:
            match = re.search(pattern, text)
            if match:
                penalty_amount = match.group(1).replace(',', '').replace('，', '')
                break
        
        # 处罚类型
        penalty_type = None
        if '警告' in text:
            penalty_type = '警告'
        elif '罚款' in text or penalty_amount:
            penalty_type = '罚款'
        elif '责令改正' in text:
            penalty_type = '责令改正'
        
        return penalty_amount, penalty_type
    
    def extract_price_info(self, text: str) -> Optional[str]:
        """提取价格相关信息"""
        # 查找价格相关描述
        price_patterns = [
            r'划线价[：:]\s*([0-9,，.]+)[元]',
            r'原价[：:]\s*([0-9,，.]+)[元]',
            r'现价[：:]\s*([0-9,，.]+)[元]',
            r'成交价[：:]\s*([0-9,，.]+)[元]',
            r'([0-9,，.]+)[元].*?([0-9,，.]+)[元]',  # 价格对比
        ]
        
        price_info = []
        for pattern in price_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                price_info.append(match.group(0))
        
        if price_info:
            return '；'.join(price_info[:5])  # 最多保留5条
        return None
    
    def extract_region(self, text: str) -> Optional[str]:
        """提取地区信息"""
        # 从处罚决定书编号或文本中提取
        case_number = self.extract_case_number(text)
        if case_number:
            # 提取城市名（通常在编号开头）
            match = re.search(r'^([^市监]+)市监', case_number)
            if match:
                return match.group(1) + '市'
        
        # 从文本中查找
        region_patterns = [
            r'([^省]+省[^市]+市)',
            r'([^市]+市[^区]+区)',
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, text[:500])
            if match:
                return match.group(1)
        
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """提取处罚日期"""
        date_patterns = [
            r'([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日',
            r'([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    def parse_case(self, pdf_path: Path) -> CaseInfo:
        """解析单个PDF案例"""
        case_id = pdf_path.stem
        
        # 提取文本
        full_text = self.extract_text_from_pdf(pdf_path)
        if not full_text:
            logger.warning(f"无法提取文本: {pdf_path}")
            return CaseInfo(case_id=case_id, full_text="")
        
        # 提取结构化信息
        case_number = self.extract_case_number(full_text)
        case_info = CaseInfo(
            case_id=case_id,
            case_number=case_number,
            company_name=self.extract_company_name(full_text),
            violation_type=self.classify_violation_type(full_text),
            law_references=self.extract_law_references(full_text),
            platform=self.extract_platform(full_text),
            price_info=self.extract_price_info(full_text),
            region=self.extract_region(full_text),
            date=self.extract_date(full_text),
            full_text=full_text
        )
        
        # 从CSV补充信息（如果可用）
        if case_number and case_number in self.csv_info:
            csv_data = self.csv_info[case_number]
            if not case_info.company_name and csv_data.get('company_name'):
                case_info.company_name = csv_data['company_name']
            if not case_info.date and csv_data.get('penalty_date'):
                case_info.date = csv_data['penalty_date']
            if csv_data.get('penalty_content'):
                # 从处罚内容中提取更多信息
                penalty_content = csv_data['penalty_content']
                if not case_info.penalty_amount:
                    amount, ptype = self.extract_penalty_info(penalty_content)
                    case_info.penalty_amount = amount
                    case_info.penalty_type = ptype
        
        # 提取处罚信息
        if not case_info.penalty_amount:
            penalty_amount, penalty_type = self.extract_penalty_info(full_text)
            case_info.penalty_amount = penalty_amount
            case_info.penalty_type = penalty_type
        
        # 提取违规事实描述（优先从"违法事实"或"经查"部分提取一整个事实段落）
        #
        # 典型格式：
        #   经查，……（事实经过若干句）……违法所得共计：XXXX元。
        #   上述事实，主要有以下证据证明：……
        #
        # 因此这里采用“从标题词开始，一直到‘上述事实 / 以上事实 / 本局认为’等转折语之前”的非贪婪匹配，
        # 尽量把完整事实段落提取出来，而不是只取第一句。
        violation_section_patterns = [
            # 从“违法事实：”开始，到“上述事实/以上事实/本局认为/本机关认为”等转折语之前
            r'违法事实[：:]\s*([\s\S]*?)(?:上述事实|以上事实|本局认为|本机关认为)',
            # 从“经查，”开始，到转折语之前
            r'经查[，,]?\s*([\s\S]*?)(?:上述事实|以上事实|本局认为|本机关认为)',
            # 兜底：从“当事人…”开头的一大段事实描述，到转折语之前
            r'当事人[：:，,。\s]*([\s\S]*?)(?:上述事实|以上事实|本局认为|本机关认为)',
        ]

        for pattern in violation_section_patterns:
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                # 适当放宽长度限制，避免截断关键信息
                desc = match.group(1).strip()[:800]
                case_info.violation_description = desc
                break
        
        return case_info
    
    def batch_extract(
        self,
        pdf_files: List[Path] = None,
        case_id_mode: str = "stem",
    ) -> List[CaseInfo]:
        """批量提取PDF信息"""
        if pdf_files is None:
            pdf_files = sorted(self.pdf_dir.glob("*.pdf"))
        
        logger.info(f"开始批量提取，共{len(pdf_files)}个PDF文件")
        
        cases = []
        for idx, pdf_path in enumerate(pdf_files, 1):
            try:
                logger.info(f"[{idx}/{len(pdf_files)}] 处理: {pdf_path.name}")
                case_info = self.parse_case(pdf_path)
                if case_id_mode == "index":
                    case_info.case_id = f"{idx:04d}"
                elif case_id_mode == "case_number" and case_info.case_number:
                    case_info.case_id = case_info.case_number
                cases.append(case_info)
            except Exception as e:
                logger.error(f"处理失败 {pdf_path}: {str(e)}")
                continue
        
        logger.info(f"提取完成，共成功提取{len(cases)}个案例")
        return cases
    
    def save_to_json(self, cases: List[CaseInfo], filename: str = "extracted_cases.json"):
        """保存为JSON格式"""
        output_path = self.output_dir / filename
        
        # 转换为字典列表
        cases_dict = [asdict(case) for case in cases]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cases_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存到: {output_path}")
        return output_path
    
    def save_to_jsonl(self, cases: List[CaseInfo], filename: str = "extracted_cases.jsonl"):
        """保存为JSONL格式（用于后续处理）"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for case in cases:
                f.write(json.dumps(asdict(case), ensure_ascii=False) + '\n')
        
        logger.info(f"已保存到: {output_path}")
        return output_path


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent.parent

    default_pdf_dir = project_root / "data" / "raw" / "cases" / "133处罚文书-价格-网店"
    default_csv_file = project_root / "data" / "raw" / "cases" / "133处罚文书基本信息-价格-网店.csv"
    default_output_dir = project_root / "data" / "processed"

    parser = argparse.ArgumentParser(description="PDF处罚文书结构化信息提取工具")
    parser.add_argument(
        "--pdf-dir",
        default=str(default_pdf_dir),
        help="PDF文件目录（默认使用项目内置样例目录）",
    )
    parser.add_argument(
        "--csv-file",
        default=str(default_csv_file) if default_csv_file.exists() else "",
        help="CSV基本信息文件（可选；默认使用项目内置CSV，如不存在则跳过）",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir),
        help="输出目录（默认 data/processed）",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="递归搜索PDF（默认仅扫描 pdf-dir 顶层的 *.pdf）",
    )
    parser.add_argument(
        "--case-id-mode",
        choices=["stem", "index", "case_number"],
        default="stem",
        help="case_id 生成方式：stem=文件名（默认）；index=按处理顺序编号；case_number=提取到文书编号则使用文书编号",
    )
    parser.add_argument(
        "--json-name",
        default="extracted_cases.json",
        help="输出JSON文件名",
    )
    parser.add_argument(
        "--jsonl-name",
        default="extracted_cases.jsonl",
        help="输出JSONL文件名",
    )
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    output_dir = Path(args.output_dir)
    csv_file = args.csv_file.strip() or None

    extractor = PDFExtractor(
        pdf_dir=str(pdf_dir),
        output_dir=str(output_dir),
        csv_file=csv_file if csv_file and Path(csv_file).exists() else None,
    )

    pdf_files = sorted(pdf_dir.rglob("*.pdf") if args.recursive else pdf_dir.glob("*.pdf"))
    cases = extractor.batch_extract(pdf_files=pdf_files, case_id_mode=args.case_id_mode)

    extractor.save_to_json(cases, args.json_name)
    extractor.save_to_jsonl(cases, args.jsonl_name)
    
    # 打印统计信息
    print("\n=== 提取统计 ===")
    print(f"总案例数: {len(cases)}")
    print(f"违规类型分布:")
    violation_types = {}
    for case in cases:
        vtype = case.violation_type or '未知'
        violation_types[vtype] = violation_types.get(vtype, 0) + 1
    for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
        print(f"  {vtype}: {count}")
    
    print(f"\n平台分布:")
    platforms = {}
    for case in cases:
        platform = case.platform or '未知'
        platforms[platform] = platforms.get(platform, 0) + 1
    for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
        print(f"  {platform}: {count}")


if __name__ == "__main__":
    main()

