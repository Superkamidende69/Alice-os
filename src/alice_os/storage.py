from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import StoredMessage


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Storage:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            str(database_path), check_same_thread=False, isolation_level=None
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    provider_id TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, created_at);
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create_session(
        self,
        title: str = "New conversation",
        workspace: str = "",
        provider_id: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        now = utc_now()
        clean_title = title.strip()[:120] or "New conversation"
        with self._lock:
            self._connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, clean_title, workspace, provider_id, model, now, now),
            )
        return self.get_session(session_id, include_messages=False)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str, *, include_messages: bool = True) -> dict[str, Any]:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown session: {session_id}")
        result = dict(row)
        if include_messages:
            result["messages"] = [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "metadata": message.metadata,
                    "created_at": message.created_at,
                }
                for message in self.list_messages(session_id)
            ]
        return result

    def update_session(self, session_id: str, **changes: str) -> dict[str, Any]:
        allowed = {"title", "workspace", "provider_id", "model"}
        selected = {key: value for key, value in changes.items() if key in allowed}
        if not selected:
            return self.get_session(session_id, include_messages=False)
        selected["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in selected)
        values = [*selected.values(), session_id]
        with self._lock:
            cursor = self._connection.execute(
                f"UPDATE sessions SET {assignments} WHERE id = ?", values
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Unknown session: {session_id}")
        return self.get_session(session_id, include_messages=False)

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            cursor = self._connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if cursor.rowcount == 0:
            raise KeyError(f"Unknown session: {session_id}")

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> StoredMessage:
        message = StoredMessage(
            id=uuid.uuid4().hex,
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
            created_at=utc_now(),
        )
        with self._lock:
            self._connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                (
                    message.id,
                    message.session_id,
                    message.role,
                    message.content,
                    json.dumps(message.metadata),
                    message.created_at,
                ),
            )
            self._connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (message.created_at, session_id),
            )
        return message

    def list_messages(self, session_id: str) -> list[StoredMessage]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at, rowid",
                (session_id,),
            ).fetchall()
        return [
            StoredMessage(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_memory(self, session_id: str, content: str) -> dict[str, str]:
        memory = {"id": uuid.uuid4().hex, "content": content, "created_at": utc_now()}
        with self._lock:
            self._connection.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?)",
                (memory["id"], session_id, memory["content"], memory["created_at"]),
            )
        return memory

    def search_memories(self, session_id: str, query: str, limit: int = 10) -> list[dict[str, str]]:
        pattern = f"%{query}%"
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, content, created_at FROM memories "
                "WHERE session_id = ? AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (session_id, pattern, max(1, min(limit, 50))),
            ).fetchall()
        return [dict(row) for row in rows]
