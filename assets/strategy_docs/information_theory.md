# Information Theory of Guessing

Each guess is a question, and the answer (too high, too low, correct) carries information measured in bits. With a uniform prior over a range of N candidates, the maximum information a single yes-or-no answer can give is 1 bit. Binary search is "optimal" precisely because it extracts that full bit on every step.

A guess at the midpoint partitions the live range into two equal halves, so whichever answer arrives, it eliminates exactly half the candidates. A guess far from the midpoint splits the range unevenly: it might yield more than 1 bit if the player gets lucky (small partition is correct) but less than 1 bit on average.

This is why "guessing low to play it safe" is mathematically worse than guessing the midpoint over many games. Safety has a cost paid in extra attempts.

Encouraging takeaway for a player: every guess at the midpoint of your live range is the most informative move you can make. There is no smarter guess.
