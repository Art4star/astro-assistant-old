from datetime import datetime
from typing import Optional

# Умови без вагових коефіцієнтів: (поле, значення, пояснення)
# Ваги призначаються в _score_goal_day: +2 за best, -3 за avoid
# mercury_direct / venus_direct — базовий стан, не позитивний сигнал:
#   тому вони ТІЛЬКИ в avoid (як mercury_retrograde = -X)
GOAL_ASTRO_MAP = {
    "career": {
        "best_conditions": [
            ("sun_sign", ["aries", "capricorn", "leo"], "висока сонячна енергія для лідерства"),
            ("jupiter_aspect", ["conjunction", "trine", "sextile"], "Юпітер розширює можливості"),
            ("moon_phase", ["waxing_gibbous", "full"], "зростаючий місяць — видимість"),
            ("saturn_aspect", ["trine", "sextile"], "Сатурн дає структуру і авторитет"),
        ],
        "avoid_conditions": [
            ("saturn_aspect", ["square", "opposition"], "Сатурн блокує просування"),
            ("mercury_retrograde", True, "переговори про умови краще відкласти"),
            ("moon_phase", ["balsamic"], "не час для нових кроків"),
        ],
        "timing_note": "Найкраще діяти коли Юпітер аспектує натальне Сонце",
    },
    "negotiations": {
        "best_conditions": [
            ("venus_aspect", ["trine", "sextile", "conjunction"], "Венера пом'якшує і приваблює"),
            ("moon_sign", ["gemini", "libra", "aquarius"], "повітряні знаки — дипломатія"),
            ("moon_phase", ["waxing_crescent", "first_quarter"], "зростання — хороший момент для прохань"),
            ("jupiter_aspect", ["trine", "sextile"], "Юпітер розширює можливості домовленостей"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "КРИТИЧНО: не підписувати, не домовлятись"),
            ("moon_voc", True, "рішення не матимуть сили"),
            ("mars_aspect", ["square", "opposition"], "конфліктний фон"),
            ("saturn_aspect", ["square", "opposition"], "жорсткість, опір з боку іншої сторони"),
        ],
        "timing_note": "Меркурій ретро = автоматична заборона на будь-які переговори",
    },
    "purchase": {
        "best_conditions": [
            ("moon_phase", ["waxing_gibbous", "first_quarter"], "зростаючий місяць — добре для придбання"),
            ("moon_sign", ["taurus", "virgo", "capricorn"], "земні знаки — практичність"),
            ("jupiter_aspect", ["trine", "sextile"], "Юпітер приносить вигідні умови"),
            ("venus_aspect", ["trine", "sextile"], "Венера сприяє вигідній угоді"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "техніка, документи — ризиковано"),
            ("venus_retrograde", True, "КРИТИЧНО: не купувати дорогі речі"),
            ("moon_voc", True, "угода може мати приховані проблеми"),
            ("saturn_aspect", ["square"], "затримки, прихована бюрократія"),
        ],
        "timing_note": "Венера ретро — найгірший час для великих покупок",
    },
    "documents": {
        "best_conditions": [
            ("moon_sign", ["virgo", "capricorn", "gemini"], "точність і порядок"),
            ("saturn_aspect", ["trine", "sextile"], "система і держструктури сприяють"),
            ("moon_phase", ["waxing_crescent", "first_quarter"], "зростаюча енергія — документи рухаються"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "документи губляться, помилки, затримки"),
            ("moon_voc", True, "не подавати заяви"),
            ("saturn_aspect", ["square", "opposition"], "бюрократичний опір"),
        ],
        "timing_note": "Меркурій ретро = 100% затримка в бюрократії",
    },
    "education": {
        "best_conditions": [
            ("jupiter_aspect", ["conjunction", "trine", "sextile"], "Юпітер — планета навчання"),
            ("moon_sign", ["gemini", "sagittarius", "virgo"], "допитливість і систематизація"),
            ("moon_phase", ["new", "waxing_crescent"], "новий цикл — ідеально для старту"),
            ("mercury_aspect", ["trine", "sextile"], "Меркурій сприяє засвоєнню"),
        ],
        "avoid_conditions": [
            ("moon_phase", ["balsamic"], "не час для нового навчання"),
            ("mercury_retrograde", True, "труднощі з концентрацією і розумінням"),
        ],
        "timing_note": "Юпітер транзит до натального Меркурія = найкращий рік для навчання",
    },
    "personal": {
        "best_conditions": [
            ("venus_aspect", ["trine", "sextile", "conjunction"], "Венера активна — тяга і симпатія"),
            ("moon_sign", ["taurus", "libra", "cancer", "pisces"], "романтичний фон"),
            ("moon_phase", ["full", "waxing_gibbous"], "повний місяць підсилює почуття"),
            ("jupiter_aspect", ["conjunction", "trine"], "розширення, радість, удача"),
        ],
        "avoid_conditions": [
            ("venus_retrograde", True, "стосунки заходять у глухий кут"),
            ("saturn_aspect", ["conjunction", "square"], "холодність, дистанція"),
            ("mars_aspect", ["square", "opposition"], "конфлікти, роздратування"),
            ("moon_voc", True, "зустріч не матиме продовження"),
        ],
        "timing_note": "Венера ретро — час переосмислення, не нових романів",
    },
    "housing": {
        "best_conditions": [
            ("moon_sign", ["cancer", "taurus", "scorpio"], "місяць у домашніх знаках"),
            ("moon_phase", ["waxing_crescent", "first_quarter"], "зростання для нового місця"),
            ("saturn_aspect", ["trine", "sextile"], "стабільна основа"),
            ("venus_aspect", ["trine", "sextile"], "Венера сприяє комфортним угодам"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "документи, договори — проблеми"),
            ("moon_voc", True, "підписання без сили"),
            ("saturn_aspect", ["square", "opposition"], "затримки, бюрократія"),
        ],
        "timing_note": "Місяць у Раку або Тельці = ідеальний час для питань житла",
    },
    "health": {
        "best_conditions": [
            ("moon_sign", ["virgo", "scorpio"], "Діва — деталі, Скорпіон — глибоке лікування"),
            ("moon_phase", ["waxing_crescent", "new"], "початок лікування на зростаючому"),
            ("sun_aspect", ["trine", "sextile"], "вітальна сила"),
            ("jupiter_aspect", ["trine", "sextile"], "Юпітер підтримує відновлення"),
        ],
        "avoid_conditions": [
            ("moon_voc", True, "не оперуватись, не починати лікування"),
            ("mars_aspect", ["square", "opposition"], "запальні процеси, травми"),
            ("saturn_aspect", ["square"], "хронічна втома, спротив лікуванню"),
        ],
        "timing_note": "Місяць у знаку органу що лікуєш — уникай хірургії",
    },
    "finance": {
        "best_conditions": [
            ("jupiter_aspect", ["trine", "sextile", "conjunction"], "Юпітер = прибуток"),
            ("moon_phase", ["waxing_gibbous", "full"], "зростаюча енергія для вкладень"),
            ("moon_sign", ["taurus", "capricorn", "scorpio"], "фінансові знаки"),
            ("venus_aspect", ["trine", "sextile"], "Венера приносить ресурс"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "договори, угоди — ризик"),
            ("saturn_aspect", ["square", "opposition"], "обмеження, витрати"),
            ("moon_voc", True, "фінансові рішення без реального результату"),
        ],
        "timing_note": "Юпітер ретро = час перегляду, не нових вкладень",
    },
    "travel": {
        "best_conditions": [
            ("jupiter_aspect", ["trine", "sextile"], "Юпітер = далекі подорожі"),
            ("moon_sign", ["sagittarius", "gemini", "aquarius"], "мобільність і пригоди"),
            ("moon_phase", ["waxing_crescent", "first_quarter"], "зростаюча енергія для руху"),
        ],
        "avoid_conditions": [
            ("mercury_retrograde", True, "скасування рейсів, плутанина"),
            ("saturn_aspect", ["square"], "затримки, обмеження"),
            ("moon_voc", True, "подорож без мети або результату"),
        ],
        "timing_note": "Меркурій ретро під час поїздки = гарантовані проблеми",
    },
    "project": {
        "best_conditions": [
            ("moon_phase", ["new", "waxing_crescent"], "новий місяць — ідеальний старт"),
            ("mars_aspect", ["trine", "sextile"], "Марс дає енергію і рух"),
            ("jupiter_aspect", ["conjunction", "trine"], "Юпітер розширює масштаб"),
            ("sun_aspect", ["trine", "sextile"], "сонячна підтримка"),
        ],
        "avoid_conditions": [
            ("moon_phase", ["balsamic", "last_quarter"], "не час для старту"),
            ("saturn_aspect", ["square", "opposition"], "блоки і опір"),
            ("mercury_retrograde", True, "плани розсипаються"),
        ],
        "timing_note": "Новий місяць + Юпітер трин = найкращий старт проєкту в році",
    },
}

