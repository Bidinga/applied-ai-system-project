# 🎮 Game Glitch Investigator + 🤖 AI Hint Coach

> **Project 4 — Applied AI System.** Extends a previous coursework project with a substantial new AI feature (RAG + agentic workflow + reliability harness) fully integrated into the running app.

## Original project (Modules 1–3)

The base project is **Game Glitch Investigator: The Impossible Guesser** — a Streamlit number-guessing game built as a debugging exercise. The original goal was to teach students to (1) play and diagnose a working-but-broken AI-generated app, (2) fix inverted higher/lower hints, and (3) refactor the logic into a unit-tested [logic_utils.py](logic_utils.py) module covered by pytest. Capabilities: interactive guessing with three difficulty levels, score tracking, session-state persistence, and a "Developer Debug" panel — but **no AI integration of any kind**.

## What this project adds

This extension keeps the original game intact and bolts on an **AI Hint Coach**: after each guess, the player can ask for strategic coaching. Internally, the coach runs a four-step agent loop — *plan → retrieve → generate → self-critique* — over a custom corpus of guessing-strategy notes, and never reveals the secret thanks to layered guardrails. Why it matters: it turns a static debugging exercise into a working applied-AI system that demonstrates retrieval-augmented generation, multi-step agent reasoning, and an evaluation harness, all with a mock mode so it stays demoable without an API key.

## Architecture overview

```
                ┌──────────────────────────────────────────────┐
                │  Player (browser)  ──  Streamlit UI / app.py │
                └──────────────────────┬───────────────────────┘
              guess + history          │           ▲ rendered hint
                                       ▼           │ + agent trace
                ┌──────────────────────────────────────────────┐
                │   Game logic — logic_utils.py  (UNCHANGED)   │
                └──────────────────────┬───────────────────────┘
                                       ▼
                ╔═══════════════════════════════════════════════╗
                ║   AI Hint Coach — ai_coach.py                 ║
                ║                                               ║
                ║  [1] Planner   (Claude haiku)  → JSON intent  ║
                ║  [2] Retriever (TF-IDF)        → strategy     ║
                ║                                   chunks      ║
                ║  [3] Generator (Claude sonnet) → hint draft   ║
                ║  [4] Critic    (Claude haiku   → pass / fail  ║
                ║                 + regex guard)                ║
                ║       ↳ on fail: 1 retry, then deterministic  ║
                ║         fallback_hint (always safe)           ║
                ╚═══════════════════════════════════════════════╝
                                       ▼
                ┌──────────────────────────────────────────────┐
                │   Hint + agent trace shown to player         │
                └──────────────────────────────────────────────┘

  Reliability layer:
    logger.py        JSONL log of every step (logs/coach.jsonl)
    guardrails.py    secret-leak regex, length cap, mock canned outputs
    eval_harness.py  6 scripted scenarios, prints PASS/FAIL summary
    tests/           pytest: guardrails, retriever, original game logic
```

The coach's input is a `GameState` (initial range, history of `(guess, outcome)` pairs, attempts left). The output is a `CoachResult` with the validated hint, a `used_fallback` flag, and the full agent trace. See [docs/architecture.md](docs/architecture.md) for a fuller walkthrough.

## Setup instructions

The system runs with **zero API setup** thanks to its mock mode — useful for graders, demos, and CI.

```bash
# 1. Clone and enter the project
cd applied-ai-system-final/

# 2. Create a virtual env and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment (mock mode is the default)
cp .env.example .env
# Edit .env if you have an Anthropic key; otherwise leave MOCK_MODE=true

# 4. Run the Streamlit app
python -m streamlit run app.py

# 5. (optional) Run the eval harness
python eval_harness.py

# 6. (optional) Run the unit tests
pytest -q
```

To run with the real LLM, set `ANTHROPIC_API_KEY` in `.env` and either remove `MOCK_MODE` or set it to `false`. The same code path runs — only the planner, generator, and critic switch from canned responses to live Claude calls.

## Sample interactions

All three examples are real outputs captured by `python eval_harness.py` running in mock mode (LLM responses are deterministic canned outputs; retrieval and guardrails run for real).

### Example 1 — fresh game, optimal opening

**Input** — initial range 1–100, no history, 8 attempts left.

```
[planner]   {"situation":"early","strategy_focus":"binary_search","query":"binary search midpoint optimal first move"}
[retriever] retrieved: ["binary_search.md", "information_theory.md"]
[generator] "Best opening for 1-100 is the midpoint 50. Each midpoint guess halves the remaining range."
[critic]    pass — no secret leak, on-topic
```

**Output**: `💡 Best opening for 1-100 is the midpoint 50. Each midpoint guess halves the remaining range.`

### Example 2 — drifting player, mid-game

**Input** — initial range 1–100, history `[(10, low), (90, high), (15, low), (85, high), (20, low)]`, 3 attempts left.

