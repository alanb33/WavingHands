# Static Groble Names

from random import randint

def get_random_name():

    first_f = "./groble_first_names.txt"
    last_first_f = "./groble_last_first_compound.txt"
    last_second_f = "./groble_last_second_compound.txt"

    try:
        first_name_list = []
        last_name_firstcomp = []
        last_name_secondcomp = []
        with open(first_f) as f:
            first_name_list = f.read().splitlines()
        with open(last_first_f) as f:
            last_name_firstcomp = f.read().splitlines()
        with open(last_second_f) as f:
            last_name_secondcomp = f.read().splitlines()

        first = first_name_list[randint(1, len(first_name_list)-1)]
        last_first = last_name_firstcomp[randint(1, len(last_name_firstcomp)-1)]
        last_second = last_name_secondcomp[randint(1, len(last_name_secondcomp)-1)]

        return first.capitalize() + " " + last_first.capitalize() + last_second

    except FileNotFoundError:
        raise FileNotFoundError("Failed to populate spellbook: Could not find path \'" + str(first_f) + "\'")

    return "stupid groble"