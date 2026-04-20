# 6 Multi-Node Agent Workflow

## 6.1 Motivation and Design Philosophy

The RAG pipeline described in Chapter 5 addresses one genuine weakness of the pure baseline approach: it grounds the model's legal reasoning in retrieved statute text rather than relying solely on parametric knowledge. Yet retrieval-augmented generation, even with cross-encoder re-ranking, remains a largely passive mechanism. It produces a classification and a reasoning string, but it cannot inspect what it has produced, cannot detect when its own output is internally inconsistent, and cannot tell a regulator what to do next. For a tool intended to support actual price-compliance supervision, those gaps matter in practice. An investigator who receives a binary verdict and a paragraph of reasoning still has to decide, case by case, what remediation actions to recommend — a step the RAG pipeline leaves entirely to human judgment.

There is a second, more technical limitation. RAG treats all incoming queries uniformly: every case, whether a straightforward failure to post a marked price or a complex scheme involving disguised price hikes across multiple product categories, triggers the same fixed retrieval call with the same parameter values. In practice, simple cases carry enough of a lexical signal that three retrieved articles are more than sufficient, while complex cases may genuinely benefit from a wider statutory context. A uniform retrieval depth either wastes inference budget on easy cases or under-serves hard ones.

The six-node agent architecture described in this chapter is designed to address both problems. The pipeline decomposes the compliance decision into a sequence of small, individually inspectable steps — intent analysis, adaptive retrieval, document grading, structured reasoning, heuristic reflection, and remediation generation — each of which can be examined, logged, and debugged independently. This decomposition also makes the system's behavior traceable in the sense that matters to an evaluator or auditor: rather than a single opaque call to a language model, the workflow produces a chain of intermediate outputs that record exactly which articles were retrieved, how they were scored, what the model's step-by-step reasoning was, and whether that reasoning passed a validation check.

A deliberate architectural choice deserves explanation here: the agent is designed as a **linear** pipeline rather than as a ReAct-style loop [1]. In a ReAct architecture, the model interleaves reasoning and tool calls in an open-ended cycle, potentially issuing many retrieval requests before converging on an answer. That design offers flexibility but comes with two costs that are difficult to accept in this deployment context. The first is latency: an unbounded loop has no guaranteed upper bound on the number of model calls, which is problematic when the baseline wall-clock time per case is already around 7 seconds and the target is a tool that regulators can use interactively. The second is traceability: the more dynamic and stateful the control flow, the harder it becomes to produce a fixed-length, auditable trace for each case. A linear pipeline with a pre-determined node order allows the system to guarantee that every case goes through the same sequence of steps, that every step is logged, and that the total latency is bounded by the sum of node-level budgets. The orchestration logic lives in `src/agents/agent_coordinator.py`, which instantiates all six nodes and invokes them in sequence, passing the accumulated state object from one node to the next.

The Reflexion framework [3] and Self-RAG [4] offer a conceptually related insight: a system that can evaluate and revise its own intermediate outputs tends to make fewer structural errors than one that commits to its first response. The Reflector node (§6.6) is the component that most directly draws on this idea, though in a deliberately lightweight form: rather than a full self-critique loop, the reflector applies a fixed set of heuristic rules to check the reasoning engine's output for logical contradictions, and at most triggers one re-run.

---

## 6.2 Node 1 — IntentAnalyzer

The first node in the pipeline, implemented in `src/agents/intent_analyzer.py`, performs no language model call. It is a deterministic, rule-based classifier that reads the incoming case description and returns a structured intent analysis: a set of `violation_type_hints` (at most three candidate violation categories ranked by signal strength), a `key_entities` dictionary capturing the platform name, any monetary amounts, and price-related wording, a `complexity` label (`simple`, `medium`, or `complex`), an integer `suggested_laws_k` (either 3, 4, or 5), an integer `suggested_cases_k` (always 0, for reasons discussed below), and a `reasoning_hints` list that carries the matched keywords forward for use by the reasoning engine.