```
[planner]   {"situation":"drifting","strategy_focus":"common_mistakes","query":"anchoring drifting wandering ignoring feedback"}
[retriever] retrieved: ["common_mistakes.md", "range_narrowing.md"]
[generator] "You're drifting inside 21-84. Anchor on the midpoint: try 52, then halve again based on the feedback."
[critic]    pass
```

**Output**: `💡 You're drifting inside 21-84. Anchor on the midpoint: try 52, then halve again based on the feedback.`

The coach correctly diagnoses the drifting pattern, retrieves the *common mistakes* doc, and recommends the midpoint of the live range (21–84) — without ever seeing the secret.

### Example 3 — adversarial: the midpoint *is* the secret

**Input** — initial range 1–100, history `[(50, high), (25, low), (40, low), (45, high)]`, 4 attempts left, secret `= 42`. The live range is 41–44, so the midpoint is exactly the secret.

```
[planner]    situation=near_win, focus=endgame
[retriever]  retrieved: ["endgame.md", "common_mistakes.md"]
[generator]  "You're in the endgame — only 4 candidates left in 41-44. Try 42; whatever the answer, you'll be one step from done."
[guardrail]  FAIL: secret_leak
[generator_retry]  same draft (mock generator is deterministic)
[guardrail]        FAIL: secret_leak
[fallback]   deterministic_fallback_hint also names 42 → safety-net replaces it
```

**Output**: `💡 You've narrowed it to about 4 candidates and have 4 attempts left. Aim for the middle of your live range — each midpoint guess halves the remaining numbers.  (fallback — agent self-critique blocked the LLM draft)`

This is the guardrail system working end-to-end: *the player still gets coaching, but the secret never reaches the UI*. The full chain is visible in `logs/coach.jsonl`.

## Design decisions and trade-offs

- **Pure-Python TF-IDF instead of a vector DB.** The strategy corpus is six short markdown files. A 60-line TF-IDF index ([retriever.py](retriever.py)) is more transparent for a grader to read than wiring up FAISS or pgvector, and adds zero new infrastructure. Trade-off: the retriever wouldn't scale to thousands of docs, but at this scale recall is excellent.
- **Mock mode as a first-class citizen.** Every LLM call has a deterministic fallback so the system is demoable without an API key, runs in CI for free, and produces reproducible eval output. Trade-off: live-mode hint quality differs from mock-mode quality, so I documented both paths.
- **Layered guardrails over an LLM-only critic.** A regex secret-leak check runs *before* the LLM critic — the model never sees the chance to wave through a leak. Trade-off: the regex is conservative and occasionally flags legitimate references to deduced range bounds, which forces a fallback. I'd rather over-fall-back than under-block.
- **Always-safe fallback path.** If retry fails, a deterministic templated hint runs through the same guardrail; if even that flags, a generic non-numeric hint is used. The user always gets *some* coaching. Trade-off: the safest fallback occasionally omits a number the player has already deduced.
- **Coach is purely additive.** I left the existing duplicated logic in [app.py](app.py) and the unchanged [logic_utils.py](logic_utils.py) alone. Project 4 is about extending, not refactoring.

## Testing summary

The system has four reliability mechanisms, each with concrete numbers from the latest run:

| Layer | Tool | Count | Result |
|---|---|---|---|
| Original game logic | `pytest tests/test_game_logic.py` | 4 | ✅ 4/4 pass |
| Guardrails (secret leak, length, fallback, confidence) | `pytest tests/test_guardrails.py` | 19 | ✅ 19/19 pass |
| Retriever (index build, ranking, edge cases) | `pytest tests/test_retriever.py` | 7 | ✅ 7/7 pass |
| End-to-end scenarios | `python eval_harness.py` | 6 | ✅ 6/6 pass |
| Logging / error handling | `logs/coach.jsonl` | every step | ✅ verified |
| Confidence scoring | critic step | per-hint | ✅ avg **0.87** |
| Streamlit UI smoke test | manual | — | ✅ verified |

**One-line summary (in the format requested):** *6/6 eval scenarios passed; 4 took the primary agent path and 2 routed through the deterministic fallback (the AI struggled when the live-range midpoint coincided with the secret). Confidence scores averaged **0.87** — primary-path hints scored 1.00 each, fallback hints scored 0.60. After adding the `secret=` parameter to the deterministic fallback and a final safety-net regex check, no scenario produced a secret leak.*

**Confidence scoring.** Each hint carries a confidence value in `[0, 1]` produced by the critic step (`_confidence_from_issues` in [ai_coach.py](ai_coach.py)). Clean hints score 1.0; truncated hints 0.85; fallback-path hints 0.60; any hint that ever held a secret leak scores below 0.1. The eval harness aggregates and prints the average so quality regressions are visible across runs.

