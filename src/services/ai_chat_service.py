"""Chart-grounded OpenAI chat service; it never calculates astrology data."""

import json
import os
from datetime import date

from dotenv import load_dotenv
from openai import OpenAI

from src.models import BirthDetails, KundaliChart
from src.services.chart_serializer import chart_to_payload
from src.services.chat_persistence_service import configured_user_id, get_chat_store

load_dotenv()

CHAT_SYSTEM_PROMPT = """You are a Vedic astrology interpretation assistant. Use only the provided calculated Kundali data.
Do not invent or recalculate planetary positions, house placements, dashas, dates, Nakshatras, Lagna, or D1/D9/D10 placements.
If a requested fact is not in the context, state that it is unavailable. Clearly distinguish supplied deterministic chart facts from astrology-based interpretation.
Present future-oriented content as reflective guidance, never guaranteed future events. Do not give medical, legal, or financial advice."""
HINGLISH_WORDS = {"hai", "mera", "meri", "kab", "kya", "kaise", "kundli", "naukri", "shaadi", "career", "job", "mujhe", "aap", "meri"}


def detect_language(message: str, fallback: str = "en") -> str:
    """Detect Hindi/Devanagari or common Hinglish before falling back to UI language."""
    if any("\u0900" <= character <= "\u097f" for character in message):
        return "hi"
    words = {word.strip(".,?!:;'").lower() for word in message.split()}
    return "hi" if words & HINGLISH_WORDS else fallback


def build_chat_context(chart: KundaliChart | None, details: BirthDetails | None) -> dict | None:
    """Create the complete JSON-safe context passed to chat from existing chart results."""
    if chart is None or details is None:
        return None
    payload = chart_to_payload(chart)
    return {
        "birth_details": {"name": details.name, "date_of_birth": details.date_of_birth.isoformat(), "time_of_birth": details.time_of_birth.isoformat(), "place_of_birth": details.place_of_birth},
        "d1": {"lagna": payload["lagna"], "houses": payload["houses"]},
        "d9": payload["navamsa"],
        "d10": payload["dashamsa"],
        "planetary_positions": payload["planets"],
        "vimshottari_dasha": {"timeline": [{"lord": period.lord, "start": period.start.isoformat(), "end": period.end.isoformat()} for period in chart.mahadashas]},
        "current_dasha": payload["current_dasha"],
        "current_date": date.today().isoformat(),
    }


def build_chat_prompt(context: dict | None, history: list[dict[str, str]], question: str, lang: str, retrieved_memories: list[str] | None = None) -> str:
    """Build a language-specific prompt containing only local session history and facts."""
    if context is None:
        raise ValueError("A generated Kundali is required before chat can answer.")
    language_rule = "Respond entirely in natural Hindi using Devanagari script; retain only D1, D9, and D10 abbreviations in English." if lang == "hi" else "Respond entirely in English."
    transcript = history[-12:]
    return f"{language_rule}\nDeterministic chart context:\n{json.dumps(context, ensure_ascii=False, sort_keys=True)}\nRelevant older conversations for this same user:\n{json.dumps(retrieved_memories or [], ensure_ascii=False)}\nConversation history:\n{json.dumps(transcript, ensure_ascii=False)}\nUser question:\n{question}"


def chat_is_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _embed(client: OpenAI, text: str) -> list[float]:
    return client.embeddings.create(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=text).data[0].embedding


def _invoke_with_langgraph(database_url: str, thread_id: str, prompt: str, client: OpenAI) -> str:
    """Run an OpenAI answer node with PostgreSQL-backed LangGraph checkpoints."""
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.graph import START, MessagesState, StateGraph

    def answer_node(_: MessagesState) -> dict:
        response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), instructions=CHAT_SYSTEM_PROMPT, input=prompt, store=False)
        return {"messages": [AIMessage(response.output_text)]}

    builder = StateGraph(MessagesState)
    builder.add_node("answer", answer_node)
    builder.add_edge(START, "answer")
    with PostgresSaver.from_conn_string(database_url) as checkpointer:
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)
        result = graph.invoke({"messages": [HumanMessage(prompt)]}, {"configurable": {"thread_id": thread_id}})
    return result["messages"][-1].content


def ask_chart_question(context: dict | None, history: list[dict[str, str]], question: str, lang: str, user_id: str | None = None, thread_id: str | None = None) -> str | None:
    """Return an answer from OpenAI, or None if no API key is configured."""
    if not chat_is_available():
        return None
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response_lang = detect_language(question, lang)
    store = get_chat_store()
    active_user = user_id or configured_user_id()
    retrieved: list[str] = []
    question_embedding: list[float] | None = None
    if store and thread_id:
        store.setup()
        question_embedding = _embed(client, question)
        retrieved = store.retrieve_memories(active_user, question_embedding, thread_id)
    prompt = build_chat_prompt(context, history, question, response_lang, retrieved)
    if store and thread_id:
        answer = _invoke_with_langgraph(store.database_url, thread_id, prompt, client)
        store.save_message(active_user, thread_id, "user", question, question_embedding)
        answer_embedding = _embed(client, answer)
        store.save_message(active_user, thread_id, "assistant", answer, answer_embedding)
        store.save_memory(active_user, thread_id, f"User: {question}\nAssistant: {answer}", _embed(client, f"User: {question}\nAssistant: {answer}"))
        return answer
    response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), instructions=CHAT_SYSTEM_PROMPT, input=prompt, store=False)
    return response.output_text
