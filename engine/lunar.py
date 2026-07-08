from datetime import datetime, timedelta
from engine.calculator import get_moon_phase, is_void_of_course, _get_longitude
import ephem

PHASE_EMOJI = {
    "new": "🌑",
    "waxing_crescent": "🌒",
    "first_quarter": "🌓",
    "waxing_gibbous": "🌔",
    "full": "🌕",
    "waning_gibbous": "🌖",
    "last_quarter": "🌗",
    "balsamic": "🌘",
}

PHASE_UA = {
    "new": "Новий місяць",
    "waxing_crescent": "Зростаючий серп",
    "first_quarter": "Перша чверть",
    "waxing_gibbous": "Зростаючий горбатий",
    "full": "Повний місяць",
    "waning_gibbous": "Спадаючий горбатий",
    "last_quarter": "Остання чверть",
    "balsamic": "Бальзамічний",
}

SIGN_EMOJI = {
    "aries": "♈", "taurus": "♉", "gemini": "♊", "cancer": "♋",
    "leo": "♌", "virgo": "♍", "libra": "♎", "scorpio": "♏",
    "sagittarius": "♐", "capricorn": "♑", "aquarius": "♒", "pisces": "♓",
}

SIGN_UA = {
    "aries": "Овен", "taurus": "Телець", "gemini": "Близнюки",
    "cancer": "Рак", "leo": "Лев", "virgo": "Діва",
    "libra": "Терези", "scorpio": "Скорпіон", "sagittarius": "Стрілець",
    "capricorn": "Козеріг", "aquarius": "Водолій", "pisces": "Риби",
}


def get_phase_emoji(phase: str) -> str:
    return PHASE_EMOJI.get(phase, "🌙")


def get_phase_name_ua(phase: str) -> str:
    return PHASE_UA.get(phase, phase)


def get_sign_emoji(sign: str) -> str:
    return SIGN_EMOJI.get(sign, "")


def get_sign_name_ua(sign: str) -> str:
    return SIGN_UA.get(sign, sign)


SIGN_UA_LOCATIVE = {
    "aries": "в Овні", "taurus": "у Тельці", "gemini": "у Близнюках",
    "cancer": "у Раку", "leo": "у Леві", "virgo": "у Діві",
    "libra": "у Терезах", "scorpio": "у Скорпіоні", "sagittarius": "у Стрільці",
    "capricorn": "у Козерозі", "aquarius": "у Водолії", "pisces": "у Рибах",
}


def get_sign_in_ua(sign: str) -> str:
    """Знак з прийменником у місцевому відмінку: 'в Овні', 'у Тельці'."""
    return SIGN_UA_LOCATIVE.get(sign, f"у {SIGN_UA.get(sign, sign)}")


def get_moon_sign_change(date: datetime):
    """Найближчий перехід Місяця в наступний знак після date.

    Повертає (datetime, sign_key) з точністю до хвилини,
    або (None, None), якщо перехід не знайдено протягом 72 годин.
    """
    import swisseph as swe
    from engine.calculator import _to_jd, _get_sign

    lon = _get_longitude(swe.MOON, _to_jd(date))
    boundary = ((int(lon / 30) + 1) * 30.0) % 360.0

    def crossed(dt: datetime) -> bool:
        lon_at = _get_longitude(swe.MOON, _to_jd(dt))
        if boundary == 0.0:
            return lon_at < 30.0
        return lon_at >= boundary

    lo, hi = date, None
    check = date
    for _ in range(72):
        check += timedelta(hours=1)
        if crossed(check):
            lo, hi = check - timedelta(hours=1), check
            break
    if hi is None:
        return None, None

    while hi - lo > timedelta(minutes=1):
        mid = lo + (hi - lo) / 2
        if crossed(mid):
            hi = mid
        else:
            lo = mid

    next_sign = _get_sign(_get_longitude(swe.MOON, _to_jd(hi)))
    return hi, next_sign


def get_month_lunar_events(year: int, month: int) -> dict:
    import calendar
    _, days = calendar.monthrange(year, month)

    full_moon_days = []
    new_moon_days = []
    voc_days = []

    prev_phase = None
    for day in range(1, days + 1):
        date = datetime(year, month, day, 12, 0, 0)
        phase = get_moon_phase(date)

        if phase == "full" and prev_phase != "full":
            full_moon_days.append(day)
        if phase == "new" and prev_phase != "new":
            new_moon_days.append(day)
        if is_void_of_course(date):
            voc_days.append(day)

        prev_phase = phase

    return {
        "full_moon": full_moon_days,
        "new_moon": new_moon_days,
        "voc_days": voc_days,
    }
