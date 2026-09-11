"""Responsive Streamlit presentation layer for deterministic Kundali calculations."""

from html import escape

import logging

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


def inject_styles() -> None:
    st.markdown("""<style>
    .stApp { background: #f7f8fc; }
    [data-testid="stAppViewContainer"] > .main { max-width: 1300px; margin: 0 auto; }
    .block-container { padding-top: 1.3rem; padding-bottom: 2.5rem; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e9eaf2; }
    [data-testid="stSidebar"] .block-container { padding-top: 1rem; }
    .hero { background: linear-gradient(135deg,#3d2157,#734a92); color:#fff; border-radius:20px; padding:24px 30px; box-shadow:0 10px 26px rgba(54,25,79,.16); margin-bottom:22px; }
    .hero h1 { margin:0; font-size:2rem; }.hero p { margin:7px 0 0; opacity:.9; }
    .summary-card { background:#fff; border:1px solid #ececf3; border-radius:16px; padding:18px; box-shadow:0 4px 14px rgba(31,35,51,.06); height:100%; box-sizing:border-box; }
    .summary-card .label { color:#6b7280; font-size:.78rem; margin-bottom:5px; }.summary-card .value { color:#1f2937; font-weight:700; font-size:1rem; overflow-wrap:anywhere; }
    div[data-testid="stTabs"] [role="tablist"] { overflow-x:auto; flex-wrap:nowrap; scrollbar-width:thin; } div[data-testid="stTabs"] button { font-weight:600; white-space:nowrap; } div[data-testid="stTabs"] button[aria-selected="true"] { color:#8a5900; border-color:#d6a11c; }.stButton > button { border-radius:10px; font-weight:700; min-height:44px; }
    [data-testid="stSidebar"] .stButton > button { background:#5d337a; color:#fff; border:0; }
    [data-testid="stSidebar"] .stButton > button:hover { background:#44245c; color:#fff; }
    [data-testid="stDataFrame"] { border:1px solid #e7e8ef; border-radius:12px; overflow:hidden; }
    @media (max-width:900px) { .block-container { padding-left:1rem; padding-right:1rem; }.hero { padding:20px; }.hero h1 { font-size:1.7rem; } }
    @media (max-width:600px) { .block-container { padding-top:.75rem; padding-left:.7rem; padding-right:.7rem; }.hero { border-radius:14px; padding:17px; }.hero h1 { font-size:1.4rem; }.hero p { font-size:.9rem; }.summary-card { padding:13px; margin-bottom:8px; } }
    </style>""", unsafe_allow_html=True)


def render_header(lang: str) -> None:
    st.markdown(f'<section class="hero"><h1>✦ {escape(t("app_title", lang))}</h1><p>{escape(t("app_subtitle", lang))}</p></section>', unsafe_allow_html=True)


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
    rows = [{t("planet", lang): planet_name(p.name, lang), t("sign", lang): sign_name(p.sign, lang), t("house", lang): p.house, t("degree", lang): f"{p.degree_in_sign:.2f}", t("nakshatra", lang): nakshatra_name(p.nakshatra, lang)} for p in chart.planets]
    if not compact:
        for row, planet in zip(rows, chart.planets):
            row[t("longitude", lang)] = f"{planet.longitude:.2f}"
            row[t("pada", lang)] = planet.pada
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_lagna_chart(chart, lang: str) -> None:
    with st.container(border=True):
        st.subheader(t("d1_heading", lang))
        st.caption(t("d1_caption", lang))
        layout = st.radio(t("charts", lang), ["north", "south"], index=0, horizontal=True, format_func=lambda value: t("north_indian" if value == "north" else "south_indian", lang), key="chart_layout")
        if layout == "north": render_north_indian_chart(chart, lang)
        else: render_south_indian_chart(chart, lang)
    st.subheader(t("planet_details", lang))
    sign_tab, nakshatra_tab = st.tabs([t("sign_details", lang), t("nakshatra_details", lang)])
    with sign_tab:
        st.dataframe([{t("planet", lang): planet_name(p.name, lang), t("sign", lang): sign_name(p.sign, lang), t("degree", lang): f"{p.degree_in_sign:.2f}", t("house", lang): p.house, t("retrograde", lang): t("no", lang)} for p in chart.planets], use_container_width=True, hide_index=True)
    with nakshatra_tab:
        st.dataframe([{t("planet", lang): planet_name(p.name, lang), t("nakshatra", lang): nakshatra_name(p.nakshatra, lang), t("pada", lang): p.pada, t("house", lang): p.house} for p in chart.planets], use_container_width=True, hide_index=True)


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
    st.set_page_config(page_title="Kundali AI", page_icon="K", layout="wide", initial_sidebar_state="expanded")
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
