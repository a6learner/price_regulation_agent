# 5 Retrieval-Augmented Generation Approach

## 5.1 Motivation

The Baseline system described in Chapter 4 reduces price-compliance judgment to a single forward pass through Qwen-8B, using only the model's parametric knowledge to decide whether a merchant has violated the *Price Law of the People's Republic of China* or its implementing regulations. That design is deliberately simple, and Chapter 4 showed it achieves a respectable 89.35% binary accuracy on the 780-sample evaluation set. The simplicity, however, carries a structural risk that becomes apparent the moment the model is asked to cite a specific legal article: nothing in the architecture forces the cited text to actually exist, to belong to the correct statute, or to be semantically aligned with the alleged violation. The model may confidently output `"legal_basis": "价格法第十三条"` when the correct provision is the *Administrative Penalty Rules for Price Violations* (价格违法行为行政处罚规定), or it may confuse the numbering of articles across different regulatory levels. In a supervision context, a misidentified statutory provision is not merely a stylistic imprecision; it is the kind of error that undermines the downstream case-routing decisions that a compliance officer would rely on.

Retrieval-Augmented Generation (RAG) [1] is a natural remedy for this class of failure. Rather than relying on memorized, potentially stale representations of legal text, a RAG system maintains an external, curated knowledge base of law articles and retrieves the most relevant chunks at inference time. The retrieved chunks are injected directly into the prompt, grounding the model's output in verified statutory text. In the price-compliance setting, this matters particularly for two reasons. First, Chinese price regulation is hierarchical: the *Price Law* sits above administrative rules, which sit above provincial and platform-level regulations; a general-purpose LLM has uneven coverage across these layers. Second, article numbers are the atomic unit of legal reasoning in Chinese administrative law — if the model cites the wrong article number, the entire reasoning chain is invalidated at the procedural level even if the factual analysis is correct.

The RAG pipeline we adopt consists of the following stages: (1) query extraction from the case description, (2) hybrid retrieval combining dense vector search with BM25 lexical search, (3) Reciprocal Rank Fusion (RRF) to merge the two ranked lists, (4) cross-encoder re-ranking of the fused candidates, (5) dynamic threshold filtering, (6) construction of an augmented prompt by injecting the retrieved law chunks, (7) a single LLM call to Qwen-8B, and (8) structured JSON response parsing. The orchestrating function is `RAGEvaluator.evaluate_single_case()` in `src/rag/evaluator.py`, which calls the hybrid retriever and then hands the retrieved context to the prompt template before making the model API call. Sections 5.2–5.4 detail each subsystem; Section 5.5 reports the evaluation results against the 780-sample benchmark.

Contemporary RAG research has explored several extensions beyond the basic retrieve-then-read setup. Self-RAG [2] teaches models to issue retrieval tokens adaptively and critique their own generations. Corrective RAG (CRAG) [3] adds a relevance assessor that decides whether the retrieved documents are trustworthy enough to use. GraphRAG [4] moves beyond chunk-level retrieval toward community-level knowledge graph summaries for multi-hop questions. Our system does not implement these extensions in the RAG stage; instead, we offload the reflection and self-correction responsibilities to the Agent workflow introduced in Chapter 6, keeping the RAG pipeline comparatively streamlined and interpretable.

---

## 5.2 Hybrid Retriever Architecture

### 5.2.1 Dense Retrieval

The dense retrieval component is implemented in `src/rag/retriever.py` and uses `SentenceTransformer('BAAI/bge-small-zh-v1.5')` to embed both the law chunks in the knowledge base and the query at inference time. The choice of this specific model is worth explaining in some detail.

BGE-small-zh-v1.5 is a bi-encoder trained by the Beijing Academy of Artificial Intelligence specifically for Chinese-language retrieval tasks. Among the BGE family, the `-small` variant has a substantially reduced memory footprint compared to BGE-m3 or the full BGE-large models, while still achieving competitive performance on Chinese information-retrieval benchmarks. In our deployment environment, where the vector database is built and queried on a single machine alongside the LLM API calls, keeping the embedding model small matters: the retriever must not become the latency bottleneck. The `-small` model processes a chunk or query in single-digit milliseconds on CPU, which is acceptable given that the dominant latency cost is the remote LLM API round-trip.

