"""
Agent Communication Protocol
Defines: message schema, agent contracts, message bus (file-based).

Message flow:
  User → Coordinator → [Chart Parser, Forecast Agent] → Interpretation Agent (Claude)

All agent communication is logged to data/memory/messages.jsonl
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ── Message Types ────────────────────────────────────────────────────────────

class MsgType(str, Enum):
    TASK_REQUEST   = "TASK_REQUEST"    # Coordinator → Agent: run this task
    TASK_COMPLETE  = "TASK_COMPLETE"   # Agent → Coordinator: done, here's output
    TASK_ERROR     = "TASK_ERROR"      # Agent → Coordinator: failed, here's why
    HANDOFF        = "HANDOFF"         # Agent → Agent: passing output forward
    MEMORY_READ    = "MEMORY_READ"     # Agent: reading from shared memory
    MEMORY_WRITE   = "MEMORY_WRITE"    # Agent: writing to shared memory
    CONTEXT_UPDATE = "CONTEXT_UPDATE"  # User/Coordinator: update session context
    VALIDATION_REQ = "VALIDATION_REQ"  # Coordinator → User: validate this pattern


class AgentID(str, Enum):
    USER           = "user"
    COORDINATOR    = "coordinator"
    CHART_PARSER   = "chart_parser"      # Agent 1
    INTERPRETATION = "interpretation"    # Agent 2 (Claude)
    FORECAST       = "forecast"          # Agent 3


# ── Message Schema ───────────────────────────────────────────────────────────

def make_message(
    msg_type: MsgType,
    sender: AgentID,
    receiver: AgentID,
    payload: dict,
    correlation_id: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> dict:
    """Create a protocol-compliant message."""
    return {
        "id": str(uuid.uuid4())[:8],
        "correlation_id": correlation_id or str(uuid.uuid4())[:8],
        "parent_id": parent_id,
        "type": msg_type,
        "sender": sender,
        "receiver": receiver,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": payload,
        "status": "sent",
    }


def task_request(
    sender: AgentID,
    receiver: AgentID,
    task: str,
    params: dict,
    correlation_id: Optional[str] = None,
) -> dict:
    return make_message(
        MsgType.TASK_REQUEST, sender, receiver,
        payload={"task": task, "params": params},
        correlation_id=correlation_id,
    )


def task_complete(
    sender: AgentID,
    receiver: AgentID,
    task: str,
    result_path: str,
    summary: dict,
    parent_msg: dict,
) -> dict:
    return make_message(
        MsgType.TASK_COMPLETE, sender, receiver,
        payload={"task": task, "result_path": result_path, "summary": summary},
        correlation_id=parent_msg["correlation_id"],
        parent_id=parent_msg["id"],
    )


def task_error(
    sender: AgentID,
    receiver: AgentID,
    task: str,
    error: str,
    parent_msg: dict,
) -> dict:
    return make_message(
        MsgType.TASK_ERROR, sender, receiver,
        payload={"task": task, "error": error},
        correlation_id=parent_msg["correlation_id"],
        parent_id=parent_msg["id"],
    )


def handoff(
    sender: AgentID,
    receiver: AgentID,
    data_path: str,
    context: dict,
    parent_msg: dict,
) -> dict:
    return make_message(
        MsgType.HANDOFF, sender, receiver,
        payload={"data_path": data_path, "context": context},
        correlation_id=parent_msg["correlation_id"],
        parent_id=parent_msg["id"],
    )


def memory_write(
    sender: AgentID,
    path: str,
    keys_written: list,
    reason: str,
) -> dict:
    return make_message(
        MsgType.MEMORY_WRITE, sender, AgentID.COORDINATOR,
        payload={"path": path, "keys_written": keys_written, "reason": reason},
    )


# ── Agent Contracts ──────────────────────────────────────────────────────────

AGENT_CONTRACTS = {
    AgentID.CHART_PARSER: {
        "description": "Computes natal chart from birth data using Swiss Ephemeris",
        "reads_from": ["data/birth_data.json"],
        "writes_to": ["output/data/natal_chart.json"],
        "input_required": ["birth_date", "birth_time", "latitude", "longitude", "timezone"],
        "output_guarantees": [
            "planets (SE/Moshier geocentric ecliptic)",
            "angles (ASC, MC via swe.houses Whole Sign)",
            "aspects (top by orb, classical + outer)",
            "stelliums, angular_planets, dominants, dispositors",
        ],
        "cache_policy": "permanent — natal chart never changes",
    },
    AgentID.FORECAST: {
        "description": "Computes monthly transits, solar return, critical windows",
        "reads_from": ["data/birth_data.json", "data/memory/natal_patterns.json"],
        "writes_to": ["output/data/YYYY-MM-forecast.json"],
        "input_required": ["natal_planets", "year", "month"],
        "output_guarantees": [
            "transits (all planets incl. Pluto/Neptune/Uranus)",
            "solar_return (SE binary search, location-aware)",
            "critical_windows (outer planets to angles/luminaries only)",
        ],
        "cache_policy": "per period — recompute with --force",
    },
    AgentID.INTERPRETATION: {
        "description": "Claude Code — synthesizes natal + forecast + memory into analysis",
        "reads_from": [
            "output/data/YYYY-MM-interpret.json",
            "ASTRO_PROMPT.md",
        ],
        "writes_to": ["data/memory/sessions/YYYY-MM/interpretation.json"],
        "input_required": [
            "identity layer",
            "activated_patterns",
            "active_cycles",
            "forecast",
        ],
        "output_guarantees": [
            "Ukrainian language",
            "follows ASTRO_PROMPT.md format",
            "references identity patterns, not raw aspects",
            "includes timing recommendations",
        ],
        "cache_policy": "never — each interpretation is unique",
    },
    AgentID.COORDINATOR: {
        "description": "Orchestrates agents, manages memory, resolves contradictions",
        "reads_from": ["data/memory/*"],
        "writes_to": [
            "data/memory/coordinator.json",
            "data/memory/cycles.json (via update)",
            "data/memory/predictions.json",
        ],
        "responsibilities": [
            "decide which agents need to run",
            "trim context before passing to Agent 2",
            "log all agent messages",
            "resolve contradictions in natal_patterns.json",
            "update memory health scores",
        ],
    },
}


# ── Memory Write Permissions ─────────────────────────────────────────────────

MEMORY_PERMISSIONS = {
    "data/memory/user.json":           [AgentID.COORDINATOR],
    "data/memory/identity.json":       [AgentID.COORDINATOR, AgentID.INTERPRETATION],
    "data/memory/natal_patterns.json": [AgentID.COORDINATOR, AgentID.INTERPRETATION],
    "data/memory/cycles.json":         [AgentID.COORDINATOR],
    "data/memory/predictions.json":    [AgentID.COORDINATOR],
    "data/memory/coordinator.json":    [AgentID.COORDINATOR],
    "output/data/natal_chart.json":    [AgentID.CHART_PARSER],
    "output/data/*-forecast.json":     [AgentID.FORECAST],
    "output/data/*-interpret.json":    [AgentID.COORDINATOR],
}


def check_permission(agent: AgentID, path: str) -> bool:
    """Check if agent is allowed to write to path."""
    import fnmatch
    for pattern, allowed in MEMORY_PERMISSIONS.items():
        if fnmatch.fnmatch(path, pattern):
            return agent in allowed
    return False  # deny by default


# ── Message Bus (file-based) ─────────────────────────────────────────────────

MESSAGE_LOG = "data/memory/messages.jsonl"


def send(msg: dict) -> dict:
    """Log message to bus and return it."""
    import os
    os.makedirs(os.path.dirname(MESSAGE_LOG), exist_ok=True)
    with open(MESSAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    return msg


def get_thread(correlation_id: str) -> list:
    """Return all messages in a correlation thread."""
    if not __import__("os").path.exists(MESSAGE_LOG):
        return []
    thread = []
    with open(MESSAGE_LOG, encoding="utf-8") as f:
        for line in f:
            msg = json.loads(line)
            if msg.get("correlation_id") == correlation_id:
                thread.append(msg)
    return sorted(thread, key=lambda m: m["timestamp"])


def get_recent(limit: int = 20) -> list:
    """Return last N messages from log."""
    if not __import__("os").path.exists(MESSAGE_LOG):
        return []
    with open(MESSAGE_LOG, encoding="utf-8") as f:
        lines = f.readlines()
    return [json.loads(l) for l in lines[-limit:]]


def get_errors() -> list:
    """Return all error messages."""
    if not __import__("os").path.exists(MESSAGE_LOG):
        return []
    errors = []
    with open(MESSAGE_LOG, encoding="utf-8") as f:
        for line in f:
            msg = json.loads(line)
            if msg.get("type") == MsgType.TASK_ERROR:
                errors.append(msg)
    return errors
