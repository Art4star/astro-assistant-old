from __future__ import annotations
import json
import os
from datetime import datetime

from agents.base import AgentPlan
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RouterAgent:
    """
    Єдина точка входу. Розуміє інтент запиту і будує план виконання.
    generate_report.py і bot.py викликають тільки його.
    """

    # ВАЖЛИВО: порядок агентів у списку — це порядок виконання.
    # forecast завжди перед goals — GoalsAgent потребує forecast_data.
    INTENTS: dict = {
        "monthly_report":      ["forecast", "goals", "knowledge", "synthesis", "output"],
        "goal_timing":         ["forecast", "goals", "synthesis", "output"],
        "today_briefing":      ["forecast", "output"],
        "best_days":           ["forecast", "output"],
        "yearly_overview":     ["forecast", "goals", "knowledge", "synthesis", "output"],
        "knowledge_query":     ["knowledge", "synthesis", "output"],
        "decision_log":        ["output"],
        "personal_empowerment":["forecast", "empowerment", "output"],
    }

    TYPE_TO_INTENT: dict = {
        "month":        "monthly_report",
        "today":        "today_briefing",
        "week":         "today_briefing",
        "best":         "best_days",
        "yearly_goals": "yearly_overview",
        "log":          "decision_log",
        "empower":      "personal_empowerment",
    }

    # Ключові слова для Telegram вільного тексту
    KEYWORDS: dict = {
        "goal_timing":    ["коли", "начальник", "blue card", "розмова", "поговорити", "ціль"],
        "monthly_report": ["місяць", "звіт", "місячний", "прогноз на місяць"],
        "best_days":      ["найкращі дні", "коли краще", "фінанси", "угода", "підписати"],
        "knowledge_query":["профіль", "карма", "психологія", "кар'єра", "хто я"],
    }

    def route(self, request: dict) -> AgentPlan:
        intent = self.detect_intent(request)
        agents = self.INTENTS.get(intent, ["forecast", "synthesis", "output"])
        return AgentPlan(intent=intent, agents=agents)

    def detect_intent(self, request: dict) -> str:
        # CLI --type має пріоритет
        rtype = request.get("type", "")
        if rtype in self.TYPE_TO_INTENT:
            return self.TYPE_TO_INTENT[rtype]

        # Вільний текст (Telegram)
        text = request.get("text", "").lower()
        if text:
            for intent, keywords in self.KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    return intent

        return "today_briefing"

    def build_context(self, request: dict) -> AgentContext:
        birth_data_path = os.path.join(BASE_DIR, "data", "birth_data.json")
        birth_data: dict = {}
        if os.path.exists(birth_data_path):
            with open(birth_data_path, encoding="utf-8") as f:
                birth_data = json.load(f)

        now = datetime.now()
        return AgentContext(
            request=request,
            birth_data=birth_data,
            year=request.get("year", now.year),
            month=request.get("month", now.month),
        )
