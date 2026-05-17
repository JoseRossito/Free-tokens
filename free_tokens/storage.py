import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

DEFAULT_DB = Path.home() / ".free_tokens" / "usage.db"


class UsageStorage:
    def __init__(self, db_path: str | None = None):
        self._path = Path(db_path or DEFAULT_DB)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_creation_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    prompt_preview TEXT DEFAULT '',
                    model TEXT DEFAULT '',
                    session_id TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def save(self, record) -> None:
        # record is a UsageRecord (see usage.py); access its fields
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT INTO usage_records "
                "(timestamp, source, input_tokens, output_tokens, "
                "cache_creation_tokens, cache_read_tokens, prompt_preview, model, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.timestamp.isoformat(),
                    record.source,
                    record.input_tokens,
                    record.output_tokens,
                    record.cache_creation_input_tokens,
                    record.cache_read_input_tokens,
                    record.prompt_preview,
                    record.model,
                    record.session_id,
                )
            )
            conn.commit()

    def get_records(self, since: datetime, until: datetime | None = None) -> list[dict]:
        until = until or datetime.now()
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM usage_records WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC",
                (since.isoformat(), until.isoformat())
            )
            return [dict(r) for r in cur.fetchall()]
