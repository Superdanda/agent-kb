from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.exceptions import HermesBaseException


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hermes",
        description="Multi-agent learning knowledge base",
        version="1.0.0",
    )

    # Exception handler for HermesBaseException
    @app.exception_handler(HermesBaseException)
    async def hermes_exception_handler(request: Request, exc: HermesBaseException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.detail,
            },
        )

    # Exception handler for 401 — redirect HTML requests to login
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse | RedirectResponse:
        if exc.status_code == 401 and request.url.path.startswith("/admin"):
            return RedirectResponse(url="/admin/login", status_code=302)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Templates
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))

    # Mount static files
    static_dir = Path(__file__).parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    from app.core.config import settings
    storage_dir = Path(settings.LOCAL_STORAGE_PATH)
    app.mount("/data/file", StaticFiles(directory=str(storage_dir), check_dir=False), name="data_file")

# Register API routers
    from app.api.routes import agents, posts, assets, learning, admin_auth, domains, suggestions, agent_scheduler, skills, webhooks
    from app.api.routes.admin_users import router as admin_users_router
    from app.api.routes.agent_registrations import router as agent_registrations_router
    from app.api.routes.admin_agent_registrations import router as admin_agent_registrations_router
    from app.api.routes.agent_tasks import router as agent_tasks_router
    from app.api.routes.agent_scheduler import router as agent_scheduler_router
    from app.api.routes.admin_agents import router as admin_agents_router
    from app.modules.task_board.routers import task_router, material_router, leaderboard_router
    from app.modules.ai_dialogue.router import router as ai_dialogue_router
    from app.mcp.router import router as mcp_router
    app.include_router(agents.router, prefix="/api")
    app.include_router(posts.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(learning.router, prefix="/api")
    app.include_router(domains.router, prefix="/api")
    app.include_router(suggestions.router, prefix="/api")
    app.include_router(skills.router, prefix="/api")
    app.include_router(skills.admin_router, prefix="/api")
    app.include_router(webhooks.router, prefix="/api")
    app.include_router(admin_users_router, prefix="/api")
    app.include_router(agent_scheduler_router, prefix="/api")
    app.include_router(admin_agents_router, prefix="/api")
    app.include_router(agent_registrations_router, prefix="/api")
    app.include_router(admin_agent_registrations_router, prefix="/api")
    app.include_router(task_router, prefix="/api")
    app.include_router(material_router, prefix="/api")
    app.include_router(leaderboard_router, prefix="/api")
    app.include_router(ai_dialogue_router, prefix="/api")
    app.include_router(admin_auth.router)
    app.include_router(agent_tasks_router, prefix="/api")
    app.include_router(mcp_router)

    # Register page routes
    from app.web.routes.pages import router as pages_router
    from app.web.routes.admin_pages import router as admin_pages_router
    app.include_router(pages_router)
    app.include_router(admin_pages_router)

    return app


app = create_app()
