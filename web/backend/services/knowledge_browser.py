"""知识库浏览 - 分页查询 ChromaDB 中的法规和案例"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import chromadb
from ..config import CHROMA_DB_PATH

# 向量库构建与 HybridRetriever 使用 BAAI/bge-small-zh-v1.5（512 维）。
# 若使用 collection.query(query_texts=...)，Chroma 会改用内置默认嵌入（常见为 384 维），
# 会触发 InvalidArgumentError: expecting 512, got 384。


class KnowledgeBrowser:

    def __init__(
        self,
        db_path: str = CHROMA_DB_PATH,
        embed_query: Callable[[str], Any] | None = None,
    ):
        self.client = chromadb.PersistentClient(path=db_path)
        self.laws_collection = self.client.get_collection("price_regulation_laws")
        self.cases_collection = self.client.get_collection("price_regulation_cases")
        self._embed_query = embed_query
        self._fallback_embedder = None

    def _encode_query(self, q: str) -> list[float]:
        if self._embed_query is not None:
            vec = self._embed_query(q)
            if hasattr(vec, "tolist"):
                return vec.tolist()
            return list(vec)
        if self._fallback_embedder is None:
            from src.rag.embedder import EmbedderModel

            self._fallback_embedder = EmbedderModel()
        return self._fallback_embedder.encode([q])[0]

    def browse(self, collection_name: str, page: int = 1, page_size: int = 20, q: str | None = None):
        collection = self.laws_collection if collection_name == "laws" else self.cases_collection
        total = collection.count()

        if q and (q_stripped := q.strip()):
            emb = self._encode_query(q_stripped)
            results = collection.query(
                query_embeddings=[emb],
                n_results=min(page_size, total or 1),
            )
            ids = results["ids"][0] if results["ids"] else []
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            items = [
                {"chunk_id": ids[i], "content": docs[i], "metadata": metas[i] or {}}
                for i in range(len(ids))
            ]
            return {"items": items, "total": len(items), "page": 1, "page_size": page_size}

        offset = (page - 1) * page_size
        results = collection.get(limit=page_size, offset=offset, include=["documents", "metadatas"])
        ids = results["ids"] or []
        docs = results["documents"] or []
        metas = results["metadatas"] or []
        items = [
            {"chunk_id": ids[i], "content": docs[i], "metadata": metas[i] or {}}
            for i in range(len(ids))
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
