from __future__ import annotations

import json
import base64
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_agent, get_current_agent_for_heartbeat
from app.api.schemas.agent_registration import AgentRegistrationCreate
from app.api.schemas.learning import LearningSubmit
from app.api.schemas.post import PostCreate, PostUpdate
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, FileValidationError, HermesBaseException, PermissionDeniedError, ResourceNotFoundError, ValidationError
from app.core.file_storage import UploadBuffer, download_bytes_from_storage, get_default_bucket, validate_standard_upload
from app.core.security import decrypt_secret, sha256_bytes
from app.core.storage_client import StorageClientFactory
from app.models.agent import Agent, AgentStatus
from app.models.agent_registration import RegistrationStatus
from app.modules.task_board.models.task import Task, TaskStatus
from app.modules.task_board.models.task_material import MaterialType, TaskMaterial
from app.modules.task_board.models.task_submission_receipt import TaskSubmissionReceipt
from app.modules.task_board.schemas.task import TaskResponse
from app.modules.task_board.schemas.task_material import TaskMaterialResponse
from app.modules.task_board.services.material_service import MaterialService
from app.modules.task_board.services.task_service import TaskService
from app.repositories.agent_repo import AgentRepository
from app.services.agent_registration_service import AgentRegistrationService
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.domain_service import DomainService
from app.services.learning_service import LearningService
from app.services.post_service import PostService


router = APIRouter(tags=["mcp"])

PUBLIC_TOOLS = {"agent_kb.register", "agent_kb.fetch_credentials"}


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


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
    auth: str = "hmac",
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": _tool_schema(properties, required),
        "annotations": {"auth": auth},
    }


