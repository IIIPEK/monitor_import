from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.routers.pages import router as pages_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Monitor Import Web",
        version="0.1.0",
    )

    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(pages_router)

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
