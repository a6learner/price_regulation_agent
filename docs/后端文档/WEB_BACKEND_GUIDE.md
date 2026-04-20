# Web 后端使用指南

## 一、快速启动

```bash
cd price_regulation_agent

# 安装依赖（首次）
pip install -r web/backend/requirements.txt

# 启动后端（端口 8000）
HF_HUB_OFFLINE=1 python -m uvicorn web.backend.main:app --reload --port 8000
```

启动过程约 10-15 秒（加载嵌入模型 + BM25 索引 + ChromaDB）。看到以下输出说明就绪：

```
[startup] Loading AgentCoordinator...
[startup] Ready.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

`--reload` 参数会在代码修改后自动重启，开发时推荐使用。

---

## 二、目录结构

```
web/backend/
├── main.py                  # 入口：FastAPI app + 启动加载
├── config.py                # 路径配置（自动计算，通常不需要改）
├── models.py                # 请求/响应数据结构定义
├── db.py                    # SQLite 操作（trace 存取）
├── traces.db                # 运行后自动生成的 SQLite 数据库
├── requirements.txt         # Web 层专用依赖
├── routers/
│   ├── health.py            # GET /api/health
│   ├── chat.py              # POST /api/chat (SSE) + /api/chat/sync
│   ├── trace.py             # GET /api/trace/{id}, /api/traces
│   ├── upload.py            # POST /api/upload
│   └── knowledge.py         # GET /api/knowledge/laws|cases
└── services/
    ├── streaming_coordinator.py  # 核心：Agent 管线的流式包装
    ├── role_prompt.py            # 三角色提示词
    ├── ingest.py                 # 文档文本提取
    └── knowledge_browser.py      # ChromaDB 分页浏览
```

---

## 三、架构理解

### 与现有系统的关系

```
web/backend/                    src/（不修改）
─────────────                   ──────────────
main.py                         
  └─ lifespan 启动时创建 ─────→ AgentCoordinator 单例
                                  ├─ IntentAnalyzer（规则，无 LLM）
streaming_coordinator.py          ├─ AdaptiveRetriever（混合检索）
  └─ 借用 coordinator 的       ──→ ├─ Grader（规则评分）
     6 个节点实例                  ├─ ReasoningEngine（LLM 推理）
     逐步调用 + 推送 SSE          ├─ Reflector（LLM 反思）
                                  └─ RemediationAdvisor（LLM 建议）
```

**关键设计**：`StreamingAgentCoordinator` 不继承也不修改原始 `AgentCoordinator`，而是直接引用它内部的 6 个节点对象，手动按相同顺序调用，在每步之间插入 SSE 事件推送。

### 线程模型

```
主线程（asyncio 事件循环）          工作线程
  │                                  │
  │  POST /api/chat 请求到达          │
  │  ─→ 创建 asyncio.Queue           │
  │  ─→ run_in_executor ──────────→  _run_pipeline()
  │                                  │  step1: intent → queue.put()
  │  ←── queue.get() ← 读取事件      │  step2: retrieval → queue.put()
  │  ─→ yield SSE event              │  step3: grading → queue.put()
  │  ←── queue.get()                 │  step4: reasoning → queue.put()  ← 最慢
  │  ─→ yield SSE event              │  step5: reflection → queue.put()
  │  ...                             │  step6: remediation → queue.put()
  │                                  │  queue.put("done", result)
  │  ←── "done"                      │
  │  ─→ save_trace + yield done      │
```

Agent 管线是同步阻塞的（~25 秒），放在线程池中运行，不阻塞 FastAPI 的 async 事件循环。

---

## 四、关键细节

### 4.1 HF_HUB_OFFLINE=1

启动时必须设置此环境变量。原因：`HybridRetriever` 初始化时加载 `BAAI/bge-small-zh-v1.5` 嵌入模型和 `BAAI/bge-reranker-v2-m3` 重排序模型。如果不设置离线模式，它会尝试连 HuggingFace 检查更新，在你的网络环境下会触发 SSL 错误导致启动失败。模型文件已缓存在 `~/.cache/huggingface/hub/`。

`main.py` 中已设置了 `os.environ.setdefault("HF_HUB_OFFLINE", "1")`，但如果遇到问题，也可以在命令行显式传入。

### 4.2 工作目录

`main.py` 启动时会自动 `os.chdir()` 到 `price_regulation_agent/` 根目录，因为 `AgentCoordinator` 内部使用相对路径（如 `configs/model_config.yaml`、`data/rag/chroma_db`）。所以你必须从 `price_regulation_agent/` 目录启动 uvicorn：

```bash
# 正确 ✓
cd price_regulation_agent
python -m uvicorn web.backend.main:app --port 8000

