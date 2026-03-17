"""诊断 Reranker 在实际RAG场景中的问题"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*60)
print("模拟实际RAG场景测试")
print("="*60)

print("\n[1/6] 加载 SentenceTransformer (BGE embedder)...")
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer('BAAI/bge-small-zh-v1.5')
print("  [OK] Embedder加载成功")

print("\n[2/6] 加载向量数据库...")
from src.rag.vector_db import VectorDatabase
db = VectorDatabase("data/rag/chroma_db")
db.create_collections()
print("  [OK] VectorDB加载成功")

print("\n[3/6] 构建BM25索引...")
from rank_bm25 import BM25Okapi
all_laws = db.laws_collection.get()
if all_laws and all_laws['documents']:
    laws_corpus = all_laws['documents']
    laws_tokenized = [doc.split() for doc in laws_corpus]
    bm25 = BM25Okapi(laws_tokenized)
    print(f"  [OK] BM25索引构建成功 ({len(laws_corpus)} 条法律)")

print("\n[4/6] 现在加载 CrossEncoder reranker...")
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')
print("  [OK] Reranker加载成功")

print("\n[5/6] 模拟实际检索场景...")
query = "商品标注原价899元，实际从未销售"
query_embedding = embedder.encode([query])[0]

# 检索法律
laws_results = db.laws_collection.query(
    query_embeddings=[query_embedding],
    n_results=9  # 3x multiplier
)

print(f"  [OK] 检索到 {len(laws_results['ids'][0])} 条法律")

# 格式化结果
laws = []
for i in range(len(laws_results['ids'][0])):
    laws.append({
        'content': laws_results['documents'][0][i],
        'metadata': laws_results['metadatas'][0][i],
        'distance': laws_results['distances'][0][i]
    })

print(f"  [INFO] 第一条法律长度: {len(laws[0]['content'])} 字符")
print(f"  [INFO] 最长法律长度: {max(len(l['content']) for l in laws)} 字符")

print("\n[6/6] 使用 reranker 重排序...")
try:
    pairs = [[query, law['content']] for law in laws]
    print(f"  [INFO] 准备重排序 {len(pairs)} 个pairs")
    print("  [INFO] 调用 reranker.predict()...")

    scores = reranker.predict(pairs, show_progress_bar=False)

    print(f"  [OK] Reranking成功！")
    print(f"  [INFO] Scores: {scores[:3]}")

except Exception as e:
    print(f"  [ERROR] Reranking失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("[SUCCESS] 实际场景测试通过！")
print("="*60)
print("\n[结论] Reranker在实际RAG场景中也能正常工作。")
print("[建议] 问题可能出在RAGEvaluator的其他部分，而非Reranker本身。")
