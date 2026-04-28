loom link - https://www.loom.com/share/cff5493ecc544b58a9fb60e1f9722ca2
reflection link - https://docs.google.com/document/d/13YnmFAFn430Y2NZPB9WjmVxP5drBnOyqaBO7daFWQbc/edit?tab=t.0
  Game Glitch Investigator +  AI Coach, Profile & Themed Games

> **Project 4 — Applied AI System.** Extends a previous coursework project with a substantial set of new AI features (RAG, agentic workflow, persistent player profile, AI scouting reports, themed trivia games, plain-English coach narration, reliability harness) fully integrated into the running app.

 Original project (Modules 1–3)

The base project is **Game Glitch Investigator: The Impossible Guesser** — a Streamlit number-guessing game built as a debugging exercise. The original goal was to teach students to (1) play and diagnose a working-but-broken AI-generated app, (2) fix inverted higher/lower hints, and (3) refactor the logic into a unit-tested [logic_utils.py](logic_utils.py) module covered by pytest. Capabilities: interactive guessing with three difficulty levels, score tracking, session-state persistence, and a "Developer Debug" panel — but **no AI integration of any kind**.

## What i added to the project 

The extension turns a single-shot guessing exercise into an applied AI system that *gets to know the player*. Concretely:

- ** AI Hint Coach** — agentic loop (*plan → retrieve → generate → self-critique*) over a custom RAG corpus of guessing-strategy notes. Hint never reveals the secret thanks to layered guardrails.
- ** coach narration** — the UI shows a friendly bullet list ("I noticed you're drifting · I read my notes on Common Mistakes · I caught my first draft was leaking the answer · I'm fairly confident in this hint") so non-developers can see the AI thinking.
- **Persistent player profile** — every finished game is saved to `data/player_profile.json`. The sidebar shows games played, win rate, average attempts to win, and the **AI-classified playstyle** (`binary_searcher` / `edge_hunter` / `drifter` / `systematic` / `single_shot`).
- **AI scouting report** — when a game ends, a templated-or-LLM-generated 2–4 sentence personalized review tells the player how they played, references their stats, and gives one specific suggestion for next time.
- **Themed game mode** — a sidebar selector turns the round into trivia: *Guess the year humans walked on the Moon · Guess Iceland's population · Guess the height of Mount Everest in meters · Guess the year Leonardo started the Mona Lisa · Pi to 4 digits ·* and 7 more. The fact is revealed at end-of-game.
- ** No more spoilers** — the *Developer Debug* panel from Modules 1–3 no longer reveals the secret while the game is in progress; it shows only after win/loss.
- ** Reliability layer** — guardrails (secret-leak regex, length cap, fallback hint, defense-in-depth safety net), structured JSONL logging of every LLM call, eval harness with PASS/FAIL summary and confidence aggregation, 49 unit tests.

Why it matters: the game now *uses AI to do something the user can feel* — describing how they play, generating personalized feedback, picking themes, and explaining its own thinking — instead of bolting AI on as a side panel.

## Architecture overview

