from __future__ import annotations
import json
import os

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATEGORY_TRANSIT_MAP = {
    "career":        {"expand": [("jupiter","trine"), ("jupiter","conjunction"), ("saturn","trine")],
                      "block":  [("saturn","square"), ("saturn","opposition"), ("neptune","square")]},
    "finance":       {"expand": [("jupiter","trine"), ("venus","trine"), ("jupiter","sextile")],
                      "block":  [("saturn","square"), ("pluto","square"), ("pluto","conjunction")]},
    "health":        {"expand": [("sun","trine"), ("mars","trine"), ("jupiter","trine")],
                      "block":  [("saturn","square"), ("mars","square")]},
    "relationships": {"expand": [("venus","trine"), ("jupiter","trine"), ("venus","sextile")],
                      "block":  [("saturn","square"), ("pluto","square"), ("pluto","conjunction"), ("mars","opposition")]},
    "creativity":    {"expand": [("venus","trine"), ("sun","trine"), ("jupiter","sextile")],
                      "block":  [("saturn","square")]},
    "learning":      {"expand": [("mercury","trine"), ("jupiter","trine"), ("mercury","sextile")],
                      "block":  [("mercury","square"), ("saturn","opposition"), ("neptune","square"), ("jupiter","opposition")]},
    "negotiations":  {"expand": [("jupiter","trine"), ("venus","trine"), ("mercury","trine"), ("jupiter","sextile")],
                      "block":  [("saturn","square"), ("saturn","opposition"), ("neptune","square"), ("jupiter","opposition")]},
    "purchase":      {"expand": [("jupiter","trine"), ("venus","trine"), ("venus","sextile"), ("jupiter","sextile")],
                      "block":  [("saturn","square"), ("pluto","conjunction"), ("mercury","square")]},
    "documents":     {"expand": [("mercury","trine"), ("mercury","sextile"), ("jupiter","trine")],
                      "block":  [("mercury","square"), ("saturn","square"), ("neptune","square")]},
    "personal":      {"expand": [("venus","trine"), ("venus","sextile"), ("venus","conjunction"), ("jupiter","trine")],
                      "block":  [("saturn","square"), ("pluto","conjunction"), ("mars","opposition")]},
}


class GoalsAgent(BaseAgent):
    """
    Завантажує активні цілі та оцінює їх підтримку транзитами місяця.
    Потребує forecast_data (від ForecastAgent) для scoring.
    """
    name = "goals"
    requires = ["birth_data"]
    produces = ["active_goals", "goal_windows"]

    def run(self, context: AgentContext) -> AgentContext:
        goals = self._load_goals()
        context.active_goals = goals

        if context.has("forecast_data") and goals:
            transits = context.forecast_data.get("top_transits", [])
            critical_windows = context.forecast_data.get("critical_windows", [])
            context.goal_windows = self._score_goal_alignment(goals, transits, critical_windows)
        else:
            context.goal_windows = []

        return context

    # ── helpers ──────────────────────────────────────────────────────────────

    def _load_goals(self) -> list:
        path = os.path.join(BASE_DIR, "data", "goals.json")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("active", [])

    def _score_goal_alignment(
        self, goals: list, transits: list, critical_windows: list
    ) -> list:
        transit_set = {
            (t["transit_planet"], t["aspect"])
            for t in transits
            if t.get("intensity", 0) >= 15
        }

        result = []
        for goal in goals:
            category = (goal.get("category") or "").lower()
            rules = CATEGORY_TRANSIT_MAP.get(category, {})
            expand_hits = [p for p in rules.get("expand", []) if p in transit_set]
            block_hits  = [p for p in rules.get("block",  []) if p in transit_set]

            score = len(expand_hits) * 2 - len(block_hits) * 3
            if score >= 3:
                support = "strong"
            elif score >= 1:
                support = "moderate"
            elif score == 0:
                support = "weak"
            else:
                support = "blocked"

            result.append({
                "goal_id":    goal.get("id", ""),
                "goal_title": goal.get("title", ""),
                "category":   category,
                "monthly_support":    support,
                "score":              score,
                "supporting_transit": f"{expand_hits[0][0]} {expand_hits[0][1]}" if expand_hits else None,
                "blocking_transit":   f"{block_hits[0][0]} {block_hits[0][1]}" if block_hits else None,
            })

        result.sort(key=lambda x: -x["score"])
        return result
