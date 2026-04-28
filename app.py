import streamlit as st
import random
from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ai_coach import GameState, get_hint, get_post_game_review
from narrator import narrate
import player_profile
import themes



def get_range_for_difficulty(difficulty: str):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100


def parse_guess(raw: str):
    if raw is None:
        return False, None, "Enter a guess."

    if raw == "":
        return False, None, "Enter a guess."

    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."

    return True, value, None


def check_guess(guess, secret):
    if guess == secret:
        return "Win", "🎉 Correct!"

    try:
        if guess > secret:
            return "Too High", "📉 Go LOWER!"
        else:
            return "Too Low", "📈 Go HIGHER!"
    except TypeError:
        g = str(guess)
        if g == secret:
            return "Win", "🎉 Correct!"
        if g > secret:
            return "Too High", "📉 Go LOWER!"
        return "Too Low", "📈 Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int):
    if outcome == "Win":
        points = 100 - 10 * (attempt_number + 1)
        if points < 10:
            points = 10
        return current_score + points

    if outcome == "Too High":
        if attempt_number % 2 == 0:
            return current_score + 5
        return current_score - 5

    if outcome == "Too Low":
        return current_score - 5

    return current_score

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

# ---------------------------------------------------------------------------
# Session-state setup
# ---------------------------------------------------------------------------

if "profile" not in st.session_state:
    st.session_state.profile = player_profile.load_profile()

ATTEMPT_LIMIT_MAP = {"Easy": 6, "Normal": 8, "Hard": 5}
ALL_THEMES = themes.themes_by_name()


def _start_new_game(theme_name: str, difficulty: str) -> None:
    """(Re)initialize a game given the chosen theme and difficulty."""
    if theme_name == "Classic":
        diff_low, diff_high = get_range_for_difficulty(difficulty)
        theme = themes.make_classic_theme(diff_low, diff_high)
    else:
        theme = ALL_THEMES.get(theme_name, themes.CLASSIC_THEME)
    st.session_state.theme = {
        "name": theme.name,
        "prompt": theme.prompt,
        "explanation": theme.explanation,
        "category": theme.category,
        "initial_low": theme.initial_low,
        "initial_high": theme.initial_high,
    }
    st.session_state.secret = int(theme.secret)
    st.session_state.difficulty = difficulty
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.pop("coach_result", None)
    st.session_state.pop("post_game_review", None)
    st.session_state.pop("game_recorded", None)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty (controls attempt limit)",
    ["Easy", "Normal", "Hard"],
    index=1,
    help="Easy = 6 attempts, Normal = 8, Hard = 5",
)

theme_options = list(ALL_THEMES.keys())
selected_theme_name = st.sidebar.selectbox(
    "Game mode",
    theme_options,
    index=0,
    help="Classic = guess a random number. Themed games turn the round into trivia.",
)

attempt_limit = ATTEMPT_LIMIT_MAP[difficulty]

# Initialize on first load or whenever theme/difficulty changes mid-game
need_new = (
    "theme" not in st.session_state
    or st.session_state.theme.get("name") != selected_theme_name
    or st.session_state.get("difficulty") != difficulty
)
if need_new:
    _start_new_game(selected_theme_name, difficulty)

theme_state = st.session_state.theme
low = int(theme_state["initial_low"])
high = int(theme_state["initial_high"])

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

st.sidebar.divider()
st.sidebar.subheader("📋 Your profile")
stats = player_profile.stats_summary(st.session_state.profile)
if stats["games_played"] == 0:
    st.sidebar.caption("No games on record yet — play one and your stats will appear here.")
else:
    st.sidebar.metric("Games played", stats["games_played"])
    st.sidebar.metric("Win rate", f"{stats['win_rate']}%")
    if stats["avg_attempts_to_win"] is not None:
        st.sidebar.metric("Avg attempts (wins)", stats["avg_attempts_to_win"])
    st.sidebar.caption(f"Playstyle so far: **{stats['dominant_playstyle'].replace('_', ' ')}**")

# ---------------------------------------------------------------------------
# Main area — header + game state
# ---------------------------------------------------------------------------

st.title("🎮 Game Glitch Investigator")
st.caption("Number-guessing game with an AI coach that learns how you play.")

if theme_state["name"] == "Classic":
    st.subheader(f"🎲 {theme_state['prompt']}")
else:
    st.subheader(f"🧠 {theme_state['prompt']}")
    st.caption(f"_(Theme: {theme_state['name']} · category: {theme_state['category']})_")

info_placeholder = st.empty()

