# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

The game loaded as a Streamlit interface featuring a sidebar for difficulty settings and a main dashboard with a 'Developer Debug Info' section.
the layout appeared professional but the 'Make a guess' area displayed confusing instructions, claiming the range was always 1 to 100 regardless of the difficulty level I selected.The UI included interactive elements like a text input field, a 'Submit Guess' button, and a 'New Game' button, but the feedback messages immediately felt unreliable.

---

## 2. How did you use AI as a teammate?

For this project, I used Gemini as my primary AI pair programmer to diagnose terminal issues and refactor the game logic.

Gemini correctly identified that the "Too High" and "Too Low" hints were logically inverted in the original app.py. I verified this by running the new test_hint_logic_is_correct test case in pytest, which confirmed that a high guess now correctly prompts the user to go "LOWER".

Early on, the AI assumed my environment was configured for the standard python command. I verified this was incorrect when my terminal failed to register the version, and I had to manually switch to using python3 to match my Mac's installation.

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

# 💭 Reflection: Project 4 — AI Hint Coach extension

## 1. How I used AI during this build

For Project 4 I paired with Claude inside Claude Code as a co-author. I used it for three distinct things: (a) brainstorming the agent shape (the planner → retrieve → generate → critique chain came out of a back-and-forth about what "substantial" means in the rubric), (b) accelerating boilerplate (the `GuardResult` dataclass, the JSONL logger, the TF-IDF math), and (c) catching my own design mistakes early through smoke testing. I did *not* use AI to write the strategy documents — those are six small markdown files I wrote by hand, because the corpus quality directly determines hint quality and I wanted full control.

## 2. One helpful AI suggestion

When I described the design, the AI pushed back on my initial idea of a single-shot generator with the secret hidden behind a system prompt. It pointed out that LLMs occasionally echo numeric facts from context regardless of system instructions, and that a *separate critic step that re-reads the draft with the secret in hand* would catch leaks the generator missed. I implemented it, and it found a real bug: my `deterministic_fallback_hint` was naming the live-range midpoint, which equaled the secret in one of the eval scenarios. Without the critic + guardrail layer, the system would have shipped a leak.

## 3. One flawed AI suggestion

The AI initially suggested using `sklearn.feature_extraction.text.TfidfVectorizer` for the retriever. That would have added ~150 MB of installed dependencies for six short markdown files. I rejected it and wrote a 60-line pure-Python TF-IDF instead — easier to read, faster to install, and now the only retrieval dependency is the standard library. The lesson: AI defaults toward "use the well-known library" even when the well-known library is dramatically over-scoped for the task. Match the tool to the problem size, not to the popular reference architecture.

## 4. System limitations

- The strategy corpus is small (6 hand-written notes). Hint quality is bounded by what's in those notes; broader topics like probability priors or game-theoretic adversaries aren't represented.
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

