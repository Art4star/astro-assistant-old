ACTIVITY_RULES = {
    "finance": {
        "favorable": [
            ("moon_phase", ["waxing_gibbous", "full"], +3),
            ("jupiter_aspect", ["trine", "sextile"], +3),
            ("moon_sign", ["taurus", "capricorn", "virgo"], +2),
            ("tr_jupiter_natal_sun", ["trine", "sextile", "conjunction"], +3),
            ("tr_venus_natal_sun", ["trine", "sextile"], +2),
            ("tr_venus_natal_moon", ["conjunction", "trine", "sextile"], +1),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -4),
            ("saturn_aspect", ["square", "opposition"], -3),
            ("moon_voc", True, -3),
            ("moon_phase", ["balsamic", "new"], -2),
            ("tr_saturn_natal_sun", ["square", "opposition"], -3),
            ("tr_jupiter_natal_sun", ["opposition", "square"], -2),
            ("tr_pluto_natal_venus", ["conjunction", "square", "opposition"], -2),
            ("tr_neptune_natal_sun", ["square", "opposition"], -2),
        ]
    },
    "work_technical": {
        "favorable": [
            ("moon_sign", ["virgo", "capricorn", "gemini"], +3),
            ("mercury_aspect", ["trine", "sextile"], +2),
            ("moon_phase", ["waxing_crescent", "first_quarter"], +2),
            ("tr_jupiter_natal_mercury", ["trine", "sextile", "conjunction"], +3),
            ("tr_jupiter_natal_sun", ["trine", "sextile"], +2),
            ("tr_uranus_natal_venus", ["trine", "sextile"], +1),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_voc", True, -2),
            ("moon_sign", ["pisces", "cancer"], -2),
            ("tr_saturn_natal_mercury", ["square", "opposition"], -2),
            ("tr_jupiter_natal_mercury", ["opposition", "square"], -2),
            ("tr_neptune_natal_ascendant", ["square", "opposition"], -2),
        ]
    },
    "negotiations": {
        "favorable": [
            ("mercury_direct", True, +3),
            ("venus_aspect", ["trine", "sextile"], +2),
            ("moon_sign", ["gemini", "libra", "aquarius"], +2),
            ("jupiter_aspect", ["trine", "sextile"], +2),
            ("tr_jupiter_natal_sun", ["trine", "sextile", "conjunction"], +3),
            ("tr_venus_natal_sun", ["trine", "sextile"], +2),
            ("tr_venus_natal_moon", ["conjunction", "trine", "sextile"], +2),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -5),
            ("moon_voc", True, -3),
            ("mars_aspect", ["square", "opposition"], -2),
            ("tr_saturn_natal_sun", ["square", "opposition"], -3),
            ("tr_mars_natal_sun", ["square", "opposition"], -2),
            ("tr_jupiter_natal_sun", ["opposition", "square"], -2),
            ("tr_jupiter_natal_mercury", ["opposition", "square"], -3),
            ("tr_neptune_natal_ascendant", ["square", "opposition"], -2),
        ]
    },
    "content_publishing": {
        "favorable": [
            ("sun_aspect", ["trine", "sextile"], +2),
            ("moon_phase", ["waxing_gibbous", "full"], +3),
            ("venus_aspect", ["trine", "sextile"], +2),
            ("tr_jupiter_natal_mercury", ["trine", "sextile"], +2),
            ("tr_venus_natal_venus", ["conjunction", "trine", "sextile"], +2),
            ("tr_uranus_natal_venus", ["trine", "sextile"], +2),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_phase", ["balsamic"], -3),
            ("saturn_aspect", ["square"], -2),
            ("tr_saturn_natal_mercury", ["square", "opposition"], -2),
            ("tr_jupiter_natal_mercury", ["opposition", "square"], -1),
        ]
    },
    "rest_reflection": {
        "favorable": [
            ("moon_phase", ["balsamic", "last_quarter", "new"], +4),
            ("moon_sign", ["pisces", "cancer", "scorpio"], +2),
            ("saturn_aspect", ["trine"], +1),
            ("tr_saturn_natal_moon", ["trine", "sextile"], +1),
            ("tr_venus_natal_moon", ["conjunction", "trine", "sextile"], +2),
        ],
        "unfavorable": [
            ("moon_phase", ["full", "waxing_gibbous"], -2),
            ("mars_aspect", ["conjunction"], -1),
            ("tr_mars_natal_moon", ["square", "opposition"], -2),
        ]
    },
    "new_beginnings": {
        "favorable": [
            ("moon_phase", ["new", "waxing_crescent"], +4),
            ("jupiter_aspect", ["conjunction", "trine"], +3),
            ("tr_jupiter_natal_sun", ["conjunction", "trine", "sextile"], +4),
            ("tr_jupiter_natal_moon", ["trine", "sextile"], +2),
            ("tr_uranus_natal_venus", ["trine", "sextile"], +1),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_phase", ["balsamic", "last_quarter"], -4),
            ("saturn_aspect", ["square", "opposition"], -3),
            ("tr_saturn_natal_sun", ["square", "opposition"], -3),
            ("tr_jupiter_natal_sun", ["opposition", "square"], -2),
            ("tr_neptune_natal_sun", ["square", "opposition"], -2),
            # Neptune sq ASC = розмитість ідентичності та напрямку — ризик для нових починань
            ("tr_neptune_natal_ascendant", ["square", "opposition"], -2),
        ]
    },
    "health_body": {
        "favorable": [
            ("moon_sign", ["virgo", "taurus"], +3),
            ("moon_phase", ["waxing_crescent"], +2),
            ("tr_jupiter_natal_moon", ["trine", "sextile", "conjunction"], +2),
            ("tr_venus_natal_moon", ["conjunction", "trine"], +1),
        ],
        "unfavorable": [
            ("moon_voc", True, -2),
            ("mars_aspect", ["square", "opposition"], -2),
            ("tr_mars_natal_mars", ["square", "opposition"], -2),
            ("tr_saturn_natal_moon", ["square", "opposition"], -2),
            ("tr_neptune_natal_ascendant", ["square", "opposition"], -2),
        ]
    }
}

