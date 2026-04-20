# 6 Agent Route with Multi-Node Reflection

## 6.1 Motivation

Chapter 5 demonstrated that grounding Qwen3-8B with retrieved law articles produces measurable improvements in classification accuracy and reasoning quality. RAG is fast, modular, and easy to audit at the retrieval level. For bulk classification tasks — deciding whether 780 penalty records constitute violations and labeling their types — it is a sensible default.

There are nonetheless scenarios where RAG's single-shot architecture falls short. A regulator preparing an enforcement memorandum needs not just a verdict but a traceable chain of legal reasoning: which provision was triggered, why the defendant's conduct meets each element of that provision, and what follow-up steps are required. A merchant conducting a self-audit needs actionable remediation guidance, not merely a binary label. In both cases, the quality of the *explanation* matters as much as the accuracy of the *classification*, and a system that generates its conclusion in a single forward pass through the model has no opportunity to catch its own logical errors before committing to an output^[15]^^[18]^.

The agent paradigm addresses this by decomposing the decision process into a sequence of specialized sub-tasks, each with its own data structures, prompts, and validation criteria^[19]^^[16]^. Rather than asking the model to classify, cite, reason, and recommend simultaneously, the agent assigns each concern to a dedicated node. An intent analysis step focuses the retrieval query. A grader filters retrieved evidence for relevance. A structured reasoning step forces the model into an explicit multi-step chain of thought^[14]^. A reflection step checks the output for internal contradictions before it leaves the pipeline. A remediation advisor converts the verdict into forward-looking compliance recommendations.

This decomposition does not come free: the agent route averages 37.62 seconds per sample on the 780-sample set, compared to 7.77 seconds for RAG. Whether that cost is worth paying depends on the use case, a point we return to in Section 6.8. The goal of this chapter is to describe the architecture in enough detail that both the design decisions and their performance consequences can be understood and reproduced.

It is also worth noting that accuracy and quality are not the only evaluation dimensions that matter in this domain. Legal AI systems deployed in regulatory contexts face scrutiny on explainability grounds: regulators, courts, and supervised parties may all demand to know *why* a system reached a particular verdict. A system that achieves 89% accuracy through a black-box generation step is harder to defend than one that achieves 87% accuracy with a step-by-step reasoning trail that a lawyer can check. The agent architecture is therefore designed with auditability as a first-class constraint, not as an afterthought.

The agent builds on several theoretical foundations: the ReAct framework for interleaving reasoning and action^[15]^, the Reflexion approach for verbal self-correction^[16]^, and the Self-Refine idea of iterative output improvement via feedback^[17]^. The concept of multi-agent simulation and behavior decomposition also informs the node separation philosophy, particularly in how specialized sub-agents are given narrow mandates with clearly defined inputs and outputs^[20]^. Neither LangChain^[22]^ nor LlamaIndex^[23]^ is used as an orchestration framework here; the six-node graph is implemented directly in `src/agents/` to keep the state representation and control flow fully transparent and auditable.

---

## 6.2 System Architecture

The agent operates as a **linear six-node graph** in which state is passed from node to node as a shared dictionary. The nodes execute in the following order:

```
IntentAnalyzer → AdaptiveRetriever → Grader → ReasoningEngine → Reflector → RemediationAdvisor
```

There is one conditional loop: if the Reflector detects a critical inconsistency in the ReasoningEngine's output and the maximum reflection count has not been reached, control returns to the ReasoningEngine for a single re-reasoning attempt. In all other cases the graph is strictly forward.

Each node reads from and writes to a shared `AgentState` dictionary. Fields populated by earlier nodes are available to all subsequent nodes, so the Reflector can inspect the raw reasoning chain, the retrieved articles, and the intent metadata simultaneously. This shared-state design mirrors the "blackboard" architecture common in classical expert systems and avoids the need for explicit inter-node message passing.

![Figure 6-1: Agent state graph — six-node linear flow with Reflector feedback loop](figures/ch6_agent_state_graph.png)

Figure 6-1 Agent state graph. Solid arrows show the primary linear execution path. The dashed arrow from Reflector back to ReasoningEngine is triggered only when a critical heuristic is violated and `reflection_count < max_reflection`.

---

## 6.3 Node Design

### 6.3.1 IntentAnalyzer

