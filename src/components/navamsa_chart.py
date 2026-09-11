"""D9 wrapper around the reusable North Indian divisional chart renderer."""

from src.components.divisional_chart import build_divisional_svg, map_house_contents, render_divisional_chart
from src.models import NavamsaChart
from src.localization.translations import t


def navamsa_house_data(chart: NavamsaChart, lang: str = "en") -> dict[int, dict[str, object]]:
    return map_house_contents(chart.houses, ((planet.name, planet.d9_house) for planet in chart.positions), lang)


def build_navamsa_svg(chart: NavamsaChart, lang: str = "en") -> str:
    return build_divisional_svg(chart.houses, ((planet.name, planet.d9_house) for planet in chart.positions), f"D9 {t('lagna', lang)}", "#174b68", lang)


def render_navamsa_chart(chart: NavamsaChart, lang: str = "en") -> None:
    render_divisional_chart(chart.houses, ((planet.name, planet.d9_house) for planet in chart.positions), f"D9 {t('lagna', lang)}", "#174b68", lang)