The choice to use a rule-based approach here rather than a second LLM classifier is primarily driven by cost and predictability. An LLM-based intent classifier would add at minimum one extra inference call — roughly 7 seconds at current API latency — to every case processed, doubling the pre-reasoning pipeline overhead for no clear accuracy benefit given that the price-compliance domain has strong, consistent lexical signals. In practice, the vocabulary used in Chinese price-enforcement documents is remarkably stable: the same two or three dozen keywords appear repeatedly across violation types, and a keyword-matching approach captures the intent correctly for the vast majority of cases. The rare edge cases where novel phrasing defeats the rules are a genuine limitation, discussed further in §6.10.

The violation-type detection logic in `_detect_violation_types` covers six major categories:

**不明码标价 (failure to display marked price):** triggered when the description contains terms such as "未标明价格", "未明码标价", "无价格标示", or variations of "明码标价" combined with negation markers.

**政府定价违规 (government-pricing violation):** triggered by references to "政府定价", "政府指导价", or "超出政府定价" — all terms with precise regulatory definitions in Chinese price law that are unlikely to appear in non-relevant contexts.

**标价外加价 (surcharge above marked price):** detected via keywords like "另行收费", "额外收费", "加收", combined with the absence of explicit authorization language.

**误导性价格标示 (misleading price display):** this type uses a two-tier feature combination. A "strong feature" match — phrases like "虚假原价", "虚构原价", "误导消费者" — immediately flags the type. A "weak feature" match, where terms like "划线价", "参考价", or "促销价" appear alongside some form of comparison or contrast, counts only if at least two weak features co-occur, in order to reduce false positives from legitimate promotional descriptions.

**变相提高价格 (disguised price hike):** recognized via "变相涨价", "变相提价", "以降低质量或者数量等方式变相提高价格", and similar circumlocutions.

**哄抬价格 (price gouging):** triggered by "哄抬", "囤积居奇", "大幅提高价格" in conjunction with references to emergencies, shortages, or sudden demand surges.

The `complexity` label is assigned based on the number of violation type hints that fire and the presence of multiple entities or monetary figures in the description. A single clear violation type with no ambiguity produces `simple`; two or more competing hypotheses, or a description involving multiple products or transaction stages, produces `medium` or `complex`. The `suggested_laws_k` value is set to 3 for `simple`, 4 for `medium`, and 5 for `complex`.

The `suggested_cases_k` field warrants special attention. The current implementation unconditionally returns 0, and this is not a bug — it is a design commitment that mirrors the RAG evaluation decision described in Chapter 5. Because the 133-case knowledge base shares a non-trivial overlap with the 780-sample evaluation set (8 source PDF files appear in both), injecting case evidence during evaluation would risk same-source contamination. The IntentAnalyzer encodes that constraint directly, so downstream nodes receive a clear zero without any conditional logic.

---

## 6.3 Node 2 — AdaptiveRetriever

The second node reuses the `HybridRetriever` infrastructure described in Chapter 5 without modification. What the Agent layer adds is the ability to call that retriever with parameters that vary by case complexity rather than with a single fixed configuration. At call time, the AdaptiveRetriever passes `distance_threshold=0.15` and `min_k=2` as hard-coded constants — the same values used in the RAG evaluation path — while `laws_k` is taken from the IntentAnalyzer's `suggested_laws_k` output (3, 4, or 5 depending on case complexity). The `cases_k` parameter is taken from the IntentAnalyzer as well, which, as noted above, always returns 0.

The "adaptive" label refers specifically to this case-complexity-driven variation in `laws_k`. For a `simple` case, the retriever fetches at most 3 candidate articles after re-ranking and dynamic filtering; for a `complex` case it fetches up to 5. The practical effect is that the reasoning engine for complex cases receives a wider set of potentially relevant legal provisions, which can matter when the violation spans multiple statutes or when the applicable penalty article differs from the qualifying article. For simple cases, the narrower context keeps the prompt shorter and the reasoning more focused.

