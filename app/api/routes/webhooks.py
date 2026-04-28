from fastapi import APIRouter, Depends, HTTPException, WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.api.middleware.auth import get_current_agent
from app.api.middleware.admin_auth import ALGORITHM
from app.api.schemas.webhook import KbTaskStreamChunkRequest
from app.core.config import settings
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.modules.task_board.models.task import Task
from app.services.webhook_stream_service import webhook_stream_hub

# NOTE: The /webhooks/kb/notify endpoint previously called KbWebhookService.deliver
# which is for outbound KB→Agent notifications. This route is for inbound
# Agent→KB callbacks. Refactor separately when inbound callback handling is needed.

router = APIRouter(prefix="/webhooks/kb", tags=["kb-webhooks"])


@router.websocket("/tasks/{task_id}/stream")
async def task_webhook_stream(
    websocket: WebSocket,
    task_id: str,
    db: Session = Depends(get_db),
):
    if not _can_watch_task_stream(websocket, db, task_id):
        await websocket.close(code=1008)
        return

    connection = await webhook_stream_hub.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        webhook_stream_hub.disconnect(connection)


@router.post("/tasks/{task_id}/stream/chunks")
async def publish_task_stream_chunk(
    task_id: str,
    payload: KbTaskStreamChunkRequest,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.assigned_to_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Only the assigned Agent can publish task stream chunks")

    event = {
        "type": payload.type,
        "event": "agent.runtime",
        "delivery_id": payload.delivery_id,
        "sequence": payload.sequence,
        "source_timestamp": payload.timestamp.isoformat(),
    }
    if payload.content is not None:
        event["content"] = payload.content
    if payload.message is not None:
        event["message"] = payload.message
    if payload.status_code is not None:
        event["status_code"] = payload.status_code

    webhook_stream_hub.publish(task_id, event)
    return {"status": "accepted", "task_id": task_id}


def _can_watch_task_stream(websocket: WebSocket, db: Session, task_id: str) -> bool:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    if _has_active_admin_cookie(websocket, db):
        return True

    agent_id = websocket.cookies.get("agent_id") or websocket.headers.get("x-agent-id")
    return bool(agent_id and agent_id in {task.created_by_agent_id, task.assigned_to_agent_id})


def _has_active_admin_cookie(websocket: WebSocket, db: Session) -> bool:
    token = websocket.cookies.get("admin_token")
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get("admin_id")
        username = payload.get("username")
    except JWTError:
        return False
    if admin_id is None or username is None:
        return False
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    return bool(admin and admin.status == "ACTIVE")
