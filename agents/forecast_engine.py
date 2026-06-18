"""
Agent 3 — Forecast Engine
Calculates: transits (with peak_date, applying/separating, intensity),
solar return (with natal house overlay), critical windows.
Uses Swiss Ephemeris (pyswisseph) Moshier.

FROZEN 2026-05-16 — Solar Return Placidus cusps verified. Transit logic verified.
DO NOT MODIFY without explicit permission from Artur in the current conversation.
"""

import math
import calendar
import pytz
import swisseph as swe
from datetime import datetime, timedelta
from typing import Optional

PLANET_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

ASPECT_ANGLES = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}

TRANSIT_ORBS = {
    "conjunction": 8.0, "opposition": 8.0,
    "square": 6.0, "trine": 6.0, "sextile": 4.0,
}

TRANSIT_PRIORITY = {
    "pluto": 1, "neptune": 2, "uranus": 3, "saturn": 4,
    "jupiter": 5, "mars": 6, "sun": 7, "venus": 8,
    "mercury": 9, "moon": 10, "true_node": 11,
}

PLANETS_TRANSIT = [
    "pluto", "neptune", "uranus", "saturn", "jupiter",
    "mars", "sun", "venus", "mercury", "moon",
]

PLANET_IDS = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY,
    "venus": swe.VENUS, "mars": swe.MARS, "jupiter": swe.JUPITER,
    "saturn": swe.SATURN, "uranus": swe.URANUS, "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO, "true_node": swe.TRUE_NODE,
}

# Priority 2: intensity scoring weights
_TRANSIT_PLANET_WEIGHT = {
    "pluto": 10, "neptune": 9, "uranus": 8, "saturn": 7, "jupiter": 6,
    "mars": 5, "true_node": 4, "sun": 4, "venus": 3, "mercury": 2, "moon": 1,
}
_NATAL_PLANET_WEIGHT = {
    "ascendant": 10, "sun": 9, "moon": 8, "midheaven": 7,
    "mercury": 5, "venus": 5, "mars": 5, "true_node": 5,
    "saturn": 4, "jupiter": 4, "uranus": 3, "neptune": 3, "pluto": 3,
}
_ASPECT_WEIGHT = {
    "conjunction": 10, "opposition": 9, "square": 8, "trine": 7, "sextile": 6,
}

_SE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


def _to_jd(dt: datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0 + dt.second / 3600.0)


def _get_longitude(planet_id: int, jd: float) -> float:
    result, _ = swe.calc_ut(jd, planet_id, _SE_FLAGS)
    return result[0] % 360


def _get_speed(planet_id: int, jd: float) -> float:
    result, _ = swe.calc_ut(jd, planet_id, _SE_FLAGS)
    return result[3]


def _get_sign(lon: float) -> str:
    return PLANET_SIGNS[int(lon / 30) % 12]


def _aspect_between(lon1: float, lon2: float) -> Optional[tuple]:
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    for angle, name in ASPECT_ANGLES.items():
        orb = abs(diff - angle)
        if orb <= TRANSIT_ORBS[name]:
            return name, round(orb, 2)
    return None


def _intensity_score(tr_planet: str, natal_planet: str, aspect: str,
                     min_orb: float, duration_days: int) -> float:
    """
    Priority 2: 0–100 score. Higher = more significant.
    Factors: planet weights, aspect weight, orb tightness, duration.
    """
    tp = _TRANSIT_PLANET_WEIGHT.get(tr_planet, 1) / 10
    np = _NATAL_PLANET_WEIGHT.get(natal_planet, 1) / 10
    asp = _ASPECT_WEIGHT.get(aspect, 5) / 10
    max_orb = TRANSIT_ORBS[aspect]
    orb_factor = max(0.1, 1.0 - min_orb / max_orb)
    # Outer planet transits lasting the whole month get full duration bonus
    duration_factor = min(1.0, 0.6 + duration_days / 75)
    return round(tp * np * asp * orb_factor * duration_factor * 100, 1)