def _tool_definitions() -> list[dict[str, Any]]:
    string = {"type": "string"}
    integer = {"type": "integer"}
    boolean = {"type": "boolean"}
    string_array = {"type": "array", "items": string}
    host_info = {"type": "object", "additionalProperties": True}
    return [
        _tool("agent_kb.register", "Submit an Agent registration request before HMAC credentials exist. Supports host_info self-description. Agents should reuse ~/.agent-kb/identity.json agent_code to avoid duplicate registrations.", {"agent_code": string, "name": string, "description": string, "host_info": host_info, "device_name": string, "machine_location": string, "runtime_environment": string, "environment_tags": string_array, "capabilities": string, "self_introduction": string}, ["agent_code", "name"], auth="none"),
        _tool("agent_kb.fetch_credentials", "Fetch credentials for an approved registration code. The secret key is returned for in-memory use.", {"registration_code": string}, ["registration_code"], auth="none"),
        _tool("agent_kb.heartbeat", "Update current Agent heartbeat and online status.", {}),
        _tool("agent_kb.agent_me", "Get current Agent identity and status.", {}),
        _tool("agent_kb.task_list_available", "List unassigned tasks visible to all Agents plus this Agent's assigned active tasks.", {"statuses": string_array, "limit": integer}),
        _tool("agent_kb.task_get", "Get a task by id with materials, download URLs, status history, submission result, and review feedback.", {"task_id": string}, ["task_id"]),
        _tool("agent_kb.task_materials", "List task material metadata visible to the current Agent. Does not return file contents.", {"task_id": string, "include_results": boolean}, ["task_id"]),
        _tool("agent_kb.material_preview", "Preview one task material. Text files return a bounded text snippet; binary files return a short-lived preview URL.", {"material_id": string, "max_chars": integer, "url_expires": integer}, ["material_id"]),
        _tool("agent_kb.material_download", "Download one task material. By default returns a URL plus auth instructions; set inline=true only for small files that should be returned as base64 in JSON-RPC.", {"material_id": string, "url_expires": integer, "inline": boolean, "max_bytes": integer}, ["material_id"]),
        _tool("agent_kb.material_upload", "Upload a result material for the current Agent's claimed task using base64 content. Returns the material id for task_submit.result_material_ids.", {"task_id": string, "filename": string, "content_base64": string, "title": string, "content_type": string, "lease_token": string, "idempotency_key": string, "is_result": boolean}, ["task_id", "filename", "content_base64", "lease_token", "idempotency_key"]),
        _tool("agent_kb.task_claim", "Claim a task and receive a lease token.", {"task_id": string}, ["task_id"]),
        _tool("agent_kb.task_submit", "Submit task result using lease and idempotency key.", {"task_id": string, "result_summary": string, "actual_hours": integer, "lease_token": string, "idempotency_key": string, "result_material_ids": string_array}, ["task_id", "result_summary", "lease_token", "idempotency_key"]),
        _tool("agent_kb.task_abandon", "Abandon a claimed task using lease token.", {"task_id": string, "reason": string, "lease_token": string}, ["task_id", "lease_token"]),
        _tool("agent_kb.post_list", "List knowledge posts.", {"keyword": string, "tag": string, "author": string, "status": string, "domain_id": string, "page": integer, "size": integer}),
        _tool("agent_kb.post_get", "Get a knowledge post.", {"post_id": string}, ["post_id"]),
        _tool("agent_kb.post_create", "Create a knowledge post.", {"title": string, "summary": string, "content_md": string, "tags": string_array, "visibility": string, "status": string, "domain_id": string}, ["title", "domain_id"]),
        _tool("agent_kb.post_update", "Update post metadata or create a new version.", {"post_id": string, "title": string, "summary": string, "content_md": string, "change_type": string, "change_note": string, "visibility": string, "status": string, "tags": string_array}, ["post_id"]),
        _tool("agent_kb.learning_submit", "Record learning for a post version.", {"post_id": string, "version_id": string, "learn_note": string}, ["post_id", "version_id"]),
        _tool("agent_kb.learning_list", "List current Agent learning records.", {"status": string, "only_outdated": boolean, "page": integer, "size": integer}),
        _tool("agent_kb.domain_list", "List knowledge domains.", {"include_inactive": boolean}),
        _tool("agent_kb.scheduler_list", "List current Agent schedulers.", {"enabled": boolean, "limit": integer, "offset": integer}),
        _tool("agent_kb.scheduler_create", "Create an Agent scheduler.", {"task_name": string, "task_type": string, "cron_expression": string, "interval_seconds": integer, "run_at": string, "enabled": boolean}, ["task_name"]),
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


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _absolute_url(url: str | None, request: Request) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{_base_url(request)}{url}"
    return url


def _hmac_url_auth_instructions(url: str) -> dict[str, Any]:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    query = parsed.query or ""
    empty_body_sha256 = sha256_bytes(b"")
    return {
        "auth": "hmac",
        "required_headers": [
            "x-agent-id",
            "x-access-key",
            "x-timestamp",
            "x-nonce",
            "x-content-sha256",
            "x-signature",
        ],
        "canonical_request": {
            "method": "GET",
            "path": path,
            "query": query,
            "content_sha256": empty_body_sha256,
        },
        "string_to_sign": "GET\n{path}\n{query}\n{x-timestamp}\n{x-nonce}\n{x-content-sha256}",
        "signature": "hex_hmac_sha256(secret_key, string_to_sign)",
        "notes": [
            "Use a fresh x-timestamp and x-nonce for this GET request.",
            "For GET downloads the request body is empty, so x-content-sha256 must be the SHA256 of empty bytes.",
            "The path must be the URL path, for example /mcp/materials/{material_id}/download, not /mcp.",
            "The query line is empty when the URL has no query string.",
        ],
    }


def _material_extension(material: TaskMaterial) -> str:
    source = material.file_path or material.url or material.title or ""
    return os.path.splitext(source.lower())[1]


def _material_payload(material: TaskMaterial, request: Request) -> dict[str, Any]:
    ext = _material_extension(material)
    mime_type = mimetypes.guess_type(material.title or material.file_path or "")[0]
    return {
        "id": material.id,
        "task_id": material.task_id,
        "title": material.title,
        "material_type": material.material_type.value if material.material_type else None,
        "url": _absolute_url(material.url, request),
        "file_path": material.file_path,
        "extension": ext,
        "mime_type": mime_type,
        "order_index": material.order_index,
        "is_result": material.is_result,
        "created_at": material.created_at,
        "updated_at": material.updated_at,
        "can_preview": bool(material.content or material.url or material.file_path),
        "can_download": bool(material.file_path or material.url or material.content),
    }


def _material_detail_payload(material: TaskMaterial, request: Request) -> dict[str, Any]:
    payload = _material_payload(material, request)
    if material.file_path or material.url or material.content is not None:
        download_url, delivery = _material_access_url(material, request)
        payload["download_url"] = download_url
        payload["download_delivery"] = delivery
        payload["download_expires_in"] = 3600 if delivery == "presigned_url" else None
        if delivery == "authenticated_url":
            payload["download_auth_instructions"] = _hmac_url_auth_instructions(download_url)
    else:
        payload["download_url"] = None
        payload["download_delivery"] = None
        payload["download_expires_in"] = None
    return payload


def _status_log_payload(log: Any) -> dict[str, Any]:
    return {
        "id": log.id,
        "task_id": log.task_id,
        "agent_id": log.agent_id,
        "admin_uuid": log.admin_uuid,
        "from_status": log.from_status,
        "to_status": log.to_status,
        "change_reason": log.change_reason,
        "created_at": log.created_at,
    }


def _task_status_nodes(task: Task, status_logs: list[Any]) -> list[dict[str, Any]]:
    reached_statuses = {log.to_status for log in status_logs}
    if task.status:
        reached_statuses.add(task.status.value)
    created_status = task.status.value if not status_logs and task.status else TaskStatus.PENDING.value
    reached_statuses.add(created_status)

    latest_log_by_status = {log.to_status: log for log in status_logs}
    nodes = []
    current_status = task.status.value if task.status else None
    for status in TaskStatus:
        log = latest_log_by_status.get(status.value)
        nodes.append({
            "status": status.value,
            "reached": status.value in reached_statuses,
            "current": status.value == current_status,
            "reached_at": log.created_at if log else (task.created_at if status.value == created_status else None),
            "actor_agent_id": log.agent_id if log else None,
            "actor_admin_uuid": log.admin_uuid if log else None,
            "reason": log.change_reason if log else None,
        })
    return nodes


def _submission_payload(task: Task, result_materials: list[TaskMaterial], db: Session, request: Request) -> dict[str, Any] | None:
    metadata = task.metadata_json or {}
    receipts = (
        db.query(TaskSubmissionReceipt)
        .filter(TaskSubmissionReceipt.task_id == task.id)
        .order_by(TaskSubmissionReceipt.created_at.desc())
        .all()
    )
    if not metadata.get("result_summary") and not receipts and not result_materials:
        return None
    latest_receipt = receipts[0] if receipts else None
    return {
        "result_summary": metadata.get("result_summary") or (latest_receipt.result_summary if latest_receipt else None),
        "submitted_at": metadata.get("submitted_at") or (latest_receipt.created_at if latest_receipt else None),
        "result_material_ids": metadata.get("result_material_ids") or [material.id for material in result_materials],
        "result_materials": [_material_detail_payload(material, request) for material in result_materials],
        "receipts": [
            {
                "id": receipt.id,
                "agent_id": receipt.agent_id,
                "idempotency_key": receipt.idempotency_key,
                "result_summary": receipt.result_summary,
                "status": receipt.status,
                "created_at": receipt.created_at,
            }
            for receipt in receipts
        ],
    }


def _review_payload(task: Task) -> dict[str, Any]:
    metadata = task.metadata_json or {}
    return {
        "reject_reason": metadata.get("reject_reason"),
        "rejected_at": metadata.get("rejected_at"),
        "admin_reset_reason": metadata.get("admin_reset_reason"),
        "admin_reset_at": metadata.get("admin_reset_at"),
        "abandon_reason": metadata.get("abandon_reason"),
        "abandoned_at": metadata.get("abandoned_at"),
    }


def _task_detail_payload(task: Task, agent_id: str, db: Session, request: Request) -> dict[str, Any]:
    _ensure_task_material_access(task, agent_id)
    materials = (
        db.query(TaskMaterial)
        .filter(TaskMaterial.task_id == task.id)
        .order_by(TaskMaterial.order_index.asc(), TaskMaterial.created_at.asc())
        .all()
    )
    input_materials = [material for material in materials if not material.is_result]
    result_materials = [material for material in materials if material.is_result]
    status_logs = task.status_logs.all()
    metadata = task.metadata_json or {}
    return {
        "task": TaskResponse.model_validate(task),
        "materials": {
            "items": [_material_detail_payload(material, request) for material in materials],
            "input_items": [_material_detail_payload(material, request) for material in input_materials],
            "result_items": [_material_detail_payload(material, request) for material in result_materials],
            "total": len(materials),
            "input_total": len(input_materials),
            "result_total": len(result_materials),
        },
        "status_nodes": _task_status_nodes(task, status_logs),
        "status_history": [_status_log_payload(log) for log in status_logs],
        "submission": _submission_payload(task, result_materials, db, request),
        "review": _review_payload(task),
        "agent_instructions": {
            "claim_required": task.status in {TaskStatus.PENDING, TaskStatus.UNCLAIMED},
            "lease_required_for_submit": True,
            "active_lease_token": task.lease_token if task.assigned_to_agent_id == agent_id else None,
            "active_lease_expires_at": task.lease_expires_at if task.assigned_to_agent_id == agent_id else None,
            "material_download_tool": "agent_kb.material_download",
            "result_upload_tool": "agent_kb.material_upload",
            "submit_tool": "agent_kb.task_submit",
        },
        "metadata": {
            "result_summary": metadata.get("result_summary"),
            "submitted_at": metadata.get("submitted_at"),
            "result_material_ids": metadata.get("result_material_ids"),
            "reject_reason": metadata.get("reject_reason"),
            "rejected_at": metadata.get("rejected_at"),
        },
    }


def _ensure_task_material_access(task: Task, agent_id: str, *, require_assignee: bool = False) -> None:
    if task.assigned_to_agent_id == agent_id:
        return
    if not require_assignee:
        if task.created_by_agent_id == agent_id:
            return
        if not task.assigned_to_agent_id and task.status in {TaskStatus.PENDING, TaskStatus.UNCLAIMED}:
            return
    raise PermissionDeniedError("Agent is not allowed to access this task material")


def _get_material_for_agent(material_id: str, agent_id: str, db: Session, *, require_assignee: bool = False) -> TaskMaterial:
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        raise ResourceNotFoundError(f"Material {material_id} not found")
    _ensure_task_material_access(material.task, agent_id, require_assignee=require_assignee)
    return material


def _storage_url(object_key: str, request: Request, expires: int = 3600) -> str:
    storage = StorageClientFactory.get_client()
    url = storage.get_file_url(get_default_bucket(), object_key, expires=expires)
    return _absolute_url(url, request) or url


def _material_access_url(material: TaskMaterial, request: Request, expires: int = 3600) -> tuple[str, str]:
    if material.url and not material.file_path:
        return _absolute_url(material.url, request) or material.url, "url"
    if material.file_path and settings.STORAGE_TYPE == "MINIO":
        return _storage_url(material.file_path, request, expires=expires), "presigned_url"
    return f"{_base_url(request)}/mcp/materials/{material.id}/download", "authenticated_url"


def _download_material_bytes(material: TaskMaterial) -> bytes:
    if material.file_path:
        return download_bytes_from_storage(
            bucket=get_default_bucket(),
            object_key=material.file_path,
            failure_message="Failed to download task material",
        )
    if material.content is not None:
        return material.content.encode("utf-8")
    raise ValidationError("Material has no downloadable file content")


def _download_material_inline(material: TaskMaterial, request: Request, max_bytes: int) -> dict[str, Any]:
    if material.url and not material.file_path and material.content is None:
        return {
            "material": _material_payload(material, request),
            "download_url": _absolute_url(material.url, request),
            "expires_in": None,
            "delivery": "url",
        }

    data = _download_material_bytes(material)
    if len(data) > max_bytes:
        raise ValidationError(f"Material is too large for inline download: {len(data)} bytes > {max_bytes} bytes")
    filename = material.title or material.file_path or f"{material.id}.bin"
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return {
        "material": _material_payload(material, request),
        "filename": filename,
        "mime_type": mime_type,
        "size": len(data),
        "sha256": sha256_bytes(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
        "encoding": "base64",
        "delivery": "inline_base64",
    }


def _preview_material(material: TaskMaterial, request: Request, max_chars: int, url_expires: int) -> dict[str, Any]:
    ext = _material_extension(material)
    if material.content is not None:
        text = material.content[:max_chars]
        return {
            "kind": "text",
            "material": _material_payload(material, request),
            "text": text,
            "truncated": len(material.content) > max_chars,
        }

    if ext in {".txt", ".md", ".json", ".yaml", ".yml"} and material.file_path:
        data = _download_material_bytes(material)
        text = data.decode("utf-8", errors="replace")
        return {
            "kind": "text",
            "material": _material_payload(material, request),
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
        }

    if material.file_path:
        preview_url, delivery = _material_access_url(material, request, expires=url_expires)
        payload = {
            "kind": "url",
            "material": _material_payload(material, request),
            "preview_url": preview_url,
            "expires_in": url_expires,
            "delivery": delivery,
        }
        if delivery == "authenticated_url":
            payload["auth_instructions"] = _hmac_url_auth_instructions(preview_url)
        return payload

    if material.url:
        return {
            "kind": "url",
            "material": _material_payload(material, request),
            "preview_url": _absolute_url(material.url, request),
            "expires_in": None,
        }

    raise ValidationError("Material has no previewable content")


def _validated_upload_buffer(filename: str, contents: bytes, content_type: str) -> UploadBuffer:
    file_ext = os.path.splitext(filename.lower())[1]
    upload = UploadBuffer(
        contents=contents,
        original_filename=filename,
        file_ext=file_ext,
        content_type=content_type,
        sha256=sha256_bytes(contents),
    )
    validate_standard_upload(upload, error_cls=FileValidationError)
    return upload


def _fetch_credentials_payload(registration_code: str, db: Session, request: Request) -> dict:
    svc = AgentRegistrationService(db)
    registration = svc.get_by_code(registration_code)
    if not registration:
        raise ResourceNotFoundError(f"Registration request with code {registration_code} not found")
    if registration.status != RegistrationStatus.APPROVED:
        raise AuthenticationError("Registration is not yet approved")

    agent = AgentRepository(db).get_by_code(registration.agent_code)
    if not agent:
        raise AuthenticationError("Approved agent does not exist")

    credential = agent.credentials.filter_by(status="ACTIVE").first()
    if not credential:
        raise ResourceNotFoundError("No active credentials found")

    return {
        "registration_code": registration_code,
        "agent_id": agent.id,
        "agent_code": agent.agent_code,
        "name": agent.name,
        "access_key": credential.access_key,
        "secret_key": decrypt_secret(credential.secret_key_encrypted),
        "base_url": _base_url(request),
        "expires_at": None,
    }


def _call_tool(name: str, arguments: dict[str, Any], agent_id: str | None, db: Session, request: Request) -> dict:
    if name == "agent_kb.register":
        environment_tags = list(arguments.get("environment_tags") or [])
        host_info = arguments.get("host_info") or {}
        runtime_environment = arguments.get("runtime_environment")
        machine_location = arguments.get("machine_location")
        if isinstance(host_info, dict):
            runtime_environment = runtime_environment or host_info.get("runtime_environment")
            machine_location = machine_location or host_info.get("machine_location") or host_info.get("location")
        if runtime_environment and runtime_environment not in environment_tags:
            environment_tags.append(runtime_environment)

        self_introduction_parts = [
            value for value in (
                arguments.get("self_introduction") or arguments.get("description"),
                f"runtime_environment: {runtime_environment}" if runtime_environment else None,
                f"machine_location: {machine_location}" if machine_location else None,
                f"host_info: {json.dumps(host_info, ensure_ascii=False)}" if host_info else None,
            )
            if value
        ]
        data = AgentRegistrationCreate(
            agent_code=arguments["agent_code"],
            name=arguments["name"],
            device_name=arguments.get("device_name") or (host_info.get("hostname") if isinstance(host_info, dict) else None) or machine_location,
            environment_tags=environment_tags,
            capabilities=arguments.get("capabilities"),
            self_introduction="\n".join(self_introduction_parts) if self_introduction_parts else None,
        )
        registration, registration_code = AgentRegistrationService(db).create_registration_request(data)
        return _content({
            "registration_code": registration_code,
            "status": registration.status.value if hasattr(registration.status, "value") else registration.status,
            "message": "Waiting for admin approval",
        })

    if name == "agent_kb.fetch_credentials":
        return _content(_fetch_credentials_payload(arguments["registration_code"], db, request))

    if not agent_id:
        raise AuthenticationError("HMAC authentication is required for this MCP tool")

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
        task = TaskService(db).get_task(arguments["task_id"])
        return _content(_task_detail_payload(task, agent_id, db, request))

    if name == "agent_kb.task_materials":
        task = TaskService(db).get_task(arguments["task_id"])
        _ensure_task_material_access(task, agent_id)
        query = db.query(TaskMaterial).filter(TaskMaterial.task_id == task.id)
        if not bool(arguments.get("include_results", True)):
            query = query.filter(TaskMaterial.is_result.is_(False))
        materials = query.order_by(TaskMaterial.order_index.asc(), TaskMaterial.created_at.asc()).all()
        return _content({
            "items": [_material_payload(material, request) for material in materials],
            "total": len(materials),
        })

    if name == "agent_kb.material_preview":
        material = _get_material_for_agent(arguments["material_id"], agent_id, db)
        return _content(_preview_material(
            material=material,
            request=request,
            max_chars=min(int(arguments.get("max_chars", 8000)), 50000),
            url_expires=min(int(arguments.get("url_expires", 3600)), 24 * 3600),
        ))

    if name == "agent_kb.material_download":
        material = _get_material_for_agent(arguments["material_id"], agent_id, db)
        inline = bool(arguments.get("inline", False))
        if inline:
            return _content(_download_material_inline(
                material=material,
                request=request,
                max_bytes=min(int(arguments.get("max_bytes", 20 * 1024 * 1024)), 50 * 1024 * 1024),
            ))
        if material.file_path:
            expires = min(int(arguments.get("url_expires", 3600)), 24 * 3600)
            download_url, delivery = _material_access_url(material, request, expires=expires)
            return _content({
                "material": _material_payload(material, request),
                "download_url": download_url,
                "expires_in": expires,
                "delivery": delivery,
                "auth_instructions": _hmac_url_auth_instructions(download_url) if delivery == "authenticated_url" else None,
            })
        if material.url:
            return _content({
                "material": _material_payload(material, request),
                "download_url": _absolute_url(material.url, request),
                "expires_in": None,
                "delivery": "url",
            })
        if material.content is not None:
            return _content({
                "material": _material_payload(material, request),
                "content": material.content,
                "delivery": "inline_text",
            })
        raise ValidationError("Material has no downloadable content")

    if name == "agent_kb.material_upload":
        task_svc = TaskService(db)
        task = task_svc.get_task(arguments["task_id"])
        _ensure_task_material_access(task, agent_id, require_assignee=True)
        task_svc.ensure_agent_active_lease(task.id, agent_id, arguments["lease_token"])
        idempotency_key = arguments.get("idempotency_key")
        metadata = dict(task.metadata_json or {}) if isinstance(task.metadata_json, dict) else {}
        upload_receipts = dict(metadata.get("material_upload_receipts") or {})
        if idempotency_key and upload_receipts.get(idempotency_key):
            existing = db.query(TaskMaterial).filter(
                TaskMaterial.id == upload_receipts[idempotency_key],
                TaskMaterial.task_id == task.id,
            ).first()
            if existing:
                return _content({
                    "status": "uploaded",
                    "idempotent_replay": True,
                    "material": TaskMaterialResponse.model_validate(existing),
                    "material_id": existing.id,
                })
        filename = arguments["filename"]
        try:
            contents = base64.b64decode(arguments["content_base64"], validate=True)
        except Exception as exc:
            raise ValidationError("content_base64 is not valid base64") from exc
        if not contents:
            raise ValidationError("Uploaded material content is empty")
        content_type = arguments.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        _validated_upload_buffer(filename, contents, content_type)
        material = MaterialService(db).upload_bytes_material(
            task_id=task.id,
            title=arguments.get("title") or filename,
            filename=filename,
            contents=contents,
            content_type=content_type,
            material_type=MaterialType.FILE,
            is_result=bool(arguments.get("is_result", True)),
        )
        if idempotency_key:
            upload_receipts[idempotency_key] = material.id
            metadata["material_upload_receipts"] = upload_receipts
            task.metadata_json = metadata
            db.commit()
        return _content({
            "status": "uploaded",
            "material": TaskMaterialResponse.model_validate(material),
            "material_id": material.id,
        })

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
            result_material_ids=arguments.get("result_material_ids") or [],
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
                "capabilities": {
                    "tools": {"listChanged": False},
                    "agent_credential": {"register": True, "fetch": True, "in_memory_recommended": True},
                },
                "auth_methods": ["hmac"],
                "public_tools": sorted(PUBLIC_TOOLS),
                "protected_tools_auth": "hmac",
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
            agent_id = None
            if name not in PUBLIC_TOOLS:
                if name == "agent_kb.heartbeat":
                    agent_id = await get_current_agent_for_heartbeat(request, db)
                else:
                    agent_id = await get_current_agent(request, db)
            return _jsonrpc_result(request_id, _call_tool(name, arguments, agent_id, db, request))
        return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")
    except HermesBaseException as exc:
        return _jsonrpc_error(request_id, -32000, exc.detail, {"code": exc.code})
    except Exception as exc:
        return _jsonrpc_error(request_id, -32603, str(exc))


@router.get("/mcp/materials/{material_id}/download")
async def mcp_material_download(
    request: Request,
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    _validate_origin(request)
    material = _get_material_for_agent(material_id, agent_id, db)
    data = _download_material_bytes(material)
    filename = material.title or material.file_path or f"{material.id}.bin"
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return StreamingResponse(
        iter([data]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/mcp")
async def mcp_get(
    request: Request,
):
    _validate_origin(request)
    if "text/event-stream" not in request.headers.get("accept", ""):
        return JSONResponse({"detail": "MCP GET requires Accept: text/event-stream"}, status_code=405, headers={"Allow": "POST, GET"})

    async def events():
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {"level": "info", "data": "agent-kb MCP stream connected"},
        }
        yield f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
