"""健康检查"""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/health")
async def health(request: Request):
    return {
        "status": "ok",
        "agent_loaded": hasattr(request.app.state, "coordinator"),
    }
