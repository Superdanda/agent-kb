import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.schemas.webhook import KbTaskWebhookNotifyRequest
from app.core.database import Base
from app.core.security import encrypt_secret
from app.models import Agent, AgentCredential
from app.modules.task_board.services.task_service import TaskService
from app.services.kb_webhook_service import KbWebhookService, WebhookSigningIdentity


def test_signed_headers_match_hermes_agent_webhook_contract():
    """Verify headers match what Hermes Agent webhook adapter expects.

    Hermes Agent adapter validates X-Webhook-Signature (plain HMAC-SHA256 hex).
    It does NOT use x-signature, x-agent-id, x-timestamp, etc.
    """
    webhook_url = "http://localhost:8644/webhooks/kb-task"
    identity = WebhookSigningIdentity(
        agent_id="agent-1",
        access_key="agent-access",
        secret_key="agent-secret",
    )

    body = b'{"task_id":"task-1"}'
    headers = KbWebhookService()._signed_headers(body, webhook_url, identity)

    # Only Content-Type and X-Webhook-Signature are sent
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Webhook-Signature"] == hmac.new(
        b"agent-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    # Agent does NOT receive these old-style headers
    assert "x-agent-id" not in headers
    assert "x-access-key" not in headers
    assert "x-signature" not in headers


def test_task_create_does_not_change_metadata_when_agent_has_no_credentials():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
        db.add(agent)
        db.commit()

        task = TaskService(db).create_task(title="Work item", assigned_to_agent_id=agent.id)

        assert "last_webhook_notification" not in task.metadata_json
    finally:
        db.close()


def test_task_notification_uses_assigned_agent_callback_url():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        agent = Agent(
            id="agent-1",
            agent_code="agent-1",
            name="Agent 1",
            agent_type="hermes",
            callback_url="http://agent-host:8644/webhooks/kb-task",
        )
        db.add(agent)
        db.add(AgentCredential(
            id="credential-1",
            agent_id=agent.id,
            access_key="agent-access",
            secret_key_encrypted=encrypt_secret("agent-secret"),
            status="ACTIVE",
        ))
        db.commit()

        task = TaskService(db).create_task(title="Work item", assigned_to_agent_id=agent.id)

        assert KbWebhookService()._resolve_callback_url(db, agent.id) == "http://agent-host:8644/webhooks/kb-task"
        identity = KbWebhookService()._resolve_signing_identity(db, agent.id)
        assert identity.access_key == "agent-access"
        assert identity.secret_key == "agent-secret"
        assert task.assigned_to.agent_type == "hermes"
    finally:
        db.close()


def test_deliver_streams_agent_response_chunks_to_task_hub(monkeypatch):
    published = []

    class FakeResponse:
        status_code = 202

        async def aiter_text(self):
            yield "思考中..."
            yield "提交结果完成"

    class FakeStream:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, callback_url, content, headers):
            assert method == "POST"
            assert callback_url == "http://agent-host:8644/webhooks/kb-task"
            assert content
            assert headers["X-Webhook-Signature"]
            return FakeStream()

    monkeypatch.setattr("app.services.kb_webhook_service.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        "app.services.kb_webhook_service.webhook_stream_hub.publish",
        lambda task_id, event: published.append((task_id, event)),
    )

    payload = KbTaskWebhookNotifyRequest(
        event="task.assigned",
        task_id="task-1",
        agent_id="agent-1",
        message="有新任务分配给你，请处理",
        timestamp=datetime.now(timezone.utc),
    )
    result = KbWebhookService().deliver(
        payload,
        "http://agent-host:8644/webhooks/kb-task",
        WebhookSigningIdentity("agent-1", "agent-access", "agent-secret"),
    )

    assert result.delivered is True
    assert result.status_code == 202
    assert [event["type"] for _, event in published] == [
        "started",
        "chunk",
        "chunk",
        "completed",
    ]
    assert published[1] == ("task-1", {
        "type": "chunk",
        "event": "task.assigned",
        "content": "思考中...",
    })
