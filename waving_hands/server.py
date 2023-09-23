import logging
import socket 
import select
import pickle
import typing as t

log = logging.getLogger(__name__)


class Server:

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        self.server = None
        self.ENCODING = "utf-8"
        self.BUFFSIZE = 1024

        self.clients: list = []

    def wait_for_connections(self, minimum_clients: int = 2) -> t.List[socket.socket]:
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addr = (self.host, self.port)
        self.server.bind(addr)
        self.server.listen(minimum_clients)        

        log.info(f"Waiting for connections from {minimum_clients} hosts.")

        while len(self.clients) < minimum_clients:
            c, addr = self.server.accept()
            log.info("Connection accepted from " + str(addr))
            self.clients.append(c)
            if len(self.clients) < minimum_clients:
                self.wait_msg(c, "Waiting for challenger...")

        return self.clients

    def get_from_clients(self, client_command: str, client_done: callable):
        """
        Send the client_command to all users, and wait from responses from all of them.
        Yield the message from each client

        """
        log.debug(f'Fetching responses from clients for command: "{client_command}"')
        for client in self.clients:
            client.send(client_command.encode(self.ENCODING))

        while not all(client_done(c) for c in self.clients):
            rlist, wlist, elist = select.select( self.clients, [], [] )
            for client in rlist:
                message = self.get_client_message(client)
                yield client, message

    def get_client_message(self, client: socket.socket) -> t.Any:
        message = client.recv(self.BUFFSIZE)
        try:
            message = self.depickle(message)
        except pickle.UnpicklingError:
            message = message.decode(self.ENCODING)
        self.check_response(message, f"Client died during message {message}")
        return message

    def _get_command_default_ack(self, command):
        return f"{command}_ACK"

    def _get_command_default_complete(self, command):
        return f"{command}_COMPLETE"

    def _process_command(self, client: socket.socket, command: str, 
                            messages: t.List[str], command_ack: t.Optional[str] = None, command_complete: t.Optional[str] = None):
        command_ack = command_ack or self._get_command_default_ack(command)
        received_message = self.get_client_message(client)
        if received_message != command_ack:
            log.warning(f"Command {command} received {received_message} instead of the expected response {command_ack} from client {client}")

        self.msg_client_pp(messages, client)
        complete_msg = self.get_client_message(client)
        
        com_c = command_complete or self._get_command_default_complete(command)
        if complete_msg != com_c:
            log.warning(f"Command {command} received {complete_msg} instead of the expected"
                "complete command {com_c} by client {client}")
        log.debug(f'Client command {command} completed successfully.')

    def message_clients_command(self, command: str, messages: t.List[str]):
        self.msg_clients(command)
        for client in self.clients:
            return self._process_command(client, command, messages)
    
    def message_client_command(self, client: socket.socket, command: str, messages: t.List[str]):
        self.wait_msg(client, command)
        return self._process_command(client, command, messages)


    def message_clients(self, message: str):
        for client in self.clients:
            self.wait_msg(client, message)

    
    def check_response(self, data, msg=""):

        """ Kills the connection if the data is blank, otherwise returns True. """

        

        if self.dead_response(data):
            if msg:
                print(msg)
            self.kill_connection()
        
        return True
                    

    def depickle(self, pickled_item):

        """ Return the depickled version of the item. """
        return pickle.loads(pickled_item)

    def pickle(self, item):

        """ Return the pickled version of the item. """

        return pickle.dumps(item)

    def wait_msg(self, client, msg=""):

        if msg == "":
            self.msg_client_g("Waiting on other wizards...", client)
        else:
            self.msg_client_g(msg, client)


    def msg_clients(self, msg):
        """ Encode the message and send it to all clients. """
        for client in self.clients:
            client.send(msg.encode(self.ENCODING))

    def msg_client_i(self, int_to_pass, client):

        bytes_i = (int_to_pass).to_bytes(4, "big")
        client.send(bytes_i)

    def dead_response(self, data):

        if data == b'':
            return True
        else:
            return False

    def kill_connection(self):

        print("Server shutting down.")

        c_list = self.get_clients()

        print("Killing clients.")

        for client in c_list:
            client.shutdown(1)
            client.close()

        print("Killing server.")

        self.server.shutdown(1)
        self.server.close()

        print("Server shut down.")

        sys.exit()

    def msg_client_g(self, msg, client):

        """ Send a generic string to the client. """

        self.msg_client("MSG", client)
        msg_ack = client.recv(self.BUFFSIZE)

        if self.dead_response(msg_ack):
            self.kill_connection()
        else:
            msg_ack = msg_ack.decode(self.ENCODING)
            if msg_ack == "ACK_MSG":
                self.msg_client(msg, client)
                msg_ackack = client.recv(self.BUFFSIZE)

                if self.dead_response(msg_ackack):
                    # Client is disconnected
                    pass
                else:
                    pass
    

    def msg_client(self, msg, client):

        """ Encode the message (as a string) and send it to the client. """

        log.debug(f"Sending {msg} to client.")
        client.send(msg.encode(self.ENCODING))

    def msg_client_pp(self, msg, client):

        """ Pickle an item and send it to the client. """

        msg = self.pickle(msg)
        client.send(msg)

    def msg_client_p(self, msg, client):

        """ Send the client a pickled item. """

        client.send(msg)


    def close_connections(self):

        for wizard in self.wizards:
            wizard.client.shutdown(1)
            wizard.client.close()

        self.server.shutdown(1)
        self.server.close()
        