from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_agent
from app.api.schemas.learning import LearningSubmit
from app.api.schemas.post import PostCreate, PostUpdate
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import HermesBaseException, ValidationError
from app.models.agent import Agent, AgentStatus
from app.modules.task_board.models.task import Task, TaskStatus
from app.modules.task_board.schemas.task import TaskResponse
from app.modules.task_board.services.task_service import TaskService
from app.repositories.agent_repo import AgentRepository
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.domain_service import DomainService
from app.services.learning_service import LearningService
from app.services.post_service import PostService


router = APIRouter(tags=["mcp"])


def _jsonrpc_result(request_id: Any, result: Any) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any | None = None) -> JSONResponse:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": error})


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    mapper = getattr(value, "__mapper__", None)
    if mapper is not None:
        return {column.key: _jsonable(getattr(value, column.key)) for column in mapper.columns}
    return str(value)


def _content(payload: Any) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(_jsonable(payload), ensure_ascii=False),
            }
        ]
    }


def _tool_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _tool_definitions() -> list[dict[str, Any]]:
    string = {"type": "string"}
    integer = {"type": "integer"}
    boolean = {"type": "boolean"}
    string_array = {"type": "array", "items": string}
    return [
        {"name": "agent_kb.heartbeat", "description": "Update current Agent heartbeat and online status.", "inputSchema": _tool_schema({})},
        {"name": "agent_kb.agent_me", "description": "Get current Agent identity and status.", "inputSchema": _tool_schema({})},
        {"name": "agent_kb.task_list_available", "description": "List tasks assigned to this Agent or currently unclaimed.", "inputSchema": _tool_schema({"statuses": string_array, "limit": integer})},
        {"name": "agent_kb.task_get", "description": "Get a task by id.", "inputSchema": _tool_schema({"task_id": string}, ["task_id"])},
        {"name": "agent_kb.task_claim", "description": "Claim a task and receive a lease token.", "inputSchema": _tool_schema({"task_id": string}, ["task_id"])},
        {"name": "agent_kb.task_submit", "description": "Submit task result using lease and idempotency key.", "inputSchema": _tool_schema({"task_id": string, "result_summary": string, "actual_hours": integer, "lease_token": string, "idempotency_key": string}, ["task_id", "result_summary", "lease_token", "idempotency_key"])},
        {"name": "agent_kb.task_abandon", "description": "Abandon a claimed task using lease token.", "inputSchema": _tool_schema({"task_id": string, "reason": string, "lease_token": string}, ["task_id", "lease_token"])},
        {"name": "agent_kb.post_list", "description": "List knowledge posts.", "inputSchema": _tool_schema({"keyword": string, "tag": string, "author": string, "status": string, "domain_id": string, "page": integer, "size": integer})},
        {"name": "agent_kb.post_get", "description": "Get a knowledge post.", "inputSchema": _tool_schema({"post_id": string}, ["post_id"])},
        {"name": "agent_kb.post_create", "description": "Create a knowledge post.", "inputSchema": _tool_schema({"title": string, "summary": string, "content_md": string, "tags": string_array, "visibility": string, "status": string, "domain_id": string}, ["title", "domain_id"])},
        {"name": "agent_kb.post_update", "description": "Update post metadata or create a new version.", "inputSchema": _tool_schema({"post_id": string, "title": string, "summary": string, "content_md": string, "change_type": string, "change_note": string, "visibility": string, "status": string, "tags": string_array}, ["post_id"])},
        {"name": "agent_kb.learning_submit", "description": "Record learning for a post version.", "inputSchema": _tool_schema({"post_id": string, "version_id": string, "learn_note": string}, ["post_id", "version_id"])},
        {"name": "agent_kb.learning_list", "description": "List current Agent learning records.", "inputSchema": _tool_schema({"status": string, "only_outdated": boolean, "page": integer, "size": integer})},
        {"name": "agent_kb.domain_list", "description": "List knowledge domains.", "inputSchema": _tool_schema({"include_inactive": boolean})},
        {"name": "agent_kb.scheduler_list", "description": "List current Agent schedulers.", "inputSchema": _tool_schema({"enabled": boolean, "limit": integer, "offset": integer})},
        {"name": "agent_kb.scheduler_create", "description": "Create an Agent scheduler.", "inputSchema": _tool_schema({"task_name": string, "task_type": string, "cron_expression": string, "interval_seconds": integer, "run_at": string, "enabled": boolean}, ["task_name"])},
    ]


