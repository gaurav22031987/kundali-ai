"""OpenAI-backed interpretation of already-calculated chart facts only."""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import KundaliChart
from src.services.chart_serializer import chart_to_payload

load_dotenv()

SYSTEM_INSTRUCTIONS = """You are a careful Vedic-astrology interpreter. The supplied JSON is the complete,
authoritative calculation output. Do not calculate, correct, infer, or invent planetary longitudes, signs,
houses, Nakshatras, Padas, or dasha dates. Do not present new astrological facts as calculated data.
Use only the supplied facts to give reflective, non-deterministic interpretations. Avoid medical, legal,
or financial advice. Write concise Markdown with exactly these headings: Personality, Career, Finance,
Marriage, Health, Education, Foreign Travel, Current Mahadasha / Antardasha, Next 12 months overview.
Inside Career include short subsections: Career strengths, Suitable profession themes, Leadership vs technical orientation,
Job vs business tendencies, Career challenges, Career growth periods, Current Dasha career context, and Next 12 months career overview.
Present all future-oriented statements as astrology-based possibilities, never guarantees."""


def build_interpretation_prompt(chart: KundaliChart, lang: str = "en") -> str:
    """Build a transparent structured-data prompt without calculating any chart values."""
    payload = json.dumps({"language": lang, "chart_data": chart_to_payload(chart)}, indent=2, sort_keys=True)
    language_instruction = (
        "Respond entirely in natural Hindi using Devanagari script. Do not use English except for unavoidable technical abbreviations such as D1, D9 and D10."
        if lang == "hi" else "Respond entirely in English."
    )
    return f"{language_instruction}\nInterpret only this deterministic chart JSON:\n```json\n{payload}\n```"


def get_ai_interpretation(chart: KundaliChart, lang: str = "en") -> str | None:
    """Request a narrative interpretation, or return None when no key is configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    client = OpenAI(api_key=api_key)
    language_heading_rule = (
        " Use Hindi Devanagari headings and prose throughout, retaining only D1, D9, and D10 abbreviations in English."
        if lang == "hi" else " Use English headings and prose throughout."
    )
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=SYSTEM_INSTRUCTIONS + language_heading_rule,
        input=build_interpretation_prompt(chart, lang),
        store=False,
    )
    return response.output_text
