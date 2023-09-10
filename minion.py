from targetable import Targetable

class Minion(Targetable):

    def __init__(self, name, rank):

        super().__init__()

        self._name = name
        
        self._rank = rank
        self._maxhp = self._rank
        self._hp = self._maxhp

        self._killing_blow = "dies!"

        self._damage = rank
        self._master = ""
        self._original_master = ""
        self._target = ""
        
        self._commanded = False
        self._attacked = False
        self._amnesia_target_override = None
        self._confusion_target_override = None
        self._resist_charm = False
        self._paralyzed = False

        self._haste_attacked_this_turn = False

    @property
    def haste_attacked_this_turn(self):
        return self._haste_attacked_this_turn

    @haste_attacked_this_turn.setter
    def haste_attacked_this_turn(self, bool):
        self._haste_attacked_this_turn = bool

    @property
    def paralyzed(self):
        return self._paralyzed

    @paralyzed.setter
    def paralyzed(self, bool):
        self._paralyzed = bool

    @property
    def resist_charm(self):
        return self._resist_charm

    @resist_charm.setter
    def resist_charm(self, bool):
        self._resist_charm = bool

    @property
    def original_master(self):
        return self._original_master

    @original_master.setter
    def original_master(self, who):
        self._original_master = who

    def remove_enchantments_spellcast(self):

        """ The list of spells removed by this is:

            "Amnesia",
            "Confusion",
            "Charm Person",
            "Charm Monster",
            "Fear",
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

        # Amnesia
        self.amnesia_target_override = None
        self.amnesiac = False
        
        # Confusion
        self.confusion_target_override = None
        
        # Charm Person (has no effect)

        # Charm Monster
        self.master.remove_minion(self)
        self.original_master.add_minion(self)
        self.target = self.master
        self.master = self.original_master

        # Fear does not affect monsters

        # Paralysis
        self.clear_enchantment("Paralysis")

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

        # Blindness
        #self.blinded = False

        # Invisibility
        #self.invisible = False

        # Haste
        #self.hasted = False

        # Time Stopped
        # Cannot be handled

        # Delayed Effect does not affect monsters

        # Permanency
        # for permanent_spell in self.permanencies
        #   ...

    def remove_enchantments(self):
        
        # This will prevent further enchantments on this turn.

        self.enchantment = ""
        self.amnesia_target_override = None
        self.confusion_target_override = None
        self.paralyzed = False

    @property
    def amnesia_target_override(self):
        return self._amnesia_target_override

    @amnesia_target_override.setter
    def amnesia_target_override(self, target):
        self._amnesia_target_override = target

    @property
    def confusion_target_override(self):
        return self._confusion_target_override

    @confusion_target_override.setter
    def confusion_target_override(self, target):
        self._confusion_target_override = target

    @property
    def attacked(self):
        return self._attacked

    @attacked.setter
    def attacked(self, bool):
        self._attacked = bool

    def clear_enchantment(self, enchantment):
        
        if enchantment == "Confusion":
            self.confused = False
            self.confusion_target_override = None

        if enchantment == "Paralysis":
            self.paralysis = False
            self.paralyzed = False
            self.enchantment = ""

        if enchantment == "Amnesia":
            self.amnesiac = False
            self.enchantment = ""

        if enchantment == "Haste":
            self.hasted = False
            self.haste_attacked_this_turn = False

    def end_turn(self):

        self.commanded = False
        self.attacked = False
        self.resist_charm = False
        self.haste_attacked_this_turn = False

        if "Charm" in self.enchantment or self.enchantment == "Fear":
            self.enchantment = ""

        self.clear_ephemeral_vars(self)

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, newhp):
        if newhp > self.maxhp:
            self._hp = self.maxhp
        else:
            self._hp = newhp

    @property
    def rank(self):
        return self._rank

    @property
    def damage(self):
        return self._damage

    @property
    def commanded(self):
        return self._commanded

    @commanded.setter
    def commanded(self, bool):
        self._commanded = bool

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, victim):
        self._target = victim

    def check_if_dead(self):
        """ This is separate from take_damage for proper phase spacing. """

        if self.hp <= 0:
            self.die()

    def die(self):
        """ 
            Prints some flavor text and then removes the minion from the
            master Wizard's minions list.
        """

        return (self.master.name + "\'s minion, " + self.name + ", " 
                + self.killing_blow)

    @property
    def master(self):
        return self._master

    @master.setter
    def master(self, master):
        self._master = master