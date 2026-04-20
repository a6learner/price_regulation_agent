# 7 Evaluation Metric System

## 7.1 Motivation

A single accuracy number tells you whether the system got the right binary answer on average—nothing more. For a price-compliance reasoning system that must not only flag violations but also name their legal category, cite the correct statutory articles, and explain how the facts connect to the law, that one number would hide almost everything practitioners actually care about.^[53]^

Consider two outputs that both produce `is_violation = true`. One cites the exact clause of the Price Law and walks through the relevant facts in three coherent sentences; the other generates a confident-looking JSON with a fabricated article number and a generic one-liner that could apply to any case. A binary accuracy metric treats them identically. In legal reasoning tasks the quality of the explanation and the provenance of the statutory basis are not optional extras—they are the substance of the decision.^[54]^

This chapter defines the six measurement dimensions we apply across Baseline, RAG, and Agent, explains how each is computed, presents the aggregate cross-route comparison table, and ends with a frank account of what the heuristic scores can and cannot support.

## 7.2 Metric Categories

### 7.2.1 Binary Correctness

The most fundamental question is whether the system correctly determines whether a given pricing practice constitutes a violation. We frame this as a binary classification problem on the `is_violation` field: positive for any violation type, negative for a compliant case.

From the confusion matrix we derive the standard set: **Accuracy** (fraction of all 780 samples classified correctly), **Precision** (fraction of predicted positives that are genuine violations), **Recall** (fraction of true violations that are identified), and **F1** (harmonic mean of precision and recall). The 780-sample dataset contains 489 positive and 291 negative instances, so a naïve positive-always baseline would score 62.7% accuracy — a useful lower bound for interpreting the ~89–90% figures we observe.

All four statistics are computed on the subset of samples where the model returned a parseable response. Parse failures are counted separately and excluded from the denominator for accuracy and the other statistics. In practice all three routes achieved parse success on at least 773 out of 780 samples.

Precision and recall deserve individual attention even when F1 is the headline number. A compliance system with high recall but low precision raises many false alarms, eroding regulator trust over time. Conversely, high precision with poor recall misses genuine violations and fails the underlying public-interest mandate. We report all four statistics so a reader can judge which type of error their deployment context tolerates more easily.

### 7.2.2 Violation-Type Correctness

Binary correctness does not distinguish between a model that identifies the right violation category (e.g., "不明码标价 — unpriced display") and one that marks the record as a violation but assigns a wrong or generic type label. We capture this with **type_accuracy**: the fraction of successfully processed samples for which the predicted `violation_type` exactly matches the ground-truth label.

Critically, the denominator for type_accuracy includes compliant samples (`is_violation = false`), where the correct type is "无违规." Matching "无违规" against "无违规" counts as a correct type prediction. This choice reflects real system behavior: correctly recognising a compliant case as compliant is just as meaningful as correctly naming a violation category. Inflating type_accuracy by restricting the denominator to violation-only samples would overstate the system's performance on the harder negative cases.

The dataset's class distribution makes this metric demanding. There are ten distinct violation categories in the 780-sample set, with counts ranging from 221 ("不明码标价") down to 1 ("哄抬价格"). Any system that relies on surface-level keyword cues will struggle with the rarer categories, and that structural difficulty shows up directly in type_accuracy scores in the low-to-mid 70s across all three routes.

We made a deliberate choice not to restrict the type_accuracy denominator to violation-positive samples. Some prior work evaluates violation-type classification only on cases where the binary label is positive, reasoning that the type question is undefined for compliant samples. We disagree: in practice, a model that says "this is a violation" when the correct answer is "no violation" has made a compounded error—wrong binary prediction *and* wrong type. Excluding such cases from the type metric would mask that failure mode.

### 7.2.3 Legal-Basis Quality (Heuristic)

The field `legal_basis` in the model's JSON output is free text—an explanation of the statutory articles supporting the judgment. Rather than attempting to parse and verify every cited article against a ground-truth list (which would require a structured legal database beyond the scope of this project), we compute a heuristic quality score using the following additive formula:^[56]^

- **+0.3** if `legal_basis` is non-empty (the model cited something at all)
- **up to +0.5** for keyword hits against a preset list covering terms such as "价格法," "明码标价," "禁止价格欺诈," and related phrases; each hit contributes +0.2, capped at +0.5
- **+0.2** if the text contains a statutory reference matching the regex pattern "第[零一二三四五六七八九十百]+条" (i.e., an Article citation in Chinese form)
- Final score clamped to 1.0

The implementation lives in `src/baseline/response_parser.py` under `evaluate_legal_basis_accuracy`. The same scorer is applied to all three routes so results are directly comparable.

