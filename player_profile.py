"""Persistent player profile + playstyle classification.

State is stored as JSON at `data/player_profile.json` (gitignored). Every
finished game appends a `GameSummary` and updates aggregate stats so the
sidebar and post-game review can reference the player's history.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_DIR = Path(__file__).parent / "data"
PROFILE_FILE = PROFILE_DIR / "player_profile.json"

MAX_HISTORY = 25


@dataclass
class GameSummary:
    timestamp: str
    difficulty: str
    theme: str
    won: bool
    attempts: int
    score: int
    secret: int
    initial_low: int
    initial_high: int
    history: list[tuple[int, str]]
    playstyle: str

    @classmethod
    def from_dict(cls, d: dict) -> "GameSummary":
        return cls(
            timestamp=d.get("timestamp", ""),
            difficulty=d.get("difficulty", ""),
            theme=d.get("theme", "Classic"),
            won=bool(d.get("won", False)),
            attempts=int(d.get("attempts", 0)),
            score=int(d.get("score", 0)),
            secret=int(d.get("secret", 0)),
            initial_low=int(d.get("initial_low", 1)),
            initial_high=int(d.get("initial_high", 100)),
            history=[tuple(h) for h in d.get("history", [])],
            playstyle=d.get("playstyle", "unknown"),
        )


@dataclass
class PlayerProfile:
    games: list[GameSummary] = field(default_factory=list)

    @property
    def games_played(self) -> int:
        return len(self.games)

    @property
    def games_won(self) -> int:
        return sum(1 for g in self.games if g.won)

    @property
    def games_lost(self) -> int:
        return self.games_played - self.games_won

    @property
    def win_rate(self) -> float:
        if not self.games:
            return 0.0
        return self.games_won / self.games_played

    @property
    def avg_attempts_to_win(self) -> float | None:
        wins = [g.attempts for g in self.games if g.won]
        if not wins:
            return None
        return sum(wins) / len(wins)

    @property
    def total_score(self) -> int:
        return sum(g.score for g in self.games)

    @property
    def playstyle_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for g in self.games:
            counts[g.playstyle] = counts.get(g.playstyle, 0) + 1
        return counts

    @property
    def dominant_playstyle(self) -> str:
        counts = self.playstyle_counts
        if not counts:
            return "new player"
        return max(counts.items(), key=lambda pair: pair[1])[0]


def classify_playstyle(
    initial_low: int,
    initial_high: int,
    history: list[tuple[int, str]],
) -> str:
    """Categorize how a player narrowed the range.

    - **binary_searcher**: every guess sits within 25% of the live midpoint
    - **edge_hunter**: most guesses are within 20% of the current bounds
    - **drifter**: high variance, ignores feedback, repeats dead numbers
    - **single_shot**: only one guess (won or lost immediately)
    - **systematic**: not perfectly binary but consistently narrows
    """
    int_history = [(g, o) for g, o in history if isinstance(g, int) and o in {"Too High", "Too Low", "Win"}]
    if len(int_history) <= 1:
        return "single_shot"

    low, high = initial_low, initial_high
    binary_count = 0
    edge_count = 0
    repeats = 0
    seen: set[int] = set()
    drift_signals = 0

    for guess, outcome in int_history:
        span = max(high - low + 1, 1)
        mid = (low + high) // 2
        if span > 1:
            distance_from_mid = abs(guess - mid)
            if distance_from_mid <= max(1, span * 0.15):
                binary_count += 1
            distance_from_low = guess - low
            distance_from_high = high - guess
            if min(distance_from_low, distance_from_high) <= max(1, span * 0.20):
                edge_count += 1
        if guess in seen:
            repeats += 1
        seen.add(guess)
        if guess < low or guess > high:
            drift_signals += 1
        if outcome == "Too Low" and guess + 1 > low:
            low = guess + 1
        elif outcome == "Too High" and guess - 1 < high:
            high = guess - 1

    n = len(int_history)
    if binary_count / n >= 0.6:
        return "binary_searcher"
    if drift_signals + repeats >= max(2, n // 2):
        return "drifter"
    if edge_count / n >= 0.6:
        return "edge_hunter"
    return "systematic"


def _serialize_profile(profile: PlayerProfile) -> dict:
    return {
        "games": [asdict(g) for g in profile.games[-MAX_HISTORY:]],
    }


def _deserialize_profile(data: dict) -> PlayerProfile:
    raw = data.get("games", [])
    return PlayerProfile(games=[GameSummary.from_dict(g) for g in raw])


def load_profile(path: Path = PROFILE_FILE) -> PlayerProfile:
    """Read the profile from disk, returning an empty profile if missing."""
    if not path.exists():
        return PlayerProfile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _deserialize_profile(data)
    except (json.JSONDecodeError, OSError):
        return PlayerProfile()


def save_profile(profile: PlayerProfile, path: Path = PROFILE_FILE) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_serialize_profile(profile), indent=2), encoding="utf-8")


def record_game(
    profile: PlayerProfile,
    *,
    difficulty: str,
    theme: str,
    won: bool,
    attempts: int,
    score: int,
    secret: int,
    initial_low: int,
    initial_high: int,
    history: list[tuple[int, str]],
) -> GameSummary:
    """Append a finished game to the profile and return the GameSummary."""
    summary = GameSummary(
        timestamp=datetime.now(timezone.utc).isoformat(),
        difficulty=difficulty,
        theme=theme,
        won=won,
        attempts=attempts,
        score=score,
        secret=secret,
        initial_low=initial_low,
        initial_high=initial_high,
        history=history,
        playstyle=classify_playstyle(initial_low, initial_high, history),
    )
    profile.games.append(summary)
    if len(profile.games) > MAX_HISTORY:
        profile.games = profile.games[-MAX_HISTORY:]
    return summary


def stats_summary(profile: PlayerProfile) -> dict[str, Any]:
    """Plain dict suitable for rendering in the sidebar."""
    avg = profile.avg_attempts_to_win
    return {
        "games_played": profile.games_played,
        "games_won": profile.games_won,
        "games_lost": profile.games_lost,
        "win_rate": round(profile.win_rate * 100, 1),
        "avg_attempts_to_win": round(avg, 1) if avg is not None else None,
        "total_score": profile.total_score,
        "dominant_playstyle": profile.dominant_playstyle,
        "playstyle_counts": profile.playstyle_counts,
    }
