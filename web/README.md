# 价格合规智能体 Web 系统 — 使用指南

## 一、系统架构

```
浏览器 (localhost:5173)
  │
  │  /api/*  ──→  Vite proxy 转发
  │
FastAPI 后端 (localhost:8000)
  │
  ├── AgentCoordinator / StreamingAgentCoordinator（6 节点 AI 分析管线）
  ├── 按用户身份（消费者 / 政府监管 / 商家）生成不同侧重建议
  ├── ChromaDB（691 条法规 + 133 条案例，知识库搜索与 RAG 共用 BGE 嵌入）
  └── SQLite（对话溯源记录 traces.db，含 role 与完整 JSON 结果）
```

前端：React 18 + TypeScript + Vite + Tailwind CSS
后端：FastAPI + SSE 流式推送 + SQLite

## 二、前置条件

- Python >= 3.11（后端）
- Node.js >= 18（前端）
- 已构建 RAG 向量库（`data/rag/chroma_db/` 存在）
- HuggingFace 模型已缓存到本地（`~/.cache/huggingface/hub/` 下有 `bge-small-zh-v1.5` 和 `bge-reranker-v2-m3`）
- 讯飞星辰 API Key 已填入 `configs/model_config.yaml`

## 三、首次安装

```bash
cd price_regulation_agent

# 1. 后端依赖
pip install -r web/backend/requirements.txt

# 2. 前端依赖
cd web/frontend
npm install
cd ../..
```

## 四、启动

需要开两个终端：

### 终端 1：启动后端

```bash
cd price_regulation_agent
HF_HUB_OFFLINE=1 python -m uvicorn web.backend.main:app --reload --port 8000
$env:HF_HUB_OFFLINE=1; python -m uvicorn web.backend.main:app --reload --port 8000 #powershell格式
```

等待看到以下输出表示就绪：
```
[startup] Loading AgentCoordinator...
[startup] Ready.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

启动耗时约 10-15 秒（加载嵌入模型和 BM25 索引）。

### 终端 2：启动前端

```bash
cd price_regulation_agent/web/frontend
npm run dev
```

看到：
```
VITE v8.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### 打开浏览器

访问 **http://localhost:5173/**

## 五、使用流程

### 5.1 角色选择（首页）

打开首页看到三张卡片：

| 角色 | 适用场景 | AI 分析侧重 |
|------|----------|-------------|
| **消费者** | 怀疑遇到价格欺诈 | 侵权识别、知情权、维权路径 |
| **政府监管** | 执法审查价格行为 | 违法认定、法条适用、证据链、处罚建议 |
| **网店商家** | 自查定价是否合规 | 合规风险、整改方案、预防机制 |

点击任一卡片进入对话工作台。**身份会随路由参数传给后端**，影响最终建议的体裁（见下节「身份化建议」）。

### 5.2 对话工作台（核心页面）

**布局**：左侧历史记录 | 中间对话区 | 右侧溯源抽屉（按需滑出）

**使用步骤**：
1. 在底部输入框输入价格行为描述，例如：
   - `某电商平台标注原价1680元但从未以此价格销售`
   - `超市货架上5瓶洗手液未标明价格`
   - `某酒店标注划线价3000元，实际预订价198元`
2. 点击「发送」或按 Enter
3. 观察 **6 节点进度条** 逐步亮起：
   - 意图分析 → 法规检索 → 质量评分 → 推理分析 → 反思验证 → 建议生成（管道内最后一步；文案对商家偏「整改」，对消费者/监管见下）
4. 分析完成后显示 **报告卡片**，包含：
   - 判定结论（违规 / 合规 / 存在风险）+ 置信度
   - 违规类型
   - **法律依据**：展示检索到的法规片段；若有 `retrieved_legal_sources`，可通过 **「选择条文查看全文」** 下拉查看正文（与 Grader 保留的条文一致）
   - 推理分析全文
   - **身份化建议**（区块标题随身份变化，见 5.2.1）
5. 点击「查看完整溯源」→ 右侧滑出 **溯源抽屉**（展示与列表所选记录一致的结构化内容）

**上传文档**：
- 点击输入框左侧📎图标，选择 PDF / DOCX / TXT 文件
- 文件文本自动提取并附加到下次查询中

**历史记录**：
- 存储位置：`web/backend/traces.db`（SQLite），字段含用户原文、`role`、结果 JSON、`duration_ms` 等
- 左侧栏列出过往查询；每条可 **删除**，标题栏可 **清空** 全部
- 点击一条可打开 **完整溯源**；若在旧版本分析产生记录，可能无「条文全文」字段，界面会提示可重新分析后查看全文

#### 5.2.1 身份化建议（三种用户）

