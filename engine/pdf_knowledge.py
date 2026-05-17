"""
Extracts interpretive content from corrected HTML files in PDFs/.
Used to enrich the interpretation package with natal profile depth.
"""

import os
import re
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup

PDF_DIR = "PDFs"

# Maps filename → (topic_key, section_limit, chars_per_section)
FILE_TOPICS: Dict[str, Tuple[str, int, int]] = {
    "psychological-profile_CORRECTED.html":       ("psychological",   6, 400),
    "career-path-2026_CORRECTED.html":            ("career",          5, 350),
    "karmic-nodes_CORRECTED.html":                ("karmic",          5, 350),
    "saturn-jupiter-transits_CORRECTED.html":     ("saturn_jupiter",  5, 400),
    "grounding-guide_CORRECTED.html":             ("grounding",       4, 300),
    "Asto full-profile-summary_CORRECTED.html":   ("natal_summary",   4, 400),
    "session_summary_artur_2026_CORRECTED.html":  ("session_summary", 3, 300),
    "strategic_profile_2026.html":                ("strategic",       4, 350),
    "intuition_acceleration.html":                ("intuition",       3, 300),
    "intuition_capricorn.html":                   ("intuition_cap",   3, 300),
}


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


HEADING_CLASSES = (
    "sec-title", "h-title", "section-header", "mini-title",
    "card-title", "block-title", "topic-title", "ch-title",
)


def _extract_sections(path: str, max_sections: int, max_chars: int) -> List[dict]:
    """
    Parse one HTML file, split by heading elements, collect content under each.
    Tries standard h2/h3/h4 first; falls back to common custom heading classes.
    Returns list of {"title": ..., "content": ...}.
    """
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for tag in soup(["script", "style", "nav", "button", "footer"]):
        tag.decompose()

    # Decide which elements are "headings"
    standard_headings = soup.find_all(["h2", "h3", "h4"])
    if standard_headings:
        heading_names = {"h2", "h3", "h4"}
        is_heading = lambda el: el.name in heading_names
    else:
        # Fallback: treat elements with known heading CSS classes as headings
        is_heading = lambda el: bool(
            el.get("class") and any(c in HEADING_CLASSES for c in el.get("class", []))
        )

    sections: list[dict] = []
    current_title: str | None = None
    current_parts: list[str] = []

    def flush():
        if current_title and current_parts:
            body = " ".join(current_parts)[:max_chars]
            sections.append({"title": current_title, "content": body})

    for el in soup.find_all(["h2", "h3", "h4", "div", "p", "li", "td", "th"]):
        if len(sections) >= max_sections:
            break

        text = _clean(el.get_text())
        if not text or len(text) < 8:
            continue

        if is_heading(el):
            flush()
            current_title = text[:120]
            current_parts = []
        elif current_title and el.name in ("p", "li", "td"):
            if len(text) >= 20 and text != current_title:
                current_parts.append(text)

    flush()
    return sections


def load_knowledge_base(pdf_dir: str = PDF_DIR) -> dict:
    """
    Load all PDF HTML files and return structured knowledge base.
    Keys: topic name → {source, sections: [{title, content}]}.
    """
    knowledge: dict = {}

    for filename, (topic, sec_limit, char_limit) in FILE_TOPICS.items():
        path = os.path.join(pdf_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            sections = _extract_sections(path, sec_limit, char_limit)
            knowledge[topic] = {
                "source": filename,
                "sections": sections,
            }
        except Exception as exc:
            knowledge[topic] = {"source": filename, "error": str(exc), "sections": []}

    return knowledge


def get_compact_knowledge(pdf_dir: str = PDF_DIR) -> dict:
    """
    Compact version for the interpretation package.
    Each section trimmed to first 200 chars of content.
    """
    full = load_knowledge_base(pdf_dir)
    compact: dict = {}
    for topic, data in full.items():
        compact[topic] = {
            "source": data.get("source", ""),
            "sections": [
                {"title": s["title"], "content": s["content"][:200]}
                for s in data.get("sections", [])
            ],
        }
    return compact


def flat_text(topic_data: dict, max_chars: int = 800) -> str:
    """Flatten one topic's sections into a single string."""
    parts = []
    for s in topic_data.get("sections", []):
        parts.append(f"[{s['title']}] {s['content']}")
    return " | ".join(parts)[:max_chars]
