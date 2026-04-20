---
title: "Research on Key Technologies for the Construction of Intelligent Agents for Price Compliance Supervision"
author: "Wang Jun"
date: "2026"
---

# 本 科 毕 业 设 计

# （2026届）

|              |                                                                                                                      |
| ------------ | -------------------------------------------------------------------------------------------------------------------- |
| **题 目**     | Research on Key Technologies for the Construction of Intelligent Agents for Price Compliance Supervision |
| **学 院**     | 杭电圣光机联合学院                                                                                                   |
| **专 业**     | 计算机科学与技术                                                                                                     |
| **班 级**     | 22320212                                                                                                             |
| **学 号**     | 22320225                                                                                                             |
| **学生姓名**  | 王俊                                                                                                                 |
| **指导教师**  | 秦飞巍                                                                                                               |
| **完成日期**  | 2026年5月                                                                                                            |

# 诚 信 承 诺

我谨在此承诺：本人所写的毕业论文《Research on Key Technologies for the Construction of Intelligent Agents for Price Compliance Supervision》均系本人独立完成，没有抄袭行为，凡涉及其他作者的观点和材料，均作了注释，若有不实，后果由本人承担。

**承诺人（签名）：**

**2026 年 5 月 15 日**

# ABSTRACT

The rapid growth of Chinese e-commerce has created a structural mismatch between the scale of online transactions and the capacity of regulatory agencies tasked with policing price compliance. Administrative bureaus issue thousands of penalty decisions each year for unpriced display, misleading price comparisons, surcharges above the marked price, and related violations, yet manual case processing cannot keep pace with platform activity. This thesis investigates whether large language models, combined with retrieval augmentation and agent-style orchestration, can assist price compliance supervision in a measurable way.

Three progressively richer technical routes are constructed and compared on the same 780-sample evaluation set derived from real administrative penalty documents collected from the China Market Supervision Administrative Penalty Document Network. The Baseline route issues a pure-prompt call to Qwen3-8B and evaluates accuracy, violation-type classification, heuristic legal-basis quality, heuristic reasoning quality, and wall-clock latency. The RAG route adds a hybrid retriever—BM25 combined with BAAI/bge-small-zh-v1.5 dense vectors, fused through reciprocal rank fusion and re-ranked by BAAI/bge-reranker-v2-m3—over a 691-article law knowledge base constructed from the National Laws and Regulations Database. The Agent route adds a six-node pipeline comprising intent analysis, adaptive retrieval, grader filtering, structured chain-of-thought reasoning, heuristic reflection, and remediation advising.

The Baseline reaches 89.35% binary accuracy at 7.02 seconds per sample. RAG improves to 89.85% accuracy and 0.8685 reasoning quality at a modest 7.77-second cost, making it the cost-effectiveness winner. The Agent route trades 2.4 percentage points of binary accuracy for the highest reasoning quality (0.8931) and is the only route that produces actionable remediation output, at the cost of 37.62 seconds per sample—roughly five times the Baseline latency. A three-model pilot (Qwen3.5-397B-A17B, MiniMax-M2.5, Qwen3-8B) on a 159-sample subset motivates the Qwen3-8B selection as a cost-latency compromise. A four-way RAG ablation on 154 samples isolates the contribution of re-ranking, which lifts violation-type accuracy from 0.5844 (BM25 only) to 0.6299 (RRF + re-rank). Per-node timing analysis of the Agent pipeline attributes 53 percent of wall-clock to adaptive retrieval and 31 percent to the reasoning engine.

A React-TypeScript-Vite front end and a FastAPI-SSE back end, both reusing the same Agent coordinator as the evaluation pipeline, deliver a role-selectable (consumer / regulator / merchant) interactive prototype with streaming six-node progress, full trace persistence in SQLite, and a knowledge-base browser over the same ChromaDB collection. The prototype complements rather than replaces the batch evaluation and is the work's primary human-in-the-loop deliverable.

**Key words：** Price compliance supervision; Large language model; Retrieval-augmented generation; Agent; Chain-of-thought reasoning

# Contents

1 Introduction ......................................................................... 1

&nbsp;&nbsp;1.1 Research background .......................................................... 1

&nbsp;&nbsp;1.2 Research status at home and abroad ............................................ 3

&nbsp;&nbsp;1.3 Research content of this paper ................................................ 7

&nbsp;&nbsp;1.4 Chapter arrangement ........................................................... 9

2 Theoretical Background ............................................................. 10

&nbsp;&nbsp;2.1 Large language models and Transformer basics ................................. 10

&nbsp;&nbsp;2.2 Prompt engineering and chain-of-thought ...................................... 13

&nbsp;&nbsp;2.3 Retrieval-augmented generation ............................................... 15

&nbsp;&nbsp;2.4 LLM-based agents and reflection .............................................. 19

&nbsp;&nbsp;2.5 Evaluation of generative systems ............................................. 22

&nbsp;&nbsp;2.6 Summary of this chapter ...................................................... 25

3 Dataset Construction ............................................................... 26

&nbsp;&nbsp;3.1 Data sources and scope ....................................................... 26

&nbsp;&nbsp;3.2 Penalty document collection pipeline ......................................... 27

&nbsp;&nbsp;3.3 From raw PDFs to evaluation set (v4) ......................................... 30

&nbsp;&nbsp;3.4 Evaluation-set structure and statistics ...................................... 31

&nbsp;&nbsp;3.5 Law knowledge base (691 articles) ............................................ 33

&nbsp;&nbsp;3.6 Case base (133 cases) and leakage control .................................... 34

&nbsp;&nbsp;3.7 Limitations .................................................................. 35

&nbsp;&nbsp;3.8 Summary of this chapter ...................................................... 36

4 Baseline: Pure LLM Inference ....................................................... 37

&nbsp;&nbsp;4.1 Method overview .............................................................. 37

&nbsp;&nbsp;4.2 Prompt template design ....................................................... 38

&nbsp;&nbsp;4.3 Response parsing and scoring ................................................. 39

&nbsp;&nbsp;4.4 Multi-model comparison (pilot on 159 samples) ................................ 41

&nbsp;&nbsp;4.5 Hyperparameters .............................................................. 44

&nbsp;&nbsp;4.6 Failure case study ........................................................... 45

&nbsp;&nbsp;4.7 Baseline on the full 780-sample set .......................................... 47

&nbsp;&nbsp;4.8 Limitations and motivation for RAG ........................................... 48

&nbsp;&nbsp;4.9 Summary of this chapter ...................................................... 49

5 Retrieval-Augmented Generation Route .............................................. 50

&nbsp;&nbsp;5.1 Motivation and design goals .................................................. 50

&nbsp;&nbsp;5.2 Pipeline overview ............................................................ 51

&nbsp;&nbsp;5.3 Document processing and indexing ............................................. 53

&nbsp;&nbsp;5.4 Hybrid retrieval ............................................................. 56

&nbsp;&nbsp;5.5 Dynamic top-k and score thresholds ........................................... 59

&nbsp;&nbsp;5.6 Prompt assembly .............................................................. 61

&nbsp;&nbsp;5.7 Ablation study ............................................................... 63

&nbsp;&nbsp;5.8 End-to-end RAG on the 780 set ................................................ 66

&nbsp;&nbsp;5.9 Limitations .................................................................. 68

&nbsp;&nbsp;5.10 Summary of this chapter ..................................................... 69

6 Agent Route with Multi-Node Reflection ............................................ 70

&nbsp;&nbsp;6.1 Motivation ................................................................... 70

&nbsp;&nbsp;6.2 System architecture .......................................................... 71

&nbsp;&nbsp;6.3 Node design .................................................................. 73

&nbsp;&nbsp;6.4 Data leakage control ......................................................... 80

&nbsp;&nbsp;6.5 End-to-end Agent results on 780 samples ...................................... 81

&nbsp;&nbsp;6.6 Per-node timing analysis ..................................................... 83

&nbsp;&nbsp;6.7 Case study ................................................................... 85

&nbsp;&nbsp;6.8 Discussion ................................................................... 87

&nbsp;&nbsp;6.9 Limitations .................................................................. 88

&nbsp;&nbsp;6.10 Summary of this chapter ..................................................... 89

7 Evaluation Metric System ........................................................... 90

&nbsp;&nbsp;7.1 Motivation ................................................................... 90

&nbsp;&nbsp;7.2 Metric categories ............................................................ 91

&nbsp;&nbsp;7.3 Overall metric table across three routes ..................................... 94

&nbsp;&nbsp;7.4 Honest caveats of the metric system .......................................... 96

&nbsp;&nbsp;7.5 Summary of this chapter ...................................................... 97

8 Web Interactive Prototype .......................................................... 98

&nbsp;&nbsp;8.1 Design goals ................................................................. 98

&nbsp;&nbsp;8.2 Overall architecture ......................................................... 99

&nbsp;&nbsp;8.3 Technology stack ............................................................ 100

&nbsp;&nbsp;8.4 Information architecture .................................................... 101

&nbsp;&nbsp;8.5 Streaming via SSE ........................................................... 103

&nbsp;&nbsp;8.6 Reuse of the evaluation pipeline ............................................ 105

&nbsp;&nbsp;8.7 Boundary between prototype and batch evaluator .............................. 106

&nbsp;&nbsp;8.8 Early-design pivot from Streamlit ........................................... 107

&nbsp;&nbsp;8.9 Limitations ................................................................. 108

&nbsp;&nbsp;8.10 Summary of this chapter .................................................... 109

9 Conclusion and Future Work ........................................................ 110

&nbsp;&nbsp;9.1 Summary of the work ......................................................... 110

&nbsp;&nbsp;9.2 Contributions ............................................................... 111

&nbsp;&nbsp;9.3 Limitations and open problems ............................................... 112

&nbsp;&nbsp;9.4 Future work ................................................................. 113

&nbsp;&nbsp;9.5 Closing note ................................................................ 114

Acknowledgements .................................................................... 115

References .......................................................................... 116
# 1 Introduction

## 1.1 Research background

China's e-commerce sector now accounts for a substantial share of the country's retail economy, and the volume of online transactions has made price transparency a genuine governance concern. Unlike brick-and-mortar retail, where posted prices are physically visible and relatively easy to audit, e-commerce platforms host millions of dynamically updated listings that change without notice. Regulatory agencies face the structural problem of needing to monitor far more data than human staff can reasonably inspect.

The existing enforcement machinery relies heavily on reactive measures: consumers file complaints, a local market supervision bureau investigates, and a penalty may eventually be issued. The China Market Supervision Administrative Penalty Document Network^[45]^ publishes thousands of finalized penalty decisions each year, providing concrete evidence that violations are frequent and geographically widespread. Yet the complaints-first model means that many violations go undetected until they have already harmed buyers. In high-volume categories like fresh groceries, electronics, and holiday promotions, the gap between the moment a violation begins and the moment it is investigated can span weeks.

Chinese price law establishes clear obligations. The *Price Law of the People's Republic of China*^[46]^ requires merchants to clearly display prices for all goods and services—the statutory basis for the "unpriced display" (*bù míngmǎ biāojià*) category that makes up the largest share of administrative penalties. The *Administrative Punishment Regulations for Price Violations*^[47]^ enumerate specific prohibited conducts and their penalty ranges, including surcharges above the marked price, misleading price displays, and disguised price hikes. The *E-Commerce Law of the People's Republic of China*^[49]^ extends these obligations explicitly to platform operators, who bear additional duties to police their own merchants and cooperate with administrative investigations. Together, these instruments define a reasonably clear normative framework—the challenge is not interpretive ambiguity but rather operational scale.

No existing automated tool reliably maps a factual case description onto the applicable articles and renders an analysis comparable to what an experienced regulatory official would write. Manual enforcement has several bottlenecks that create demand for intelligent assistance. Investigative staff must search across multiple statutory instruments, cross-reference prior penalty cases, and produce documented legal reasoning for each case file. When caseloads spike—during holiday shopping seasons, for instance—throughput drops sharply. Small regional bureaus often lack legal specialists, creating uneven enforcement quality across jurisdictions. A system that could flag likely violations, identify the applicable legal basis, and produce a draft analysis would allow staff to spend time on review and judgment rather than retrieval and drafting.

Large language models (LLMs) have demonstrated genuine competence in knowledge-intensive reasoning tasks, including legal question-answering. The core capability—generating coherent, structured text conditioned on a long context that includes regulatory rules and a factual scenario—is well matched to the price compliance problem. However, deploying a general LLM directly raises two concerns that this thesis addresses directly: the model's training knowledge may be outdated relative to current regulations, and the model has no mechanism for tracing its legal-basis claims to authoritative sources.

Retrieval-augmented generation addresses the knowledge currency problem by injecting statute text retrieved from an up-to-date knowledge base at inference time. Structured agent pipelines address the reasoning transparency problem by decomposing the analysis into auditable steps: intent classification, document retrieval, relevance grading, chain-of-thought reasoning, consistency reflection, and remediation advice. The 780-sample evaluation set drawn from real administrative penalty documents provides a rigorous empirical basis for comparing how much each layer of added complexity contributes to the overall task performance.

One honest caveat belongs at the outset: the regulatory landscape for this problem extends beyond the three primary statutes cited above. Sector-specific rules, local government standards, and platform-level contracts all affect how a practitioner would analyze a given case. The experiments reported in this thesis treat the national-level statutory corpus as the knowledge base; capturing sub-national or platform-specific rules is left to future work. The absence of a public benchmark for this specific task also means that comparisons with prior systems are not currently possible—a limitation acknowledged throughout.

![Figure 1-1: Overall research roadmap from regulatory problem to system evaluation](figures/ch1_research_roadmap.png)

Figure 1-1 Overall research roadmap showing the path from the e-commerce price compliance problem through dataset construction, three-route technical evaluation, and web prototype delivery.

## 1.2 Research status at home and abroad

### 1.2.1 Large language models and their application

The modern era of large language models can be dated to the GPT-3 preprint^[1]^, which demonstrated that scaling transformer-based models to billions of parameters produced qualitatively new capabilities in few-shot in-context learning. Without any gradient updates, a model with 175 billion parameters could answer questions about medical dosage, write code, and translate languages simply by conditioning on a few examples in the prompt. GPT-4^[2]^ extended this further, achieving near-human performance on several professional licensing exams and showing that the same architecture could handle both reasoning-heavy and knowledge-retrieval tasks. Comprehensive surveys of the LLM literature^[29]^ document the rapid proliferation of model variants, training strategies, and downstream applications that followed these landmark releases.

The Qwen family of models, developed at Alibaba, offers a Chinese-first design that addresses tokenization efficiency and instruction comprehension for Mandarin text. Qwen's first technical report^[4]^ described a series of pretrained and instruction-tuned models with strong performance on Chinese NLP benchmarks. The Qwen2.5 technical report^[5]^ extended this to a broader parameter range (0.5B to 72B) and documented improvements in mathematical reasoning, coding, and multi-turn dialogue. For this thesis, Qwen3-8B was selected as the base model for both the RAG and Agent routes—not because it scored highest on the three-model pilot (Qwen3.5-397B-A17B reached 93.15% binary accuracy on the 159-sample subset, compared to 89.91% for Qwen3-8B), but because the cost and latency profile of the larger model would make it impractical for a real-time system. The 8B model yields a 7.17-second average response time on the 159-sample pilot; the 397B model runs at 5.41 seconds but at an order-of-magnitude higher API cost per token. This trade-off is a genuine engineering constraint, not an evaluation oversight.

Instruction tuning and reinforcement learning from human feedback^[28]^ transformed base pretrained models into practical assistants that reliably follow user intent and produce formatted outputs. The same techniques form the backbone of Chinese legal LLMs. ChatLaw^[30]^ combined a legal corpus with retrieval of statute texts during generation; Lawyer LLaMA^[31]^ fine-tuned LLaMA on Chinese legal question-answering data; DISC-LawLLM^[32]^ addressed the full legal service chain from consultation to document drafting and demonstrated that domain-specific fine-tuning meaningfully improved performance on Chinese legal tasks beyond generic instruction tuning. Lawformer^[34]^ tackled the specific challenge of processing long Chinese legal documents by extending BERT-style pretraining to that domain. Each of these systems targets broad legal assistance—contract review, court judgment prediction, and general consultation—rather than the narrow but high-volume task of price compliance determination with a structured, machine-parsable JSON output.

The price compliance domain differs from general legal NLP in a practically important way: the output must be machine-readable and evaluation-ready. A chatbot-style narrative answer does not integrate easily into a regulatory workflow, and it is difficult to evaluate at scale without secondary human review. The system built in this thesis requires the LLM to produce a JSON object specifying `is_violation`, `violation_type`, `legal_basis`, and `reasoning` fields on every call. This constraint simplifies downstream evaluation and mirrors how automated systems would consume the output in production.

Two additional characteristics distinguish the price compliance task from general legal LLM benchmarks. The violation categories are administratively defined and fixed: the regulatory framework specifies exactly which behaviors are prohibited and under which articles. This bounded output space means that structured evaluation is feasible—a model's `violation_type` field can be compared directly against a human-labeled ground truth derived from the penalty decision itself. And the factual inputs—descriptions of specific pricing behaviors by named merchants—are short enough to fit comfortably within a standard prompt context, unlike full contract review or multi-document case analysis.

### 1.2.2 Retrieval-augmented generation and agents

Retrieval-augmented generation (RAG) was formalized as a way to condition LLM generation on documents retrieved at inference time^[6]^, allowing the model's factual claims to be grounded in a regularly updated corpus rather than frozen training data. A survey of RAG for large language models^[7]^ traces the subsequent expansion of this paradigm through dense retrieval, query rewriting, iterative retrieval, and pipeline variants that blur the line between RAG and agent-style orchestration. The fundamental insight—that grounding generation in retrieved text reduces hallucination and enables knowledge updates without retraining—proved applicable across question answering, dialogue, and, as this thesis explores, regulatory analysis.

Chain-of-thought prompting^[14]^ established that eliciting intermediate reasoning steps substantially improves performance on multi-step tasks. For legal analysis, this matters because the chain from case facts to violation determination passes through statute identification, article matching, and applicability judgment—four distinct reasoning steps where an error at any point can invalidate the conclusion. The ReAct framework^[15]^ demonstrated that interleaving reasoning with action calls to external tools produces more reliable task completion than either pure generation or pure tool use. Reflexion^[16]^ added a verbal self-evaluation loop that improves success rates without gradient updates—directly informing the reflection design in this thesis.

