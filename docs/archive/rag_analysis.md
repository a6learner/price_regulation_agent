# RAG System Analysis

**Last Updated**: 2026-04-17

---

## Overview

The RAG (Retrieval-Augmented Generation) system was implemented and evaluated through a three-phase optimization process to improve price compliance analysis. This document summarizes key findings from comprehensive testing on 159 evaluation cases.

For detailed phase-by-phase breakdown and complete metrics, see [1].

---

## Key Performance Results

### Binary Classification Performance

| Metric | Baseline | RAG (Phase 3) | Change |
|--------|----------|---------------|--------|
| **Binary Accuracy** | 99.35% | **100.00%** | **+0.65%** ✅ |
| **Violation Type Accuracy** | 99.35% | 5.73% | -93.62% ❌ |

**Key Finding**: RAG achieved perfect binary classification (100% accuracy), completely eliminating false positives and false negatives [1].

### Quality Metrics Performance

| Metric | Baseline | RAG (Phase 3) | Change |
|--------|----------|---------------|--------|
| **Legal Basis Quality** | 89.48% | 82.23% | **-7.25%** ❌ |
| **Reasoning Quality** | 93.00% | 92.45% | -0.55% ≈ |

**Critical Issue**: Legal basis quality decreased despite retrieval augmentation. Root cause: retrieval noise leading to citation of all retrieved laws instead of most relevant ones [1].

### Performance Costs

| Metric | Baseline | RAG (Phase 3) | Change |
|--------|----------|---------------|--------|
| **Response Time** | 6.00s | 7.07s | +17.8% |
| **Token Usage** | 111,028 | 181,566 | +63.5% |

**Cost Analysis**: RAG increased token consumption by 63.5% (+500-600 tokens per query) and response time by 17.8% due to retrieval context expansion [1].

---

## Technical Architecture

### RAG Pipeline (Final Phase 3)

```
Query → BGE-small-zh-v1.5 Embedder
  ↓
Parallel Search:
  ├─ Semantic Search (Chroma, Top-9)
  └─ BM25 Lexical Search (691 laws, Top-9)
  ↓
RRF Fusion (k=60, weights: BM25=1.0, Semantic=0.7) → 9-12 candidates
  ↓
CrossEncoder Reranker (BGE-reranker-v2-m3)
  ↓
Distance Filtering (threshold=0.15) + Dynamic Top-K
  ↓
Final Results (2-3 laws + 5 cases) → Enhanced Prompt → LLM (Qwen3-8B)
```

**Key Components**:
- **Embedder**: BAAI/bge-small-zh-v1.5 (Chinese-optimized, 512-dim)
- **Reranker**: BAAI/bge-reranker-v2-m3 (cross-encoder, multilingual)
- **BM25**: rank_bm25.BM25Okapi (lexical matching)
- **Vector DB**: Chroma (691 law documents + 133 penalty cases)
- **Fusion**: Reciprocal Rank Fusion (k=60)

For complete technical stack details, see [1] Section "Technical Stack".

---

## Three-Phase Optimization Journey

### Phase 1: Distance Threshold + Dynamic Top-K

**Implementation**:
- Distance threshold filtering (0.15)
- Dynamic Top-K adjustment based on average distance
- Two-stage recall (recall_multiplier=3x)
- **Critical Issue**: Reranker disabled due to perceived hang bug

**Results**:
- Legal Basis: 89.48% → 78.34% (-11.14%) ❌
- Reasoning: 93.00% → 90.00% (-3.00%) ⚠️

**Analysis**: Disabling reranker caused significant quality degradation [1].

### Phase 2: + BM25 Hybrid Search + RRF Fusion

**New Techniques**:
- BM25Okapi for lexical matching on 691 law documents
- RRF fusion combining semantic and keyword signals
- Hybrid retrieval: semantic similarity + exact keyword matches

**Results**:
- Legal Basis: 78.34% → 79.56% (+1.22%) ✅
- Reasoning: 90.00% → 93.36% (+3.36%) ✅

**Analysis**: BM25 keyword matching improved recall, reasoning quality recovered to baseline level [1].

### Phase 3: + CrossEncoder Reranker (FINAL)

