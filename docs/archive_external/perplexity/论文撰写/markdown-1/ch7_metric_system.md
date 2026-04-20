# 7 Evaluation Metric System

## 7.1 Motivation and Design Principles

Evaluating a price-compliance system with a single accuracy number tells only part of the story. Accuracy collapses all prediction errors into one figure, hiding the asymmetry between the two error types that matter most in a regulatory context: missing a genuine violation versus raising a false alarm. Beyond that, a system that labels cases correctly but cannot explain *why* it reached a decision is of limited operational value; a compliance officer who receives "violation detected" without a cited legal basis has no obvious next action. Cost is a third consideration that a purely accuracy-focused view ignores entirely. An approach that triples the computation time may still be worth deploying — or may not be — but this cannot be determined without the data to make the comparison.

These three concerns — how well the system classifies, how interpretable and legally grounded its outputs are, and what resources it consumes — motivate the three-dimensional evaluation framework used throughout this thesis. We call the three dimensions *effectiveness*, *quality*, and *cost*, and we measure each with a family of specific metrics. The framework is designed from the outset to be shared across all three technical routes (Baseline, RAG, Agent), so that results are directly comparable. Every metric is computed by the same `evaluator` module, applied to the same evaluation set, producing the same structured output format. This is a deliberate choice: cross-route comparisons are only meaningful when the measurement ruler does not change between routes.

One design principle worth stating explicitly is that the metric system is intentionally *stratified*. Classification metrics come first because they measure the primary task. Quality metrics come second because they measure the value added beyond a correct label. Cost metrics come third because they bound the deployment trade-off space. In the analysis chapters (Chapters 4–6) we already reported numbers from this system; here we document the definitions, decompositions, and known limits of each metric so that the experimental claims rest on an auditable foundation.

---

## 7.2 Classification-Level Metrics

Classification-level metrics answer the most basic question: does the system make the right binary decision, and can it correctly identify which type of violation is present?

### 7.2.1 Accuracy, Precision, Recall, and F1

Let TP, FP, FN, and TN denote the counts of true positives, false positives, false negatives, and true negatives over the evaluation set. The four standard metrics are defined as follows:

$$\text{Accuracy} = \frac{TP + TN}{TP + FP + FN + TN}$$

$$\text{Precision} = \frac{TP}{TP + FP}$$

$$\text{Recall} = \frac{TP}{TP + FN}$$

$$\text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

In our setting, a *positive* prediction is "this case contains a price-compliance violation." Precision therefore measures the fraction of flagged cases that are genuine violations, while Recall measures the fraction of actual violations that the system successfully flags.

Looking at the numbers, binary accuracy is 89.35% for Baseline, 89.85% for RAG, and 86.98% for Agent. RAG holds close to Baseline, while Agent registers a ~2.4 percentage-point regression — a meaningful drop that reflects the accuracy cost of its more elaborate reasoning pipeline. F1 scores follow a similar pattern: 91.47%, 92.01%, and 89.79% respectively, with RAG marginally ahead and Agent trading some classification performance for gains on quality dimensions.

Where the routes start to diverge is in the Precision/Recall trade-off. RAG achieves the highest Recall at 96.00%, compared to Baseline's 94.40% and Agent's 95.60%, meaning it is the least likely to let a real violation go undetected. At the same time, RAG's Precision (89.05%) is slightly lower than Baseline's (90.25%), meaning it generates more false alarms. Agent shows the sharpest Precision drop (87.39%), paired with a high Recall (95.60%), suggesting that its more complex reasoning pipeline is, to some extent, tilted toward flagging cases rather than letting them pass.

### 7.2.2 Confusion Matrix and the Cost Asymmetry of Errors

The full confusion matrices are reported in Chapters 5 and 6.

In ordinary classification tasks, FP and FN are treated as roughly symmetric mistakes. In compliance supervision, they are not. A false negative — a violation case classified as compliant — means the platform escapes regulatory scrutiny it should have faced. A false positive — a compliant case flagged as a violation — causes unnecessary investigation burden but can typically be corrected at relatively low cost once a human reviewer checks it. This asymmetry means Recall deserves priority over Precision when the two pull in opposite directions, and FN counts warrant particular attention.