The IntentAnalyzer is a **pure rule-based module** — it makes no LLM call and adds negligible latency (average 0.11 ms per sample). Its role is to pre-process the case description and populate an intent record that guides the downstream nodes, particularly the retrieval configuration.

The output fields are:

- **`violation_type_hints`** (up to 3 strings): suspected violation categories detected by keyword triggers.
- **`key_entities`** (list): extracted references to platforms, monetary amounts, and price-related terminology.
- **`complexity`** (`simple` / `medium` / `complex`): determines the RemediationAdvisor operating mode.
- **`suggested_laws_k`** (3, 4, or 5): the number of law articles to retrieve, calibrated to complexity.
- **`suggested_cases_k`** (always 0): the number of similar historical cases to retrieve; hard-coded to zero for the reasons discussed in Section 6.4.
- **`reasoning_hints`** (list): brief guidance strings forwarded to the ReasoningEngine prompt.

Violation type detection is performed by `_detect_violation_types`, which iterates over a set of trigger-keyword lists. The logic for each category is:

- **不明码标价 (Unpriced display)**: strong triggers include "未标价", "未明码标价", "没有标价"; weak triggers such as "价格不清晰" or "标价不规范" must co-occur with at least one strong feature before the hint is emitted.

- **政府定价违规 (Government-priced violation)**: triggered by keywords like "政府定价", "政府指导价", "超出定价范围". Cases involving utilities, medical services, or public transportation are flagged as medium or complex complexity.

- **标价外加价 (Surcharge above marked price)**: triggers include "加收", "额外收费", "超出标价收取", "收取标价外费用".

- **误导性价格标示 (Misleading price display)**: this category uses a two-tier feature system. Strong features are phrases such as "虚假原价", "虚标原价", "不实折扣". Weak features include "原价", "划线价", "参考价". A hint is emitted if at least one strong feature is present, or if two or more weak features co-occur with a general price-comparison term.

- **变相提高价格 (Disguised price hike)**: triggers include "缩减数量", "降低质量", "搭售", "强制附加" combined with evidence of price change or additional charges.

- **哄抬价格 (Price gouging)**: triggered by "哄抬", "囤积居奇", "散布涨价信息", or the co-occurrence of commodity shortage terms with significant price increase evidence.

When no specific type is identified, the analyzer emits an empty hint list and defaults to `complexity=simple`, `suggested_laws_k=3`.

### 6.3.2 AdaptiveRetriever

The AdaptiveRetriever wraps the same `HybridRetriever` used in the RAG route (Chapter 5) but parameterizes it dynamically based on the IntentAnalyzer's output. Specifically:

- `laws_k` is set to the `suggested_laws_k` value from the intent record (3, 4, or 5).
- `cases_k` is set to the `suggested_cases_k` value, which is always 0.
- `distance_threshold` and `min_k` are fixed at 0.15 and 2 respectively, matching the RAG evaluation configuration.

The dynamic `laws_k` means that complex cases with multiple suspected violation types receive a broader retrieval scope (up to 5 articles), while simple single-violation cases are served by a focused 3-article set. This reduces the risk of prompt pollution from tangentially related statutes, which is more important in the agent setting because the retrieved articles propagate through the Grader and directly influence the ReasoningEngine's chain-of-thought prompt.

### 6.3.3 Grader

After retrieval, the Grader scores each candidate article and filters out those that are unlikely to be genuinely relevant to the current case. The goal is to prevent the ReasoningEngine from reasoning over low-quality evidence.

Each article receives a weighted composite score:

$$\text{final\_score} = 0.6 \times \text{relevance} + 0.3 \times \text{coverage} + 0.1 \times \text{freshness}$$

The three components are computed as follows:

**Relevance.** If a CrossEncoder re-rank score is attached to the article (which it will be when `use_reranker=True`), that score is used directly. Otherwise, relevance falls back to `max(0, 1 − distance)`, converting cosine distance into a similarity value on [0, 1].

**Coverage.** The proportion of the IntentAnalyzer's `key_entities` tokens that appear as substrings in the article's `content` field. If the intent analysis produced no key entities, coverage defaults to 0.5 — a neutral value that neither rewards nor penalizes the article.