后端根据请求体中的 `role`（`consumer` / `regulator` / `merchant`）生成不同侧重的 `remediation`（并实现 `panel_title` 等字段供前端展示）：

| 身份 | 报告/溯源中侧重的区块（示例标题） |
|------|----------------------------------|
| **消费者** | 维权与法律指引：证据保全、协商与平台、12315 等 |
| **政府监管** | 监管处置与下一步：执法要点、风险档位（高/中/低）、监管摘要等 |
| **网店商家** | 整改建议：规则模板或 LLM 生成的经营者整改步骤（责任部门等） |

说明：**推理与法条引用仍共用同一套 Agent 与 RAG**；差异主要体现在最后一步面向谁的「可执行建议」。同步接口 `POST /api/chat/sync` 与流式接口均传入 `role`。

### 5.3 知识库浏览

顶部导航点击「知识库」进入。

- **法规库**：691 条法律法规条文，可搜索
- **案例库**：133 条行政处罚案例，可搜索
- 支持分页浏览和关键词 **语义搜索**（查询向量与向量库一致，均来自 **BAAI/bge-small-zh-v1.5**，与 RAG 管线对齐，避免维度不一致）

### 5.4 前端鲁棒性说明（可选读）

- 法规片段的正文展示依赖当次分析写入的 `retrieved_legal_sources`；**仅短语的 `legal_references` / `legal_basis`** 在无全文数据时仍展示摘要。
- 推理结果中 `reasoning_chain` 可能为字符串或数组；`remediation_steps` 可能为字符串或结构化对象，前端会格式化为可显示文本。
- 根级 **ErrorBoundary** 可在子组件渲染异常时显示提示而非整页白屏。

## 六、一次完整对话的数据流

```
用户输入 "某平台虚构原价"
    │
    ▼
前端 POST /api/chat（SSE 流式）
    │
    ▼ 后端拼接角色提示词前缀
    │
    ├─ [1] IntentAnalyzer.analyze()     → SSE event: intent
    ├─ [2] AdaptiveRetriever.retrieve() → SSE event: retrieval
    ├─ [3] Grader.grade()               → SSE event: grading
    ├─ [4] ReasoningEngine.reason()     → SSE event: reasoning  ← 最慢（LLM 调用）
    ├─ [5] Reflector.reflect()          → SSE event: reflection
    ├─ [6] RemediationAdvisor（按 role 分支） → SSE event: remediation
    │
    ▼ 组装结果：含 remediation、retrieved_legal_sources（检索条文全文）等
    │
    ▼ 写入 SQLite（traces.db，含 role）
    │
    └─ SSE event: done（含 trace_id + 完整结果）
         │
         ▼
    前端渲染报告卡片
         │
         ▼（用户点击"查看溯源"）
    GET /api/trace/{trace_id} → 溯源抽屉
```

## 七、API 端点速查

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat` | SSE 流式对话（核心） |
| POST | `/api/chat/sync` | 同步对话（调试用，~25s 阻塞） |
| POST | `/api/upload` | 上传文档提取文本（PDF/DOCX/TXT） |
| GET | `/api/trace/{id}` | 查询单条完整溯源（含 `role` 与完整 `result`） |
| GET | `/api/traces?page=1&page_size=20` | 分页查询历史 |
| DELETE | `/api/trace/{id}` | 删除单条历史 |
| DELETE | `/api/traces` | 清空全部历史 |
| GET | `/api/knowledge/laws?page=1&q=...` | 法规浏览/搜索 |
| GET | `/api/knowledge/cases?page=1&q=...` | 案例浏览/搜索 |

### 对话接口请求体（`POST /api/chat` 与 `POST /api/chat/sync`）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户输入的价格行为描述（**不含**角色前缀；后端会拼接 `role_prompt` 中的视角说明） |
| `role` | string | 否，默认 `consumer` | 用户身份，枚举：`consumer`（消费者）、`regulator`（政府监管）、`merchant`（网店商家）。影响最终 `remediation` 体裁（维权指引 / 监管处置 / 整改建议等）及入库字段 |
| `attachment_text` | string 或 null | 否 | 由 `/api/upload` 提取的附件正文；有则拼入模型输入 |

流式接口返回 **SSE**（`event:` + `data:` JSON）；结束时 `event: done` 的 `data` 内含 `trace_id` 与 `result`（含 `remediation`、`retrieved_legal_sources` 等）。同步接口返回 JSON：`{ "trace_id", "result" }`。

Swagger 文档：启动后端后访问 http://localhost:8000/docs

## 八、目录结构

```
web/
├── README.md               ← 本文件
├── backend/
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 路径配置
│   ├── models.py           # Pydantic 数据模型
│   ├── db.py               # SQLite 操作
│   ├── traces.db           # 运行后自动生成
│   ├── requirements.txt    # Python 依赖
│   ├── routers/
│   │   ├── health.py       # 健康检查
│   │   ├── chat.py         # 对话（SSE + 同步）
│   │   ├── trace.py        # 溯源查询
│   │   ├── upload.py       # 文档上传
│   │   └── knowledge.py    # 知识库浏览
│   └── services/
│       ├── streaming_coordinator.py  # Agent 管线流式包装（传入 role；写入条文全文）
│       ├── role_prompt.py            # 三角色提示词前缀
│       ├── ingest.py                 # 文档文本提取
│       └── knowledge_browser.py      # ChromaDB 分页与语义搜索（与 RAG 同嵌入）
└── frontend/
    ├── package.json
    ├── vite.config.ts      # Vite 配置 + API 代理
    ├── src/
    │   ├── index.css       # Tailwind v4 主题（设计系统色彩）
    │   ├── types.ts        # TypeScript 类型
    │   ├── api.ts          # API 调用封装（含删除 trace、流式解析）
    │   ├── analysisDisplay.ts   # 推理链/法条/整改步骤展示归一化
    │   ├── adviceHeading.ts       # 按身份的建议区块标题
    │   ├── components/     # 含 ErrorBoundary、LegalSourcesPanel、TraceDrawer 等
    │   └── pages/          # 3 个页面
    └── dist/               # npm run build 产物
