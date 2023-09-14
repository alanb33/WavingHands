# a spellbook contains spells.
# the spellbook is responsible for spell lookup.

import operator
from waving_hands.spell import Spell

class Spellbook:

    # the _spell_list will be populated by a list of Spell objects.

    def __init__(self, path_to_spellbook):
        self.spell_list = []
        self._path_to_spellbook = path_to_spellbook
        self.populate()

    @property
    def spell_list(self):
        return self._spell_list

    @spell_list.setter
    def spell_list(self, new_list):
        self._spell_list = new_list

    def populate(self):
        # the spellbook will create Spell() objects from the contents of the
        # given path_to_spellbook file.

        

        try:
            spell_list_f = []
            with open(self._path_to_spellbook) as f:
                spell_list_f = f.read().splitlines()

            # find lines that start with spell=
            for line in spell_list_f:
                if line.startswith("spell="):
                    gestureline = spell_list_f.index(line) + 1
                    error = "Could not find gesture line"
                    if spell_list_f[gestureline].startswith("gesture="):
                        descline = gestureline + 1
                        error = "Could not find desc line"
                        if spell_list_f[descline].startswith("desc="):
                            killline = descline + 1
                            error = "Could not find kill line"
                            if spell_list_f[killline].startswith("kill="):
                                spellname = spell_list_f[spell_list_f.index(line)][len("spell="):]
                                gesture = spell_list_f[gestureline][len("gesture="):]
                                desc = spell_list_f[descline][len("desc="):]
                                kill = spell_list_f[killline][len("kill="):]
                                valid = self.validate_gesture(gesture)
                                if valid:
                                    self.add_spell(spellname, gesture, desc, kill)
                                else:
                                    print("Malformed spell at line " + str(gestureline) + ": " + spellname)
                                    raise ValueError("Malformed spell -- see above traceback")
                            else:
                                raise ValueError("Malformed spell at line " + 
                                    str(spell_list_f.index(line)+1) + ": " + error)

        except FileNotFoundError:
            raise FileNotFoundError("Failed to populate spellbook: Could not find path \'" + str(self._path_to_spellbook) + "\'")

        self.sort_spells()

    def add_spell(self, spell_name, spell_gesture, spell_desc, spell_kill):
        new_spell = Spell(spell_name, spell_gesture, spell_desc, spell_kill)

        spells_with_time = {"Shield":1}

        if new_spell.name in spells_with_time:
            new_spell.has_time = True
            new_spell.time_remaining = spells_with_time[new_spell.name]

        self.spell_list.append(new_spell)

    def sort_spells(self):
        self.spell_list.sort(key=operator.attrgetter('name'))

    def validate_gesture(self, gesture):
        valid_gestures = ["f", "p", "s", "w", "d", "c"]

        # examine the gesture digit-by-digit

        for character in gesture:
            if character.lower() not in valid_gestures:
                print("Invalid gesture: " + character)
                return False

        return True

    def show_spell_desc_by_name(self, spell_name):

        for spell in self.spell_list:
            if spell.name == spell_name:
                return "\n" + spell.name.upper() + "\n\n" + spell.desc + "\n"
    
        return "\nThat spell is not in your spellbook!\n"

    def search_by_gesture_length(self, history, length):

        if history == "Nothing yet.":
            print("\nYou have no gesture history yet.")
        else:
            if len(history) < length:
                print("\nYour gesture history is too short -- you do not have " + str(length) + " gestures to search by.")
            else:
                search_key = history[-length:]
                # Run through the search key and lower() everything but C
                lowered_search_key = []
                for character in search_key:
                    new_char = character
                    if new_char != "C":
                        new_char = new_char.lower()
                    lowered_search_key.append(new_char)
                    search_key = "".join(lowered_search_key)

                matching_spells = []
                for spell in self.spell_list:
                    if len(spell.gesture) > length:
                        key_gestures = spell.gesture[:length]
                        if key_gestures == search_key:
                            matching_spells.append(spell)

                if matching_spells:
                    longest_name = 0
                    for spell in matching_spells:
                        if len(spell.name) > longest_name:
                            longest_name = len(spell.name)

                    print("\nSpells that can be cast with the given gestures [" + search_key + "]:\n")
                    for spell in matching_spells:
                        print("{0:{width}} {1}".format(spell.name, spell.gesture, width = longest_name))

                else:
                    print("\nNo spells can be made with the given gestures [" + search_key + "].")
            
        print("")

    def show_spell_desc_gesture_sort(self, index):
        
        by_gesture = self.spell_list.copy()
        by_gesture.sort(key=operator.attrgetter('gesture'))
        
        try:
            index = int(index)
            if index-1 > len(by_gesture)-1 or index <= 0:
                return "\nThat spell is not in your spellbook!\n"
            else:
                return "\n\n" + by_gesture[index-1].name.upper() + "\n\n" + by_gesture[index-1].desc + "\n"
        except ValueError:
            return "\nThat spell is not in your spellbook!\n"

    def show_spell_desc(self, index):
        try:
            index = int(index)
            if index-1 > len(self.spell_list)-1 or index <= 0:
                return "\nThat spell is not in your spellbook!\n"
            else:
                return "\n\n" + self.spell_list[index-1].name.upper() + "\n\n" + self.spell_list[index-1].desc + "\n"
        except ValueError:
            return "\nThat spell is not in your spellbook!\n"

    def print_spell_header(self):

        header_line = "##. {:<30} {:<30}".format("Spell name", "Gestures required")
        print(header_line)
        print("-"*len(header_line))

    def list_spells(self):


        self.print_spell_header()

        for i,spell in enumerate(self.spell_list, 1):
            print("{:>2}. {:<30} {:<30}".format(str(i), spell.name, spell.gesture))

        print("\n")

    def list_spells_by_gesture(self):

        self.print_spell_header()

        by_gestures = self.spell_list.copy()
        by_gestures.sort(key=operator.attrgetter('gesture'))

        for i,spell in enumerate(by_gestures, 1):
            print("{:>2}. {:<30} {:<30}".format(str(i), spell.name, spell.gesture))

        print("\n")