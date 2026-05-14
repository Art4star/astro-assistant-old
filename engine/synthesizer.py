from datetime import datetime, date
import calendar as cal_module
from typing import List, Dict, Optional

from engine.interpreter import score_day, get_overall_score, ACTIVITY_LABELS

MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}
MONTH_NAMES_GEN = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}


def _day_num(daily: dict) -> int:
    return int(daily["date"].split("-")[2])


def _month_num(daily: dict) -> int:
    return int(daily["date"].split("-")[1])


def find_windows(month_data: list, activity: str, min_score: int = 2) -> list:
    """Find date ranges where score for activity >= min_score (max 1-day gap allowed)."""
    month = _month_num(month_data[0])
    scored = []
    for d in month_data:
        scores = score_day(d)
        sc = scores.get(activity, 0)
        scored.append((_day_num(d), sc))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc = scored[i]
        if sc >= min_score:
            start = day_num
            end = day_num
            max_sc = sc
            j = i + 1
            while j < len(scored):
                next_day, next_sc = scored[j]
                gap = next_day - end
                if next_sc >= min_score:
                    end = next_day
                    max_sc = max(max_sc, next_sc)
                    j += 1
                elif gap <= 2 and j + 1 < len(scored) and scored[j + 1][1] >= min_score:
                    j += 1
                else:
                    break
            if end - start >= 1:
                mn = MONTH_NAMES_GEN[month]
                dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
                windows.append({
                    "dates": dates_str,
                    "score": max_sc,
                    "start": start,
                    "end": end,
                    "days": list(range(start, end + 1)),
                })
            i = j
        else:
            i += 1

    windows.sort(key=lambda x: x["score"], reverse=True)
    return windows


def find_avoid_windows(month_data: list, activity: str, max_score: int = -2) -> list:
    """Find date ranges where score for activity <= max_score."""
    month = _month_num(month_data[0])
    scored = []
    for d in month_data:
        scores = score_day(d)
        sc = scores.get(activity, 0)
        scored.append((_day_num(d), sc))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc = scored[i]
        if sc <= max_score:
            start = day_num
            end = day_num
            min_sc = sc
            j = i + 1
            while j < len(scored):
                next_day, next_sc = scored[j]
                gap = next_day - end
                if next_sc <= max_score:
                    end = next_day
                    min_sc = min(min_sc, next_sc)
                    j += 1
                elif gap <= 2 and j + 1 < len(scored) and scored[j + 1][1] <= max_score:
                    j += 1
                else:
                    break
            if end - start >= 0:
                mn = MONTH_NAMES_GEN[month]
                dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
                windows.append({
                    "dates": dates_str,
                    "score": min_sc,
                    "start": start,
                    "end": end,
                })
            i = j
        else:
            i += 1
    return windows


