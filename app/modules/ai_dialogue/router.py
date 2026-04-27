"""
AI Task Router - SSE streaming endpoints for AI-powered task creation/editing.

POST /api/tasks/ai/create   - AI task creation (SSE stream)
POST /api/tasks/{id}/ai/edit - AI task editing (SSE stream)
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_admin_or_agent
from app.modules.ai_dialogue.service import AIDialogueService
from app.modules.task_board.services.task_service import TaskService
from app.modules.task_board.models.task import TaskPriority, TaskDifficulty, TaskStatus
from app.modules.task_board.models.task_material import TaskMaterial, MaterialType
from app.modules.task_board.services.material_service import MaterialService
from app.models.agent import Agent
from app.core.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/tasks", tags=["ai_tasks"])


def _get_available_agents(db: Session) -> List[dict]:
    """Get list of active agents for AI context."""
    agents = db.query(Agent).filter(Agent.status == "ACTIVE").order_by(Agent.name).all()
    return [
        {"id": a.id, "name": a.name, "agent_code": a.agent_code}
        for a in agents
    ]


def _format_field_for_display(field: str, value) -> str:
    """Format a field value for SSE display."""
    if value is None or value == "":
        return "未设置"
    if isinstance(value, list):
        return "、".join(str(v) for v in value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)


FIELD_LABELS_CN = {
    "title": "标题",
    "description": "描述",
    "priority": "优先级",
    "difficulty": "难度",
    "points": "积分",
    "estimated_hours": "预计工时",
    "due_date": "截止日期",
    "tags": "标签",
    "assigned_to_agent_id": "负责人",
}

PRIORITY_CN = {"LOW": "低", "MEDIUM": "中", "HIGH": "高", "URGENT": "紧急"}
DIFFICULTY_CN = {"EASY": "简单", "MEDIUM": "中等", "HARD": "困难", "EXPERT": "专家"}


def _build_create_result_text(fields: dict, task_id: str, material_count: int) -> str:
    """Build the final result display text for task creation."""
    title = fields.get("title", "未命名任务")
    lines = [
        f"已创建任务：{title}。",
        "",
        "本次 AI 自动添加的内容如下：",
        "",
    ]
    for field, label in FIELD_LABELS_CN.items():
        if field in fields and fields[field] is not None and fields[field] != "" and fields[field] != []:
            val = fields[field]
            if field == "priority":
                val = PRIORITY_CN.get(val, val)
            elif field == "difficulty":
                val = DIFFICULTY_CN.get(val, val)
            elif field == "tags":
                val = "、".join(val) if isinstance(val, list) else str(val)
            lines.append(f"{label}：{val}")

    if material_count > 0:
        lines.append(f"任务材料：已关联 {material_count} 个文件")
    else:
        lines.append("任务材料：无")
    lines.append(f"截止日期：{_format_field_for_display('due_date', fields.get('due_date'))}")

    lines.append("")
    lines.append("你可以在任务列表中查看该任务，也可以继续告诉我需要如何修改。")
    return "\n".join(lines)


def _build_edit_result_text(fields: dict, changes: list, task_title: str) -> str:
    """Build the final result display text for task editing."""
    lines = [
        f"已修改任务：{task_title}。",
        "",
        "本次修改内容如下：",
        "",
    ]
    for change in changes:
        lines.append(f"{change['label']}：{change['old_value']} → {change['new_value']}")

    lines.append("")
    lines.append("任务已保存，你可以返回详情页查看最新内容。")
    return "\n".join(lines)


@router.post("/ai/create")
async def ai_create_task(
    request: Request,
    message: str = Form(...),
    files: List[UploadFile] = File(default_factory=list),
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    """
    AI-powered task creation with SSE streaming.

    Accepts a natural language message and optional file uploads.
    Returns an SSE stream with thinking states, text chunks, and final task result.
    """
    # Extract admin/agent identity
    admin = _actor.get("admin")
    admin_uuid = admin.uuid if admin else None
    agent_id = _actor.get("agent_id")

    if not admin_uuid and not agent_id:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Authentication required")

    # Process uploaded files - save them temporarily and collect context
    file_context = []
    saved_files = []
    if files:
        for f in files:
            if f.filename:
                file_context.append({
                    "filename": f.filename,
                    "content_type": f.content_type or "unknown",
                })
                saved_files.append(f)

    # Get available agents for AI context
    available_agents = _get_available_agents(db)

    async def event_generator():
        dialogue = AIDialogueService()

        # Stream AI dialogue
        async for sse_msg in dialogue.stream_dialogue(
            scenario="task_create",
            user_message=message,
            file_context=file_context if file_context else None,
            available_agents=available_agents,
        ):
            # Parse SSE message to check for tool_result
            if "event: tool_result" in sse_msg or "event: task_ready" in sse_msg:
                # Extract the data
                for line in sse_msg.strip().split("\n"):
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            action_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # Execute the business action
                        try:
                            fields = action_data.get("fields", {})

                            # Resolve agent
                            assigned_to = fields.get("assigned_to_agent_id")
                            if assigned_to:
                                # Verify agent exists
                                agent = db.query(Agent).filter(Agent.id == assigned_to).first()
                                if not agent:
                                    assigned_to = None

                            # Parse priority
                            priority_str = fields.get("priority", "MEDIUM")
                            try:
                                priority = TaskPriority(priority_str)
                            except ValueError:
                                priority = TaskPriority.MEDIUM

                            # Parse difficulty
                            difficulty_str = fields.get("difficulty")
                            difficulty = None
                            if difficulty_str:
                                try:
                                    difficulty = TaskDifficulty(difficulty_str)
                                except ValueError:
                                    pass

                            # Parse due date
                            due_date = None
                            due_date_str = fields.get("due_date")
                            if due_date_str:
                                try:
                                    due_date = datetime.fromisoformat(due_date_str)
                                except (ValueError, TypeError):
                                    pass

                            # Parse tags
                            tags = fields.get("tags", [])
                            if isinstance(tags, str):
                                tags = [t.strip() for t in tags.split(",") if t.strip()]

                            # Create task using service
                            svc = TaskService(db)
                            task = svc.create_task(
                                title=fields.get("title", "AI 创建的任务"),
                                created_by_admin_uuid=admin_uuid,
                                created_by_agent_id=agent_id,
                                description=fields.get("description"),
                                assigned_to_agent_id=assigned_to,
                                priority=priority,
                                difficulty=difficulty,
                                points=fields.get("points", 0),
                                estimated_hours=fields.get("estimated_hours"),
                                due_date=due_date,
                                tags=tags if tags else None,
                                metadata={"ai_created": True, "ai_source": "ai_dialogue"},
                            )

                            # Process saved files - associate with task
                            material_count = 0
                            if saved_files:
                                material_svc = MaterialService(db)
                                for f in saved_files:
                                    try:
                                        await f.seek(0)
                                        material_svc.upload_file_material(
                                            task_id=task.id,
                                            title=f.filename or "任务材料",
                                            material_type=MaterialType.FILE,
                                            file=f,
                                            is_result=False,
                                        )
                                        material_count += 1
                                    except Exception:
                                        pass

                            # Build result text
                            result_text = _build_create_result_text(fields, task.id, material_count)

                            # Send task_created event
                            result = {
                                "task_id": task.id,
                                "title": task.title,
                                "fields": fields,
                                "material_count": material_count,
                            }
                            yield f"event: task_created\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
                            yield f"event: text\ndata: {json.dumps(result_text, ensure_ascii=False)}\n\n"
                            yield f"event: done\ndata: {json.dumps('stream_complete', ensure_ascii=False)}\n\n"
                            return  # Stream complete

                        except Exception as e:
                            yield f"event: error\ndata: {json.dumps(f'任务创建失败：{str(e)}', ensure_ascii=False)}\n\n"
                            return

            yield sse_msg

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{task_id}/ai/edit")
async def ai_edit_task(
    request: Request,
    task_id: str,
    message: str = Form(...),
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    """
    AI-powered task editing with SSE streaming.

    Accepts a natural language message describing desired changes.
    Returns an SSE stream with thinking states, text chunks, and final edit result.
    """
    admin = _actor.get("admin")
    admin_uuid = admin.uuid if admin else None
    agent_id = _actor.get("agent_id")

    if not admin_uuid and not agent_id:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Authentication required")

    # Load current task
    from app.modules.task_board.models.task import Task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ResourceNotFoundError(f"Task {task_id} not found")

    # Build current task context
    current_task = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value if task.priority else None,
        "difficulty": task.difficulty.value if task.difficulty else None,
        "points": task.points,
        "estimated_hours": task.estimated_hours,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "tags": task.tags_json or [],
        "assigned_to_agent_id": task.assigned_to_agent_id,
    }

    available_agents = _get_available_agents(db)

    async def event_generator():
        dialogue = AIDialogueService()

        async for sse_msg in dialogue.stream_dialogue(
            scenario="task_edit",
            user_message=message,
            current_task=current_task,
            available_agents=available_agents,
        ):
            if "event: tool_result" in sse_msg or "event: task_updated" in sse_msg:
                for line in sse_msg.strip().split("\n"):
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            action_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        try:
                            fields = action_data.get("fields", {})
                            changes = action_data.get("changes", [])

                            # Apply only non-None fields
                            if fields.get("title"):
                                task.title = fields["title"]
                            if fields.get("description") is not None:
                                task.description = fields["description"]
                            if fields.get("priority"):
                                try:
                                    task.priority = TaskPriority(fields["priority"])
                                except ValueError:
                                    pass
                            if fields.get("difficulty"):
                                try:
                                    task.difficulty = TaskDifficulty(fields["difficulty"])
                                except ValueError:
                                    pass
                            if fields.get("points") is not None:
                                task.points = fields["points"]
                            if fields.get("estimated_hours") is not None:
                                task.estimated_hours = fields["estimated_hours"]
                            if fields.get("due_date"):
                                try:
                                    task.due_date = datetime.fromisoformat(fields["due_date"])
                                except (ValueError, TypeError):
                                    pass
                            if fields.get("tags") is not None:
                                tags = fields["tags"]
                                if isinstance(tags, str):
                                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                                task.tags_json = tags
                            if fields.get("assigned_to_agent_id") is not None:
                                task.assigned_to_agent_id = fields["assigned_to_agent_id"]

                            task.updated_at = datetime.now(timezone.utc)
                            db.commit()
                            db.refresh(task)

                            result_text = _build_edit_result_text(
                                fields, changes, task.title
                            )

                            result = {
                                "task_id": task.id,
                                "title": task.title,
                                "changes": changes,
                            }
                            yield f"event: task_updated\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
                            yield f"event: text\ndata: {json.dumps(result_text, ensure_ascii=False)}\n\n"
                            yield f"event: done\ndata: {json.dumps('stream_complete', ensure_ascii=False)}\n\n"
                            return

                        except Exception as e:
                            yield f"event: error\ndata: {json.dumps(f'任务修改失败：{str(e)}', ensure_ascii=False)}\n\n"
                            return

            yield sse_msg

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
