"""
Agent 1 — Chart Parser
Parses natal chart: planets, houses, aspects, dispositors, dominants.
Uses Swiss Ephemeris (pyswisseph) for precise geocentric ecliptic positions.
Output: structured dict ready for Claude Code interpretation.

FROZEN 2026-05-16 — Placidus house assignment verified against astro.com.
DO NOT MODIFY without explicit permission from Artur in the current conversation.
"""

import math
import pytz
import swisseph as swe
from datetime import datetime
from typing import Optional

PLANET_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

SIGN_ELEMENTS = {
    "aries": "fire", "leo": "fire", "sagittarius": "fire",
    "taurus": "earth", "virgo": "earth", "capricorn": "earth",
    "gemini": "air", "libra": "air", "aquarius": "air",
    "cancer": "water", "scorpio": "water", "pisces": "water",
}

SIGN_MODALITIES = {
    "aries": "cardinal", "cancer": "cardinal", "libra": "cardinal", "capricorn": "cardinal",
    "taurus": "fixed", "leo": "fixed", "scorpio": "fixed", "aquarius": "fixed",
    "gemini": "mutable", "virgo": "mutable", "sagittarius": "mutable", "pisces": "mutable",
}

SIGN_RULERS = {
    "aries": "mars", "taurus": "venus", "gemini": "mercury",
    "cancer": "moon", "leo": "sun", "virgo": "mercury",
    "libra": "venus", "scorpio": "mars", "sagittarius": "jupiter",
    "capricorn": "saturn", "aquarius": "saturn", "pisces": "jupiter",
}

DIGNITIES = {
    "domicile": {
        "sun": ["leo"], "moon": ["cancer"], "mercury": ["gemini", "virgo"],
        "venus": ["taurus", "libra"], "mars": ["aries", "scorpio"],
        "jupiter": ["sagittarius", "pisces"], "saturn": ["capricorn", "aquarius"],
        "uranus": ["aquarius"], "neptune": ["pisces"], "pluto": ["scorpio"],
    },
    "exaltation": {
        "sun": "aries", "moon": "taurus", "mercury": "virgo", "venus": "pisces",
        "mars": "capricorn", "jupiter": "cancer", "saturn": "libra",
        "uranus": "scorpio", "neptune": "cancer", "pluto": "aries",
        "true_node": "gemini",
    },
    "detriment": {
        "sun": ["aquarius"], "moon": ["capricorn"], "mercury": ["sagittarius", "pisces"],
        "venus": ["aries", "scorpio"], "mars": ["taurus", "libra"],
        "jupiter": ["gemini", "virgo"], "saturn": ["cancer", "leo"],
        "uranus": ["leo"], "neptune": ["virgo"], "pluto": ["taurus"],
    },
    "fall": {
        "sun": "libra", "moon": "scorpio", "mercury": "pisces", "venus": "virgo",
        "mars": "cancer", "jupiter": "capricorn", "saturn": "aries",
        "uranus": "taurus", "neptune": "capricorn", "pluto": "libra",
    },
}


def get_dignity(planet: str, sign: str) -> str:
    """Returns planet dignity: domicile, exaltation, detriment, fall, or peregrine."""
    dom = DIGNITIES["domicile"].get(planet, [])
    if isinstance(dom, str):
        dom = [dom]
    if sign in dom:
        return "domicile"
    if DIGNITIES["exaltation"].get(planet) == sign:
        return "exaltation"
    det = DIGNITIES["detriment"].get(planet, [])
    if isinstance(det, str):
        det = [det]
    if sign in det:
        return "detriment"
    if DIGNITIES["fall"].get(planet) == sign:
        return "fall"
    return "peregrine"


ASPECT_ORBS = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "square": 6.0,
    "trine": 6.0,
    "sextile": 4.0,
}

ASPECT_ANGLES = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}

# Swiss Ephemeris planet IDs
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
    "lilith": swe.MEAN_APOG,  # Mean Black Moon Lilith (no .se1 file needed)
}

PLANETS_ORDER = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
    "true_node", "lilith",
]

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


def _get_degree_in_sign(lon: float) -> float:
    return round(lon % 30, 2)


def _calc_houses_placidus(jd: float, lat: float, lon: float) -> tuple:
    """Returns (cusps, ascmc) using Placidus system. cusps[0..11] = H1..H12."""
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    return cusps, ascmc


def _planet_house(planet_lon: float, cusps: tuple) -> int:
    """Assigns planet to house 1-12 using Placidus cusps (degree-based)."""
    lon = planet_lon % 360
    for i in range(12):
        start = cusps[i] % 360
        end = cusps[(i + 1) % 12] % 360
        if end > start:
            if start <= lon < end:
                return i + 1
        else:  # arc wraps around 0°/360°
            if lon >= start or lon < end:
                return i + 1
    return 1


