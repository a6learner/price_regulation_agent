# 多模型评估系统使用指南

## 概述

新的评估系统支持：
- ✅ 灵活添加新模型
- ✅ 增量评估（避免重复）
- ✅ 多模型对比（支持N个模型）
- ✅ 命令行参数控制
- ✅ 法律依据和推理质量评估

---

## 快速开始

### 1. 查看所有可用模型

```bash
python scripts/run_baseline_eval.py --list-models
```

**输出示例**:
```
可用模型列表:
======================================================================
Key             Name                           Type       Has Result
----------------------------------------------------------------------
qwen            Qwen3.5-397B-A17B              baseline   [有结果]
minimax         MiniMax-M2.5                   baseline   [有结果]
======================================================================
```

### 2. 评估单个模型

```bash
# 评估Qwen模型
python scripts/run_baseline_eval.py --models qwen

# 限制案例数量（测试）
python scripts/run_baseline_eval.py --models qwen --limit 5
```

### 3. 对比现有结果（不重新评估）

```bash
python scripts/run_baseline_eval.py --compare-only --models qwen,minimax
```

**生成**: `results/baseline/multi_model_comparison.md`

### 4. 添加新模型并评估

**步骤1**: 编辑 `configs/model_config.yaml`

```yaml
models:
  qwen:
    model_id: "xopqwen35397b"
    name: "Qwen3.5-397B-A17B"
    type: baseline
    max_tokens: 2048
    temperature: 0.7

  minimax:
    model_id: "xminimaxm25"
    name: "MiniMax-M2.5"
    type: baseline
    max_tokens: 2048
    temperature: 0.7

  # 新增小模型
  qwen7b:
    model_id: "qwen2.5-7b-instruct"  # 填写实际model_id
    name: "Qwen2.5-7B"
    type: baseline
    max_tokens: 2048
    temperature: 0.7
```

**步骤2**: 评估新模型

```bash
# 方式1：只评估新模型
python scripts/run_baseline_eval.py --models qwen7b

# 方式2：评估所有模型（跳过已有结果）
python scripts/run_baseline_eval.py --all --skip-existing
```

**步骤3**: 生成三模型对比报告

```bash
python scripts/run_baseline_eval.py --compare-only --models qwen,minimax,qwen7b
```

---

## 常用命令

### 增量评估（推荐）

```bash
# 评估所有模型，跳过已有结果的模型
python scripts/run_baseline_eval.py --all --skip-existing
```

**场景**: 添加了新模型qwen7b，不想重新评估qwen和minimax

### 强制重新评估

```bash
# 强制重新评估所有模型
python scripts/run_baseline_eval.py --models qwen,minimax --force
```

**场景**: 修改了prompt模板，需要重新评估

### 仅生成对比报告

```bash
# 不评估，只生成对比报告
python scripts/run_baseline_eval.py --compare-only --models qwen,minimax,qwen7b
```

**场景**: 已经有所有结果，只想更新对比报告

---

## 工作流示例

### 场景1: 初次运行（评估2个大模型）

```bash
# 1. 查看可用模型
python scripts/run_baseline_eval.py --list-models

# 2. 评估Qwen和MiniMax
python scripts/run_baseline_eval.py --models qwen,minimax

# 3. 查看对比报告
cat results/baseline/multi_model_comparison.md
```

### 场景2: 添加小模型对比

```bash
# 1. 编辑configs/model_config.yaml，添加qwen7b配置

# 2. 评估新模型（跳过已有结果）
python scripts/run_baseline_eval.py --models qwen,minimax,qwen7b --skip-existing

# 3. 生成三模型对比报告
python scripts/run_baseline_eval.py --compare-only --models qwen,minimax,qwen7b
```

### 场景3: 实验不同Prompt

```bash
# 1. 修改src/baseline/prompt_template.py

# 2. 强制重新评估（覆盖旧结果）
python scripts/run_baseline_eval.py --models qwen --force

# 3. 对比新旧结果
python scripts/run_baseline_eval.py --compare-only --models qwen,minimax
```

---

## 输出文件说明

### 单模型结果

