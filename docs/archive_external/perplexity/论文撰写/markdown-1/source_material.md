# 论文写作材料（Perplexity / Ch3–Ch6）

本文档依据仓库内**可核对**的代码、配置与数据文件整理；凡仓库未记录或无法复算的内容，在「需作者补充」一节列出。**请勿将 `configs/model_config.yaml` 中的 API 密钥写入论文或对外分享。**

---

## Ch3 数据集构建

### D1 EasySpider 采集流程（⭐）

- **入口站点**：`easyspider/tasks/358.json` 中 `url` 为 `https://cfws.samr.gov.cn/index.html`（中国市场监管行政处罚文书网）。
- **任务图结构（358）**：打开首页 → 点击「登录」→ 确定登录 → 点击用户入口（配置中 xpath 为 `#user`）→ 进入「收集」模板表格中的收集链接（iframe 内）→ **循环「下一页」** → 在列表页循环提取每条文书：**文书编号、文书链接、当事人名称、处罚机关、处罚日期、处罚内容**（列表摘要，非全文 PDF）。
- **输出格式**：任务配置 `outputFormat: "csv"`；`removeDuplicate: 0`（去重未在 EasySpider 任务内开启）。
- **筛选条件**：具体「热门主题 / 处罚依据 / 全文关键词 / 时间切片」等**不在 JSON 任务文件里**，属于你在浏览器高级检索中预先完成的步骤；论文叙述应与你提供的截图及自述一致（价格主题、《价格法》、《价格违法行为行政处罚规定》、因列表仅展示前 200 条而按时间/年份分批等）。
- **反爬 / 工程问题**：任务含**登录态**与 **iframe** 采集；仓库内**无**单独的反爬对策文档，若论文要写「验证码、频控、封禁」等需你补充实际经历。

### D2 评测侧「脱敏后」数据（⭐）

- **作者口径**：主评测集 `price_regulation_agent/data/eval/eval_dataset_v4_final.jsonl` 即为从源 PDF 提炼、清洗并脱敏后的最终样本；论文中「脱敏样例」可直接引用该文件中的 `input.case_description` 与 `ground_truth` 字段（勿写入真实当事人全名等未脱敏信息）。
- **原始池**：PDF 等原始材料目录见脚本注释 `data/cases/791处罚文书/files/`（`scripts/data/smart_pdf_extractor.py`）。
- **EasySpider 列表字段**（与 PDF 全文不同层）：`easyspider/tasks/358.json` 的 `outputParameters` 示例：文书编号、文书链接、当事人名称、处罚机关、处罚日期、处罚内容。

### D3 `eval_dataset_v4_final.jsonl` 一条 JSON 样例（⭐，已脱敏/结构化）

以下为真实文件中**截断**后的结构示例（字段名以仓库为准）：

```json
{
  "id": "CASE_0001",
  "source_pdf": "esfile_....pdf",
  "region": "南平市市",
  "tier": 1,
  "input": {
    "case_description": "（案情叙述，可能含换行与脱敏符号）",
    "platform": "支付宝",
    "goods_or_service": null
  },
  "ground_truth": {
    "is_violation": true,
    "violation_type": "不明码标价",
    "qualifying_articles": [
      {"law": "价格法", "article": "第十三条", "article_key": "价格法_十三"}
    ],
    "penalty_articles": [
      {"law": "价格法", "article": "第四十二条", "article_key": "价格法_四十二"}
    ],
    "legal_analysis_reference": "",
    "penalty_result": "罚款402500元"
  },
  "_debug": {
    "desc_source": "violation_facts",
    "leakage_found": false,
    "text_length": 6171
  },
  "review_required": true,
  "review_bucket": "fn_candidate",
  "review_reason": "…",
  "suggested_action": "…"
}
```

**字段含义（简述）**

| 字段 | 含义 |
|------|------|
| `id` | 评测用案例编号 |
| `source_pdf` | 来源文书标识（哈希式文件名，用于同源/去重分析） |
| `region` / `tier` | 地域与难度分层（构建脚本中 tier 过滤相关） |
| `input.case_description` | 输入给模型的案情描述 |
| `input.platform` | 电商平台提示（可为 null） |
| `ground_truth.*` | 标注：是否违规、类型、定性与处罚法条等 |
| `_debug` | 流水线调试与质量元数据 |
| `review_*` | 人工复核队列标记（若启用） |

### D4 791 → 780 过滤了什么（⭐）

