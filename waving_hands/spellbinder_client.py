from random import randint

import curses
import os
import pickle
import select
import socket
import sys
import time

from spellbook import Spellbook
from targetable_client import TargetableClient

class SpellbinderClient:

    def __init__(self):

        self._server = None

        self._HOST      = "192.168.1.1"
        self._PORT      = 12345
        self._HOST_ADDR = (self._HOST, self._PORT)
        self._ENC       = "utf-8"
        self._BUFFSIZE  = 1024

        self._screen    = None
        self._MAX_WIDTH = 79

        self._hasted    = False
        self._blind     = False
        self._timestopped = False
        self._enemy_hp  = 14
        self._hp        = 14
        self._name      = "Merlin"

        self._spellbook = Spellbook('./spelllist.txt')
        self._hands     = {}
        self._perceived_history = {}
        self._monsters  = {}
        self._autospell = False

        self._debug      = False
        self._sleep_time = 0.8

        self._haste_turn_two = False

        self._enchantments = []
        self._charmed_hand = ""
        self._paralyzed_hand = ""

    @property
    def autospell(self):
        return self._autospell

    @autospell.setter
    def autospell(self, bool):
        self._autospell = bool

    @property
    def charmed_hand(self):
        return self._charmed_hand

    @charmed_hand.setter
    def charmed_hand(self, hand):
        self._charmed_hand = hand

    @property
    def debug(self):
        return self._debug

    @property
    def enchantments(self):
        return self._enchantments

    @property
    def enemy_hp(self):
        return self._enemy_hp

    @enemy_hp.setter
    def enemy_hp(self, new_hp):
        self._enemy_hp = new_hp

    @property
    def hands(self):
        return self._hands

    @hands.setter
    def hands(self, new_dict):
        self._hands = new_dict

    @property
    def haste_turn_two(self):
        return self._haste_turn_two

    @haste_turn_two.setter
    def haste_turn_two(self, bool):
        self._haste_turn_two = bool

    @property
    def hasted(self):
        return self._hasted

    @hasted.setter
    def hasted(self, bool):
        self._hasted = bool

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, new_hp):
        self._hp = new_hp

    @property
    def monsters(self):
        return self._monsters

    @monsters.setter
    def monsters(self, new_dict):
        self._monsters = new_dict

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def paralyzed_hand(self):
        return self._paralyzed_hand

    @paralyzed_hand.setter
    def paralyzed_hand(self, hand):
        self._paralyzed_hand = hand

    @property
    def perceived_history(self):
        return self._perceived_history

    @perceived_history.setter
    def perceived_history(self, new_dict):
        self._perceived_history = new_dict

    @property
    def screen(self):
        return self._screen

    @screen.setter
    def screen(self, new_screen):
        self._screen = new_screen

    @property
    def server(self):
        return self._server

    @server.setter
    def server(self, socket):
        self._server = socket

    @property
    def sleep_time(self):
        return self._sleep_time

    @property
    def spellbook(self):
        return self._spellbook

    @spellbook.setter
    def spellbook(self, spellbook):
        self._spellbook = spellbook

    @property
    def timestopped(self):
        return self._timestopped

    @timestopped.setter
    def timestopped(self, bool):
        self._timestopped = bool

    def connection_loop(self):

        running = True

        while running:

            rlist, wlist, elist = select.select( [self.server], [], [] )

            for source in rlist:

                if source == self.server:
                    
                    command = self.recv()

                    if self.response(command, "Server died during generic connection loop."):

                        command = self.dec(command)

                        if command == "MSG":
                            self.dmsg("Received MSG request")
                            self.receive_msg()
                        elif command == "COMMAND_MONSTER":
                            self.command_monster()
                        elif command == "CUSTOMIZE":
                            self.customization()
                        elif command == "DELAYED_SPELL_RELEASE_QUERY":
                            self.delayed_spell_release_query()
                        elif command == "DELAYED_SPELL_STORE_QUERY":
                            self.delayed_spell_store_query()
                        elif command == "ENCHANTMENT_CHARM_PERSON":
                            self.choose_charm_person_info()
                        elif command == "ENCHANTMENT_PARALYSIS":
                            self.choose_paralysis_target()
                        elif command == "GET_GESTURES":
                            self.get_gestures()
                        elif command == "GET_PERMANENT":
                            self.get_permanency()
                        elif command == "GET_TARGET":
                            self.get_target()
                        elif command == "MULTIPLE_SPELLS":
                            self.choose_spell()
                        elif command == "OFFER_PERMANENCY":
                            self.offer_permanency()
                        elif command == "PREGAME":
                            self.pregame()
                        elif command == "PRINT_FLAVOR":
                            self.round_end()
                        elif command == "RAISE_DEAD":
                            self.raise_dead()
                        elif command == "SUMMON_ELEMENTAL":
                            self.summon_elemental()

    def show_monsters(self):

        if self.monsters:

            print("\nMonsters on the field:\n")

            for monster in self.monsters:
                self.print_t(monster + ", " + self.monsters[monster] + "\'s minion")

    def get_permanency(self):

        self.send("GET_PERMANENT_ACK")
        permanencies = self.recv()
        if self.response(permanencies, "Server died before sending pickled permanencies."):
            permanencies = self.depickle(permanencies)

            self.clear_screen()

            self.print_t("Spells are being cast on this turn that can be made permanent.")
            self.print_t("Choose a spell to make permanent or send N for none.")
            
            for i,spell_name in enumerate(permanencies, 1):
                self.print_t(str(i) + ". " + spell_name)

            while True:
                choice = input("Choose a spell to make permanent (N for none): ")
                if choice.lower() == "n":
                    choice = "none"
                    break
                else:
                    try:
                        choice = int(choice) - 1
                        if choice >= 0 and choice < len(permanencies):
                            choice = permanencies[choice]
                            break
                        else:
                            self.print_t("Your choice is invalid.")
                    except ValueError:
                        self.print_t("Your choice is invalid.")

            self.send_p(self.pickle(choice))

            self.wait_msg()


    def offer_permanency(self):

        self.send("OFFER_PERMANENCY_ACK")
        spell_name = self.recv()
        if self.response(spell_name, "Server died before sending Permanency spell name."):
            spell_name = self.dec(spell_name)

            while True:
                choice = input("Do you want to make the effects of " + spell_name + " permanent? (y/n) ")
                if choice.lower() == "y":
                    choice = True
                    break
                elif choice.lower() == "n":
                    choice = False
                    break
                else:
                    self.print_t("Your choice is invalid.")

            self.send_p(self.pickle(choice))

            self.wait_msg()

    def delayed_spell_store_query(self):

        self.send("DELAYED_SPELL_STORE_QUERY_ACK", True)
        data_p = self.recv()
        if self.response(data_p, "Server died while sending pickled delayed spell storage info to client."):
            delayable_names = self.depickle(data_p)

            self.clear_screen()

            self.print_t("Spells are being cast on this turn that can be delayed.")
            self.print_t("Choose a spell to delay or send N or press enter for none.\n")
            
            for i,spell_name in enumerate(delayable_names, 1):
                self.print_t(str(i) + ". " + spell_name)

            spell = "none"

            while True:
                choice = input("\nChoose a spell to delay (N or enter for none): ")
                if choice.lower() == "n" or choice.lower() == "":
                    break
                else:
                    try:
                        choice = int(choice) - 1
                        if choice >= 0 and choice < len(delayable_names):
                            spell = delayable_names[choice]
                            break
                        else:
                            self.print_t("Your choice is invalid.")
                    except ValueError:
                        self.print_t("Your choice is invalid.")

            self.wait_msg()
            self.send(spell)

    def delayed_spell_release_query(self):

        self.send("DELAYED_SPELL_RELEASE_QUERY_ACK", True)
        data_p = self.recv()
        if self.response(data_p, "Server died while sending pickled delayed spell release info to client."):
            delayed_spell_name = self.depickle(data_p)

            while True:

                self.clear_screen()

                choice = input("Do you want to release " + delayed_spell_name + " this turn? (y/n) ")
                if choice.lower() == "y":
                    choice = True
                    break
                elif choice.lower() == "n":
                    choice = False
                    break
                else:
                    self.print_t("Your choice is invalid.")

            self.wait_msg()
            self.send_p(self.pickle(choice))

    def wait_msg(self):

        """Prints out 'Waiting for challenger...'"""

        self.print_t("Waiting for challenger...")

    def choose_charm_person_info(self):

        self.send("CHARM_PERSON_ACK")
        self.print_t("Send CHARM_PERSON_ACK to server.")
        enemy_name = self.recv()
        if self.response(enemy_name, "Server died while client waited for charm person enemy name."):
            enemy_name = self.dec(enemy_name)
            self.print_t("Decoded enemy name for Charm Person.")

            self.clear_screen()

            self.print_t(self.name + ": Choose which of " + enemy_name + "\'s hands will be controlled.")
            
            self.show_hands_history_others()

            hands = ("Left", "Right")

            for i,hand in enumerate(hands, 1):
                self.print_t(str(i) + ". " + hand)

            charmed_hand = ""
            charmed_gesture = ""

            while True:
                try:
                    choice = int(input("Choose a hand (by number): "))
                    if choice == 1:
                        charmed_hand = "Left"
                        break
                    elif choice == 2:
                        charmed_hand = "Right"
                        break
                    else:
                        self.print_t("Your choice is invalid.")
                except ValueError:
                    self.print_t("Your choice is invalid.")

            self.clear_screen()

            self.print_t(self.name + ": Enter a gesture for " + enemy_name + "\'s " + charmed_hand.lower() + " hand.")

            self.show_hands_history_others()

            valid_gestures = ("f", "p", "s", "w", "d", "c", "$")

            while True:
                choice = input("Choose a gesture (f/p/s/w/d/c/$): ")
                if choice.lower() in valid_gestures:
                    charmed_gesture = choice
                    break
                else:
                    self.print_t("Your choice is invalid.")

            data_p = (charmed_hand, charmed_gesture)
            self.send_p(self.pickle(data_p))
            self.print_t("Sent pickled charm person info to server.")

    def summon_elemental(self):

        self.send("SUMMON_ACK")
        self.print_t("Sent SUMMON_ACK to server, waiting on response")

        if self.response(self.recv(), "Server died while client was waiting for response to SUMMON_ACK."):

            self.clear_screen()

            self.print_t(self.name + ": What type of elemental will you summon?\n")

            hands = ("Fire Elemental", "Ice Elemental")

            for i,hand in enumerate(hands, 1):
                self.print_t(str(i) + ". " + hand)

            choice = 0

            while True:
                try:
                    choice = int(input("\nChoose a type (by number): "))
                    if choice > 0 and choice < 3:
                        break
                    else:
                        self.print_t("Your choice is invalid.")
                except ValueError:
                    self.print_t("Your choice is invalid.")

            self.print_t("Sending choice " + str(choice) + " to server.")
            self.send(str(choice))

    def choose_paralysis_target(self):

        self.send("PARALYSIS_ACK")
        self.print_t("Sent PARALYSIS_ACK to server, waiting on pickled data")
        target_name = self.recv()

        if self.response(target_name, "Server died while client was waiting for pickled paralysis data."):
            target_name = self.depickle(target_name)

            self.clear_screen()

            self.print_t(self.name + ": Choose which of " + target_name + "\'s hands will be paralyzed.\n")

            self.show_hands_history_others()

            hands = ("Left", "Right")

            for i,hand in enumerate(hands, 1):
                self.print_t(str(i) + ". " + hand)

            choice = 0

            while True:
                try:
                    choice = int(input("\nChoose a hand (by number): "))
                    if choice > 0 and choice < 3:
                        break
                    else:
                        self.print_t("Your choice is invalid.")
                except ValueError:
                    self.print_t("Your choice is invalid.")

            self.send(str(choice))

    def pregame(self):

        """ Receive a pregame flavor list and iterate through it. """

        self.send("PREGAME_ACK")
        pregame_flavor = self.recv()

        if self.response(pregame_flavor, "Server died while sending pickled pregame flavor list."):
            pregame_flavor = self.depickle(pregame_flavor)

            self.send("PREGAME_COMPLETE")

            self.clear_screen()

            for line in pregame_flavor:
                self.print_t(line)
                time.sleep(2)
            
            time.sleep(3)

    def clear_screen(self):

        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    def choose_spell(self):

        """ Multiple spells are being cast -- choose one. """

        self.send("MULTIPLE_SPELLS_ACK")
        data_p = self.recv()

        if self.response(data_p, "Server died while client waited for multiple spells pickle."):
            spell_list, hand_casting = self.depickle(data_p)

            self.clear_screen()

            self.print_t("Multiple spells can be casted with the gestures of your " + hand_casting + " hand.\n")

            for i,spell_name in enumerate(spell_list, 1):
                self.print_t(str(i) + ". " + spell_name)

            choice = 0
            
            while True:
                choice = input("\nChoose a spell to cast: ")
                try:
                    choice = int(choice) - 1
                    if choice >= 0 and choice < len(spell_list):
                        break
                    else:
                        self.print_t("Your choice is invalid.")
                except ValueError:
                    self.print_t("Your choice is invalid.")

            self.send(spell_list[choice])

    def round_end(self):

        """ Receive the list containing all of the round's flavor messages,
        and then print them one-by-one. Ask for confirmation before continuing.
        """

        self.print_t("Receiving PRINT_FLAVOR.")
        self.send("PRINT_FLAVOR_ACK")
        self.print_t("Sent PRINT_FLAVOR_ACK")

        size = self.recv()
        if self.response(size, "Server died before data size was sent"):
            size = int.from_bytes(size, "big")
            self.print_t("Incoming size is " + str(size))
            self.send("SIZE_ACK")

            flavor_list = b""
            while len(flavor_list) < size:
                self.print_t("Receiving...")
                data = self.recv(4096)
                if not data:
                    break
                flavor_list += data
                self.print_t("Size is now " + str(len(flavor_list)))
                if "\0" in self.depickle(flavor_list):
                    # EOF
                    break
                if len(flavor_list) < size:
                    self.send("MORE_DATA")
                    self.print_t("Sent MORE_DATA request")

            self.send("DATA_DONE")
            self.print_t("Sent DATA_DONE request")

        if self.response(flavor_list, "Server died before sending flavor list."):
            flavor_list = self.depickle(flavor_list)

            self.clear_screen()

            game_ending = False
            time_stopping = False

            for line in flavor_list:
                if line == "\0":
                    continue
                ending = self.check_for_game_end(line)
                if self.check_for_timestop_end(line):
                    time_stopping = False
                if not ending:
                    if not time_stopping:
                        if "blind" in self.enchantments:
                            # Ignore any strings that do not have our name.
                            if line.find(self.name) > -1:
                                # It's here.
                                self.print_t(line)
                                time.sleep(self.sleep_time)
                        else:
                            self.print_t(line)
                            time.sleep(self.sleep_time)
                        time_stopping = self.check_for_timestop(line)
                    else:
                        # When timestopped, remove any lines that do not include our name.
                        if line.find(self.name) > -1:
                            # Our name is here. Further review...
                            self.print_t(line)
                            time.sleep(self.sleep_time)

                else:
                    game_ending = True
                    self.print_t(line)
                    time.sleep(self.sleep_time)

            input("\nPress enter to continue.")

            if game_ending:
                self.print_t("\nThank you for playing Richard Bartle's Spellbinder!\n")
                self.kill_connection("GAME OVER")
            else:
                self.send("NEXT_TURN_READY")

    def check_for_timestop(self, line):

        if line.find("For an instant,") > -1:
            return True

        return False

    def check_for_timestop_end(self, line):

        if line.find("The normal flow of time") > -1:
            return True

        return False

    def check_for_game_end(self, line):

        game_enders = ("less messily",
                       "equally messily",
                       "has won the battle",
                       "ends in a draw",
                       "is victorious!")

        for ender in game_enders:
            if line.strip().find(ender) > -1:
                return True

        return False

    def raise_dead(self):

        """ Choose a target and either raise it from the dead or heal it. """

        

        self.send("RAISE_DEAD_ACK")

        # Receive a list in the format [list minion_graveyard, list living_targets]
        p_data = self.recv()

        if self.response(p_data, "Server died before sending Raise Dead pickle data"):
            dead, living = self.depickle(p_data)

            target = "No target"

            while True:
                self.clear_screen()
                living_index = 1
                self.print_t(self.name + " is raising the dead!")

                self.print_t('{:>2}. {:<22} {:<4} {:<4} {:^22} {:<22}'.format('#', 'Name', 'HP', 'Rank', 'Target', 'Master'))
                if dead:
                    living_index = 1 + len(dead)
                    
                    print_f = ""
                    for i,dead_minion in enumerate(dead, 1):
                        if dead_minion.e_type == "minion":
                            print_f = "{:>2}. {:<22} {:<4} {:<2}".format(str(i), dead_minion.name.title(), "dead", str(dead_minion.rank))
                        else:
                            print_f = "{:>2}. {:<22} {:<4}".format(str(i), dead_minion.name.title(), "dead")
                        self.print_t(print_f)

                for i,entity in enumerate(living, living_index):
                    if entity.e_type == "minion":
                        print_f = "{:>2}. {:<22} {:<2} {:<4} {:^22} {:<22}".format(str(i), entity.name.title(), str(entity.hp), str(entity.rank), entity.target.name, entity.master.name)
                    else:
                        print_f = "{:>2}. {:<22} {:<2}".format(str(i), entity.name.title(), entity.hp)
                    self.print_t(print_f)

                while True:

                    choice = input("Choose a target to raise: ")

                    try:
                        choice = int(choice) - 1
                        if choice >= 0 and choice < (len(dead) + len(living)):
                            if choice < len(dead):
                                target = dead[choice]
                                break

                            elif choice >= len(dead):
                                target = living[choice - len(dead)]
                                break

                        else:
                            self.print_t("Invalid selection.")

                    except ValueError:
                        self.print_t("Invalid selection.")

                confirm = False

                while True:

                    choice = input("You wish to cast Raise Dead on " + target.name + ", is that correct? (y/n, enter for y) ")

                    if choice == "y" or choice == "":
                        confirm = True
                        break
                    elif choice == "n":
                        break
                    else:
                        self.print_t("Your answer is invalid.")

                if confirm:
                    break
                
            self.send(target.name)

    def command_monster(self):

        """ Command a single monster. """

        self.clear_screen()

        self.send("COMMAND_MONSTER_ACK")

        # Receive a list in the format [list targets, string
        p_data = self.recv()

        targets, minion = self.depickle(p_data)
        target = minion.target_name

        while True:

            self.print_t("Who will be the target of " + minion.name + "?")

            self.print_t("Current target is: " + minion.target_name)
            
            self.enumerate_targets(targets)

            choice = input("\nChoose target (leave blank or press enter for current target): ")

            if choice == "":
                if minion.target_name == "No target":
                    self.print_t("You must select an initial target for " + minion.name +".")
                else:
                    break
            else:
                try:
                    if (int(choice) >= 1) and (int(choice) <= len(targets)):
                        target = targets[int(choice)-1].name
                        break
                    else:
                        self.print_t("Invalid target \'" + choice + "\'.")
                except ValueError:
                    self.print_t("Invalid target \'" + choice + "\'.")

        self.send(target)

    def enumerate_targets(self, target_list, starting_index = 1):

        self.print_t('{:>2}. {:<30} {:<2} {:<4} {:^22} {:<22}'.format('#', 'Name', 'HP', 'Rank', 'Target', 'Master'))
        for i,entity in enumerate(target_list, starting_index):
            
            name = entity.name.title()
            if entity.e_type == "minion":
                print_f = "{:>2}. {:<30} {:<2} {:<4} {:^22} {:<22}".format(str(i), name, str(entity.hp), str(entity.rank), entity.target_name, entity.master_name)
            else:
                if entity.e_type == "wizard":
                    if entity.invisible:
                        name = entity.name.title() + " (invisible)"
                print_f = "{:>2}. {:<30} {:<2}".format(str(i), name, entity.hp)
            print(print_f)

    def get_spell_desc(self, spell_name):

        return spell_name.upper() + "\n\n" + self.spellbook.show_spell_desc_by_name(spell_name)

    def print_t(self, line):

        lines = self.trim_long_line(line)
        for t_line in lines:
            if self.screen:
                self.screen.addstr(t_line)
                self.screen.refresh()
            else:
                print(t_line.strip())

    def get_target(self):

        """ Received an attack name and a pickled target list from the server. """

        self.clear_screen()

        self.send("GET_TARGET_ACK")
        
        # Receive a list in the format [list targets, string attack]
        p_data = self.recv()

        targets, attack = self.depickle(p_data)

        target = "self"

        while True:

            self.print_t(self.name + ": Who will be the target of the " + attack + "?")
            
            self.enumerate_targets(targets)

            choice = input("\nChoose target (leave blank or press enter for self, ? for spell description): ")

            if choice == "":
                break

            try:
                if (int(choice) >= 1) and (int(choice) <= len(targets)):
                    target = targets[int(choice)-1]
                    if target.e_type == "elemental":
                        if "Groble" in attack:
                            self.print_t("A groble-summoning spell cannot target an elemental.")
                        elif attack == "Amnesia":
                            self.print_t("An elemental cannot be made amnesiac.")
                        elif attack == "Confusion":
                            self.print_t("An elemental cannot be confused.")
                        elif "Charm" in attack: # Charm Person, Charm Monster
                            self.print_t("An elemental cannot be charmed.")
                        elif attack == "Raise Dead":
                            self.print_t("A non-wizard cannot wield the power to raise the dead.")
                        elif attack == "Paralysis":
                            self.print_t("An elemental cannot be paralyzed.")
                        elif attack == "Fear":
                            self.print_t("An elemental cannot feel fear.")
                        elif attack == "Anti-spell":
                            self.print_t("An elemental cannot be anti-spelled.")
                        elif attack == "Delayed Effect":
                            self.print_t("An elemental cannot cast spells.")
                        else:
                            break
                    elif target.e_type == "minion":
                        if attack == "Raise Dead":
                            self.print_t("A non-wizard cannot wield the power to raise the dead.")
                        elif attack == "Anti-spell":
                            self.print_t(target.name + ", a minion, cannot be anti-spelled.")
                        elif attack == "Delayed Effect":
                            self.print_t(target.name + " cannot cast spells.")
                        else:
                            break
                    else:
                        break
                else:
                    self.print_t("Invalid target \'" + choice + "\'.")
            except ValueError:
                if choice == "?":
                    if "stab" in attack:
                        print("") 
                        self.print_t("\n" + attack.upper() + "\n\nStab the target of choice for 1 damage. Stabs are prevented by any spell that has a shield effect.\n")
                    else:
                        spell_desc = self.spellbook.show_spell_desc_by_name(attack)
                        print("")
                        self.print_t(spell_desc)
                else:
                    self.print_t("Invalid target \'" + choice + "\'.")

        self.wait_msg()
        
        if target != "self":
            target = target.name

        self.send(target)

    def dead_response(self, data):

        """ Returns True if the encoded data passed is a blank bytestring,
        otherwise returns False. """

        if data == b'':
            return True
        else:
            return False

    def receive_msg(self):

        """ Prepare to receive a message.  Send the server ACK_MSG. Receive
        message. Send the server ACKACK_MSG to confirm it was received, then
        print to the client. """

        self.dmsg("Sending ACK_MSG")
        self.send("ACK_MSG")
        self.dmsg("Sent ACK_MSG")

        gen_msg = self.recv()
        if self.dead_response(gen_msg):
            self.kill_connection("Server died during MSG.")
        else:
            self.print_t(self.dec(gen_msg))
            self.send("ACKACK_MSG")

    def clear_enchantments(self):

        self.enchantments.clear()

    def add_enchantment(self, new_enchantment):

        self.enchantments.append(new_enchantment)

    def has_enchantment(self, enchantment):

        if enchantment in self.enchantments:
            return True

        return False

    def print_enchantment_info(self):

        enchs_and_descs = {"blind"    :"BLINDNESS\n\nYou are blinded! You can't see anything that does not happen to you in this round.",
                           "fear"     :"FEAR     \n\nYou are afraid! You cannot perform the C, D, F, or S gestures.\nYou can only perform P, W, or stabs.",
                           "amnesia"  :"AMNESIA  \n\nYou are amnesiac! You will repeat the gestures you just performed, no matter your input.",
                           "confusion":"CONFUSION\n\nYou are confused! One of your hands will perform a random gesture this turn.",
                           "charmed"  :"CHARMED  \n\nYou are charmed! Your opponent will control your " + self.charmed_hand + " hand this turn.",
                           "paralyzed":"PARALYZED\n\nYou are paralyzed! Your " + self.paralyzed_hand + " hand will repeat its previous gestures.\nIf you did C, S, or W last turn, it will turn into F, D, or P, respectively.",}

        if self.enchantments:
            
            self.print_t("\nCurrent enchantments:\n")

            for enchantment in self.enchantments:
                if enchantment in enchs_and_descs:
                    self.print_t(enchs_and_descs[enchantment])

    def trim_long_line(self, long_str):

        trimmed_string = []

        while len(long_str) > self._MAX_WIDTH:
            #while len(long_str) > MAX_WIDTH:
                # Split it into a table of strings.
                # First, find where the last word ends.
            search_index = self._MAX_WIDTH
            
            while long_str[search_index] != " ":
                search_index -= 1

            # Now we have a space, so slice the string here.
            long_str_trimmed = long_str[:search_index].strip()
            trimmed_string.append(long_str_trimmed)

            long_str = long_str[search_index:]

        trimmed_string.append(long_str)

        return trimmed_string

    def get_wizard_status(self, phase):

        self.clear_enchantments()

        if phase.lower() == "gesture":

            self.send("STATUS_AMNESIA")
            amnesia = self.recv()

            if self.response(amnesia, "Server stopped communicating during the STATUS_AMNESIA request."):
                amnesia = self.depickle(amnesia)

                if amnesia:
                    self.add_enchantment("amnesia")

            self.send("STATUS_BLIND")
            blind = self.recv()

            if self.response(blind, "Server stopped communicating during the STATUS_BLIND request."):
                blind = self.depickle(blind)

                if blind:
                    self.add_enchantment("blind")

            self.send("STATUS_CHARMED")
            charmed = self.recv()

            if self.response(charmed, "Server stopped communicating during the STATUS_CHARMED request."):
                charmed, charmed_hand = self.depickle(charmed)

                if charmed:
                    self.charmed_hand = charmed_hand
                    self.add_enchantment("charmed")

            self.send("STATUS_CONFUSION")
            confusion = self.recv()

            if self.response(confusion, "Server stopped communicating during the STATUS_CONFUSION request."):
                confusion = self.depickle(confusion)

                if confusion:
                    self.add_enchantment("confusion")

            self.send("STATUS_FEAR")
            fear = self.recv()
            
            if self.response(fear, "Server stopped communicating during the STATUS_FEAR request."):
                fear = self.depickle(fear)
                
                if fear:
                    self.add_enchantment("fear")

            self.send("STATUS_HASTE")
            haste = self.recv()

            if self.response(haste, "Server stopped communicating during the STATUS_HASTE request."):
                self.hasted = self.depickle(haste)

            self.send("STATUS_HP")
            hp = self.recv()

            if self.response(hp, "Server stopped communicating during the STATUS_HP request."):
                self.hp = self.depickle(hp)

            self.send("STATUS_ENEMY_HP")
            enemy_hp = self.recv()

            if self.response(enemy_hp, "Server stopped communicating during the STATUS_ENEMY_HP request."):
                self.enemy_hp = self.depickle(enemy_hp)

            self.send("STATUS_MONSTERS")
            monsters = self.recv()

            if self.response(monsters, "Server stopped communicating during the STATUS_MONSTERS request."):
                monsters = self.depickle(monsters)

                if monsters:
                    self.monsters = monsters

            self.send("STATUS_PARALYZED")
            paralysis = self.recv()

            if self.response(paralysis, "Server stopped communicating during the STATUS_PARALYZED request."):
                paralysis, paralyzed_hand = self.depickle(paralysis)

                if paralysis:
                    self.paralyzed_hand = paralyzed_hand
                    self.add_enchantment("paralyzed")

            self.send("STATUS_TIMESTOP")
            timestop = self.recv()

            if self.response(timestop, "Server stopped communicating during the STATUS_TIMESTOP request."):
                self.timestopped = self.depickle(timestop)

    def send(self, msg, reason=False):

        """ Send to server as an encoded string. """

        if reason:
            self.print_t("Sending " + msg + " to server.")

        self.server.send(msg.encode(self._ENC))

    def recv(self, buff=0):

        """ Receive from server. """

        if buff == 0:
            buff = self._BUFFSIZE

        self.dmsg("Receiving message...")

        return self.server.recv(buff)

    def dmsg(self, msg: str) -> None:

        """ Print a debug message. """

        if self.debug:
            self.print_t(msg)

    def dec(self, msg):

        """ Decode encoded string and return it. """

        return msg.decode(self._ENC)

    def send_p(self, pickled_item):

        """ Send a pickled item. """

        self.server.send(pickled_item)

    def depickle(self, pickled_item):

        """ Return the depickled version of the item. """

        return pickle.loads(pickled_item)

    def pickle(self, item):

        """ Return the pickled version of the item. """

        return pickle.dumps(item)

    def get_gestures(self):

        # First, we need to get information about the wizard status.
        # We need the wizard's fear status and the wizard's spellbook item.

        # TODO: For @, the wizard calls self._spellbook.list_spells()

        self.get_wizard_status("gesture")

        self.get_history()
        self.get_history_others()

        gestures_d = self.prompt_for_gestures()

        self.send("GESTURES_COMPLETE")

        confirmation = self.recv()

        if self.response(confirmation, "Server stopped communicating during the GESTURES_COMPLETE request."):
            confirmation = self.dec(confirmation)
            if confirmation == "RECEIVE_GESTURES":
                gestures_d_p = self.pickle(gestures_d)
                self.send_p(gestures_d_p)

    def show_hp(self):

        self.print_t("\nYour HP:  " + str(self.hp))
        self.print_t("Enemy HP: " + str(self.enemy_hp) + "\n")

    def prompt_for_gestures(self):

        self.clear_screen()

        valid_gestures = ("f", "p", "s", "w", "d", "c", "h", "?", "@", "$", "!", "%", "#")
        fear_gestures = ("c", "d", "f", "s")

        if not self.hasted and self.haste_turn_two:
            self.haste_turn_two = False

        while True:

            self.clear_screen()

            if self.hasted and self.haste_turn_two:
                self.print_t("You make an additional set of gestures due to haste!\n")

            if self.timestopped:
                self.print_t("The clapping of your hands echoes through the silence of stopped time.\n")

            restart = False

            gestures_d = {"left":"", "right":""}

            duplicate_stab = False

            hands = ("left", "right")
            hand_width = len("Enter a gesture for your right hand (? for help): ")

            self.print_t(self.name.upper())

            if self.autospell:
                self.spellbook.list_spells()

            self.show_hp()

            self.show_hands_history_others()

            self.show_monsters()

            self.print_enchantment_info()

            self.print_t("")

            for hand in hands:
                
                while True:
                    g_input = "{0:{width}}".format("Enter a gesture for your " + hand + " hand (? for help): ", width = hand_width)

                    gestures = (input(g_input)).lower()

                    if len(gestures) > 1 and gestures[0] != "@":
                        self.print_t("Gesture input too long.")
                    elif len(gestures) > 1 and gestures[0] == "@":
                        try:
                            # Spell number?
                            gesture = int(gestures[1:])
                            spell_desc = self.spellbook.show_spell_desc(gesture)
                            print("")
                            self.print_t(spell_desc)
                        except ValueError:
                            # Can't turn it into an int.
                            gesture = gestures[1:]
                            if gesture.lower() == "g":
                                self.spellbook.list_spells_by_gesture()
                            elif gestures[:2].lower() == "@g" and len(gestures) > 2:
                                num = gestures[2:]
                                spell_desc = self.spellbook.show_spell_desc_gesture_sort(num)
                                print("")
                                self.print_t(spell_desc)
                            elif gestures[:2] == "@#" and len(gestures) > 3:
                                hand_s = gestures[2]
                                num = gestures[3:]
                                try:
                                    num = int(num)
                                    if hand_s == "l":
                                        hand_s = "left"
                                    elif hand_s == "r":
                                        hand_s = "right"
                                    else:
                                        hand_s = "none"
                                    if hand_s == "none":
                                        print("The given hand is invalid.")
                                    else:
                                        hand_hist = self.hands[hand_s]
                                        self.spellbook.search_by_gesture_length(hand_hist, num)
                                except ValueError:
                                    print("Please enter a gesture length number to search by.")
                            else:
                                if "@#" not in gestures:
                                    print("Trying to find " + gesture.title())
                                    spell_desc = self.spellbook.show_spell_desc_by_name(gesture.title())
                                    print("")
                                    self.print_t(spell_desc)
                                else:
                                    print("Please enter a hand and gesture length number to search by.")
                       
                        self.show_hands_history_others()
                    
                    else:
                        if gestures in valid_gestures:
                            if gestures == "?":
                                self.print_help()
                            elif gestures == "@":
                                self.spellbook.list_spells()
                                self.show_hands_history_others()
                            elif gestures == "h":
                                self.show_hands_history_others()
                            elif gestures == "!":
                                restart = True
                                break
                            elif gestures == "%":
                                self.show_hp()
                            elif gestures == "#":
                                if not self.autospell:
                                    print("Auto-spellbook enabled -- the spellbook will automatically open on your turn.")
                                    self.autospell = True
                                else:
                                    print("Auto-spellbook disabled.")
                                    self.autospell = False
                            else:
                                if gestures in fear_gestures and "fear" in self.enchantments:
                                    self.print_t("You are too fearful to perform that gesture!")
                                else:
                                    # actual recordable gestures now
                                    # don't add gestures to history until we have both.
                                    # this is so we can capitalize gestures to represent 'both hands'
                                    if gestures == "$" and duplicate_stab:
                                        self.print_t("You have only one dagger to stab with!")
                                    else:
                                        if gestures == "$":
                                            duplicate_stab = True
                                        gestures_d[hand] = gestures
                                        break

                        else:
                            self.print_t("You've given an invalid gesture.")

                if restart:
                    break

            if gestures_d["left"] and gestures_d["right"]:

                self.print_t("\nLeft hand gesture:  [" + gestures_d["left"] + "]")
                self.print_t("Right hand gesture: [" + gestures_d["right"] + "]")
                
                satisfied = False

                while True:
                    answer = input("\nIs this correct? (y/n or enter for y): ")
                    if answer.lower() == "y" or answer == "":
                        if gestures_d["left"] == "p" and gestures_d["right"] == "p":
                            while True:
                                surrender = input("\nBEWARE: These gestures will make you surrender! Are you sure? (Y/N) ")
                                if surrender == "Y":
                                    satisfied = True
                                    break
                                if surrender == "N":
                                    break
                        else:
                            satisfied = True
                            break
                        break
                    elif answer.lower() == "n":
                        break
                    else:
                        self.print_t("You've given an invalid answer.")
                
                if satisfied:
                    break

        if self.hasted and not self.haste_turn_two:
            self.haste_turn_two = True

        return gestures_d

    def print_help(self):
        print("\nWaving Hands is played by two wizards making " +
            "arcane gestures at each other.\n" +
            "The valid gestures are: \n" +
            "\nF:    The wiggled fingers" +
            "\nP:    The proffered palm" + 
            "\nS:    The snap of the fingers" +
            "\nW:    The wave of the hand" +
            "\nD:    The pointing digit" +
            "\nC:    The clapping of the hands" +
            "\n$:    The stab of the dagger" +
            "\n\n@:   Consult your spellbook" +
            "\n@#:   See spell description" +
            "\n@g:   Consult your spellbook, sorted by gesture" +
            "\n@g#:  See spell description, per gesture-sorted numeral"
            "\n@#hX: See what spells can be made with the last X gestures of your h hand.\nUsage examples:  @#r1 (See what can be made from the last gesture of the right hand)\n                 @#L3 (See what can be made from the last 3 gestures of the left hand)\n" +
            "\n#:    Toggle auto-opening of spellbook."
            "\nH:    See previous gestures." +
            "\n!:    Cancel your current gestures and repeat your turn." +
            "\n%:    See HP levels." +
            "\n\nTo surrender, proffer both palms.")

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
            self.print_t("{0:{width}} {1}".format(prehistory_line, self.hands[hand], width = prehistory_len))

        if self.perceived_history:
            for other_wizard in self.perceived_history:
                self.print_t("")
                other_hands = ("left", "right")
                for hand in other_hands:
                    prehistory_line = other_wizard + "\'s " + hand + " hand history: "
                    self.print_t("{0:{width}} {1}".format(prehistory_line, self.perceived_history[other_wizard][hand], width = prehistory_len))

    def get_history(self):

        """ Get the history string for this client.
        This is expected in a dictionary:

        {
            "left":history,
            "right":history
        }
        """

        self.send("REQUEST_HISTORY_SELF")
        my_history = self.recv()

        if self.response(my_history, "Server died after sending client's hand history dictionary."):
            self.hands = self.depickle(my_history)

    def get_history_others(self):

        """ Get the perceived history table from the server. """

        self.send("REQUEST_HISTORY_OTHERS")
        others_history = self.recv()

        if self.response(others_history, "Server died after sending other's hand history dictionary."):
            self.perceived_history = self.depickle(others_history)

    def response(self, data, kill_msg=""):

        if self.dead_response(data):
            self.kill_connection(kill_msg)

        return True

    def customization(self):

        cust_q = {"name":"What is your name? ",
                  "color":"What is the color of your robes? ",
                  "taunt":"What will you say to make your enemies tremble in fear? ",
                  "victory":"What will you say on your inevitable victory? "}
        
        """
        cust_d = {}
        cust_d["name"] = "Merlin" + str(randint(1, 100))
        self.name = cust_d["name"]
        cust_d["color"] = "blue"
        cust_d["taunt"] = "Beware!"
        cust_d["victory"] = "I win!"
        """

        max_len = 30
        customizing = True

        while customizing:

            self.clear_screen()

            print("Welcome to Richard Bartle's Spellbinder.\n")

            cust_d = {}
            # field will be the key of each entry in cust_q.
            for field in cust_q:
                # While cust_d does not have a 'field' key...
                while field not in cust_d:
                    command = input(cust_q[field])
                    # This is to prevent blank entries.
                    if command.strip() == "":
                        self.print_t("Please enter an answer.")
                    else:
                        if len(command) > max_len:
                            self.print_t("Your entry is too long (" + str(max_len) + ") characters maximum).")
                        else:
                            # Assign command to cust_d's field key.  Since cust_d has
                            # an entry for field, it moves on to the next key.
                            cust_d[field] = command
            
            print("\nYou will be introduced like so:")
            print("A wizard in " + cust_d["color"] + " robes steps forward.")
            print('\"I am ' + cust_d["name"] + '. ' + cust_d["taunt"] + '\"')
            print("\nAnd on your inevitable victory:")
            #rint(self.name + " triumphantly declares, \"" + self.victory + "\"")
            print(cust_d["name"] + ' triumphantly declares, \"' + cust_d["victory"] + '\"')
            
            while True:
                satisfied = input("\nAre you satisfied with this? (y/n) ")

                if satisfied.lower() == "y":
                    customizing = False
                    break
                elif satisfied.lower() == "n":
                    break
                else:
                    self.print_t("Your choice is invalid.")

        self.dmsg("This client is " + cust_d["name"])
        self.name = cust_d["name"]

        cust_d = self.pickle(cust_d)
        self.send_p(cust_d)

        """
        # The server will send the SpellbookClient object.
        spellbook_c = []
        while True:
            self.print_t("Receiving spellbook data...")
            spellbook_data = self.recv(4096)
            if not spellbook_data:
                self.print_t("Received!")
                break
            spellbook_c += spellbook_data 
            self.print_t("End block.")
        spellbook_c = b"".join(spellbook_c)

        if self.response(spellbook_c, "Server died while receiving spellbook"):
            spellbook_c = self.depickle(spellbook_c)
            self.spellbook = spellbook_c

            self.send("ACK_SPELLBOOK")

        """

    def kill_connection(self, reason=""):

        """ Gracefully shut down the connection to the server and exit the program. """

        self.print_t("Killing connection to server.")

        if reason:
            self.print_t("Reason: " + reason)

        self.server.shutdown(1)
        self.server.close()

        self.print_t("Server closed.")

        sys.exit()

    def make_server_connection(self):

        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.clear_screen()

        try:
            self.server.connect(self._HOST_ADDR)
            self.print_t("Connected to server!")
        except:
            self.print_t("Unable to connect to server!")
            raise

    def setup(self, screen):

        # Make a connection to the server.
        self.screen = screen

        self.make_server_connection()
        self.connection_loop()
        self.kill_connection()

def main(screen=None):

    client = SpellbinderClient()
    client.setup(screen)

    curses.nocbreak()
    screen.keypad(False)
    curses.noecho()
    curses.endwin()

    print("Thanks for playing Richard Bartle's Spellbinder!")

if __name__ == "__main__":
    main()
    #curses.wrapper(main)