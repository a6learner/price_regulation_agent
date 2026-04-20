# 5 Retrieval-Augmented Generation Route

## 5.1 Motivation and Design Goals

The baseline system described in Chapter 4 treats every compliance query as a pure generation problem: Qwen3-8B receives a case description, infers whether a price violation occurred, and then constructs a legal rationale from whatever statutory knowledge was encoded during pre-training. That approach works reasonably well as a first pass — achieving 89.35% binary accuracy on the 780-sample evaluation set — yet it carries a structural weakness that becomes apparent once one examines its failure modes closely.

Large language models frequently hallucinate specific statutory provisions^[60]^. In the price-compliance domain this is especially damaging: a model might confidently assert that a merchant violated Article 14 of the Price Law when the relevant provision is actually Article 13, or cite a regulation that has since been superseded. The end user — whether a regulator writing an enforcement memo or a merchant deciding whether to contest a fine — has no way to verify the model's claim without independently consulting the original statute. Absent an evidence trail connecting each conclusion to a retrievable text fragment, the system cannot be audited or corrected.^[6]^^[55]^

A second weakness is temporal: pre-training data has a knowledge cutoff, so any statutory amendment issued after the model's training window is invisible to it. Price-related regulations in China have evolved steadily; the Market Supervision Administration has issued or revised several pricing rules in recent years, and a frozen model cannot reflect those changes.^[7]^

Retrieval-Augmented Generation (RAG) was introduced precisely to address this class of problems^[6]^. Rather than relying exclusively on parametric knowledge, RAG couples the language model with an external retrieval index so that each inference step is grounded in verifiable text fragments. For legal reasoning, this provides two practical benefits: the cited articles are traceable to actual documents, and the index can be updated without retraining the model.^[57]^

Against this backdrop, we define four concrete design goals for the RAG route in this thesis. We frame them as measurable constraints rather than aspirational principles, so that the evaluation results in Sections 5.7 and 5.8 can be directly interpreted as success or failure against each goal.

(1) **Grounded generation.** Every compliance conclusion should be derivable from at least one retrieved law article that appears verbatim in the prompt, so an auditor can cross-check it.

(2) **Controllable evidence scope.** The system must avoid injecting irrelevant statutes into the prompt, which would both inflate token count and confuse the model with spurious legal context.

(3) **Latency compatibility.** The retrieval overhead should keep the per-sample wall-clock within a factor of roughly two compared to the baseline (~7 s); in practice the target is under 10 s.

(4) **Separation of retrieval and generation.** The retrieval module should be independently testable and swappable — if a better embedding model becomes available, replacing it should not require touching the generation prompt.

The remainder of this chapter describes how each goal is realized in the implemented pipeline.

---

## 5.2 Pipeline Overview

The RAG pipeline follows a linear document-to-answer flow with six distinct stages:

**Document ingestion → Chunking → Hybrid retrieval → RRF fusion → Re-ranking → Dynamic top-k → Prompt assembly → Qwen3-8B inference**

At ingestion time, law articles stored as DOCX files in `data/laws/` are extracted and split into article-level chunks, then embedded and persisted in a ChromaDB collection. A separate BM25 index is constructed over the same chunks.

At query time, a case description is used as both the dense query and the BM25 query. The dense retriever (BAAI/bge-small-zh-v1.5) returns a ranked list of candidate articles; the BM25 retriever returns another. The two lists are fused via Reciprocal Rank Fusion (RRF), and the merged top list is passed to a CrossEncoder re-ranker (BAAI/bge-reranker-v2-m3). After re-ranking, a distance-threshold filter and a dynamic top-k selector reduce the candidate set to a compact, high-confidence group of law articles. Those articles, formatted as `laws_context`, are inserted into the system prompt together with the case description. Qwen3-8B then generates the compliance verdict and rationale in the same JSON schema as the baseline.

A figure placeholder is provided below:

![Figure 5-1: RAG pipeline — from document ingestion to LLM inference](figures/ch5_rag_pipeline.png)

Figure 5-1 End-to-end RAG pipeline. Arrows show the data flow from raw DOCX statutes through chunk indexing, hybrid retrieval, RRF fusion, CrossEncoder re-ranking, and dynamic top-k selection to final Qwen3-8B inference.

---

## 5.3 Document Processing and Indexing

### 5.3.1 Law Corpus Chunking

Before any model call can happen at query time, the law corpus must be transformed from DOCX files into a searchable, machine-readable index. This offline indexing phase is the foundation of the entire RAG pipeline, and the quality of the chunks produced here directly determines the ceiling of what the retriever can return.

The statutory source material spans multiple Chinese price-related laws and administrative regulations downloaded from the National Laws and Regulations Database (flk.npc.gov.cn) as DOCX files. These include the Price Law of the People's Republic of China, the Provisions on Administrative Penalties for Price Violations, the E-Commerce Law, the Anti-Unfair Competition Law, and several supplementary regulations on pricing practices.

Each DOCX file is processed by `LawDocumentExtractor.process_all_laws("data/laws/")` in `src/rag/data_processor.py`. The extractor walks the paragraph stream and uses a regular expression that matches the pattern `第[零一二三四五六七八九十百]+条` (i.e., "Article N" in Chinese) as a segment boundary. Every time a new article header is detected, the previous article's accumulated paragraphs are flushed as a completed chunk. Subsequent paragraphs before the next article header are appended to the current chunk.

Each resulting chunk carries five fields:

| Field | Description |
|---|---|
| `chunk_id` | Globally unique identifier within the corpus |
| `law_name` | Short title of the parent statute (e.g., "价格法") |
| `law_level` | Hierarchical tier: central / provincial / platform rule |
| `article` | Article label string (e.g., "第十三条") |
| `content` | Full text of the article body |

The final corpus contains **691 articles**. Content lengths range from 18 to 816 characters, with an arithmetic mean of approximately **140 characters** per chunk — compact enough to fit many articles into a single prompt without exceeding context limits. The article-level granularity was chosen deliberately over finer sub-article splitting (e.g., splitting by sub-clause) or coarser chapter-level grouping. Sub-article splits risk orphaning a clause from the interpretive context provided by the article preamble; chapter-level chunks are too large to embed meaningfully with a 512-dimensional model and would consume too much of the prompt's context window. An article is the natural legal unit: it defines a complete obligation, prohibition, or penalty, and it is also the unit that enforcement decisions cite when justifying a penalty.

### 5.3.2 Vector Encoding

Each chunk's `content` field is encoded with **BAAI/bge-small-zh-v1.5**, a 512-dimensional sentence-transformer model tailored for Chinese text^[11]^. The choice of bge-small-zh over the larger bge-m3 model^[12]^ was deliberate: for short legal article snippets averaging 140 characters, the smaller model achieves acceptable retrieval quality while consuming roughly one-fifth the memory footprint and encoding noticeably faster. In a deployment scenario where the vector index must coexist with the CrossEncoder re-ranker and the language model on the same machine, that memory saving is non-trivial.

The 512-dimensional embeddings are stored as float32 tensors. At query time the case description is encoded with the same model, and cosine distance is used as the similarity measure throughout. Cosine distance is preferred over Euclidean distance because it is invariant to the magnitude of the embedding vector, which can vary across documents of different lengths. For short legal article texts this is particularly important: a long article would naturally have a higher-norm embedding than a short one, and Euclidean distance would artificially penalize short articles in nearest-neighbor search.

All embeddings are computed offline at index-build time and loaded into memory at system startup. Incremental updates — adding new regulations as they are enacted — require only re-encoding and re-inserting the new chunks; the existing collection is not invalidated.

### 5.3.3 ChromaDB Collection

