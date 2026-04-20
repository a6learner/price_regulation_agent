import time
from typing import Optional

from src.baseline import BaselineEvaluator
from .retriever import HybridRetriever
from .prompt_template import RAGPromptTemplate


class RAGEvaluator(BaselineEvaluator):
    def __init__(
        self,
        config_path="configs/model_config.yaml",
        db_path="data/rag/chroma_db",
        retriever: Optional[HybridRetriever] = None,
    ):
        super().__init__(config_path)
        self.retriever = retriever if retriever is not None else HybridRetriever(db_path)
        self.rag_prompt = RAGPromptTemplate()

    def evaluate_single_case(self, eval_case, model_key='qwen-8b'):
        case_id = eval_case.get('meta', {}).get('case_id', 'unknown')

        # Step 1: 提取query
        query = self.prompt_template.extract_case_description_from_eval(eval_case)

        # Step 2: 检索相关文档（cases_k=0，避免案例同源污染）
        retrieved = self.retriever.retrieve(query, laws_k=3, cases_k=0)

        # Step 3: 构建RAG prompt
        prompts = self.rag_prompt.build_rag_prompt(
            query,
            retrieved['laws'],
            retrieved['cases']
        )

        # Step 4-6: 调用模型、解析、评估
        start_time = time.time()
        api_response = self.client.call_model(
            system_prompt=prompts['system_prompt'],
            user_prompt=prompts['user_prompt'],
            model_key=model_key
        )
        response_time = time.time() - start_time

        if api_response is None:
            return {
                'case_id': case_id,
                'model': model_key,
                'success': False,
                'error': 'API调用失败'
            }

        response_text = self.client.extract_response_text(api_response)
        prediction = self.parser.parse_response(response_text)

        if prediction is None:
            return {
                'case_id': case_id,
                'model': model_key,
                'success': False,
                'error': '响应解析失败',
                'raw_response': response_text[:500] if response_text else ''
            }

        ground_truth = self.parser.extract_ground_truth(eval_case)
        comparison = self.parser.compare_prediction_with_truth(prediction, ground_truth)
        legal_eval = self.parser.evaluate_legal_basis_accuracy(prediction)
        reasoning_eval = self.parser.evaluate_reasoning_quality(prediction)

        retrieved_laws_compact = []
        for law in retrieved.get('laws', [])[:8]:
            meta = law.get('metadata') or {}
            retrieved_laws_compact.append({
                'chunk_id': meta.get('chunk_id'),
                'law_name': meta.get('law_name'),
                'article': meta.get('article'),
                'distance': round(float(law.get('distance', 0)), 4),
            })

        return {
            'case_id': case_id,
            'model': model_key,
            'success': True,
            'prediction': prediction,
            'ground_truth': ground_truth,
            'metrics': comparison,
            'quality_metrics': {
                'legal_basis': legal_eval,
                'reasoning': reasoning_eval
            },
            'retrieved_laws': retrieved_laws_compact,
            'retrieval_info': {
                'laws_count': len(retrieved['laws']),
                'cases_count': len(retrieved['cases'])
            },
            'performance': {
                'response_time': round(response_time, 2),
                'input_tokens': api_response.get('usage', {}).get('prompt_tokens', 0),
                'output_tokens': api_response.get('usage', {}).get('completion_tokens', 0)
            },
            'llm_response': response_text
        }
