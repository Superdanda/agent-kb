# Task Board 模块开发进度

> 更新时间: 2026-04-22
> 项目路径: `E:\code\hermes-knowledge-base` (WSL: `/mnt/e/code/hermes-knowledge-base`)

---

## 概述

任务看板模块允许人类用户创建任务、上传材料，Agent 定时查询并完成任务，支持任务状态流转、成果下载、评分和排行榜。

---

## 一、已完成 ✅

### 1.1 项目结构概览

```
E:\code\hermes-knowledge-base\
├── app/
│   ├── modules/task_board/           # 任务看板模块
│   │   ├── models/                   # SQLAlchemy 模型
│   │   ├── routers/                  # FastAPI 路由
│   │   └── services/                 # 业务逻辑层
│   ├── utils/
│   │   └── security_check.py         # 文件安全审查工具
│   └── __init__.py                   # 路由已注册
├── alembic/versions/
│   └── 005_add_task_board.py         # 数据库迁移
└── PROGRESS.md                       # 本文件
```

### 1.2 Models (数据库模型) ✅

| 文件 | 类名 | 说明 |
|------|------|------|
| `app/modules/task_board/models/task.py` | `Task` | 任务主表 |
| `app/modules/task_board/models/task_material.py` | `TaskMaterial` | 任务材料（附件） |
| `app/modules/task_board/models/task_status_log.py` | `TaskStatusLog` | 状态变更日志 |
| `app/modules/task_board/models/task_rating.py` | `TaskRating` | 任务评分 |
| `app/modules/task_board/models/leaderboard.py` | `Leaderboard` | 排行榜 |
| `app/modules/task_board/models/__init__.py` | - | 导出所有模型 |

**Task 模型字段:**
```python
id: UUID (PK)
title: String(512)          # 任务标题
description: Text           # 任务描述
created_by_agent_id: FK     # 创建者
assigned_to_agent_id: FK   # 承接者（Agent）
domain_id: FK              # 知识域
priority: Enum(LOW/MEDIUM/HIGH/URGENT)
difficulty: Enum(EASY/MEDIUM/HARD/EXPERT)
status: Enum(PENDING/IN_PROGRESS/REVIEW/COMPLETED/CANCELLED)
points: Integer             # 积分
estimated_hours: Integer    # 预估工时
actual_hours: Integer       # 实际工时
tags_json: JSON             # 标签
metadata_json: JSON         # 元数据
due_date: DateTime          # 截止时间
started_at: DateTime        # 开始时间
completed_at: DateTime      # 完成时间
created_at/updated_at
```

**枚举定义:**
```python
class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"

class TaskStatus(str, Enum):
    PENDING = "PENDING"       # 待处理
    IN_PROGRESS = "IN_PROGRESS"  # 进行中
    REVIEW = "REVIEW"         # 待审核
    COMPLETED = "COMPLETED"   # 已完成
    CANCELLED = "CANCELLED"   # 已取消

class MaterialType(str, Enum):
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    LINK = "LINK"
    FILE = "FILE"
    REFERENCE = "REFERENCE"

class RatingDimension(str, Enum):
    QUALITY = "QUALITY"
    SPEED = "SPEED"
    COMMUNICATION = "COMMUNICATION"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    OVERALL = "OVERALL"

class LeaderboardPeriod(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ALL_TIME = "ALL_TIME"
```

### 1.3 Routers (API 路由) ✅

| 文件 | 前缀 | 端点 |
|------|------|------|
| `app/modules/task_board/routers/task_router.py` | `/tasks` | 任务 CRUD + 状态变更 + 评分 |
| `app/modules/task_board/routers/material_router.py` | `/materials` | 材料管理 |
| `app/modules/task_board/routers/leaderboard_router.py` | `/leaderboard` | 排行榜 |
| `app/modules/task_board/routers/__init__.py` | - | 导出 |

**API 端点详细:**

```
# 任务 (task_router.py)
POST   /api/tasks                        - 创建任务
GET    /api/tasks                        - 任务列表（?status=&priority=&page=&size=）
GET    /api/tasks/{task_id}              - 任务详情
PUT    /api/tasks/{task_id}              - 更新任务
POST   /api/tasks/{task_id}/status       - 更新状态（body: new_status, change_reason）
GET    /api/tasks/{task_id}/logs          - 状态变更日志
POST   /api/tasks/{task_id}/rate          - 评分（body: rated_agent_id, dimension, score, comment）
GET    /api/tasks/{task_id}/ratings       - 评分列表
GET    /api/tasks/my/tasks                - 我的任务

# 材料 (material_router.py)
POST   /api/materials                     - 创建材料
GET    /api/materials/task/{task_id}      - 任务材料列表
GET    /api/materials/{material_id}       - 材料详情
PUT    /api/materials/{material_id}        - 更新材料
DELETE /api/materials/{material_id}       - 删除材料
POST   /api/materials/reorder             - 排序（body: task_id, material_ids）

# 排行榜 (leaderboard_router.py)
GET    /api/leaderboard                   - 排行榜（?period=DAILY/WEEKLY/MONTHLY/ALL_TIME）
GET    /api/leaderboard/my-rank           - 我的排名
GET    /api/leaderboard/agent/{agent_id}  - Agent 统计
```

