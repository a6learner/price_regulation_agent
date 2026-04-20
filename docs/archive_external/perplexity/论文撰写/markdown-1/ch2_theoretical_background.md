# 2 Theoretical Background

This chapter surveys the technical and regulatory foundations on which the three experimental routes — baseline inference, retrieval-augmented generation, and multi-node agent — are built. The discussion is deliberately selective: each topic is treated at the depth needed to justify design choices made later, rather than as a comprehensive tutorial. Section 2.1 introduces large language models and prompt engineering, with particular attention to the Qwen series that underlies all downstream experiments. Section 2.2 covers retrieval-augmented generation in detail, since the hybrid retrieval pipeline is the most engineering-intensive component of this work. Section 2.3 surveys intelligent agent paradigms — chain-of-thought, ReAct, self-reflection, and multi-node orchestration. Section 2.4 provides the legal background: the body of Chinese price-regulation statutes whose articles the system must cite and apply.

---

## 2.1 Large Language Models and Prompt Engineering

### 2.1.1 Transformer Architecture and the Decoder-Only Variant

The modern large language model traces its lineage to the Transformer proposed by Vaswani et al. [1], which replaced recurrent sequence processing with a fully attention-based architecture. The critical insight was that a scaled dot-product attention mechanism — computing weighted sums over all token positions simultaneously — could capture long-range dependencies without the vanishing-gradient problems associated with RNNs.

For generation tasks, the decoder-only variant has proved dominant. Unlike the full encoder-decoder arrangement used in machine translation, a decoder-only model reads the entire context (prompt plus any previously generated tokens) through a single stack of causal self-attention layers, predicting the next token at each step. Causal masking ensures that position *t* can attend only to positions ≤ *t*, preserving the left-to-right generation order. GPT-style models, PaLM, and the Llama/Qwen families all follow this design. The practical upside is architectural simplicity and efficient batching at inference time; the downside, relevant to this project, is that the model has no explicit "read-write memory" beyond its context window — a limitation that motivates retrieval augmentation.

### 2.1.2 Pretraining and Instruction Tuning

A decoder-only model is first trained on a massive text corpus via next-token prediction. At this stage the model learns factual associations, syntactic structure, and — crucially for compliance work — the surface patterns of legal language. Pretraining alone, however, does not yield a model that follows user instructions reliably; it tends to continue text rather than answer questions.

Instruction tuning addresses this by fine-tuning the pretrained model on curated (instruction, response) pairs, often with reinforcement learning from human feedback (RLHF) or the cheaper direct preference optimization (DPO) variant. After instruction tuning the model becomes a "chat" or "instruct" model: it answers questions, adopts specified roles, and — with sufficient training signal — respects output format constraints such as JSON schemas. This capability is central to the baseline route in this thesis, where the model must produce a structured JSON verdict from a plain-text prompt.

### 2.1.3 The Qwen Series and the Choice of Qwen-8B

The Qwen series, developed by Alibaba's DAMO Academy and released by the Qwen team [2], is a family of decoder-only language models with variants ranging from 0.5 B to 72 B parameters. Qwen2.5 — the generation used in this work — was pretrained on roughly 18 trillion tokens and subsequently instruction-tuned with a particular emphasis on Chinese-language text, structured outputs, and long-context reasoning. These properties matter for price-compliance supervision because penalty documents, statutory articles, and administrative precedents are predominantly in Chinese, and the model's output must conform to a fixed JSON schema containing fields such as `violation_type`, `legal_basis`, and `remediation_advice`.

In the pilot comparison conducted prior to the main experiments, three candidate models were evaluated: the commercial MiniMax API, the full Qwen (72 B, accessed via API), and Qwen-8B (self-hosted). Qwen-8B achieved classification accuracy within one percentage point of the 72 B variant on a 99-sample pilot set while running entirely on local hardware, eliminating the per-token cost and latency variability of external API calls. MiniMax showed notably lower recall on compliance cases. For these reasons Qwen-8B was adopted as the base model for all downstream RAG and Agent experiments. It is worth acknowledging that a locally hosted 8 B model is not the ceiling of achievable performance; a larger or domain-fine-tuned model might narrow the remaining error gap on difficult cases.

### 2.1.4 Zero-Shot and Few-Shot Prompting; Structured Output Constraints

