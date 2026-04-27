"""Structured JSON-line logging for AI Hint Coach.

Every LLM call (planner, generator, critic) and every guardrail decision is
appended to logs/coach.jsonl so failures can be inspected after the fact.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "coach.jsonl"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_event(step: str, **fields: Any) -> None:
    """Append a single JSON record to logs/coach.jsonl.

    `step` is a short tag (e.g. 'planner', 'retriever', 'generator',
    'critic', 'guardrail', 'fallback'). All other fields are included verbatim.
    Never raises on logging errors — logging must not break the user-facing
    request path.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": step,
        **fields,
    }
    try:
        _ensure_log_dir()
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


class TimedStep:
    """Context manager that logs latency_ms and any exception for a step."""

    def __init__(self, step: str, **fields: Any) -> None:
        self.step = step
        self.fields = fields
        self.start: float = 0.0

    def __enter__(self) -> "TimedStep":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        latency_ms = int((time.perf_counter() - self.start) * 1000)
        if exc is None:
            log_event(self.step, latency_ms=latency_ms, **self.fields)
        else:
            log_event(
                self.step,
                latency_ms=latency_ms,
                error=str(exc),
                error_type=exc_type.__name__ if exc_type else "Unknown",
                **self.fields,
            )

    def add(self, **fields: Any) -> None:
        """Attach more fields to be logged when the context exits."""
        self.fields.update(fields)


def is_mock_mode() -> bool:
    """True if the system should use canned responses instead of real LLM calls."""
    if os.environ.get("MOCK_MODE", "").strip().lower() in {"1", "true", "yes"}:
        return True
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return True
    return False
