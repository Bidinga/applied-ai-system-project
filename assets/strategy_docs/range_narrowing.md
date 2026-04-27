# Range Narrowing

Every guess plus its feedback ("too high" or "too low") tightens the live range. The current live range is bounded by:

- **low_bound** = max(initial_low, every guess that was "too low" + 1)
- **high_bound** = min(initial_high, every guess that was "too high" - 1)

A common error is to make a new guess outside the live range — for example guessing 30 after already learning that 40 was too low. That guess is wasted; the answer cannot be 30.

When coaching a player, compute the live range from their history. If their next guess would fall outside it, point that out gently. If their guesses are wandering inside the range without narrowing it, recommend the midpoint.

The live range is the single most useful piece of information for choosing the next guess. Players who lose track of it tend to drift.