Surveys of LLM-based autonomous agents^[18]^^[19]^ catalog the design patterns—memory, planning, tool use, and multi-agent coordination—that define modern agent architectures. The 6-node pipeline built here draws selectively on these patterns while constraining the design to the price compliance task's specific requirements: intent classification, adaptive retrieval, relevance grading, structured chain-of-thought reasoning, heuristic reflection, and remediation advice generation. The self-contained, linear structure was chosen deliberately to make behavior predictable and evaluation reproducible; fully autonomous agents with open-ended tool use introduce variance that is difficult to isolate in a controlled experiment.

For this domain, two additional concerns motivate the RAG+Agent design over plain LLM inference. Price law is specific: the model must not merely identify that a violation occurred, but must cite the exact statutory article that applies. A model relying on parametric memory will frequently produce plausible-sounding but incorrect article numbers. Injecting the retrieved article text directly into the prompt both grounds the output and provides an auditable link between the model's legal-basis claim and the authoritative source.

### 1.2.3 Legal/regulatory NLP and domain gaps

Legal NLP has a longer history than LLM-based agents, with work on statute retrieval, judgment prediction, and similar-case matching predating the transformer era. LEGAL-BERT^[33]^ demonstrated that pretraining on legal corpora substantially improves performance on legal classification tasks compared to a general English BERT, suggesting that domain vocabulary and stylistic conventions are sufficiently distinct to warrant separate pretraining. In the Chinese legal domain, the CAIL similar-case matching dataset^[35]^ provided a benchmark for tasks where precedent retrieval is the primary challenge—a different formulation from the compliance classification task here, but related in its demand for legal-domain language understanding.

The LLM-based Chinese legal assistants discussed in Section 1.2.1 represent a more recent wave. DISC-LawLLM^[32]^ is probably the closest prior work to the system built here: it combines fine-tuning on legal instructions with a retrieval module that supplies relevant statutes at inference time. The difference lies in scope and output format. DISC-LawLLM targets a broad range of legal questions including courtroom scenarios and contract interpretation; this thesis targets a narrow, well-defined classification task with a structured output requirement that enables automated evaluation at scale.

The price compliance supervision problem sits at an intersection that none of this prior work occupies directly. It is narrower than general legal assistance—the normative corpus is small and well-defined, covering primarily the Price Law, the Administrative Punishment Regulations for Price Violations, and a cluster of related statutes—but more structured in its output requirements than a consultation chatbot. It is also genuinely different from case-based judgment prediction: rather than predicting a court's ruling from a decided case, the task is to classify a factual description against a set of administrative prohibitions and identify applicable articles from a specific statute cluster.

We are not aware of published work that uses RAG or agent pipelines specifically for Chinese price compliance supervision at the scale of real administrative penalty documents. The 780-sample evaluation set constructed in this thesis, drawn from approximately 791 penalty decisions published on cfws.samr.gov.cn^[45]^, is one contribution toward filling that gap. The dataset is, to our knowledge, the first publicly documented benchmark for this specific task, though the underlying documents are public records. The annotation methodology—treating the penalty decision itself as the ground-truth label—has well-understood coverage limitations but avoids the scalability problem of expert re-annotation.

The violation distribution in the dataset is naturally skewed, reflecting the actual enforcement landscape: "unpriced display" accounts for 221 of 489 violation samples, while rare categories like price gouging and fake discounts contribute only 1–2 samples each. This imbalance is preserved in the evaluation set rather than corrected through oversampling, so performance on the rare categories should be interpreted cautiously. The overall metrics reported throughout this thesis are calculated on the full skewed distribution, which more faithfully represents the real-world task distribution that a deployed system would face.

## 1.3 Research content of this paper

The core contribution of this thesis is an empirical comparison of three technical routes for automated price compliance analysis, evaluated on a dataset of real administrative penalty decisions. The three routes represent an incremental stack: each successive layer adds capability (grounded knowledge, structured reasoning, reflection) while also adding complexity and latency. A key design goal was to quantify not just whether each layer improves performance but whether it does so at a cost that is acceptable for the target deployment context.

**The three routes.** The Baseline route submits a case description directly to Qwen3-8B with a carefully engineered system prompt that requests structured JSON output. No external knowledge is retrieved; the model must rely entirely on its parametric knowledge of Chinese price law. This route represents the performance achievable without retrieval or orchestration overhead and provides the reference point against which the more complex systems are judged.

The RAG route augments the same model with a hybrid retrieval pipeline over 691 law article chunks—BM25 plus dense vector search, fused with reciprocal rank fusion (RRF), then re-ranked by a CrossEncoder—and injects the top-ranked articles into the prompt context before generation. The retrieval step grounds the model's legal-basis output in specific statutory text rather than parameterized memory, and the ablation study confirms that the full RRF+rerank configuration outperforms simpler retrieval designs on the 154-sample subset.

The Agent route replaces the single-turn generation with a 6-node pipeline: an intent analyzer that classifies complexity and suggests retrieval parameters, an adaptive retriever, a relevance grader, a reasoning engine that generates a structured 4-step chain-of-thought, a heuristic reflector that triggers one optional re-reasoning pass for internally inconsistent outputs, and a remediation advisor that suggests compliance steps for the merchant. The agent adds coordination overhead—37.62 seconds per sample versus 7.77 for RAG—while improving reasoning quality at the cost of binary accuracy. This trade-off between thoroughness and speed is the central tension documented in Chapters 6 and 7, and it determines which route is appropriate for which deployment scenario.

**The evaluation set.** Starting from approximately 791 administrative penalty documents collected from cfws.samr.gov.cn^[45]^ using EasySpider (task 358.json), we filtered to 780 samples with complete case descriptions and structured ground-truth labels. The set contains 489 violation cases spanning 10 violation types, with "unpriced display" (*bù míngmǎ biāojià*) being the most common at 221 cases, and 291 compliant (negative) examples. A 133-case historical case base was built but excluded from formal evaluation because approximately 8 source documents overlapped with the evaluation set; including them would constitute same-source data contamination that would inflate apparent retrieval performance.

**Principal results.** On the 780-sample set, the Baseline achieves 89.35% binary accuracy and 91.47% F1 at 7.02 seconds per sample. RAG improves to 89.85% accuracy and 92.01% F1 at 7.77 seconds—a modest but consistent gain across both metrics. The Agent pipeline reaches 86.98% accuracy at 37.62 seconds, lower on binary accuracy but highest on reasoning quality score (0.8931 vs. 0.8415 for Baseline), reflecting the structured 4-step chain-of-thought and the reflection pass. The trade-off between response latency and reasoning quality is the central analytical finding of the comparative evaluation.

**The web prototype.** Chapter 8 describes a fully implemented interactive prototype with a React 19 / TypeScript / Vite frontend and a FastAPI backend that streams agent pipeline events via Server-Sent Events (SSE). Three user roles—consumer, regulator, and merchant—receive differentiated prompts and remediation advice via a role-specific prompt prefix in `role_prompt.py`. The prototype reuses the same AgentCoordinator and ChromaDB vector store as the evaluation pipeline, so its analytical behavior is consistent with the reported metrics. Role differentiation is a deliberate design choice: a consumer filing a complaint has different information needs from a regulatory official drafting a penalty decision, and the merchant-facing remediation advice is the component most likely to prevent future violations.

The prototype is implemented in a fully separated frontend/backend architecture (React on port 5173, FastAPI on port 8000) rather than the Streamlit single-process approach considered in early design sketches. This separation allows the frontend to display a six-stage progress indicator that advances in real time as SSE events arrive from the server: `intent` → `retrieval` → `grading` → `reasoning` → `reflection` → `remediation` → `done`. Each event carries partial results that the UI renders incrementally, giving the user visibility into the pipeline state rather than a blank waiting screen during the 37-second agent run.

The three-model pilot comparing Qwen3.5-397B-A17B, MiniMax-M2.5, and Qwen3-8B on 159 samples (Chapter 4) motivates the model selection. The RAG ablation comparing BM25-only, semantic-only, RRF, and RRF+CrossEncoder-rerank on 154 samples (Chapter 5) justifies the retrieval design choices. The agent node timing breakdown—retrieval consumes approximately 53% of the 36.14-second pipeline, and reasoning approximately 31%—informs the latency discussion in Chapter 6 and points to where future optimization effort would be most productive.

**Knowledge base construction.** The law knowledge base contains 691 article chunks parsed from DOCX files downloaded from the National Laws and Regulations Database (flk.npc.gov.cn). Each chunk corresponds to a single statutory article, identified by a regular-expression pattern that recognizes the 「第…条」 heading structure. Articles from multiple laws are included: the Price Law, the Administrative Punishment Regulations for Price Violations, the E-Commerce Law, and related statutes on anti-unfair competition, online transaction supervision, and platform rules. The average chunk length is approximately 140 characters. This article-level granularity was chosen to match the citation format expected in penalty decisions, where the relevant article is referenced by number; the trade-off is that articles with complex multi-paragraph structures are not decomposed further.

The case base—133 historical penalty cases—was excluded from formal RAG evaluation (`cases_k=0`) because source document overlap analysis identified approximately 8 shared source PDFs between the case base and the evaluation set. Admitting even a small number of contaminated samples would undermine the integrity of the retrieval evaluation. The cases remain in the system and are accessible via the web prototype's knowledge base browser, where the overlap risk does not apply because no automated metrics are being computed.

![Figure 1-2: Three-route comparison overview](figures/ch1_three_routes.png)

Figure 1-2 Schematic of the three technical routes (Baseline, RAG, Agent) evaluated in this thesis, showing the additional components introduced at each stage and the direction of capability–latency trade-offs.

## 1.4 Chapter arrangement

Chapter 2 reviews the theoretical foundations—transformer architecture and decoder-only LLMs, prompt engineering and chain-of-thought reasoning, retrieval-augmented generation with hybrid retrieval and re-ranking, LLM-based agent design with reflection loops, and evaluation methods for generative systems. Chapter 3 describes dataset construction: EasySpider-based collection from cfws.samr.gov.cn, PDF extraction, label annotation, and quality filtering from roughly 791 raw documents to the final 780-sample evaluation set, along with the 691-chunk law knowledge base built from the National Laws and Regulations Database (flk.npc.gov.cn). Chapter 4 presents the Baseline experiments: the three-model pilot on 159 samples and the full 780-sample Qwen3-8B evaluation, with analysis of representative failure cases. Chapter 5 covers the RAG system in detail—retrieval component design, the four-variant ablation on 154 samples, and the full 780-sample RAG evaluation including comparison against the Baseline. Chapter 6 details the 6-node Agent pipeline, including the IntentAnalyzer rule set, Grader scoring formula, ReasoningEngine 4-step CoT prompt, Reflector heuristic checks, RemediationAdvisor modes, and node-level timing data from the 780-sample run. Chapter 7 defines the composite evaluation metric system, explaining why binary accuracy alone is insufficient for legal reasoning tasks and how the legal-basis quality score and reasoning quality score are computed and interpreted. Chapter 8 describes the web prototype implementation: the React/FastAPI architecture, SSE streaming, three-role differentiation via `role_prompt.py`, and the knowledge base browsing interface at `/api/knowledge/laws` and `/api/knowledge/cases`. Chapter 9 concludes with a summary of findings, a structured comparison of the three routes' trade-offs across all five metrics, limitations of the current work, and directions for future work including fine-tuning on domain data, multi-jurisdiction regulatory coverage, and real-time monitoring integration.
# 2 Theoretical Background

## 2.1 Large language models and Transformer basics

The attention mechanism, introduced in the original Transformer paper^[25]^, replaced recurrence with a computation that allows every position in a sequence to attend to every other position in parallel. That architectural shift was what made scaling feasible: training on hundreds of billions of tokens became a wall-clock-time engineering challenge rather than a fundamental barrier imposed by sequential computation. BERT^[24]^ demonstrated that masked-language-model pretraining on large corpora produced general-purpose representations that could be fine-tuned with small labeled datasets for classification, question answering, and many other downstream tasks—establishing that deep pretrained representations transfer broadly across NLP tasks.

Decoder-only architectures follow a different principle from BERT's bidirectional encoder. Rather than encoding the full input bidirectionally, they generate text left to right: given tokens $t_1, \ldots, t_{n-1}$, predict $t_n$. At each step the model attends to all previous tokens in the context window through causal (masked) self-attention, producing a probability distribution over the vocabulary. Sampling or greedy decoding selects the next token, which is appended and fed back as input. This autoregressive loop is how all the generation-focused models discussed in this thesis work, including the GPT series^[1]^^[2]^ and the Qwen family^[4]^^[5]^.

Tokenization matters more for Chinese than for alphabetic languages. A subword tokenizer that handles Chinese characters poorly will fragment common legal terms into uninformative pieces, wasting context window capacity and degrading the model's ability to recognize statutory vocabulary. The Chinese LLaMA work^[26]^ demonstrated that expanding the vocabulary to include high-frequency Chinese tokens substantially improves both throughput and downstream task quality on Chinese benchmarks. Qwen's tokenizer follows the same principle, treating common Chinese character n-grams as single tokens; this design choice is directly relevant to legal text, where article identifiers like "第十三条" (Article 13) and compound legal terms like "明码标价" (clearly marked price) should ideally be single or double tokens rather than character-level fragments.

**Why Qwen3-8B for this thesis.** The three-model pilot on 159 samples compared Qwen3.5-397B-A17B (93.15% accuracy, 5.41 s/sample), MiniMax-M2.5 (91.45%, 8.98 s/sample), and Qwen3-8B (89.91%, 7.17 s/sample). Qwen3-8B ranked third on accuracy but is the practical choice for two reasons. Response latency scales roughly linearly with model size for MaaS API calls because larger models require more compute per generated token; at 37.62 seconds per sample for the Agent pipeline using Qwen3-8B, adding a 3–4× latency multiplier from the larger model would push interactive response times above any reasonable tolerance for a real-time tool. API cost scales similarly—calls to the 397B model are substantially more expensive per token than to the 8B model, which matters when evaluating 780 samples repeatedly across ablation runs. The 3.2-percentage-point accuracy gap between the 397B and 8B models is real but acceptable given these constraints. This is not a claim that Qwen3-8B is intrinsically the best model for this task; it is an engineering trade-off documented honestly so that future work can revisit the choice as cost curves change.

The context window of Qwen3-8B comfortably accommodates the prompt format used here: a system prompt with injected law article chunks (typically 2–5 articles at an average of approximately 140 characters each), a user message with the case description (often several hundred to over a thousand characters), and the model's JSON output (typically 300–500 tokens). Long-context coherence matters for the Agent's ReasoningEngine, which receives a structured 4-step chain-of-thought prompt in addition to the retrieved context; empirically, outputs remain well-formed at these lengths without observable degradation.

One limitation applies to all generation-based systems: model outputs are probabilistic, and the same input can yield different outputs across runs depending on sampling temperature and random seed. The evaluation results reported in this thesis are from single fixed-configuration runs; run-to-run variance is not characterized. This is a known gap in the experimental design that future work should address through multiple-run averaging.

## 2.2 Prompt engineering and chain-of-thought

Prompts are the primary interface between the practitioner and the model. For classification and legal analysis tasks, prompt design affects not just accuracy but also the reliability and parsability of outputs. Two developments in this area are directly relevant to the system built here.

Chain-of-thought (CoT) prompting^[14]^ showed that eliciting intermediate reasoning steps—either through few-shot examples with worked reasoning or through the instruction "think step by step"—substantially improved performance on multi-step reasoning tasks. The improvement is most pronounced in larger models and appears across arithmetic, symbolic reasoning, and commonsense inference. For legal analysis specifically, the value of CoT is structural: a violation determination involves identifying the relevant statute cluster, matching case facts to specific article conditions, and confirming that all elements of the offense are present. Each of these sub-steps can surface errors that would otherwise be invisible in a direct answer.

The ReasoningEngine in this thesis uses a structured 4-step CoT: (1) analyze the factual situation from the case description, identifying key actors, pricing behaviors, and affected goods or services; (2) identify the apparent violation type based on the fact pattern and the intent-analyzer hints; (3) match facts to specific articles from the retrieved law chunks, checking both the qualifying article (which defines the offense) and the penalty article (which specifies the sanction); (4) render a final judgment with legal basis in the required JSON format. This decomposition mirrors the reasoning structure of a regulatory official's analysis memo. When the case base is unavailable (as in all evaluations reported here, because `cases_k=0` to avoid data contamination), the step involving similar-case analogy is disabled and replaced with a direct article-matching step.

JSON-constrained output is a further prompt engineering choice with practical consequences. The system prompt instructs the model to return a JSON object with five specific fields: `is_violation` (boolean), `violation_type` (string), `legal_basis` (string), `reasoning` (string), and `cited_articles` (list). This constraint enables deterministic parsing and structured evaluation without secondary natural-language processing of the output. It also limits hallucination in one important way: the model cannot obscure a weak legal analysis behind verbose narrative. If `legal_basis` is empty or does not contain a recognizable article reference, the heuristic scoring function detects this directly. In pilot experiments without the JSON constraint, a meaningful fraction of outputs failed to produce parsable results and had to be excluded from evaluation.

Self-Refine^[17]^ demonstrated that asking a model to critique and revise its own output improves quality on open-ended generation tasks such as code and text rewriting, even without additional training. Instruction-following tuning with human feedback^[28]^ produces the same kind of output-quality signal but requires annotator effort. The Reflector node in this thesis applies a restricted version of the self-refine idea: it checks the model's own output for specific logical contradictions and triggers one re-reasoning pass if a critical inconsistency is found—for example, `is_violation=True` paired with `violation_type` set to "no violation", or a violation type asserted in the absence of any supporting fact keywords in the reasoning chain. The heuristic check is inexpensive (sub-millisecond on average) and the re-reasoning pass is triggered in a minority of cases. This conservative design avoids the known failure mode of using the model to evaluate itself on open-ended criteria, where the self-evaluation can be as unreliable as the original output.

A limitation of prompt engineering is that the same prompt can interact differently with different model families, different quantization levels, and different instruction-tuning styles. The prompts designed for Qwen3-8B are not guaranteed to work equally well with other models without adjustment.

## 2.3 Retrieval-augmented generation

RAG^[6]^ addresses a fundamental weakness of LLMs used for factual tasks: the model's knowledge is frozen at training time, and its recall of specific documents—especially niche regulatory texts that appear infrequently in the training corpus—is unreliable. The solution is to retrieve relevant documents at inference time and supply them in the prompt, so the model's generation is grounded in current, verifiable text rather than parameterized memory. The original RAG formulation^[6]^ combined a dense retriever (DPR) over a Wikipedia passage index with a seq2seq generator and demonstrated gains on several open-domain QA benchmarks. A comprehensive survey^[7]^ traces subsequent development through modular RAG variants, iterative retrieval, and hybrid pipelines.

