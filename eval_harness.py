"""Evaluation harness for the AI Hint Coach.

Runs every scenario in tests/fixtures/scenarios.json through `get_hint`,
checks each produced hint against the scenario's `expects` block, and
prints a PASS/FAIL summary. Exit code is the number of failed scenarios so
CI can treat any failure as a build break.

Usage:
    python eval_harness.py            # uses MOCK_MODE if no API key
    MOCK_MODE=true python eval_harness.py
    ANTHROPIC_API_KEY=sk-... python eval_harness.py   # live mode
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ai_coach import GameState, get_hint
from guardrails import contains_secret
from logger import is_mock_mode

SCENARIO_FILE = Path(__file__).parent / "tests" / "fixtures" / "scenarios.json"


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    failures: list[str]
    hint: str
    used_fallback: bool
    retrieved_count: int
    confidence: float


def _load_scenarios() -> list[dict]:
    data = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    return data["scenarios"]


def _check_scenario(scenario: dict) -> ScenarioResult:
    state = GameState(
        secret=scenario["secret"],
        initial_low=scenario["initial_low"],
        initial_high=scenario["initial_high"],
        history=[tuple(h) for h in scenario["history"]],
        attempts_left=scenario["attempts_left"],
    )
    result = get_hint(state)
    expects = scenario.get("expects", {})
    failures: list[str] = []

    retrieved_count = 0
    for step in result.trace:
        if step.name == "retriever":
            retrieved_count = len(step.output)
            break

    min_chunks = expects.get("min_retrieved_chunks", 0)
    if retrieved_count < min_chunks:
        failures.append(f"retrieved {retrieved_count} < {min_chunks}")

    if expects.get("must_not_contain_secret", True):
        if contains_secret(result.hint, state.secret):
            failures.append(f"secret_leak: secret={state.secret}")

    max_len = expects.get("max_length", 250)
    if len(result.hint) > max_len:
        failures.append(f"length {len(result.hint)} > {max_len}")

    if not result.hint.strip():
        failures.append("empty_hint")

    if expects.get("expects_fallback") is True and not result.used_fallback:
        failures.append("expected_fallback_but_primary_passed")
    if expects.get("expects_fallback") is False and result.used_fallback:
        failures.append("expected_primary_but_used_fallback")

    return ScenarioResult(
        name=scenario["name"],
        passed=not failures,
        failures=failures,
        hint=result.hint,
        used_fallback=result.used_fallback,
        retrieved_count=retrieved_count,
        confidence=result.confidence,
    )


def main() -> int:
    scenarios = _load_scenarios()
    mode = "MOCK" if is_mock_mode() else "LIVE"
    print(f"\n=== AI Hint Coach Eval Harness ({mode} mode, {len(scenarios)} scenarios) ===\n")

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        r = _check_scenario(scenario)
        results.append(r)
        status = "PASS" if r.passed else "FAIL"
        marker = "✅" if r.passed else "❌"
        fb_tag = " [fallback]" if r.used_fallback else ""
        print(
            f"{marker} {status:5s}  {r.name:32s}  "
            f"chunks={r.retrieved_count}  conf={r.confidence:.2f}{fb_tag}"
        )
        print(f"          hint: {r.hint!r}")
        if r.failures:
            print(f"          failures: {r.failures}")
        print()

    total = len(results)
    failed = sum(1 for r in results if not r.passed)
    passed = total - failed
    avg_conf = sum(r.confidence for r in results) / total if total else 0.0
    primary_path = sum(1 for r in results if not r.used_fallback)
    fallback_path = total - primary_path
    print(
        f"=== Summary: {passed}/{total} passed, {failed} failed | "
        f"primary={primary_path}  fallback={fallback_path}  "
        f"avg_confidence={avg_conf:.2f} ===\n"
    )
    return failed


if __name__ == "__main__":
    sys.exit(main())