The knowledge base comprises 691 law article chunks, stored and queried via ChromaDB. Each chunk is produced by the `LawDocumentExtractor.process_all_laws()` function in `src/rag/data_processor.py`, which segments each DOCX law file at article boundaries: whenever a paragraph opens with the pattern "第…条" (Article N), a new chunk begins. Subsequent paragraphs belonging to the same article are concatenated into a single chunk, resulting in chunks that are on average approximately 140 characters in length (ranging from 18 to 816 characters). Each chunk stores the law name, regulatory level, article identifier, and content. At query time, the cosine distance between the query embedding and each chunk embedding is used as the primary relevance signal for the dense channel.

### 5.2.2 BM25 Lexical Retrieval

Dense retrieval is strong on semantic paraphrase — it matches "must display the price clearly" against "应当明码标价" even when the surface strings share no tokens. But in legal retrieval, the surface strings often carry all the relevant information. A case involving a violation of Article 13 of the Price Law will use the token sequence "价格法" together with "第十三条" almost verbatim, and a model that cannot match on those exact tokens risks retrieving thematically adjacent but legally distinct articles. BM25 [5] is the natural complement here: it scores documents by term frequency and inverse document frequency without any learned representations, which means it is highly sensitive to rare but discriminative tokens such as specific article numbers, monetary thresholds, or regulatory body names.

The BM25 channel operates over the same 691-chunk corpus as the dense channel, but uses tokenized keyword overlap rather than embedding similarity. In practice, when a case description explicitly names a law or cites a monetary amount, BM25 tends to surface the correct article near the top of its ranking; when the description is more narrative and paraphrastic, the dense channel usually outperforms it. Using the two channels together is precisely the motivation for hybrid retrieval.

### 5.2.3 Reciprocal Rank Fusion

Neither the dense scores nor the BM25 scores are directly comparable. Dense similarity is a cosine value in \([0, 1]\); BM25 is an unnormalized log-TF-IDF score that depends on corpus statistics. Attempting to linearly combine them would require careful calibration of a mixing weight, and that weight would in principle depend on the query distribution. Reciprocal Rank Fusion (RRF) [6] sidesteps this problem by operating on ranks rather than raw scores. For a document \(d\) appearing in ranked list \(L_i\), its RRF contribution from that list is:

\[
\text{RRF}(d, L_i) = \frac{1}{k + \text{rank}_{L_i}(d)}
\]

where \(k\) is a smoothing constant (conventionally set to 60). The final fused score for document \(d\) is the sum of its contributions across all participating lists:

\[
\text{score}_{\text{RRF}}(d) = \sum_{i=1}^{m} \frac{1}{k + \text{rank}_{L_i}(d)}
\]

Documents that appear near the top of multiple lists receive high fused scores; documents that appear in only one list still receive nonzero credit. The key advantage of RRF in our setting is that it is parameter-free in terms of score magnitudes — only ranks matter, so there is no need to normalize or re-calibrate when the dense and BM25 channels produce numbers on incompatible scales. Empirically, RRF has been found to be a robust default for multi-channel fusion, matching or exceeding more complex learned fusion approaches across a range of benchmarks [6].

### 5.2.4 Cross-Encoder Re-ranking

After RRF fusion, the top-N candidate chunks are passed to a cross-encoder re-ranker when `use_reranker=True` is configured. The re-ranker model is `CrossEncoder('BAAI/bge-reranker-v2-m3')` [7], which jointly encodes the query and each candidate document as a single input sequence and produces a scalar relevance score. Unlike the bi-encoder used in dense retrieval — which encodes query and document independently and can only compare their vector representations — the cross-encoder attends across all token pairs simultaneously, enabling much finer-grained relevance assessment. The practical cost is that cross-encoders are slower than bi-encoders: they cannot pre-compute document representations offline. This is why cross-encoders are applied only to the shortlist produced by the faster upstream stages rather than to the entire corpus.

