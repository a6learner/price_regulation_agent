# 价格合规智能体 — 前端对接 API 规格

> 本文档提供给 Stitch 用于前端开发。后端地址：`http://localhost:8000`

---

## 一、角色系统

系统有 3 种用户角色，通过请求体 `role` 字段区分：

| role 值 | 中文 | 分析侧重 |
|---------|------|----------|
| `consumer` | 消费者 | 价格欺诈识别、知情权保护、维权措施 |
| `regulator` | 政府监管 | 违法认定、适用法条、证据链、处罚建议 |
| `merchant` | 商家 | 合规风险自查、整改方案、预防机制 |

三个角色使用**同一套页面组件**，后端走同一条分析管线，区别仅在于 AI 分析的角度不同。

---

## 二、API 端点一览

| Method | Path | 用途 |
|--------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/chat` | **核心 — SSE 流式对话** |
| `POST` | `/api/chat/sync` | 同步对话（调试用） |
| `POST` | `/api/upload` | 文档上传提取文本 |
| `GET` | `/api/trace/{trace_id}` | 查询单条完整溯源 |
| `GET` | `/api/traces` | 分页查询历史记录 |
| `GET` | `/api/knowledge/laws` | 浏览法规库 |
| `GET` | `/api/knowledge/cases` | 浏览案例库 |

---

## 三、核心对话 — `POST /api/chat`（SSE 流式）

### 请求

```
POST /api/chat
Content-Type: application/json
```

```json
{
  "query": "某电商平台标注原价1680元但从未以此价格销售",
  "role": "regulator",
  "attachment_text": "（可选）上传文档提取的文本内容"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户输入的价格行为描述 |
| `role` | string | 否 | `consumer` / `regulator` / `merchant`，默认 `consumer` |
| `attachment_text` | string | 否 | 通过 `/api/upload` 提取的文本，附加到查询中 |

### 响应：SSE 事件流

返回 `Content-Type: text/event-stream`，按顺序推送以下 7 种事件：

#### 事件 1：`intent`（意图分析）

```
event: intent
data: {"node":"intent","detail":{"complexity":"medium","violation_type_hints":["误导性价格标示"],"key_entities":{"platforms":["电商平台"],"amounts":["1680元"]},"suggested_laws_k":4,"suggested_cases_k":0}}
```

前端动作：点亮6节点进度条第1步，显示分析复杂度和识别到的关键实体。

#### 事件 2：`retrieval`（法规检索）

```
event: retrieval
data: {"node":"retrieval","detail":{"laws_count":4,"cases_count":0,"laws_preview":[{"title":"明码标价和禁止价格欺诈规定","score":0.82}]}}
```

前端动作：点亮第2步，显示检索到的法规数量和预览。

#### 事件 3：`grading`（质量评分）

```
event: grading
data: {"node":"grading","detail":{"filtered_count":1,"laws_after":3,"cases_after":0}}
```

前端动作：点亮第3步，显示过滤统计。

#### 事件 4：`reasoning`（推理分析）

```
event: reasoning
data: {"node":"reasoning","detail":{"violation_type":"误导性价格标示","is_violation":true,"confidence":0.92}}
```

前端动作：点亮第4步，显示初步判定结果和置信度。这一步耗时最长（LLM 推理），前端可以在等待时显示"正在分析中..."。

#### 事件 5：`reflection`（反思验证）

```
event: reflection
data: {"node":"reflection","detail":{"validation_passed":true,"issues_found":[],"reflection_count":0}}
```

前端动作：点亮第5步，显示验证结果。

#### 事件 6：`remediation`（整改建议）

```
event: remediation
data: {"node":"remediation","detail":{"has_violation":true,"has_risk_flag":false,"steps_count":4}}
```

前端动作：点亮第6步。

#### 事件 7：`done`（完成）

```
event: done
data: {"trace_id":"a1b2c3d4-...","result":{...完整结果对象...}}
```

**`result` 对象包含所有分析细节**，是前端渲染报告和溯源抽屉的数据源。关键字段：

```json
{
  "is_violation": true,
  "violation_type": "误导性价格标示",
  "confidence": 0.92,
  "has_risk_flag": false,
  "reasoning_chain": "1. 事实提取：...\n2. 数据核查：...\n3. 法条匹配：...\n4. 案例参照：...\n5. 综合结论：...",
  "legal_references": ["《明码标价和禁止价格欺诈规定》第十九条"],
  "remediation": {
    "has_violation": true,
    "remediation_steps": ["立即下架虚假原价标注", "..."],
    "generation_mode": "detailed"
  },
  "validation_passed": true,
  "issues_found": [],
  "reflection_count": 0
}
```

前端动作：用 `trace_id` 存起来，点击"查看完整溯源"时调用 `/api/trace/{trace_id}`。

#### 错误事件：`error`

```
event: error
data: {"code":"REASONING_FAILED","message":"推理失败"}
```

错误后仍会推送一个 `done` 事件（`result.success=false`），前端不会卡住。

### 6节点进度条映射

| 步骤 | 事件名 | 中文标签 | 图标建议 |
|------|--------|----------|----------|
| 1 | `intent` | 意图分析 | search / target |
| 2 | `retrieval` | 法规检索 | database / book |
| 3 | `grading` | 质量评分 | filter / star |
| 4 | `reasoning` | 推理分析 | brain / lightbulb |
| 5 | `reflection` | 反思验证 | shield-check / verify |
| 6 | `remediation` | 整改建议 | clipboard-list / tool |

### 前端 SSE 接入方式

**因为 SSE 是 POST 请求**（标准 `EventSource` 只支持 GET），需要用 `fetch` + `ReadableStream` 手动解析：

```javascript
async function streamChat(query, role) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, role })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // 保留未完成的行

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7);
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleSSEEvent(currentEvent, data);
      }
    }
  }
}

function handleSSEEvent(event, data) {
  switch (event) {
    case 'intent':
    case 'retrieval':
    case 'grading':
    case 'reasoning':
    case 'reflection':
    case 'remediation':
      // 点亮对应的进度节点，显示 data.detail 中的摘要
      updateProgressNode(data.node, data.detail);
      break;
    case 'done':
      // 渲染完整报告，保存 data.trace_id
      renderReport(data.result);
      saveTraceId(data.trace_id);
      break;
    case 'error':
      showError(data.message);
      break;
  }
}
```

---

## 四、同步对话 — `POST /api/chat/sync`

与 `/api/chat` 相同的请求体，但直接返回 JSON（阻塞 ~25 秒）：

```json
{
  "trace_id": "a1b2c3d4-...",
  "result": { ... }
}
```

适合调试和不需要进度显示的场景。

---

## 五、文档上传 — `POST /api/upload`

```
POST /api/upload
Content-Type: multipart/form-data
```

| 参数 | 说明 |
|------|------|
| `file` | 上传文件（PDF / DOCX / TXT，最大 20MB） |

响应：

```json
{
  "filename": "处罚决定书.pdf",
  "text_length": 3842,
  "text_preview": "（前500字的文本预览）..."
}
```

**使用流程**：先上传文件拿到提取文本 → 将文本放入 `/api/chat` 的 `attachment_text` 字段。

---

## 六、溯源查询

### `GET /api/trace/{trace_id}`

返回完整分析结果（与 `done` 事件中的 `result` 相同，外加元信息）：

```json
{
  "id": "a1b2c3d4-...",
  "query": "某电商平台标注原价1680元...",
  "role": "regulator",
  "result": { ... },
  "duration_ms": 24500,
  "created_at": "2026-04-18 14:30:22"
}
```

### `GET /api/traces?page=1&page_size=20`

```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "query": "某电商平台标注原价1680元...",
      "role": "regulator",
      "duration_ms": 24500,
      "created_at": "2026-04-18 14:30:22"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## 七、知识库浏览

### `GET /api/knowledge/laws?page=1&page_size=20&q=明码标价`

### `GET /api/knowledge/cases?page=1&page_size=20&q=虚假折扣`

| 参数 | 说明 |
|------|------|
| `page` | 页码，从 1 开始 |
| `page_size` | 每页条数，默认 20 |
| `q` | 可选搜索关键词（语义搜索） |

响应：

```json
{
  "items": [
    {
      "chunk_id": "law_0042",
      "content": "第十九条 经营者不得实施下列价格欺诈行为...",
      "metadata": {
        "law_name": "明码标价和禁止价格欺诈规定",
        "article": "第十九条",
        "law_level": "部门规章"
      }
    }
  ],
  "total": 691,
  "page": 1,
  "page_size": 20
}
```

法规库共 691 条，案例库共 133 条。

---

## 八、错误处理

所有端点的错误统一格式：

```json
{
  "detail": "错误描述信息"
}
```

HTTP 状态码：
- `400` — 请求参数错误（文件格式不支持、文件太大等）
- `404` — trace_id 不存在
- `500` — 服务器内部错误

---

## 九、页面与 API 对应关系

| 页面 | 使用的 API |
|------|-----------|
| 角色选择入口 | 无（纯前端路由） |
| 对话工作台 | `POST /api/chat`（SSE）、`POST /api/upload` |
| 溯源抽屉 | `GET /api/trace/{id}` |
| 历史记录 | `GET /api/traces` |
| 知识库浏览 | `GET /api/knowledge/laws`、`GET /api/knowledge/cases` |