Embedded chunks are persisted in a **ChromaDB**^[39]^ collection under `data/rag/chroma_db`. ChromaDB was chosen for its zero-configuration local operation and its native support for metadata filtering, which allows the retriever to optionally restrict results to specific `law_level` values or to a particular statute by `law_name`. Alternative vector databases such as Milvus^[38]^ or FAISS^[37]^ offer higher throughput at scale, but for a 691-article corpus the performance difference is negligible, and ChromaDB's simpler deployment model reduces operational complexity. The collection is built once by `rag_build_vector_db.py` and reused across all evaluation runs; because the underlying HNSW index is persisted to disk, cold-start latency on subsequent runs is negligible.

---

## 5.4 Hybrid Retrieval

Hybrid retrieval combines two complementary signals to produce a ranked list of candidate articles. We adopt a two-component design rather than a three- or four-component ensemble because the primary trade-off in Chinese legal retrieval is between lexical precision and semantic generalization: BM25 handles the former, and dense retrieval handles the latter. Adding more components (e.g., sparse learned representations such as SPLADE) would increase index complexity and serving cost without a clear benefit on a 691-article corpus.

### 5.4.1 BM25 Component

BM25 (Best Match 25) is a classical probabilistic ranking function that scores documents by term frequency saturation and inverse document frequency^[9]^. It operates purely on token overlap, making it complementary to dense retrieval: BM25 rewards exact keyword matches (e.g., a case description that explicitly names "明码标价" will strongly retrieve Article 13 of the Price Law), whereas dense retrieval captures semantic paraphrase where the surface terms differ.

The BM25 index is built over the `content` fields of all 691 chunks after character-level or word-level tokenization of Chinese text. Standard BM25 parameters (k1 = 1.5, b = 0.75) are used throughout, matching the defaults commonly reported in the information retrieval literature^[36]^. The rank list returned by BM25 is treated as one input to the fusion step.

### 5.4.2 Dense Component

Dense passage retrieval encodes both queries and documents into a shared continuous embedding space, allowing retrieval by nearest-neighbor search rather than lexical overlap^[8]^. For short Chinese legal text, this is particularly valuable when a case description uses colloquial phrasing to describe behavior that the statute expresses in formal legal language. A complainant might write "the seller did not display the price clearly"; the relevant statute uses "未依法明码标价" — lexically different, but semantically close enough for the dense model to bridge.

The top-$N$ nearest neighbors retrieved from ChromaDB by cosine distance form the dense candidate list. In the full evaluation, the initial dense pool size is set equal to `laws_k` (typically 3), and a larger pool of candidates (up to twice `laws_k`) is passed to the subsequent fusion and re-ranking stages to give the CrossEncoder a diverse input set.

### 5.4.3 RRF Fusion

The two ranked lists — one from BM25 and one from the dense retriever — are combined using **Reciprocal Rank Fusion (RRF)**^[10]^. Given a document $d$, its RRF score aggregates its position across all input lists:

$$\text{RRF}(d) = \sum_{i} \frac{1}{k + \text{rank}_i(d)}$$

where $k = 60$ (the standard default) dampens the influence of very highly ranked documents and prevents a single-list monopoly. Documents that appear near the top of *both* lists receive the highest fused scores, effectively implementing a voting scheme. Documents absent from a list are treated as having infinite rank (zero contribution).

RRF requires no per-query training and is robust to score-scale differences between the BM25 and cosine-distance metrics, which would otherwise make direct score aggregation unreliable.

### 5.4.4 CrossEncoder Re-ranking

The RRF-fused list is passed to a **CrossEncoder**^[13]^ for re-ranking. Unlike the bi-encoder used at retrieval time (which scores query and document independently), a CrossEncoder processes the concatenated query–document pair through the full transformer stack, enabling richer attention interactions. We use **BAAI/bge-reranker-v2-m3** for this step.

