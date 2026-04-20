# PDF结构化信息提取指南

## 🚀 快速开始

### 1. 安装依赖

```bash
cd price_regulation_agent
pip install -r requirements.txt
```

**主要依赖**:
- `pdfplumber`: PDF文本提取
- `pandas`: 数据处理
- `beautifulsoup4`: HTML解析（用于后续数据采集）

### 2. 运行提取工具

```bash
cd src/data_collection
python pdf_extractor.py
```

#### 可选：指定任意PDF目录（推荐）

你的 `files` 目录文件名是否“有意义”无所谓，只要是 PDF 就能提取。示例（PowerShell / CMD 都可用，注意路径加引号）：

```bash
python pdf_extractor.py ^
  --pdf-dir "D:\pdd\project\毕设\数据\电商\电商-文件\2026_02_06_14_47_28\files" ^
  --csv-file "D:\pdd\project\毕设\数据\电商\电商-基本信息\133处罚文书基本信息-价格-网店.csv" ^
  --output-dir "..\..\data\processed" ^
  --case-id-mode case_number
```

常用参数：
- `--pdf-dir`: PDF所在目录（必看）
- `--csv-file`: 基本信息CSV（可选）
- `--output-dir`: 输出目录
- `--case-id-mode`: `stem`（默认）/ `index` / `case_number`
- `--recursive`: 递归搜索PDF（子目录很多时用）

### 3. 查看结果

提取完成后，结果保存在：
- `data/processed/extracted_cases.json` - JSON格式（便于查看）
- `data/processed/extracted_cases.jsonl` - JSONL格式（便于后续处理）

## 📊 提取的字段

每条案例包含以下字段：

```json
{
  "case_id": "案例ID（文件名）",
  "case_number": "处罚决定书编号",
  "company_name": "被处罚企业名称",
  "violation_type": "违规类型（虚构原价/虚假折扣/价格误导/要素缺失/其他）",
  "violation_description": "违规事实描述",
  "law_references": ["法律条文引用列表"],
  "evidence": "证据描述",
  "penalty_amount": "处罚金额",
  "penalty_type": "处罚类型（罚款/警告等）",
  "region": "地区",
  "date": "处罚日期",
  "platform": "涉及平台（淘宝/京东/美团等）",
  "product_info": "涉及商品/服务信息",
  "price_info": "价格信息（划线价、现价、成交价等）",
  "full_text": "完整文本"
}
```

## 🔍 提取质量检查

提取完成后，工具会自动打印统计信息：

```
=== 提取统计 ===
总案例数: 133
违规类型分布:
  虚构原价: 45
  虚假折扣: 30
  价格误导: 25
  要素缺失: 20
  其他: 13

平台分布:
  淘宝: 50
  京东: 30
  美团: 25
  携程: 20
  其他: 8
```

## ⚠️ 注意事项

1. **提取可能不完美**: PDF格式多样，提取结果可能需要人工检查
2. **CSV补充信息**: 工具会自动从CSV文件中补充基本信息
3. **编码问题**: 如果遇到编码错误，检查PDF文件编码

## 🛠️ 手动修正

如果提取结果有误，可以：

1. **查看完整文本**: 检查`full_text`字段
2. **手动修正**: 编辑JSON文件
3. **重新提取**: 修改提取逻辑后重新运行

## 📝 下一步

提取完成后，下一步是：
1. 检查提取质量
2. 转换为CoT训练集格式
3. 构建知识库

详见：[实施路线图](../docs/实施路线图.md)