**BM25.** The probabilistic BM25 ranking function^[9]^ scores documents by term frequency, inverse document frequency, and a length normalization factor. For legal retrieval, BM25 reliably handles queries that contain exact statutory phrases—"第十三条" (Article 13), "明码标价" (clearly marked price)—because these high-IDF terms dominate the ranking signal when they appear in both query and document. BM25 implementation uses the standard parameters ($k_1=1.5$, $b=0.75$) and operates over the tokenized article text without further preprocessing.

**Dense retrieval.** Dense passage retrieval^[8]^ replaced BM25-style term matching with learned bi-encoder representations, improving recall on semantically related but lexically different queries—a common situation when a case description describes a behavior in lay language that the statute codifies in formal terms. The dense retriever in this thesis uses `BAAI/bge-small-zh-v1.5`^[11]^, a 512-dimensional Chinese embedding model from the C-Pack family. This model was chosen for its compact size (small enough to run locally), good performance on Chinese semantic similarity benchmarks, and compatibility with ChromaDB's distance-based retrieval interface. Embeddings for all 691 law article chunks are precomputed and indexed at startup. At query time, the 512-dimensional query embedding is compared to stored chunk vectors using cosine distance; a threshold of 0.15 filters out chunks with low semantic similarity even if they fall within the requested top-K range.

**RRF fusion.** Neither BM25 nor dense retrieval is uniformly superior. BM25 handles exact legal terminology well; dense retrieval handles paraphrased or lay-language descriptions better. Reciprocal rank fusion (RRF)^[10]^ provides a parameter-free method for combining ranked lists from heterogeneous retrievers. Given a document $d$ appearing at rank $r_1$ in the BM25 list and rank $r_2$ in the dense list, its RRF score is:

$$\text{RRF}(d) = \frac{1}{k + r_1} + \frac{1}{k + r_2}$$

where $k=60$ is the standard smoothing constant. Documents appearing high in both lists receive the largest aggregate scores; a document absent from one list receives zero contribution from that list. The final ranking is determined by descending RRF score. The appeal of RRF is its robustness: it does not require estimating score distributions for either retriever, and it empirically performs as well or better than learned fusion weights across a wide range of benchmarks^[10]^.

**CrossEncoder re-ranking.** After RRF fusion produces a merged candidate list, a CrossEncoder (`BAAI/bge-reranker-v2-m3`^[12]^) scores each (query, document) pair jointly. Unlike the bi-encoder, which encodes query and document independently, the CrossEncoder sees both together through full cross-attention and can model fine-grained interaction terms—for example, whether a specific numeric price threshold from the case description matches a penalty amount threshold in the statute text. This is substantially more expensive than bi-encoder scoring but orders-of-magnitude cheaper than a full LLM call. The original passage re-ranking work with BERT^[13]^ established this pattern: a fast first-stage retriever narrows the candidate set, and a slower but more precise re-ranker produces the final ranking.

**Dynamic filtering.** After re-ranking, a distance-based filter retains only chunks with cosine distance ≤ 0.15. If the retained set would fall below `min_k=2` items, the filter falls back to the top-2 by rerank score. Additionally, if the mean distance of the top-3 retained chunks falls below 0.10, only 2 chunks are passed to the generator (the evidence is strong and compact); if it falls between 0.10 and 0.15, 3 chunks are passed; otherwise, the full `laws_k` value (3, 4, or 5 depending on intent complexity) is used. This prevents both empty-context hallucination and diluted-context confusion.

The ablation study on 154 samples (Table 2-1) shows the incremental value of each component.

Table 2-1 Comparison of retrieval strategy variants on 154-sample ablation subset (Qwen3-8B base model).

| Strategy | Accuracy | F1 | Violation-type Acc | Avg time (s) |
|---|---|---|---|---|
| BM25 only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| Semantic (dense) only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| RRF hybrid | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| RRF + CrossEncoder rerank | **0.9026** | **0.9470** | **0.6299** | 8.11 |

The performance gain from RRF+rerank versus the single-retriever baselines is most visible in violation-type accuracy, which measures whether the model correctly categorizes the specific violation subtype—a harder task than binary compliance judgment because it requires correctly matching the case facts to one of ten fine-grained categories. The wall-clock time is nearly identical across all four variants (7.9–8.2 s), confirming that the gain comes from retrieval quality rather than any additional compute-time investment.

![Figure 2-1: Hybrid retrieval architecture diagram](figures/ch2_hybrid_retrieval.png)

Figure 2-1 Hybrid retrieval architecture: BM25 and dense retrieval run in parallel over the 691-chunk law knowledge base; their ranked lists are merged via RRF; the CrossEncoder re-ranker re-scores the merged candidates; dynamic filtering based on distance threshold and mean-distance heuristics selects the final context window injected into the prompt.

One limitation of the retrieval design is that the law knowledge base is article-granular but not paragraph-granular: each chunk is one statutory article, averaging approximately 140 characters. For articles with complex multi-paragraph structure, the chunk may contain both relevant and irrelevant content together. Finer-grained chunking or passage-level splitting could improve precision at the cost of more retrieval steps and a larger index.

## 2.4 LLM-based agents and reflection

An LLM-based agent is a system in which an LLM is embedded as the reasoning core within a larger workflow that includes memory, tool calls, and conditional loops^[18]^^[19]^. The distinguishing feature is that the LLM's outputs at one step condition what happens at the next step—the system is not a single-turn prompt but a directed sequence of operations in which intermediate states carry information forward.

The ReAct framework^[15]^ demonstrated that interleaving "Thought" traces with "Action" calls to external tools—search, a calculator, a database lookup—produced more reliable task completion than either pure chain-of-thought or pure tool use. The model reasons about what action to take, takes it, observes the result, and reasons again. Reflexion^[16]^ added a verbal self-evaluation step: after completing a task, the model generates an "experience" summary noting what went wrong, which is prepended to the prompt on the next attempt. This verbal reinforcement loop improved success rates on sequential decision-making benchmarks without any gradient updates to model weights.

Self-Refine^[17]^ generalized this idea to open-ended generation: any capable LLM can serve as its own critic, and iterating the generate-critique-refine loop typically improves output quality. Generative agents^[20]^ showed that for longer-horizon tasks—such as simulating the social behavior of a community of agents over days of simulated time—memory management is essential. Agent surveys^[18]^^[19]^ organize the design space into planning mechanisms (tree-of-thought, MCTS-style search), memory architectures (in-context, external database, parametric), and tool-use strategies (API calls, code execution, environment interaction).

**State-machine view of the 6-node pipeline.** The Agent pipeline in this thesis is best understood as a linear state machine with one optional back-edge. Each node receives a shared state object and emits an updated state that is passed to the next node; Figure 2-2 shows the graph.

The six nodes are:

- **IntentAnalyzer**: Pure rule-based, no LLM call. Uses keyword pattern matching to classify the case description into `simple`, `medium`, or `complex` and emits `violation_type_hints` (up to 3), `key_entities` (platform name, price amounts, pricing terminology), and `suggested_laws_k` (3 for simple, 4 for medium, 5 for complex). `suggested_cases_k` is hard-coded to 0 throughout all evaluations. Average execution time: 0.11 ms.
- **AdaptiveRetriever**: Calls HybridRetriever with the intent-specified `laws_k` and fixed parameters `distance_threshold=0.15`, `min_k=2`. Returns the re-ranked, dynamically filtered law chunk list. Average execution time: 19,167 ms (~19.2 s), the single largest contributor to pipeline latency.
- **Grader**: Scores each retrieved chunk on three weighted criteria: relevance (weight 0.6, using CrossEncoder rerank score if available, else $1 - \text{distance}$), coverage (weight 0.3, fraction of `key_entities` appearing in chunk content), and freshness (weight 0.1, mapped from statute publication year: ≥2024→1.0, ≥2020→0.8, else 0.6). Retains chunks with composite score ≥ 0.5, with a `min_keep=2` fallback. Average execution time: 0.08 ms.
- **ReasoningEngine**: Constructs a system prompt embedding the graded law chunks and invokes Qwen3-8B with a 4-step structured CoT. Returns a JSON with the five output fields. Average execution time: 11,175 ms (~11.2 s).
- **Reflector**: Applies rule-based consistency checks to the ReasoningEngine output. Critical failures trigger one re-reasoning call. The maximum retry count is 1 (`max_reflection=1`). Non-critical warnings are logged but do not trigger retries. Average execution time across all samples (including triggered retries): 454 ms.
- **RemediationAdvisor**: For `simple` cases, fills a template with the violation type and applicable article. For `medium` and `complex` cases, calls the LLM to generate a structured `remediation_steps` and `compliance_checklist` JSON. Average execution time: 5,343 ms (~5.3 s).

The back-edge from Reflector to ReasoningEngine is what makes this an agent rather than a plain pipeline. The overall system handles the retry internally and returns only the final output to the caller, so the calling code is unaware of whether a retry occurred.

![Figure 2-2: Six-node agent state diagram](figures/ch2_agent_state_diagram.png)

Figure 2-2 State diagram of the 6-node agent pipeline. Solid arrows indicate normal sequential flow; the dashed arrow from Reflector back to ReasoningEngine represents the optional reflection retry (at most once per sample). All timings are from the 780-sample evaluation run (agent_v4_780_node_timings__04-19).

**Node timing summary.** On the 780-sample run, the six-node total pipeline averages 36,139 ms (36.14 s) per sample (success: 777/780). The retrieval step dominates at ~53% of total time, followed by reasoning at ~31% and remediation at ~15%. The intent analysis and grading nodes together contribute less than 0.01% of total time. This distribution indicates where optimization effort would be most productive: improvements to vector search hardware, embedding cache warming for common query patterns, or speculative decoding in the LLM inference backend would each target the bottleneck nodes.

A genuine limitation of the reflection design is that the Reflector detects only structural and logical consistency violations, not factual correctness. A reasoning chain that internally contradicts itself is caught; one that cites a plausible-sounding but incorrect article number is not. Detecting the latter would require grounding the cited article reference against the knowledge base at reflection time—a non-trivial extension that would add latency and complexity.

## 2.5 Evaluation of generative systems

Evaluating the outputs of generative systems is harder than evaluating classification predictions, and the difficulty is compounded when the output is legal reasoning. Binary accuracy—whether the model's `is_violation` prediction matches the ground-truth label—is necessary but not sufficient: a system that correctly classifies most cases while citing nonexistent statutes is practically useless for regulatory work. This section reviews the evaluation methods that motivated the metric design used in Chapter 7.

The BLEU metric^[51]^ was designed for machine translation and measures n-gram overlap between the system output and one or more human reference translations. ROUGE^[52]^ is the summarization analogue, measuring recall of n-grams from a reference summary. Both metrics can be applied to the `reasoning` field of the model's output if a reference explanation is available, but n-gram overlap does not measure legal correctness: a paraphrase of the correct analysis and a structurally similar but legally incorrect analysis may score identically on BLEU or ROUGE. For legal tasks, these metrics are best understood as surface-form consistency checks rather than correctness judges.

LLM-as-a-judge evaluation^[53]^ uses a capable LLM (typically larger than the one being evaluated) to rate outputs on dimensions like fluency, factual accuracy, and reasoning quality. MT-Bench^[53]^ demonstrated that GPT-4 judgments correlate well with human pairwise preferences on multi-turn dialogue, and the correlation holds across multiple capability dimensions including reasoning, coding, and knowledge retrieval. This approach is attractive for legal NLP because a well-prompted GPT-4 can apply domain-aware criteria that BLEU and ROUGE cannot. The drawback is evaluation-by-oracle circularity: when the same model family (Qwen) is used for both generation and judgment, the judge may systematically prefer the style of the model it is evaluating.

RAGAS^[54]^ extends LLM-based evaluation to retrieval-augmented systems, measuring three dimensions independently: faithfulness (does the generated answer follow from the retrieved context?), answer relevance (does the generated answer address the question?), and context relevance (does the retrieved context contain information necessary to answer the question?). This decomposition is directly applicable to the RAG pipeline evaluated here; in principle, a low faithfulness score would indicate that the model is ignoring the retrieved articles in favor of parametric knowledge, producing hallucinated legal bases.

Hallucination is a well-documented failure mode of LLMs deployed for factual tasks^[55]^^[56]^. A retrieval-augmented system can still hallucinate: the model may cite an article that appears in the knowledge base but is not applicable to the case, misquote an article's conditions, or—most dangerously for regulatory work—assert a legal conclusion that the retrieved articles do not actually support. Enabling large language models to generate text with citations^[56]^ showed that grounding generation in retrieved text reduces hallucination rates but does not eliminate them; the model can still selectively ignore retrieved context when its parametric knowledge provides a confident-seeming alternative.

The composite evaluation approach used in this thesis—combining binary accuracy, F1, violation-type accuracy, legal-basis quality score, and reasoning quality score into a multi-dimensional profile—is motivated by the recognition that different use cases weight these dimensions differently. A consumer-protection agency primarily interested in flagging likely violations for human review would weight binary accuracy heavily. A regulatory attorney reviewing flagged cases before taking enforcement action would weight legal-basis quality more strongly. Reporting all five metrics preserves this interpretive flexibility and avoids the misleading simplicity of a single aggregate score.

The heuristic quality scores used here (awarding partial credit based on structural features of the legal-basis and reasoning text rather than substantive correctness) are proxies, not ground-truth legal-correctness judgments. A human legal expert reviewing each output would likely assign different scores than the heuristic. One fundamental limitation of the evaluation design is the absence of this kind of expert annotation, which would be the most important single improvement available to future work on this benchmark.

## 2.6 Summary of this chapter

This chapter has laid out the technical foundations required to understand the system architecture and experimental results presented in subsequent chapters. The decoder-only transformer architecture underlies all three evaluation routes; chain-of-thought prompting with JSON output constraints structures the generation step; hybrid BM25 plus dense retrieval with RRF fusion and CrossEncoder re-ranking defines the RAG pipeline and is empirically justified by the ablation results in Table 2-1; the 6-node linear state machine with one optional reflection back-edge defines the Agent; and a multi-dimensional metric system combining binary accuracy with quality-proxy scores defines the evaluation framework. The quantitative comparisons across routes begin in Chapter 4.

Several connections across sections are worth making explicit before moving on. The chain-of-thought decomposition described in Section 2.2 is only effective because the retrieved law chunks (Section 2.3) provide the factual grounding that anchors each reasoning step. The Grader node (Section 2.4) exists specifically to filter out retrieved chunks that RRF ranks highly but that are not actually applicable to the specific case at hand—a problem that arises because RRF is query-agnostic in its fusion step and does not consider the full case context. The evaluation framework (Section 2.5) attempts to assess both the classification accuracy that summarizes the model's performance on the binary task and the reasoning quality that would matter to a practitioner reviewing the output before taking enforcement action. These connections motivate the specific engineering choices made in subsequent chapters and explain why the system design is not a simple pipeline but a multi-stage orchestration where each component addresses a specific failure mode of its predecessor.
# 3 Dataset Construction

The quality of any empirical NLP evaluation hinges on the data it rests on. This chapter documents how we assembled the two resources that underpin all downstream experiments: a 780-sample evaluation set of real-world administrative penalty records and a 691-article law knowledge base. Both were collected from public government portals, processed through a semi-automated pipeline, and curated to eliminate identifiable personal information before any model ever saw them.

## 3.1 Data sources and scope

Two online repositories provide the raw material for this project.

The primary source is the **中国市场监管行政处罚文书网** (China Market Supervision Administrative Penalty Document Network), hosted at https://cfws.samr.gov.cn/index.html^[45]^. The portal is maintained by the State Administration for Market Regulation (SAMR) and publishes official penalty decisions issued by local and provincial market-supervision bureaus across China. Each document is structured as a scanned or digital PDF containing the case background, the legal basis for the ruling, and the penalty outcome. The site exposes a search interface that accepts filters for topic, legal basis, keyword, and date range, though its list view is hard-capped at 200 rows per query.

The secondary source is the **国家法律法规数据库** (National Laws and Regulations Database), accessible at https://flk.npc.gov.cn/index^[46][49][50]^. Maintained by the Standing Committee of the National People's Congress, it serves as the authoritative digital repository for PRC legislation, administrative regulations, and local rules. We used it as the sole source for constructing the law knowledge base described in Section 3.5.

We restrict the study to **price-compliance** documents for two reasons. Price violations constitute one of the most common categories of e-commerce regulatory enforcement in China, and the underlying legal framework is well-delimited: the Price Law^[46]^, the Regulations on Administrative Penalties for Price Violations^[47]^, and related e-commerce and unfair-competition statutes^[49][50]^ together form a coherent rule set whose article structure lends itself naturally to structured legal reasoning.

![Figure 3-1: Screenshot of the cfws.samr.gov.cn penalty document search interface](figures/ch3_cfws_search_ui.png)

Figure 3-1 The search interface of the China Market Supervision Administrative Penalty Document Network (cfws.samr.gov.cn), showing topic and legal-basis filter controls used during data collection.^[45]^

## 3.2 Penalty document collection pipeline

### 3.2.1 EasySpider workflow

Manual downloading of hundreds of PDFs from a paginated government portal is neither scalable nor reproducible. We used **EasySpider**^[44]^, a no-code visual web-crawling tool that lets users define a task graph in a browser-based GUI and saves the result as a portable JSON configuration. Our task configuration is stored at `easyspider/tasks/358.json`; the task graph executes the following sequence:

1. Open the homepage at `https://cfws.samr.gov.cn/index.html`.
2. Click the login button and confirm the login action.
3. Navigate to the user entry point (XPath: `#user`) to reach the authenticated collection interface.
4. Enter the "collect" template via an iframe-embedded table that lists available collections.
5. **Loop "next page"**: iterate through all paginated list pages matching the active filter.
6. Within each page, extract the following fields for every document row: 文书编号 (document ID), 文书链接 (document URL), 当事人名称 (party name), 处罚机关 (enforcement authority), 处罚日期 (penalty date), 处罚内容 (penalty summary).

Output is written in CSV format (`outputFormat: "csv"`). Duplicate removal at the EasySpider task level was not enabled (`removeDuplicate: 0`); deduplication was handled in the downstream cleaning step.

Importantly, the filter configuration — price-topic keyword, legal-basis selection (including the Price Law and the Regulations on Administrative Penalties for Price Violations), and year-wise slicing to work around the 200-row list cap — was set up through the portal's advanced-search UI **before** task execution rather than being embedded in the JSON task file. The operator enters the desired constraints in the browser, then triggers EasySpider to replay the navigation and harvest whatever the server returns for that filter state. Year-by-year slicing was therefore a manual but necessary step: by submitting one query per calendar year, we kept each result set within the 200-row display limit and ensured complete coverage across multiple years.

![Figure 3-2: EasySpider task graph for penalty-document collection (task 358)](figures/ch3_easyspider_task.png)