def get_transits_for_month(year: int, month: int, natal_planets: dict) -> list:
    """
    Returns transit-to-natal aspects with peak_date, applying/separating status,
    and intensity score.
    """
    _, days = calendar.monthrange(year, month)

    # Track orb per day per transit key for peak detection
    raw: dict = {}  # key → {meta, orbs_by_day: {day: orb}, retro_by_day: {day: bool}}

    for day in range(1, days + 1):
        jd = _to_jd(datetime(year, month, day, 12, 0))

        for tr_name in PLANETS_TRANSIT:
            pid = PLANET_IDS.get(tr_name)
            if pid is None:
                continue
            tr_lon = _get_longitude(pid, jd)
            retrograde = _get_speed(pid, jd) < 0

            for natal_name, natal_lon in natal_planets.items():
                result = _aspect_between(tr_lon, natal_lon)
                if not result:
                    continue
                aspect, orb = result
                key = (tr_name, natal_name, aspect)
                if key not in raw:
                    raw[key] = {
                        "transit_planet": tr_name,
                        "natal_planet": natal_name,
                        "aspect": aspect,
                        "first_day": day,
                        "last_day": day,
                        "orbs_by_day": {day: orb},
                        "retro_by_day": {day: retrograde},
                    }
                else:
                    raw[key]["last_day"] = day
                    raw[key]["orbs_by_day"][day] = orb
                    raw[key]["retro_by_day"][day] = retrograde

    # Priority 1: derive peak_date, applying/separating, status
    transits = []
    for data in raw.values():
        orbs = data["orbs_by_day"]
        first_day = data["first_day"]
        last_day = data["last_day"]
        duration_days = last_day - first_day + 1

        peak_day = min(orbs, key=orbs.get)
        min_orb = orbs[peak_day]

        # Applying at start: orb decreasing from first to second day
        next_day_orb = orbs.get(first_day + 1)
        applying_at_start = (next_day_orb is not None and next_day_orb < orbs[first_day])

        if peak_day == first_day and not applying_at_start:
            status = "separating"          # already past peak when month started
        elif peak_day == last_day:
            status = "applying"            # still tightening at month end
        else:
            status = "exact_within_month"  # peaked inside the month

        intensity = _intensity_score(
            data["transit_planet"], data["natal_planet"],
            data["aspect"], min_orb, duration_days,
        )

        transits.append({
            "transit_planet": data["transit_planet"],
            "natal_planet": data["natal_planet"],
            "aspect": data["aspect"],
            "first_date": f"{year}-{month:02d}-{first_day:02d}",
            "last_date": f"{year}-{month:02d}-{last_day:02d}",
            "peak_date": f"{year}-{month:02d}-{peak_day:02d}",
            "min_orb": round(min_orb, 2),
            "status": status,
            "applying_at_start": applying_at_start,
            "retrograde": data["retro_by_day"].get(peak_day, False),
            "intensity": intensity,
            "priority": TRANSIT_PRIORITY.get(data["transit_planet"], 99),
        })

    transits.sort(key=lambda x: (-x["intensity"], x["priority"]))
    return transits


def find_solar_return(birth_data: dict, year: int) -> dict:
    """
    Finds exact solar return moment. Priority 6: adds natal house overlay
    (which natal house each SR planet occupies, and vice versa).
    """
    natal_sun_lon = birth_data["natal_planets"]["sun"]
    birth_month = int(birth_data["birth_date"].split("-")[1])
    birth_day = int(birth_data["birth_date"].split("-")[2])

    search_start = datetime(year, birth_month, max(1, birth_day - 5), 0, 0)
    search_end = datetime(year, birth_month, min(28, birth_day + 5), 23, 59)

    jd_lo = _to_jd(search_start)
    jd_hi = _to_jd(search_end)

    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        sun_lon = _get_longitude(swe.SUN, jd_mid)
        diff = (sun_lon - natal_sun_lon + 360) % 360
        if diff > 180:
            diff -= 360
        if abs(diff) < 0.0001:
            break
        elif diff > 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid

    jd_return = (jd_lo + jd_hi) / 2
    y, mo, d, hh, mm, _ = swe.jdut1_to_utc(jd_return, 1)
    return_moment_str = f"{y}-{mo:02d}-{d:02d} {int(hh):02d}:{int(mm):02d} UTC"

    location = birth_data.get("current_location", {})
    sr_lat = location.get("latitude", birth_data["latitude"])
    sr_lon_coord = location.get("longitude", birth_data["longitude"])

    sr_planets = {}
    for name in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
                 "uranus", "neptune", "pluto", "true_node"]:
        pid = PLANET_IDS[name]
        lon = _get_longitude(pid, jd_return)
        speed = _get_speed(pid, jd_return)
        sr_planets[name] = {
            "longitude": round(lon, 4),
            "sign": _get_sign(lon),
            "degree": round(lon % 30, 2),
            "retrograde": speed < 0,
        }

    # SR Placidus cusps
    sr_cusps, sr_ascmc = swe.houses(jd_return, sr_lat, sr_lon_coord, b'P')
    asc_lon = sr_ascmc[0] % 360
    mc_lon = sr_ascmc[1] % 360

    # Natal Placidus cusps (computed from birth data)
    tz = pytz.timezone(birth_data["timezone"])
    birth_local = datetime.strptime(
        f"{birth_data['birth_date']} {birth_data['birth_time']}", "%Y-%m-%d %H:%M"
    )
    birth_utc = tz.localize(birth_local).astimezone(pytz.utc)
    jd_natal = _to_jd(birth_utc)
    natal_cusps, _ = swe.houses(jd_natal, birth_data["latitude"], birth_data["longitude"], b'P')

    def _house_from_cusps(planet_lon: float, cusps: tuple) -> int:
        lon = planet_lon % 360
        for i in range(12):
            start = cusps[i] % 360
            end = cusps[(i + 1) % 12] % 360
            if end > start:
                if start <= lon < end:
                    return i + 1
            else:
                if lon >= start or lon < end:
                    return i + 1
        return 1

    # Priority 6: natal house overlay — Placidus degree-based
    sr_planets_in_natal_houses = {
        name: _house_from_cusps(data["longitude"], natal_cusps)
        for name, data in sr_planets.items()
    }

    natal_planets_in_sr_houses = {
        name: _house_from_cusps(lon, sr_cusps)
        for name, lon in birth_data["natal_planets"].items()
        if isinstance(lon, (int, float))
    }

    return {
        "moment": return_moment_str,
        "location_used": f"{sr_lat}N, {sr_lon_coord}E",
        "planets": sr_planets,
        "ascendant": {
            "longitude": round(asc_lon, 4),
            "sign": _get_sign(asc_lon),
            "degree": round(asc_lon % 30, 2),
        },
        "midheaven": {
            "longitude": round(mc_lon, 4),
            "sign": _get_sign(mc_lon),
            "degree": round(mc_lon % 30, 2),
        },
        # Priority 6 additions
        "sr_planets_in_natal_houses": sr_planets_in_natal_houses,
        "natal_planets_in_sr_houses": natal_planets_in_sr_houses,
    }


