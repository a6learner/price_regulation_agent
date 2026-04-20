"""运行PDF提取工具"""
import sys
from pathlib import Path

# 添加src目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

# 设置工作目录
import os
os.chdir(str(current_dir))

# 导入并运行
from data_collection.pdf_extractor import PDFExtractor, main

if __name__ == "__main__":
    main()

