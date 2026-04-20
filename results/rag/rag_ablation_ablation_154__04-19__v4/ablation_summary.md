# RAG 检索消融汇总
- 数据: `data/eval/eval_dataset_v4_final.jsonl` 前 **154** 条
- 模型: `qwen-8b`
- 输出目录: `results\rag\rag_ablation_ablation_154__04-19__v4`

| 变体 | Accuracy | F1 | Type Acc | 平均耗时s |
|---|---:|---:|---:|---:|
| bm25_only | 0.8766 | 0.9319 | 0.5844 | 7.93 |
| semantic_only | 0.8831 | 0.9357 | 0.6039 | 8.17 |
| rrf | 0.8896 | 0.9395 | 0.5909 | 8.12 |
| rrf_rerank | 0.9026 | 0.9470 | 0.6299 | 8.11 |