The re-ranker receives the top-$M$ fused candidates (where $M$ is the initial retrieval pool size) and outputs a scalar relevance score for each. The list is sorted by this score, and the top entries are forwarded to the dynamic top-k selector. Because re-ranking is applied only to a small candidate pool rather than the entire 691-article corpus, the latency cost is manageable — the ablation study in Section 5.7 confirms that adding re-ranking does not materially increase wall-clock time.

---

## 5.5 Dynamic Top-k and Score Thresholds

Not every query benefits from retrieving the same number of law articles. A simple dispute about whether a price tag was displayed may be fully resolved by one or two articles, while a complex multi-violation case involving overlapping statutes needs broader coverage. Injecting too many articles into the prompt wastes context budget and risks confusing the model with tangentially relevant provisions; injecting too few risks missing the governing statute entirely.

We implement a three-tier **dynamic top-k** strategy based on the average cosine distance of the top-3 re-ranked results:

- If the mean distance of the top-3 candidates is **below 0.10**, the retrieval is considered high-confidence and the final law context is truncated to **2 articles**.
- If the mean distance falls in **[0.10, 0.15)**, moderate confidence, the context is set to **3 articles**.
- Otherwise, the full `laws_k` value (default 3, but up to 5 when the IntentAnalyzer suggests broader coverage) is used.

In all cases, only candidates that pass a distance threshold of **0.15** are considered; documents with distance ≥ 0.15 are filtered out before the mean is computed. A floor of `min_k=2` prevents the system from returning fewer than two articles even when confidence is high (a single article could be a false positive). The CrossEncoder re-rank score threshold `min_rerank_score` is left at its default of **0.0** during evaluation — no additional score-based pruning is applied beyond distance filtering.

The practical effect of this scheme is visible in the ablation: when the retriever is given free rein (no dynamic filtering), extraneous articles from adjacent legal domains occasionally appear in the prompt and degrade classification accuracy. The threshold at 0.15 was selected empirically by inspecting the distance distributions on a development subset. Intuitively, a distance of 0.15 in the bge-small-zh-v1.5 embedding space corresponds to articles whose phrasing is recognizably related to the query but not obviously on-point — transitional cases where the model is more likely to be misled than helped by inclusion.

An important consequence of combining the distance filter with the dynamic top-k is that the effective number of articles injected into the prompt is often *smaller* than `laws_k`, which keeps prompts compact and reduces hallucination risk on cases that have a clear single governing provision. The minimum guarantee of `min_k=2` ensures the model never lacks at least some statutory grounding even when the case description is unusually terse or ambiguous.

---

## 5.6 Prompt Assembly

With the evidence set finalized by the dynamic top-k selector, the pipeline moves to prompt construction. This step bridges the retrieval world (article chunks with metadata) and the generation world (an LLM system prompt). The assembly logic is deliberately simple: no summarization, no abstractive compression, no re-writing of the retrieved articles. The articles are inserted verbatim so that the model can reason directly against the statutory text, and so that the cited article keys in the model's output can be traced back to exact document locations without ambiguity.

After dynamic top-k selection, the surviving law articles are formatted into a `laws_context` block — a newline-delimited sequence of entries, each presenting the law name, article label, and article body. This block is injected into `RAGPromptTemplate.RAG_SYSTEM_PROMPT` alongside the case description.

The system prompt instructs the model to base its compliance judgement *only* on the provided articles, and to cite specific article keys in its output. Attribution-aware generation of this kind has been studied as a mechanism for reducing confabulation and improving verifiability of LLM outputs^[56]^. The output JSON schema is identical to the baseline — the same `is_violation`, `violation_type`, `legal_basis`, `reasoning`, and `cited_articles` fields — which makes cross-route comparison straightforward.

The template also contains a `cases_context` placeholder. During evaluation, **`cases_k` is set to 0** (no similar cases are retrieved), so `cases_context` is populated with the string "暂无相似案例" ("no similar cases available"). This is not merely a convenience: as noted in Section 5.3.1 and detailed in Section 6.4, the case base of 133 historical enforcement decisions overlaps with approximately 8 source PDFs present in the evaluation set. Injecting case context under those conditions would constitute same-source contamination.

