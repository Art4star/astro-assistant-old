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
    """Divide month into 3-4 meaningful segments based on score patterns."""
    month = _month_num(month_data[0])
    mn = MONTH_NAMES_GEN[month]
    days_count = len(month_data)

    def avg_score(days_slice):
        scores = []
        for d in days_slice:
            s = score_day(d)
            scores.append(get_overall_score(s))
        return sum(scores) / len(scores) if scores else 0

    boundaries = [0, 7, 15, 22, days_count]
    periods = []
    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1]
        if start_idx >= days_count:
            break
        slice_ = month_data[start_idx:end_idx]
        if not slice_:
            continue
        avg = avg_score(slice_)
        start_day = _day_num(slice_[0])
        end_day = _day_num(slice_[-1])
        dates_str = f"{start_day}–{end_day} {mn}"

        retro_count = sum(1 for d in slice_ if d.get("mercury_retrograde"))
        voc_count = sum(1 for d in slice_ if d.get("moon_voc"))
        full_moon = any(d.get("moon_phase") == "full" for d in slice_)
        new_moon = any(d.get("moon_phase") == "new" for d in slice_)

        if avg > 4:
            theme = "найсильніше вікно для дій"
        elif avg > 2:
            theme = "активна, сприятлива фаза"
        elif avg > 0:
            theme = "помірний темп, вибіркові дії"
        elif avg > -2:
            theme = "уповільнення, не форсувати"
        else:
            theme = "відпочинок і відновлення"

        if retro_count > 3:
            theme += " · перевіряйте деталі"
        if full_moon:
            theme += " · повний місяць — пік енергії"
        if new_moon:
            theme += " · новий місяць — нові наміри"
        if voc_count > 4:
            theme += " · багато VOC"

        periods.append({"period": dates_str, "theme": theme, "avg": round(avg, 1)})

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


def build_report_sections(month_data: list, birth_data: dict) -> dict:
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
            strongest = None
            for d in month_data:
                if w["start"] <= _day_num(d) <= w["end"]:
                    sc = score_day(d).get(act, 0)
                    if strongest is None or sc > strongest[1]:
                        strongest = (d, sc)
            tip = ""
            if strongest:
                d = strongest[0]
                if not d.get("mercury_retrograde") and not d.get("moon_voc"):
                    tip = "Меркурій прямий, Місяць активний — ідеальний час"
                elif d.get("mercury_retrograde"):
                    tip = "Перевіряйте деталі — Меркурій ретроградний"
                elif d.get("moon_voc"):
                    tip = "Уникайте початків під VOC"
            window_details.append({
                "dates": w["dates"],
                "score": w["score"],
                "hot": w["score"] > 5,
                "tip": tip,
            })

        avoid_strs = [a["dates"] for a in avoid[:2]]

        sections[key] = {
            "label": meta["label"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "windows": window_details,
            "avoid": avoid_strs,
            "has_windows": len(window_details) > 0,
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

    return {
        "month_theme": month_theme,
        "period_overview": period_overview,
        "sections": sections,
        "danger_zones": danger_zones,
        "strongest_day": strongest_day,
        "summary_table": summary_table,
        "name": name,
    }
