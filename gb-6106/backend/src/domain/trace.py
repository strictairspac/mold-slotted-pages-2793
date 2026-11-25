"""Extract the surviving address-book entries from a stored replay report."""

TRACE_ACTION = "追溯地址"
MAX_NOTE = 1000


def entries_from_result(result):
    """Return the final live slot per record key.

    The replay appends one ``追溯地址`` row per surviving slot after all
    operations, so rejected writes and withdrawn records never appear here.
    """
    if not isinstance(result, dict):
        return []
    rows = result.get("rows")
    if not isinstance(rows, list):
        return []
    entries = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("操作") != TRACE_ACTION:
            continue
        key = row.get("履历")
        slot_id = row.get("槽号")
        if not isinstance(key, str) or not key or not isinstance(slot_id, int):
            continue
        note = row.get("结果")
        offset = row.get("现偏移")
        length = row.get("记录字节")
        entries[key] = {
            "key": key,
            "slot_id": slot_id,
            "note": (note if isinstance(note, str) else "")[:MAX_NOTE],
            "offset": offset if isinstance(offset, int) else None,
            "byte_length": length if isinstance(length, int) else None,
        }
    return list(entries.values())
