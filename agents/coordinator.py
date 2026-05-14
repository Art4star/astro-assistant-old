"""
Coordinator Agent
Orchestrates Chart Parser → Forecast Engine → Interpretation.
Reads from Shared Memory Layer, trims context, merges outputs.
All agent communication is logged via protocol.send().
"""

import json
import os
from datetime import datetime
from agents.protocol import (
    AgentID, MsgType,
    task_request, task_complete, task_error, handoff, memory_write,
    send as bus_send, get_thread,
)


MEMORY_DIR = "data/memory"
OUTPUT_DATA_DIR = "output/data"


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_memory() -> dict:
    """Load full shared memory layer."""
    return {
        "user": _load(f"{MEMORY_DIR}/user.json"),
        "identity": _load(f"{MEMORY_DIR}/identity.json"),
        "natal_patterns": _load(f"{MEMORY_DIR}/natal_patterns.json"),
        "cycles": _load(f"{MEMORY_DIR}/cycles.json"),
        "coordinator": _load(f"{MEMORY_DIR}/coordinator.json"),
    }


def get_natal_chart(birth_data: dict, force_recompute: bool = False) -> dict:
    """Return cached natal chart or recompute if needed."""
    cache_path = f"{OUTPUT_DATA_DIR}/natal_chart.json"

    coordinator = _load(f"{MEMORY_DIR}/coordinator.json")
    cached = coordinator.get("natal_chart_cached", False)

    if cached and os.path.exists(cache_path) and not force_recompute:
        return _load(cache_path)

    req = bus_send(task_request(
        AgentID.COORDINATOR, AgentID.CHART_PARSER,
        task="parse_natal_chart",
        params={"birth_date": birth_data["birth_date"], "birth_city": birth_data["birth_city"]},
    ))

    print("  Agent 1: computing natal chart (Swiss Ephemeris)...")
    try:
        from agents.chart_parser import parse_natal_chart
        chart = parse_natal_chart(birth_data)

        os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)
        _save(cache_path, chart)

        bus_send(task_complete(
            AgentID.CHART_PARSER, AgentID.COORDINATOR,
            task="parse_natal_chart",
            result_path=cache_path,
            summary={
                "asc": f"{chart['angles']['ascendant']['sign']} {chart['angles']['ascendant']['degree']}°",
                "stelliums": [s["sign"] for s in chart.get("stelliums", [])],
                "angular_planets": chart.get("angular_planets", []),
            },
            parent_msg=req,
        ))
        bus_send(memory_write(
            AgentID.CHART_PARSER, cache_path,
            keys_written=["planets", "angles", "houses", "aspects", "stelliums"],
            reason="natal chart computed from birth data",
        ))

        coordinator["natal_chart_cached"] = True
        coordinator["natal_chart_path"] = cache_path
        coordinator["natal_chart_computed_at"] = datetime.now().strftime("%Y-%m-%d")
        _save(f"{MEMORY_DIR}/coordinator.json", coordinator)

    except Exception as e:
        bus_send(task_error(AgentID.CHART_PARSER, AgentID.COORDINATOR,
                            "parse_natal_chart", str(e), req))
        raise

    return chart


def get_forecast(birth_data: dict, year: int, month: int, force: bool = False) -> dict:
    """Return cached forecast or recompute."""
    period = f"{year}-{month:02d}"
    cache_path = f"{OUTPUT_DATA_DIR}/{period}-forecast.json"

    if os.path.exists(cache_path) and not force:
        return _load(cache_path)

    req = bus_send(task_request(
        AgentID.COORDINATOR, AgentID.FORECAST,
        task="build_forecast",
        params={"period": period, "natal_planets_count": len(birth_data.get("natal_planets", {}))},
    ))

    print(f"  Agent 3: computing forecast for {period}...")
    try:
        from agents.forecast_engine import build_forecast
        forecast = build_forecast(birth_data, year, month)
        _save(cache_path, forecast)

        bus_send(task_complete(
            AgentID.FORECAST, AgentID.COORDINATOR,
            task="build_forecast",
            result_path=cache_path,
            summary={
                "transits_count": len(forecast.get("transits", [])),
                "critical_windows": len(forecast.get("critical_windows", [])),
                "solar_return_moment": forecast.get("solar_return", {}).get("moment"),
            },
            parent_msg=req,
        ))
        bus_send(memory_write(
            AgentID.FORECAST, cache_path,
            keys_written=["transits", "solar_return", "critical_windows"],
            reason=f"forecast computed for {period}",
        ))

        _update_coordinator_session(period, "forecast_ready", True)

    except Exception as e:
        bus_send(task_error(AgentID.FORECAST, AgentID.COORDINATOR,
                            "build_forecast", str(e), req))
        raise

    return forecast