Prompting is the practice of steering a frozen (or parameter-fixed) language model's behavior through the text placed in its context. Zero-shot prompting provides only a task description and expects the model to generalize from pretraining knowledge alone. Few-shot prompting prepends a small number of worked examples — typically two to eight — before the actual query, demonstrating the expected reasoning pattern or output format [3]. In practice, carefully crafted few-shot examples can substantially reduce format errors in structured outputs, since the model can imitate the demonstrated schema directly.

This project primarily uses zero-shot prompting for the baseline route: the system prompt specifies the task, the output schema, and a brief description of each violation category, but no worked examples are provided. The rationale is partly principled — we want to measure how much of the model's capability is intrinsic before adding retrieval — and partly practical: the 780-sample evaluation set is drawn from the same administrative-penalty corpus, and few-shot examples sourced from the same pool would conflate retrieval-style memorization with genuine generalization.

Structured output constraints refer to the practice of restricting the model's generation space to a valid JSON object matching a declared schema. Modern inference frameworks (vLLM, Ollama, OpenAI's response format API) support this through guided decoding, which at each decoding step masks logits for tokens that would produce an invalid prefix. The result is a virtually parse-error-free output stream, at the cost of a small increase in token entropy that can occasionally suppress nuanced phrasing.

---

## 2.2 Retrieval-Augmented Generation

Retrieval-augmented generation (RAG), as formalized by Lewis et al. [4], combines a parametric generator — the language model whose knowledge is "frozen" in its weights — with a non-parametric retrieval component that fetches relevant passages from an external corpus at inference time. The retrieved passages are appended to the prompt, giving the model grounded evidence it can cite and reason over. For legal-compliance tasks the benefit is direct: statutes are updated periodically, penalty precedents accumulate continuously, and no fixed-weight model can be expected to recall the precise wording of a 2022 regulatory amendment without external grounding.

The RAG pipeline used in this work has five distinct stages — dense retrieval, sparse retrieval, fusion, re-ranking, and dynamic filtering — each of which is described below.

### 2.2.1 Dense Vector Retrieval

Dense retrieval represents both queries and documents as continuous vectors in a shared embedding space, then measures relevance by the cosine similarity or inner product between the query vector and each document vector. The embedding model — a bi-encoder, typically a BERT-style encoder fine-tuned on retrieval pairs — projects arbitrary-length text to a fixed-dimensional space (commonly 768 or 1024 dimensions) in a single forward pass. At indexing time, every chunk in the knowledge base is encoded and stored; at query time, only the query is encoded, and approximate nearest-neighbor search (ANN) identifies the top-*k* candidates in sub-linear time.

Vector databases such as Chroma and Milvus manage this process. Chroma is a lightweight, in-process solution suitable for prototyping and moderate-scale corpora; Milvus is a distributed, production-grade system designed for billion-scale indexes with hardware-accelerated ANN (IVF, HNSW). This project uses Chroma because the law knowledge base (691 articles) and case base (133 documents) are small enough that exhaustive cosine search over all stored vectors is fast without approximation.

Dense retrieval excels at semantic matching: a query phrased as "operator did not display the price of goods on the shelf" will correctly retrieve an article about "clearly marked prices" even if no word overlaps between the two. The weakness is that it can miss highly specific token sequences — model numbers, article identifiers like "第十三条第一款", or monetary thresholds — because embedding models compress text into a dense vector that may wash out rare, high-information tokens.

### 2.2.2 Sparse Lexical Retrieval — BM25

BM25 (Best Match 25) is a bag-of-words ranking function that scores each document by the weighted overlap between query terms and document terms [5]. Its core formula is

\[
\text{score}(d, q) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, d) \cdot (k_1 + 1)}{f(t, d) + k_1 \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}
\]

where \(f(t, d)\) is the term frequency of query term *t* in document *d*, \(|d|\) is the document length, avgdl is the average document length across the corpus, and \(k_1\), *b* are free parameters (typically \(k_1 = 1.5\), \(b = 0.75\)). The inverse document frequency \(\text{IDF}(t) = \log\frac{N - n(t) + 0.5}{n(t) + 0.5}\) down-weights terms appearing in many documents and up-weights rare terms.