The internal mechanics of the retriever — vector search with BAAI/bge-small-zh-v1.5, BM25 search over the same 691-article law corpus, RRF fusion of the two ranked lists, CrossEncoder re-ranking with BAAI/bge-reranker-v2-m3, and distance-threshold-based dynamic Top-K — are identical to those described in §5.3 and §5.4 and are not repeated here. The only caller-visible difference is that the AdaptiveRetriever node packages the retriever's output into the agent state object so that subsequent nodes (Grader and ReasoningEngine) can consume it without knowing the underlying retrieval mechanism.

It is worth noting one subtle implication of the dynamic Top-K logic inside the retriever itself. Even when `laws_k=5` is requested by the IntentAnalyzer for a complex case, the retriever may return fewer articles if the mean distance of the top-3 results falls below 0.10, in which case it truncates the list to 2 highly confident hits. This means the final set of retrieved articles can be smaller than `suggested_laws_k` for cases where the top results are very closely matched — a behavior that slightly undermines the "complex cases get more context" premise, but also prevents the reasoning engine from being swamped with marginally relevant articles when the retrieval is already confident.

---

## 6.4 Node 3 — Grader

The Grader node, implemented in `src/agents/grader.py`, takes the retrieved document list from the AdaptiveRetriever and assigns each document a composite quality score before passing a filtered subset to the ReasoningEngine. The scoring formula is:

**final\_score = 0.6 · relevance + 0.3 · coverage + 0.1 · freshness**

Each component is computed as follows. The `relevance` sub-score uses the CrossEncoder's `rerank_score` when that field is present in the document metadata (which it is whenever the re-ranker was invoked), and falls back to `max(0, 1 − distance)` for documents that came through without re-ranking. This ensures that the grader's relevance judgment is aligned with the same cross-encoder signal that already shaped the retrieval ranking. The `coverage` sub-score measures the fraction of the IntentAnalyzer's `reasoning_hints` keywords that appear in the document's `content` field; if no keywords were extracted (i.e., the hints list is empty), coverage defaults to 0.5 as a neutral value. The `freshness` sub-score rewards recently amended statutes: a document with `metadata.year >= 2024` scores 1.0, one with year between 2020 and 2023 scores 0.8, and older documents score 0.6. When no year metadata is available, the grader assumes 2020 and assigns 0.8 accordingly.

After scoring, the Grader applies a threshold filter: documents with `final_score < 0.5` are discarded. If fewer than `min_keep=2` documents survive the filter, the fallback is to retain the top 2 by score regardless of the threshold — ensuring that the ReasoningEngine always receives at least two statutory anchors. This fallback is intended to protect against degenerate retrieval cases where the law corpus contains no strongly relevant article (e.g., for novel violation patterns not well-represented in the 691-article collection).

The weight allocation reflects the domain's priorities. Relevance carries the largest weight because an article that the cross-encoder judges as semantically close to the case description is likely to be the legally applicable one — the cross-encoder, having been trained on Chinese text-pair similarity, tends to surface the correct statute even when the case description uses colloquial rather than legal language. Coverage adds a complementary signal: an article that contains the same keywords the intent analyzer flagged is probably discussing the same violation category. Freshness is weighted lightly but not ignored, because Chinese price law has been amended and supplemented repeatedly since 2013, and older provisions may have been superseded or clarified; a 0.1 weight is enough to break ties in favor of more recent legislation without letting recency override semantic relevance.

---

## 6.5 Node 4 — ReasoningEngine

The ReasoningEngine, in `src/agents/reasoning_engine.py`, is where the language model call actually occurs. Its `_build_system_prompt` method dynamically assembles a system prompt that includes the graded law articles as context, the case description, the intent hints from Node 1, and an explicit chain-of-thought (CoT) scaffold. The structured CoT prompt is the component most directly inspired by the Wei et al. [1] findings on chain-of-thought reasoning: rather than asking the model to produce a classification and justification in free form, the prompt enumerates the exact steps it should follow and requests the output as a structured array called `reasoning_chain`.

