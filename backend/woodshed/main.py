from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from woodshed.db import get_session

app = FastAPI(title="Woodshed")


@app.get("/healthz")
def healthz(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(503, "database unreachable") from None
    return {"status": "ok"}