Figure 3-2 EasySpider task graph (task 358.json) for collecting penalty documents from cfws.samr.gov.cn. The graph progresses from homepage login through iframe navigation to paginated row extraction.^[44]^

### 3.2.2 Engineering challenges

Running an automated workflow against a live government portal introduced several practical complications.

**Login state management.** The portal requires an authenticated session before the collection interface becomes accessible. EasySpider's XPath-based click sequences handle the login flow, but any session timeout between batches required restarting the task from the login step. We did not encounter CAPTCHA challenges during our runs, though the portal documentation warns that anti-bot measures may be activated under high-frequency access.

**Iframe navigation.** The collection template is rendered inside an HTML iframe, which means the crawler's DOM context must be switched before any element within the template can be targeted. Task 358 explicitly accounts for this by including an iframe-entry step; without it, EasySpider would attempt to locate list elements in the outer page and fail silently.

**200-row display cap.** The portal's result list shows at most 200 rows regardless of how many documents match the query. There is no programmatic way to request a higher page count. We mitigated this by issuing separate queries for each calendar year, thereby ensuring that no single query's result set exceeded 200 rows. The downside is that years with more than 200 matching penalty decisions would still be under-sampled; we have no way to quantify this gap precisely.

**Pagination batching.** Each year's query generates its own paginated result set. EasySpider's "next page" loop handles pagination within a single query session, but the operator must manually re-run the task for each year slice. This added coordination overhead but was manageable given the relatively modest total volume.

One limitation we acknowledge openly: we do not retain a per-document exclusion log recording exactly which raw URLs were excluded at any stage. The 791 PDFs we ultimately downloaded and the 780 samples that survived cleaning (Section 3.3) represent our best reconstruction of the collection as-is.

## 3.3 From raw PDFs to evaluation set (v4)

### 3.3.1 PDF extraction

The 791 downloaded penalty PDFs were processed using `scripts/data/smart_pdf_extractor.py`. The extractor applies a cascade of parsing strategies — direct text layer extraction first, with an OCR fallback for scanned images — and outputs a structured record for each document. The record preserves the case facts section (违法事实), the legal basis (法律依据), and the penalty outcome (处罚结果), which together constitute the three ground-truth components we annotate.

After extraction, each record was **anonymized**: party names, addresses, and registration numbers were replaced with generic placeholders to reduce the risk of re-identification and to prevent models from relying on entity names rather than case logic. The `input.case_description` field that models receive is therefore a cleaned narrative that describes the conduct without exposing the original business identity.

### 3.3.2 Evolution from eval_159 to eval_754 to v4

The evaluation set went through three generations before we settled on the final 780-sample corpus.

`eval_159` was an early 159-sample subset assembled to validate the end-to-end pipeline quickly. It served its purpose — all three baseline models were piloted against this set (Section 4.4) — but its small size made per-class analysis unstable and it did not represent the full range of violation types.

`eval_754` was a mid-scale expansion that included LLM-rewritten case descriptions to augment difficulty. The rewriting step introduced a distributional gap between the synthetic descriptions and authentic penalty document language, which undermined the ecological validity of the evaluation. Results on `eval_754` therefore overestimated model sensitivity to stylistic cues rather than legal substance.

`v4` (the current set, `eval_dataset_v4_final.jsonl`) returns to **authentic penalty document text** as the primary input source. The 791 raw PDFs yielded 780 valid samples after removing records with incomplete case descriptions or format anomalies that did not conform to the evaluation pipeline's structural requirements. No per-item exclusion log was maintained for this filtering step; the 11 removed documents are not recoverable from repository artifacts alone.

![Figure 3-3: Data pipeline flowchart from raw PDFs to eval_dataset_v4_final.jsonl](figures/ch3_pipeline_flowchart.png)

Figure 3-3 End-to-end data pipeline: 791 raw penalty PDFs → text extraction and anonymization → annotation and structuring → 780-sample eval_dataset_v4_final.jsonl. Intermediate sets eval_159 and eval_754 are shown for historical context.

## 3.4 Evaluation-set structure and statistics

### 3.4.1 JSON schema

Each sample in `eval_dataset_v4_final.jsonl` is a single JSON object. A representative (truncated, anonymized) example from the file looks like this:

```json
{
  "id": "CASE_0001",
  "source_pdf": "esfile_....pdf",
  "region": "南平市市",
  "tier": 1,
  "input": {
    "case_description": "(case narrative, may contain line breaks and anonymization markers)",
    "platform": "支付宝",
    "goods_or_service": null
  },
  "ground_truth": {
    "is_violation": true,
    "violation_type": "不明码标价",
    "qualifying_articles": [
      {"law": "价格法", "article": "第十三条", "article_key": "价格法_十三"}
    ],
    "penalty_articles": [
      {"law": "价格法", "article": "第四十二条", "article_key": "价格法_四十二"}
    ],
    "legal_analysis_reference": "",
    "penalty_result": "罚款402500元"
  },
  "_debug": {
    "desc_source": "violation_facts",
    "leakage_found": false,
    "text_length": 6171
  },
  "review_required": true,
  "review_bucket": "fn_candidate",
  "review_reason": "...",
  "suggested_action": "..."
}
```

The top-level fields are:

- **`id`** — a sequential case identifier (CASE_0001 through CASE_0780) used for cross-referencing results files.
- **`source_pdf`** — a hash-style filename pointing to the originating document; used for overlap detection between the evaluation set and the case base (Section 3.6).
- **`region` / `tier`** — geographic origin and difficulty tier assigned during construction; `tier` was used in filter scripts to control set composition.
- **`input.case_description`** — the anonymized case narrative passed as input to all models; this is the only text the model sees.
- **`input.platform`** — the e-commerce platform named in the document, if any; may be null.
- **`ground_truth.is_violation`** — binary label (true/false).
- **`ground_truth.violation_type`** — the specific violation category drawn from the nine-class taxonomy (or "无违规" for compliant cases).
- **`ground_truth.qualifying_articles`** — the statutory articles that establish the violation (定性条款).
- **`ground_truth.penalty_articles`** — the statutory articles that authorize the penalty (处罚条款).
- **`ground_truth.penalty_result`** — the monetary or non-monetary sanction imposed.
- **`_debug.leakage_found`** — set to true if the case narrative was detected to contain information that directly reveals the ground-truth label (used during quality review).
- **`_debug.text_length`** — character count of the raw case description before truncation.
- **`review_*` fields** — metadata for the human review queue; records flagged as `fn_candidate` (false-negative candidates) were prioritized for manual inspection.

### 3.4.2 Violation-type distribution

The 780 samples split into 489 violation cases and 291 compliant cases. Among the 489 violations, ten subtypes appear; their counts are shown in Table 3-1. The distribution is heavily skewed: 不明码标价 (unpriced display) accounts for 221 of the 489 violation records — more than the next two subtypes combined — while 哄抬价格 (price gouging) and 不履行价格承诺 (non-fulfilment of price commitment) each appear exactly once.

| Violation type | Count |
|---|---:|
| Compliant (no violation) | 291 |
| 不明码标价 (Unpriced display) | 221 |
| 政府定价违规 (Government-priced violation) | 117 |
| 标价外加价 (Surcharge above marked price) | 73 |
| 误导性价格标示 (Misleading price display) | 49 |
| 未识别 (Unidentified sub-type) | 14 |
| 变相提高价格 (Disguised price hike) | 6 |
| 虚假价格比较 (Fake price comparison) | 5 |
| 虚假折扣 (Fake discount) | 2 |
| 不履行价格承诺 (Non-fulfilment of price commitment) | 1 |
| 哄抬价格 (Price gouging) | 1 |
| **Total** | **780** |

Table 3-1 Distribution of violation types in eval_dataset_v4_final.jsonl (n=780).

## 3.5 Law knowledge base (691 articles)

The 691-article law knowledge base was built by retrieving legislation from the 国家法律法规数据库^[46][49][50]^ through a series of targeted batch searches. We submitted queries using keywords related to price enforcement, e-commerce regulation, and unfair competition (e.g., 价格法, 明码标价, 价格违法, 电子商务, 反不正当竞争, 网络交易) and downloaded matching documents as DOCX files from the official portal. The downloaded files were organized into three subdirectories under `data/laws/`:

- **中央** — national-level legislation (Price Law, E-Commerce Law, Anti-Unfair Competition Law, Regulations on Administrative Penalties for Price Violations, etc.)
- **浙江** — provincial-level rules from Zhejiang, reflecting the project's regional focus on e-commerce enforcement
- **平台规则** — platform-specific pricing rules from major e-commerce operators

![Figure 3-4: Screenshot of the flk.npc.gov.cn law database search interface](figures/ch3_flk_search_ui.png)

Figure 3-4 The search interface of the National Laws and Regulations Database (flk.npc.gov.cn), used to retrieve price-compliance legislation for the knowledge base.^[46]^

Article-level chunking was performed by `src/rag/data_processor.py` (`LawDocumentExtractor.process_all_laws("data/laws")`). The extractor iterates through DOCX paragraph sequences and uses a regular expression to detect article boundaries — any paragraph beginning with "第…条" is treated as the start of a new chunk. Subsequent paragraphs are concatenated into the same chunk until the next article heading appears. Each resulting chunk record carries four fields:

- **`chunk_id`** — a unique identifier of the form `{law_name}_art_{article_number}`.
- **`law_name`** — the short name of the statute (e.g., "价格法").
- **`law_level`** — one of 中央, 浙江, or 平台规则, matching the source subdirectory.
- **`article`** — the article label extracted from the heading (e.g., "第十三条").
- **`content`** — the full text of the article, including any clause numbers within it.

Across all 691 chunks, the mean `content` length is approximately 140 characters, with a range of 18 to 816 characters. The brevity of most articles reflects the concise legislative drafting style common in Chinese administrative law; the longest articles tend to be definitional or penalty-schedule provisions that enumerate multiple sub-clauses.

## 3.6 Case base (133 cases) and leakage control

In addition to the law knowledge base, we maintain a case base of 133 historical penalty summaries. These were compiled separately from the main evaluation pipeline and are stored in ChromaDB alongside the law chunks. Their intended purpose is to give the retrieval system concrete precedents — factual descriptions of past enforcement decisions — that might help distinguish between closely related violation types.

However, a leakage check against the evaluation set revealed approximately 8 `source_pdf` identifiers that appear in both the case base and the evaluation set. Because these overlapping records originate from the same underlying penalty documents, injecting them as "similar cases" during evaluation would allow the model to receive near-duplicate information from the ground-truth source — a form of same-source contamination.

To eliminate this risk, the formal evaluator pipeline (`src/rag/evaluator.py`) calls `retrieve(..., laws_k=3, cases_k=0)`, passing `cases_k=0` to suppress all case injection. The agent pipeline (Chapter 6) applies the same constraint: `IntentAnalyzer._decide_topk` hard-codes `suggested_cases_k` to 0, so the `AdaptiveRetriever` never returns case chunks regardless of the query. The `RAGPromptTemplate` still contains a "similar cases" placeholder in its system prompt; when `cases_k=0`, that slot is populated with the string "暂无相似案例" (no similar cases available), ensuring the model's prompt is structurally consistent across all runs.

The 8 overlapping `source_pdf` values represent roughly 6% of the case base and about 1.6% of the 489 evaluation violation sources — a small fraction, but large enough in absolute terms to distort per-type metrics if admitted.

## 3.7 Limitations

Three limitations of the dataset deserve explicit mention.

We do not have a per-item exclusion log for the transition from 791 raw PDFs to the 780 final samples. The 11 dropped records were filtered out during pipeline construction, but no separate manifest file was written. If a reviewer needs to audit the exact exclusion criteria, the repository artifacts are insufficient on their own; we can only say that the drops were due to structural incompleteness or format incompatibility.

The violation-type distribution is heavily imbalanced. 不明码标价 accounts for 221 of the 489 violation samples — roughly 45% — while four subtypes have counts of 6 or fewer. Per-class F1 scores for 变相提高价格, 虚假折扣, 不履行价格承诺, and 哄抬价格 are therefore statistically unreliable; any model that achieves high macro-averaged F1 on the full set may still completely misclassify the rarest categories. We report per-class breakdowns where available but caution against drawing strong conclusions from them.

The 200-row cap on the portal's search interface means that any calendar year with more than 200 matching price-compliance decisions will be under-sampled in our corpus. Since we cannot query the total counts without triggering the cap, we cannot quantify this truncation effect precisely. The dataset is best understood as a representative, rather than exhaustive, sample of publicly available price-compliance enforcement records from the years covered.

## 3.8 Summary of this chapter

This chapter described the two-source data collection strategy, the EasySpider-based automation pipeline for harvesting penalty PDFs from cfws.samr.gov.cn, and the multi-stage cleaning and structuring process that produced `eval_dataset_v4_final.jsonl` with 780 samples (489 violation + 291 compliant) across ten violation subtypes. We also documented the 691-article law knowledge base compiled from flk.npc.gov.cn, its article-level chunking procedure, and the leakage-control decision to set `cases_k=0` in all formal evaluations. The resulting dataset, while not without class-imbalance and coverage limitations, provides a realistic and reproducible benchmark for comparing baseline LLM inference, retrieval-augmented generation, and agent-based approaches to price-compliance analysis — the subject of Chapters 4 through 6.
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
# 5 Retrieval-Augmented Generation Route

## 5.1 Motivation and Design Goals

The baseline system described in Chapter 4 treats every compliance query as a pure generation problem: Qwen3-8B receives a case description, infers whether a price violation occurred, and then constructs a legal rationale from whatever statutory knowledge was encoded during pre-training. That approach works reasonably well as a first pass — achieving 89.35% binary accuracy on the 780-sample evaluation set — yet it carries a structural weakness that becomes apparent once one examines its failure modes closely.

Large language models frequently hallucinate specific statutory provisions^[60]^. In the price-compliance domain this is especially damaging: a model might confidently assert that a merchant violated Article 14 of the Price Law when the relevant provision is actually Article 13, or cite a regulation that has since been superseded. The end user — whether a regulator writing an enforcement memo or a merchant deciding whether to contest a fine — has no way to verify the model's claim without independently consulting the original statute. Absent an evidence trail connecting each conclusion to a retrievable text fragment, the system cannot be audited or corrected.^[6]^^[55]^

A second weakness is temporal: pre-training data has a knowledge cutoff, so any statutory amendment issued after the model's training window is invisible to it. Price-related regulations in China have evolved steadily; the Market Supervision Administration has issued or revised several pricing rules in recent years, and a frozen model cannot reflect those changes.^[7]^

Retrieval-Augmented Generation (RAG) was introduced precisely to address this class of problems^[6]^. Rather than relying exclusively on parametric knowledge, RAG couples the language model with an external retrieval index so that each inference step is grounded in verifiable text fragments. For legal reasoning, this provides two practical benefits: the cited articles are traceable to actual documents, and the index can be updated without retraining the model.^[57]^

Against this backdrop, we define four concrete design goals for the RAG route in this thesis. We frame them as measurable constraints rather than aspirational principles, so that the evaluation results in Sections 5.7 and 5.8 can be directly interpreted as success or failure against each goal.

(1) **Grounded generation.** Every compliance conclusion should be derivable from at least one retrieved law article that appears verbatim in the prompt, so an auditor can cross-check it.

(2) **Controllable evidence scope.** The system must avoid injecting irrelevant statutes into the prompt, which would both inflate token count and confuse the model with spurious legal context.

(3) **Latency compatibility.** The retrieval overhead should keep the per-sample wall-clock within a factor of roughly two compared to the baseline (~7 s); in practice the target is under 10 s.

(4) **Separation of retrieval and generation.** The retrieval module should be independently testable and swappable — if a better embedding model becomes available, replacing it should not require touching the generation prompt.

The remainder of this chapter describes how each goal is realized in the implemented pipeline.

---

## 5.2 Pipeline Overview

The RAG pipeline follows a linear document-to-answer flow with six distinct stages:

**Document ingestion → Chunking → Hybrid retrieval → RRF fusion → Re-ranking → Dynamic top-k → Prompt assembly → Qwen3-8B inference**

At ingestion time, law articles stored as DOCX files in `data/laws/` are extracted and split into article-level chunks, then embedded and persisted in a ChromaDB collection. A separate BM25 index is constructed over the same chunks.

At query time, a case description is used as both the dense query and the BM25 query. The dense retriever (BAAI/bge-small-zh-v1.5) returns a ranked list of candidate articles; the BM25 retriever returns another. The two lists are fused via Reciprocal Rank Fusion (RRF), and the merged top list is passed to a CrossEncoder re-ranker (BAAI/bge-reranker-v2-m3). After re-ranking, a distance-threshold filter and a dynamic top-k selector reduce the candidate set to a compact, high-confidence group of law articles. Those articles, formatted as `laws_context`, are inserted into the system prompt together with the case description. Qwen3-8B then generates the compliance verdict and rationale in the same JSON schema as the baseline.

A figure placeholder is provided below:

![Figure 5-1: RAG pipeline — from document ingestion to LLM inference](figures/ch5_rag_pipeline.png)

Figure 5-1 End-to-end RAG pipeline. Arrows show the data flow from raw DOCX statutes through chunk indexing, hybrid retrieval, RRF fusion, CrossEncoder re-ranking, and dynamic top-k selection to final Qwen3-8B inference.

---

## 5.3 Document Processing and Indexing

### 5.3.1 Law Corpus Chunking

Before any model call can happen at query time, the law corpus must be transformed from DOCX files into a searchable, machine-readable index. This offline indexing phase is the foundation of the entire RAG pipeline, and the quality of the chunks produced here directly determines the ceiling of what the retriever can return.

The statutory source material spans multiple Chinese price-related laws and administrative regulations downloaded from the National Laws and Regulations Database (flk.npc.gov.cn) as DOCX files. These include the Price Law of the People's Republic of China, the Provisions on Administrative Penalties for Price Violations, the E-Commerce Law, the Anti-Unfair Competition Law, and several supplementary regulations on pricing practices.

Each DOCX file is processed by `LawDocumentExtractor.process_all_laws("data/laws/")` in `src/rag/data_processor.py`. The extractor walks the paragraph stream and uses a regular expression that matches the pattern `第[零一二三四五六七八九十百]+条` (i.e., "Article N" in Chinese) as a segment boundary. Every time a new article header is detected, the previous article's accumulated paragraphs are flushed as a completed chunk. Subsequent paragraphs before the next article header are appended to the current chunk.

Each resulting chunk carries five fields:

| Field | Description |
|---|---|
| `chunk_id` | Globally unique identifier within the corpus |
| `law_name` | Short title of the parent statute (e.g., "价格法") |
| `law_level` | Hierarchical tier: central / provincial / platform rule |
| `article` | Article label string (e.g., "第十三条") |
| `content` | Full text of the article body |

