import json

from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.mcp.router import PUBLIC_TOOLS, _call_tool, _task_detail_payload, _tool_definitions
from app.models import Agent
from app.modules.task_board.models.task import TaskStatus
from app.modules.task_board.models.task_material import MaterialType
from app.modules.task_board.services.material_service import MaterialService
from app.modules.task_board.services.task_service import TaskService


def test_mcp_tool_definitions_mark_public_and_protected_auth():
    tools = {tool["name"]: tool for tool in _tool_definitions()}

    assert PUBLIC_TOOLS == {"agent_kb.register", "agent_kb.fetch_credentials"}
    assert tools["agent_kb.register"]["annotations"]["auth"] == "none"
    assert "host_info" in tools["agent_kb.register"]["inputSchema"]["properties"]
    assert tools["agent_kb.fetch_credentials"]["annotations"]["auth"] == "none"
    assert tools["agent_kb.heartbeat"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.task_submit"]["annotations"]["auth"] == "hmac"
    assert "result_material_ids" in tools["agent_kb.task_submit"]["inputSchema"]["properties"]

    assert tools["agent_kb.task_materials"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_preview"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_download"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_upload"]["annotations"]["auth"] == "hmac"
    assert "content_base64" in tools["agent_kb.material_upload"]["inputSchema"]["properties"]
    assert "inline" in tools["agent_kb.material_download"]["inputSchema"]["properties"]
    assert "max_bytes" in tools["agent_kb.material_download"]["inputSchema"]["properties"]


def test_task_get_detail_payload_includes_work_context():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
        db.add(agent)
        db.commit()

        task_service = TaskService(db)
        material_service = MaterialService(db)
        task = task_service.create_task(title="Contract review", description="Review the uploaded contract")
        input_material = material_service.create_material(
            task_id=task.id,
            material_type=MaterialType.FILE,
            title="contract.docx",
            file_path="task_materials/contract.docx",
        )
        claimed = task_service.claim_task(task.id, agent.id)
        result_material = material_service.create_material(
            task_id=claimed.id,
            material_type=MaterialType.FILE,
            title="reviewed-contract.docx",
            file_path="task_materials/reviewed-contract.docx",
        )
        submitted = task_service.submit_task_result(
            task_id=claimed.id,
            agent_id=agent.id,
            result_summary="Reviewed contract and added comments.",
            lease_token=claimed.lease_token,
            idempotency_key="submit-1",
            result_material_ids=[result_material.id],
            require_lease=True,
        )
        rejected = task_service.reject_task(
            task_id=submitted.id,
            reviewer_admin_uuid="admin-1",
            reason="Missing risk summary.",
        )
        request = Request({
            "type": "http",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/mcp",
            "headers": [],
        })

        payload = _task_detail_payload(rejected, agent.id, db, request)

        assert payload["task"].status == TaskStatus.IN_PROGRESS
        assert payload["review"]["reject_reason"] == "Missing risk summary."
        assert payload["submission"]["result_summary"] == "Reviewed contract and added comments."
        assert payload["submission"]["result_material_ids"] == [result_material.id]
        assert {item["id"] for item in payload["materials"]["input_items"]} == {input_material.id}
        assert {item["id"] for item in payload["materials"]["result_items"]} == {result_material.id}
        assert all(item["download_url"].startswith("http://testserver/mcp/materials/") for item in payload["materials"]["items"])
        assert any(node["status"] == "SUBMITTED" and node["reached"] for node in payload["status_nodes"])
        assert any(log["to_status"] == "IN_PROGRESS" and log["change_reason"] == "Missing risk summary." for log in payload["status_history"])
    finally:
        db.close()


def test_material_download_returns_inline_base64_when_requested():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
        db.add(agent)
        db.commit()

        task = TaskService(db).create_task(title="Contract review")
        claimed = TaskService(db).claim_task(task.id, agent.id)
        material = MaterialService(db).create_material(
            task_id=claimed.id,
            material_type=MaterialType.FILE,
            title="contract.txt",
            content="contract text",
        )
        request = Request({
            "type": "http",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/mcp",
            "headers": [],
        })

        payload = _call_tool(
            "agent_kb.material_download",
            {"material_id": material.id, "inline": True},
            agent.id,
            db,
            request,
        )
        data = payload["content"][0]["text"]

        assert '"delivery": "inline_base64"' in data
        assert '"content_base64": "Y29udHJhY3QgdGV4dA=="' in data
        assert '"filename": "contract.txt"' in data
    finally:
        db.close()


def test_material_download_returns_authenticated_url_by_default():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
        db.add(agent)
        db.commit()

        task = TaskService(db).create_task(title="Contract review")
        claimed = TaskService(db).claim_task(task.id, agent.id)
        material = MaterialService(db).create_material(
            task_id=claimed.id,
            material_type=MaterialType.FILE,
            title="contract.docx",
            file_path="task_materials/contract.docx",
        )
        request = Request({
            "type": "http",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/mcp",
            "headers": [],
        })

        payload = _call_tool(
            "agent_kb.material_download",
            {"material_id": material.id},
            agent.id,
            db,
            request,
        )
        data = json.loads(payload["content"][0]["text"])

        assert data["delivery"] == "authenticated_url"
        assert data["download_url"].startswith("http://testserver/mcp/materials/")
        assert data["auth_instructions"]["auth"] == "hmac"
        assert data["auth_instructions"]["canonical_request"]["method"] == "GET"
        assert data["auth_instructions"]["canonical_request"]["path"] == f"/mcp/materials/{material.id}/download"
        assert data["auth_instructions"]["canonical_request"]["query"] == ""
        assert data["auth_instructions"]["canonical_request"]["content_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    finally:
        db.close()
