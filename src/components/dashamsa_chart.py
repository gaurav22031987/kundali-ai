"""D10 wrapper around the reusable North Indian divisional chart renderer."""

from src.components.divisional_chart import render_divisional_chart
from src.models import DashamsaChart
from src.localization.translations import t


def render_dashamsa_chart(chart: DashamsaChart, lang: str = "en") -> None:
    render_divisional_chart(chart.houses, ((planet.name, planet.house) for planet in chart.positions), f"D10 {t('lagna', lang)}", "#7a3e11", lang)
