#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接运行PDF提取工具"""
import sys
import os
from pathlib import Path

# 获取当前脚本所在目录
BASE_DIR = Path(__file__).parent.absolute()

# 添加src目录到Python路径
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

# 切换到项目根目录
os.chdir(str(BASE_DIR))

# 导入并运行
try:
    from data_collection.pdf_extractor import PDFExtractor
    
    print("=" * 60)
    print("开始提取PDF结构化信息...")
    print("=" * 60)
    
    # PDF目录
    pdf_dir = BASE_DIR / "data" / "raw" / "cases" / "133处罚文书-价格-网店"
    csv_file = BASE_DIR / "data" / "raw" / "cases" / "133处罚文书基本信息-价格-网店.csv"
    output_dir = BASE_DIR / "data" / "processed"
    
    print(f"\nPDF目录: {pdf_dir}")
    print(f"CSV文件: {csv_file}")
    print(f"输出目录: {output_dir}\n")
    
    # 检查PDF目录
    if not pdf_dir.exists():
        print(f"错误: PDF目录不存在: {pdf_dir}")
        sys.exit(1)
    
    pdf_count = len(list(pdf_dir.glob("*.pdf")))
    print(f"找到 {pdf_count} 个PDF文件\n")
    
    # 创建提取器
    extractor = PDFExtractor(
        pdf_dir=str(pdf_dir),
        output_dir=str(output_dir),
        csv_file=str(csv_file) if csv_file.exists() else None
    )
    
    # 批量提取
    print("开始提取...")
    cases = extractor.batch_extract()
    
    # 保存结果
    print("\n保存结果...")
    extractor.save_to_json(cases, "extracted_cases.json")
    extractor.save_to_jsonl(cases, "extracted_cases.jsonl")
    
    # 打印统计信息
    print("\n" + "=" * 60)
    print("提取完成！")
    print("=" * 60)
    print(f"\n总案例数: {len(cases)}")
    
    print("\n违规类型分布:")
    violation_types = {}
    for case in cases:
        vtype = case.violation_type or '未知'
        violation_types[vtype] = violation_types.get(vtype, 0) + 1
    for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
        print(f"  {vtype}: {count}")
    
    print("\n平台分布:")
    platforms = {}
    for case in cases:
        platform = case.platform or '未知'
        platforms[platform] = platforms.get(platform, 0) + 1
    for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
        print(f"  {platform}: {count}")
    
    print(f"\n结果已保存到: {output_dir}")
    print("=" * 60)
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("\n请先安装依赖:")
    print("  pip install pdfplumber pandas")
    sys.exit(1)
except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