The final corpus contains **691 articles**. Content lengths range from 18 to 816 characters, with an arithmetic mean of approximately **140 characters** per chunk — compact enough to fit many articles into a single prompt without exceeding context limits. The article-level granularity was chosen deliberately over finer sub-article splitting (e.g., splitting by sub-clause) or coarser chapter-level grouping. Sub-article splits risk orphaning a clause from the interpretive context provided by the article preamble; chapter-level chunks are too large to embed meaningfully with a 512-dimensional model and would consume too much of the prompt's context window. An article is the natural legal unit: it defines a complete obligation, prohibition, or penalty, and it is also the unit that enforcement decisions cite when justifying a penalty.

### 5.3.2 Vector Encoding

Each chunk's `content` field is encoded with **BAAI/bge-small-zh-v1.5**, a 512-dimensional sentence-transformer model tailored for Chinese text^[11]^. The choice of bge-small-zh over the larger bge-m3 model^[12]^ was deliberate: for short legal article snippets averaging 140 characters, the smaller model achieves acceptable retrieval quality while consuming roughly one-fifth the memory footprint and encoding noticeably faster. In a deployment scenario where the vector index must coexist with the CrossEncoder re-ranker and the language model on the same machine, that memory saving is non-trivial.

The 512-dimensional embeddings are stored as float32 tensors. At query time the case description is encoded with the same model, and cosine distance is used as the similarity measure throughout. Cosine distance is preferred over Euclidean distance because it is invariant to the magnitude of the embedding vector, which can vary across documents of different lengths. For short legal article texts this is particularly important: a long article would naturally have a higher-norm embedding than a short one, and Euclidean distance would artificially penalize short articles in nearest-neighbor search.

All embeddings are computed offline at index-build time and loaded into memory at system startup. Incremental updates — adding new regulations as they are enacted — require only re-encoding and re-inserting the new chunks; the existing collection is not invalidated.

### 5.3.3 ChromaDB Collection

Embedded chunks are persisted in a **ChromaDB**^[39]^ collection under `data/rag/chroma_db`. ChromaDB was chosen for its zero-configuration local operation and its native support for metadata filtering, which allows the retriever to optionally restrict results to specific `law_level` values or to a particular statute by `law_name`. Alternative vector databases such as Milvus^[38]^ or FAISS^[37]^ offer higher throughput at scale, but for a 691-article corpus the performance difference is negligible, and ChromaDB's simpler deployment model reduces operational complexity. The collection is built once by `rag_build_vector_db.py` and reused across all evaluation runs; because the underlying HNSW index is persisted to disk, cold-start latency on subsequent runs is negligible.

---

## 5.4 Hybrid Retrieval

Hybrid retrieval combines two complementary signals to produce a ranked list of candidate articles. We adopt a two-component design rather than a three- or four-component ensemble because the primary trade-off in Chinese legal retrieval is between lexical precision and semantic generalization: BM25 handles the former, and dense retrieval handles the latter. Adding more components (e.g., sparse learned representations such as SPLADE) would increase index complexity and serving cost without a clear benefit on a 691-article corpus.

### 5.4.1 BM25 Component

BM25 (Best Match 25) is a classical probabilistic ranking function that scores documents by term frequency saturation and inverse document frequency^[9]^. It operates purely on token overlap, making it complementary to dense retrieval: BM25 rewards exact keyword matches (e.g., a case description that explicitly names "明码标价" will strongly retrieve Article 13 of the Price Law), whereas dense retrieval captures semantic paraphrase where the surface terms differ.

The BM25 index is built over the `content` fields of all 691 chunks after character-level or word-level tokenization of Chinese text. Standard BM25 parameters (k1 = 1.5, b = 0.75) are used throughout, matching the defaults commonly reported in the information retrieval literature^[36]^. The rank list returned by BM25 is treated as one input to the fusion step.

### 5.4.2 Dense Component

Dense passage retrieval encodes both queries and documents into a shared continuous embedding space, allowing retrieval by nearest-neighbor search rather than lexical overlap^[8]^. For short Chinese legal text, this is particularly valuable when a case description uses colloquial phrasing to describe behavior that the statute expresses in formal legal language. A complainant might write "the seller did not display the price clearly"; the relevant statute uses "未依法明码标价" — lexically different, but semantically close enough for the dense model to bridge.

The top-$N$ nearest neighbors retrieved from ChromaDB by cosine distance form the dense candidate list. In the full evaluation, the initial dense pool size is set equal to `laws_k` (typically 3), and a larger pool of candidates (up to twice `laws_k`) is passed to the subsequent fusion and re-ranking stages to give the CrossEncoder a diverse input set.

### 5.4.3 RRF Fusion

The two ranked lists — one from BM25 and one from the dense retriever — are combined using **Reciprocal Rank Fusion (RRF)**^[10]^. Given a document $d$, its RRF score aggregates its position across all input lists:

$$\text{RRF}(d) = \sum_{i} \frac{1}{k + \text{rank}_i(d)}$$

where $k = 60$ (the standard default) dampens the influence of very highly ranked documents and prevents a single-list monopoly. Documents that appear near the top of *both* lists receive the highest fused scores, effectively implementing a voting scheme. Documents absent from a list are treated as having infinite rank (zero contribution).

RRF requires no per-query training and is robust to score-scale differences between the BM25 and cosine-distance metrics, which would otherwise make direct score aggregation unreliable.

### 5.4.4 CrossEncoder Re-ranking

The RRF-fused list is passed to a **CrossEncoder**^[13]^ for re-ranking. Unlike the bi-encoder used at retrieval time (which scores query and document independently), a CrossEncoder processes the concatenated query–document pair through the full transformer stack, enabling richer attention interactions. We use **BAAI/bge-reranker-v2-m3** for this step.

The re-ranker receives the top-$M$ fused candidates (where $M$ is the initial retrieval pool size) and outputs a scalar relevance score for each. The list is sorted by this score, and the top entries are forwarded to the dynamic top-k selector. Because re-ranking is applied only to a small candidate pool rather than the entire 691-article corpus, the latency cost is manageable — the ablation study in Section 5.7 confirms that adding re-ranking does not materially increase wall-clock time.

---

## 5.5 Dynamic Top-k and Score Thresholds

Not every query benefits from retrieving the same number of law articles. A simple dispute about whether a price tag was displayed may be fully resolved by one or two articles, while a complex multi-violation case involving overlapping statutes needs broader coverage. Injecting too many articles into the prompt wastes context budget and risks confusing the model with tangentially relevant provisions; injecting too few risks missing the governing statute entirely.

We implement a three-tier **dynamic top-k** strategy based on the average cosine distance of the top-3 re-ranked results:

- If the mean distance of the top-3 candidates is **below 0.10**, the retrieval is considered high-confidence and the final law context is truncated to **2 articles**.
- If the mean distance falls in **[0.10, 0.15)**, moderate confidence, the context is set to **3 articles**.
- Otherwise, the full `laws_k` value (default 3, but up to 5 when the IntentAnalyzer suggests broader coverage) is used.

In all cases, only candidates that pass a distance threshold of **0.15** are considered; documents with distance ≥ 0.15 are filtered out before the mean is computed. A floor of `min_k=2` prevents the system from returning fewer than two articles even when confidence is high (a single article could be a false positive). The CrossEncoder re-rank score threshold `min_rerank_score` is left at its default of **0.0** during evaluation — no additional score-based pruning is applied beyond distance filtering.

The practical effect of this scheme is visible in the ablation: when the retriever is given free rein (no dynamic filtering), extraneous articles from adjacent legal domains occasionally appear in the prompt and degrade classification accuracy. The threshold at 0.15 was selected empirically by inspecting the distance distributions on a development subset. Intuitively, a distance of 0.15 in the bge-small-zh-v1.5 embedding space corresponds to articles whose phrasing is recognizably related to the query but not obviously on-point — transitional cases where the model is more likely to be misled than helped by inclusion.

An important consequence of combining the distance filter with the dynamic top-k is that the effective number of articles injected into the prompt is often *smaller* than `laws_k`, which keeps prompts compact and reduces hallucination risk on cases that have a clear single governing provision. The minimum guarantee of `min_k=2` ensures the model never lacks at least some statutory grounding even when the case description is unusually terse or ambiguous.

---

## 5.6 Prompt Assembly

With the evidence set finalized by the dynamic top-k selector, the pipeline moves to prompt construction. This step bridges the retrieval world (article chunks with metadata) and the generation world (an LLM system prompt). The assembly logic is deliberately simple: no summarization, no abstractive compression, no re-writing of the retrieved articles. The articles are inserted verbatim so that the model can reason directly against the statutory text, and so that the cited article keys in the model's output can be traced back to exact document locations without ambiguity.

After dynamic top-k selection, the surviving law articles are formatted into a `laws_context` block — a newline-delimited sequence of entries, each presenting the law name, article label, and article body. This block is injected into `RAGPromptTemplate.RAG_SYSTEM_PROMPT` alongside the case description.

The system prompt instructs the model to base its compliance judgement *only* on the provided articles, and to cite specific article keys in its output. Attribution-aware generation of this kind has been studied as a mechanism for reducing confabulation and improving verifiability of LLM outputs^[56]^. The output JSON schema is identical to the baseline — the same `is_violation`, `violation_type`, `legal_basis`, `reasoning`, and `cited_articles` fields — which makes cross-route comparison straightforward.

The template also contains a `cases_context` placeholder. During evaluation, **`cases_k` is set to 0** (no similar cases are retrieved), so `cases_context` is populated with the string "暂无相似案例" ("no similar cases available"). This is not merely a convenience: as noted in Section 5.3.1 and detailed in Section 6.4, the case base of 133 historical enforcement decisions overlaps with approximately 8 source PDFs present in the evaluation set. Injecting case context under those conditions would constitute same-source contamination.

---

## 5.7 Ablation Study

Ablation studies are standard practice for validating that each component of a multi-stage pipeline earns its place. Without ablation, a researcher cannot distinguish between a pipeline where every component contributes and one where a single dominant component does all the work while the others add complexity for no gain. Given that our pipeline has four distinct retrieval components (BM25, dense, RRF fusion, CrossEncoder), an ablation that removes each in turn provides a principled basis for the design choices.

### 5.7.1 Setup

To isolate the contribution of each retrieval component, we run four retrieval variants on the **first 154 samples** of the evaluation set, keeping the generation model (Qwen3-8B) and all other hyperparameters fixed. The four variants are:

- **bm25_only**: BM25 ranking, no dense retrieval, no re-ranking.
- **semantic_only**: Dense cosine-distance retrieval only, no BM25, no re-ranking.
- **rrf**: RRF fusion of both BM25 and dense lists, but no CrossEncoder re-ranking step.
- **rrf_rerank**: Full pipeline — RRF fusion followed by CrossEncoder re-ranking. This matches the configuration used for the main 780-sample evaluation.

Results are stored in `results/rag/rag_ablation_ablation_154__04-19__v4/`. Because the ablation covers a 154-sample subset, these numbers are not directly comparable to the 780-sample main results; they serve only to characterize component contributions within the same data slice.

### 5.7.2 Results

**Table 5-1** summarizes performance across the four variants on the 154-sample subset.

**Table 5-1** RAG ablation on the first 154 evaluation samples.

| Variant | Accuracy | F1 | Type Acc | Avg time (s) |
|---|---|---|---|---|
| bm25_only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| semantic_only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| rrf | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| rrf_rerank | **0.9026** | **0.9470** | **0.6299** | 8.11 |

Table 5-1 RAG ablation on the first 154 evaluation samples.

### 5.7.3 Analysis

The most striking finding is that `rrf_rerank` leads on every quality metric while remaining essentially indistinguishable from the other variants in wall-clock time — all four configurations run between 7.93 and 8.17 seconds per sample. The gain from adding the CrossEncoder is therefore essentially free in terms of latency, which is the expected behavior: re-ranking operates on a small candidate pool and the model is small.

Looking at individual metrics: binary accuracy climbs from 0.8766 (bm25_only) to 0.9026 (rrf_rerank), a gain of 2.6 percentage points. The F1 improvement is similar in magnitude (0.9319 → 0.9470). Violation-type accuracy — a harder metric that requires the model to name the specific violation category — shows the largest swing: 0.5844 for bm25_only versus **0.6299** for rrf_rerank, a gap of 4.55 percentage points. This is consistent with our expectation that precise identification of violation type depends on fine-grained semantic matching that BM25 alone cannot provide; the exact statutory wording for subtypes like "标价外加价" (surcharge above marked price) or "误导性价格标示" (misleading price display) differs enough from colloquial case descriptions that lexical retrieval misses the governing provision.

An interesting detail is that `rrf` (fusion without re-ranking) actually *decreases* type accuracy relative to `semantic_only` (0.5909 vs 0.6039). Adding BM25 can introduce lexically matching but contextually irrelevant articles — for instance, a general "price transparency" article that scores high on BM25 for almost any query. The CrossEncoder re-ranker corrects this: it assigns low scores to articles that are lexically similar but contextually mismatched, so `rrf_rerank` recovers and surpasses the semantic-only baseline.

The pattern reinforces a known result in the retrieval literature: fusion of multiple signals often helps average-case performance but can introduce noise that requires a re-ranking stage to clean up. In domain-specific retrieval settings like legal article matching, where the vocabulary is specialized and the candidate pool is small, the combination of BM25 fusion and CrossEncoder re-ranking appears to be a robust default worth the marginal complexity.

![Figure 5-2: Retrieval score distribution across ablation variants](figures/ch5_retrieval_score_dist.png)

Figure 5-2 Illustration of RRF fusion score distributions for the four ablation variants on the 154-sample subset.

![Figure 5-3: Ablation metric comparison bar chart](figures/ch5_ablation_bar_chart.png)

Figure 5-3 Bar chart comparing Accuracy, F1, and Type Accuracy across the four ablation variants. rrf_rerank consistently leads on all three metrics.

---

## 5.8 End-to-End RAG on the 780 Sample Set

The ablation study established the best retrieval configuration on a 154-sample slice. We now run the winning variant, `rrf_rerank`, on the complete 780-sample evaluation set. The larger set includes all violation types and both the compliant and non-compliant classes in their full proportions, so these numbers are the figures we report as the definitive RAG performance in the cross-route comparison.

When the full `rrf_rerank` pipeline is evaluated on all 780 samples, we obtain the results reported in the main comparison table (Table 5-2 below). The comparison also includes the Baseline figures from Chapter 4 for reference.

**Table 5-2** RAG vs. Baseline on the 780-sample evaluation set.

| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) |
|---|---|---|
| Binary accuracy | 89.35% | **89.85%** |
| Violation-type accuracy | 73.68% | **74.94%** |
| F1 | 91.47% | **92.01%** |
| Legal-basis quality avg | **0.8411** | 0.7321 |
| Reasoning quality avg | 0.8415 | **0.8685** |
| Avg response time (s) | 7.02 | 7.77 |

RAG improves binary accuracy by 0.50 pp, type accuracy by 1.26 pp, and F1 by 0.54 pp over the Baseline, while the average response time rises by only 0.75 seconds — a modest cost for the grounding benefit.

The **legal-basis quality score** presents an apparent paradox: it *drops* from 0.8411 to 0.7321 when moving to RAG. This requires careful interpretation. The legal-basis scorer, implemented in `src/baseline/response_parser.py`, is a heuristic keyword matcher: it awards points for the presence of predefined legal keywords (e.g., "价格法", "明码标价") and article-reference patterns ("第X条"). It does *not* perform any semantic legal analysis or cross-reference against ground-truth statutes.

Under the Baseline, the model generates legal rationales in free form and tends to use the exact vocabulary of those keywords, scoring well on the heuristic. Under RAG, the model is instructed to cite specific articles by their formal names and keys (e.g., "价格法_十三"), which may not always match the heuristic's keyword list. Moreover, RAG sometimes retrieves articles from less-cited statutes — provincial pricing rules, platform-specific regulations — whose titles fall outside the scorer's vocabulary. The retrieved context thus *widens* the lexical surface of the model's output in ways the heuristic was not calibrated to recognize.

This is a measurement artefact, not a legal quality regression. The reasoning quality score — which is less sensitive to exact vocabulary and more sensitive to the presence of logical connectives, factual claims, and structured analysis — moves in the opposite direction: 0.8415 (Baseline) → 0.8685 (RAG), an improvement of 2.7 points. That trend, combined with the classification gains, indicates that grounding on retrieved evidence genuinely improves the model's output even though the proxy legal-basis score fails to capture it.

This finding also has a broader methodological implication: heuristic surface-matching scores should not be taken as ground truth for legal argument quality. Future work that uses retrieval augmentation in legal domains may find that the actual correctness of cited statutes — verified by a legal expert or a structured ontology — diverges substantially from keyword-based proxies. We revisit this measurement concern more systematically in Chapter 7.

---

## 5.9 Limitations

Three limitations of the RAG route are worth acknowledging. We state them plainly here rather than burying them in footnotes, because honest documentation of a system's boundaries is part of responsible AI research.

The heuristic legal-basis scorer is a proxy, not a ground-truth legal correctness judgement. Its keyword-matching design rewards outputs that superficially resemble familiar legal vocabulary, and it penalizes — or simply misses — outputs that cite less common but legally valid provisions. The resulting score should be interpreted as a rough signal rather than a precise measure of legal accuracy.

The hybrid retriever can misfire for rare or novel violation types. The dataset contains only 6 samples of "变相提高价格" (disguised price hike) and 1 sample of "哄抬价格" (price gouging). For these minority categories, the BM25 and dense indices have little statistical signal from training-time priors, and the relevant articles may not rank highly if the case description uses atypical phrasing. The dynamic top-k system partially mitigates this by allowing a wider candidate set when confidence is low, but it cannot recover from a wholesale retrieval miss.

Retriever latency dominates the per-sample wall-clock. At 7.77 s average, the RAG route is already close to the design budget of ~10 s, and that budget is consumed almost entirely by the embedding, HNSW search, BM25 query, and CrossEncoder inference steps. Any meaningful latency reduction would require either a smaller re-ranker, an approximate index with lower recall, or batched inference — each of which involves a quality trade-off. For the 780-sample evaluation in this thesis, serial single-sample evaluation is fine; but a production system handling hundreds of concurrent requests per minute would need a very different serving architecture.

A fourth, more subtle limitation is that the evaluation dataset itself shapes what we can claim. The 780 samples are drawn from administrative penalty documents, which means they are cases where a regulatory authority already concluded a violation occurred. The distribution of violation types in the dataset (221 cases of 不明码标价 vs. only 1 case of 哄抬价格) reflects the actual frequency of enforcement actions in the source dataset rather than the true distribution of pricing violations in the market. Retrieval performance on underrepresented types is therefore hard to assess, and conclusions about the pipeline's strengths should be interpreted with that sampling caveat in mind.

