# 💭 Reflection: Game Glitch Investigator


## 1. What was broken when you started?

The game loaded as a Streamlit interface featuring a sidebar for difficulty settings and a main dashboard with a 'Developer Debug Info' section.
the layout appeared professional but the 'Make a guess' area displayed confusing instructions, claiming the range was always 1 to 100 regardless of the difficulty level I selected. The UI included interactive elements like a text input field, a 'Submit Guess' button, and a 'New Game' button, but the feedback messages immediately felt unreliable.

---

## 2. How did you use AI as a teammate?

I used Gemini as my primary AI pair programmer to diagnose terminal issues and refactor the game logic.

Gemini correctly identified that the "Too High" and "Too Low" hints were logically inverted in the original app.py. I verified this by running the new test_hint_logic_is_correct test case in pytest, which confirmed that a high guess now correctly prompts the user to go "LOWER".


---

## 3. Debugging and testing your fixes

I decided a bug was truly fixed when it passed both a targeted automated test in pytest and a manual "sanity check" by playing the game in the browser.

I ran a manual test by opening the "Developer Debug Info" in the Streamlit app to see the secret number. This showed me that the secret number remained stable across multiple guesses instead of resetting every time I clicked "Submit".

Yes, the AI helped me design a specific test case for test_game_logic.py that checked if the output message contained the word "LOWER" when a guess was too high. This helped me understand how to assert specific string contents in a test.

---

## 4. What did you learn about Streamlit and state?

Why the Secret Kept Changing: In the original app, the secret number was being regenerated or mismanaged during the script's execution because Streamlit reruns the entire script from top to bottom every time a user interacts with a widget.

Explaining Reruns and State: I would tell a friend that a Streamlit "rerun" is like the browser hitting the refresh button every time you click anything. Session state is like a "memory bank" or a sticky note that stays on the screen during those refreshes so the app doesn't forget your score or your secret number.

The Change for Stability: The change that finally stabilized the secret number was ensuring it was stored in st.session_state.secret and only re-initialized when the "New Game" button was explicitly pressed.
---

## 5. Looking ahead: your developer habits

 I want to reuse the habit of refactoring core logic into a separate logic_utils.py file. This made it much easier to write clean unit tests without the overhead of the Streamlit UI.

Next time, I would start by writing the pytest cases before fixing the code to follow a true Test-Driven Development (TDD) approach.

This project changed my perspective by showing me that AI can generate code that looks functional but contains deep logical flaws. I now view AI as a source of "drafts" that require mandatory human verification and testing.

---

#  Reflection AI Hint Coach extension

## 1. How I used AI during this build

For Project 4 I paired with Claude inside Claude Code as a co-author. I used it for three distinct things: (a) brainstorming the agent shape (the planner → retrieve → generate → critique chain came out of a back-and-forth about what "substantial" means in the rubric), (b) accelerating boilerplate (the `GuardResult` dataclass, the JSONL logger, the TF-IDF math), and (c) catching my own design mistakes early through smoke testing. 

## 2. One helpful AI suggestion

When I described the design, the AI pushed back on my initial idea of a single-shot generator with the secret hidden behind a system prompt. It pointed out that LLMs occasionally echo numeric facts from context regardless of system instructions, and that a *separate critic step that re-reads the draft with the secret in hand* would catch leaks the generator missed. I implemented it, and it found a real bug: my `deterministic_fallback_hint` was naming the live-range midpoint, which equaled the secret in one of the eval scenarios. 

## 3. One flawed AI suggestion

The AI initially suggested using `sklearn.feature_extraction.text.TfidfVectorizer` for the retriever. That would have added ~150 MB of installed dependencies for six short markdown files. I rejected it and wrote a 60-line pure-Python TF-IDF instead — easier to read, faster to install, and now the only retrieval dependency is the standard library. 

## 4. System limitations

- The strategy corpus is small. Hint quality is bounded by what's in those notes; broader topics like probability priors or game-theoretic adversaries aren't represented.
- TF-IDF doesn't handle paraphrasing or semantic similarity — a query worded differently from the docs may miss the relevant chunk. At this corpus size this hasn't been a problem, but it would be at 10× scale.
- The mock-mode generator is deterministic, so the eval harness mostly tests *guardrails* rather than LLM hint quality. Live-mode hint quality is observable in the UI but not regression-tested.
- The critic runs on the same model family as the generator. Shared blind spots are possible. Rotating the critic to a different provider (or even a different model size) would be a stronger signal.
- The secret-leak regex is conservative — it occasionally flags references to range bounds the player has already deduced themselves, which forces the system into the deterministic fallback. The player still gets coaching but a slightly less specific one.

