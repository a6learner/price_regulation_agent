# Shared Context for Thesis Writing (v2 — 2026-04-20, all experiments complete)

## Project Identity
- Author: Wang Jun (王俊), 22320225, 杭州电子科技大学圣光机学院 (HDU Shengguang Joint College), CS major
- Advisor: Qin Feiwei (秦飞巍)
- Thesis title (English): Research on Key Technologies for the Construction of Intelligent Agents for Price Compliance Supervision
- Language: English only (body text)
- Target AIGC detection rate: below 25%
- Graduation year: 2026
- Format template: yc论文.docx (see `/home/user/workspace/converted/ycLun-Wen-6.md`)

## Core Project Facts (authoritative)
- Domain: e-commerce price compliance supervision
- Three technical routes compared: **Baseline** (pure LLM inference) → **RAG** (retrieval-augmented) → **Agent** (6-node workflow)
- Base model for RAG/Agent: **Qwen3-8B** (via 讯飞星辰 MaaS). Qwen3-8B chosen NOT because it was strongest on pilot — the 159-sample three-model pilot shows Qwen3.5-397B-A17B had the highest accuracy — but because it offers a much more favorable cost/latency profile for the downstream pipeline.
- Dataset: `price_regulation_agent/data/eval/eval_dataset_v4_final.jsonl`, **780 samples, 489 violations + 291 compliant**, derived from ~791 administrative penalty documents collected from https://cfws.samr.gov.cn/index.html using EasySpider (task 358.json).
- Law knowledge base: **691 articles** parsed article-by-article from DOCX files downloaded from https://flk.npc.gov.cn/index (National Laws and Regulations Database).
- Case base: **133 historical cases** — kept in system but excluded from formal evaluation (`cases_k=0`) because ~8 overlapping `source_pdf` were detected between the case base and the evaluation set; admitting them would cause same-source contamination.
- RAG retrieval: vector (BAAI/bge-small-zh-v1.5, 512-dim) + BM25 → RRF fusion → CrossEncoder re-ranking (BAAI/bge-reranker-v2-m3) + dynamic filtering (distance threshold 0.15, min_k=2, mean-distance-driven dynamic Top-K between 2 and laws_k).
- Agent: 6 linear nodes implemented in `src/agents/`:
  1. IntentAnalyzer (rule-based, no LLM call) — emits violation_type_hints, key_entities, complexity, suggested_laws_k; `suggested_cases_k` is hard-coded to 0.
  2. AdaptiveRetriever (reuses HybridRetriever with distance_threshold=0.15, min_k=2).
  3. Grader (relevance 0.6 + coverage 0.3 + freshness 0.1, min_score=0.5, fallback min_keep=2).
  4. ReasoningEngine (structured 4-step CoT → JSON; because cases_k=0, the "similar case" branch is disabled).
  5. Reflector (zero-cost heuristic validation + at most 1 re-reasoning retry, max_reflection=1).
  6. RemediationAdvisor (fast template mode for `simple` intent, detailed LLM mode for `medium`/`complex`).

## Main 780-sample Results (one authoritative table — from `results/compare/improved-1.md`)
| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) | Agent (Qwen3-8B) |
|---|---|---|---|
| Binary accuracy | 89.35% | 89.85% | 86.98% |
| Violation-type accuracy | 73.68% | 74.94% | 71.52% |
| F1 | 91.47% | 92.01% | 89.79% |
| Legal-basis quality avg | 0.8411 | 0.7321 | 0.7035 |
| Reasoning quality avg | 0.8415 | 0.8685 | 0.8931 |
| Avg response time (s) | 7.02 | 7.77 | 37.62 |