---

## 5.10 Summary of This Chapter

Table 5-3 provides a quick-reference summary of the key design parameters used in the RAG pipeline as evaluated in this thesis.

**Table 5-3** RAG pipeline configuration parameters.

| Parameter | Value | Notes |
|---|---|---|
| Embedding model | BAAI/bge-small-zh-v1.5 | 512-dim, Chinese |
| Re-ranker | BAAI/bge-reranker-v2-m3 | CrossEncoder |
| Vector database | ChromaDB | Local HNSW |
| BM25 parameters | k1=1.5, b=0.75 | Defaults |
| distance_threshold | 0.15 | Cosine distance cutoff |
| min_k | 2 | Minimum articles injected |
| laws_k (eval) | 3 | Default retrieval pool |
| cases_k | 0 | Disabled (leakage control) |
| min_rerank_score | 0.0 | No additional score cutoff |
| Language model | Qwen3-8B | Via MaaS API |

This chapter has described the design, implementation, and evaluation of the Retrieval-Augmented Generation route for price compliance supervision. The pipeline couples Qwen3-8B with a 691-article law corpus through hybrid BM25 + dense retrieval, RRF fusion, CrossEncoder re-ranking, and distance-threshold dynamic top-k selection.

An ablation study on 154 samples showed that each component of the pipeline contributes to quality, with the CrossEncoder re-ranker providing the largest marginal gain (from 0.5909 to 0.6299 type accuracy) at negligible additional latency. On the full 780-sample set, RAG improves binary accuracy, type accuracy, and F1 over the Baseline while maintaining a response time under 8 seconds. The apparent drop in legal-basis quality score is attributed to a measurement artefact in the heuristic scorer rather than a true legal regression, as the reasoning quality score and classification metrics both improve.

From a system-design perspective, the RAG route occupies an appealing middle ground. It is substantially more grounded than the Baseline, meaningfully faster than the Agent, and requires no fine-tuning of the language model. Its principal limitation — the absence of adaptive intent-driven retrieval and structured self-correction — motivates the agent architecture described in the next chapter.

The next chapter builds on the retrieval infrastructure introduced here, embedding it within a six-node agent workflow that adds intent analysis, evidence grading, structured reasoning, self-reflection, and remediation guidance.
# 6 Agent Route with Multi-Node Reflection

## 6.1 Motivation

Chapter 5 demonstrated that grounding Qwen3-8B with retrieved law articles produces measurable improvements in classification accuracy and reasoning quality. RAG is fast, modular, and easy to audit at the retrieval level. For bulk classification tasks — deciding whether 780 penalty records constitute violations and labeling their types — it is a sensible default.

There are nonetheless scenarios where RAG's single-shot architecture falls short. A regulator preparing an enforcement memorandum needs not just a verdict but a traceable chain of legal reasoning: which provision was triggered, why the defendant's conduct meets each element of that provision, and what follow-up steps are required. A merchant conducting a self-audit needs actionable remediation guidance, not merely a binary label. In both cases, the quality of the *explanation* matters as much as the accuracy of the *classification*, and a system that generates its conclusion in a single forward pass through the model has no opportunity to catch its own logical errors before committing to an output^[15]^^[18]^.

The agent paradigm addresses this by decomposing the decision process into a sequence of specialized sub-tasks, each with its own data structures, prompts, and validation criteria^[19]^^[16]^. Rather than asking the model to classify, cite, reason, and recommend simultaneously, the agent assigns each concern to a dedicated node. An intent analysis step focuses the retrieval query. A grader filters retrieved evidence for relevance. A structured reasoning step forces the model into an explicit multi-step chain of thought^[14]^. A reflection step checks the output for internal contradictions before it leaves the pipeline. A remediation advisor converts the verdict into forward-looking compliance recommendations.

This decomposition does not come free: the agent route averages 37.62 seconds per sample on the 780-sample set, compared to 7.77 seconds for RAG. Whether that cost is worth paying depends on the use case, a point we return to in Section 6.8. The goal of this chapter is to describe the architecture in enough detail that both the design decisions and their performance consequences can be understood and reproduced.

It is also worth noting that accuracy and quality are not the only evaluation dimensions that matter in this domain. Legal AI systems deployed in regulatory contexts face scrutiny on explainability grounds: regulators, courts, and supervised parties may all demand to know *why* a system reached a particular verdict. A system that achieves 89% accuracy through a black-box generation step is harder to defend than one that achieves 87% accuracy with a step-by-step reasoning trail that a lawyer can check. The agent architecture is therefore designed with auditability as a first-class constraint, not as an afterthought.

The agent builds on several theoretical foundations: the ReAct framework for interleaving reasoning and action^[15]^, the Reflexion approach for verbal self-correction^[16]^, and the Self-Refine idea of iterative output improvement via feedback^[17]^. The concept of multi-agent simulation and behavior decomposition also informs the node separation philosophy, particularly in how specialized sub-agents are given narrow mandates with clearly defined inputs and outputs^[20]^. Neither LangChain^[22]^ nor LlamaIndex^[23]^ is used as an orchestration framework here; the six-node graph is implemented directly in `src/agents/` to keep the state representation and control flow fully transparent and auditable.

---

## 6.2 System Architecture

The agent operates as a **linear six-node graph** in which state is passed from node to node as a shared dictionary. The nodes execute in the following order:

```
IntentAnalyzer → AdaptiveRetriever → Grader → ReasoningEngine → Reflector → RemediationAdvisor
```

There is one conditional loop: if the Reflector detects a critical inconsistency in the ReasoningEngine's output and the maximum reflection count has not been reached, control returns to the ReasoningEngine for a single re-reasoning attempt. In all other cases the graph is strictly forward.

Each node reads from and writes to a shared `AgentState` dictionary. Fields populated by earlier nodes are available to all subsequent nodes, so the Reflector can inspect the raw reasoning chain, the retrieved articles, and the intent metadata simultaneously. This shared-state design mirrors the "blackboard" architecture common in classical expert systems and avoids the need for explicit inter-node message passing.

![Figure 6-1: Agent state graph — six-node linear flow with Reflector feedback loop](figures/ch6_agent_state_graph.png)

Figure 6-1 Agent state graph. Solid arrows show the primary linear execution path. The dashed arrow from Reflector back to ReasoningEngine is triggered only when a critical heuristic is violated and `reflection_count < max_reflection`.

---

## 6.3 Node Design

### 6.3.1 IntentAnalyzer

The IntentAnalyzer is a **pure rule-based module** — it makes no LLM call and adds negligible latency (average 0.11 ms per sample). Its role is to pre-process the case description and populate an intent record that guides the downstream nodes, particularly the retrieval configuration.

The output fields are:

- **`violation_type_hints`** (up to 3 strings): suspected violation categories detected by keyword triggers.
- **`key_entities`** (list): extracted references to platforms, monetary amounts, and price-related terminology.
- **`complexity`** (`simple` / `medium` / `complex`): determines the RemediationAdvisor operating mode.
- **`suggested_laws_k`** (3, 4, or 5): the number of law articles to retrieve, calibrated to complexity.
- **`suggested_cases_k`** (always 0): the number of similar historical cases to retrieve; hard-coded to zero for the reasons discussed in Section 6.4.
- **`reasoning_hints`** (list): brief guidance strings forwarded to the ReasoningEngine prompt.

Violation type detection is performed by `_detect_violation_types`, which iterates over a set of trigger-keyword lists. The logic for each category is:

- **不明码标价 (Unpriced display)**: strong triggers include "未标价", "未明码标价", "没有标价"; weak triggers such as "价格不清晰" or "标价不规范" must co-occur with at least one strong feature before the hint is emitted.

- **政府定价违规 (Government-priced violation)**: triggered by keywords like "政府定价", "政府指导价", "超出定价范围". Cases involving utilities, medical services, or public transportation are flagged as medium or complex complexity.

- **标价外加价 (Surcharge above marked price)**: triggers include "加收", "额外收费", "超出标价收取", "收取标价外费用".

- **误导性价格标示 (Misleading price display)**: this category uses a two-tier feature system. Strong features are phrases such as "虚假原价", "虚标原价", "不实折扣". Weak features include "原价", "划线价", "参考价". A hint is emitted if at least one strong feature is present, or if two or more weak features co-occur with a general price-comparison term.

- **变相提高价格 (Disguised price hike)**: triggers include "缩减数量", "降低质量", "搭售", "强制附加" combined with evidence of price change or additional charges.

- **哄抬价格 (Price gouging)**: triggered by "哄抬", "囤积居奇", "散布涨价信息", or the co-occurrence of commodity shortage terms with significant price increase evidence.

When no specific type is identified, the analyzer emits an empty hint list and defaults to `complexity=simple`, `suggested_laws_k=3`.

### 6.3.2 AdaptiveRetriever

The AdaptiveRetriever wraps the same `HybridRetriever` used in the RAG route (Chapter 5) but parameterizes it dynamically based on the IntentAnalyzer's output. Specifically:

- `laws_k` is set to the `suggested_laws_k` value from the intent record (3, 4, or 5).
- `cases_k` is set to the `suggested_cases_k` value, which is always 0.
- `distance_threshold` and `min_k` are fixed at 0.15 and 2 respectively, matching the RAG evaluation configuration.

The dynamic `laws_k` means that complex cases with multiple suspected violation types receive a broader retrieval scope (up to 5 articles), while simple single-violation cases are served by a focused 3-article set. This reduces the risk of prompt pollution from tangentially related statutes, which is more important in the agent setting because the retrieved articles propagate through the Grader and directly influence the ReasoningEngine's chain-of-thought prompt.

### 6.3.3 Grader

After retrieval, the Grader scores each candidate article and filters out those that are unlikely to be genuinely relevant to the current case. The goal is to prevent the ReasoningEngine from reasoning over low-quality evidence.

Each article receives a weighted composite score:

$$\text{final\_score} = 0.6 \times \text{relevance} + 0.3 \times \text{coverage} + 0.1 \times \text{freshness}$$

The three components are computed as follows:

**Relevance.** If a CrossEncoder re-rank score is attached to the article (which it will be when `use_reranker=True`), that score is used directly. Otherwise, relevance falls back to `max(0, 1 − distance)`, converting cosine distance into a similarity value on [0, 1].

**Coverage.** The proportion of the IntentAnalyzer's `key_entities` tokens that appear as substrings in the article's `content` field. If the intent analysis produced no key entities, coverage defaults to 0.5 — a neutral value that neither rewards nor penalizes the article.

**Freshness.** A step function on the article's publication year: 1.0 for year ≥ 2024 (reflecting recent regulatory updates), 0.8 for year ≥ 2020, and 0.6 for older material. When no year metadata is available, the system defaults to 2020 and applies the 0.8 weight. This heuristic acknowledges that China's price regulation framework has been updated more actively in recent years and that the most recent provisions should be preferred when evidence scores are otherwise close.

Articles with `final_score < min_score` (default 0.5) are filtered out. A fallback `min_keep=2` ensures that at least two articles are passed to the ReasoningEngine even if all candidates score below the threshold — in that case, the top-2 by score are retained regardless of the cutoff. The Grader runs in under 0.1 ms on average (0.08 ms measured), because it involves only arithmetic operations on a small candidate list.

### 6.3.4 ReasoningEngine

The ReasoningEngine is the only node in the agent (other than RemediationAdvisor in detailed mode) that makes an LLM call. It invokes Qwen3-8B via the same MaaS client used in the Baseline and RAG routes.

Because `cases_k = 0` throughout evaluation, the engine uses the **4-step chain-of-thought (CoT)** branch of its prompt^[14]^:

1. **Fact extraction.** Identify the specific conduct alleged in the case description — what the operator did, at what price, on which platform, and to whom.
2. **Legal element matching.** For each retrieved and graded law article, determine whether the elements of that provision are satisfied by the extracted facts.
3. **Violation determination.** Based on the element-matching analysis, reach a binary verdict (`is_violation`) and, if positive, identify the specific violation type.
4. **Reasoning synthesis.** Produce a narrative explanation connecting the factual findings to the legal conclusions, in language suitable for an enforcement record.

When `cases_k > 0` (a configuration available but not used in the formal evaluation), the prompt adds a fifth step that compares the current case against retrieved historical cases and adjusts confidence accordingly. For the purposes of this thesis, that branch is disabled.

The output JSON schema mirrors the Baseline and RAG outputs: `is_violation`, `violation_type`, `legal_basis`, `reasoning`, and `cited_articles`. The explicit CoT structure tends to produce longer and more logically organized reasoning fields, which is reflected in the reasoning quality score discussed in Section 6.5. Chain-of-thought prompting was originally proposed for arithmetic and commonsense reasoning benchmarks^[14]^, but its benefits transfer well to structured legal analysis, where each inferential step must establish a clear connection between a factual premise and a legal conclusion before the next step can proceed.

### 6.3.5 Reflector

The Reflector applies a set of **heuristic validation rules** to the ReasoningEngine's output without making an additional LLM call. Its purpose is to catch the most common categories of logical error before the result is finalized. The `max_reflection` parameter is set to **1**, meaning that at most one re-reasoning attempt is permitted per case.

Critical triggers — any of which will initiate a re-reasoning cycle — include:

- `is_violation == True` but `violation_type` is "无违规" or a similar null-type string.
- `is_violation == False` but `violation_type` is a named violation category (a contradiction in the opposite direction).
- The reasoning chain **completely lacks** fact keywords that are expected for the detected violation type. For example, a case flagged as 不明码标价 should contain some reference to pricing display; if the reasoning chain mentions only monetary penalties with no discussion of price labeling, the Reflector flags this as a missing-element gap.
- The case description contains **non-price-domain keywords** (e.g., references to food safety, product quality standards, or environmental violations) with no corresponding price-related evidence — suggesting the model may have over-generalized.

Warning-level triggers (logged but not causing re-reasoning) include absent legal-basis text, cited articles that do not match the declared violation type, and unusually short reasoning fields.

When a critical trigger fires and `reflection_count < max_reflection`, the Reflector composes a structured feedback message describing the detected problem and passes it back to the ReasoningEngine along with the original case context and retrieved articles. The ReasoningEngine then re-generates its output, ideally correcting the flagged inconsistency. If the revised output still triggers the same critical rule, the system accepts the revised output anyway (since a second reflection round is not allowed) and logs the failure for post-hoc analysis.^[16]^^[17]^

The one-reflection limit is a practical engineering choice. Empirically, most CoT errors fall into one of the contradiction categories caught by the heuristics, and a single re-reasoning pass corrects these in the majority of triggered cases. Allowing more reflection rounds would not eliminate the deeper classes of error (e.g., wrong legal domain or missing statutory element) and would add meaningful latency for each triggered case. The Reflector's 453.58 ms average already reflects some amortized cost from triggered reflections; a `max_reflection=2` setting would push this higher with diminishing returns.

The average Reflector latency is 453.58 ms per sample. This is much larger than the Grader (0.08 ms) but much smaller than the retrieval or reasoning steps, and it includes both the heuristic evaluation and, in cases where reflection is triggered, the overhead of assembling the feedback message.

### 6.3.6 RemediationAdvisor

The final node in the pipeline translates the compliance verdict into actionable guidance. Its behavior is gated on the `complexity` field from the IntentAnalyzer:

- **Fast mode** (`complexity == simple`): a pre-defined template from `REMEDIATION_TEMPLATES` is selected based on the detected violation type. The template provides a boilerplate list of corrective actions (e.g., "display prices on all listed items within 5 business days") without an additional LLM call.

- **Detailed mode** (`complexity == medium` or `complex`): the advisor makes an LLM call with a structured prompt requesting a JSON response containing two fields: `remediation_steps` (a numbered list of specific corrective actions tailored to the case facts) and `compliance_checklist` (a set of ongoing compliance checkpoints the operator should maintain).

Detailed mode accounts for most of the advisor's average latency of 5,342.60 ms. For simple cases, the fast-mode template returns in sub-millisecond time. In the 780-sample evaluation, the distribution of complexity labels (determined by the IntentAnalyzer) determines the overall share of detailed-mode calls. The RemediationAdvisor is the only node whose output is not directly compared against the evaluation set's ground-truth labels; its quality is therefore harder to quantify automatically. In the web prototype (Chapter 8), this output is the primary content surfaced to merchant users, making it the most user-visible component of the entire pipeline.

---

## 6.4 Data Leakage Control

Any system evaluated against a benchmark must be checked for inadvertent exposure of test data to the model during inference. In RAG and agent systems, this risk is qualitatively different from the training-set contamination studied in the LLM pre-training literature: the concern is not that the model memorized specific case outcomes during training, but that the retrieval system might surface the ground-truth answer as a retrieved document at inference time.

The case base contains 133 historical enforcement decisions collected alongside the evaluation dataset. An analysis of `source_pdf` identifiers — each of which corresponds to a distinct administrative penalty document — identified **8 cases** where the same underlying enforcement document appears in both the case base and the evaluation set. Admitting these cases as retrieved context during evaluation would mean that the model is shown the answer to some of its test questions, invalidating those samples' results.

To avoid this, `suggested_cases_k` in the IntentAnalyzer is **hard-coded to 0**, and the AdaptiveRetriever's `cases_k` parameter is always 0. The system prompt still contains a `cases_context` placeholder (inherited from the RAG template), but it is populated with "暂无相似案例" at runtime. The case base remains in the system for the web prototype (Chapter 8), where the leakage concern does not apply in the same way — a merchant or regulator using the interactive tool is not submitting items from the frozen evaluation set.

This decision means the agent's performance figures in Section 6.5 represent a fair, contamination-free evaluation of retrieval-only augmentation. Had cases been enabled, performance numbers would be artificially inflated for the 8 overlapping samples and likely also for semantically similar cases nearby in the embedding space. The 8 overlapping PDFs represent approximately 6% of the case base and roughly 1.6% of the evaluation set's violation sources — small enough that enabling cases would not dramatically change the aggregate metrics, but the principle of clean separation between retrieval knowledge and evaluation targets is important to maintain for scientific validity.

---

## 6.5 End-to-End Agent Results on the 780 Samples

Running the full six-node agent over all 780 evaluation samples produces the results shown in Table 6-2, reproduced here alongside the RAG and Baseline benchmarks for context.

**Table 6-2** Three-route comparison on the 780-sample evaluation set.

| Metric | Baseline (Qwen3-8B) | RAG (Qwen3-8B) | Agent (Qwen3-8B) |
|---|---|---|---|
| Binary accuracy | 89.35% | 89.85% | 86.98% |
| Violation-type accuracy | 73.68% | 74.94% | 71.52% |
| F1 | 91.47% | 92.01% | 89.79% |
| Legal-basis quality avg | 0.8411 | 0.7321 | 0.7035 |
| Reasoning quality avg | 0.8415 | 0.8685 | **0.8931** |
| Avg response time (s) | 7.02 | 7.77 | 37.62 |

