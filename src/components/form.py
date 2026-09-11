"""Birth-details form component."""

from datetime import date, time

import streamlit as st

from src.models import BirthDetails
from src.localization.translations import t
from src.services.birth_data_service import normalize_birth_data
from src.validators import ALLOWED_GENDERS, validate_birth_details


def render_birth_details_form(lang: str = "en") -> tuple[bool, BirthDetails | None]:
    """Render the form and return validated details after submission."""
    defaults = {
        "birth_name": "Gaurav Gupta",
        "birth_day": 22,
        "birth_month": 3,
        "birth_year": 1987,
        "birth_time": time(1, 45),
        "birth_gender": "Male",
        "birth_place": "Delhi",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    with st.form("birth_details_form"):
        name = st.text_input(t("name", lang), max_chars=80, placeholder="e.g., Aditi Sharma", key="birth_name")
        st.markdown(f"**{t('dob', lang)}**")
        day_column, month_column, year_column = st.columns(3)
        with day_column:
            day = st.selectbox(t("day", lang), options=list(range(1, 32)), key="birth_day")
        with month_column:
            month_labels = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December") if lang == "en" else ("जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर")
            month = st.selectbox(t("month", lang), options=list(range(1, 13)), format_func=lambda value: month_labels[value - 1], key="birth_month")
        with year_column:
            years = list(range(date.today().year, 1899, -1))
            year = st.selectbox(t("year", lang), options=years, key="birth_year")
        time_of_birth = st.time_input(t("time", lang), key="birth_time")
        gender_labels = {t("female", lang): "Female", t("male", lang): "Male", t("non_binary", lang): "Non-binary", t("prefer_not", lang): "Prefer not to say"}
        gender = st.selectbox(t("gender", lang), options=["Female", "Male", "Non-binary", "Prefer not to say"], format_func=lambda value: next(label for label, internal in gender_labels.items() if internal == value), key="birth_gender")
        place_of_birth = st.text_input(
            t("place", lang), max_chars=120, placeholder="e.g., Jaipur, Rajasthan, India", key="birth_place"
        )
        submitted = st.form_submit_button(t("generate", lang), use_container_width=True)

    if not submitted:
        return False, None

    if time_of_birth is None:
        st.error(t("invalid_time", lang))
        return True, None

    try:
        details = normalize_birth_data(name, day, month, year, time_of_birth, gender, place_of_birth)
    except ValueError:
        st.error(t("invalid_date", lang, day=day, month=month_labels[month - 1], year=year))
        return True, None

    errors = validate_birth_details(details, lang)
    if errors:
        for error in errors:
            st.error(error)
        return True, None

    return True, details
