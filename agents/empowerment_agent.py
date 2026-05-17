from __future__ import annotations
import json
import os
from collections import Counter
from typing import List

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_corr() -> dict:
    path = os.path.join(BASE_DIR, "data", "correspondences.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class EmpowermentAgent(BaseAgent):
    """
    Аналізує натальну карту і повертає персональні кореспонденції:
    кольори, матеріали, камені, стиль, авто — що підсилює і що краде силу.
    """
    name = "empowerment"
    requires = ["natal_chart"]
    produces = ["power_items"]

    def run(self, context: AgentContext) -> AgentContext:
        chart = context.natal_chart
        corr = _load_corr()

        # ── Ключові фактори карти ──────────────────────────────────────────
        asc_sign      = chart.get("angles", {}).get("ascendant", {}).get("sign", "")
        asc_ruler     = chart.get("ascendant_ruler", "")
        dominant_sign = chart.get("dominants", {}).get("sign", "")
        dominant_el   = chart.get("dominants", {}).get("element", "")
        stelliums     = [s["sign"] for s in chart.get("stelliums", [])]
        planets       = chart.get("planets", {})

        # Стиль → Венера (як виглядаю), Марс (де енергія), Плутон (сила)
        venus_sign  = planets.get("venus", {}).get("sign", "")
        mars_sign   = planets.get("mars", {}).get("sign", "")
        pluto_sign  = planets.get("pluto", {}).get("sign", "")
        sun_sign    = planets.get("sun", {}).get("sign", "")

        # ── Збираємо кольори ──────────────────────────────────────────────
        power_colors: List[str] = []
        avoid_colors: List[str] = []

        # Пріоритет 1: Асцендент і його керівник (найважливіше для зовнішнього вигляду)
        for src in [asc_sign, asc_ruler]:
            power_colors += corr["signs"].get(src, {}).get("colors", [])
            power_colors += corr["planets"].get(src, {}).get("colors", [])
            avoid_colors += corr["signs"].get(src, {}).get("avoid", [])
            avoid_colors += corr["planets"].get(src, {}).get("avoid_colors", [])

        # Пріоритет 2: Стеліуми (масивні конфігурації)
        for sign in stelliums:
            power_colors += corr["signs"].get(sign, {}).get("colors", [])

        # Пріоритет 3: Домінантний елемент
        power_colors += corr["elements"].get(dominant_el, {}).get("colors", [])

        # Пріоритет 4: Венера (стиль і естетика)
        power_colors += corr["signs"].get(venus_sign, {}).get("colors", [])
        power_colors += corr["planets"].get("venus", {}).get("colors", [])

        # Пріоритет 5: Плутон (глибина і сила образу)
        power_colors += corr["signs"].get(pluto_sign, {}).get("colors", [])
        power_colors += corr["planets"].get("pluto", {}).get("colors", [])

        # ── Матеріали ─────────────────────────────────────────────────────
        materials: List[str] = []
        for sign in [asc_sign, dominant_sign] + stelliums:
            materials += corr["signs"].get(sign, {}).get("materials", [])
        materials += corr["elements"].get(dominant_el, {}).get("materials", [])
        materials += corr["planets"].get(asc_ruler, {}).get("stones", [])

        # ── Камені ────────────────────────────────────────────────────────
        stones: List[str] = []
        for planet in [asc_ruler, "pluto", "saturn"]:
            stones += corr["planets"].get(planet, {}).get("stones", [])
        for sign in [asc_sign] + stelliums + [pluto_sign]:
            stones += corr["signs"].get(sign, {}).get("stones", [])

        # Додатково: Венера (для приємності і стилю)
        stones += corr["planets"].get("venus", {}).get("stones", [])
        # Додатково: Уран (для інновації — сильний в карті)
        stones += corr["planets"].get("uranus", {}).get("stones", [])

        # ── Авто ─────────────────────────────────────────────────────────
        car_vibes: List[str] = []
        for sign in [asc_sign, dominant_sign, venus_sign]:
            vibe = corr["signs"].get(sign, {}).get("car_vibe", "")
            if vibe:
                car_vibes.append(vibe)

        # ── Стиль одягу ───────────────────────────────────────────────────
        style_notes: List[str] = []
        for src in [asc_sign, dominant_sign, venus_sign]:
            s = corr["signs"].get(src, {}).get("style", "")
            if s:
                style_notes.append(s)
        for planet in [asc_ruler, "venus", "pluto"]:
            s = corr["planets"].get(planet, {}).get("style", "")
            if s:
                style_notes.append(s)

        # ── Що краде силу ─────────────────────────────────────────────────
        drain: List[str] = []
        for sign in [asc_sign] + stelliums:
            drain += corr["signs"].get(sign, {}).get("avoid", [])
        for planet in [asc_ruler, "saturn"]:
            drain += corr["planets"].get(planet, {}).get("avoid_colors", [])
        # Протилежний елемент до земного домінанту → вогонь без структури
        drain += ["яскраво-синтетичні матеріали", "дешеві підробки брендів",
                  "надто яскраві кричущі кольори без структури",
                  "пастельні відтінки (рожевий, м'ятний, baby blue)"]

        # ── Дедуплікація і топ ────────────────────────────────────────────
        def dedup_top(lst: list, n: int = 8) -> list:
            seen = []
            for x in lst:
                x = x.strip()
                if x and x not in seen:
                    seen.append(x)
            return seen[:n]

        context.power_items = {
            "profile": {
                "ascendant": asc_sign,
                "ruler": asc_ruler,
                "dominant_sign": dominant_sign,
                "dominant_element": dominant_el,
                "stelliums": stelliums,
                "venus_sign": venus_sign,
                "mars_sign": mars_sign,
                "pluto_sign": pluto_sign,
            },
            "power_colors":   dedup_top(power_colors, 8),
            "avoid_colors":   dedup_top(avoid_colors + drain, 6),
            "materials":      dedup_top(materials, 6),
            "stones":         dedup_top(stones, 8),
            "style_notes":    dedup_top(style_notes, 5),
            "car_vibes":      dedup_top(car_vibes, 3),
        }

        return context
