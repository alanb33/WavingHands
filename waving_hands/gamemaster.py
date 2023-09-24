from random import randint
import pickle
import select
import socket
import sys
import logging
import logging.config

from waving_hands.elemental import Elemental
from waving_hands.minion import Minion
from waving_hands.targetable_client import TargetableClient
from waving_hands.wizard import Wizard
from waving_hands import groblenames, server

log = logging.getLogger(__name__)


class Gamemaster:

    def __init__(self,
        host: str = "localhost",
        port: int = 12345,
        pregame: bool = True,
        customize_wizards: bool = True,
        players: int = 2):
        """
        Start the game, with a given number of parameters

        :param host: IP address or host to serve the game, defaults to localhost
        :param port: Port to use for the server
        :param pregame: Start the game with pre-game flair? Defaults to True
        :param customize_wizards: Allow players to customize their wizards? Defaults to True
        :param players: Number of players to use for the game. Defaults to 2
        """

        self._wizards = []

        self.pregame = pregame
        self.customize_wizards = customize_wizards

        self._winner = None
        self._loser = None
        self._surrender = False

        self._targets = []
        self._stab_targets = []
        self._spell_targets = []
        self._spells_reflected = []

        self._dying_minions = []
        self._minion_graveyard = []
        self._summoned_this_turn = []

        self._field_elemental = None
        self._field_storm = ""
        self._firestorm = False     # This is only for state checking during spell resolution.

        self._playing = False

        self._flavor_list = []

        self._expiring_spells = []

        self._NUMBER_OF_WIZARDS = players

        self.server = server.Server(host, port)

    def setup_game(self):
    
        self.create_wizards() # create wizards, populate spellbook
        # Wait for incoming connections and assign the sockets to the wizards.
        clients = self.server.wait_for_connections(minimum_clients=self._NUMBER_OF_WIZARDS)
        if len(clients) != len(self.wizards):
            log.warning(f"Connected clients {len(clients)} do not match expected wizards {len(self.wizards)}!")
        for wiz, cli in zip(self.wizards, clients):
            wiz.client = cli

        if self.customize_wizards:
            log.debug("Customizing Wizards")
            self.customize()      # customize wizards. technically polish phase

        """@
        for wizard in self.wizards:
            wizard.hasted = True
            break
        """

        if self.pregame:
            log.debug("Starting pregame")
            self.pregame_flavor()

    def welcome(self):

        c_list = []

        for wizard in self.wizards:
            if wizard.client:
                c_list.append(wizard.client)

        for client in c_list:
            client.send("WELCOME".encode(self._ENC))

        while True:

            rlist, wlist, elist = select.select( c_list, [], [] )
            pass        

        welcome_msg = ("---\n",
                       "A storm rages on a windswept plain.\n",
                       "Flashes of lightning illuminate the darkened sky.\n",
                       "Rain cascades around two mysterious figures.\n",
                       "There is an ominous roll of thunder as they step forward...\n",
                       "---\n")

        for line in welcome_msg:
            for client in c_list:
                client.send(line.encode(self._ENC))

    def create_wizards(self):

        # Waving Hands will be played with two wizards.
        #
        # Due to the way the code is written, theoretically there could be more
        # than two wizards.
        #
        # Balancing the game for multiple wizards is outside the scope of the
        # original program.


        # This code will be uncommented when the customization phase is the
        # focus of ongoing development.

        # for i in range(NUMBER_OF_WIZARDS):
        #     wizards.append(Wizard())

        # The following code only exists for development purposes, as the
        # customization code is not the current focus.

        self.wizards = [
            Wizard("Gandalf"),
            Wizard("Saruman")
            ]

        for wizard in self.wizards:
            self.add_target(wizard)

    def get_clients(self):

        """ Get the list of connected clients and return it as a list. """

        c_list = []

        for wizard in self.wizards:
            if wizard.client:
                c_list.append(wizard.client)

        return c_list

    def get_wizard_from_client(self, client):

        for wizard in self.wizards:
            if wizard.client == client:
                return wizard

        return None

    def get_enemy_wizard(self, wizard: Wizard) -> None:
        """Get an enemy wizard from this wizard"""
        if len(self.wizards) > 2:
            log.warning(f"There are more than two wizards! "
                        "Cannot distinguish particular wizard enemies!")

        for w in self.wizards:
            if w != wizard:
                return wizard
        log.warning(f"No enemy wizards found for wizard {wizard}")
        return None

    def customize(self):
        for wizard in self.wizards:
            wizard.clear_slate()

        server_responses = self.server.get_from_clients(
            "CUSTOMIZE", lambda c: self.get_wizard_from_client(c).is_ready()
        )

        for client, message in server_responses:
            wizard = self.get_wizard_from_client(client)
            try:
                # Passing in ** keyword arguments isn't great here because we haven't verified that the stuff
                # inside message is valid or not. It could be junk! In which case we get a nasty exception here.
                wizard.set_slate(**message)
            except Exception as e:
                log.exception(e)
                log.error(
                    "Bad code is coming back to haunt you. Received unexpected state when deserializing client response during customization"
                )

    def pregame_flavor(self):

        pf = ["A storm rages over a windswept plain.",
                "Despite the torrential downpour, two figures can be seen approaching each other.",
                "They stop at a distance, waiting. Thunder rumbles overhead.\n"]

        for wizard in self.wizards:
            pf.append(f"A wizard in {wizard.color} robes steps forward.")
            pf.append(f'"I am {wizard.name}. {wizard.taunt}"')

        pf.append("\nWith a flash of lightning, the battle begins!")

        self.server.message_clients_command("PREGAME", pf)


    def play_game(self, max_turns=0):

        """
        
        Waving Hands proceeds in four (technically five) phases.

        Phase 1: Input phase.
            - The player is asked for their gestures or other commands.

        Phase 1.5: Hybrid Input/Processing phase.
            - After receiving inputs, determine if any actions require
              additional input -- like choosing the target for a spell.

        Phase 2: Processing phase
            - Resolve the actual mechanical effects of all activities.

        Phase 3: Output phase:
            - Print flavor text for all activities. Including:
                * Gestures made
                * Spells cast by who, with what hand, on what
                * Stabs, monster attacks
                * Death, victory/defeat scenes

        Phase 4: Cleanup phase:
            - Clean up lingering variables to prepare the loop for a second
              (and on) runthrough until the game is over.

        """

        self.playing = True
        turn = 0

        while self.playing:
            turn += 1

            self.get_gestures()
            self.get_additional_gestures()

            self.process_turn()

            self.resolve_death_or_surrender()

            self.print_flavor_messages()
            self.cleanup()

            if self.surrender:
                print("Thank you for playing Richard Bartle's Spellbinder!")
                self.playing = False

            log.info(f"Turn {turn}: {tuple(w.basic_stats for w in self.wizards)}")

            # IF max turns was set above zero, turns will be tracked and end the game on max_turns
            if turn >= max_turns > 0:
                self.playing = False
        

    def cleanup(self):

        for wizard in self.wizards:
            wizard.end_turn()
            for minion in wizard.minions:
                minion.end_turn()

                # Get the index where " (newly summoned)" begins.
                newsum_i = minion.name.find(" (newly summoned)")
                
                # Remove " (newly summoned)" from the minion's name, if it exists
                if newsum_i > -1:   # string.find returns -1 if the argument is not found
                    minion.name = minion.name[:newsum_i]

        if self.field_elemental:
            self.field_elemental.end_turn()

        self.field_storm = ""
        self.firestorm = False

        self.clear_targets()

        self.clear_flavor_list()

        self._summoned_this_turn = []
        self._spells_reflected = []
        self._expiring_spells = []

    def clear_flavor_list(self):
        self._flavor_list = []

    @property
    def expiring_spells(self):
        return self._expiring_spells

    @property
    def firestorm(self):
        return self._firestorm

    @firestorm.setter
    def firestorm(self, bool):
        self._firestorm = bool

    @property
    def field_storm(self):
        return self._field_storm

    @field_storm.setter
    def field_storm(self, element):
        if element == "cold":
            self._field_storm = "ice"
        else:
            self._field_storm = element

    @property
    def spells_reflected(self):
        return self._spells_reflected

    def add_spell_reflection(self, spell_tuple):
        self._spells_reflected.append(spell_tuple)

    def get_gestures(self):

        # Receive the wizard's gestures for this turn.
        # Gestures are in the format of d, f, p, s, w, and C.
        # Capitalized gestures imply that both hands were used to make the
        # gesture.

        # The gamemaster does not need to know what the gestures are right
        # now -- the gestures are placed into the relevant Hand object of the
        # wizard. A wizard has two hands, left and right, and can get details
        # about them.

        wizards = self.wizards

        if self.field_elemental:
            c_list = self.get_clients()
            for client in c_list:
                self.msg_client_g("An elemental of " + self.field_elemental.element + " rages on the battlefield.", client)

        timestopped_wizard = None

        for wizard in wizards:
            if wizard.timestopped:
                timestopped_wizard = wizard

        if timestopped_wizard:
            for wizard in self.wizards:
                if wizard != timestopped_wizard:
                    self.wait_msg(wizard.client, "Waiting for a timestopped turn...")
            self.get_gestures_from_client(timestopped_wizard.client)
            self.handle_gesture_phase(timestopped_wizard)
        else:
            self.get_client_gestures()
            for wizard in self.wizards:
                self.handle_gesture_phase(wizard)
        
        for wizard in self.wizards:
            if not wizard.timestopped:
                self.broadcast_gestures(wizard)

    def get_client_gestures(self):
        clients_finished_turn = {}
        server_responses = self.server.get_from_clients(
            "GET_GESTURES", lambda c: clients_finished_turn.get(c) is True
        )

        for client, command in server_responses:
            wizard = self.get_wizard_from_client(client)
            log.debug(f"Received {command} from {wizard}.")
            if command == "GESTURES_COMPLETE":
                self.server.msg_client("RECEIVE_GESTURES", client)
                wizard.c_hands = self.server.get_client_message(client)
                clients_finished_turn[client] = True
                if len(clients_finished_turn) < self._NUMBER_OF_WIZARDS:
                    self.server.wait_msg(client, "Waiting for challenger to submit gestures...")
            else:
                result = self.get_wizard_status_commands(wizard)[command]
                self.server.msg_client_pp(result, client)
        
        log.info(f"Gestures completed for wizards {self.wizards}")

    def get_monsters(self) -> dict:
        monsters = {}
        for wizard in self.wizards:
            for minion in wizard.minions:
                monsters[minion.name] = minion.master.name

        if self.field_elemental:
            monsters[self.field_elemental.name.title()] = "nobody"
        return monsters

    def get_wizard_status_commands(self, wizard):
       return {
            "STATUS_AMNESIA": wizard.amnesiac,
            "STATUS_BLIND": wizard.blinded,
            "STATUS_CHARMED": [wizard.charmed_hand, wizard.charmed_hand],
            "STATUS_CONFUSION": wizard.confused,
            "STATUS_FEAR": wizard.afraid,
            "STATUS_HASTE": wizard.hasted,
            "STATUS_HP": wizard.hp,
            "STATUS_ENEMY_HP": self.get_enemy_wizard(wizard).hp,
            "STATUS_MONSTERS": self.get_monsters(),
            "STATUS_PARALYZED": [wizard.paralyzed_hand, wizard.paralyzed_hand],
            "STATUS_TIMESTOP": wizard.timestopped,
            "REQUEST_HISTORY_SELF": wizard.hands_history,
            "REQUEST_HISTORY_OTHERS": wizard.perceived_history,
        }

    def get_gestures_from_client(self, client_to_get):

        self.msg_client("GET_GESTURES", client_to_get)

        self.handle_client_gestures_and_status([client_to_get], 1)

        """
        while len(gestures_got) < 1:

            rlist, wlist, elist = select.select( [client_to_get], [], [] )

            for client in rlist:

                request = client.recv(self._BUFFSIZE)
                if self.response(request):

                    request = request.decode(self._ENC)

                    wizard = self.get_wizard_from_client(client)

                    if request == "STATUS_BLIND":

                        print("Received STATUS_BLIND from " + wizard.name)
                        status_blind = self.pickle(wizard.blinded)
                        self.msg_client_p(status_blind, client)
                        print("Sent blind status [" + str(wizard.afraid) + "] to " + wizard.name)

                    if request == "STATUS_FEAR":

                        print("Received STATUS_FEAR from " + wizard.name)
                        status_fear = self.pickle(wizard.afraid)
                        self.msg_client_p(status_fear, client)
                        print("Sent fear status [" + str(wizard.afraid) + "] to " + wizard.name)

                    if request == "STATUS_HASTE":

                        print("Received STATUS_HASTE from " + wizard.name)
                        status_haste = self.pickle(wizard.hasted)
                        self.msg_client_p(status_haste, client)
                        print("Sent haste status [" + str(wizard.hasted) + "] to " + wizard.name)


                    if request == "STATUS_ENEMY_HP":

                        who_wiz_hp = 14

                        for who_wizard in self.wizards:
                            if who_wizard != wizard:
                                who_wiz_hp = who_wizard.hp
                                break

                        print("Received STATUS_HP from " + wizard.name)
                        status_enemy_hp = self.pickle(who_wiz_hp)
                        self.msg_client_p(status_enemy_hp, client)
                        print("Sent enemy HP status [" + str(who_wiz_hp) + "] to " + wizard.name)


                    if request == "STATUS_HP":

                        print("Received STATUS_HP from " + wizard.name)
                        status_hp = self.pickle(wizard.hp)
                        self.msg_client_p(status_hp, client)
                        print("Sent HP status [" + str(wizard.hp) + "] to " + wizard.name)

                    if request == "STATUS_TIMESTOP":

                        print("Received STATUS_TIMESTOP from " + wizard.name)
                        status_timestop = self.pickle(wizard.timestopped)
                        self.msg_client_p(status_timestop, client)
                        print("Sent timestop status [" + str(wizard.timestopped) + "]")

                    if request == "REQUEST_HISTORY_SELF":

                        print("Received REQUEST_HISTORY_SELF from " + wizard.name)
                        
                        history_dict = {"left":"", "right":""}

                        hands = ("left", "right")
                        for hand in hands:
                            history_dict[hand] = wizard.get_hand(hand).show_history()
                            
                        history_dict_p = self.pickle(history_dict)
                        self.msg_client_p(history_dict_p, client)

                        print("Pickled hand history sent to " + wizard.name)

                    if request == "REQUEST_HISTORY_OTHERS":

                        print("Received REQUEST_HISTORY_OTHERS from " + wizard.name)

                        history_dict = wizard.perceived_history

                        history_dict_p = self.pickle(history_dict)
                        self.msg_client_p(history_dict_p, client)

                        print("Pickled perceived history sent to " + wizard.name)

                    if request == "GESTURES_COMPLETE":

                        print("Received GESTURES_COMPLETE from " + wizard.name)
                        self.msg_client("RECEIVE_GESTURES", client)
                        print("Sent RECEIVE_GESTURES to " + wizard.name)
                        gestures_dict = client.recv(self._BUFFSIZE)
                        gestures_dict = self.depickle(gestures_dict)
                        wizard.c_hands = gestures_dict
                        gestures_got.append(client)
                        """
                        


    def add_gesture_flavor(self, wizard):

        """ Read the latest gestures and turn them into flavor messages. """

        left = wizard.get_latest_gesture("left")
        right = wizard.get_latest_gesture("right")

        hands = ("left", "right")

        for hand in hands:
            log.debug(f"Gesture flavor: {wizard}\'s {hand} is {wizard.get_latest_gesture(hand)}")

        if left == right:
            # The same gesture performed twice.
            left = left.upper()
            if left == "F" and not wizard.invisible:
                self.add_flavor(wizard.name + " wiggles the fingers of both hands, magically!")
            elif left == "P" and not wizard.invisible:
                self.add_flavor(wizard.name + " proferrs both palms in surrender!")
            elif left == "S":
                self.add_flavor(wizard.name + " snaps both fingers at once!")
            elif left == "W" and not wizard.invisible:
                self.add_flavor(wizard.name + " waves both hands, mysteriously!")
            elif left == "D" and not wizard.invisible:
                self.add_flavor(wizard.name + " points both digits as finger guns!")
            elif left == "C":
                self.add_flavor(wizard.name + " claps their hands together!")
        else:
            for hand in hands:
                if wizard.get_latest_gesture(hand) == "f" and not wizard.invisible:
                    self.add_flavor(wizard.name + " wiggles the fingers of their " + hand + " hand!")
                elif wizard.get_latest_gesture(hand) == "p" and not wizard.invisible:
                    self.add_flavor(wizard.name + " proferrs their " + hand + " palm!")
                elif wizard.get_latest_gesture(hand) == "s":
                    self.add_flavor(wizard.name + " snaps the fingers of their " + hand + " hand!")
                elif wizard.get_latest_gesture(hand) == "w" and not wizard.invisible:
                    self.add_flavor(wizard.name + " waves their " + hand + " hand through the air!")
                elif wizard.get_latest_gesture(hand) == "d" and not wizard.invisible:
                    self.add_flavor(wizard.name + " points a foreboding finger with their " + hand + " hand!")
                elif wizard.get_latest_gesture(hand) == "c" and not wizard.invisible:
                    self.add_flavor(wizard.name + " demonstrates one hand clapping with their " + hand + " hand.")

    def ask_client_for_release(self, delayed_spell, wizard):

        """ Ask the client if we are releasing the delayed spell.
        Returns True if yes, False if no. """

        client = wizard.client

        self.msg_client("DELAYED_SPELL_RELEASE_QUERY", client)
        if self.response(self.recv(client), "Client died while server waited for response to DELAYED_SPELL_RELEASE_QUERY."):
            data_p = delayed_spell.name
            self.msg_client_pp(data_p, client)
            answer = self.recv(client)
            if self.response(answer, "Client died while server waited for an answer on the delayed spell query."):
                answer = self.depickle(answer)

                if answer == True or answer == False:
                    return answer
                else:
                    print("Received an unusual format for answer, returning False: [" + str(answer) + "]")
                    return False

    def handle_gesture_phase(self, wizard):

        if wizard.blinded:
            if wizard.blinded_duration > 0:
                self.add_flavor(wizard.name + " fumbles about blindly!")
            else:
                wizard.blinded = False
                wizard.blinded_duration = 3
                self.add_flavor(wizard.name + " regains their vision!")
            wizard.blinded_duration = wizard.blinded_duration - 1

        if wizard.invisible:
            if wizard.invisible_duration > 0:
                self.add_flavor(wizard.name + " is invisible!")
            else:
                wizard.invisible = False
                wizard.invisible_duration = 3
                self.add_flavor(wizard.name + " reappears as the invisibility fades!")
            wizard.invisible_duration = wizard.invisible_duration - 1

        wizard.get_gestures()

        if wizard.hasted:
            self.broadcast_gestures(wizard)
            self.add_flavor(wizard.name + " makes an additional set of gestures due to haste!")
            for wiz in self.wizards:
                if wiz != wizard:
                    self.wait_msg(wiz.client, "Waiting for challenger to send hasted gestures...")
            self.get_gestures_from_client(wizard.client)
            wizard.get_gestures()
        
        if wizard.delayed_spell:
            delayed_spell = wizard.get_delayed_spell()
            if delayed_spell:
                # Ask the client if we're releasing
                releasing = self.ask_client_for_release(delayed_spell, wizard)
                if releasing:
                    wizard.releasing_delayed_spell = True

        if wizard.dagger_stolen:
            wielding_hand = ""
            if wizard.dagger_stolen == "left":
                wielding_hand = "right"
            else:
                wielding_hand = "left"
            self.add_flavor(wizard.name + "\'s " + wielding_hand + " hand wrests the dagger out of their " + wizard.dagger_stolen + "! They are too startled to react!")

        if wizard.confused:
            self.add_flavor(wizard.name + " fumbles their " + wizard.confusion_hand + " hand gesture in confusion!")
            wizard.clear_enchantment("Confusion")

        if wizard.amnesiac:
            self.add_flavor(wizard.name + "\'s looks forgetful... they repeat their previous gestures!")

        if wizard.charmed:
            self.add_flavor(wizard.name + " struggles for control of their " + wizard.charmed_hand + " hand!")
            self.add_flavor(wizard.charmer.name + " commands " + wizard.name + "\'s " + wizard.charmed_hand + " hand to perform the gesture '" + wizard.charmed_gesture + "'!")
            wizard.clear_enchantment("Charm Person")

        if wizard.afraid:
            self.add_flavor(wizard.name + " overcomes the consuming terror!")
            wizard.clear_enchantment("Fear")

        if wizard.paralysis:
            if not wizard.paralysis_expiration:
                wizard.clear_enchantment("Paralysis")
            else:
                self.add_flavor(wizard.name + " struggles to shape the gestures of their " + wizard.paralysis_expiration + " hand!")

        self.add_gesture_flavor(wizard)

        if wizard.amnesiac:
            self.add_flavor(wizard.name + " seems less forgetful.")
            wizard.clear_enchantment("Amnesia")

    def broadcast_gestures(self, wizard):

        """ Broadcast the latest gestures of the given Wizard object.

        Other wizards will record that in their own properties.
        """

        for other_wizard in self.wizards:
            if other_wizard != wizard:
                other_wizard.add_broadcasted_gesture(wizard)

    def erase_perceived_history(self, wizard):

        """ When a wizard is hit with Anti-spell, erase their perceived
        history -- it's no longer relevant.
        """

        for other_wizard in self.wizards:
            if other_wizard != wizard:
                other_wizard.erase_perceived_history(wizard)

    @property
    def summoned_this_turn(self):
        return self._summoned_this_turn

    def summon_minion_this_turn(self, minion):
        self._summoned_this_turn.append(minion)

    @property
    def flavor_list(self):
        return self._flavor_list

    def add_flavor(self, line):
        self._flavor_list.append(line)

    def print_flavor_messages(self):

        """ Send the list of flavor messages to each client. """
        payload = self.server.pickle(self.flavor_list + ["\0"])
        clients_finished_turn = {}
        data_sent = {}
        server_responses = self.server.get_from_clients(
            "PRINT_FLAVOR", lambda c: clients_finished_turn.get(c) is True
        )
        for client, message in server_responses:
            if message == "PRINT_FLAVOR_ACK":
                wizard = self.get_wizard_from_client(client)
                self.server.msg_client_i(len(payload), client)
            elif message in ["SIZE_ACK", "MORE_DATA"]:
                sent_size = data_sent.get(client, 0)
                data_sent[client] = client.send(payload[sent_size:])
            elif message == "DATA_DONE":
                pass
            elif message == "NEXT_TURN_READY":
                clients_finished_turn[client] = True
            else:
                log.error(f"Received unexpected command {message}! Ignoring...")

        log.info(f"Finished sending results of turn to {self.wizards}")

    @property
    def stab_targets(self):
        return self._stab_targets

    def clear_targets(self):

        self.clear_stab_targets()
        self.clear_spell_targets()

    def clear_stab_targets(self):

        self._stab_targets = []

    def add_stab_target(self, stabber, stabbed):
        
        """ (Wizard stabber, Object stabbed) Store stab targets for later
            resolution. They are stored as tuples in the argument fomat. """

        self.stab_targets.append((stabber, stabbed))

    @property
    def minion_graveyard(self):
        return self._minion_graveyard

    def bury_minion(self, minion):
        self._minion_graveyard.append(minion)

    @property 
    def spell_targets(self):

        return self._spell_targets

    def clear_spell_targets(self):

        self._spell_targets = []

    def add_spell_target(self, caster, target, spell):

        """ (Wizard caster, Object target, Spell spell) Store spell targets
            for later resolution. They are stored as tuples in the argument
            format. """

        self.spell_targets.append((caster, target, spell))

    def get_additional_gestures(self):

        # Here is where things get a little more tricky.
        # We need to evaluate the given gestures and see if they resolve into
        # anything that we need to handle.
        # This phase will also be used to give orders to any summoned
        # creatures.

        # We must determine spellcasts first in the event of monsters being
        # summoned.

        timestopped_wizard = None

        for wizard in self.wizards:
            if wizard.timestopped:
                timestopped_wizard = wizard

        self.server.message_clients("Waiting for challenger to submit additional commands...")
        if timestopped_wizard:
            if wizard in self.wizards:
                if wizard != timestopped_wizard:
                    self.server.wait_msg(wizard.client, "Waiting for a timestopped turn (additional commands)...")

        if timestopped_wizard:
            self.determine_spellcasts_individual(timestopped_wizard)
        else:
            for wizard in self.wizards:
                self.determine_spellcasts_individual(wizard)

        if timestopped_wizard:
            self.handle_additional_gestures_individual(timestopped_wizard)
        else:
            for wizard in self.wizards:
                self.handle_additional_gestures_individual(wizard)

    def handle_additional_gestures_individual(self, wizard):

        log.debug("in hagi for {wizard.name}")

        if wizard.hasted:
            #self.add_flavor(wizard.name + " makes a second pair of gestures due to their magical haste!")
            wizard.hasted_duration = wizard.hasted_duration - 1
            if wizard.hasted_duration <= 0:
                self.add_flavor(wizard.name + " returns to normal speed.")
                wizard.hasted = False
                wizard.hasted_duration = 3
        if wizard.permanency_primed:
            wizard.permanency_duration = wizard.permanency_duration - 1
            if wizard.permanency_duration <= 0:
                wizard.permanency_primed = False
                wizard.permanency_duration = 3
                self.add_flavor(wizard.name + "\'s time loop dissipates, unused.")
        if wizard.releasing_delayed_spell:
            wizard.releasing_delayed_spell = False
            actual_spell = wizard.delayed_spell[2]
            self.add_flavor("The potential energy surrounding " + wizard.name + " turns into a " + actual_spell.name + " spell!")
            d_caster, d_target, d_spell = wizard.delayed_spell
            self.add_spell_target(d_caster, d_target, d_spell)
            wizard.delayed_spell = None
        if wizard.delayed_effect_primed:
            spell = self.get_delayed_spell(wizard)
            if spell:
                wizard.delayed_effect_primed = False
                if "Delayed Effect" in wizard.permanencies:
                    wizard.remove_permanency(wizard, "Delayed Effect")
                    if not wizard.permanencies:
                        self.add_flavor("The time loop surrounding " + wizard.name + " fades away.")
                wizard.delayed_effect_duration = 3
                wizard.delayed_spell = spell
                self.spell_targets.remove(spell)
                actual_spell = spell[2] # get the name
                self.add_flavor(wizard.name + "\'s spell, " + actual_spell.name + ", is wound into potentia!")
            else:
                wizard.delayed_effect_duration = wizard.delayed_effect_duration - 1
                if wizard.delayed_effect_duration <= 0:
                    wizard.delayed_effect_primed = False
                    wizard.delayed_effect_duration = 3
                    self.add_flavor(wizard.name + "\'s potential energy unwinds, unused.")

        if wizard.stabbed_this_turn:
            if wizard.amnesia_stab_victim and wizard.amnesiac:
                stab_target = wizard.amnesia_stab_victim
                wizard.clear_enchantment("Amnesia")
            elif wizard.charmed_stab_override:
                stab_target = wizard.charmed_stab_override
                wizard.clear_enchantment("Charm Person")
            else:
                stab_target = self.get_target(wizard, "stab")
            wizard.stab_victim = stab_target
            self.add_stab_target(wizard, stab_target)

        # self.command_existing_monsters()


    def offer_permanency(self, spell_tuple):

        caster, target, spell = spell_tuple

        if caster.permanency_primed:

            client = caster.client
            spell_name = spell.name

            self.msg_client("OFFER_PERMANENCY", client)
            if self.response(self.recv(client), "Client died during OFFER_PERMANENCY request"):
                # OFFER_PERMANENCY_ACK
                self.msg_client(spell_name, client)
                choice = self.recv(client)
                if self.response(choice, "Client died while server waited for Permanency answer."):
                    choice = self.depickle(choice)

                    if choice == True:
                        self.add_flavor("The effects of " + spell.name + " are locked in a time loop on " + target.name + "!")
                        caster.permanency_primed = False
                        caster.permanency_duration = 3
                        target.add_permanency(target, spell.name)
                    else:
                        print(str(choice) + " choice for permanency.")

    def timestopped_process_turn(self, timestopped):

        """ A version of process_turn to be called when a wizard is
            timestopped.  Skips over some things like minion attacks.
        """

        self.resolve_duration_spell("Protection from Evil")

        self.cycle_spell_list(["Delayed Effect"])

        self.handle_protection()

        self.handle_pre_attack_enchantment()

        # Stabs, summon attacks, damaging spells, etc
        self.handle_summoning()
        self.resolve_damage()

        self.process_permanencies()

        self.handle_post_attack_enchantment()

        self.handle_healing()

        self.handle_other_spells()

        while self.spell_list_contains("Raise Dead"):
            self.resolve_spell(self.get_spell_tuple("Raise Dead"))

        # This is called again to let raised grobles and elementals get a new target.
        self.command_existing_monsters()

        self.tick_poison_and_disease(timestopped)
        self.tick_duration_spells(timestopped)

        self.kill_dead()

        if timestopped.paralysis_expiration:
            self.add_flavor(timestopped.name + " regains the use of their " + timestopped.paralysis_expiration + " hand.")

    def process_turn(self):

        """ Do the actual mechanical resolutions of things like spellcasts,
            stabs, groble commands, etc.

        """

        self.resolve_duration_spell("Protection from Evil")

        self.cycle_spell_list(["Delayed Effect"])

        self.handle_protection()

        self.handle_pre_attack_enchantment()

        # Stabs, summon attacks, damaging spells, etc
        self.handle_summoning()
        self.resolve_damage()

        # The following exists to let hasted monsters have a second turn.
        self.command_existing_monsters()
        self.resolve_elemental_attacks()
        self.resolve_groble_attacks()

        self.tick_nonwizard_haste()

        self.process_permanencies()

        self.handle_post_attack_enchantment()

        self.handle_healing()

        self.handle_other_spells()

        while self.spell_list_contains("Raise Dead"):
            self.resolve_spell(self.get_spell_tuple("Raise Dead"))

        # This is called again to let raised grobles and elementals act.
        self.command_existing_monsters()
        self.resolve_damage()

        if self.field_elemental and self.field_elemental not in self.targets:
            self.add_target(self.field_elemental)

        for target in self.targets:
            if target.diseased or target.poisoned:
                self.tick_poison_and_disease(target)
            self.tick_duration_spells(target)

        self.handle_time_stop()

        self.kill_dead()

        for wizard in self.wizards:
            if wizard.paralysis_expiration:
                self.add_flavor(wizard.name + " regains the use of their " + wizard.paralysis_expiration + " hand.")

        if self.field_storm:
            self.add_flavor("The " + self.field_storm + " storm fades away.")

    def tick_poison_and_disease(self, target):

        if target.diseased:
            target.disease_countdown = target.disease_countdown - 1
            self.add_flavor(target.name + " looks increasingly ill as the disease wracks their body.")

        if target.poisoned:
            target.poison_countdown = target.poison_countdown - 1
            self.add_flavor(target.name + " cringes in pain as the poison races through their body.")

        if target.disease_countdown <= 0:
            self.add_flavor("The virulent plague finally takes its toll on " + target.name + "...")
            target.hp = -100
            target.killing_blow = "collapses, suffering catastrophic organ failure."
            target.diseased = False
            target.disease_countdown = 6

        if target.poison_countdown <= 0:
            self.add_flavor("The deadly poison finally takes its toll on " + target.name + "...")
            target.hp = -100
            target.killing_blow = "died in agony, caused by a deadly magical poison."
            target.poisoned = False
            target.poison_countdown = 6

    def cycle_spell_list(self, spell_order):

        for i in range(len(spell_order)):
            while self.spell_list_contains(spell_order[i]):
                self.resolve_spell(self.get_spell_tuple(spell_order[i]))

    def resolve_duration_spell(self, spell_name):

        if spell_name == "Protection from Evil":

            for wizard in self.wizards:
                pfe_duration = wizard.get_spell_duration("Protection from Evil")
                if pfe_duration:
                    # The duration is greater than 0.
                    self.add_flavor(wizard.name + " glows with a protective aura.")
                    wizard.shielded = True

    def resolve_expiring_spells(self):

        """ Resolve expiring spells.
            Expiring spells are a tuple of Targetable target and 
            String spell_name.
        """
        
        expiring_spells = self.expiring_spells

        for spell in expiring_spells:
            target, spell_name = spell

            if spell_name == "Protection from Evil":

                self.add_flavor(target.name + "\'s protective aura fades away.")

            """
            elif spell_name == "Amnesia":

                self.add_flavor(target.name + "\'s seems to remember what they're doing.")
                target.remove_enchantments()

            elif spell_name == "Confusion":

                if type(target) is Wizard:
                    self.add_flavor(target.name + "\'s eyes uncross!")
                target.remove_enchantments()
            """


    def tick_duration_spells(self, target):

        """ Reduce the time of all duration spells by 1. """

        all_duration_spells = target.spell_durations
        for spell_name, duration in all_duration_spells.items():
            if duration > 0:
                new_duration = duration - 1
                target.change_spell_duration(spell_name, new_duration)
                if new_duration <= 0:
                    expiring_spell = (target, spell_name)
                    self.expiring_spells.append(expiring_spell)

        self.resolve_expiring_spells()

    def handle_time_stop(self):

        spell_order = (["Time Stop"])

        self.cycle_spell_list(spell_order)

        timestop = False

        for wizard in self.wizards:
            if wizard.timestopped:
                timestop = True
                self.time_stop_turn(wizard)

        timestopped_minion = False

        for wizard in self.wizards:
            if wizard.minions:
                for minion in wizard.minions:
                    if minion.timestopped:
                        minion.attacked = False
                        timestopped_minion = True
                        timestop = True
                        break
                if timestopped_minion:
                    break
        
        timestopped_elemental = False

        if self.field_elemental and self.field_elemental.timestopped:
            timestopped_elemental = True
            timestop = True

        if timestopped_minion:
            self.resolve_groble_attacks()
        
        if timestopped_elemental:
            self.resolve_elemental_attacks()
        
        if timestop:
            self.add_flavor("The normal flow of time resumes.")

    def time_stop_turn(self, wizard):

        # Get gestures, check if spells are being cast, get stab victims.
        # Resolve only the time stopped spells and stab enemies.  New minions
        # can't attack now.

        print("The clapping of your hands reverberates through the silence of stopped time.")

        self.get_gestures()
        self.get_additional_gestures()
        self.timestopped_process_turn(wizard)

        wizard.timestopped = False

    def handle_protection(self):

        # The highest priority spell is Dispel Magic.

        spell_order = ("Dispel Magic",
                       "Counter-spell",
                       "Counter-spell (alt)",
                       "Magic Mirror",
                       "Remove Enchantment",
                       "Protection from Evil",
                       "Shield",
                       "Resist Heat",
                       "Resist Cold")

        self.cycle_spell_list(spell_order)

    def handle_damaging_spells(self):

        spell_order = ("Magic Missile",
                       "Finger of Death",
                       "Lightning Bolt",
                       "Lightning Bolt (Quick)",
                       "Cause Light Wounds",
                       "Cause Heavy Wounds",
                       "Ice Storm",
                       "Fire Storm",
                       "Fireball")

        self.cycle_spell_list(spell_order)

    def handle_healing(self):

        spell_order = ("Cure Light Wounds",
                       "Cure Heavy Wounds")

        self.cycle_spell_list(spell_order)

    def handle_other_spells(self):

        spell_order = ("Anti-spell",
                       "Poison",
                       "Disease")

        self.cycle_spell_list(spell_order)

    def handle_post_attack_enchantment(self):

        spell_order = ("Amnesia",
                       "Charm Person",
                       "Paralysis",
                       "Fear",
                       "Haste")

        self.cycle_spell_list(spell_order)

    def handle_pre_attack_enchantment(self):

        spell_order = ("Permanency",
                       "Confusion",
                       "Charm Monster",
                       "Blindness",
                       "Invisibility")

        """
                       "Charm Person",
                       "Charm Monster",
                       "Paralysis",
                       "Fear",
                       "Anti-spell")
        """

        self.cycle_spell_list(spell_order)

    def process_permanencies(self):

        """ If an enchantment is permanent, it will remain permanent
        until dispelled. Order of permanency appliance effects does not
        matter.
        
        valid_permanencies = ("Amnesia",
                              "Confusion",
                              "Charm Person",
                              "Delayed Effect",
                              "Paralysis",
                              "Fear",
                              "Protection from Evil",
                              "Blindness",
                              "Invisibility",
                              "Haste")

        """

        for target in self.targets:
            if target.permanencies:
                for effect in target.permanencies:
                    self.add_flavor("The time loop repeats the effects of " + effect + " on " + target.name + "!")
                    if effect == "Amnesia":
                        target.amnesiac = True
                        target.enchantment == "Amnesia"
                    elif effect == "Blindness":
                        target.blinded = True
                        target.blinded_duration = 3
                    elif effect == "Charm Person":
                        if not target.charmed_this_turn:
                            target.charmed_hand, target.charmed_gesture = self.charm_person_get_hand_and_gesture(target.charmer, target)
                            target.charmed = True
                            target.enchantment = "Charm Person"
                    elif effect == "Confusion":
                        if type(target) is Wizard:
                            target.confused = True
                        elif type(target) is Minion:
                            target.confusion_target_override = self.get_random_target()
                        target.enchantment = "Confusion"
                    elif effect == "Delayed Effect":
                        target.delayed_effect_primed = True
                        target.delayed_effect_duration = 3
                    elif effect == "Fear":
                        target.afraid = True
                        target.enchantment = "Fear"
                    elif effect == "Haste":
                        target.hasted = True
                        target.hasted_duration = 3
                    elif effect == "Invisibility":
                        target.invisible = True
                        target.invisible_duration = 3
                    elif effect == "Paralysis":
                        if target.paralysis_expiration:
                            target.paralyzed_hand = target.paralysis_expiration
                            target.paralysis_expiration = ""
                    elif effect == "Protection from Evil":
                        target.change_spell_duration("Protection from Evil", 4)




    def kill_dead(self):

        # Minions

        dying_minions = []

        for wizard in self.wizards:
            for minion in wizard.minions:
                if minion.hp <= 0:
                    dying_minions.append(minion)

        for minion in dying_minions:
            minion.end_turn()
            self.kill_minion(minion)

        # Elementals

        if self.field_elemental:
            if self.field_elemental.hp <= 0:
                self.kill_elemental(self.field_elemental)

        # Wizards

    def kill_elemental(self, elemental):

        """ Kill the elemental immediately. Pass the Elemental object.
        """

        self.add_flavor(self.field_elemental.die())
        self.targets.remove(self.field_elemental)
        self.bury_minion(self.field_elemental)
        self.field_elemental.end_turn()
        self.field_elemental = None

    def kill_minion(self, minion):

        self.add_flavor(minion.die())
        minion.master.remove_minion(minion)
        self.remove_target(minion)
        self.bury_minion(minion)

    def get_delayed_spell(self, caster):

        """ Check all spells to see if any are being cast by the caster.
        If so, offer to delay that spell.
        """

        spell = None

        if caster.delayed_effect_primed:

            delayables = []

            for spell_tuple in self.spell_targets:
                s_caster, s_target, s_spell = spell_tuple
                if s_spell.name != "Delayed Effect" and s_caster == caster:
                    delayables.append(spell_tuple)

            if delayables:

                client = caster.client

                self.msg_client("DELAYED_SPELL_STORE_QUERY", client)
                if self.response(self.recv(client), "Client died while server waited for response to DELAYED_SPELL_STORE_QUERY"):

                    delayable_names = []

                    for delayable_spell_tuple in delayables:
                        delayable_names.append(delayable_spell_tuple[2].name)

                    self.msg_client_pp(delayable_names, client)
                    spell_name = self.recv(client)
                    if self.response(spell_name, "Client died while server waited for delayed spell storage spell name."):
                        spell_name = self.dec(spell_name)

                        print("Received spell_name of " + spell_name)

                        if spell_name == "none":
                            spell = None
                        else:
                            # Find out what the spell is from the string returned.
                            for spell_tuple in delayables:
                                spell_t_name = spell_tuple[2].name
                                print("Comparing " + spell_t_name + " with " + spell_name)
                                if spell_t_name == spell_name:
                                    spell = spell_tuple
                                    break

                        
                """
                print("Spells are being cast on this turn that can be delayed.")
                print("Choose a spell to delay or send Q for none.")
                
                for i,spell_tuple in enumerate(delayables, 1):
                    d_spell = spell_tuple[2]    # 2 is the Spell object.
                    print(str(i) + ". " + d_spell.name)

                while True:
                    choice = input("Choose a spell to delay (Q for none): ")
                    if choice.lower() == "q":
                        break
                    else:
                        try:
                            choice = int(choice) - 1
                            if choice >= 0 and choice < len(delayables):
                                spell = delayables[choice]
                                break
                            else:
                                print("Your choice is invalid.")
                        except ValueError:
                            print("Your choice is invalid.")
                """

        return spell

    def get_permanent_spell(self, caster):

        """ Check if enchantment spells are being cast.
        If they are being cast by the same caster of Permanency, offer to make
        the spell permanent.
        """

        valid_permanencies = ("Amnesia",
                              "Confusion",
                              "Charm Person",
                              "Paralysis",
                              "Fear",
                              "Protection from Evil",
                              "Blindness",
                              "Invisibility",
                              "Haste")

        spell = None

        if caster.permanency_primed:

            permanencies = []

            for spell_tuple in self.spell_targets:
                s_caster, s_target, s_spell = spell_tuple
                if s_spell.name in valid_permanencies and s_caster == caster:
                    permanencies.append(spell_tuple)

            if permanencies:

                client = caster.client

                self.msg_client("GET_PERMANENT", client)
                if self.response(self.recv(client), "Client died before sending GET_PERMANENT_ACK"):
                    permanency_names = []
                    for stt_tuple in permanencies:
                        permanency_names.append(stt_tuple[2].name)

                    data_p = self.pickle(permanency_names)
                    self.msg_client_p(data_p, client)
                    spell_name = self.recv(client)
                    if self.response(spell_name, "Client died before sending spell response for Permanency."):
                        spell_name = self.dec(spell_name)

                        if spell_name == "none":
                            spell = None
                        else:
                            for stt_tuple in permanencies:
                                stt_name = stt_tuple[2].name
                                if spell_name == stt_name:
                                    spell = stt_tuple
                                    break

        return spell

    def get_spell_name_from_spell_tuple(self, spell_tuple):

        return spell_tuple[2]

    def resolve_spell(self, spell_tuple):

        # The tuple is in the format of caster, target, and spell
        
        caster, target, spell = spell_tuple

        self.add_flavor(caster.name + " casts " + spell.name + " at " + target.name + "!")
        if spell_tuple in self.spells_reflected:
            self.add_flavor("...but it was reflected!")
            if spell.name == "Charm Person":
                target_holder = target
                target = caster
                caster = target_holder
            else:
                target = caster
        
        if type(target) is Wizard and target.invisible and target is not caster:
            self.add_flavor("...but the magic fails to find its mark!")
        else:
            if spell.name == "Delayed Effect":

                if target.delayed_spell:
                    self.add_flavor("Potential energy unwinds as " + target.name + "\'s delayed " + target.delayed_spell.name + " is nullified!")
                    target.delayed_spell = None

                self.add_flavor("Potential energy winds around " + target.name + "!")
                target.delayed_effect_primed = True
                target.delayed_effect_duration = 3
            
                delayed_spell = self.get_delayed_spell(target)
            
                if delayed_spell:
                    target.delayed_spell = delayed_spell
                    target.delayed_effect_primed = False
                    if "Delayed Effect" in target.permanencies:
                        target.remove_permanency(target, "Delayed Effect")
                        if not target.permanencies:
                            self.add_flavor("The time loop surrounding " + target.name + " fades away.")
                    self.spell_targets.remove(delayed_spell)
                    actual_spell = delayed_spell[2]
                    self.add_flavor(actual_spell.name + " is wound into potentia!")
                else:
                    self.offer_permanency(spell_tuple)

            elif spell.name == "Dispel Magic":

                # Dispel Magic will stop any spell from working and will remove
                # all enchantments from all beings. All monsters are destroyed,
                # but they can still attack on this turn. We will resolve that
                # by setting their HP to 0, so Raise Dead can still target them.
                # Also acts as a Shield.

                # 1. Eliminate all incoming spells.

                self.add_flavor("A wave of magic-nullifying energy flows through the battlefield!")

                for s_spell_tuple in self.spell_targets:
                    s_caster, s_target, s_spell = s_spell_tuple
                    if s_spell_tuple != spell_tuple:
                        self.add_flavor(s_caster.name + "\'s forming " + s_spell.name + " spell is undone!")

                self.clear_spell_targets()

                # 2. Remove ongoing enchantments.
                # Even if removed now, blindness will not be lifted until the end
                # of the turn (so enemy gestures are hidden)

                for target in self.targets:
                    self.remove_enchantment_flavor(target)
                    target.remove_enchantments_spellcast()

                # 3. Destroy any monsters, but don't do it here -- final death
                # happens later on.

                for wizard in self.wizards:
                    wizard.fire_resistant = False
                    wizard.cold_resistant = False
                    if wizard.minions:
                        for minion in wizard.minions:
                            minion.hp = 0
                            minion.killing_blow = "was unraveled by " + caster.name + "\'s Dispel Magic spell!"

                if self.field_elemental:
                    self.add_flavor(self.field_elemental.name.capitalize() + " was unraveled by " + caster.name + "\'s Dispel Magic spell!")
                    self.field_elemental.hp = 0



                # It also acts as a shield effect.

                target.shielded = True

            elif spell.name.find("Counter-spell") == 0:

                self.add_flavor(target.name + " is blasted by magic-nullifying energy!")

                # The target of the counter-spell is immune to spells cast on them
                # this turn, with the exception of Dispel Magic and Finger of
                # Death.  Dispel Magic is handled in the block prior.

                # It also acts as a shield effect.

                target.counterspelled = True
                target.shielded = True

                # First, get spells that are targeting the target of the
                # Counter-spell.

                spells_to_counterspell = []
                do_not_counterspell = [
                    "Finger of Death",
                    "Fire Storm",
                    "Ice Storm"
                ]

                too_powerful = False

                for spell_targets_tuple in self.spell_targets:
                    stt_caster, stt_target, stt_spell = spell_targets_tuple
                    if target == stt_target:
                        if stt_spell.name == "Finger of Death":
                            too_powerful = True
                        if stt_spell.name not in do_not_counterspell:
                            if spell_targets_tuple is not spell_tuple:
                                spells_to_counterspell.append(spell_targets_tuple)
                                

                # Now we have a list of spells to counterspell.

                for spell in spells_to_counterspell:
                    s_caster, s_target, s_spell = spell
                    self.add_flavor(s_caster.name + "\'s " + s_spell.name + " spell was cancelled by a Counter-spell cast on " + s_target.name + " by " + caster.name + "!")
                    self.spell_targets.remove(spell)

                if too_powerful:
                    self.add_flavor("...but a spell was too powerful to be stopped!")

                """
                minions_to_remove = []

                for wizard in self.wizards:
                    if wizard.minions:
                        for minion in wizard.minions:
                            if not minion.counterspelled:
                                self.kill_minion(minion, "was undone by " + caster.name + "\'s Counter-spell before it fully coalesced!")
                                minions_to_remove.append(minion)
                            else:
                                self.add_flavor(minion.name + " is fully summoned thanks to its Counter-spell protection!")

                if minions_to_remove:
                    for minion in minions_to_remove:
                        minion.master.remove_minion(minion)
                """

            elif spell.name == "Magic Mirror":

                # Any spells targeting the subject of Magic Mirror will find their
                # magic turned against them!  This has no effect on storm spells.

                # First, don't do anything if the target is already mirrored.

                #if target.mirrored:
                #    self.add_flavor(caster.name + "\'s Magic Mirror melds with " + target.name + "\'s existing mirror!")
                #else:

                if not target.mirrored:
                    self.add_flavor("A Magic Mirror shimmers into being in front of " + target.name + "!")
                else:
                    self.add_flavor("The new Magic Mirror melds into the original!")

                for spell_target_tuple in self.spell_targets:
                    if spell_target_tuple is not spell_tuple:
                        stt_caster, stt_target, stt_spell = spell_target_tuple
                        if stt_target is target:
                            if stt_target is not stt_caster:
                                if stt_spell.name != "Magic Mirror" and stt_spell.name != "Finger of Death":
                                    self.add_spell_reflection(spell_target_tuple)

                target.mirrored = True

            elif spell.name == "Remove Enchantment":

                # Terminates enchantment spells before they can be cast on the target.
                # Also destroy any minions, but they must be allowed to attack first.

                # First, eliminate any Enchantment spells targeting the target.

                enchantment_spell_list = ("Amnesia",
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
                            "Permanency")

                spell_tuples_to_remove = []

                for s_spell_tuple in self.spell_targets:
                    if s_spell_tuple is not spell_tuple:
                        s_caster, s_target, s_spell = s_spell_tuple
                        if s_target == target:
                            if s_spell.name in enchantment_spell_list:
                                self.add_flavor("The " + s_spell.name + " enchantment spell cast against " + s_target.name + " is nullified!")
                                spell_tuples_to_remove.append(s_spell_tuple)

                for r_spell_tuple in spell_tuples_to_remove:
                    self.spell_targets.remove(r_spell_tuple)

                # Even if the target is being destroyed (in the case of Minions
                # and Elementals), we still want to remove any debilitating
                # enchantments that might be affecting them this turn.

                self.remove_enchantment_flavor(target)

                target.remove_enchantments_spellcast()

                # Next, is the target a Wizard or a Minion/Elemental?

                if type(target) is Minion:
                    self.add_flavor("The spell begins to unravel the magic composing " + target.name + "!")
                    self.add_flavor(target.name + " gives a warcry as they prepare their final attack!")
                    target.hp = 0
                    target.killing_blow = "was unraveled by " + caster.name + "\'s Remove Enchantment spell."
                elif type(target) is Elemental:
                    self.add_flavor("The spell begins to unravel the magic composing " + target.name + "!")
                    target.end_turn_death = True
                    target.killing_blow = "was unraveled by " + caster.name + "\'s Remove Enchantment spell."
                else:
                    # Enchantment spells targeting this wizard have already been erased, so get rid of anything ongoing.
                    pass

            elif spell.name == "Permanency":

                self.add_flavor("A visible time loop begins to manifest around " + target.name + " at " + caster.name + "\'s command!")

                """
                spell_tuple = self.get_permanent_spell(caster)

                if spell_tuple:
                    spell_name = self.get_spell_name_from_spell_tuple(spell_tuple)
                    target.permanencies.append(spell_name)
                    self.add_flavor(spell_name + " is locked in a time loop on " + target.name + "!")
                else:
                """

                target.permanency_primed = True
                target.permanency_duration = 3

            elif spell.name == "Protection from Evil":

                # This is a shield effect for this turn and the next three turns.

                if target.spell_has_active_duration("Protection from Evil"):
                    self.add_flavor(target.name + "\'s aura glows with a new light!")
                else:
                    self.add_flavor(target.name + " glows with a protective aura!")

                target.shielded = True
                target.change_spell_duration("Protection from Evil", 4)
                self.offer_permanency(spell_tuple)

            elif spell.name == "Shield":

                # A very simple resolution. A shield will protect from summoned
                # monster attacks (including elementals), stabs, and Magic
                # Missile.

                if target.shielded:
                    self.add_flavor("The two shields merge into one.")
                else:
                    self.add_flavor(target.name + " is protected by a magical shield!")

                target.shielded = True

            elif spell.name == "Resist Heat":

                if target == self.field_elemental:
                    if self.field_elemental.element == "fire":
                        self.add_flavor("The fire elemental resists its own heat and fizzles out!")
                        self.field_elemental.hp = 0
                    else:
                        self.add_flavor("The ice elemental absorbs the Resist Fire spell!")
                else:
                    self.add_flavor(target.name + " feels they could brave a volcano!")
                    target.fire_resistant = True

            elif spell.name == "Resist Cold":

                if target == self.field_elemental:
                    if self.field_elemental.element == "ice":
                        self.add_flavor("The ice elemental resists itself and melts!")
                        self.field_elemental.hp = 0
                    else:
                        self.add_flavor("The fire elemental absorbs the Resist Cold spell!")
                else:
                    self.add_flavor(target.name + " feels they could outlast a blizzard!")
                    target.cold_resistant = True

            elif spell.name == "Raise Dead":

                client = target.client

                self.add_flavor(target.name + " wields the power to give life to the dead!")

                self.msg_client("RAISE_DEAD", client)
                ack = self.recv(client)

                if self.response(ack, "Client died while processing RAISE_DEAD"):
                    ack = self.dec(ack)

                    if ack == "RAISE_DEAD_ACK":

                        minion_graveyard_c = self.targetables_to_targetableclients(self.minion_graveyard)
                        living_targets_c = self.targetables_to_targetableclients(self.targets)

                        data_p = [minion_graveyard_c, living_targets_c]

                        self.msg_client_pp(data_p, client)
                        c_target = self.recv(client)

                        if self.response(c_target, "Client died before sending target for Raise Dead."):
                            c_target = self.dec(c_target)
                            
                            found = False
                            undead = False

                            for dead in self.minion_graveyard:
                                if dead.name == c_target:
                                    target = dead
                                    undead = True
                                    found = True
                                    break

                            if not found:
                                for alive in self.targets:
                                    if alive.name == c_target:
                                        target = alive
                                        found = True
                                        break

                            if not found:
                                print("Could not find target by the name of [" + c_target + "]")

                            if undead:
                                zombie = target
                                self.add_flavor(zombie.name.title() + " is raised from the dead by " + caster.name + "!")
                                zombie.hp = zombie.maxhp
                                if type(zombie) is Minion:
                                    zombie.master = caster
                                    zombie.original_master = caster
                                    zombie.master.add_minion(zombie)
                                    self.add_target(zombie)
                                    self.command_existing_monsters()
                                    self.minion_graveyard.remove(zombie)
                                elif type(zombie) is Elemental:
                                    # Let finalize_elemental_summon() handle adding
                                    # the target and removing from the graveyard,
                                    # since there are special cases regarding multiple
                                    # elementals being summoned.
                                    self.finalize_elemental_summon(zombie.element)

                            else:
                                # Living target!
                                self.add_flavor(target.name.title() + " is revitalized by the spell!")
                                target.hp = target.hp + 5

            elif spell.name == "Cure Light Wounds":

                target.hp = target.hp + 1
                self.add_flavor(target.name + " looks healthier. (+1 HP)")

            elif spell.name == "Cure Heavy Wounds":

                target.hp = target.hp + 2
                self.add_flavor(target.name + " looks healthier. (+2 HP)")
                if target.diseased:
                    target.diseased = False
                    target.disease_countdown = 6
                    self.add_flavor(target.name + "\'s Disease is cured!")

            elif spell.name == "Magic Missile":

                if target.shielded and not target.get_spell_duration("Protection from Evil"):
                    self.add_flavor("...but it is deflected by " + target.name + "\'s shield!")
                elif target.shielded and target.get_spell_duration("Protection from Evil"):
                    self.add_flavor("...but " + target.name + "\'s protective aura bends the missile away!")
                else:
                    hit_loc = self.get_random_body_part()
                    self.add_flavor("...and they are struck in the " + hit_loc + " for 1 damage!")
                    target.killing_blow = "lanced through the " + hit_loc + " by a magic missile."
                    target.hp = target.hp - 1

            elif spell.name == "Finger of Death":

                if target.shielded:
                    self.add_flavor(caster.name + "\'s Finger of Death passes through " + target.name + "\'s shield!")

                if target.mirrored:
                    self.add_flavor(caster.name + "\'s Finger of Death shatters the feeble mirror spell!")

                if target.counterspelled:
                    self.add_flavor(caster.name + "\'s Finger of Death warps around the protective Counter-spell!")

                self.add_flavor(target.name + "\'s flesh is scoured from their bones by the beam of pure entropic power!")
                target.killing_blow = "was blasted to dust by " + caster.name + "\'s Finger of Death."
                target.hp = target.hp - 100

            elif spell.name == "Lightning Bolt" or spell.name == "Lightning Bolt (Quick)":

                if target.shielded:
                    self.add_flavor(caster.name +"\'s Lightning Bolt breaks through " + target.name + "\'s shield!")

                self.add_flavor(target.name + " is electrocuted by a lightning bolt for 5 damage!")
                target.killing_blow = "was flash-fried by " + caster.name + "\'s Lightning Bolt."
                target.hp = target.hp - 5

            elif spell.name == "Cause Light Wounds":

                self.add_flavor(target.name + " feels a sharp pain in their head for 2 damage.")
                target.killing_blow = "collapses, suffering critical brain damage."
                target.hp = target.hp - 2

            elif spell.name == "Cause Heavy Wounds":

                self.add_flavor(target.name + " feels a sudden spike of pain throughout their body!")
                target.killing_blow = "suffered catastrophic organ failure."
                target.hp = target.hp - 3

            elif spell.name == "Ice Storm":

                # Is a fire storm being cast?

                for s_spell_tuple in self.spell_targets:
                    s_spell = s_spell_tuple[2]
                    if s_spell.name == "Fire Storm":
                        self.firestorm = True
                        break

                if self.firestorm:
                    self.add_flavor("The wind whistles and the temperature drops as an ice storm starts to take shape...")
                    # This will finish resolving in Fire Storm.
                else:
                    
                    if self.field_storm == "ice":
                        self.add_flavor("The two ice storms merge into one!")
                    else:
                        elemental_cancellation = False

                        if self.field_elemental:
                            if self.field_elemental.element == "fire":
                                elemental_cancellation = True

                        if elemental_cancellation:
                            self.add_flavor("...but the fire elemental roars and blasts the ice storm away!")
                        else:
                            self.add_flavor("A blizzard rages through the battlefield!")
                            for target in self.targets:
                                if target.cold_resistant:
                                    self.add_flavor(target.name.title() + " braves the weather with their cold resistance!")
                                else:
                                    self.add_flavor(target.name + " is blasted by the arctic might of the storm for 5 damage!")
                                    target.hp = target.hp - 5
                            self.field_storm = "ice"

            elif spell.name == "Fire Storm":

                # Is an ice storm happening?

                # This is unintuitive. This is set to true by Ice Storm if it
                # detects that a Fire Storm is being cast in the same turn.
                if self.firestorm:
                    self.add_flavor("...but a sudden blast of heat blows the brewing ice storm away and then dissolves into steam!")
                    self.firestorm = False
                else:

                    if self.field_storm == "fire":
                        self.add_flavor("The two fire storms merge into one!")
                    else:                
                        elemental_cancellation = False

                        if self.field_elemental:
                            if self.field_elemental.element == "ice":
                                elemental_cancellation = True

                        if elemental_cancellation:
                            self.add_flavor("...but the ice elemental focuses on the brewing storm and freezes the heating air before it ignites!")
                        else:
                            self.add_flavor("A firestorm rages through the battlefield!")
                            for target in self.targets:
                                if target.fire_resistant:
                                    self.add_flavor(target.name + " brushes off the heat with their fire resistance!")
                                else:
                                    self.add_flavor(target.name + " is incinerated by the firestorm for 5 damage!")
                                    target.hp = target.hp - 5
                            self.field_storm = "fire"

            elif spell.name == "Fireball":

                fireball_safety = False

                if self.field_storm == "ice":
                    fireball_safety = True
                    
                if target.shielded:
                    self.add_flavor("The Fireball passes through " + target.name + "\'s shield!")

                if target.fire_resistant:
                    self.add_flavor("...but it splashes harmlessly against their fire resistance!")
                else:      
                    if type(target) is Elemental:
                        if target.element == "ice":
                            self.add_flavor("The ice elemental is immediately melted by the fireball!")
                            self.field_elemental.hp = 0
                    else:
                        if fireball_safety:
                            self.add_flavor("The fireball miraculously restores their normal body temperature! (+5 HP)")
                            target.hp = target.hp + 5
                        else:
                            self.add_flavor(target.name + " is blasted by the fireball for 5 damage!")
                            target.hp = target.hp - 5

            elif spell.name == "Amnesia":

                # Since all enchantments will be checking for other enchantments,
                # the checks have been moved to an individual function.

                # check_enchantments will return True if they do not have any
                # enchantments, otherwise False.

                continue_enchantment = self.check_enchantments(target, "Amnesia")

                if continue_enchantment:

                    if type(target) is Wizard:
                        self.add_flavor(target.name + " feels forgetful and begins to repeat their gestures.")
                        if target.stab_victim:
                            target.amnesia_stab_victim = target.stab_victim
                    else:
                        # It's a minion. Elemental targeting of Amnesia is forbidden in get_target.
                        self.add_flavor(target.name + " looks forgetful and raises their weapon at " + target.target.name + " again!")
                        target.amnesia_target_override = target.target
                    target.enchantment = "Amnesia"
                    target.amnesiac = True
                    #target.change_spell_duration("Amnesia", 2)

                    self.offer_permanency(spell_tuple)

            elif spell.name == "Confusion":

                continue_enchantment = self.check_enchantments(target, "Confusion")

                if continue_enchantment:

                    if type(target) is Wizard:
                        self.add_flavor(target.name + "\'s eyes cross!")
                    else:
                        self.add_flavor(target.name + " looks dizzy and turns to a random target!")
                        target.confusion_target_override = self.get_random_target()

                    target.enchantment = "Confusion"
                    target.confused = True
                    #target.change_spell_duration("Confusion", 2)

                    self.offer_permanency(spell_tuple)

            elif spell.name == "Charm Person":

                continue_enchantment = self.check_enchantments(target, "Charm Person")

                if continue_enchantment:

                    if type(target) is Wizard:
                        charmed_hand, charmed_gesture = self.charm_person_get_hand_and_gesture(caster, target)
                        target.charmed_this_turn = True
                        target.charmer = caster
                        target.charmed_hand = charmed_hand
                        target.charmed_gesture = charmed_gesture
                        self.add_flavor(caster.name + " takes control of " + target.name + "\'s " + charmed_hand + " hand!")
                        target.enchantment = "Charm Person"
                        self.offer_permanency(spell_tuple)
                    else:
                        self.add_flavor(target.name + " looks flattered that " + caster.name + " considers them a person, but is unaffected.")
                        target.enchantment = "Charm Person"

            elif spell.name == "Charm Monster":

                continue_enchantment = self.check_enchantments(target, "Charm Monster")

                if continue_enchantment:

                    if type(target) is Wizard:
                        self.add_flavor("While " + target.name + " is indeed monstrous, they are unaffected by the spell.")
                        target.enchantment = "Charm Monster"
                    else:
                        # Minion
                        for spell_tuple in self.spell_targets:
                            caster, target, spell = spell_tuple
                            if spell.name == "Charm Monster":
                                if caster == target.original_master and not target.mirrored:
                                    target.resist_charm = True
                                    break

                        if target.resist_charm and caster != target.original_master:
                            self.add_flavor(target.name + " looks dizzy as they struggle against the charm!")
                        elif target.resist_charm and caster == target.original_master:
                            self.add_flavor(target.name + " struggles against the charm, but gives " + target.original_master.name + " a loyal nod!")
                        else:
                            self.add_flavor(target.name + " gives " + caster.name + " a look of adoration and loyalty!")
                            # Change the master of the target
                            target.master.remove_minion(target)
                            caster.add_minion(target)
                            target.commanded = False
                            self.command_existing_monsters()
                            target.enchantment = "Charm Monster"

            elif spell.name == "Paralysis":

                continue_enchantment = self.check_enchantments(target, "Paralysis")
                if continue_enchantment:

                    if type(target) is Wizard:
                        if target.paralysis_expiration:
                            hand = target.paralysis_expiration
                            target.paralysis_expiration = ""
                            self.add_flavor(target.name + "\'s " + hand + " hand has been paralyzed again!")
                        elif target.paralyzed_hand:
                            hand = target.paralyzed_hand
                            self.add_flavor(target.name + "\'s " + target.paralyzed_hand + " hand has been paralyzed again!")
                        else:
                            hand = self.paralysis_choose_hand(caster, target)
                            self.add_flavor(target.name + "\'s " + hand + " hand has been paralyzed by magic!")
                        target.paralysis = True
                        target.paralyzed_hand = hand
                        target.enchantment = "Paralysis"
                    else:
                        # Minion
                        if target.paralyzed:
                            self.add_flavor(target.name + "\'s looks increasingly stiff!")
                        else:
                            self.add_flavor(target.name + "\'s goes still as the magic takes hold!")
                            target.paralyzed = True
                            target.enchantment = "Paralysis"

                    self.offer_permanency(spell_tuple)

            elif spell.name == "Fear":

                continue_enchantment = self.check_enchantments(target, "Fear")
                if continue_enchantment:

                    if type(target) is Wizard:
                        self.add_flavor(target.name + "\'s mind is filled with fear!")
                        self.offer_permanency(spell_tuple)
                    else:
                        self.add_flavor(target.name + " trembles, but clings tightly to their weapon, overcoming fear!")
                    target.afraid = True
                    target.enchantment = "Fear"

                    

            elif spell.name == "Anti-spell":

                self.add_flavor(target.name + " is blasted by anti-magic, erasing their accumulating spells!")
                target.erase_history()
                self.erase_perceived_history(target)

            elif spell.name == "Disease":

                if target.diseased:
                    self.add_flavor(target.name + " looks slightly healthier as the magical disease is overwritten!")
                else:
                    self.add_flavor(target.name + " looks ill as a magical disease takes hold!")
                target.diseased = True
                target.disease_countdown = 6

            elif spell.name == "Poison":

                if target.poisoned:
                    self.add_flavor(target.name + " scowls as the magical poison is reintroduced to their bloodstream.")
                else:
                    self.add_flavor(target.name + " cries out in pain as a magical poison races through their veins!")
                target.poisoned = True
                target.poison_countdown = 6

            elif spell.name == "Blindness":

                if type(target) is Minion:
                    # Blinded monsters are INSTANTLY killed without attacking.
                    target.killing_blow = "died by hitting themself with their weapon while blinded!"
                    self.kill_minion(target)
                elif type(target) is Elemental:
                    self.add_flavor("The elemental's head is vaporized by the compounding magical effects!")
                    target.killing_blow = target.name + "\'s head is vaporized by the blinding magic! It is destroyed!"
                    self.kill_elemental(target)
                else:
                    # Wizard!
                    self.add_flavor(target.name + "\'s sight is stolen by the blindness enchantment!")
                    target.blinded = True
                    target.blinded_duration = 3
                    self.offer_permanency(spell_tuple)
            
            elif spell.name == "Invisibility":

                if type(target) is Minion:
                    # Blinded monsters are INSTANTLY killed without attacking.
                    target.killing_blow = "is killed by a magical overload, parts vanishing!"
                    self.kill_minion(target)
                elif type(target) is Elemental:
                    self.add_flavor("The elemental and its oppressive presence vanishes, destroyed by a magical overload!")
                    self.kill_elemental(target)
                else:
                    # Wizard!
                    self.add_flavor(target.name + " vanishes!")
                    target.invisible = True
                    self.offer_permanency(spell_tuple)

            elif spell.name == "Haste":

                if target.hasted:
                    self.add_flavor(target.name + "\'s additional speed is extended!")
                    target.hasted_duration = 3
                else:
                    self.add_flavor(target.name.title() + " starts moving faster!")
                    target.hasted = True
                    target.hasted_duration = 3

            elif spell.name == "Time Stop":

                self.add_flavor("For an instant, time stops at " + caster.name + "\'s command.")
                target.timestopped = True

        if self.spell_targets:
            if spell_tuple in self.spell_targets:
                self.spell_targets.remove(spell_tuple)

    def paralysis_choose_hand(self, caster, target):

        client = caster.client

        self.msg_client("ENCHANTMENT_PARALYSIS", client)
        print("Sent ENCHANTMENT_PARALYSIS to client, waiting on PARALYSIS_ACK")
        ack = self.recv(client)
        if self.response(ack, "Client died while server waited on PARALYSIS_ACK"):
            ack = self.dec(ack)

            if ack == "PARALYSIS_ACK":

                self.msg_client_pp(target.name, client)
                print("Received PARALYSIS_ACK, sent pickled target name")
                choice = self.recv(client)
                if self.response(choice, "Client died while server waited on paralysis choice."):
                    choice = int(self.dec(choice))
                    print("Received paralysis choice from client")

                    if choice == 1:
                        return "left"
                    elif choice == 2:
                        return "right"
                    else:
                        print("paralysis_choose_hand returned unknown choice.")
                        return "left"

    def charm_person_get_hand_and_gesture(self, caster, target):

        """ Get the hand and gesture to use for Charm Person.
        """

        client = caster.client

        self.msg_client("ENCHANTMENT_CHARM_PERSON", client)
        if self.response(self.recv(client), "Client died while server waiting for response after sending CHARM_PERSON"):
            # Send the enemy name as an encoded string.
            self.msg_client(target.name, client)
            data_p = self.recv(client)
            if self.response(data_p, "Client died while server waited on charm person choices."):
                charmed_hand, charmed_gesture = self.depickle(data_p)
                # We are expecting it in the form "left", "c" for example.
                if charmed_gesture == "$":
                    target.charmed_stab_override = self.get_target(caster, "stab by " + target.name)

                charm_tuple = (charmed_hand.lower(), charmed_gesture.lower())

                return charm_tuple

        """
        print(caster.name + ": Choose which of " + target.name + "\'s hands will be controlled.")
        
        caster.show_hands_history_others()

        hands = ("Left", "Right")

        for i,hand in enumerate(hands, 1):
            print(str(i) + ". " + hand)

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
                    print("Your choice is invalid.")
            except ValueError:
                print("Your choice is invalid.")

        print(caster.name + ": Enter a gesture for " + target.name + "\'s " + charmed_hand.lower() + " hand.")

        target.show_hands_history()

        valid_gestures = ("f", "p", "s", "w", "d", "c", "$")

        while True:
            choice = input("Choose a gesture (f/p/s/w/d/c/$): ")
            if choice.lower() in valid_gestures:
                charmed_gesture = choice
                if charmed_gesture == "$":
                    target.charmed_stab_override = self.get_target(caster, "stab by Saruman")
                break
            else:
                print("Your choice is invalid.")
                """
            
        charm_tuple = (charmed_hand.lower(), charmed_gesture.lower())

        return charm_tuple

    def remove_enchantment_flavor(self, target):

        if target.diseased:
            self.add_flavor(target.name + " looks healthier as the magical disease is erased!")

        if target.poisoned:
            self.add_flavor(target.name + " looks healthier as the magical poison is erased!")

        if target.amnesiac:
            self.add_flavor(target.name + " seems less forgetful.")

        if target.charmed:
            if type(target) is Wizard:
                self.add_flavor(target.name + " regains control of their " + target.charmed_hand + " hand!")
            if type(target) is Minion:
                self.add_flavor(target.name + "\'s eyes uncloud as it looks at " + target.original_master.name + " with loyalty!")

        if target.afraid:
            self.add_flavor(target.name + " musters their courage!")

        if target.confused:
            self.add_flavor(target.name + " seems less confused.")
        
        if target.paralysis:
            self.add_flavor(target.name + " seems more limber!")

        if target.spell_has_active_duration("Protection from Evil"):
            self.add_flavor(target.name + "\'s protective aura fades away!")

        if target.fire_resistant:
            self.add_flavor(target.name + " looks flammable again!")

        if target.cold_resistant:
            self.add_flavor(target.name + " looks suddenly chilly!")

        if target.hasted:
            self.add_flavor(target.name + " slows down!")

        if type(target) is Wizard:
            if target.delayed_spell:
                self.add_flavor(target.name + " is startled as the " + target.delayed_spell[2].name + " spell held in reserve is suddenly nullified in a blast of magical sparks!")
            if target.permanency_primed:
                self.add_flavor(target.name + "\'s primed time loop is broken!")
            if target.permanencies:
                self.add_flavor(target.name + " is released from the time loop!")
            if target.invisible:
                self.add_flavor(target.name + " suddenly reappears!")
            if target.blinded:
                self.add_flavor(target.name + " can see again!")

    def get_random_target(self):
        
        random_target = randint(0, len(self.targets)-1)
        return self.targets[random_target]

    def check_enchantments(self, target, incoming_enchantment):

        # First, see if any other enchantment spells are being cast on the target.

        enchantment_spells = ("Amnesia",
                              "Confusion",
                              "Charm Person",
                              "Charm Monster",
                              "Paralysis",
                              "Fear")

        warp_enchantment = False

        for spell_tuple in self.spell_targets:
            st_spell = spell_tuple[2]
            st_target = spell_tuple[1]
            if st_spell.name in enchantment_spells:
                if st_target == target:
                    if st_spell.name != incoming_enchantment:
                        # An enchantment that is not this enchantment is being cast.
                        warp_enchantment = True
                        break

        if warp_enchantment:
            self.add_flavor("...but the enchantment begins to warp!")
            target.enchantment_cancel = True
            return False

        # First, see if the target is already being afflicted by multiple enchantments.
       
        if target.enchantment_cancel:
            self.add_flavor("The conflicting enchantments fizzle out!")
            return False
        else:
            if target.enchantment and target.enchantment != incoming_enchantment:
                # Yes, they have an enchantment. Turn on multi-enchantment,
                # to signal that no enchantments will work this turn.
                self.add_flavor("...but the multiple enchantments upon them cancel each other out!")
                target.remove_enchantments()
                target.enchantment_cancel = True
                return False
            else:
                # Silently fail the enchantment. Messages will be handled
                # elsewhere.
                if warp_enchantment:
                    return False
                else:
                    # The target does not have any enchantments, so assign
                    # the enchantment to them.
                    return True

    def resolve_damage(self):
        
        """
        This section handles stabs, monster attacks, and spells that deal
        damage directly.

        The order of resolution doesn't particularly matter.
        """

        # Start taking damage

        self.handle_damaging_spells()
        self.resolve_stabs()

        timestopped_wizard = False

        for wizard in self.wizards:
            if wizard.timestopped:
                timestopped_wizard = True

        if not timestopped_wizard:
            self.resolve_groble_attacks()
            self.resolve_elemental_attacks()
            
    def resolve_stabs(self):

        for stab_tuple in self.stab_targets:
                stabber, stabbed = stab_tuple
                if not stabber.already_stabbed:
                    if stabbed.hp < 1:
                        self.add_flavor(stabber.name + " stabs at " + stabbed.name + "\'s corpse with their dagger!")
                    else:
                        self.add_flavor(stabber.name + " stabs at " + stabbed.name + " with their dagger!")
                    if stabbed.invisible:
                        self.add_flavor("...but they stab at thin air!")
                    elif stabbed.shielded and not stabbed.get_spell_duration("Protection from Evil"):
                        self.add_flavor("...but it is deflected by " + stabbed.name + "\'s shield!")
                    elif stabbed.shielded and stabbed.get_spell_duration("Protection from Evil"):
                        self.add_flavor("...but " + stabbed.name + "\'s protective aura bends the stab away!")
                    else:
                        if stabbed.hp < 1:
                            self.add_flavor("...and looks confused because they're already dead.")
                        else:
                            hit_loc = self.get_random_body_part()
                            self.add_flavor("...and hits them in the " + hit_loc + " for 1 damage!")
                            stabbed.hp = stabbed.hp - 1
                            stabbed.killing_blow = "was stabbed to death by " + stabber.name + "!"
                    stabber.already_stabbed = True

    def resolve_groble_attacks(self):

        """ Receives a list of minions.

        Get their targets and then do damage to them.
        """

        attacker_list = []

        for wizard in self.wizards:
            for minion in wizard.minions:
                if minion.target and not minion.attacked:
                    attacker_list.append(minion)

        for attacker in attacker_list:
            if attacker.timestopped:
                attacker.attacked = False
            if not attacker.attacked:
                if attacker.paralyzed:
                    self.add_flavor(attacker.name + " is unable to act due to paralysis!")
                    attacker.paralyzed = False
                else:
                    if attacker.amnesia_target_override and attacker.amnesiac:
                        target = attacker.amnesia_target_override
                        self.add_flavor(attacker.name + " seems forgetful, and faces its previous target!")
                        attacker.clear_enchantment("Amnesia")
                    elif attacker.confusion_target_override:
                        target = attacker.confusion_target_override
                        self.add_flavor(attacker.name + " faces " + target.name + ", looking confused!")
                        attacker.enchantment = ""
                        attacker.clear_enchantment("Confusion")
                    else:
                        target = attacker.target
                    damage = attacker.damage
                    self.add_flavor(attacker.name + ", " + attacker.master.name + "\'s minion, swings at " + target.name + "!")
                    if target.invisible:
                        self.add_flavor("...but they swing at nothing!")
                    elif attacker.timestopped:
                        if target.shielded:
                            self.add_flavor(target.name + " cannot defend themself against the time-stopped monster!")
                        self.groble_do_damage(attacker, target, damage)
                        attacker.timestopped = False
                    elif target.shielded and not target.get_spell_duration("Protection from Evil"):
                       self.add_flavor("...but it is deflected by " + target.name + "\'s shield!")
                    elif target.shielded and target.get_spell_duration("Protection from Evil"):
                        self.add_flavor("...but " + target.name + "\'s protective aura bends the swing away!")
                    else:
                        self.groble_do_damage(attacker, target, damage)
                if attacker.hasted and attacker.haste_attacked_this_turn:
                    attacker.attacked = True
                if attacker.hasted and not attacker.haste_attacked_this_turn:
                    self.add_flavor("The accelerated monster raises its weapon a second time!")
                    attacker.haste_attacked_this_turn = True
                    attacker.commanded = False
                else:
                    attacker.attacked = True

    def groble_do_damage(self, attacker, target, damage):

        hit_loc = self.get_random_body_part()
        self.add_flavor("...and hits them in the " + hit_loc + " for " + str(damage) + " damage!")
        target.hp = target.hp - damage
        target.killing_blow = "was beaten to death by " + attacker.name + "!"

    def tick_nonwizard_haste(self):

        for target in self.targets:
            if target.hasted:
                target.hasted_duration = target.hasted_duration - 1
                if target.hasted_duration <= 0:
                    target.hasted = False
                    target.hasted_duration = 3
                    self.add_flavor(target.name + " returns to normal speed.")

    def resolve_elemental_attacks(self):
        
        if self.field_elemental and self.field_elemental.timestopped:
            self.field_elemental.attacked = False

        if self.field_elemental and self.field_elemental.hp > 0 and not self.field_elemental.attacked:
            element = self.field_elemental.element
            if element == "fire":
                self.add_flavor("The fire elemental releases a scorching flare of heat!")
            else:
                self.add_flavor("The ice elemental releases a freezing wave of cold!")
            for target in self.targets:
                if target is not self.field_elemental:
                    if self.field_elemental.timestopped:
                        self.add_flavor("Nothing can stop the attack from the time-stopped " + element + " elemental!")
                        self.elemental_do_damage(element, target)
                    elif target.shielded:
                        self.add_flavor(target.name + " is shielded from the attack!")
                    elif element == "fire" and target.fire_resistant:
                        self.add_flavor(target.name + " absorbs the heat with their fire resistance!")
                    elif element == "ice" and target.cold_resistant:
                        self.add_flavor(target.name + " absorbs the frost with their cold resistance!")
                    else:
                        self.elemental_do_damage(element, target)
            if self.field_elemental.hasted and self.field_elemental.haste_attacked_this_turn:
                self.field_elemental.attacked = True
            elif self.field_elemental.hasted and not self.field_elemental.haste_attacked_this_turn:
                self.add_flavor("The accelerated " + self.field_elemental.element + " elementals prepares for a second attack!")
                self.field_elemental.haste_attacked_this_turn = True
            else:
                self.field_elemental.attacked = True
            if self.field_elemental.end_turn_death:
                self.field_elemental.hp = 0
                self.field_elemental.end_turn_death = False

    def elemental_do_damage(self, element, target):

        if element == "fire":
            self.add_flavor(target.name + " is blasted by heat for 3 HP!")
        else:
            self.add_flavor(target.name + " is chilled to the bone for 3 HP!")
        target.hp = target.hp - 3

    def spell_list_contains(self, spell_name):
        
        for spell in self.spell_targets:
            # This is a tuple of caster, target, spell.
            name = spell[2].name
            if name == spell_name:
                return True
            
        return False        

    def get_spell_tuple(self, spell_name):
        """ Return the first instance of the spell encountered in the spell
            encountered in the spell_targets list.
        """

        for spell_tuple in self.spell_targets:
            spell = spell_tuple[2]
            if spell.name == spell_name:
                return spell_tuple

        # Shouldn't happen
        return None

    def handle_summoning(self):

        # Handle Elementals first since they can't be commanded.

        self.handle_elemental_summon()
        self.handle_groble_summon()

    def handle_elemental_summon(self):

        spell_targets = self.spell_targets

        for spell_tuple in spell_targets:
            caster, target, spell = spell_tuple
            if spell.name == "Summon Elemental":
                if self.field_elemental:
                    print("An elemental of " + self.field_elemental.element + " is present on the field.")

                client = caster.client

                self.msg_client("SUMMON_ELEMENTAL", client)
                if self.response(self.recv(client), "Client died while server waited for SUMMON_ELEMENTAL_ACK"):
                    self.msg_client("SUMMON_ELEMENTAL_CONTINUE", client)
                    element = self.recv(client)
                    if self.response(element, "Client died while server waited on elemental type."):
                        element = int(self.dec(element))

                        if element == 1:
                            self.finalize_elemental_summon("fire")
                        elif element == 2:
                            self.finalize_elemental_summon("ice")
                        else:
                            print("Received unknown element choice, using fire")
                            self.finalize_elemental_summon("fire")

    def finalize_elemental_summon(self, element):

        if self.field_elemental:
            if self.field_elemental.element is element:
                self.add_flavor("A " + element + " elemental is summoned, but is absorbed into the existing " + element + " elemental!")
            else:
                self.add_flavor("An opposing elemental tries to take form, but they destroy each other in a blast of ice and fire!")
                new_elemental = Elemental(element)
                
                new_elemental.hp = 0
                self.field_elemental.hp = 0
                self.bury_minion(new_elemental)
                self.bury_minion(self.field_elemental)

                self.remove_target(self.field_elemental)
                self.field_elemental = None
        else:
            if element == ("fire"):
                self.add_flavor("The battlefield erupts into flame as a fire elemental whirls into being!")
            else:
                self.add_flavor("The battlefield is drained of heat as an ice elemental coalesces!")
            self.field_elemental = Elemental(element)
            #self.add_target(self.field_elemental)
            self.summon_minion_this_turn(self.field_elemental)

    @property
    def field_elemental(self):
        return self._field_elemental

    @field_elemental.setter
    def field_elemental(self, elemental):
        self._field_elemental = elemental

    def handle_groble_summon(self):

        summon_spells = ("Summon Groble I", "Summon Groble II",
                         "Summon Groble III", "Summon Groble IV"
                        )

        # The tuples in this dictionary refer to the monster name and its
        # HP/damage dealt.

        summon_dict = {"Summon Groble I":("Groble", 1),
                       "Summon Groble II":("Big Groble", 2),
                       "Summon Groble III":("Very Big Groble", 3),
                       "Summon Groble IV":("Very Very Big Groble", 4)
                      }

        # Handle Groble summoning first.

        spell_targets = self.spell_targets

        new_grobles = []

        for spell_target_tuple in spell_targets:

            caster, target, spell = spell_target_tuple

            # For this first pass-through, we only care about summons.
            if spell.name in summon_spells:
                # A summon is coming!
                # Assign it to the target or the master of the target.
                summon_name = summon_dict[spell.name][0]
                summon_rank = summon_dict[spell.name][1]

                monster = Minion(summon_name, summon_rank)
                monster.name = groblenames.get_random_name()
                if type(target) is Minion:
                    #monster.name = target.master.name + "\'s " + monster.name
                    target.master.add_minion(monster)
                else:
                    #monster.name = target.name + "\'s " + monster.name
                    target.add_minion(monster)
                    monster.original_master = target
                new_grobles.append(monster)
                
                self.summon_minion_this_turn(monster)
                self.add_flavor(monster.name + " enters " + monster.master.name + "\'s command.")

        # The grobles are now in the proper lists. Next, we need to indicate
        # that they have just been summoned, but only for this moment.

        self.command_existing_monsters()

        for groble in new_grobles:
            self.targets.append(groble)
            groble.name = groble.name + " (newly summoned)"

        # Now that they have been assigned their 'newly summoned' tags, ask
        # their masters who they will be attacking.

        """ This code is disabled after moving groble commanding to be
            entirely centralized after summoning.

        for groble in new_grobles:
            target = self.get_new_groble_target(groble)
            groble.target = target
            print(groble.name + " raises its weapon at " + target.name + "!")

        """

        # We don't remove " (newly summoned)" until new orders have been totally given.

    def find_target_from_ctarget(self, ctarget):

        """ Accept a string of a target's name and find the target it refers to. """

        # Find what target the client's target refers to.

        for target in self.targets:
            if target.name == ctarget:
                return target

    def command_existing_monsters(self):

        """ Iterate through a Wizard's minions list and ask for new orders.
            For user-friendliness, a blank/enter press is 'use old target'.
        """

        

        for wizard in self.wizards:
            for minion in wizard.minions:

                if not minion.commanded:
                    for client in self.get_clients():
                        self.wait_msg(client, "Waiting on monster commands...")

                    target = minion.target

                    self.msg_client("COMMAND_MONSTER", wizard.client)
                    ack = self.recv(wizard.client)

                    if self.response(ack, "Client died during COMMAND_MONSTER"):
                        
                        ack = self.dec(ack)
                        if ack == "COMMAND_MONSTER_ACK":
                            target_list = self.targetables_to_targetableclients(self.targets)
                            minion_c = self.targetable_to_targetableclient(minion)
                            data_p = [target_list, minion_c]
                            self.msg_client_pp(data_p, wizard.client)

                            c_target = self.recv(wizard.client)
                            if self.response(c_target, "Client died before it could sent monster target data"):
                                c_target = self.dec(c_target)
                                target = self.find_target_from_ctarget(c_target)

                                
                    """
                    while True:
                        print(wizard.name + ": Who will be the target of " + minion.name + "?")
                        target_name = ""

                        try:
                            target_name = minion.target.name
                        except AttributeError:
                            target_name = "No target"

                        print("Current target is: " + target_name)
                        
                        self.enumerate_targets()

                        ""
                        for i,entity in enumerate(self.targets, 1):
                            if type(entity) == "Minion"
                            print(str(i) + ". " + entity.name)
                        ""

                        choice = input("Choose target (leave blank or press enter for current target): ")

                        if choice == "":
                            if minion.target == "":
                                print("You must select an initial target for " + minion.name +".")
                            else:
                                break
                        else:
                            try:
                                if (int(choice) >= 1) and (int(choice) <= len(self.targets)):
                                    target = self.targets[int(choice)-1]
                                    break
                                else:
                                    print("Invalid target \'" + choice + "\'.")
                            except ValueError:
                                print("Invalid target \'" + choice + "\'.")
                    """

                    if minion.target != target:
                        minion.target = target
                        self.add_flavor(minion.name + " raises its weapon at " + minion.target.name + "!")

                    minion.commanded = True

    def check_for_surrender(self, wizard):

        """ Return True if both of the wizard's latest gestures are p. """

        left = wizard.get_latest_gesture("left")
        right = wizard.get_latest_gesture("right")

        if left.upper() == "P" and right.upper() == "P":
            return True

        return False

    def determine_spellcasts(self):

        """ Determine if a spell or spells are being cast as a result of the
            latest gestures. If so, add them to a list for later processing in
            the form of (Wizard caster, Object target, Spell spell).

            Only one spell can be cast at a time per hand. 
        """

        spells_to_cast = []

        for wizard in self.wizards:

            spellbook = wizard.spellbook

            hands = ("left", "right")

            spell_list = {"left":[], "right":[]}
            hasted_spell_list = {"left":[], "right":[]}

            one_cast = False
            one_casted = False
            hasted_one_cast = False
            hasted_one_casted = False

            surrender = self.check_for_surrender(wizard)

            if surrender:
                wizard.surrendering = True
            else:
                for hand in hands:
                    final_index = 0
                    if wizard.hasted:
                        final_index = -1
                    while final_index <= 0:
                        if final_index == -1:
                            hand_history = wizard.get_hand(hand).history[:-1]
                        else:
                            hand_history = wizard.get_hand(hand).history
                        for spell in spellbook.spell_list:
                            # Only check the spell if we've made enough gestures for one.
                            if len(spell.gesture) <= len(hand_history): 
                                spell_slice = hand_history[-len(spell.gesture):]
                                for i in range(0, len(spell_slice)):
                                    # Never check C -- this must ALWAYS use both hands.
                                    if spell.gesture[i] != "C":          
                                        # Don't check other spells if their gestures don't align.                            
                                        if spell_slice[i].lower() == spell.gesture[i].lower():
                                            if spell_slice[i] != spell.gesture[i]:
                                                if spell_slice[i].lower() == spell.gesture[i]:
                                                    spell_slice = spell_slice.replace(spell_slice[i], spell_slice[i].lower(), 1)

                                if spell_slice == spell.gesture:
                                    #print("A match has been found for " + spell.name)
                                    if spell.name != "Surrender":
                                        final_gesture = spell.gesture[final_index:]
                                        if final_gesture.upper() == final_gesture:
                                            #print("Final gestures match.")
                                            if final_index == -1:
                                                #print("Hasted one_cast setting to true")
                                                hasted_one_cast = True
                                            else:
                                                #print("Non-hasted one_cast setting to true")
                                                one_cast = True

                                        # one_casted will skip a second adding of the same spell.
                                        if one_cast:
                                            #print("Entering one_cast.")
                                            if not one_casted:
                                                #print("We are not one_casted.")
                                                one_casted = True
                                                append = True
                                                if spell.name == "Lightning Bolt (Quick)":
                                                    if wizard.used_quick_lightning:
                                                        append = False
                                                    else:
                                                        wizard.used_quick_lightning = True
                                                
                                                if append:
                                                    #print("Appending... from one_cast")
                                                    
                                                    if final_index == -1:
                                                        #print("[one_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                        hasted_spell_list[hand].append((wizard, spell))
                                                    else:
                                                        #print("[one_cast] Appended " + spell.name + " from " + wizard.name)
                                                        spell_list[hand].append((wizard, spell))
                                            else:
                                                #print("We are one_casted, not proceeding with append.")
                                                pass

                                        # The following conditional may be redundant

                                        if hasted_one_cast:
                                            #print("Entering hasted_one_cast")
                                            if not hasted_one_casted:
                                                #print("We are not hasted_one_casted.")
                                                hasted_one_casted = True
                                                append = True
                                                if spell.name == "Lightning Bolt (Quick)":
                                                    if wizard.used_quick_lightning:
                                                        append = False
                                                    else:
                                                        wizard.used_quick_lightning = True
                                                
                                                if append:
                                                    
                                                    if final_index == -1:
                                                        this_spell = (wizard, spell)
                                                        if this_spell not in hasted_spell_list["left"]:
                                                            #print("[hasted_one_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                            hasted_spell_list[hand].append(this_spell)
                                                    else:
                                                        #print("[hasted_one_cast] Appended " + spell.name + " from " + wizard.name)
                                                        spell_list[hand].append((wizard, spell))
                                            #else:
                                                #print("We are hasted_one_casted, not proceeding with append.")
                                                    

                                        else:
                                            append = True
                                            if spell.name == "Lightning Bolt (Quick)":
                                                if wizard.used_quick_lightning:
                                                    append = False
                                                else:
                                                    wizard.used_quick_lightning = True
                                            
                                            if append:
                                                
                                                if final_index == -1:
                                                    #print("[multi_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                    hasted_spell_list[hand].append((wizard, spell))
                                                else:
                                                    #print("[multi_cast] Appended " + spell.name + " from " + wizard.name)
                                                    spell_list[hand].append((wizard, spell))

                        final_index = final_index + 1
                        hasted_one_cast = False
                        hasted_one_casted = False
                        

                for hand in hands:
                    if spell_list[hand]:
                        if len(spell_list[hand]) > 1:
                            spell_tuple = self.choose_spell(spell_list[hand], hand, wizard)
                            spells_to_cast.append(spell_tuple)
                        else:
                            spells_to_cast.append(spell_list[hand][0])
                    if hasted_spell_list[hand]:
                        if len(hasted_spell_list[hand]) > 1:
                            spell_tuple = self.choose_spell(hasted_spell_list[hand], hand, wizard)
                            spells_to_cast.append(spell_tuple)
                        else:
                            spells_to_cast.append(hasted_spell_list[hand][0])

            if spells_to_cast:
                for cast_tuple in spells_to_cast:
                    wizard, spell = cast_tuple
                    target = self.get_target(wizard, spell.name)
                    self.add_spell_target(wizard, target, spell)
    
    def determine_spellcasts_individual(self, wizard):

        """ Determine if a spell or spells are being cast as a result of the
            latest gestures. If so, add them to a list for later processing in
            the form of (Wizard caster, Object target, Spell spell).

            Only one spell can be cast at a time per hand. 
        """

        spells_to_cast = []

        spellbook = wizard.spellbook

        hands = ("left", "right")

        spell_list = {"left":[], "right":[]}
        hasted_spell_list = {"left":[], "right":[]}

        one_cast = False
        one_casted = False
        hasted_one_cast = False
        hasted_one_casted = False


        surrender = self.check_for_surrender(wizard)

        if surrender:
            wizard.surrendering = True
        else:
            for hand in hands:
                final_index = 0
                if wizard.hasted:
                    final_index = -1
                while final_index <= 0:
                    if final_index == -1:
                        hand_history = wizard.get_hand(hand).history[:-1]
                    else:
                        hand_history = wizard.get_hand(hand).history
                    for spell in spellbook.spell_list:
                        # Only check the spell if we've made enough gestures for one.
                        if len(spell.gesture) <= len(hand_history): 
                            spell_slice = hand_history[-len(spell.gesture):]
                            for i in range(0, len(spell_slice)):
                                # Never check C -- this must ALWAYS use both hands.
                                if spell.gesture[i] != "C":          
                                    # Don't check other spells if their gestures don't align.                            
                                    if spell_slice[i].lower() == spell.gesture[i].lower():
                                        if spell_slice[i] != spell.gesture[i]:
                                            if spell_slice[i].lower() == spell.gesture[i]:
                                                spell_slice = spell_slice.replace(spell_slice[i], spell_slice[i].lower(), 1)

                            if spell_slice == spell.gesture:
                                print("A match has been found for " + spell.name)
                                if spell.name != "Surrender":
                                    final_gesture = spell.gesture[final_index:]
                                    if final_gesture.upper() == final_gesture:
                                        print("Final gestures match.")
                                        if final_index == -1:
                                            print("Hasted one_cast setting to true")
                                            hasted_one_cast = True
                                        else:
                                            print("Non-hasted one_cast setting to true")
                                            one_cast = True

                                    # one_casted will skip a second adding of the same spell.
                                    if one_cast:
                                        print("Entering one_cast.")
                                        if not one_casted:
                                            print("We are not one_casted.")
                                            one_casted = True
                                            append = True
                                            if spell.name == "Lightning Bolt (Quick)":
                                                if wizard.used_quick_lightning:
                                                    append = False
                                                else:
                                                    wizard.used_quick_lightning = True
                                            
                                            if append:
                                                print("Appending... from one_cast")
                                                
                                                if final_index == -1:
                                                    print("[one_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                    hasted_spell_list[hand].append((wizard, spell))
                                                else:
                                                    print("[one_cast] Appended " + spell.name + " from " + wizard.name)
                                                    spell_list[hand].append((wizard, spell))
                                        else:
                                            print("We are one_casted, not proceeding with append.")

                                    # The following conditional may be redundant

                                    elif hasted_one_cast:
                                        print("Entering hasted_one_cast")
                                        if not hasted_one_casted:
                                            print("We are not hasted_one_casted.")
                                            hasted_one_casted = True
                                            append = True
                                            if spell.name == "Lightning Bolt (Quick)":
                                                if wizard.used_quick_lightning:
                                                    append = False
                                                else:
                                                    wizard.used_quick_lightning = True
                                            
                                            if append:
                                                
                                                if final_index == -1:
                                                    this_spell = (wizard, spell)
                                                    if this_spell not in hasted_spell_list["left"]:
                                                        print("[hasted_one_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                        hasted_spell_list[hand].append(this_spell)
                                                else:
                                                    print("[hasted_one_cast] Appended " + spell.name + " from " + wizard.name)
                                                    spell_list[hand].append((wizard, spell))
                                        else:
                                            print("We are hasted_one_casted, not proceeding with append.")
                                                

                                    else:
                                        append = True
                                        if spell.name == "Lightning Bolt (Quick)":
                                            if wizard.used_quick_lightning:
                                                append = False
                                            else:
                                                wizard.used_quick_lightning = True
                                        
                                        if append:
                                            
                                            if final_index == -1:
                                                print("[multi_cast] HASTE appended " + spell.name + " from " + wizard.name + "(" + hand + " hand)")
                                                hasted_spell_list[hand].append((wizard, spell))
                                            else:
                                                print("[multi_cast] Appended " + spell.name + " from " + wizard.name)
                                                spell_list[hand].append((wizard, spell))
                    
                    final_index = final_index + 1
                    hasted_one_cast = False
                    hasted_one_casted = False
                        
            for hand in hands:
                if spell_list[hand]:
                    if len(spell_list[hand]) > 1:
                        spell_tuple = self.choose_spell(spell_list[hand], hand, wizard)
                        spells_to_cast.append(spell_tuple)
                    else:
                        spells_to_cast.append(spell_list[hand][0])
                if hasted_spell_list[hand]:
                    if len(hasted_spell_list[hand]) > 1:
                        spell_tuple = self.choose_spell(hasted_spell_list[hand], hand, wizard)
                        spells_to_cast.append(spell_tuple)
                    else:
                        spells_to_cast.append(hasted_spell_list[hand][0])

            if spells_to_cast:
                for cast_tuple in spells_to_cast:
                    wizard, spell = cast_tuple
                    target = self.get_target(wizard, spell.name)
                    self.add_spell_target(wizard, target, spell)


    def choose_spell(self, spell_list, hand_casting, wizard):

        """ Multiple spells are being cast at once.
        Choose the spell to cast.
        """

        client = wizard.client

        message = [[s[1].name, hand_casting] for s in spell_list]
        self.server.message_client_command(wizard.client, "MULTIPLE_SPELLS", message)
        response = self.server.get_client_message(wizard.client)

        for spell in spell_list:
            if spell[1].name == response:
                log.debug(f"{wizard} chose spell {spell}")
                return spell

        log.warning(f"{wizard}: Failed to find chosen spell {response}")
        return None

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, bool):
        self._playing = bool

    @property
    def targets(self):
        return self._targets

    def add_target(self, target):
        self.targets.append(target)

    def remove_target(self, target):
        self.targets.remove(target)

    @property
    def surrender(self):
        return self._surrender

    @surrender.setter
    def surrender(self, bool):
        self._surrender = bool

    @property
    def winner(self):
        return self._winner

    @winner.setter
    def winner(self, wizard):
        self._winner = wizard

    @property
    def loser(self):
        return self._winner

    @loser.setter
    def loser(self, wizard):
        self._winner = wizard  

    @property
    def wizards(self):
        return self._wizards

    @wizards.setter
    def wizards(self, wizard_list):
        self._wizards = wizard_list

    """
    def print_spell_flavor(self):

        for wizard in self.wizards:
            if wizard.hand_spell["left"] == "":
                # no spell was casted OR this is a two-hand spell.
                print(wizard.hand_spell["left"])
            else:
                for hand in ("left", "right"):
                    print(wizard.hand_spell[hand])
    """

    def get_random_body_part(self):

        # just for fun and flavor
        # this is using the gurps body table, but it doesn't actually have an effect

        hit = "face"
        roll = randint(3, 18)
        if roll < 5:
            hit = "skull"
        elif roll < 6:
            hit = "face"
        elif roll < 9:
            hit = "right leg"
        elif roll < 11:
            hit = "torso"
        elif roll < 12:
            hit = "groin"
        elif roll < 13:
            hit = "left arm"
        elif roll < 15:
            hit = "left leg"
        elif roll < 16:
            hit = "hand"
        elif roll < 17:
            hit = "foot"
        elif roll < 19:
            hit = "neck"

        return hit

    def resolve_death_or_surrender(self):

        # first, check if either wizard has 0 hp or less.
        
        dying_wizards = []

        for wizard in self.wizards:
            if wizard.hp <= 0:
                dying_wizards.append(wizard)
        
        # next, is raise dead being cast on a dead wizard?

        # code here to remove the wizard from dying_wizards
        # and add their hp back.

        for wizard in self.wizards:
            if wizard.resurrecting:
                dying_wizards.remove(wizard)
                wizard.hp = wizard.hp + 10 #TODO: bad way to do this

        # finally, is raise dead being cast on a dead wizard?

        # finally, is either wizard surrendering?

        for wizard in self.wizards:
            if wizard.get_latest_gesture("left") == "P":
                wizard.surrendering = True
                self.surrender = True

        # code

        if dying_wizards != []:
            self.print_flavor_victory("death")
            return False

        if self.surrender:
            self.print_flavor_victory("surrender")
            return False
        
        return True

    def print_flavor_victory(self, cause):

        print("")

        if cause == "death":

            dying_wizards = []

            for wizard in self.wizards:
                if wizard.hp <= 0:
                    dying_wizards.append(wizard)
                    self.add_flavor(wizard.death_throes())

            if len(dying_wizards) == 2:
                # both wizards are dying.
                # find out who is less dead.
                wiza_hp = dying_wizards[0].hp
                wizb_hp = dying_wizards[1].hp
                winner = None
                if wiza_hp < wizb_hp:
                    winner = dying_wizards[1]
                elif wizb_hp < wiza_hp:
                    winner = dying_wizards[0]
                
                if winner == None:
                    self.add_flavor("\nBoth wizards die equally messily.")
                    self.add_flavor("Suddenly, a red-robed wizard appears in a flash of lightning.")
                    self.add_flavor("The wizard examines the two dead competitors and declares the match to be a non-conclusive draw.")
                    self.add_flavor("The red-robed wizard loots their valuables and lives happily ever after.")
                else:
                    self.add_flavor("\nAs " + winner.name + " died less messily than their opponent, they are considered to be the winner.")
                    self.add_flavor("The council of wizards think this is a wise and just ruling.")
                    self.add_flavor(winner.name + " is added to the annals of wizarding history as a great hero.")
            else:
                # only one is dying.
                loser = dying_wizards[0]
                winner = None
                for wizard in self.wizards:
                    if wizard.hp > 0:
                        winner = wizard

                self.add_flavor(winner.name + " has won the battle!\n")
                self.add_flavor(winner.win())
                self.add_flavor(loser.die())

                self.add_flavor("\nThe storm continues to rumble as " + winner.name + " turns and leaves the battlefield...")

        elif cause == "surrender":

            # Unnecessary -- this flavor is printed in add_gesture_flavor
            """
            for wizard in self.wizards:
                if wizard.surrendering:
                    print(wizard.name + " proferrs both palms in the gesture of surrender!")
            """

            if self.wizards[0].surrendering and self.wizards[1].surrendering:
                self.add_flavor("\nThe battle between " + self.wizards[0].name + " and " + self.wizards[1].name + " ends in a draw.")
                self.wizards[0].defeat()
                self.wizards[1].defeat()

                self.add_flavor("\nThe wizards, looking embarrassed, quietly agree to never speak of this incident again.")
            else:
                for wizard in self.wizards:
                    if not wizard.surrendering:
                        self.add_flavor("\n" + wizard.name + " is victorious!\n")
                        self.add_flavor(wizard.win())
                for wizard in self.wizards:
                    if wizard.surrendering:
                        self.add_flavor(wizard.defeat())

                self.add_flavor("\nThe sun breaks through the clouds to shine upon both wizards as live to see another day.")

    def resolve_flavor(self, wizard):
        # read the latest hand history.
        # print flavor text for the gestures.

        wizlh = wizard.get_hand("left").show_history()
        wizrh = wizard.get_hand("right").show_history()

        wizal_newest = str(wizlh[-1:])
        wizar_newest = str(wizrh[-1:])

        self.print_flavor_text(wizard, wizal_newest, wizar_newest)

    def resolve_flavor_spell(self, wizard):

        # read the hand history.

        spellbook = wizard.spellbook

        # compare the gesture history to all of the spell gestures.
        # was a spell cast?

        hands = ("left", "right")

        one_cast = False
        one_casted = False

        hand_spell = {"left":"", "right":""}

        for hand in hands:
            hand_history = wizard.get_hand(hand).history
            for spell in spellbook.spell_list:
                if len(spell.gesture) <= len(hand_history): # only check the spell if we've made enough gestures for one.

                    spell_slice = hand_history[-len(spell.gesture):]

                    for i in range(0, len(spell_slice)):
                        if spell.gesture[i] != "C": # never check C -- this must ALWAYS use both hands   
                            #print("spell_slice[" + str(i) + "] = " + spell_slice[i])
                            #print("spell.gesture[" + str(i) + "] = " + spell.gesture[i])
                            #print("i="+str(i)+" "+ spell_slice[i] + " != " + spell.gesture[i])    
                            if spell_slice[i].lower() == spell.gesture[i].lower():

                                # don't check other spells if their gestures don't align.

                                if spell_slice[i] != spell.gesture[i]:
                            
                                    if spell_slice[i].lower() == spell.gesture[i]:

                                        spell_slice = spell_slice.replace(spell_slice[i], spell_slice[i].lower(), 1)

                            # for character in sFw, do
                            # gesture: sfw

                            # if s != s (false)
                            # pass!

                            # if F != f (true)
                            # if f == f (true)

                            # if 2 (i=1,i+1) == 3 (false):
                            # sFw = s + f + w



                        # this is so a W/S/F/D in history counts as a w/s/f/d for gesture checking.
                        # we don't want to cast C spells with c.
                    if spell_slice == spell.gesture:
                        if spell.name != "Surrender":
                            final_gesture = spell.gesture[-1:]
                            if final_gesture.upper() == final_gesture:
                                one_cast = True 

                            target = self.get_target(wizard, spell.name)
                        

                            if one_cast:
                                if not one_casted:

                                    line = wizard.name + " casts " + spell.name + " on " + target.name + "!"
                                    wizard.set_hand_spell("left", line)
                                    one_casted = True
                                    
                            else:
                                line = wizard.name + " casts " + spell.name + " with their " + hand + " hand on " + target.name + "!"
                                wizard.set_hand_spell(hand, line)
                                target.add_active_spell(spell)

    def enumerate_targets(self, starting_index = 1):

        print('{:>2}. {:<22} {:<2} {:<4} {:^22} {:<22}'.format('#', 'Name', 'HP', 'Rank', 'Target', 'Master'))
        for i,entity in enumerate(self.targets, starting_index):
            
            name = entity.name.title()
            if type(entity) is Minion:
                print_f = "{:>2}. {:<22} {:<2} {:<4} {:^22} {:<22}".format(str(i), name, str(entity.hp), str(entity.rank), entity.target.name, entity.master.name)
            else:
                if type(entity) is Wizard:
                    if entity.invisible:
                        name = entity.name.title() + " (invisible)"
                print_f = "{:>2}. {:<22} {:<2}".format(str(i), name, entity.hp)
            print(print_f)

    def targetable_to_targetableclient(self, target):

        print(target.name)

        e_type = "unknown"
        if type(target) is Wizard:
            e_type = "wizard"
        elif type(target) is Minion:
            e_type = "minion"
        elif type(target) is Elemental:
            e_type = "elemental"

        if e_type == "unknown":
            print("An object is passing as type unknown [" + target.name + "]")

        if e_type == "wizard" or e_type == "elemental" or e_type == "unknown":
            new_targetable_c = TargetableClient(target.name, target.hp, e_type, target.invisible)
        elif e_type == "minion":
            target_name = ""
            if target.target == "":
                target_name == "No target"
            else:
                target_name = target.target.name
            new_targetable_c = TargetableClient(target.name, target.hp, e_type, target.invisible, target.rank, target_name, target.master.name)

        return new_targetable_c

    def targetables_to_targetableclients(self, target_list):

        targetables_c = []

        for target in target_list:
            
            e_type = "unknown"
            if type(target) is Wizard:
                e_type = "wizard"
            elif type(target) is Minion:
                e_type = "minion"
            elif type(target) is Elemental:
                e_type = "elemental"

            if e_type == "unknown":
                print("An object is passing as type unknown [" + target.name + "]")

            if e_type == "wizard" or e_type == "elemental" or e_type == "unknown":
                new_targetable_c = TargetableClient(target.name, target.hp, e_type, target.invisible)
            elif e_type == "minion":
                new_targetable_c = TargetableClient(target.name, target.hp, e_type, target.invisible, target.rank, target.target.name, target.master.name)

            targetables_c.append(new_targetable_c)

        return targetables_c


    def get_target(self, attacker, attack):

        """ get_target accepts (Wizard attacker, string attack). This is not
            a Spell object but a literal string, though Spell.name can be 
            passed an argument. """

        # First, turn the list of target objects into TargetableClients.

        targetables_c = self.targetables_to_targetableclients(self.targets)

        self.server.message_client_command(attacker.client, "GET_TARGET", [targetables_c, attack])
        target_name = self.server.get_client_message(attacker.client)

        if target_name == "self":
            return attacker
        else:
            for victim in self.targets:
                if victim.name == target_name:
                    return victim.name

        log.warning(f"{wizard}: Failed to choose target, {response} does not exist!")
        return None

        self.msg_client("GET_TARGET", attacker.client)
        ack = self.recv(attacker.client)

        if self.response(ack, "Client died while sending ack for GET_TARGET"):
            ack = self.dec(ack)
            
            if ack == "GET_TARGET_ACK":
                # Send info about what the attack is and the targets list.
                targets_p = self.pickle([targetables_c, attack])
                self.msg_client_p(targets_p, attacker.client)

                target = self.recv(attacker.client)
                if self.response(target, "Client died while sending target choice."):

                    # The client sent a string, so find out which target it applies to.
                    target_name = self.dec(target)

                    if target_name == "self":
                        target = attacker
                    else:
                        for victim in self.targets:
                            if victim.name == target_name:
                                target = victim
                                break
        """
        target = attacker

        while True:
            print(attacker.name + ": Who will be the target of the " + attack + "?")
            
            self.enumerate_targets()

            choice = input("Choose target (leave blank or press enter for self): ")

            if choice == "":
                break

            try:
                if (int(choice) >= 1) and (int(choice) <= len(self.targets)):
                    target = self.targets[int(choice)-1]
                    if type(target) == Elemental:
                        if "Groble" in attack:
                            print("A groble-summoning spell cannot target an elemental.")
                        elif attack == "Amnesia":
                            print("An elemental cannot be made amnesiac.")
                        elif attack == "Confusion":
                            print("An elemental cannot be confused.")
                        elif "Charm" in attack: # Charm Person, Charm Monster
                            print("An elemental cannot be charmed.")
                        elif attack == "Raise Dead":
                            print("A non-wizard cannot wield the power to raise the dead.")
                        elif attack == "Paralysis":
                            print("An elemental cannot be paralyzed.")
                        elif attack == "Fear":
                            print("An elemental cannot feel fear.")
                        elif attack == "Anti-spell":
                            print("An elemental cannot be anti-spelled.")
                        elif attack == "Delayed Effect":
                            print("An elemental cannot cast spells.")
                        else:
                            break
                    elif type(target) == Minion:
                        if attack == "Raise Dead":
                            print("A non-wizard cannot wield the power to raise the dead.")
                        elif attack == "Anti-spell":
                            print(target.name + ", a minion, cannot be anti-spelled.")
                        elif attack == "Delayed Effect":
                            print(target.name + " cannot cast spells.")
                        else:
                            break
                    else:
                        break
                else:
                    print("Invalid target \'" + choice + "\'.")
            except ValueError:
                print("Invalid target \'" + choice + "\'.")

        print("")
        """

        return target

    def print_flavor_text(self, wizard, left, right):

        if left == right:
            # they are the same gesture, we do not need to do excessive checking.
            # capital letters mean that both hands did the same gesture.
            if left == "F":
                print(wizard.name + " wiggles the fingers of both hands, mysteriously!")
            elif left == "P":
                print(wizard.name + " proferrs both palms to the sky!")
            elif left == "S":
                print(wizard.name + " snaps both fingers jazzily.")
            elif left == "W":
                print(wizard.name + " waves both hands, magically!")
            elif left == "D":
                print(wizard.name + " makes finger guns!")
            elif left == "C":
                print(wizard.name + " claps both hands together!")
        else:

            hands_dict = {"left":left, "right":right}
            hands = ("left", "right")

            for i,hand in enumerate(hands):
                # hand 0 is left, hand 1 is right
                active_hand_gesture = hands_dict[hands[i]]
                if active_hand_gesture == "f":
                    print(wizard.name + " wiggles the fingers of their " + hand + " hand!")
                elif active_hand_gesture == "p":
                    print(wizard.name + " proferrs the palm of their " + hand + " hand!")
                elif active_hand_gesture == "s":
                    print(wizard.name + " snaps the fingers of their " + hand + " hand!")
                elif active_hand_gesture == "w":
                    print(wizard.name + " waves their " + hand + " hand!")
                elif active_hand_gesture == "d":
                    print(wizard.name + " points the digit of their " + hand + " hand!")
                elif active_hand_gesture == "c":
                    print(wizard.name + " demonstrates the art of one hand clapping with their " + hand + " hand!")
                elif active_hand_gesture == "$":
                    print(wizard.name + " thrusts at " + wizard.opponent.name + " with the dagger in their " + hand + " hand!")

def main():

    gm = Gamemaster()

    gm.setup_game()     # create wizards, customize, etc
    gm.play_game()      # see play_game() function for further details

if __name__ == '__main__':
    main()