ACTIVITY_LABELS = {
    "finance": "Фінанси",
    "work_technical": "Робота",
    "negotiations": "Переговори",
    "content_publishing": "Контент",
    "rest_reflection": "Відпочинок",
    "new_beginnings": "Нові починання",
    "health_body": "Здоров'я",
}


def _check_rule(daily_data: dict, field: str, condition) -> bool:
    value = daily_data.get(field)
    if isinstance(condition, list):
        return value in condition
    return value == condition


def score_day(daily_data: dict) -> dict:
    scores = {}
    for activity, rules in ACTIVITY_RULES.items():
        score = 0
        for field, condition, points in rules.get("favorable", []):
            if _check_rule(daily_data, field, condition):
                score += points
        for field, condition, points in rules.get("unfavorable", []):
            if _check_rule(daily_data, field, condition):
                score += points
        scores[activity] = max(-10, min(10, score))
    return scores


def get_overall_score(scores: dict) -> int:
    if not scores:
        return 0
    return round(sum(scores.values()) / len(scores))


def is_polarized_day(scores: dict) -> bool:
    """True if day has both high positive and low negative activities (spread >= 6)."""
    if not scores:
        return False
    vals = list(scores.values())
    return max(vals) - min(vals) >= 6


def get_day_label(overall_score: int, scores=None) -> str:
    if scores and is_polarized_day(scores):
        return "Поляризований"
    if overall_score > 5:
        return "Відмінний день"
    elif overall_score >= 2:
        return "Хороший"
    elif overall_score >= -1:
        return "Нейтральний"
    elif overall_score >= -4:
        return "Краще почекати"
    else:
        return "День відпочинку"


def get_warnings(daily_data: dict) -> list:
    warnings = []

    # Retrograde planets
    if daily_data.get("mercury_retrograde"):
        warnings.append("☿ Меркурій ретроградний — уникайте підписів і нових домовленостей")
    if daily_data.get("venus_retrograde"):
        warnings.append("♀ Венера ретроградна — обережно з фінансовими рішеннями")
    if daily_data.get("mars_retrograde"):
        warnings.append("♂ Марс ретроградний — уникайте конфронтацій і різких дій")
    if daily_data.get("jupiter_retrograde"):
        warnings.append("♃ Юпітер ретроградний")
    if daily_data.get("saturn_retrograde"):
        warnings.append("♄ Сатурн ретроградний")

    # VOC
    if daily_data.get("moon_voc"):
        warnings.append("🌀 Місяць без курсу (VOC) — не починайте важливого")

    # Moon–planet aspects (immediate daily tension)
    if daily_data.get("mars_aspect") == "conjunction":
        warnings.append("♂ Місяць кон'юнкція Марс — імпульсивність, підвищена напруга")
    if daily_data.get("saturn_aspect") in ("square", "opposition"):
        warnings.append("♄ Місяць у напрузі з Сатурном — емоційна важкість, затримки")
    if daily_data.get("mars_aspect") in ("square", "opposition"):
        warnings.append("♂ Місяць у напрузі з Марсом — конфліктний фон")

    # Active transit tensions to natal chart
    if daily_data.get("tr_jupiter_natal_sun") in ("opposition", "square"):
        warnings.append("♃ Юпітер у напрузі до натального Сонця — ризик переоцінки сил")
    if daily_data.get("tr_jupiter_natal_mercury") in ("opposition", "square"):
        warnings.append("♃ Юпітер у напрузі до натального Меркурія — обережно з домовленостями")
    if daily_data.get("tr_neptune_natal_ascendant") in ("square", "opposition"):
        warnings.append("♆ Нептун квадрат ASC — розмитість меж, перевіряйте деталі")
    if daily_data.get("tr_pluto_natal_venus") in ("conjunction", "square", "opposition"):
        warnings.append("♇ Плутон кон'юнкція натальній Венері — трансформація фінансів/відносин")

    return warnings


def get_recommendations(daily_data: dict, scores: dict) -> dict:
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    best_for = [
        ACTIVITY_LABELS[act] for act, sc in sorted_scores[:3] if sc >= 2
    ]
    avoid = [
        ACTIVITY_LABELS[act] for act, sc in sorted_scores if sc <= -2
    ]

    tips = []
    if daily_data.get("moon_voc"):
        tips.append("Уникайте важливих рішень під час VOC Місяця")
    if daily_data.get("mercury_retrograde"):
        tips.append("Меркурій ретроградний — перевіряйте деталі, не підписуйте контракти")
    if daily_data.get("moon_phase") == "full":
        tips.append("Повний місяць підсилює емоції та інтуїцію")
    if daily_data.get("moon_phase") == "new":
        new_beginnings_score = scores.get("new_beginnings", 0)
        if new_beginnings_score >= 2:
            tips.append("Новий місяць — час для нових намірів та починань")
        else:
            tips.append("Новий місяць — зосередьтесь на внутрішніх намірах, зовнішні дії краще відкласти")

    return {
        "best_for": best_for,
        "avoid": avoid,
        "tip": tips[0] if tips else "",
    }


def get_day_color(overall_score: int) -> str:
    if overall_score > 5:
        return "#166534"
    elif overall_score >= 2:
        return "#365314"
    elif overall_score >= -1:
        return "#1f2937"
    elif overall_score >= -4:
        return "#7c2d12"
    else:
        return "#450a0a"