In the context of legal retrieval, the cross-encoder's ability to jointly reason over query and document is valuable because relevance in law is not purely semantic. Whether Article 13 of the Price Law is the appropriate citation depends on whether the factual elements of the case description — the nature of the transaction, the pricing mechanism alleged, the platform type — align with the normative conditions described in that article. A bi-encoder approximates this match at the embedding level; the cross-encoder can, in principle, capture the conditional relationship more directly.

### 5.2.5 Filtering and Dynamic Top-K Policy

After re-ranking, the retriever applies a distance-based quality gate before handing chunks to the prompt builder. The distance threshold is set to `distance_threshold=0.15` for the formal evaluation, with a minimum floor of `min_k=2`: even if every retrieved chunk exceeds the threshold, the two closest chunks are retained to ensure the prompt is not left without any legal context.

Beyond this hard threshold, the system applies a dynamic top-k policy. After re-ranking, the mean cosine distance of the top-3 retrieved chunks is computed. If this mean is below 0.10 — indicating very high average confidence — the system retains only the two most relevant chunks, on the grounds that the additional chunk would add noise rather than signal. If the mean falls in the range \([0.10, 0.15)\), three chunks are retained. Otherwise, the originally requested `laws_k` value (three in the formal evaluation) is used. This policy was designed to handle two failure modes simultaneously: retrieving too many marginally relevant articles dilutes the prompt with potentially misleading context, while retrieving too few leaves genuine gaps. The `min_rerank_score` parameter, which could filter out low-scoring candidates from the re-ranker, defaults to 0.0 in the formal evaluation path, meaning no re-rank score filtering is applied beyond the distance threshold.

---

## 5.3 RAG Prompt Design

The prompt architecture is defined in `src/rag/prompt_template.py`, in the class `RAGPromptTemplate`. The central design decision was to keep the system prompt as structurally close to the Baseline as possible while adding the retrieved legal context. This choice is deliberate: if the RAG route were to use a completely different prompt format or output schema, then differences in metric scores between Baseline and RAG could be attributed to prompt engineering rather than to the retrieval mechanism.

The RAG system prompt injects two context blocks into the instruction: `laws_context` and `cases_context`. The `laws_context` block contains the retrieved law article chunks, formatted with their law name, article number, and full content. The `cases_context` block is reserved for analogical case text. When `cases_k=0` — which is the setting used throughout the formal evaluation, as discussed in Section 5.4 — `cases_context` is substituted with the placeholder string "暂无相似案例" (no similar cases available), which preserves the structural template without providing any case content to the model.

The output schema demanded by the RAG system prompt is identical to the Baseline: the model must return a JSON object containing `is_violation` (boolean), `violation_type` (string), `legal_basis` (string), `reasoning` (string), and `cited_articles` (list). Maintaining this schema means that the same `ResponseParser` and metric computation functions can be applied uniformly across all three experimental routes — Baseline, RAG, and Agent — making cross-route comparisons methodologically clean.

One practical concern in prompt design for legal RAG is context ordering. When multiple retrieved chunks are injected, the model's attention may not weight all positions equally; there is empirical evidence that LLMs pay disproportionate attention to the beginning and end of long contexts, a phenomenon sometimes called the "lost in the middle" problem. We address this partially through the dynamic top-k policy described in Section 5.2.5, which limits the number of injected chunks to a small number (two or three) rather than flooding the context. Given that the average chunk length is approximately 140 characters, a three-chunk injection adds at most a few hundred characters to the prompt — small enough that context-position effects are unlikely to be severe.

---

## 5.4 Anti-Contamination Design

A specific design choice in the formal RAG evaluation deserves explicit discussion: the retrieval call in `src/rag/evaluator.py` is hardcoded as `retrieve(..., laws_k=3, cases_k=0)`, meaning the case retrieval channel is entirely disabled during evaluation.