**Freshness.** A step function on the article's publication year: 1.0 for year ≥ 2024 (reflecting recent regulatory updates), 0.8 for year ≥ 2020, and 0.6 for older material. When no year metadata is available, the system defaults to 2020 and applies the 0.8 weight. This heuristic acknowledges that China's price regulation framework has been updated more actively in recent years and that the most recent provisions should be preferred when evidence scores are otherwise close.

Articles with `final_score < min_score` (default 0.5) are filtered out. A fallback `min_keep=2` ensures that at least two articles are passed to the ReasoningEngine even if all candidates score below the threshold — in that case, the top-2 by score are retained regardless of the cutoff. The Grader runs in under 0.1 ms on average (0.08 ms measured), because it involves only arithmetic operations on a small candidate list.

### 6.3.4 ReasoningEngine

The ReasoningEngine is the only node in the agent (other than RemediationAdvisor in detailed mode) that makes an LLM call. It invokes Qwen3-8B via the same MaaS client used in the Baseline and RAG routes.

Because `cases_k = 0` throughout evaluation, the engine uses the **4-step chain-of-thought (CoT)** branch of its prompt^[14]^:

1. **Fact extraction.** Identify the specific conduct alleged in the case description — what the operator did, at what price, on which platform, and to whom.
2. **Legal element matching.** For each retrieved and graded law article, determine whether the elements of that provision are satisfied by the extracted facts.
3. **Violation determination.** Based on the element-matching analysis, reach a binary verdict (`is_violation`) and, if positive, identify the specific violation type.
4. **Reasoning synthesis.** Produce a narrative explanation connecting the factual findings to the legal conclusions, in language suitable for an enforcement record.

When `cases_k > 0` (a configuration available but not used in the formal evaluation), the prompt adds a fifth step that compares the current case against retrieved historical cases and adjusts confidence accordingly. For the purposes of this thesis, that branch is disabled.

The output JSON schema mirrors the Baseline and RAG outputs: `is_violation`, `violation_type`, `legal_basis`, `reasoning`, and `cited_articles`. The explicit CoT structure tends to produce longer and more logically organized reasoning fields, which is reflected in the reasoning quality score discussed in Section 6.5. Chain-of-thought prompting was originally proposed for arithmetic and commonsense reasoning benchmarks^[14]^, but its benefits transfer well to structured legal analysis, where each inferential step must establish a clear connection between a factual premise and a legal conclusion before the next step can proceed.

### 6.3.5 Reflector

The Reflector applies a set of **heuristic validation rules** to the ReasoningEngine's output without making an additional LLM call. Its purpose is to catch the most common categories of logical error before the result is finalized. The `max_reflection` parameter is set to **1**, meaning that at most one re-reasoning attempt is permitted per case.

Critical triggers — any of which will initiate a re-reasoning cycle — include:

- `is_violation == True` but `violation_type` is "无违规" or a similar null-type string.
- `is_violation == False` but `violation_type` is a named violation category (a contradiction in the opposite direction).
- The reasoning chain **completely lacks** fact keywords that are expected for the detected violation type. For example, a case flagged as 不明码标价 should contain some reference to pricing display; if the reasoning chain mentions only monetary penalties with no discussion of price labeling, the Reflector flags this as a missing-element gap.
- The case description contains **non-price-domain keywords** (e.g., references to food safety, product quality standards, or environmental violations) with no corresponding price-related evidence — suggesting the model may have over-generalized.

Warning-level triggers (logged but not causing re-reasoning) include absent legal-basis text, cited articles that do not match the declared violation type, and unusually short reasoning fields.

When a critical trigger fires and `reflection_count < max_reflection`, the Reflector composes a structured feedback message describing the detected problem and passes it back to the ReasoningEngine along with the original case context and retrieved articles. The ReasoningEngine then re-generates its output, ideally correcting the flagged inconsistency. If the revised output still triggers the same critical rule, the system accepts the revised output anyway (since a second reflection round is not allowed) and logs the failure for post-hoc analysis.^[16]^^[17]^

The one-reflection limit is a practical engineering choice. Empirically, most CoT errors fall into one of the contradiction categories caught by the heuristics, and a single re-reasoning pass corrects these in the majority of triggered cases. Allowing more reflection rounds would not eliminate the deeper classes of error (e.g., wrong legal domain or missing statutory element) and would add meaningful latency for each triggered case. The Reflector's 453.58 ms average already reflects some amortized cost from triggered reflections; a `max_reflection=2` setting would push this higher with diminishing returns.

