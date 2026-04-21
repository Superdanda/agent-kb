# Task Board 模块开发进度

> 更新时间: 2026-04-21

## 概述

任务看板模块允许人类用户创建任务、上传材料，Agent 定时查询并完成任务，支持任务状态流转、成果下载、评分和排行榜。

---

## 一、已完成 ✅

### 1.1 Models (数据库模型)

| 文件 | 说明 |
|------|------|
| `app/modules/task_board/models/task.py` | Task 任务模型（状态、优先级、难度、积分等） |
| `app/modules/task_board/models/task_material.py` | TaskMaterial 材料模型（上传的附件/成果） |
| `app/modules/task_board/models/task_status_log.py` | TaskStatusLog 状态变更日志 |
| `app/modules/task_board/models/task_rating.py` | TaskRating 任务评分（多维度） |
| `app/modules/task_board/models/leaderboard.py` | Leaderboard 排行榜（周期积分） |
| `app/modules/task_board/models/__init__.py` | 模型导出 |

**任务状态枚举 (TaskStatus):**
- `pending` - 待发布
- `unclaimed` - 未承接
- `in_progress` - 进行中
- `submitted` - 已提交待确认
- `confirmed` - 已确认完成
- `rated` - 已评分
- `cancelled` - 已取消

**任务优先级 (TaskPriority):** low / medium / high / urgent

**任务难度 (TaskDifficulty):** easy / medium / hard / expert

### 1.2 Routers (API 路由)

| 文件 | 说明 |
|------|------|
| `app/modules/task_board/routers/task_router.py` | 任务 CRUD + 状态变更 + 评分 |
| `app/modules/task_board/routers/material_router.py` | 材料上传/下载/管理 |
| `app/modules/task_board/routers/leaderboard_router.py` | 排行榜 API |
| `app/modules/task_board/routers/__init__.py` | 路由导出 |

**API 端点:**
```
POST   /api/tasks              - 创建任务
GET    /api/tasks              - 任务列表（分页/筛选）
GET    /api/tasks/{id}         - 任务详情
PUT    /api/tasks/{id}         - 更新任务
POST   /api/tasks/{id}/status  - 更新状态
GET    /api/tasks/{id}/logs    - 状态变更日志
POST   /api/tasks/{id}/rate    - 评分
GET    /api/tasks/{id}/ratings - 评分列表
GET    /api/tasks/my/tasks     - 我的任务

POST   /api/materials          - 上传材料
GET    /api/materials/task/{id} - 任务材料列表
GET    /api/materials/{id}      - 材料详情
PUT    /api/materials/{id}     - 更新材料
DELETE /api/materials/{id}     - 删除材料
POST   /api/materials/reorder  - 排序材料

GET    /api/leaderboard              - 排行榜
GET    /api/leaderboard/my-rank     - 我的排名
GET    /api/leaderboard/agent/{id}  - Agent 统计
```

### 1.3 Services (业务逻辑)

| 文件 | 说明 |
|------|------|
| `app/modules/task_board/services/task_service.py` | 任务业务逻辑 |
| `app/modules/task_board/services/material_service.py` | 材料管理 + 安全审查调用 |
| `app/modules/task_board/services/rating_service.py` | 评分管理 |
| `app/modules/task_board/services/leaderboard_service.py` | 排行榜计算 |
| `app/modules/task_board/services/__init__.py` | 服务导出 |

### 1.4 安全审查工具

| 文件 | 说明 |
|------|------|
| `app/utils/security_check.py` | 文件安全审查工具（337行） |

**功能:**
- 扩展名校验（白名单/黑名单）
- Magic bytes 校验（PDF/ZIP/EXE/ELF 等）
- 内容危险模式扫描（`<script>`、javascript:、PHP 标签、恶意代码等）
- ZIP 安全校验（路径遍历、嵌套危险文件）
- SHA256 计算

### 1.5 数据库迁移

| 文件 | 说明 |
|------|------|
| `alembic/versions/005_add_task_board.py` | 创建所有 task_board 表 |

### 1.6 路由注册

- `app/__init__.py` - 已注册 task_router, material_router, leaderboard_router

---

## 二、未完成 ❌

### 2.1 Schemas (Pydantic)

| 文件 | 状态 |
|------|------|
| `app/modules/task_board/schemas/task.py` | ❌ 缺失 |
| `app/modules/task_board/schemas/task_material.py` | ❌ 缺失 |
| `app/modules/task_board/schemas/task_rating.py` | ❌ 缺失 |
| `app/modules/task_board/schemas/leaderboard.py` | ❌ 缺失 |
| `app/modules/task_board/schemas/task_status_log.py` | ❌ 缺失 |

> 注: routers 目前直接使用 SQLAlchemy 模型作为响应，未经过 Pydantic schema 转换。后续需要补充 schemas。

### 2.2 Agent 定时任务查询系统

| 文件 | 状态 |
|------|------|
| `app/modules/task_board/agent_scheduler.py` | ❌ 缺失 |

需要实现:
- 定时轮询未承接任务（unclaimed 状态）
- 通知有能力的 Agent
- 记录轮询日志

### 2.3 前端页面

| 页面 | 状态 |
|------|------|
| 任务看板列表页 | ❌ 缺失 |
| 任务创建/编辑页 | ❌ 缺失 |
| 任务详情页（含成果下载） | ❌ 缺失 |
| 排行榜页面 | ❌ 缺失 |

### 2.4 任务状态机完善

当前状态流转:
```
pending -> unclaimed -> in_progress -> submitted -> confirmed -> rated
                                              ↓
                                         cancelled
any -> cancelled
```

需要 Agent 侧完善:
- Agent 承接任务逻辑
- Agent 提交成果逻辑
- Agent 取消承接逻辑

### 2.5 激励机制

积分规则（计划）:
- 任务完成基础积分: 10分
- 评分加成: score × 2 分
- 优先级加成: urgent=8, high=5, medium=3, low=0

---

## 三、目录结构

```
app/modules/task_board/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── task.py
│   ├── task_material.py
│   ├── task_status_log.py
│   ├── task_rating.py
│   └── leaderboard.py
├── routers/
│   ├── __init__.py
│   ├── task_router.py
│   ├── material_router.py
│   └── leaderboard_router.py
├── services/
│   ├── __init__.py
│   ├── task_service.py
│   ├── material_service.py
│   ├── rating_service.py
│   └── leaderboard_service.py
└── schemas/                   # ❌ 待创建
    ├── __init__.py
    ├── task.py
    ├── task_material.py
    ├── task_rating.py
    ├── leaderboard.py
    └── task_status_log.py

app/utils/
└── security_check.py          # ✅ 文件安全审查

alembic/versions/
└── 005_add_task_board.py       # ✅ 数据库迁移
```

---

## 四、下一步工作

1. **高优先级:**
   - [ ] 创建 schemas 目录和 schema 文件
   - [ ] 完善 agent_scheduler.py 实现定时查询
   - [ ] 修复 routers 中直接使用 ORM 模型的问题（改用 schemas）

2. **中优先级:**
   - [ ] 前端任务看板页面
   - [ ] 前端排行榜页面
   - [ ] 成果材料下载功能

3. **低优先级:**
   - [ ] 任务分类/标签系统
   - [ ] 任务评论/讨论功能
   - [ ] 任务模板功能
