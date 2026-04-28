# Model Card — AI Hint Coach + Themed Games System

A model card for the applied-AI system extending Game Glitch Investigator  
## Overview

This system adds AI features to a Streamlit number-guessing game. The headline feature is an AI Hint Coach that runs a four-step agent loop (plan, retrieve, generate, self-critique) over a custom corpus of guessing-strategy notes and produces a coaching hint without ever revealing the secret. Around that core, the system also includes a persistent player profile that classifies playstyle across sessions, a themed game mode (12 curated trivia themes plus optional AI-generated ones), an end-of-game scouting report personalized to the player, and narration of how the coach made its decision. 

## System details

| Component | What it does | Where |
|---|---|---|
| Planner LLM | Classifies the player's situation and produces a RAG query | `ai_coach.py::_planner` |
| Retriever | TF-IDF over six hand-written strategy notes | `retriever.py` |
| Generator LLM | Drafts a 1–2 sentence coaching hint | `ai_coach.py::_generator` |
| Critic LLM + regex guard | Validates the draft against the secret | `ai_coach.py::_critic` + `guardrails.py` |
| Post-game review | 2–4 sentence personalized scouting report | `ai_coach.py::get_post_game_review` |
| Narrator | Converts agent trace into plain-English bullets | `narrator.py` |
| Player profile | Persistent stats + AI-classified playstyle | `player_profile.py` |
| Themed game mode | 12 curated trivia themes + optional live generation | `themes.py` |
| Logger | JSONL record of every LLM call and guard decision | `logger.py` → `logs/coach.jsonl` |
| Eval harness | 6 scripted scenarios with PASS/FAIL summary | `eval_harness.py` |

**Models.** Anthropic Claude (default `claude-haiku-4-5-20251001` for planner/critic, `claude-sonnet-4-6` for generator and post-game review). All models are configurable via environment variables. The same code runs in **mock mode** (deterministic templated responses) when no API key is set, so the system is reproducible without billed inference.

**License.** Educational coursework. Anyone may read, learn from, or extend.

## Intended use

This system is designed for:

- Playing the number-guessing game with optional AI coaching.
- Demonstrating how RAG, agentic workflows, guardrails, and reliability tooling fit together in a small applied-AI project.
- Coursework grading (Project 4 — Applied AI System rubric).

## Out-of-scope use and misuse risks

The pattern this system implements is "an AI assistant with privileged context produces user-facing text." That pattern generalizes badly to high-stakes domains. Specifically, the system should not be used or copied for:

- **Anywhere the privileged context is genuinely sensitive.** The "secret number" is a low-stakes stand-in. The same architecture applied to answer keys on a graded exam, internal pricing data, private medical records, or a user's personal credentials would either need much stronger guardrails than what's in `guardrails.py` or shouldn't exist at all.
- **Production decision-making.** Mock mode produces deterministic responses; live mode produces probabilistic ones. Neither is calibrated for situations where a wrong hint causes harm.
- **Adversarial environments.** A user who deliberately tries to coax the coach into leaking the secret can find the boundary between "the regex catches the leak" and "the regex fails." The eval harness covers some adversarial cases but not all.

**Mitigations applied here.** Three defense layers (regex secret-leak check, LLM critic, deterministic templated fallback), a final safety net that swaps in a generic non-numeric hint if even the fallback would leak, and structured logging so every decision is reconstructable after the fact. These are useful in proportion to how much you trust whoever configures them, and they aren't a substitute for not deploying the pattern in domains where the cost of a single leak is high.

## Data

**RAG corpus.** Six hand-written markdown files in `assets/strategy_docs/`: binary search, range narrowing, information theory, common mistakes, persistence and tilt, endgame play. Each file is short (under 300 words) and reflects strategy I think a coach should be able to draw on. The corpus is deliberately small so the TF-IDF retriever stays interpretable.

**Themes.** Twelve hand-curated trivia themes in `themes.py`, spanning history, geography, science, culture, and math. Each theme has a verifiable secret, a generous range so binary search takes 5–7 guesses, and an explanation revealed at end-of-game.

**No user data leaves the device.** The player profile (`data/player_profile.json`) is local, gitignored, and never sent to any external service. The only outbound network calls are to Anthropic's API in live mode, which receive game state but no profile data.

## Evaluation results

| Layer | Tool | Count | Result |
|---|---|---|---|
| Original game logic | `pytest tests/test_game_logic.py` | 4 | 4/4 pass |
| Guardrails | `pytest tests/test_guardrails.py` | 19 | 19/19 pass |
| Retriever | `pytest tests/test_retriever.py` | 7 | 7/7 pass |
| Player profile | `pytest tests/test_player_profile.py` | 9 | 9/9 pass |
| Themed game mode | `pytest tests/test_themes.py` | 6 | 6/6 pass |
| Plain-English narrator | `pytest tests/test_narrator.py` | 4 | 4/4 pass |
| End-to-end agent | `python eval_harness.py` | 6 scenarios | 6/6 pass |
| Confidence scoring | per-hint, aggregated by harness | — | average 0.87 |

**Headline summary.** 49 unit tests pass. The eval harness runs 6 scripted scenarios including an adversarial one where the live-range midpoint coincides with the secret. 4 of 6 scenarios are resolved by the primary agent path (planner → retriever → generator → critic, single pass). 2 of 6 route through the deterministic fallback because the primary path would have leaked. No scenario produces a hint containing the secret. Average confidence across scenarios is 0.87 (primary path scores 1.00, fallback path scores 0.60).