def build_interpretation_package(year: int, month: int, force: bool = False) -> dict:
    """
    Full orchestration: load memory, compute what's missing, assemble package.
    This is what Agent 2 (Claude) receives.
    """
    period = f"{year}-{month:02d}"
    package_path = f"{OUTPUT_DATA_DIR}/{period}-interpret.json"

    memory = load_memory()
    birth_data = _birth_data_from_memory(memory)

    natal_chart = get_natal_chart(birth_data, force_recompute=force)
    forecast = get_forecast(birth_data, year, month, force=force)

    goals = _load_goals()
    session_context = _load_session_context(period)
    active_cycles = _get_active_cycles(memory["cycles"], year)
    activated_patterns = _get_activated_patterns(
        memory["natal_patterns"], forecast["critical_windows"]
    )

    # Priority 2: trim to top-10 transits by intensity score
    top_transits = _top_transits(forecast["transits"], limit=10)

    # Priority 3: lunar calendar
    from agents.lunar_calendar import build_lunar_calendar
    print(f"  Lunar: computing Moon calendar for {period}...")
    lunar = build_lunar_calendar(year, month)

    # Priority 5: contradiction detection
    contradictions = _detect_contradictions(forecast["transits"])

    # Priority 7: goal alignment scoring
    goal_alignment = _score_goal_alignment(goals, forecast["transits"], forecast["critical_windows"])

    # Coordinator logs the handoff to Agent 2
    handoff_req = bus_send(task_request(
        AgentID.COORDINATOR, AgentID.INTERPRETATION,
        task="interpret_month",
        params={
            "period": period,
            "activated_patterns": [p["id"] for p in activated_patterns],
            "contradictions_found": len(contradictions),
            "active_question": session_context.get("active_question"),
        },
    ))

    package = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period": period,

        "user": memory["user"],
        "identity": _trim_identity(memory["identity"]),
        "activated_patterns": activated_patterns,
        "active_cycles": active_cycles,
        "session_context": session_context,
        "natal_chart": _trim_natal_chart(natal_chart),

        "forecast": {
            "period": forecast["period"],
            # Priority 2: top-10 by intensity, not all 118
            "top_transits": top_transits,
            "critical_windows": forecast["critical_windows"],
            "solar_return": forecast["solar_return"],
            # Full list kept for reference but clearly labelled
            "all_transits_count": len(forecast["transits"]),
        },

        # Priority 3
        "lunar_calendar": lunar,

        # Priority 5
        "contradictions": contradictions,

        # Priority 7
        "goal_alignment": goal_alignment,

        "goals": [
            {"title": g["title"], "category": g.get("category"),
             "priority": g.get("priority"), "deadline": g.get("deadline")}
            for g in goals
        ],

        "prompt_instructions": (
            "Use ASTRO_PROMPT.md as system prompt. Respond in Ukrainian. "
            "Prioritize identity patterns over raw aspects. "
            "Only reference top_transits — do not invent transits. "
            "Use peak_date for timing. Cite intensity scores."
        ),
    }

    _save(package_path, package)
    _update_coordinator_session(period, "package_ready", True)

    bus_send(handoff(
        AgentID.COORDINATOR, AgentID.INTERPRETATION,
        data_path=package_path,
        context={
            "prompt_path": "ASTRO_PROMPT.md",
            "activated_patterns": [p["id"] for p in package.get("activated_patterns", [])],
            "active_question": package.get("session_context", {}).get("active_question"),
        },
        parent_msg=handoff_req,
    ))

    return package, package_path


