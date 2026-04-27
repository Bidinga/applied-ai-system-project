# Architecture — AI Hint Coach

This document expands the diagram in the [README](../README.md) with component-level details.

## System diagram

```
                ┌──────────────────────────────────────────────┐
                │  Player (browser)  ──  Streamlit UI / app.py │
                └──────────────────────┬───────────────────────┘
              guess + history          │           ▲ rendered hint
                                       ▼           │ + agent trace
                ┌──────────────────────────────────────────────┐
                │   Game logic — logic_utils.py  (UNCHANGED)   │
                │   parse_guess │ check_guess │ update_score   │
                └──────────────────────┬───────────────────────┘
                       GameState       │
                       (history,       ▼
                        secret,   ╔═══════════════════════════════╗
                        attempts) ║   AI Hint Coach — ai_coach.py ║
                                  ║                               ║
                                  ║  [1] Planner   (Claude haiku) ║
                                  ║  [2] Retriever (TF-IDF)       ║
                                  ║  [3] Generator (Claude sonnet)║
                                  ║  [4] Critic    (Claude haiku  ║
                                  ║                + regex guard) ║
                                  ║       on fail: 1 retry, then  ║
                                  ║       deterministic fallback  ║
                                  ╚═══════════════════════════════╝
                                          ▼
                ┌──────────────────────────────────────────────┐
                │  Streamlit UI renders hint + agent trace     │
                └──────────────────────────────────────────────┘

  Reliability layer (always-on, even in mock mode):
  • logger.py        appends every step to logs/coach.jsonl
  • guardrails.py    secret-leak regex, length cap, fallback hint
  • eval_harness.py  PASS/FAIL on 6 scripted scenarios
  • tests/           pytest covers guardrails + retriever + game logic

  Human / testing verification points:
  • UI "Show agent trace" expander  → human inspects each step's output
  • README "Sample interactions"    → 3 worked examples
  • eval_harness.py PASS/FAIL table → automated scoring
  • pytest                          → unit-level guardrail assertions
```

## Components

### `app.py` — Streamlit UI

Owns session state (secret, attempts, score, history). After each guess it renders the static "Go higher/lower" hint. The new "Get coach hint 🧠" button builds a `GameState` from session data, calls `ai_coach.get_hint(...)`, and renders the result plus a `st.expander("Show agent trace")` that shows planner intent, retrieved chunks, draft, and critic verdict. The status banner shows whether the system is in **mock** mode (no key) or **live** mode (Anthropic).

### `logic_utils.py` — original game logic (unchanged)

Pure functions for difficulty range, parse, comparison, scoring. Kept exactly as the prior project shipped it; the coach is purely additive.

### `ai_coach.py` — agent orchestration

Defines the `GameState` and `CoachResult` dataclasses and the public `get_hint(state) -> CoachResult` function.

The agent loop:

1. **Planner** classifies the player's situation and produces a RAG query string. Output: `{situation, strategy_focus, query}`. In live mode this is a Claude haiku call returning JSON; in mock mode it's a deterministic Python classifier (`_classify_for_mock`) that inspects the live range and history.
2. **Retriever** calls `retriever.get_index().retrieve(query, k=2)` over the strategy docs.
3. **Generator** drafts a 1–2 sentence hint conditioned on the live range, history, planner intent, and retrieved chunks. Live = Claude sonnet; mock = templated text using the live midpoint.
4. **Critic** runs the deterministic guardrails first (`guardrails.check_hint`); if they pass, in live mode an LLM critic reviews the draft for tone and on-topic relevance with the secret in context.

If the critic rejects the draft, the generator is rerun once with the issues pasted into the prompt. If that also fails, `deterministic_fallback_hint` produces a templated hint (and is itself re-checked, with a final non-numeric escape hatch). Every transition is logged via `logger.TimedStep` / `logger.log_event`.

### `retriever.py` — RAG over strategy docs

A pure-Python TF-IDF index over `assets/strategy_docs/*.md`. The corpus was hand-written for this project: six short notes covering binary search, range narrowing, information theory, common mistakes, persistence/tilt, and endgame play. Index is built once and cached via `lru_cache`. Tokenization is lowercased word characters of length ≥ 2 with a small stopword list. Cosine similarity ranks chunks by IDF-weighted term frequency.

### `guardrails.py` — output safety

- `contains_secret(hint, secret)` — word-boundary regex that ignores partial matches (e.g., secret 4 doesn't match "40") and strips thousands separators.
- `check_hint(hint, secret)` — strips code fences/HTML, applies length cap (10–250 chars), runs the leak check, returns a `GuardResult` with cleaned text and an issues list.
- `compute_live_range(initial_low, initial_high, history)` — derives `(low, high)` from the player's `[(guess, outcome), ...]`.
- `deterministic_fallback_hint(...)` — always-safe templated hint. When the secret coincides with the midpoint or a live bound, falls back to a non-numeric description ("aim for the middle of your live range").

### `logger.py` — structured logging

Every LLM call and every guardrail decision is appended to `logs/coach.jsonl` as a single JSON record with `ts`, `step`, and arbitrary fields. The `TimedStep` context manager records latency_ms automatically and captures exceptions without breaking the user-facing path. `is_mock_mode()` is the single source of truth for whether canned responses or real LLM calls are used.

### `eval_harness.py` — reliability/eval

Loads `tests/fixtures/scenarios.json`, runs `get_hint` on each scenario, asserts the produced hint against the scenario's `expects` block (no secret leak, length cap, retrieval count, fallback expectation). Prints a PASS/FAIL table and exits with the failure count, so it can gate CI.

## Data flow (one-line)

`guess → game state → planner → retriever → generator → critic + guardrails → hint + trace → UI`

## Where humans/testing verify AI output

- **Player**: sees the hint and the *Show agent trace* expander, which exposes each step's output. They can spot leaks or off-topic hints visually.
- **Eval harness** (`python eval_harness.py`): scripted PASS/FAIL on 6 scenarios including an adversarial one designed to make the coach want to leak.
- **Pytest** (`pytest`): unit-level guardrail assertions, including word-boundary edge cases and fallback safety.
- **Logs** (`logs/coach.jsonl`): permanent record of every LLM call and guardrail decision; the entire defense-in-depth chain is reconstructable from logs alone.