```

与 Web 对话结果组装相关的 **项目根目录** `src/agents/` 文件（不在 `web/` 下）：`legal_sources_serialize.py`（`retrieved_legal_sources`）、`audience_remediation.py`（按身份的建议与合规/风险文案）、`nodes/remediation_advisor.py`（`generate_remediation(..., audience=...)`）。`main.py` 在启动时会为 `KnowledgeBrowser` 注入与 `HybridRetriever` 相同的嵌入函数，保证知识库搜索与 Chroma 维度一致。

## 九、常见问题

**Q: 后端启动报 SSL / HuggingFace 连接错误**
A: 确保启动命令带 `HF_HUB_OFFLINE=1`。`main.py` 已内置此设置，但环境变量优先级更高。

**Q: 后端启动报 `ModuleNotFoundError: No module named 'src'`**
A: 必须从 `price_regulation_agent/` 目录启动 uvicorn，不能从子目录。

**Q: 前端页面空白或 API 报错 502**
A: 确认后端已启动且在 8000 端口运行。前端的 Vite 代理需要后端在线。

**Q: 对话返回错误 / 推理失败**
A: 检查 `configs/model_config.yaml` 中的讯飞 API Key 是否有效。

**Q: 想清空所有历史记录**
A: 对话页左侧「清空」可删库内全部记录；或删除 `web/backend/traces.db` 后重启后端。

**Q: 知识库带 `q` 搜索报 500，`Collection expecting embedding with dimension of 512, got 384`**
A: 已修复：语义搜索与向量库均使用 BGE 512 维嵌入。请拉取最新代码并重启后端。

**Q: 页面白屏或「Objects are not valid as a React child」**
A: 多为旧数据或字段形态异常。请更新前端；`remediation_steps` 等已做展示层归一化。仍异常时可看浏览器控制台报错。

**Q: 想修改角色提示词**
A: 编辑 `web/backend/services/role_prompt.py`，用了 `--reload` 的话自动生效。

**Q: 想调整「三种用户」建议话术（维权 / 监管 / 整改）**
A: 编辑项目根目录 `src/agents/audience_remediation.py`（与消费者、监管、商家相关的规则模板）；商家向 LLM 详细整改仍在 `src/agents/nodes/remediation_advisor.py`。

**Q: 如何部署为单端口服务（不开两个终端）**
A: 先构建前端 `cd web/frontend && npm run build`，然后在 `web/backend/main.py` 末尾加上：
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=str(PROJECT_ROOT / "web/frontend/dist"), html=True), name="frontend")
```
之后只启动后端即可：`http://localhost:8000/` 直接访问。

## 十、技术栈总览

| 层 | 技术 | 版本 |
|---|------|------|
| 前端框架 | React + TypeScript | 19 + 6.0 |
| 构建工具 | Vite | 8.0 |
| 样式 | Tailwind CSS | 4.2 |
| 路由 | React Router | 7.x |
| 后端框架 | FastAPI | 0.115+ |
| 流式推送 | sse-starlette | 2.0+ |
| 数据库 | SQLite (aiosqlite) | - |
| 向量库 | ChromaDB | 1.5+ |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 | - |
| 重排模型 | BAAI/bge-reranker-v2-m3 | - |
| LLM | 讯飞星辰 MaaS (Qwen) | - |
