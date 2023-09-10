from spell import Spell

class SpellbookClient:

    # The client version of Spellbook doesn't include any of the management functions.

    def __init__(self, spell_list):
        self._spell_list = spell_list

    def show_spell_desc(self, index):
        try:
            index = int(index)
            if index-1 > len(self.spell_list)-1 or index <= 0:
                print("That spell is not in your spellbook!")
            else:
                print(self._spell_list[index-1].desc)
        except ValueError:
            print("That spell is not in your spellbook!")

    def list_spells(self):

        header_line = "##. {:<30} {:<30}".format("Spell name", "Gestures required")
        print(header_line)
        print("-"*len(header_line))
        for i,spell in enumerate(self._spell_list, 1):
            print("{:>2}. {:<30} {:<30}".format(str(i), spell.name, spell.gesture))

    @property
    def spell_list(self):
        return self._spell_list