def _aspect_between(lon1: float, lon2: float) -> Optional[tuple]:
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    for angle, name in ASPECT_ANGLES.items():
        orb = abs(diff - angle)
        if orb <= ASPECT_ORBS[name]:
            return name, round(orb, 2)
    return None


def _get_aspects(planets: dict) -> list:
    aspects = []
    names = list(planets.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1, p2 = names[i], names[j]
            result = _aspect_between(planets[p1]["longitude"], planets[p2]["longitude"])
            if result:
                aspect_name, orb = result
                aspects.append({
                    "p1": p1,
                    "p2": p2,
                    "type": aspect_name,
                    "orb": orb,
                    "harmony": aspect_name in ("trine", "sextile", "conjunction"),
                })
    aspects.sort(key=lambda x: x["orb"])
    return aspects


def _get_dispositors(planets: dict) -> dict:
    return {name: SIGN_RULERS[data["sign"]] for name, data in planets.items()
            if data["sign"] in SIGN_RULERS}


def _get_dominants(planets: dict) -> dict:
    # Only classical planets for dominant calculation
    classical = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    elements, modalities, signs = {}, {}, {}
    for name, data in planets.items():
        if name not in classical:
            continue
        sign = data["sign"]
        el = SIGN_ELEMENTS[sign]
        mod = SIGN_MODALITIES[sign]
        elements[el] = elements.get(el, 0) + 1
        modalities[mod] = modalities.get(mod, 0) + 1
        signs[sign] = signs.get(sign, 0) + 1
    return {
        "element": max(elements, key=elements.get),
        "element_counts": elements,
        "modality": max(modalities, key=modalities.get),
        "modality_counts": modalities,
        "sign": max(signs, key=signs.get),
        "sign_counts": signs,
    }


def _get_stelliums(planets: dict) -> list:
    sign_groups = {}
    for name, data in planets.items():
        sign = data["sign"]
        sign_groups.setdefault(sign, []).append(name)
    return [
        {"sign": sign, "planets": plist}
        for sign, plist in sign_groups.items()
        if len(plist) >= 3
    ]


def _get_angular_planets(planets: dict) -> list:
    return [name for name, data in planets.items() if data.get("house") in (1, 4, 7, 10)]


def parse_natal_chart(birth_data: dict) -> dict:
    tz = pytz.timezone(birth_data["timezone"])
    birth_dt_str = f"{birth_data['birth_date']} {birth_data['birth_time']}"
    birth_local = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M")
    birth_utc = tz.localize(birth_local).astimezone(pytz.utc)

    lat = birth_data["latitude"]
    lon = birth_data["longitude"]
    jd = _to_jd(birth_utc)

    planets = {}
    for name in PLANETS_ORDER:
        pid = PLANET_IDS[name]
        planet_lon = _get_longitude(pid, jd)
        speed = _get_speed(pid, jd)
        planets[name] = {
            "longitude": round(planet_lon, 4),
            "sign": _get_sign(planet_lon),
            "degree": _get_degree_in_sign(planet_lon),
            "retrograde": speed < 0,
        }

    cusps, ascmc = _calc_houses_placidus(jd, lat, lon)
    asc_lon = ascmc[0] % 360
    mc_lon = ascmc[1] % 360
    angles = {
        "ascendant": {
            "longitude": round(asc_lon, 4),
            "sign": _get_sign(asc_lon),
            "degree": _get_degree_in_sign(asc_lon),
        },
        "midheaven": {
            "longitude": round(mc_lon, 4),
            "sign": _get_sign(mc_lon),
            "degree": _get_degree_in_sign(mc_lon),
        },
    }

    # Placidus house cusps: sign label per house for display
    houses = {i + 1: _get_sign(cusps[i]) for i in range(12)}
    # Degree-based house assignment using actual Placidus cusps
    for name in planets:
        planets[name]["house"] = _planet_house(planets[name]["longitude"], cusps)

    all_points = dict(planets)
    all_points["ascendant"] = angles["ascendant"]
    all_points["midheaven"] = angles["midheaven"]

    house_cusps = {i + 1: round(cusps[i] % 360, 4) for i in range(12)}

    return {
        "user": {
            "name": birth_data.get("name", ""),
            "birth_date": birth_data["birth_date"],
            "birth_time": birth_data["birth_time"],
            "birth_city": birth_data["birth_city"],
        },
        "planets": planets,
        "angles": angles,
        "houses": houses,
        "house_cusps": house_cusps,
        "ascendant_ruler": SIGN_RULERS[angles["ascendant"]["sign"]],
        "aspects": _get_aspects(all_points),
        "dispositors": _get_dispositors(planets),
        "dominants": _get_dominants(planets),
        "stelliums": _get_stelliums(planets),
        "angular_planets": _get_angular_planets(planets),
    }
