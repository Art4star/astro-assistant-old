#!/usr/bin/env python3
"""CLI for managing personal goals/themes."""

import json
import os
import sys
from datetime import datetime

GOALS_FILE = os.path.join(os.path.dirname(__file__), "data", "goals.json")

PRIORITY_EMOJI = {1: "🔴", 2: "🟡", 3: "🟢"}
CATEGORIES = {
    "career": "Кар'єра / нова роль",
    "negotiations": "Переговори",
    "purchase": "Велика покупка",
    "housing": "Житло / переїзд",
    "documents": "Документи / бюрократія",
    "education": "Навчання / курси",
    "personal": "Особисті стосунки",
    "health": "Здоров'я",
    "finance": "Фінанси / інвестиції",
    "travel": "Поїздки / подорожі",
    "project": "Запуск проєкту",
}

MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}


def load_goals() -> dict:
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"active": [], "completed": [], "paused": []}


def save_goals(data: dict) -> None:
    with open(GOALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_deadline(goal: dict) -> str:
    dl = goal.get("deadline")
    if not dl:
        return ""
    try:
        d = datetime.strptime(dl, "%Y-%m-%d")
        return f"  [дедлайн: {d.day} {MONTH_NAMES_UA[d.month].lower()}]"
    except Exception:
        return f"  [до: {dl}]"


def cmd_list(data: dict) -> None:
    active = sorted(data["active"], key=lambda g: g["priority"])
    print(f"\nАКТИВНІ ТЕМИ ({len(active)})")
    print("━" * 40)
    for g in active:
        emoji = PRIORITY_EMOJI.get(g["priority"], "⚪")
        dl = format_deadline(g)
        print(f"{emoji} [{g['priority']}] {g['id']:<20} — {g['title']}{dl}")

    paused = data.get("paused", [])
    if paused:
        print(f"\n⏸  ВІДКЛАДЕНІ ({len(paused)})")
        for g in paused:
            print(f"   {g['id']:<20} — {g['title']}")

    completed = data.get("completed", [])
    print(f"\n✅ ВИКОНАНІ ({len(completed)})")
    for g in completed[:3]:
        print(f"   {g['id']:<20} — {g['title']}  [{g.get('completed_date', '')}]")
    print()


def cmd_add(data: dict) -> None:
    print("\nДодати нову ціль")
    print("━" * 40)

    goal_id = input("ID (латиницею, без пробілів, напр. learn_python): ").strip()
    if not goal_id:
        print("ID не може бути порожнім")
        return

    title = input("Назва: ").strip()
    if not title:
        print("Назва не може бути порожньою")
        return

    print("\nКатегорії:")
    cat_list = list(CATEGORIES.items())
    for i, (k, v) in enumerate(cat_list, 1):
        print(f"  {i}. {v}")
    cat_input = input("Номер категорії: ").strip()
    try:
        category = cat_list[int(cat_input) - 1][0]
    except (ValueError, IndexError):
        print("Невірний номер")
        return

    priority_input = input("Пріоритет 1-3 [2]: ").strip() or "2"
    priority = int(priority_input) if priority_input in ("1", "2", "3") else 2

    deadline_input = input("Дедлайн РРРР-ММ-ДД (або Enter): ").strip() or None
    notes = input("Нотатки (або Enter): ").strip() or ""

    goal = {
        "id": goal_id,
        "title": title,
        "category": category,
        "priority": priority,
        "added": datetime.now().strftime("%Y-%m-%d"),
        "deadline": deadline_input,
        "notes": notes,
        "status": "active",
        "completed_date": None,
        "best_windows": [],
    }

    data["active"].append(goal)
    save_goals(data)
    print(f"\n✅ Додано: {title}")


def cmd_done(data: dict, goal_id: str) -> None:
    for i, g in enumerate(data["active"]):
        if g["id"] == goal_id:
            g["status"] = "completed"
            g["completed_date"] = datetime.now().strftime("%Y-%m-%d")
            data["completed"].append(g)
            data["active"].pop(i)
            save_goals(data)

            remaining = len(data["active"])
            print(f'\n✅ "{g["title"]}" виконано! ({g["completed_date"]})')
            print(f"\nЗалишилось активних тем: {remaining}")

            if data["active"]:
                next_goal = sorted(data["active"], key=lambda x: x["priority"])[0]
                print(f"Наступний пріоритет: {next_goal['title']}")
            return

    print(f"Ціль '{goal_id}' не знайдена в активних")


def cmd_pause(data: dict, goal_id: str) -> None:
    for i, g in enumerate(data["active"]):
        if g["id"] == goal_id:
            g["status"] = "paused"
            data.setdefault("paused", []).append(g)
            data["active"].pop(i)
            save_goals(data)
            print(f'⏸  "{g["title"]}" відкладено')
            return
    print(f"Ціль '{goal_id}' не знайдена")


def cmd_resume(data: dict, goal_id: str) -> None:
    for i, g in enumerate(data.get("paused", [])):
        if g["id"] == goal_id:
            g["status"] = "active"
            data["active"].append(g)
            data["paused"].pop(i)
            save_goals(data)
            print(f'▶️  "{g["title"]}" відновлено')
            return
    print(f"Ціль '{goal_id}' не знайдена у відкладених")


def cmd_priority(data: dict, goal_id: str, new_priority: int) -> None:
    for g in data["active"]:
        if g["id"] == goal_id:
            g["priority"] = new_priority
            save_goals(data)
            print(f'Пріоритет "{g["title"]}" → {new_priority}')
            return
    print(f"Ціль '{goal_id}' не знайдена")


def cmd_history(data: dict) -> None:
    completed = data.get("completed", [])
    if not completed:
        print("Виконаних цілей немає")
        return
    print(f"\nВИКОНАНІ ({len(completed)})")
    print("━" * 40)
    for g in completed:
        print(f"✅ {g['completed_date']}  {g['title']}")
    print()


def main():
    args = sys.argv[1:]
    if not args:
        print("Використання: manage_goals.py {list|add|done|pause|resume|priority|history} [id] [значення]")
        sys.exit(0)

    data = load_goals()
    cmd = args[0]

    if cmd == "list":
        cmd_list(data)
    elif cmd == "add":
        cmd_add(data)
    elif cmd == "done":
        if len(args) < 2:
            print("Вкажіть ID: manage_goals.py done <id>")
        else:
            cmd_done(data, args[1])
    elif cmd == "pause":
        if len(args) < 2:
            print("Вкажіть ID: manage_goals.py pause <id>")
        else:
            cmd_pause(data, args[1])
    elif cmd == "resume":
        if len(args) < 2:
            print("Вкажіть ID: manage_goals.py resume <id>")
        else:
            cmd_resume(data, args[1])
    elif cmd == "priority":
        if len(args) < 3:
            print("Вкажіть ID і пріоритет: manage_goals.py priority <id> <1-3>")
        else:
            cmd_priority(data, args[1], int(args[2]))
    elif cmd == "history":
        cmd_history(data)
    else:
        print(f"Невідома команда: {cmd}")


if __name__ == "__main__":
    main()