- **作者口径（可写论文）**：从约 **791** 份原始文书到最终 **780** 条评测样本，剔除了少量**案情描述不完整**或**不符合当前评测集构建规则**的样本；无需逐条列举。
- 仓库内**无**逐条剔除清单；若审稿人追问，可补充「未纳入 v4 的文书未保留独立清单」等诚实说明。

### D5 违规样本类型分布 — 以 `eval_dataset_v4_final.jsonl` 为准（⭐）

对当前文件**实算**（`ground_truth.is_violation == true` 计为违规，共 **489** 条；合规 **291** 条；合计 **780**）：

| 违规类型 | 条数 |
|----------|------|
| 不明码标价 | 221 |
| 政府定价违规 | 117 |
| 标价外加价 | 73 |
| 误导性价格标示 | 49 |
| 未识别 | 14 |
| 变相提高价格 | 6 |
| 虚假价格比较 | 5 |
| 虚假折扣 | 2 |
| 不履行价格承诺 | 1 |
| 哄抬价格 | 1 |

**口径**：`CLAUDE.md` 与 `README_使用指南.md` 已与该文件对齐为 **489 / 291**。

### D6 v4 之前 eval_159 / eval_754 演进（推荐）

- 与你自述一致即可：**eval_159** 为早期小集合验证链路；**eval_754** 为扩大规模且经 LLM 改写，难度与真实处罚文书有差距；**v4** 回到以真实价格执法文书为主构建评测集。
- 仓库保留路径：`CLAUDE.md` 中「历史评测集」说明；`results/archive/` 等可能有中间 jsonl。

### D7 法规库 691 条来源与切块（⭐）

