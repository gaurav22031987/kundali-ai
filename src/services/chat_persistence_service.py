"""Optional PostgreSQL/pgvector persistence for user-scoped Kundali chat memory."""

import os
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: str
    title: str
    language: str
    updated_at: datetime


class PostgresChatStore:
    """Durable conversations plus vector-searchable user memory.

    Imports psycopg lazily so an unconfigured local Streamlit app retains its
    existing in-memory chat behavior.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    @property
    def enabled(self) -> bool:
        return bool(self.database_url)

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url)

    def setup(self) -> None:
        """Create extension, tables, and vector indexes; safe to call repeatedly."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("""CREATE TABLE IF NOT EXISTS chat_conversations (
                id UUID PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL,
                language TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY, conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
                embedding vector(1536), created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_memories (
                id UUID PRIMARY KEY, user_id TEXT NOT NULL, source_conversation_id UUID REFERENCES chat_conversations(id) ON DELETE SET NULL,
                content TEXT NOT NULL, embedding vector(1536), created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
            cursor.execute("CREATE INDEX IF NOT EXISTS chat_messages_user_conversation_idx ON chat_messages (user_id, conversation_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS user_memories_user_idx ON user_memories (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS user_memories_embedding_idx ON user_memories USING hnsw (embedding vector_cosine_ops)")

    def create_conversation(self, user_id: str, language: str, title: str = "New Kundali Chat") -> str:
        conversation_id = str(uuid4())
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO chat_conversations (id, user_id, title, language) VALUES (%s, %s, %s, %s)", (conversation_id, user_id, title, language))
        return conversation_id

    def list_conversations(self, user_id: str) -> list[Conversation]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id::text, user_id, title, language, updated_at FROM chat_conversations WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
            return [Conversation(*row) for row in cursor.fetchall()]

    def load_messages(self, user_id: str, conversation_id: str) -> list[dict[str, str]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT role, content FROM chat_messages WHERE user_id = %s AND conversation_id = %s::uuid ORDER BY created_at", (user_id, conversation_id))
            return [{"role": role, "content": content} for role, content in cursor.fetchall()]

    def save_message(self, user_id: str, conversation_id: str, role: str, content: str, embedding: list[float] | None) -> None:
        vector = _vector_literal(embedding) if embedding else None
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO chat_messages (id, conversation_id, user_id, role, content, embedding) VALUES (%s, %s::uuid, %s, %s, %s, %s::vector)", (str(uuid4()), conversation_id, user_id, role, content, vector))
            cursor.execute("UPDATE chat_conversations SET title = CASE WHEN title = 'New Kundali Chat' AND %s = 'user' THEN left(%s, 80) ELSE title END, updated_at = now() WHERE id = %s::uuid AND user_id = %s", (role, content, conversation_id, user_id))

    def save_memory(self, user_id: str, conversation_id: str, content: str, embedding: list[float]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO user_memories (id, user_id, source_conversation_id, content, embedding) VALUES (%s, %s, %s::uuid, %s, %s::vector)", (str(uuid4()), user_id, conversation_id, content, _vector_literal(embedding)))

    def retrieve_memories(self, user_id: str, query_embedding: list[float], exclude_conversation_id: str | None, limit: int = 5) -> list[str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""SELECT content FROM user_memories
                WHERE user_id = %s AND (%s::uuid IS NULL OR source_conversation_id IS DISTINCT FROM %s::uuid)
                ORDER BY embedding <=> %s::vector LIMIT %s""", (user_id, exclude_conversation_id, exclude_conversation_id, _vector_literal(query_embedding), limit))
            return [row[0] for row in cursor.fetchall()]


def _vector_literal(vector: list[float] | None) -> str | None:
    return None if vector is None else "[" + ",".join(f"{value:.8g}" for value in vector) + "]"


def get_chat_store() -> PostgresChatStore | None:
    database_url = os.getenv("DATABASE_URL", "")
    return PostgresChatStore(database_url) if database_url else None


def configured_user_id() -> str:
    """Replace KUNDALI_USER_ID with authenticated identity in a production host."""
    return os.getenv("KUNDALI_USER_ID", "local-user")