## Three-model baseline comparison — 159-sample subset (run_info says 780 but actual runs capped at 159; use 159 everywhere)
Directory: `results/baseline/baseline_v4_780_three_models__04-19/` (note: limit=159 per user's actual runs).

| Model | Success/Total | Accuracy | Precision | Recall | F1 | Type Acc | Legal avg | Reasoning avg | Avg time (s) |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-397B-A17B (`qwen`) | 774/780 | 93.15% | 95.39% | 93.62% | 94.50% | 79.07% | 0.9128 | 0.9033 | 5.41 |
| MiniMax-M2.5 (`minimax`) | 772/780 | 91.45% | 93.72% | 92.56% | 93.14% | 75.26% | 0.9097 | 0.8086 | 8.98 |
| Qwen3-8B (`qwen-8b`) | 773/780 | 89.91% | 92.37% | 91.62% | 91.99% | 73.74% | 0.8336 | 0.8431 | 7.17 |

## RAG ablation — first 154 samples of the evaluation set
Directory: `results/rag/rag_ablation_ablation_154__04-19__v4/`. Base model: Qwen3-8B.

| Variant | Accuracy | F1 | Type Acc | Avg time (s) |
|---|---|---|---|---|
| bm25_only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| semantic_only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| rrf | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| rrf_rerank | **0.9026** | **0.9470** | **0.6299** | 8.11 |

Ablation takeaway: the CrossEncoder re-ranker + RRF fusion drives the gain, not the extra wall-clock (all four variants within ~7.9–8.2s).

## Agent per-node timings — from `results/agent/agent_v4_780_node_timings__04-19/results.json`
Wall-clock for this run: 36.14 s/sample (success 777/780). Main 780 table in this thesis uses the 37.62 s figure from `improved-1.md` (a different run). Difference is noted as a footnote — do NOT try to mix them.

| Node | Avg (ms) | Share of pipeline |
|---|---|---|
| intent_analyzer | 0.11 | <0.01% |
| adaptive_retriever | 19167.81 | ~53% |
| grader | 0.08 | <0.01% |
| reasoning_engine | 11175.34 | ~31% |
| reflector | 453.58 | ~1.3% |
| remediation_advisor | 5342.60 | ~15% |
| **total_pipeline** | **36139.52 ms (~36.14 s)** | 100% |

## Violation-type distribution (eval_dataset_v4_final.jsonl)
| Type | Count |
|---|---|
| Compliant (negative) | 291 |
| Unpriced display (不明码标价) | 221 |
| Government-priced violation (政府定价违规) | 117 |
| Surcharge above marked price (标价外加价) | 73 |
| Misleading price display (误导性价格标示) | 49 |
| Unidentified sub-type | 14 |
| Disguised price hike (变相提高价格) | 6 |
| Fake price comparison (虚假价格比较) | 5 |
| Fake discount (虚假折扣) | 2 |
| Non-fulfilment of price commitment (不履行价格承诺) | 1 |
| Price gouging (哄抬价格) | 1 |

## Web prototype (Ch8) — IMPLEMENTED, no longer "proposed"
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS 4 + React Router 7 (NOT Streamlit — explicitly drop any old wording)
- Backend: FastAPI 0.115+ with sse-starlette for SSE streaming, aiosqlite for trace persistence
- Vector DB: ChromaDB 1.5+ shared with the RAG component
- Three user roles: consumer / regulator / merchant (different remediation prompts via `web/backend/services/role_prompt.py`)
- SSE event order: intent → retrieval → grading → reasoning → reflection → remediation → done
- Path: `price_regulation_agent/web/backend/main.py`, `web/frontend/src/`, `web/backend/traces.db`
- Default ports: frontend 5173 (Vite), backend 8000 (FastAPI); Vite proxies `/api/*` to the backend in dev

## Figure placeholders policy
Insert image placeholders using the pattern below (no real images yet — user will supply later). Example:

```
![Figure 3-1: EasySpider task graph for penalty-document collection](figures/ch3_easyspider_task.png)

Figure 3-1 EasySpider task graph for collecting penalty documents from cfws.samr.gov.cn.
```

Figure numbering: `Figure <chapter>-<n>`. Table numbering: `Table <chapter>-<n>`.

## Reference citation format (yc style)
- Inline: superscript numeric, e.g., `...has attracted wide attention^[4]^.`  (pandoc-friendly markdown that will render as bracketed super `[4]` in docx).
- Reference list entries at end of thesis: `[n] Authors. Title[J]. Journal, Year, Vol(Issue): Pages.` (matches yc论文.docx).
- Use the bibliography in `/home/user/workspace/thesis/references.md`. Every citation number must exist in that file.
- Do NOT invent citations. If a factual claim has no matching reference, re-word the sentence so it is a first-person methodological statement that does not need one.

## Writing style rules (critical — AIGC < 25%)
- Language: American English.
- Avoid: "firstly/secondly/finally", "in conclusion", "it is worth noting that", "this thesis proposes a novel", "a myriad of", "in today's era", "delve into".
- Vary paragraph length; mix 1-sentence and long paragraphs. Avoid three-item parallel lists everywhere.
- Use first-person plural sparingly ("we adopt", "we observe") — it is a more human signal than fully passive voice.
- Each chapter must contain ≥1 honest limitation sentence (e.g., "the heuristic legal-basis score is a proxy, not a ground-truth legal-correctness judgement").
- Cite concrete numbers from this context, not rounded or made-up ones.
- Use tables for data comparisons (B2, B-ablation, per-node timings, violation distribution, etc.).
- Insert image placeholders at natural "show, not tell" moments — especially: data collection workflow (Ch3), RAG pipeline (Ch5), Agent state diagram (Ch6), Web UI screenshots (Ch8).

## Section numbering convention
Use engineering style consistent with yc: `1 Introduction`, `1.1 Research background`, `1.1.1 ...`.

## Chapter length guidance
- Ch1 Introduction: ~3500 words
- Ch2 Theoretical Background: ~4000 words
- Ch3 Dataset Construction: ~3500 words
- Ch4 Baseline: ~3000 words
- Ch5 RAG: ~5000 words
- Ch6 Agent: ~5000 words
- Ch7 Metric System: ~2500 words
- Ch8 System & Prototype: ~2500 words
- Ch9 Conclusion: ~2000 words