def get_critical_windows(transits: list, year: int, month: int) -> list:
    """High-importance periods: outer planets to angles/luminaries, by intensity."""
    OUTER = {"pluto", "neptune", "uranus", "saturn", "jupiter"}
    KEY_NATAL = {"sun", "moon", "mercury", "venus", "mars", "jupiter", "ascendant", "midheaven", "true_node"}

    TYPE_MAP = {
        ("saturn", "square"):      ("restructuring",  "тиск, дисципліна, усунення зайвого"),
        ("saturn", "opposition"):  ("restructuring",  "тиск, дисципліна, усунення зайвого"),
        ("saturn", "trine"):       ("consolidation",  "закріпити досягнення, будувати довгострокове"),
        ("saturn", "sextile"):     ("consolidation",  "закріпити досягнення, будувати довгострокове"),
        ("saturn", "conjunction"): ("consolidation",  "структурування, серйозні рішення"),
        ("jupiter", "trine"):      ("expansion",      "вікно зростання, сприятливий час"),
        ("jupiter", "sextile"):    ("expansion",      "вікно зростання, сприятливий час"),
        ("jupiter", "conjunction"):("expansion",      "вікно зростання, нові ініціативи"),
        ("jupiter", "square"):     ("overreach_risk", "ризик переоцінки, потрібен реалізм"),
        ("jupiter", "opposition"): ("overreach_risk", "ризик переоцінки, потрібен реалізм"),
        ("pluto", "conjunction"):  ("transformation", "глибока трансформація, незворотні зміни"),
        ("pluto", "square"):       ("power_struggle", "кризова точка, боротьба за контроль"),
        ("pluto", "opposition"):   ("power_struggle", "зовнішній тиск, вимушені зміни"),
        ("neptune", "conjunction"):("dissolution",    "розмиття меж, духовний пошук"),
        ("neptune", "square"):     ("confusion",      "невизначеність, ризик самообману"),
        ("uranus", "conjunction"): ("breakthrough",   "раптові зміни, звільнення від рутини"),
        ("uranus", "square"):      ("disruption",     "нестабільність, несподівані розриви"),
        ("uranus", "trine"):       ("liberation",     "свобода, інновації, позитивні зміни"),
    }

    windows = []
    for t in transits:
        planet = t["transit_planet"]
        if planet not in OUTER or t["natal_planet"] not in KEY_NATAL:
            continue
        key = (planet, t["aspect"])
        if key not in TYPE_MAP:
            continue
        window_type, theme = TYPE_MAP[key]
        windows.append({
            "type": window_type,
            "transit_planet": planet,
            "natal_planet": t["natal_planet"],
            "aspect": t["aspect"],
            "first_date": t["first_date"],
            "last_date": t["last_date"],
            "peak_date": t["peak_date"],
            "status": t["status"],
            "orb": t["min_orb"],
            "intensity": t["intensity"],
            "retrograde": t.get("retrograde", False),
            "description": f"{planet.capitalize()} {t['aspect']} natal {t['natal_planet']} — {theme}.",
        })

    windows.sort(key=lambda x: -x["intensity"])
    return windows