The average Reflector latency is 453.58 ms per sample. This is much larger than the Grader (0.08 ms) but much smaller than the retrieval or reasoning steps, and it includes both the heuristic evaluation and, in cases where reflection is triggered, the overhead of assembling the feedback message.

### 6.3.6 RemediationAdvisor

The final node in the pipeline translates the compliance verdict into actionable guidance. Its behavior is gated on the `complexity` field from the IntentAnalyzer:

- **Fast mode** (`complexity == simple`): a pre-defined template from `REMEDIATION_TEMPLATES` is selected based on the detected violation type. The template provides a boilerplate list of corrective actions (e.g., "display prices on all listed items within 5 business days") without an additional LLM call.

- **Detailed mode** (`complexity == medium` or `complex`): the advisor makes an LLM call with a structured prompt requesting a JSON response containing two fields: `remediation_steps` (a numbered list of specific corrective actions tailored to the case facts) and `compliance_checklist` (a set of ongoing compliance checkpoints the operator should maintain).

Detailed mode accounts for most of the advisor's average latency of 5,342.60 ms. For simple cases, the fast-mode template returns in sub-millisecond time. In the 780-sample evaluation, the distribution of complexity labels (determined by the IntentAnalyzer) determines the overall share of detailed-mode calls. The RemediationAdvisor is the only node whose output is not directly compared against the evaluation set's ground-truth labels; its quality is therefore harder to quantify automatically. In the web prototype (Chapter 8), this output is the primary content surfaced to merchant users, making it the most user-visible component of the entire pipeline.

---

## 6.4 Data Leakage Control

Any system evaluated against a benchmark must be checked for inadvertent exposure of test data to the model during inference. In RAG and agent systems, this risk is qualitatively different from the training-set contamination studied in the LLM pre-training literature: the concern is not that the model memorized specific case outcomes during training, but that the retrieval system might surface the ground-truth answer as a retrieved document at inference time.

The case base contains 133 historical enforcement decisions collected alongside the evaluation dataset. An analysis of `source_pdf` identifiers — each of which corresponds to a distinct administrative penalty document — identified **8 cases** where the same underlying enforcement document appears in both the case base and the evaluation set. Admitting these cases as retrieved context during evaluation would mean that the model is shown the answer to some of its test questions, invalidating those samples' results.

To avoid this, `suggested_cases_k` in the IntentAnalyzer is **hard-coded to 0**, and the AdaptiveRetriever's `cases_k` parameter is always 0. The system prompt still contains a `cases_context` placeholder (inherited from the RAG template), but it is populated with "暂无相似案例" at runtime. The case base remains in the system for the web prototype (Chapter 8), where the leakage concern does not apply in the same way — a merchant or regulator using the interactive tool is not submitting items from the frozen evaluation set.

This decision means the agent's performance figures in Section 6.5 represent a fair, contamination-free evaluation of retrieval-only augmentation. Had cases been enabled, performance numbers would be artificially inflated for the 8 overlapping samples and likely also for semantically similar cases nearby in the embedding space. The 8 overlapping PDFs represent approximately 6% of the case base and roughly 1.6% of the evaluation set's violation sources — small enough that enabling cases would not dramatically change the aggregate metrics, but the principle of clean separation between retrieval knowledge and evaluation targets is important to maintain for scientific validity.

---

## 6.5 End-to-End Agent Results on the 780 Samples

Running the full six-node agent over all 780 evaluation samples produces the results shown in Table 6-2, reproduced here alongside the RAG and Baseline benchmarks for context.

**Table 6-2** Three-route comparison on the 780-sample evaluation set.

| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) | Agent (Qwen3-8B) |
|---|---|---|---|
| Binary accuracy | 89.35% | 89.85% | 86.98% |
| Violation-type accuracy | 73.68% | 74.94% | 71.52% |
| F1 | 91.47% | 92.01% | 89.79% |
| Legal-basis quality avg | 0.8411 | 0.7321 | 0.7035 |
| Reasoning quality avg | 0.8415 | 0.8685 | **0.8931** |
| Avg response time (s) | 7.02 | 7.77 | 37.62 |

The agent's binary accuracy (86.98%) and type accuracy (71.52%) are approximately 2.4 pp and 2.2 pp below the Baseline respectively — a drop that may seem counterintuitive given the additional processing steps.