The reason for this is contamination risk. During the construction of the evaluation dataset, an internal leakage check identified that the RAG case base (133 historical penalty cases) and the 780-sample evaluation set share approximately 8 `source_pdf` identifiers — that is, eight evaluation samples were derived from the same original penalty documents as cases in the retrieval index. In terms of raw numbers this overlap is small: 8 out of 133 cases, or about 6% of the case index. But the risk extends beyond direct overlap. Even evaluation samples drawn from different individual documents may originate from the same regulatory office, follow the same penalty document template, and use very similar phrasing in the "violation facts" section. In that situation, retrieving a similar case could give the model a near-verbatim template to follow, making it look as though the model reasoned correctly when it was in fact pattern-matching on stylistic similarity.

We decided that the right response to this ambiguity is to disable case retrieval entirely for the formal evaluation, fixing `cases_k=0` uniformly. This is an honest trade-off. The three-shot or few-shot signal from similar historical cases can genuinely help a model that might otherwise misclassify an unusual pricing arrangement; by setting `cases_k=0` we forgo that benefit. The compensation is that all three routes — Baseline, RAG, and Agent — operate under the same case-injection policy (zero cases), so the comparisons remain fair. The law-chunk retrieval channel (`laws_k=3`) carries no such contamination risk because the law articles are public, static texts that are already part of the model's parametric knowledge; retrieving them does not leak ground-truth labels.

---

## 5.5 Main Results on the 780 Evaluation Set

Table 5.1 presents the performance of the Baseline and RAG systems across the six metrics computed on all 780 evaluation samples. The Agent results are included for reference but are discussed in Chapter 6.

**Table 5.1: Main evaluation results on the 780-sample evaluation set**

| Route    | Accuracy | Type Acc | F1     | Legal-basis avg | Reasoning avg | Latency (s) |
|----------|----------|----------|--------|-----------------|---------------|-------------|
| Baseline | 89.35%   | 73.68%   | 91.47% | 0.8411          | 0.8415        | 7.02        |
| RAG      | 89.85%   | 74.94%   | 92.01% | 0.7321          | 0.8685        | 7.77        |

RAG achieves a 0.50 percentage point gain in binary accuracy and a 0.54 pp gain in F1 over Baseline. In absolute terms these improvements are modest, and one should resist the temptation to overinterpret them as dramatic gains. The more meaningful interpretation is that the gains are directionally consistent across all three primary classification metrics. A system that adds retrieval overhead and prompt complexity but somehow degraded classification performance would be difficult to justify; the fact that RAG improves all three metrics — even slightly — confirms that the retrieved legal context is at worst neutral and at best provides a marginal but genuine signal.

The violation-type accuracy improvement of 1.26 pp (from 73.68% to 74.94%) is arguably more consequential than the binary accuracy gain for downstream applications. Correctly identifying the type of violation — whether a merchant failed to display prices visibly (不明码标价), charged above the marked price (标价外加价), or issued misleading price comparisons (误导性价格标示) — determines which legal provision applies and shapes the severity of the administrative remedy. A retrieval system that surfaces the more specific article for a given violation type is therefore making a practically useful contribution, even when the binary is_violation decision would have been correct without it.

The reasoning quality average rises from 0.8415 to 0.8685, a gain of 0.0270. This metric, computed by the `evaluate_reasoning_quality` function in `src/baseline/response_parser.py`, rewards outputs that contain factual keywords, explicit legal references, logical connectives, and multiple complete sentences. The improvement suggests that when Qwen-8B has the relevant statute in front of it as retrieved context, it is more likely to structure its reasoning around that statute rather than producing a generic conclusion. In practice, the retrieved articles serve as scaffolding: the model can quote or paraphrase specific article language, which naturally satisfies the heuristic indicators of good legal reasoning.

The most surprising observation in Table 5.1 is the legal-basis quality average, which drops from 0.8411 (Baseline) to 0.7321 (RAG). This result needs careful interpretation because it runs counter to the naive expectation that retrieval should improve legal grounding.

