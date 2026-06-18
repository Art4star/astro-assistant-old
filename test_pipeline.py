#!/usr/bin/env python3
"""
Інтеграційний тест data pipeline astro-assistant.
Перевіряє що кожен компонент:
  1) повертає дані в очікуваному форматі
  2) передає їх далі без втрат
  3) кінцевий вивід містить інформацію від кожного етапу

Запуск: python3 test_pipeline.py
"""

import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

PASSED = 0
FAILED = 0
ERRORS = []

TEST_DATE = datetime(2026, 6, 15, 12, 0, 0)
TEST_YEAR = 2026
TEST_MONTH = 6


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✓ {name}")
    else:
        FAILED += 1
        msg = f"  ✗ {name}" + (f" — {detail}" if detail else "")
        print(msg)
        ERRORS.append(msg)


def section(title):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ═══════════════════════════════════════════════════
# 1. CALCULATOR → daily_data
# ═══════════════════════════════════════════════════
section("1. engine/calculator.py → get_daily_data")

from engine.calculator import get_daily_data, get_month_data

birth_data = {}
bd_path = os.path.join(BASE_DIR, "data", "birth_data.json")
if os.path.exists(bd_path):
    with open(bd_path) as f:
        birth_data = json.load(f)
check("birth_data.json існує і не порожній", bool(birth_data))

daily = get_daily_data(TEST_DATE, birth_data)
check("get_daily_data повертає dict", isinstance(daily, dict))

REQUIRED_DAILY_KEYS = [
    "date", "moon_sign", "moon_phase", "moon_voc",
    "mercury_retrograde",
]
for key in REQUIRED_DAILY_KEYS:
    check(f"daily_data має ключ '{key}'", key in daily, f"відсутній: {key}")

check("moon_sign — валідний знак",
      daily.get("moon_sign") in [
          "aries", "taurus", "gemini", "cancer", "leo", "virgo",
          "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"],
      f"got: {daily.get('moon_sign')}")

check("moon_phase — валідна фаза",
      daily.get("moon_phase") in [
          "new", "waxing_crescent", "first_quarter", "waxing_gibbous",
          "full", "waning_gibbous", "last_quarter", "balsamic"],
      f"got: {daily.get('moon_phase')}")

check("moon_voc — bool", isinstance(daily.get("moon_voc"), bool))
check("mercury_retrograde — bool", isinstance(daily.get("mercury_retrograde"), bool))


# ═══════════════════════════════════════════════════
# 2. INTERPRETER → scores
# ═══════════════════════════════════════════════════
section("2. engine/interpreter.py → score_day, get_overall_score, get_day_label")

from engine.interpreter import (
    score_day, get_overall_score, get_day_label,
    get_warnings, get_recommendations, ACTIVITY_RULES,
)

scores = score_day(daily)
check("score_day повертає dict", isinstance(scores, dict))
check("scores має всі активності з ACTIVITY_RULES",
      set(ACTIVITY_RULES.keys()).issubset(set(scores.keys())),
      f"missing: {set(ACTIVITY_RULES.keys()) - set(scores.keys())}")

for act, sc in scores.items():
    check(f"score '{act}' — int у межах [-20, +20]",
          isinstance(sc, (int, float)) and -20 <= sc <= 20,
          f"got: {sc}")

overall = get_overall_score(scores)
check("get_overall_score — int/float", isinstance(overall, (int, float)))

label = get_day_label(overall, scores)
check("get_day_label — непорожній str", isinstance(label, str) and len(label) > 0,
      f"got: {label!r}")

warnings = get_warnings(daily)
check("get_warnings — list", isinstance(warnings, list))

recs = get_recommendations(daily, scores)
check("get_recommendations — dict з best_for, avoid, tip",
      isinstance(recs, dict) and "best_for" in recs and "avoid" in recs and "tip" in recs,
      f"keys: {list(recs.keys()) if isinstance(recs, dict) else 'not dict'}")


# ═══════════════════════════════════════════════════
# 3. LUNAR → names, emojis
# ═══════════════════════════════════════════════════
section("3. engine/lunar.py → get_phase_emoji, get_sign_name_ua, get_phase_name_ua")

from engine.lunar import get_phase_emoji, get_sign_name_ua, get_phase_name_ua

phase_emoji = get_phase_emoji(daily["moon_phase"])
check("get_phase_emoji — непорожній", len(phase_emoji) > 0)

sign_ua = get_sign_name_ua(daily["moon_sign"])
check("get_sign_name_ua — українська назва", isinstance(sign_ua, str) and len(sign_ua) > 2,
      f"got: {sign_ua!r}")

phase_ua = get_phase_name_ua(daily["moon_phase"])
check("get_phase_name_ua — українська назва", isinstance(phase_ua, str) and len(phase_ua) > 2,
      f"got: {phase_ua!r}")


# ═══════════════════════════════════════════════════
# 4. MONTH DATA → calculator batch
# ═══════════════════════════════════════════════════
section("4. engine/calculator.py → get_month_data")

