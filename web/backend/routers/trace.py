"""溯源查询端点"""
from fastapi import APIRouter, Request, HTTPException

from .. import db

router = APIRouter()


@router.get("/api/trace/{trace_id}")
async def get_trace(trace_id: str, request: Request):
    result = await db.get_trace(request.app.state.db, trace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


@router.delete("/api/trace/{trace_id}")
async def delete_trace(trace_id: str, request: Request):
    deleted = await db.delete_trace(request.app.state.db, trace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"ok": True, "id": trace_id}


@router.delete("/api/traces")
async def delete_all_traces(request: Request):
    n = await db.delete_all_traces(request.app.state.db)
    return {"ok": True, "deleted": n}


@router.get("/api/traces")
async def list_traces(request: Request, page: int = 1, page_size: int = 20):
    return await db.list_traces(request.app.state.db, page, page_size)