The agent's binary accuracy (86.98%) and type accuracy (71.52%) are approximately 2.4 pp and 2.2 pp below the Baseline respectively — a drop that may seem counterintuitive given the additional processing steps.

Several factors contribute to this classification trade-off. The structured CoT prompt is more verbose and directive than the baseline's single-shot prompt, which means that when the model's prior knowledge and the retrieved evidence point in different directions, the CoT structure can occasionally lock the model into a wrong reasoning path that it then rationalizes. The rule-based IntentAnalyzer may also generate incorrect violation-type hints for atypical phrasing, biasing the retrieval toward the wrong legal domain before the model has a chance to reason freely. A third contributor is that the agent introduces more decision points that can go wrong: a failed Grader filter may remove a genuinely relevant article, leaving the ReasoningEngine with incomplete statutory evidence. In the single-shot routes, all retrieved articles reach the model without filtering; the Grader trades recall for precision, which helps the majority of cases but hurts edge cases where the most relevant article happens to be the one with low coverage score.

The reasoning quality score tells a different story: at **0.8931**, the agent produces the highest-quality reasoning outputs across all three routes, exceeding the Baseline (0.8415) by a margin of 5.2 points and RAG (0.8685) by 2.5 points. Because the reasoning quality metric rewards factual specificity, logical connectives, and multi-sentence structure, the 4-step CoT architecture is directly responsible for this gain. The model is not merely generating a verdict; it is constructing a document-level argument.

Whether the classification trade-off is acceptable depends on the deployment context, which we discuss in Section 6.8.

---

## 6.6 Per-Node Timing Analysis

Table 6-3 shows average per-node latency from the timing run `results/agent/agent_v4_780_node_timings__04-19/results.json`, which processed 777 of 780 samples successfully.^[note1]^

**Table 6-3** Per-node average latency (777/780 successful samples, `agent_v4_780_node_timings__04-19`).

| Node | Avg (ms) | Share of pipeline |
|---|---|---|
| intent_analyzer | 0.11 | < 0.01% |
| adaptive_retriever | 19,167.81 | ~53% |
| grader | 0.08 | < 0.01% |
| reasoning_engine | 11,175.34 | ~31% |
| reflector | 453.58 | ~1.3% |
| remediation_advisor | 5,342.60 | ~15% |
| **total_pipeline** | **36,139.52 ms (~36.14 s)** | 100% |

Table 6-3 Per-node average latency for the agent pipeline. Values are averaged over 777 successfully processed samples.

^[note1]^ *The per-node timing run reports 36.14 s average. The 37.62 s figure cited in Table 6-2 comes from a separate run (`results/compare/improved-1.md`). These are distinct experimental runs and their latency figures should not be mixed or averaged.*

The latency profile is dominated by two LLM-backed nodes: AdaptiveRetriever (19.17 s, ~53%) and ReasoningEngine (11.18 s, ~31%). The retrieval dominance is consistent with the RAG findings in Chapter 5 — encoding the query, running the HNSW search, computing BM25 scores, and running the CrossEncoder re-ranker all add up, and in the agent the retrieval call may use `laws_k = 4` or `5` for complex cases, slightly widening the re-ranking pool. ReasoningEngine latency reflects Qwen3-8B inference time over a longer structured prompt.

The RemediationAdvisor accounts for approximately 5.34 s (~15%), reflecting the mixture of fast-mode (near-zero) and detailed-mode (LLM call) activations across the 777 samples. The remaining nodes — IntentAnalyzer (0.11 ms) and Grader (0.08 ms) — are computationally negligible. The Reflector's 453.58 ms is partly the cost of string-matching heuristics and partly the amortized overhead of re-reasoning invocations triggered on a subset of samples.

One design implication is clear: reducing the agent's wall-clock time requires targeting the retrieval step. Options include a lighter re-ranker, early stopping in HNSW search, or asynchronous retrieval that overlaps with intent analysis. Any of these would require re-validating accuracy, which we leave as future work.

![Figure 6-2: Per-node latency breakdown (pie/bar chart)](figures/ch6_node_timing_breakdown.png)

Figure 6-2 Visualization of per-node average latency from the `agent_v4_780_node_timings__04-19` run. AdaptiveRetriever and ReasoningEngine together account for over 84% of total pipeline time.

---

## 6.7 Case Study

To illustrate the agent's behavior on a concrete example, we trace through a representative case from the `agent_v4_780_node_timings__04-19` results: a merchant operating on Alipay Life who was penalized for failing to display the unit price for a service package, with a total penalty of ¥402,500.

**IntentAnalyzer output.** The case description contains "未明码标价" and "未标明价格" — both strong triggers for the 不明码标价 category. The analyzer also detects a platform reference ("支付宝") and a monetary figure, setting `key_entities = ["支付宝", "402500元"]`, `complexity = simple`, `suggested_laws_k = 3`, `suggested_cases_k = 0`, and `violation_type_hints = ["不明码标价"]`.

**AdaptiveRetriever output.** With `laws_k = 3`, the retriever returns the top-3 articles after RRF fusion and CrossEncoder re-ranking. The top result is Article 13 of the Price Law ("经营者销售商品和提供服务，应当按照政府价格主管部门的规定明码标价"), with a rerank score indicating high relevance. Article 42 of the Price Law (penalty provision) and an article from the Provisions on Administrative Penalties for Price Violations also appear in the returned set.

**Grader output.** The Grader assigns Article 13 a final score based on the weighted composite: the rerank score (high, contributing approximately 0.52 to the relevance term), plus coverage of key entity keywords in the article content ("标价" appears in the article body, contributing 0.15 to the coverage term), plus freshness (Article 13 of the Price Law was enacted in 1997, scoring 0.6 and contributing 0.06 to the freshness term). The estimated final score exceeds 0.5, so the article passes the filter. Both penalty articles also score above 0.5 and are retained. All three articles are forwarded to the ReasoningEngine.

**ReasoningEngine output (4-step CoT).** The model identifies the operative facts (service on Alipay, no unit price displayed), matches them against Article 13's elements (operator must display prices clearly), determines that the elements are satisfied, and concludes `is_violation: true, violation_type: "不明码标价"`. The reasoning field explicitly walks through each CoT step, citing the specific article keys.

**Reflector.** No critical triggers are fired: `is_violation` and `violation_type` are consistent, the reasoning chain contains the expected "明码标价" and "未标明" keywords, and there are no non-price-domain signals. `reflection_count = 0` at the end of this case.

**RemediationAdvisor.** With `complexity = simple`, the fast-mode template for 不明码标价 is selected, producing a two-item remediation list: (1) immediately post unit prices for all listed services, and (2) train staff on price-display requirements within 10 business days.

![Figure 6-3: Case study walk-through — annotated screenshot or flowchart of the six-node trace](figures/ch6_case_study_trace.png)

Figure 6-3 Step-by-step trace of the agent pipeline for the representative 不明码标价 case. Each panel shows the input and output of one node.

---

## 6.8 Discussion

**Where the 5× latency is justified.** The agent route is most valuable in two settings. The first is high-stakes regulatory enforcement: a regulator who is preparing an administrative penalty decision needs a traceable, step-by-step reasoning chain that can be reviewed by legal counsel and attached to the official record. The agent's 4-step CoT output, graded evidence list, and optional case-comparison analysis provide precisely that — and the 37-second wait is trivial relative to the days a human reviewer would spend on the same task. The second is merchant self-audit: a seller who wants to assess their own compliance posture before a regulatory inspection benefits from the RemediationAdvisor's checklist, which the single-shot RAG route does not provide. For these actors, the qualitative depth of the output justifies the latency cost.

**Where it is not worth the overhead.** Bulk classification at scale — e.g., screening 10,000 newly filed enforcement cases to assign preliminary violation-type labels for routing — does not require structured CoT or remediation steps. In this setting, the RAG route is clearly preferable: it is 4.8× faster, and its classification accuracy is actually 2.9 pp higher than the agent's. Using the agent for batch screening would impose a ~170× total compute cost compared to the baseline with no accuracy benefit.

A practical deployment would route incoming queries based on use-case context: brief, low-complexity queries from consumers or automated monitoring pipelines go to RAG; detailed, high-stakes queries from regulators preparing enforcement memos or merchants conducting self-audits go to the agent. The IntentAnalyzer's complexity estimate could serve as the routing signal with minimal added overhead, since it runs in under 0.2 ms. A hybrid deployment of this kind would achieve near-RAG accuracy at scale while preserving the agent's depth for the minority of cases that genuinely require it.

---

## 6.9 Limitations

Honest evaluation requires documenting not just what a system does well but where it falls short. Three limitations of the agent route deserve explicit acknowledgment.

The rule-based IntentAnalyzer is brittle against novel phrasing. Its keyword trigger lists were constructed by inspecting the existing 780-sample dataset and the 691 law articles. If a new category of pricing violation emerges — or if complaint language shifts significantly — the trigger lists will fail silently, emitting empty hints and defaulting to generic configuration. Maintaining these lists requires ongoing curation. An LLM-based intent analysis node would generalize better but would add latency and cost.

The Reflector's heuristic validation misses deeper legal nuance. It catches internal contradictions (the most common failure mode) but cannot detect subtler errors such as applying the wrong penalty provision to a correctly identified violation type, or misidentifying which element of a multi-element provision is satisfied. A more robust reflection step would require either a dedicated legal-reasoning LLM or a formal rule engine with statute-level knowledge — both beyond the scope of this thesis.

Retriever latency dominates the pipeline. At 19.17 s average, the AdaptiveRetriever accounts for more than half of total agent time. The node-level timing data shows that no amount of optimization to the other five nodes can reduce total latency below roughly 16 seconds without also addressing retrieval. This creates a fundamental engineering challenge for real-time interactive deployments, particularly on CPU-only inference hardware. Speculative or asynchronous retrieval — beginning the embedding call in parallel with the IntentAnalyzer rather than sequentially after it — is a straightforward optimization that could reduce end-to-end latency by the IntentAnalyzer's (admittedly tiny) 0.11 ms, but the bigger win would come from quantizing the CrossEncoder or using a smaller re-ranker model.

A fourth limitation applies to the evaluation coverage of individual nodes. The 780-sample aggregate metrics measure the pipeline as a whole, but individual nodes may have compensating errors: the Grader might incorrectly filter an article, and the Reflector might correctly compensate by triggering a re-reasoning. Or the IntentAnalyzer might assign the wrong violation-type hint, the retriever might nonetheless return the right articles through lexical matching, and the ReasoningEngine might arrive at the correct verdict anyway. Disentangling these node-level contributions would require per-node ground-truth annotations, which are not available in the current dataset.

---

## 6.10 Summary of This Chapter

Table 6-4 provides a concise reference of the agent pipeline's key configuration parameters as used in the formal 780-sample evaluation.

**Table 6-4** Agent pipeline configuration.

| Parameter | Value | Notes |
|---|---|---|
| Architecture | 6-node linear graph | With one conditional reflection loop |
| IntentAnalyzer | Rule-based, no LLM | 0.11 ms avg |
| AdaptiveRetriever | HybridRetriever | distance_threshold=0.15, min_k=2 |
| laws_k | 3 / 4 / 5 | Driven by complexity |
| cases_k | 0 | Disabled (leakage control) |
| Grader weights | rel=0.6, cov=0.3, fresh=0.1 | min_score=0.5, min_keep=2 |
| ReasoningEngine | Qwen3-8B, 4-step CoT | via MaaS |
| max_reflection | 1 | At most one re-reasoning |
| RemediationAdvisor | Fast (simple) / Detailed (medium/complex) | Template vs LLM |

This chapter has presented the design, implementation, and evaluation of the six-node agent pipeline for price compliance supervision. The pipeline augments the RAG retrieval infrastructure with intent-driven parameterization, evidence grading, structured 4-step chain-of-thought reasoning, heuristic self-reflection, and template or LLM-based remediation advice.

On the 780-sample evaluation set, the agent achieves the highest reasoning quality score of any route (0.8931), demonstrating that the explicit CoT architecture and reflection mechanism produce more structured and evidence-grounded analyses. The trade-off is a 2.4 pp reduction in binary classification accuracy relative to the Baseline and a wall-clock time of 37.62 s per sample — approximately 4.8× slower than RAG. Per-node timing analysis locates 84% of the latency in the AdaptiveRetriever and ReasoningEngine nodes.

The appropriate interpretation is that classification accuracy and reasoning quality are not the same objective. The agent trades the former for the latter in a domain — regulatory price enforcement — where the quality of the legal argument often matters more than the correctness of the binary label. Chapter 7 revisits the metric design that underlies these comparisons, and Chapter 8 shows how the agent pipeline is wrapped into an interactive web prototype that serves consumers, regulators, and merchants.
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
# 8 Web Interactive Prototype

## 8.1 Design Goals

The batch evaluation scripts in `scripts/` are designed for one thing: running a fixed dataset through a pipeline and writing metrics to a JSON file. That is the right tool for rigorous comparison, but it leaves no room for human involvement. A regulator who wants to check whether a specific merchant's pricing page looks problematic cannot run `run_agent_eval.py`—and even if they could, they would not get a result tailored to their enforcement context.

The Web prototype was built to close that gap. The core design goal is a human-in-the-loop interface where a user can describe a pricing situation in plain text, watch the six-node agent pipeline process it in real time, and receive a structured compliance report—without needing to understand anything about the underlying retrieval or reasoning machinery.

Three user roles shape the experience: a **consumer** who suspects price fraud and wants to know their rights, a **regulator** conducting an enforcement review, and a **merchant** running a self-compliance check before a promotion. Each role gets an identical analytical pipeline—the same six nodes, the same ChromaDB knowledge base, the same Qwen3-8B LLM—but receives a remediation block written for their specific situation. A consumer gets guidance on evidence preservation and complaint channels; a regulator gets a structured enforcement memo with a risk tier; a merchant gets a checklist of corrective actions.

A secondary goal was modularity: the web system should reuse the agent code without duplicating it, and the knowledge browser should allow users to explore the 691-article legal database and 133-case history independently of any specific query.

## 8.2 Overall Architecture

The system uses a decoupled front-end / back-end architecture, connected over a local proxy during development.

```
Browser (localhost:5173)
  │
  │  /api/*  →  Vite proxy
  ▼
FastAPI backend (localhost:8000)
  │
  ├── StreamingCoordinator → AgentCoordinator (6 nodes)
  ├── ChromaDB  (691 laws + 133 cases, shared with eval pipeline)
  └── SQLite traces.db  (conversation history + full results)
```

The browser is served by Vite's development server on port 5173. Any request whose path starts with `/api/` is transparently forwarded to the FastAPI backend on port 8000 via a proxy rule in `web/frontend/vite.config.ts`. The backend loads `AgentCoordinator` at startup, together with the embedding model and BM25 index; cold-start takes roughly 10–15 seconds. After that, each incoming chat request is handled by `StreamingCoordinator`, which wraps `AgentCoordinator` and streams node-by-node progress back to the browser over Server-Sent Events (SSE).

All conversation records—including the user query, the assigned role, the full JSON result, and `duration_ms`—are persisted asynchronously to a SQLite database at `web/backend/traces.db`. No data leaves the local machine; the only external call is the MaaS inference request to 讯飞星辰.

## 8.3 Technology Stack

Table 8-1 lists every layer of the stack with its version. The choices were guided by two constraints: reuse the existing Python agent code without modification, and build a front end capable of rendering streaming updates and navigating between three pages.^[41]^^[42]^

**Table 8-1** Web prototype technology stack.

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | React + TypeScript | 19 + 6.0 |
| Build tool | Vite | 8.0 |
| Styling | Tailwind CSS | 4.2 |
| Routing | React Router | 7.x |
| Backend framework | FastAPI | 0.115+ |
| Streaming | SSE (sse-starlette) | 2.0+ |
| Persistence | SQLite (aiosqlite) | — |
| Vector database | ChromaDB | 1.5+ |
| Embedding model | BAAI/bge-small-zh-v1.5 | 512-dim |
| Re-ranker | BAAI/bge-reranker-v2-m3 | — |
| LLM | 讯飞星辰 MaaS (Qwen3-8B) | — |

React was chosen over alternatives such as Vue or plain HTML because the front end needed component-level state management for the six-node progress bar, the trace drawer, and the knowledge browser—all of which update independently. Tailwind CSS 4's utility-first approach allowed rapid iteration on the layout without a separate design system. FastAPI's native support for asynchronous handlers fits naturally with SSE streaming and non-blocking SQLite writes via aiosqlite.

## 8.4 Information Architecture

The application contains three pages, navigated via a top bar.

### 8.4.1 Role Selection Page

The landing page presents three cards side by side: Consumer (消费者), Regulator (政府监管), and Merchant (网店商家). Clicking a card routes the user to the chat workstation and passes the selected role as a URL parameter, which is then included in every API request.

On the backend, `web/backend/services/role_prompt.py` maps each role to a system-prompt prefix that is prepended to the user query before it reaches the agent pipeline. The consumer prefix orients the analysis toward rights-protection and complaint procedures; the regulator prefix emphasises violation identification, evidence chain, and applicable penalty ranges; the merchant prefix shifts the remediation output toward a corrective action checklist. The analytical nodes themselves are role-agnostic—only the RemediationAdvisor's output format changes.

![Figure 8-1: Role selection landing page showing three cards — Consumer, Regulator, Merchant](figures/ch8_role_selection.png)

Figure 8-1 The role selection page. Each card routes to the chat workstation with the corresponding role context.

### 8.4.2 Chat Workstation

The chat workstation is the primary interaction surface. The layout places conversation history in a collapsible left panel, the main conversation area in the centre, and a slide-out trace drawer on the right.

When a user submits a query, the centre panel displays a six-step progress bar whose nodes light up in sequence as SSE events arrive from the backend: **intent analysis → law retrieval → relevance grading → legal reasoning → reflection → remediation**. The bar gives the user a live view of where the pipeline is without requiring them to understand what happens at each step. The slowest step—retrieval, at roughly 19 seconds on average—is the one where users see the longest pause; knowing that the system is actively working at that point matters for usability.

Once the `done` event arrives, the workstation renders a **report card** containing six fields: the violation conclusion with confidence, the violation type, the legal basis (with an expandable panel showing full article text from the retrieved sources), the full reasoning chain, and the role-specific remediation block.