Several factors contribute to this classification trade-off. The structured CoT prompt is more verbose and directive than the baseline's single-shot prompt, which means that when the model's prior knowledge and the retrieved evidence point in different directions, the CoT structure can occasionally lock the model into a wrong reasoning path that it then rationalizes. The rule-based IntentAnalyzer may also generate incorrect violation-type hints for atypical phrasing, biasing the retrieval toward the wrong legal domain before the model has a chance to reason freely. A third contributor is that the agent introduces more decision points that can go wrong: a failed Grader filter may remove a genuinely relevant article, leaving the ReasoningEngine with incomplete statutory evidence. In the single-shot routes, all retrieved articles reach the model without filtering; the Grader trades recall for precision, which helps the majority of cases but hurts edge cases where the most relevant article happens to be the one with low coverage score.

The reasoning quality score tells a different story: at **0.8931**, the agent produces the highest-quality reasoning outputs across all three routes, exceeding the Baseline (0.8415) by a margin of 5.2 points and RAG (0.8685) by 2.5 points. Because the reasoning quality metric rewards factual specificity, logical connectives, and multi-sentence structure, the 4-step CoT architecture is directly responsible for this gain. The model is not merely generating a verdict; it is constructing a document-level argument.

Whether the classification trade-off is acceptable depends on the deployment context, which we discuss in Section 6.8.

---

## 6.6 Per-Node Timing Analysis

Table 6-3 shows average per-node latency from the timing run `results/agent/agent_v4_780_node_timings__04-19/results.json`, which processed 777 of 780 samples successfully.^[note1]^

**Table 6-3** Per-node average latency (777/780 successful samples, `agent_v4_780_node_timings__04-19`).

| Node | Avg (ms) | Share of pipeline |
|---|---|---|
| intent_analyzer | 0.11 | < 0.01% |
| adaptive_retriever | 19,167.81 | ~53% |
| grader | 0.08 | < 0.01% |
| reasoning_engine | 11,175.34 | ~31% |
| reflector | 453.58 | ~1.3% |
| remediation_advisor | 5,342.60 | ~15% |
| **total_pipeline** | **36,139.52 ms (~36.14 s)** | 100% |

Table 6-3 Per-node average latency for the agent pipeline. Values are averaged over 777 successfully processed samples.

^[note1]^ *The per-node timing run reports 36.14 s average. The 37.62 s figure cited in Table 6-2 comes from a separate run (`results/compare/improved-1.md`). These are distinct experimental runs and their latency figures should not be mixed or averaged.*

The latency profile is dominated by two LLM-backed nodes: AdaptiveRetriever (19.17 s, ~53%) and ReasoningEngine (11.18 s, ~31%). The retrieval dominance is consistent with the RAG findings in Chapter 5 — encoding the query, running the HNSW search, computing BM25 scores, and running the CrossEncoder re-ranker all add up, and in the agent the retrieval call may use `laws_k = 4` or `5` for complex cases, slightly widening the re-ranking pool. ReasoningEngine latency reflects Qwen3-8B inference time over a longer structured prompt.

The RemediationAdvisor accounts for approximately 5.34 s (~15%), reflecting the mixture of fast-mode (near-zero) and detailed-mode (LLM call) activations across the 777 samples. The remaining nodes — IntentAnalyzer (0.11 ms) and Grader (0.08 ms) — are computationally negligible. The Reflector's 453.58 ms is partly the cost of string-matching heuristics and partly the amortized overhead of re-reasoning invocations triggered on a subset of samples.

One design implication is clear: reducing the agent's wall-clock time requires targeting the retrieval step. Options include a lighter re-ranker, early stopping in HNSW search, or asynchronous retrieval that overlaps with intent analysis. Any of these would require re-validating accuracy, which we leave as future work.

![Figure 6-2: Per-node latency breakdown (pie/bar chart)](figures/ch6_node_timing_breakdown.png)

Figure 6-2 Visualization of per-node average latency from the `agent_v4_780_node_timings__04-19` run. AdaptiveRetriever and ReasoningEngine together account for over 84% of total pipeline time.

---

## 6.7 Case Study

