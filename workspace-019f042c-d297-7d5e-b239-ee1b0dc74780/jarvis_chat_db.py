"""
JARVIS v4 - Persistent Chat Database
====================================
SQLite-based chat history with conversation management,
message search, and metadata tracking.

Tables:
- conversations: Chat sessions with titles and timestamps
- messages: Individual messages with role, content, and metadata
- message_feedback: User feedback on AI responses (thumbs up/down)
"""

import sqlite3
import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from contextlib import contextmanager

from jarvis_core import BASE_DIR, OWNER_NAME, get_timestamp

# Database file path
CHAT_DB_PATH = BASE_DIR / "memory" / "jarvis_chat.db"


class ChatDatabase:
    """Thread-safe SQLite database for persistent chat history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or CHAT_DB_PATH)
        self._local = threading.local()
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                is_pinned INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0,
                model TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # Message feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_feedback (
                message_id INTEGER PRIMARY KEY,
                feedback INTEGER CHECK(feedback IN (1, -1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conv 
            ON messages(conversation_id, created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_content 
            ON messages(content)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated 
            ON conversations(updated_at DESC)
        """)

        conn.commit()

    # ============================================================
    # CONVERSATION OPERATIONS
    # ============================================================

    def create_conversation(self, title: str = None) -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())[:8]
        title = title or f"Chat {datetime.now().strftime('%m/%d %H:%M')}"

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, title) VALUES (?, ?)
        """, (conv_id, title))
        conn.commit()
        return conv_id

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get a conversation by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations WHERE id = ?
        """, (conv_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str = None
    ) -> List[Dict]:
        """List conversations ordered by most recent update."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if search:
            cursor.execute("""
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                ORDER BY c.updated_at DESC
                LIMIT ? OFFSET ?
            """, (f"%{search}%", f"%{search}%", limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        return [dict(row) for row in cursor.fetchall()]

    def update_conversation_title(self, conv_id: str, title: str):
        """Update conversation title."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations 
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, conv_id))
        conn.commit()

    def pin_conversation(self, conv_id: str, pinned: bool = True):
        """Pin or unpin a conversation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations SET is_pinned = ? WHERE id = ?
        """, (1 if pinned else 0, conv_id))
        conn.commit()

    def delete_conversation(self, conv_id: str):
        """Delete a conversation and all its messages."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()

    # ============================================================
    # MESSAGE OPERATIONS
    # ============================================================

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        model: str = "",
        metadata: Dict = None
    ) -> int:
        """Add a message to a conversation. Returns message ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Insert message
        cursor.execute("""
            INSERT INTO messages 
            (conversation_id, role, content, tokens_used, model, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conv_id, role, content, tokens_used, model,
              json.dumps(metadata or {})))

        msg_id = cursor.lastrowid

        # Update conversation timestamp and message count
        cursor.execute("""
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP,
                message_count = message_count + 1
            WHERE id = ?
        """, (conv_id,))

        conn.commit()
        return msg_id

    def get_messages(
        self,
        conv_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get messages for a conversation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, f.feedback
            FROM messages m
            LEFT JOIN message_feedback f ON m.id = f.message_id
            WHERE m.conversation_id = ?
            ORDER BY m.created_at
            LIMIT ? OFFSET ?
        """, (conv_id, limit, offset))
        return [dict(row) for row in cursor.fetchall()]

    def get_messages_for_ai(self, conv_id: str, limit: int = 30) -> List[Dict[str, str]]:
        """Get messages formatted for AI context (role/content only)."""
        messages = self.get_messages(conv_id, limit=limit)
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def search_messages(
        self,
        query: str,
        conv_id: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search messages by content."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if conv_id:
            cursor.execute("""
                SELECT m.*, c.title as conversation_title
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.conversation_id = ? AND m.content LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (conv_id, f"%{query}%", limit))
        else:
            cursor.execute("""
                SELECT m.*, c.title as conversation_title
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.content LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (f"%{query}%", limit))

        return [dict(row) for row in cursor.fetchall()]

    def add_feedback(self, message_id: int, feedback: int):
        """Add thumbs up (1) or thumbs down (-1) feedback."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO message_feedback (message_id, feedback)
            VALUES (?, ?)
        """, (message_id, feedback))
        conn.commit()

    def delete_message(self, message_id: int):
        """Delete a specific message."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()

    # ============================================================
    # STATS & ANALYTICS
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total conversations
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        total_conversations = cursor.fetchone()["count"]

        # Total messages
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        total_messages = cursor.fetchone()["count"]

        # Messages by role
        cursor.execute("""
            SELECT role, COUNT(*) as count 
            FROM messages GROUP BY role
        """)
        messages_by_role = {row["role"]: row["count"] for row in cursor.fetchall()}

        # Today's messages
        cursor.execute("""
            SELECT COUNT(*) as count FROM messages 
            WHERE DATE(created_at) = DATE('now')
        """)
        today_messages = cursor.fetchone()["count"]

        # Most active conversation
        cursor.execute("""
            SELECT id, title, message_count 
            FROM conversations 
            ORDER BY message_count DESC LIMIT 1
        """)
        most_active = dict(cursor.fetchone()) if cursor.fetchone else None

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "messages_by_role": messages_by_role,
            "today_messages": today_messages,
            "most_active_conversation": most_active,
        }

    def get_conversation_stats(self, conv_id: str) -> Dict[str, Any]:
        """Get statistics for a specific conversation."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as ai_messages,
                SUM(tokens_used) as total_tokens,
                MIN(created_at) as started_at,
                MAX(created_at) as last_active
            FROM messages
            WHERE conversation_id = ?
        """, (conv_id,))

        row = cursor.fetchone()
        return dict(row) if row else {}


# ============================================================
# GLOBAL INSTANCE
# ============================================================

chat_db = ChatDatabase()


# Convenience functions
def create_conversation(title: str = None) -> str:
    """Create a new conversation."""
    return chat_db.create_conversation(title)


def add_user_message(conv_id: str, content: str) -> int:
    """Add a user message to a conversation."""
    return chat_db.add_message(conv_id, "user", content)


def add_assistant_message(
    conv_id: str,
    content: str,
    tokens_used: int = 0,
    model: str = ""
) -> int:
    """Add an assistant message to a conversation."""
    return chat_db.add_message(conv_id, "assistant", content, tokens_used, model)


def get_conversation_messages(conv_id: str, limit: int = 100) -> List[Dict]:
    """Get all messages in a conversation."""
    return chat_db.get_messages(conv_id, limit=limit)


def get_ai_context(conv_id: str, limit: int = 30) -> List[Dict[str, str]]:
    """Get messages formatted for AI context."""
    return chat_db.get_messages_for_ai(conv_id, limit=limit)


__all__ = [
    'ChatDatabase', 'chat_db',
    'create_conversation',
    'add_user_message', 'add_assistant_message',
    'get_conversation_messages', 'get_ai_context',
]