def record_prediction(period: str, forecast_summary: str, cause: list) -> None:
    """Log a prediction for future validation."""
    predictions = _load(f"{MEMORY_DIR}/predictions.json")
    pred_id = f"pred_{period.replace('-', '_')}_{len(predictions['predictions']):02d}"
    predictions["predictions"].append({
        "id": pred_id,
        "period": period,
        "forecast": forecast_summary,
        "cause": cause,
        "outcome": None,
        "validated": False,
        "validated_at": None,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    })
    _save(f"{MEMORY_DIR}/predictions.json", predictions)


def validate_prediction(pred_id: str, outcome: str, matched: bool) -> None:
    """Mark a past prediction as validated and update pattern confidence."""
    predictions = _load(f"{MEMORY_DIR}/predictions.json")
    for p in predictions["predictions"]:
        if p["id"] == pred_id:
            p["outcome"] = outcome
            p["validated"] = True
            p["validated_at"] = datetime.now().strftime("%Y-%m-%d")
            p["matched"] = matched
            break
    _save(f"{MEMORY_DIR}/predictions.json", predictions)


# ── Internal helpers ────────────────────────────────────────────────────────

def _birth_data_from_memory(memory: dict) -> dict:
    """Reconstruct birth_data dict from memory + original file."""
    import json
    with open("data/birth_data.json", encoding="utf-8") as f:
        return json.load(f)


def _load_goals() -> list:
    path = "data/goals.json"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [g for g in data.get("goals", []) if g.get("status") == "active"]


def _load_session_context(period: str) -> dict:
    path = f"{MEMORY_DIR}/sessions/{period}/context.json"
    if os.path.exists(path):
        return _load(path)
    return {"recent_topics": [], "active_question": None}


def _get_active_cycles(cycles_data: dict, year: int) -> list:
    return cycles_data.get(str(year), [])


def _get_activated_patterns(natal_patterns: dict, critical_windows: list) -> list:
    """Match critical windows to behavioral patterns."""
    window_planet_set = {w["transit_planet"] for w in critical_windows}
    window_type_set = {w["type"] for w in critical_windows}

    activated = []
    for p in natal_patterns.get("patterns", []):
        activated_by = p.get("when_activated", "")
        # Simple match: if pattern's trigger planets appear in critical windows
        match = any(planet in activated_by for planet in window_planet_set)
        match = match or any(wtype in p.get("theme", "") for wtype in window_type_set)
        if match:
            activated.append({
                "id": p["id"],
                "theme": p["theme"],
                "behavioral_signature": p["behavioral_signature"],
                "confidence": p["confidence"],
            })
    return activated


def _top_transits(transits: list, limit: int = 10) -> list:
    """Priority 2: return top N transits by intensity score."""
    sorted_t = sorted(transits, key=lambda x: -x.get("intensity", 0))
    return sorted_t[:limit]


def _detect_contradictions(transits: list) -> list:
    """
    Priority 5: find natal points where both expansion and restriction
    transits are active simultaneously.
    """
    EXPANSION_PLANETS = {"jupiter", "sun", "venus"}
    RESTRICTION_PLANETS = {"saturn", "pluto", "neptune"}
    EXPANSION_ASPECTS = {"trine", "sextile", "conjunction"}
    RESTRICTION_ASPECTS = {"square", "opposition"}

    natal_expand: dict = {}   # natal_planet → [transit]
    natal_restrict: dict = {} # natal_planet → [transit]

    for t in transits:
        if t.get("intensity", 0) < 15:
            continue
        np = t["natal_planet"]
        planet = t["transit_planet"]
        aspect = t["aspect"]
        if planet in EXPANSION_PLANETS and aspect in EXPANSION_ASPECTS:
            natal_expand.setdefault(np, []).append(t)
        if planet in RESTRICTION_PLANETS and aspect in RESTRICTION_ASPECTS:
            natal_restrict.setdefault(np, []).append(t)

    contradictions = []
    for np in set(natal_expand) & set(natal_restrict):
        exp = natal_expand[np]
        rest = natal_restrict[np]
        contradictions.append({
            "natal_point": np,
            "expanding": [f"{t['transit_planet']} {t['aspect']}" for t in exp],
            "restricting": [f"{t['transit_planet']} {t['aspect']}" for t in rest],
            "interpretation_note": (
                f"Натальний {np} одночасно під тиском розширення і обмеження. "
                f"Не ігноруй — вкажи обидві сили і як їх збалансувати."
            ),
        })
    return contradictions


