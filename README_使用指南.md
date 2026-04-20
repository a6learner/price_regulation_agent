# 电商价格合规技术探索 - 使用指南

## 1. 项目概览

本项目用于价格合规场景的技术探索，比较三种实现路径：

- `Baseline`：纯 LLM 推理
- `RAG`：法规检索增强（当前正式评测关闭案例注入，避免同源污染）
- `Agent`：实验性实现，持续迭代中

## 2. 当前状态（简版）

- **主评测集（固定）**：`data/eval/eval_dataset_v4_final.jsonl`
- **v4 数据规模**：780 条（违规 489，合规 291；以 `data/eval/eval_dataset_v4_final.jsonl` 为准）
- **RAG 法规库**：691 条法规
- **RAG 案例库**：133 条历史案例（正式评测不注入）

关键实验结论（保留）：
- Baseline：二分类准确率约 99%+
- RAG：二分类准确率可达 100%，但法律依据质量有优化空间
- Agent：已有可运行评测链路，仍在迭代

> 详细历史实验过程与分阶段分析见 `docs/archive/`。

## 3. 快速开始

### 3.1 环境安装

```bash
cd price_regulation_agent
pip install -r requirements.txt
```

### 3.2 配置 API

编辑 `configs/model_config.yaml`，设置 `api.api_key`。

## 4. 常用命令

### 4.1 Baseline 评测

```bash
python scripts/run_baseline_eval.py --list-models
python scripts/run_baseline_eval.py --models qwen-8b --limit 5
python scripts/run_baseline_eval.py --models qwen,minimax,qwen-8b
```

### 4.2 RAG 构建与评测

首次构建向量库：

```bash
python scripts/rag/rag_extract_laws.py
python scripts/rag/rag_process_cases.py
python scripts/rag/rag_build_vector_db.py
```

运行评测：

```bash
python scripts/run_rag_eval.py --model qwen-8b --limit 5
python scripts/run_rag_eval.py --model qwen-8b
```

RAG 检索消融（默认前 **154** 条，四变体；需 `--note`）：

```bash
python scripts/rag/run_rag_ablation.py --limit 154 --model qwen-8b --note ablation_154
```

### 4.3 Agent 评测

```bash
python scripts/run_agent_eval.py --limit 5
python scripts/run_agent_eval.py
```

### 4.4 三路结果对比

无参数进入交互：依次在 `results/baseline`、`results/rag`、`results/agent` 中选运行文件夹（至少两路），再输入保存到 `results/compare/` 的文件名。

```bash
python scripts/compare_eval_results.py
python scripts/compare_eval_results.py --baseline <运行文件夹名> --rag <运行文件夹名> --name <文件名>
```

`<运行文件夹名>` 只需与对应目录下文件夹名一致（如 `improved_baseline_full_eval-780__04-18`），无需写完整路径。

## 5. 数据集说明（保留历史，简述原因）

当前建议使用：
- `data/eval/eval_dataset_v4_final.jsonl`（主评测集，固定）

历史数据集（保留但简化说明）：
- `eval_159`：早期小规模验证集，用于原型期快速迭代
- `eval_754`：扩展阶段评测集，用于中期对比与稳定性验证

升级原因（简述）：
- 提升案例覆盖度与类型分布
- 改善数据一致性与标注质量
- 支撑后续 RAG/Agent 的更可靠比较

## 6. 目录约定（当前结构）

### 6.1 脚本目录

- `scripts/run_baseline_eval.py`
- `scripts/run_rag_eval.py`
- `scripts/run_agent_eval.py`
- `scripts/compare_eval_results.py`：Baseline / RAG / Agent 结果对比
- `scripts/rag/`：RAG 构建脚本（含 `run_rag_ablation.py` 消融）
- `scripts/data/`：数据处理与构建脚本
- `scripts/archive/`：旧版/实验脚本

### 6.2 结果目录

- `results/baseline/`
- `results/rag/`
- `results/agent/`
- `results/compare/`：对比脚本输出的 Markdown
- `results/archive/`：中间产物与历史进度文件

## 7. 关键实验口径（重要）

- 为避免案例同源污染，RAG 正式评测链路已设置为**不注入案例检索结果**（`cases_k=0`）。
- 仍保留法规检索（laws）作为主要检索增强来源。

## 8. 常见问题（精简）

- API 401：检查 `configs/model_config.yaml` 的 `api_key`
- 模型名报错：先执行 `--list-models`，并使用英文逗号分隔
- 找不到数据集：确认在 `price_regulation_agent/` 目录执行命令
- RAG 首次慢：模型与向量库初始化耗时，后续会使用缓存

