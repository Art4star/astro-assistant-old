"""
Lunar Calendar — Priority 3
Computes for a given month:
  - Moon sign per day
  - Moon phase name + emoji per day
  - New Moon and Full Moon exact moments
  - Void of Course (VOC) windows
"""

import swisseph as swe
import calendar
from datetime import datetime, timedelta
from typing import Optional

_SE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

PLANET_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

PHASE_NAMES = [
    (0,   22.5,  "new_moon",         "🌑"),
    (22.5, 67.5, "waxing_crescent",  "🌒"),
    (67.5, 112.5,"first_quarter",    "🌓"),
    (112.5,157.5,"waxing_gibbous",   "🌔"),
    (157.5,202.5,"full_moon",        "🌕"),
    (202.5,247.5,"waning_gibbous",   "🌖"),
    (247.5,292.5,"last_quarter",     "🌗"),
    (292.5,337.5,"balsamic",         "🌘"),
    (337.5,360,  "new_moon",         "🌑"),
]

# Planets to check for VOC aspects (classical + outer)
VOC_PLANETS = [
    swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS,
    swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO,
]

VOC_ASPECT_ANGLES = [0, 60, 90, 120, 180]
VOC_ORB = 1.0  # degrees


def _to_jd(dt: datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0)


def _moon_lon(jd: float) -> float:
    res, _ = swe.calc_ut(jd, swe.MOON, _SE_FLAGS)
    return res[0] % 360


def _sun_lon(jd: float) -> float:
    res, _ = swe.calc_ut(jd, swe.SUN, _SE_FLAGS)
    return res[0] % 360


def _get_sign(lon: float) -> str:
    return PLANET_SIGNS[int(lon / 30) % 12]


def _phase_from_angle(angle: float) -> tuple:
    for lo, hi, name, emoji in PHASE_NAMES:
        if lo <= angle < hi:
            return name, emoji
    return "new_moon", "🌑"


def _moon_phase_angle(jd: float) -> float:
    """Sun–Moon elongation 0–360°."""
    m = _moon_lon(jd)
    s = _sun_lon(jd)
    return (m - s) % 360


def _has_aspect_to_planet(moon_lon: float, planet_id: int, jd: float) -> bool:
    res, _ = swe.calc_ut(jd, planet_id, _SE_FLAGS)
    planet_lon = res[0] % 360
    diff = abs(moon_lon - planet_lon) % 360
    if diff > 180:
        diff = 360 - diff
    return any(abs(diff - a) <= VOC_ORB for a in VOC_ASPECT_ANGLES)


def _find_sign_changes(year: int, month: int) -> list:
    """Find exact times (JD) when Moon changes sign during the month."""
    _, days = calendar.monthrange(year, month)
    jd_start = _to_jd(datetime(year, month, 1, 0, 0))
    jd_end = _to_jd(datetime(year, month, days, 23, 59))

    changes = []
    prev_sign = int(_moon_lon(jd_start) / 30) % 12
    step = 1 / 24  # 1 hour steps

    jd = jd_start
    while jd <= jd_end:
        lon = _moon_lon(jd)
        sign = int(lon / 30) % 12
        if sign != prev_sign:
            # Binary search for exact crossing
            lo, hi = jd - step, jd
            for _ in range(30):
                mid = (lo + hi) / 2
                s = int(_moon_lon(mid) / 30) % 12
                if s == prev_sign:
                    lo = mid
                else:
                    hi = mid
            exact_jd = (lo + hi) / 2
            changes.append((exact_jd, PLANET_SIGNS[sign]))
            prev_sign = sign
        jd += step

    return changes