**路由注册位置:** `app/__init__.py` 第 38, 46-48 行

### 1.4 Services (业务逻辑) ✅

| 文件 | 类名 | 说明 |
|------|------|------|
| `app/modules/task_board/services/task_service.py` | `TaskService` | 任务 CRUD，状态流转 |
| `app/modules/task_board/services/material_service.py` | `MaterialService` | 材料管理 |
| `app/modules/task_board/services/rating_service.py` | `RatingService` | 评分管理 |
| `app/modules/task_board/services/leaderboard_service.py` | `LeaderboardService` | 排行榜计算 |
| `app/modules/task_board/services/__init__.py` | - | 导出 |

### 1.5 安全审查工具 ✅

| 文件 | 说明 |
|------|------|
| `app/utils/security_check.py` | 文件上传安全审查（337行） |

**API:**
```python
from app.utils.security_check import validate_file_bytes, validate_zip_safety

# 主检查函数
result = validate_file_bytes(filename, file_bytes, scan_content=True)
# result.is_safe: bool
# result.message: str
# result.file_type: str (pdf/zip/exe/elf/macho/unknown)
# result.sha256: str
# result.threats: List[str]

# ZIP 专项检查
result = validate_zip_safety(zip_bytes, max_files=100, max_total_size_mb=50)
```

**检查项:**
1. 扩展名校验（白名单: `.md .txt .pdf .docx .zip`，黑名单: `.exe .bat .py .html .php` 等）
2. Magic bytes 校验（识别 pdf/zip/exe/elf/macho）
3. 扩展名与内容一致性检查
4. 内容危险模式扫描（`<script>` javascript: `import os` subprocess 等）
5. ZIP 安全校验（加密检测、路径遍历、嵌套危险文件）

### 1.6 数据库迁移 ✅

| 文件 | 说明 |
|------|------|
| `alembic/versions/005_add_task_board.py` | 创建 tasks, task_materials, task_status_logs, task_ratings, leaderboards 表 |

**运行迁移:**
```bash
cd /mnt/e/code/hermes-knowledge-base
alembic upgrade head
```

---

## 二、未完成 ❌

### 2.1 Schemas (Pydantic) ❌

**缺失文件:**
```
app/modules/task_board/schemas/
├── __init__.py
├── task.py          # TaskCreate, TaskUpdate, TaskResponse
├── task_material.py # MaterialCreate, MaterialResponse
├── task_rating.py    # RatingCreate, RatingResponse
├── leaderboard.py    # LeaderboardResponse, AgentStats
└── task_status_log.py # StatusLogResponse
```

**要求:**
- 参考 `app/api/schemas/agent.py` 或 `app/api/schemas/domain.py` 的风格
- 使用 Pydantic v2 (`model_config = {"from_attributes": True}`)
- 导入对应模型的 Enum 类型
- **当前 routers 直接返回 SQLAlchemy 模型对象**，需要改为返回 Pydantic schema

**示例 schema 结构:**
```python
# app/modules/task_board/schemas/task.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.modules.task_board.models.task import TaskPriority, TaskDifficulty, TaskStatus

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=512)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: Optional[TaskDifficulty] = None
    domain_id: Optional[str] = None
    points: int = 0
    estimated_hours: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    difficulty: Optional[TaskDifficulty]
    points: int
    # ... 其他字段
    model_config = {"from_attributes": True}
```

### 2.2 Agent 定时任务查询系统 ❌

**缺失文件:** `app/modules/task_board/agent_scheduler.py`

**需求:**
1. **定时轮询任务**
   - 每分钟检查 `status = 'UNCLAIMED'` 的任务
   - 或者检查 `status = 'PENDING'` 需要 Agent 认领

2. **通知 Agent**
   - 调用 Agent 的消息通知接口
   - 或者写入任务队列供 Agent 拉取

3. **Agent 承接任务 API**
   - `POST /api/tasks/{id}/claim` - Agent 承接任务
   - `POST /api/tasks/{id}/submit` - Agent 提交成果（body: result_summary, materials）
   - `POST /api/tasks/{id}/abandon` - Agent 放弃任务（需说明原因）

4. **状态机完善**
   ```
   PENDING -> UNCLAIMED -> IN_PROGRESS -> SUBMITTED -> REVIEW -> CONFIRMED -> RATED
                                    |           |
                                    v           v
                                CANCELLED   CANCELLED
   ```