The prompt has two branches, selected based on whether any case evidence was retrieved (i.e., whether `cases_k > 0`). The five-step branch — fact extraction → data verification → law matching → case reference → conclusion — is available when similar-case context is present in the prompt. Since `cases_k=0` in the current evaluation configuration, the four-step branch is always used: fact extraction → data verification → law matching → conclusion. The four-step prompt explicitly forbids the model from referring to past cases with phrases like "类似案例" or "参考案例", because injecting such references when no case evidence has been retrieved would constitute unsupported hallucination. This guard is a direct operational consequence of the anti-contamination decision taken at the IntentAnalyzer stage.

The output schema extends the Baseline JSON structure (which returned `is_violation`, `violation_type`, `legal_basis`, `reasoning`, and `cited_articles`) with an explicit `reasoning_chain` field: an ordered array of objects, each with a `step` label and a `content` string. The presence of this array is what allows the Reflector node to inspect the model's intermediate reasoning rather than just its final classification.

The model call uses `MaaSClient.call_model(..., model_key='qwen-8b')` with the same hyperparameters — `max_tokens: 2048`, `temperature: 0.7`, `top_p: 0.9` — as the Baseline and RAG routes. This is a deliberate choice for fair comparison: any difference in classification or reasoning quality between the Agent and the other two routes should be attributable to the pipeline architecture and the richer prompt structure, not to a different model or different decoding parameters.

In practice, we found that the structured CoT prompt tends to produce longer and more organized reasoning outputs than the Baseline prompt, which accounts for the Agent's higher reasoning-quality score (0.8931 versus 0.8415 for Baseline) despite the model being identical. The multi-step scaffold forces the model to address each analytical stage explicitly, which in turn produces reasoning text that scores higher on the heuristic evaluation metrics described in Chapter 7 — metrics that reward the presence of fact-verification language, law-citation patterns, and logical connectors.

---

## 6.6 Node 5 — Reflector

The Reflector, implemented in `src/agents/reflector.py`, is a zero-LLM validation layer that examines the ReasoningEngine's output for logical and structural inconsistencies. Its default `max_reflection` is 1, meaning it will trigger at most one re-reasoning attempt per case — a bound chosen to keep the latency impact predictable. If no critical rules fire, the Reflector simply passes the output downstream unchanged. If at least one critical rule fires and the retry budget has not been exhausted, the Reflector concatenates a structured feedback message and calls `ReasoningEngine.reason` again with the same inputs plus the feedback.

The critical rules fall into four main categories. The first addresses the most obvious contradiction: an output where `is_violation=True` but `violation_type` is set to "无违规" (no violation), or conversely where `is_violation=False` but `violation_type` names a specific violation category. These internal contradictions should not survive to the final output. The second rule checks that when a specific violation type is claimed, the reasoning chain contains at least one of the type-specific fact keywords that the IntentAnalyzer associated with that category — for example, a "误导性价格标示" verdict without any reference to comparison pricing, historical pricing, or promotional language in the reasoning chain is flagged as insufficiently supported. The third rule flags outputs where non-price-domain keywords dominate the reasoning chain without any price-related element, which can happen when the model misreads a dense penalty document and focuses on tangential facts. The fourth critical rule catches cases where the `reasoning_chain` field is missing or empty entirely, indicating a JSON parsing failure.

Warning-level rules — which are logged but do not trigger a retry — include cases where the `legal_basis` field is empty, where the cited articles do not match the claimed violation type (e.g., citing a government-pricing article in a failure-to-display case), or where the `reasoning_chain` array has only one step when the prompt requested four.

The Reflector's design is honest about its ceiling. Because it operates on heuristic rules rather than on external legal verification, it cannot guarantee that the reasoning it allows through is legally correct — only that it is internally consistent by its own criteria. A more powerful reflector might call an external knowledge base or a second model to verify factual claims, but that would add substantial latency and complexity. The current implementation is best understood as a structural validator, not a legal fact-checker.

