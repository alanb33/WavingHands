# Static Groble Names

from random import randint

from waving_hands.config import DATA

# Load these immediately on import. This will do two things: Cause exceptions sooner
# rather than when the game starts if files can't be found. And second, cache the
# names in memory for less IO.
with open(DATA["names"]["first"]) as f:
    first_name_list = f.read().splitlines()
with open(DATA["names"]["last_first"]) as f:
    last_name_firstcomp = f.read().splitlines()
with open(DATA["names"]["last_second"]) as f:
    last_name_secondcomp = f.read().splitlines()


def get_random_name():
    first = first_name_list[randint(1, len(first_name_list)-1)]
    last_first = last_name_firstcomp[randint(1, len(last_name_firstcomp)-1)]
    last_second = last_name_secondcomp[randint(1, len(last_name_secondcomp)-1)]

    return f"{first.capitalize()} {last_first.capitalize()}{last_second}"
