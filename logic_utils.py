def get_range_for_difficulty(difficulty: str):
    """Return (low, high) inclusive range for a given difficulty."""
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100

def parse_guess(raw: str):
    """Parse user input into an int guess."""
    if not raw or raw.strip() == "":
        return False, None, "Enter a guess."
    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
        return True, value, None
    except Exception:
        return False, None, "That is not a number."

def check_guess(guess, secret):
    """Compare guess to secret and return (outcome, message)."""
    # Fix: Ensure both are integers to avoid the string comparison bug
    guess = int(guess)
    secret = int(secret)
    
    if guess == secret:
        return "Win", "🎉 Correct!"
    
    if guess > secret:
        # BUG FIXED: If guess is too high, tell them to go LOWER
        return "Too High", "📉 Go LOWER!"
    else:
        # BUG FIXED: If guess is too low, tell them to go HIGHER
        return "Too Low", "📈 Go HIGHER!"

def update_score(current_score: int, outcome: str, attempt_number: int):
    """Update score based on outcome and attempt number."""
    if outcome == "Win":
        points = 100 - 10 * (attempt_number)
        return current_score + max(points, 10)
    
    # Simple penalty for wrong guesses
    return current_score - 5