# Kundali AI

A Streamlit Vedic-astrology application that deterministically calculates a sidereal birth chart. It uses Swiss Ephemeris (`pyswisseph`) with Lahiri Ayanamsa, whole-sign houses, and Vimshottari dasha calculations.

## Language selector

Use the sidebar **Language** selector to switch between English and हिंदी. The choice remains in the Streamlit session across tabs. It changes only presentation and AI response language; all Swiss Ephemeris, D1, D9, D10, and dasha calculations retain the same deterministic values.

Birth input is normalized into canonical Python `date`/`time` values and English internal enums before it reaches the calculation engine. Hindi is used only at the presentation layer.

The selected language is stored as one Streamlit session preference and mirrored in the `lang` URL query parameter, so it remains selected after form submission, navigation, component reruns, and browser refreshes of that URL.

## AI Chat

After generating a Kundali, use the **AI Chat / AI चैट** tab to ask chart-specific questions. The current Streamlit session keeps the chat transcript until it is cleared or a new Kundali is generated. Each answer receives structured, deterministic D1/D9/D10 and dasha context; the AI is instructed not to calculate or invent astrological facts.

## Persistent chat, LangGraph, and pgvector

Set `DATABASE_URL` to a PostgreSQL database where the `pgvector` extension can be created, and set `KUNDALI_USER_ID` to your authenticated application user ID. The app then stores conversations and messages durably, uses the conversation UUID as the LangGraph `thread_id`, and retrieves the most relevant memories from that user's older conversations using pgvector cosine similarity. **New Chat** creates a separate thread; retrieval remains restricted to the same `KUNDALI_USER_ID`. Without `DATABASE_URL`, chat continues as session-only and shows a setup note.

## Features

- Converts Place of Birth to latitude, longitude, and an IANA timezone via OpenStreetMap/Nominatim and `timezonefinder`.
- Converts the entered local birth time to UTC before calling Swiss Ephemeris.
- Calculates sidereal Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu (true node), Ketu, Lagna, 12 houses, Nakshatra, Pada, and a complete 120-year Vimshottari Mahadasha timeline with every Antardasha.
- Shows planetary and house tables and life-area study prompts for career, finance, marriage, health, and education.
- Includes a North Indian diamond-style chart and an optional OpenAI interpretation tab. The AI receives calculated JSON facts only and cannot calculate chart data.
- Includes a North Indian Navamsa (D9) chart, D1/D9 comparisons, and Vargottama detection.
- Includes a North Indian Dashamsa (D10) chart with deterministic career-analysis data.

## Navamsa (D9) methodology

The D9 service derives each placement from the already-calculated Lahiri sidereal D1 longitude. A sign is divided into nine equal parts of 3 degrees 20 minutes. Movable signs begin their Navamsa sequence from the same sign, fixed signs from the ninth sign, and dual signs from the fifth sign. D9 houses use the derived Navamsa Lagna with whole-sign houses. A planet is marked Vargottama only when its deterministic D1 and D9 signs are identical.

## Dashamsa (D10) methodology

The D10 service also starts with the existing Lahiri sidereal D1 longitude. Each sign is divided into ten exact 3-degree parts. For odd-numbered zodiac signs, the first Dashamsa starts from that sign; for even-numbered signs, it starts from the ninth sign. Subsequent divisions proceed zodiacally. D10 Lagna and whole-sign houses are then derived from the same deterministic rule. Career data is a structured summary of D1/D10 tenth-house facts and current dasha lords; it is not an AI calculation.

## Calculation boundaries

`src/services/vedic_calculator.py` is the sole astronomical/dasha calculation module. `src/services/interpretation_service.py` receives only a completed chart and never calculates or fabricates positions or dasha dates. No LLM is used for these calculations.

## Install and run (PowerShell)

```powershell
cd "D:\Kundali\codex ai"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Enter a specific place, for example `Jaipur, Rajasthan, India`. Place lookup requires an internet connection.

### Streamlit Cloud geocoding

Birthplace lookup uses OpenStreetMap Nominatim through `geopy`, then resolves an IANA timezone with `timezonefinder`. In Streamlit Community Cloud, configure `GEOCODER_USER_AGENT` in **Secrets** with an identifiable application name and contact URL/email, and optionally `GEOCODER_TIMEOUT`. Provider failures are logged with the original exception traceback in Cloud logs. Delhi remains a built-in fallback, alongside several common Indian cities, if Nominatim is temporarily unavailable.

## Optional AI interpretation

Copy `.env.example` to `.env`, then set `OPENAI_API_KEY` to use the AI Interpretation tab. The application uses the official OpenAI Python SDK and sends a structured copy of the calculated chart. If no key is configured, the tab stays available and shows a setup message.

## Test

With the virtual environment active, run:

```powershell
python -m pytest tests -p no:cacheprovider
```

The tests use fixed New Delhi coordinates, so they do not call the geocoding provider.