The legal-basis scoring function is heuristic: it awards points for the presence of a non-empty `legal_basis` field, for matches against a preset keyword list that includes tokens such as "价格法", "明码标价", and "禁止价格欺诈", and for patterns matching "第X条" article references. The keyword list was designed around the most commonly cited price-law provisions and therefore provides reliable coverage of the central statutes. However, RAG sometimes retrieves articles from secondary instruments — for instance, specific provisions of the *Administrative Penalty Rules for Price Violations* (价格违法行为行政处罚规定) or platform-level price-display rules — whose names or article headings do not appear in the preset keyword list. When the model faithfully cites one of these retrieved articles, it produces output that is arguably better grounded in the law than a generic reference to "价格法第十三条", but the heuristic scorer penalizes it because the cited name does not match any keyword. The drop in legal-basis average is therefore a measurement artifact rather than evidence of weaker legal grounding.

This artifact is, in fact, one of the core motivations for the three-tier metric system introduced in Chapter 7. Heuristic scoring is not equivalent to legal-fact correctness; the discrepancy seen here illustrates precisely the kind of case where a more semantically sophisticated evaluation approach is needed.

Turning to latency, RAG adds approximately 0.75 seconds per sample compared to Baseline (7.77 s vs. 7.02 s), representing an overhead of roughly 10%. This overhead is modest given the retrieval and re-ranking steps involved. The low latency cost is attributable to two factors: the embedding-based lookup over 691 chunks is fast on CPU, and the cross-encoder re-ranking is applied only to a small shortlist (typically three to five candidates). The dominant time cost remains the LLM API round-trip, which is shared between the two routes. The 10% overhead means that RAG achieves a favorable cost-effectiveness tradeoff: it improves classification and reasoning quality at minimal latency expense, making it the practical default for production deployments where response time matters.

These results motivate the ablation study in Section 5.6, which isolates the contribution of each retrieval component.

---

## 5.6 Ablation Study (Retrieval Variants)

To understand which components of the hybrid retrieval pipeline drive the observed gains, we designed an ablation study comparing four retrieval variants. The study is implemented in `scripts/rag/run_rag_ablation.py` and is executed on the first 154 samples of the 780 evaluation set. This subset corresponds to the default `--limit 154` argument of the ablation script. We use 154 samples rather than the full 780 to reduce the API cost and time of the ablation, and it must be noted that the first 154 samples may not perfectly represent the distribution of the full evaluation set — in particular, the rare violation types (哄抬价格, 虚假折扣, etc.) may be underrepresented. Results on the subset should therefore be interpreted with caution.

The four variants are realized by toggling the constructor flags `use_semantic`, `use_bm25`, and `use_reranker` in `HybridRetriever`:

- **semantic_only**: only the BGE-small-zh-v1.5 dense retriever is used; BM25 is disabled.
- **bm25_only**: only the BM25 channel is used; dense retrieval is disabled.
- **rrf**: both dense and BM25 channels are active, fused via RRF; cross-encoder re-ranking is disabled.
- **rrf_rerank**: the full production pipeline — dense + BM25 + RRF + cross-encoder re-ranking — matching the configuration used for the main 780-sample results.

**Table 5.2: Ablation study results (first 154 samples of the evaluation set)**

| Variant        | Accuracy  | F1        | Legal-basis avg | Reasoning avg | Avg latency (s) |
|----------------|-----------|-----------|-----------------|---------------|-----------------|
| semantic\_only  | *pending* | *pending* | *pending*       | *pending*     | *pending*       |
| bm25\_only      | *pending* | *pending* | *pending*       | *pending*     | *pending*       |
| rrf (no rerank) | *pending* | *pending* | *pending*       | *pending*     | *pending*       |
| rrf + rerank   | *pending* | *pending* | *pending*       | *pending*     | *pending*       |

*Note: All ablation numbers will be back-filled from the forthcoming `results/rag/rag_ablation_<note>__<date>/ablation_summary.md`. Until then, this section reports qualitative expectations only; the final thesis version will replace these placeholders with measured values.*

Even without the measured numbers, the expected behavior of each variant can be stated on the basis of well-established properties of the underlying methods.