## 5. Future improvements

- **Multi-turn coaching mode.** Today each hint is independent. A coach that remembers what it said two turns ago could detect when a player keeps ignoring its advice and adjust tone.
- **Live-mode regression eval.** Run the eval harness once per CI cycle against a real Anthropic key with a fixed seed, and store the hint outputs as fixtures so I can diff hint quality across model versions.
- **Token-budget surface.** Each hint costs 3 LLM calls. A small UI affordance that shows "this hint cost $0.0003" would teach me to think about cost-per-feature.
- **Cross-provider critic.** Make the critic call a different provider so its blind spots don't overlap with the generator's.
- **Bigger corpus + real embeddings.** If the project grew to support adjacent games (Wordle-style, Mastermind), I'd swap TF-IDF for sentence-transformers or hosted embeddings.

---

# 💭 Reflection: Project 4 — second pass (themed games, profile, narrator)

After the first pass landed I opened the running app and reacted to my own work as a player, not an engineer. The coach panel was full of developer noise: a " mock mode (no API key)" status banner, a JSON `st.expander("Show agent trace")` dumping raw planner intent and critic verdict, the secret visible in the *Developer Debug Info* panel. As a player I couldn't FEEL the AI doing anything for me — the surface was a debug tool. I told my AI collaborator: *"what i am seeing now on the app is not showing me anything USEFUL"* and asked for new meaningful features.

## What changed in the second pass

**1. coach narration ([narrator.py](narrator.py)).** The same structured trace still flows to `logs/coach.jsonl` for engineers, but the UI now renders a friendly bullet list: what the AI noticed, what notes it pulled, what it caught itself doing, and how confident it is. The player sees prose, not JSON.

**2. Persistent player profile ([player_profile.py](player_profile.py)).** Every finished game is appended to `data/player_profile.json`. The sidebar shows games played, win rate, average attempts to win, and an AI-classified dominant playstyle (`binary_searcher`, `drifter`, `edge_hunter`, `systematic`, `single_shot`). The classification runs on the move history; it's deterministic Python, not an LLM call.

**3. Post-game AI scouting report ([ai_coach.py::get_post_game_review](ai_coach.py)).** When a game ends, the coach generates a 2–4 sentence personalized review keyed off the player's playstyle, the outcome, and their long-running stats. Mock mode uses templated language that varies by playstyle (a binary searcher gets *"Keep doing exactly this"*, a drifter gets *"Pause after each piece of feedback, find the live midpoint, and guess there"*). Live mode hands the same data to Claude.

**4. Themed game mode! ([themes.py](themes.py)).** A sidebar selector turns the round into trivia: *Guess the year humans walked on the Moon · Guess Iceland's population · Guess Mount Everest's height in meters ·* etc. 12 hand-curated themes ship with the project so it works without an API key; live mode can also call Claude to generate fresh themes. Theme explanations are revealed at end-of-game.

**5. Hidden secret.** The *Game info* panel no longer reveals the secret while the game is in progress — only after win or loss.

## One helpful AI suggestion 

When I described the player profile, my collaborator suggested splitting it into two layers: a *deterministic* playstyle classifier (Python rules over the move history) and an *LLM* post-game review that consumes the classifier's output. I'd been planning to send the raw move history straight to the LLM and ask it to do everything. The split turned out to be much better: the classifier is unit-testable, the review is short and focused, and the LLM has less work to do per call. The same structure now powers the narrator (deterministic transformation → optional LLM polish).

## One flawed AI suggestion )

I asked the AI to name the new player-state module `profile.py`. It did, and Streamlit ran fine — but Python's standard library has a stdlib `profile` module (the cProfile sibling) and there's a real risk of import collisions when other code does `import profile`. I caught it on review and renamed to `player_profile.py`. The AI defaulted to the most natural name without checking the namespace; I had to apply the engineer's discipline. Lesson: even a simple module name needs a quick `python -c "import X"` collision check before commit.

## What this round taught me

The single biggest insight from this project: *the AI's natural output is structure, but humans want narrative*. A JSON trace is technically more informative than a bullet list , it has more facts. But the bullet list is more useful because it explains, in language, what the system did and why. Designing for the user means doing the structure → narrative transformation yourself; the AI won't do it by default. I now treat "the AI gave me a structured response, what would a person actually want to read?" as a deliberate design step, not something to skip. i think that the AI makes exactly what it is prompted to make, but doesnt think about real life use cases, UI for the user to like what they are looking at. It's all very interesting. 
