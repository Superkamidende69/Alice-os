from __future__ import annotations

import json
import re
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
                CREATE TABLE IF NOT EXISTS global_memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source_session_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_global_memories_updated
                    ON global_memories(updated_at DESC);
                """
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO global_memories "
                "(id, content, source_session_id, created_at, updated_at) "
                "SELECT id, content, session_id, created_at, created_at FROM memories"
            )
            columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(global_memories)").fetchall()
            }
            migrations = {
                "category": "TEXT NOT NULL DEFAULT 'fact'",
                "memory_key": "TEXT NOT NULL DEFAULT ''",
                "importance": "INTEGER NOT NULL DEFAULT 3",
                "confidence": "REAL NOT NULL DEFAULT 1.0",
                "source": "TEXT NOT NULL DEFAULT 'conversation'",
                "last_accessed_at": "TEXT NOT NULL DEFAULT ''",
                "archived": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    self._connection.execute(
                        f"ALTER TABLE global_memories ADD COLUMN {name} {definition}"
                    )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_global_memories_active "
                "ON global_memories(archived, category, importance DESC, updated_at DESC)"
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

    def add_global_memory(
        self,
        content: str,
        source_session_id: str = "",
        *,
        category: str = "fact",
        memory_key: str = "",
        importance: int = 3,
        confidence: float = 1.0,
        source: str = "conversation",
    ) -> dict[str, Any]:
        now = utc_now()
        category = category.strip().lower()[:32] or "fact"
        memory_key = memory_key.strip().lower()[:120]
        importance = max(1, min(int(importance), 5))
        confidence = max(0.0, min(float(confidence), 1.0))
        with self._lock:
            existing = None
            if memory_key:
                existing = self._connection.execute(
                    "SELECT id, content, created_at FROM global_memories "
                    "WHERE archived = 0 AND category = ? AND memory_key = ?",
                    (category, memory_key),
                ).fetchone()
            if existing is None:
                existing = self._connection.execute(
                    "SELECT id, content, created_at FROM global_memories "
                    "WHERE archived = 0 AND lower(content) = lower(?)",
                    (content,),
                ).fetchone()
            if existing:
                self._connection.execute(
                    "UPDATE global_memories SET content = ?, importance = ?, confidence = ?, "
                    "source = ?, updated_at = ?, last_accessed_at = ? WHERE id = ?",
                    (content, importance, confidence, source, now, now, existing["id"]),
                )
                result = dict(existing)
                result.update({
                    "content": content,
                    "category": category,
                    "memory_key": memory_key,
                    "importance": importance,
                    "confidence": confidence,
                })
                return result
            memory = {
                "id": uuid.uuid4().hex,
                "content": content,
                "created_at": now,
                "category": category,
                "memory_key": memory_key,
                "importance": importance,
                "confidence": confidence,
            }
            self._connection.execute(
                "INSERT INTO global_memories "
                "(id, content, source_session_id, created_at, updated_at, category, memory_key, "
                "importance, confidence, source, last_accessed_at, archived) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    memory["id"], content, source_session_id, now, now, category, memory_key,
                    importance, confidence, source, now,
                ),
            )
        return memory

    def list_global_memories(self, limit: int = 100) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, content, created_at, updated_at, category, memory_key, importance, "
                "confidence, source, last_accessed_at FROM global_memories "
                "WHERE archived = 0 ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def search_global_memories(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        terms = [term for term in re.findall(r"[\w'-]{2,}", query.casefold()) if term not in {
            "what", "when", "where", "which", "that", "this", "with", "have", "from", "about",
            "tell", "please", "alice", "remember", "forget",
        }]
        if not terms:
            return []
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, content, created_at, updated_at, category, memory_key, importance, "
                "confidence, source, last_accessed_at FROM global_memories WHERE archived = 0",
            ).fetchall()
        now = datetime.now(UTC)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            haystack = f"{item['content']} {item['memory_key']}".casefold()
            matches = sum(1 for term in terms if term in haystack)
            if not matches:
                continue
            try:
                age_days = max(0.0, (now - datetime.fromisoformat(item["updated_at"])).total_seconds() / 86400)
            except (KeyError, TypeError, ValueError):
                age_days = 365.0
            recency = 1.0 / (1.0 + age_days / 30.0)
            score = matches * 10 + int(item["importance"]) * 1.5 + float(item["confidence"]) + recency
            ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        results = [item for _, item in ranked[: max(1, min(limit, 50))]]
        if results:
            self.touch_global_memories([item["id"] for item in results])
        return results

    def touch_global_memories(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        now = utc_now()
        with self._lock:
            self._connection.executemany(
                "UPDATE global_memories SET last_accessed_at = ? WHERE id = ? AND archived = 0",
                [(now, memory_id) for memory_id in memory_ids],
            )

    def delete_global_memory(self, memory_id: str) -> None:
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE global_memories SET archived = 1, updated_at = ? WHERE id = ? AND archived = 0",
                (utc_now(), memory_id),
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Unknown memory: {memory_id}")

    def update_global_memory(self, memory_id: str, **changes: Any) -> dict[str, Any]:
        allowed = {"content", "category", "memory_key", "importance", "confidence"}
        selected = {key: value for key, value in changes.items() if key in allowed and value is not None}
        if not selected:
            raise ValueError("No memory changes supplied")
        if "content" in selected:
            selected["content"] = str(selected["content"]).strip()
            if not selected["content"]:
                raise ValueError("Memory content is required")
        if "category" in selected:
            selected["category"] = str(selected["category"]).strip().lower()[:32] or "fact"
        if "memory_key" in selected:
            selected["memory_key"] = str(selected["memory_key"]).strip().lower()[:120]
        if "importance" in selected:
            selected["importance"] = max(1, min(int(selected["importance"]), 5))
        if "confidence" in selected:
            selected["confidence"] = max(0.0, min(float(selected["confidence"]), 1.0))
        selected["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in selected)
        with self._lock:
            cursor = self._connection.execute(
                f"UPDATE global_memories SET {assignments} WHERE id = ? AND archived = 0",
                [*selected.values(), memory_id],
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Unknown memory: {memory_id}")
            row = self._connection.execute(
                "SELECT id, content, created_at, updated_at, category, memory_key, importance, "
                "confidence, source, last_accessed_at FROM global_memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return dict(row)
