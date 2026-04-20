# 3 Dataset Construction

The quality of any empirical NLP evaluation hinges on the data it rests on. This chapter documents how we assembled the two resources that underpin all downstream experiments: a 780-sample evaluation set of real-world administrative penalty records and a 691-article law knowledge base. Both were collected from public government portals, processed through a semi-automated pipeline, and curated to eliminate identifiable personal information before any model ever saw them.

## 3.1 Data sources and scope

Two online repositories provide the raw material for this project.

The primary source is the **中国市场监管行政处罚文书网** (China Market Supervision Administrative Penalty Document Network), hosted at https://cfws.samr.gov.cn/index.html^[45]^. The portal is maintained by the State Administration for Market Regulation (SAMR) and publishes official penalty decisions issued by local and provincial market-supervision bureaus across China. Each document is structured as a scanned or digital PDF containing the case background, the legal basis for the ruling, and the penalty outcome. The site exposes a search interface that accepts filters for topic, legal basis, keyword, and date range, though its list view is hard-capped at 200 rows per query.

The secondary source is the **国家法律法规数据库** (National Laws and Regulations Database), accessible at https://flk.npc.gov.cn/index^[46][49][50]^. Maintained by the Standing Committee of the National People's Congress, it serves as the authoritative digital repository for PRC legislation, administrative regulations, and local rules. We used it as the sole source for constructing the law knowledge base described in Section 3.5.

We restrict the study to **price-compliance** documents for two reasons. Price violations constitute one of the most common categories of e-commerce regulatory enforcement in China, and the underlying legal framework is well-delimited: the Price Law^[46]^, the Regulations on Administrative Penalties for Price Violations^[47]^, and related e-commerce and unfair-competition statutes^[49][50]^ together form a coherent rule set whose article structure lends itself naturally to structured legal reasoning.

![Figure 3-1: Screenshot of the cfws.samr.gov.cn penalty document search interface](figures/ch3_cfws_search_ui.png)

Figure 3-1 The search interface of the China Market Supervision Administrative Penalty Document Network (cfws.samr.gov.cn), showing topic and legal-basis filter controls used during data collection.^[45]^

## 3.2 Penalty document collection pipeline

### 3.2.1 EasySpider workflow

Manual downloading of hundreds of PDFs from a paginated government portal is neither scalable nor reproducible. We used **EasySpider**^[44]^, a no-code visual web-crawling tool that lets users define a task graph in a browser-based GUI and saves the result as a portable JSON configuration. Our task configuration is stored at `easyspider/tasks/358.json`; the task graph executes the following sequence:

1. Open the homepage at `https://cfws.samr.gov.cn/index.html`.
2. Click the login button and confirm the login action.
3. Navigate to the user entry point (XPath: `#user`) to reach the authenticated collection interface.
4. Enter the "collect" template via an iframe-embedded table that lists available collections.
5. **Loop "next page"**: iterate through all paginated list pages matching the active filter.
6. Within each page, extract the following fields for every document row: 文书编号 (document ID), 文书链接 (document URL), 当事人名称 (party name), 处罚机关 (enforcement authority), 处罚日期 (penalty date), 处罚内容 (penalty summary).

Output is written in CSV format (`outputFormat: "csv"`). Duplicate removal at the EasySpider task level was not enabled (`removeDuplicate: 0`); deduplication was handled in the downstream cleaning step.

Importantly, the filter configuration — price-topic keyword, legal-basis selection (including the Price Law and the Regulations on Administrative Penalties for Price Violations), and year-wise slicing to work around the 200-row list cap — was set up through the portal's advanced-search UI **before** task execution rather than being embedded in the JSON task file. The operator enters the desired constraints in the browser, then triggers EasySpider to replay the navigation and harvest whatever the server returns for that filter state. Year-by-year slicing was therefore a manual but necessary step: by submitting one query per calendar year, we kept each result set within the 200-row display limit and ensured complete coverage across multiple years.

![Figure 3-2: EasySpider task graph for penalty-document collection (task 358)](figures/ch3_easyspider_task.png)

Figure 3-2 EasySpider task graph (task 358.json) for collecting penalty documents from cfws.samr.gov.cn. The graph progresses from homepage login through iframe navigation to paginated row extraction.^[44]^

