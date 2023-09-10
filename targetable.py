from abc import ABC, abstractmethod

class Targetable(ABC):

    def __init__(self):
        self._name = ""
        self._color = ""
        self._hp = 0
        self._maxhp = 0
        self._killing_blow = ""

        self._counterspelled = False
        self._mirrored = False
        self._shielded = False
        self._cold_resistant = False
        self._fire_resistant = False
        self._fireball_protected = False

        self._poisoned = False
        self._poison_countdown = 6
        self._diseased = False
        self._disease_countdown = 6

        self._spell_durations = {
            "Protection from Evil":0,
            }
        
        self._enchantment = ""
        self._enchantment_cancel = False
        self._expiring_enchantment = ""

        self._permanencies = []

        self._amnesiac = False

        self._invisible = False
        self._blinded = False
        
        self._charmer = None
        self._charmed_this_turn = False
        self._charmed = False

        self._confused = False

        self._afraid = False

        self._paralysis = False

        self._hasted = False
        self._hasted_duration = 3

        self._timestopped = False

    @property
    def paralysis(self):
        return self._paralysis

    @paralysis.setter
    def paralysis(self, bool):
        self._paralysis = bool

    @property
    def confused(self):
        return self._confused

    @confused.setter
    def confused(self, bool):
        self._confused = bool

    @property
    def timestopped(self):
        return self._timestopped

    @timestopped.setter
    def timestopped(self, bool):
        self._timestopped = bool

    @property
    def hasted(self):
        return self._hasted

    @hasted.setter
    def hasted(self, bool):
        self._hasted = bool

    @property
    def hasted_duration(self):
        return self._hasted_duration

    @hasted_duration.setter
    def hasted_duration(self, new_duration):
        self._hasted_duration = new_duration

    @property
    def afraid(self):
        return self._afraid

    @afraid.setter
    def afraid(self, bool):
        self._afraid = bool

    @property
    def charmed(self):
        return self._charmed

    @charmed.setter
    def charmed(self, bool):
        self._charmed = bool

    @property
    def charmed_this_turn(self):
        return self._charmed_this_turn

    @charmed_this_turn.setter
    def charmed_this_turn(self, bool):
        self._charmed_this_turn = bool

    @property
    def charmer(self):
        return self._charmer

    @charmer.setter
    def charmer(self, who):
        self._charmer = who

    @property
    def invisible(self):
        return self._invisible

    @invisible.setter
    def invisible(self, bool):
        self._invisible = bool

    @property
    def blinded(self):
        return self._blinded

    @blinded.setter
    def blinded(self, bool):
        self._blinded = bool

    @property
    def amnesiac(self):
        return self._amnesiac
    
    @amnesiac.setter
    def amnesiac(self, bool):
        self._amnesiac = bool

    @property
    def permanencies(self):
        return self._permanencies

    @permanencies.setter
    def permanencies(self, new_list):
        self._permanencies = new_list

    def add_permanency(self, target, spell_name):
        target.permanencies.append(spell_name)

    def remove_permanency(self, target, spell_name):

        if spell_name in target.permanencies:
            target.permanencies.remove(spell_name)

    @property
    def poison_countdown(self):
        return self._poison_countdown

    @poison_countdown.setter
    def poison_countdown(self, new_duration):
        self._poison_countdown = new_duration

    @property
    def disease_countdown(self):
        return self._disease_countdown

    @disease_countdown.setter
    def disease_countdown(self, new_duration):
        self._disease_countdown = new_duration

    @property
    def enchantment_cancel(self):
        return self._enchantment_cancel

    @enchantment_cancel.setter
    def enchantment_cancel(self, bool):
        self._enchantment_cancel = bool

    @property
    def enchantment(self):
        return self._enchantment

    @enchantment.setter
    def enchantment(self, enchantment_name):
        self._enchantment = enchantment_name

    def spell_has_active_duration(self, spell_name):

        if self.spell_durations[spell_name] > 0:
            return True
        else:
            return False

    def change_spell_duration(self, spell_name, new_duration):

        """ Set the duration of the spell to the new duration.
        """

        self._spell_durations[spell_name] = new_duration

    def get_spell_duration(self, spell_name):

        return self._spell_durations[spell_name]

    @property
    def spell_durations(self):
        return self._spell_durations

    @property
    def fireball_protected(self):
        return self._fireball_protected

    @fireball_protected.setter
    def fireball_protected(self, bool):
        self._fireball_protected = bool

    @property
    def poisoned(self):
        return self._poisoned

    @poisoned.setter
    def poisoned(self, bool):
        self._poisoned = bool

    @property
    def diseased(self):
        return self._diseased

    @diseased.setter
    def diseased(self, bool):
        self._diseased = bool

    @property
    def cold_resistant(self):
        return self._cold_resistant
    
    @cold_resistant.setter
    def cold_resistant(self, bool):
        self._cold_resistant = bool

    @property
    def fire_resistant(self):
        return self._fire_resistant

    @fire_resistant.setter
    def fire_resistant(self, bool):
        self._fire_resistant = bool

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color

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
    def maxhp(self):
        return self._maxhp

    def heal(self, value):
        if self.hp + value > self.maxhp:
            self.hp = self.maxhp
        else:
            self.hp = self.hp + value

    def take_damage(self, value):
        self.hp = self.hp - value

    @property
    def counterspelled(self):
        return self._counterspelled

    @counterspelled.setter
    def counterspelled(self, bool):
        self._counterspelled = bool

    @property
    def shielded(self):
        return self._shielded

    @shielded.setter
    def shielded(self, bool):
        self._shielded = bool

    @property
    def mirrored(self):
        return self._mirrored

    @mirrored.setter
    def mirrored(self, bool):
        self._mirrored = bool

    @property
    def killing_blow(self):
        return self._killing_blow

    @killing_blow.setter
    def killing_blow(self, value):
        self._killing_blow = value

    @classmethod
    @abstractmethod
    def end_turn(self):
        pass

    @classmethod
    @abstractmethod
    def remove_enchantments(self):
        pass

    @classmethod
    @abstractmethod
    def remove_enchantments_spellcast(self):
        pass

    @classmethod
    def clear_ephemeral_vars(self, targetable):
        
        targetable.counterspelled = False
        targetable.mirrored = False
        targetable.shielded = False
        targetable.fireball_protected = False
        targetable.enchantment_cancel = False
        targetable.charmed_this_turn = False