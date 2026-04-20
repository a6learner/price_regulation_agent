"""Web 后端配置"""
import os
from pathlib import Path

# 项目根目录：price_regulation_agent/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_PATH = str(PROJECT_ROOT / "configs" / "model_config.yaml")
CHROMA_DB_PATH = str(PROJECT_ROOT / "data" / "rag" / "chroma_db")
SQLITE_PATH = str(PROJECT_ROOT / "web" / "backend" / "traces.db")

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