# 错误 ✗（会找不到 configs/）
cd price_regulation_agent/web/backend
python -m uvicorn main:app --port 8000
```

### 4.3 并发限制

`AgentCoordinator` 内部的 `MaaSClient` 有请求计数器等可变状态，不是线程安全的。当前实现没有加锁（因为是本地单人使用），但如果你同时发多个请求，可能出现竞态。正常使用（一次一个对话）没有问题。

### 4.4 trace 数据库

`traces.db` 在首次启动时自动创建在 `web/backend/` 目录下。它是一个 SQLite 文件，存储每次对话的完整输入输出。你可以用任何 SQLite 工具（如 DB Browser for SQLite）查看。

删除 `traces.db` 会清空所有历史记录，不影响系统运行。

### 4.5 角色提示词

在 `services/role_prompt.py` 中定义，每种角色对应一段中文前缀，拼接在用户输入之前发给 LLM。如果想调整分析角度，直接编辑这个文件即可。

当前内容：
- **consumer**：消费者权益保护视角 — 价格欺诈、知情权、维权措施
- **regulator**：监管执法视角 — 违法认定、法条适用、证据链、处罚建议
- **merchant**：商家合规视角 — 合规风险、整改方案、预防机制

### 4.6 文档上传

上传的文件不做持久化存储，仅在请求中提取文本后返回。前端拿到文本后放入下一次 `/api/chat` 的 `attachment_text` 字段。支持格式：

| 格式 | 库 | 说明 |
|------|-----|------|
| PDF | pdfplumber | 逐页提取文本 |
| DOCX | python-docx | 提取段落文本 |
| TXT | 内置 | UTF-8 解码 |

### 4.7 知识库浏览

直接读取已构建好的 ChromaDB（`data/rag/chroma_db`），不做任何写入。提供分页浏览和语义搜索两种模式。数据量：

- 法规：691 条（来自多部法律法规的逐条拆分）
- 案例：133 条（行政处罚文书）

---

## 五、前后端结合

### 方案 A：Vite 代理（推荐）

前端项目用 Vite，在 `vite.config.ts` 中配置代理：

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

开发时前端跑在 `localhost:5173`，所有 `/api` 请求自动转发到后端 `localhost:8000`。

### 方案 B：直连（最简单）

后端已启用 CORS（允许所有来源），前端可以直接请求 `http://localhost:8000/api/...`。适合纯 HTML 页面不走构建工具的场景。

### 方案 C：FastAPI 静态文件托管

如果前端是纯 HTML/CSS/JS（Stitch 输出），可以让 FastAPI 直接托管。在 `main.py` 中添加：

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="web/frontend", html=True), name="frontend")
```

这样访问 `http://localhost:8000/` 就是前端页面，`/api/*` 是后端接口，一个端口搞定。

---

## 六、测试命令速查

```bash
# 健康检查
curl http://localhost:8000/api/health

# 同步对话（等 ~25 秒）
curl -X POST http://localhost:8000/api/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"query":"某超市货架上5瓶洗手液未标明价格","role":"consumer"}'

# SSE 流式对话（逐行打印事件）
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"某电商平台标注原价1680元但从未以此价格销售","role":"regulator"}'

# 查询溯源（替换为实际 trace_id）
curl http://localhost:8000/api/trace/{trace_id}

# 历史记录
curl "http://localhost:8000/api/traces?page=1&page_size=5"

# 浏览法规（分页）
curl "http://localhost:8000/api/knowledge/laws?page=1&page_size=5"

# 搜索法规
curl "http://localhost:8000/api/knowledge/laws?q=明码标价"

# 浏览案例
curl "http://localhost:8000/api/knowledge/cases?page=1&page_size=5"

# 上传文档
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test.pdf"
```

---

## 七、常见问题

**Q: 启动时报 SSL 错误 / HuggingFace 连接失败**
A: 确保设置了 `HF_HUB_OFFLINE=1` 环境变量。

**Q: 启动时报 `ModuleNotFoundError: No module named 'src'`**
A: 确保从 `price_regulation_agent/` 目录启动，不要从子目录启动。

**Q: 对话返回空结果或 error**
A: 检查 `configs/model_config.yaml` 中的 API key 是否有效，讯飞星辰 API 是否正常。

**Q: 想清空历史记录**
A: 删除 `web/backend/traces.db` 文件，重启服务即可。

**Q: 修改了 `services/role_prompt.py` 后没生效**
A: 如果用了 `--reload` 参数启动，会自动重载。否则需要重启 uvicorn。

**Q: API 文档在哪里看**
A: 启动后访问 `http://localhost:8000/docs`，FastAPI 自动生成 Swagger UI。