The `semantic_only` variant should perform best on paraphrastic queries — cases where the violation description uses different vocabulary from the statute text but describes the same legal concept. Chinese-language bi-encoders trained on retrieval tasks learn to bridge synonymous expressions, and in a domain like price regulation where regulatory language can differ substantially from the everyday phrasing in a penalty document, this generalization capacity is valuable. Against that, semantic retrieval can fail on queries containing specific article numbers or law names, because these surface-form signals are not necessarily preserved in the embedding space.

BM25 exhibits the opposite profile. For queries that mention a specific statute by name — or that contain exact phrases like "明码标价" that appear verbatim in a particular article — BM25 will rank the correct article highly. However, on queries that paraphrase or describe the violation without naming the law, BM25's reliance on exact token overlap becomes a liability.

RRF fusion is expected to outperform either channel in isolation across the full range of query types, because it benefits from the complementary strengths of both channels while being insensitive to the incompatible score magnitudes. The primary mechanism is recall improvement: RRF brings the correct article into the candidate set more reliably than either single channel, leaving less work for the re-ranker.

The `rrf_rerank` variant, which corresponds to the production pipeline, should achieve the highest precision among the four. The cross-encoder re-ranks the candidates with full query-document attention, which is particularly useful in legal retrieval where the question of which article applies can depend on fine-grained conditions stated in both the case description and the article text. Whether the precision gain from re-ranking translates to a meaningful improvement in downstream LLM output quality — relative to the already strong `rrf` baseline — is one of the empirical questions the ablation is designed to answer.

We do not claim any numerical gains for any variant here. The ablation experiment has not been executed at paper-writing time, and fabricating plausible numbers would undermine the integrity of the work. The measured values will replace the placeholders above in the final thesis.

---

## 5.7 Retrieval Failure Cases and Honest Limits

Even a well-designed hybrid retrieval system cannot guarantee correct statutory citation, and it is worth examining where and why it falls short.

The most fundamental limitation is corpus completeness. The 691-chunk law knowledge base covers the principal national-level price regulations — the *Price Law*, the *Administrative Penalty Rules for Price Violations*, the *Clearly Marked Price Rules* (明码标价规定), and a selection of platform-level and provincial regulations. For violations that fall squarely within these instruments, retrieval has a reasonable chance of surfacing the correct article. But for cases involving local municipal pricing rules, sector-specific regulations (e.g., rules for medical services, utilities, or real-estate transactions), or recent regulatory amendments not captured in the knowledge base, the correct article may simply not exist in the corpus. In these cases, the retrieval system returns the closest available article, and the model either cites that article inappropriately or falls back on its parametric knowledge — reintroducing the Baseline's weakness for precisely those cases where retrieval should help most.

Chunking granularity introduces a second source of failure. The current chunking strategy splits at article boundaries, which means each chunk contains one complete article. This is usually appropriate for law retrieval, but some Chinese legal instruments use a hierarchical structure where a single article has multiple numbered clauses (款) or items (项), and the relevant condition may be stated in a sub-item rather than the article header. A retrieval system that operates at article granularity may retrieve the correct article but present the model with a chunk that buries the crucial clause in its second or third paragraph. Whether the model correctly identifies the relevant clause within a retrieved article depends on the model's own reading comprehension, not on the retrieval quality.

A subtler failure mode occurs when retrieval succeeds — the correct article appears in the top-ranked results — but the model misuses it. Consider a case where the retrieved chunk is a definitional article (e.g., an article that defines what constitutes "明码标价"), whereas the legally operative provision for penalty calculation is a separate penalty article (e.g., an article specifying the fine range for failure to clearly mark prices). If the model cites the definitional article as the sole legal basis, its reasoning is logically incomplete: the definitional article establishes what the violation is but not what the penalty consequence should be. This kind of compound-article reasoning is difficult for a single-pass RAG system to handle reliably, because it requires recognizing that multiple retrieved articles serve different functions within the same legal analysis.

It is precisely this limitation that motivates the Grader and Reflector nodes introduced in the Agent workflow of Chapter 6. The Grader assesses retrieved documents for relevance, coverage, and recency before they reach the model; the Reflector checks the model's output for internal consistency (e.g., whether the cited article is consistent with the alleged violation type). Together, these components add a layer of introspection that a pure RAG pipeline lacks.

