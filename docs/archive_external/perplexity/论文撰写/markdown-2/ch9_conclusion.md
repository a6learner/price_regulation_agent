# 9 Conclusion and Future Work

## 9.1 Summary of the Work

This thesis set out to answer a practical question: for automated price-compliance supervision on e-commerce platforms, which technical route offers the best combination of classification accuracy, legal-reasoning quality, and operational cost—a plain LLM call, retrieval-augmented generation, or a structured multi-node agent?

We built three systems—Baseline, RAG, and Agent—on top of the same Qwen3-8B model accessed via 讯飞星辰 MaaS, and evaluated all three on 780 real administrative penalty documents collected from the State Administration for Market Regulation's public penalty portal (cfws.samr.gov.cn). The documents were cleaned from an original pool of ~791 records, annotated with binary violation labels and violation-type categories, and split into 489 positive (violation) and 291 negative (compliant) samples across ten violation types.

The evaluation framework itself is one of the outputs of this work. A single accuracy figure was inadequate for a system whose outputs feed into legal decisions, so we defined five quality dimensions—binary accuracy, violation-type accuracy, F1, legal-basis quality, and reasoning quality—alongside wall-clock latency, and applied all six to the same 780-sample ground-truth set. Heuristic scores for the last two dimensions are directional proxies rather than ground-truth validators, a limitation we acknowledge throughout.

On binary accuracy, the three routes sit remarkably close together: **89.35%** (Baseline), **89.85%** (RAG), and **86.98%** (Agent).^[16]^^[18]^ F1 scores follow the same ordering: 91.47%, 92.01%, and 89.79%. Violation-type accuracy—the metric that measures whether the system correctly names the legal category—is 73.68%, 74.94%, and 71.52% respectively. These numbers confirm that retrieval-augmented context provides a modest but real classification benefit, while the agent's additional complexity slightly hurts raw accuracy without offering a compensating gain on that dimension alone.

Latency tells the other side of the story. Baseline averages **7.02 s/query**, RAG adds only 0.75 s to reach **7.77 s**, and the Agent jumps to **37.62 s**—roughly 5× slower. Per-node timing shows that the retriever (19.17 s average) and the LLM reasoning call (11.18 s) together account for over 80% of the agent's pipeline time.

The reasoning quality heuristic—which measures whether the output contains factual keywords, legal-analysis terms, logical connectives, and multi-sentence structure—tells a different story. Baseline scores 0.8415, RAG scores 0.8685, and Agent scores **0.8931**. The agent's structured CoT prompt in the ReasoningEngine and the Reflector's ability to retry when it detects internal inconsistencies produce measurably richer explanations even when the binary verdict does not change. For a compliance system where the explanation is as legally consequential as the classification, that gap matters.^[27]^^[28]^

We also deployed the agent pipeline as an interactive web prototype—a React + FastAPI + SSE application with role-specific interfaces for consumers, regulators, and merchants—demonstrating that the same six-node code path can support human-in-the-loop use without modification.

## 9.2 Contributions

This work makes four concrete contributions.

**A 780-sample real-world evaluation dataset.** The dataset, `price_regulation_agent/data/eval/eval_dataset_v4_final.jsonl`, is built from genuine administrative penalty documents rather than synthetic or LLM-generated cases. Each record has a binary violation label, a typed violation category drawn from ten classes, and annotated qualifying and penalty articles. Measuring five quality dimensions—binary accuracy, type accuracy, legal-basis quality, reasoning quality, and latency—provides a richer characterisation of system behaviour than any single metric.^[53]^^[54]^

**A quantified cost-effectiveness trade-off between RAG and Agent.** The side-by-side comparison on identical data shows that RAG dominates on the cost-effectiveness axis: +0.5 pp accuracy for +10% latency relative to Baseline. The Agent dominates on reasoning depth: +5.2 pp reasoning score and +0.52 pp type accuracy relative to Baseline, at roughly 5× the latency cost. Neither route is universally superior; the choice depends on whether the deployment prioritises throughput (RAG) or explanation quality (Agent).^[16]^^[27]^

**A complete 6-node agent architecture with heuristic reflection.** The architecture—IntentAnalyzer → AdaptiveRetriever → Grader → ReasoningEngine → Reflector → RemediationAdvisor—is fully implemented, reproducible from the repository, and designed so that each node has a well-defined input/output contract. The Reflector operates at zero extra LLM cost for passing cases (it is a rule-based heuristic check) and calls for at most one re-reasoning retry on failure, keeping the per-query cost bounded.^[16]^

**A React + FastAPI + SSE human-in-the-loop prototype.** The web application reuses the exact agent pipeline without duplication, adds role-aware remediation framing for three user types, and persists every conversation to a SQLite trace database for future analysis. The prototype demonstrates that the same code powering batch evaluation can support interactive compliance assistance with minimal architectural changes.^[41]^^[42]^

## 9.3 Limitations and Open Problems

Each of the contributions listed above comes with a corresponding limitation that shapes the scope of the claims we can make.

**Heuristic quality scores are proxies, not legal ground truth.** The legal-basis and reasoning scores are computed by a keyword-matching and sentence-counting formula defined in `src/baseline/response_parser.py`. They measure surface properties of the output—the presence of domain terms, statutory article patterns, logical connectives—not the accuracy of the legal analysis itself. A model that generates plausible-sounding but legally incorrect reasoning can score well on these metrics. Replacing them with expert-adjudicated ratings is the single most important quality improvement available to future work.^[53]^^[54]^