```
results/baseline/
├── qwen_results.json       # Qwen完整评估结果
├── minimax_results.json    # MiniMax完整评估结果
└── qwen7b_results.json     # Qwen7B完整评估结果（新增）
```

**格式**:
```json
[
  {
    "case_id": "eval_001",
    "model": "qwen",
    "success": true,
    "prediction": {...},
    "ground_truth": {...},
    "metrics": {
      "is_correct": true,
      "type_correct": true
    },
    "quality_metrics": {
      "legal_basis": {
        "legal_basis_score": 0.9,
        "laws_mentioned_count": 2,
        ...
      },
      "reasoning": {
        "reasoning_score": 0.85,
        ...
      }
    },
    "performance": {...}
  },
  ...
]
```

### 多模型对比报告

**文件**: `results/baseline/multi_model_comparison.md`

**包含内容**:
1. 综合排名（综合评分）
2. 准确率与质量指标对比表
3. 性能指标对比（Token、响应时间）
4. 混淆矩阵（所有模型）
5. 详细分析和建议

---

## 评估指标说明

### 准确率指标

| 指标 | 说明 |
|------|------|
| Accuracy | 二分类准确率（违规/合规判断） |
| Precision | 精确率 |
| Recall | 召回率 |
| F1-Score | F1分数 |
| Type Accuracy | 违规类型识别准确率 |

### 质量指标（新增）

| 指标 | 说明 | 评分范围 |
|------|------|----------|
| 法律依据质量 | 法律引用的准确性和完整性 | 0-100% |
| 推理质量 | 推理过程的逻辑性和可解释性 | 0-100% |
| 法律依据覆盖率 | 有法律引用的案例比例 | 0-100% |
| 推理覆盖率 | 有推理过程的案例比例 | 0-100% |

### 综合评分

```
综合分 = Accuracy × 40% + F1 × 30% + 法律质量 × 15% + 推理质量 × 15%
```

---

## 常见问题

### Q1: 如何添加本地部署的模型？

**A**: 编辑`configs/model_config.yaml`，添加新模型配置：

```yaml
models:
  qwen7b_local:
    model_id: "qwen2.5-7b-instruct"
    name: "Qwen2.5-7B (本地)"
    type: baseline
    api_endpoint: "http://localhost:8000/v1"  # 本地API地址
    max_tokens: 2048
```

然后修改`src/baseline/maas_client.py`支持自定义endpoint（如果需要）。

### Q2: 评估中断了怎么办？

**A**: 使用`--skip-existing`继续评估：

```bash
python scripts/run_baseline_eval.py --models qwen,minimax --skip-existing
```

系统会自动跳过已完成的模型。

### Q3: 如何对比RAG和Baseline？

**A**:
1. 在`configs/model_config.yaml`中添加RAG模型配置（type设为rag）
2. 实现RAG评估逻辑（继承BaselineEvaluator）
3. 运行对比：

```bash
python scripts/run_baseline_eval.py --models qwen,qwen_rag --compare-only
```

### Q4: 报告中质量指标为0怎么办？

**A**: 检查LLM输出是否包含`legal_basis`和`reasoning`字段。新的评估系统会自动计算这些质量分数。

---

## 下一步

1. **测试新系统**: 运行`python scripts/run_baseline_eval.py --list-models`
2. **对比现有结果**: `python scripts/run_baseline_eval.py --compare-only --models qwen,minimax`
3. **添加小模型**: 编辑配置文件，添加7B模型
4. **实现RAG系统**: Phase 2，使用相同的评估框架

---

## 技术架构

```
scripts/run_baseline_eval.py          # 主评估脚本（命令行入口）
├── src/baseline/model_registry.py   # 模型注册表（管理所有模型配置）
├── src/baseline/evaluator.py         # 评估器（核心评估逻辑）
├── src/baseline/multi_model_comparator.py  # 多模型对比器（生成报告）
└── configs/model_config.yaml         # 模型配置文件
```

**优势**:
- 添加新模型无需修改代码，只需修改配置
- 支持增量评估，节省时间和成本
- 统一的对比报告格式，便于论文写作
- 灵活的命令行接口，适合不同场景

---

**最后更新**: 2026-03-15
