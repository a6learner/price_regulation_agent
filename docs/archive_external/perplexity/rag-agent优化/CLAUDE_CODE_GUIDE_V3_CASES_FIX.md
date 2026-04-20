# CLAUDE_CODE_GUIDE_V3: 移除 Cases 索引注入

> 目标：消除 RAG/Agent 评测中的案例同源污染
> 改动量：2 个文件、~6 行代码
> 优先级：P0（在正式评测前必须完成）

---

## 背景

经排查，当前 ChromaDB 的 `price_regulation_cases` collection（133条）中有 8 条与 `eval_dataset_v4_final.jsonl`（500条违规）来源重叠。且同类型处罚文书的事实描述高度相似，存在隐性泄漏风险。

**解决方案**：将 `cases_k` 强制设为 0，不再向 LLM prompt 注入历史案例。法规条文索引（691条 `price_regulation_laws`）不受影响。

---

## 修改 1：`src/agents/intent_analyzer.py`

找到 `_decide_topk` 方法，把所有 `cases_k` 改为 0：

```python
# 修改前
def _decide_topk(self, complexity):
    if complexity == 'complex':
        return 5, 7
    elif complexity == 'medium':
        return 4, 5
    else:
        return 3, 4

# 修改后
def _decide_topk(self, complexity):
    """cases_k=0: 移除案例注入，避免同源污染"""
    if complexity == 'complex':
        return 5, 0
    elif complexity == 'medium':
        return 4, 0
    else:
        return 3, 0
```

## 修改 2：`src/rag/retriever.py`

找到 `retrieve` 方法中查询 cases 的部分（约 L35-38），加一个短路判断：

```python
# 修改前
cases_results = self.db.cases_collection.query(
    query_embeddings=[query_embedding],
    n_results=cases_k * 2
)

# 修改后
if cases_k == 0:
    cases_results = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
else:
    cases_results = self.db.cases_collection.query(
        query_embeddings=[query_embedding],
        n_results=cases_k * 2
    )
```

---

## 不需要改的地方

- **prompt_template（RAG）**：`_format_cases_context` 已有兜底，空列表返回"暂无相似案例"
- **reasoning_engine（Agent）**：`_format_cases` 已有兜底，空列表返回"（暂无相似案例）"
- **ChromaDB 本身**：不需要删除 collection，只是不再查询
- **eval 脚本**：不涉及 cases_k 参数

---

## 验证

修改完成后运行：

```bash
# 验证 IntentAnalyzer 的 cases_k 全部为 0
python -c "
from src.agents.intent_analyzer import IntentAnalyzer
ia = IntentAnalyzer()
for c in ['simple', 'medium', 'complex']:
    result = ia.analyze('测试案例')
    # 直接调用内部方法验证
    laws_k, cases_k = ia._decide_topk(c)
    assert cases_k == 0, f'{c}: cases_k={cases_k}, expected 0'
    print(f'{c}: laws_k={laws_k}, cases_k={cases_k} ✓')
print('IntentAnalyzer OK')
"

# 验证 Retriever 对 cases_k=0 不报错
python -c "
from src.rag.retriever import HybridRetriever
r = HybridRetriever()
result = r.retrieve('不明码标价测试', laws_k=3, cases_k=0)
assert len(result['cases']) == 0, f'Expected 0 cases, got {len(result[\"cases\"])}'
assert len(result['laws']) > 0, 'Should still return laws'
print(f'laws={len(result[\"laws\"])}, cases={len(result[\"cases\"])} ✓')
print('Retriever cases_k=0 OK')
"
```

---

## 论文写法（实验设置章节加一句）

> 为避免案例索引与评测集之间的同源污染（经排查，133条案例索引中有8条与评测集来源PDF重叠），RAG和Agent系统的正式评测均仅使用法规条文索引（691条），不注入历史处罚案例。