def get_period_overview(month_data: list) -> list:
    """Divide month into meaningful periods based on actual lunar phase transitions."""
    month = _month_num(month_data[0])
    mn = MONTH_NAMES_GEN[month]
    days_count = len(month_data)

    # --- Збираємо ключові події ---
    events = {}  # day_num -> list of event strings

    prev_phase = None
    for d in month_data:
        day = _day_num(d)
        phase = d.get("moon_phase")
        retro = d.get("mercury_retrograde")

        if phase != prev_phase:
            if phase == "new":
                events.setdefault(day, []).append("new_moon")
            elif phase == "full":
                events.setdefault(day, []).append("full_moon")
            elif phase == "first_quarter":
                events.setdefault(day, []).append("first_quarter")
            elif phase == "last_quarter":
                events.setdefault(day, []).append("last_quarter")
            elif phase == "waxing_crescent" and prev_phase == "new":
                events.setdefault(day, []).append("waxing_start")
            elif phase == "waning_gibbous" and prev_phase == "full":
                events.setdefault(day, []).append("waning_start")
            elif phase == "balsamic":
                events.setdefault(day, []).append("balsamic")
        prev_phase = phase

    # Межі відрізків — дні ключових подій
    boundary_days = sorted(set([1] + list(events.keys()) + [days_count]))

    # Мерджимо суміжні межі що стоять менш ніж 3 дні окремо
    merged = [boundary_days[0]]
    for b in boundary_days[1:]:
        if b - merged[-1] >= 3:
            merged.append(b)
    merged.append(days_count + 1)

    # --- Будуємо відрізки ---
    def avg_score(slice_):
        vals = [get_overall_score(score_day(d)) for d in slice_]
        return sum(vals) / len(vals) if vals else 0

    def retro_days_in(slice_):
        return sum(1 for d in slice_ if d.get("mercury_retrograde"))

    def voc_days_in(slice_):
        return sum(1 for d in slice_ if d.get("moon_voc"))

    periods = []
    for i in range(len(merged) - 1):
        start_day = merged[i]
        end_day = merged[i + 1] - 1
        if end_day < start_day:
            continue

        slice_ = [d for d in month_data if start_day <= _day_num(d) <= end_day]
        if not slice_:
            continue

        avg = avg_score(slice_)
        retro = retro_days_in(slice_)
        voc = voc_days_in(slice_)
        period_events = []
        for day in range(start_day, end_day + 1):
            period_events += events.get(day, [])

        dates_str = f"{start_day}–{end_day} {mn}" if start_day != end_day else f"{start_day} {mn}"

        # Визначаємо тему за подіями і score
        parts = []

        if "new_moon" in period_events:
            parts.append("🌑 Новий місяць — час нових намірів і починань")
        elif "full_moon" in period_events:
            parts.append("🌕 Повний місяць — емоційний пік, кульмінація справ")
        elif "first_quarter" in period_events:
            parts.append("🌓 Перша чверть — подолання першого опору")
        elif "last_quarter" in period_events:
            parts.append("🌗 Остання чверть — час підсумків і відпускання")
        elif "balsamic" in period_events:
            parts.append("🌘 Бальзамічна фаза — відпочинок, не починати нового")
        elif "waxing_start" in period_events:
            parts.append("🌒 Місяць росте — сприятливо для дій і просування")
        elif "waning_start" in period_events:
            parts.append("🌖 Місяць спадає — завершення, аналіз, відпочинок")

        if retro > len(slice_) // 2:
            parts.append("☿ Меркурій ретро — перевіряйте деталі, не підписуйте")
        if voc > len(slice_) // 2:
            parts.append("🌀 Багато VOC — плануйте важливе заздалегідь")

        if not parts:
            if avg > 3:
                parts.append("Активна, сприятлива фаза для дій")
            elif avg > 1:
                parts.append("Помірний темп, обирайте моменти")
            elif avg > -1:
                parts.append("Нейтральний фон, без різких кроків")
            else:
                parts.append("Краще уникати великих рішень")

        theme = " · ".join(parts)
        periods.append({"period": dates_str, "theme": theme})

    return periods


