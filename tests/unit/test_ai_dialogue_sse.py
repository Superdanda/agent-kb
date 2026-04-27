import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.ai_dialogue import router as ai_router
from app.modules.ai_dialogue.router import _normalize_fields, _parse_sse_action_data
from app.modules.ai_dialogue.service import AIDialogueService, _coerce_json_object, _sse_event
from app.modules.task_board.models.task import Task


def test_sse_event_encodes_action_payload_once():
    event = _sse_event(
        "tool_result",
        {"action": "create_task", "fields": {"title": "诉论文"}},
    )

    data_line = next(line for line in event.splitlines() if line.startswith("data: "))
    parsed = json.loads(data_line.removeprefix("data: "))

    assert isinstance(parsed, dict)
    assert parsed["fields"]["title"] == "诉论文"


def test_parse_sse_action_data_accepts_legacy_double_encoded_payload():
    action_data = {"action": "create_task", "fields": {"title": "诉论文"}}
    legacy_payload = json.dumps(json.dumps(action_data, ensure_ascii=False), ensure_ascii=False)

    parsed = _parse_sse_action_data(legacy_payload)

    assert parsed == action_data


def test_normalize_fields_accepts_json_string_fields():
    fields = _normalize_fields('{"title": "诉论文", "priority": "MEDIUM"}')

    assert fields == {"title": "诉论文", "priority": "MEDIUM"}


def test_ai_dialogue_service_summary_accepts_string_encoded_fields():
    fields = '{"title": "赞美温州议论文", "priority": "MEDIUM"}'
    summary = AIDialogueService()._build_action_summary(
        {"action": "create_task", "fields": fields}
    )

    assert "赞美温州议论文" in summary


def test_coerce_json_object_rejects_non_object_json():
    assert _coerce_json_object('"plain string"') == {}


@pytest.mark.asyncio
async def test_ai_create_route_creates_wenzhou_essay_task_from_legacy_sse_payload(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    action_data = {
        "action": "create_task",
        "fields": {
            "title": "赞美温州议论文",
            "description": "完成一份关于赞美温州的议论文。",
            "priority": "MEDIUM",
            "difficulty": "MEDIUM",
            "points": 2,
            "estimated_hours": 2,
            "tags": ["文书"],
        },
    }
    legacy_payload = json.dumps(json.dumps(action_data, ensure_ascii=False), ensure_ascii=False)

    class FakeDialogueService:
        async def stream_dialogue(self, **kwargs):
            assert kwargs["user_message"] == "帮我创建一个关于 完成一份 赞美温州的 议论文 的任务"
            yield f"event: task_ready\ndata: {legacy_payload}\n\n"

    monkeypatch.setattr(ai_router, "AIDialogueService", FakeDialogueService)
    db = TestingSessionLocal()
    try:
        response = await ai_router.ai_create_task(
            request=None,
            message="帮我创建一个关于 完成一份 赞美温州的 议论文 的任务",
            files=[],
            _actor={
                "actor_type": "admin",
                "actor_id": "admin-uuid-1",
                "admin": SimpleNamespace(uuid="admin-uuid-1"),
                "agent_id": None,
            },
            db=db,
        )
        response_body = "".join([chunk async for chunk in response.body_iterator])

        assert response.status_code == 200
        assert "event: task_created" in response_body
        assert "'str' object has no attribute 'get'" not in response_body

        task = db.query(Task).one()
        assert task.title == "赞美温州议论文"
        assert task.description == "完成一份关于赞美温州的议论文。"
        assert task.metadata_json["ai_created"] is True
    finally:
        db.close()