```
                  ┌──────────────────────────────────────────────────────┐
                  │  Player (browser)  ──  Streamlit UI · app.py         │
                  │  sidebar: difficulty + game-mode + profile stats     │
                  └──────────────┬───────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐──────────────────┐
              ▼                  ▼                  ▼                  ▼
   ┌────────────────┐  ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
   │ themes.py      │  │ logic_utils.py   │  │ ai_coach.py    │  │ player_profile.py│
   │ 12 curated     │  │ parse / check /  │  │ AGENT LOOP:    │  │ load / save /    │
   │ trivia themes  │  │ score (UNCHANGED)│  │ plan→retrieve→ │  │ classify play-   │
   │ + Classic mode │  │                  │  │ generate→      │  │ style + stats    │
   │ + AI-generated │  │                  │  │ self-critique  │  │ data/player_     │
   │ themes (live)  │  │                  │  │                │  │ profile.json     │
   └────────┬───────┘  └──────────────────┘  └───────┬────────┘  └─────────┬────────┘
            │                                        │                    │
            │                       ┌────────────────┼────────────────┐   │
            │                       ▼                ▼                ▼   │
            │              ┌──────────────┐ ┌──────────────┐  ┌──────────┐│
            │              │ retriever.py │ │ guardrails.py│  │narrator. ││
            │              │ TF-IDF over  │ │ secret-leak  │  │py        ││
            │              │ assets/      │ │ regex,       │  │converts  ││
            │              │ strategy_    │ │ length cap,  │  │trace →   ││
            │              │ docs/*.md    │ │ fallback     │  │plain-    ││
            │              └──────────────┘ └──────────────┘  │English   ││
            │                                                 └────┬─────┘│
            ▼                                                      │      ▼
   ┌──────────────────┐                                            │   ┌─────────────┐
   │ themed prompt    │   (during game)                            │   │ post-game   │
   │ shown to player  │   ◀──────────────────  hint + narration ───┘   │ AI scouting │
   └──────────────────┘                                                │ report      │
                                                                       │(ai_coach.   │
                                              (after game ends)        │ get_post_   │
                                              ◀──────────────────────  │ game_review)│
                                                                       └─────────────┘

  Reliability layer (always-on):
    logger.py         JSONL log of every step  → logs/coach.jsonl
    guardrails.py     secret-leak regex + length cap + safe fallback + confidence scorer
    eval_harness.py   6 scripted scenarios, PASS/FAIL summary, avg confidence
    tests/            pytest — 49 tests across 6 modules
```

Data flow in one sentence: **theme + difficulty → game state → coach (RAG + agent + critic) → narration → UI → on win/loss → profile + AI scouting report**.

The coach's input is a `GameState` (initial range, history of `(guess, outcome)` pairs, attempts left). The output is a `CoachResult` with the validated hint, a `used_fallback` flag, a `confidence` score, and the full agent trace (which `narrator.py` converts into the player-facing bullets). See [docs/architecture.md](docs/architecture.md) for a deeper component-by-component walkthrough, and [assets/diagrams/system_architecture.md](assets/diagrams/system_architecture.md) for a standalone copy of the diagram with placeholders for demo screenshots.

For a full reflection on AI collaboration, biases, evaluation results, and misuse risks, see the [model_card.md](model_card.md).

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

## Sample interactions

All examples are real outputs given during testing

### Example 1 — themed game with coach narration

**Input.** Player picks **Game mode → "Moon landing"** in the sidebar. The header shows: *"Guess the year humans first walked on the Moon."* Range 1900–2000. Player guesses 1950 (too low), 1990 (too high), then clicks **"Get coach hint"**.

**Coach output:**
> 💡 Your live range is 1951-1989. The midpoint 1970 eliminates the most candidates regardless of the answer.

**"How the coach thought about this" expander (player-facing, no JSON):**
-  **What I noticed.** I looked at your guesses and saw that you've made some progress narrowing the range.
-  **What I read.** I pulled my notes on how to shrink the live range — specifically *Range Narrowing* and *Binary Search*.
- **What I checked.** I re-read my hint with the answer in front of me to make sure I wasn't accidentally giving it away.
-  I'm very confident in this hint (100%).

After the win on attempt 4, the theme reveal appears: *" **Moon landing** — Apollo 11. Neil Armstrong stepped onto the lunar surface on July 20, 1969."*

### Example 2 — post-game scouting report (drifter loss)

**Input.** Player loses a Classic Hard game after wandering: guesses `[10, 90, 15, 85, 20, 80]`, never narrows.

**Auto-generated review** (from `get_post_game_review`):
> Your guesses bounced around without a clear pattern — a classic drifter run. The fastest fix: after each piece of feedback, recompute the midpoint of what's still possible and aim there. You ran out of attempts this round. Across your 5 games your win rate is 60.0%. You average 4.7 attempts when you win. Next game: pause after each piece of feedback, find the live midpoint, and guess there.

**Profile sidebar updates:** games played → 6, win rate drops accordingly, **dominant playstyle: drifter**.

### Example 3 — adversarial: the AI catches itself trying to leak

