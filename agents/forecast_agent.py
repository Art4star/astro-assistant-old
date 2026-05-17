from __future__ import annotations
import json
import os
from datetime import datetime

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DATA_DIR = os.path.join(BASE_DIR, "output", "data")
MEMORY_DIR = os.path.join(BASE_DIR, "data", "memory")


class ForecastAgent(BaseAgent):
    """
    Відповідає за: натальна карта + транзити місяця + місячний календар.
    Кешує результат в output/data/{period}-interpret.json.
    Якщо кеш є — бере звідти (без повторних розрахунків).
    """
    name = "forecast"
    requires = ["birth_data", "year", "month"]
    produces = ["forecast_data", "transits", "lunar_calendar", "natal_chart"]

    def run(self, context: AgentContext) -> AgentContext:
        year, month = context.year, context.month
        period = f"{year}-{month:02d}"
        package_path = os.path.join(OUTPUT_DATA_DIR, f"{period}-interpret.json")

        if os.path.exists(package_path):
            print(f"    кеш: {period}-interpret.json")
            with open(package_path, encoding="utf-8") as f:
                pkg = json.load(f)
            self._fill_context(context, pkg)
            return context

        # Розраховуємо з нуля
        natal_chart = self._get_natal_chart(context.birth_data)
        forecast    = self._get_forecast(context.birth_data, year, month)
        lunar       = self._get_lunar(year, month)

        top_transits   = self._top_transits(forecast["transits"])
        contradictions = self._detect_contradictions(forecast["transits"])
        activated      = self._activated_patterns(forecast["critical_windows"])

        pkg = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "period": period,
            "natal_chart": self._trim_natal(natal_chart),
            "forecast": {
                "period": period,
                "top_transits": top_transits,
                "critical_windows": forecast["critical_windows"],
                "solar_return": forecast.get("solar_return", {}),
                "all_transits_count": len(forecast["transits"]),
            },
            "lunar_calendar": lunar,
            "contradictions": contradictions,
            "activated_patterns": activated,
        }

        os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)
        with open(package_path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, ensure_ascii=False, indent=2)
        print(f"    збережено: {package_path}")

        self._fill_context(context, pkg)
        return context

    # ── helpers ──────────────────────────────────────────────────────────────

    def _fill_context(self, context: AgentContext, pkg: dict) -> None:
        context.forecast_data  = pkg.get("forecast", {})
        context.transits       = context.forecast_data.get("top_transits", [])
        context.lunar_calendar = pkg.get("lunar_calendar", {})
        context.natal_chart    = pkg.get("natal_chart", {})

    def _get_natal_chart(self, birth_data: dict) -> dict:
        cache = os.path.join(OUTPUT_DATA_DIR, "natal_chart.json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        from agents.chart_parser import parse_natal_chart
        chart = parse_natal_chart(birth_data)
        os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(chart, f, ensure_ascii=False, indent=2)
        return chart

    def _get_forecast(self, birth_data: dict, year: int, month: int) -> dict:
        cache = os.path.join(OUTPUT_DATA_DIR, f"{year}-{month:02d}-forecast.json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        from agents.forecast_engine import build_forecast
        forecast = build_forecast(birth_data, year, month)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(forecast, f, ensure_ascii=False, indent=2)
        return forecast

    def _get_lunar(self, year: int, month: int) -> dict:
        from agents.lunar_calendar import build_lunar_calendar
        return build_lunar_calendar(year, month)

    def _top_transits(self, transits: list, limit: int = 10) -> list:
        return sorted(transits, key=lambda x: -x.get("intensity", 0))[:limit]

    def _detect_contradictions(self, transits: list) -> list:
        EXPANSION  = {"jupiter", "sun", "venus"}
        RESTRICTION = {"saturn", "pluto", "neptune"}
        EXP_ASP    = {"trine", "sextile", "conjunction"}
        REST_ASP   = {"square", "opposition", "conjunction"}

        expand: dict  = {}
        restrict: dict = {}
        for t in transits:
            if t.get("intensity", 0) < 15:
                continue
            np = t["natal_planet"]
            pl = t["transit_planet"]
            asp = t["aspect"]
            if pl in EXPANSION and asp in EXP_ASP:
                expand.setdefault(np, []).append(t)
            if pl in RESTRICTION and asp in REST_ASP:
                restrict.setdefault(np, []).append(t)

        result = []
        for np in set(expand) & set(restrict):
            result.append({
                "natal_point": np,
                "expanding":   [f"{t['transit_planet']} {t['aspect']}" for t in expand[np]],
                "restricting": [f"{t['transit_planet']} {t['aspect']}" for t in restrict[np]],
                "note": (
                    f"Натальний {np} одночасно під тиском розширення і обмеження. "
                    "Вкажи обидві сили і як їх збалансувати."
                ),
            })
        return result

    def _activated_patterns(self, critical_windows: list) -> list:
        path = os.path.join(MEMORY_DIR, "natal_patterns.json")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            natal_patterns = json.load(f)

        planets = {w["transit_planet"] for w in critical_windows}
        types   = {w["type"] for w in critical_windows}

        result = []
        for p in natal_patterns.get("patterns", []):
            trigger = p.get("when_activated", "")
            if any(pl in trigger for pl in planets) or any(t in p.get("theme", "") for t in types):
                result.append({
                    "id": p["id"],
                    "theme": p["theme"],
                    "behavioral_signature": p["behavioral_signature"],
                    "confidence": p["confidence"],
                })
        return result

    def _trim_natal(self, chart: dict) -> dict:
        return {
            "user":             chart.get("user"),
            "angles":           chart.get("angles"),
            "houses":           chart.get("houses"),
            "ascendant_ruler":  chart.get("ascendant_ruler"),
            "stelliums":        chart.get("stelliums"),
            "angular_planets":  chart.get("angular_planets"),
            "dominants":        chart.get("dominants"),
            "aspects":          chart.get("aspects", [])[:15],
            "planets":          chart.get("planets"),
        }