The Reflexion paper [3] by Shinn et al. demonstrates that even simple self-evaluation with verbal feedback can meaningfully reduce error rates on reasoning tasks. The Reflector node operationalizes that idea in a domain-specific way: the feedback message it constructs is not generic ("your answer may be wrong") but names the specific rule that fired and what evidence would be needed to satisfy it, giving the model a concrete correction target for its re-run.

---

## 6.7 Node 6 — RemediationAdvisor

The final node, implemented in `src/agents/nodes/remediation_advisor.py`, is the component that most clearly distinguishes the Agent from the other two routes. Neither the Baseline nor the RAG pipeline produces any output beyond the classification and legal reasoning; the RemediationAdvisor adds a structured set of actionable next steps intended for the regulatory officer handling the case.

The node operates in two modes. For cases the IntentAnalyzer labeled as `simple`, the **fast** mode is used: a `REMEDIATION_TEMPLATES` dictionary maps each violation type to a pre-written set of remediation steps, which are returned without any model call. This is appropriate for simple cases because the remediation for a straightforward failure-to-display violation is essentially identical across instances — post the marked price visibly, within a specified timeframe, and submit evidence of compliance — and there is no benefit to generating that text from scratch with an LLM for each case. The fast mode ensures simple cases incur no additional model-call latency beyond the ReasoningEngine.

For `medium` and `complex` cases, the **detailed** mode issues an additional LLM call with a prompt that asks the model to generate a JSON object containing `remediation_steps` (an ordered list of specific corrective actions) and `compliance_checklist` (a set of verifiable criteria the business must satisfy to demonstrate compliance). The prompt is conditioned on the violation type, the legal basis identified by the ReasoningEngine, and any entity-specific details extracted by the IntentAnalyzer (such as the platform name or the monetary amounts involved). The `AgentCoordinator` defaults to detailed mode for all non-simple cases in the current evaluation run.

The actionability gain from the RemediationAdvisor is a qualitative benefit that is not fully captured by the quantitative metrics reported in §6.8. The heuristic evaluation framework described in Chapter 7 does not separately rate remediation quality against a legal standard, which is an acknowledged limitation. A rigorous assessment would require human expert review of the remediation outputs, which falls outside the scope of this thesis.

CRAG [5] and Self-RAG [4] both motivate the idea of post-retrieval refinement — generating outputs that are not just informative but corrected and actionable. The RemediationAdvisor can be seen as an application of that principle in a downstream, domain-specific form: rather than refining the retrieved context itself, it refines what the system does with its conclusion.

---

## 6.8 End-to-End Experimental Results

Table 6.1 presents the comparative results across all three routes on the full 780-sample evaluation set. The numbers are identical to those reported in Chapter 5's closing comparison, reproduced here for completeness since this chapter is responsible for explaining the Agent-specific figures.

**Table 6.1: Comparative evaluation results on the 780-sample test set**

| Route | Accuracy | Type Acc | F1 | Legal-basis avg | Reasoning avg | Latency (s) |
|---|---|---|---|---|---|---|
| Baseline | 89.35% | 73.68% | 91.47% | 0.8411 | 0.8415 | 7.02 |
| RAG | 89.85% | 74.94% | 92.01% | 0.7321 | 0.8685 | 7.77 |
| Agent | 86.98% | 71.52% | 89.79% | 0.7035 | 0.8931 | 37.62 |

The most positive result for the Agent is the reasoning-quality score of 0.8931 — the highest across all three routes, and 5.16 percentage points above the Baseline. This is the clearest evidence that the structured CoT prompt and the Reflector's consistency checking actually produce more thorough reasoning text. The heuristic scoring metrics that underlie the reasoning-quality average (described in detail in Chapter 7) reward the presence of fact-verification language, explicit law citation patterns, and multi-clause logical chains, all of which the four-step CoT scaffold encourages by design.