**Class imbalance harms rare violation types.** The dataset contains 221 "不明码标价" samples but only 1 "哄抬价格" and 1 "不履行价格承诺" sample. All three routes show dramatically lower type accuracy on rare categories, and no amount of retrieval improvement can compensate for a language model that has seen very few training examples of those categories. Future work should explore data augmentation or targeted few-shot prompting for the long-tail violation types.

**Agent latency is dominated by the retriever.** At 19.17 s average, the adaptive retriever—which runs a CrossEncoder re-ranker over every candidate chunk—accounts for ~53% of the pipeline. This is the primary barrier to interactive deployment. Approximate nearest-neighbour indexing, cached re-ranking results, or a lighter re-ranker model could plausibly reduce this by an order of magnitude.

**The IntentAnalyzer is rule-based and brittle.** The intent analysis node uses a hard-coded keyword vocabulary to infer violation type hints and set retrieval parameters. It will misfire on any phrasing that falls outside the observed keyword set—regional slang for pricing violations, newly coined regulatory terminology, or cases described entirely in English. A learned intent classifier trained on the annotation labels in the evaluation set would be more robust.^[56]^

**No per-item provenance log for the 791 → 780 cleaning step.** Eleven documents were removed during the construction of `eval_dataset_v4_final.jsonl`, but no itemised record of which documents were removed and why was retained. If a reviewer questions a specific annotation decision, we cannot trace it back to the cleaning pipeline. Future dataset construction should maintain a deletion log as a matter of course.

One further limitation cuts across all three routes: the choice to use Qwen3-8B—rather than the larger Qwen3.5-397B-A17B that scored 93.15% accuracy on the 159-sample pilot—was driven by cost and latency, not by model strength. The three-model pilot showed that a 4.6× larger model gains only 3.24 pp on binary accuracy. For most deployments that trade-off is reasonable, but it means the results in this thesis represent a cost-optimised operating point, not an upper bound on what is achievable with this architecture.

## 9.4 Future Work

**Expert legal adjudication to replace heuristic scoring.** The most direct improvement to the evaluation framework would be to have practitioners—either licensed lawyers or experienced enforcement officials—rate a stratified sample of outputs on dimensions such as statutory accuracy, factual completeness, and reasoning soundness. Even adjudicating a few hundred samples would allow calibration of the heuristic scores against human judgement and would give a more defensible basis for comparing the three routes.

**Extending to more violation categories and jurisdictions.** The current dataset covers price violations under Chinese national law (Price Law, E-Commerce Law, Anti-Unfair Competition Law) and concentrates on five major violation types. The architecture is not inherently China-specific—the retriever, grader, and reasoning engine would work with any structured legal knowledge base. Extending to provincial regulations, platform-specific rules, or other consumer protection domains (product safety, advertising standards) would test the generalisability of the design.

**Distillation or LoRA adaptation of a domain model.** The system currently relies entirely on a MaaS endpoint for inference. Training a smaller, locally-deployable model on the 780-sample dataset—either through supervised fine-tuning on the ground-truth labels or through distillation from the larger MaaS model's outputs—would remove the external API dependency, reduce latency, and allow deployment in environments with strict data-privacy requirements. The trace database accumulated by the web prototype could serve as an additional source of training signal.^[27]^^[28]^

**Human-in-the-loop learning from prototype traces.** The `traces.db` database accumulates every query, role, result, and implicit feedback signal (whether the user re-queried, deleted the trace, or accepted the result). A small feedback widget on the report card—a simple thumbs-up / thumbs-down on the conclusion—would make that signal explicit. Those ratings could feed an active-learning loop: surface borderline cases to a legal reviewer, add their labels to the evaluation set, and retrain or re-prompt the agent accordingly.

**Production deployment: single-port packaging, authentication, audit log page.** The three gaps identified in Section 8.9 (dual-port setup, no authentication, no audit log) are all tractable engineering work. Single-port packaging by mounting the built React app as a FastAPI static route is already documented in the README. Adding OAuth2 via `python-jose` and the `fastapi-security` utilities is straightforward given the existing middleware structure. An audit-log page within the React application could surface the `traces.db` data in a table with filtering and export, turning the prototype into a minimal production-grade compliance dashboard.

## 9.5 Closing Note

We started this project with a simple question about which retrieval strategy makes a legal-reasoning system better. The answer turned out to be "it depends on what better means"—and making that dependence explicit required building out a five-dimensional metric framework, running three complete evaluation pipelines on 780 real enforcement documents, and then building an interactive prototype to show what the system actually looks like when a human uses it.

None of the three routes is finished. The Agent produces the richest reasoning but takes half a minute per query; the legal-basis heuristic rewards the Baseline for memorising article numbers it learned from training data, not for genuine legal analysis; the compliant-case class trips up all three systems about a quarter of the time. Those are the open problems, and they are real ones worth solving.

The raw numbers—780 samples, three routes, six metrics—are a starting point, not a conclusion. The eventual goal is a system that a regulator can trust, a merchant can learn from, and a consumer can navigate without a law degree. We are not there yet, but the distance is measurable.
