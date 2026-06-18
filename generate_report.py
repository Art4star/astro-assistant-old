#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, date
import calendar

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.calculator import get_daily_data, get_month_data
from engine.interpreter import (
    score_day, get_overall_score, get_day_label,
    get_warnings, get_recommendations, get_day_color, ACTIVITY_LABELS
)
from engine.lunar import (
    get_phase_emoji, get_phase_name_ua, get_sign_name_ua, get_sign_emoji,
    get_month_lunar_events
)
from engine.synthesizer import build_report_sections
from engine.goal_matcher import get_yearly_goal_calendar, MONTH_NAMES_UA as GM_MONTHS

MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}

WEEKDAY_UA = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

REPORTS_DIR = os.path.join(BASE_DIR, os.getenv("REPORTS_DIR", "output/reports"))
BIRTH_DATA_FILE = os.path.join(BASE_DIR, os.getenv("BIRTH_DATA_FILE", "data/birth_data.json"))


def load_birth_data() -> dict:
    if os.path.exists(BIRTH_DATA_FILE):
        with open(BIRTH_DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if data else {}
    return {}


def build_day_context(daily_data: dict, today: date) -> dict:
    scores = score_day(daily_data)
    overall = get_overall_score(scores)
    label = get_day_label(overall, scores)
    warnings = get_warnings(daily_data)
    recs = get_recommendations(daily_data, scores)
    color = get_day_color(overall)

    day_date = datetime.strptime(daily_data["date"], "%Y-%m-%d").date()
    day_num = day_date.day
    weekday_ua = WEEKDAY_UA[day_date.weekday()]
    date_str = f"{weekday_ua}, {day_num} {MONTH_NAMES_UA[day_date.month].lower()}"

    activity_colors = {
        act: get_day_color(sc) for act, sc in scores.items()
    }

    return {
        "num": day_num,
        "is_today": day_date == today,
        "empty": False,
        "color": color,
        "phase_emoji": get_phase_emoji(daily_data["moon_phase"]),
        "sign_short": get_sign_emoji(daily_data["moon_sign"]),
        "mercury_retro": daily_data.get("mercury_retrograde", False),
        "moon_voc": daily_data.get("moon_voc", False),
        "label": label,
        "overall_score": overall,
        "scores_json": json.dumps(scores),
        "activity_colors": activity_colors,
        # for JS
        "date_str": date_str,
        "phase_name": get_phase_name_ua(daily_data["moon_phase"]),
        "moon_sign_ua": get_sign_name_ua(daily_data["moon_sign"]),
        "warnings": warnings,
        "recommendations": recs,
        "scores": scores,
        "tip": recs.get("tip", ""),
        "overall": overall,
        "label_js": label,
    }


def load_goals() -> list:
    goals_file = os.path.join(BASE_DIR, "data", "goals.json")
    if os.path.exists(goals_file):
        with open(goals_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("active", [])
    return []


def generate_yearly_goals_report(year: int) -> str:
    print(f"Генерую річний огляд цілей: {year}...")
    birth_data = load_birth_data()
    goals = load_goals()
    if not goals:
        print("Немає активних цілей. Додайте: python manage_goals.py add")
        return ""

    calendar_data = get_yearly_goal_calendar(goals, year, birth_data)

    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
    template = env.get_template("yearly_goals.html")

    html = template.render(
        year=year,
        goals=goals,
        calendar=calendar_data,
        name=birth_data.get("name", ""),
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, f"{year}-yearly-goals.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Збережено: {filepath}")
    return filepath


def generate_month_report_v2(year: int, month: int) -> str:
    print(f"Генерую місячний звіт v2: {MONTH_NAMES_UA[month]} {year}...")
    birth_data = load_birth_data()
    goals = load_goals()

    month_data = get_month_data(year, month, birth_data)

    # Load cached interpretation package for transit narratives
    package_path = os.path.join(BASE_DIR, f"output/data/{year}-{month:02d}-interpret.json")
    forecast_data: dict = {}
    if os.path.exists(package_path):
        with open(package_path, encoding="utf-8") as f:
            pkg = json.load(f)
        forecast_data = pkg.get("forecast", {})
        print(f"  Завантажено transit-пакет: {len(forecast_data.get('top_transits', []))} транзитів")

    report = build_report_sections(month_data, birth_data, goals=goals, forecast_data=forecast_data)

    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
    template = env.get_template("report.html")

    html = template.render(
        **report,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{year}-{month:02d}-report.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Збережено: {filepath}")
    return filepath


def generate_month_report(year: int, month: int) -> str:
    print(f"Генерую місячний звіт: {MONTH_NAMES_UA[month]} {year}...")
    birth_data = load_birth_data()
    today = date.today()

    month_data = get_month_data(year, month, birth_data)

    first_day_weekday = date(year, month, 1).weekday()  # 0=Mon

    days = []
    for _ in range(first_day_weekday):
        days.append({"empty": True})

    days_data_js = {}
    for daily in month_data:
        ctx = build_day_context(daily, today)
        days.append(ctx)
        days_data_js[ctx["num"]] = {
            "date_str": ctx["date_str"],
            "phase_emoji": ctx["phase_emoji"],
            "phase_name": ctx["phase_name"],
            "moon_sign_ua": ctx["moon_sign_ua"],
            "warnings": ctx["warnings"],
            "recommendations": ctx["recommendations"],
            "scores": ctx["scores"],
            "tip": ctx["tip"],
            "overall": ctx["overall"],
            "label": ctx["label_js"],
        }

    month_start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    month_end = f"{year}-{month:02d}-{last_day:02d}"
    goal_windows = _get_goal_windows_for_range(month_start, month_end)
    goal_dates = {gw["date"]: gw for gw in goal_windows}

    for ctx in days:
        if ctx.get("empty"):
            continue
        day_date = f"{year}-{month:02d}-{ctx['num']:02d}"
        if day_date in goal_dates:
            gw = goal_dates[day_date]
            ctx["goal_marker"] = gw["goal"]

    lunar_events = get_month_lunar_events(year, month)
    month_warnings = []

    retro_planets = set()
    for daily in month_data:
        for p in ["mercury", "venus", "mars", "jupiter", "saturn"]:
            if daily.get(f"{p}_retrograde"):
                retro_planets.add(p)

    retro_names = {"mercury": "Меркурій", "venus": "Венера", "mars": "Марс",
                   "jupiter": "Юпітер", "saturn": "Сатурн"}
    for p in retro_planets:
        month_warnings.append(f"☿ {retro_names[p]} ретроградний цього місяця")

    if lunar_events["full_moon"]:
        for d in lunar_events["full_moon"]:
            month_warnings.append(f"🌕 Повний місяць: {d} {MONTH_NAMES_UA[month].lower()}")
    if lunar_events["new_moon"]:
        for d in lunar_events["new_moon"]:
            month_warnings.append(f"🌑 Новий місяць: {d} {MONTH_NAMES_UA[month].lower()}")
    if lunar_events["voc_days"]:
        voc_str = ", ".join(str(d) for d in lunar_events["voc_days"][:5])
        month_warnings.append(f"🌀 VOC (Місяць без курсу): {voc_str}...")

    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
    template = env.get_template("dashboard.html")

    if goal_windows:
        month_warnings.append("")
        month_warnings.append("📌 Вікна для цілей:")
        for gw in goal_windows:
            d = int(gw["date"].split("-")[2])
            month_warnings.append(f"  {d:02d} — {gw['goal']} (+{gw['score']})")

    user_name = birth_data.get("name", "Astro")
    html = template.render(
        year=year,
        month_num=month,
        month_name=MONTH_NAMES_UA[month],
        user_name=user_name,
        days=days,
        days_data_json=json.dumps(days_data_js, ensure_ascii=False),
        month_warnings=month_warnings,
        goal_windows=goal_windows,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{year}-{month:02d}-month.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Збережено: {filepath}")
    return filepath


PLANET_UA = {
    "sun": "Сонце", "moon": "Місяць", "mercury": "Меркурій",
    "venus": "Венера", "mars": "Марс", "jupiter": "Юпітер",
    "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
    "pluto": "Плутон", "true_node": "Вузол", "lilith": "Ліліт",
    "ascendant": "Асцендент", "midheaven": "MC",
}

ASPECT_UA = {
    "conjunction": "кон'юнкція", "opposition": "опозиція",
    "square": "квадрат", "trine": "трін", "sextile": "секстиль",
}

WINDOW_TYPE_EMOJI = {
    "confusion": "🌫", "transformation": "🔥", "liberation": "⚡",
    "consolidation": "🧱", "overreach_risk": "⚠️", "restructuring": "🔧",
    "expansion": "🚀", "tension": "💥",
}


def _load_interpret_package(year, month):
    pkg_path = os.path.join(BASE_DIR, "output", "data", f"{year}-{month:02d}-interpret.json")
    if not os.path.exists(pkg_path):
        return None
    with open(pkg_path, encoding="utf-8") as f:
        return json.load(f)


def _get_today_transits(pkg, today_str):
    transits = pkg.get("forecast", {}).get("top_transits", [])
    active = []
    for t in transits:
        if t["first_date"] <= today_str <= t["last_date"]:
            active.append(t)
    active.sort(key=lambda t: t["intensity"], reverse=True)
    return active


def _get_today_windows(pkg, today_str):
    windows = pkg.get("forecast", {}).get("critical_windows", [])
    active = []
    for w in windows:
        if w["first_date"] <= today_str <= w["last_date"]:
            active.append(w)
    active.sort(key=lambda w: w["intensity"], reverse=True)
    return active


def _format_transit(t):
    tp = PLANET_UA.get(t["transit_planet"], t["transit_planet"])
    np_ = PLANET_UA.get(t["natal_planet"], t["natal_planet"])
    asp = ASPECT_UA.get(t["aspect"], t["aspect"])
    retro = " (R)" if t.get("retrograde") else ""
    peak = t.get("peak_date", "")
    peak_str = f", пік {peak[5:]}" if peak else ""
    return f"{tp} {asp} {np_}{retro}{peak_str}"


def _format_window_short(w):
    emoji = WINDOW_TYPE_EMOJI.get(w["type"], "🔹")
    tp = PLANET_UA.get(w["transit_planet"], w["transit_planet"])
    np_ = PLANET_UA.get(w["natal_planet"], w["natal_planet"])
    asp = ASPECT_UA.get(w["aspect"], w["aspect"])
    return f"{emoji} {tp} {asp} {np_}"


def _get_goal_windows_for_date(date_str):
    goals = load_goals()
    matches = []
    for g in goals:
        for w in g.get("best_windows", []):
            if w.get("date") == date_str:
                matches.append({"goal": g["title"], "score": w.get("score", 0), "reason": w.get("reason", "")})
    return matches


def _get_goal_windows_for_range(start_str, end_str):
    goals = load_goals()
    matches = []
    for g in goals:
        for w in g.get("best_windows", []):
            d = w.get("date", "")
            if start_str <= d <= end_str:
                matches.append({"goal": g["title"], "date": d, "score": w.get("score", 0), "reason": w.get("reason", "")})
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


PHASE_GUIDANCE = {
    "new":              "Час для намірів і внутрішньої роботи. Дій не потрібно — сіяти зерна.",
    "waxing_crescent":  "Місяць росте — починай, пропонуй, рухайся вперед.",
    "first_quarter":    "Перший опір — не здавайся, просувай почате.",
    "waxing_gibbous":   "Набираєш темп — доводь до результату, не розпорошуйся.",
    "full":             "Пік емоцій і ясності — побачиш результати або правду.",
    "waning_gibbous":   "Час ділитись і передавати далі. Аналізуй що спрацювало.",
    "last_quarter":     "Відпусти те що не працює. Не починай нового.",
    "balsamic":         "Відпочинок і перезавантаження. Мінімум дій — максимум рефлексії.",
}

SIGN_ENERGY = {
    "aries":       "енергія дії і ініціативи",
    "taurus":      "стабільність, фінанси, тіло",
    "gemini":      "комунікації і навчання",
    "cancer":      "дім, емоції, близькі",
    "leo":         "творчість, самовираження, лідерство",
    "virgo":       "порядок, деталі, здоров'я",
    "libra":       "партнерства, домовленості, баланс",
    "scorpio":     "глибина, трансформація, чесність з собою",
    "sagittarius": "розширення, навчання, нові горизонти",
    "capricorn":   "кар'єра, структура, довгострокове",
    "aquarius":    "нестандартні рішення, спільнота, свобода",
    "pisces":      "інтуїція, творчість, духовне",
}


def generate_today_report():
    from engine.synthesizer import _make_narrative

    today = datetime.now()
    birth_data = load_birth_data()

    daily_data = get_daily_data(today, birth_data)
    scores = score_day(daily_data)
    overall = get_overall_score(scores)
    label = get_day_label(overall, scores)
    recs = get_recommendations(daily_data, scores)

    weekday_ua = WEEKDAY_UA[today.weekday()]
    phase = daily_data["moon_phase"]
    sign = daily_data["moon_sign"]
    phase_emoji = get_phase_emoji(phase)
    phase_ua = get_phase_name_ua(phase)
    sign_ua = get_sign_name_ua(sign)

    lines = [f"🔮 {weekday_ua}, {today.day}.{today.month:02d}"]
    lines.append(f"{phase_emoji} {phase_ua} у {sign_ua}")
    lines.append("")

    if overall >= 5:
        lines.append("🟢 День для активних дій — використай по максимуму.")
    elif overall >= 2:
        lines.append("🟡 Хороший день — дій у своєму темпі.")
    elif overall >= -1:
        if daily_data.get("moon_voc") or daily_data.get("mercury_retrograde"):
            lines.append("⚪ Нейтрально, але є перешкоди — обирай моменти.")
        else:
            lines.append("⚪ Рівний день — можна діяти, але вибірково.")
    elif overall >= -4:
        lines.append("🟠 Краще не форсувати — завершуй почате, не починай нового.")
    else:
        lines.append("🔴 День для відпочинку і рефлексії. Великі рішення — на потім.")

    if daily_data.get("mercury_retrograde"):
        lines.append("☿ Меркурій ретро — перечитуй перед підписом, перевіряй деталі.")
    if daily_data.get("moon_voc"):
        lines.append("🌀 Місяць без курсу — не починай нічого важливого прямо зараз.")

    if recs["best_for"]:
        lines.append("")
        lines.append("✅ Русло дня: " + ", ".join(recs["best_for"][:3]).lower())
    if recs["avoid"]:
        lines.append("🚫 Відкласти: " + ", ".join(recs["avoid"][:2]).lower())

    today_str = today.strftime("%Y-%m-%d")
    goal_hits = _get_goal_windows_for_date(today_str)
    if goal_hits:
        lines.append("")
        for gh in goal_hits[:3]:
            lines.append(f"📌 Вдалий день для: {gh['goal']}")

    pkg = _load_interpret_package(today.year, today.month)
    if pkg:
        transits = _get_today_transits(pkg, today_str)

        narratives = []
        for t in transits[:5]:
            n = _make_narrative(t)
            if n:
                narratives.append(n)

        peak_narratives = [n for n, t in zip(narratives, transits) if t.get("peak_date") == today_str]
        if peak_narratives:
            lines.append("")
            n = peak_narratives[0]
            lines.append(f"{n['icon']} Пік сьогодні: {n['title']}")
            lines.append(f"→ {n['action']}")

        bg = [n for n, t in zip(narratives, transits) if t.get("peak_date") != today_str]
        if bg and not peak_narratives:
            lines.append("")
            n = bg[0]
            lines.append(f"{n['icon']} {n['title']}")
            lines.append(f"→ {n['action']}")

    sign_note = SIGN_ENERGY.get(sign, "")
    phase_note = PHASE_GUIDANCE.get(phase, "")
    if phase_note:
        lines.append("")
        lines.append(f"💡 {phase_note}")
        if sign_note:
            lines.append(f"   Фокус дня: {sign_note}.")

    return "\n".join(lines)


def log_decision(note: str) -> None:
    """Log a decision/event to data/history.json with today's astro context."""
    from engine.interpreter import score_day, get_overall_score, get_day_label
    history_file = os.path.join(BASE_DIR, "data", "history.json")
    today = datetime.now()
    birth_data = load_birth_data()
    daily_data = get_daily_data(today, birth_data)
    scores = score_day(daily_data)
    overall = get_overall_score(scores)
    label = get_day_label(overall, scores)

    entry = {
        "date": today.strftime("%Y-%m-%d"),
        "time": today.strftime("%H:%M"),
        "note": note,
        "context": {
            "day_label": label,
            "overall_score": overall,
            "moon_phase": daily_data.get("moon_phase", ""),
            "moon_sign": daily_data.get("moon_sign", ""),
            "mercury_retrograde": daily_data.get("mercury_retrograde", False),
            "moon_voc": daily_data.get("moon_voc", False),
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

    weekday_ua = WEEKDAY_UA[today.weekday()]
    print(f"✅ Записано: {weekday_ua}, {today.strftime('%d.%m.%Y')} — {label} ({'+' if overall > 0 else ''}{overall})")
    print(f"   \"{note}\"")


def generate_week_report() -> str:
    today = datetime.now()
    birth_data = load_birth_data()

    from datetime import timedelta
    lines = [f"📅 Астро-тиждень з {today.strftime('%d.%m')}:", ""]

    end_day = today + timedelta(days=6)
    goal_windows = _get_goal_windows_for_range(
        today.strftime("%Y-%m-%d"), end_day.strftime("%Y-%m-%d")
    )
    goal_dates = {gw["date"] for gw in goal_windows}

    for i in range(7):
        day = today + timedelta(days=i)
        daily = get_daily_data(day, birth_data)
        scores = score_day(daily)
        overall = get_overall_score(scores)
        label = get_day_label(overall, scores)
        phase_emoji = get_phase_emoji(daily["moon_phase"])
        weekday = WEEKDAY_UA[day.weekday()]
        day_str = day.strftime("%Y-%m-%d")
        marker = " 📌" if day_str in goal_dates else ""
        lines.append(f"{phase_emoji} {weekday} {day.strftime('%d.%m')} — {label} ({'+' if overall > 0 else ''}{overall}){marker}")

    if goal_windows:
        lines.append("")
        lines.append("📌 Вікна для цілей цього тижня:")
        for gw in goal_windows:
            d = gw["date"][5:]
            lines.append(f"  {d} — {gw['goal']} (+{gw['score']})")

    return "\n".join(lines)


def find_best_days(activity: str, days: int) -> str:
    today = datetime.now()
    birth_data = load_birth_data()

    from datetime import timedelta
    results = []
    for i in range(days):
        day = today + timedelta(days=i)
        daily = get_daily_data(day, birth_data)
        scores = score_day(daily)
        sc = scores.get(activity, 0)
        results.append((day, sc))

    results.sort(key=lambda x: x[1], reverse=True)
    act_label = ACTIVITY_LABELS.get(activity, activity)

    lines = [f"🏆 Найкращі дні для «{act_label}» (наступні {days} днів):", ""]
    for day, sc in results[:10]:
        weekday = WEEKDAY_UA[day.weekday()]
        lines.append(f"  {day.strftime('%d.%m')} ({weekday}) — {'+' if sc > 0 else ''}{sc}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Астро-асистент")
    parser.add_argument("--type", choices=["month", "week", "today", "best", "yearly_goals", "log", "empower"], default="today")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--activity", default="finance")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--note", default="", help="Нотатка для трекера рішень (з --type log)")
    args = parser.parse_args()

    from agents.router import RouterAgent
    from agents.executor import Executor

    request = {
        "type": args.type,
        "year": args.year,
        "month": args.month,
        "activity": args.activity,
        "days": args.days,
        "note": args.note,
    }

    router = RouterAgent()
    context = router.build_context(request)
    plan = router.route(request)
    context = Executor().run(plan, context)

    if context.output_text:
        print(context.output_text)
    if context.output_path:
        print(f"\nВідкрити: open '{context.output_path}'")


if __name__ == "__main__":
    main()
