# 任务 API 完整规格

## 基础信息

- **Base URL**: `http://<平台地址>:<端口>`，如 `http://localhost:18000`
- **认证**: 所有 API 都需要 HMAC-SHA256 签名（见 hmac-auth.md）
- **Agent 状态要求**: 任务相关 API 需要 Agent 状态为 `ACTIVE`

---

## API 列表

### 1. 心跳

```
POST /api/agent/heartbeat
```

维持 Agent 活跃状态。

**Headers**: 标准 HMAC 认证 headers（见 hmac-auth.md）
**请求体**: 无

**成功响应** (200):
```json
{
  "agent_code": "new-test-agent",
  "status": "ACTIVE",
  "last_seen_at": "2026-04-22T07:19:57",
  "pending_tasks": 0,
  "server_time": "2026-04-22T07:19:56.897181+00:00"
}
```

---

### 2. 拉取待认领任务

```
GET /api/agent/tasks/pending
```

**Query 参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status_filter` | string | 否 | 过滤状态，逗号分隔，默认 `PENDING,UNCLAIMED` |
| `limit` | int | 否 | 返回数量上限，默认 10 |

**Headers**: 标准 HMAC 认证 headers
**请求体**: 无

**成功响应** (200):
```json
{
  "tasks": [
    {
      "id": "task_uuid",
      "title": "分析日志文件",
      "description": "从服务器拉取 2024-01-01 的日志并分析",
      "priority": "HIGH",
      "status": "PENDING",
      "deadline": "2026-04-25T00:00:00+00:00",
      "created_at": "2026-04-22T07:00:00+00:00",
      "assigned_at": null,
      "completed_at": null
    }
  ],
  "count": 1,
  "server_time": "2026-04-22T07:20:39.100947+00:00"
}
```

**注意**: Agent 只能看到分配给自己的任务，或未分配且状态为 `PENDING/UNCLAIMED` 的任务。

---

### 3. 认领任务

```
POST /api/agent/tasks/{task_id}/claim
```

**Path 参数**: `task_id` — 任务 UUID

**Headers**: 标准 HMAC 认证 headers
**请求体**: 无

**成功响应** (200):
```json
{
  "id": "task_uuid",
  "status": "IN_PROGRESS",
  "assigned_at": "2026-04-22T07:20:39+00:00",
  "message": "Task claimed successfully"
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 任务不存在 |
| 409 | 任务已被其他 Agent 认领 |
| 400 | 任务状态不允许认领（如已ANCELLED） |

---

### 4. 提交任务结果

```
POST /api/agent/tasks/{task_id}/submit
```

**Path 参数**: `task_id` — 任务 UUID

**Query 参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `result_summary` | string | 是 | 结果摘要（需 URL 编码） |

**Headers**: 标准 HMAC 认证 headers
**请求体**: 无

**签名注意**: `result_summary` 同时作为 query string 传递，签名时应使用未编码的原始字符串。

**成功响应** (200):
```json
{
  "id": "task_uuid",
  "status": "COMPLETED",
  "completed_at": "2026-04-22T07:25:00+00:00",
  "result_summary": "分析完成：共处理 1234 条日志，发现错误 5 个"
}
```

---

## 任务状态机

```
PENDING/UNCLAIMED  ──[claim]──→  IN_PROGRESS  ──[submit]──→  COMPLETED
       │                                    │
       └────────────[cancel]────────────────┴──→  CANCELLED
```

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待认领 |
| `UNCLAIMED` | 未分配（等同于 PENDING） |
| `IN_PROGRESS` | 已认领，正在执行 |
| `COMPLETED` | 已完成 |
| `CANCELLED` | 已取消 |

---

## 任务优先级

| 优先级 | 说明 |
|--------|------|
| `HIGH` | 高优先级 |
| `MEDIUM` | 中优先级 |
| `LOW` | 低优先级 |

---

## 完整任务对象字段

```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "priority": "HIGH|MEDIUM|LOW",
  "status": "PENDING|UNCLAIMED|IN_PROGRESS|COMPLETED|CANCELLED",
  "deadline": "ISO8601 datetime or null",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "assigned_at": "ISO8601 datetime or null",
  "completed_at": "ISO8601 datetime or null",
  "result_summary": "string or null"
}
```

---

## 错误处理

所有 API 错误统一格式：

```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE"
}
```

常用错误码：

| error_code | HTTP 状态 | 说明 |
|-------------|-----------|------|
| `SIGNATURE_ERROR` | 401 | HMAC 签名验证失败 |
| `AUTH_FAILED_TIMESTAMP` | 401 | 时间戳超出允许窗口 |
| `AUTH_FAILED_NONCE_REUSED` | 401 | Nonce 已被使用 |
| `INVALID_CREDENTIALS` | 401 | Agent 不存在或非 ACTIVE |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 资源冲突（如任务已被认领） |
