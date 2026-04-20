from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from app import app
from app.core.config import settings
from app.core.database import init_db, dispose_engine
from app.core.storage_client import get_storage_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()

    # Ensure local storage directory exists
    storage_client = get_storage_client()
    if hasattr(storage_client, "base_path"):
        storage_path = Path(storage_client.base_path)
        storage_path.mkdir(parents=True, exist_ok=True)

    # Start scheduler
    from app.tasks.scheduler import init_scheduler, start_scheduler
    sched = init_scheduler()
    start_scheduler()

    yield

    # Stop scheduler
    from app.tasks.scheduler import stop_scheduler
    stop_scheduler()
    dispose_engine()

app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "dev",
    )
