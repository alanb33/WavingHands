import pytest
from waving_hands.gamemaster import Gamemaster
from waving_hands.spellbook import Spellbook
from waving_hands.config import DATA

CHOOSE_MULTIPLE_SPELLS = [
    "MULTIPLE_SPELLS_ACK",
    "MULTIPLE_SPELLS_COMPLETE",
]

TARGET_SELF = [
    "GET_TARGET_ACK",
    "GET_TARGET_COMPLETE",
    "self",
]

ENCHANT_SELF = [
    "ENCHANTMENT_CHARM_PERSON_ACK",
    "ENCHANTMENT_CHARM_PERSON_COMPLETE",
    ("left", "f"),
]

SPELLS = [
    ("Amnesia", CHOOSE_MULTIPLE_SPELLS + ["Amnesia"] + TARGET_SELF,),
    ("Anti-spell", TARGET_SELF),
    ("Blindness", TARGET_SELF),
    ("Cause Heavy Wounds", TARGET_SELF),
    (
        "Cause Light Wounds",
        CHOOSE_MULTIPLE_SPELLS + ["Cause Light Wounds"] + TARGET_SELF,
    ),
    ("Charm Monster", TARGET_SELF),
    ("Charm Person", TARGET_SELF + ENCHANT_SELF + ["$"]),
    #  'Confusion',
    #  'Counter-spell',
    #  'Counter-spell (alt)',
    #  'Cure Heavy Wounds',
    #  'Cure Light Wounds',
    #  'Delayed Effect',
    #  'Disease',
    #  'Dispel Magic',
    #  'Fear',
    #  'Finger of Death',
    #  'Fire Storm',
    #  'Fireball',
    #  'Haste',
    #  'Ice Storm',
    #  'Invisibility',
    #  'Lightning Bolt',
    #  'Lightning Bolt (Quick)',
    #  'Magic Mirror',
    #  'Magic Missile',
    #  'Paralysis',
    #  'Permanency',
    #  'Poison',
    #  'Protection from Evil',
    #  'Raise Dead',
    #  'Remove Enchantment',
    #  'Resist Cold',
    #  'Resist Heat',
    #  'Shield',
    #  'Summon Elemental',
    #  'Summon Groble I',
    #  'Summon Groble II',
    #  'Summon Groble III',
    #  'Summon Groble IV',
    #  'Surrender',
    #  'Time Stop'
]


@pytest.mark.parametrize("spell, client_messages", SPELLS)
def test_spells(spell, client_messages, game, wizard):
    sp = Spellbook(DATA["spellbook"]).get_spell(spell)
    wizard.client.messages = client_messages
    wizard.c_hands = dict(left=sp.gesture, right="")
    game.play_game(max_turns=1)
    # It would be nice to make assertions about what the server is sending so this can be verified too,
    # but since there are pickled objects being sent back and forth right now this is difficult.
    # assert spell in wizard.client.send.call_args
    # assert wizard.client.send.call_args_list  == []
    assert wizard.client.send.call_count > 0
    # assert wizard.client.send.call_args == []