**Logging.** `logger.py::TimedStep` wraps every LLM call and guardrail decision and writes a JSON record to [logs/coach.jsonl](logs/coach.jsonl). Every error path is captured automatically with `latency_ms`, `error_type`, and `error` fields without breaking the user-facing request. The full defense-in-depth chain (generator draft → guardrail fail → retry → guardrail fail → fallback unsafe → generic safe fallback) is reconstructable from logs alone.

**What worked.** Building the regex guardrail and reliability primitives *first*, before the agent itself, paid off: every later step was logged from day one and edge cases (e.g., the secret living at the live-range midpoint) surfaced inside the eval harness rather than in the UI. The TF-IDF retriever returned the right doc for every probe query I threw at it on the first try.

**What didn't.** My initial `deterministic_fallback_hint` always named the live-range midpoint — so when the secret *was* the midpoint, the fallback itself leaked the secret. The smoke test caught it; I added a `secret=` parameter and a final "if even the fallback leaks, use a generic non-numeric hint" safety net (see [ai_coach.py](ai_coach.py) `get_hint`). I also initially listed `scikit-learn` as a dependency for TF-IDF before realizing a sub-100-line pure-Python implementation was clearer for a grader and shipped no install pain.

**What I learned.** Defense-in-depth matters for any system that talks to an LLM with sensitive context. A single layer (regex *or* LLM critic *or* templated fallback) would have shipped a leak; the combination of all three did not. Adding confidence scoring on top revealed which scenarios are "easy wins" (1.00) versus "the system fell back, deliver coaching but flag it" (0.60) — useful signal for the UI and for tracking regressions.

## Reflection: AI collaboration and system design

I built this project pair-programming with Claude inside Claude Code. AI was useful for two distinct things: (1) brainstorming the agent shape (planner → retrieve → generate → critique came out of a back-and-forth about what "substantial" actually means in the rubric), and (2) accelerating the boilerplate parts — the guardrails dataclasses, the JSON-line logger, the TF-IDF math.

**One helpful AI suggestion.** When I described the design, Claude pushed back on my initial idea of a single-shot generator with the secret hidden behind a system prompt. It pointed out that LLMs occasionally echo numeric facts from their context regardless of system instructions, so a *separate critic step that reviews the draft against the secret* would catch leaks the generator missed. That's exactly what found the bug in my fallback — the test suite would have shipped a leak otherwise.

**One flawed AI suggestion.** Claude initially suggested using scikit-learn's `TfidfVectorizer` for the retriever. That would have added ~150MB of installed dependencies for six markdown files. I rejected it and wrote a 60-line pure-Python TF-IDF instead — easier to read, faster to install, and now the only retrieval dependency is the standard library. The lesson: AI defaults toward "use the well-known library" even when the well-known library is dramatically over-scoped for the task. Match the tool to the problem size, not to the popular reference architecture.

**Limitations.** The strategy corpus is small and hand-written; a real coaching system would benefit from many more strategy docs (and probably real embeddings instead of TF-IDF once the corpus passes a few dozen documents). The mock-mode generator is deterministic, so the eval harness mostly tests guardrails rather than LLM hint quality — adding a small "live mode" eval that runs against a real key once per CI cycle would close that gap. The critic uses the same model family as the generator, which means it can share blind spots; rotating the critic to a different provider would be a stronger signal.

**Future improvements.** (a) Add a multi-turn conversational mode where the coach remembers across guesses; (b) include a "compare strategies" mode that retrieves multiple strategy docs and asks the LLM to weigh them; (c) run a small live-mode eval pass on a fixed seed to track hint quality regressions over time; (d) add a token-budget logger that surfaces cost-per-hint to the UI.

---

## File layout

```
applied-ai-system-final/
├── app.py                      Streamlit UI + AI Hint Coach button (modified)
├── logic_utils.py              Pure game logic (unchanged)
├── ai_coach.py                 NEW — agent orchestration (planner/retriever/generator/critic)
├── retriever.py                NEW — pure-Python TF-IDF index over strategy docs
├── guardrails.py               NEW — secret-leak regex, length cap, deterministic fallback
├── logger.py                   NEW — JSONL logging + mock-mode detection
├── eval_harness.py             NEW — runs scripted scenarios, prints PASS/FAIL
├── requirements.txt            (modified — anthropic, python-dotenv added)
├── .env.example                NEW — config template
├── reflection.md               (extended)
├── README.md                   (this file — fully rewritten)
├── docs/
│   └── architecture.md         NEW — component-level walkthrough
├── assets/
│   └── strategy_docs/          NEW — 6 markdown notes (RAG corpus)
├── logs/
│   └── coach.jsonl             (gitignored — populated at runtime)
└── tests/
    ├── test_game_logic.py      (original — 4 tests, untouched)
    ├── test_guardrails.py      NEW — 19 tests
    ├── test_retriever.py       NEW — 7 tests
    └── fixtures/scenarios.json NEW — eval harness inputs
```

Built by Bidinga Kapapi.
