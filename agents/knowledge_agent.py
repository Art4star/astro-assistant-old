from __future__ import annotations
import os

from agents.base import BaseAgent
from agents.context import AgentContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "PDFs")


class KnowledgeAgent(BaseAgent):
    """
    Завантажує базу знань із PDF-файлів натальних профілів.
    Результат кешується всередині get_compact_knowledge.
    """
    name = "knowledge"
    requires = ["birth_data"]
    produces = ["knowledge_base"]

    def run(self, context: AgentContext) -> AgentContext:
        from engine.pdf_knowledge import get_compact_knowledge
        context.knowledge_base = get_compact_knowledge(pdf_dir=PDF_DIR)
        return context
