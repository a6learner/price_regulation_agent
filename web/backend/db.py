"""SQLite trace 存储"""
import json
import aiosqlite
from .config import SQLITE_PATH

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS traces (
    id          TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'consumer',
    result      TEXT NOT NULL,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON traces(created_at DESC);
"""


async def init_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(SQLITE_PATH)
    await db.execute(CREATE_TABLE)
    await db.execute(CREATE_INDEX)
    await db.commit()
    return db


async def save_trace(db: aiosqlite.Connection, trace_id: str, query: str,
                     role: str, result: dict, duration_ms: int | None):
    await db.execute(
        "INSERT INTO traces (id, query, role, result, duration_ms) VALUES (?, ?, ?, ?, ?)",
        (trace_id, query, role, json.dumps(result, ensure_ascii=False), duration_ms),
    )
    await db.commit()


async def get_trace(db: aiosqlite.Connection, trace_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM traces WHERE id = ?", (trace_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0], "query": row[1], "role": row[2],
        "result": json.loads(row[3]), "duration_ms": row[4], "created_at": row[5],
    }


async def delete_trace(db: aiosqlite.Connection, trace_id: str) -> bool:
    cur = await db.execute("DELETE FROM traces WHERE id = ?", (trace_id,))
    await db.commit()
    return cur.rowcount > 0


async def delete_all_traces(db: aiosqlite.Connection) -> int:
    cur = await db.execute("DELETE FROM traces")
    await db.commit()
    return cur.rowcount


async def list_traces(db: aiosqlite.Connection, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    cursor = await db.execute("SELECT COUNT(*) FROM traces")
    total = (await cursor.fetchone())[0]

    cursor = await db.execute(
        "SELECT id, query, role, duration_ms, created_at FROM traces ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset),
    )
    rows = await cursor.fetchall()
    items = [
        {"id": r[0], "query": r[1], "role": r[2], "duration_ms": r[3], "created_at": r[4]}
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
