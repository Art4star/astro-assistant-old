"""
Priority 4 — Structured Output Schema for Agent 2 (Claude / Interpretation)
Defines the JSON structure Claude must produce.
Coordinator validates the output before storing.
"""

import json
from typing import Optional


# Schema that Agent 2 must follow
OUTPUT_SCHEMA = {
    "period": "YYYY-MM",
    "generated_at": "YYYY-MM-DD HH:MM",
    "confidence_overall": "<low|medium|high>",

    "identity_resonance": {
        "patterns_active": ["list of pattern IDs from natal_patterns that are activated"],
        "primary_theme": "one sentence — the core theme of this month for this person",
        "tension_points": ["list of inner conflicts or pressures this month"],
    },

    "timing": {
        "best_window": {
            "dates": "YYYY-MM-DD – YYYY-MM-DD",
            "for": ["list of activities: decisions, launches, negotiations, etc."],
            "reason": "which transit supports this — must cite data",
        },
        "avoid_window": {
            "dates": "YYYY-MM-DD – YYYY-MM-DD",
            "reason": "which transit creates difficulty — must cite data",
        },
        "peak_tension_date": "YYYY-MM-DD — when peak_date of highest-intensity transit lands",
    },

    "critical_windows_analysis": [
        {
            "window_type": "<from critical_windows type field>",
            "transit": "Planet aspect natal Planet",
            "peak_date": "YYYY-MM-DD",
            "behavioral_prediction": "what will likely happen based on identity patterns",
            "recommended_action": "concrete action for this person",
            "confidence": "<low|medium|high>",
        }
    ],

    "lunar_rhythm": {
        "new_moon_focus": "what to initiate at new moon based on sign",
        "full_moon_release": "what to release or complete at full moon",
        "voc_warnings": ["key VOC periods — avoid signing, launching, deciding"],
    },

    "goal_alignment": [
        {
            "goal_title": "from goals list",
            "monthly_support": "<strong|moderate|weak|blocked>",
            "best_action_this_month": "concrete step",
            "transit_supporting": "which transit helps — must cite data",
        }
    ],

    "solar_return_note": "one paragraph on how SR chart modifies interpretation for the year",

    "contradictions_noted": [
        "explicit contradictions found — e.g. Jupiter expanding while Saturn restricting same natal point"
    ],

    "three_key_insights": [
        "Most important thing to know this month — grounded in data",
        "Second most important",
        "Third most important",
    ],
}


INSTRUCTIONS_FOR_AGENT2 = """
## Output instructions for Agent 2 (Interpretation Engine)

You MUST produce a JSON response matching the schema below.
Rules to prevent hallucination:

1. CITE DATA: Every claim about timing must reference a specific field from the input JSON
   (e.g. "Jupiter opposition natal Sun, peak_date 2026-05-15, intensity 67.2")

2. USE IDENTITY LAYER FIRST: Before referencing raw aspects, check identity.json patterns.
   Interpret transits through the person's behavioral signature, not generic astrology.

3. ONLY USE peak_date FOR TIMING: Never invent dates. Use peak_date from transit data.

4. STATUS MATTERS:
   - "applying" transit = energy building, prepare now
   - "exact_within_month" = action window is NOW
   - "separating" transit = already peaked, process rather than initiate

5. INTENSITY THRESHOLD: Only interpret transits with intensity ≥ 20.
   Do not mention transits below this threshold.

6. CONFIDENCE LABELS: Mark your own confidence. If the data is ambiguous → "low".

7. CONTRADICTIONS: If two transits conflict (e.g. expansion + restriction on same natal point),
   list it in contradictions_noted. Do not suppress it.

8. VOC: Warn about VOC periods lasting > 4 hours. Do not schedule key actions in VOC.

Output only valid JSON. No prose outside the JSON structure.
"""


def get_prompt_addition() -> str:
    """Returns the schema + instructions to append to ASTRO_PROMPT.md for the session."""
    schema_str = json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)
    return f"""
---
## Structured Output Schema (required)

{INSTRUCTIONS_FOR_AGENT2}

### Required JSON schema:
```json
{schema_str}
```
"""


def validate_output(raw_output: str) -> tuple[bool, Optional[dict], list]:
    """
    Validate Agent 2 output against schema.
    Returns (is_valid, parsed_dict, list_of_errors).
    """
    errors = []

    try:
        # Strip markdown code blocks if present
        text = raw_output.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return False, None, [f"JSON parse error: {e}"]

    required_keys = [
        "period", "confidence_overall", "identity_resonance",
        "timing", "critical_windows_analysis", "lunar_rhythm",
        "three_key_insights",
    ]
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    insights = data.get("three_key_insights", [])
    if len(insights) < 3:
        errors.append("three_key_insights must have exactly 3 items")

    timing = data.get("timing", {})
    if "peak_tension_date" not in timing:
        errors.append("timing.peak_tension_date is required")

    return len(errors) == 0, data, errors


def save_interpretation(data: dict, year: int, month: int) -> str:
    """Save validated interpretation to session memory."""
    import os
    path = f"data/memory/sessions/{year}-{month:02d}/interpretation.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