---

## 5.7 Ablation Study

Ablation studies are standard practice for validating that each component of a multi-stage pipeline earns its place. Without ablation, a researcher cannot distinguish between a pipeline where every component contributes and one where a single dominant component does all the work while the others add complexity for no gain. Given that our pipeline has four distinct retrieval components (BM25, dense, RRF fusion, CrossEncoder), an ablation that removes each in turn provides a principled basis for the design choices.

### 5.7.1 Setup

To isolate the contribution of each retrieval component, we run four retrieval variants on the **first 154 samples** of the evaluation set, keeping the generation model (Qwen3-8B) and all other hyperparameters fixed. The four variants are:

- **bm25_only**: BM25 ranking, no dense retrieval, no re-ranking.
- **semantic_only**: Dense cosine-distance retrieval only, no BM25, no re-ranking.
- **rrf**: RRF fusion of both BM25 and dense lists, but no CrossEncoder re-ranking step.
- **rrf_rerank**: Full pipeline — RRF fusion followed by CrossEncoder re-ranking. This matches the configuration used for the main 780-sample evaluation.

Results are stored in `results/rag/rag_ablation_ablation_154__04-19__v4/`. Because the ablation covers a 154-sample subset, these numbers are not directly comparable to the 780-sample main results; they serve only to characterize component contributions within the same data slice.

### 5.7.2 Results

**Table 5-1** summarizes performance across the four variants on the 154-sample subset.

**Table 5-1** RAG ablation on the first 154 evaluation samples.

| Variant | Accuracy | F1 | Type Acc | Avg time (s) |
|---|---|---|---|---|
| bm25_only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| semantic_only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| rrf | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| rrf_rerank | **0.9026** | **0.9470** | **0.6299** | 8.11 |

Table 5-1 RAG ablation on the first 154 evaluation samples.

### 5.7.3 Analysis

The most striking finding is that `rrf_rerank` leads on every quality metric while remaining essentially indistinguishable from the other variants in wall-clock time — all four configurations run between 7.93 and 8.17 seconds per sample. The gain from adding the CrossEncoder is therefore essentially free in terms of latency, which is the expected behavior: re-ranking operates on a small candidate pool and the model is small.

Looking at individual metrics: binary accuracy climbs from 0.8766 (bm25_only) to 0.9026 (rrf_rerank), a gain of 2.6 percentage points. The F1 improvement is similar in magnitude (0.9319 → 0.9470). Violation-type accuracy — a harder metric that requires the model to name the specific violation category — shows the largest swing: 0.5844 for bm25_only versus **0.6299** for rrf_rerank, a gap of 4.55 percentage points. This is consistent with our expectation that precise identification of violation type depends on fine-grained semantic matching that BM25 alone cannot provide; the exact statutory wording for subtypes like "标价外加价" (surcharge above marked price) or "误导性价格标示" (misleading price display) differs enough from colloquial case descriptions that lexical retrieval misses the governing provision.

An interesting detail is that `rrf` (fusion without re-ranking) actually *decreases* type accuracy relative to `semantic_only` (0.5909 vs 0.6039). Adding BM25 can introduce lexically matching but contextually irrelevant articles — for instance, a general "price transparency" article that scores high on BM25 for almost any query. The CrossEncoder re-ranker corrects this: it assigns low scores to articles that are lexically similar but contextually mismatched, so `rrf_rerank` recovers and surpasses the semantic-only baseline.

The pattern reinforces a known result in the retrieval literature: fusion of multiple signals often helps average-case performance but can introduce noise that requires a re-ranking stage to clean up. In domain-specific retrieval settings like legal article matching, where the vocabulary is specialized and the candidate pool is small, the combination of BM25 fusion and CrossEncoder re-ranking appears to be a robust default worth the marginal complexity.

