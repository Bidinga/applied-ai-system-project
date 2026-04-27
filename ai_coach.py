"""AI Hint Coach — agentic workflow that produces a coaching hint.

The agent runs four sequential steps:

    [1] Planner   (LLM)      classifies the situation and crafts a RAG query
    [2] Retriever (TF-IDF)   fetches the most relevant strategy chunks
    [3] Generator (LLM)      drafts a 1-2 sentence hint grounded in those chunks
    [4] Critic    (LLM + guardrails) checks for secret leaks and tone

If the critic fails, the generator is rerun once with the critic's issues
appended to its prompt. If it fails again, a deterministic fallback hint is
returned. Either way, the player always gets a safe hint.

Mock mode (no API key, or MOCK_MODE=true) substitutes canned responses so
the system stays demoable and the eval harness still runs.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

from guardrails import (
    GuardResult,
    check_hint,
    compute_live_range,
    deterministic_fallback_hint,
)
from logger import TimedStep, is_mock_mode, log_event
from retriever import Chunk, get_index

PLANNER_MODEL_DEFAULT = "claude-haiku-4-5-20251001"
GENERATOR_MODEL_DEFAULT = "claude-sonnet-4-6"
CRITIC_MODEL_DEFAULT = "claude-haiku-4-5-20251001"


@dataclass
class GameState:
    secret: int
    initial_low: int
    initial_high: int
    history: list[tuple[int, str]]
    attempts_left: int


@dataclass
class TraceStep:
    name: str
    output: Any
    used_mock: bool = False
    issues: list[str] = field(default_factory=list)


@dataclass
class CoachResult:
    hint: str
    used_fallback: bool
    trace: list[TraceStep]
    guard_issues: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "hint": self.hint,
            "used_fallback": self.used_fallback,
            "guard_issues": self.guard_issues,
            "confidence": self.confidence,
            "trace": [
                {
                    "name": step.name,
                    "used_mock": step.used_mock,
                    "issues": step.issues,
                    "output": step.output,
                }
                for step in self.trace
            ],
        }


@lru_cache(maxsize=1)
def _client():
    """Return an Anthropic client, or None if running in mock mode.

    Imported lazily so the system runs without `anthropic` installed when
    MOCK_MODE is on. The client is cached for reuse across calls.
    """
    if is_mock_mode():
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        log_event(
            "client_init",
            error="anthropic_not_installed",
            note="falling back to mock mode",
        )
        return None
    return Anthropic()


def _planner_model() -> str:
    return os.environ.get("COACH_PLANNER_MODEL", PLANNER_MODEL_DEFAULT)


def _generator_model() -> str:
    return os.environ.get("COACH_GENERATOR_MODEL", GENERATOR_MODEL_DEFAULT)


def _critic_model() -> str:
    return os.environ.get("COACH_CRITIC_MODEL", CRITIC_MODEL_DEFAULT)


def _call_llm(model: str, system: str, user: str, max_tokens: int = 400) -> str:
    """Single point of contact with the Anthropic SDK. Raises on failure."""
    client = _client()
    if client is None:
        raise RuntimeError("LLM call attempted in mock mode")
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in msg.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _extract_json(text: str) -> dict | None:
    """Extract the first JSON object from an LLM response, tolerating fences."""
    if not text:
        return None
    cleaned = re.sub(r"```[a-zA-Z]*\n?", "", text).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _classify_for_mock(state: GameState) -> dict:
    """Cheap deterministic classifier used by mock mode and as a fallback."""
    low, high = compute_live_range(state.initial_low, state.initial_high, state.history)
    span = max(high - low + 1, 1)
    n_guesses = len(state.history)

    if span <= 4:
        situation = "near_win"
        focus = "endgame"
        query = "endgame few candidates left forced move close"
    elif n_guesses == 0:
        situation = "early"
        focus = "binary_search"
        query = "binary search midpoint optimal first move"
    elif n_guesses >= 4 and span > (state.initial_high - state.initial_low) * 0.4:
        situation = "drifting"
        focus = "common_mistakes"
        query = "anchoring drifting wandering ignoring feedback"
    elif state.attempts_left <= 2:
        situation = "stuck"
        focus = "persistence"
        query = "persistence tilt focus stay calm midpoint"
    else:
        situation = "mid"
        focus = "range_narrowing"
        query = "narrowing live range midpoint shrink window"

    return {"situation": situation, "strategy_focus": focus, "query": query}


def _planner(state: GameState) -> tuple[dict, bool]:
    """Step 1 — return (intent_dict, used_mock)."""
    if is_mock_mode():
        intent = _classify_for_mock(state)
        log_event("planner", used_mock=True, intent=intent)
        return intent, True

    system = (
        "You analyze players of a number-guessing game and decide what kind "
        "of coaching they need. Respond with strict JSON only — no prose."
    )
    user = (
        f"Player game state:\n"
        f"  initial_range: {state.initial_low}-{state.initial_high}\n"
        f"  attempts_left: {state.attempts_left}\n"
        f"  history (guess, outcome): {state.history}\n\n"
        f"Output JSON with keys:\n"
        f'  situation: one of "early", "mid", "near_win", "stuck", "drifting"\n'
        f'  strategy_focus: one of "binary_search", "range_narrowing", '
        f'"endgame", "persistence", "common_mistakes"\n'
        f"  query: 8-15 keyword string for retrieving coaching notes (no quotes)\n"
    )

    with TimedStep("planner", model=_planner_model()) as step:
        try:
            raw = _call_llm(_planner_model(), system, user, max_tokens=200)
            parsed = _extract_json(raw)
            if not parsed or "query" not in parsed:
                raise ValueError("planner_invalid_json")
            step.add(intent=parsed)
            return parsed, False
        except Exception as e:
            step.add(error=str(e), used_fallback=True)
            return _classify_for_mock(state), True


def _retrieve(query: str) -> list[Chunk]:
    with TimedStep("retriever", query=query) as step:
        chunks = get_index().retrieve(query, k=2)
        step.add(retrieved=[c.source for c in chunks])
        return chunks


def _format_chunks(chunks: list[Chunk]) -> str:
    if not chunks:
        return "(no notes retrieved)"
    return "\n\n".join(f"## {c.title}\n{c.text.strip()}" for c in chunks)


def _mock_generate(state: GameState, intent: dict, chunks: list[Chunk]) -> str:
    """Canned generator used by mock mode. Always uses the live midpoint."""
    low, high = compute_live_range(state.initial_low, state.initial_high, state.history)
    if low > high:
        return "Your guess history looks contradictory — start a fresh game."
    if low == high:
        return f"You've narrowed it to a single candidate. Guess {low}."
    mid = (low + high) // 2
    span = high - low + 1
    focus = intent.get("strategy_focus", "binary_search")
    if focus == "endgame":
        return (
            f"You're in the endgame — only {span} candidates left in {low}-{high}. "
            f"Try {mid}; whatever the answer, you'll be one step from done."
        )
    if focus == "common_mistakes":
        return (
            f"You're drifting inside {low}-{high}. Anchor on the midpoint: try {mid}, "
            f"then halve again based on the feedback."
        )
    if focus == "persistence":
        return (
            f"Stay calm — {span} candidates left in {low}-{high}. "
            f"Guess the midpoint {mid}; that's the move with the most information."
        )
    if focus == "range_narrowing":
        return (
            f"Your live range is {low}-{high}. The midpoint {mid} eliminates "
            f"the most candidates regardless of the answer."
        )
    return (
        f"Best opening for {low}-{high} is the midpoint {mid}. "
        f"Each midpoint guess halves the remaining range."
    )


def _generator(
    state: GameState,
    intent: dict,
    chunks: list[Chunk],
    extra_critique: str = "",
) -> tuple[str, bool]:
    if is_mock_mode():
        draft = _mock_generate(state, intent, chunks)
        log_event("generator", used_mock=True, draft=draft)
        return draft, True

    low, high = compute_live_range(state.initial_low, state.initial_high, state.history)
    notes = _format_chunks(chunks)

    system = (
        "You are an encouraging coach for a number-guessing game. Write 1-2 "
        "sentences, max 250 characters. NEVER reveal the secret number. Be "
        "specific about the player's live range and recommend a concrete next "
        "guess (typically the midpoint of the live range). Do not quote the "
        "strategy notes verbatim — use them as inspiration."
    )
    user = (
        f"Game state:\n"
        f"  initial_range: {state.initial_low}-{state.initial_high}\n"
        f"  live_range: {low}-{high}\n"
        f"  attempts_left: {state.attempts_left}\n"
        f"  history: {state.history}\n"
        f"  situation: {intent.get('situation')}\n\n"
        f"Strategy notes:\n{notes}\n\n"
        f"{extra_critique}\n"
        f"Write the hint now."
    )

    with TimedStep("generator", model=_generator_model()) as step:
        try:
            draft = _call_llm(_generator_model(), system, user, max_tokens=300)
            step.add(draft=draft)
            return draft, False
        except Exception as e:
            step.add(error=str(e), used_fallback=True)
            return _mock_generate(state, intent, chunks), True


def _confidence_from_issues(issues: list[str]) -> float:
    """Map a list of guardrail issue tags to a confidence score in [0, 1].

    Used in mock mode and as a fallback when the LLM critic forgets to
    include `confidence` in its JSON. Fatal issues drive confidence near 0;
    cosmetic issues only slightly reduce it.
    """
    if not issues:
        return 1.0
    fatal = {"empty_hint", "secret_leak"}
    if any(i in fatal or i.startswith("too_short") for i in issues):
        return 0.05
    if "truncated_to_max_length" in issues:
        return 0.85
    return 0.7


def _critic(draft: str, state: GameState) -> tuple[dict, bool]:
    """Step 4 — LLM self-critique on top of regex guardrails.

    Always runs the deterministic guardrails first; the LLM critic only adds
    judgment about tone/relevance. Returns a verdict dict that always contains
    a `confidence` float in [0, 1] so the eval harness can aggregate it.
    """
    guard = check_hint(draft, state.secret)
    if not guard.ok:
        verdict = {
            "pass": False,
            "issues": guard.issues,
            "confidence": _confidence_from_issues(guard.issues),
            "source": "guardrail",
        }
        log_event("guardrail", **verdict)
        return verdict, False

    if is_mock_mode():
        verdict = {
            "pass": True,
            "issues": guard.issues,
            "confidence": _confidence_from_issues(guard.issues),
            "source": "guardrail",
        }
        log_event("critic", used_mock=True, **verdict)
        return verdict, True

    low, high = compute_live_range(state.initial_low, state.initial_high, state.history)
    system = (
        "You review hints written for a number-guessing game coach. The hint "
        "must (a) not reveal the secret, (b) be encouraging, (c) stay focused "
        "on the game and the player's live range. Respond with strict JSON only."
    )
    user = (
        f"Hint draft: {draft!r}\n"
        f"Secret (do not echo): {state.secret}\n"
        f"Live range: {low}-{high}\n\n"
        f'Output JSON: {{"pass": true|false, "issues": ["..."], '
        f'"confidence": <float 0..1>}}'
    )

    with TimedStep("critic", model=_critic_model()) as step:
        try:
            raw = _call_llm(_critic_model(), system, user, max_tokens=200)
            parsed = _extract_json(raw) or {"pass": True, "issues": []}
            if "confidence" not in parsed:
                parsed["confidence"] = _confidence_from_issues(parsed.get("issues", []))
            try:
                parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
            except (TypeError, ValueError):
                parsed["confidence"] = _confidence_from_issues(parsed.get("issues", []))
            parsed["source"] = "llm"
            step.add(verdict=parsed)
            return parsed, False
        except Exception as e:
            step.add(error=str(e))
            return {
                "pass": True,
                "issues": [],
                "confidence": 0.5,
                "source": "llm_error",
            }, False


def _validate_state(state: GameState) -> None:
    if state.initial_low >= state.initial_high:
        raise ValueError("initial_low must be < initial_high")
    if not (state.initial_low <= state.secret <= state.initial_high):
        raise ValueError("secret outside initial range")
    if len(state.history) > 10:
        state.history[:] = state.history[-10:]


def get_hint(state: GameState) -> CoachResult:
    """Run the four-step agent loop and return a CoachResult."""
    _validate_state(state)
    trace: list[TraceStep] = []

    intent, planner_mocked = _planner(state)
    trace.append(TraceStep(name="planner", output=intent, used_mock=planner_mocked))

    chunks = _retrieve(intent.get("query", ""))
    trace.append(
        TraceStep(
            name="retriever",
            output=[{"title": c.title, "source": c.source} for c in chunks],
            used_mock=False,
        )
    )

    draft, gen_mocked = _generator(state, intent, chunks)
    trace.append(TraceStep(name="generator", output=draft, used_mock=gen_mocked))

    verdict, critic_mocked = _critic(draft, state)
    trace.append(
        TraceStep(
            name="critic",
            output=verdict,
            used_mock=critic_mocked,
            issues=list(verdict.get("issues", [])),
        )
    )

    if verdict.get("pass"):
        guard = check_hint(draft, state.secret)
        log_event("coach_done", path="primary", hint=guard.cleaned)
        return CoachResult(
            hint=guard.cleaned,
            used_fallback=False,
            trace=trace,
            guard_issues=guard.issues,
            confidence=float(verdict.get("confidence", 1.0)),
        )

    extra = (
        f"PREVIOUS DRAFT FAILED REVIEW. Issues: {verdict.get('issues')}. "
        f"Rewrite the hint avoiding these issues. Never include the digits {state.secret}."
    )
    draft2, gen2_mocked = _generator(state, intent, chunks, extra_critique=extra)
    trace.append(TraceStep(name="generator_retry", output=draft2, used_mock=gen2_mocked))

    verdict2, critic2_mocked = _critic(draft2, state)
    trace.append(
        TraceStep(
            name="critic_retry",
            output=verdict2,
            used_mock=critic2_mocked,
            issues=list(verdict2.get("issues", [])),
        )
    )

    if verdict2.get("pass"):
        guard = check_hint(draft2, state.secret)
        log_event("coach_done", path="retry", hint=guard.cleaned)
        return CoachResult(
            hint=guard.cleaned,
            used_fallback=False,
            trace=trace,
            guard_issues=guard.issues,
            confidence=float(verdict2.get("confidence", 0.8)),
        )

    low, high = compute_live_range(state.initial_low, state.initial_high, state.history)
    fallback = deterministic_fallback_hint(low, high, state.attempts_left, secret=state.secret)
    fallback_guard = check_hint(fallback, state.secret)
    if not fallback_guard.ok:
        log_event("fallback_unsafe", issues=fallback_guard.issues, hint=fallback)
        fallback = (
            "Aim for the middle of your live range. Each midpoint guess "
            "halves the remaining candidates."
        )
    log_event("fallback", reason=verdict2.get("issues"), hint=fallback)
    trace.append(
        TraceStep(name="fallback", output=fallback, used_mock=True, issues=["used_fallback"])
    )
    # Fallback hints are deterministic and known-safe but generic — moderate confidence.
    return CoachResult(hint=fallback, used_fallback=True, trace=trace, confidence=0.6)
