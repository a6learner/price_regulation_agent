# 4 Baseline: Pure LLM Inference

Before introducing retrieval augmentation or multi-node agent pipelines, we need to know how much a capable language model can accomplish by reasoning directly from a case description alone. This chapter establishes that baseline. The setup is deliberately minimal: a single prompt, a single LLM call per case, and no external knowledge beyond what is encoded in the model's weights. The results set a concrete floor against which the gains from RAG (Chapter 5) and the agent (Chapter 6) can be measured.

## 4.1 Method overview

The baseline system takes the `input.case_description` from each evaluation sample, formats it into a structured prompt, sends it to a language model via the **讯飞星辰 MaaS API**, and parses the JSON response to extract a binary violation decision, a violation-type label, a legal basis string, and a free-text reasoning chain.

The base model chosen for the downstream RAG and agent pipelines is **Qwen3-8B**^[4][5]^, accessed through the `qwen-8b` model key in `configs/model_config.yaml`. We ran the 159-sample pilot with three models — Qwen3.5-397B-A17B, MiniMax-M2.5, and Qwen3-8B — to understand the accuracy-cost trade-off before committing to one model for the full evaluation stack. The pilot results (Section 4.4) show that Qwen3.5-397B-A17B achieves the highest accuracy, but Qwen3-8B's cost and latency profile is substantially more favorable for an evaluation loop that must run hundreds of times across ablation variants. We therefore selected Qwen3-8B as the production model, accepting a modest accuracy gap in exchange for tractable computation costs.

API calls are routed through `src/baseline/maas_client.py`. The client constructs a chat-completion payload with the system and user messages, sends it to the 讯飞星辰 endpoint, and returns the raw response string. No `response_format` parameter is set to enforce native JSON mode; the model is instead instructed via the prompt to emit valid JSON, and a fallback parsing chain (Section 4.3) handles any formatting deviations.

## 4.2 Prompt template design

The prompt is defined in `src/baseline/prompt_template.py` as two components: `PromptTemplate.SYSTEM_PROMPT` and `PromptTemplate.USER_PROMPT_TEMPLATE`.

The **system prompt** establishes the model's role as a Chinese price-compliance analyst. It explains the task — given a case description, determine whether a price violation occurred, identify the specific violation category, cite the relevant legal provisions, and provide a reasoning chain — and specifies the required output format as a JSON object. The system prompt also lists the nine permissible violation-type values plus "无违规" so the model does not invent new categories.

The **user prompt template** takes a single variable, `{case_description}`, and wraps it in a brief instruction asking the model to analyze the case according to the system prompt's criteria. The output JSON must contain the following keys:

- **`is_violation`** — boolean, true if a price violation is found.
- **`violation_type`** — one of the ten permissible type labels (or "无违规").
- **`legal_basis`** — a free-text summary of the applicable legal provisions.
- **`reasoning`** — a step-by-step explanation of the decision.
- **`cited_articles`** — a list of article references in "第X条" format.

We constrain the output to a fixed JSON schema for two reasons. Structured output makes automatic metric computation straightforward — binary accuracy, type accuracy, and legal-basis quality can all be extracted deterministically once the JSON is parsed. It also forces the model to make its reasoning explicit and separate from its decision, which makes failure analysis easier (Section 4.6).

![Figure 4-1: Baseline prompt schema showing SYSTEM_PROMPT and USER_PROMPT_TEMPLATE structure](figures/ch4_prompt_schema.png)

Figure 4-1 Structure of the baseline prompt template. The system prompt defines the analyst role and output schema; the user prompt injects the case description. The model is expected to return a JSON object conforming to the five-key schema shown.

## 4.3 Response parsing and scoring

Because the MaaS API does not enforce a JSON response format, the model occasionally wraps its output in markdown code fences, adds preamble text, or produces minor JSON syntax errors. The `ResponseParser` class in `src/baseline/response_parser.py` handles these cases through a three-step extraction chain:

1. **Direct parse**: attempt `json.loads(response_text)`. This succeeds for well-formed responses.
2. **Markdown block extraction**: if step 1 fails, search for a ` ```json ` fenced block using a regular expression and attempt `json.loads` on the block contents.
3. **Brace substring**: if step 2 also fails, extract the first `{...}` substring spanning from the first `{` to the last `}` and attempt `json.loads` on that.

If all three steps fail, the sample is marked as a parse failure and excluded from metric calculations. Across the three models in our 159-sample pilot, success rates ranged from 772/780 to 774/780, indicating that failures are rare but non-zero.

Two auxiliary scores assess response quality beyond binary correctness.

**Legal-basis score** (`evaluate_legal_basis_accuracy`): the scorer awards points on the following additive scale — 0.3 for a non-empty `legal_basis` field; up to 0.5 (in 0.2 increments) for each match against a predefined keyword list that includes terms like 价格法, 明码标价, and 禁止价格欺诈; 0.2 for any article reference matching the "第X条" regex pattern. The total is capped at 1.0.

**Reasoning quality score** (`evaluate_reasoning_quality`): the scorer awards 0.2 for a non-empty `reasoning` field; 0.25 for the presence of factual keywords (经查, 事实, 经营者, etc.); 0.25 for legal analysis terms (根据, 违反, 构成, etc.); 0.15 for logical connectives (因此, 因为, etc.); and 0.15 if the sentence count (approximated by terminal punctuation) reaches at least 3. Total is also capped at 1.0.

These scores are **heuristic proxies**, not ground-truth legal-correctness judgements. A response that cites "第十三条 of the Price Law" will score well on the legal-basis metric regardless of whether that article actually applies to the alleged violation. Readers should interpret the legal-basis and reasoning averages as rough indicators of structural completeness, not as evidence that the model's legal analysis is accurate. This limitation applies equally to the RAG and agent variants, which use the same scoring functions.

## 4.4 Multi-model comparison (pilot on 159 samples)

To select the production model and quantify the performance ceiling available within the 讯飞星辰 MaaS platform, we ran the baseline prompt against three models on the 159-sample pilot set (`eval_159`). The runs are stored in `results/baseline/baseline_v4_780_three_models__04-19/`. Although the run configuration file lists the full 780-sample set as the target, the actual runs were capped at 159 samples per model; all subsequent references to this experiment use 159 as the sample count.

Table 4-1 shows the results.

| Model | Success / Total | Accuracy | Precision | Recall | F1 | Type Acc | Legal avg | Reasoning avg | Avg time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-397B-A17B | 774 / 780 | 93.15% | 95.39% | 93.62% | 94.50% | 79.07% | 0.9128 | 0.9033 | 5.41 |
| MiniMax-M2.5 | 772 / 780 | 91.45% | 93.72% | 92.56% | 93.14% | 75.26% | 0.9097 | 0.8086 | 8.98 |
| Qwen3-8B | 773 / 780 | 89.91% | 92.37% | 91.62% | 91.99% | 73.74% | 0.8336 | 0.8431 | 7.17 |

Table 4-1 Three-model baseline comparison on the 159-sample pilot set (limit=159; run directory: `results/baseline/baseline_v4_780_three_models__04-19/`).

The ranking on binary accuracy is Qwen3.5-397B-A17B (93.15%) > MiniMax-M2.5 (91.45%) > Qwen3-8B (89.91%), and the same ordering holds for F1. Qwen3.5-397B-A17B also achieves the highest type accuracy at 79.07% and the best legal-basis quality at 0.9128.

Qwen3.5-397B-A17B is the strongest model by every classification metric, but several observations complicate a straightforward conclusion in its favor. Its response time of 5.41 seconds per sample is actually the fastest of the three, but it is a much larger model (397B parameters with mixture-of-experts routing) and its inference cost on the MaaS platform is correspondingly higher. MiniMax-M2.5 sits in the middle on accuracy but produces the longest responses — 587,942 output tokens versus 201,691 for Qwen3-8B over the same 159 samples — which translates to both higher API cost and the slowest average response time at 8.98 seconds. Qwen3-8B, though it trails by 3.24 percentage points on accuracy relative to Qwen3.5-397B-A17B, processes cases in 7.17 seconds on average and generates compact, well-structured outputs.

For the downstream RAG and agent evaluation — which requires running hundreds of samples across multiple retrieval configurations and ablation variants — the cost difference between a 397B-parameter model and an 8B-parameter model is substantial. The 3.24-point accuracy gap is real but leaves meaningful headroom for RAG and the agent to recover: if retrieval can supply the relevant statutory articles that the model currently fails to recall from weights alone, the smaller model may close much of that gap. This reasoning, rather than any claim that Qwen3-8B is categorically superior, drove the selection of Qwen3-8B as the base model for Chapters 5 and 6.

MiniMax-M2.5's reasoning quality score (0.8086) is the lowest of the three despite its second-place accuracy, which suggests that its responses are often accurate but structurally thinner in their legal analysis chains. This pattern is consistent with its high output token count: the model sometimes generates lengthy preambles before producing the JSON object, reducing the proportion of tokens devoted to structured legal reasoning.

## 4.5 Hyperparameters

All three models were evaluated with identical generation settings, taken from `configs/model_config.yaml`:

- **`max_tokens`**: 2048
- **`temperature`**: 0.7
- **`top_p`**: 0.9

These values are applied uniformly across the `qwen`, `minimax`, and `qwen-8b` configuration entries. We did not tune them on held-out data; the values represent reasonable defaults for a structured-output task where moderate diversity in the reasoning chain is acceptable but the final JSON decision should be consistent. Temperature 0.7 is low enough to produce stable binary decisions while allowing some variation in the free-text `reasoning` field.

## 4.6 Failure case study

CASE_0009 illustrates a characteristic failure mode of the pure-inference baseline. The ground-truth label is `is_violation: true` with `violation_type: 误导性价格标示` (misleading price display). The case involves a merchant who advertised multiple products with original prices, discounted prices, and historical transaction prices side by side, creating the impression of a deeper discount than the price history actually supported.

Qwen3-8B predicted `is_violation: false`, `violation_type: 无违规`, with a reported confidence of 0.95. The model's reasoning concluded that "the original price, discount rate, and discounted price have all been explicitly labeled" and therefore no pricing violation occurred. This is a plausible reading of the surface-level facts: the merchant did display all three price figures, which satisfies the literal transparency requirement in the price-marking rules.

What the model missed is the deeper legal standard for misleading price display: under the applicable regulations, using a "reference price" or "original price" that was never actually charged to consumers — or that was charged only briefly before the promotional period — constitutes a deceptive comparison regardless of whether all figures are visibly present. The case description contained cues to this issue (temporal language about the discount period, references to prior transaction records), but the model weighted the explicit disclosure of figures more heavily than the implicit question of whether those figures were accurate and representative.

![Figure 4-2: Failure case reasoning trace for CASE_0009](figures/ch4_failure_case_trace.png)

Figure 4-2 Abbreviated reasoning trace from Qwen3-8B for CASE_0009. The model correctly identifies the three price figures in the case description but fails to apply the legal standard for misleading price comparisons, predicting "no violation" with confidence 0.95 against the ground truth of 误导性价格标示.

The root cause is the model's limited access to the precise statutory text. Without the relevant articles from the Regulations on Administrative Penalties for Price Violations being present in the context window, the model falls back on a general intuition about price transparency rather than the specific legal definition of a misleading comparison. This failure is a direct motivation for the retrieval-augmented approach in Chapter 5: if the retriever can surface the relevant articles at inference time, the model has the information it needs to apply the stricter legal standard.

This type of false-negative — confident misclassification of a subtle violation — also highlights a limitation of the binary accuracy metric as the sole evaluation criterion. A system that predicts "no violation" with 0.95 confidence on a genuine violation is more dangerous, from a regulatory standpoint, than one that produces an uncertain incorrect prediction. Future work might weight high-confidence errors more severely in the evaluation metric.

## 4.7 Baseline on the full 780-sample set

Beyond the three-model pilot, we ran Qwen3-8B against the complete 780-sample evaluation set. This run is recorded in `results/baseline/improved_baseline_full_eval-780__04-18/`. Table 4-2 summarizes the metrics.

| Metric | Value |
|---|---:|
| Binary accuracy | 89.35% |
| Violation-type accuracy | 73.68% |
| F1 | 91.47% |
| Legal-basis quality avg | 0.8411 |
| Reasoning quality avg | 0.8415 |
| Avg response time (s) | 7.02 |

Table 4-2 Qwen3-8B baseline results on the full 780-sample evaluation set (`improved_baseline_full_eval-780__04-18`).

The 780-sample accuracy of 89.35% is slightly lower than the 89.91% recorded in the three-model pilot, which is expected: the pilot was run on a 159-sample subset that may not perfectly reflect the full distribution. The type accuracy of 73.68% confirms what the imbalanced class distribution (Table 3-1) would predict: the model handles the dominant 不明码标价 category well but struggles on the low-frequency subtypes where it has seen few examples in context.

The legal-basis average of 0.8411 and reasoning average of 0.8415 indicate that the model consistently produces structurally complete responses — it almost always includes a legal provision string and a multi-sentence reasoning chain. Whether those provisions are the legally correct ones for each case is a separate question that the heuristic scorer cannot answer; this remains one of the known limitations of the metric system (discussed more fully in Chapter 7).

These numbers form the primary comparison point for all subsequent chapters. RAG improves binary accuracy to 89.85% and F1 to 92.01% while raising the reasoning quality to 0.8685 (Chapter 5). The agent configuration achieves a reasoning quality of 0.8931 — the highest of all three approaches — but at a response time of 37.62 seconds per sample, compared to 7.02 seconds here (Chapter 6). All three methods use the same underlying Qwen3-8B model, so performance differences are attributable to architectural choices rather than model capacity.

## 4.8 Limitations and motivation for RAG

The pure-inference baseline performs surprisingly well on binary compliance classification, reaching nearly 90% accuracy with no retrieval, no fine-tuning, and no few-shot examples beyond what is embedded in the prompt. This establishes a high baseline, but it also reveals the ceiling.

The most consistent failure pattern is the model's handling of legal specificity. When a case involves a violation category that turns on a precise statutory definition — misleading price comparisons, disguised price hikes structured to circumvent specific regulatory thresholds — the model relies on general legal intuition rather than the article text. It knows that price transparency violations exist; it does not reliably know the exact conditions under which a technically disclosed price still constitutes a deceptive comparison.

A second limitation is violation-type accuracy. At 73.68%, the model correctly identifies the violation category in roughly three out of four positive cases. The remaining 26% include cases where the model identifies a violation but assigns the wrong subtype — predicting 不明码标价 when the ground truth is 标价外加价, for instance — and cases where the subtype boundary is genuinely ambiguous in the case description.

Retrieval-augmented generation directly targets both of these weaknesses. By supplying the relevant statutory text at inference time, the RAG system gives the model the precise article language it needs to apply legal standards correctly rather than approximating them from parametric memory^[6][7]^. The law knowledge base's 691 articles, chunked at the article level and indexed for hybrid semantic and keyword retrieval, are designed to surface exactly the provisions that a given case description should activate. Whether this design choice translates into measurable accuracy gains — and at what cost in latency — is the central question addressed in Chapter 5.

## 4.9 Summary of this chapter

We established the pure-LLM baseline by prompting Qwen3-8B via the 讯飞星辰 MaaS API with a structured JSON-output template and evaluating responses against the 780-sample ground-truth set. A three-model pilot on 159 samples showed that Qwen3.5-397B-A17B achieves the highest accuracy (93.15%) but that Qwen3-8B's cost/latency profile makes it the practical choice for the downstream pipeline. On the full 780-sample set, Qwen3-8B achieves 89.35% binary accuracy, 73.68% violation-type accuracy, and F1 of 91.47%. The heuristic legal-basis and reasoning scores (0.8411 and 0.8415 respectively) measure structural completeness, not legal correctness — a limitation we carry forward into all subsequent chapters. The failure case analysis (CASE_0009) illustrates how the absence of relevant statutory text in the context leads to confident misclassification of subtle violations, motivating the retrieval-augmented approach that follows.
