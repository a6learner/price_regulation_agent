# 9 Conclusion and Future Work

## 9.1 Summary of Work

This thesis set out to examine whether retrieval augmentation and agentic reasoning genuinely improve an LLM-based price compliance system, or whether a capable base model already handles the core classification task well enough to make further architectural investment unnecessary. The answer turned out to be both yes and no, depending on which aspect of "improvement" one has in mind.

The evaluation was conducted on a unified set of 780 samples — 489 confirmed price-violation cases and 291 compliant cases — drawn from administrative penalty records published by the State Administration for Market Regulation. Three technical routes were compared under identical conditions: a Baseline route relying solely on Qwen-8B with a structured prompt, a RAG route augmenting that model with hybrid retrieval over 691 law articles and 133 historical cases, and an Agent route replacing the single inference step with a 6-node linear workflow. To prevent same-source contamination, the 133 historical cases were included in the system but excluded from retrieval during evaluation (`cases_k=0`); the RAG and Agent routes therefore retrieved only from the law knowledge base during all reported experiments.

On binary classification accuracy, the three routes returned 89.35%, 89.85%, and 86.98% respectively — a spread of approximately 2.4 percentage points. The F1 scores follow a similar pattern: 91.47% for Baseline, 92.01% for RAG, and 89.79% for Agent. These figures confirm that Qwen-8B carries most of the classification capacity on its own, and that adding layers of retrieval or reasoning around it does not materially raise, or lower, that ceiling.

The more meaningful differences appear elsewhere. RAG improves Recall relative to Baseline, reducing false negatives in a domain where missing a genuine violation carries greater institutional cost than raising an unnecessary flag. Agent achieves a reasoning-quality score of 0.8931, the highest of the three routes, compared with 0.8415 for Baseline and 0.8685 for RAG. Beyond classification, Agent is the only route that generates actionable remediation suggestions alongside a judgment. This comes at the cost of a small binary-accuracy regression (86.98% vs. Baseline 89.35%) and substantially higher latency (37.62 s vs. 7.02 s per case).

The retrieval design in RAG and Agent shared the same HybridRetriever: BM25 and dense vector retrieval combined via Reciprocal Rank Fusion, followed by a CrossEncoder re-ranking step and dynamic Top-K filtering using a distance threshold and mean-distance-based cutoff. Within the Agent workflow, the Grader node weighted retrieved documents by relevance (0.6), coverage (0.3), and freshness (0.1). The ReasoningEngine then produced a structured chain-of-thought in five steps — fact extraction, data verification, law matching, case reference, conclusion — before the Reflector applied heuristic validation and triggered at most one re-reasoning retry. The RemediationAdvisor node issued operator-directed corrective suggestions only when a violation was confirmed.

Response latency reflects this complexity. Baseline averaged 7.02 seconds per case. RAG added a modest overhead at 7.77 seconds. Agent, running five LLM calls through its full node sequence, averaged 37.62 seconds — roughly 5.4 times the Baseline cost.

---

## 9.2 Main Findings and Their Meaning for Practice

### 9.2.1 Classification Capability Is Largely Saturated by the Base Model

The near-flat accuracy across three architecturally distinct routes — approximately 2.4 percentage points separating them — points to one straightforward conclusion: for this domain and at this data scale, the dominant factor in classification performance is the quality of the underlying language model, not the scaffolding built around it. Qwen-8B, after a pilot comparison against Qwen (full-size) and MiniMax, was selected as the base for all downstream work. Its 89.35% binary accuracy on the Baseline route reflects genuine language understanding of price-regulation language, not simply pattern matching.

This finding matters to practitioners because it pushes back against a common assumption — that more engineering necessarily yields better predictions. In a compliance domain with relatively well-defined violation categories, a well-prompted LLM already covers most of the decision space. Architectural complexity earns marginal accuracy gains while substantially raising inference cost and system maintenance burden. The implication is that teams should establish a strong Baseline before investing in retrieval pipelines or agent frameworks, and frame those investments around explainability goals rather than accuracy targets.

### 9.2.2 RAG Is the Cost-Effectiveness Sweet Spot for Routine Compliance Monitoring

