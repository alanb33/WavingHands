from random import randint

from hand import Hand
from spellbook_client import SpellbookClient
from spellbook import Spellbook
from targetable import Targetable

class Wizard(Targetable):

    # a wizard has two hands.
    # a wizard also has their own spellbook.

    def __init__(self, name="Merlin"):

        """ Create a wizard. Accepted argument is (string name). This is to
            speed up testing by skipping the customization phase by giving 
            distinct names to each Wizard object. """ 

        super().__init__()

        self._name = name
        self._maxhp = 14
        self._hp = self._maxhp

        self._color = "blue"
        self._left = Hand()
        self._right = Hand()
        self._spellbook = Spellbook('./spelllist.txt')
        self._spellbook_client = SpellbookClient(self._spellbook.spell_list)
        self._taunt = "I forgot what I was going to say."
        self._victory = "It looks like I win again."
        self._stabbed_this_turn = False
        self._already_stabbed = False
        self._duplicate_stab = False
        self._stab_victim = None
        self._surrendering = False

        self._c_hands = {}

        self._resurrecting = False
        self._killing_blow = "falls over dead."

        self._hand_spell = {"left":"", "right":""}

        self._confused = False
        self._confusion_hand = ""
        
        self._minions = []
        self._charmed_hand = ""
        self._charmed_gesture = ""
        self._charmed_stab_override = ""
        self._amnesia_stab_victim = None
        self._paralyzed_hand = ""
        self._paralysis_expiration = ""

        self._blinded = False
        self._blinded_duration = 3
        self._invisible = False
        self._invisible_duration = 3

        self._delayed_spell = None
        self._delayed_effect_primed = False
        self._delayed_effect_duration = 3
        self._releasing_delayed_spell = False

        self._permanency_primed = False
        self._permanency_duration = 3

        self._dagger_stolen = ""

        self._used_quick_lightning = False

        self._perceived_history = {}

        self._client = None

    @property
    def c_hands(self):
        return self._c_hands

    @c_hands.setter
    def c_hands(self, new_dict):
        self._c_hands = new_dict

    @property
    def spellbook_client(self):
        return self._spellbook_client

    @spellbook_client.setter
    def spellbook_client(self, spellbook_client):
        self._spellbook_client = spellbook_client

    @property
    def victory(self):
        return self._victory

    @victory.setter
    def victory(self, victory_line):
        self._victory = victory_line

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, socket):
        self._client = socket

    @property
    def confused(self):
        return self._confused

    @confused.setter
    def confused(self, bool):
        self._confused = bool

    @property
    def permanency_primed(self):
        return self._permanency_primed

    @permanency_primed.setter
    def permanency_primed(self, bool):
        self._permanency_primed = bool

    @property
    def permanency_duration(self):
        return self._permanency_duration

    @permanency_duration.setter
    def permanency_duration(self, integer):
        self._permanency_duration = integer

    def get_delayed_spell(self):

        """ Returns the delayed spell if it exists, else return None. """

        if self.delayed_spell:
            return self.delayed_spell[2]
        else:
            return None

    def ask_to_release(self):

        if self.delayed_spell:
            actual_spell = self.delayed_spell[2]
            while True:
                choice = input("Do you want to release " + actual_spell.name + " this turn? (y/n) ")
                if choice.lower() == "y":
                    return True
                elif choice.lower() == "n":
                    return False
                else:
                    print("Your choice is invalid.")

    @property
    def releasing_delayed_spell(self):
        return self._releasing_delayed_spell

    @releasing_delayed_spell.setter
    def releasing_delayed_spell(self, bool):
        self._releasing_delayed_spell = bool

    @property
    def delayed_spell(self):
        return self._delayed_spell

    @delayed_spell.setter
    def delayed_spell(self, spell):
        self._delayed_spell = spell

    @property
    def delayed_effect_primed(self):
        return self._delayed_effect_primed

    @delayed_effect_primed.setter
    def delayed_effect_primed(self, bool):
        self._delayed_effect_primed = bool

    @property
    def delayed_effect_duration(self):
        return self._delayed_effect_duration

    @delayed_effect_duration.setter
    def delayed_effect_duration(self, new_duration):
        self._delayed_effect_duration = new_duration

    @property
    def invisible_duration(self):
        return self._invisible_duration

    @invisible_duration.setter
    def invisible_duration(self, new_duration):
        self._invisible_duration = new_duration

    def add_broadcasted_gesture(self, other_wizard):

        """ Add 'known' gesture history of the other_wizard.
        Replace gestures with ? if this wizard is blind or other_wizard is
        invisible.
        
        This is the only link between different wizards.
        """

        # First, create an entry for the other wizard if it does not already exist.

        if other_wizard.name not in self.perceived_history:
            # The name is not here. Create one.
            self.perceived_history[other_wizard.name] = {"left":"", "right":""}

        # Next, get the broadcasted gestures, and determine if we add them to our own.

        hands = ("left", "right")

        for hand in hands:
            hand_history = other_wizard.get_latest_gesture(hand)
            if hand_history.lower() != "s" and hand_history != "C":
                if self.blinded or other_wizard.invisible:
                    hand_history = "?"
            
            enemy_history = self.perceived_history[other_wizard.name][hand]

            # Finally, add the character to the end of the history string.
            if len(enemy_history) == 8:
                new_history = []
                for i in range(1, len(enemy_history)):
                    new_history.append(enemy_history[i])
                new_history.append(hand_history)
                new_history = "".join(new_history)

                self.perceived_history[other_wizard.name][hand] = new_history
            else:
                self.perceived_history[other_wizard.name][hand] += hand_history

    def erase_perceived_history(self, other_wizard):

        """ Erase the perceived history of the other wizard. """

        if other_wizard.name in self.perceived_history:
            self.perceived_history[other_wizard.name] = {"left":"", "right":""}

    def show_perceived_history(self, other_wizard):

        """ Print the perceived history of the enemy wizard. """

        pass

    @property
    def blinded_duration(self):
        return self._blinded_duration

    @blinded_duration.setter
    def blinded_duration(self, turns):
        self._blinded_duration = turns

    @property
    def perceived_history(self):
        return self._perceived_history

    @property
    def paralysis_expiration(self):
        return self._paralysis_expiration

    @paralysis_expiration.setter
    def paralysis_expiration(self, hand):
        self._paralysis_expiration = hand

    @property
    def paralyzed_hand(self):
        return self._paralyzed_hand

    @paralyzed_hand.setter
    def paralyzed_hand(self, hand):
        self._paralyzed_hand = hand

    @property
    def charmed_stab_override(self):
        return self._charmed_stab_override

    @charmed_stab_override.setter
    def charmed_stab_override(self, target):
        self._charmed_stab_override = target

    @property
    def amnesia_stab_victim(self):
        return self._amnesia_stab_victim

    @amnesia_stab_victim.setter
    def amnesia_stab_victim(self, target):
        self._amnesia_stab_victim = target

    @property
    def stab_victim(self):
        return self._stab_victim

    @stab_victim.setter
    def stab_victim(self, target):
        self._stab_victim = target

    @property
    def dagger_stolen(self):
        return self._dagger_stolen

    @dagger_stolen.setter
    def dagger_stolen(self, hand):
        self._dagger_stolen = hand

    def clear_enchantment(self, enchantment):

        if enchantment == "Confusion":
            self.confused = False
            self.confusion_hand = ""
            self.enchantment = ""
        
        if enchantment == "Amnesia":
            #self.amnesia_stab_victim = None    # Don't clear this... we can re-use it for amnesia permanency.
            self.amnesiac = False

        if enchantment == "Charm Person":
            #self.charmer = None
            self.charmed = False
            self.charmed_hand = ""
            self.charmed_gesture = ""
            if "Charm Person" not in self.permanencies:
                self.charmed_stab_override = None

        if enchantment == "Charm Monster":
            self.enchantment = ""

        if enchantment == "Paralysis":
            self.paralysis = False
            self.paralyzed_hand = ""
            self.paralysis_expiration = ""
            self.enchantment = ""

        if enchantment == "Fear":
            self.afraid = False
            self.enchantment = ""

        if enchantment == "Haste":
            self.hasted = False
            self.hasted_duration = 3

        if enchantment == "Permanency":
            self.permanency_primed = False
            self.permanency_duration = 3
            self.permanencies = []
            if self.charmer:
                self.charmer = None

    @property
    def charmed_hand(self):
        return self._charmed_hand

    @charmed_hand.setter
    def charmed_hand(self, hand):
        self._charmed_hand = hand

    @property
    def charmed_gesture(self):
        return self._charmed_gesture

    @charmed_gesture.setter
    def charmed_gesture(self, gesture):
        self._charmed_gesture = gesture

    @property
    def confusion_hand(self):
        return self._confusion_hand

    @confusion_hand.setter
    def confusion_hand(self, hand):
        self._confusion_hand = hand

    @property
    def used_quick_lightning(self):
        return self._used_quick_lightning

    @used_quick_lightning.setter
    def used_quick_lightning(self, bool):
        self._used_quick_lightning = bool

    @property
    def duplicate_stab(self):
        return self._duplicate_stab

    @duplicate_stab.setter
    def duplicate_stab(self, bool):
        self._duplicate_stab = bool

    @property
    def already_stabbed(self):
        return self._already_stabbed

    @already_stabbed.setter
    def already_stabbed(self, bool):
        self._already_stabbed = bool

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
    def minions(self):
        return self._minions

    def add_minion(self, minion):
        """ (Minion minion)
            Add a Minion under the Wizard's command.
        """

        self.rename_minion_if_duplicate(minion, self.minions)
        minion.master = self
        self.minions.append(minion)

    def remove_minion(self, minion):
        """ Remove a minion under the Wizard's command. """

        self.minions.remove(minion)

    def rename_minion_if_duplicate(self, minion_to_rename, minion_list):

        """ To avoid confusion, append a letter to the end of the minion's
            name if a minion with the same name already exists.

            If Groble exists, then a new Groble should be given Groble B as a
            name.
        """
        
        alphabet = ("BCDEFGHIJKLMNOPQRSTUVWXYZ")

        """
            Groble
            Groble B

            while Groble == Groble:
                Groble = Groble B
                if Groble == Groble B (false)
                alpha_index remains 0

            while Groble B == Groble B:
                Groble B = Groble B
                if Groble B == Groble B (true)
                alpha_index becomes 1

            while Groble B == Groble B:
                Groble B = Groble C
                if 

            Groble B == Groble? False
            break!
        """

        original_name = minion_to_rename.name
        potential_name = minion_to_rename.name
        alpha_index = 0

        for minion in minion_list:
            while minion.name == potential_name:
                potential_name = original_name + " " + alphabet[alpha_index]
                if minion.name == potential_name:
                    alpha_index = alpha_index + 1

        minion_to_rename.name = potential_name
        
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
        #self.amnesia_stab_victim = None    # Not cleared due to re-use with amnesia permanency.
        self.amnesiac = False
        
        # Confusion
        self.confused = False
        self.confusion_hand = ""
        
        # Charm Person
        self.clear_enchantment("Charm Person")

        # Charm Monster (has no effect)

        # Fear is handled by self.enchantment for wizards

        # Paralysis
        self.clear_enchantment("Paralysis")


        # Anti-spell is not handled here.

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
        self.blinded = False
        self.blinded_duration = 3

        # Invisibility
        self.invisible = False
        self.invisible_duration = 3

        # Haste
        self.clear_enchantment("Haste")

        # Time Stopped
        # Cannot be handled

        # Delayed Effect
        self.delayed_effect_primed = False
        self.delayed_effect_duration = 3
        self.delayed_spell = None
        self.releasing_delayed_spell = False

        # Permanency
        self.clear_enchantment("Permanency")

    def remove_enchantments(self):
        
        self.enchantment = ""

    @property
    def hand_spell(self):
        return self._hand_spell

    def set_hand_spell(self, hand, spell_line):
        self.hand_spell[hand] = spell_line

    def end_turn(self):

        self.already_stabbed = False
        self.stabbed_this_turn = False
        self.stab_victim = False
        self.duplicate_stab = False
        self.paralysis_expiration = ""

        for hand in ("left", "right"):
            self.set_hand_spell(hand, "")

        if self.enchantment == "Charm Monster":
            self.enchantment = ""

        self.confusion_hand = ""
        self.dagger_stolen = ""
        self.clear_ephemeral_vars(self)

    def death_throes(self):
        return self._name + " " + self._killing_blow

    @property
    def resurrecting(self):
        return self._resurrecting

    @resurrecting.setter
    def resurrecting(self, bool):
        self._resurrecting = bool

    @property
    def surrendering(self):
        return self._surrendering

    def get_latest_gesture(self, hand):
        if hand.lower() in ("left", "right"):
            return self.get_hand(hand).history[-1:]
        else:
            raise AttributeError("Received request for invalid hand: " + str(hand))

    @surrendering.setter
    def surrendering(self, bool):
        self._surrendering = bool

    def customize(self):

        while True:
            name = input("What is your name?\n")
            if name != "":
                self._name = name
                break

        while True:
            color = input("What is your color of your robes?\n")
            if color != "":
                self._color = color
                break
        
        while True:
            taunt = input("What will you say at the start of the fight? (include punctuation)\n")
            if taunt != "":
                self._taunt = taunt
                break

        while True:
            victory = input("What will you say at your inevitable victory? (include punctuation)\n")
            if victory != "":
                self._victory = victory
                break

    def introduce(self):
        print("A wizard in " + self.color + " robes steps forward.")
        print("\"I am " + self.name + ". " + self.taunt + "\"")

    def win(self):

        return self.name + " triumphantly declares, \"" + self.victory + "\""

    def die(self):

        return "With their dying gasp, " + self.name + " rasps, \"" + self.victory + "\""

    def defeat(self):
        
        return self.name + " kicks up some dirt and mumbles, \"" + self.victory + "\""

    def show_hands_history(self):

        hands = ("left", "right")
        for hand in hands:
            print("Your " + hand + " hand history: " + self.get_hand(hand).show_history())

    def get_history_width(self):

        history_width = len("Your right hand history: ")
        if self.perceived_history:
            for other_wizard in self.perceived_history:
                other_width = len(other_wizard + "\'s right hand history: ")
                if other_width > history_width:
                    history_width = other_width

        return history_width

    def show_hands_history_others(self):

        prehistory_len = self.get_history_width()

        your_hands = ("left", "right")
        for hand in your_hands:
            prehistory_line = "Your " + hand + " hand history: "
            print("{0:{width}} {1}".format(prehistory_line, self.get_hand(hand).show_history(), width = prehistory_len))

        if self.perceived_history:
            for other_wizard in self.perceived_history:
                print("")
                other_hands = ("left", "right")
                for hand in other_hands:
                    prehistory_line = other_wizard + "\'s " + hand + " hand history: "
                    print("{0:{width}} {1}".format(prehistory_line, self.perceived_history[other_wizard][hand], width = prehistory_len))

    def erase_history(self):
        hands = ("left", "right")
        for hand in hands:
            self.get_hand(hand).erase_history()

    def get_gestures(self):

        # get the gestures of the wizard.
        try:
            confusion_gesture = ""

            if self.confused:
                # Which hand will be confused? 0 for left, 1 for right
                hands = ("left", "right")
                rand_hand = randint(0, len(hands)-1)
                self.confusion_hand = hands[rand_hand]

                # What will the gesture be replaced with?
                # 1=C, 2=D, 3=F, 4=P, 5=S, 6=W

                r_gestures = ("c", "d", "f", "p", "s", "w")
                rand_gesture = randint(0, len(r_gestures)-1)
                confusion_gesture = r_gestures[rand_gesture]
            """
            valid_gestures = ["f", "p", "s", "w", "d", "c", "h", "?", "@", "$"]
            fear_gestures = ("c", "d", "f", "s")
            """

            hands = ("left", "right")
            #hand_i = 0
            hand_dict = {"left":"", "right":""}

            for hand in hands:
                hand_dict[hand] = self.c_hands[hand]

            """
            print("")

            print(self.name.upper())
            print("Your HP: " + str(self.hp))
            #self.show_hands_history()
            self.show_hands_history_others()

            print("")

            while True:
                line_end = ""

                if hands[hand_i] == "left":
                    line_end = "  "
                else:
                    line_end = " "

                # hacky way to format

                gestures = input(self.name + ": Enter a " + hands[hand_i] + " hand gesture (send ? for help):" + line_end)
                gestures = gestures.lower()
                if len(gestures) > 1 and gestures[0] != "@":
                    print("Gesture input too long.")
                elif len(gestures) > 1 and gestures[0] == "@":
                    self.show_spell_desc(gestures[1:])
                else:
                    if gestures in valid_gestures:
                        if gestures == "?":
                            self.print_help()
                        elif gestures == "@":
                            self.list_spells()
                        elif gestures == "h":
                            self.show_hands_history()
                        elif gestures == "%":
                            print(self.name + "\'s HP: " + str(self.hp))
                        else:
                            if gestures in fear_gestures and self.afraid:
                                print("You are too fearful to perform that gesture!")
                            else:
                                # actual recordable gestures now
                                # don't add gestures to history until we have both.
                                # this is so we can capitalize gestures to represent 'both hands'
                                if gestures == "$" and self.duplicate_stab:
                                    print("You have only one dagger to stab with!")
                                else:
                                    if gestures == "$":
                                        self.duplicate_stab = True
                                    hand_dict[hands[hand_i]] = gestures
                                    hand_i = hand_i + 1
                                    if hand_i > 1:
                                        break

                    else:
                        print("You've given an invalid gesture.")
            """

            if self.charmed_hand:
                hand_dict[self.charmed_hand] = self.charmed_gesture
                if self.charmed_gesture == "$":
                    opposite_hand = ""
                    if self.charmed_hand == "left":
                        opposite_hand = "right"
                    else:
                        opposite_hand = "left"
                    if hand_dict[opposite_hand] == "$":
                        self.dagger_stolen = opposite_hand
                        hand_dict[opposite_hand] == " "
                    self.stabbed_this_turn = True

            if self.paralyzed_hand:
                # C/S/W becomes F/D/P, otherwise stays the same
                last_turn_gesture = self.get_hand(self.paralyzed_hand).get_latest_gesture()
                new_gesture = last_turn_gesture
                if last_turn_gesture.lower() == "c":
                    new_gesture = "f"
                elif last_turn_gesture.lower() == "s":
                    new_gesture = "d"
                elif last_turn_gesture.lower() == "w":
                    new_gesture = "p"
                hand_dict[self.paralyzed_hand] = new_gesture
                self.paralysis_expiration = self.paralyzed_hand
                self.paralyzed_hand = ""

            if self.confusion_hand:
                hand_dict[self.confusion_hand] = confusion_gesture

            if self.amnesiac:
                # Repeat the previous turn's gestures.
                last_turn_left = self.get_hand("left").get_latest_gesture()
                last_turn_right = self.get_hand("right").get_latest_gesture()
                if last_turn_left == "$" or last_turn_right == "$":
                    self.stabbed_this_turn = True
                self.get_hand("left").add_gesture(last_turn_left)
                self.get_hand("right").add_gesture(last_turn_right)
            else:
                if hand_dict["left"] == "$" or hand_dict["right"] == "$":
                    self.stabbed_this_turn = True
                if hand_dict["left"] == hand_dict["right"]:
                    # if they are the same gesture
                    self.get_hand("left").add_gesture(hand_dict["left"].upper())
                    self.get_hand("right").add_gesture(hand_dict["right"].upper())
                else:
                    self.get_hand("left").add_gesture(hand_dict["left"])
                    self.get_hand("right").add_gesture(hand_dict["right"])
                print(self.name + " left:  " + hand_dict["left"])
                print(self.name + " right: " + hand_dict["right"])                
        except KeyboardInterrupt:
            raise KeyboardInterrupt("catch these hands aron lamo")

    def show_spell_desc(self, spell_number):
        self.spellbook.show_spell_desc(spell_number)

    def print_help(self):
        print("\nWaving Hands is played by two wizards making " +
            "arcane gestures at each other.\n" +
            "The valid gestures are: \n" +
            "\nF: The wiggled fingers" +
            "\nP: The proffered palm" + 
            "\nS: The snap of the fingers" +
            "\nW: The wave of the hand" +
            "\nD: The pointing digit" +
            "\nC: The clapping of the hands" +
            "\n\n$: The stab of the dagger" +
            "\n@: Consult your spellbook" +
            "\n@#: See spell description" +
            "\nH: See your previous gestures" +
            "\nR: Cancel your current gestures and repeat" +
            "\n%: See your HP" +
            "\n\nTo surrender, proffer both palms.")

    @property
    def stabbed_this_turn(self):
        return self._stabbed_this_turn

    @stabbed_this_turn.setter
    def stabbed_this_turn(self, value):
        self._stabbed_this_turn = value

    @property
    def taunt(self):
        return self._taunt

    @taunt.setter
    def taunt(self, value):
        self._taunt = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def spellbook(self):
        return self._spellbook

    def get_hand(self, hand):
        if hand == "left":
            return self._left
        elif hand == "right":
            return self._right
        else:
            raise("Tried to retrieve invalid hand \'" + hand + "\' from \'" + self.name + "\'")

    def list_spells(self):
        self._spellbook.list_spells()