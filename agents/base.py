from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.context import AgentContext


class BaseAgent:
    name: str = ""
    requires: List[str] = []   # що має бути в context до запуску
    produces: List[str] = []   # що додає в context після запуску

    def can_run(self, context: "AgentContext") -> bool:
        return all(context.has(k) for k in self.requires)

    def run(self, context: "AgentContext") -> "AgentContext":
        raise NotImplementedError(f"{self.__class__.__name__}.run() not implemented")


class AgentPlan:
    def __init__(self, intent: str, agents: List[str]):
        self.intent = intent
        self.agents = agents

    def __repr__(self) -> str:
        return f"AgentPlan(intent={self.intent!r}, agents={self.agents})"
