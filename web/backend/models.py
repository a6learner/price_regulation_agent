"""Pydantic v2 请求/响应模型"""
from typing import Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    role: Literal["consumer", "regulator", "merchant"] = "consumer"
    attachment_text: str | None = None


class ChatSyncResponse(BaseModel):
    trace_id: str
    result: dict


class UploadResponse(BaseModel):
    filename: str
    text_length: int
    text_preview: str


class TraceItem(BaseModel):
    id: str
    query: str
    role: str
    duration_ms: int | None
    created_at: str


class TraceDetail(TraceItem):
    result: dict


class TraceListResponse(BaseModel):
    items: list[TraceItem]
    total: int
    page: int
    page_size: int


class KnowledgeItem(BaseModel):
    chunk_id: str
    content: str
    metadata: dict


class KnowledgePage(BaseModel):
    items: list[KnowledgeItem]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    code: str
    message: str