**参考现有调度器:** `app/services/agent_scheduler_service.py` (定时任务框架)

### 2.3 前端页面 ❌

**缺失页面:**
```
app/web/templates/task_board/
├── list.html           # 任务看板列表
├── detail.html         # 任务详情页
├── create.html          # 创建任务
├── edit.html            # 编辑任务
├── materials.html       # 材料管理
└── leaderboard.html     # 排行榜

app/web/routes/task_board_pages.py  # 页面路由
```

**功能要求:**

1. **任务列表页** (`list.html`)
   - 筛选：状态、优先级、负责人、创建者
   - 排序：创建时间、优先级、截止时间
   - 分页
   - 快捷操作：认领、查看详情

2. **任务详情页** (`detail.html`)
   - 显示任务完整信息
   - 显示承接的 Agent
   - 材料列表（上传/下载）
   - 状态变更历史
   - 成果下载（标记为 is_result=true 的材料）
   - 评分区域（任务确认后）
   - 按钮：确认完成 / 拒绝完成

3. **任务创建/编辑页** (`create.html`, `edit.html`)
   - 表单：标题、描述、优先级、难度、积分、预估工时、截止时间
   - 材料上传（调用安全审查）
   - 标签输入

4. **排行榜页** (`leaderboard.html`)
   - 切换：日/周/月/总榜
   - 排名列表：Agent 名、任务数、平均评分、总积分
   - 突出显示当前 Agent 的排名

**参考现有页面:** `app/web/templates/posts/` 下的模板

### 2.4 文件上传与下载 ❌

**缺失功能:**
1. **实际上传接口** - 当前 material_router 只有 metadata，没有实际文件存储
2. **下载接口** - 需要实现文件流下载
3. **材料标记为成果** - `is_result` 字段需要添加到 TaskMaterial

**需要添加:**
```python
# TaskMaterial 模型添加字段
is_result: bool = Column(Boolean, default=False)

# material_router.py 添加
POST /api/materials/upload          # 上传文件（含安全审查）
GET  /api/materials/{id}/download    # 下载文件
POST /api/materials/{id}/mark-result # 标记为成果
```

**存储路径:** `uploads/task_board/{task_id}/{material_id}/{filename}`

### 2.5 激励机制完善 ❌

**积分规则（计划实现）:**
```python
# 任务完成基础积分
BASE_POINTS = 10

# 评分加成
RATING_BONUS = score * 2

# 优先级加成
PRIORITY_BONUS = {
    "URGENT": 8,
    "HIGH": 5,
    "MEDIUM": 3,
    "LOW": 0,
}

# 总积分 = BASE_POINTS + RATING_BONUS + PRIORITY_BONUS
```

**排行榜更新时机:**
- 任务状态变为 `CONFIRMED` 时，更新排行榜
- 需要在 `LeaderboardService.update_on_task_complete()` 中实现

---

## 三、目录结构

### 3.1 当前结构

```
app/modules/task_board/
├── __init__.py
├── models/
│   ├── __init__.py                    ✅
│   ├── task.py                        ✅
│   ├── task_material.py               ✅
│   ├── task_status_log.py             ✅
│   ├── task_rating.py                 ✅
│   └── leaderboard.py                 ✅
├── routers/
│   ├── __init__.py                    ✅
│   ├── task_router.py                 ✅
│   ├── material_router.py             ✅
│   └── leaderboard_router.py          ✅
├── services/
│   ├── __init__.py                    ✅
│   ├── task_service.py                ✅
│   ├── material_service.py            ✅
│   ├── rating_service.py              ✅
│   └── leaderboard_service.py         ✅
└── schemas/                            ❌ 需要创建
    ├── __init__.py
    ├── task.py
    ├── task_material.py
    ├── task_rating.py
    ├── leaderboard.py
    └── task_status_log.py

app/utils/
└── security_check.py                  ✅

alembic/versions/
└── 005_add_task_board.py              ✅
```

### 3.2 完整目标结构

```
app/modules/task_board/
├── __init__.py
├── models/                            ✅ 完成
│   ├── __init__.py
│   ├── task.py
│   ├── task_material.py
│   ├── task_status_log.py
│   ├── task_rating.py
│   └── leaderboard.py
├── routers/                            ✅ 完成
│   ├── __init__.py
│   ├── task_router.py
│   ├── material_router.py
│   └── leaderboard_router.py
├── services/                           ✅ 完成
│   ├── __init__.py
│   ├── task_service.py
│   ├── material_service.py
│   ├── rating_service.py
│   └── leaderboard_service.py
├── schemas/                             ❌ 待创建
│   ├── __init__.py
│   ├── task.py
│   ├── task_material.py
│   ├── task_rating.py
│   ├── leaderboard.py
│   └── task_status_log.py
├── agent_scheduler.py                  ❌ 待创建（Agent 定时查询）

app/web/
├── templates/task_board/               ❌ 待创建
│   ├── list.html
│   ├── detail.html
│   ├── create.html
│   ├── edit.html
│   └── leaderboard.html
└── routes/task_board_pages.py           ❌ 待创建
```

