"""Trace-address index: per-batch final slots for record keys.

The index is a projection of the replay report. A batch is indexed once, at
completion or by the backfill, and its marker row is written in the same
transaction as its entries. Re-indexing a batch replaces its entries, so a
retried or resumed backfill never duplicates a batch's slots.
"""
from time import time

from sqlalchemy import delete, func, insert, select

from src.constants.job_state import JobState
from src.domain.trace import entries_from_result
from src.models.cases import cases
from src.models.runs import runs
from src.models.trace import trace_entries, trace_index_marks
from src.services.audit import record

INDEXABLE = (JobState.DONE,)


def _replace(db, run_id, result):
    db.execute(delete(trace_entries).where(trace_entries.c.run_id == run_id))
    entries = [
        {"run_id": run_id, "record_key": item["key"], "slot_id": item["slot_id"],
         "note": item["note"], "offset": item["offset"], "byte_length": item["byte_length"]}
        for item in entries_from_result(result)
    ]
    if entries:
        db.execute(insert(trace_entries), entries)
    db.execute(delete(trace_index_marks).where(trace_index_marks.c.run_id == run_id))
    db.execute(insert(trace_index_marks).values(run_id=run_id, indexed_at=int(time())))


def index_run(db, run_id, status, result):
    """Index one finished batch inside the caller's transaction."""
    if status not in INDEXABLE:
        return False
    _replace(db, run_id, result)
    return True


def _pending(db):
    marked = select(trace_index_marks.c.run_id)
    return select(runs.c.id, runs.c.status, runs.c.result).where(
        runs.c.status.in_([state.value for state in INDEXABLE]),
        runs.c.id.not_in(marked),
    ).order_by(runs.c.id)


def backfill_chunk(limit, actor="system"):
    """Index up to ``limit`` unmarked terminal batches, committing each.

    Every batch commits on its own, so an interrupted run leaves completed
    batches marked and the next invocation continues with the rest.
    """
    from src.config.resources import engine

    with engine.connect() as db:
        batch_ids = [row.id for row in db.execute(_pending(db).limit(limit))]
    indexed = 0
    for run_id in batch_ids:
        with engine.begin() as db:
            row = db.execute(
                select(runs.c.status, runs.c.result).where(runs.c.id == run_id).with_for_update()
            ).first()
            if row is None or row.status not in INDEXABLE:
                continue
            # The run row lock serializes this check against a concurrent
            # worker finishing the same batch; the marker is re-read so a
            # batch indexed live is never indexed again.
            already = db.scalar(
                select(trace_index_marks.c.run_id).where(trace_index_marks.c.run_id == run_id)
            )
            if already is not None:
                continue
            _replace(db, run_id, row.result if row.status == JobState.DONE else None)
            record(db, "trace_backfill", actor, "run", run_id)
            indexed += 1
    return indexed


def backfill(chunk=100, max_batches=None, actor="system"):
    """Drain the pending batches chunk by chunk."""
    total = 0
    while max_batches is None or total < max_batches:
        limit = chunk if max_batches is None else min(chunk, max_batches - total)
        done = backfill_chunk(limit, actor)
        if done == 0:
            break
        total += done
    return total


def status(db):
    total = db.scalar(
        select(func.count()).select_from(runs).where(
            runs.c.status.in_([state.value for state in INDEXABLE])
        )
    ) or 0
    marked = db.scalar(select(func.count()).select_from(trace_index_marks)) or 0
    return {"total": total, "indexed": marked, "pending": max(0, total - marked),
            "complete": total <= marked}


def lookup(db, record_key=None):
    """Resolve each batch's final slot for a record key.

    Marked batches read from the index only. Batches committed before the
    index existed are derived from their stored report until the backfill
    reaches them, so lookups stay complete while the backfill runs.
    """
    entries = select(
        trace_entries.c.record_key, trace_entries.c.slot_id, trace_entries.c.note,
        trace_entries.c.offset, trace_entries.c.byte_length,
        runs.c.id.label("run_id"), runs.c.parameter, runs.c.actor, runs.c.finished_at,
        cases.c.title.label("case_title"),
    ).join(runs, runs.c.id == trace_entries.c.run_id).join(cases, cases.c.id == runs.c.case_id)
    if record_key is not None:
        entries = entries.where(trace_entries.c.record_key == record_key)
    entries = entries.where(runs.c.status == JobState.DONE)
    results = [{**dict(row), "indexed": True} for row in db.execute(entries).mappings()]

    marked = select(trace_index_marks.c.run_id)
    pending = select(
        runs.c.id.label("run_id"), runs.c.parameter, runs.c.actor, runs.c.finished_at,
        runs.c.result, cases.c.title.label("case_title"),
    ).join(cases, cases.c.id == runs.c.case_id).where(
        runs.c.status == JobState.DONE, runs.c.id.not_in(marked),
    )
    for row in db.execute(pending).mappings():
        for item in entries_from_result(row["result"]):
            if record_key is not None and item["key"] != record_key:
                continue
            results.append({
                "record_key": item["key"], "slot_id": item["slot_id"], "note": item["note"],
                "offset": item["offset"], "byte_length": item["byte_length"], "run_id": row["run_id"],
                "parameter": row["parameter"], "actor": row["actor"], "finished_at": row["finished_at"],
                "case_title": row["case_title"], "indexed": False,
            })

    results.sort(key=lambda item: (item["record_key"], item["run_id"]))
    return results
