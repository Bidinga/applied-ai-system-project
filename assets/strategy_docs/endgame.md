# Endgame: Closing the Last Few Candidates

When the live range has narrowed to fewer than 5 candidates, the strategy shifts. There is no longer enough range for binary search to provide leverage, and most legal guesses will produce immediate resolution one way or the other.

Endgame heuristics:

- **Range of 1 candidate.** Guess it. The answer is forced.
- **Range of 2 candidates.** Pick either. There is no information advantage.
- **Range of 3 candidates.** Guess the middle one. If wrong, the next guess is forced.
- **Range of 4 candidates.** Guess the second-from-low. Two outcomes leave a forced one-of-three; one leaves a forced one-of-two.

Tone advice for coaching: in the endgame, the player is usually nervous and counting attempts. Acknowledge that they are close ("you've narrowed it down to N candidates") and name the forced move. Avoid abstract strategy talk this late in the game.
