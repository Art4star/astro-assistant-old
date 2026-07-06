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
    get_sign_name_ua, get_sign_emoji, get_sign_in_ua
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

LOCALHOST_PORT = 8765
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")

COMMANDS = """
/today — прогноз на сьогодні
/tomorrow — прогноз на завтра
/week — тижневий огляд
/month — місячний звіт (HTML)
/goals — активні цілі
/best — найкращі дні (фінанси)
/best work — робота
/best negotiations — переговори
/help — список команд

Також можеш писати будь-яке питання — відповім з астро-контекстом.
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


def cmd_today(date=None):
    if date is None:
        return generate_today_report()
    birth_data = load_birth_data()
    daily = get_daily_data(date, birth_data)
    scores = score_day(daily)
    overall = get_overall_score(scores)
    recs = get_recommendations(daily, scores)
    weekday = WEEKDAY_UA[date.weekday()]

    from generate_report import PHASE_GUIDANCE, SIGN_ENERGY
    phase = daily["moon_phase"]
    sign = daily["moon_sign"]

    lines = [f"🔮 {weekday}, {date.day}.{date.month:02d}"]
    lines.append(f"{get_phase_emoji(phase)} {get_phase_name_ua(phase)} {get_sign_in_ua(sign)}")
    lines.append("")

    if overall >= 5:
        lines.append("🟢 День для активних дій.")
    elif overall >= 2:
        lines.append("🟡 Хороший день — дій у своєму темпі.")
    elif overall >= -1:
        lines.append("⚪ Рівний день — можна діяти, але вибірково.")
    elif overall >= -4:
        lines.append("🟠 Краще не форсувати.")
    else:
        lines.append("🔴 День для відпочинку.")

    if recs["best_for"]:
        lines.append(f"✅ Русло дня: {', '.join(recs['best_for'][:3]).lower()}")
    if recs["avoid"]:
        lines.append(f"🚫 Відкласти: {', '.join(recs['avoid'][:2]).lower()}")

    phase_note = PHASE_GUIDANCE.get(phase, "")
    sign_note = SIGN_ENERGY.get(sign, "")
    if phase_note:
        lines.append("")
        lines.append(f"💡 {phase_note}")
        if sign_note:
            lines.append(f"   Фокус: {sign_note}.")
    return "\n".join(lines)


def cmd_week():
    return generate_week_report()


def cmd_best(activity="finance"):
    return find_best_days(activity, 30)


def cmd_month():
    now = datetime.now()
    try:
        from generate_report import generate_month_report_v2
        filepath = generate_month_report_v2(now.year, now.month)
    except Exception as e:
        log.error("Month report generation failed: %s", e)
        return f"⚠️ Помилка генерації: {e}"

    filename = os.path.basename(filepath)
    url = f"http://localhost:{LOCALHOST_PORT}/{filename}"
    return (
        f"📅 Звіт за {MONTH_NAMES_UA[now.month]} {now.year} згенеровано.\n\n"
        f"🔗 {url}"
    )


def cmd_goals():
    goals_path = os.path.join(BASE_DIR, "data", "goals.json")
    if not os.path.exists(goals_path):
        return "Цілей немає. Додай: python3 manage_goals.py add"

    with open(goals_path, encoding="utf-8") as f:
        data = json.load(f)

    active = sorted(data.get("active", []), key=lambda g: g.get("priority", 9))
    if not active:
        return "Активних цілей немає."

    PRIO = {1: "🔴", 2: "🟡", 3: "🟢", 4: "⚪"}
    lines = [f"🎯 Активні цілі ({len(active)}):", ""]

    for g in active:
        emoji = PRIO.get(g.get("priority", 4), "⚪")
        dl = ""
        if g.get("deadline"):
            dl = f" · до {g['deadline'][5:]}"
        lines.append(f"{emoji} {g['title']}{dl}")

        windows = g.get("best_windows", [])
        upcoming = [w for w in windows if w["date"] >= datetime.now().strftime("%Y-%m-%d")]
        if upcoming:
            top = upcoming[0]
            lines.append(f"   📌 найкращий день: {top['date'][5:]} (+{top['score']})")

    completed = data.get("completed", [])
    if completed:
        lines.append(f"\n✅ Завершено: {len(completed)}")

    return "\n".join(lines)


def cmd_ask(question, chat_id):
    """Free dialog with Claude — send question with astro context."""
    birth_data = load_birth_data()
    today = datetime.now()
    daily = get_daily_data(today, birth_data)
    scores = score_day(daily)
    overall = get_overall_score(scores)
    recs = get_recommendations(daily, scores)

    pkg_path = os.path.join(BASE_DIR, "output", "data",
                            f"{today.year}-{today.month:02d}-interpret.json")
    transit_context = ""
    if os.path.exists(pkg_path):
        with open(pkg_path, encoding="utf-8") as f:
            pkg = json.load(f)
        from engine.synthesizer import get_transit_narratives
        narratives = get_transit_narratives(pkg.get("forecast", {}).get("top_transits", []))
        if narratives:
            parts = []
            for n in narratives[:3]:
                parts.append(f"- {n['title']}: {n['impact']} → {n['action']}")
            transit_context = "\n".join(parts)

    goals_path = os.path.join(BASE_DIR, "data", "goals.json")
    goals_text = ""
    if os.path.exists(goals_path):
        with open(goals_path, encoding="utf-8") as f:
            goals = json.load(f).get("active", [])
        if goals:
            goals_text = "\n".join(f"- {g['title']} (до {g.get('deadline', 'без дедлайну')})" for g in goals[:5])

    prompt = f"""Ти — астрологічний асистент. Відповідай українською, лаконічно, практично. Без езотерики.
