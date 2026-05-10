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
    label = get_day_label(overall)
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


def generate_month_report_v2(year: int, month: int) -> str:
    print(f"Генерую місячний звіт v2: {MONTH_NAMES_UA[month]} {year}...")
    birth_data = load_birth_data()

    month_data = get_month_data(year, month, birth_data)
    report = build_report_sections(month_data, birth_data)

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

    user_name = birth_data.get("name", "Astro")
    html = template.render(
        year=year,
        month_num=month,
        month_name=MONTH_NAMES_UA[month],
        user_name=user_name,
        days=days,
        days_data_json=json.dumps(days_data_js, ensure_ascii=False),
        month_warnings=month_warnings,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
    )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{year}-{month:02d}-month.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Збережено: {filepath}")
    return filepath


def generate_today_report() -> str:
    today = datetime.now()
    birth_data = load_birth_data()

    daily_data = get_daily_data(today, birth_data)
    scores = score_day(daily_data)
    overall = get_overall_score(scores)
    label = get_day_label(overall)
    warnings = get_warnings(daily_data)
    recs = get_recommendations(daily_data, scores)

    weekday_ua = WEEKDAY_UA[today.weekday()]
    date_str = f"{weekday_ua}, {today.day}.{today.month:02d}.{today.year}"

    lines = [
        f"🔮 Астро-прогноз на сьогодні — {date_str}",
        "",
        f"{get_phase_emoji(daily_data['moon_phase'])} {get_phase_name_ua(daily_data['moon_phase'])} у {get_sign_name_ua(daily_data['moon_sign'])}",
        "",
        f"📊 Оцінка дня: {label} ({'+' if overall > 0 else ''}{overall})",
    ]

    if recs["best_for"]:
        lines += ["", "✅ Найкраще:"] + [f"  • {x}" for x in recs["best_for"]]
    if recs["avoid"]:
        lines += ["", "⚡ Уникати:"] + [f"  • {x}" for x in recs["avoid"]]
    if warnings:
        lines += ["", "⚠️ Попередження:"] + [f"  • {w}" for w in warnings]
    if recs["tip"]:
        lines += ["", f"💡 Порада: {recs['tip']}"]

    return "\n".join(lines)


def generate_week_report() -> str:
    today = datetime.now()
    birth_data = load_birth_data()

    from datetime import timedelta
    lines = [f"📅 Астро-тиждень з {today.strftime('%d.%m')}:", ""]

    for i in range(7):
        day = today + timedelta(days=i)
        daily = get_daily_data(day, birth_data)
        scores = score_day(daily)
        overall = get_overall_score(scores)
        label = get_day_label(overall)
        phase_emoji = get_phase_emoji(daily["moon_phase"])
        weekday = WEEKDAY_UA[day.weekday()]
        lines.append(f"{phase_emoji} {weekday} {day.strftime('%d.%m')} — {label} ({'+' if overall > 0 else ''}{overall})")

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
    parser.add_argument("--type", choices=["month", "week", "today", "best"], default="today")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--activity", default="finance")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    if args.type == "month":
        path = generate_month_report_v2(args.year, args.month)
        print(f"\nВідкрити: open '{path}'")
    elif args.type == "today":
        report = generate_today_report()
        print(report)
    elif args.type == "week":
        report = generate_week_report()
        print(report)
    elif args.type == "best":
        report = find_best_days(args.activity, args.days)
        print(report)


if __name__ == "__main__":
    main()