### 3.2.2 Engineering challenges

Running an automated workflow against a live government portal introduced several practical complications.

**Login state management.** The portal requires an authenticated session before the collection interface becomes accessible. EasySpider's XPath-based click sequences handle the login flow, but any session timeout between batches required restarting the task from the login step. We did not encounter CAPTCHA challenges during our runs, though the portal documentation warns that anti-bot measures may be activated under high-frequency access.

**Iframe navigation.** The collection template is rendered inside an HTML iframe, which means the crawler's DOM context must be switched before any element within the template can be targeted. Task 358 explicitly accounts for this by including an iframe-entry step; without it, EasySpider would attempt to locate list elements in the outer page and fail silently.

**200-row display cap.** The portal's result list shows at most 200 rows regardless of how many documents match the query. There is no programmatic way to request a higher page count. We mitigated this by issuing separate queries for each calendar year, thereby ensuring that no single query's result set exceeded 200 rows. The downside is that years with more than 200 matching penalty decisions would still be under-sampled; we have no way to quantify this gap precisely.

**Pagination batching.** Each year's query generates its own paginated result set. EasySpider's "next page" loop handles pagination within a single query session, but the operator must manually re-run the task for each year slice. This added coordination overhead but was manageable given the relatively modest total volume.

One limitation we acknowledge openly: we do not retain a per-document exclusion log recording exactly which raw URLs were excluded at any stage. The 791 PDFs we ultimately downloaded and the 780 samples that survived cleaning (Section 3.3) represent our best reconstruction of the collection as-is.

## 3.3 From raw PDFs to evaluation set (v4)

### 3.3.1 PDF extraction

The 791 downloaded penalty PDFs were processed using `scripts/data/smart_pdf_extractor.py`. The extractor applies a cascade of parsing strategies — direct text layer extraction first, with an OCR fallback for scanned images — and outputs a structured record for each document. The record preserves the case facts section (违法事实), the legal basis (法律依据), and the penalty outcome (处罚结果), which together constitute the three ground-truth components we annotate.

After extraction, each record was **anonymized**: party names, addresses, and registration numbers were replaced with generic placeholders to reduce the risk of re-identification and to prevent models from relying on entity names rather than case logic. The `input.case_description` field that models receive is therefore a cleaned narrative that describes the conduct without exposing the original business identity.

### 3.3.2 Evolution from eval_159 to eval_754 to v4

The evaluation set went through three generations before we settled on the final 780-sample corpus.

`eval_159` was an early 159-sample subset assembled to validate the end-to-end pipeline quickly. It served its purpose — all three baseline models were piloted against this set (Section 4.4) — but its small size made per-class analysis unstable and it did not represent the full range of violation types.

`eval_754` was a mid-scale expansion that included LLM-rewritten case descriptions to augment difficulty. The rewriting step introduced a distributional gap between the synthetic descriptions and authentic penalty document language, which undermined the ecological validity of the evaluation. Results on `eval_754` therefore overestimated model sensitivity to stylistic cues rather than legal substance.

`v4` (the current set, `eval_dataset_v4_final.jsonl`) returns to **authentic penalty document text** as the primary input source. The 791 raw PDFs yielded 780 valid samples after removing records with incomplete case descriptions or format anomalies that did not conform to the evaluation pipeline's structural requirements. No per-item exclusion log was maintained for this filtering step; the 11 removed documents are not recoverable from repository artifacts alone.

![Figure 3-3: Data pipeline flowchart from raw PDFs to eval_dataset_v4_final.jsonl](figures/ch3_pipeline_flowchart.png)

Figure 3-3 End-to-end data pipeline: 791 raw penalty PDFs → text extraction and anonymization → annotation and structuring → 780-sample eval_dataset_v4_final.jsonl. Intermediate sets eval_159 and eval_754 are shown for historical context.

## 3.4 Evaluation-set structure and statistics

### 3.4.1 JSON schema

Each sample in `eval_dataset_v4_final.jsonl` is a single JSON object. A representative (truncated, anonymized) example from the file looks like this:

```json
{
  "id": "CASE_0001",
  "source_pdf": "esfile_....pdf",
  "region": "南平市市",
  "tier": 1,
  "input": {
    "case_description": "(case narrative, may contain line breaks and anonymization markers)",
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
  "review_reason": "...",
  "suggested_action": "..."
}
```