For price-compliance work, BM25 fills a gap that dense retrieval struggles with. Penalty documents frequently mention specific article numbers ("价格法第十四条"), monetary amounts ("罚款五万元"), and product category names that are not paraphrased across documents. BM25 rewards exact token overlap, so such hard tokens receive high IDF weight and surface the correct document reliably — provided the query includes the same tokens, which is reasonable when the input is an excerpt from an administrative penalty notice containing those very strings.

### 2.2.3 Retrieval Fusion — Reciprocal Rank Fusion

Dense and sparse retrieval produce separate ranked lists that may partially overlap. A straightforward approach is to normalize each list's scores and take a weighted linear combination, but this requires calibrating scores across retrieval systems with different numeric scales. Reciprocal Rank Fusion (RRF) [6] sidesteps score calibration by using only the rank positions:

\[
\text{RRF}(d) = \sum_{r \in R} \frac{1}{k + \text{rank}_r(d)}
\]

where *R* is the set of ranked lists (here, dense and sparse), \(\text{rank}_r(d)\) is document *d*'s position in list *r* (1-indexed), and *k* is a smoothing constant (conventionally 60). Documents near the top of any list receive a high contribution to their RRF score; documents absent from a list contribute zero. The combined list is then re-sorted by descending RRF score.

The appeal of RRF is its robustness: it consistently outperforms individual retrievers and most score-based fusion strategies across diverse benchmarks, with no hyperparameter to tune beyond *k*. In practice, a document that ranks 1st on the BM25 list and 5th on the dense list will outrank a document that ranks 2nd on the dense list but is absent from BM25 — which is often the desired behavior for compliance queries where exact statutory wording is decisive.

### 2.2.4 Re-ranking — Cross-Encoder vs. Bi-Encoder Trade-offs

After fusion, the merged candidate list is passed to a re-ranker. The fundamental distinction in re-ranking is between bi-encoders and cross-encoders. A bi-encoder encodes query and document independently and computes their similarity in the vector space — the same mechanism used in dense retrieval. A cross-encoder, by contrast, concatenates the query and document into a single input and runs a joint attention across both, producing a single relevance score. Because every query-document pair shares attention, the cross-encoder can model fine-grained token-level interactions that bi-encoder similarity misses; the cost is that it cannot be pre-indexed and must run inference for each (query, document) pair at query time.

This project uses a cross-encoder re-ranker applied to the top candidates from RRF fusion. For a law knowledge base of 691 articles, the cross-encoder adds acceptable latency — measured at roughly 0.15 seconds per query on the evaluation hardware — while meaningfully improving ranking quality on ambiguous queries where two articles differ in subtle wording. The limitation, acknowledged plainly, is that cross-encoder scores reflect a general notion of semantic relevance and are not equivalent to legal-fact matching: an article may rank highly because it shares vocabulary with the query while actually applying to a different fact pattern.

### 2.2.5 Filtering Strategies — Distance Thresholds and Dynamic Top-K

Retrieval pipelines routinely return the top-*k* candidates without asking whether any of them are actually relevant. In a compliance setting this matters: an irrelevant article inserted into the prompt can mislead the generator into citing law that does not apply to the case at hand.

Three complementary filtering mechanisms are used in this work. A distance threshold discards any candidate whose vector cosine distance exceeds a configured ceiling, ensuring that only documents within a minimum semantic proximity enter the prompt. A minimum-*k* floor prevents the prompt from being empty on rare queries where all candidates fall below the threshold. A dynamic top-*k* mechanism observes the distribution of re-ranker scores in the candidate list: if there is a large score gap between position *j* and position *j+1*, candidates beyond position *j* are dropped, on the hypothesis that they represent a qualitatively different relevance tier. Together these three mechanisms reduce "retrieval noise" — a proxy for the proportion of returned articles not actually relevant to the queried case — though measuring this directly requires human annotation and is left to future work.

---

## 2.3 Intelligent Agent Paradigms

The term "agent" in the NLP literature is used loosely to mean a language model that does more than produce a single response — it takes actions, observes results, and revises its behavior accordingly. Four paradigms are particularly relevant to the architecture of this project.

### 2.3.1 Chain-of-Thought Prompting

