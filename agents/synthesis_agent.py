from __future__ import annotations
import os

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SynthesisAgent(BaseAgent):
    """
    Обчислює місячні дані (calculator) і збирає всі секції звіту (synthesizer).
    Потребує birth_data + year + month. Використовує active_goals і forecast_data
    якщо вони вже є в контексті.
    """
    name = "synthesis"
    requires = ["birth_data", "year", "month"]
    produces = ["report_sections", "month_data"]

    def run(self, context: AgentContext) -> AgentContext:
        from engine.calculator import get_month_data
        from engine.synthesizer import build_report_sections

        month_data = get_month_data(context.year, context.month, context.birth_data)
        context.month_data = month_data

        goals = context.active_goals or []
        forecast_data = context.forecast_data or {}

        context.report_sections = build_report_sections(
            month_data,
            context.birth_data,
            goals=goals,
            forecast_data=forecast_data,
        )
        return context
