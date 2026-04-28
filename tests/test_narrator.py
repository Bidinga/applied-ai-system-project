import os

os.environ.setdefault("MOCK_MODE", "true")

from ai_coach import GameState, get_hint
from narrator import narrate


def test_narrate_includes_what_i_noticed_and_what_i_read():
    state = GameState(
        secret=42,
        initial_low=1,
        initial_high=100,
        history=[(50, "Too High"), (25, "Too Low")],
        attempts_left=6,
    )
    result = get_hint(state)
    lines = narrate(result.to_dict())
    joined = "\n".join(lines)
    assert "What I noticed" in joined
    assert "What I read" in joined
    # Confidence phrase always present
    assert any("confiden" in line.lower() or "confidence" in line.lower() for line in lines)


def test_narrate_mentions_caught_when_retry_happens():
    # Endgame scenario where the midpoint == secret triggers a retry
    state = GameState(
        secret=42,
        initial_low=1,
        initial_high=100,
        history=[(50, "Too High"), (25, "Too Low"), (40, "Too Low"), (45, "Too High")],
        attempts_left=4,
    )
    result = get_hint(state)
    lines = narrate(result.to_dict())
    joined = "\n".join(lines)
    # Either we caught the leak (retry succeeded) OR we used the safety fallback
    assert ("What I caught" in joined) or ("Why this hint is generic" in joined)


def test_narrate_handles_missing_steps_gracefully():
    # A degenerate trace shouldn't crash narrate()
    minimal = {
        "trace": [],
        "used_fallback": False,
        "confidence": 1.0,
    }
    lines = narrate(minimal)
    assert len(lines) >= 2  # at least "what I noticed" + confidence


def test_narrate_lines_are_player_friendly_strings():
    state = GameState(
        secret=42,
        initial_low=1,
        initial_high=100,
        history=[],
        attempts_left=8,
    )
    lines = narrate(get_hint(state).to_dict())
    for line in lines:
        assert isinstance(line, str)
        # No raw JSON leaking through
        assert not line.startswith("{")
        assert not line.startswith("[")
