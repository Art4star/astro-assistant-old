"""
Prepares interpretation package via Coordinator Agent.
Replaces direct agent calls with memory-aware orchestration.
"""

import os
from agents.coordinator import build_interpretation_package


def run(year: int, month: int, force: bool = False) -> None:
    print(f"\nCoordinator: preparing package for {year}-{month:02d}...")
    package, path = build_interpretation_package(year, month, force=force)
    _print_instructions(path, package)


def _print_instructions(path: str, package: dict) -> None:
    prompt_path = os.path.abspath("ASTRO_PROMPT.md")
    data_path = os.path.abspath(path)

    activated = package.get("activated_patterns", [])
    active_q = package.get("session_context", {}).get("active_question")

    print("\n" + "=" * 60)
    print("Пакет готовий. Відкрий нову сесію Claude Code:")
    print("=" * 60)
    print(f"\n1. Read: {prompt_path}")
    print(f"\n2. Read: {data_path}")
    print("\n3. Запитай:")
    print("   Зроби повний астрологічний аналіз на основі цих даних.")
    if active_q:
        print(f"   Активне питання: {active_q}")
    if activated:
        ids = ", ".join(p["id"] for p in activated)
        print(f"   Активовані патерни: {ids}")
    print("   Відповідай українською. Дотримуйся формату з ASTRO_PROMPT.md.")
    print("=" * 60 + "\n")
