from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from .vector_db import VectorDatabase


class HybridRetriever:
    def __init__(self, db_path="data/rag/chroma_db", use_reranker=True, use_bm25=True):
        self.db = VectorDatabase(db_path)
        self.db.create_collections()
        self.embedder = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        self.reranker = CrossEncoder('BAAI/bge-reranker-v2-m3') if use_reranker else None

        # Build BM25 index for laws
        self.bm25 = None
        self.laws_corpus_ids = []
        if use_bm25:
            all_laws = self.db.laws_collection.get()
            if all_laws and all_laws['documents']:
                self.laws_corpus = all_laws['documents']
                self.laws_corpus_ids = all_laws['ids']
                self.laws_tokenized = [doc.split() for doc in self.laws_corpus]
                self.bm25 = BM25Okapi(self.laws_tokenized)

    def retrieve(self, query, laws_k=3, cases_k=5,
                 distance_threshold=0.15, min_k=2):
        query_embedding = self.embedder.encode([query])[0]

        # Stage 1: Recall - retrieve more candidates
        recall_multiplier = 3 if self.reranker else 2
        semantic_laws_results = self.db.laws_collection.query(
            query_embeddings=[query_embedding],
            n_results=laws_k * recall_multiplier
        )

        cases_results = self.db.cases_collection.query(
            query_embeddings=[query_embedding],
            n_results=cases_k * 2
        )

        # BM25 search (if enabled)
        bm25_law_ids = []
        if self.bm25:
            tokenized_query = query.split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:laws_k * recall_multiplier]
            bm25_law_ids = [self.laws_corpus_ids[i] for i in top_bm25_indices]

        # RRF Fusion: combine semantic + BM25
        laws = self._format_results(semantic_laws_results)

        if self.bm25 and bm25_law_ids:
            # RRF scores (k=60 standard)
            rrf_scores = {}
            semantic_ids = [l['metadata'].get('chunk_id', '') for l in laws]

            for rank, law_id in enumerate(semantic_ids):
                rrf_scores[law_id] = rrf_scores.get(law_id, 0) + 0.7 / (60 + rank + 1)

            for rank, law_id in enumerate(bm25_law_ids):
                rrf_scores[law_id] = rrf_scores.get(law_id, 0) + 1.0 / (60 + rank + 1)

            # Rerank laws by RRF scores
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

            # Sort by reranker scores
            reranked_laws = sorted(
                zip(laws, scores),
                key=lambda x: x[1],
                reverse=True
            )
            laws = [law for law, score in reranked_laws]

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
