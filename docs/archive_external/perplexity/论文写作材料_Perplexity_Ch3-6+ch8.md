# 论文写作材料（Perplexity / Ch3–Ch6 + Ch8 Web）

本文档依据仓库内**可核对**的代码、配置与数据文件整理；凡仓库未记录或无法复算的内容，在「需作者补充」一节列出。**请勿将 `configs/model_config.yaml` 中的 API 密钥写入论文或对外分享。**

**Ch8 说明**：若你手头仍有旧稿 `docs/archive_external/perplexity/论文撰写/ch8_system_prototype.md`（Streamlit、三栏拟议、且写「前端未实现」），**请以本文「Ch8 Web 交互原型」一节及 `price_regulation_agent/web/README.md` 为准**，旧稿中 Streamlit 与「未实现」表述**作废**。

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

- **正式跑次（论文引用）**：`results/baseline/baseline_v4_780_three_models__04-19/`  
  - `run_info.json`：`eval_data` 为 `data/eval/eval_dataset_v4_final.jsonl`，**780** 条，`models`: `qwen`, `minimax`, `qwen-8b`。  
  - 逐模型结果：`qwen_results.json`、`minimax_results.json`、`qwen-8b_results.json`。  
  - 同目录 `multi_model_comparison.md` 为脚本生成的对比报告；**若报告头仍写旧子集名，以 `run_info.json` + 下表（由 `BaselineEvaluator.calculate_metrics` 与三份 `*_results.json` 核对）为准。**
- **指标口径**：成功样本内 `accuracy` / `precision` / `recall` / `f1_score` / `type_accuracy`（`type_correct` 覆盖**全部**成功条，含合规类「无违规」匹配）；质量分为 `quality_metrics.avg_legal_basis_score`、`avg_reasoning_score`；墙钟为 `performance.avg_response_time`（秒）。

| 模型（config key） | 成功 / 提交 | Accuracy | Precision | Recall | F1 | Type Acc | 法律依据均分 | 推理均分 | 平均响应 s |
|--------------------|------------:|---------:|----------:|-------:|---:|---------:|-------------:|---------:|-----------:|
| Qwen3.5-397B-A17B (`qwen`) | 774 / 780 | 93.15% | 95.39% | 93.62% | 94.50% | 79.07% | 0.9128 | 0.9033 | 5.41 |
| MiniMax-M2.5 (`minimax`) | 772 / 780 | 91.45% | 93.72% | 92.56% | 93.14% | 75.26% | 0.9097 | 0.8086 | 8.98 |
| Qwen3-8B (`qwen-8b`) | 773 / 780 | 89.91% | 92.37% | 91.62% | 91.99% | 73.74% | 0.8336 | 0.8431 | 7.17 |

- **单模型仅 qwen-8b 的历史全量**：仍可作为附录引用：`results/baseline/improved_baseline_full_eval-780__04-18/qwen-8b_results.json`（同 v4 780，但与上表**非同一跑次**时勿混排行列）。
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
- **已跑结果（论文引用）**：`results/rag/rag_ablation_ablation_154__04-19__v4/`  
  - `run_info.json`：`eval_data` 为 `eval_dataset_v4_final.jsonl`，**limit=154**，模型 **`qwen-8b`**，`variants` 为四者。  
  - 汇总：`ablation_summary.md`、`ablation_summary.json`；分变体：`results_bm25_only.json` 等。

| 变体 | Accuracy | F1 | Type Acc | 平均耗时 s |
|------|---------:|---:|---------:|-----------:|
| bm25_only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| semantic_only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| rrf | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| rrf_rerank | **0.9026** | **0.9470** | **0.6299** | 8.11 |

- **结论要点（供正文压缩）**：在 154 条子集上，`rrf_rerank` 在 Accuracy / F1 / Type Acc 上均优于仅 BM25、仅语义与无重排 RRF；平均墙钟与另几档接近（约 7.9–8.2 s），说明增益主要来自**融合与 Cross-Encoder 重排**而非单纯拉长耗时。全文指标仍以 `run_rag_eval.py` 780 条主表为准，消融表注明子集规模即可。

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
- **带 `agent_trace` + 节点测时的全量跑次**：`results/agent/agent_v4_780_node_timings__04-19/results.json`（`run_info.json`：`eval_dataset_v4_final.jsonl`，780 条，`note`: `agent_v4_780_node_timings`）。每条成功样本含 **`agent_trace`**：`intent`、`retrieved` / `graded` 摘要、`timings_ms`、`total_pipeline_ms`（六节点本地耗时之和，不含 MaaS 网络排队）。
- **论文写法**：Case study 与节点统计以**具体 `results/agent/<run>/results.json`** 为准，并标注目录与日期；旧文件无 `agent_trace` 属正常。

### A7 各节点平均耗时（推荐）

- **全链路墙钟（本测次）**：`results/agent/agent_v4_780_node_timings__04-19/results.json` → `metrics.performance.avg_response_time` = **36.14 s/条**（成功 **777** / 780；与 `results/compare/improved-1.md` 中约 **37.62 s** 为**不同跑次**，论文择一主表并脚注日期即可）。**勿**与未说明口径的「25.6 s」混写。
- **节点级均值（由 `agent_trace` 聚合）**：同文件 **`metrics.node_timings_avg_ms`**（毫秒）。以下为该跑次实测：

