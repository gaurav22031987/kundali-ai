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
    """Apply production-style responsive layout and hide Streamlit chrome."""
    st.markdown(
        """
        <style>
        /* ---------------------------------
           PRODUCTION / WHITE-LABEL CHROME
           --------------------------------- */
        #MainMenu,
        footer,
        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"],
        [data-testid="stHeaderActionElements"],
        button[data-testid="stBaseButton-header"],
        button[data-testid="stBaseButton-headerNoPadding"],
        .stDeployButton,
        div[class*="viewerBadge"],
        div[class*="ViewerBadge"],
        a[href*="share.streamlit.io"],
        a[href*="github.com"][target="_blank"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* Remove reserved header space after hiding Streamlit header. */
        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
        }

        html, body, [class*="css"] {
            font-family:
                Inter,
                "Segoe UI",
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                sans-serif !important;
        }

        .block-container {
            max-width: 1500px;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }

        /* ---------------------------------
           LEFT CONTROL PANEL
           --------------------------------- */
        div[data-testid="stForm"] {
            border-radius: 16px !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stTimeInput"] input {
            border-radius: 10px !important;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 11px !important;
            font-weight: 600 !important;
            min-height: 44px !important;
        }

        /* ---------------------------------
           ASTROJIVAN BRAND HEADER
           --------------------------------- */
        .astrojivan-header {
            min-height: 126px;
            display: flex;
            align-items: stretch;
            overflow: hidden;
            background: linear-gradient(135deg, #2f1648, #643d7d);
            color: #fff;
            border-radius: 18px;
            box-shadow: 0 10px 26px rgba(54, 25, 79, .16);
            margin-bottom: 22px;
        }

        .astrojivan-header-image {
            width: 156px;
            flex: 0 0 156px;
            border-right: 2px solid rgba(216, 169, 51, .72);
            background: #241137;
        }

        .astrojivan-header-image img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
            object-position: center;
        }

        .astrojivan-header-copy {
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 20px 28px;
            min-width: 0;
        }

        .astrojivan-header-copy h1 {
            margin: 0;
            color: #f4cf71;
            font-size: 2rem;
            line-height: 1.1;
        }

        .astrojivan-header-copy p {
            margin: 8px 0 0;
            color: rgba(255, 255, 255, .9);
            font-size: 1rem;
        }

        /* ---------------------------------
           BIRTH DETAILS TOGGLE
           --------------------------------- */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(100, 61, 125, .18) !important;
            border-radius: 14px !important;
            overflow: hidden !important;
            background: rgba(100, 61, 125, .025) !important;
        }

        div[data-testid="stExpander"] details > summary {
            font-weight: 700 !important;
            font-size: 1rem !important;
            min-height: 48px !important;
            padding: 0 .2rem !important;
        }

        div[data-testid="stExpander"] details > summary:hover {
            color: #643d7d !important;
        }

        /* ---------------------------------
           MOBILE RESPONSIVE LAYOUT
           --------------------------------- */
        @media (max-width: 768px) {
            html, body {
                overflow-x: hidden !important;
            }

            .block-container {
                max-width: 100% !important;
                padding: .75rem .85rem 1.5rem .85rem !important;
            }

            /* Birth Details behaves like a compact mobile drawer/toggle. */
            div[data-testid="stExpander"] {
                border-radius: 12px !important;
                margin-bottom: .45rem !important;
            }

            div[data-testid="stExpander"] details > summary {
                min-height: 52px !important;
                font-size: 1.02rem !important;
                padding-left: .15rem !important;
                padding-right: .15rem !important;
            }

            /*
            All Streamlit columns become vertical on mobile.
            This makes the Birth Details panel appear above the main content
            and also prevents tiny DOB/chart columns.
            */
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: .7rem !important;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }

            /* Compact AstroJivan header on phone. */
            .astrojivan-header {
                min-height: 96px !important;
                height: 96px !important;
                border-radius: 14px !important;
                margin-bottom: 14px !important;
            }

            .astrojivan-header-image {
                width: 90px !important;
                height: 96px !important;
                flex: 0 0 90px !important;
            }

            .astrojivan-header-image img {
                height: 96px !important;
                max-height: 96px !important;
                object-fit: cover !important;
            }

            .astrojivan-header-copy {
                padding: 10px 12px !important;
            }

            .astrojivan-header-copy h1 {
                font-size: 1.35rem !important;
            }

            .astrojivan-header-copy p {
                margin-top: 4px !important;
                font-size: .78rem !important;
                line-height: 1.25 !important;
            }

            div[data-testid="stTextInput"] input,
            div[data-testid="stSelectbox"] > div,
            div[data-testid="stTimeInput"] input {
                min-height: 44px !important;
            }

            .stFormSubmitButton > button,
            .stButton > button {
                width: 100% !important;
                min-height: 46px !important;
            }

            h1 { font-size: 1.8rem !important; }
            h2 { font-size: 1.4rem !important; }
            h3 { font-size: 1.12rem !important; }

            /* Keep tabs scrollable instead of squeezing labels. */
            div[data-baseweb="tab-list"] {
                overflow-x: auto !important;
                scrollbar-width: none;
            }

            div[data-baseweb="tab-list"]::-webkit-scrollbar {
                display: none;
            }

            div[data-baseweb="tab"] {
                flex: 0 0 auto !important;
                white-space: nowrap !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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


def _initialize_language() -> None:
    if "language" not in st.session_state:
        st.session_state.language = normalize_language(st.query_params.get("lang"))
    if "language_selector" not in st.session_state:
        st.session_state.language_selector = st.session_state.language


def render_language_selector() -> str:
    current = st.session_state.language
    selected = st.selectbox(
        t("language", current), ["hi", "en"],
        format_func=lambda code: t("english" if code == "en" else "hindi", code),
        key="language_selector",
    )
    st.session_state.language = normalize_language(selected)
    if st.query_params.get("lang") != st.session_state.language:
        st.query_params["lang"] = st.session_state.language
    return st.session_state.language


def render_controls_panel() -> tuple[bool, object | None, str]:
    """Render language plus a collapsible Birth Details panel.

    The native Streamlit expander works on desktop and mobile and avoids
    duplicate widget keys. On mobile the user can collapse the form after
    entering details, leaving more room for the Kundali content.
    """
    _initialize_language()
    lang = render_language_selector()

    with st.expander(
        f"🧾 {t('birth_details', lang)}",
        expanded=True,
    ):
        submitted, details = render_birth_details_form(
            lang,
            compact=True,
        )

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
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    # Do not use st.sidebar for the Birth Details form.
    # On desktop this behaves like a left control panel; on mobile CSS stacks
    # the same panel above the AstroJivan content.
    controls_column, content_column = st.columns(
        [0.31, 0.69],
        gap="large",
    )

    with controls_column:
        with st.container(border=True):
            submitted, details, lang = render_controls_panel()

    with content_column:
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
                LOGGER.info(
                    "[Language] after Kundali generation: %s",
                    st.session_state.language,
                )
            except LocationResolutionError as error:
                LOGGER.exception("Kundali location resolution failed")
                st.error(t(str(error), lang))
            except Exception:
                LOGGER.exception("Kundali generation failed")
                st.error(t("unable_generate", lang))

        chart = st.session_state.get("chart")
        saved_details = st.session_state.get("birth_details")

        if chart is None or saved_details is None:
            st.info(t("generate_new", lang))
            return

        render_kundali_tabs(chart, saved_details, lang)


if __name__ == "__main__":
    main()
