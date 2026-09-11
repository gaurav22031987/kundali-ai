"""PostgreSQL/pgvector persistence for multi-user Kundali chat."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class User:
    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: str
    title: str
    language: str
    updated_at: datetime


class PostgresChatStore:
    """Durable multi-user conversations and optional vector memories.

    Architecture:
    - app_users stores application users.
    - chat_conversations stores conversations per user.
    - chat_messages is the canonical UI transcript.
    - user_memories stores optional vector-searchable long-term memory.
    - LangGraph checkpoint tables, if used elsewhere, are execution state only.
    """

    def __init__(self, database_url: str):
        self.database_url = (database_url or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.database_url)

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    def setup(self) -> None:
        """Create/migrate extension, tables, and indexes.

        Safe to call repeatedly on local PostgreSQL and hosted PostgreSQL/Neon.
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    language TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id UUID PRIMARY KEY,
                    conversation_id UUID NOT NULL
                        REFERENCES chat_conversations(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    turn_id UUID,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            # Migration for older DBs where turn_id did not exist.
            cursor.execute(
                """
                ALTER TABLE chat_messages
                ADD COLUMN IF NOT EXISTS turn_id UUID
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    source_conversation_id UUID
                        REFERENCES chat_conversations(id) ON DELETE SET NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS chat_conversations_user_idx
                ON chat_conversations (user_id, updated_at DESC)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS chat_messages_user_conversation_idx
                ON chat_messages (user_id, conversation_id, created_at, id)
                """
            )

            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_turn_role_uniq
                ON chat_messages (conversation_id, turn_id, role)
                WHERE turn_id IS NOT NULL
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS user_memories_user_idx
                ON user_memories (user_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS user_memories_embedding_idx
                ON user_memories USING hnsw (embedding vector_cosine_ops)
                """
            )

            # Ensure configured/default user exists.
            default_user_id = configured_user_id()
            default_user_name = (
                os.getenv("KUNDALI_USER_NAME", "Default User").strip()
                or "Default User"
            )

            cursor.execute(
                """
                INSERT INTO app_users (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (default_user_id, default_user_name),
            )

            # Backfill users from legacy conversation data.
            cursor.execute(
                """
                INSERT INTO app_users (id, name)
                SELECT DISTINCT user_id, user_id
                FROM chat_conversations
                WHERE user_id IS NOT NULL
                  AND user_id <> ''
                ON CONFLICT (id) DO NOTHING
                """
            )

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def create_user(self, name: str) -> str:
        name = (name or "").strip()
        if not name:
            raise ValueError("User name cannot be empty.")

        user_id = str(uuid4())

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_users (id, name)
                VALUES (%s, %s)
                """,
                (user_id, name),
            )

        return user_id

    def list_users(self) -> list[User]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, created_at
                FROM app_users
                ORDER BY lower(name), created_at
                """
            )

            return [User(*row) for row in cursor.fetchall()]

    def get_user(self, user_id: str) -> User | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, created_at
                FROM app_users
                WHERE id = %s
                """,
                (user_id,),
            )

            row = cursor.fetchone()
            return User(*row) if row else None

    def rename_user(self, user_id: str, name: str) -> None:
        name = (name or "").strip()
        if not name:
            raise ValueError("User name cannot be empty.")

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE app_users
                SET name = %s
                WHERE id = %s
                """,
                (name, user_id),
            )

    def delete_user(self, user_id: str) -> None:
        """Delete user and all associated chat/memory data."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_memories WHERE user_id = %s",
                (user_id,),
            )

            cursor.execute(
                "DELETE FROM chat_conversations WHERE user_id = %s",
                (user_id,),
            )

            cursor.execute(
                "DELETE FROM app_users WHERE id = %s",
                (user_id,),
            )

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        user_id: str,
        language: str,
        title: str = "New Kundali Chat",
        *,
        reuse_empty: bool = True,
    ) -> str:
        """Create a conversation, reusing an existing empty default chat."""
        with self._connect() as connection, connection.cursor() as cursor:
            if reuse_empty and title == "New Kundali Chat":
                cursor.execute(
                    """
                    SELECT c.id::text
                    FROM chat_conversations c
                    WHERE c.user_id = %s
                      AND c.language = %s
                      AND c.title = 'New Kundali Chat'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM chat_messages m
                          WHERE m.conversation_id = c.id
                      )
                    ORDER BY c.updated_at DESC
                    LIMIT 1
                    """,
                    (user_id, language),
                )

                row = cursor.fetchone()
                if row:
                    return row[0]

            conversation_id = str(uuid4())

            cursor.execute(
                """
                INSERT INTO chat_conversations (
                    id,
                    user_id,
                    title,
                    language
                )
                VALUES (%s::uuid, %s, %s, %s)
                """,
                (
                    conversation_id,
                    user_id,
                    title,
                    language,
                ),
            )

            return conversation_id

    def list_conversations(self, user_id: str) -> list[Conversation]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, user_id, title, language, updated_at
                FROM chat_conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC, created_at DESC
                """,
                (user_id,),
            )

            return [Conversation(*row) for row in cursor.fetchall()]

    def load_messages(
        self,
        user_id: str,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        """Load one user's conversation in stable chronological order."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE user_id = %s
                  AND conversation_id = %s::uuid
                ORDER BY created_at ASC, id ASC
                """,
                (
                    user_id,
                    conversation_id,
                ),
            )

            return [
                {
                    "role": role,
                    "content": content,
                }
                for role, content in cursor.fetchall()
            ]

    def append_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        embedding: list[float] | None = None,
        *,
        turn_id: str | None = None,
    ) -> bool:
        """Persist exactly one message.

        turn_id should be shared by the user and assistant message for one
        logical turn. The unique index prevents duplicate writes on reruns.

        Returns True if inserted, False if it was already present.
        """
        if role not in {"user", "assistant"}:
            raise ValueError("Role must be 'user' or 'assistant'.")

        content = (content or "").strip()
        if not content:
            raise ValueError("Message content cannot be empty.")

        resolved_turn_id = turn_id or str(uuid4())
        vector = _vector_literal(embedding) if embedding else None

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    id,
                    conversation_id,
                    user_id,
                    role,
                    content,
                    embedding,
                    turn_id
                )
                VALUES (
                    %s::uuid,
                    %s::uuid,
                    %s,
                    %s,
                    %s,
                    %s::vector,
                    %s::uuid
                )
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (
                    str(uuid4()),
                    conversation_id,
                    user_id,
                    role,
                    content,
                    vector,
                    resolved_turn_id,
                ),
            )

            inserted = cursor.fetchone() is not None

            if inserted:
                cursor.execute(
                    """
                    UPDATE chat_conversations
                    SET
                        title = CASE
                            WHEN title = 'New Kundali Chat'
                                 AND %s = 'user'
                            THEN left(%s, 80)
                            ELSE title
                        END,
                        updated_at = now()
                    WHERE id = %s::uuid
                      AND user_id = %s
                    """,
                    (
                        role,
                        content,
                        conversation_id,
                        user_id,
                    ),
                )

            return inserted

    def save_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        embedding: list[float] | None,
    ) -> None:
        """Backward-compatible alias."""
        self.append_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            embedding=embedding,
        )

    def clear_conversation(
        self,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Clear selected user's selected conversation."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM user_memories
                WHERE user_id = %s
                  AND source_conversation_id = %s::uuid
                """,
                (
                    user_id,
                    conversation_id,
                ),
            )

            cursor.execute(
                """
                DELETE FROM chat_messages
                WHERE user_id = %s
                  AND conversation_id = %s::uuid
                """,
                (
                    user_id,
                    conversation_id,
                ),
            )

            cursor.execute(
                """
                UPDATE chat_conversations
                SET title = 'New Kundali Chat',
                    updated_at = now()
                WHERE id = %s::uuid
                  AND user_id = %s
                """,
                (
                    conversation_id,
                    user_id,
                ),
            )

    def delete_conversation(
        self,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Delete selected conversation and associated derived memories."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM user_memories
                WHERE user_id = %s
                  AND source_conversation_id = %s::uuid
                """,
                (
                    user_id,
                    conversation_id,
                ),
            )

            cursor.execute(
                """
                DELETE FROM chat_conversations
                WHERE id = %s::uuid
                  AND user_id = %s
                """,
                (
                    conversation_id,
                    user_id,
                ),
            )

    # ------------------------------------------------------------------
    # Vector memory
    # ------------------------------------------------------------------

    def save_memory(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        embedding: list[float],
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_memories (
                    id,
                    user_id,
                    source_conversation_id,
                    content,
                    embedding
                )
                VALUES (
                    %s::uuid,
                    %s,
                    %s::uuid,
                    %s,
                    %s::vector
                )
                """,
                (
                    str(uuid4()),
                    user_id,
                    conversation_id,
                    content,
                    _vector_literal(embedding),
                ),
            )

    def retrieve_memories(
        self,
        user_id: str,
        query_embedding: list[float],
        exclude_conversation_id: str | None,
        limit: int = 5,
    ) -> list[str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT content
                FROM user_memories
                WHERE user_id = %s
                  AND (
                      %s::uuid IS NULL
                      OR source_conversation_id IS DISTINCT FROM %s::uuid
                  )
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    user_id,
                    exclude_conversation_id,
                    exclude_conversation_id,
                    _vector_literal(query_embedding),
                    limit,
                ),
            )

            return [row[0] for row in cursor.fetchall()]


def _vector_literal(vector: list[float] | None) -> str | None:
    """Convert a Python vector to pgvector literal format."""
    if vector is None:
        return None

    return "[" + ",".join(f"{value:.8g}" for value in vector) + "]"


def get_chat_store() -> PostgresChatStore | None:
    """Return the configured PostgreSQL chat store, if DATABASE_URL exists."""
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        return None

    return PostgresChatStore(database_url)


def configured_user_id() -> str:
    """Return default user id used before/without real authentication."""
    return (
        os.getenv("KUNDALI_USER_ID", "local-user").strip()
        or "local-user"
    )
