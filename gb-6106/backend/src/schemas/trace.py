from pydantic import BaseModel


class TraceHit(BaseModel):
    record_key: str
    slot_id: int
    note: str
    offset: int | None
    byte_length: int | None
    run_id: int
    parameter: int
    actor: str
    finished_at: int | None
    case_title: str
    indexed: bool


class TraceIndexStatus(BaseModel):
    total: int
    indexed: int
    pending: int
    complete: bool


class TraceBackfillResult(BaseModel):
    processed: int
    total: int
    indexed: int
    pending: int
    complete: bool
