#!/usr/bin/env python3
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_text(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID не налаштовані", file=sys.stderr)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=15)

    if resp.ok:
        print("Повідомлення відправлено в Telegram")
    else:
        print(f"Помилка Telegram: {resp.status_code} {resp.text}", file=sys.stderr)


def send_summary(daily_data: dict) -> None:
    from generate_report import generate_today_report
    message = generate_today_report()
    send_text(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["today", "week"], default="today")
    parser.add_argument("--message", help="Довільне повідомлення")
    args = parser.parse_args()

    if args.message:
        send_text(args.message)
        return

    if args.type == "today":
        from generate_report import generate_today_report
        report = generate_today_report()
        send_text(report)
    elif args.type == "week":
        from generate_report import generate_week_report
        report = generate_week_report()
        send_text(report)


if __name__ == "__main__":
    main()
