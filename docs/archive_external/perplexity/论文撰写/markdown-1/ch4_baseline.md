# 4 Baseline: Direct LLM Inference

## 4.1 Design Rationale

Before layering retrieval or multi-node orchestration onto a language model, it is important to know exactly how much work the language model alone can do. This is not a rhetorical point — it has real methodological weight. If the base model already performs strongly, then any gain from RAG or an agentic pipeline must be measured against a competitive starting point, not a deliberately weakened one. Conversely, if the baseline collapses, we would not know whether improvements from later routes come from retrieval, orchestration, or simply from the model receiving a better prompt. The baseline in this chapter exists precisely to separate those contributions.

To be clear about what the baseline is not meant to demonstrate: it is not a study of zero-shot weakness, and no fine-tuning has been applied. The model receives the same task description in every query, via a stable prompt template, under fixed hyperparameters. The goal is to characterize the ceiling that pure in-context reasoning can reach when given a carefully written instruction set. That ceiling turns out to be higher than one might expect — which is itself a substantive finding, and one that shapes how we interpret the comparisons in Chapters 5 and 6.

The choice of a pure-LLM baseline also enforces a clean ablation logic across the three technical routes compared in this thesis. Route 1 (Baseline) provides no external knowledge beyond what is encoded in model weights. Route 2 (RAG) adds retrieved law articles. Route 3 (Agent) adds retrieved knowledge plus a six-node reasoning workflow. Holding everything else constant and varying only these components lets the experiments isolate, at least approximately, the marginal effect of retrieval and orchestration on price-compliance classification.

## 4.2 Prompt Design

The prompt structure is defined in `src/baseline/prompt_template.py`, which contains two components: `PromptTemplate.SYSTEM_PROMPT` and `USER_PROMPT_TEMPLATE`. The system prompt establishes role framing — the model is asked to act as a professional price-compliance expert operating within the Chinese regulatory context, with particular familiarity with the Price Law of the People's Republic of China (《价格法》) and related administrative penalty regulations. This framing is not decorative. There is reasonable empirical evidence that role prompting shapes the output distribution in ways that help surface domain-specific vocabulary and citation patterns [1].

