"""Agent Coordinator - Agent协调器

编排6个Agent节点，实现端到端的价格合规分析工作流
"""
import time

from .legal_sources_serialize import serialize_graded_laws_for_ui
from .audience_remediation import build_compliant_remediation, build_risk_remediation
from .intent_analyzer import IntentAnalyzer
from .adaptive_retriever import AdaptiveRetriever
from .grader import Grader
from .reasoning_engine import ReasoningEngine
from .reflector import Reflector
from .nodes.remediation_advisor import RemediationAdvisor


class AgentCoordinator:
    """Agent协调器 - 编排6节点工作流"""

    def __init__(self, config_path="configs/model_config.yaml", db_path="data/rag/chroma_db"):
        self.intent_analyzer = IntentAnalyzer(config_path)
        self.retriever = AdaptiveRetriever(db_path)
        self.grader = Grader()
        self.reasoning_engine = ReasoningEngine(config_path)
        self.reflector = Reflector(config_path)
        self.remediation_advisor = RemediationAdvisor(config_path)

    @staticmethod
    def _compact_laws_for_trace(laws):
        out = []
        for law in laws or []:
            meta = law.get('metadata') or {}
            out.append({
                'chunk_id': meta.get('chunk_id'),
                'law_name': meta.get('law_name'),
                'article': meta.get('article'),
                'distance': round(float(law.get('distance', 0)), 4),
                'final_score': law.get('final_score'),
            })
        return out

    def process(self, query, return_trace=False, *, role: str = "merchant"):
        """处理价格合规查询

        Args:
            query: 用户查询字符串
            return_trace: 为 True 时在结果中加入 agent_trace（意图摘要、检索摘要、评分后法规列表、各节点耗时 ms）
            role: Web 端用户身份 consumer | regulator | merchant，影响建议表述

        Returns:
            dict: 最终分析结果（可能含 agent_trace）
        """
        print(f"\n[Agent Workflow] Processing query: {query[:50]}...")

        trace = {
            'timings_ms': {},
            'intent': None,
            'retrieved': None,
            'graded': None,
        } if return_trace else None

        # Step 1: 意图分析
        print("[1/6] Intent Analyzer...")
        t0 = time.perf_counter()
        intent = self.intent_analyzer.analyze(query)
        if trace is not None:
            trace['timings_ms']['intent_analyzer'] = round((time.perf_counter() - t0) * 1000, 2)
            trace['intent'] = intent
        print(f"  - Complexity: {intent.get('complexity')}")
        print(f"  - Suggested TopK: laws={intent.get('suggested_laws_k')}, cases={intent.get('suggested_cases_k')}")

        # Step 2: 自适应检索
        print("[2/6] Adaptive Retriever...")
        t0 = time.perf_counter()
        retrieved = self.retriever.retrieve(query, intent)
        if trace is not None:
            trace['timings_ms']['adaptive_retriever'] = round((time.perf_counter() - t0) * 1000, 2)
            trace['retrieved'] = {
                'laws': self._compact_laws_for_trace(retrieved.get('laws')),
                'cases': self._compact_laws_for_trace(retrieved.get('cases')),
                'metadata': retrieved.get('metadata'),
            }
        print(f"  - Retrieved: {len(retrieved.get('laws', []))} laws, {len(retrieved.get('cases', []))} cases")

        # Step 3: 质量评分
        print("[3/6] Grader...")
        t0 = time.perf_counter()
        graded = self.grader.grade(query, retrieved, intent)
        if trace is not None:
            trace['timings_ms']['grader'] = round((time.perf_counter() - t0) * 1000, 2)
            trace['graded'] = {
                'filtering_stats': graded.get('filtering_stats'),
                'graded_laws': self._compact_laws_for_trace(graded.get('graded_laws')),
                'graded_cases': self._compact_laws_for_trace(graded.get('graded_cases')),
            }
        stats = graded.get('filtering_stats', {})
        print(f"  - Filtered: {stats.get('filtered_count', 0)} low-quality docs")
        print(f"  - Kept: {stats.get('laws_after', 0)} laws, {stats.get('cases_after', 0)} cases")

        # Step 4: 推理分析
        print("[4/6] Reasoning Engine...")
        t0 = time.perf_counter()
        reasoning_result = self.reasoning_engine.reason(query, graded, intent)
        if trace is not None:
            trace['timings_ms']['reasoning_engine'] = round((time.perf_counter() - t0) * 1000, 2)

        if not reasoning_result.get('success'):
            print(f"  - Error: {reasoning_result.get('error')}")
            if trace is not None:
                reasoning_result['agent_trace'] = trace
            return reasoning_result

        print(f"  - Result: {reasoning_result.get('violation_type', 'N/A')}")
        print(f"  - Confidence: {reasoning_result.get('confidence', 0):.2f}")

        # Step 5: 自我反思验证
        print("[5/6] Reflector...")
        t0 = time.perf_counter()
        final_result = self.reflector.reflect(reasoning_result, graded, query, intent)
        if trace is not None:
            trace['timings_ms']['reflector'] = round((time.perf_counter() - t0) * 1000, 2)

        issues = final_result.get('issues_found', [])
        print(f"  - Validation: {'PASSED' if final_result.get('validation_passed') else 'FAILED'}")
        print(f"  - Issues found: {len(issues)}")
        print(f"  - Reflection count: {final_result.get('reflection_count', 0)}")

        # Step 6: 整改建议生成
        print("[6/6] Remediation Advisor...")
        t0 = time.perf_counter()
        if final_result.get('is_violation'):
            remediation_mode = "detailed" if intent.get('complexity') in ('complex', 'medium') else "fast"
            remediation = self.remediation_advisor.generate_remediation(
                query=query,
                reasoning_result=final_result,
                graded_docs=graded,
                mode=remediation_mode,
                audience=role,
            )
            steps_count = len(remediation.get('remediation_steps', []))
            print(f"  - Generated {steps_count} remediation steps")
            print(f"  - Mode: {remediation.get('generation_mode', 'N/A')}")
        elif final_result.get('has_risk_flag'):
            remediation = build_risk_remediation(role, final_result)
            print(f"  - Risk flag: level={remediation['risk_level']}, categories={remediation['risk_categories']}")
        else:
            remediation = build_compliant_remediation(role)
            print(f"  - No violation, no remediation needed")
        if trace is not None:
            trace['timings_ms']['remediation_advisor'] = round((time.perf_counter() - t0) * 1000, 2)

        # 合并结果
        final_result['remediation'] = remediation
        final_result['retrieved_legal_sources'] = serialize_graded_laws_for_ui(
            graded.get('graded_laws', [])
        )

        if trace is not None:
            trace['total_pipeline_ms'] = round(sum(trace['timings_ms'].values()), 2)
            final_result['agent_trace'] = trace

        return final_result
