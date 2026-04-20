"""对话端点：同步 + SSE 流式"""
import asyncio
import json
import time
import uuid
from functools import partial

from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..models import ChatRequest, ChatSyncResponse
from ..services.role_prompt import get_role_prefix
from .. import db

router = APIRouter()


def _build_query(req: ChatRequest) -> str:
    """拼接角色前缀 + 用户查询 + 附件文本"""
    parts = [get_role_prefix(req.role), req.query]
    if req.attachment_text:
        parts.append(f"\n\n【附件内容】\n{req.attachment_text}")
    return "".join(parts)


@router.post("/api/chat/sync")
async def chat_sync(req: ChatRequest, request: Request):
    """同步版：阻塞等待完整结果"""
    coordinator = request.app.state.coordinator
    query = _build_query(req)

    loop = asyncio.get_event_loop()
    start = time.time()
    result = await loop.run_in_executor(None, partial(coordinator.process, query, role=req.role))
    duration_ms = int((time.time() - start) * 1000)

    trace_id = str(uuid.uuid4())
    await db.save_trace(request.app.state.db, trace_id, req.query, req.role, result, duration_ms)

    return ChatSyncResponse(trace_id=trace_id, result=result)


@router.post("/api/chat")
async def chat_stream(req: ChatRequest, request: Request):
    """SSE 流式：逐节点推送事件"""
    streaming = request.app.state.streaming_coordinator
    query = _build_query(req)

    async def event_generator():
        start = time.time()
        trace_id = str(uuid.uuid4())
        final_result = None

        async for event_name, data in streaming.stream(query, req.role):
            if event_name == "done":
                final_result = data
                duration_ms = int((time.time() - start) * 1000)
                await db.save_trace(
                    request.app.state.db, trace_id, req.query, req.role, data, duration_ms
                )
                yield {
                    "event": "done",
                    "data": json.dumps({"trace_id": trace_id, "result": data}, ensure_ascii=False),
                }
            elif event_name == "error":
                duration_ms = int((time.time() - start) * 1000)
                error_result = {"error": data.get("message"), "success": False}
                await db.save_trace(
                    request.app.state.db, trace_id, req.query, req.role, error_result, duration_ms
                )
                yield {
                    "event": "error",
                    "data": json.dumps(data, ensure_ascii=False),
                }
                yield {
                    "event": "done",
                    "data": json.dumps({"trace_id": trace_id, "result": error_result}, ensure_ascii=False),
                }
            else:
                yield {
                    "event": event_name,
                    "data": json.dumps({"node": event_name, "detail": data}, ensure_ascii=False),
                }

    return EventSourceResponse(event_generator())