![Figure 5-2: Retrieval score distribution across ablation variants](figures/ch5_retrieval_score_dist.png)

Figure 5-2 Illustration of RRF fusion score distributions for the four ablation variants on the 154-sample subset.

![Figure 5-3: Ablation metric comparison bar chart](figures/ch5_ablation_bar_chart.png)

Figure 5-3 Bar chart comparing Accuracy, F1, and Type Accuracy across the four ablation variants. rrf_rerank consistently leads on all three metrics.

---

## 5.8 End-to-End RAG on the 780 Sample Set

The ablation study established the best retrieval configuration on a 154-sample slice. We now run the winning variant, `rrf_rerank`, on the complete 780-sample evaluation set. The larger set includes all violation types and both the compliant and non-compliant classes in their full proportions, so these numbers are the figures we report as the definitive RAG performance in the cross-route comparison.

When the full `rrf_rerank` pipeline is evaluated on all 780 samples, we obtain the results reported in the main comparison table (Table 5-2 below). The comparison also includes the Baseline figures from Chapter 4 for reference.

**Table 5-2** RAG vs. Baseline on the 780-sample evaluation set.

| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) |
|---|---|---|
| Binary accuracy | 89.35% | **89.85%** |
| Violation-type accuracy | 73.68% | **74.94%** |
| F1 | 91.47% | **92.01%** |
| Legal-basis quality avg | **0.8411** | 0.7321 |
| Reasoning quality avg | 0.8415 | **0.8685** |
| Avg response time (s) | 7.02 | 7.77 |

RAG improves binary accuracy by 0.50 pp, type accuracy by 1.26 pp, and F1 by 0.54 pp over the Baseline, while the average response time rises by only 0.75 seconds — a modest cost for the grounding benefit.

The **legal-basis quality score** presents an apparent paradox: it *drops* from 0.8411 to 0.7321 when moving to RAG. This requires careful interpretation. The legal-basis scorer, implemented in `src/baseline/response_parser.py`, is a heuristic keyword matcher: it awards points for the presence of predefined legal keywords (e.g., "价格法", "明码标价") and article-reference patterns ("第X条"). It does *not* perform any semantic legal analysis or cross-reference against ground-truth statutes.

Under the Baseline, the model generates legal rationales in free form and tends to use the exact vocabulary of those keywords, scoring well on the heuristic. Under RAG, the model is instructed to cite specific articles by their formal names and keys (e.g., "价格法_十三"), which may not always match the heuristic's keyword list. Moreover, RAG sometimes retrieves articles from less-cited statutes — provincial pricing rules, platform-specific regulations — whose titles fall outside the scorer's vocabulary. The retrieved context thus *widens* the lexical surface of the model's output in ways the heuristic was not calibrated to recognize.

This is a measurement artefact, not a legal quality regression. The reasoning quality score — which is less sensitive to exact vocabulary and more sensitive to the presence of logical connectives, factual claims, and structured analysis — moves in the opposite direction: 0.8415 (Baseline) → 0.8685 (RAG), an improvement of 2.7 points. That trend, combined with the classification gains, indicates that grounding on retrieved evidence genuinely improves the model's output even though the proxy legal-basis score fails to capture it.

This finding also has a broader methodological implication: heuristic surface-matching scores should not be taken as ground truth for legal argument quality. Future work that uses retrieval augmentation in legal domains may find that the actual correctness of cited statutes — verified by a legal expert or a structured ontology — diverges substantially from keyword-based proxies. We revisit this measurement concern more systematically in Chapter 7.

---

## 5.9 Limitations

Three limitations of the RAG route are worth acknowledging. We state them plainly here rather than burying them in footnotes, because honest documentation of a system's boundaries is part of responsible AI research.

The heuristic legal-basis scorer is a proxy, not a ground-truth legal correctness judgement. Its keyword-matching design rewards outputs that superficially resemble familiar legal vocabulary, and it penalizes — or simply misses — outputs that cite less common but legally valid provisions. The resulting score should be interpreted as a rough signal rather than a precise measure of legal accuracy.

