from __future__ import annotations
import importlib

from agents.base import AgentPlan
from agents.context import AgentContext

_REGISTRY: dict = {
    "forecast":     ("agents.forecast_agent",     "ForecastAgent"),
    "goals":        ("agents.goals_agent",         "GoalsAgent"),
    "knowledge":    ("agents.knowledge_agent",     "KnowledgeAgent"),
    "synthesis":    ("agents.synthesis_agent",     "SynthesisAgent"),
    "empowerment":  ("agents.empowerment_agent",   "EmpowermentAgent"),
    "output":       ("agents.output_agent",        "OutputAgent"),
}


class Executor:
    """
    Запускає агентів у порядку визначеному планом.
    Якщо агент впав — логує помилку і продовжує (graceful degradation).
    Якщо агенту не вистачає prerequisites — пропускає його.
    """

    def _load(self, name: str) -> "BaseAgent":
        if name not in _REGISTRY:
            raise ValueError(f"Невідомий агент: {name!r}. Доступні: {list(_REGISTRY)}")
        module_path, class_name = _REGISTRY[name]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()

    def run(self, plan: AgentPlan, context: AgentContext) -> AgentContext:
        print(f"[Executor] intent={plan.intent!r}  pipeline={plan.agents}")
        for agent_name in plan.agents:
            agent = self._load(agent_name)

            if not agent.can_run(context):
                msg = f"не вистачає: {[k for k in agent.requires if not context.has(k)]}"
                print(f"  [{agent_name}] SKIP — {msg}")
                context.add_error(agent_name, f"SKIP: {msg}")
                continue

            print(f"  [{agent_name}] ...")
            try:
                context = agent.run(context)
                print(f"  [{agent_name}] OK → {agent.produces}")
            except Exception as exc:
                context.add_error(agent_name, str(exc))
                print(f"  [{agent_name}] ERROR: {exc}")

        if context.errors:
            errs = [e for e in context.errors if not e["error"].startswith("SKIP")]
            if errs:
                print(f"[Executor] завершено з {len(errs)} помилками")
        return context
