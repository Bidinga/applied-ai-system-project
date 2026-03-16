from logic_utils import check_guess

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    outcome, message = check_guess(50, 50)
    assert outcome == "Win"

def test_guess_too_high():
    # If the secret is 50 and guess is 60, hint should be "Too High"
    outcome, message = check_guess(60, 50)
    assert outcome == "Too High"

def test_guess_too_low():
    # If the secret is 50 and guess is 40, hint should be "Too Low"
    outcome, message = check_guess(40, 50)
    assert outcome == "Too Low"

def test_hint_logic_is_correct():
    ## Specifically tests that 'Too High' results in a 'Go LOWER' message.

    outcome, message = check_guess(guess=80, secret=50)
    
    assert outcome == "Too High"
    assert "LOWER" in message  # Verifies the hint is no longer backwards