There is an inherent limitation here, which we discuss in Section 7.4. The score rewards the *appearance* of legal reasoning—presence of domain keywords, mention of a statute article—rather than verified correctness. A model that memorises and reproduces common article citations from its training data can score well without genuinely grounding its answer in the retrieved facts.

### 7.2.4 Reasoning Quality (Heuristic)

The `reasoning` field is the model's explanation of how it reached its conclusion. We apply an analogous heuristic scoring formula to the reasoning text:^[51]^^[52]^

- **+0.2** if `reasoning` is non-empty
- **+0.25** if the text contains factual investigative keywords ("经查," "事实," "经营者," and similar)
- **+0.25** if the text contains legal-analysis terms ("根据," "违反," "构成," and similar)
- **+0.15** if the text contains logical connectives ("因此," "因为," "所以," and similar)
- **+0.15** if the sentence count (approximated by punctuation marks such as "。," "？," "！") reaches three or more
- Final score clamped to 1.0

The sentence-count component is a rough proxy for response completeness: a one-sentence answer is unlikely to carry the step-by-step chain of reasoning we expect from a well-functioning legal-reasoning system.

Together, the legal-basis and reasoning scores give a directional read on output quality that binary accuracy entirely misses. A system could achieve 90% binary accuracy while systematically generating single-sentence reasoning with no statutory citations; these heuristic scores would surface that failure mode.

### 7.2.5 Latency

We record wall-clock response time as `performance.avg_response_time` (seconds per sample), measured from the moment a request is dispatched to the MaaS API endpoint to the moment a parsed result is available. This metric folds in network round-trip time, model inference time, and any local post-processing (retrieval, re-ranking, reflection retries).

Latency matters for deployment plausibility: a system that takes 37 seconds per query is not suitable for interactive use without architectural changes, even if its quality metrics are strong. We report latency alongside quality figures rather than treating it as a secondary concern.

### 7.2.6 Per-Node Latency (Agent Only)

Because the Agent route decomposes into six sequential nodes, aggregate latency alone does not identify where time is spent. We instrument each node using wall-clock timestamps captured in `agent_trace.timings_ms` and aggregate across all 780 samples to produce `metrics.node_timings_avg_ms`.

| Node | Avg (ms) | Share of pipeline |
|---|---:|---:|
| intent_analyzer | 0.11 | <0.01% |
| adaptive_retriever | 19,167.81 | ~53% |
| grader | 0.08 | <0.01% |
| reasoning_engine | 11,175.34 | ~31% |
| reflector | 453.58 | ~1.3% |
| remediation_advisor | 5,342.60 | ~15% |
| **total_pipeline** | **36,139.52** | 100% |

Table 7-2 Agent per-node average latency (run `agent_v4_780_node_timings__04-19`). Wall-clock in the main comparison table (37.62 s) comes from a separate run; the 36.14 s figure here differs by ~4% due to network variability.

The adaptive retriever alone accounts for roughly half the pipeline time, primarily because it runs the CrossEncoder re-ranker over every candidate chunk. The reasoning engine (the LLM call) claims another 31%. The intent analyzer and grader, both rule-based or lightweight, contribute negligible time. Any future effort to reduce Agent latency should focus on the retriever and reasoning steps.

## 7.3 Overall Metric Table Across Three Routes

Table 7-1 collects the main results across all 780 samples. Each column is the "best run" for that route as recorded in `results/compare/improved-1.md`.

**Table 7-1** Cross-route evaluation results on 780 real price-enforcement documents.

| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) | Agent (Qwen3-8B) |
|---|---|---|---|
| Binary accuracy | 89.35% | **89.85%** | 86.98% |
| Violation-type accuracy | 73.68% | **74.94%** | 71.52% |
| F1 | 91.47% | **92.01%** | 89.79% |
| Legal-basis quality avg | **0.8411** | 0.7321 | 0.7035 |
| Reasoning quality avg | 0.8415 | 0.8685 | **0.8931** |
| Avg response time (s) | **7.02** | 7.77 | 37.62 |

Several patterns emerge from this table.

**Classification performance is nearly flat across routes.** RAG edges out Baseline by 0.5 percentage points on binary accuracy, while Agent falls ~2.4 pp below Baseline. Given that the Agent uses the same underlying Qwen3-8B model and the same retrieval pipeline, the small accuracy drop likely reflects the additional prompt complexity introduced by the reflection and remediation steps, which can occasionally cause the model to second-guess a correct initial answer during re-reasoning.