**New Techniques**:
- CrossEncoder reranker successfully enabled after diagnostic testing
- Two-stage reranking: Recall (BM25+Semantic) → Precision (CrossEncoder)
- Isolation tests confirmed reranker works correctly

**Results**:
- Legal Basis: 79.56% → 82.23% (+2.67%) ✅
- Reasoning: 93.36% → 92.45% (-0.91%) ≈
- Binary Accuracy: → **100.00%** ✅

**Analysis**: Reranker improved precision but still below baseline 89.48% target [1].

For detailed phase-by-phase comparison and metrics, see [1] Section "Three-Phase Optimization".

---

## Root Cause Analysis

### Why Did Legal Basis Quality Decrease?

**Hypothesis 1: Retrieval Noise**
- Retrieved 3 laws may include 1-2 low-relevance items
- Model tends to cite all retrieved laws instead of selecting most relevant
- Evidence: Violation Type Accuracy only 5.73% (vs Baseline 99.35%)

**Hypothesis 2: Prompt Design Issue**
- RAG prompt emphasizes "refer to following materials" but lacks "select most relevant"
- Model misled to cite all provided laws
- Evidence: Legal basis length increased but precision decreased

**Hypothesis 3: Evaluation Metric Limitations**
- Quality metrics based on keyword matching, may not accurately measure "law relevance"
- More law citations ≠ Higher quality
- Evidence: Reasoning length increased but quality not significantly improved

For complete root cause analysis, see [1] Section "Root Cause Analysis".

---

## Key Findings

### Successes ✅

1. **Perfect Binary Classification**: 100% accuracy, eliminated all FP/FN cases
2. **Hybrid Retrieval Effectiveness**: BM25+RRF improved reasoning quality by 3.36% in Phase 2
3. **Reranker Validation**: Diagnostic methodology confirmed CrossEncoder works correctly
4. **Stable Reasoning Quality**: Maintained 92-93% range comparable to baseline

### Challenges ❌

1. **Legal Basis Quality Gap**: 82.23% vs 89.48% baseline (-7.25%)
2. **Missed Target**: 82.23% vs 95% goal (-12.77%)
3. **Increased Costs**: +63.5% tokens, +17.8% response time
4. **Retrieval Noise**: More context does not guarantee better quality

---

## Improvement Recommendations

### Short-term Optimizations (Immediate)

1. **Optimize Prompt Template**: Emphasize "cite only most relevant 1-2 laws"
2. **Adjust Top-K Parameters**: Reduce laws_k from 3 to 2, cases_k from 5 to 3
3. **Increase Distance Threshold**: From 0.15 to 0.12 (stricter filtering)
4. **Add Reranker Score Filtering**: Set threshold=0.5 to remove low-confidence results

**Expected Gain**: +3-5% legal basis quality (82% → 85-87%)

For complete optimization roadmap, see [1] Section "Improvement Recommendations".

### Mid-term Optimizations (Requires Development)

1. **Multi-hop RAG**: First hop for laws, second hop for cases based on laws
2. **Query Expansion**: Extract key entities and behaviors to improve recall
3. **Fine-tune Reranker**: Domain-specific fine-tuning on price compliance data

### Long-term Redesign

1. **Agent Architecture**: Intent Analysis → Targeted Retrieval → Grading → Reasoning → Self-Reflection
2. **Better Evaluation Metrics**: GPT-4 scoring or human-annotated ground truth

---

## Thesis Narrative Recommendations

### Recommended Claims ✅

- "RAG achieved perfect binary accuracy (100%), eliminating all misclassifications"
- "Hybrid retrieval (BM25+RRF) effectively improved reasoning quality (+3.36%)"
- "CrossEncoder reranker brought precision improvement (+2.67%)"
- "Systematic diagnostic methodology: isolation tests confirmed reranker usability"
- "RAG challenges: retrieval noise vs quality tradeoff"

### Not Recommended Claims ❌

- ~~"RAG improved legal basis quality"~~ (actually decreased by 7.25%)
- ~~"Small model + RAG matches large model performance"~~ (quality metrics decreased)
- ~~"Three-phase optimization achieved 95% target"~~ (only reached 82.23%)

### Technical Contributions