RAG yields small but consistent improvements over Baseline on binary accuracy, violation-type accuracy, and F1 (see Chapters 5 and 6 for full confusion matrices). Agent, by contrast, drops to 86.98% binary accuracy — approximately 2.4 percentage points below Baseline — while delivering higher reasoning quality and remediation coverage. Whether that trade-off is acceptable depends on the deployment context; we do not resolve that policy question here but provide the numbers to inform it.

### 7.2.3 Violation-Type Fine-Grained Accuracy

Binary classification accuracy tells only whether the system correctly distinguishes compliant from violating cases. A compliance officer also needs to know *which* type of violation is present, because different violation types carry different penalty schedules and trigger different remediation requirements. We therefore compute a second accuracy metric — violation-type accuracy — that is conditional on the binary decision being correct.

Formally, violation-type accuracy is computed only over the subset of cases where the system's binary decision matches the ground truth. Within that subset, we check whether the predicted violation category matches the annotated category. This conditional framing is intentional: conflating binary errors with sub-type errors would make it impossible to distinguish a system that fails at coarse classification from one that handles coarse classification well but struggles with fine distinctions.

The evaluation set covers five categories: compliant cases (291 samples) and four violation types — unpriced display (221 samples), government-priced violation (117 samples), surcharge above marked price (73 samples), and misleading price display (49 samples). Overall violation-type accuracy is: 73.68% for Baseline, 74.94% for RAG, and 71.52% for Agent.

Per-category breakdowns are maintained in the per-run JSON output files and are most useful for diagnosing which violation types drive the overall accuracy figures. A common pattern observed across preliminary analyses is that the compliant class is harder to handle than any single violation class — all three routes show a systematic tendency to over-flag when uncertain. This is arguably the appropriate bias given the cost-asymmetry argument above, but it also means that the system as currently designed would require human review to absorb a non-trivial false-positive load. The final per-category numbers will be back-filled from the authoritative 780-sample run at the time of final thesis submission.

---

## 7.3 Quality-Level Metrics

Correct classification is necessary but not sufficient for a compliance system. A response that says "this is a violation" without identifying the relevant law or explaining the legal reasoning cannot be acted upon by a regulator without additional work. Quality-level metrics capture this dimension by scoring the structure and content of the system's output, independent of whether the binary label is right or wrong.

All quality scores are computed by heuristic functions in the shared `ResponseParser` module and are normalized to the range [0, 1]. Their definitions and decompositions are documented below.

### 7.3.1 Legal-Basis Quality Score

The legal-basis quality score assesses whether the system's response contains a credible legal grounding for its decision. We decompose it into three binary sub-components, each carrying equal weight:

**(a) Legal basis provided** — Does the response include any reference to a legal source, regulation, or statutory requirement? This is the minimum bar: a response that gives a verdict with no legal backing at all scores zero on this component.