def get_month_theme(month_data: list, birth_data: dict) -> dict:
    """Determine main astrological theme of the month based on dominant patterns."""
    all_scores = {act: 0 for act in ACTIVITY_LABELS}
    retro_planets = set()
    voc_days = 0
    full_moon_days = []
    new_moon_days = []
    month = _month_num(month_data[0])
    year = int(month_data[0]["date"].split("-")[0])

    for d in month_data:
        scores = score_day(d)
        for act, sc in scores.items():
            all_scores[act] += sc
        for p in ["mercury", "venus", "mars", "jupiter", "saturn"]:
            if d.get(f"{p}_retrograde"):
                retro_planets.add(p)
        if d.get("moon_voc"):
            voc_days += 1
        if d.get("moon_phase") == "full":
            full_moon_days.append(_day_num(d))
        if d.get("moon_phase") == "new":
            new_moon_days.append(_day_num(d))

    sorted_acts = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    top_acts = [a for a, _ in sorted_acts[:3]]
    worst_acts = [a for a, s in sorted_acts if s < 0]

    mn = MONTH_NAMES_UA[month]
    mn_gen = MONTH_NAMES_GEN[month]

    THEMES = {
        ("negotiations", "content_publishing", "work_technical"): {
            "title": "Місяць комунікацій і дій",
            "subtitle": "ясність думки, переконлива мова, видимість результатів",
            "mantra": f"Я говорю — мене чують. Я дію — результат видно.",
        },
        ("finance", "new_beginnings", "work_technical"): {
            "title": "Закладання нового фундаменту",
            "subtitle": "не про хаотичний ривок, а про стабілізацію і ріст",
            "mantra": f"Я не виживаю. Я починаю будувати.",
        },
        ("rest_reflection", "health_body"): {
            "title": "Місяць відновлення і переосмислення",
            "subtitle": "тіло і психіка просять уваги — варто прислухатись",
            "mantra": f"Зупинитись — це теж рух.",
        },
        ("finance", "negotiations"): {
            "title": "Місяць фінансових рішень",
            "subtitle": "гроші, угоди і стратегії виходять на перший план",
            "mantra": f"Чіткість у домовленостях — основа для зростання.",
        },
    }

    title = f"Місяць рівноваги та точності"
    subtitle = "важливо обирати правильні моменти для правильних дій"
    mantra = f"Не все одразу — але кожне вчасно."

    for key_acts, theme_data in THEMES.items():
        if all(a in top_acts for a in key_acts[:2]):
            title = theme_data["title"]
            subtitle = theme_data["subtitle"]
            mantra = theme_data["mantra"]
            break

    core_themes = [ACTIVITY_LABELS[a] for a in top_acts]

    bullets = []
    name = birth_data.get("name", "Ти")
    if "negotiations" in top_acts or "content_publishing" in top_acts:
        bullets.append(f"сприятливий час для переговорів і публічності")
    if "finance" in top_acts:
        bullets.append(f"фінансові рішення мають підтримку планет")
    if "new_beginnings" in top_acts:
        bullets.append(f"нові проєкти і починання можуть злетіти")
    if "rest_reflection" in top_acts:
        bullets.append(f"тіло і психіка просять відновлення")
    if "mercury" in retro_planets:
        bullets.append(f"Меркурій ретроградний — перевіряйте деталі, не поспішайте з підписами")
    if voc_days > 10:
        bullets.append(f"багато Місяць-без-курсу: плануйте важливе заздалегідь")
    if full_moon_days:
        bullets.append(f"Повний місяць {full_moon_days[0]} {mn_gen} — пік емоцій і кульмінація справ")

    if not bullets:
        bullets = ["рівномірний розподіл енергії протягом місяця"]

    return {
        "title": title,
        "subtitle": subtitle,
        "core_themes": core_themes,
        "mantra": mantra,
        "bullets": bullets,
        "retro_planets": list(retro_planets),
        "voc_days": voc_days,
        "full_moon_days": full_moon_days,
        "new_moon_days": new_moon_days,
        "month_name": mn,
        "year": year,
    }


def get_strongest_day(month_data: list) -> dict:
    """Find the single best day of the month."""
    month = _month_num(month_data[0])
    best = None
    best_score = -99
    for d in month_data:
        scores = score_day(d)
        overall = get_overall_score(scores)
        if overall > best_score:
            best_score = overall
            best = (d, scores, overall)

    if not best:
        return {}

    d, scores, overall = best
    day_num = _day_num(d)
    mn = MONTH_NAMES_GEN[month]
    year = int(d["date"].split("-")[0])

    sorted_acts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_for = [ACTIVITY_LABELS[a] for a, s in sorted_acts[:3] if s > 0]

    from engine.lunar import get_phase_name_ua, get_sign_name_ua
    phase_name = get_phase_name_ua(d["moon_phase"])
    sign_name = get_sign_name_ua(d["moon_sign"])

    return {
        "date": f"{day_num} {mn} {year}",
        "day_num": day_num,
        "score": overall,
        "best_for": best_for,
        "moon": f"{phase_name} у {sign_name}",
        "mercury_direct": not d.get("mercury_retrograde"),
        "moon_voc": d.get("moon_voc"),
    }


