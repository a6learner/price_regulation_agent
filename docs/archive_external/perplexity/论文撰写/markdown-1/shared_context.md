# Shared Context for Thesis Writing

## Project Identity
- Author: Wang Jun (王俊), 22320225, 杭州电子科技大学圣光机学院, CS major
- Advisor: Qin Feiwei (秦飞巍)
- Thesis title (English): Research on Key Technologies for the Construction of Intelligent Agents for Price Compliance Supervision
- Language: English only (body text)
- Target AIGC detection rate: below 25%
- Graduation year: 2026

## Core Project Facts (authoritative)
- Domain: e-commerce price compliance supervision
- Three technical routes compared: **Baseline** (pure LLM inference) → **RAG** (retrieval-augmented) → **Agent** (6-node workflow)
- Base model (after pilot comparison of Qwen, MiniMax, Qwen-8B): **Qwen-8B** chosen for all downstream RAG/Agent work
- Dataset: `eval_dataset_v4_final.jsonl`, **780 samples, 489 violations + 291 compliant** (authoritative count per CLAUDE.md and README), derived from ~791 administrative penalty documents scraped from https://cfws.samr.gov.cn/index.html using EasySpider
- Law knowledge base: **691 law articles**
- Case base: **133 historical cases** — kept in system but excluded from formal evaluation (`cases_k=0`) to prevent same-source contamination
- RAG retrieval: vector + BM25 → RRF fusion → CrossEncoder re-ranking + dynamic filtering (distance threshold / min-k / mean-distance-based dynamic Top-K)
- Agent: 6 linear nodes
  1. IntentAnalyzer (rule-based, no LLM call)
  2. AdaptiveRetriever (reuses HybridRetriever)
  3. Grader (relevance 0.6 / coverage 0.3 / freshness 0.1)
  4. ReasoningEngine (structured CoT → JSON, 5-step chain: fact extraction → data verification → law matching → case reference → conclusion)
  5. Reflector (zero-cost heuristic validation + at most 1 re-reasoning retry)
  6. RemediationAdvisor (actionable remediation suggestions)

## Final Experimental Results (780 samples, authoritative per improved-1.md)
| Metric | Baseline | RAG | Agent |
|---|---|---|---|
| Binary accuracy | 89.35% | 89.85% | 86.98% |
| Violation-type accuracy | 73.68% | 74.94% | 71.52% |
| F1 | 91.47% | 92.01% | 89.79% |
| Legal-basis quality avg | 0.8411 | 0.7321 | 0.7035 |
| Reasoning quality avg | 0.8415 | 0.8685 | 0.8931 |
| Avg response time (s) | 7.02 | 7.77 | 37.62 |

### Violation-type distribution of the evaluation set (489 violations + 291 compliant)
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

### Key findings the thesis must convey
1. Classification accuracy is nearly flat across routes (within ~2.4 pp of each other) → Qwen-8B already has strong baseline capability
2. RAG gives small but consistent gains in Accuracy (+0.50 pp), Type-Accuracy (+1.26 pp) and F1 (+0.54 pp) over Baseline, while keeping latency only ~10% higher — the cost-effectiveness sweet spot
3. Agent trades classification accuracy for explainability: reasoning-quality avg 0.8931 (highest), and it is the only route producing remediation suggestions
4. Legal-basis avg surprisingly drops from Baseline 0.8411 → RAG 0.7321 → Agent 0.7035 — an honest observation to explain (likely because RAG/Agent rely on retrieved articles that sometimes mismatch the heuristic keyword set; the opposite trend on reasoning quality shows deeper reasoning is happening)
5. Agent latency is ~5x Baseline (37.62s vs 7.02s) — a real cost for the explainability gain
6. Compliant-case handling is a shared weak point across all routes
7. Honest technical notes to include: ~791 raw docs → 780 samples (no per-item exclusion list kept); cases_k=0 defended against same-source contamination (8 overlapping source_pdf identified between case base and eval set)

## Writing Style Rules (critical for AIGC-rate < 25%)
- Avoid templated transitions like "firstly… secondly… finally…", "in conclusion…", "it is worth noting that…", "this thesis proposes a novel…"
- Prefer varied paragraph lengths; occasionally use short standalone sentences for emphasis
- Do not use bullet lists when a short paragraph works; English theses read more naturally with flowing prose
- Use first-person plural sparingly ("we adopt", "we observe") in a scientific-report style — one of the more human signals
- Keep 1–2 honest limitation statements per chapter (e.g., "the heuristic scoring is not equivalent to legal-fact correctness")
- Cite concrete numbers not round claims (use the real numbers above)
- Avoid perfectly symmetric parallel structures (e.g., avoid always having three items per list)
- Include minor hedging phrases human authors use ("to some extent", "in practice", "as shown below", "this choice is primarily driven by")
- Use British or American English consistently — pick American

## Chapter Length Guidance
- Ch1 Introduction: ~3500 words
- Ch2 Theoretical Background: ~4000 words
- Ch3 Dataset Construction: ~3500 words
- Ch4 Baseline: ~3000 words
- Ch5 RAG: ~5000 words
- Ch6 Agent: ~5000 words
- Ch7 Metric System: ~2500 words
- Ch8 System & Prototype: ~2500 words
- Ch9 Conclusion: ~2000 words

## Section Numbering
Use 1., 1.1, 1.1.1 (engineering style, per university规范).
