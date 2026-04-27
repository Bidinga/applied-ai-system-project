# Common Mistakes in Number Guessing

Players who lose tend to make a small set of repeating errors. Recognizing the pattern is the fastest way to recover.

1. **Repeating dead numbers.** Guessing a number already ruled out by previous feedback. Symptom: the same value or a value clearly outside the live range appears twice in the history.
2. **Stepping by one.** After learning a guess was too low, guessing exactly one higher. This burns attempts; the live range still has many candidates.
3. **Ignoring the upper bound.** After "too high" feedback, guessing higher again. This usually happens when the player conflates "too high" with "go higher".
4. **Anchoring on the first guess.** Continuing to guess values close to the first attempt regardless of feedback. The mind treats the first guess as a baseline; the math doesn't.
5. **Random drift.** No discernible pattern between consecutive guesses; the player is essentially sampling. Costs many attempts in expectation.

When you spot one of these, name the pattern plainly and recommend the midpoint of the live range as the next move.