---

## 四、技术参考

### 4.1 项目代码风格

- **ORM:** SQLAlchemy，使用 `Session = Depends(get_db)`
- **Schema:** Pydantic v2，`model_config = {"from_attributes": True}`
- **认证:** `get_current_agent = Depends(get_current_agent)` 返回 agent_id (str)
- **异常:** 使用 `app.core.exceptions` 中的 `ResourceNotFoundError`, `PermissionDeniedError`
- **数据库:** MySQL + Alembic 迁移

### 4.2 关键导入

```python
from app.core.database import get_db, Base
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority, TaskDifficulty
```

### 4.3 现有枚举值

```python
TaskPriority: "LOW", "MEDIUM", "HIGH", "URGENT"
TaskDifficulty: "EASY", "MEDIUM", "HARD", "EXPERT"
TaskStatus: "PENDING", "IN_PROGRESS", "REVIEW", "COMPLETED", "CANCELLED"
MaterialType: "DOCUMENT", "IMAGE", "LINK", "FILE", "REFERENCE"
RatingDimension: "QUALITY", "SPEED", "COMMUNICATION", "PROBLEM_SOLVING", "OVERALL"
LeaderboardPeriod: "DAILY", "WEEKLY", "MONTHLY", "ALL_TIME"
```

---

## 五、工作阶段

### 阶段 1: Schemas 创建 ✅ 已完成

- [x] 创建 `app/modules/task_board/schemas/` 目录
- [x] 创建 `task.py` - TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
- [x] 创建 `task_material.py` - MaterialCreate, MaterialUpdate, MaterialResponse
- [x] 创建 `task_rating.py` - RatingCreate, RatingResponse
- [x] 创建 `leaderboard.py` - LeaderboardEntry, LeaderboardResponse, AgentStats
- [x] 创建 `task_status_log.py` - StatusLogResponse
- [x] 更新 routers 使用 schemas 替代直接返回 ORM 模型

### 阶段 2: 文件上传/下载功能 ✅ 已完成

- [x] TaskMaterial 模型添加 `is_result` 字段
- [x] 创建 `file_router.py` 的实际上传下载接口
- [x] 集成 `security_check.py` 到上传流程
- [x] 实现文件存储（本地 `uploads/` 目录）
- [x] 创建下载接口（流式响应）
- [x] 标记成果材料功能
- [x] 创建数据库迁移 `006_add_material_is_result.py`

### 阶段 3: Agent 定时任务查询 ✅ 已完成

- [x] 创建 `agent_scheduler.py` 定时任务
- [x] 实现轮询未承接任务逻辑
- [x] 实现 Agent 承接、提交成果、放弃任务的 API
- [x] 完善状态机流转
- [x] 添加确认/拒绝任务接口

### 阶段 4: 前端页面 ✅ 已完成

- [x] 创建 `app/web/routes/task_board_pages.py`
- [x] 创建 `app/web/templates/task_board/` 模板
- [x] 任务列表页
- [x] 任务详情页（含成果下载）
- [x] 任务创建/编辑页
- [x] 排行榜页面
- [x] 在 `app/__init__.py` 注册页面路由

### 阶段 5: 激励机制 ✅ 已完成

- [x] 实现 LeaderboardService 排行榜计算
- [x] 任务完成时自动更新排行榜
- [x] 评分加成计算
- [x] 优先级加成计算

### 阶段 6: 测试与文档 🔄 进行中

- [ ] API 接口测试
- [ ] 前端功能测试
- [x] 更新 PROGRESS.md

---

## 六、快速开始

### 运行数据库迁移

```bash
cd /mnt/e/code/hermes-knowledge-base
alembic upgrade head
```

### 启动服务

```bash
cd /mnt/e/code/hermes-knowledge-base
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 测试 API

```bash
# 创建任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "测试任务", "description": "测试描述", "priority": "MEDIUM"}'

# 获取任务列表
curl http://localhost:8000/api/tasks

# 获取排行榜
curl http://localhost:8000/api/leaderboard?period=WEEKLY
```

---

## 七、注意事项

1. **Agent 认证:** 所有 API 需要通过 `get_current_agent` 获取当前 agent_id
2. **文件安全:** 所有上传文件必须经过 `security_check.py` 审查
3. **状态机:** 状态变更必须记录到 `TaskStatusLog`
4. **排行榜:** 任务确认完成后调用 `LeaderboardService.update_on_task_complete()`
5. **Material Type:** 目前 material_router 的 `material_type` 是 Enum，传入字符串需确认格式一致