def _validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = settings.mcp_allowed_origins_list
    if origin in allowed:
        return
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return
    raise ValidationError("Origin is not allowed for MCP requests")


def _agent_name(db: Session, agent_id: str) -> str:
    agent = AgentRepository(db).get_by_id(agent_id)
    return agent.name if agent else agent_id


def _parse_statuses(values: list[str] | None) -> list[TaskStatus] | None:
    if not values:
        return None
    statuses = []
    for value in values:
        statuses.append(TaskStatus(value.upper()))
    return statuses


def _call_tool(name: str, arguments: dict[str, Any], agent_id: str, db: Session) -> dict:
    if name == "agent_kb.heartbeat":
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValidationError("Agent not found")
        agent.last_seen_at = datetime.now(timezone.utc)
        agent.status = AgentStatus.ACTIVE
        db.commit()
        pending_count = db.query(Task).filter(
            Task.assigned_to_agent_id == agent_id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.UNCLAIMED, TaskStatus.IN_PROGRESS]),
        ).count()
        return _content({"status": "ok", "agent_id": agent_id, "pending_tasks": pending_count, "server_time": datetime.now(timezone.utc)})

    if name == "agent_kb.agent_me":
        return _content(AgentRepository(db).get_by_id(agent_id))

    if name == "agent_kb.task_list_available":
        tasks = TaskService(db).list_available_tasks(
            agent_id=agent_id,
            statuses=_parse_statuses(arguments.get("statuses")),
            limit=int(arguments.get("limit", 10)),
        )
        return _content({"items": [TaskResponse.model_validate(task) for task in tasks], "total": len(tasks)})

    if name == "agent_kb.task_get":
        return _content(TaskResponse.model_validate(TaskService(db).get_task(arguments["task_id"])))

    if name == "agent_kb.task_claim":
        task = TaskService(db).claim_task(arguments["task_id"], agent_id)
        return _content({"task": TaskResponse.model_validate(task), "lease_token": task.lease_token, "lease_expires_at": task.lease_expires_at})

    if name == "agent_kb.task_submit":
        task = TaskService(db).submit_task_result(
            task_id=arguments["task_id"],
            agent_id=agent_id,
            result_summary=arguments["result_summary"],
            actual_hours=arguments.get("actual_hours"),
            lease_token=arguments.get("lease_token"),
            idempotency_key=arguments.get("idempotency_key"),
            require_lease=True,
        )
        return _content({"status": "submitted", "task": TaskResponse.model_validate(task)})

    if name == "agent_kb.task_abandon":
        task = TaskService(db).abandon_task(
            task_id=arguments["task_id"],
            agent_id=agent_id,
            reason=arguments.get("reason"),
            lease_token=arguments.get("lease_token"),
            require_lease=True,
        )
        return _content({"status": "abandoned", "task": TaskResponse.model_validate(task)})

    if name == "agent_kb.post_list":
        posts, total = PostService(db).get_posts(
            keyword=arguments.get("keyword"),
            tags=[arguments["tag"]] if arguments.get("tag") else None,
            author_agent_id=arguments.get("author"),
            status=arguments.get("status"),
            domain_id=arguments.get("domain_id"),
            page=int(arguments.get("page", 1)),
            size=int(arguments.get("size", 20)),
        )
        return _content({"items": posts, "total": total, "page": int(arguments.get("page", 1)), "size": int(arguments.get("size", 20))})

    if name == "agent_kb.post_get":
        return _content(PostService(db).get_post(arguments["post_id"], learner_agent_id=agent_id))

    if name == "agent_kb.post_create":
        data = PostCreate(
            title=arguments["title"],
            summary=arguments.get("summary"),
            content_md=arguments.get("content_md"),
            tags=arguments.get("tags") or [],
            visibility=arguments.get("visibility", "PUBLIC_INTERNAL"),
            status=arguments.get("status", "DRAFT"),
            domain_id=arguments["domain_id"],
        )
        return _content(PostService(db).create_post(agent_id, _agent_name(db, agent_id), data))

    if name == "agent_kb.post_update":
        data = PostUpdate(**{key: value for key, value in arguments.items() if key != "post_id"})
        return _content(PostService(db).update_post(arguments["post_id"], agent_id, data))

    if name == "agent_kb.learning_submit":
        record = LearningService(db).submit_learning(
            learner_agent_id=agent_id,
            post_id=arguments["post_id"],
            data=LearningSubmit(version_id=arguments["version_id"], learn_note=arguments.get("learn_note")),
        )
        return _content(record)

    if name == "agent_kb.learning_list":
        records, total = LearningService(db).get_my_records(
            agent_id=agent_id,
            status=arguments.get("status"),
            only_outdated=bool(arguments.get("only_outdated", False)),
            page=int(arguments.get("page", 1)),
            size=int(arguments.get("size", 20)),
        )
        return _content({"items": records, "total": total})

    if name == "agent_kb.domain_list":
        domains = DomainService(db).get_all_domains(include_inactive=bool(arguments.get("include_inactive", False)))
        return _content({"items": domains, "total": len(domains)})

    if name == "agent_kb.scheduler_list":
        return _content(AgentSchedulerService(db).list_by_agent(
            agent_id=agent_id,
            enabled=arguments.get("enabled"),
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        ))

    if name == "agent_kb.scheduler_create":
        run_at = None
        if arguments.get("run_at"):
            run_at = datetime.fromisoformat(arguments["run_at"])
        return _content(AgentSchedulerService(db).create_scheduler(
            agent_id=agent_id,
            task_name=arguments["task_name"],
            task_type=arguments.get("task_type", "periodic"),
            cron_expression=arguments.get("cron_expression"),
            interval_seconds=arguments.get("interval_seconds"),
            run_at=run_at,
            enabled=bool(arguments.get("enabled", True)),
        ))

    raise ValidationError(f"Unknown MCP tool: {name}")


