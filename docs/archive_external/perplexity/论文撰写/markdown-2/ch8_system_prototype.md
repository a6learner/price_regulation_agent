# 8 Web Interactive Prototype

## 8.1 Design Goals

The batch evaluation scripts in `scripts/` are designed for one thing: running a fixed dataset through a pipeline and writing metrics to a JSON file. That is the right tool for rigorous comparison, but it leaves no room for human involvement. A regulator who wants to check whether a specific merchant's pricing page looks problematic cannot run `run_agent_eval.py`—and even if they could, they would not get a result tailored to their enforcement context.

The Web prototype was built to close that gap. The core design goal is a human-in-the-loop interface where a user can describe a pricing situation in plain text, watch the six-node agent pipeline process it in real time, and receive a structured compliance report—without needing to understand anything about the underlying retrieval or reasoning machinery.

Three user roles shape the experience: a **consumer** who suspects price fraud and wants to know their rights, a **regulator** conducting an enforcement review, and a **merchant** running a self-compliance check before a promotion. Each role gets an identical analytical pipeline—the same six nodes, the same ChromaDB knowledge base, the same Qwen3-8B LLM—but receives a remediation block written for their specific situation. A consumer gets guidance on evidence preservation and complaint channels; a regulator gets a structured enforcement memo with a risk tier; a merchant gets a checklist of corrective actions.

A secondary goal was modularity: the web system should reuse the agent code without duplicating it, and the knowledge browser should allow users to explore the 691-article legal database and 133-case history independently of any specific query.

## 8.2 Overall Architecture

The system uses a decoupled front-end / back-end architecture, connected over a local proxy during development.

```
Browser (localhost:5173)
  │
  │  /api/*  →  Vite proxy
  ▼
FastAPI backend (localhost:8000)
  │
  ├── StreamingCoordinator → AgentCoordinator (6 nodes)
  ├── ChromaDB  (691 laws + 133 cases, shared with eval pipeline)
  └── SQLite traces.db  (conversation history + full results)
```

The browser is served by Vite's development server on port 5173. Any request whose path starts with `/api/` is transparently forwarded to the FastAPI backend on port 8000 via a proxy rule in `web/frontend/vite.config.ts`. The backend loads `AgentCoordinator` at startup, together with the embedding model and BM25 index; cold-start takes roughly 10–15 seconds. After that, each incoming chat request is handled by `StreamingCoordinator`, which wraps `AgentCoordinator` and streams node-by-node progress back to the browser over Server-Sent Events (SSE).

All conversation records—including the user query, the assigned role, the full JSON result, and `duration_ms`—are persisted asynchronously to a SQLite database at `web/backend/traces.db`. No data leaves the local machine; the only external call is the MaaS inference request to 讯飞星辰.

## 8.3 Technology Stack

Table 8-1 lists every layer of the stack with its version. The choices were guided by two constraints: reuse the existing Python agent code without modification, and build a front end capable of rendering streaming updates and navigating between three pages.^[41]^^[42]^

**Table 8-1** Web prototype technology stack.

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | React + TypeScript | 19 + 6.0 |
| Build tool | Vite | 8.0 |
| Styling | Tailwind CSS | 4.2 |
| Routing | React Router | 7.x |
| Backend framework | FastAPI | 0.115+ |
| Streaming | SSE (sse-starlette) | 2.0+ |
| Persistence | SQLite (aiosqlite) | — |
| Vector database | ChromaDB | 1.5+ |
| Embedding model | BAAI/bge-small-zh-v1.5 | 512-dim |
| Re-ranker | BAAI/bge-reranker-v2-m3 | — |
| LLM | 讯飞星辰 MaaS (Qwen3-8B) | — |

React was chosen over alternatives such as Vue or plain HTML because the front end needed component-level state management for the six-node progress bar, the trace drawer, and the knowledge browser—all of which update independently. Tailwind CSS 4's utility-first approach allowed rapid iteration on the layout without a separate design system. FastAPI's native support for asynchronous handlers fits naturally with SSE streaming and non-blocking SQLite writes via aiosqlite.

## 8.4 Information Architecture

The application contains three pages, navigated via a top bar.

### 8.4.1 Role Selection Page

The landing page presents three cards side by side: Consumer (消费者), Regulator (政府监管), and Merchant (网店商家). Clicking a card routes the user to the chat workstation and passes the selected role as a URL parameter, which is then included in every API request.

On the backend, `web/backend/services/role_prompt.py` maps each role to a system-prompt prefix that is prepended to the user query before it reaches the agent pipeline. The consumer prefix orients the analysis toward rights-protection and complaint procedures; the regulator prefix emphasises violation identification, evidence chain, and applicable penalty ranges; the merchant prefix shifts the remediation output toward a corrective action checklist. The analytical nodes themselves are role-agnostic—only the RemediationAdvisor's output format changes.

