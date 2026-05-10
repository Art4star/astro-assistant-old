#!/usr/bin/env python3
"""Telegram bot for astro-assistant. Long polling, no extra dependencies."""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.calculator import get_daily_data, get_month_data
from engine.interpreter import (
    score_day, get_overall_score, get_day_label,
    get_warnings, get_recommendations, ACTIVITY_LABELS
)
from engine.lunar import (
    get_phase_emoji, get_phase_name_ua,
    get_sign_name_ua, get_sign_emoji
)
from generate_report import (
    generate_today_report, generate_week_report,
    find_best_days, generate_month_report,
    load_birth_data, MONTH_NAMES_UA, WEEKDAY_UA
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/tmp/astro-bot.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", ""))
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

COMMANDS = """
/today — прогноз на сьогодні
/tomorrow — прогноз на завтра
/week — тижневий огляд
/month — місячний календар (текст)
/cal — компактний календар місяця
/best — найкращі дні (фінанси)
/best work — найкращі дні для роботи
/best negotiations — переговори
/best content — контент
/best rest — відпочинок
/best health — здоров'я
/best new — нові починання
/help — список команд
""".strip()

ACTIVITY_ALIASES = {
    "фінанси": "finance", "finance": "finance", "fin": "finance",
    "робота": "work_technical", "work": "work_technical", "work_technical": "work_technical",
    "переговори": "negotiations", "negotiations": "negotiations", "neg": "negotiations",
    "контент": "content_publishing", "content": "content_publishing", "content_publishing": "content_publishing",
    "відпочинок": "rest_reflection", "rest": "rest_reflection", "rest_reflection": "rest_reflection",
    "здоров'я": "health_body", "health": "health_body", "health_body": "health_body",
    "нові": "new_beginnings", "new": "new_beginnings", "new_beginnings": "new_beginnings",
}


def tg_get(method: str, **params) -> dict:
    try:
        r = requests.get(f"{API}/{method}", params=params, timeout=30)
        return r.json()
    except Exception as e:
        log.error("tg_get %s: %s", method, e)
        return {}


def tg_post(method: str, **data) -> dict:
    try:
        r = requests.post(f"{API}/{method}", json=data, timeout=15)
        return r.json()
    except Exception as e:
        log.error("tg_post %s: %s", method, e)
        return {}


def send(chat_id, text: str) -> None:
    tg_post("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")


def cmd_today(date: datetime = None) -> str:
    if date is None:
        return generate_today_report()
    birth_data = load_birth_data()
    daily = get_daily_data(date, birth_data)
    scores = score_day(daily)
    overall = get_overall_score(scores)
    label = get_day_label(overall)
    warnings = get_warnings(daily)
    recs = get_recommendations(daily, scores)
    weekday = WEEKDAY_UA[date.weekday()]
    date_str = f"{weekday}, {date.day}.{date.month:02d}.{date.year}"
    lines = [
        f"🔮 Астро-прогноз — {date_str}",
        "",
        f"{get_phase_emoji(daily['moon_phase'])} {get_phase_name_ua(daily['moon_phase'])} у {get_sign_name_ua(daily['moon_sign'])}",
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
        lines += ["", f"💡 {recs['tip']}"]
    return "\n".join(lines)


def cmd_week() -> str:
    return generate_week_report()


def cmd_best(activity: str = "finance") -> str:
    return find_best_days(activity, 30)


def cmd_month() -> str:
    now = datetime.now()
    birth_data = load_birth_data()
    month_data = get_month_data(now.year, now.month, birth_data)

    lines = [f"📅 {MONTH_NAMES_UA[now.month]} {now.year}", ""]

    score_sum = 0
    best_day = None
    best_score = -99
    worst_day = None
    worst_score = 99

    for daily in month_data:
        scores = score_day(daily)
        overall = get_overall_score(scores)
        score_sum += overall
        d = int(daily["date"].split("-")[2])
        if overall > best_score:
            best_score = overall
            best_day = d
        if overall < worst_score:
            worst_score = overall
            worst_day = d

    avg = round(score_sum / len(month_data))
    lines.append(f"📊 Середня оцінка місяця: {'+' if avg >= 0 else ''}{avg} ({get_day_label(avg)})")
    lines.append(f"🏆 Найкращий день: {best_day} ({'+' if best_score >= 0 else ''}{best_score})")
    lines.append(f"😴 Найважчий день: {worst_day} ({'+' if worst_score >= 0 else ''}{worst_score})")

    lines += ["", "Топ-3 активності місяця:"]
    all_scores = {}
    for daily in month_data:
        scores = score_day(daily)
        for act, sc in scores.items():
            all_scores[act] = all_scores.get(act, 0) + sc
    sorted_acts = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    for act, total in sorted_acts[:3]:
        lines.append(f"  • {ACTIVITY_LABELS[act]}: середній {'+' if total//len(month_data) >= 0 else ''}{total//len(month_data)}")

    lines += ["", f"Детальний HTML-звіт: /cal"]
    return "\n".join(lines)


def cmd_cal() -> str:
    now = datetime.now()
    birth_data = load_birth_data()
    month_data = get_month_data(now.year, now.month, birth_data)

    SCORE_EMOJI = {
        lambda s: s > 5: "🟢",
        lambda s: 2 <= s <= 5: "🟡",
        lambda s: -1 <= s < 2: "⬜",
        lambda s: -4 <= s < -1: "🟠",
        lambda s: s < -4: "🔴",
    }

    def score_emoji(s):
        if s > 5: return "🟢"
        if s >= 2: return "🟡"
        if s >= -1: return "⬜"
        if s >= -4: return "🟠"
        return "🔴"

    lines = [f"<b>{MONTH_NAMES_UA[now.month]} {now.year}</b>", ""]
    lines.append("Пн Вт Ср Чт Пт Сб Нд")

    from datetime import date as date_cls
    first_wd = date_cls(now.year, now.month, 1).weekday()

    row = ["  "] * first_wd
    for daily in month_data:
        d = int(daily["date"].split("-")[2])
        scores = score_day(daily)
        overall = get_overall_score(scores)
        emoji = score_emoji(overall)
        phase = get_phase_emoji(daily["moon_phase"])
        marker = "◀" if d == now.day else " "
        row.append(f"{emoji}{str(d).zfill(2)}{marker}")
        if len(row) == 7:
            lines.append(" ".join(row))
            row = []
    if row:
        while len(row) < 7:
            row.append("    ")
        lines.append(" ".join(row))

    lines += [
        "",
        "🟢 Відмінний  🟡 Хороший",
        "⬜ Нейтральний  🟠 Краще почекати  🔴 Відпочинок",
    ]
    return "\n".join(lines)


def handle_message(msg: dict) -> None:
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()

    if not text or not text.startswith("/"):
        return

    if CHAT_ID and chat_id != CHAT_ID:
        log.warning("Ignored message from unknown chat %s", chat_id)
        return

    parts = text.lstrip("/").split()
    command = parts[0].lower().split("@")[0]
    args = parts[1:]

    log.info("Command: /%s %s from chat %s", command, args, chat_id)

    try:
        if command in ("today", "сьогодні"):
            send(chat_id, cmd_today())

        elif command in ("tomorrow", "завтра"):
            tomorrow = datetime.now() + timedelta(days=1)
            send(chat_id, cmd_today(tomorrow))

        elif command in ("week", "тиждень"):
            send(chat_id, cmd_week())

        elif command in ("month", "місяць"):
            send(chat_id, cmd_month())

        elif command in ("cal", "календар"):
            send(chat_id, cmd_cal())

        elif command in ("best", "кращі"):
            raw = args[0].lower() if args else "finance"
            activity = ACTIVITY_ALIASES.get(raw, "finance")
            send(chat_id, cmd_best(activity))

        elif command in ("help", "start", "допомога"):
            send(chat_id, f"🔮 <b>Astro Assistant</b>\n\n{COMMANDS}")

        else:
            send(chat_id, f"Невідома команда. Напишіть /help")

    except Exception as e:
        log.error("Error handling /%s: %s", command, e)
        send(chat_id, f"⚠️ Помилка: {e}")


def main():
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN не налаштований")
        sys.exit(1)

    log.info("Astro Bot запущено (polling)")
    offset = 0

    while True:
        try:
            data = tg_get("getUpdates", offset=offset, timeout=25, allowed_updates=["message"])
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if msg:
                    handle_message(msg)
        except KeyboardInterrupt:
            log.info("Bot зупинено")
            break
        except Exception as e:
            log.error("Polling error: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