| 节点 key | 平均耗时 (ms) | 约 (s) |
|----------|----------------:|-------:|
| intent_analyzer | 0.11 | <0.01 |
| adaptive_retriever | 19167.81 | 19.17 |
| grader | 0.08 | <0.01 |
| reasoning_engine | 11175.34 | 11.18 |
| reflector | 453.58 | 0.45 |
| remediation_advisor | 5342.60 | 5.34 |
| **total_pipeline_ms（六节点加总）** | **36139.52** | **36.14** |

- **解读要点**：墙钟与 `total_pipeline_ms` 量级一致；耗时主要落在 **`adaptive_retriever`（检索+重排等）** 与 **`reasoning_engine`（LLM 推理）**，其次为 **`remediation_advisor`**；`intent_analyzer` / `grader` 为规则或极轻量调用，毫秒级。**若采用子集或不同统计方式须在论文脚注说明。**

---

## 与 `improved-1.md` 一致的 780 主结果摘要

| 方法 | Accuracy | Type Acc | F1 | 法律依据均分 | 推理均分 | 平均耗时 s |
|------|----------|----------|-----|--------------|----------|------------|
| Baseline | 89.35% | 73.68% | 91.47% | 0.8411 | 0.8415 | 7.02 |
| RAG | 89.85% | 74.94% | 92.01% | 0.7321 | 0.8685 | 7.77 |
| Agent | 86.98% | 71.52% | 89.79% | 0.7035 | 0.8931 | 37.62 |

（成功样本口径、去重说明见该 Markdown。）**三模型 Baseline 分项对比**（非本表的单模型汇总）见 **B2** 与 `results/baseline/baseline_v4_780_three_models__04-19/`。

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

以下**1–3 已跑通并写入 B2 / R5 / A6–A7**；其余仍按需补充。

1. ~~**Baseline 三模型同表（B2）**~~ **已完成**：`results/baseline/baseline_v4_780_three_models__04-19/`（见 B2 表）。
2. ~~**RAG 检索消融（R5）**~~ **已完成**：`results/rag/rag_ablation_ablation_154__04-19__v4/`（见 R5 表；子集为**前 154 条**）。
3. ~~**Agent 全量 + `agent_trace` + `node_timings_avg_ms`（A6/A7）**~~ **已完成**：`results/agent/agent_v4_780_node_timings__04-19/results.json`（见 A7 表）。
4. **主表数字与脚注**：若正文同时出现 `improved-1.md` 与 **2026-04-19/20** 新跑次，须统一**主表选用哪次**并在脚注写明路径（例如 Agent 墙钟 37.62 s vs 36.14 s）。
5. **（可选）法条检索 F1 / 高级指标**：各脚本已支持部分输出；若正文引用，须对应到具体 `run_info.json` 与 `results.json` 路径。
6. **（可选）清洗清单**：791→780 无逐条文件时保持 D4 的概括表述即可。

---

## 仍建议人工准备、但非「跑实验」类

- 文书网 / 法规库截图已具备时可插入第三章；EasySpider 任务 JSON 路径：`easyspider/tasks/358.json`。
- 若审稿要求「原始处罚决定书体例」：可另附附录扫描件（非本仓库必需文件）。

---

## Ch8 Web 交互原型（已实现，交 Perplexity 写第八章用）

以下可直接作为论文「系统实现 / 人机交互原型」的事实依据；**权威路径**：`price_regulation_agent/web/README.md`，实现代码在 `web/backend/`、`web/frontend/`。

### 8.0 与旧大纲的关系（写作时必须交代）

| 旧稿（如 `ch8_system_prototype.md`） | 当前实现（事实） |
|-------------------------------------|------------------|
| 前端拟用 **Streamlit** | 实际为 **React + TypeScript + Vite**，**无 Streamlit** |
| 三栏布局为「拟议」 | 实际为 **首页角色选择** + **对话工作台**（左历史 / 中对话 / 右溯源抽屉）+ **知识库页** |
| 曾写「前端未实现」 | **Web 原型已实现**（见 `web/`） |

**建议表述**：早期可曾考虑 Streamlit；最终实现采用前后端分离与 SSE，以降低与批量评测脚本耦合、便于导航与知识库扩展。

### 8.1 总体架构

- **浏览器**：开发时 `http://localhost:5173`（Vite）。
- **代理**：`/api/*` 由 **Vite** 转发至后端（见 `web/frontend/vite.config.ts`）。
- **后端**：**FastAPI**，默认 `http://127.0.0.1:8000`，入口 `web/backend/main.py`。
- **推理**：复用 **`AgentCoordinator`（6 节点）**，由 **`web/backend/services/streaming_coordinator.py`** 包装为 **SSE**。
- **数据**：**ChromaDB**（与 RAG 一致：`data/rag/chroma_db`，法规 691 条 + 案例 133 条）；**SQLite**（`web/backend/traces.db`，对话溯源，运行后生成）。
- **LLM**：讯飞星辰 MaaS（`configs/model_config.yaml`）；本地需嵌入/重排模型（`BAAI/bge-small-zh-v1.5` / `bge-reranker-v2-m3`，可 `HF_HUB_OFFLINE=1` 或见 `models/` 与 `src/rag/local_model_paths.py`）。