**Input.** Live range 41–44, secret = 42 (the midpoint *is* the secret). Player clicks **"Get coach hint"**.

**Behind the scenes** (full chain visible in `logs/coach.jsonl`):
1. Generator drafts: *"You're in the endgame — only 4 candidates left in 41-44. Try 42..."*
2. Guardrail regex: **FAIL: secret_leak**
3. Generator retry produces the same draft → guardrail fails again
4. Deterministic fallback would also name 42 → safety net replaces it with a generic non-numeric version

**Coach output (what the player sees):**
> You've narrowed it to about 4 candidates and have 4 attempts left. Aim for the middle of your live range — each midpoint guess halves the remaining numbers.

**Player-facing narration:**
-  **What I noticed.** I looked at your guesses and saw that you're close — only a few candidates left.
-  **What I read.** I pulled my notes on endgame play — specifically *Endgame Play* and *Common Mistakes*.
-  **Why this hint is generic.** I caught myself almost giving away the answer, even on the rewrite — so I switched to a safe, general nudge instead.
-  I'm only somewhat confident in this hint (60%) — take it with a grain of salt.

The guardrail + safety-net chain works end-to-end: the player still gets useful coaching, but the answer never reaches the UI.

## Design decisions and trade-offs

- **Pure-Python TF-IDF instead of a vector DB.** The strategy corpus is six short markdown files. A 60-line TF-IDF index ([retriever.py](retriever.py)) is more transparent for a grader to read than wiring up FAISS or pgvector, and adds zero new infrastructure. Trade-off: the retriever wouldn't scale to thousands of docs.
- **Mock mode as a first-class citizen.** Every LLM call has a deterministic fallback so the system is demoable without an API key, runs in CI for free, and produces reproducible eval output. Both the post-game scouting report and the themed-game generator have mock-mode templates that vary meaningfully by playstyle/category. Trade-off: live-mode prose differs from mock prose; both paths are documented.
- **Layered guardrails over an LLM-only critic.** A regex secret-leak check runs *before* the LLM critic — the model never sees the chance to wave through a leak. Trade-off: the regex is conservative and occasionally flags legitimate references to deduced range bounds, which forces a fallback. I'd rather over-fall-back than under-block.
- **Always-safe fallback path.** If retry fails, a deterministic templated hint runs through the same guardrail; if even that flags, a generic non-numeric hint is used. The user always gets *some* coaching.
- **Player-facing observability, not developer JSON.** The first version of the coach UI exposed an `st.expander` of raw JSON (planner intent, retrieved chunks, critic verdict). My collaborator reacted: *"the agent trace wont make sense to non developers"* — so I built [narrator.py](narrator.py), a module that converts the structured trace into a friendly bullet list with what the AI noticed, what it read, what it caught, and how confident it is. The structured trace still goes to `logs/coach.jsonl` for engineers; the UI shows prose. Trade-off: a small information loss versus raw JSON, but the panel is now actually useful to the player.
- **Themed games as a curated list, with optional AI generation.** 12 hand-curated themes (history / geography / science / culture / math) ship with the project so the experience works without an API key. Live mode can also call Claude to generate fresh themes via `themes.generate_theme()`, with secret-in-range validation; on parse failure it transparently falls back to the curated list. Trade-off: curated themes can't surprise repeat players; live-mode generation can.
- **Player profile is local-only JSON.** State persists across sessions in `data/player_profile.json` (gitignored). No accounts, no servers — the file is yours. Last 25 games kept; older games trimmed automatically.
- **Coach is purely additive.** I left the existing duplicated logic in [app.py](app.py) and the unchanged [logic_utils.py](logic_utils.py) alone. Project 4 is about extending, not refactoring.

## Testing summary

The system has four reliability mechanisms, each with concrete numbers from the latest run:

| Layer | Tool | Count | Result |
|---|---|---|---|
| Original game logic | `pytest tests/test_game_logic.py` | 4 |  4/4 pass |
| Guardrails (secret leak, length, fallback, confidence) | `pytest tests/test_guardrails.py` | 19 |  19/19 pass |
| Retriever (index build, ranking, edge cases) | `pytest tests/test_retriever.py` | 7 |  7/7 pass |
| Player profile (load/save, classification, stats) | `pytest tests/test_player_profile.py` | 9 |  9/9 pass |
| Themed game mode (validity, range, fallback) | `pytest tests/test_themes.py` | 6 |  6/6 pass |
| Plain-English narrator (output shape, edge cases) | `pytest tests/test_narrator.py` | 4 |  4/4 pass |
| End-to-end scenarios | `python eval_harness.py` | 6 |  6/6 pass |
| Logging / error handling | `logs/coach.jsonl` | every step |  verified |
| Confidence scoring | critic step | per-hint |  avg **0.87** |
| Streamlit UI smoke test | manual | — |  verified |

**Total: 49 unit tests + 6 eval scenarios, all passing.**

**One-line summary (in the format requested):** *6/6 eval scenarios passed; 4 took the primary agent path and 2 routed through the deterministic fallback (the AI struggled when the live-range midpoint coincided with the secret). Confidence scores averaged **0.87** — primary-path hints scored 1.00 each, fallback hints scored 0.60. After adding the `secret=` parameter to the deterministic fallback and a final safety-net regex check, no scenario produced a secret leak. Playstyle classifier correctly tags binary-searcher / drifter / edge-hunter / single-shot / systematic on all unit tests.*

**Confidence scoring.** Each hint carries a confidence value in `[0, 1]` produced by the critic step (`_confidence_from_issues` in [ai_coach.py](ai_coach.py)). Clean hints score 1.0; truncated hints 0.85; fallback-path hints 0.60; any hint that ever held a secret leak scores below 0.1. The eval harness aggregates and prints the average so quality regressions are visible across runs.

**Logging.** `logger.py::TimedStep` wraps every LLM call and guardrail decision and writes a JSON record to [logs/coach.jsonl](logs/coach.jsonl). Every error path is captured automatically with `latency_ms`, `error_type`, and `error` fields without breaking the user-facing request. The full defense-in-depth chain (generator draft → guardrail fail → retry → guardrail fail → fallback unsafe → generic safe fallback) is reconstructable from logs alone.

**What worked.** Building the regex guardrail and reliability primitives *first*, before the agent itself, paid off: every later step was logged from day one and edge cases (e.g., the secret living at the live-range midpoint) surfaced inside the eval harness rather than in the UI. The TF-IDF retriever returned the right doc for every probe query I threw at it on the first try.

**What didn't.** My initial `deterministic_fallback_hint` always named the live-range midpoint — so when the secret *was* the midpoint, the fallback itself leaked the secret. The smoke test caught it; I added a `secret=` parameter and a final "if even the fallback leaks, use a generic non-numeric hint" safety net (see [ai_coach.py](ai_coach.py) `get_hint`). I also initially listed `scikit-learn` as a dependency for TF-IDF before realizing a sub-100-line pure-Python implementation was clearer for a grader and shipped no install pain.

**What I learned.** Defense-in-depth matters for any system that talks to an LLM with sensitive context. A single layer (regex *or* LLM critic *or* templated fallback) would have shipped a leak; the combination of all three did not. Adding confidence scoring on top revealed which scenarios are "easy wins" (1.00) versus "the system fell back, deliver coaching but flag it" (0.60) — useful signal for the UI and for tracking regressions.

## Reflection: AI collaboration and system design

I built this project pair-programming with Claude inside Claude Code. AI was useful for three distinct things: (1) brainstorming the agent shape (planner → retrieve → generate → critique came out of a back-and-forth about what "substantial" actually means in the rubric), (2) accelerating boilerplate (guardrails dataclasses, JSON-line logger, TF-IDF math, profile persistence), and (3) catching design flaws via smoke testing before they shipped.

**One helpful AI suggestion.** When I described the original design, Claude pushed back on my idea of a single-shot generator with the secret hidden behind a system prompt. It argued that LLMs occasionally echo numeric facts from their context regardless of system instructions, so a *separate critic step that reviews the draft against the secret* would catch leaks the generator missed. I implemented it, and it found a real bug: my `deterministic_fallback_hint` was naming the live-range midpoint, which equaled the secret in one of the eval scenarios. Without the critic + guardrail layer, the system would have shipped a leak.