Chain-of-thought (CoT) prompting, introduced by Wei et al. [7], encourages the model to externalize intermediate reasoning steps before arriving at a final answer. Rather than mapping directly from input to output, the model produces a natural-language scratchpad: "the seller listed a promotional price without noting an expiry date; under Article 14(4) of the Price Law this constitutes misleading price display; therefore the verdict is violation." Empirically, CoT substantially improves accuracy on multi-step tasks — mathematical reasoning, commonsense inference, and, as we find, legal case classification — compared to generating only the final answer.

The mechanism behind CoT's effectiveness remains partially contested in the research literature. One explanation is that generating intermediate tokens shifts the model's computation toward a more deliberate regime, effectively increasing effective "reasoning depth" without increasing model size. Another is that the scratchpad tokens condition subsequent generation, making certain error patterns less likely. Regardless of explanation, the practical result is consistent enough that CoT or its variants are standard practice in any pipeline where the model must apply rules to facts.

In this project, the ReasoningEngine node of the Agent route employs a structured, five-step CoT: (1) fact extraction from the penalty document, (2) data verification, (3) law matching, (4) case reference lookup, and (5) conclusion. The structured framing — rather than open-ended "let's think step by step" — is intended to reduce variance in reasoning paths and produce outputs whose intermediate steps can be evaluated independently.

### 2.3.2 ReAct and Tool Use

