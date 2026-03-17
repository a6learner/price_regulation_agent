import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.vector_db import VectorDatabase
from src.rag.embedder import EmbedderModel


def main():
    db = VectorDatabase()
    db.create_collections()
    embedder = EmbedderModel()

    # 加载法律数据
    laws = []
    with open("data/rag/laws_chunks.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            laws.append(json.loads(line))

    # 向量化并添加到laws_collection
    print(f"正在向量化 {len(laws)} 条法律...")
    texts = [law['content'] for law in laws]
    embeddings = embedder.encode(texts)

    def clean_metadata(meta):
        return {k: v for k, v in meta.items() if v}

    db.add_documents(
        collection_name="laws",
        ids=[law['chunk_id'] for law in laws],
        documents=texts,
        embeddings=embeddings,
        metadatas=[clean_metadata({
            'law_name': law['law_name'],
            'law_level': law.get('law_level', ''),
            'article': law.get('article', '')
        }) for law in laws]
    )

    # 加载案例数据
    cases = []
    with open("data/rag/cases_chunks.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            cases.append(json.loads(line))

    # 向量化并添加到cases_collection
    print(f"正在向量化 {len(cases)} 个案例...")
    texts = [case['content'] for case in cases]
    embeddings = embedder.encode(texts)

    db.add_documents(
        collection_name="cases",
        ids=[case['chunk_id'] for case in cases],
        documents=texts,
        embeddings=embeddings,
        metadatas=[clean_metadata({
            'violation_type': case.get('violation_type', ''),
            'platform': case.get('platform', '')
        }) for case in cases]
    )

    print("\n向量数据库构建完成！")
    print(f"- Laws: {db.laws_collection.count()} 条")
    print(f"- Cases: {db.cases_collection.count()} 个")


if __name__ == '__main__':
    main()
