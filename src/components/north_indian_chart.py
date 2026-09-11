"""D1 wrapper around the reusable North Indian divisional chart renderer."""

from src.components.divisional_chart import (
    PLANET_ABBREVIATIONS,
    build_divisional_svg,
    map_house_contents,
    render_divisional_chart,
)
from src.models import KundaliChart
from src.localization.translations import planet_name, t


def _placements(chart: KundaliChart, lang: str):
    for planet in chart.planets:
        label = PLANET_ABBREVIATIONS[planet.name] if lang == "en" else planet_name(planet.name, lang)
        yield planet.name, planet.house, f"{label} {planet.degree_dms}"


def house_chart_data(chart: KundaliChart, lang: str = "en") -> dict[int, dict[str, object]]:
    return map_house_contents(chart.houses, _placements(chart, lang), lang)


def build_chart_svg(chart: KundaliChart, lang: str = "en") -> str:
    return build_divisional_svg(chart.houses, _placements(chart, lang), t("lagna", lang), "#5b3975", lang)


def render_north_indian_chart(chart: KundaliChart, lang: str = "en") -> None:
    render_divisional_chart(chart.houses, _placements(chart, lang), t("lagna", lang), "#5b3975", lang)