**RAG is the cost-effectiveness winner.** The 0.5 pp accuracy gain over Baseline comes at a wall-clock penalty of only +0.75 s per query—a roughly 10% latency increase for a measurable quality improvement. That trade-off is favourable for any deployment scenario where per-query cost scales with inference time.

**Agent is the reasoning-quality winner.** The reasoning score of 0.8931 is 5.2 points above Baseline (0.8415) and 2.5 points above RAG (0.8685). The structured four-step CoT prompt in the ReasoningEngine, combined with the Reflector's ability to retry when critical inconsistencies are detected, consistently produces more fact-grounded, logically articulated explanations—even in cases where the binary classification does not change.

**Legal-basis score shows a paradox: Baseline scores highest (0.8411) while Agent scores lowest (0.7035).** This is an artefact of the heuristic scorer, not a genuine quality reversal. The Baseline model, relying on memorised training-data patterns, tends to reproduce familiar statutory article numbers and domain keywords regardless of whether they are appropriate for the specific case—and the heuristic rewards exactly that surface behaviour. The RAG and Agent routes retrieve *relevant* law excerpts and ground their reasoning in those passages, which are sometimes less keyword-rich than the formulaic article references the Baseline regurgitates. The legal-basis heuristic thus over-rewards pattern repetition and undervalues grounded citation.

This paradox is not a failure of the RAG or Agent designs; it is a diagnostic finding about the heuristic itself. A scorer that gives the same +0.3 bonus for citing "价格法第13条" whether or not that article actually governs the conduct in question cannot distinguish memorisation from understanding. We discuss this in more depth in Section 7.4.

**Compliant cases remain the hardest across all three routes.** The violation-type distribution is heavily skewed: 291 compliant ("无违规") samples against 489 violation samples, with the most common violation type ("不明码标价") alone outnumbering the entire compliant class. All three systems show lower recall on compliant cases—they tend to predict too many violations, a bias consistent with the positive class imbalance in the training data distribution seen by the MaaS model.

![Figure 7-1: Radar chart comparing five quality metrics (Binary accuracy, Type accuracy, F1, Legal-basis avg, Reasoning avg) across Baseline, RAG, and Agent routes](figures/ch7_radar_metrics.png)

Figure 7-1 Radar chart of five quality metrics across the three evaluation routes. The Agent route's reasoning advantage and legal-basis deficit are both visible at a glance.

## 7.4 Honest Caveats of the Metric System

The heuristic legal-basis and reasoning scores measure *linguistic surface properties*, not legal correctness.^[53]^^[54]^ They cannot tell you whether a cited article actually prohibits the conduct in question, whether the reasoning chain is logically sound, or whether a real enforcement officer would accept the output. At best they are directional signals: a very low legal-basis score strongly suggests the model produced nothing meaningful; a very high score is consistent with—but does not prove—substantive quality.

A rigorous evaluation of legal-reasoning quality would require human adjudicators with legal training to rate each output on criteria such as accuracy of statutory identification, completeness of factual analysis, and persuasiveness of the reasoning chain. We did not conduct such an adjudication, and we make no claim that our heuristic scores substitute for it.

The binary and type metrics, by contrast, rest on human-annotated ground truth derived from actual administrative penalty decisions. Within the limits of the annotation quality and the 791→780 data cleaning pipeline, they are the most trustworthy signals in the table. The legal and reasoning scores should be read as supplementary and treated with appropriate scepticism.

A secondary caveat concerns latency measurement. The wall-clock figures in Table 7-1 fold in MaaS network round-trip time, which varies with server load and is not a property of the local code. Two runs on the same dataset with the same code can yield different latency figures—this is why the Agent shows 37.62 s in the main table (from `results/compare/improved-1.md`) and 36.14 s in the per-node timing table (from a different run on the same day). We do not attempt to reconcile these; we note both figures and identify which run each comes from.

## 7.5 Summary of This Chapter

We defined six evaluation dimensions: binary accuracy (and Precision/Recall/F1), violation-type accuracy, legal-basis quality, reasoning quality, aggregate latency, and per-node latency for the Agent route. The heuristic quality scores use an additive rule-based formula applied uniformly across all three routes.

Applied to the 780-sample dataset, the results show RAG as the best trade-off between quality and cost, Agent as the strongest on reasoning depth (0.8931 vs 0.8415 for Baseline), and a legal-basis paradox where the Baseline's tendency to parrot memorised article citations inflates its heuristic score above the grounded-retrieval routes. The compliant-case class presents consistent difficulty across all routes.

The next chapter steps away from batch evaluation and describes the interactive web prototype built to let human users—consumers, regulators, and merchants—engage with the same agent pipeline on their own cases.
