"""Reusable North Indian diamond-chart renderer for deterministic divisional charts."""

from html import escape
from typing import Iterable

import streamlit.components.v1 as components

from src.models import House
from src.localization.translations import planet_name, sign_name, t

HOUSE_CENTERS = {1: (300, 205), 2: (165, 115), 3: (80, 205), 4: (165, 390), 5: (300, 480), 6: (435, 390), 7: (520, 300), 8: (435, 205), 9: (300, 115), 10: (165, 300), 11: (300, 390), 12: (435, 300)}
PLANET_ABBREVIATIONS = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}


def map_house_contents(houses: tuple[House, ...], placements: Iterable[tuple[str, int]], lang: str = "en") -> dict[int, dict[str, object]]:
    """Map existing planet-house assignments to visual cells without calculations."""
    planets = {number: [] for number in range(1, 13)}
    for name, house in placements:
        planets[house].append(PLANET_ABBREVIATIONS[name] if lang == "en" else planet_name(name, lang))
    return {house.number: {"sign": sign_name(house.sign, lang), "planets": tuple(planets[house.number]), "lagna": house.number == 1} for house in houses}


def build_divisional_svg(houses: tuple[House, ...], placements: Iterable[tuple[str, int]], lagna_label: str, accent: str, lang: str = "en") -> str:
    """Build one reusable SVG layout for D1, D9, or D10."""
    cells = map_house_contents(houses, placements, lang)
    labels = []
    for number, (x, y) in HOUSE_CENTERS.items():
        cell = cells[number]
        lagna = f'<text x="{x}" y="{y + 4}" class="lagna">{escape(lagna_label)}</text>' if cell["lagna"] else ""
        labels.append(f'<text x="{x}" y="{y - 32}" class="number">{number}</text><text x="{x}" y="{y - 14}" class="house">{escape(str(cell["sign"]))}</text>{lagna}<text x="{x}" y="{y + 24}" class="planets">{escape(", ".join(cell["planets"]) or "-")}</text>')
    svg = f'''<div class="chart-shell"><svg viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="North Indian divisional chart">
      <style>.line{{stroke:{accent};stroke-width:2;fill:none}}.number{{font:600 11px sans-serif;fill:#6b7280;text-anchor:middle}}.house{{font:700 14px sans-serif;fill:{accent};text-anchor:middle}}.lagna{{font:700 11px sans-serif;fill:#b45309;text-anchor:middle}}.planets{{font:12px sans-serif;fill:#111827;text-anchor:middle}}@media(max-width:600px){{.house{{font-size:12px}}.planets{{font-size:10px}}}}</style>
      <rect x="18" y="18" width="564" height="564" class="line"/><path d="M18 18 L300 300 L582 18 M582 582 L300 300 L18 582 M18 300 L300 18 L582 300 L300 582 Z M18 18 L300 300 L582 582 M582 18 L300 300 L18 582" class="line"/>{''.join(labels)}</svg>'''
    return svg + "</div><style>.chart-shell{max-width:700px;width:100%;margin:0 auto;padding:12px;box-sizing:border-box}.chart-shell svg{display:block;width:100%;height:auto}@media(max-width:900px){.chart-shell{max-width:600px}}@media(max-width:600px){.chart-shell{max-width:100%;padding:4px}}</style>"


def render_divisional_chart(houses: tuple[House, ...], placements: Iterable[tuple[str, int]], lagna_label: str, accent: str = "#174b68", lang: str = "en") -> None:
    components.html(build_divisional_svg(houses, placements, lagna_label, accent, lang), height=650, scrolling=False)
