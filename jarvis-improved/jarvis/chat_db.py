"""
Persistent chat database — SQLite with conversation management.
Thread-safe via per-thread connections and WAL mode.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from jarvis.config import MEMORY_DIR

DB_PATH = MEMORY_DIR / "jarvis_chat.db"


class ChatDatabase:
    def __init__(self, path: Path | None = None):
        self.path = str(path or DB_PATH)
        self._local = threading.local()
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_tables(self):
        c = self._conn().cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0, is_pinned INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_msg ON messages(conversation_id, created_at)")
        self._conn().commit()

    # Conversations
    def create(self, title: str | None = None) -> str:
        cid = str(uuid.uuid4())[:8]
        title = title or f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
        c = self._conn().cursor()
        c.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", (cid, title))
        self._conn().commit()
        return cid

    def list(self, limit: int = 50) -> list[dict]:
        c = self._conn().cursor()
        c.execute("SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]

    def delete(self, cid: str):
        c = self._conn().cursor()
        c.execute("DELETE FROM conversations WHERE id = ?", (cid,))
        self._conn().commit()

    # Messages
    def add_msg(self, cid: str, role: str, content: str) -> int:
        c = self._conn().cursor()
        c.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                  (cid, role, content))
        mid = c.lastrowid
        c.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP, message_count=message_count+1 WHERE id=?", (cid,))
        self._conn().commit()
        return mid

    def get_messages(self, cid: str, limit: int = 100) -> list[dict]:
        c = self._conn().cursor()
        c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at LIMIT ?", (cid, limit))
        return [dict(r) for r in c.fetchall()]

    def ai_context(self, cid: str, limit: int = 30) -> list[dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in self.get_messages(cid, limit)]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        c = self._conn().cursor()
        c.execute("""SELECT m.*, c.title as conv_title FROM messages m
            JOIN conversations c ON m.conversation_id=c.id
            WHERE m.content LIKE ? ORDER BY m.created_at DESC LIMIT ?""", (f"%{query}%", limit))
        return [dict(r) for r in c.fetchall()]

    def stats(self) -> dict:
        c = self._conn().cursor()
        c.execute("SELECT COUNT(*) as n FROM conversations"); convs = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages"); msgs = c.fetchone()["n"]
        return {"conversations": convs, "messages": msgs}


chat_db = ChatDatabase()
