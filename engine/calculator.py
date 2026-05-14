from datetime import datetime, timedelta
from typing import Optional
import swisseph as swe

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

# Moshier ephemeris — no .se1 files required, accuracy sufficient for transits
_SE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

PLANET_IDS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
    "true_node": swe.TRUE_NODE,
}


def _to_jd(dt: datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0 + dt.second / 3600.0)


def _calc_ut(planet_id: int, jd: float):
    result, _ = swe.calc_ut(jd, planet_id, _SE_FLAGS)
    return result


def _get_longitude(planet_id: int, jd: float) -> float:
    return _calc_ut(planet_id, jd)[0] % 360


def _get_speed(planet_id: int, jd: float) -> float:
    return _calc_ut(planet_id, jd)[3]


def _get_sign(longitude: float) -> str:
    return PLANET_SIGNS[int(longitude / 30) % 12]


def _aspect_between(lon1: float, lon2: float) -> Optional[str]:
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    for angle, name in ASPECT_NAMES.items():
        if abs(diff - angle) <= ORB:
            return name
    return None


def get_moon_phase(date: datetime) -> str:
    jd = _to_jd(date)
    sun_lon = _get_longitude(swe.SUN, jd)
    moon_lon = _get_longitude(swe.MOON, jd)
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
    jd = _to_jd(date)
    moon_lon = _get_longitude(swe.MOON, jd)
    current_sign_end = (int(moon_lon / 30) + 1) * 30.0

    check = date
    while True:
        check += timedelta(hours=1)
        check_jd = _to_jd(check)
        next_lon = _get_longitude(swe.MOON, check_jd)
        if next_lon >= current_sign_end or (current_sign_end >= 360 and next_lon < 30):
            break
        for pid in [swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]:
            if _aspect_between(next_lon, _get_longitude(pid, check_jd)):
                return False
        if check > date + timedelta(hours=72):
            break
    return True


def is_mercury_retrograde(date: datetime) -> bool:
    return _get_speed(swe.MERCURY, _to_jd(date)) < 0


def _get_planet_data(date: datetime) -> dict:
    jd = _to_jd(date)
    planets = {}
    for name, pid in PLANET_IDS.items():
        result = _calc_ut(pid, jd)
        lon = result[0] % 360
        planets[name] = {
            "longitude": lon,
            "sign": _get_sign(lon),
            "retrograde": result[3] < 0,
        }
    return planets


def _get_transits(date: datetime, birth_data: dict) -> list:
    natal_planets = birth_data.get("natal_planets", {})
    if not natal_planets:
        return []

    current_planets = _get_planet_data(date)
    transits = []
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


def _natal_transit_aspect(transit_planet: str, natal_planet: str, transits: list) -> Optional[str]:
    for t in transits:
        if t["transit"] == transit_planet and t["natal"] == natal_planet:
            return t["aspect"]
    return None


def _find_moon_aspect_to(planets: dict, target: str) -> Optional[str]:
    return _aspect_between(planets["moon"]["longitude"], planets[target]["longitude"])


def get_daily_data(date: datetime, birth_data: dict) -> dict:
    planets = _get_planet_data(date)
    transits = _get_transits(date, birth_data)

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
        "tr_jupiter_natal_sun": _natal_transit_aspect("jupiter", "sun", transits),
        "tr_saturn_natal_sun": _natal_transit_aspect("saturn", "sun", transits),
        "tr_mars_natal_sun": _natal_transit_aspect("mars", "sun", transits),
        "tr_venus_natal_sun": _natal_transit_aspect("venus", "sun", transits),
        "tr_jupiter_natal_moon": _natal_transit_aspect("jupiter", "moon", transits),
        "tr_saturn_natal_moon": _natal_transit_aspect("saturn", "moon", transits),
        "tr_mars_natal_moon": _natal_transit_aspect("mars", "moon", transits),
        "tr_jupiter_natal_mercury": _natal_transit_aspect("jupiter", "mercury", transits),
        "tr_saturn_natal_mercury": _natal_transit_aspect("saturn", "mercury", transits),
        "tr_mars_natal_mercury": _natal_transit_aspect("mars", "mercury", transits),
        "tr_jupiter_natal_venus": _natal_transit_aspect("jupiter", "venus", transits),
        "tr_venus_natal_venus": _natal_transit_aspect("venus", "venus", transits),
        "tr_mars_natal_mars": _natal_transit_aspect("mars", "mars", transits),
        "tr_saturn_natal_mars": _natal_transit_aspect("saturn", "mars", transits),
        "transits": transits,
    }


def get_month_data(year: int, month: int, birth_data: dict) -> list:
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    result = []
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day, 12, 0, 0)
        result.append(get_daily_data(date, birth_data))
    return result