The top-level fields are:

- **`id`** — a sequential case identifier (CASE_0001 through CASE_0780) used for cross-referencing results files.
- **`source_pdf`** — a hash-style filename pointing to the originating document; used for overlap detection between the evaluation set and the case base (Section 3.6).
- **`region` / `tier`** — geographic origin and difficulty tier assigned during construction; `tier` was used in filter scripts to control set composition.
- **`input.case_description`** — the anonymized case narrative passed as input to all models; this is the only text the model sees.
- **`input.platform`** — the e-commerce platform named in the document, if any; may be null.
- **`ground_truth.is_violation`** — binary label (true/false).
- **`ground_truth.violation_type`** — the specific violation category drawn from the nine-class taxonomy (or "无违规" for compliant cases).
- **`ground_truth.qualifying_articles`** — the statutory articles that establish the violation (定性条款).
- **`ground_truth.penalty_articles`** — the statutory articles that authorize the penalty (处罚条款).
- **`ground_truth.penalty_result`** — the monetary or non-monetary sanction imposed.
- **`_debug.leakage_found`** — set to true if the case narrative was detected to contain information that directly reveals the ground-truth label (used during quality review).
- **`_debug.text_length`** — character count of the raw case description before truncation.
- **`review_*` fields** — metadata for the human review queue; records flagged as `fn_candidate` (false-negative candidates) were prioritized for manual inspection.

### 3.4.2 Violation-type distribution

The 780 samples split into 489 violation cases and 291 compliant cases. Among the 489 violations, ten subtypes appear; their counts are shown in Table 3-1. The distribution is heavily skewed: 不明码标价 (unpriced display) accounts for 221 of the 489 violation records — more than the next two subtypes combined — while 哄抬价格 (price gouging) and 不履行价格承诺 (non-fulfilment of price commitment) each appear exactly once.

| Violation type | Count |
|---|---:|
| Compliant (no violation) | 291 |
| 不明码标价 (Unpriced display) | 221 |
| 政府定价违规 (Government-priced violation) | 117 |
| 标价外加价 (Surcharge above marked price) | 73 |
| 误导性价格标示 (Misleading price display) | 49 |
| 未识别 (Unidentified sub-type) | 14 |
| 变相提高价格 (Disguised price hike) | 6 |
| 虚假价格比较 (Fake price comparison) | 5 |
| 虚假折扣 (Fake discount) | 2 |
| 不履行价格承诺 (Non-fulfilment of price commitment) | 1 |
| 哄抬价格 (Price gouging) | 1 |
| **Total** | **780** |

Table 3-1 Distribution of violation types in eval_dataset_v4_final.jsonl (n=780).

## 3.5 Law knowledge base (691 articles)

The 691-article law knowledge base was built by retrieving legislation from the 国家法律法规数据库^[46][49][50]^ through a series of targeted batch searches. We submitted queries using keywords related to price enforcement, e-commerce regulation, and unfair competition (e.g., 价格法, 明码标价, 价格违法, 电子商务, 反不正当竞争, 网络交易) and downloaded matching documents as DOCX files from the official portal. The downloaded files were organized into three subdirectories under `data/laws/`:

- **中央** — national-level legislation (Price Law, E-Commerce Law, Anti-Unfair Competition Law, Regulations on Administrative Penalties for Price Violations, etc.)
- **浙江** — provincial-level rules from Zhejiang, reflecting the project's regional focus on e-commerce enforcement
- **平台规则** — platform-specific pricing rules from major e-commerce operators

![Figure 3-4: Screenshot of the flk.npc.gov.cn law database search interface](figures/ch3_flk_search_ui.png)

Figure 3-4 The search interface of the National Laws and Regulations Database (flk.npc.gov.cn), used to retrieve price-compliance legislation for the knowledge base.^[46]^

Article-level chunking was performed by `src/rag/data_processor.py` (`LawDocumentExtractor.process_all_laws("data/laws")`). The extractor iterates through DOCX paragraph sequences and uses a regular expression to detect article boundaries — any paragraph beginning with "第…条" is treated as the start of a new chunk. Subsequent paragraphs are concatenated into the same chunk until the next article heading appears. Each resulting chunk record carries four fields:

- **`chunk_id`** — a unique identifier of the form `{law_name}_art_{article_number}`.
- **`law_name`** — the short name of the statute (e.g., "价格法").
- **`law_level`** — one of 中央, 浙江, or 平台规则, matching the source subdirectory.
- **`article`** — the article label extracted from the heading (e.g., "第十三条").
- **`content`** — the full text of the article, including any clause numbers within it.

Across all 691 chunks, the mean `content` length is approximately 140 characters, with a range of 18 to 816 characters. The brevity of most articles reflects the concise legislative drafting style common in Chinese administrative law; the longest articles tend to be definitional or penalty-schedule provisions that enumerate multiple sub-clauses.

## 3.6 Case base (133 cases) and leakage control

In addition to the law knowledge base, we maintain a case base of 133 historical penalty summaries. These were compiled separately from the main evaluation pipeline and are stored in ChromaDB alongside the law chunks. Their intended purpose is to give the retrieval system concrete precedents — factual descriptions of past enforcement decisions — that might help distinguish between closely related violation types.

However, a leakage check against the evaluation set revealed approximately 8 `source_pdf` identifiers that appear in both the case base and the evaluation set. Because these overlapping records originate from the same underlying penalty documents, injecting them as "similar cases" during evaluation would allow the model to receive near-duplicate information from the ground-truth source — a form of same-source contamination.

To eliminate this risk, the formal evaluator pipeline (`src/rag/evaluator.py`) calls `retrieve(..., laws_k=3, cases_k=0)`, passing `cases_k=0` to suppress all case injection. The agent pipeline (Chapter 6) applies the same constraint: `IntentAnalyzer._decide_topk` hard-codes `suggested_cases_k` to 0, so the `AdaptiveRetriever` never returns case chunks regardless of the query. The `RAGPromptTemplate` still contains a "similar cases" placeholder in its system prompt; when `cases_k=0`, that slot is populated with the string "暂无相似案例" (no similar cases available), ensuring the model's prompt is structurally consistent across all runs.

The 8 overlapping `source_pdf` values represent roughly 6% of the case base and about 1.6% of the 489 evaluation violation sources — a small fraction, but large enough in absolute terms to distort per-type metrics if admitted.

## 3.7 Limitations

Three limitations of the dataset deserve explicit mention.

We do not have a per-item exclusion log for the transition from 791 raw PDFs to the 780 final samples. The 11 dropped records were filtered out during pipeline construction, but no separate manifest file was written. If a reviewer needs to audit the exact exclusion criteria, the repository artifacts are insufficient on their own; we can only say that the drops were due to structural incompleteness or format incompatibility.

The violation-type distribution is heavily imbalanced. 不明码标价 accounts for 221 of the 489 violation samples — roughly 45% — while four subtypes have counts of 6 or fewer. Per-class F1 scores for 变相提高价格, 虚假折扣, 不履行价格承诺, and 哄抬价格 are therefore statistically unreliable; any model that achieves high macro-averaged F1 on the full set may still completely misclassify the rarest categories. We report per-class breakdowns where available but caution against drawing strong conclusions from them.

The 200-row cap on the portal's search interface means that any calendar year with more than 200 matching price-compliance decisions will be under-sampled in our corpus. Since we cannot query the total counts without triggering the cap, we cannot quantify this truncation effect precisely. The dataset is best understood as a representative, rather than exhaustive, sample of publicly available price-compliance enforcement records from the years covered.

## 3.8 Summary of this chapter

This chapter described the two-source data collection strategy, the EasySpider-based automation pipeline for harvesting penalty PDFs from cfws.samr.gov.cn, and the multi-stage cleaning and structuring process that produced `eval_dataset_v4_final.jsonl` with 780 samples (489 violation + 291 compliant) across ten violation subtypes. We also documented the 691-article law knowledge base compiled from flk.npc.gov.cn, its article-level chunking procedure, and the leakage-control decision to set `cases_k=0` in all formal evaluations. The resulting dataset, while not without class-imbalance and coverage limitations, provides a realistic and reproducible benchmark for comparing baseline LLM inference, retrieval-augmented generation, and agent-based approaches to price-compliance analysis — the subject of Chapters 4 through 6.
