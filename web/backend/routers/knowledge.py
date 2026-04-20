"""知识库浏览端点"""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/knowledge/laws")
async def browse_laws(request: Request, page: int = 1, page_size: int = 20, q: str | None = None):
    browser = request.app.state.knowledge_browser
    return browser.browse("laws", page, page_size, q)


@router.get("/api/knowledge/cases")
async def browse_cases(request: Request, page: int = 1, page_size: int = 20, q: str | None = None):
    browser = request.app.state.knowledge_browser
    return browser.browse("cases", page, page_size, q)