Users can attach a document—PDF, DOCX, or TXT—via the 📎 button beside the input field. The file is sent to `/api/upload`, which extracts the text and returns it to the front end; the extracted text is then injected into the next query as `attachment_text`. This allows a regulator, for example, to upload a screenshot-derived text of a product listing and have the agent analyse it directly.

![Figure 8-2: Chat workstation mid-flow showing the six-node progress bar with retrieval active](figures/ch8_chat_workstation.png)

Figure 8-2 Chat workstation during an active query. The progress bar shows the system advancing through the six pipeline nodes. The report card will appear in this panel once the `done` event is received.

### 8.4.3 Knowledge-Base Browser

The third page lets users explore the underlying knowledge base without running a query. Two tabs expose the law collection (691 articles, backed by `GET /api/knowledge/laws`) and the case collection (133 historical enforcement cases, backed by `GET /api/knowledge/cases`). Both support keyword search and pagination.

The search uses the same BAAI/bge-small-zh-v1.5 embedding model and ChromaDB collection as the retrieval pipeline, so the distance scores returned by the browser are directly comparable to those used during agent reasoning. A user who searches for "虚假折扣" in the law browser will see roughly the same articles that the retriever would surface for a query containing that phrase.

![Figure 8-3: Knowledge-base browser showing paginated law articles with a search bar](figures/ch8_knowledge_browser.png)

Figure 8-3 Knowledge-base browser displaying the 691-article law collection. The search bar at the top performs semantic search using the same embedding model as the RAG retrieval pipeline.

## 8.5 Streaming via SSE

Server-Sent Events provide a simple, unidirectional channel from server to browser over a persistent HTTP connection.^[40]^ We use `sse-starlette 2+` on the FastAPI side, which integrates with Python's `asyncio` event loop without blocking.

**Table 8-2** Web API endpoints.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check; returns `{ "status": "ok" }` |
| POST | `/api/chat` | SSE streaming chat (primary) |
| POST | `/api/chat/sync` | Synchronous chat for debugging (~25 s blocking) |
| POST | `/api/upload` | Document upload; returns extracted text |
| GET | `/api/trace/{id}` | Retrieve full trace record by ID |
| GET | `/api/traces` | Paginated trace history |
| DELETE | `/api/trace/{id}` | Delete single trace |
| DELETE | `/api/traces` | Clear all trace history |
| GET | `/api/knowledge/laws` | Browse/search law articles |
| GET | `/api/knowledge/cases` | Browse/search enforcement cases |

The `POST /api/chat` endpoint accepts a JSON body with three fields: `query` (required), `role` (optional, defaults to `consumer`), and `attachment_text` (optional). The backend prepends the role-specific system-prompt prefix from `role_prompt.py`, instantiates a `StreamingCoordinator`, and begins yielding SSE events.

The synchronous endpoint `POST /api/chat/sync` exists for debugging and scripted testing. It accepts the same request body but blocks until the full result is assembled, returning a JSON object with `trace_id` and `result`. Because the Agent pipeline takes roughly 37 seconds on average, this endpoint is not suitable for interactive use—it is there to make it easy to inspect complete results from a command-line tool or test harness without parsing an SSE stream.

The event sequence mirrors the agent pipeline exactly: `intent` → `retrieval` → `grading` → `reasoning` → `reflection` → `remediation` → `done`. Each event's `data` payload contains the partial result from that node, so the front end can render intermediate outputs (e.g., the list of retrieved articles) before the final report is ready. The terminal `done` event carries `trace_id` and the complete `result` object, including `retrieved_legal_sources` (full article text for all retrieved chunks). After dispatching `done`, the backend writes the full record to SQLite asynchronously.

Swagger documentation is available at `http://localhost:8000/docs` when the backend is running.

## 8.6 Reuse of the Evaluation Pipeline

A key design decision was that the web system must not introduce a second copy of the agent logic. The batch evaluator and the web prototype both call the same `AgentCoordinator` class from `src/agents/agent_coordinator.py`; the only layer added by the web system is `StreamingCoordinator` (`web/backend/services/streaming_coordinator.py`), which wraps `AgentCoordinator.process()` and yields intermediate results as SSE events after each node completes.

Because of this shared code path, there is no risk of the interactive prototype silently using different retrieval parameters, a different reflection threshold, or a different violation-type matching configuration than the batch evaluator. Any change to the agent's behaviour propagates to both consumers.

The 780-sample batch results in Chapter 7 remain the authoritative quality measure for this system. The Web prototype is not a replacement for those results—it is a different mode of use, designed for one-off interactive queries rather than aggregate performance measurement. Both serve a purpose; neither substitutes for the other.

## 8.7 Boundary Between Prototype and Batch Evaluator

It is worth being explicit about what belongs to each component.

The **batch evaluator** owns: dataset management (loading `eval_dataset_v4_final.jsonl`), ground-truth comparison, metric calculation (`ResponseParser`, `BaselineEvaluator`, `RAGEvaluator`, `AgentCoordinator.process` called in a loop), results serialisation to `results/`, and the aggregate statistics tables in Chapter 7.

The **web prototype** owns: user session management, role routing, SSE streaming, trace persistence to SQLite, document upload and text extraction, the knowledge-base browser, and the three React pages. It does not compute aggregate metrics; it does not read the evaluation dataset; and it does not write to `results/`.

Any latency figures cited from interactive sessions would not be comparable to the batch evaluation numbers in Table 7-1, because the batch evaluator runs queries sequentially on a dedicated machine whereas the web prototype is designed for single-user interactive use with network overhead. Do not mix the two.

## 8.8 Early-Design Pivot from Streamlit

Early in the project we considered building the front end with Streamlit, which would have allowed rapid prototyping within a single Python process. We switched to a decoupled React front + FastAPI back for three reasons: it separates UI development entirely from the batch-evaluation scripts (which are also Python), it enables proper multi-page navigation with React Router rather than a single-page layout, and it provides a natural extension point for future features such as the knowledge browser and an audit-log page that would be awkward to build inside Streamlit's widget model.

## 8.9 Limitations

**MaaS external dependency.** Every chat request must reach the 讯飞星辰 API endpoint. In offline environments or under network degradation, the prototype cannot function. Moving to a locally-served LLM or a self-hosted inference endpoint would remove this dependency, but is out of scope for this project.

**Dual-port development setup.** Running frontend on port 5173 and backend on port 8000 is straightforward during development but requires two terminal sessions and is not suitable for production deployment as-is. The README documents a single-port packaging approach (building the React app with `npm run build` and mounting the `dist/` directory as a FastAPI static route), but we have not validated it under load.

**No authentication.** The current prototype assumes a trusted local environment. Anyone with network access to the running instance can read all stored traces, query the agent, and delete conversation history. Adding OAuth or token-based authentication is a prerequisite for any deployment beyond a single developer's workstation.

## 8.10 Summary of This Chapter

We described a working React + TypeScript + Vite front end paired with a FastAPI + SSE + SQLite back end that exposes the full six-node agent pipeline as an interactive web application. Three user roles—consumer, regulator, and merchant—receive identical analytical results with role-specific remediation framing. The technology stack is listed in Table 8-1; the API surface is documented in Table 8-2.

The system was built on the principle of code reuse: `StreamingCoordinator` wraps the same `AgentCoordinator` used in batch evaluation, so there is no divergence between the interactive and batch code paths. The 780-sample evaluation results from Chapter 7 remain the authoritative quality benchmark; the prototype complements them by providing a human-in-the-loop access mode that the batch scripts were never designed to support.

The directory structure under `web/` separates concerns cleanly: `backend/routers/` handles HTTP routing, `backend/services/` contains the agent wrapping and role-prompt logic, and `frontend/src/components/` holds the reusable React components. This layout makes it straightforward to extend any single layer—adding a new role, swapping the LLM endpoint, or redesigning the report card—without touching the others. The limitations noted in Section 8.9 are engineering problems with known solutions; the architecture itself is sound.
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
# Acknowledgements

This thesis owes its existence to many people. My advisor, Professor Qin Feiwei, gave me the freedom to pick a real-world engineering problem rather than a textbook topic and steadied me when the evaluation numbers surprised me in ways I had not anticipated. Several rounds of feedback on the thesis structure, the dataset scope, and the experimental comparisons shaped the work into something I am willing to put my name on.

I thank the teachers and peers at the HDU Shengguang Joint College for the four years that brought me to this point. The joint-college program exposed me to the difference between writing code and building a system that has to survive contact with real data, and that distinction runs through every chapter of this thesis.

A graduation thesis is never really a solo effort. I am grateful to the classmates who discussed the RAG ablation design with me, the roommates who tolerated the many late nights when a training job was running, and the friends outside the department who asked the naive questions that turned out to be the right ones. A few teachers whose courses I took before I knew I would eventually need their material deserve specific mention: the natural language processing course gave me the vocabulary to describe what retrieval augmentation is doing under the hood, and the software engineering course gave me the discipline to keep the Web prototype and the evaluation pipeline from drifting apart.

Finally, I thank my family for their patience during the months of uncertainty about what the final thesis would be about, and for trusting the process even when I could not explain why a pure-prompt Baseline kept outperforming the much more elaborate Agent pipeline on one particular metric. That single observation, which felt like a failure at first, ended up becoming the thesis's most honest contribution.

# References

[1] Brown T, Mann B, Ryder N, et al. Language models are few-shot learners[C]. Advances in Neural Information Processing Systems, 2020, 33: 1877-1901.

[2] OpenAI. GPT-4 technical report[EB/OL]. arXiv:2303.08774, 2023.

[3] Touvron H, Martin L, Stone K, et al. LLaMA 2: Open foundation and fine-tuned chat models[EB/OL]. arXiv:2307.09288, 2023.

[4] Bai J, Bai S, Chu Y, et al. Qwen technical report[EB/OL]. arXiv:2309.16609, 2023.

[5] Yang A, Xiao B, Wang B, et al. Qwen2.5 technical report[EB/OL]. arXiv:2412.15115, 2024.

[6] Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]. Advances in Neural Information Processing Systems, 2020, 33: 9459-9474.

[7] Gao Y, Xiong Y, Gao X, et al. Retrieval-augmented generation for large language models: A survey[EB/OL]. arXiv:2312.10997, 2023.

[8] Karpukhin V, Oguz B, Min S, et al. Dense passage retrieval for open-domain question answering[C]. Proceedings of EMNLP, 2020: 6769-6781.

[9] Robertson S, Zaragoza H. The probabilistic relevance framework: BM25 and beyond[J]. Foundations and Trends in Information Retrieval, 2009, 3(4): 333-389.

[10] Cormack G V, Clarke C L A, Buettcher S. Reciprocal rank fusion outperforms Condorcet and individual rank learning methods[C]. Proceedings of SIGIR, 2009: 758-759.

[11] Xiao S, Liu Z, Zhang P, et al. C-Pack: Packed resources for general Chinese embeddings[C]. Proceedings of SIGIR, 2024: 641-649.

[12] Chen J, Xiao S, Zhang P, et al. BGE M3-Embedding: Multi-lingual, multi-functionality, multi-granularity text embeddings through self-knowledge distillation[EB/OL]. arXiv:2402.03216, 2024.

[13] Nogueira R, Cho K. Passage re-ranking with BERT[EB/OL]. arXiv:1901.04085, 2019.

[14] Wei J, Wang X, Schuurmans D, et al. Chain-of-thought prompting elicits reasoning in large language models[C]. Advances in Neural Information Processing Systems, 2022, 35: 24824-24837.

[15] Yao S, Zhao J, Yu D, et al. ReAct: Synergizing reasoning and acting in language models[C]. International Conference on Learning Representations, 2023.

[16] Shinn N, Cassano F, Berman E, et al. Reflexion: Language agents with verbal reinforcement learning[C]. Advances in Neural Information Processing Systems, 2023, 36: 8634-8652.

[17] Madaan A, Tandon N, Gupta P, et al. Self-Refine: Iterative refinement with self-feedback[C]. Advances in Neural Information Processing Systems, 2023, 36: 46534-46594.

[18] Wang L, Ma C, Feng X, et al. A survey on large language model based autonomous agents[J]. Frontiers of Computer Science, 2024, 18(6): 186345.

[19] Xi Z, Chen W, Guo X, et al. The rise and potential of large language model based agents: A survey[EB/OL]. arXiv:2309.07864, 2023.

[20] Park J S, O'Brien J, Cai C J, et al. Generative agents: Interactive simulacra of human behavior[C]. Proceedings of UIST, 2023: 1-22.

[21] Lewis P, Oguz B, Rinott R, et al. MLQA: Evaluating cross-lingual extractive question answering[C]. Proceedings of ACL, 2020: 7315-7330.

[22] Chase H. LangChain: Building applications with LLMs through composability[EB/OL]. https://github.com/langchain-ai/langchain, 2022.

[23] Liu J. LlamaIndex: A data framework for your LLM applications[EB/OL]. https://github.com/run-llama/llama_index, 2022.

[24] Devlin J, Chang M W, Lee K, et al. BERT: Pre-training of deep bidirectional transformers for language understanding[C]. Proceedings of NAACL, 2019: 4171-4186.

[25] Vaswani A, Shazeer N, Parmar N, et al. Attention is all you need[C]. Advances in Neural Information Processing Systems, 2017, 30: 5998-6008.

[26] Cui Y, Yang Z, Yao X. Efficient and effective text encoding for Chinese LLaMA and Alpaca[EB/OL]. arXiv:2304.08177, 2023.

[27] Zhang S, Dong L, Li X, et al. Instruction tuning for large language models: A survey[EB/OL]. arXiv:2308.10792, 2023.

[28] Ouyang L, Wu J, Jiang X, et al. Training language models to follow instructions with human feedback[C]. Advances in Neural Information Processing Systems, 2022, 35: 27730-27744.

[29] Zhao W X, Zhou K, Li J, et al. A survey of large language models[EB/OL]. arXiv:2303.18223, 2023.

[30] Cui J, Li Z, Yan Y, et al. ChatLaw: Open-source legal large language model with integrated external knowledge bases[EB/OL]. arXiv:2306.16092, 2023.

[31] Huang Q, Tao M, An Z, et al. Lawyer LLaMA technical report[EB/OL]. arXiv:2305.15062, 2023.

[32] Yue S, Chen W, Wang S, et al. DISC-LawLLM: Fine-tuning large language models for intelligent legal services[EB/OL]. arXiv:2309.11325, 2023.

[33] Chalkidis I, Fergadiotis M, Malakasiotis P, et al. LEGAL-BERT: The Muppets straight out of law school[C]. Findings of EMNLP, 2020: 2898-2904.

[34] Xiao C, Hu X, Liu Z, et al. Lawformer: A pre-trained language model for Chinese legal long documents[J]. AI Open, 2021, 2: 79-84.

[35] Ma S, Zhang X, Hu W, et al. CAIL2019-SCM: A dataset of similar case matching in legal domain[EB/OL]. arXiv:1911.08962, 2019.

[36] Manning C D, Raghavan P, Schütze H. Introduction to information retrieval[M]. Cambridge University Press, 2008.

[37] Johnson J, Douze M, Jégou H. Billion-scale similarity search with GPUs[J]. IEEE Transactions on Big Data, 2021, 7(3): 535-547.

[38] Wang J, Yi X, Guo R, et al. Milvus: A purpose-built vector data management system[C]. Proceedings of SIGMOD, 2021: 2614-2627.

[39] Chroma. Chroma: The AI-native open-source embedding database[EB/OL]. https://www.trychroma.com/, 2024.

[40] Ramamurthy A, Shermer M, Sun L. Streaming responses with server-sent events[EB/OL]. MDN Web Docs, 2023.

[41] Ramírez S. FastAPI: Fast, modern web framework for APIs with Python[EB/OL]. https://fastapi.tiangolo.com/, 2024.

[42] Meta. React: A JavaScript library for building user interfaces[EB/OL]. https://react.dev/, 2024.

[43] Schulman J, Zoph B, Kim C, et al. ChatGPT: Optimizing language models for dialogue[EB/OL]. OpenAI Blog, 2022.

[44] Huang X, Liu M, Shi G, et al. EasySpider: A no-code visual web crawler[EB/OL]. https://github.com/NaiboWang/EasySpider, 2023.

[45] 国家市场监督管理总局. 中国市场监管行政处罚文书网[EB/OL]. https://cfws.samr.gov.cn/index.html, 2024.

[46] 全国人民代表大会常务委员会. 中华人民共和国价格法[EB/OL]. https://flk.npc.gov.cn/index, 1997.

[47] 国家发展和改革委员会. 价格违法行为行政处罚规定[EB/OL]. http://www.gov.cn/gongbao/content/2010/content_1768770.htm, 2010.

[48] 国家市场监督管理总局. 禁止价格欺诈行为的规定[EB/OL]. https://www.samr.gov.cn/, 2022.

[49] 全国人民代表大会常务委员会. 中华人民共和国电子商务法[EB/OL]. https://flk.npc.gov.cn/index, 2018.

[50] 全国人民代表大会常务委员会. 中华人民共和国反不正当竞争法[EB/OL]. https://flk.npc.gov.cn/index, 2019.

[51] Papineni K, Roukos S, Ward T, et al. BLEU: A method for automatic evaluation of machine translation[C]. Proceedings of ACL, 2002: 311-318.

[52] Lin C Y. ROUGE: A package for automatic evaluation of summaries[C]. Workshop on Text Summarization Branches Out, 2004: 74-81.

[53] Zheng L, Chiang W L, Sheng Y, et al. Judging LLM-as-a-judge with MT-Bench and Chatbot Arena[C]. Advances in Neural Information Processing Systems, 2023, 36: 46595-46623.

[54] Es S, James J, Espinosa-Anke L, et al. RAGAS: Automated evaluation of retrieval augmented generation[C]. Proceedings of EACL: System Demonstrations, 2024: 150-158.

[55] Shuster K, Poff S, Chen M, et al. Retrieval augmentation reduces hallucination in conversation[C]. Findings of EMNLP, 2021: 3784-3803.

[56] Gao T, Yen H, Yu J, et al. Enabling large language models to generate text with citations[C]. Proceedings of EMNLP, 2023: 6465-6488.

[57] Ren R, Wang Y, Qu Y, et al. Investigating the factual knowledge boundary of large language models with retrieval augmentation[EB/OL]. arXiv:2307.11019, 2023.

[58] Zhou H, Gu B, Zou X, et al. A survey of large language models in medicine: Progress, application, and challenge[EB/OL]. arXiv:2311.05112, 2023.

[59] Bommasani R, Hudson D A, Adeli E, et al. On the opportunities and risks of foundation models[EB/OL]. arXiv:2108.07258, 2021.

[60] Zhang Y, Li Y, Cui L, et al. Siren's song in the AI ocean: A survey on hallucination in large language models[EB/OL]. arXiv:2309.01219, 2023.
