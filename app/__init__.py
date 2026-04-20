from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

    # Templates
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))

    # Mount static files
    static_dir = Path(__file__).parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register API routers
    from app.api.routes import agents, posts, assets, learning, admin_auth
    app.include_router(agents.router, prefix="/api")
    app.include_router(posts.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(learning.router, prefix="/api")
    app.include_router(admin_auth.router)

    # Register page routes
    from app.web.routes.pages import router as pages_router
    from app.web.routes.admin_pages import router as admin_pages_router
    app.include_router(pages_router)
    app.include_router(admin_pages_router)

    return app


app = create_app()