**What surprised me during testing.** The same blind spot kept showing up across layers I had built specifically to defend against it. My deterministic fallback hint was supposed to be the always-safe path, and it was — except in the one case where the live-range midpoint happened to equal the secret, in which case the fallback's templated text named the secret directly. I caught this only because I had a final regex check on the fallback's own output, and that check fired during the smoke test. The lesson was that defense in depth is not three times as safe as a single layer if all three layers were written by the same person with the same blind spot. The retry path was a related surprise: in mock mode the generator is deterministic, so retrying produces the identical flawed draft. A retry buys you nothing if the input that broke things hasn't changed — you need a different fallback strategy, not just a second attempt.

## Limitations

- **Small RAG corpus.** Six hand-written documents. The coach's strategic vocabulary is whatever I happened to think of when writing them.
- **No semantic retrieval.** TF-IDF doesn't handle paraphrasing. A query worded differently from the documents may miss the relevant chunk. Fine at six documents, would fail at sixty.
- **Critic shares model family with generator.** Both default to Claude. They probably share blind spots, which means a hint the generator produces and the critic approves might both be wrong in the same direction.
- **Mock-mode generator is deterministic.** The eval harness mostly tests guardrails rather than LLM hint quality. Live-mode hint quality is observable in the UI but not regression-tested.
- **Conservative leak regex.** Occasionally flags references to range bounds the player has already deduced themselves. The player still gets coaching, just a more generic version.
- **Session memory is one game deep.** The coach doesn't remember what it said two turns ago. A multi-turn conversational mode would catch when a player keeps ignoring its advice.

## Biases

- **Cultural bias in themed games.** The 12 curated themes lean heavily Western: Roman Colosseum, Mona Lisa, Berlin Wall, Eiffel Tower, Mount Everest, Tokyo population, Apollo 11. A player from Lagos, Mumbai, or São Paulo gets fewer culturally relevant prompts than a player from Boston, and the bias was introduced just by being the person who picked the themes. Live-mode AI-generated themes inherit whatever distribution the model was trained on, which is also probably Western-skewed.
- **Author voice in the strategy corpus.** I wrote all six strategy documents myself. The coach's "voice" — what it considers a mistake, what it praises, how it phrases encouragement — is an extension of mine, not a neutral reflection of optimal play.
- **English-only.** Both the corpus and the themes are English. The system would not work for a player who reads or thinks in a different language.
- **Mock-mode templates encode my writing style.** A player who plays primarily in mock mode gets reviews and hints written by templates I wrote. They feel personalized because the templates substitute the player's stats, but the underlying voice is mine.

## AI collaboration during development

I built this project pair-programming with Claude inside Claude Code. The collaboration was less about "the AI writes my code" and more about "the AI proposes, I edit, sometimes I push back." A few moments stand out.

**One helpful AI suggestion.** When I described doing the secret-leak check inside the generator's own system prompt, the AI pushed back and said the generator can't reliably police itself, you need a separate critic step. I built it. That step ended up catching a real leak in my own deterministic fallback code on the first eval run. Without that suggestion, I would have shipped a bug I would have been confident wasn't there. The broader pattern, that LLMs occasionally echo numeric facts from their context regardless of system instructions, would not have occurred to me on my own.

**One flawed AI suggestion.** The AI initially shipped a developer-facing UI for the coach. The agent's full trace was rendered as a JSON `st.expander` showing planner intent, retrieved chunks, the draft, and the critic verdict. When I opened the running app and reacted as a player rather than as an engineer, the surface felt like a debug console. I told the AI: "what i am seeing now on the app is not showing me anything USEFUL." The AI had optimized for engineering completeness — every step rendered — instead of player utility. I rejected the JSON dump, defined a `narrator.py` module that converts the same trace into plain-English bullets, and saved a persistent memory note so future me doesn't repeat the mistake. The AI's instinct was to expose structure; humans want narrative.

There were smaller examples in the same vein. The AI suggested scikit-learn for the TF-IDF retriever, which would have added 150 megabytes of dependencies for six markdown files. It named a module `profile.py`, which silently shadows a Python standard library module. None of these suggestions were dangerous on their own, but they shared a pattern: the AI optimizing for the most familiar reference architecture instead of the actual problem in front of it. Catching that was my job.

**What I came away with.** Working alongside an AI assistant doesn't make me a better coder by writing code for me. It makes me a better editor. The AI generates fast, which is great, but it generates toward the most well-documented version of any given idea. If I had taken its first answer for everything, I would have shipped a working but joyless product — technically a Streamlit app with RAG, but practically a debug console wearing a game costume. The decisions that made the project actually feel like a game (hide the secret, replace the JSON trace with a friendly bullet list, add the post-game review, build themed trivia rounds) were all decisions where I had to push back on what the AI gave me first and ask, "would my non-technical friend find this useful?" That question is the one piece of judgment that doesn't transfer. Everything else, the AI can help me with.

## Reproducibility

To reproduce the evaluation results:

```bash
cd applied-ai-system-final/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # leave keys blank for mock mode
pytest -q              # expect 49 passed
MOCK_MODE=true python eval_harness.py   # expect 6/6 passed, avg confidence 0.87
```

For live-mode evaluation, set `ANTHROPIC_API_KEY` in `.env`, set `MOCK_MODE=false`, and rerun. Live-mode hint quality is not yet regression-tested; this is one of the future improvements listed in the limitations section.

## Author

Bidinga Kapapi. Project 4, Applied AI System. Original base project (Modules 1–3): *Game Glitch Investigator: The Impossible Guesser*.