ReAct (Reasoning + Acting), proposed by Yao et al. [8], interleaves language model reasoning with discrete actions, typically API calls or database queries. The model alternates between producing a "Thought" (a natural-language rationale), taking an "Action" (invoking a tool with specified arguments), and receiving an "Observation" (the tool's return value). This loop continues until the model decides it has enough information to produce a final answer.

ReAct is the conceptual ancestor of the Agent node structure used here: the IntentAnalyzer identifies what information is needed, the AdaptiveRetriever acts as the tool that fetches it, and the subsequent nodes process the observation. One practical divergence from the original ReAct formulation is that this project uses a linear, predetermined node sequence rather than a fully dynamic loop. The reason is partly the compliance domain's predictability — every query has the same high-level subtask structure (retrieve law, grade relevance, reason, reflect, advise) — and partly the need for bounded latency: an unconstrained ReAct loop could in principle run many iterations, whereas the six-node pipeline guarantees at most one retry by the Reflector.

Tool use more broadly — the ability to call external functions and incorporate their results — is what distinguishes agent systems from "standalone" language models. In this context the primary tool is the HybridRetriever, but the RemediationAdvisor node also implicitly "uses" the output of upstream nodes as structured data rather than raw text.

### 2.3.3 Self-Reflection and the Reflexion Framework

Reflexion, proposed by Shinn et al. [9], adds a self-evaluation layer to the ReAct loop: after the model produces a response (or fails a task), a "reflection" step generates verbal feedback about what went wrong, which is stored in a short-term memory buffer and used to condition the next attempt. This differs from simple chain-of-thought in that the model explicitly evaluates its own prior output rather than just producing reasoning before an answer.

Self-RAG [10] applies a related idea to retrieval: the model generates special tokens indicating whether retrieval is needed, whether the retrieved documents are relevant, and whether the final output is supported by the retrieved evidence. These "reflection tokens" allow the model to selectively engage retrieval and to self-rate citation quality — a useful property for compliance work where not every query requires statutory lookup.

The Reflector node in this project draws from both paradigms. After the ReasoningEngine produces a structured JSON verdict, the Reflector applies a zero-cost heuristic validation: it checks for logical consistency (e.g., does the cited article number match the stated violation type?), field completeness, and score thresholds on the Grader's output. If validation fails, the Reflector triggers a single re-reasoning call with an augmented prompt that includes the detected inconsistencies. The one-retry ceiling is a deliberate engineering constraint: at most one additional LLM call per query keeps the expected per-case latency bounded, and empirically one retry suffices for the majority of cases that fail initial validation.

### 2.3.4 Multi-Node Orchestration — Planner-Executor-Critic

As agent tasks grow more complex, a single monolithic prompt becomes unwieldy. Multi-node (or multi-agent) orchestration decomposes the task into roles: a planner determines the sequence of subtasks, executors carry out individual steps, and a critic evaluates intermediate results before passing them downstream. This planner-executor-critic pattern is common in recent agentic frameworks and has been shown to reduce error propagation compared to end-to-end single-step approaches.

The six-node pipeline in this project is a simplified instantiation of this pattern. The IntentAnalyzer (rule-based, no LLM call) acts as a planner in the narrow sense of parsing the input and setting top-K parameters for the downstream retriever. The AdaptiveRetriever, Grader, and ReasoningEngine are executors operating in sequence. The Reflector is a critic. The RemediationAdvisor is a post-critic executor whose output is conditioned on the critic's approval. By keeping the IntentAnalyzer rule-based, we avoid the overhead of an LLM call for a task that is fully deterministic given the input structure — a design choice that contributes to the pipeline's average response time of 37.62 seconds being dominated by the ReasoningEngine and Reflector rather than by orchestration overhead.

---

## 2.4 Chinese Price Regulation Legal Framework

The compliance domain of this project is Chinese price regulation as administered by the State Administration for Market Regulation (SAMR) and its provincial counterparts. The relevant statutory instruments form a layered hierarchy: national laws enacted by the National People's Congress, administrative regulations issued by the State Council, and departmental rules promulgated by SAMR. This section describes the statutes most frequently invoked in the penalty documents from which the evaluation dataset was derived.

**Price Law of the People's Republic of China (价格法, 1997).** The foundational legislation, enacted in 1997 and still in force with amendments. Chapter 3 (Articles 11–17) defines unlawful pricing conducts by operators. Article 13 mandates clearly marked prices for all goods and services offered to consumers. Article 14 enumerates eight categories of prohibited practices, including collusion to fix prices, predatory pricing below cost, and misleading price displays. Article 14(4) — which prohibits "using false or misleading price means to induce consumers to trade" — is among the most frequently cited articles in the penalty documents examined in this work. Violations of Chapter 3 can attract administrative fines under Chapter 6, and the same chapter empowers pricing authorities to order corrective measures.

**Anti-Unfair Competition Law (反不正当竞争法, 1993, revised 2017 and 2019).** This statute addresses a broader range of market-distorting behaviors, including false advertising and misleading commercial promotions. Article 8 prohibits operators from using false or misleading commercial promotional statements about goods. In price-compliance contexts, the Anti-Unfair Competition Law tends to be cited alongside the Price Law when a penalty document characterizes a fictitious original price or a fabricated comparison as both a price fraud and a deceptive trade practice.

**E-Commerce Law (电子商务法, 2018).** Enacted in 2018, this statute applies specifically to e-commerce platform operators and merchants operating on those platforms. Article 17 requires e-commerce operators to ensure that promotional information is truthful and transparent, explicitly prohibiting fictitious transactions or fabricated reviews used to create false price impressions. Article 72 addresses data security and consumer information obligations. Because the evaluation dataset is derived from administrative penalties in the e-commerce sector, the E-Commerce Law appears in a non-trivial share of case documents, often cited alongside the Price Law to establish jurisdiction over platform-based sellers.

**Provisions on Clearly Marked Prices and Prohibition of Price Fraud (明码标价和禁止价格欺诈规定, SAMR Order No. 56, 2022).** This SAMR departmental rule, effective May 2022, is the most operationally detailed instrument in the corpus. It consolidates and supersedes earlier guidance on price marking and fraud prohibition, providing precise definitions for each violation type. For this project, Article 5 (clearly marked price obligations) and Articles 19–21 (enumerated forms of price fraud) are of central importance. The rule also explicitly defines what constitutes a "reference price" for comparison purposes, addressing the common practice of listing inflated "original prices" against which a "sale price" is displayed.

The penalty documents in the evaluation dataset exhibit seven recurring violation types, whose mapping to the statutory framework is as follows:

*Unpriced display (不明码标价)* covers situations where a seller fails to display any price at all for an offered good or service — a violation of Price Law Article 13 and SAMR Provisions Article 5. This is the most common violation type in the dataset (221 of 489 violation samples), likely reflecting the ease of detection during routine inspections.

*Government-priced violation (政府定价违规)* refers to charging prices above or below government-mandated price ceilings or floors. Certain public utilities, pharmaceuticals, and agricultural products remain subject to government pricing; exceeding the permitted price is a violation of Price Law Article 12. This category comprises 117 samples in the dataset.

*Surcharge above marked price (标价外加价)* describes the practice of charging fees beyond what is displayed — a "hidden surcharge" pattern. The SAMR Provisions and Price Law Article 14(1) explicitly prohibit this. 73 samples fall into this category.

*Misleading price display (误导性价格标示)* encompasses cases where prices are displayed in a technically compliant format but in a manner designed to mislead the consumer — for example, prominently showing a per-unit price while burying a mandatory bundled quantity in small print. Price Law Article 14(4) and SAMR Provisions Article 19 are the primary bases. With 49 samples, this is a smaller but analytically interesting category because the violation requires inference about intent, making it harder to classify automatically.

*Variant price hikes (变相涨价)* capture practices that effectively raise the price without an explicit price change, such as reducing product weight while keeping the listed unit price constant. These are addressed under Price Law Article 14(3). The dataset contains 15 such cases — few enough that model performance on this category should be interpreted with caution.

*Fake price comparisons (虚假价格比较)* involve fabricating a reference price (often labeled "original price" or "market price") against which a lower "sale price" is compared, creating a false impression of a discount. The SAMR Provisions Articles 20–21 provide detailed criteria for what constitutes a valid reference price. This category is subsumed in the "misleading price display" count in some tabulations.

*Fake discounts (虚假打折)* cover claims of a percentage discount from a price that was never actually charged at the stated original amount. Like fake price comparisons, these are addressed under the SAMR Provisions and are treated as a form of price fraud under Price Law Article 14(4).

Understanding this statutory framework is necessary not only for interpreting model outputs but also for designing the law knowledge base and the violation-type taxonomy used in the evaluation metric system. The 691 articles in the knowledge base span the four instruments above plus related provincial implementing rules, and the cross-article citation patterns seen in real penalty documents informed the decision to use hybrid retrieval rather than relying on semantic similarity alone — a point developed further in Chapter 5.

---

## Bridging to Chapter 3

The theories reviewed in this chapter collectively motivate the architecture choices made throughout the experimental work. Dense and sparse retrieval address complementary weaknesses; RRF fusion and cross-encoder re-ranking correct systematic biases in either modality; structured CoT and self-reflection improve not just accuracy but the auditability of reasoning outputs; and the multi-node planner-executor-critic pattern provides a principled way to decompose a legally complex classification task into manageable, evaluable subtasks. Before any of these techniques can be applied, however, a suitable evaluation dataset must exist. Chapter 3 describes how the 780-sample dataset was constructed from publicly available SAMR administrative penalty documents, including the annotation schema, quality-control steps, and the deliberate exclusion of the 133 historical cases from the formal evaluation to avoid same-source contamination.

---

## References

[1] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin, "Attention is all you need," in *Advances in Neural Information Processing Systems*, vol. 30, 2017.

[2] Qwen Team, "Qwen2.5 technical report," Alibaba Group, 2024.

[3] T. Brown, B. Mann, N. Ryder et al., "Language models are few-shot learners," in *Advances in Neural Information Processing Systems*, vol. 33, pp. 1877–1901, 2020.

[4] P. Lewis, E. Perez, A. Piktus et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems*, vol. 33, pp. 9459–9474, 2020.

[5] S. Robertson and H. Zaragoza, "The probabilistic relevance framework: BM25 and beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–389, 2009.

[6] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal rank fusion outperforms Condorcet and individual rank learning methods," in *Proc. 32nd ACM SIGIR*, pp. 758–759, 2009.

[7] J. Wei, X. Wang, D. Schuurmans et al., "Chain-of-thought prompting elicits reasoning in large language models," in *Advances in Neural Information Processing Systems*, vol. 35, 2022.

[8] S. Yao, J. Zhao, D. Yu et al., "ReAct: Synergizing reasoning and acting in language models," in *Proc. ICLR*, 2023.

[9] N. Shinn, F. Cassano, E. Berman, A. Gopalan, K. Narasimhan, and S. Yao, "Reflexion: Language agents with verbal reinforcement learning," in *Advances in Neural Information Processing Systems*, vol. 36, 2023.

[10] A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, "Self-RAG: Learning to retrieve, generate, and critique through self-reflection," in *Proc. ICLR*, 2024.

[11] J. Cui, Z. Li, Y. Yan, B. Chen, and Y. Liu, "ChatLaw: Open-source legal large language model with integrated external knowledge bases," arXiv:2306.16092, 2024.
