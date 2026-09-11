"""Multi-user interactive Kundali chat UI with typing indicators.

Features:
- Suggested questions removed.
- Multi-user selection and per-user conversation history.
- Add user, new chat, clear chat, delete conversation.
- Real per-keystroke draft updates using streamlit-keyup.
- "You are typing..." indicator while the user types.
- "AI is typing..." animated indicator while waiting for the model.
- Typewriter-style rendering for the assistant response.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
import streamlit as st
from st_keyup import st_keyup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.localization.translations import t
from src.services.ai_chat_service import (
    ask_chart_question,
    build_chat_context,
    chat_is_available,
    detect_language,
)
from src.services.chat_persistence_service import (
    configured_user_id,
    get_chat_store,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def _inject_chat_css() -> None:
    st.markdown(
        """
        <style>
        .kundali-typing {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 14px;
            background: rgba(128,128,128,0.08);
            font-size: 0.95rem;
            margin: 4px 0 8px 0;
        }

        .kundali-typing-dots {
            display: inline-flex;
            gap: 4px;
            align-items: center;
        }

        .kundali-typing-dots span {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
            opacity: 0.35;
            animation: kundaliTyping 1.25s infinite ease-in-out;
        }

        .kundali-typing-dots span:nth-child(2) {
            animation-delay: 0.15s;
        }

        .kundali-typing-dots span:nth-child(3) {
            animation-delay: 0.30s;
        }

        @keyframes kundaliTyping {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.35;
            }
            30% {
                transform: translateY(-4px);
                opacity: 1;
            }
        }

        .kundali-user-typing {
            font-size: 0.85rem;
            opacity: 0.75;
            margin-top: -6px;
            margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _welcome_message(lang: str, user_name: str) -> str:
    if lang == "hi":
        return (
            f"नमस्ते {user_name}! 👋\n\n"
            "मैं आपकी कुंडली के आधार पर आपसे बातचीत कर सकता हूँ। "
            "Career, Job, Mahadasha, D10, Marriage, Finance, Foreign opportunity "
            "या किसी भी कुंडली संबंधी सवाल से शुरू करें।\n\n"
            "**आप क्या जानना चाहेंगे?**"
        )

    return (
        f"Namaste {user_name}! 👋\n\n"
        "I can discuss your Kundali interactively. "
        "Ask me about Career, Job, Mahadasha, D10, Marriage, Finance, "
        "Foreign opportunities, or anything else related to your chart.\n\n"
        "**What would you like to know?**"
    )


def _reset_chat_state() -> None:
    st.session_state.chat_messages = []
    st.session_state.pop("chat_conversation_id", None)
    st.session_state.pop("chat_conversation_selector", None)
    st.session_state.pop("chat_loaded_conversation_id", None)
    st.session_state.chat_draft = ""
    st.session_state.chat_input_version = (
        st.session_state.get("chat_input_version", 0) + 1
    )


def _display_messages(
    messages: list[dict[str, str]],
    lang: str,
    user_name: str,
) -> None:
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(_welcome_message(lang, user_name))
        return

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _typing_html(lang: str) -> str:
    text = "AI लिख रहा है" if lang == "hi" else "AI is typing"

    return f"""
    <div class="kundali-typing">
        <span>{text}</span>
        <span class="kundali-typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </span>
    </div>
    """


def _stream_answer(answer: str):
    words = answer.split(" ")

    for index, word in enumerate(words):
        yield word + (" " if index < len(words) - 1 else "")
        time.sleep(0.012)


# ---------------------------------------------------------------------------
# Multi-user management
# ---------------------------------------------------------------------------

def _render_user_manager(store) -> tuple[str, str]:
    users = store.list_users()

    if not users:
        default_id = configured_user_id()
        return default_id, default_id

    labels = {user.id: user.name for user in users}
    user_ids = list(labels)

    current_user_id = st.session_state.get("selected_kundali_user_id")

    if current_user_id not in labels:
        configured = configured_user_id()
        current_user_id = configured if configured in labels else user_ids[0]

    st.markdown("### 👤 User")

    user_col, add_col = st.columns((3, 1))

    selected_user_id = user_col.selectbox(
        "Select user",
        user_ids,
        index=user_ids.index(current_user_id),
        format_func=lambda item: labels[item],
        key="kundali_user_selector",
        label_visibility="collapsed",
    )

    if selected_user_id != st.session_state.get("selected_kundali_user_id"):
        st.session_state.selected_kundali_user_id = selected_user_id
        _reset_chat_state()
        st.rerun()

    with add_col.popover("➕ Add user", use_container_width=True):
        new_name = st.text_input(
            "User name",
            key="new_kundali_user_name",
            placeholder="e.g. Gaurav Gupta",
        )

        if st.button(
            "Create user",
            key="create_kundali_user",
            use_container_width=True,
        ):
            name = (new_name or "").strip()

            if not name:
                st.warning("Please enter a user name.")
            else:
                new_user_id = store.create_user(name)
                st.session_state.selected_kundali_user_id = new_user_id
                st.session_state.pop("kundali_user_selector", None)
                st.session_state.pop("new_kundali_user_name", None)
                _reset_chat_state()
                st.rerun()

    return selected_user_id, labels[selected_user_id]


# ---------------------------------------------------------------------------
# Main chat UI
# ---------------------------------------------------------------------------

def render_ai_chat(chart, details, lang: str) -> None:
    _inject_chat_css()

    st.subheader(t("chat_title", lang))
    st.caption(t("chat_caption", lang))

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if "chat_draft" not in st.session_state:
        st.session_state.chat_draft = ""

    if "chat_input_version" not in st.session_state:
        st.session_state.chat_input_version = 0

    store = get_chat_store()

    thread_id: str | None = None
    user_id = configured_user_id()
    user_name = "User"

    # --------------------------------------------------------------
    # Users + conversations
    # --------------------------------------------------------------
    if store:
        try:
            store.setup()

            user_id, user_name = _render_user_manager(store)

            conversations = store.list_conversations(user_id)

            if not conversations:
                conversation_id = store.create_conversation(
                    user_id,
                    lang,
                    reuse_empty=True,
                )
                st.session_state.chat_conversation_id = conversation_id
                conversations = store.list_conversations(user_id)

            st.markdown("### 💬 Conversations")

            controls = st.columns((1, 4, 1))

            if controls[0].button(
                t("new_chat", lang),
                use_container_width=True,
            ):
                conversation_id = store.create_conversation(
                    user_id,
                    lang,
                    reuse_empty=True,
                )

                st.session_state.chat_conversation_id = conversation_id
                st.session_state.chat_messages = []
                st.session_state.pop("chat_conversation_selector", None)
                st.session_state.pop("chat_loaded_conversation_id", None)
                st.session_state.chat_draft = ""
                st.session_state.chat_input_version += 1
                st.rerun()

            labels = {
                conversation.id: conversation.title
                for conversation in conversations
            }

            active = st.session_state.get(
                "chat_conversation_id",
                conversations[0].id,
            )

            if active not in labels:
                active = conversations[0].id

            conversation_ids = list(labels)

            selected = controls[1].selectbox(
                t("conversations", lang),
                conversation_ids,
                index=conversation_ids.index(active),
                format_func=lambda item: labels[item],
                key="chat_conversation_selector",
                label_visibility="collapsed",
            )

            thread_id = selected
            st.session_state.chat_conversation_id = selected

            if controls[2].button(
                "🗑️",
                key="delete_current_chat",
                help="Delete current conversation",
                use_container_width=True,
            ):
                store.delete_conversation(user_id, selected)
                _reset_chat_state()
                st.rerun()

            if (
                st.session_state.get("chat_loaded_conversation_id")
                != selected
            ):
                st.session_state.chat_messages = store.load_messages(
                    user_id,
                    selected,
                )
                st.session_state.chat_loaded_conversation_id = selected

        except Exception as exc:
            logger.exception("Persistent chat memory initialization failed")
            st.warning(
                f"{t('memory_unavailable', lang)} "
                f"({type(exc).__name__}: {exc})"
            )
            store = None
            thread_id = None

    else:
        st.caption(t("memory_unavailable", lang))

    # --------------------------------------------------------------
    # Clear chat
    # --------------------------------------------------------------
    clear_col, _ = st.columns((1, 5))

    if clear_col.button(
        t("clear_chat", lang),
        use_container_width=True,
    ):
        if store and thread_id:
            try:
                store.clear_conversation(user_id, thread_id)
            except Exception:
                logger.exception("Could not clear persistent conversation")

        st.session_state.chat_messages = []
        st.session_state.chat_loaded_conversation_id = thread_id
        st.session_state.chat_draft = ""
        st.session_state.chat_input_version += 1
        st.rerun()

    if not chat_is_available():
        st.info(t("chat_unavailable", lang))
        return

    # --------------------------------------------------------------
    # Conversation
    # --------------------------------------------------------------
    _display_messages(
        st.session_state.chat_messages,
        lang,
        user_name,
    )

    # --------------------------------------------------------------
    # Custom typing input
    # --------------------------------------------------------------
    input_placeholder = (
        "अपना सवाल लिखें..."
        if lang == "hi"
        else "Type your question..."
    )

    input_key = f"kundali_chat_keyup_{st.session_state.chat_input_version}"

    draft = st_keyup(
        input_placeholder,
        value=st.session_state.chat_draft,
        debounce=250,
        key=input_key,
        label_visibility="collapsed",
    )

    st.session_state.chat_draft = draft or ""

    action_col, send_col = st.columns((8, 1))

    with action_col:
        if st.session_state.chat_draft.strip():
            typing_text = (
                "✍️ आप लिख रहे हैं..."
                if lang == "hi"
                else "✍️ You are typing..."
            )
            st.markdown(
                f'<div class="kundali-user-typing">{typing_text}</div>',
                unsafe_allow_html=True,
            )

    with send_col:
        send_clicked = st.button(
            "➤",
            key=f"send_chat_message_{st.session_state.chat_input_version}",
            help="Send message",
            use_container_width=True,
        )

    question = None

    if send_clicked and st.session_state.chat_draft.strip():
        question = st.session_state.chat_draft.strip()

    if not question:
        return

    # --------------------------------------------------------------
    # Build model context
    # --------------------------------------------------------------
    context = build_chat_context(chart, details)
    language = detect_language(question, lang)
    turn_id = str(uuid4())
    previous_history = list(st.session_state.chat_messages)

    # --------------------------------------------------------------
    # Persist and show user message
    # --------------------------------------------------------------
    st.session_state.chat_messages.append(
        {"role": "user", "content": question}
    )

    if store and thread_id:
        try:
            store.append_message(
                user_id,
                thread_id,
                "user",
                question,
                turn_id=turn_id,
            )
        except Exception:
            logger.exception("Could not persist user chat message")

    with st.chat_message("user"):
        st.markdown(question)

    # Clear the draft for the next rerun/input instance.
    st.session_state.chat_draft = ""
    st.session_state.chat_input_version += 1

    # --------------------------------------------------------------
    # AI response
    # --------------------------------------------------------------
    try:
        with st.chat_message("assistant"):
            typing_placeholder = st.empty()

            typing_placeholder.markdown(
                _typing_html(lang),
                unsafe_allow_html=True,
            )

            answer = ask_chart_question(
                context,
                previous_history,
                question,
                language,
                user_id=user_id,
                thread_id=thread_id,
            )

            typing_placeholder.empty()

            if answer is None:
                st.info(t("chat_unavailable", lang))
                return

            st.write_stream(_stream_answer(answer))

    except Exception as exc:
        logger.exception("AI chat request failed")
        st.error(
            f"{t('chat_error', lang)} "
            f"({type(exc).__name__}: {exc})"
        )
        return

    # --------------------------------------------------------------
    # Persist AI response
    # --------------------------------------------------------------
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": answer}
    )

    if store and thread_id:
        try:
            store.append_message(
                user_id,
                thread_id,
                "assistant",
                answer,
                turn_id=turn_id,
            )
        except Exception:
            logger.exception("Could not persist assistant chat message")

    st.rerun()