month_data = get_month_data(TEST_YEAR, TEST_MONTH, birth_data)
check("get_month_data — list", isinstance(month_data, list))
check("get_month_data — 28-31 днів", 28 <= len(month_data) <= 31,
      f"got: {len(month_data)}")
check("кожен день має date, moon_sign, moon_phase",
      all("date" in d and "moon_sign" in d and "moon_phase" in d for d in month_data))


# ═══════════════════════════════════════════════════
# 5. FORECAST AGENT → interpret.json
# ═══════════════════════════════════════════════════
section("5. agents/forecast_agent.py → interpret.json")

pkg_path = os.path.join(BASE_DIR, "output", "data", f"{TEST_YEAR}-{TEST_MONTH:02d}-interpret.json")
check("interpret.json існує", os.path.exists(pkg_path))

pkg = {}
if os.path.exists(pkg_path):
    with open(pkg_path) as f:
        pkg = json.load(f)

REQUIRED_PKG_KEYS = ["natal_chart", "forecast", "lunar_calendar"]
for key in REQUIRED_PKG_KEYS:
    check(f"interpret.json має '{key}'", key in pkg)

forecast = pkg.get("forecast", {})
check("forecast.top_transits — list", isinstance(forecast.get("top_transits"), list))
check("forecast.critical_windows — list", isinstance(forecast.get("critical_windows"), list))
check("top_transits > 0", len(forecast.get("top_transits", [])) > 0)

if forecast.get("top_transits"):
    t = forecast["top_transits"][0]
    TRANSIT_KEYS = ["transit_planet", "natal_planet", "aspect", "intensity", "peak_date"]
    for key in TRANSIT_KEYS:
        check(f"transit має '{key}'", key in t, f"keys: {list(t.keys())}")

if forecast.get("critical_windows"):
    w = forecast["critical_windows"][0]
    CW_KEYS = ["type", "transit_planet", "natal_planet", "aspect", "intensity"]
    for key in CW_KEYS:
        check(f"critical_window має '{key}'", key in w)

lc = pkg.get("lunar_calendar", {})
check("lunar_calendar.day_by_day — list", isinstance(lc.get("day_by_day"), list))


# ═══════════════════════════════════════════════════
# 6. SYNTHESIZER → transit narratives + report sections
# ═══════════════════════════════════════════════════
section("6. engine/synthesizer.py → narratives + build_report_sections")

from engine.synthesizer import (
    get_transit_narratives, build_report_sections,
    get_month_theme, _make_narrative,
)

top_transits = forecast.get("top_transits", [])
narratives = get_transit_narratives(top_transits)
check("get_transit_narratives — list", isinstance(narratives, list))
check("narratives > 0 (є транзити для інтерпретації)", len(narratives) > 0)

if narratives:
    n = narratives[0]
    for key in ["icon", "title", "impact", "action", "intensity"]:
        check(f"narrative має '{key}'", key in n, f"keys: {list(n.keys())}")
    check("narrative.title — непорожній str", isinstance(n["title"], str) and len(n["title"]) > 5)
    check("narrative.action — непорожній str", isinstance(n["action"], str) and len(n["action"]) > 5)

goals = []
goals_path = os.path.join(BASE_DIR, "data", "goals.json")
if os.path.exists(goals_path):
    with open(goals_path) as f:
        goals = json.load(f).get("active", [])

report = build_report_sections(month_data, birth_data, goals=goals, forecast_data=forecast)
check("build_report_sections — dict", isinstance(report, dict))

REPORT_KEYS = ["month_theme", "period_overview", "sections", "transit_narratives", "goal_cards"]
for key in REPORT_KEYS:
    check(f"report має '{key}'", key in report)

mt = report.get("month_theme", {})
check("month_theme.title — str", isinstance(mt.get("title"), str) and len(mt.get("title", "")) > 0)
check("month_theme.bullets — list", isinstance(mt.get("bullets"), list))

check("report.transit_narratives збігається з окремим виходом",
      len(report.get("transit_narratives", [])) == len(narratives))


# ═══════════════════════════════════════════════════
# 7. GOALS AGENT → goal_windows
# ═══════════════════════════════════════════════════
section("7. agents/goals_agent.py → goal alignment")

from agents.goals_agent import GoalsAgent
from agents.context import AgentContext

ctx = AgentContext(request={"type": "month", "year": TEST_YEAR, "month": TEST_MONTH})
ctx.birth_data = birth_data
ctx.year = TEST_YEAR
ctx.month = TEST_MONTH
ctx.forecast_data = forecast

ga = GoalsAgent()
check("GoalsAgent.can_run — True", ga.can_run(ctx))

ctx = ga.run(ctx)
check("active_goals заповнені", ctx.active_goals is not None and len(ctx.active_goals) > 0,
      f"count: {len(ctx.active_goals) if ctx.active_goals else 0}")
check("goal_windows заповнені", ctx.goal_windows is not None and isinstance(ctx.goal_windows, list))