RAG offers the best combination of classification reliability and operational efficiency. Its F1 of 92.01% is the highest of the three routes, and its Recall improves on Baseline's, meaning more genuine violations are caught. The response time of 7.77 seconds is only marginally higher than the Baseline's 7.02 seconds. RAG outputs are more readable and auditable than Baseline's, even if they do not reach Agent depth.

For organizations running continuous, high-volume compliance screening — monitoring product listings across a platform, for instance — RAG provides audit trails and reduced false-negative rates without the latency and cost penalties of a full agentic loop. It is, in practice, a pragmatic upgrade rather than a fundamental redesign.

### 9.2.3 Agent's Real Value Is Auditability and Remediation

Agent's real value is auditability and remediation. Its reasoning-quality score (0.8931) is the highest of the three routes, and it is the only route that produces remediation suggestions alongside a judgment. This comes at the cost of a small binary-accuracy regression (86.98% vs. Baseline 89.35%) and substantially higher latency (37.62 s vs. 7.02 s per case).

These outputs matter for a particular use case: deep case review by a human regulatory officer who needs to produce a written decision. The officer is not just asking "is this a violation?" but "what are the relevant legal provisions, what evidence in the case record supports that reading, and what should the operator be told to do?" The Agent, through its ReasoningEngine and RemediationAdvisor nodes, attempts to answer all three. Whether the answer is legally correct is a separate question — that gap is addressed in Section 9.3 — but the structure of the output aligns with what formal administrative review actually requires.

### 9.2.4 Compliant-Case Handling Remains a Shared Weakness

All three routes struggle disproportionately with compliant cases. Preliminary analyses indicate that the compliant class is harder to handle than any single violation class, and that the Agent, despite its most elaborate reasoning chain, is not the best on this class — its more thorough reasoning appears to make it more prone to finding borderline reasons to flag a case. Exact per-category figures will be back-filled from the authoritative run at the time of final submission.

This asymmetry is consistent with what one might expect from a model trained primarily on regulatory language and violation descriptions: the model has a vocabulary and conceptual frame oriented toward identifying wrongdoing, and it takes extra interpretive effort to conclude that nothing is wrong. The compliant-case weakness is, to some extent, a feature of the training signal embedded in the base model, not merely a pipeline design choice. It represents the clearest remaining gap in the current system's reliability.

---

## 9.3 Limitations

Several limitations of this work are worth stating plainly, both to situate the results correctly and to inform how future work might address them.

The evaluation domain covers only price-related administrative penalties. Every sample in the 780-case set was drawn from penalty documents issued under price regulation statutes. It is not known how well any of the three routes would generalize to other compliance domains — product quality, advertising standards, food safety — even within the same market supervision authority. The vocabulary overlap and violation logic differ enough that direct transfer cannot be assumed.

The quality metrics used for reasoning, evidence-chain completeness, and remediation actionability are heuristic scores. They measure surface properties of the output — presence of certain structural elements, citation patterns, linguistic markers of specificity — rather than legal-fact correctness. A response can score well on evidence-chain completeness while citing a law article that does not actually apply to the case at hand. The metrics are useful proxies for output quality but should not be mistaken for legal validity assessments.

The Reflector node in the Agent operates on heuristic rules only. It checks internal consistency of the ReasoningEngine output and triggers a retry if violations of those rules are detected. It does not consult any external regulatory database, does not verify that cited law articles exist in their current form, and does not compare its conclusions against a ground-truth legal database. This means the self-correction the Reflector provides is bounded by the quality of its own rule set.

Legal-article citation accuracy remains low across all routes. The best figures in the evaluation are achieved by Agent, though they remain far from reliable. Most citations the system produces are plausible but imprecise — pointing to the correct regulatory instrument without pinning the exact article number. This is a meaningful limitation in any context where legal precision matters.

The frontend prototype described in Chapter 8 is at the design stage only. No user studies have been conducted, and the interface has not been tested with actual regulatory officers. The usability claims in that chapter are design intentions, not empirical findings.

One additional point deserves an honest mention. An attempt was made to fine-tune Qwen-8B using LoRA and QLoRA on the available labeled data, with the goal of producing a domain-specialized model that might close the gap in compliant-case handling or legal citation accuracy. The experiment did not yield satisfactory results. At the current data scale and with the class imbalance present in the dataset (489 violations vs. 291 compliant cases), the fine-tuned models did not outperform the original Qwen-8B in a way that justified including them in the main comparison. This result is not reported in the experimental chapters, but it is noted here because it shaped the decision to focus on prompt-based and retrieval-based approaches rather than parameter-level adaptation.