@router.post("/mcp")
async def mcp_post(
    request: Request,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    _validate_origin(request)
    try:
        payload = await request.json()
    except Exception:
        return _jsonrpc_error(None, -32700, "Parse error")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    try:
        if method == "initialize":
            return _jsonrpc_result(request_id, {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "agent-kb", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            })
        if method == "ping":
            return _jsonrpc_result(request_id, {})
        if method == "tools/list":
            return _jsonrpc_result(request_id, {"tools": _tool_definitions()})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not name:
                raise ValidationError("Tool name is required")
            return _jsonrpc_result(request_id, _call_tool(name, arguments, agent_id, db))
        return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")
    except HermesBaseException as exc:
        return _jsonrpc_error(request_id, -32000, exc.detail, {"code": exc.code})
    except Exception as exc:
        return _jsonrpc_error(request_id, -32603, str(exc))


@router.get("/mcp")
async def mcp_get(
    request: Request,
    agent_id: str = Depends(get_current_agent),
):
    _validate_origin(request)
    if "text/event-stream" not in request.headers.get("accept", ""):
        return JSONResponse({"detail": "MCP GET requires Accept: text/event-stream"}, status_code=405, headers={"Allow": "POST, GET"})

    async def events():
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {"level": "info", "data": f"agent-kb MCP stream connected for {agent_id}"},
        }
        yield f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
