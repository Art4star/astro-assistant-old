from datetime import datetime, timedelta
from typing import Optional, List
import pytz

try:
    from kerykeion import AstrologicalSubject
    KERYKEION_AVAILABLE = True
except ImportError:
    KERYKEION_AVAILABLE = False

import ephem

PLANET_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

ASPECT_NAMES = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}

ORB = 3.0


def _ephem_planet(name: str):
    planets = {
        "sun": ephem.Sun,
        "moon": ephem.Moon,
        "mercury": ephem.Mercury,
        "venus": ephem.Venus,
        "mars": ephem.Mars,
        "jupiter": ephem.Jupiter,
        "saturn": ephem.Saturn,
    }
    return planets.get(name.lower())


def _get_sign(longitude: float) -> str:
    idx = int(longitude / 30) % 12
    return PLANET_SIGNS[idx]


def _get_longitude(planet_cls, date: datetime) -> float:
    obs = ephem.Observer()
    obs.date = date.strftime("%Y/%m/%d %H:%M:%S")
    p = planet_cls()
    p.compute(obs)
    return float(p.hlong) * 180.0 / ephem.pi


def _aspect_between(lon1: float, lon2: float) -> Optional[str]:
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    for angle, name in ASPECT_NAMES.items():
        if abs(diff - angle) <= ORB:
            return name
    return None


def _is_retrograde(planet_cls, date: datetime) -> bool:
    lon1 = _get_longitude(planet_cls, date)
    lon2 = _get_longitude(planet_cls, date + timedelta(days=1))
    delta = (lon2 - lon1 + 360) % 360
    return delta > 180


def get_moon_phase(date: datetime) -> str:
    sun_lon = _get_longitude(ephem.Sun, date)
    moon_lon = _get_longitude(ephem.Moon, date)
    angle = (moon_lon - sun_lon) % 360

    if angle < 22.5 or angle >= 337.5:
        return "new"
    elif angle < 67.5:
        return "waxing_crescent"
    elif angle < 112.5:
        return "first_quarter"
    elif angle < 157.5:
        return "waxing_gibbous"
    elif angle < 202.5:
        return "full"
    elif angle < 247.5:
        return "waning_gibbous"
    elif angle < 292.5:
        return "last_quarter"
    else:
        return "balsamic"


def is_void_of_course(date: datetime) -> bool:
    moon_lon = _get_longitude(ephem.Moon, date)
    current_sign_end = (int(moon_lon / 30) + 1) * 30.0

    check = date
    while True:
        check += timedelta(hours=1)
        next_lon = _get_longitude(ephem.Moon, check)
        if next_lon >= current_sign_end or (current_sign_end >= 360 and next_lon < 30):
            break
        for planet_name in ["sun", "mercury", "venus", "mars", "jupiter", "saturn"]:
            pcls = _ephem_planet(planet_name)
            p_lon = _get_longitude(pcls, check)
            if _aspect_between(next_lon, p_lon):
                return False
        if check > date + timedelta(hours=72):
            break
    return True


def is_mercury_retrograde(date: datetime) -> bool:
    return _is_retrograde(ephem.Mercury, date)


def _get_planet_data(date: datetime) -> dict:
    planets = {}
    for name in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]:
        pcls = _ephem_planet(name)
        lon = _get_longitude(pcls, date)
        planets[name] = {
            "longitude": lon,
            "sign": _get_sign(lon),
        }

    for name in ["mercury", "venus", "mars", "jupiter", "saturn"]:
        pcls = _ephem_planet(name)
        planets[name]["retrograde"] = _is_retrograde(pcls, date)

    return planets


def _get_transits(date: datetime, birth_data: dict) -> list:
    transits = []
    if not birth_data:
        return transits

    natal_planets = birth_data.get("natal_planets", {})
    current_planets = _get_planet_data(date)

    for transit_planet, tdata in current_planets.items():
        for natal_planet, nlon in natal_planets.items():
            aspect = _aspect_between(tdata["longitude"], nlon)
            if aspect:
                transits.append({
                    "transit": transit_planet,
                    "natal": natal_planet,
                    "aspect": aspect,
                })
    return transits


def get_daily_data(date: datetime, birth_data: dict) -> dict:
    planets = _get_planet_data(date)

    return {
        "date": date.strftime("%Y-%m-%d"),
        "moon_sign": planets["moon"]["sign"],
        "moon_phase": get_moon_phase(date),
        "moon_voc": is_void_of_course(date),
        "mercury_retrograde": planets["mercury"]["retrograde"],
        "mercury_direct": not planets["mercury"]["retrograde"],
        "venus_retrograde": planets["venus"]["retrograde"],
        "mars_retrograde": planets["mars"]["retrograde"],
        "jupiter_retrograde": planets["jupiter"]["retrograde"],
        "saturn_retrograde": planets["saturn"]["retrograde"],
        "planets": planets,
        "sun_sign": planets["sun"]["sign"],
        "sun_aspect": _find_moon_aspect_to(planets, "sun"),
        "moon_aspect": None,
        "mercury_aspect": _find_moon_aspect_to(planets, "mercury"),
        "venus_aspect": _find_moon_aspect_to(planets, "venus"),
        "mars_aspect": _find_moon_aspect_to(planets, "mars"),
        "jupiter_aspect": _find_moon_aspect_to(planets, "jupiter"),
        "saturn_aspect": _find_moon_aspect_to(planets, "saturn"),
        "transits": _get_transits(date, birth_data),
    }


def _find_moon_aspect_to(planets: dict, target: str) -> Optional[str]:
    moon_lon = planets["moon"]["longitude"]
    target_lon = planets[target]["longitude"]
    return _aspect_between(moon_lon, target_lon)


def get_month_data(year: int, month: int, birth_data: dict) -> list:
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    result = []
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day, 12, 0, 0)
        result.append(get_daily_data(date, birth_data))
    return result
