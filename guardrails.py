"""Output guardrails for the AI Hint Coach.

The coach must never reveal the secret number, must produce hints under a
hard length cap, and must keep tone game-relevant. These checks are pure
functions so they can be unit-tested without touching the LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

MAX_HINT_LENGTH = 250
MIN_HINT_LENGTH = 10


@dataclass
class GuardResult:
    ok: bool
    issues: list[str]
    cleaned: str


def _strip_formatting(text: str) -> str:
    """Remove code fences and HTML tags that an LLM might add."""
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = text.replace("```", "")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def contains_secret(hint: str, secret: int) -> bool:
    """True if the hint contains the secret as a standalone number.

    Uses a word-boundary regex so that secret=4 doesn't false-match '40'.
    Also catches the secret written with thousands separators in case the
    LLM adds them.
    """
    if not hint:
        return False
    cleaned = hint.replace(",", "")
    pattern = rf"(?<!\d){re.escape(str(secret))}(?!\d)"
    return re.search(pattern, cleaned) is not None


def check_hint(hint: str, secret: int, history_guesses: Iterable[int] = ()) -> GuardResult:
    """Validate a hint draft. Returns a GuardResult with cleaned text.

    Rules:
      1. Strip code fences / HTML.
      2. Length must be between MIN and MAX after stripping.
      3. Must not contain the secret number as a standalone token.
      4. Must not be empty / whitespace.

    `history_guesses` is accepted for future expansion (e.g., flagging hints
    that contradict previously revealed bounds) but is not enforced today.
    """
    issues: list[str] = []
    cleaned = _strip_formatting(hint or "")

    if not cleaned:
        return GuardResult(ok=False, issues=["empty_hint"], cleaned="")

    if len(cleaned) < MIN_HINT_LENGTH:
        issues.append(f"too_short:{len(cleaned)}")

    if len(cleaned) > MAX_HINT_LENGTH:
        cleaned = cleaned[:MAX_HINT_LENGTH].rsplit(" ", 1)[0] + "..."
        issues.append("truncated_to_max_length")

    if contains_secret(cleaned, secret):
        issues.append("secret_leak")

    fatal = {"empty_hint", "secret_leak"} | {i for i in issues if i.startswith("too_short")}
    is_ok = not (set(issues) & fatal)
    return GuardResult(ok=is_ok, issues=issues, cleaned=cleaned)


def deterministic_fallback_hint(
    live_low: int,
    live_high: int,
    attempts_left: int,
    secret: int | None = None,
) -> str:
    """Always-safe templated hint used when the agent cannot produce one.

    Never references the secret. When `secret` is provided and would appear
    in the numeric form of the hint (as midpoint or live bound), we fall
    back to a non-numeric description so the regex guard never trips.
    """
    if live_low > live_high:
        return "Something looks off with your guess history — try a fresh start."
    if live_low == live_high:
        # Player has deduced this themselves; naming it isn't new info.
        return f"You've narrowed it to one candidate. Guess {live_low}."

    mid = (live_low + live_high) // 2
    span = live_high - live_low + 1
    risky = secret is not None and secret in {mid, live_low, live_high}

    if risky:
        return (
            f"You've narrowed it to about {span} candidates and have "
            f"{attempts_left} attempts left. Aim for the middle of your live "
            f"range — each midpoint guess halves the remaining numbers."
        )

    return (
        f"Your live range is {live_low}-{live_high} ({attempts_left} attempts left). "
        f"The midpoint of that range is {mid} — that's the most informative guess."
    )


def compute_live_range(
    initial_low: int,
    initial_high: int,
    history: Iterable[tuple[int, str]],
) -> tuple[int, int]:
    """Return the current (low, high) live range from a history of (guess, outcome).

    `outcome` is "Too High", "Too Low", or "Win" — matching logic_utils.check_guess.
    """
    low, high = initial_low, initial_high
    for guess, outcome in history:
        if outcome == "Too Low" and guess + 1 > low:
            low = guess + 1
        elif outcome == "Too High" and guess - 1 < high:
            high = guess - 1
    return low, high