def get_danger_zones(month_data: list) -> list:
    """Find multi-day periods that are bad across multiple activities."""
    month = _month_num(month_data[0])
    mn = MONTH_NAMES_GEN[month]

    zones = []
    i = 0
    while i < len(month_data):
        d = month_data[i]
        scores = score_day(d)
        overall = get_overall_score(scores)
        if overall <= -2:
            start = _day_num(d)
            end = start
            reasons = []
            avoids = []

            if d.get("mercury_retrograde"):
                reasons.append("Меркурій ретроградний")
                avoids.append("підписання документів")
            if d.get("moon_voc"):
                reasons.append("Місяць без курсу")
                avoids.append("важливі рішення")
            if scores.get("finance", 0) <= -3:
                avoids.append("фінансові операції")
            if scores.get("negotiations", 0) <= -3:
                avoids.append("переговори і угоди")

            j = i + 1
            while j < len(month_data):
                next_d = month_data[j]
                next_scores = score_day(next_d)
                next_overall = get_overall_score(next_scores)
                if next_overall <= -1:
                    end = _day_num(next_d)
                    j += 1
                else:
                    break

            if end - start >= 1:
                dates_str = f"{start}–{end} {mn}"
                if not reasons:
                    reasons.append("складне планетарне поєднання")
                if not avoids:
                    avoids.append("важливі починання")
                zones.append({
                    "dates": dates_str,
                    "reasons": reasons,
                    "avoid": avoids[:3],
                    "tip": "Використайте цей час для планування і відпочинку",
                })
            i = j
        else:
            i += 1

    return zones[:3]


def build_goal_sections(month_data: list, goals: list, birth_data: dict) -> list:
    """Build personalized goal cards for active goals."""
    from engine.goal_matcher import (
        find_best_windows_in_month, find_avoid_windows_for_goal,
        get_warnings_for_goal, PRIORITY_EMOJI
    )
    from datetime import datetime

    month = _month_num(month_data[0])
    year = int(month_data[0]["date"].split("-")[0])
    mn_gen = MONTH_NAMES_GEN[month]

    active = sorted(
        [g for g in goals if g.get("status") == "active"],
        key=lambda g: g.get("priority", 9)
    )

    goal_cards = []
    for goal in active:
        favorable = find_best_windows_in_month(goal, month_data)
        avoid = find_avoid_windows_for_goal(goal, month_data)
        windows = sorted(favorable + avoid, key=lambda w: w["start"])
        warnings = get_warnings_for_goal(goal, month_data)
        priority = goal.get("priority", 3)
        emoji = PRIORITY_EMOJI.get(priority, "⚪")

        deadline_str = ""
        if goal.get("deadline"):
            try:
                dl = datetime.strptime(goal["deadline"], "%Y-%m-%d")
                if dl.year == year and dl.month == month:
                    deadline_str = f"{dl.day} {MONTH_NAMES_GEN[dl.month]}"
            except Exception:
                pass

        goal_cards.append({
            "id": goal["id"],
            "title": goal["title"],
            "category": goal["category"],
            "priority": priority,
            "priority_emoji": emoji,
            "deadline": deadline_str,
            "notes": goal.get("notes", ""),
            "windows": windows,
            "warnings": warnings,
            "has_windows": len(windows) > 0,
        })

    return goal_cards


