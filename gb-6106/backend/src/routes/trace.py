from fastapi import APIRouter, Depends, Query

from src.config.resources import engine
from src.controllers.access import identity, operator
from src.schemas.trace import TraceBackfillResult, TraceHit, TraceIndexStatus
from src.services import trace

router = APIRouter(prefix="/trace", tags=["Trace"])


@router.get("", response_model=list[TraceHit], dependencies=[Depends(identity)])
def trace_lookup(key: str | None = Query(default=None, max_length=24)):
    with engine.connect() as db:
        return trace.lookup(db, key)


@router.get("/index", response_model=TraceIndexStatus, dependencies=[Depends(identity)])
def trace_index_status():
    with engine.connect() as db:
        return trace.status(db)


@router.post("/index/backfill", response_model=TraceBackfillResult)
def trace_backfill(max_batches: int | None = Query(default=None, ge=1), user=Depends(operator)):
    indexed = trace.backfill(max_batches=max_batches, actor=user["username"])
    with engine.connect() as db:
        state = trace.status(db)
    return {"processed": indexed, **state}