- **条数**：`data/rag/laws_chunks.jsonl` 共 **691** 条（实算）。
- **平均 chunk 长度**：`content` 字段字符数均值约 **140**（约 18–816）。
- **作者口径（法规获取）**：法规文本来自 **[国家法律法规数据库](https://flk.npc.gov.cn/index)**（`flk.npc.gov.cn`），通过多个与价格执法、电商、反不正当竞争、网络交易等相关的**标题关键词**检索后，从官网**批量下载**整理为本地 **DOCX**，再放入 `data/laws/`（中央 / 浙江 / 平台规则子目录）。截图可作为论文附图。
- **代码切块路径**：`LawDocumentExtractor.process_all_laws("data/laws")`（`src/rag/data_processor.py`）。
- **切块策略**：**按「条」切段**——用正则识别以「第…条」开头的段落作为新条款起点，将该条下后续段落拼入同一 chunk；字段包括 `chunk_id`、`law_name`、`law_level`、`article`、`content`。

### D8 案例库 133 条与评测集重叠（⭐）

- 依据内部分析文档 `docs/archive/rag_analysis.md`（Data Leakage Check）：RAG 案例索引约 **133** 个来源；与 eval 违规来源 PDF **存在非零重叠**（文中示例为 **8** 个直接重叠的 `source_pdf`，占案例索引比例约 6%、占 eval 违规源约 1.6% 量级——具体数字以你当时统计脚本为准）。
- **正式 RAG 评测**：`src/rag/evaluator.py` 中 `retrieve(..., laws_k=3, cases_k=0)`，即**不向模型注入相似案例文本**，以降低同源污染；论文可据此解释「为何设 `cases_k=0`」。
- **注意**：`RAGPromptTemplate` 的 system 文案仍含「相似处罚案例」占位；`cases_k=0` 时 cases_context 为「暂无相似案例」。

---

## Ch4 Baseline

### B1 Baseline 主 Prompt（⭐）

- 完整系统提示与用户模板见：`src/baseline/prompt_template.py` 中 `PromptTemplate.SYSTEM_PROMPT` 与 `USER_PROMPT_TEMPLATE`（要求 JSON：`is_violation`、`violation_type`、`legal_basis`、`reasoning`、`cited_articles` 等）。

### B2 Qwen / MiniMax / Qwen-8B 在 **780 评测集** 上的对比（⭐）

- **已有可溯源结果**：`results/baseline/improved_baseline_full_eval-780__04-18/qwen-8b_results.json`（780 条，`eval_dataset_v4_final.jsonl`）。
- **另两模型**：需在**同一数据集、同一超参**下重跑后才有论文级对比表；旧文件 `results/baseline/qwen_results.json`、`minimax_results.json` 为**历史 eval 格式**，**不能**与 v4 780 混用。
- **复现命令**（在 `price_regulation_agent` 目录下，需配置好 `configs/model_config.yaml`；全量 780 跑前会交互确认 `y`）：

```bash
cd price_regulation_agent
python scripts/run_baseline_eval.py --models qwen,minimax,qwen-8b --eval-path data/eval/eval_dataset_v4_final.jsonl --results-dir results/baseline --note v4_780_three_models
```

- 非交互环境可加 `--limit` 做试跑；全量时若需跳过确认，需改脚本或本地 stdin 输入 `y`。

### B3 对比实验设置（推荐）

- **API**：`src/baseline/maas_client.py` 为讯飞星辰 MaaS，`payload` 含 `max_tokens`、`temperature`、`top_p`；**未见** `response_format` 强制 JSON mode。
- **默认超参**（`configs/model_config.yaml`）：各模型 `max_tokens: 2048`，`temperature: 0.7`，`top_p: 0.9`（`qwen`、`minimax`、`qwen-8b` 等条目一致）。
- **论文写法**：写明「聊天补全 + 提示词约束 JSON」，并列出上述数值即可。

### B4 `ResponseParser` 启发式规则（⭐）

文件：`src/baseline/response_parser.py`。

**JSON 抽取**：`json.loads` → 失败则尝试 markdown 代码块 `` ```json `` → 再尝试首个 `{...}` 子串。

**法律依据分 `evaluate_legal_basis_accuracy`**：

- 有非空 `legal_basis`：+0.3；
- 命中预设关键词列表（含「价格法」「明码标价」「禁止价格欺诈」等）：每条 +0.2，上限 +0.5；
- 正则匹配「第X条」形式：+0.2；
- 总分截断至 1.0。

**推理分 `evaluate_reasoning_quality`**：

- 有非空 `reasoning`：+0.2；
- 含事实类关键词（如「经查」「事实」「经营者」等）：+0.25；
- 含法律分析词（如「根据」「违反」「构成」等）：+0.25；
- 含逻辑连接词（如「因此」「因为」等）：+0.15；
- 句号/问号/叹号计数 ≥3：+0.15；
- 总分截断至 1.0。

**违规类型**：可选智能匹配（同义词组、多标签、上位概念等），配置见 `violation_type_config.py`。

### B5 Baseline 失败案例示例（推荐）

- **案例**：`CASE_0009`（`results/baseline/improved_baseline_full_eval-780__04-18/qwen-8b_results.json`）。
- **Ground truth**：`is_violation: true`，`violation_type: 误导性价格标示`（案情涉及多商品促销原价/折后价与此前成交价对比等）。
- **模型预测**：`is_violation: false`，`violation_type: 无违规`，`confidence: 0.95`；推理中认为「原价、折扣率、折后价均已被明确标注」故不违法。
- **输入摘要**：见 `eval_dataset_v4_final.jsonl` 中该条 `input.case_description`（较长，论文可节选）。

---

## Ch5 RAG

### R1 向量模型（⭐）

- `src/rag/retriever.py`：`SentenceTransformer('BAAI/bge-small-zh-v1.5')`（**不是** bge-m3 / m3e）。

### R2 CrossEncoder 重排模型（⭐）

- 同上文件：`CrossEncoder('BAAI/bge-reranker-v2-m3')`（启用 `use_reranker` 时）。

### R3 `distance_threshold`、`min_k`、动态 Top-K（⭐）

- **正式 RAG 评测路径**：`RAGEvaluator` → `HybridRetriever.retrieve(query, laws_k=3, cases_k=0, distance_threshold=0.15, min_k=2)`（`evaluator.py` 显式传参）。
- **Agent 路径**：`AdaptiveRetriever` 调用时写死 `distance_threshold=0.15`、`min_k=2`；`laws_k` 来自意图分析（3/4/5），`cases_k` 来自意图分析但当前 `IntentAnalyzer._decide_topk` **恒为 0**。
- **动态 Top-K（法规）**：重排与阈值过滤后，若列表非空：用前 3 条平均 distance，`avg < 0.10` 取 **2** 条；`avg < 0.15` 取 **3** 条；否则取 **`laws_k` 条**（`retriever.py`）。
- **`min_rerank_score`**：默认 **0.0**（不在评测代码中改为正数）。

### R4 RAG Prompt（⭐）

- `src/rag/prompt_template.py`：`RAGPromptTemplate.RAG_SYSTEM_PROMPT` + 继承的 `build_user_prompt`；在 system 中注入 `laws_context` 与 `cases_context`，并要求与 Baseline 同结构的 JSON 输出。

### R5 消融实验（推荐）

- **脚本**：`scripts/rag/run_rag_ablation.py`（默认取评测集**前 154 条**，与全量 780 分布可能略有差异，论文需写明）。
- **四变体**：`semantic_only`（仅向量）、`bm25_only`（仅 BM25）、`rrf`（向量+BM25，无重排）、`rrf_rerank`（与线上一致）。
- **实现**：`HybridRetriever` 新增构造参数 `use_semantic` / `use_bm25` / `use_reranker` 组合；`bm25_only` 路径见 `src/rag/retriever.py`。
- **输出**：`results/rag/rag_ablation_<note>__<日期>/` 下 `ablation_summary.md`、`ablation_summary.json`、各变体 `results_<variant>.json`。
- **跑数后再写论文表**：当前仓库**不含**已填好的消融数值，以该目录下生成文件为准。

```bash
cd price_regulation_agent
python scripts/rag/run_rag_ablation.py --limit 154 --model qwen-8b --note ablation_154
```

### R6 向量库规模（推荐）

- **法规 chunk**：691（见 D7）。
- **Chroma 集合**：由 `rag_build_vector_db.py` 构建；案例集合规模未在此文档重算，需可查 `cases_chunks.jsonl` 行数。

### R7 法规切块策略（⭐）

- 同 D7：**按「条」**从 DOCX 段落流切分。

---

## Ch6 Agent

### A1 `IntentAnalyzer` 规则清单（⭐）

- 文件：`src/agents/intent_analyzer.py`；**无 LLM**，纯规则。
- **输出意图相关字段**：`violation_type_hints`（最多 3 个）、`key_entities`（平台、金额、价格用语等）、`complexity`（`simple`/`medium`/`complex`）、`suggested_laws_k`（3/4/5）、**`suggested_cases_k` 恒为 0**、`reasoning_hints`。
- **违规类型触发关键词**：见 `_detect_violation_types` 内各 `if any(kw in query ...)` 列表（不明码标价、政府定价违规、标价外加价、误导性价格标示（含强/弱特征组合）、变相提高价格、哄抬价格等）。

### A2 `Grader` 评分公式（⭐）

- 文件：`src/agents/grader.py`；默认权重 **relevance 0.6、coverage 0.3、freshness 0.1**；**`min_score=0.5`**。
- **relevance**：若文档有 `rerank_score` 则用其值；否则 `max(0, 1 - distance)`。
- **coverage**：关键词在 `content` 中出现比例；无关键词时默认 **0.5**。
- **freshness**：`metadata.year >= 2024` → 1.0；`>=2020` → 0.8；否则 0.6（缺省年用 2020）。
- **过滤**：保留 `final_score >= min_score`；若不足 **`min_keep=2`** 则回退为按分数排序后的前 2 条。

### A3 `ReasoningEngine` 主 Prompt（⭐）

- 由 `_build_system_prompt` 动态拼接：`src/agents/reasoning_engine.py`（含法规片段、`cases_k>0` 时增加相似案例与 5 步 COT；**当前 Agent 路径 cases 为空**，走 **4 步** COT 分支，并禁止「类似案例」等表述）。
- 模型调用：`MaaSClient.call_model(..., model_key='qwen-8b')`。

### A4 `Reflector` 启发式规则（⭐）

- 文件：`src/agents/reflector.py`；`max_reflection` 默认 **1**。
- **严重（critical）示例**：`is_violation==True` 与 `violation_type` 为「无违规」类矛盾；`is_violation==False` 但类型非无违规；违规类型下推理链**完全缺失**该类型所需事实关键词；非价格领域关键词命中且无价格要素等。
- **warning 示例**：无法律依据文本、法条与类型不匹配等。
- 存在 critical 且未超最大反思次数时，拼接反馈后**再次调用** `ReasoningEngine.reason`。

### A5 `RemediationAdvisor`（⭐）

- **默认评测路径倾向**：`AgentCoordinator` 对 `complex`/`medium` 用 `mode="detailed"`（LLM），`simple` 用 `fast`（规则模板）；以你实际 `run_agent_eval` 调用链为准（若评估脚本未改，以脚本为准）。
- **fast**：`REMEDIATION_TEMPLATES` 字典（`nodes/remediation_advisor.py`）。
- **detailed**：同文件内 `system_prompt` / `user_prompt` 字符串（要求 JSON：`remediation_steps`、`compliance_checklist` 等）。

### A6 Case Study 完整样本（⭐⭐）

- **历史全量结果**（仍可作为案例引用）：`results/agent/improved_agent_full_eval-780__04-19/results.json` — 含 `reasoning_chain`、`legal_basis`、`validation_passed`、`reflection_count`、`remediation`、与 ground truth 对比等。
- **自本次代码更新起**：`scripts/run_agent_eval.py` 每条成功样本额外写入 **`agent_trace`**：`intent` 全量、`retrieved` / `graded` 的法规摘要列表（chunk_id、法规名、条号、distance、final_score）、`timings_ms` 各节点毫秒数、`total_pipeline_ms`（六节点本地耗时之和，不含 MaaS 网络排队）。
- **论文写法**：Case study 以**你重新跑出的** `results/agent/<run>/results.json` 为准，并标注运行目录与日期；旧文件无 `agent_trace` 属正常。

### A7 各节点平均耗时（推荐）

- **全链路墙钟**：仍以 `results.json` → `metrics.performance.avg_response_time` 及 `results/compare/improved-1.md` 汇总为准（例：约 **37.62 s/条** Agent 全量一次跑）。
- **节点级均值**：重跑 Agent 评测后，查看同文件 **`metrics.node_timings_avg_ms`**（由 `agent_trace` 汇总）。**勿**与未说明口径的「25.6 s」混写；若采用子集或不同统计方式须在论文脚注说明。

---

## 与 `improved-1.md` 一致的 780 主结果摘要

| 方法 | Accuracy | Type Acc | F1 | 法律依据均分 | 推理均分 | 平均耗时 s |
|------|----------|----------|-----|--------------|----------|------------|
| Baseline | 89.35% | 73.68% | 91.47% | 0.8411 | 0.8415 | 7.02 |
| RAG | 89.85% | 74.94% | 92.01% | 0.7321 | 0.8685 | 7.77 |
| Agent | 86.98% | 71.52% | 89.79% | 0.7035 | 0.8931 | 37.62 |

（成功样本口径、去重说明见该 Markdown。）

---

## 复现命令摘要（论文数据一律以运行产出目录为准）

| 任务 | 命令（工作目录：`price_regulation_agent`） |
|------|--------------------------------------------|
| Baseline 三模型 780 | `python scripts/run_baseline_eval.py --models qwen,minimax,qwen-8b --eval-path data/eval/eval_dataset_v4_final.jsonl --results-dir results/baseline --note <备注>` |
| RAG 780 | `python scripts/run_rag_eval.py --model qwen-8b --eval-data data/eval/eval_dataset_v4_final.jsonl --note <备注>` |
| Agent 780 | `python scripts/run_agent_eval.py --eval-data data/eval/eval_dataset_v4_final.jsonl --note <备注>` |
| RAG 消融 154 | `python scripts/rag/run_rag_ablation.py --limit 154 --model qwen-8b --note <备注>` |

---

## 目前仍需补充或可写的实验（检查清单）

以下为**跑完后才有数值或表格**的项目；未跑前论文应写「待实验」或引用本仓库已有**唯一**结果路径。

1. **Baseline 三模型同表（B2）**：在 `eval_dataset_v4_final.jsonl` 上补齐 `qwen`、`minimax` 与既有 `qwen-8b` 的 Acc / F1 / 时延；产出目录 `results/baseline/<run>/`。
2. **RAG 检索消融（R5）**：运行 `run_rag_ablation.py`，将 `ablation_summary.md` 中四行指标写入论文；注明子集为**前 154 条**。
3. **Agent 全量重跑与 Case study（A6/A7）**：用新版 `run_agent_eval.py` 生成带 `agent_trace` 与 `node_timings_avg_ms` 的 `results.json`；Case study 从此文件摘录。
4. **主表数字与脚注**：若论文中曾出现与 `improved-1.md` 不一致的耗时（如 25.6 s），以**新跑** `compare_eval_results.py` 或 `results.json` 为准并统一脚注口径。
5. **（可选）法条检索 F1 / 高级指标**：各脚本已支持部分输出；若正文引用，须对应到具体 `run_info.json` 与 `results.json` 路径。
6. **（可选）清洗清单**：791→780 无逐条文件时保持 D4 的概括表述即可。

---

## 仍建议人工准备、但非「跑实验」类

- 文书网 / 法规库截图已具备时可插入第三章；EasySpider 任务 JSON 路径：`easyspider/tasks/358.json`。
- 若审稿要求「原始处罚决定书体例」：可另附附录扫描件（非本仓库必需文件）。

---

*生成说明：依据 `price_regulation_agent` 仓库代码与数据整理；数值类表述以对应 `results/` 下文件及 `eval_dataset_v4_final.jsonl` 实算为准。*