def _find_voc_start(sign_change_jd: float) -> Optional[float]:
    """
    Scan backward from sign change to find last Moon aspect.
    Returns JD of last aspect (= VOC start), or None if none found.
    """
    step = 1 / 48  # 30-minute steps backward
    moon_at_change = _moon_lon(sign_change_jd)

    # Look back up to 3 days
    jd = sign_change_jd - step
    last_aspect_jd = None

    while jd >= sign_change_jd - 3.0:
        moon_lon = _moon_lon(jd)
        for pid in VOC_PLANETS:
            if _has_aspect_to_planet(moon_lon, pid, jd):
                last_aspect_jd = jd
                break
        if last_aspect_jd is not None:
            break
        jd -= step

    return last_aspect_jd


def _jd_to_str(jd: float) -> str:
    y, mo, d, hh, mm, _ = swe.jdut1_to_utc(jd, 1)
    return f"{y}-{mo:02d}-{d:02d} {int(hh):02d}:{int(mm):02d} UTC"


def _find_exact_phase(year: int, month: int, target_angle: float) -> Optional[str]:
    """Find exact New (0°) or Full (180°) Moon moment within the month."""
    _, days = calendar.monthrange(year, month)
    jd_start = _to_jd(datetime(year, month, 1, 0, 0))
    jd_end = _to_jd(datetime(year, month, days, 23, 59))

    step = 1 / 24
    jd = jd_start
    prev_angle = _moon_phase_angle(jd)

    while jd <= jd_end:
        jd += step
        angle = _moon_phase_angle(jd)

        # Detect crossing of target_angle
        crossed = False
        if target_angle == 0:
            crossed = (prev_angle > 350 and angle < 10) or (prev_angle < angle < 10 and prev_angle < 5)
        else:
            crossed = prev_angle < target_angle <= angle

        if crossed:
            lo, hi = jd - step, jd
            for _ in range(40):
                mid = (lo + hi) / 2
                a = _moon_phase_angle(mid)
                if target_angle == 0:
                    a = a if a < 180 else a - 360
                    if a < 0:
                        lo = mid
                    else:
                        hi = mid
                else:
                    if a < target_angle:
                        lo = mid
                    else:
                        hi = mid
            return _jd_to_str((lo + hi) / 2)

        prev_angle = angle

    return None


def build_lunar_calendar(year: int, month: int) -> dict:
    """
    Returns full lunar calendar for the month:
    - day_by_day: list of {date, moon_sign, phase_name, phase_emoji, phase_angle}
    - new_moon: exact moment string or None
    - full_moon: exact moment string or None
    - voc_windows: list of {start, end, entering_sign}
    """
    _, days = calendar.monthrange(year, month)

    # Day-by-day at noon
    day_by_day = []
    for day in range(1, days + 1):
        jd = _to_jd(datetime(year, month, day, 12, 0))
        moon_lon = _moon_lon(jd)
        angle = _moon_phase_angle(jd)
        phase_name, phase_emoji = _phase_from_angle(angle)
        day_by_day.append({
            "date": f"{year}-{month:02d}-{day:02d}",
            "moon_sign": _get_sign(moon_lon),
            "moon_degree": round(moon_lon % 30, 1),
            "phase_name": phase_name,
            "phase_emoji": phase_emoji,
            "phase_angle": round(angle, 1),
        })

    # Exact New and Full Moon
    new_moon = _find_exact_phase(year, month, 0)
    full_moon = _find_exact_phase(year, month, 180)

    # VOC windows
    sign_changes = _find_sign_changes(year, month)
    voc_windows = []
    for change_jd, entering_sign in sign_changes:
        voc_start_jd = _find_voc_start(change_jd)
        if voc_start_jd is not None and voc_start_jd < change_jd:
            duration_h = (change_jd - voc_start_jd) * 24
            voc_windows.append({
                "start": _jd_to_str(voc_start_jd),
                "end": _jd_to_str(change_jd),
                "entering_sign": entering_sign,
                "duration_hours": round(duration_h, 1),
            })

    return {
        "period": f"{year}-{month:02d}",
        "day_by_day": day_by_day,
        "new_moon": new_moon,
        "full_moon": full_moon,
        "voc_windows": voc_windows,
    }
