from pathlib import Path

import pytest

from player_profile import (
    GameSummary,
    PlayerProfile,
    classify_playstyle,
    load_profile,
    record_game,
    save_profile,
    stats_summary,
)


def test_classify_playstyle_binary_searcher():
    # Player who always guesses the live midpoint
    history = [(50, "Too High"), (25, "Too Low"), (37, "Too High"), (31, "Win")]
    assert classify_playstyle(1, 100, history) == "binary_searcher"


def test_classify_playstyle_drifter():
    # Player who bounces and repeats
    history = [(10, "Too Low"), (90, "Too High"), (10, "Too Low"), (95, "Too High"), (5, "Too Low")]
    assert classify_playstyle(1, 100, history) == "drifter"


def test_classify_playstyle_single_shot():
    history = [(50, "Win")]
    assert classify_playstyle(1, 100, history) == "single_shot"


def test_classify_playstyle_edge_hunter():
    # Player who always guesses near the boundary of their live range
    history = [(2, "Too Low"), (99, "Too High"), (3, "Too Low"), (98, "Too High")]
    assert classify_playstyle(1, 100, history) == "edge_hunter"


def test_record_game_appends_summary(tmp_path: Path):
    profile = PlayerProfile()
    summary = record_game(
        profile,
        difficulty="Normal",
        theme="Classic",
        won=True,
        attempts=5,
        score=60,
        secret=42,
        initial_low=1,
        initial_high=100,
        history=[(50, "Too High"), (25, "Too Low"), (37, "Too Low"), (43, "Too High"), (42, "Win")],
    )
    assert profile.games_played == 1
    assert profile.games_won == 1
    assert summary.playstyle in {"binary_searcher", "systematic"}


def test_save_and_load_round_trip(tmp_path: Path):
    profile = PlayerProfile()
    record_game(
        profile,
        difficulty="Hard",
        theme="Moon landing",
        won=False,
        attempts=8,
        score=-20,
        secret=1969,
        initial_low=1900,
        initial_high=2000,
        history=[(1950, "Too Low"), (1990, "Too High")],
    )
    path = tmp_path / "profile.json"
    save_profile(profile, path=path)

    loaded = load_profile(path=path)
    assert loaded.games_played == 1
    assert loaded.games[0].theme == "Moon landing"
    assert loaded.games[0].won is False
    assert loaded.games[0].attempts == 8


def test_load_missing_file_returns_empty():
    profile = load_profile(path=Path("/tmp/nonexistent_glitch_profile_xyz.json"))
    assert profile.games_played == 0


def test_stats_summary_no_games():
    summary = stats_summary(PlayerProfile())
    assert summary["games_played"] == 0
    assert summary["win_rate"] == 0.0
    assert summary["avg_attempts_to_win"] is None
    assert summary["dominant_playstyle"] == "new player"


def test_stats_summary_with_mixed_games():
    profile = PlayerProfile()
    for i in range(3):
        record_game(
            profile,
            difficulty="Normal",
            theme="Classic",
            won=True,
            attempts=4,
            score=50,
            secret=42,
            initial_low=1,
            initial_high=100,
            history=[(50, "Too High"), (37, "Too Low"), (43, "Too High"), (42, "Win")],
        )
    record_game(
        profile,
        difficulty="Normal",
        theme="Classic",
        won=False,
        attempts=8,
        score=-30,
        secret=42,
        initial_low=1,
        initial_high=100,
        history=[(50, "Too High"), (90, "Too High")],
    )
    summary = stats_summary(profile)
    assert summary["games_played"] == 4
    assert summary["games_won"] == 3
    assert summary["win_rate"] == 75.0
    assert summary["avg_attempts_to_win"] == 4.0
