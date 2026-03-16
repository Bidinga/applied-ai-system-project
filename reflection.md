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