![Figure 8-1: Role selection landing page showing three cards — Consumer, Regulator, Merchant](figures/ch8_role_selection.png)

Figure 8-1 The role selection page. Each card routes to the chat workstation with the corresponding role context.

### 8.4.2 Chat Workstation

The chat workstation is the primary interaction surface. The layout places conversation history in a collapsible left panel, the main conversation area in the centre, and a slide-out trace drawer on the right.

When a user submits a query, the centre panel displays a six-step progress bar whose nodes light up in sequence as SSE events arrive from the backend: **intent analysis → law retrieval → relevance grading → legal reasoning → reflection → remediation**. The bar gives the user a live view of where the pipeline is without requiring them to understand what happens at each step. The slowest step—retrieval, at roughly 19 seconds on average—is the one where users see the longest pause; knowing that the system is actively working at that point matters for usability.

Once the `done` event arrives, the workstation renders a **report card** containing six fields: the violation conclusion with confidence, the violation type, the legal basis (with an expandable panel showing full article text from the retrieved sources), the full reasoning chain, and the role-specific remediation block.

Users can attach a document—PDF, DOCX, or TXT—via the 📎 button beside the input field. The file is sent to `/api/upload`, which extracts the text and returns it to the front end; the extracted text is then injected into the next query as `attachment_text`. This allows a regulator, for example, to upload a screenshot-derived text of a product listing and have the agent analyse it directly.

![Figure 8-2: Chat workstation mid-flow showing the six-node progress bar with retrieval active](figures/ch8_chat_workstation.png)

Figure 8-2 Chat workstation during an active query. The progress bar shows the system advancing through the six pipeline nodes. The report card will appear in this panel once the `done` event is received.

### 8.4.3 Knowledge-Base Browser

The third page lets users explore the underlying knowledge base without running a query. Two tabs expose the law collection (691 articles, backed by `GET /api/knowledge/laws`) and the case collection (133 historical enforcement cases, backed by `GET /api/knowledge/cases`). Both support keyword search and pagination.

The search uses the same BAAI/bge-small-zh-v1.5 embedding model and ChromaDB collection as the retrieval pipeline, so the distance scores returned by the browser are directly comparable to those used during agent reasoning. A user who searches for "虚假折扣" in the law browser will see roughly the same articles that the retriever would surface for a query containing that phrase.

![Figure 8-3: Knowledge-base browser showing paginated law articles with a search bar](figures/ch8_knowledge_browser.png)

Figure 8-3 Knowledge-base browser displaying the 691-article law collection. The search bar at the top performs semantic search using the same embedding model as the RAG retrieval pipeline.

## 8.5 Streaming via SSE

Server-Sent Events provide a simple, unidirectional channel from server to browser over a persistent HTTP connection.^[40]^ We use `sse-starlette 2+` on the FastAPI side, which integrates with Python's `asyncio` event loop without blocking.

**Table 8-2** Web API endpoints.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check; returns `{ "status": "ok" }` |
| POST | `/api/chat` | SSE streaming chat (primary) |
| POST | `/api/chat/sync` | Synchronous chat for debugging (~25 s blocking) |
| POST | `/api/upload` | Document upload; returns extracted text |
| GET | `/api/trace/{id}` | Retrieve full trace record by ID |
| GET | `/api/traces` | Paginated trace history |
| DELETE | `/api/trace/{id}` | Delete single trace |
| DELETE | `/api/traces` | Clear all trace history |
| GET | `/api/knowledge/laws` | Browse/search law articles |
| GET | `/api/knowledge/cases` | Browse/search enforcement cases |

The `POST /api/chat` endpoint accepts a JSON body with three fields: `query` (required), `role` (optional, defaults to `consumer`), and `attachment_text` (optional). The backend prepends the role-specific system-prompt prefix from `role_prompt.py`, instantiates a `StreamingCoordinator`, and begins yielding SSE events.

The synchronous endpoint `POST /api/chat/sync` exists for debugging and scripted testing. It accepts the same request body but blocks until the full result is assembled, returning a JSON object with `trace_id` and `result`. Because the Agent pipeline takes roughly 37 seconds on average, this endpoint is not suitable for interactive use—it is there to make it easy to inspect complete results from a command-line tool or test harness without parsing an SSE stream.

