import logging
from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import hashlib
import asyncio
import json

import httpx
from sqlalchemy.orm import Session

from app.api.schemas.webhook import KbTaskWebhookEvent, KbTaskWebhookNotifyRequest
from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.credential import AgentCredential
from app.services.webhook_stream_service import webhook_stream_hub

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebhookDeliveryResult:
    delivered: bool
    status_code: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class WebhookSigningIdentity:
    agent_id: str
    access_key: str
    secret_key: str


class KbWebhookService:
    """Deliver task notifications from KB to the assigned Agent's callback_url.

    Per-Agent callbacks are signed with that Agent's active credential from
    agent_credentials, using the same HMAC header contract as existing Agent APIs.
    """

    def notify_task(
        self,
        db: Session,
        task,  # Task model
        event: KbTaskWebhookEvent,
        message: str | None = None,
    ) -> WebhookDeliveryResult:
        """Send webhook to the task's assigned Agent.

        Args:
            db: database session
            task: Task model instance (must have assigned_to_agent_id)
            event: KbTaskWebhookEvent string
            message: optional override message
        """
        agent_id = getattr(task, "assigned_to_agent_id", None)
        callback_url = self._resolve_callback_url(db, agent_id)
        if not callback_url:
            return WebhookDeliveryResult(delivered=False, error="no_callback_url_configured")

        signing_identity = self._resolve_signing_identity(db, agent_id)
        if not signing_identity:
            return WebhookDeliveryResult(delivered=False, error="agent_has_no_credentials")

        payload = KbTaskWebhookNotifyRequest(
            event=event,
            task_id=task.id,
            agent_id=agent_id,
            message=message or self._default_message(event),
            timestamp=datetime.now(timezone.utc),
        )
        return self.deliver(payload, callback_url, signing_identity)

    def deliver(
        self,
        payload: KbTaskWebhookNotifyRequest,
        callback_url: str,
        signing_identity: WebhookSigningIdentity,
    ) -> WebhookDeliveryResult:
        """Deliver a webhook to callback_url, signed as the target Agent.

        Uses an async httpx client so that the streaming response from the Agent
        can be consumed without blocking the caller.  This prevents back-pressure
        on the Agent's response stream which would otherwise stall task execution.
        """
        body = payload.model_dump_json(exclude_none=True).encode("utf-8")
        headers = self._signed_headers(body, callback_url, signing_identity)

        try:
            return self._run_async(
                self._deliver_streaming(
                    payload=payload,
                    callback_url=callback_url,
                    body=body,
                    headers=headers,
                )
            )
        except httpx.HTTPError as exc:
            logger.warning("Failed to deliver KB task webhook: %s", exc)
            webhook_stream_hub.publish(payload.task_id, {
                "type": "error",
                "event": payload.event,
                "message": str(exc),
            })
            return WebhookDeliveryResult(delivered=False, error=str(exc))

    async def _deliver_streaming(
        self,
        payload: KbTaskWebhookNotifyRequest,
        callback_url: str,
        body: bytes,
        headers: dict[str, str],
    ) -> WebhookDeliveryResult:
        response_text_parts: list[str] = []
        webhook_stream_hub.publish(payload.task_id, {
            "type": "started",
            "event": payload.event,
            "message": payload.message,
        })
        async with httpx.AsyncClient(timeout=settings.HERMES_GATEWAY_WEBHOOK_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                callback_url,
                content=body,
                headers=headers,
            ) as response:
                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    response_text_parts.append(chunk)
                    if _is_agent_acceptance_ack(chunk):
                        continue
                    webhook_stream_hub.publish(payload.task_id, {
                        "type": "chunk",
                        "event": payload.event,
                        "content": chunk,
                    })
                response_text = "".join(response_text_parts)

        delivered = 200 <= response.status_code < 300
        if delivered and _is_agent_acceptance_ack(response_text):
            webhook_stream_hub.publish(payload.task_id, {
                "type": "accepted",
                "event": payload.event,
                "status_code": response.status_code,
                "message": "Agent 已接受任务通知，等待运行流回传。",
            })
            return WebhookDeliveryResult(
                delivered=True,
                status_code=response.status_code,
                error=None,
            )

        webhook_stream_hub.publish(payload.task_id, {
            "type": "completed" if delivered else "failed",
            "event": payload.event,
            "status_code": response.status_code,
            "message": "Agent webhook completed" if delivered else response_text[:500],
        })
        return WebhookDeliveryResult(
            delivered=delivered,
            status_code=response.status_code,
            error=None if delivered else response_text[:500],
        )

    def _run_async(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coroutine)).result()

    def _signed_headers(
        self,
        body: bytes,
        webhook_url: str,
        signing_identity: WebhookSigningIdentity,
    ) -> dict[str, str]:
        """Build headers for Hermes Agent webhook callback.

        Hermes Agent webhook adapter only validates X-Webhook-Signature
        (plain HMAC-SHA256 hex). Other headers are ignored.
        """
        webhook_signature = hmac.new(
            signing_identity.secret_key.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": webhook_signature,
        }
        return headers

    def _resolve_callback_url(self, db: Session, agent_id: str) -> str | None:
        if not agent_id:
            return None
        from app.models.agent import Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return None
        return agent.callback_url or None

    def _resolve_signing_identity(self, db: Session, agent_id: str | None) -> WebhookSigningIdentity | None:
        if not agent_id:
            return None
        credential = (
            db.query(AgentCredential)
            .filter(
                AgentCredential.agent_id == agent_id,
                AgentCredential.status == "ACTIVE",
            )
            .order_by(AgentCredential.created_at.desc())
            .first()
        )
        if not credential:
            return None
        return WebhookSigningIdentity(
            agent_id=agent_id,
            access_key=credential.access_key,
            secret_key=decrypt_secret(credential.secret_key_encrypted),
        )

    def _default_message(self, event: str) -> str:
        if event == "task.assigned":
            return "有新任务分配给你，请处理"
        if event == "task.updated":
            return "任务已更新，请检查"
        if event == "task.completed":
            return "任务已完成，请确认"
        return "有新任务到达，请处理"


def _is_agent_acceptance_ack(response_text: str) -> bool:
    try:
        payload = json.loads(response_text)
    except (TypeError, ValueError):
        return False
    return payload.get("status") == "accepted" and payload.get("route") == "kb-task"