The classification accuracy result requires a candid reading. The Agent's binary accuracy of 86.98% is 2.37 percentage points below the Baseline and 2.87 percentage points below RAG — a meaningful regression, not a rounding artifact. The violation-type accuracy of 71.52% follows the same pattern. The most plausible explanation for this regression involves the Reflector's single retry mechanism. When the Reflector detects a critical inconsistency in an initially correct answer — for example, when the model correctly classifies a borderline compliant case as compliant but produces a reasoning chain that the Reflector judges as insufficiently grounded in price-domain evidence — the re-run can produce a different classification. For borderline compliant cases, where the model's initial confidence is not high, a retry is more likely to land on a different side of the decision boundary than to converge on the same answer. In other words, the safety mechanism that catches genuine errors also occasionally disrupts correct ones.

The latency cost is real and substantial. At 37.62 seconds per case, the Agent is approximately 5.4 times slower than the Baseline (7.02 s) and 4.8 times slower than RAG (7.77 s). The primary contributors are the ReasoningEngine's model call (which alone accounts for most of the Baseline latency), the RemediationAdvisor's detailed-mode LLM call for non-simple cases, and the occasional Reflector retry. Node-level latency figures are reported in §6.9 as pending values pending a re-run with the updated `agent_trace` instrumentation.

The legal-basis quality average continues the downward trend observed between Baseline and RAG: it falls from 0.8411 (Baseline) to 0.7321 (RAG) to 0.7035 (Agent). As argued in §5.8, this trend is most likely a measurement artifact rather than a substantive degradation. The legal-basis heuristic scoring rewards citations that match a preset keyword list; when the pipeline retrieves and re-grades specific statute articles, those articles may use slightly different phrasings or article numbering than the keywords in the scoring list, even when the retrieved content is legally more precise. The opposite trend on reasoning quality — improving steadily as the pipeline becomes richer — supports this interpretation: the same underlying output is becoming more legally detailed while scoring lower on a keyword-match proxy.

---

## 6.9 Case Study

The case study below is an illustrative trace drawn from realistic patterns in the evaluation dataset. Because the current `results/agent/improved_agent_full_eval-780__04-19/results.json` was produced before the `agent_trace` instrumentation was added to `scripts/run_agent_eval.py`, exact intermediate values for retrieval distances, grader scores, and per-node timings are not available from that run. The trace below uses realistic representative values consistent with the system's documented behavior; exact numeric fields from node-level outputs will be filled from the forthcoming re-run with `agent_trace` enabled, and the final thesis will replace these placeholders with the actual trace data.

**Case description (paraphrased from dataset patterns):** An e-commerce platform operator ran a promotional campaign in which multiple products were displayed with a "crossed-out original price" next to a lower "event price." An investigation found that the crossed-out price had never been the actual transaction price within the preceding 7-day period; it was a figure the operator had set specifically to create the appearance of a discount. The penalty document charges a violation of Article 13 of the Price Law and the relevant provision of the Administrative Regulations on Penalties for Price Violations.

**Node 1 — IntentAnalyzer output:**
- `violation_type_hints`: ["误导性价格标示", "不明码标价"] (two hints; misleading-display is the primary)
- `key_entities`: platform identified, promotional price and crossed-out price noted, "划线价" and "虚构原价" flagged as strong feature keywords
- `complexity`: "medium" (two competing hints, multiple price figures)
- `suggested_laws_k`: 4
- `suggested_cases_k`: 0
- `reasoning_hints`: ["划线价", "虚构原价", "促销价格", "实际成交价"]

**Node 2 — AdaptiveRetriever output:**  
With `laws_k=4`, the retriever runs vector + BM25 over the 691-article corpus and returns, after RRF fusion and CrossEncoder re-ranking, the following candidate articles (article names are illustrative of the expected retrieval pattern):
1. 价格法 第十四条 (prohibition on misleading price conduct)
2. 价格法 第十三条 (明码标价 requirement)
3. 禁止价格欺诈行为的规定 第三条 (definitions of price fraud including false original prices)
4. 价格违法行为行政处罚规定 第七条 (penalty provisions for misleading price display)

**Node 3 — Grader output:**  
All four candidates are scored. Representative scores (to be confirmed from `agent_trace`):