def find_retrograde_stations(year: int, month: int) -> list:
    """
    Finds exact moments when planets station retrograde or direct within the month.
    These are ground-truth dates — prevents LLM from guessing retrograde timing.
    """
    STATION_PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn",
                       "uranus", "neptune", "pluto"]
    _, days = calendar.monthrange(year, month)
    stations = []

    for planet_name in STATION_PLANETS:
        pid = PLANET_IDS[planet_name]
        prev_jd = _to_jd(datetime(year, month, 1, 12, 0))
        prev_speed = _get_speed(pid, prev_jd)

        for day in range(2, days + 1):
            jd = _to_jd(datetime(year, month, day, 12, 0))
            speed = _get_speed(pid, jd)

            if (prev_speed > 0 and speed < 0) or (prev_speed < 0 and speed > 0):
                # Binary search for exact station moment
                jd_lo, jd_hi = prev_jd, jd
                for _ in range(40):
                    jd_mid = (jd_lo + jd_hi) / 2
                    s = _get_speed(pid, jd_mid)
                    if (prev_speed > 0 and s > 0) or (prev_speed < 0 and s < 0):
                        jd_lo = jd_mid
                    else:
                        jd_hi = jd_mid

                exact_jd = (jd_lo + jd_hi) / 2
                y, mo, d, hh, mm, _ = swe.jdut1_to_utc(exact_jd, 1)
                lon = _get_longitude(pid, exact_jd)
                stations.append({
                    "planet": planet_name,
                    "type": "retrograde" if prev_speed > 0 else "direct",
                    "date": f"{y}-{mo:02d}-{d:02d}",
                    "time_utc": f"{int(hh):02d}:{int(mm):02d}",
                    "sign": _get_sign(lon),
                    "degree": round(lon % 30, 2),
                })

            prev_speed = speed
            prev_jd = jd

    stations.sort(key=lambda x: x["date"])
    return stations


def get_sky_aspects(year: int, month: int) -> list:
    """
    Transit-to-transit aspects (what's happening in the sky globally).
    Detects T-squares, Grand Trines, conjunctions of outer planets.
    Orbs: 3° for outer planets, 2° for inner.
    """
    SKY_PLANETS = ["pluto", "neptune", "uranus", "saturn", "jupiter",
                   "mars", "sun", "venus", "mercury"]
    SKY_ORBS = {"conjunction": 5.0, "opposition": 5.0, "square": 4.0,
                "trine": 4.0, "sextile": 3.0}

    _, days = calendar.monthrange(year, month)
    aspects_seen = {}

    for day in range(1, days + 1):
        jd = _to_jd(datetime(year, month, day, 12, 0))
        positions = {p: _get_longitude(PLANET_IDS[p], jd) for p in SKY_PLANETS}

        names = SKY_PLANETS
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                p1, p2 = names[i], names[j]
                diff = abs(positions[p1] - positions[p2]) % 360
                if diff > 180:
                    diff = 360 - diff
                for angle, asp_name in ASPECT_ANGLES.items():
                    orb = abs(diff - angle)
                    if orb <= SKY_ORBS.get(asp_name, 3.0):
                        key = (p1, p2, asp_name)
                        if key not in aspects_seen:
                            aspects_seen[key] = {
                                "planet1": p1, "planet2": p2, "aspect": asp_name,
                                "first_date": f"{year}-{month:02d}-{day:02d}",
                                "last_date": f"{year}-{month:02d}-{day:02d}",
                                "min_orb": orb,
                            }
                        else:
                            aspects_seen[key]["last_date"] = f"{year}-{month:02d}-{day:02d}"
                            aspects_seen[key]["min_orb"] = min(aspects_seen[key]["min_orb"], orb)

    # Keep only aspects involving at least one outer planet (Jupiter+)
    OUTER = {"pluto", "neptune", "uranus", "saturn", "jupiter"}
    result = [
        a for a in aspects_seen.values()
        if a["planet1"] in OUTER or a["planet2"] in OUTER
    ]
    result.sort(key=lambda x: (
        -(1 if x["planet1"] in OUTER else 0) - (1 if x["planet2"] in OUTER else 0),
        x["min_orb"]
    ))
    return result


def build_forecast(birth_data: dict, year: int, month: int) -> dict:
    natal_planets = birth_data.get("natal_planets", {})
    if not natal_planets:
        raise ValueError("natal_planets not found in birth_data. Run setup first.")

    transits = get_transits_for_month(year, month, natal_planets)
    critical_windows = get_critical_windows(transits, year, month)
    stations = find_retrograde_stations(year, month)
    sky_aspects = get_sky_aspects(year, month)

    try:
        solar_return = find_solar_return(birth_data, year)
    except Exception as e:
        solar_return = {"error": str(e)}

    return {
        "period": f"{year}-{month:02d}",
        "transits": transits,
        "solar_return": solar_return,
        "critical_windows": critical_windows,
        "retrograde_stations": stations,
        "sky_aspects": sky_aspects,
    }