with st.expander("Game info"):
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)
    if st.session_state.status != "playing":
        st.write("Secret was:", st.session_state.secret)
    else:
        st.write("Secret: 🔒 hidden until the game ends")

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{theme_state['name']}_{difficulty}",
    disabled=st.session_state.status != "playing",
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit guess 🚀", disabled=st.session_state.status != "playing")
with col2:
    new_game = st.button("New game 🔁")
with col3:
    show_hint = st.checkbox("Show direction hint", value=True)

if new_game:
    _start_new_game(selected_theme_name, difficulty)
    st.success("New game started.")
    st.rerun()


# ---------------------------------------------------------------------------
# Submit handler
# ---------------------------------------------------------------------------


def _record_finished_game(won: bool) -> None:
    """Append this game to the player profile, save, and request a review."""
    if st.session_state.get("game_recorded"):
        return
    history_pairs: list[tuple[int, str]] = []
    for entry in st.session_state.history:
        if not isinstance(entry, int):
            continue
        outcome, _ = check_guess(entry, st.session_state.secret)
        history_pairs.append((entry, outcome))

    summary = player_profile.record_game(
        st.session_state.profile,
        difficulty=difficulty,
        theme=theme_state["name"],
        won=won,
        attempts=st.session_state.attempts,
        score=st.session_state.score,
        secret=int(st.session_state.secret),
        initial_low=low,
        initial_high=high,
        history=history_pairs,
    )
    try:
        player_profile.save_profile(st.session_state.profile)
    except OSError:
        pass

    stats_snapshot = player_profile.stats_summary(st.session_state.profile)
    review = get_post_game_review(stats_snapshot, {
        "won": won,
        "attempts": summary.attempts,
        "score": summary.score,
        "playstyle": summary.playstyle,
        "theme": summary.theme,
        "difficulty": summary.difficulty,
    })
    st.session_state.post_game_review = review
    st.session_state.game_recorded = True


if submit:
    st.session_state.pop("coach_result", None)
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        outcome, message = check_guess(guess_int, st.session_state.secret)

        if show_hint and outcome != "Win":
            st.warning(message)

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            _record_finished_game(won=True)
        elif st.session_state.attempts >= attempt_limit:
            st.session_state.status = "lost"
            _record_finished_game(won=False)


# ---------------------------------------------------------------------------
# Status panel
# ---------------------------------------------------------------------------

if st.session_state.status == "playing":
    info_placeholder.info(
        f"Guess between {low} and {high}. Attempts left: {attempt_limit - st.session_state.attempts}"
    )
elif st.session_state.status == "won":
    info_placeholder.success(
        f"🎉 You got it! The answer was **{st.session_state.secret}**. Final score: {st.session_state.score}."
    )
else:
    info_placeholder.error(
        f"😬 Out of attempts. The answer was **{st.session_state.secret}**. Final score: {st.session_state.score}."
    )

# Reveal the theme's explanation once the game is over
if st.session_state.status != "playing" and theme_state["name"] != "Classic":
    st.info(f"📖 **{theme_state['name']}** — {theme_state['explanation']}")

# ---------------------------------------------------------------------------
# Post-game AI scouting report
# ---------------------------------------------------------------------------

if st.session_state.status != "playing" and st.session_state.get("post_game_review"):
    st.divider()
    st.subheader("📝 Coach's scouting report")
    st.write(st.session_state.post_game_review)


# ---------------------------------------------------------------------------
# Coach hint button + plain-English narration
# ---------------------------------------------------------------------------

st.divider()
st.subheader("🧠 Ask the coach for a hint")
st.caption("The coach reads your moves, looks up a strategy note, and writes a hint — without giving away the answer.")

coach_clicked = st.button(
    "Get coach hint",
    disabled=st.session_state.status != "playing",
)

if coach_clicked:
    history_pairs: list[tuple[int, str]] = []
    for entry in st.session_state.history:
        if not isinstance(entry, int):
            continue
        outcome, _ = check_guess(entry, st.session_state.secret)
        history_pairs.append((entry, outcome))

    attempts_left = max(attempt_limit - st.session_state.attempts, 0)
    with st.spinner("Coach is thinking..."):
        result = get_hint(
            GameState(
                secret=int(st.session_state.secret),
                initial_low=low,
                initial_high=high,
                history=history_pairs,
                attempts_left=attempts_left,
            )
        )
    st.session_state.coach_result = result.to_dict()

if "coach_result" in st.session_state:
    cr = st.session_state.coach_result
    if cr.get("used_fallback"):
        st.warning(f"💡 {cr['hint']}")
    else:
        st.success(f"💡 {cr['hint']}")

    with st.expander("How the coach thought about this"):
        for line in narrate(cr):
            st.markdown(f"- {line}")

st.divider()
st.caption("Built by Bidinga Kapapi · AI features added in Project 4")
