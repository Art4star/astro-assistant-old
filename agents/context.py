from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AgentContext:
    """
    Спільна пам'ять між агентами.
    Кожен агент читає що потрібно і додає свій результат.
    Поля None означають «ще не заповнено цим агентом».
    """
    request: dict

    # Заповнює Router перед запуском
    birth_data: Optional[dict] = None
    year: Optional[int] = None
    month: Optional[int] = None

    # ForecastAgent → produces
    forecast_data: Optional[dict] = None
    transits: Optional[list] = None
    lunar_calendar: Optional[dict] = None
    natal_chart: Optional[dict] = None

    # GoalsAgent → produces
    active_goals: Optional[list] = None
    goal_windows: Optional[list] = None   # list of {goal_id, support, score, ...}

    # KnowledgeAgent → produces
    knowledge_base: Optional[dict] = None

    # SynthesisAgent → produces
    report_sections: Optional[dict] = None
    month_data: Optional[list] = None

    # EmpowermentAgent → produces
    power_items: Optional[dict] = None

    # OutputAgent → produces
    output_path: Optional[str] = None
    output_text: Optional[str] = None

    errors: list = field(default_factory=list)

    def has(self, key: str) -> bool:
        return getattr(self, key, None) is not None

    def add_error(self, agent: str, error: str) -> None:
        self.errors.append({
            "agent": agent,
            "error": error,
            "time": datetime.now().isoformat(),
        })