Ти маєш доступ до Python і можеш запускати розрахунки через Bash.

## Поточний контекст

Сьогодні: {today.strftime('%d.%m.%Y')}, {WEEKDAY_UA[today.weekday()]}
Місяць: {get_phase_name_ua(daily['moon_phase'])} {get_sign_in_ua(daily['moon_sign'])}
Оцінка дня: {overall} ({get_day_label(overall, scores)})
Найкраще для: {', '.join(recs['best_for'][:3]) if recs['best_for'] else 'немає'}
Уникати: {', '.join(recs['avoid'][:2]) if recs['avoid'] else 'немає'}
Меркурій ретро: {'так' if daily.get('mercury_retrograde') else 'ні'}

Активні транзити:
{transit_context or 'немає даних'}

Цілі:
{goals_text or 'немає'}

## Доступні Python-функції (запускай через Bash якщо потрібні розрахунки)

```python
import sys; sys.path.insert(0, '{BASE_DIR}')
from engine.calculator import get_daily_data, get_month_data
from engine.interpreter import score_day, get_overall_score, get_day_label, get_recommendations
from engine.lunar import get_phase_name_ua, get_sign_name_ua
from engine.synthesizer import get_transit_narratives, _make_narrative
import json

birth_data = json.load(open('{BASE_DIR}/data/birth_data.json'))

# Дані на конкретну дату:
from datetime import datetime
daily = get_daily_data(datetime(2027, 3, 15), birth_data)
scores = score_day(daily)

# Транзити за місяць (повний пакет):
from agents.forecast_engine import build_forecast
forecast = build_forecast(birth_data, 2027, 3)
# forecast["transits"] — всі транзити, forecast["critical_windows"] — критичні вікна

# Щоденні дані за місяць:
month_data = get_month_data(2027, 3, birth_data)
```

## Правила

- Якщо питання про конкретну дату або період — РОЗРАХУЙ через Python, не вигадуй
- Якщо питання про майбутнє (місяці, роки) — запусти build_forecast для потрібних місяців
- Не вигадуй позиції планет чи аспекти — завжди рахуй
- Відповідай коротко (до 10 речень), конкретно, з датами і фактами
- Заморожені файли (calculator.py, interpreter.py, chart_parser.py, forecast_engine.py) — лише читай, не змінюй

Питання користувача: {question}"""

    import subprocess
    try:
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text",
             "--dangerously-skip-permissions",
             "--no-session-persistence", prompt],
            capture_output=True, text=True, timeout=300, cwd=BASE_DIR,
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            log.error("Claude CLI error: %s", result.stderr[:300])
            return "⚠️ Не вдалось отримати відповідь від Claude."
    except subprocess.TimeoutExpired:
        return "⚠️ Claude не встиг відповісти (таймаут)."
    except FileNotFoundError:
        return "⚠️ Claude CLI не знайдено."


def handle_message(msg: dict) -> None:
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()

    if not text:
        return

    if CHAT_ID and chat_id != CHAT_ID:
        log.warning("Ignored message from unknown chat %s", chat_id)
        return

    if text.startswith("/"):
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

            elif command in ("goals", "цілі"):
                send(chat_id, cmd_goals())

            elif command in ("best", "кращі"):
                raw = args[0].lower() if args else "finance"
                activity = ACTIVITY_ALIASES.get(raw, "finance")
                send(chat_id, cmd_best(activity))

            elif command in ("help", "start", "допомога"):
                send(chat_id, f"🔮 <b>Astro Assistant</b>\n\n{COMMANDS}")

            else:
                send(chat_id, f"Невідома команда. /help")

        except Exception as e:
            log.error("Error handling /%s: %s", command, e)
            send(chat_id, f"⚠️ Помилка: {e}")
    else:
        log.info("Free question from chat %s: %s", chat_id, text[:80])
        send(chat_id, "🔮 Думаю...")
        try:
            answer = cmd_ask(text, chat_id)
            send(chat_id, answer)
        except Exception as e:
            log.error("Free dialog error: %s", e)
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