| Article | relevance | coverage | freshness | final_score |
|---|---|---|---|---|
| 价格法 第十四条 | ~0.87 | 0.75 | 0.8 | ~0.85 |
| 禁止价格欺诈行为的规定 第三条 | ~0.81 | 0.75 | 0.8 | ~0.81 |
| 价格违法行为行政处罚规定 第七条 | ~0.74 | 0.50 | 0.8 | ~0.69 |

All three exceed the `min_score=0.5` threshold and are retained. The fourth candidate falls below 0.5 and is dropped. Two retained articles (final_score ≥ 0.5) proceed to the ReasoningEngine.

**Node 4 — ReasoningEngine output (four-step CoT):**

```json
{
  "is_violation": true,
  "violation_type": "误导性价格标示",
  "reasoning_chain": [
    {
      "step": "fact_extraction",
      "content": "The operator displayed crossed-out prices alongside promotional prices across multiple product listings. The crossed-out figures were not the actual transaction prices during any recent reference period."
    },
    {
      "step": "data_verification",
      "content": "The case description confirms that the original price labels ('划线价') were set by the operator without basis in actual prior transactions, constituting a fabricated price reference. The promotional discount therefore misrepresents the savings offered."
    },
    {
      "step": "law_matching",
      "content": "Article 14 of the Price Law prohibits operators from using false or misleading price methods to deceive consumers. The Regulations on Prohibiting Price Fraud, Article 3, explicitly identifies fictitious original prices as a form of price fraud. Both provisions apply here."
    },
    {
      "step": "conclusion",
      "content": "The conduct constitutes misleading price display (误导性价格标示) under Article 14 of the Price Law, subject to administrative penalty under the applicable penalty regulations."
    }
  ],
  "legal_basis": "《价格法》第十四条；《禁止价格欺诈行为的规定》第三条",
  "cited_articles": ["价格法_十四", "禁止价格欺诈_三"]
}
```

**Node 5 — Reflector verdict:**  
The Reflector checks the output against all critical rules. The `is_violation=True` / `violation_type` consistency check passes. The keyword check for "误导性价格标示" finds "划线价", "虚构原价", and "实际成交价" referenced across the reasoning chain steps — the threshold is satisfied. No non-price-domain keywords are dominant. The `reasoning_chain` array contains exactly four populated steps. **Result: passed, no retry triggered.**

**Node 6 — RemediationAdvisor output (detailed mode for medium complexity):**

```json
{
  "remediation_steps": [
    "Immediately remove or correct all product listings that display crossed-out prices not supported by actual recent transaction records.",
    "Establish an internal pricing documentation procedure: any reference price displayed to consumers must correspond to an actual transaction price within the preceding 7-day period, or be clearly labeled as a manufacturer's suggested price.",
    "Submit a compliance rectification report to the supervising authority within the deadline specified in the penalty notice, including evidence of corrected listings."
  ],
  "compliance_checklist": [
    "All crossed-out prices traceable to documented prior transactions",
    "Promotional materials reviewed by compliance officer before publication",
    "Staff training records updated to include price-display regulations"
  ]
}
```

**Node-level latency breakdown:**

| Node | Avg latency (ms) |
|---|---|
| IntentAnalyzer | *pending from `metrics.node_timings_avg_ms`* |
| AdaptiveRetriever | *pending* |
| Grader | *pending* |
| ReasoningEngine | *pending (dominant)* |
| Reflector (including retry) | *pending* |
| RemediationAdvisor | *pending* |

*These figures will be back-filled from `results/agent/<new_run>/metrics.node_timings_avg_ms`. The total pipeline wall-clock of 37.62 s per case reported in §6.8 is the end-to-end average including model API queuing time, which is larger than the sum of node-local timings.*

---

## 6.10 Discussion and Limitations

The accuracy regression reported in §6.8 is real, and it should not be obscured by the reasoning-quality improvement. The Agent achieves its highest-ever reasoning score precisely because it does more: it runs a structured multi-step prompt, validates its own output, and when the validation fails, retries the reasoning. Doing more is not always better for binary classification accuracy. For cases where the model's first answer is correct but the Reflector raises a warning based on the surface features of the reasoning text rather than the underlying legal substance, the retry can move the system away from the right answer. This is the clearest limitation of heuristic-based validation: it can only see what it has been taught to look for.