PRIORITY_EMOJI = {1: "🔴", 2: "🟡", 3: "🟢"}

MONTH_NAMES_GEN = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}
MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}


def _check_condition(daily_data: dict, field: str, value) -> bool:
    val = daily_data.get(field)
    if val is None:
        return False
    if isinstance(value, list):
        return val in value
    return val == value


BEST_WEIGHT = +2
AVOID_WEIGHT = -3


def _score_goal_day(category: str, daily_data: dict):
    rules = GOAL_ASTRO_MAP.get(category, {})
    score = 0
    reasons = []
    for field, values, explanation in rules.get("best_conditions", []):
        if _check_condition(daily_data, field, values):
            score += BEST_WEIGHT
            reasons.append(explanation)
    for field, values, explanation in rules.get("avoid_conditions", []):
        if _check_condition(daily_data, field, values):
            score += AVOID_WEIGHT
            reasons.append(f"⚠ {explanation}")
    return score, reasons


def find_best_windows_in_month(goal: dict, month_data: list) -> list:
    category = goal.get("category", "")
    month = int(month_data[0]["date"].split("-")[1])
    mn = MONTH_NAMES_GEN[month]

    scored = []
    for d in month_data:
        day_num = int(d["date"].split("-")[2])
        sc, reasons = _score_goal_day(category, d)
        scored.append((day_num, sc, reasons, d))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc, reasons, d = scored[i]
        if sc >= 2:
            start = day_num
            end = day_num
            max_sc = sc
            best_reasons = reasons[:]
            j = i + 1
            while j < len(scored):
                nd, nsc, nr, nd_data = scored[j]
                gap = nd - end
                if nsc >= 2:
                    end = nd
                    if nsc > max_sc:
                        max_sc = nsc
                        best_reasons = nr[:]
                    j += 1
                elif gap <= 2 and j + 1 < len(scored) and scored[j + 1][1] >= 2:
                    j += 1
                else:
                    break
            if end >= start:
                dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
                pos_reasons = [r for r in best_reasons if not r.startswith("⚠")]
                neg_reasons = [r for r in best_reasons if r.startswith("⚠")]
                windows.append({
                    "dates": dates_str,
                    "score": max_sc,
                    "emoji": "🔥" if max_sc >= 6 else ("🟢" if max_sc >= 3 else "🟡"),
                    "level": "hot" if max_sc >= 6 else ("good" if max_sc >= 3 else "mild"),
                    "reasons": pos_reasons[:2],
                    "warnings": neg_reasons[:1],
                    "start": start,
                    "end": end,
                })
            i = j
        else:
            i += 1

    windows.sort(key=lambda x: x["start"])
    return windows[:3]


