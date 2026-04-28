"""Themed game modes.

A theme is a short prompt + a numeric secret + a range bracket + an
explanation that's revealed at the end of the game. Themes turn the bare
"guess 1-100" exercise into "guess the year humans landed on the moon"
or "guess the population of Iceland in thousands" — the game becomes a
small piece of trivia that's actually fun to play.

Themes ship as a hand-curated list of facts (so the game is reproducible
and works without an API key). When live mode is on, the AI can also
generate fresh themes on demand via `generate_theme()`.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Optional

from logger import TimedStep, is_mock_mode, log_event


@dataclass
class Theme:
    """A single themed game.

    Attributes:
        name: short label (e.g. "Year humans walked on the moon")
        prompt: question shown to the player ("Guess the year ...")
        explanation: revealed after the game ends — gives the player the fact
        category: one of {"history", "geography", "science", "culture", "math", "classic"}
        secret: the answer (numeric)
        initial_low / initial_high: range hint shown to the player
    """

    name: str
    prompt: str
    explanation: str
    category: str
    secret: int
    initial_low: int
    initial_high: int


CLASSIC_THEME = Theme(
    name="Classic",
    prompt="Guess the secret number.",
    explanation="No theme — pure number-guessing.",
    category="classic",
    secret=0,  # placeholder; classic mode uses random.randint at game start
    initial_low=1,
    initial_high=100,
)


# Hand-curated themed games. Each one is reproducible without an API key.
# Ranges are deliberately generous so binary search is interesting.
CURATED_THEMES: list[Theme] = [
    Theme(
        name="Moon landing",
        prompt="Guess the year humans first walked on the Moon.",
        explanation="Apollo 11. Neil Armstrong stepped onto the lunar surface on July 20, 1969.",
        category="history",
        secret=1969,
        initial_low=1900,
        initial_high=2000,
    ),
    Theme(
        name="Berlin Wall fall",
        prompt="Guess the year the Berlin Wall fell.",
        explanation="The Berlin Wall fell on November 9, 1989, after 28 years dividing the city.",
        category="history",
        secret=1989,
        initial_low=1950,
        initial_high=2010,
    ),
    Theme(
        name="World Wide Web",
        prompt="Guess the year the World Wide Web was first proposed by Tim Berners-Lee.",
        explanation="Tim Berners-Lee submitted his proposal at CERN in 1989 — the same year the Berlin Wall fell.",
        category="science",
        secret=1989,
        initial_low=1960,
        initial_high=2010,
    ),
    Theme(
        name="Iceland population",
        prompt="Guess the population of Iceland (in thousands, 2024).",
        explanation="Iceland had about 384,000 people in 2024 — one of the smallest national populations in Europe.",
        category="geography",
        secret=384,
        initial_low=100,
        initial_high=900,
    ),
    Theme(
        name="Mount Everest height",
        prompt="Guess the height of Mount Everest in meters.",
        explanation="Everest's official height is 8,849 meters (29,032 ft), revised in 2020.",
        category="geography",
        secret=8849,
        initial_low=7000,
        initial_high=10000,
    ),
    Theme(
        name="Speed of light",
        prompt="Guess the speed of light in km per second (rounded to the nearest thousand).",
        explanation="The speed of light is exactly 299,792 km/s — rounded that's 300,000 km/s.",
        category="science",
        secret=300000,
        initial_low=100000,
        initial_high=500000,
    ),
    Theme(
        name="Boiling point",
        prompt="Guess the boiling point of water in degrees Fahrenheit.",
        explanation="Water boils at 212°F (100°C) at standard atmospheric pressure.",
        category="science",
        secret=212,
        initial_low=100,
        initial_high=400,
    ),
    Theme(
        name="Roman Colosseum",
        prompt="Guess the year the Roman Colosseum was completed (CE).",
        explanation="The Colosseum was completed in 80 CE under Emperor Titus, with games lasting 100 days.",
        category="history",
        secret=80,
        initial_low=1,
        initial_high=300,
    ),
    Theme(
        name="Tokyo population",
        prompt="Guess the population of greater Tokyo (in millions, 2024).",
        explanation="Greater Tokyo (the metropolitan area) has about 37 million people — the most populous urban area on Earth.",
        category="geography",
        secret=37,
        initial_low=10,
        initial_high=60,
    ),
    Theme(
        name="Mona Lisa",
        prompt="Guess the year Leonardo da Vinci began painting the Mona Lisa.",
        explanation="Leonardo started the Mona Lisa around 1503 and is thought to have worked on it for 16 years.",
        category="culture",
        secret=1503,
        initial_low=1400,
        initial_high=1600,
    ),
    Theme(
        name="Pi to 4 digits",
        prompt="Guess the first 4 digits of pi (as an integer, e.g. 3141).",
        explanation="π ≈ 3.14159... so the first four digits are 3141.",
        category="math",
        secret=3141,
        initial_low=3000,
        initial_high=4000,
    ),
    Theme(
        name="Eiffel Tower height",
        prompt="Guess the height of the Eiffel Tower in meters (including antenna).",
        explanation="The Eiffel Tower is 330 meters tall including its broadcast antenna; 300 m to the tip of the original structure.",
        category="geography",
        secret=330,
        initial_low=100,
        initial_high=600,
    ),
]


def list_themes() -> list[Theme]:
    """All themes available in the UI selector — Classic plus curated."""
    return [CLASSIC_THEME] + CURATED_THEMES


def themes_by_name() -> dict[str, Theme]:
    return {t.name: t for t in list_themes()}


def random_curated_theme(rng: Optional[random.Random] = None) -> Theme:
    """Return a random curated theme (excluding Classic)."""
    rng = rng or random.Random()
    return rng.choice(CURATED_THEMES)


def make_classic_theme(low: int, high: int, rng: Optional[random.Random] = None) -> Theme:
    """Realize a classic-mode theme with a freshly-drawn secret in [low, high]."""
    rng = rng or random.Random()
    return Theme(
        name="Classic",
        prompt=f"Guess the secret number between {low} and {high}.",
        explanation=f"The secret was a random integer drawn uniformly from {low}–{high}.",
        category="classic",
        secret=rng.randint(low, high),
        initial_low=low,
        initial_high=high,
    )


# ---------------------------------------------------------------------------
# Optional: live AI-generated themes (only used when MOCK_MODE is off)
# ---------------------------------------------------------------------------


def _parse_generated_theme(raw: str) -> Theme | None:
    """Extract a Theme from an LLM JSON response."""
    if not raw:
        return None
    cleaned = re.sub(r"```[a-zA-Z]*\n?", "", raw).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return Theme(
            name=str(data["name"])[:60],
            prompt=str(data["prompt"])[:200],
            explanation=str(data["explanation"])[:400],
            category=str(data.get("category", "trivia"))[:30],
            secret=int(data["secret"]),
            initial_low=int(data["initial_low"]),
            initial_high=int(data["initial_high"]),
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def generate_theme(category: str | None = None) -> Theme:
    """Ask the LLM for a fresh theme. In mock mode, return a curated one.

    Themes generated live are validated: secret must lie in [initial_low,
    initial_high]. If validation fails, falls back to a curated theme.
    """
    if is_mock_mode():
        return random_curated_theme()

    from ai_coach import _call_llm, _generator_model  # lazy import to avoid cycles

    cat_clause = f"Category: {category}." if category else "Pick any category you like (history, science, geography, culture, math)."
    system = (
        "You design themed number-guessing trivia. Output strict JSON only with "
        "keys: name, prompt, explanation, category, secret, initial_low, initial_high. "
        "The secret MUST be an integer that is verifiably correct and MUST lie strictly "
        "between initial_low and initial_high. Range should be wide enough that a binary "
        "search takes 5-7 guesses. The explanation reveals the fact after the game."
    )
    user = (
        f"{cat_clause} Output a single JSON theme — no prose, no markdown fences."
    )

    with TimedStep("theme_generation") as step:
        try:
            raw = _call_llm(_generator_model(), system, user, max_tokens=400)
            theme = _parse_generated_theme(raw)
            if theme is None:
                step.add(error="parse_failed", used_fallback=True)
                return random_curated_theme()
            if not (theme.initial_low <= theme.secret <= theme.initial_high):
                step.add(error="secret_out_of_range", theme=theme.name)
                return random_curated_theme()
            step.add(theme=theme.name, category=theme.category)
            return theme
        except Exception as e:
            step.add(error=str(e), used_fallback=True)
            log_event("theme_generation_error", error=str(e))
            return random_curated_theme()
