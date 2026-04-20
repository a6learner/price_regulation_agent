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
