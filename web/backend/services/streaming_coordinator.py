"""StreamingAgentCoordinator - 流式包装器

复用 AgentCoordinator 的各节点实例，逐步执行并通过 Queue 推送 SSE 事件。
不修改 src/ 中的任何代码。
"""
import asyncio
import queue
import time

from src.agents.audience_remediation import build_compliant_remediation, build_risk_remediation
from src.agents.legal_sources_serialize import serialize_graded_laws_for_ui


class StreamingAgentCoordinator:

    def __init__(self, coordinator):
        self.intent_analyzer = coordinator.intent_analyzer
        self.retriever = coordinator.retriever
        self.grader = coordinator.grader
        self.reasoning_engine = coordinator.reasoning_engine
        self.reflector = coordinator.reflector
        self.remediation_advisor = coordinator.remediation_advisor

    def _run_pipeline(self, query: str, role: str, q: queue.Queue):
        """同步管线，在线程中运行，逐步向 Queue 推送事件"""
        try:
            # Step 1: 意图分析
            intent = self.intent_analyzer.analyze(query)
            q.put(("intent", {
                "complexity": intent.get("complexity"),
                "violation_type_hints": intent.get("violation_type_hints", []),
                "key_entities": intent.get("key_entities", {}),
                "suggested_laws_k": intent.get("suggested_laws_k"),
                "suggested_cases_k": intent.get("suggested_cases_k"),
            }))

            # Step 2: 自适应检索
            retrieved = self.retriever.retrieve(query, intent)
            laws = retrieved.get("laws", [])
            cases = retrieved.get("cases", [])
            q.put(("retrieval", {
                "laws_count": len(laws),
                "cases_count": len(cases),
                "laws_preview": [
                    {"title": l.get("metadata", {}).get("title", ""), "score": l.get("score")}
                    for l in laws[:5]
                ],
            }))

            # Step 3: 质量评分
            graded = self.grader.grade(query, retrieved, intent)
            stats = graded.get("filtering_stats", {})
            q.put(("grading", {
                "filtered_count": stats.get("filtered_count", 0),
                "laws_after": stats.get("laws_after", 0),
                "cases_after": stats.get("cases_after", 0),
            }))

            # Step 4: 推理分析
            reasoning_result = self.reasoning_engine.reason(query, graded, intent)
            if not reasoning_result.get("success"):
                q.put(("error", {"code": "REASONING_FAILED", "message": reasoning_result.get("error", "推理失败")}))
                return
            q.put(("reasoning", {
                "violation_type": reasoning_result.get("violation_type"),
                "is_violation": reasoning_result.get("is_violation"),
                "confidence": reasoning_result.get("confidence"),
            }))

            # Step 5: 自我反思验证
            final_result = self.reflector.reflect(reasoning_result, graded, query, intent)
            q.put(("reflection", {
                "validation_passed": final_result.get("validation_passed"),
                "issues_found": final_result.get("issues_found", []),
                "reflection_count": final_result.get("reflection_count", 0),
            }))

            # Step 6: 整改建议（复制自 agent_coordinator.py:75-98）
            if final_result.get("is_violation"):
                remediation_mode = "detailed" if intent.get("complexity") in ("complex", "medium") else "fast"
                remediation = self.remediation_advisor.generate_remediation(
                    query=query,
                    reasoning_result=final_result,
                    graded_docs=graded,
                    mode=remediation_mode,
                    audience=role,
                )
            elif final_result.get("has_risk_flag"):
                remediation = build_risk_remediation(role, final_result)
            else:
                remediation = build_compliant_remediation(role)

            final_result["remediation"] = remediation
            # 供前端展示「检索到的法规」全文（与推理引用的条文对应）
            final_result["retrieved_legal_sources"] = serialize_graded_laws_for_ui(
                graded.get("graded_laws", [])
            )
            q.put(("remediation", {
                "has_violation": remediation.get("has_violation", False),
                "has_risk_flag": remediation.get("has_risk_flag", False),
                "steps_count": len(remediation.get("remediation_steps") or []),
            }))

            q.put(("done", final_result))

        except Exception as e:
            q.put(("error", {"code": "PIPELINE_ERROR", "message": str(e)}))

    async def stream(self, query: str, role: str = "consumer"):
        """异步生成器，yield (event_name, data) 元组"""
        q = queue.Queue()
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self._run_pipeline, query, role, q)

        while True:
            try:
                event_name, data = q.get_nowait()
                yield (event_name, data)
                if event_name in ("done", "error"):
                    break
            except queue.Empty:
                if future.done():
                    while not q.empty():
                        event_name, data = q.get_nowait()
                        yield (event_name, data)
                    break
                await asyncio.sleep(0.1)

        await future
