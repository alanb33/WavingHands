from waving_hands.gamemaster import Gamemaster
from waving_hands.spellbook import Spellbook
from waving_hands.config import DATA


def test_simple_spell(game):
    spells = Spellbook(DATA["spellbook"]).spell_list
    # print([(s, s.gesture) for s in spells])
    # print(Spellbook(DATA["spellbook"]).spell_list)
    wiz1, wiz2 = game.wizards
    wiz1.client.messages = [
        "choose_my_spell",
        "MULTIPLE_SPELLS_ACK",
        "MULTIPLE_SPELLS_COMPLETE",
        "Amnesia",
        "Aoeu",
        "GET_TARGET_ACK",
        "GET_TARGET_COMPLETE",
        "self",
    ]

    wiz1.c_hands = dict(left=spells[0].gesture, right="")
    game.play_game(max_turns=1)