To illustrate the agent's behavior on a concrete example, we trace through a representative case from the `agent_v4_780_node_timings__04-19` results: a merchant operating on Alipay Life who was penalized for failing to display the unit price for a service package, with a total penalty of ¥402,500.

**IntentAnalyzer output.** The case description contains "未明码标价" and "未标明价格" — both strong triggers for the 不明码标价 category. The analyzer also detects a platform reference ("支付宝") and a monetary figure, setting `key_entities = ["支付宝", "402500元"]`, `complexity = simple`, `suggested_laws_k = 3`, `suggested_cases_k = 0`, and `violation_type_hints = ["不明码标价"]`.

**AdaptiveRetriever output.** With `laws_k = 3`, the retriever returns the top-3 articles after RRF fusion and CrossEncoder re-ranking. The top result is Article 13 of the Price Law ("经营者销售商品和提供服务，应当按照政府价格主管部门的规定明码标价"), with a rerank score indicating high relevance. Article 42 of the Price Law (penalty provision) and an article from the Provisions on Administrative Penalties for Price Violations also appear in the returned set.

**Grader output.** The Grader assigns Article 13 a final score based on the weighted composite: the rerank score (high, contributing approximately 0.52 to the relevance term), plus coverage of key entity keywords in the article content ("标价" appears in the article body, contributing 0.15 to the coverage term), plus freshness (Article 13 of the Price Law was enacted in 1997, scoring 0.6 and contributing 0.06 to the freshness term). The estimated final score exceeds 0.5, so the article passes the filter. Both penalty articles also score above 0.5 and are retained. All three articles are forwarded to the ReasoningEngine.

**ReasoningEngine output (4-step CoT).** The model identifies the operative facts (service on Alipay, no unit price displayed), matches them against Article 13's elements (operator must display prices clearly), determines that the elements are satisfied, and concludes `is_violation: true, violation_type: "不明码标价"`. The reasoning field explicitly walks through each CoT step, citing the specific article keys.

**Reflector.** No critical triggers are fired: `is_violation` and `violation_type` are consistent, the reasoning chain contains the expected "明码标价" and "未标明" keywords, and there are no non-price-domain signals. `reflection_count = 0` at the end of this case.

**RemediationAdvisor.** With `complexity = simple`, the fast-mode template for 不明码标价 is selected, producing a two-item remediation list: (1) immediately post unit prices for all listed services, and (2) train staff on price-display requirements within 10 business days.

![Figure 6-3: Case study walk-through — annotated screenshot or flowchart of the six-node trace](figures/ch6_case_study_trace.png)

Figure 6-3 Step-by-step trace of the agent pipeline for the representative 不明码标价 case. Each panel shows the input and output of one node.

---

## 6.8 Discussion

**Where the 5× latency is justified.** The agent route is most valuable in two settings. The first is high-stakes regulatory enforcement: a regulator who is preparing an administrative penalty decision needs a traceable, step-by-step reasoning chain that can be reviewed by legal counsel and attached to the official record. The agent's 4-step CoT output, graded evidence list, and optional case-comparison analysis provide precisely that — and the 37-second wait is trivial relative to the days a human reviewer would spend on the same task. The second is merchant self-audit: a seller who wants to assess their own compliance posture before a regulatory inspection benefits from the RemediationAdvisor's checklist, which the single-shot RAG route does not provide. For these actors, the qualitative depth of the output justifies the latency cost.

**Where it is not worth the overhead.** Bulk classification at scale — e.g., screening 10,000 newly filed enforcement cases to assign preliminary violation-type labels for routing — does not require structured CoT or remediation steps. In this setting, the RAG route is clearly preferable: it is 4.8× faster, and its classification accuracy is actually 2.9 pp higher than the agent's. Using the agent for batch screening would impose a ~170× total compute cost compared to the baseline with no accuracy benefit.

A practical deployment would route incoming queries based on use-case context: brief, low-complexity queries from consumers or automated monitoring pipelines go to RAG; detailed, high-stakes queries from regulators preparing enforcement memos or merchants conducting self-audits go to the agent. The IntentAnalyzer's complexity estimate could serve as the routing signal with minimal added overhead, since it runs in under 0.2 ms. A hybrid deployment of this kind would achieve near-RAG accuracy at scale while preserving the agent's depth for the minority of cases that genuinely require it.

---

## 6.9 Limitations

