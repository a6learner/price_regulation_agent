import jieba
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from .local_model_paths import resolve_st_model
from .vector_db import VectorDatabase

_EMBED_HUB = "BAAI/bge-small-zh-v1.5"
_RERANK_HUB = "BAAI/bge-reranker-v2-m3"


class HybridRetriever:
    """混合检索：语义（Chroma）+ 可选 BM25（RRF）+ 可选 CrossEncoder 重排。

    use_semantic=False 且 use_bm25=True 时为 **仅 BM25** 路径（用于消融）。
    """

    def __init__(
        self,
        db_path="data/rag/chroma_db",
        use_reranker=True,
        use_bm25=True,
        use_semantic=True,
    ):
        self.use_semantic = use_semantic
        self._use_reranker = use_reranker
        self._embedder = None
        self._reranker = None
        self.db = VectorDatabase(db_path)
        self.db.create_collections()

        # Build BM25 index for laws
        self.bm25 = None
        self.laws_corpus_ids = []
        if use_bm25:
            all_laws = self.db.laws_collection.get()
            if all_laws and all_laws['documents']:
                self.laws_corpus = all_laws['documents']
                self.laws_corpus_ids = all_laws['ids']
                self.laws_tokenized = [list(jieba.cut(doc)) for doc in self.laws_corpus]
                self.bm25 = BM25Okapi(self.laws_tokenized)

    @property
    def embedder(self):
        """延迟加载，避免仅 BM25 消融仍访问 HuggingFace。"""
        if self._embedder is None:
            mid = resolve_st_model(
                "PRICE_REG_EMBEDDING_MODEL", _EMBED_HUB, "bge-small-zh-v1.5"
            )
            self._embedder = SentenceTransformer(mid)
        return self._embedder

    @property
    def reranker(self):
        """延迟加载 CrossEncoder。"""
        if not self._use_reranker:
            return None
        if self._reranker is None:
            mid = resolve_st_model(
                "PRICE_REG_RERANKER_MODEL", _RERANK_HUB, "bge-reranker-v2-m3"
            )
            self._reranker = CrossEncoder(mid)
        return self._reranker

    def _laws_from_bm25_only(self, query: str, n_candidates: int):
        """仅 BM25：按得分取 top id，再从 Chroma 取正文；distance 置为固定低值以通过阈值过滤。"""
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:n_candidates]
        ordered_ids = []
        seen = set()
        for i in top_bm25_indices:
            cid = self.laws_corpus_ids[i]
            if cid not in seen:
                seen.add(cid)
                ordered_ids.append(cid)
        if not ordered_ids:
            return []
        raw = self.db.laws_collection.get(ids=ordered_ids)
        id_to_row = {}
        for cid, doc, meta in zip(raw['ids'], raw['documents'], raw['metadatas']):
            id_to_row[cid] = (doc, meta or {})
        laws = []
        for cid in ordered_ids:
            row = id_to_row.get(cid)
            if not row:
                continue
            doc, meta = row
            laws.append({
                'content': doc,
                'metadata': meta,
                'distance': 0.05,
            })
        return laws

    def retrieve(self, query, laws_k=3, cases_k=3,
                 distance_threshold=0.15, min_k=2, min_rerank_score=0.0):
        # 仅当需要向量检索案例或语义搜法规时才加载/调用 embedder（HF 可能不稳定）
        need_vec = self.use_semantic or cases_k > 0
        query_embedding = None
        if need_vec:
            query_embedding = self.embedder.encode([query])[0]

        recall_multiplier = 3 if self._use_reranker else 2
        n_cand = laws_k * recall_multiplier

        if cases_k == 0:
            cases_results = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        else:
            cases_results = self.db.cases_collection.query(
                query_embeddings=[query_embedding],
                n_results=cases_k * 2
            )

        if not self.use_semantic:
            if not self.bm25:
                raise ValueError("HybridRetriever: use_semantic=False 时必须启用 use_bm25")
            laws = self._laws_from_bm25_only(query, n_cand)
        else:
            semantic_laws_results = self.db.laws_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_cand
            )

            bm25_law_ids = []
            if self.bm25:
                tokenized_query = list(jieba.cut(query))
                bm25_scores = self.bm25.get_scores(tokenized_query)
                top_bm25_indices = sorted(
                    range(len(bm25_scores)),
                    key=lambda i: bm25_scores[i],
                    reverse=True
                )[:n_cand]
                bm25_law_ids = [self.laws_corpus_ids[i] for i in top_bm25_indices]

            laws = self._format_results(semantic_laws_results)

            if self.bm25 and bm25_law_ids:
                # RRF scores (k=60 standard)
                rrf_scores = {}
                semantic_ids = [l['metadata'].get('chunk_id', '') for l in laws]

                # Phase 4.2: Restored RRF weights (BM25=1.0, Semantic=0.7)
                for rank, law_id in enumerate(semantic_ids):
                    rrf_scores[law_id] = rrf_scores.get(law_id, 0) + 0.7 / (60 + rank + 1)

                for rank, law_id in enumerate(bm25_law_ids):
                    rrf_scores[law_id] = rrf_scores.get(law_id, 0) + 1.0 / (60 + rank + 1)

                laws_with_rrf = []
                for law in laws:
                    law_id = law['metadata'].get('chunk_id', '')
                    law['rrf_score'] = rrf_scores.get(law_id, 0)
                    laws_with_rrf.append(law)

                laws = sorted(laws_with_rrf, key=lambda x: x.get('rrf_score', 0), reverse=True)

        cases = self._format_results(cases_results)

        # Stage 2: Rerank with cross-encoder (if enabled)
        if self.reranker and laws:
            pairs = [[query, law['content']] for law in laws]
            scores = self.reranker.predict(pairs)

            # Sort by reranker scores and filter by min_rerank_score
            reranked_laws = sorted(
                zip(laws, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # Apply reranker score filtering (Phase 4.1)
            if min_rerank_score > 0:
                laws = [law for law, score in reranked_laws if score >= min_rerank_score]
            else:
                laws = [law for law, score in reranked_laws]

            # Store reranker scores in metadata for debugging
            for i, (law, score) in enumerate(reranked_laws):
                if i < len(laws):
                    laws[i]['rerank_score'] = float(score)

        # Filter by distance threshold
        filtered_laws = [l for l in laws if l['distance'] < distance_threshold]
        filtered_cases = [c for c in cases if c['distance'] < distance_threshold]

        # Ensure minimum results
        if len(filtered_laws) < min_k and len(laws) >= min_k:
            filtered_laws = laws[:min_k]
        if len(filtered_cases) < min_k and len(cases) >= min_k:
            filtered_cases = cases[:min_k]

        # Dynamic Top-K: adjust based on average distance
        if filtered_laws:
            avg_distance = sum(l['distance'] for l in filtered_laws[:3]) / min(3, len(filtered_laws))
            if avg_distance < 0.10:
                filtered_laws = filtered_laws[:2]
            elif avg_distance < 0.15:
                filtered_laws = filtered_laws[:3]
            else:
                filtered_laws = filtered_laws[:laws_k]

        return {
            'laws': filtered_laws,
            'cases': filtered_cases[:cases_k],
            'metadata': {
                'laws_count': len(filtered_laws),
                'cases_count': len(filtered_cases[:cases_k]),
                'avg_laws_distance': sum(l['distance'] for l in filtered_laws) / len(filtered_laws) if filtered_laws else 0,
                'reranker_used': self.reranker is not None
            }
        }

    def _format_results(self, results):
        if not results['ids'] or not results['ids'][0]:
            return []

        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            })
        return formatted
