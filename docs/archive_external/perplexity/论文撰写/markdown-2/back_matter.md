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