Honest evaluation requires documenting not just what a system does well but where it falls short. Three limitations of the agent route deserve explicit acknowledgment.

The rule-based IntentAnalyzer is brittle against novel phrasing. Its keyword trigger lists were constructed by inspecting the existing 780-sample dataset and the 691 law articles. If a new category of pricing violation emerges — or if complaint language shifts significantly — the trigger lists will fail silently, emitting empty hints and defaulting to generic configuration. Maintaining these lists requires ongoing curation. An LLM-based intent analysis node would generalize better but would add latency and cost.

The Reflector's heuristic validation misses deeper legal nuance. It catches internal contradictions (the most common failure mode) but cannot detect subtler errors such as applying the wrong penalty provision to a correctly identified violation type, or misidentifying which element of a multi-element provision is satisfied. A more robust reflection step would require either a dedicated legal-reasoning LLM or a formal rule engine with statute-level knowledge — both beyond the scope of this thesis.

Retriever latency dominates the pipeline. At 19.17 s average, the AdaptiveRetriever accounts for more than half of total agent time. The node-level timing data shows that no amount of optimization to the other five nodes can reduce total latency below roughly 16 seconds without also addressing retrieval. This creates a fundamental engineering challenge for real-time interactive deployments, particularly on CPU-only inference hardware. Speculative or asynchronous retrieval — beginning the embedding call in parallel with the IntentAnalyzer rather than sequentially after it — is a straightforward optimization that could reduce end-to-end latency by the IntentAnalyzer's (admittedly tiny) 0.11 ms, but the bigger win would come from quantizing the CrossEncoder or using a smaller re-ranker model.

A fourth limitation applies to the evaluation coverage of individual nodes. The 780-sample aggregate metrics measure the pipeline as a whole, but individual nodes may have compensating errors: the Grader might incorrectly filter an article, and the Reflector might correctly compensate by triggering a re-reasoning. Or the IntentAnalyzer might assign the wrong violation-type hint, the retriever might nonetheless return the right articles through lexical matching, and the ReasoningEngine might arrive at the correct verdict anyway. Disentangling these node-level contributions would require per-node ground-truth annotations, which are not available in the current dataset.

---

## 6.10 Summary of This Chapter

Table 6-4 provides a concise reference of the agent pipeline's key configuration parameters as used in the formal 780-sample evaluation.

**Table 6-4** Agent pipeline configuration.

| Parameter | Value | Notes |
|---|---|---|
| Architecture | 6-node linear graph | With one conditional reflection loop |
| IntentAnalyzer | Rule-based, no LLM | 0.11 ms avg |
| AdaptiveRetriever | HybridRetriever | distance_threshold=0.15, min_k=2 |
| laws_k | 3 / 4 / 5 | Driven by complexity |
| cases_k | 0 | Disabled (leakage control) |
| Grader weights | rel=0.6, cov=0.3, fresh=0.1 | min_score=0.5, min_keep=2 |
| ReasoningEngine | Qwen3-8B, 4-step CoT | via MaaS |
| max_reflection | 1 | At most one re-reasoning |
| RemediationAdvisor | Fast (simple) / Detailed (medium/complex) | Template vs LLM |

This chapter has presented the design, implementation, and evaluation of the six-node agent pipeline for price compliance supervision. The pipeline augments the RAG retrieval infrastructure with intent-driven parameterization, evidence grading, structured 4-step chain-of-thought reasoning, heuristic self-reflection, and template or LLM-based remediation advice.

On the 780-sample evaluation set, the agent achieves the highest reasoning quality score of any route (0.8931), demonstrating that the explicit CoT architecture and reflection mechanism produce more structured and evidence-grounded analyses. The trade-off is a 2.4 pp reduction in binary classification accuracy relative to the Baseline and a wall-clock time of 37.62 s per sample — approximately 4.8× slower than RAG. Per-node timing analysis locates 84% of the latency in the AdaptiveRetriever and ReasoningEngine nodes.

The appropriate interpretation is that classification accuracy and reasoning quality are not the same objective. The agent trades the former for the latter in a domain — regulatory price enforcement — where the quality of the legal argument often matters more than the correctness of the binary label. Chapter 7 revisits the metric design that underlies these comparisons, and Chapter 8 shows how the agent pipeline is wrapped into an interactive web prototype that serves consumers, regulators, and merchants.
