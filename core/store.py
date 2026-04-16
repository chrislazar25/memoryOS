"""
store.py — SQLite storage layer for MemoryOS.

Schema
------
memories
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  repo          TEXT NOT NULL
  commit_hash   TEXT NOT NULL
  commit_message TEXT NOT NULL
  reason        TEXT NOT NULL
  decision_type TEXT NOT NULL          -- design_choice | design_change | performance | security_incident_response
  tradeoffs     TEXT NOT NULL          -- JSON object: {chosen, rejected, known_downsides}
  tags          TEXT NOT NULL          -- JSON array of strings
  created_at    TEXT NOT NULL          -- ISO-8601 UTC
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_DB = Path(__file__).parent / "memories.db"


def _connect(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = _DEFAULT_DB) -> None:
    """Create the memories table if it does not exist."""
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                repo           TEXT NOT NULL,
                commit_hash    TEXT NOT NULL,
                commit_message TEXT NOT NULL,
                reason         TEXT NOT NULL,
                decision_type  TEXT NOT NULL,
                tradeoffs      TEXT NOT NULL,
                tags           TEXT NOT NULL,
                created_at     TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_repo ON memories(repo)"
        )


def insert_memory(
    *,
    repo: str,
    commit_hash: str,
    commit_message: str,
    reason: str,
    decision_type: str,
    tradeoffs: dict,
    tags: list[str],
    db_path: Path = _DEFAULT_DB,
) -> int:
    """Insert one memory row and return its new id."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO memories
                (repo, commit_hash, commit_message, reason, decision_type,
                 tradeoffs, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo,
                commit_hash,
                commit_message,
                reason,
                decision_type,
                json.dumps(tradeoffs),
                json.dumps(tags),
                now,
            ),
        )
        return cur.lastrowid


def fetch_all(repo: str, db_path: Path = _DEFAULT_DB) -> list[dict]:
    """Return all memories for *repo* as plain dicts with parsed JSON fields."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE repo = ? ORDER BY id", (repo,)
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["tradeoffs"] = json.loads(d["tradeoffs"])
        d["tags"] = json.loads(d["tags"])
        result.append(d)
    return result


def clear_repo(repo: str, db_path: Path = _DEFAULT_DB) -> int:
    """Delete all memories for *repo*. Returns number of rows deleted."""
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM memories WHERE repo = ?", (repo,))
        return cur.rowcount
