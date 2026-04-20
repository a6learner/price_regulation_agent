"""
快速开始脚本
一键运行PDF提取和数据采集准备
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("=" * 60)
    print("电商价格合规监管智能体 - 快速开始")
    print("=" * 60)
    
    print("\n📋 当前任务:")
    print("1. 提取133份PDF处罚文书的结构化信息")
    print("2. 准备商品数据采集方案")
    
    print("\n🔧 步骤1: 检查依赖...")
    try:
        import pdfplumber
        print("✅ pdfplumber 已安装")
    except ImportError:
        print("❌ pdfplumber 未安装")
        print("   请运行: pip install pdfplumber")
        return
    
    print("\n📂 步骤2: 检查数据目录...")
    pdf_dir = Path(__file__).parent / "data" / "raw" / "cases" / "133处罚文书-价格-网店"
    if pdf_dir.exists():
        pdf_count = len(list(pdf_dir.glob("*.pdf")))
        print(f"✅ 找到 {pdf_count} 个PDF文件")
    else:
        print(f"❌ PDF目录不存在: {pdf_dir}")
        return
    
    csv_file = Path(__file__).parent / "data" / "raw" / "cases" / "133处罚文书基本信息-价格-网店.csv"
    if csv_file.exists():
        print("✅ 找到CSV基本信息文件")
    else:
        print("⚠️  CSV基本信息文件不存在（可选）")
    
    print("\n🚀 步骤3: 开始提取PDF结构化信息...")
    print("   这可能需要几分钟时间，请耐心等待...")
    
    try:
        from data_collection.pdf_extractor import PDFExtractor
        
        extractor = PDFExtractor(
            pdf_dir=str(pdf_dir),
            output_dir=str(Path(__file__).parent / "data" / "processed"),
            csv_file=str(csv_file) if csv_file.exists() else None
        )
        
        cases = extractor.batch_extract()
        
        # 保存结果
        extractor.save_to_json(cases, "extracted_cases.json")
        extractor.save_to_jsonl(cases, "extracted_cases.jsonl")
        
        print("\n✅ 提取完成！")
        print(f"   共提取 {len(cases)} 个案例")
        print(f"   结果保存在: data/processed/")
        
        # 打印统计
        print("\n📊 统计信息:")
        violation_types = {}
        platforms = {}
        for case in cases:
            vtype = case.violation_type or '未知'
            violation_types[vtype] = violation_types.get(vtype, 0) + 1
            platform = case.platform or '未知'
            platforms[platform] = platforms.get(platform, 0) + 1
        
        print("\n违规类型分布:")
        for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
            print(f"  {vtype}: {count}")
        
        print("\n平台分布:")
        for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
            print(f"  {platform}: {count}")
        
    except Exception as e:
        print(f"\n❌ 提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ 完成！下一步:")
    print("1. 检查提取结果: data/processed/extracted_cases.json")
    print("2. 查看实施路线图: docs/实施路线图.md")
    print("3. 开始构建CoT训练集")
    print("=" * 60)


if __name__ == "__main__":
    main()