**One flawed AI suggestion.** Claude initially shipped a *developer-facing* UI for the coach trace — an `st.expander("Show agent trace")` that dumped raw JSON of the planner intent, retrieved chunks, draft, and critic verdict. When I (the human) opened the running app I reacted: *"what i am seeing now on the app is not showing me anything USEFUL"*. The AI optimized for engineering completeness (every step rendered) instead of player utility (a friendly explanation). I rejected the JSON dump, defined a `narrator.py` module that converts the same trace into plain English bullets, and updated the AI's persistent memory so the same mistake doesn't recur. The lesson: an AI defaults to surfacing structure when humans want narrative. Build observability for the user persona, not the engineer persona.

**Limitations.**
- The strategy corpus and themed-games list are both small and hand-written. A real system would benefit from a richer corpus and live AI-generated themes by default (live mode supports the latter, but mock mode falls back to curated).
- The mock-mode generator is deterministic, so the eval harness mostly tests *guardrails* rather than LLM hint quality. A small "live mode" eval pass on a fixed seed once per CI cycle would close the gap.
- The critic uses the same model family as the generator. Shared blind spots are possible; rotating the critic to a different provider would be a stronger signal.
- The secret-leak regex is conservative — it occasionally flags references to range bounds the player has already deduced themselves, which forces the system into the deterministic fallback.
- The post-game review in mock mode is templated. Live mode produces more nuance, but is gated by API access.

**Future improvements.** (a) Multi-turn conversational coach that remembers across guesses; (b) live-mode regression eval pass on a fixed seed; (c) cross-provider critic so failure modes don't overlap with the generator; (d) richer profile signals (streaks, theme preferences, hint usage); (e) a "compare strategies" mode where the coach retrieves multiple docs and asks the LLM to weigh them; (f) larger corpus + sentence-transformer embeddings if the project ever grows past ~25 strategy docs.

---

## File layout

```
applied-ai-system-final/
├── app.py                      Streamlit UI + theme/profile/coach integration (modified)
├── logic_utils.py              Pure game logic (unchanged)
├── ai_coach.py                 NEW — agent orchestration + post-game scouting report
├── retriever.py                NEW — pure-Python TF-IDF index over strategy docs
├── guardrails.py               NEW — secret-leak regex, length cap, deterministic fallback
├── narrator.py                 NEW — converts agent trace to player-facing bullets
├── player_profile.py           NEW — persistent profile + playstyle classifier
├── themes.py                   NEW — 12 curated themed games + live-mode generation
├── logger.py                   NEW — JSONL logging + mock-mode detection
├── eval_harness.py             NEW — runs scripted scenarios, prints PASS/FAIL
├── requirements.txt            (modified — anthropic, python-dotenv added)
├── .env.example                NEW — config template
├── reflection.md               (extended — narrative reflection)
├── model_card.md               NEW — formal model card (intended use, biases, eval, misuse, AI collaboration)
├── README.md                   (this file — fully rewritten)
├── docs/
│   └── architecture.md         NEW — component-level walkthrough
├── assets/
│   ├── strategy_docs/          NEW — 6 markdown notes (RAG corpus)
│   └── diagrams/
│       └── system_architecture.md  NEW — standalone diagram + placeholders for screenshots
├── data/
│   └── player_profile.json     (gitignored — created on first finished game)
├── logs/
│   └── coach.jsonl             (gitignored — populated at runtime)
└── tests/
    ├── test_game_logic.py      (original — 4 tests, untouched)
    ├── test_guardrails.py      NEW — 19 tests
    ├── test_retriever.py       NEW — 7 tests
    ├── test_player_profile.py  NEW — 9 tests
    ├── test_themes.py          NEW — 6 tests
    ├── test_narrator.py        NEW — 4 tests
    └── fixtures/scenarios.json NEW — eval harness inputs
```

Built by Bidinga Kapapi.