```
浏览器 (localhost:5173)
  │  /api/*  →  Vite 代理
  ▼
FastAPI (8000) → AgentCoordinator + ChromaDB + SQLite(traces)
```

### 8.2 技术栈（可做成论文表格）

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React + TypeScript + Vite | 组件约 7 个，页面 3 个（以 `web/frontend/src` 为准） |
| 样式 | Tailwind CSS 4 | `index.css` 主题 |
| 路由 | React Router 7 | 首页 / 工作台 / 知识库等 |
| 后端 | FastAPI 0.115+ | `web/backend/main.py` |
| 流式 | SSE（sse-starlette 2+） | `POST /api/chat` |
| 持久化 | SQLite（aiosqlite） | 溯源与历史 |
| 向量库 | ChromaDB 1.5+ | 与项目 RAG 向量库同源 |

### 8.3 功能与信息架构

1. **角色选择（首页）**：三张卡片 — **消费者 / 政府监管 / 网店商家**；系统提示前缀见 `web/backend/services/role_prompt.py`（维权 / 执法审查 / 商家自查侧重不同）。
2. **对话工作台**：文本输入；**六节点进度条**（意图分析 → 法规检索 → 质量评分 → 推理分析 → 反思验证 → 整改建议）；完成后 **报告卡片**（结论、置信度、违规类型、法律依据、推理、整改）；支持 **📎 上传** PDF/DOCX/TXT（`/api/upload` + 文本注入查询）；**左侧**历史记录；**右侧抽屉**「完整溯源」与法条交互。
3. **知识库浏览**：**法规库**、**案例库**分页与搜索（`/api/knowledge/laws`、`/api/knowledge/cases`）。

### 8.4 API 与 SSE 数据流

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat` | **SSE 流式对话（核心）** |
| POST | `/api/chat/sync` | 同步整包（调试，约数十秒阻塞） |
| POST | `/api/upload` | 文档上传提取文本 |
| GET | `/api/trace/{id}` | 单条完整溯源 |
| GET | `/api/traces` | 历史分页 |
| GET | `/api/knowledge/laws` | 法规浏览/搜索 |
| GET | `/api/knowledge/cases` | 案例浏览/搜索 |

**SSE 事件顺序（与 Agent 节点对应）**：`intent` → `retrieval` → `grading` → `reasoning` → `reflection` → `remediation` → `done`（含 `trace_id` 与完整结果）；服务端写入 SQLite。Swagger：`http://localhost:8000/docs`。

### 8.5 与批量评测系统的关系（论文边界）

- **780 条指标**仍以 `scripts/run_baseline_eval.py` / `run_rag_eval.py` / `run_agent_eval.py` 产出为准，目录 `results/`。
- **Web** 为 **交互式单条**调用同一 **`AgentCoordinator`**，**不替代**离线全量评测；可写：「原型面向人机协同；全量实验指标以固定评测集脚本为准。」

### 8.6 启动与复现（工程段落）

在 **`price_regulation_agent`** 根目录：

```bash
# 终端1：后端（PowerShell 示例）
$env:HF_HUB_OFFLINE=1; python -m uvicorn web.backend.main:app --reload --port 8000

# 终端2：前端
cd web/frontend && npm run dev
```

浏览器访问 `http://localhost:5173/`。依赖与排错见 `web/README.md`。**可选**：`npm run build` 后由 FastAPI 挂载 `dist` 单端口部署（README 第十节）。

### 8.7 旧拟议中应弱化或删除的写法

- **Streamlit**、`st.write_stream`：删除，改为 **React + SSE**。
- **固定「左上传 + 中六块 + 右法条」三栏**：改为 **抽屉溯源 + 独立知识库页**；法条可追溯目标仍在，布局不同。
- **Remediation「Accept / Revise」**：以实际 UI 为准；若仅有展示而无独立「接受/修订」按钮，勿写未实现控件。
- **批量目录上传、独立审计日志专页**：可作为**未来工作**，勿写成已实现。

### 8.8 局限（可选写 Discussion）

- 依赖外网 **MaaS API**；本地嵌入模型需缓存或 `models/`。
- 开发态双端口（5173+8000）；生产可合并为单端口（见 README）。
- 与第三章数据集、第六章 Agent 逻辑衔接时强调：**同源 Agent 管线，论文章节指标仍以离线 `eval_dataset_v4_final.jsonl` 评测为准**。

---

*生成说明：依据 `price_regulation_agent` 仓库代码与数据整理；数值类表述以对应 `results/` 下文件及 `eval_dataset_v4_final.jsonl` 实算为准；**Ch8 Web 以 `web/README.md` 与 `web/` 代码为准**。*
