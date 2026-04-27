# Binary Search

Binary search is the optimal strategy for guessing a number in a known range when the only feedback is "higher" or "lower". On every guess you eliminate half of the remaining range, so the worst-case number of guesses for a range of size N is ceil(log2(N)).

The mechanic is simple: track the active window [low, high]. Always guess the midpoint, `mid = (low + high) // 2`. If the answer is "too high", the new window is [low, mid - 1]. If "too low", the new window is [mid + 1, high]. Repeat.

For a range of 1 to 100, you should always finish within 7 guesses. For 1 to 20, within 5. If a player exceeds these bounds, they are almost certainly not narrowing systematically.

Common mistake: forgetting to advance the window after the feedback, so the next guess re-explores already-eliminated territory. Always shrink the window before guessing again.
