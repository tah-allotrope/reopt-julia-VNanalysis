"""Internal Vietnam DPPA web app (PHASE-01): FastAPI wrapper over
``reopt_pysam_vn.analysis``. Launch with:

    uvicorn reopt_pysam_vn.webapp:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["app", "create_app"]


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from reopt_pysam_vn.webapp.jobs import JobManager
    from reopt_pysam_vn.webapp.logging_config import configure_logging
    from reopt_pysam_vn.webapp.routes.api import router as api_router
    from reopt_pysam_vn.webapp.routes.pages import router as pages_router
    from reopt_pysam_vn.webapp.storage import RunStorage, default_runs_dir

    configure_logging()

    storage = RunStorage(default_runs_dir())
    jobs = JobManager(storage)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        jobs.start()
        try:
            yield
        finally:
            jobs.stop()

    app = FastAPI(title="Vietnam DPPA Deal Screener", lifespan=lifespan)
    app.state.storage = storage
    app.state.jobs = jobs

    app.include_router(api_router, prefix="/api")
    app.include_router(pages_router)

    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app


def __getattr__(name: str) -> Any:
    if name == "app":
        return create_app()
    raise AttributeError(name)
