from __future__ import annotations
import json
import os
from datetime import datetime, timedelta

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

WEEKDAY_UA = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}
ACTIVITY_LABELS = {
    "finance": "Фінанси", "work_technical": "Технічна робота",
    "negotiations": "Переговори", "content_publishing": "Контент",
    "rest_reflection": "Відпочинок", "new_beginnings": "Нові починання",
    "health_body": "Здоров'я",
}


class OutputAgent(BaseAgent):
    """
    Єдина точка виводу для всіх інтентів.
    HTML-рендер для місячного/річного звіту, текст для решти.
    """
    name = "output"
    requires = ["birth_data"]
    produces = ["output_path", "output_text"]

    def run(self, context: AgentContext) -> AgentContext:
        req_type = context.request.get("type", "today")

        if context.has("power_items"):
            return self._output_empowerment(context)
        elif context.has("report_sections"):
            return self._render_html(context)
        elif req_type == "log":
            return self._decision_log(context)
        elif req_type == "week":
            return self._output_week(context)
        elif req_type == "best":
            return self._output_best_days(context)
        else:
            return self._output_today(context)

    # ── HTML ─────────────────────────────────────────────────────────────────

    def _render_html(self, context: AgentContext) -> AgentContext:
        from jinja2 import Environment, FileSystemLoader

        req_type = context.request.get("type", "month")
        if req_type == "yearly_goals":
            template_name = "yearly_goals.html"
            filename = f"{context.year}-yearly-goals.html"
            render_kwargs = dict(
                year=context.year,
                goals=context.active_goals or [],
                name=context.birth_data.get("name", ""),
                generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            )
            # yearly_goals needs calendar data from goal_matcher
            from engine.goal_matcher import get_yearly_goal_calendar
            render_kwargs["calendar"] = get_yearly_goal_calendar(
                context.active_goals or [], context.year, context.birth_data
            )
        else:
            template_name = "report.html"
            filename = f"{context.year}-{context.month:02d}-report.html"
            render_kwargs = dict(
                **context.report_sections,
                generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            )

        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        html = env.get_template(template_name).render(**render_kwargs)

        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath = os.path.join(REPORTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        context.output_path = filepath
        context.output_text = f"Збережено: {filepath}"
        print(f"    {context.output_text}")
        return context

    # ── Текстовий вивід ───────────────────────────────────────────────────────

    def _output_today(self, context: AgentContext) -> AgentContext:
        from engine.calculator import get_daily_data
        from engine.interpreter import score_day, get_overall_score, get_day_label, get_warnings, get_recommendations
        from engine.lunar import get_phase_emoji, get_sign_name_ua

        today = datetime.now()
        daily = get_daily_data(today, context.birth_data)
        scores = score_day(daily)
        overall = get_overall_score(scores)
        label = get_day_label(overall, scores)
        recs = get_recommendations(daily, scores)

        if overall >= 5:
            icon = "🟢"
        elif overall >= 2:
            icon = "🟡"
        elif overall >= -1:
            icon = "⚪"
        elif overall >= -4:
            icon = "🟠"
        else:
            icon = "🔴"

        weekday = WEEKDAY_UA[today.weekday()]
        date_str = f"{weekday}, {today.day}.{today.month:02d}"

        flags = []
        if daily.get("mercury_retrograde"):
            flags.append("☿ Меркурій ретро — перевіряй деталі")
        if daily.get("moon_voc"):
            flags.append("🌀 VOC — не починай нового")

        lines = [f"{icon} {date_str} — {label}"]
        lines.append(f"{get_phase_emoji(daily['moon_phase'])} Місяць у {get_sign_name_ua(daily['moon_sign'])}")
        if flags:
            lines.append("  " + " · ".join(flags))
        if recs["best_for"]:
            lines.append("✅ " + ", ".join(recs["best_for"][:3]))
        if recs["avoid"]:
            lines.append("🚫 Уникай: " + ", ".join(recs["avoid"][:2]))
        if recs["tip"]:
            lines.append(f"💡 {recs['tip']}")

        context.output_text = "\n".join(lines)
        return context

    def _output_week(self, context: AgentContext) -> AgentContext:
        from engine.calculator import get_daily_data
        from engine.interpreter import score_day, get_overall_score, get_day_label
        from engine.lunar import get_phase_emoji

        today = datetime.now()
        lines = [f"📅 Астро-тиждень з {today.strftime('%d.%m')}:", ""]

        for i in range(7):
            day = today + timedelta(days=i)
            daily = get_daily_data(day, context.birth_data)
            scores = score_day(daily)
            overall = get_overall_score(scores)
            label = get_day_label(overall, scores)
            weekday = WEEKDAY_UA[day.weekday()]
            sign = "+" if overall > 0 else ""
            lines.append(
                f"{get_phase_emoji(daily['moon_phase'])} {weekday} {day.strftime('%d.%m')} "
                f"— {label} ({sign}{overall})"
            )

        context.output_text = "\n".join(lines)
        return context

    def _output_best_days(self, context: AgentContext) -> AgentContext:
        from engine.calculator import get_daily_data
        from engine.interpreter import score_day

        activity = context.request.get("activity", "finance")
        days = int(context.request.get("days", 30))
        today = datetime.now()

        results = []
        for i in range(days):
            day = today + timedelta(days=i)
            daily = get_daily_data(day, context.birth_data)
            sc = score_day(daily).get(activity, 0)
            results.append((day, sc))

        results.sort(key=lambda x: x[1], reverse=True)
        act_label = ACTIVITY_LABELS.get(activity, activity)

        lines = [f"🏆 Найкращі дні для «{act_label}» (наступні {days} днів):", ""]
        for day, sc in results[:10]:
            weekday = WEEKDAY_UA[day.weekday()]
            sign = "+" if sc > 0 else ""
            lines.append(f"  {day.strftime('%d.%m')} ({weekday}) — {sign}{sc}")

        context.output_text = "\n".join(lines)
        return context

    def _decision_log(self, context: AgentContext) -> AgentContext:
        from engine.calculator import get_daily_data
        from engine.interpreter import score_day, get_overall_score, get_day_label

        note = context.request.get("note", "")
        if not note:
            context.output_text = "Вкажи нотатку: --note 'текст'"
            return context

        history_file = os.path.join(BASE_DIR, "data", "history.json")
        today = datetime.now()
        daily = get_daily_data(today, context.birth_data)
        scores = score_day(daily)
        overall = get_overall_score(scores)
        label = get_day_label(overall, scores)

        entry = {
            "date": today.strftime("%Y-%m-%d"),
            "time": today.strftime("%H:%M"),
            "note": note,
            "context": {
                "day_label": label,
                "overall_score": overall,
                "moon_phase": daily.get("moon_phase", ""),
                "moon_sign": daily.get("moon_sign", ""),
                "mercury_retrograde": daily.get("mercury_retrograde", False),
                "moon_voc": daily.get("moon_voc", False),
                "scores": scores,
            }
        }

        history = []
        if os.path.exists(history_file):
            with open(history_file, encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        history.append(entry)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        weekday = WEEKDAY_UA[today.weekday()]
        sign = "+" if overall > 0 else ""
        context.output_text = (
            f"✅ Записано: {weekday}, {today.strftime('%d.%m.%Y')} — {label} ({sign}{overall})\n"
            f"   \"{note}\""
        )
        return context

    def _output_empowerment(self, context: AgentContext) -> AgentContext:
        p = context.power_items
        profile = p["profile"]

        SIGN_UA = {
            "capricorn": "Козоріг", "aquarius": "Водолій", "scorpio": "Скорпіон",
            "sagittarius": "Стрілець", "gemini": "Близнюки", "cancer": "Рак",
            "aries": "Овен", "taurus": "Телець", "virgo": "Діва", "leo": "Лев",
            "libra": "Терези", "pisces": "Риби",
        }
        PLANET_UA = {
            "saturn": "Сатурн", "jupiter": "Юпітер", "mars": "Марс",
            "venus": "Венера", "sun": "Сонце", "moon": "Місяць",
            "mercury": "Меркурій", "uranus": "Уран", "neptune": "Нептун",
            "pluto": "Плутон",
        }
        EL_UA = {"earth": "Земля", "fire": "Вогонь", "air": "Повітря", "water": "Вода"}

        asc = SIGN_UA.get(profile["ascendant"], profile["ascendant"])
        ruler = PLANET_UA.get(profile["ruler"], profile["ruler"])
        dom = SIGN_UA.get(profile["dominant_sign"], profile["dominant_sign"])
        el = EL_UA.get(profile["dominant_element"], profile["dominant_element"])
        stelliums_ua = [SIGN_UA.get(s, s) for s in profile["stelliums"]]
        venus = SIGN_UA.get(profile["venus_sign"], profile["venus_sign"])
        pluto = SIGN_UA.get(profile["pluto_sign"], profile["pluto_sign"])

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "  ПЕРСОНАЛЬНИЙ ПРОФІЛЬ ПІДСИЛЕННЯ",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Асц: {asc}  ·  Керівник: {ruler}  ·  Домінант: {dom} ({el})",
        ]
        if stelliums_ua:
            lines.append(f"  Стеліум: {', '.join(stelliums_ua)}")
        lines.append(f"  Венера: {venus}  ·  Плутон: {pluto}")
        lines.append("")

        lines.append("🎨 КОЛЬОРИ ЩО ПІДСИЛЮЮТЬ:")
        for c in p["power_colors"]:
            lines.append(f"   ✅ {c}")
        lines.append("")

        lines.append("🚫 КОЛЬОРИ ЩО КРАДУТЬ СИЛУ:")
        for c in p["avoid_colors"]:
            lines.append(f"   ❌ {c}")
        lines.append("")

        lines.append("🧵 МАТЕРІАЛИ / ТЕКСТУРИ:")
        for m in p["materials"]:
            lines.append(f"   ✅ {m}")
        lines.append("")

        lines.append("💎 КАМЕНІ / КРИСТАЛИ:")
        for s in p["stones"]:
            lines.append(f"   ✅ {s}")
        lines.append("")

        lines.append("👔 СТИЛЬ ОДЯГУ:")
        for note in p["style_notes"]:
            lines.append(f"   • {note}")
        lines.append("")

        lines.append("🚗 АВТО — характер:")
        for v in p["car_vibes"]:
            lines.append(f"   • {v}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        context.output_text = "\n".join(lines)
        return context