def _score_goal_alignment(
    goals: list, transits: list, critical_windows: list
) -> list:
    """
    Priority 7: score how well this month's transits support each goal.
    Returns goals with support level and best action.
    """
    CATEGORY_TRANSIT_MAP = {
        "career":       {"expand": [("jupiter","trine"), ("jupiter","conjunction"), ("saturn","trine")],
                         "block":  [("saturn","square"), ("saturn","opposition"), ("neptune","square")]},
        "finance":      {"expand": [("jupiter","trine"), ("venus","trine"), ("jupiter","sextile")],
                         "block":  [("saturn","square"), ("pluto","square")]},
        "health":       {"expand": [("sun","trine"), ("mars","trine"), ("jupiter","trine")],
                         "block":  [("saturn","square"), ("mars","square")]},
        "relationships":{"expand": [("venus","trine"), ("jupiter","trine"), ("venus","sextile")],
                         "block":  [("saturn","square"), ("pluto","square"), ("mars","opposition")]},
        "creativity":   {"expand": [("venus","trine"), ("sun","trine"), ("jupiter","sextile")],
                         "block":  [("saturn","square")]},
        "learning":     {"expand": [("mercury","trine"), ("jupiter","trine"), ("mercury","sextile")],
                         "block":  [("mercury","square"), ("saturn","opposition")]},
    }

    transit_set = {(t["transit_planet"], t["aspect"]) for t in transits if t.get("intensity", 0) >= 15}

    result = []
    for goal in goals:
        category = (goal.get("category") or "").lower()
        rules = CATEGORY_TRANSIT_MAP.get(category, {})
        expand_hits = [p for p in rules.get("expand", []) if p in transit_set]
        block_hits  = [p for p in rules.get("block",  []) if p in transit_set]

        score = len(expand_hits) * 2 - len(block_hits) * 3
        if score >= 3:
            support = "strong"
        elif score >= 1:
            support = "moderate"
        elif score == 0:
            support = "weak"
        else:
            support = "blocked"

        supporting_transit = (
            f"{expand_hits[0][0]} {expand_hits[0][1]}" if expand_hits else None
        )
        blocking_transit = (
            f"{block_hits[0][0]} {block_hits[0][1]}" if block_hits else None
        )

        result.append({
            "goal_title": goal.get("title", ""),
            "category": category,
            "monthly_support": support,
            "score": score,
            "supporting_transit": supporting_transit,
            "blocking_transit": blocking_transit,
        })

    result.sort(key=lambda x: -x["score"])
    return result


def _trim_identity(identity: dict) -> dict:
    """Remove meta fields, keep signal."""
    return {k: v for k, v in identity.items() if not k.startswith("_")}


def _trim_natal_chart(chart: dict) -> dict:
    """Keep only high-signal natal data: angles, stelliums, angular planets, top aspects."""
    return {
        "user": chart.get("user"),
        "angles": chart.get("angles"),
        "houses": chart.get("houses"),
        "ascendant_ruler": chart.get("ascendant_ruler"),
        "stelliums": chart.get("stelliums"),
        "angular_planets": chart.get("angular_planets"),
        "dominants": chart.get("dominants"),
        "aspects": chart.get("aspects", [])[:15],  # top 15 by orb
        "planets": chart.get("planets"),
    }


def _update_coordinator_session(period: str, key: str, value) -> None:
    coordinator = _load(f"{MEMORY_DIR}/coordinator.json")
    if "sessions" not in coordinator:
        coordinator["sessions"] = {}
    if period not in coordinator["sessions"]:
        coordinator["sessions"][period] = {}
    coordinator["sessions"][period][key] = value
    coordinator["_meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    _save(f"{MEMORY_DIR}/coordinator.json", coordinator)
