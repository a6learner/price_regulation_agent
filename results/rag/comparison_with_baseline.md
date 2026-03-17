# RAG vs Baseline 对比报告

**模型**: Qwen3-8B
**评估案例数**: 159
**评估日期**: 2026-03-16

---

## 核心指标对比

| Metric                  | Baseline | RAG      | Improvement |
|-------------------------|----------|----------|-------------|
| **Accuracy**            | 99.35%   | 99.36%   | **+0.01%**  |
| **Legal Basis Quality** | 89.48%   | 78.34%   | **-11.14%** ⚠️ |
| **Reasoning Quality**   | 91.57%   | 92.87%   | **+1.30%**  |

---

## 结论

⚠️ **需要优化：Legal Basis Quality未达预期目标**

### 关键发现

1. **准确率维持**: RAG系统成功维持了99%+的准确率（99.36%），与baseline几乎持平
2. **推理质量提升**: 从91.57%提升至92.87%（+1.30%），说明检索到的案例提供了有价值的推理模板
3. **法律依据质量下降**: 从89.48%降至78.34%（-11.14%），这是需要重点优化的问题

---

## 问题分析：为什么Legal Basis Quality下降？

### 可能原因

1. **检索噪音**
   - Top-3法律检索可能引入了不相关的法条
   - 距离阈值没有设置，可能包含低相似度结果

2. **Prompt过载**
   - RAG上下文（3条法律+5个案例）可能让模型"注意力分散"
   - 模型倾向引用检索内容而非最精确的法条

3. **法条切分粒度问题**
   - 按条款切分可能导致上下文不完整
   - 某些法条需要连续多个条款才能完整表达

4. **质量评分算法局限**
   - 当前评分基于关键词匹配
   - RAG可能引用更完整但不同表述的法律条文，被错误扣分

---

## 优化建议

### 短期优化（立即可行）

1. **调整Top-K参数**
   ```python
   # 当前: laws_k=3, cases_k=5
   # 建议: laws_k=2, cases_k=3  (减少噪音)
   ```

2. **添加相似度过滤**
   ```python
   # 只保留distance < 0.15的结果
   laws = [l for l in laws_results if l['distance'] < 0.15]
   ```

3. **优化Prompt结构**
   - 明确指示模型"优先引用检索到的法律条文"
   - 添加示例说明如何正确引用

### 中期优化（需要实验）

4. **引入Reranking**
   ```bash
   uv add sentence-transformers  # bge-reranker-base
   ```
   - 对Top-10结果进行二次排序
   - 选择Top-3最相关的

5. **调整切分粒度**
   - 实验"段落级"切分（多个条款合并）
   - 或添加"上下文窗口"（包含前后条款）

6. **改进质量评分**
   - 使用LLM评估法律引用质量
   - 或人工标注100个case建立评分标准

---

## 详细性能数据

### 分类指标

| Metric    | Baseline | RAG   | Change |
|-----------|----------|-------|--------|
| Accuracy  | 99.35%   | 99.36% | +0.01% |
| Precision | 98.99%   | 99.00% | +0.01% |
| Recall    | 100.00%  | 100.00% | 0.00% |
| F1 Score  | 99.49%   | 99.50% | +0.01% |

### 质量指标

| Metric              | Baseline | RAG   | Change  |
|---------------------|----------|-------|---------|
| Legal Basis Quality | 89.48%   | 78.34% | **-11.14%** |
| Reasoning Quality   | 91.57%   | 92.87% | **+1.30%** |

### 性能指标

| Metric           | Baseline | RAG    | Change |
|------------------|----------|--------|--------|
| Avg Response Time | 6.16s    | 6.82s  | +0.66s |
| Total Tokens     | 110K     | 225K   | +115K  |

**成本分析**:
- 响应时间增加10.7%（主要是向量检索+embedding开销）
- Token使用增加104%（RAG上下文大幅增加输入token）

---

## 论文价值与启示

### 正面发现

1. **准确率维持**: RAG没有影响核心分类准确率（99.36% vs 99.35%）
2. **推理提升**: 检索到的案例确实帮助了推理质量（+1.30%）
3. **系统可行性**: RAG技术栈（BGE+Chroma）运行稳定，无崩溃

### 关键教训

**教训1**: RAG不是万能的，引入检索可能带来噪音
- 需要精细调参（Top-K, 相似度阈值）
- 需要质量评估机制（过滤低质量检索）

**教训2**: 小模型的"注意力"有限
- Qwen3-8B处理长上下文时可能顾此失彼
- 应该"少而精"而非"多而全"

**教训3**: 评估指标需要多维度
- Legal Basis Quality下降暴露了问题
- 如果只看Accuracy会错过关键缺陷

---

## 下一步行动

### 立即执行

1. ✅ **调整Top-K**: `laws_k=2, cases_k=3`
2. ✅ **添加距离过滤**: `distance < 0.15`
3. ✅ **优化Prompt**: 增强法律引用指导

### 待验证

4. ⏸️ **Reranking实验**: 引入bge-reranker-base
5. ⏸️ **切分粒度实验**: 段落级 vs 条款级
6. ⏸️ **质量评分改进**: LLM-based评分

### 论文撰写建议

**不要回避问题**:
- 诚实报告Legal Basis Quality下降
- 分析原因并提出改进方向
- 展示迭代优化的过程

**突出价值**:
- RAG系统的设计与实现
- 多维度评估方法论
- 问题诊断与优化思路

**结论导向**:
- "通过参数优化，RAG法律依据质量提升至XX%"
- "实验证明：检索增强需要精细调参才能发挥价值"

---

## 附录：运行命令

### 重新评估（优化后）

```bash
cd price_regulation_agent

# 修改retriever.py中的参数
# laws_k=2, cases_k=3
# 添加distance过滤

# 重新运行评估
uv run python scripts/run_rag_eval.py \
  --model qwen-8b \
  --eval-data data/eval/eval_159.jsonl \
  --output results/rag/qwen-8b-rag_optimized_results.json \
  --compare-with-baseline
```

### 查看结果

```bash
# Windows
type results\rag\qwen-8b-rag_results.json
type results\rag\comparison_with_baseline.md
```

---

**生成时间**: 2026-03-16
**RAG系统版本**: v1.0 (Baseline)
**向量数据库**: Chroma (691 laws + 133 cases)
**Embedding模型**: BAAI/bge-small-zh-v1.5
