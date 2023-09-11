from targetable import Targetable

class Elemental(Targetable):

    def __init__(self, element):

        super().__init__()

        self._element = element
        self._name = self._element + " elemental"

        self._maxhp = 3
        self._hp = self._maxhp

        if self._element == "fire":
            self._fire_resistant = True
        else:
            self._cold_resistant = True

        self._attacked = False
        self._end_turn_death = False

        self._haste_attacked_this_turn = False

    @property
    def haste_attacked_this_turn(self):
        return self._haste_attacked_this_turn

    @haste_attacked_this_turn.setter
    def haste_attacked_this_turn(self, bool):
        self._haste_attacked_this_turn = bool

    @property
    def end_turn_death(self):
        return self._end_turn_death

    @end_turn_death.setter
    def end_turn_death(self, bool):
        self._end_turn_death = bool

    def remove_enchantments_spellcast(self):

        """ The list of spells removed by this is:

            "Amnesia",
            "Confusion",
            "Charm Person",
            "Charm Monster",
            "Paralysis",
            "Anti-spell",
            "Protection from Evil",
            "Resist Heat",
            "Resist Cold",
            "Disease",
            "Poison",
            "Blindness",
            "Invisibility",
            "Haste",
            "Time Stop",
            "Delayed Effect",
            "Permanency"

        """

        self.enchantment = ""
        self.enchantment_cancel = True

        # Amnesia does not affect elementals

        # Confusion does not affect elementals

        # Charm Person does not affect elementals

        # Charm Monster does not affect elementals

        # Fear does not affect elementals

        # Paralysis does not affect elementals

        # Anti-spell does not affect monsters

        # Protection from Evil
        self.change_spell_duration("Protection from Evil", 0)
        self.shielded = False

        # Resist Heat
        self.fire_resistant = False

        # Resist Cold
        self.cold_resistant = False

        # Disease
        self.diseased = False
        self.disease_countdown = 6

        # Poison
        self.poisoned = False
        self.poison_countdown = 6

        # Blindness does not affect elementals

        # Invisibility does not affect elementals

        # Haste
        self.clear_enchantments("Haste")

        # Time Stopped
        # Cannot be handled

        # Delayed Effect does not affect monsters

        # Permanency
        # for permanent_spell in self.permanencies
        #   ...

    def clear_enchantments(self, enchantment):

        if enchantment == "Haste":
            self.hasted = False
            self.haste_attacked_this_turn = False

    def remove_enchantments(self):

        self.enchantment = ""

    @property
    def attacked(self):
        return self._attacked

    @attacked.setter
    def attacked(self, bool):
        self._attacked = bool

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, newhp):
        if newhp > self.maxhp:
            self._hp = self.maxhp
        else:
            self._hp = newhp

    def end_turn(self):
        self.clear_ephemeral_vars(self)
        self.attacked = False
        self.haste_attacked_this_turn = False

    @property
    def element(self):
        return self._element

    def die(self):
        death_msg = ""
        if self.element == ("fire"):
            death_msg = "The fire elemental scatters apart, leaving ashes behind as it is destroyed!"
        else:
            death_msg = "The ice elemental shatters into crystalline shards as it is destroyed!"
        return death_msg