"""Responsive Streamlit presentation layer for deterministic Kundali calculations."""

from html import escape
import base64
import logging
from pathlib import Path

import streamlit as st

from src.components.dashamsa_chart import render_dashamsa_chart
from src.components.ai_chat import render_ai_chat
from src.components.form import render_birth_details_form
from src.components.navamsa_chart import render_navamsa_chart
from src.components.north_indian_chart import render_north_indian_chart
from src.components.south_indian_chart import render_south_indian_chart
from src.localization.translations import nakshatra_name, planet_name, sign_name, t
from src.localization.language_state import normalize_language
from src.services.ai_interpretation_service import get_ai_interpretation
from src.services.career_analysis_service import build_career_analysis
from src.services.divisional_chart_service import d1_seventh_lord_d9_placement
from src.services.geocoding_service import LocationResolutionError
from src.services.interpretation_service import build_life_area_interpretations
from src.services.kundali_service import generate_kundali

LOGGER = logging.getLogger(__name__)
ASTROJIVAN_BANNER = Path(__file__).resolve().parent / "assets" / "astrojivan_banner.png"
def inject_styles() -> None:
    st.markdown(
    """
    <style>
    /* Hide Streamlit chrome */
    header[data-testid="stHeader"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    div[data-testid="stStatusWidget"] {
        display: none;
    }

    /* Better app spacing */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* Premium typography */
    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", system-ui, sans-serif;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }

    /* Input controls */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True)


def render_header(lang: str) -> None:
    """Render compact AstroJivan branding, with a text-only asset fallback."""
    image_markup = ""
    try:
        if ASTROJIVAN_BANNER.is_file():
            encoded_image = base64.b64encode(ASTROJIVAN_BANNER.read_bytes()).decode("ascii")
            image_markup = f'<div class="astrojivan-header-image"><img src="data:image/png;base64,{encoded_image}" alt="AstroJivan" /></div>'
        else:
            LOGGER.warning("AstroJivan banner is not available at %s", ASTROJIVAN_BANNER)
    except OSError:
        LOGGER.exception("Could not read AstroJivan banner; using text-only header")
    st.markdown(
        f'<section class="astrojivan-header">{image_markup}<div class="astrojivan-header-copy"><h1>AstroJivan</h1><p>Vedic Astrology • Kundali • AI Guidance</p></div></section>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, object | None, str]:
    if "language" not in st.session_state:
        st.session_state.language = normalize_language(st.query_params.get("lang"))
    if "language_selector" not in st.session_state:
        st.session_state.language_selector = st.session_state.language
    with st.sidebar:
        current = st.session_state.language
        selected = st.selectbox(
            t("language", current),
            ["hi", "en"],
            format_func=lambda code: t("english" if code == "en" else "hindi", code),
            key="language_selector",
        )
        st.session_state.language = normalize_language(selected)
        if st.query_params.get("lang") != st.session_state.language:
            st.query_params["lang"] = st.session_state.language
        lang = st.session_state.language
        st.markdown(f"### {t('birth_details', lang)}")
        submitted, details = render_birth_details_form(lang)
    return submitted, details, st.session_state.language


def _card(label: str, value: object) -> str:
    return f'<div class="summary-card"><div class="label">{escape(label)}</div><div class="value">{escape(str(value))}</div></div>'


def render_birth_summary(chart, details, lang: str) -> None:
    moon = next(planet for planet in chart.planets if planet.name == "Moon")
    st.subheader(t("birth_summary", lang))
    rows = [
        [(t("name", lang), details.name), (t("dob", lang), details.date_of_birth.strftime("%d-%m-%Y")), (t("birth_time", lang), details.time_of_birth.strftime("%I:%M %p"))],
        [(t("place", lang), chart.location.display_name), (t("lagna", lang), sign_name(chart.ascendant_sign, lang)), (t("moon_sign", lang), sign_name(chart.moon_sign, lang)), (t("nakshatra", lang), nakshatra_name(moon.nakshatra, lang))],
    ]
    for row in rows:
        columns = st.columns(len(row))
        for column, (label, value) in zip(columns, row):
            with column:
                st.markdown(_card(label, value), unsafe_allow_html=True)


def render_planet_table(chart, lang: str, compact: bool = False) -> None:
    rows = _d1_position_rows(chart, lang)
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _d1_position_rows(chart, lang: str) -> list[dict[str, object]]:
    """Presentation rows sourced exclusively from deterministic D1 fields."""
    columns = {
        "planet": t("planet", lang), "sign": t("sign", lang),
        "degree": t("degree", lang), "house": t("house", lang),
        "nakshatra": t("nakshatra", lang), "pada": t("pada", lang),
        "status": t("retrograde_direct", lang), "longitude": t("longitude", lang),
    }
    rows = [{
        columns["planet"]: t("lagna", lang),
        columns["sign"]: sign_name(chart.ascendant_sign, lang),
        columns["degree"]: chart.ascendant_degree_dms,
        columns["house"]: 1,
        columns["nakshatra"]: nakshatra_name(chart.ascendant_nakshatra, lang),
        columns["pada"]: chart.ascendant_pada,
        columns["status"]: "-",
        columns["longitude"]: f"{chart.ascendant_longitude:.6f}°",
    }]
    for planet in chart.planets:
        rows.append({
            columns["planet"]: planet_name(planet.name, lang),
            columns["sign"]: sign_name(planet.sign, lang),
            columns["degree"]: planet.degree_dms,
            columns["house"]: planet.house,
            columns["nakshatra"]: nakshatra_name(planet.nakshatra, lang),
            columns["pada"]: planet.pada,
            columns["status"]: t("retrograde" if planet.is_retrograde else "direct", lang),
            columns["longitude"]: f"{planet.longitude:.6f}°",
        })
    return rows


def render_lagna_chart(chart, lang: str) -> None:
    with st.container(border=True):
        st.subheader(t("d1_heading", lang))
        st.caption(t("d1_caption", lang))
        layout = st.radio(t("charts", lang), ["north", "south"], index=0, horizontal=True, format_func=lambda value: t("north_indian" if value == "north" else "south_indian", lang), key="chart_layout")
        if layout == "north": render_north_indian_chart(chart, lang)
        else: render_south_indian_chart(chart, lang)
    st.subheader(t("planetary_positions", lang))
    st.dataframe(_d1_position_rows(chart, lang), use_container_width=True, hide_index=True)


def render_dasha(chart, lang: str) -> None:
    st.subheader(t("current_dasha", lang))
    left, right = st.columns(2)
    left.info(f"**{t('mahadasha', lang)}**\n\n{planet_name(chart.current_mahadasha.lord, lang)}: {chart.current_mahadasha.start:%d %b %Y} - {chart.current_mahadasha.end:%d %b %Y}")
    right.info(f"**{t('antardasha', lang)}**\n\n{planet_name(chart.current_antardasha.lord, lang)}: {chart.current_antardasha.start:%d %b %Y} - {chart.current_antardasha.end:%d %b %Y}")
    st.subheader(t("timeline", lang))
    st.dataframe([{t("mahadasha", lang): planet_name(p.lord, lang), t("start_date", lang): p.start.strftime("%d %b %Y"), t("end_date", lang): p.end.strftime("%d %b %Y")} for p in chart.mahadashas], use_container_width=True, hide_index=True)
    for period in chart.mahadashas:
        with st.expander(t("antardasha_timeline", lang, lord=planet_name(period.lord, lang))):
            st.dataframe([{t("antardasha", lang): planet_name(p.lord, lang), t("start_date", lang): p.start.strftime("%d %b %Y"), t("end_date", lang): p.end.strftime("%d %b %Y")} for p in period.antardashas], use_container_width=True, hide_index=True)


def render_ai_analysis(chart, lang: str) -> None:
    st.caption(t("ai_caption", lang))
    if st.button(t("generate_ai", lang), type="primary"):
        try:
            with st.spinner(t("ai_loading", lang)):
                result = get_ai_interpretation(chart, lang)
        except Exception:
            st.error(t("ai_error", lang)); return
        if result is None: st.info(t("ai_setup", lang))
        else: st.session_state.ai_interpretation = result
    if st.session_state.get("ai_interpretation"): st.markdown(st.session_state.ai_interpretation)
    else:
        st.subheader(t("calculated_cues", lang))
        for area, reading in build_life_area_interpretations(chart).items():
            with st.expander(t(area.lower().replace(" ", "_"), lang)): st.write(reading)


def render_kundali_tabs(chart, details, lang: str) -> None:
    tabs = st.tabs([t(key, lang) for key in ("basic", "charts", "kp", "ashtakavarga", "dasha", "report", "chat_tab")])
    with tabs[0]: render_birth_summary(chart, details, lang)
    with tabs[1]:
        chart_tabs = st.tabs([t(key, lang) for key in ("lagna", "navamsa", "transit", "divisional")])
        with chart_tabs[0]: render_lagna_chart(chart, lang)
        with chart_tabs[1]:
            if chart.navamsa is None: st.error(t("d9_unavailable", lang))
            else:
                with st.container(border=True): st.subheader(t("d9_heading", lang)); st.caption(t("d9_caption", lang)); render_navamsa_chart(chart.navamsa, lang)
                st.dataframe([{t("planet", lang): planet_name(p.name, lang), t("d1_sign", lang): sign_name(p.d1_sign, lang), t("d9_sign", lang): sign_name(p.d9_sign, lang), t("d9_house", lang): p.d9_house} for p in chart.navamsa.positions], use_container_width=True, hide_index=True)
        with chart_tabs[2]: st.info(t("feature_unavailable", lang))
        with chart_tabs[3]:
            if chart.dashamsa is None: st.error(t("d10_unavailable", lang))
            else:
                with st.container(border=True): st.subheader(t("d10_heading", lang)); st.caption(t("d10_caption", lang)); render_dashamsa_chart(chart.dashamsa, lang)
                st.dataframe([{t("planet", lang): planet_name(p.name, lang), t("d1_sign", lang): sign_name(p.d1_sign, lang), t("d10_sign", lang): sign_name(p.sign, lang), t("d10_house", lang): p.house} for p in chart.dashamsa.positions], use_container_width=True, hide_index=True)
    with tabs[2]: st.info(t("feature_unavailable", lang))
    with tabs[3]: st.info(t("feature_unavailable", lang))
    with tabs[4]: render_dasha(chart, lang)
    with tabs[5]: render_ai_analysis(chart, lang)
    with tabs[6]: render_ai_chat(chart, details, lang)


def main() -> None:
    st.set_page_config(
    page_title="AstroJivan",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
    )
    inject_styles()
    submitted, details, lang = render_sidebar()
    render_header(lang)
    if submitted and details:
        try:
            LOGGER.info("[Language] before Kundali generation: %s", lang)
            with st.spinner(t("resolving", lang)):
                st.session_state.chart = generate_kundali(details)
                st.session_state.birth_details = details
                st.session_state.pop("ai_interpretation", None)
                st.session_state.chat_messages = []
                st.session_state.pop("chat_conversation_id", None)
                st.session_state.pop("chat_conversation_selector", None)
            LOGGER.info("[Language] after Kundali generation: %s", st.session_state.language)
        except LocationResolutionError as error:
            LOGGER.exception("Kundali location resolution failed")
            st.error(t(str(error), lang))
        except Exception:
            LOGGER.exception("Kundali generation failed")
            st.error(t("unable_generate", lang))
    chart = st.session_state.get("chart")
    details = st.session_state.get("birth_details")
    if chart is None or details is None:
        st.info(t("generate_new", lang)); return
    render_kundali_tabs(chart, details, lang)


if __name__ == "__main__":
    main()
