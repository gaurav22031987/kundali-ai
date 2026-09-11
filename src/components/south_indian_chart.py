"""Presentation-only South Indian D1 chart rendered from existing deterministic data."""

from html import escape

import streamlit.components.v1 as components

from src.localization.translations import planet_name, sign_name, t
from src.models import KundaliChart
from src.components.divisional_chart import PLANET_ABBREVIATIONS

SIGN_CELLS = {0: (1, 1), 1: (1, 2), 2: (1, 3), 3: (1, 4), 4: (2, 4), 5: (3, 4), 6: (4, 4), 7: (4, 3), 8: (4, 2), 9: (4, 1), 10: (3, 1), 11: (2, 1)}
SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")


def render_south_indian_chart(chart: KundaliChart, lang: str = "en") -> None:
    """Render signs and planet placements without recalculating their positions."""
    planets_by_sign: dict[str, list[str]] = {}
    for planet in chart.planets:
        label = PLANET_ABBREVIATIONS[planet.name] if lang == "en" else planet_name(planet.name, lang)
        planets_by_sign.setdefault(planet.sign, []).append(f"{label} {planet.degree_dms}")
    cells = []
    for index, (row, column) in SIGN_CELLS.items():
        sign = SIGNS[index]
        lagna = f'<span class="lagna">{escape(t("lagna", lang))}</span>' if sign == chart.ascendant_sign else ""
        planets = ", ".join(planets_by_sign.get(sign, [])) or "-"
        cells.append(f'<div class="cell" style="grid-row:{row};grid-column:{column}"><b>{escape(sign_name(sign, lang))}</b>{lagna}<small>{escape(planets)}</small></div>')
    html = f'''<div class="south-chart">{''.join(cells)}<div class="center">{escape(t("d1_heading", lang))}</div></div><style>.south-chart{{display:grid;grid-template:repeat(4,1fr)/repeat(4,1fr);max-width:700px;aspect-ratio:1;margin:auto;border:2px solid #5b3975;background:#fff}}.cell{{border:1px solid #cfc4d8;padding:8px;display:flex;flex-direction:column;gap:5px;font:14px sans-serif;color:#352042;overflow-wrap:anywhere}}.cell small{{font-size:12px;color:#111827}}.lagna{{color:#b45309;font-size:12px;font-weight:700}}.center{{grid-row:2/4;grid-column:2/4;display:grid;place-items:center;text-align:center;font:700 18px sans-serif;color:#5b3975;background:#faf7fc}}@media(max-width:600px){{.cell{{padding:4px;font-size:11px}}.cell small{{font-size:9px}}.center{{font-size:13px}}}}</style>'''
    components.html(html, height=650, scrolling=False)