def find_avoid_windows_for_goal(goal: dict, month_data: list) -> list:
    """Find date ranges to avoid for this goal."""
    category = goal.get("category", "")
    month = int(month_data[0]["date"].split("-")[1])
    mn = MONTH_NAMES_GEN[month]

    scored = []
    for d in month_data:
        day_num = int(d["date"].split("-")[2])
        sc, reasons = _score_goal_day(category, d)
        scored.append((day_num, sc, reasons, d))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc, reasons, d = scored[i]
        if sc <= -2:
            start = day_num
            end = day_num
            min_sc = sc
            bad_reasons = [r[2:].strip() for r in reasons if r.startswith("⚠")]
            j = i + 1
            while j < len(scored):
                nd, nsc, nr, _ = scored[j]
                if nsc <= -2:
                    end = nd
                    if nsc < min_sc:
                        min_sc = nsc
                        bad_reasons = [r[2:].strip() for r in nr if r.startswith("⚠")]
                    j += 1
                elif nd - end <= 2 and j + 1 < len(scored) and scored[j + 1][1] <= -2:
                    j += 1
                else:
                    break
            dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
            windows.append({
                "dates": dates_str,
                "score": min_sc,
                "emoji": "❌",
                "level": "avoid",
                "reasons": bad_reasons[:2],
                "warnings": [],
                "start": start,
                "end": end,
            })
            i = j
        else:
            i += 1

    return windows[:2]


