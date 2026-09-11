"""Streamlit chat UI backed by deterministic chart context."""

import logging
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

# IMPORTANT:
# Load the project-root .env before importing any service module that may
# read DATABASE_URL at module-import time.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.localization.translations import t
from src.services.ai_chat_service import (
    ask_chart_question,
    build_chat_context,
    chat_is_available,
    detect_language,
)
from src.services.chat_persistence_service import configured_user_id, get_chat_store

logger = logging.getLogger(__name__)

SUGGESTION_KEYS = ("suggest_dasha", "suggest_career", "suggest_d10", "suggest_d9", "suggest_finance")


def render_ai_chat(chart, details, lang: str) -> None:
    """Render and retain current-session conversation history for the active Kundali."""
    st.subheader(t("chat_title", lang))
    st.caption(t("chat_caption", lang))
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    store = get_chat_store()
    user_id = configured_user_id()
    thread_id = None
    if store:
        try:
            store.setup()
            conversations = store.list_conversations(user_id)
            controls = st.columns((1, 3))
            if controls[0].button(t("new_chat", lang)):
                st.session_state.chat_conversation_id = store.create_conversation(user_id, lang)
                st.session_state.chat_messages = []
                st.session_state.pop("chat_conversation_selector", None)
                st.rerun()
            if not conversations:
                st.session_state.chat_conversation_id = store.create_conversation(user_id, lang)
                conversations = store.list_conversations(user_id)
            labels = {conversation.id: conversation.title for conversation in conversations}
            active = st.session_state.get("chat_conversation_id", conversations[0].id)
            if active not in labels:
                active = conversations[0].id
            selected = controls[1].selectbox(t("conversations", lang), list(labels), index=list(labels).index(active), format_func=lambda item: labels[item], key="chat_conversation_selector")
            thread_id = selected
            if selected != st.session_state.get("chat_conversation_id"):
                st.session_state.chat_conversation_id = selected
                st.session_state.chat_messages = store.load_messages(user_id, selected)
        except Exception as exc:
            # Do not incorrectly report that DATABASE_URL is missing when
            # PostgreSQL is configured but initialization failed for another reason.
            logger.exception("Persistent chat memory initialization failed")
            st.warning(
                f"{t('memory_unavailable', lang)} "
                f"({type(exc).__name__}: {exc})"
            )
            store = None
    else:
        st.caption(t("memory_unavailable", lang))
    clear_col, _ = st.columns((1, 5))
    if clear_col.button(t("clear_chat", lang)):
        st.session_state.chat_messages = []
        st.rerun()
    if not chat_is_available():
        st.info(t("chat_unavailable", lang))
        return
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    st.markdown(f"**{t('suggested_questions', lang)}**")
    suggestion_columns = st.columns(2)
    question = None
    for index, key in enumerate(SUGGESTION_KEYS):
        if suggestion_columns[index % 2].button(t(key, lang), key=f"chat_{key}"):
            question = t(key, lang)
    question = st.chat_input(t("chat_input", lang)) or question
    if not question:
        return
    context = build_chat_context(chart, details)
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    try:
        with st.chat_message("assistant"):
            with st.spinner(t("chat_loading", lang)):
                answer = ask_chart_question(context, st.session_state.chat_messages[:-1], question, detect_language(question, lang), user_id=user_id, thread_id=thread_id)
            if answer is None:
                st.info(t("chat_unavailable", lang))
                return
            st.markdown(answer)
    except Exception as exc:
        logger.exception("AI chat request failed")
        st.error(
            f"{t('chat_error', lang)} "
            f"({type(exc).__name__}: {exc})"
        )
        return
    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