1. Complete RAG pipeline: Embedding + BM25 + RRF + CrossEncoder
2. Systematic optimization methodology: three-phase progressive optimization with evaluation
3. Diagnostic approach: isolation testing for rapid component validation
4. Experimental transparency: complete documentation of each phase including failures

For complete thesis writing recommendations, see [1] Section "Thesis Narrative Recommendations".

---

## Next Steps Options

### Option 1: Continue RAG Refinement
- Implement short-term optimizations (1-2 days)
- Expected: 82% → 85-87% legal basis quality
- Risk: Low (parameter adjustments only)

### Option 2: Transition to Agent Architecture
- Implement intent analysis and grading workflow (2-3 days)
- Expected: More precise law selection → 88-92% legal basis quality
- Risk: Medium (requires LangGraph implementation)

### Option 3: Focus on Thesis Writing (Recommended)
- Use existing results to write experimental section (3-5 days)
- Chapters: Experimental Design, Baseline Results, RAG Implementation, Results Analysis, Discussion
- Highlights: Binary accuracy 100%, hybrid retrieval effectiveness, honest limitation discussion

For detailed next steps analysis, see [1] Section "Next Steps Recommendations".

---

## Data Leakage Check (Eval v4 vs RAG Cases Index)

### Problem

Current evaluation file `data/eval/eval_dataset_v4_final.jsonl` is built from a larger penalty-document source, while current RAG case index (`data/rag/cases_chunks.jsonl`) is built from an older 133-case source. This creates a potential same-source contamination risk.

### Key Findings

- **There is real overlap** between evaluation violation sources and indexed RAG cases: `8` overlapping source PDFs [2][3].
- Eval violation set contains `500` unique source PDFs, all matching the 791-case source pool [2][4].
- RAG case index contains `133` unique sources; `10` of them are in the 791 pool, and `8` directly overlap with eval violation sources [2][3][4].
- Overlap scale is **limited but non-zero**:
  - vs indexed RAG cases: `8/133 = 6.02%`
  - vs eval violation sources: `8/500 = 1.60%` [2]
- Current pipeline injects retrieved similar cases into system prompt (`cases_k=5`), so these overlaps can directly leak near-identical factual context into inference [5][6].

### Impact Assessment

- **Does this invalidate all RAG results?** No.
- **Can it inflate metrics on affected subset?** Yes, especially binary and type classification on those overlapped violation samples.
- **Risk level**:
  - Overall dataset-level risk: **medium-low** (small overlap ratio).
  - Experimental rigor risk: **medium** (thesis/benchmark requires strict separation).

### Recommended Fix Strategy

1. **Immediate (low-cost, defensible)**: Disable case retrieval during formal evaluation (`cases_k=0`), keep only law retrieval.
2. **Preferred for fair comparison**: Rebuild `cases_chunks` from 791 source after removing all eval-overlap source PDFs (by canonical `source_pdf` id).
3. **Report both tracks**:
   - `RAG-law-only` (no case contamination path)
   - `RAG-law+case-clean` (cleaned case index)
4. Keep current index only for development/debug, not for final reported benchmark.

### Decision Guidance

- If your goal is **fast, credible thesis results this week**: choose `cases_k=0` for official evaluation first.
- If your goal is **maximize final performance while keeping fairness**: rebuild cleaned `cases_chunks` and run full reevaluation.
- Do **not** directly reuse current 133-case index for final claims.

### References

[2] data/eval/eval_dataset_v4_final.jsonl - Eval v4 records with `source_pdf` and violation labels  
[3] data/rag/cases_chunks.jsonl - Current RAG case index sources (`case_id`)  
[4] data/cases/791处罚文书/files, data/cases/133处罚文书/files - Source document pools  
[5] src/rag/evaluator.py - Retrieval call includes cases (`cases_k=5`)  
[6] src/rag/prompt_template.py - Retrieved cases are injected into prompt context

---

## References

[1] results/rag/final_comparison_report.md - Complete three-phase RAG optimization evaluation report

---

**Document Status**: Consolidated summary from comprehensive RAG evaluation
**Evaluation Dataset**: 159 price compliance cases
**Model**: Qwen3-8B
**Evaluation Date**: 2026-03-16