def get_warnings_for_goal(goal: dict, month_data: list) -> list:
    category = goal.get("category", "")
    rules = GOAL_ASTRO_MAP.get(category, {})
    warnings = []

    mercury_retro_days = [
        int(d["date"].split("-")[2])
        for d in month_data if d.get("mercury_retrograde")
    ]
    venus_retro_days = [
        int(d["date"].split("-")[2])
        for d in month_data if d.get("venus_retrograde")
    ]

    for field, values, explanation in rules.get("avoid_conditions", []):
        if field == "mercury_retrograde" and mercury_retro_days:
            first = mercury_retro_days[0]
            last = mercury_retro_days[-1]
            warnings.append(
                f"⚠️ Меркурій ретроградний {first}–{last} — {explanation}"
            )
        elif field == "venus_retrograde" and venus_retro_days:
            first = venus_retro_days[0]
            last = venus_retro_days[-1]
            warnings.append(
                f"⚠️ Венера ретроградна {first}–{last} — {explanation}"
            )

    return warnings


def check_goal_conflicts(goals: list, daily_data: dict) -> list:
    conflicts = []
    date_str = daily_data.get("date", "")
    day = int(date_str.split("-")[2]) if date_str else 0
    month = int(date_str.split("-")[1]) if date_str else 0
    mn = MONTH_NAMES_GEN.get(month, "")

    scored_goals = []
    for goal in goals:
        sc, _ = _score_goal_day(goal["category"], daily_data)
        scored_goals.append((goal, sc))

    good = [(g, s) for g, s in scored_goals if s >= 3]
    bad = [(g, s) for g, s in scored_goals if s <= -2]

    for g_good, _ in good:
        for g_bad, _ in bad:
            conflicts.append(
                f"{day} {mn} — добре для «{g_good['title']}» "
                f"АЛЕ несприятливо для «{g_bad['title']}»"
            )

    return conflicts


def score_goal_for_day(goal: dict, daily_data: dict) -> int:
    sc, _ = _score_goal_day(goal.get("category", ""), daily_data)
    return sc


def get_goal_day_status(goal: dict, daily_data: dict) -> str:
    sc, reasons = _score_goal_day(goal.get("category", ""), daily_data)
    if sc >= 5:
        return "hot"
    elif sc >= 2:
        return "good"
    elif sc <= -3:
        return "bad"
    return "neutral"


def get_yearly_goal_calendar(goals: list, year: int, birth_data: dict) -> dict:
    from engine.calculator import get_month_data

    result = {}
    for goal in goals:
        goal_windows = []
        for month in range(1, 13):
            try:
                month_data = get_month_data(year, month, birth_data)
                windows = find_best_windows_in_month(goal, month_data)
                if windows:
                    best = windows[0]
                    goal_windows.append({
                        "month": MONTH_NAMES_UA[month],
                        "month_num": month,
                        "period": best["dates"],
                        "score": best["score"],
                        "reasons": best["reasons"][:1],
                    })
            except Exception:
                pass
        goal_windows.sort(key=lambda x: x["score"], reverse=True)
        result[goal["id"]] = goal_windows
    return result
