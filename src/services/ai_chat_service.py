"""Interactive AI chat service backed by deterministic Kundali context."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()

# Keep this configurable so local and Streamlit Cloud can use the same code.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


SYSTEM_PROMPT = """
You are an interactive Vedic astrology assistant inside a Kundali application.

You receive:
1. Deterministically calculated Kundali/chart facts.
2. Previous conversation history from the application's canonical transcript.
3. The user's latest message.

GROUNDING
- Use ONLY the supplied chart context for astrological facts.
- Never invent planetary placements, houses, dashas, antardashas,
  divisional-chart positions, yogas, dates, nakshatras, degrees, or aspects.
- If required chart information is unavailable, say so clearly.
- Astrology timing is interpretive, not guaranteed.

INTERACTIVE BEHAVIOR
- Read the previous conversation before answering.
- If the user's question is broad and ONE missing real-world detail would
  materially improve the answer, ask exactly ONE short follow-up question.
- Do not ask a follow-up if the answer is already present in history.
- Do not repeat a clarification already answered.
- If the previous assistant message asked a clarification and the latest user
  message answers it, answer the ORIGINAL user intent using that new context.
- Do not turn the conversation into a questionnaire.
- Once enough context exists, provide the answer instead of asking more
  questions.
- Direct questions that can be answered from chart context should be answered
  directly.

LANGUAGE
- Hindi / Devanagari user -> natural Hindi.
- Roman-script Hindi/Hinglish user -> natural Hinglish.
- English user -> English.
- Keep astrology terms such as Mahadasha, Antardasha, D10, Navamsa, Lagna,
  Rahu, etc. where appropriate.

STYLE
- Start with the most useful conclusion.
- Explain the chart facts supporting it.
- For timing questions, describe stronger/weaker windows rather than certainty.
- Avoid claims such as "100% job lagegi".
"""


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_HINGLISH_MARKERS = {
    "kya", "kab", "kaise", "mera", "meri", "mere", "mujhe", "hai", "hain",
    "hoga", "hogi", "lagegi", "milega", "job", "naukri", "shaadi", "paisa",
    "career", "batao", "bata", "raha", "rahi", "abhi", "tak", "chance",
    "chances", "kyun", "nahi", "haan", "ha", "interview", "offer",
}


def chat_is_available() -> bool:
    """Return True when OpenAI chat can be used."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=api_key)


def detect_language(text: str, fallback: str = "en") -> str:
    """Return 'hi', 'hinglish', or 'en'."""
    text = (text or "").strip()

    if not text:
        return "hi" if fallback == "hi" else "en"

    if _DEVANAGARI_RE.search(text):
        return "hi"

    words = set(re.findall(r"[A-Za-z]+", text.lower()))
    if words.intersection(_HINGLISH_MARKERS):
        return "hinglish"

    return "hi" if fallback == "hi" else "en"


def _to_serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Mapping):
        return {
            str(key): _to_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_to_serializable(item) for item in value]

    if hasattr(value, "model_dump"):
        try:
            return _to_serializable(value.model_dump())
        except Exception:
            logger.debug("model_dump failed", exc_info=True)

    if hasattr(value, "__dict__"):
        try:
            return {
                key: _to_serializable(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        except Exception:
            logger.debug("__dict__ serialization failed", exc_info=True)

    return str(value)


def build_chat_context(chart: Any, details: Any) -> str:
    """Serialize already-calculated Kundali facts for grounded AI use."""
    payload = {
        "birth_details": _to_serializable(details),
        "calculated_chart": _to_serializable(chart),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def _normalize_history(
    history: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []

    for item in history or []:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()

        if role not in {"user", "assistant"} or not content:
            continue

        normalized.append({"role": role, "content": content})

    return normalized


def _language_instruction(language: str) -> str:
    if language == "hi":
        return "Respond naturally in Hindi using Devanagari."
    if language == "hinglish":
        return "Respond naturally in conversational Hinglish."
    return "Respond in English."


def _build_messages(
    context: str,
    history: Sequence[Mapping[str, Any]] | None,
    question: str,
    language: str,
) -> list[dict[str, str]]:
    """Build the canonical model input from chart + UI transcript."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _language_instruction(language)},
        {
            "role": "system",
            "content": (
                "CHART CONTEXT\n"
                "This is deterministic application output and is the source of "
                "truth for all astrological facts:\n\n"
                f"{context}"
            ),
        },
    ]

    messages.extend(_normalize_history(history))
    messages.append({"role": "user", "content": question})
    return messages


def _invoke_openai(
    client: OpenAI,
    messages: list[dict[str, str]],
) -> str:
    """Call OpenAI and return assistant text."""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.4,
    )

    if not response.choices:
        raise RuntimeError("OpenAI returned no choices.")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response.")

    return content.strip()


def _invoke_with_langgraph(
    *,
    database_url: str,
    thread_id: str,
    question: str,
    model_messages: list[dict[str, str]],
    client: OpenAI,
) -> str:
    """Run one turn through LangGraph without duplicating chat transcript.

    The graph receives only the latest user question as graph input.
    Full conversational context comes from the canonical UI transcript and is
    supplied to the model through this request's closure.

    The PostgreSQL checkpointer therefore stores agent execution state, not a
    second copy of the full UI conversation.
    """
    from typing_extensions import TypedDict
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.graph import END, START, StateGraph

    class ExecutionState(TypedDict, total=False):
        question: str
        answer: str

    def assistant_node(state: ExecutionState) -> ExecutionState:
        # state["question"] is the latest graph input. model_messages already
        # contains the canonical history + the same latest question.
        answer = _invoke_openai(client, model_messages)
        return {"answer": answer}

    builder = StateGraph(ExecutionState)
    builder.add_node("assistant", assistant_node)
    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", END)

    config = {
        "configurable": {
            "thread_id": str(thread_id),
            # A namespace prevents old checkpoint formats from interfering
            # with this execution-state-only graph design.
            "checkpoint_ns": "kundali-agent-v2",
        }
    }

    with PostgresSaver.from_conn_string(database_url) as checkpointer:
        # setup() is idempotent and creates LangGraph checkpoint tables.
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)

        result = graph.invoke(
            {"question": question},
            config=config,
        )

    answer = str(result.get("answer", "")).strip()
    if not answer:
        raise RuntimeError("LangGraph returned an empty assistant response.")

    return answer


def ask_chart_question(
    context: str,
    history: Sequence[Mapping[str, Any]] | None,
    question: str,
    language: str,
    *,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> str | None:
    """Answer one interactive Kundali question.

    Canonical conversation history comes from the UI/chat_messages table.
    LangGraph checkpointing is optional and never acts as a second transcript.
    """
    del user_id  # Reserved for future user-scoped agent configuration.

    question = (question or "").strip()
    if not question or not chat_is_available():
        return None

    client = _get_openai_client()

    model_messages = _build_messages(
        context=context,
        history=history,
        question=question,
        language=language,
    )

    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url and thread_id:
        try:
            return _invoke_with_langgraph(
                database_url=database_url,
                thread_id=str(thread_id),
                question=question,
                model_messages=model_messages,
                client=client,
            )
        except Exception:
            # Persistent agent execution state should never make chat unusable.
            logger.exception(
                "LangGraph/PostgreSQL execution failed; falling back to "
                "direct OpenAI invocation."
            )

    return _invoke_openai(
        client=client,
        messages=model_messages,
    )