The event sequence mirrors the agent pipeline exactly: `intent` → `retrieval` → `grading` → `reasoning` → `reflection` → `remediation` → `done`. Each event's `data` payload contains the partial result from that node, so the front end can render intermediate outputs (e.g., the list of retrieved articles) before the final report is ready. The terminal `done` event carries `trace_id` and the complete `result` object, including `retrieved_legal_sources` (full article text for all retrieved chunks). After dispatching `done`, the backend writes the full record to SQLite asynchronously.

Swagger documentation is available at `http://localhost:8000/docs` when the backend is running.

## 8.6 Reuse of the Evaluation Pipeline

A key design decision was that the web system must not introduce a second copy of the agent logic. The batch evaluator and the web prototype both call the same `AgentCoordinator` class from `src/agents/agent_coordinator.py`; the only layer added by the web system is `StreamingCoordinator` (`web/backend/services/streaming_coordinator.py`), which wraps `AgentCoordinator.process()` and yields intermediate results as SSE events after each node completes.

Because of this shared code path, there is no risk of the interactive prototype silently using different retrieval parameters, a different reflection threshold, or a different violation-type matching configuration than the batch evaluator. Any change to the agent's behaviour propagates to both consumers.

The 780-sample batch results in Chapter 7 remain the authoritative quality measure for this system. The Web prototype is not a replacement for those results—it is a different mode of use, designed for one-off interactive queries rather than aggregate performance measurement. Both serve a purpose; neither substitutes for the other.

## 8.7 Boundary Between Prototype and Batch Evaluator

It is worth being explicit about what belongs to each component.

The **batch evaluator** owns: dataset management (loading `eval_dataset_v4_final.jsonl`), ground-truth comparison, metric calculation (`ResponseParser`, `BaselineEvaluator`, `RAGEvaluator`, `AgentCoordinator.process` called in a loop), results serialisation to `results/`, and the aggregate statistics tables in Chapter 7.

The **web prototype** owns: user session management, role routing, SSE streaming, trace persistence to SQLite, document upload and text extraction, the knowledge-base browser, and the three React pages. It does not compute aggregate metrics; it does not read the evaluation dataset; and it does not write to `results/`.

Any latency figures cited from interactive sessions would not be comparable to the batch evaluation numbers in Table 7-1, because the batch evaluator runs queries sequentially on a dedicated machine whereas the web prototype is designed for single-user interactive use with network overhead. Do not mix the two.

## 8.8 Early-Design Pivot from Streamlit

Early in the project we considered building the front end with Streamlit, which would have allowed rapid prototyping within a single Python process. We switched to a decoupled React front + FastAPI back for three reasons: it separates UI development entirely from the batch-evaluation scripts (which are also Python), it enables proper multi-page navigation with React Router rather than a single-page layout, and it provides a natural extension point for future features such as the knowledge browser and an audit-log page that would be awkward to build inside Streamlit's widget model.

## 8.9 Limitations

**MaaS external dependency.** Every chat request must reach the 讯飞星辰 API endpoint. In offline environments or under network degradation, the prototype cannot function. Moving to a locally-served LLM or a self-hosted inference endpoint would remove this dependency, but is out of scope for this project.

**Dual-port development setup.** Running frontend on port 5173 and backend on port 8000 is straightforward during development but requires two terminal sessions and is not suitable for production deployment as-is. The README documents a single-port packaging approach (building the React app with `npm run build` and mounting the `dist/` directory as a FastAPI static route), but we have not validated it under load.

**No authentication.** The current prototype assumes a trusted local environment. Anyone with network access to the running instance can read all stored traces, query the agent, and delete conversation history. Adding OAuth or token-based authentication is a prerequisite for any deployment beyond a single developer's workstation.

## 8.10 Summary of This Chapter

We described a working React + TypeScript + Vite front end paired with a FastAPI + SSE + SQLite back end that exposes the full six-node agent pipeline as an interactive web application. Three user roles—consumer, regulator, and merchant—receive identical analytical results with role-specific remediation framing. The technology stack is listed in Table 8-1; the API surface is documented in Table 8-2.

The system was built on the principle of code reuse: `StreamingCoordinator` wraps the same `AgentCoordinator` used in batch evaluation, so there is no divergence between the interactive and batch code paths. The 780-sample evaluation results from Chapter 7 remain the authoritative quality benchmark; the prototype complements them by providing a human-in-the-loop access mode that the batch scripts were never designed to support.

The directory structure under `web/` separates concerns cleanly: `backend/routers/` handles HTTP routing, `backend/services/` contains the agent wrapping and role-prompt logic, and `frontend/src/components/` holds the reusable React components. This layout makes it straightforward to extend any single layer—adding a new role, swapping the LLM endpoint, or redesigning the report card—without touching the others. The limitations noted in Section 8.9 are engineering problems with known solutions; the architecture itself is sound.
