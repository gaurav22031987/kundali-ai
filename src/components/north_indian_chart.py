"""D1 wrapper around the reusable North Indian divisional chart renderer."""

from src.components.divisional_chart import (
    PLANET_ABBREVIATIONS,
    build_divisional_svg,
    map_house_contents,
    render_divisional_chart,
)
from src.models import KundaliChart
from src.localization.translations import t


def house_chart_data(chart: KundaliChart, lang: str = "en") -> dict[int, dict[str, object]]:
    return map_house_contents(chart.houses, ((planet.name, planet.house) for planet in chart.planets), lang)


def build_chart_svg(chart: KundaliChart, lang: str = "en") -> str:
    return build_divisional_svg(chart.houses, ((planet.name, planet.house) for planet in chart.planets), t("lagna", lang), "#5b3975", lang)


def render_north_indian_chart(chart: KundaliChart, lang: str = "en") -> None:
    render_divisional_chart(chart.houses, ((planet.name, planet.house) for planet in chart.planets), t("lagna", lang), "#5b3975", lang)