---

## 9.4 Future Work

### 9.4.1 Domain Fine-Tuning at Larger Scale

The LoRA/QLoRA attempt described in Section 9.3 failed primarily because the training set was too small and too imbalanced to give the adapter layers a useful learning signal. The path forward is not to abandon fine-tuning but to wait for better data conditions. If the labeled dataset could be expanded to several thousand cases with more even class distribution — including a larger share of compliant cases and rarer violation types — supervised fine-tuning becomes worth revisiting. The current 489/291 split already reflects a meaningful share of compliant cases, but the absolute count remains too low to provide a robust fine-tuning signal. Instruction-tuning on structured chain-of-thought examples generated by the Agent's ReasoningEngine might also serve as a form of synthetic augmentation, giving the fine-tuned model exposure to the kind of legal reasoning steps that the current Baseline cannot produce.

### 9.4.2 Graph-Structured Retrieval for Legal Hierarchies

The current retrieval system treats law articles as a flat collection of documents, indexed and retrieved without regard for how articles relate to each other structurally. Chinese administrative law has a hierarchical structure: framework statutes, implementing regulations, local rules, and departmental guidance interact at multiple levels, and specific articles frequently cross-reference others. A graph-based retrieval approach — building a legal knowledge graph where nodes represent articles and edges represent citation, subordination, or modification relationships — would allow the retrieval step to follow these structural links rather than relying solely on embedding similarity. GraphRAG-style architectures, which combine graph traversal with dense retrieval, are a natural direction to explore for this kind of domain.

### 9.4.3 Multi-Hop Reasoning and a Learned Planner-Critic

The Agent's Reflector currently applies a fixed set of heuristic rules to validate ReasoningEngine output. This approach is low-cost and transparent, but it cannot detect errors that the rules do not anticipate. A more capable design would replace the heuristic Reflector with a learned planner-critic model trained to evaluate the logical sufficiency of a reasoning chain — checking whether the evidence cited actually supports the conclusion, whether relevant legal provisions were overlooked, and whether the violation classification is internally consistent with the stated facts. Multi-hop reasoning, where the system iteratively queries the knowledge base in response to intermediate conclusions rather than issuing a single retrieval at the start, could also improve citation accuracy by allowing the model to narrow its legal references progressively.

### 9.4.4 Integration with Real Regulatory Workflows

The system as built was evaluated offline, against a static dataset. Bringing it into actual use within a local market supervision bureau would require integration with case management systems, structured case-file import, and mechanisms for regulatory officers to provide corrections or override the system's classification. That feedback loop — officer corrections feeding back into the system's knowledge base or fine-tuning pipeline — is the most direct way to improve the system over time. It also creates a natural audit trail: every override becomes a labeled training example where the system's prediction was demonstrably wrong. Building this integration is primarily an engineering and institutional problem rather than a modeling one, but it is the step that determines whether the research has any practical impact.

### 9.4.5 Online Streaming Evaluation Infrastructure

Price regulations are updated periodically. New guidance documents are issued, existing articles are amended, and enforcement interpretations shift. The current system's law knowledge base is a static snapshot of 691 articles indexed at a point in time. A production deployment would need infrastructure to detect regulatory changes, update the vector index incrementally, and re-evaluate any standing decisions that might be affected by the change. Building this streaming evaluation layer — monitoring official government publication channels, parsing new regulatory text, and propagating updates through the retrieval and reasoning pipeline — is a non-trivial engineering task but a necessary one for any compliance system that claims to be current.

---

Three routes, one base model, a single evaluation set of 780 cases. The numbers that came back were not what one might have hoped for before running the experiments: the architecture that took the most engineering effort did not win the classification contest. What the experiments did clarify is that classification accuracy and decision-support quality are different targets, and that building toward the second one — the kind of output a regulatory officer can actually use — requires going further than a prompt and a retrieval step. The gap between a system that answers "yes, violation" and one that explains why, cites the right article, and tells the operator what to fix next is exactly the space this work tried to occupy. Closing that gap fully is a task for future work.