def build_report_sections(month_data: list, birth_data: dict, goals: list = None) -> dict:
    """Main function — builds full structure for the report template."""
    month_theme = get_month_theme(month_data, birth_data)
    period_overview = get_period_overview(month_data)
    strongest_day = get_strongest_day(month_data)
    danger_zones = get_danger_zones(month_data)

    SPHERE_ACTIVITIES = {
        "negotiations": {
            "label": "Переговори / Керівництво / Вплив",
            "emoji": "💼",
            "color": "#3b82f6",
            "activity": "negotiations",
        },
        "finance": {
            "label": "Фінанси / Покупки / Рішення",
            "emoji": "💰",
            "color": "#f59e0b",
            "activity": "finance",
        },
        "new_beginnings": {
            "label": "Нові починання",
            "emoji": "🚀",
            "color": "#22c55e",
            "activity": "new_beginnings",
        },
        "health_body": {
            "label": "Здоров'я / Відновлення",
            "emoji": "🧘",
            "color": "#06b6d4",
            "activity": "health_body",
        },
        "housing": {
            "label": "Переїзд / Житло",
            "emoji": "🏡",
            "color": "#a855f7",
            "activity": "new_beginnings",
        },
        "documents": {
            "label": "Документи / Бюрократія",
            "emoji": "🚗",
            "color": "#6b7280",
            "activity": "work_technical",
        },
    }

    sections = {}
    for key, meta in SPHERE_ACTIVITIES.items():
        act = meta["activity"]
        windows = find_windows(month_data, act, min_score=2)
        avoid = find_avoid_windows(month_data, act, max_score=-2)

        window_details = []
        for w in windows[:3]:
            days_in_window = [d for d in month_data if w["start"] <= _day_num(d) <= w["end"]]

            # Найкращий день без VOC і без ретро — для позитивного tip
            best_clean = None
            for d in days_in_window:
                sc = score_day(d).get(act, 0)
                if not d.get("moon_voc") and not d.get("mercury_retrograde"):
                    if best_clean is None or sc > best_clean[1]:
                        best_clean = (d, sc)

            # Підрахунок VOC і ретро днів у вікні
            voc_days = sum(1 for d in days_in_window if d.get("moon_voc"))
            retro_days = sum(1 for d in days_in_window if d.get("mercury_retrograde"))
            total = len(days_in_window)

            tip = ""
            if best_clean:
                tip = "Місяць активний — ідеальний час для дій"
            elif retro_days == total:
                tip = "Весь відрізок — Меркурій ретро, діяти обережно"

            # Попередження — окремо від tip
            warnings = []
            if voc_days > 0:
                warnings.append(f"⚠ {voc_days} VOC-{'день' if voc_days == 1 else 'дні'} у вікні — уникайте початків саме тоді")
            if retro_days > 0 and retro_days < total:
                warnings.append(f"⚠ Меркурій ретро {retro_days}д — перевіряйте деталі")

            sc = w["score"]
            window_details.append({
                "dates": w["dates"],
                "score": sc,
                "emoji": "🔥" if sc >= 6 else ("🟢" if sc >= 3 else "🟡"),
                "level": "hot" if sc >= 6 else ("good" if sc >= 3 else "mild"),
                "reasons": [tip] if tip else [],
                "warnings": warnings,
                "start": w["start"],
                "end": w["end"],
            })

        avoid_details = []
        for a in avoid[:2]:
            avoid_details.append({
                "dates": a["dates"],
                "score": a["score"],
                "emoji": "❌",
                "level": "avoid",
                "reasons": [],
                "warnings": [],
                "start": a["start"],
                "end": a["end"],
            })

        all_windows = sorted(window_details + avoid_details, key=lambda w: w["start"])

        sections[key] = {
            "label": meta["label"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "windows": all_windows,
            "has_windows": len(all_windows) > 0,
        }

    summary_table = []
    for key, sec in sections.items():
        if sec["windows"]:
            best_dates = ", ".join(w["dates"].split(" ")[0] for w in sec["windows"][:2])
            summary_table.append({
                "sphere": sec["emoji"] + " " + sec["label"].split("/")[0].strip(),
                "best": best_dates,
            })
    avoid_all = get_danger_zones(month_data)
    if avoid_all:
        avoid_dates = ", ".join(z["dates"].split(" ")[0] for z in avoid_all[:2])
        summary_table.append({
            "sphere": "⚠️ Обережність",
            "best": avoid_dates,
        })

    name = birth_data.get("name", "")

    goal_cards = build_goal_sections(month_data, goals or [], birth_data) if goals else []

    return {
        "month_theme": month_theme,
        "period_overview": period_overview,
        "sections": sections,
        "danger_zones": danger_zones,
        "strongest_day": strongest_day,
        "summary_table": summary_table,
        "name": name,
        "goal_cards": goal_cards,
    }
