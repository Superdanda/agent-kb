import pytest
from starlette.requests import Request

from app.models.admin_user import AdminUser
from app.web.routes import pages


def make_request(path: str = "/tasks/new") -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("testclient", 50000),
    })


@pytest.mark.asyncio
async def test_tasks_new_defaults_to_ai_template(monkeypatch):
    async def fake_get_current_admin(request, db):
        return AdminUser(id=1, username="admin", password_hash="hash")

    class FakeQuery:
        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class FakeDb:
        def query(self, *args, **kwargs):
            return FakeQuery()

    monkeypatch.setattr("app.api.middleware.admin_auth.get_current_admin", fake_get_current_admin)

    response = await pages.new_task_page(make_request(), mode=None, db=FakeDb())

    assert response.template.name == "tasks/ai_create.html"


@pytest.mark.asyncio
async def test_tasks_new_manual_mode_uses_manual_template(monkeypatch):
    async def fake_get_current_admin(request, db):
        return AdminUser(id=1, username="admin", password_hash="hash")

    class FakeQuery:
        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class FakeDb:
        def query(self, *args, **kwargs):
            return FakeQuery()

    monkeypatch.setattr("app.api.middleware.admin_auth.get_current_admin", fake_get_current_admin)

    response = await pages.new_task_page(make_request(), mode="manual", db=FakeDb())

    assert response.template.name == "tasks/new.html"
