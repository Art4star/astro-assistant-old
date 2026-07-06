#!/usr/bin/env python3
"""
Автоматична інтерпретація місячного пакету через Claude Code CLI.
Генерує структурований JSON-аналіз і відправляє ключові інсайти в Telegram.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

OUTPUT_DATA_DIR = os.path.join(BASE_DIR, "output", "data")
SESSIONS_DIR = os.path.join(BASE_DIR, "data", "memory", "sessions")
ASTRO_PROMPT = os.path.join(BASE_DIR, "ASTRO_PROMPT.md")


def get_package_path(year: int, month: int) -> str:
    return os.path.join(OUTPUT_DATA_DIR, f"{year}-{month:02d}-interpret.json")


def build_claude_prompt(year: int, month: int) -> str:
    pkg_path = get_package_path(year, month)
    if not os.path.exists(pkg_path):
        raise FileNotFoundError(f"Пакет не знайдено: {pkg_path}")

    with open(pkg_path, encoding="utf-8") as f:
        package = json.load(f)

    with open(ASTRO_PROMPT, encoding="utf-8") as f:
        system_prompt = f.read()

    from agents.output_schema import get_prompt_addition
    schema_addition = get_prompt_addition()

    prompt = f"""{system_prompt}

{schema_addition}

---

## Дані для аналізу

```json
{json.dumps(package, ensure_ascii=False, indent=2)}
```

Зроби повний астрологічний аналіз на основі цих даних за {year}-{month:02d}.
Відповідай ТІЛЬКИ валідним JSON згідно зі схемою вище. Без прози, без markdown — лише JSON."""

    return prompt


def run_claude(prompt: str) -> str:
    # prompt через stdin: --allowedTools варіадичний і "з'їдає" позиційний аргумент
    cmd = [
        "claude", "-p",
        "--output-format", "text",
        "--no-session-persistence",
        "--allowedTools", "",
    ]

    print(f"[interpret] Запускаю Claude CLI...")
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)  # інакше CLI бере API-ключ (без кредитів) замість PRO-підписки
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=BASE_DIR,
        env=env,
    )

    if result.returncode != 0:
        print(f"[interpret] stderr: {result.stderr[:500]}", file=sys.stderr)
        raise RuntimeError(f"Claude CLI завершився з кодом {result.returncode}")

    return result.stdout.strip()


def extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end])
    return text


def format_telegram_message(data: dict, year: int, month: int) -> str:
    MONTH_UA = {
        1: "січень", 2: "лютий", 3: "березень", 4: "квітень",
        5: "травень", 6: "червень", 7: "липень", 8: "серпень",
        9: "вересень", 10: "жовтень", 11: "листопад", 12: "грудень",
    }

    month_name = MONTH_UA.get(month, str(month))
    confidence = data.get("confidence_overall", "?")

    identity = data.get("identity_resonance", {})
    primary_theme = identity.get("primary_theme", "")
    tensions = identity.get("tension_points", [])

    timing = data.get("timing", {})
    best = timing.get("best_window", {})
    avoid = timing.get("avoid_window", {})

    insights = data.get("three_key_insights", [])

    goals = data.get("goal_alignment", [])

    lines = [
        f"🔮 <b>Астро-аналіз: {month_name} {year}</b>",
        f"📊 Впевненість: {confidence}",
        "",
    ]

    if primary_theme:
        lines.append(f"🎯 <b>Тема місяця:</b> {primary_theme}")
        lines.append("")

    if insights:
        lines.append("💡 <b>Три ключові інсайти:</b>")
        for i, ins in enumerate(insights[:3], 1):
            lines.append(f"  {i}. {ins}")
        lines.append("")

    if best.get("dates"):
        lines.append(f"✅ <b>Вікно можливостей:</b> {best['dates']}")
        if best.get("for"):
            lines.append(f"   Для: {', '.join(best['for'][:3])}")
        if best.get("reason"):
            lines.append(f"   {best['reason']}")
        lines.append("")

    if avoid.get("dates"):
        lines.append(f"⚠️ <b>Уникати:</b> {avoid['dates']}")
        if avoid.get("reason"):
            lines.append(f"   {avoid['reason']}")
        lines.append("")

    if tensions:
        lines.append("🔥 <b>Точки напруги:</b>")
        for t in tensions[:3]:
            lines.append(f"  • {t}")
        lines.append("")

    if goals:
        lines.append("🎯 <b>Цілі:</b>")
        for g in goals[:5]:
            support = g.get("monthly_support", "?")
            icon = {"strong": "💪", "moderate": "👍", "weak": "😐", "blocked": "🚫"}.get(support, "❓")
            lines.append(f"  {icon} {g.get('goal_title', '?')} — {support}")
            if g.get("best_action_this_month"):
                lines.append(f"     → {g['best_action_this_month']}")
        lines.append("")

    lunar = data.get("lunar_rhythm", {})
    if lunar.get("new_moon_focus"):
        lines.append(f"🌑 Новий місяць: {lunar['new_moon_focus']}")
    if lunar.get("full_moon_release"):
        lines.append(f"🌕 Повний місяць: {lunar['full_moon_release']}")

    return "\n".join(lines)


def send_telegram(message: str) -> None:
    from send_telegram import send_text
    send_text(message)


def main():
    parser = argparse.ArgumentParser(description="Автоматична інтерпретація через Claude")
    now = datetime.now()
    parser.add_argument("--year", type=int, default=now.year)
    parser.add_argument("--month", type=int, default=now.month)
    parser.add_argument("--no-telegram", action="store_true", help="Не відправляти в Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Показати prompt без виклику Claude")
    args = parser.parse_args()

    year, month = args.year, args.month
    period = f"{year}-{month:02d}"

    pkg_path = get_package_path(year, month)
    if not os.path.exists(pkg_path):
        print(f"[interpret] Пакет {period}-interpret.json не знайдено. Спершу запусти:")
        print(f"  python generate_report.py --type month --year {year} --month {month}")
        sys.exit(1)

    print(f"[interpret] Період: {period}")
    prompt = build_claude_prompt(year, month)

    if args.dry_run:
        print(f"[interpret] Prompt ({len(prompt)} chars):")
        print(prompt[:2000])
        print("...")
        return

    raw_output = run_claude(prompt)
    print(f"[interpret] Отримано відповідь: {len(raw_output)} chars")

    json_text = extract_json(raw_output)

    from agents.output_schema import validate_output, save_interpretation
    is_valid, data, errors = validate_output(json_text)

    if not is_valid:
        print(f"[interpret] Валідація не пройшла:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        fallback_path = os.path.join(OUTPUT_DATA_DIR, f"{period}-interpretation-raw.txt")
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(raw_output)
        print(f"[interpret] Сирий вивід збережено: {fallback_path}")
        sys.exit(1)

    saved_path = save_interpretation(data, year, month)
    print(f"[interpret] Збережено: {saved_path}")

    if not args.no_telegram:
        message = format_telegram_message(data, year, month)
        print(f"[interpret] Відправляю в Telegram...")
        send_telegram(message)
        print(f"[interpret] Готово!")
    else:
        message = format_telegram_message(data, year, month)
        print("\n" + message)


if __name__ == "__main__":
    main()
