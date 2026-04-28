"""FastAPI entrypoint for the cardiopulmonary sound separation system."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database.db import DATABASE_PATH, PROJECT_ROOT
from app.routers.results import router as results_router
from app.routers.separation import router as separation_router
from app.routers.upload import router as upload_router


app = FastAPI(
    title="Cardiopulmonary Sound Separation API",
    description="Upload mixed WAV files before running NeoSSNet separation.",
    version="0.1.0",
)

templates = Jinja2Templates(directory=PROJECT_ROOT / "app" / "templates")

app.mount(
    "/static",
    StaticFiles(directory=PROJECT_ROOT / "app" / "static"),
    name="static",
)

app.include_router(upload_router)
app.include_router(separation_router)
app.include_router(results_router)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "database_exists": DATABASE_PATH.is_file(),
    }
