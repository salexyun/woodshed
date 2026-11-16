from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

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


class SPA(StaticFiles):
    """Serves the built frontend, answering unknown paths with index.html for client-side routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        if path.partition("/")[0] == "api":
            raise HTTPException(404)
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


# Only the container builds the SPA; in tests and dev Vite serves it instead.
DIST = Path(__file__).parents[2] / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", SPA(directory=DIST))
