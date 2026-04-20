# 3 Dataset Construction for Price Compliance Evaluation

Building a reliable evaluation dataset for price compliance reasoning is harder than it might appear. Administrative penalty documents are dense, jurisdiction-specific, and unevenly distributed across violation categories. The challenge is not simply one of volume — raw documents are plentiful enough on the public enforcement portal — but of structuring unruly PDF texts into machine-readable records that carry enough legal ground truth for rigorous model evaluation. This chapter describes how we assembled those records, what choices went into cleaning and labeling them, how the underlying law knowledge base was constructed, and what contamination risks we identified and mitigated before running any model experiments.

## 3.1 Data Source and Collection Pipeline

### 3.1.1 Source Portal

The primary data source is the China Market Supervision Administrative Penalty Document Portal (中国市场监管行政处罚文书网), accessible at [https://cfws.samr.gov.cn/index.html](https://cfws.samr.gov.cn/index.html). Operated by the State Administration for Market Regulation (SAMR), this portal publishes administrative penalty decisions issued at various levels of the enforcement hierarchy — national, provincial, municipal, and district. Each listed document typically records the party under investigation, the penalizing authority, the date of the penalty, and a brief summary of the violation finding, with an attached full-text PDF. Because the portal aggregates real enforcement outcomes rather than hypothetical scenarios, it provides a high degree of ecological validity: every case in the dataset corresponds to an actual administrative adjudication under Chinese price law.

We limited collection to documents whose penalty basis includes the *Price Law of the People's Republic of China* (中华人民共和国价格法, hereafter 价格法) or the *Provisions on Administrative Penalties for Price Violations* (价格违法行为行政处罚规定). These two instruments together constitute the main statutory backbone for price compliance enforcement in China, covering obligations such as price disclosure, restrictions on surcharges, and prohibitions on misleading pricing practices. Narrowing the source to these instruments ensured that every collected document pertained to the specific legal domain our system is designed to reason about.

### 3.1.2 EasySpider Automated Collection

Collection was carried out using EasySpider, a no-code web automation tool that represents tasks as JSON-defined node graphs. The task configuration used in this project is stored as `easyspider/tasks/358.json`. The node sequence proceeds as follows: the task opens the portal homepage, triggers the login interface, confirms the login action, clicks the authenticated user entry point (identified by the XPath selector `#user`), navigates into the collection template embedded inside an iframe, and then enters a page-iteration loop that steps through result pages while extracting six fields from each listed document: the document number, the document link (URL pointing to the detail page or PDF), the party name, the penalizing authority, the penalty date, and the penalty content summary.

One important detail about the portal's search interface: the site's listing view caps results at 200 per query. To collect beyond that ceiling, we applied a time-slicing strategy — running repeated searches with different year or date-range filters in the browser's advanced search panel before launching the EasySpider task. The filter parameters used (pricing-related hot topics, the two penalty basis texts cited above, and temporal partitions) are configured interactively in the browser rather than embedded inside the JSON task file itself, which means they are not automatically reproducible from the task configuration alone. Screenshots capturing these filter settings are retained as appendix material.

We should be honest about the engineering fragility involved here. The EasySpider task depends on maintaining a valid browser login state and on the iframe-based embedding of the collection template page. In practice, session timeouts, unexpected page reloads, and iframe loading delays all caused interruptions that required manual restarts. There is no anti-bot pipeline in the repository — no rotating proxy logic, no CAPTCHA handler, no request rate limiter — and the task's duplicate-removal flag (`removeDuplicate: 0`) is disabled, so deduplication had to be handled downstream. The output format is CSV, recording the six list-level fields described above. After completing the collection runs across all time slices, the raw pool contained approximately **791** penalty documents.

## 3.2 Data Cleaning and Structuring

The list-level CSV records produced by EasySpider contain only surface metadata — document number, party name, authority, date, and a short penalty summary. For compliance evaluation, we need the full case narrative: the specific conduct alleged, the pricing mechanism involved, and the legal articles cited as the basis for both the violation finding and the resulting penalty. That information is contained in the full-text PDFs linked from each record.

The processing chain starts with `scripts/data/smart_pdf_extractor.py`, which downloads each linked PDF and extracts the textual content. The extractor then parses the raw text to populate a structured JSON record for each document. The primary extraction targets are the case description (违法事实, the factual narrative of what the regulated entity allegedly did), the qualifying articles (定性条款, the statutory provisions that classify the conduct as a violation), and the penalty articles (处罚条款, the provisions that specify the applicable sanction). Alongside extraction, a desensitization step replaces identifiable information — full legal names of individuals, precise addresses — with anonymized placeholders, consistent with the principle that the evaluation dataset should not expose personally identifiable information unnecessarily.

From the 791 collected documents, **780** records were retained in the final evaluation dataset. The eleven excluded items were removed because their case descriptions were too incomplete to form a meaningful model input, or because they failed checks introduced as construction rules for the v4 dataset iteration. We do not maintain a per-item exclusion log in the repository; the decision to omit individual cases was made during processing and was not separately documented. This is a genuine limitation of our data pipeline: a future audit of exactly which documents were excluded and precisely why is not possible from the repository alone. For a compliance-critical application, a fully traceable exclusion record would be preferable.

## 3.3 Evaluation Dataset `eval_dataset_v4_final`

### 3.3.1 Schema

The final dataset is stored as `price_regulation_agent/data/eval/eval_dataset_v4_final.jsonl`, where each line is a self-contained JSON object. A representative (truncated) example is shown below:

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

The schema fields serve the following roles:

| Field | Description |
|---|---|
| `id` | Sequential case identifier used throughout evaluation scripts |
| `source_pdf` | Hash-based filename of the originating penalty document, used for deduplication and overlap analysis |
| `region` / `tier` | Geographic region of the issuing authority; `tier` supports difficulty stratification in construction scripts |
| `input.case_description` | Desensitized factual narrative passed to the model; the core model input |
| `input.platform` | E-commerce platform hint if applicable (may be `null`) |
| `input.goods_or_service` | Product or service category (may be `null`) |
| `ground_truth.is_violation` | Binary label: `true` for a confirmed violation, `false` for compliant |
| `ground_truth.violation_type` | Fine-grained type label drawn from the taxonomy used across enforcement documents |
| `ground_truth.qualifying_articles` | Statutory provisions that legally characterize the conduct as a violation |
| `ground_truth.penalty_articles` | Statutory provisions that authorize the specific sanction imposed |
| `ground_truth.penalty_result` | The actual penalty outcome recorded in the document (e.g., fine amount) |
| `_debug` | Pipeline metadata including the text source field, leakage detection result, and input character length |
| `review_*` | Flags and notes from a human-review queue, used during dataset quality control |

The separation between `qualifying_articles` and `penalty_articles` is deliberate. Chinese administrative enforcement often cites one set of articles to establish that a violation occurred and a separate set to justify the specific sanction. A model that correctly identifies the violation type but cites only one category of articles is providing an incomplete legal analysis; capturing both allows the evaluation to distinguish that case from one that gets both right.

### 3.3.2 Size and Label Balance

The dataset contains **780** samples in total: **489** labeled as violations and **291** labeled as compliant. The ratio is approximately 63% positive to 37% negative. This imbalance reflects the nature of the source material — the portal publishes penalty decisions, which by definition involve confirmed violations, so compliant samples had to be drawn from cases where the enforcement action was ultimately closed without finding a violation. The imbalance is worth keeping in mind when interpreting accuracy metrics: a naive model that always predicts "violation" would achieve roughly 62.7% binary accuracy, well below the baselines reported in Chapter 4.

### 3.3.3 Violation-Type Distribution

Among the 489 violation samples, the distribution across fine-grained violation types is heavily skewed:

| Violation Type (Chinese) | English Gloss | Count |
|---|---|---|
| 不明码标价 | Unpriced display (failure to display prices clearly) | 221 |
| 政府定价违规 | Government-priced goods violation | 117 |
| 标价外加价 | Surcharge above the marked price | 73 |
| 误导性价格标示 | Misleading price display | 49 |
| 未识别 | Unidentified sub-type | 14 |
| 变相提高价格 | Disguised price hike | 6 |
| 虚假价格比较 | Fake price comparison | 5 |
| 虚假折扣 | Fake discount | 2 |
| 不履行价格承诺 | Non-fulfilment of a price commitment | 1 |
| 哄抬价格 | Price gouging | 1 |

The top four categories — unpriced display (221), government-pricing violations (117), surcharges above the marked price (73), and misleading price display (49) — together account for 469 of the 489 violation samples, or around 96%. This concentration is not an artifact of sampling strategy; it mirrors the actual distribution of enforcement activity on the portal, where unpriced-display cases account for the largest share of administrative penalties under the 价格法 and 价格违法行为行政处罚规定 nationwide.

The 14 samples tagged "unidentified sub-type" arise in cases where the penalty document does not cite a sufficiently specific legal article to pin the conduct to one of the recognized violation categories. These samples carry a ground-truth `is_violation = true` label but lack a fine-grained type label, which means they contribute to binary accuracy measurement but cannot meaningfully contribute to violation-type accuracy.

### 3.3.4 Long-Tail Types and Their Implications

The final five categories in the table — disguised price hike (6), fake price comparison (5), fake discount (2), non-fulfilment of price commitment (1), and price gouging (1) — together contain only 15 samples. These counts are too small to draw reliable conclusions about model performance on those specific violation types. In particular, evaluating whether a model can consistently distinguish "fake price comparison" from "misleading price display" requires far more than five positive examples; any accuracy figure computed on five samples has a standard error wide enough to render it nearly uninterpretable.

We report type-accuracy results as an aggregate metric computed across all 489 violation samples, but readers should interpret the aggregate figure with the caveat that it is dominated by the top four types. Performance on the long-tail types is essentially anecdotal in this dataset. A production-grade evaluation of those categories would require targeted collection campaigns to gather sufficient samples, or alternatively the use of synthetic augmentation — an avenue we leave for future work.

## 3.4 Dataset Version Evolution

The evaluation dataset went through three identifiable iterations before arriving at `eval_dataset_v4_final`.

The first iteration, `eval_159`, was assembled as an early pipeline-validation set containing approximately 159 samples. Its primary purpose was not to produce publication-quality benchmarks but to verify that the full pipeline — PDF extraction, field parsing, ground-truth annotation, model invocation, metric computation — was functioning end to end without obvious errors. Running a small set to completion is a practical first step before committing computational resources to a larger collection; the numbers from `eval_159` were never intended to appear in the main thesis results.

The second iteration, `eval_754`, scaled up to 754 samples but introduced a problematic step in the construction process: portions of the case descriptions were rewritten by a large language model to smooth out OCR artifacts and improve readability. In retrospect, this introduced a stylistic drift that distanced the input text from the register of actual administrative penalty documents. Chinese enforcement decisions have a recognizable formal style — terse, legally precise, structured around specific statutory references — and LLM-rewritten paraphrases, even when semantically accurate, tend to lose that texture. For a thesis studying how well models reason over real compliance texts, an evaluation set where the inputs have already been partly processed by a language model introduces an awkward circularity: the evaluation sample may be easier to parse, or structurally different from deployment inputs, in ways that inflate or deflate measured performance.

The third iteration, `eval_v4` (finalized as `eval_dataset_v4_final`), corrected this by returning to the original penalty document text as the ground truth for input construction. Case descriptions were taken directly from the `violation_facts` field of each parsed PDF rather than from any LLM-reformulated version. This choice is more principled for a compliance thesis for a straightforward reason: if the downstream goal is to deploy a system that assists enforcement officers or platform operators in reviewing real penalty documents, then the evaluation inputs should be drawn from real penalty documents, not idealized restatements of them. The v4 dataset is accordingly more variable in text length and grammatical polish, but it is an honest representation of what the system will encounter in practice.

## 3.5 Law Knowledge Base Construction

### 3.5.1 Source and Organization

The law knowledge base was assembled from the National Laws and Regulations Database maintained by the National People's Congress at [https://flk.npc.gov.cn](https://flk.npc.gov.cn). After searching for statutes and regulations related to price regulation, e-commerce, anti-unfair competition, and online transaction management, we downloaded the relevant documents in DOCX format through the portal's batch download facility. Screenshots of these search and download steps are retained as appendix material for the thesis.

The downloaded files are organized under `data/laws/` in three subdirectories: one for central-level legislation (national statutes and State Council regulations), one for provincial-level rules (primarily Zhejiang province, given the regional focus of some enforcement data), and one for platform-level rules governing major e-commerce marketplaces. This three-tier structure reflects the layered nature of price regulation in China, where national statutes set the framework, provincial and municipal governments may issue implementing rules, and platform operators are increasingly required to maintain their own pricing compliance policies.

### 3.5.2 Chunking Strategy

Raw legal texts in DOCX format are processed by `LawDocumentExtractor.process_all_laws('data/laws')`, implemented in `src/rag/data_processor.py`. The chunking strategy is article-level (按条切段): a regular expression identifies paragraph boundaries that begin with the Chinese legal article marker "第…条" and treats each such match as the start of a new chunk. Subsequent paragraphs that fall under the same article — sub-clauses, provisos, definitional notes — are concatenated into the same chunk rather than split into separate records. This design keeps each chunk semantically coherent: a retriever fetching the chunk for 价格法 第十三条 returns the full text of that article, not an arbitrary mid-article fragment.

Each chunk carries five metadata fields: `chunk_id` (a unique identifier within the knowledge base), `law_name` (the full statute name), `law_level` (central / provincial / platform-rule), `article` (the article number, normalized to Arabic numerals), and `content` (the concatenated article text). The complete knowledge base contains **691 law chunks**. The average `content` length is approximately 140 characters, with a range from roughly 18 characters (short definitional clauses) to 816 characters (longer articles with multiple sub-provisions). The relatively compact average reflects the fact that Chinese statutory language is dense and precise: a single article often states a rule, its conditions, and an exception within two or three sentences.

Article-level chunking, as opposed to fixed-length or sentence-level chunking, is the appropriate granularity for legal retrieval because legal reasoning in administrative proceedings refers to articles, not arbitrary text windows [1]. A model or retriever that operates on article-aligned chunks can plausibly return the exact statutory provision cited in a penalty document, which is directly verifiable against the `qualifying_articles` and `penalty_articles` fields in the evaluation set.

## 3.6 Case Base and Contamination Control

### 3.6.1 Case Base Overview

In addition to the law knowledge base, the system maintains a case base of **133 historical case records** stored in a separate Chroma vector collection. Each record is a processed excerpt from an administrative penalty document — in this respect, the case base is structurally similar to the evaluation dataset, both being derived from documents on the SAMR portal. The intended use of the case base is to provide the retrieval-augmented generation system with relevant enforcement precedents when analyzing a new input: if a prior case involved similar conduct under similar legal provisions, a summary of that case can serve as reasoning context.

### 3.6.2 Overlap Analysis and Contamination Risk

The structural similarity between the case base and the evaluation set creates a potential data contamination problem. Because both are drawn from the same population of SAMR penalty documents, some source PDFs may appear in both collections simultaneously. If a model is provided with a retrieved case summary that was derived from the same underlying document as the evaluation sample it is currently judging, the retrieval step is effectively giving the model access to the answer — a form of test-time information leakage rather than generalization from related cases.

An internal leakage analysis found that approximately **8** `source_pdf` identifiers appear in both the case base and the evaluation set, representing roughly 6% of the 133-case case base and approximately 1.6% of the 489 evaluation violation sources. These are not large percentages in absolute terms, but even a handful of directly overlapping samples could introduce noise into the evaluation of retrieval-augmented routes, since a model retrieving a directly overlapping case would be receiving ground-truth-adjacent information that other samples do not receive. We note that these numbers reflect the author's count at the time of the overlap analysis and are subject to final re-verification; the figures should be treated as approximate rather than definitive.

### 3.6.3 Mitigation: cases_k=0

The decision to handle this contamination risk is straightforward: for all formal RAG and Agent evaluations reported in this thesis, the retrieval call is made with `cases_k=0`. In practice, this means `HybridRetriever.retrieve(query, laws_k=3, cases_k=0)` is passed in `src/rag/evaluator.py` and in the Agent's `AdaptiveRetriever` node, so no case text is injected into the model's context during evaluation. The `RAGPromptTemplate` system prompt still contains a placeholder for similar cases, but when `cases_k=0` the cases context variable is substituted with the string "暂无相似案例" (no similar cases available), so the model receives an explicit signal that no case context is present rather than simply an empty section [2].

This design choice has two important properties for cross-route comparisons. First, all three evaluation routes — Baseline, RAG, and Agent — share the same `cases_k=0` setting, meaning that none of them benefits from case retrieval. Performance differences between routes therefore reflect differences in law retrieval, prompting strategy, and reasoning architecture, not differences in how many historical precedents each route can access. Second, the anti-contamination design is conservative: it excludes case-level retrieval entirely even for the 98% of evaluation samples whose source PDFs do not overlap with the case base. This is a deliberate trade-off — we sacrifice the potential benefit of case context for all samples to ensure clean evaluation conditions across all samples.

The 133-case case base remains functional for production deployment scenarios, where there is no evaluation-set contamination concern, and for the Agent's remediation suggestion component, which in principle could draw on historical enforcement outcomes when formulating compliance recommendations. The formal exclusion from evaluation does not imply the case base is uninformative; it simply means its contribution is not assessed in the controlled experiments reported here.

## 3.7 Summary

This chapter has described the four main components of the data infrastructure: the raw document collection pipeline built on the SAMR enforcement portal and EasySpider, the cleaning and structuring process that converts raw PDFs into the 780-sample `eval_dataset_v4_final` evaluation set, the 691-chunk law knowledge base derived from the National Laws and Regulations Database, and the 133-case case base with its associated contamination controls.

Several honest limitations bear repeating. The per-item exclusion log for the 791 → 780 reduction was not retained, making it impossible to audit individual exclusion decisions after the fact. The violation-type distribution is severely skewed, with the five least common categories containing a combined 15 samples — too few for meaningful type-level performance analysis. And the case-base overlap, while small in relative terms, required a conservative `cases_k=0` design that leaves the benefit of case retrieval unmeasured in the formal experiments.

Chapter 4 introduces the Baseline system, the first of three evaluation routes, and establishes the performance reference point against which the retrieval-augmented and agent-based approaches are later measured.

---

### References (Chapter 3)

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *Advances in Neural Information Processing Systems*, vol. 33, pp. 9459–9474, 2020.

[2] ES. Gao et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation," *arXiv preprint arXiv:2309.15217*, 2023.