if ctx.goal_windows:
    gw = ctx.goal_windows[0]
    for key in ["goal_id", "goal_title", "monthly_support", "score"]:
        check(f"goal_window має '{key}'", key in gw, f"keys: {list(gw.keys())}")
    check("monthly_support — валідне значення",
          gw.get("monthly_support") in ("strong", "moderate", "weak", "blocked"),
          f"got: {gw.get('monthly_support')}")


# ═══════════════════════════════════════════════════
# 8. FULL PIPELINE → Executor
# ═══════════════════════════════════════════════════
section("8. Full agent pipeline (Executor)")

from agents.router import RouterAgent
from agents.executor import Executor

request = {"type": "month", "year": TEST_YEAR, "month": TEST_MONTH}
router = RouterAgent()
full_ctx = router.build_context(request)
plan = router.route(request)

check("router.build_context заповнює birth_data", full_ctx.birth_data is not None)
check("router.route повертає plan з агентами", len(plan.agents) > 0,
      f"agents: {plan.agents}")

full_ctx = Executor().run(plan, full_ctx)

real_errors = [e for e in full_ctx.errors if not e["error"].startswith("SKIP")]
check("pipeline без помилок", len(real_errors) == 0,
      f"errors: {real_errors}")

check("forecast_data заповнено", full_ctx.has("forecast_data"))
check("active_goals заповнено", full_ctx.has("active_goals"))
check("report_sections заповнено", full_ctx.has("report_sections"))
check("output_path заповнено", full_ctx.has("output_path"))

if full_ctx.has("report_sections"):
    rs = full_ctx.report_sections
    check("report_sections.transit_narratives — від forecast",
          len(rs.get("transit_narratives", [])) > 0)
    check("report_sections.goal_cards — від goals",
          isinstance(rs.get("goal_cards"), list))


# ═══════════════════════════════════════════════════
# 9. GENERATE_TODAY_REPORT → Telegram output
# ═══════════════════════════════════════════════════
section("9. generate_report.py → generate_today_report")

from generate_report import generate_today_report, generate_week_report

today_text = generate_today_report()
check("generate_today_report — непорожній str", isinstance(today_text, str) and len(today_text) > 50)
check("містить емодзі дня (🔮)", "🔮" in today_text)
check("містить фазу місяця", any(e in today_text for e in "🌑🌒🌓🌔🌕🌖🌗🌘"))
check("містить рекомендацію (✅ або 🔴)", "✅" in today_text or "🔴" in today_text or "⚪" in today_text)
check("містить пораду (💡)", "💡" in today_text)
check("НЕ містить raw transit names (conjunction/square/trine)",
      "conjunction" not in today_text and "square" not in today_text and "trine" not in today_text,
      "технічні терміни потрапили в Telegram")


# ═══════════════════════════════════════════════════
# 10. GENERATE_WEEK_REPORT
# ═══════════════════════════════════════════════════
section("10. generate_report.py → generate_week_report")

week_text = generate_week_report()
check("generate_week_report — непорожній str", isinstance(week_text, str) and len(week_text) > 30)
check("містить 7 днів", week_text.count("—") >= 7, f"count '—': {week_text.count('—')}")


# ═══════════════════════════════════════════════════
# 11. MANAGE_GOALS → best_windows auto-calculation
# ═══════════════════════════════════════════════════
section("11. manage_goals.py → compute_best_windows")

from manage_goals import compute_best_windows

test_goal = {
    "id": "test_goal",
    "title": "Test",
    "category": "documents",
    "deadline": "2026-09-30",
}
windows = compute_best_windows(test_goal)
check("compute_best_windows — list", isinstance(windows, list))
check("windows > 0", len(windows) > 0)

if windows:
    w = windows[0]
    for key in ["date", "score", "reason"]:
        check(f"window має '{key}'", key in w)
    check("window.date — формат YYYY-MM-DD", len(w.get("date", "")) == 10 and w["date"][4] == "-")
    check("window.score > 0", w.get("score", 0) > 0)


# ═══════════════════════════════════════════════════
# 12. DATA CONSISTENCY — interpret.json ↔ calculator
# ═══════════════════════════════════════════════════
section("12. Консистентність даних між компонентами")

lc_days = pkg.get("lunar_calendar", {}).get("day_by_day", [])
if lc_days and month_data:
    lc_day15 = next((d for d in lc_days if d.get("date") == f"{TEST_YEAR}-{TEST_MONTH:02d}-15"), None)
    calc_day15 = next((d for d in month_data if d.get("date") == f"{TEST_YEAR}-{TEST_MONTH:02d}-15"), None)

    if lc_day15 and calc_day15:
        check("moon_sign збігається: lunar_calendar ↔ calculator",
              lc_day15.get("moon_sign") == calc_day15.get("moon_sign"),
              f"lunar: {lc_day15.get('moon_sign')}, calc: {calc_day15.get('moon_sign')}")


# ═══════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════
print(f"\n{'═' * 50}")
print(f"  РЕЗУЛЬТАТ: {PASSED} passed, {FAILED} failed")
print(f"{'═' * 50}")

if ERRORS:
    print("\nПомилки:")
    for e in ERRORS:
        print(e)

sys.exit(1 if FAILED else 0)
