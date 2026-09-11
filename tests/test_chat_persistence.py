"""Tests for optional persistence configuration without requiring PostgreSQL."""

from src.services.chat_persistence_service import _vector_literal, configured_user_id, get_chat_store


def test_chat_store_is_disabled_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_chat_store() is None


def test_chat_store_preserves_database_url_and_user_scope(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("KUNDALI_USER_ID", "user-42")
    store = get_chat_store()
    assert store is not None
    assert store.database_url == "postgresql://example"
    assert configured_user_id() == "user-42"


def test_vector_literal_is_postgresql_vector_safe():
    assert _vector_literal([1.0, -0.25]) == "[1,-0.25]"
    assert _vector_literal(None) is None