The Reflector's rule set, while derived from genuine error patterns observed during development, is not exhaustive. It does not call any external price-law database to verify whether a cited article is still in force, does not cross-reference the penalty amount with the applicable penalty schedule, and does not consult any authority on whether a specific platform practice has been adjudicated previously. These are capabilities that a production regulatory tool might need; they are beyond the scope of this prototype.

The IntentAnalyzer's keyword-matching approach is another honest limitation. The classifier works well for the dominant violation types in the evaluation set — particularly the 221 不明码标价 and 117 政府定价违规 cases, which carry distinctive, unambiguous terminology. For rarer types like 变相提高价格 (6 cases in the evaluation set) or 哄抬价格 (1 case), the keyword rules were written from a small number of examples and may not generalize to novel phrasing. An LLM-based intent classifier would be more robust to paraphrase, at the cost of an additional inference call. This remains a natural direction for future development.

The RemediationAdvisor's output is assessed in this thesis only through the heuristic scoring framework that evaluates the structural quality of the JSON output rather than the legal soundness of the recommended steps. Whether the detailed-mode remediation advice is actually correct and sufficient from a regulatory standpoint has not been verified by a domain expert. We note this as a limitation explicitly: the high remediation-structure scores reported by the heuristic evaluator are a proxy for quality, not a guarantee of correctness.

Finally, the latency profile of 37.62 seconds per case, while acceptable for an asynchronous batch evaluation, would be challenging to deploy in a genuinely interactive investigator-facing interface. The primary driver is the sequence of two LLM calls (ReasoningEngine + RemediationAdvisor for non-simple cases), compounded by API queuing time. Reducing this to near-Baseline latency while preserving the structured output would require either local model deployment (eliminating network queuing) or a fast-path that uses the Baseline model's single call for simple cases and reserves the full Agent pipeline for complex ones — an architecture worth exploring in follow-on work.

---

## 6.11 Summary

This chapter has described the design, implementation, and experimental results of the six-node Agent pipeline. The pipeline's linear orchestration, rule-based intent analysis, complexity-adaptive retrieval, weighted grading, structured CoT reasoning, heuristic reflection, and template-or-LLM remediation generation collectively produce the system's most thorough reasoning outputs (0.8931 reasoning-quality average) and its only actionable remediation suggestions. The cost is a genuine accuracy regression relative to both the Baseline and RAG routes, a latency approximately five times larger than the Baseline, and a continued decline in the legal-basis heuristic score.

These trade-offs are not accidents of implementation — they reflect a fundamental tension between thoroughness and accuracy on a task where the model's initial judgment, conditioned on a strong prompt and good retrieval, is already quite capable. The structured multi-step pipeline adds analytical depth but also adds more opportunities for compounding errors.

Chapter 7 formalizes the evaluation methodology that has been applied informally across Chapters 4, 5, and 6. The metrics introduced there — binary accuracy, violation-type accuracy, F1, legal-basis quality, reasoning quality, and latency — are grounded in the heuristic scoring rules sketched in Chapters 4 and 5, and the formal treatment in Chapter 7 provides a unified framework that makes the cross-route comparisons defensible and reproducible.

---

**References (in-text citations)**

[1] Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., and Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, 35.

[2] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. *International Conference on Learning Representations*.

[3] Shinn, N., Cassano, F., Labash, B., Gopinath, A., Narasimhan, K., and Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. *Advances in Neural Information Processing Systems*, 36.

[4] Asai, A., Wu, Z., Wang, B., Sil, A., and Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique through self-reflection. *International Conference on Learning Representations*.

[5] Yan, S., Gu, J., Zhu, Y., and Ling, Z. (2024). Corrective retrieval augmented generation. *arXiv preprint arXiv:2401.15884*.

[6] Qwen Team. (2024). Qwen2.5 technical report. *arXiv preprint arXiv:2412.15115*.
