from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from woodshed.api import router
from woodshed.db import get_session

app = FastAPI(title="Woodshed")
app.include_router(router)


@app.get("/healthz")
def healthz(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(503, "database unreachable") from None
    return {"status": "ok"}


def serve_spa(app: FastAPI, dist: Path) -> None:
    """Serves the built frontend, answering unknown GETs with index.html for client-side routes."""
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.exception_handler(404)
    async def index(request: Request, exc: StarletteHTTPException) -> Response:
        section = request.url.path.split("/")[1]
        if request.method == "GET" and section not in {"api", "assets"}:
            return FileResponse(dist / "index.html")
        return await http_exception_handler(request, exc)


# Only the Docker image builds the SPA; without it the app serves the API alone.
DIST = Path(__file__).parents[2] / "frontend" / "dist"
if DIST.is_dir():
    serve_spa(app, DIST)
