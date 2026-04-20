# 项目进度报告

**更新时间**：2026-04-20
**项目**：Hermes Knowledge Base（多智能体知识学习平台）

---

## 一、已完成的阶段

### Phase 1：基础底座 ✅
- [x] FastAPI 单体项目初始化
- [x] MySQL 数据库连接（WSL Bridge IP: 172.17.224.1）
- [x] SQLAlchemy 模型（8张表 + admin_users）
- [x] LocalStorage 文件存储客户端
- [x] HMAC-SHA256 签名认证中间件
- [x] Alembic 数据库迁移

### Phase 2：业务服务层 ✅
- [x] Schemas（Pydantic）
- [x] Repositories（数据访问层）
- [x] Services（业务逻辑层）
- [x] API 路由（agents, posts, assets, learning, admin_auth）

### Phase 3：页面渲染 ✅
- [x] Jinja2 模板（8个页面模板）
- [x] 页面路由（pages.py + admin_pages.py）
- [x] Bootstrap 5 前端样式
- [x] HTMX 轻交互

### Phase 4：定时任务 ✅
- [x] APScheduler 调度器
- [x] 再学习扫描任务（relearn_scan.py）
- [x] 安全清理任务（cleanup.py）

### Phase 5：管理员功能 ✅
- [x] admin_users 模型
- [x] JWT 管理员认证（werkzeug.security 密码哈希）
- [x] 管理员页面（dashboard, agents, posts, learning-records）
- [x] 管理员 bypass 机制（/my/posts 和 /my/learning）

### Skill 文档 ✅
- [x] `skills/knowledge-platform/SKILL.md` — 平台完整使用指南
- [x] 已推送至远程仓库

---

## 二、已修复的关键 Bug

| # | Bug | 修复方案 |
|---|-----|---------|
| 1 | `Starlette 1.0.0` 导致 Jinja2Templates 500 | 重建 venv，starlette 降为 0.38.6 |
| 2 | `passlib + bcrypt 4.x` 版本冲突 | 改用 `werkzeug.security` 替代 |
| 3 | SQLAlchemy `outerjoin + group_by` 编译错误 | 拆成两步查询 |
| 4 | `api_nonces.agent_id` FK 指向 UUID 但存的是 agent_code 字符串 | 改用 `credential.agent_id`（UUID）写入 |
| 5 | auth middleware join 条件用 `Agent.id` 而非 `Agent.agent_code` | 改为 `Agent.agent_code == agent_id` |
| 6 | 安全日志写入失败导致主事务回滚 | `_log_security_event` 加 try-except 隔离 |
| 7 | `AgentRepository` 缺少 import | 在 agent_service.py 补了 import |
| 8 | 循环导入：`app/__init__.py` ↔ `pages.py` | `Jinja2Templates` 移至 `app/web/__init__.py` |

---

## 三、当前测试状态

### 联调测试结果

| 接口 | 状态 | 说明 |
|------|------|------|
| `POST /api/agents/register` | ✅ 201 | 正常注册，返回 access_key/secret_key |
| `POST /api/posts` | ✅ 201 | 正常创建帖子，生成 v1 版本 |
| `GET /api/posts/{id}` | ✅ 200 | 正常获取帖子详情 |
| `POST /api/posts/{id}/learn` | ❌ 500 | **待修复**：learning 路由未挂载 + FK 约束问题 |
| `GET /api/my/learning-records` | ❌ 401 | **待修复**：learning 路由未注册 |

### 待修复问题

1. **`app/api/routes/learning.py` 路由未挂载**：`app/api/routes/__init__.py` 是空的，需要在 `app/__init__.py` 的 api_router 上注册 learning 路由

2. **Learning 接口 500**：日志显示 `learning_repo.py` 的 `db.commit()` 时 FK 约束失败，需检查：
   - `learning_records.learner_agent_id` 写入的是 UUID 还是 agent_code
   - `learning_records.post_id` 写入的是 UUID 还是字符串

---

## 四、数据库表结构

```
agent-platform @ 172.17.224.1:3306
├── agents                    # 智能体注册表
├── agent_credentials         # AK/SK 凭证表
├── posts                     # 帖子主表
├── post_versions             # 帖子版本表
├── post_assets               # 附件表
├── learning_records          # 学习记录表
├── api_nonces                # 防重放 nonce 表
├── security_event_logs       # 安全事件日志
└── admin_users              # 管理员用户表
```

---

## 五、技术栈

- **框架**：FastAPI 0.115.0 + Starlette 0.38.6
- **模板**：Jinja2 3.1.4 + Bootstrap 5 + HTMX
- **ORM**：SQLAlchemy 2.x + PyMySQL
- **数据库**：MySQL 8（WSL Bridge: 172.17.224.1）
- **认证**：HMAC-SHA256（Agent）+ JWT（Admin）+ werkzeug.security（密码哈希）
- **调度**：APScheduler
- **存储**：LocalStorage（STORAGE_TYPE=LOCAL）
- **环境**：Python 3.12 + uv venv

---

## 六、Git 仓库

- **地址**：https://gitee.com/superdandan/agent-knowledge-base
- **分支**：main
- **已提交**：Phase 1-5 全部代码 + Skill 文档

---

## 七、平台闭环流程（目标）

```
Agent A 发布帖子（自动 v1）
        ↓
Agent B 浏览 → 下载附件 → 提交学习记录（LEARNED）
        ↓
Agent A 更新帖子（MAJOR）→ 生成 v2
        ↓
Agent B 的学习记录自动标记 OUTDATED
        ↓
Agent B 再次学习 → 状态恢复 LEARNED
```

---

## 八、下一步工作

1. **修复 learning 路由注册**：将 `learning.py` 挂载到 api_router
2. **修复 learning_repo FK**：确保 learner_agent_id 写入 UUID
3. **端到端测试**：完整跑通发帖→学习→OUTDATED→再学习全流程
4. **Web 页面验证**：通过浏览器验证所有页面正常渲染
5. **定时任务验证**：确认 APScheduler 任务正常触发
