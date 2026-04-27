from guardrails import (
    GuardResult,
    check_hint,
    compute_live_range,
    contains_secret,
    deterministic_fallback_hint,
)


def test_secret_leak_word_boundary():
    assert contains_secret("the answer is 42", 42) is True
    assert contains_secret("you guessed 420 last time", 42) is False
    assert contains_secret("try 142 next", 42) is False
    assert contains_secret("between 41 and 43", 42) is False


def test_secret_leak_with_thousands_separator():
    assert contains_secret("try 1,234", 1234) is True


def test_secret_leak_empty_string():
    assert contains_secret("", 42) is False


def test_check_hint_strips_code_fences():
    result = check_hint("```\nTry the midpoint of your range — that's the best move.\n```", secret=42)
    assert result.ok
    assert "```" not in result.cleaned


def test_check_hint_blocks_secret_leak():
    result = check_hint("The secret is 42, try 41 next.", secret=42)
    assert not result.ok
    assert "secret_leak" in result.issues


def test_check_hint_truncates_long_text():
    long = "x" * 400
    result = check_hint(long, secret=42)
    assert len(result.cleaned) <= 260
    assert "truncated_to_max_length" in result.issues


def test_check_hint_rejects_empty():
    result = check_hint("   ", secret=42)
    assert not result.ok
    assert "empty_hint" in result.issues


def test_fallback_hint_never_leaks_secret():
    hint = deterministic_fallback_hint(live_low=40, live_high=60, attempts_left=3)
    assert "50" in hint
    assert "secret" not in hint.lower()


def test_fallback_hint_handles_one_candidate():
    hint = deterministic_fallback_hint(live_low=42, live_high=42, attempts_left=1)
    assert "42" in hint


def test_fallback_hint_avoids_secret_when_secret_is_midpoint():
    # Live range 41-44, midpoint 42. If secret==42, hint must not contain "42".
    hint = deterministic_fallback_hint(live_low=41, live_high=44, attempts_left=2, secret=42)
    assert "42" not in hint
    assert "43" not in hint  # bounds 41 and 44 are fine, mid=42 risky


def test_fallback_hint_avoids_secret_when_secret_is_low_bound():
    # Live range 42-100 (player guessed 41 too-low). Secret==42 sits at lower bound.
    hint = deterministic_fallback_hint(live_low=42, live_high=100, attempts_left=5, secret=42)
    assert "42" not in hint


def test_fallback_hint_uses_numbers_when_secret_is_safe():
    # Live range 40-60, midpoint 50. Secret=43 is inside the range but not a bound/mid.
    hint = deterministic_fallback_hint(live_low=40, live_high=60, attempts_left=3, secret=43)
    assert "50" in hint  # safe to mention midpoint
    assert "43" not in hint


def test_compute_live_range_too_low():
    low, high = compute_live_range(1, 100, [(30, "Too Low")])
    assert (low, high) == (31, 100)


def test_compute_live_range_too_high():
    low, high = compute_live_range(1, 100, [(70, "Too High")])
    assert (low, high) == (1, 69)


def test_compute_live_range_combined_history():
    low, high = compute_live_range(1, 100, [(30, "Too Low"), (70, "Too High"), (40, "Too Low")])
    assert (low, high) == (41, 69)


def test_compute_live_range_ignores_win():
    low, high = compute_live_range(1, 100, [(50, "Win")])
    assert (low, high) == (1, 100)


def test_confidence_scoring_clean_hint():
    from ai_coach import _confidence_from_issues
    assert _confidence_from_issues([]) == 1.0


def test_confidence_scoring_secret_leak_is_near_zero():
    from ai_coach import _confidence_from_issues
    assert _confidence_from_issues(["secret_leak"]) < 0.1


def test_confidence_scoring_truncation_is_high_but_not_perfect():
    from ai_coach import _confidence_from_issues
    score = _confidence_from_issues(["truncated_to_max_length"])
    assert 0.7 < score < 1.0
