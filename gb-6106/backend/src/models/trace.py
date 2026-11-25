from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from .base import metadata


trace_entries = Table(
    "trace_entries", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", ForeignKey("runs.id"), nullable=False, index=True),
    Column("record_key", String(24), nullable=False, index=True),
    Column("slot_id", Integer, nullable=False),
    Column("note", String(1000), nullable=False),
    Column("offset", Integer, nullable=True),
    Column("byte_length", Integer, nullable=True),
    UniqueConstraint("run_id", "record_key", name="uq_trace_entry_run_key"),
)


trace_index_marks = Table(
    "trace_index_marks", metadata,
    Column("run_id", ForeignKey("runs.id"), primary_key=True),
    Column("indexed_at", BigInteger, nullable=False),
)