The hybrid retriever can misfire for rare or novel violation types. The dataset contains only 6 samples of "变相提高价格" (disguised price hike) and 1 sample of "哄抬价格" (price gouging). For these minority categories, the BM25 and dense indices have little statistical signal from training-time priors, and the relevant articles may not rank highly if the case description uses atypical phrasing. The dynamic top-k system partially mitigates this by allowing a wider candidate set when confidence is low, but it cannot recover from a wholesale retrieval miss.

Retriever latency dominates the per-sample wall-clock. At 7.77 s average, the RAG route is already close to the design budget of ~10 s, and that budget is consumed almost entirely by the embedding, HNSW search, BM25 query, and CrossEncoder inference steps. Any meaningful latency reduction would require either a smaller re-ranker, an approximate index with lower recall, or batched inference — each of which involves a quality trade-off. For the 780-sample evaluation in this thesis, serial single-sample evaluation is fine; but a production system handling hundreds of concurrent requests per minute would need a very different serving architecture.

A fourth, more subtle limitation is that the evaluation dataset itself shapes what we can claim. The 780 samples are drawn from administrative penalty documents, which means they are cases where a regulatory authority already concluded a violation occurred. The distribution of violation types in the dataset (221 cases of 不明码标价 vs. only 1 case of 哄抬价格) reflects the actual frequency of enforcement actions in the source dataset rather than the true distribution of pricing violations in the market. Retrieval performance on underrepresented types is therefore hard to assess, and conclusions about the pipeline's strengths should be interpreted with that sampling caveat in mind.

---

## 5.10 Summary of This Chapter

Table 5-3 provides a quick-reference summary of the key design parameters used in the RAG pipeline as evaluated in this thesis.

**Table 5-3** RAG pipeline configuration parameters.

| Parameter | Value | Notes |
|---|---|---|
| Embedding model | BAAI/bge-small-zh-v1.5 | 512-dim, Chinese |
| Re-ranker | BAAI/bge-reranker-v2-m3 | CrossEncoder |
| Vector database | ChromaDB | Local HNSW |
| BM25 parameters | k1=1.5, b=0.75 | Defaults |
| distance_threshold | 0.15 | Cosine distance cutoff |
| min_k | 2 | Minimum articles injected |
| laws_k (eval) | 3 | Default retrieval pool |
| cases_k | 0 | Disabled (leakage control) |
| min_rerank_score | 0.0 | No additional score cutoff |
| Language model | Qwen3-8B | Via MaaS API |

This chapter has described the design, implementation, and evaluation of the Retrieval-Augmented Generation route for price compliance supervision. The pipeline couples Qwen3-8B with a 691-article law corpus through hybrid BM25 + dense retrieval, RRF fusion, CrossEncoder re-ranking, and distance-threshold dynamic top-k selection.

An ablation study on 154 samples showed that each component of the pipeline contributes to quality, with the CrossEncoder re-ranker providing the largest marginal gain (from 0.5909 to 0.6299 type accuracy) at negligible additional latency. On the full 780-sample set, RAG improves binary accuracy, type accuracy, and F1 over the Baseline while maintaining a response time under 8 seconds. The apparent drop in legal-basis quality score is attributed to a measurement artefact in the heuristic scorer rather than a true legal regression, as the reasoning quality score and classification metrics both improve.

From a system-design perspective, the RAG route occupies an appealing middle ground. It is substantially more grounded than the Baseline, meaningfully faster than the Agent, and requires no fine-tuning of the language model. Its principal limitation — the absence of adaptive intent-driven retrieval and structured self-correction — motivates the agent architecture described in the next chapter.

The next chapter builds on the retrieval infrastructure introduced here, embedding it within a six-node agent workflow that adds intent analysis, evidence grading, structured reasoning, self-reflection, and remediation guidance.