The user prompt template receives the case description as its primary input and asks the model to return a single JSON object with the following required fields: `is_violation` (boolean), `violation_type` (string), `legal_basis` (free-text citation of the applicable law), `reasoning` (the model's chain-of-thought analysis), `cited_articles` (list of specific article references), and `confidence` (a self-reported probability). The JSON structure was chosen because downstream parsing and scoring depend on extractable fields; asking for free prose would make automated evaluation impractical across 780 samples.

One design tradeoff worth acknowledging honestly is that the system uses prompt-level format constraints rather than a strict JSON-mode API call. Modern LLM providers increasingly expose a `response_format` parameter that forces the model to emit valid JSON [2][3]. The Xunfei Xingchen MaaS client used in this codebase (`src/baseline/maas_client.py`) does not expose such a parameter in the version integrated here. This means the prompt must carry the full burden of enforcing structure: the system prompt explicitly instructs the model not to include any text outside the JSON object and to follow the field definitions exactly. In practice, the model complies most of the time, but JSON extraction still requires a fallback heuristic pipeline described in Section 4.4.

The decision to include `confidence` as a required output field was deliberate. A model that returns `is_violation=false` with `confidence=0.95` while being factually wrong is making a qualitatively different kind of error than one that hedges with `confidence=0.55`. High-confidence errors are the most operationally dangerous in a compliance context, and the failure case analyzed in Section 4.7 is precisely of this type. In a real deployment scenario, a human reviewer working through a large queue of flagged cases would likely deprioritize high-confidence predictions — which means that a confident false negative risks bypassing review entirely, while a low-confidence prediction at least signals uncertainty and invites scrutiny.

Chain-of-thought prompting [4] informed the structure of the `reasoning` field. Rather than asking the model for a binary decision directly, the prompt asks it to articulate its reasoning process in the `reasoning` field before committing to `is_violation`. This mirrors the insight from Wei et al. that eliciting intermediate steps improves final answer quality on reasoning tasks. Whether the model actually performs multi-step reasoning or merely produces the appearance of it is difficult to verify from outputs alone — a limitation worth keeping in mind when interpreting the reasoning-quality scores discussed in Section 4.4.

## 4.3 Inference Environment

All baseline inference runs use the Xunfei Xingchen MaaS client implemented in `src/baseline/maas_client.py`. Requests are sent in chat-completion format with the system and user prompts occupying their respective message roles. The model is asked to complete the conversation by generating the JSON analysis object.

The hyperparameters are drawn from `configs/model_config.yaml` and are kept identical across all three models tested in the pilot comparison. Specifically: `max_tokens = 2048`, `temperature = 0.7`, `top_p = 0.9`. These values apply uniformly to the `qwen`, `minimax`, and `qwen-8b` entries in the configuration file. The temperature of 0.7 sits in a moderate range — low enough to keep outputs reasonably stable across runs, but not so low that the model degenerates into repetitive phrasing. A temperature of zero was considered and rejected on the grounds that it would make repeated evaluation calls fully deterministic but would also suppress the model's ability to vary phrasing in the reasoning field, which the lexical-quality scores in Section 4.4 are sensitive to.

No system-level batching is used. Each of the 780 evaluation samples is sent as a separate API call. The average latency reported in Section 4.6 is the mean wall-clock time per call, including network round-trip but measured on a single sequential evaluation run. Sequential evaluation was chosen over parallelism in order to avoid rate-limit throttling and to produce a latency figure that reflects realistic single-query usage rather than a throughput-optimized deployment. At 7.02 seconds per query on average, the baseline is substantially faster than the Agent route (37.62 seconds), a comparison that becomes relevant when discussing operational trade-offs in Chapter 7.

## 4.4 Response Parser and Heuristic Scoring

The response parser lives in `src/baseline/response_parser.py`. Because the MaaS client does not enforce JSON mode, the model's output occasionally wraps the JSON object in prose, markdown fences, or additional commentary. The extraction strategy applies three steps in sequence: first, attempt `json.loads` directly on the raw response string; if that fails, search for a markdown-fenced code block delimited by ` ```json ` and attempt to parse its contents; if that also fails, use a regex to locate the first `{...}` substring and parse it. This cascade handles the most common deviation patterns observed in pilot testing. Responses that remain unparseable after all three steps are logged as parse failures and excluded from aggregate metrics.

Once a valid JSON object is extracted, two heuristic scoring functions evaluate the quality of the model's legal reasoning, independently of whether the binary classification is correct.

`evaluate_legal_basis_accuracy` scores the `legal_basis` field. It awards +0.3 if the field is non-empty, +0.2 for each keyword hit from a predefined list that includes 价格法, 明码标价, and 禁止价格欺诈 (capped at a total of +0.5 from keywords), and +0.2 if the text contains a pattern matching 第X条 (i.e., an explicit article reference in Chinese legal citation format). The total is clipped at 1.0. The maximum achievable score requires non-empty text, at least three keyword hits, and an explicit article reference.

`evaluate_reasoning_quality` scores the `reasoning` field. It awards +0.2 for a non-empty field, +0.25 if the text contains fact-reporting keywords such as 经查, 事实, or 经营者, +0.25 for legal-analysis terms such as 根据, 违反, or 构成, +0.15 for logical connectives such as 因此 or 因为, and +0.15 if the count of sentence-terminating punctuation marks (。? !) reaches at least three. The total is again clipped at 1.0.

These scores should not be mistaken for ground-truth correctness checks. They are lexical proxies — they measure whether the model's output looks like legally-grounded reasoning by checking for vocabulary patterns that competent legal analysis tends to contain. A model could, in principle, achieve a high reasoning score by producing superficially well-structured text that is nonetheless legally incorrect in its conclusions. The heuristics cannot detect this failure mode. This limitation is stated clearly here and is carried through the interpretation of results in Section 4.6 and in the cross-route comparison of Chapter 7.

An optional component in `violation_type_config.py` enables smart matching for the `violation_type` field, supporting synonym sets, multi-label classification (where multiple violation categories apply to the same case), and hypernym matching (where, for example, a prediction of 价格欺诈 could be credited as a partial match for 误导性价格标示). This matching logic is used in computing the violation-type accuracy metric reported in Section 4.6.

## 4.5 Multi-Model Comparison Plan and Model Selection

The pilot comparison evaluates three models available through the Xunfei Xingchen MaaS platform — referred to in the codebase as `qwen`, `minimax`, and `qwen-8b` — under identical prompts and hyperparameters on the evaluation dataset `eval_dataset_v4_final.jsonl` (780 samples). The intent is to select one base model for all downstream RAG and Agent experiments, so that any performance differences between routes cannot be attributed to a change in base model.

There is an important caveat about the current state of results. Only the Qwen-8B run (`results/baseline/improved_baseline_full_eval-780__04-18/qwen-8b_results.json`) is confirmed to have used the v4 780-sample evaluation set with the current evaluation format. The existing result files for Qwen and MiniMax come from earlier evaluation runs that used different dataset versions or output schemas and cannot be directly compared with the Qwen-8B numbers. A fresh three-model evaluation run on the same dataset is planned and can be reproduced with the following command:

```bash
cd price_regulation_agent
python scripts/run_baseline_eval.py \
    --models qwen,minimax,qwen-8b \
    --eval-path data/eval/eval_dataset_v4_final.jsonl \
    --results-dir results/baseline \
    --note v4_780_three_models
```

The table below presents the current state of the comparison. Qwen-8B numbers are definitive; the other two entries remain pending re-run.

| Model | Accuracy | F1 | Legal-basis avg | Reasoning avg | Avg latency (s) |
|---|---|---|---|---|---|
| Qwen | *pending re-run* | *pending* | *pending* | *pending* | *pending* |
| MiniMax | *pending re-run* | *pending* | *pending* | *pending* | *pending* |
| Qwen-8B | 89.35% | 91.47% | 0.8411 | 0.8415 | 7.02 |

*Two-model results will be back-filled from the forthcoming run output directory `results/baseline/<run>/`.*

Despite the incomplete comparison table, Qwen-8B is fixed as the base model for all downstream experiments. This decision is primarily driven by the need to establish a stable experimental baseline before the three-model rerun completes. It also reflects a practical judgment: among the three candidates, Qwen-8B is the lightest in terms of parameter count while still delivering near-90% accuracy, which makes it a sensible choice for an experiment that prioritizes isolating the effect of retrieval and orchestration over maximizing raw model capacity. Fixing Qwen-8B now allows RAG and Agent experiments to proceed without waiting, and ensures that the cross-route comparison in Chapter 7 rests on a single consistent model. If the forthcoming rerun reveals that another model would have been a stronger choice, a sensitivity analysis can be appended; in practice, the near-90% accuracy already achieved by Qwen-8B leaves limited room for another model to dominate on binary classification alone.

## 4.6 Qwen-8B Results on the 780-Sample Set

On the full 780-sample evaluation set (`eval_dataset_v4_final.jsonl`, 489 violations and 291 compliant cases), Qwen-8B achieves a binary accuracy of **89.35%** and an F1 score of **91.47%**. The violation-type accuracy — measuring whether the predicted violation category matches the ground-truth label — is **73.68%**. The legal-basis quality average is **0.8411** and the reasoning quality average is **0.8415**. The mean wall-clock response time per sample is **7.02 seconds**.

The binary accuracy figure is the most important single number in this chapter. At 89.35%, the baseline is not a weak starting point that RAG and Agent components will dramatically improve upon. It is already a strong classifier, and this shapes what can realistically be claimed for the downstream routes. The practical implication is that RAG and Agent improvements in Chapter 5 and 6 must be understood primarily as gains in reasoning quality, legal citation depth, and explainability — not as large jumps in classification accuracy. The overall classification accuracy spread across all three routes is in fact less than 2.4 percentage points, a point we return to in Chapter 7.

The violation-type accuracy of 73.68% is meaningfully lower than binary accuracy, which is expected. Correctly determining that a price-compliance violation occurred is an easier task than correctly categorizing the type of violation, particularly given the distribution of the evaluation set. The majority class — 不明码标价 (unpriced display violations) — accounts for 221 of the 489 violation samples, while categories like 虚假折扣 (fake discount) and 哄抬价格 (price gouging) each have only one or two examples. A model that performs well on the dominant category but struggles with rare ones will produce a type-accuracy noticeably below its binary accuracy.

The legal-basis average of 0.8411 represents the baseline's peak performance on that heuristic metric across all three routes — RAG (0.7321) and Agent (0.7035) both score lower. This seemingly counterintuitive result has a plausible explanation that is developed further in Chapter 7: RAG and Agent responses incorporate retrieved law articles into their outputs, but those retrieved articles do not always overlap with the keyword set used by `evaluate_legal_basis_accuracy`. When the model generates a legal citation from its parametric knowledge in the baseline condition, it tends to use the canonical terms (价格法, 明码标价) that the heuristic scores highly. When retrieval injects a different article from the knowledge base, the model may cite it accurately but use phrasing the heuristic does not reward. This is a known limitation of lexical scoring in a domain where multiple legally valid formulations exist.

## 4.7 Failure Case Analysis

The failure case below comes from the Qwen-8B evaluation on `CASE_0009`, drawn from `results/baseline/improved_baseline_full_eval-780__04-18/qwen-8b_results.json`.

- **Ground truth:** `is_violation: true`, `violation_type: 误导性价格标示` (misleading price display — the case involves a multi-product promotion where the "original price" used in discount comparisons did not reflect the actual prior transaction price)
- **Predicted:** `is_violation: false`, `violation_type: 无违规`, `confidence: 0.95`
- **Model reasoning (excerpt):** "原价、折扣率、折后价均已被明确标注，消费者可以清晰获取价格信息，不构成误导性价格标示。" (The original price, discount rate, and discounted price were all clearly labeled; consumers could clearly access price information; this does not constitute misleading price display.)

Several things are worth unpacking here. The model's reasoning is internally coherent and, on a surface reading, legally plausible. The Price Law and the Administrative Penalty Regulations do require that prices be clearly labeled, and the model correctly identifies that the labeling format was present. What the model fails to check is whether the "original price" itself is genuine — specifically, whether it corresponds to the actual transaction price from a preceding period, as required under the Provisions on Prohibition of Price Fraud (《禁止价格欺诈行为的规定》). The ground truth violation is precisely that the "original price" was inflated, making the stated discount misleading even though all three numbers were displayed.

This failure mode has a clear structure: the model can read and evaluate labels but cannot cross-check whether the values those labels carry are truthful. Doing so would require access to historical pricing records or at minimum to regulatory guidance that defines what constitutes a valid reference price. Neither is available from the model's parametric knowledge alone. This is exactly the motivation for introducing external legal-knowledge retrieval in Chapter 5 — if the relevant provisions of 《禁止价格欺诈行为的规定》 are retrieved and injected into the context at inference time, the model has the textual basis to recognize that the statutory definition of 原价 includes a temporal validity condition that the merchant violated. The high confidence (0.95) attached to this incorrect prediction makes the error operationally serious: a compliance-assistance system that is 95% confident in a false negative gives the downstream human reviewer no signal that the case warrants closer inspection.

This case is not isolated. The 误导性价格标示 category accounts for 49 samples in the evaluation set, and this type of reference-price manipulation is among the more legally subtle violations in the dataset. The baseline's violation-type accuracy of 73.68% is pulled down in part by exactly these cases — ones where correct classification requires not just recognizing the structural features of a promotion but also reasoning about whether the numerical values satisfy statutory definitions that depend on external context.

## 4.8 Summary and Transition

The baseline establishes that Qwen-8B, under a carefully constructed prompt and fixed inference settings, reaches 89.35% binary accuracy and a 91.47% F1 on a 780-sample evaluation set drawn from real administrative penalty documents. The heuristic legal-basis and reasoning scores are both above 0.84. These are genuine results, and they set a competitive ceiling for what retrieval and orchestration can additionally accomplish in classification terms. What the baseline does not provide is the capacity to ground its reasoning in specific retrieved statutory text, which means it can confidently misclassify cases — as CASE_0009 illustrates — where the relevant legal distinction depends on facts or regulatory definitions not encoded in the model's weights. Chapter 5 introduces the RAG route precisely to address this gap, equipping the same base model with access to a knowledge base of 691 law article chunks and evaluating whether retrieval-augmented inference yields more reliable legal grounding and, to whatever degree remains possible, improved classification accuracy.

---

**Citations**

[1] Qwen Team. *Qwen2.5 Technical Report*. Alibaba Cloud, 2024.

[2] Zheng, L., et al. "Outlines: Guided Generation for Language Models." *arXiv preprint arXiv:2307.09702*, 2023.

[3] Xue, M., et al. "StructuredRAG: JSON Response Formatting with Large Language Models." *arXiv preprint*, 2024.

[4] Wei, J., et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." *Advances in Neural Information Processing Systems*, 2022.
