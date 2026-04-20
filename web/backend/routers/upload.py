"""文档上传端点"""
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException

from ..config import MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
from ..models import UploadResponse
from ..services.ingest import extract_text

router = APIRouter()


@router.post("/api/upload", response_model=UploadResponse)
async def upload_doc(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"仅支持 {', '.join(ALLOWED_EXTENSIONS)} 格式")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"文件大小不能超过 {MAX_UPLOAD_SIZE // (1024*1024)}MB")

    text = extract_text(content, file.filename)

    return UploadResponse(
        filename=file.filename,
        text_length=len(text),
        text_preview=text[:500],
    )