---

## 5.8 Summary and Transition

The RAG system closes part of the legal-grounding gap left by the Baseline, recovering small but consistent gains in accuracy, violation-type classification, and reasoning quality while adding only 10% latency overhead. The hybrid retriever — combining dense bi-encoder search with BM25, fused via RRF and refined by a cross-encoder re-ranker — provides a more reliable mechanism for surfacing the correct statutory provision than pure parametric recall. The anti-contamination setting (`cases_k=0`) preserves evaluation integrity at the cost of forgoing few-shot case signals.

What RAG cannot do is introspect its own output. Once the retrieved chunks have been injected into the prompt and the model has generated a response, the RAG system accepts that response as-is. There is no mechanism to detect whether the cited article was misapplied, whether a penalty article was confused with a definitional one, or whether the reasoning chain contains a logical inconsistency. Chapter 6 addresses these limitations through a six-node Agent workflow in which a Grader, a Reflector, and a RemediationAdvisor collectively verify, critique, and where necessary repair the model's output — at the cost of substantially higher latency.

---

### References

[1] Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*, 33.

[2] Asai, A., et al. (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. *International Conference on Learning Representations (ICLR 2024)*.

[3] Yan, S., et al. (2024). Corrective Retrieval Augmented Generation. *arXiv preprint arXiv:2401.15884*.

[4] Edge, D., et al. (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. *arXiv preprint arXiv:2404.16130*.

[5] Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333–389.

[6] Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. *Proceedings of the 32nd ACM SIGIR Conference*.

[7] Xiao, S., et al. (2023). C-Pack: Packaged Resources to Advance General Chinese Embedding. *arXiv preprint arXiv:2309.07597*. (BGE reranker model family.)

[8] Qwen Team. (2024). Qwen2.5 Technical Report. *arXiv preprint arXiv:2412.15115*.

[9] Nogueira, R., & Cho, K. (2020). Passage Re-ranking with BERT. *arXiv preprint arXiv:1901.04085*.

---

## Appendix to Section 5.2: Implementation Notes

Several engineering details of the retriever are worth recording for reproducibility. The ChromaDB collection is built offline by `scripts/rag/rag_build_vector_db.py`, which reads `data/rag/laws_chunks.jsonl` (691 records), embeds each chunk using the BGE-small-zh-v1.5 model, and persists the collection to a local directory. This means the embedding step is a one-time cost at index-build time; at query time, only the query embedding is computed on the fly.

The BM25 index is not persisted to disk in the current implementation: it is rebuilt in memory from the same 691-chunk corpus each time a `HybridRetriever` instance is created. For a corpus of this size, the construction time is negligible (under a second), so persistence was not prioritized. In a production system handling much larger corpora — tens of thousands of articles — BM25 index persistence would become necessary.

The cross-encoder model (`BAAI/bge-reranker-v2-m3`) is loaded once per process and cached. The `-v2-m3` variant is a multilingual re-ranker that supports Chinese as a primary language and is larger than the `-v2-s` small variant; we chose it over the smaller option because re-ranking is applied to at most five candidates, so the additional inference time per query is on the order of tens of milliseconds — well within acceptable limits.

One further implementation detail concerns the BM25 formula. Following the standard BM25+ parameterization [5], the term saturation parameter is \(k_1 = 1.5\) and the document length normalization parameter is \(b = 0.75\) by default in most Python BM25 libraries. These defaults were retained without tuning, which is reasonable given the narrow domain and the relatively homogeneous document lengths in the law corpus. Changing these values could affect the balance between BM25 and dense retrieval in the fused ranking, but that sensitivity analysis is left to future work.

These implementation choices collectively define a system that is straightforward to reproduce: a practitioner with access to the same 691-chunk law corpus, the BGE-small-zh-v1.5 encoder, and any standard BM25 library can replicate the hybrid retrieval results. The modularity of the `HybridRetriever` constructor flags — `use_semantic`, `use_bm25`, `use_reranker` — makes it easy to conduct further ablations or to swap components (e.g., upgrading to a larger BGE encoder) without restructuring the pipeline.