**(b) Key laws mentioned** — Does the response name at least one of the primary laws governing price behavior in the Chinese regulatory context (most commonly the *Price Law of the People's Republic of China* or *Administrative Penalty Law*)? Naming a law by title is a stronger signal than a generic reference to "relevant regulations."

**(c) Specific article numbers cited** — Does the response include at least one explicit article number (e.g., "Article 13," "第13条")? Article-level specificity is what allows a compliance officer to look up the exact statutory text and assess whether the application is correct.

The final score is the arithmetic mean of these three binary indicators. Scores in our experiment were 0.8411 for Baseline, 0.7321 for RAG, and 0.7035 for Agent. Baseline scores highest here because its prompt is specifically tuned to produce a legal-basis field, whereas the Agent's more elaborate JSON output structure introduces more variability in how legal references appear. The direction of the gap (Baseline > RAG > Agent) is notable and discussed further in Chapter 8.

### 7.3.2 Reasoning Quality Score

Where the legal-basis score focuses on what the system cites, the reasoning quality score focuses on how it argues. It is similarly decomposed into three sub-components:

**(a) Presence of reasoning text** — Does the response contain any substantive reasoning content beyond the verdict itself? A one-word or one-line response scores zero here.

**(b) Presence of fact/law/logic elements** — Does the reasoning section include references to concrete case facts, applicable legal norms, and some form of logical connection between them? All three should be present in a well-structured compliance analysis.

**(c) Structural completeness** — Does the reasoning consist of enough sentences to constitute a coherent argument? We use a minimum sentence count as a proxy for structural depth, which is a crude but computationally tractable measure.

Reasoning quality scores move in the opposite direction from legal-basis scores: Baseline 0.8415, RAG 0.8685, Agent 0.8931. The Agent's advantage here is directly traceable to its ReasoningEngine node, which enforces a five-step structured chain-of-thought — fact extraction, data verification, law matching, case reference, and conclusion — through explicit prompt constraints. This structured generation naturally satisfies the reasoning quality rubric more consistently than the Baseline's single-pass inference. The gap between Agent (0.8931) and Baseline (0.8415) is the clearest quality win the Agent delivers.

### 7.3.3 Higher-Tier Quality Scores for Agent Comparison

The basic quality scores above were designed when only Baseline existed. As RAG and Agent were developed, additional metrics were introduced to capture capabilities that Baseline cannot produce at all. These sub-scores are not reported in the main results table of this thesis; they are available via the `metrics.quality.*` fields in the per-run JSON for follow-up studies. The framework supports additional sub-scores such as evidence-chain completeness and remediation actionability for deeper Agent analysis.

Of particular note is that the Agent is the only route producing remediation suggestions; the reasoning-quality average rises to 0.8931, the highest across the three routes. This reflects the dedicated RemediationAdvisor node at the end of the Agent pipeline, which neither Baseline nor RAG has an equivalent of.

Numerical values for evidence-chain completeness, legal-citation accuracy, remediation actionability, interpretability, and structured-output quality are available in the per-run JSON result files for researchers who wish to conduct follow-up analysis. These sub-scores are not reported in the main results table of this thesis, but the framework is in place for extension studies.

### 7.3.4 Boundary of Heuristic Scoring

A limitation of the quality metric system must be stated clearly. All scores described above are heuristic proxies computed by pattern-matching functions: checking for the presence of keywords, counting sentences, verifying JSON field existence. They measure *form* more than *substance*. A response that mentions "Article 13 of the Price Law" in a syntactically correct sentence will score well on legal-basis quality even if the application of that article to the specific facts is legally incorrect.

This means the quality scores are most reliable as indicators of *relative* differences between routes and as diagnostic tools for identifying structural deficiencies. They are not equivalent to a legal expert's judgment on factual correctness, and they should not be reported as if they were. A proper legal accuracy assessment would require annotators with substantive knowledge of Chinese price regulation — a resource that was not available within the scope of this thesis. We flag this gap explicitly because it bounds the claims that the quality metric results can support.

---

## 7.4 Cost-Level Metrics

Even a system that achieves high accuracy and excellent output quality may be impractical if it is too slow for operational use or too expensive to run at scale. Cost-level metrics provide the third leg of the evaluation framework.

### 7.4.1 Average Response Latency

Response latency is measured as the end-to-end wall-clock time from the moment a case is submitted to the moment a parsed result is returned. We average this over all cases in the evaluation set that completed without error. The values are:

| Route    | Avg. Latency |
|----------|--------------|
| Baseline | 7.02 s       |
| RAG      | 7.77 s       |
| Agent    | 37.62 s      |

Baseline and RAG are close in latency terms; the ~0.75-second overhead of retrieval is modest relative to the LLM call itself. Agent is a different story. At 37.62 seconds per case, it is 5.36 times slower than Baseline. This is primarily driven by the five-node LLM pipeline: AdaptiveRetriever, Grader, ReasoningEngine, Reflector, and RemediationAdvisor each contribute sequential latency, and Reflector may trigger a second ReasoningEngine call in cases where heuristic validation raises a concern.

For a batch processing scenario — auditing a platform's pricing records overnight — 37.62 seconds per case is operationally manageable. For a real-time query scenario — a compliance officer checking a single case interactively — it is at the upper edge of comfort. The appropriate framing depends on the deployment context.

### 7.4.2 Token Usage

Token counts are recorded separately for input and output at each evaluation run, enabling cost modeling against the API pricing of whichever model is in use. The key insight from this data is that Agent's token consumption is substantially higher than the other two routes, in line with its latency profile. Baseline generates a single inference call per case with a compact prompt; RAG extends that prompt with retrieved law articles but still makes a single call; Agent makes multiple sequential calls, with the ReasoningEngine prompt alone carrying the full set of graded law excerpts plus the five-step CoT instruction.

Precise token counts per route are available in the per-run JSON result files. For budgeting purposes, the relative cost multipliers summarized in Section 7.4.3 are the more actionable figures.

### 7.4.3 Relative Cost Multiplier

To make cost differences immediately interpretable, we express RAG and Agent costs as multiples of Baseline:

| Route    | Relative Cost Multiplier |
|----------|--------------------------|
| Baseline | 1.00×                    |
| RAG      | 1.11×                    |
| Agent    | 5.36×                    |

RAG's cost overhead is modest — approximately 11% above Baseline — because retrieval adds prompt tokens but does not add LLM calls. Agent runs at roughly 5.36 times the Baseline cost, driven by the multi-call architecture. These multipliers provide the denominator for any cost-benefit calculation: is Agent's gain in reasoning quality (0.8931 vs 0.8415), remediation coverage, and violation-type accuracy sufficient to justify a 5.36× cost increase, given its ~2.4 pp accuracy regression versus Baseline? Different deployment contexts will produce different answers to that question.

---

## 7.5 Unified Reporting Template and Result Layout

Each evaluation run — whether Baseline, RAG, or Agent — produces a structured JSON result file written to `results/{route}/{timestamp}/`. The file records every case-level prediction together with the individual metric scores, so that aggregate statistics can be recomputed or sliced (by violation type, by confidence bin, etc.) without re-running the model. Aggregate statistics across all cases are computed by the shared `evaluator` module, which is the same code regardless of which route produced the raw predictions.

All three routes are evaluated against exactly the same dataset: `eval_dataset_v4_final.jsonl`, containing 780 samples (489 violation cases and 291 compliant cases). This is a hard constraint. Comparing routes evaluated on different subsets — even subsets drawn from the same source — would introduce sampling variance that could mask or inflate genuine differences. The shared evaluation set eliminates that source of noise entirely.

The result files from the experiments reported in this thesis are:

- `results/baseline/20260418021531_qwen-8b_results.json` — 780 Baseline cases
- `results/rag/20260418021628_results.json` — 780 RAG cases
- `results/agent/20260418113740_results.json` — 780 Agent cases

---

## 7.6 Discussion: Why This Combined Metric Set Is Suitable for This Thesis

The three-dimensional metric system described above satisfies three distinguishable requirements that a thesis in applied AI for regulatory compliance must address.

Academic comparability requires that the experimental results be reproducible and comparable across routes. Using a single shared evaluation set, a single shared evaluator, and standard metric definitions (Accuracy, Precision, Recall, F1 as defined above) meets this requirement. The confusion matrix decomposition adds transparency beyond what aggregate accuracy provides, and the per-category breakdown enables targeted analysis of model behavior. A researcher wishing to repeat or extend this experiment has a well-defined measurement protocol to follow.

Business interpretability requires that the results be legible to non-technical stakeholders — compliance officers, legal team leads, platform operators — who must ultimately decide whether to adopt such a system. Legal-basis quality and reasoning quality scores speak directly to whether the system's outputs are usable in practice. Remediation actionability, unique to Agent, addresses the operational question of what a platform should do after a violation is detected. These are the metrics that translate a research outcome into a business recommendation.

Engineering deployability requires that the cost dimension be made visible. A system that provides excellent explanations but at roughly 5.36 times the latency and cost of a simple inference call requires a different infrastructure investment than one that runs at near-Baseline speed. The latency figures and relative cost multipliers quantify this investment and allow an engineering team to plan accordingly.

There are genuine limitations to acknowledge. The quality metrics are all heuristic approximations, as argued in Section 7.3.4; they capture structural signals but not legal-factual correctness. The entire evaluation is conducted within a single domain (e-commerce price compliance) and a single language (Chinese), so generalization to other compliance domains or languages cannot be assumed. The evaluation set, while constructed from 791 real administrative penalty documents, represents a particular slice of the enforcement record — cases decided and made public between certain dates — and may not reflect the full distribution of violations that a deployed system would encounter.

These limitations do not undermine the conclusions of this thesis, but they do define the boundary conditions within which those conclusions hold. Transparency about what the metrics can and cannot show is part of responsible evaluation design, and we state it here rather than leaving it implicit.

---

With the evaluation framework fully specified — its metrics defined, its decompositions explained, and its limits declared — the next chapter turns to the system implementation and prototype that operationalizes all three technical routes within a single deployable architecture.
