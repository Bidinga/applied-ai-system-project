# System Architecture Diagram

Reference copy of the architecture diagram. The same diagram is embedded in [../../README.md](../../README.md) and [../../docs/architecture.md](../../docs/architecture.md), with a deeper component-by-component walkthrough in the latter.

## Diagram

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

## Data flow (one sentence)

Theme + difficulty → game state → coach (RAG + agent + critic) → narration → UI → on win/loss → profile + AI scouting report.

## Where humans / tests verify AI output

- **Player**: sees the hint and the *How the coach thought about this* expander, exposing each step's output in plain English.
- **Eval harness** (`python eval_harness.py`): scripted PASS/FAIL on 6 scenarios including an adversarial one designed to make the coach want to leak the secret.
- **Pytest** (`pytest`): 49 unit-level assertions on guardrails, retriever, narrator, profile, themes, and original game logic.
- **Logs** (`logs/coach.jsonl`): permanent record of every LLM call and guardrail decision; the entire defense-in-depth chain is reconstructable from logs alone.

## Demo screenshots

Add screenshots of the running app here as `screenshot_*.png`. Suggested captures:

- `screenshot_themed_game.png` — sidebar showing a themed game and player profile stats
- `screenshot_coach_thinking.png` — the *How the coach thought about this* expander
- `screenshot_post_game.png` — end-of-game scouting report with theme reveal
- `screenshot_adversarial_fallback.png` — coach catching itself trying to leak the secret
