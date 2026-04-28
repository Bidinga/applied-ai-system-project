"""Plain-English narration of the AI Hint Coach's decisions.

Converts a `CoachResult` (dataclass with planner intent, retrieved chunks,
draft, critic verdict) into a friendly bullet list a non-developer can read.
The structured trace stays in `logs/coach.jsonl` for engineers; this module
is what we render in the UI.
"""

from __future__ import annotations

from typing import Any

# Player-friendly labels for the planner's `situation` and `strategy_focus`.
SITUATION_PHRASES = {
    "early": "you're just getting started",
    "mid": "you've made some progress narrowing the range",
    "near_win": "you're close — only a few candidates left",
    "stuck": "you're running low on attempts",
    "drifting": "your guesses are wandering across the range",
}

FOCUS_PHRASES = {
    "binary_search": "the binary-search strategy",
    "range_narrowing": "how to shrink the live range",
    "endgame": "endgame play",
    "persistence": "staying focused under pressure",
    "common_mistakes": "common mistakes players make",
}

# Friendly titles for the strategy doc filenames.
DOC_TITLES = {
    "binary_search.md": "Binary Search",
    "range_narrowing.md": "Range Narrowing",
    "information_theory.md": "Information Theory of Guessing",
    "common_mistakes.md": "Common Mistakes",
    "persistence_and_tilt.md": "Persistence & Tilt",
    "endgame.md": "Endgame Play",
}


def _get(step: Any, field: str) -> Any:
    """Read a field from a step that may be a dict (from to_dict) or a dataclass."""
    if isinstance(step, dict):
        return step.get(field)
    return getattr(step, field, None)


def _step_by_name(trace: list[Any], name: str) -> Any | None:
    for step in trace:
        if _get(step, "name") == name:
            return step
    return None


def _step_output(step: Any) -> Any:
    return _get(step, "output") if step is not None else None


def narrate(result_dict: dict) -> list[str]:
    """Return a list of friendly markdown lines describing the coach's process."""
    trace = result_dict.get("trace", [])
    used_fallback = result_dict.get("used_fallback", False)
    confidence = result_dict.get("confidence", 1.0)

    lines: list[str] = []

    planner = _step_by_name(trace, "planner")
    planner_out = _step_output(planner) or {}
    situation = planner_out.get("situation", "mid")
    focus = planner_out.get("strategy_focus", "binary_search")
    situation_phrase = SITUATION_PHRASES.get(situation, "you're playing")
    focus_phrase = FOCUS_PHRASES.get(focus, "your next move")
    lines.append(f"🔍 **What I noticed.** I looked at your guesses and saw that {situation_phrase}.")

    retriever = _step_by_name(trace, "retriever")
    retrieved = _step_output(retriever) or []
    if retrieved:
        titles = []
        for chunk in retrieved:
            source = chunk.get("source") if isinstance(chunk, dict) else getattr(chunk, "source", None)
            if source:
                titles.append(DOC_TITLES.get(source, source.replace("_", " ").replace(".md", "")))
        if titles:
            joined = " and ".join(f"_{t}_" for t in titles[:2])
            lines.append(f"📚 **What I read.** I pulled my notes on {focus_phrase} — specifically {joined}.")
        else:
            lines.append(f"📚 **What I read.** I pulled my notes on {focus_phrase}.")
    else:
        lines.append("📚 **What I read.** No specific notes were a strong match — going with general strategy.")

    critic = _step_by_name(trace, "critic")
    critic_out = _step_output(critic) or {}
    critic_passed = bool(critic_out.get("pass", True))

    retry = _step_by_name(trace, "generator_retry")
    if retry is not None:
        lines.append("🛠️ **What I caught.** My first draft was about to give away the answer — I rewrote it before showing you.")
    elif critic_passed and not used_fallback:
        lines.append("✅ **What I checked.** I re-read my hint with the answer in front of me to make sure I wasn't accidentally giving it away.")

    if used_fallback:
        lines.append("🛟 **Why this hint is generic.** I caught myself almost giving away the answer, even on the rewrite — so I switched to a safe, general nudge instead. You still get the right strategy, just without a specific number.")

    confidence_pct = int(round(confidence * 100))
    if confidence >= 0.95:
        confidence_phrase = f"💪 I'm very confident in this hint ({confidence_pct}%)."
    elif confidence >= 0.7:
        confidence_phrase = f"👍 I'm fairly confident in this hint ({confidence_pct}%)."
    elif confidence >= 0.4:
        confidence_phrase = f"🤔 I'm only somewhat confident in this hint ({confidence_pct}%) — take it with a grain of salt."
    else:
        confidence_phrase = f"⚠️ I'm not very confident in this hint ({confidence_pct}%) — you may want to think it through yourself."
    lines.append(confidence_phrase)

    return lines
