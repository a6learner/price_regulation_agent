"""FastAPI 应用入口"""
import os
import sys
from contextlib import asynccontextmanager

# 模型已缓存本地，跳过 HuggingFace 在线检查
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import PROJECT_ROOT, CONFIG_PATH, CHROMA_DB_PATH
from . import db

# 将项目根目录加入 sys.path，使 src.* 导入可用
sys.path.insert(0, str(PROJECT_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 切换工作目录，因为 AgentCoordinator 内部用相对路径
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)

    # 初始化 SQLite
    app.state.db = await db.init_db()

    # 加载 AgentCoordinator（耗时 ~10-20s，加载模型）
    print("[startup] Loading AgentCoordinator...")
    from src.agents.agent_coordinator import AgentCoordinator
    coordinator = AgentCoordinator(config_path=CONFIG_PATH, db_path=CHROMA_DB_PATH)
    app.state.coordinator = coordinator

    # 创建流式包装器
    from .services.streaming_coordinator import StreamingAgentCoordinator
    app.state.streaming_coordinator = StreamingAgentCoordinator(coordinator)

    # 知识库语义搜索必须与 Chroma 中向量维度一致（与 HybridRetriever 同一 BGE 模型）
    def embed_query_for_kb(q: str):
        hybrid = coordinator.retriever.retriever
        return hybrid.embedder.encode([q])[0]

    from .services.knowledge_browser import KnowledgeBrowser
    app.state.knowledge_browser = KnowledgeBrowser(
        CHROMA_DB_PATH, embed_query=embed_query_for_kb
    )

    print("[startup] Ready.")
    yield

    # 关闭
    await app.state.db.close()
    os.chdir(original_cwd)


app = FastAPI(title="价格合规智能体 Web API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from .routers import health, chat, trace, upload, knowledge

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(trace.router)
app.include_router(upload.router)
app.include_router(knowledge.router)
