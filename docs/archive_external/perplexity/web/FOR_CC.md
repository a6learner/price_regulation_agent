# 价格合规智能体 Web 系统 — 后端与前后端对接规格

> 交给 Claude Code 的总规格。放在仓库根目录作为 `CLAUDE.md` 使用。

## 项目定位

已完成的研究后端 `src/`(Baseline / RAG / Agent 三路线,AgentCoordinator 六节点)**不得修改**,本次新建 `web/` 目录,把它包装成面向三类用户的 Web 服务并对接前端。

## 技术栈

- **Backend**: Python 3.11 + FastAPI + SSE(`sse-starlette`) + SQLite + Pydantic v2
- **Frontend**: React 18 + TypeScript + Vite(Stitch 导出的设计稿还原)
- 前端通过 Vite proxy 转发 `/api` 到后端 8000 端口

## 目录

```
price_regulation_agent/
├── src/                    # 禁改
├── data/                   # 禁改
├── web/
│   ├── backend/            # FastAPI
│   └── frontend/           # React(Stitch 稿还原)
```

## 三类用户

消费者(consumer)、监管(regulator)、商家(merchant)。通过 HTTP header `X-Role` 区分。角色差异**只**体现在:
1. 后端:在 query 前拼接不同 prompt 前缀(`services/role_prompt.py`)
2. 前端:同一套组件,按 role 切换卡片展开/隐藏

**不得**为每个角色 fork 算法或页面。

## 架构分层

```
Frontend (React)
    │ HTTPS: REST + SSE
FastAPI Gateway  —— CORS / X-Role / request_id
    │
Services 层: inference · ingest(OCR) · trace_store · role_prompt
    │ import
src/agents/AgentCoordinator  (已有,禁改)
```

Web 层是薄壳,所有推理 → `AgentCoordinator.process()`。若原类不支持节点级回调,新建 `StreamingAgentCoordinator` wrapper(asyncio.Queue 桥接),**不改原类**。

## 核心 API(最小集,细节 CC 自行补充)

所有请求带 `X-Role` header。错误统一 `{code, message}`。

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/chat` | **SSE 流式**,事件见下 |
| POST | `/api/upload/doc` | PDF/DOCX/TXT ≤ 20MB → `{file_id, extracted_text}` |
| POST | `/api/upload/image` | JPG/PNG ≤ 10MB → OCR → `{file_id, ocr_text}` |
| GET  | `/api/trace/{trace_id}` | 完整溯源 JSON |
| POST | `/api/batch/submit` | 批量审核(xlsx/zip)→ `{job_id}` |
| GET  | `/api/batch/status/{job_id}` | 进度 + 下载链接 |
| GET  | `/api/knowledge/laws` | 分页查 691 条法规 |
| GET  | `/api/knowledge/cases` | 分页查 133 条案例 |
| POST | `/api/compare` | 同一 query 跑三路线并排返回 |

## SSE 事件(对齐 AgentCoordinator 六节点)

```
event: intent      data: {entities, intent_type, complexity}
event: retrieval   data: {laws:[{law_id,title,snippet,scores:{vector,bm25,rrf,rerank}}], cases:[...]}
event: grading     data: {relevance, coverage, freshness, weighted}
event: reasoning   data: {delta:"..."}                 ← token 级流式,可多条
event: reflection  data: {triggered_retry, issues}
event: remediation data: {advice:[...]}
event: done        data: {trace_id, verdict, confidence, violation_type, law_refs, cost}
event: error       data: {code, message}
```

心跳:空闲 >15s 推 `event: ping`。前端拿到 `done.trace_id` 后拉 `/api/trace/{id}` 填充溯源抽屉。

## 溯源(Trace)— 系统灵魂

每次 `/api/chat` 完成前生成 `trace_id`,完整写入 SQLite `traces` 表,字段:

```sql
trace_id TEXT PK, created_at, role, session_id,
source_type, query_preview, verdict, violation_type,
confidence, latency_ms, tokens_total,
payload_json TEXT,  -- 完整 pipeline(检索得分/prompt/输出/反思)
error_code
```

`/api/trace/{id}` 返回 `payload_json` 反序列化结果。前端的证据抽屉、得分明细、原文跳链全部基于此。

## 前后端对接要点

1. 前端用 `@microsoft/fetch-event-source` 订阅 SSE(比原生 EventSource 支持 POST + header)
2. 所有上传先拿 `file_id`,再在 `/api/chat` 的 `attachments` 数组里引用
3. 图片/文档在后端 `ingest` 层统一转文本,再进 AgentCoordinator(保证单一推理路径)
4. 前端流式渲染:intent/retrieval/grading 到达立即显示对应卡片骨架,reasoning 追加文本,done 后触发 trace 详情请求
5. 错误处理:后端任何节点异常都要 yield `error` 再 yield `done`(verdict=unknown)再关闭流,前端不能卡住

## 性能预算

- Chat 首字节 < 2s(到 intent 事件)
- Chat 完整响应 P95 < 30s(对齐论文 Agent 25.6s 均值)
- 文档解析 < 3s、OCR < 5s、trace 查询 < 200ms

## 禁止事项

- 禁改 `src/` 与 `data/`
- 禁在 `/api/chat` 同步阻塞跑 Agent(25s 级)
- 禁把 trace 存在内存 dict
- 禁把 LLM API key 暴露给前端

## 工作流(planning before coding)

每个 feature 开工前在 `docs/dev/<name>/plan.md` 写清目标/拆解/测试计划,人工 review 后再动手。MVP 顺序:

1. 后端骨架(FastAPI + 健康检查 + 同步版 `/api/chat/sync` 联通 AgentCoordinator)
2. trace 落库
3. `/api/chat` SSE 流式(核心)
4. 上传 + OCR
5. 前端脚手架
6. 对话工作台 + 溯源抽屉(核心)
7. 角色 prompt 适配
8. 批量审核
9. 知识库浏览
10. 三路线对比页

其余架构决策、代码规范、测试策略由 CC 按本规格自行制定并写入 plan。

## 参考文件

- 论文大纲:本系统对应 Chapter 8(System Implementation and Frontend Prototype)
- 已有 `CLAUDE.md`、`README.md`:研究后端的评测脚本说明,不要覆盖它们,把本文件内容并入或作为新章节追加。
