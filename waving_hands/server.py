import logging
import socket
import select
import pickle
import typing as t

log = logging.getLogger(__name__)


class Server:
    """
    The Server is a low level TCP socket server which handles client connections, in
    addition to sending and receiving messages between connected wizard clients. It
    knows nothing about how the game is played, but serves as a small abstraction layer
    for serializing and deserializing messages between players, and providing some tools
    for collecting and sending commands to each of them.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        self.server = None
        self.ENCODING = "utf-8"
        self.BUFFSIZE = 1024

        self.clients: list = []

    def wait_for_connections(self, minimum_clients: int = 2) -> t.List[socket.socket]:
        """
        Wait for connecitons from clients. Can only be done ONCE at the start of the
        server.

        TODO: Suppert client disconnects and reconnects

        :param minimum_clients: minimum clients that may connect before the game starts.
        Method will block until this number is met, and return afterwards.
        """
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

    def unstructured_command(self, command: str, client_done: callable):
        """
        Send the ``command`` to all clients, and continue to collect input until
        the callable ``client_done`` resolves to True for all clients. Client
        input will be collected and yielded so that the caller can determine whether
        ``client_done`` should resolve True.

        .. code-block:: python

            # This defines the base case for when the server should stop collecting messages
            # from a client -- when client is added to "done".
            done = {}
            server_responses = self.server.command_clients(
                "SAY_HELLO", lambda client: client in done 
            )

            # Messages will be collected from server responses. And this will happen forever
            # for each client until all clients say "HELLO". 
            for client, message in server_responses:
                if message == "HELLO":
                    self.server.message_client(client, "WE ARE NOW FRIENDS")
                    done.add(client)
                else:
                    self.server.message_client(client, f"{message} is NOT a Greeting!")

        :param command: string to send to all clients. Clients should understand how to process
            the command.
        :yield: tuple: (client: socket, message: str)
        """
        log.debug(f'Fetching responses from clients for command: "{command}"')
        for client in self.clients:
            log.debug(f"Sending command: {command}")
            client.send(command.encode(self.ENCODING))

        done = set()
        while set(self.clients) != done:
            log.debug(f"Curr clients: {self.clients}, done: {done}")
            rlist, wlist, elist = select.select(self.clients, [], [])
            for client in [c for c in rlist if c not in done]:

                message = self.get_client_message(client)
                yield client, message
                if client_done(client):
                    log.debug(f"Client has finished command {command}")
                    done.add(client)
                    log.debug(f"Have finished: {len(done)}")
        log.debug(f"Completed for all users, command: {command}")

    def command_client(
        self, client: socket.socket, command: str, messages: t.List[str]
    ) -> t.Any:
        """
        Send the command to Clients, but follow a strict structure on how input should be processed.
        Messages MUST always follow the following format:

        Server -> Client: COMMAND
        Client -> Server: COMMAND_ACK
        Server -> Client: messages
        Client -> Server: COMMAND_COMPLETE
        Client -> Server: client_info

        Failure to follow the format above won't result in exceptions, but will result in warnings and
        likely means a failure in communication somewhere.

        :param command: string to send to all clients. Clients should understand how to process
            the command.
        :param messages: Messages to send to the client after the CLIENT_ACK. If the message is an
            object, it will be pickled. Otherwise, it will be encoded as a string.
        :return: A message from the client, as a depickled object or decoded string.
        """
        self.message_client(client, command)
        return self._process_command(client, command, messages)

    def _process_command(
        self,
        client: socket.socket,
        command: str,
        messages: t.List[str],
        command_ack: t.Optional[str] = None,
        command_complete: t.Optional[str] = None,
    ) -> t.Any:
        command_ack = command_ack or self._get_command_default_ack(command)
        received_message = self.get_client_message(client)
        if received_message != command_ack:
            log.warning(
                f"Command {command} received {received_message} instead of the expected response {command_ack} from client {client}"
            )

        self.msg_client_pp(messages, client)
        complete_msg = self.get_client_message(client)

        com_c = command_complete or self._get_command_default_complete(command)
        if complete_msg != com_c:
            log.warning(
                f"Command {command} received {complete_msg} instead of the expected"
                "complete command {com_c} by client {client}"
            )
        log.debug(f"Client command {command} completed successfully.")
        return self.get_client_message(client)

    def get_client_message(self, client: socket.socket) -> t.Any:
        """
        Get a message from a connected client.

        :param client: Attempt to receive a message from a client. The message is first
        attempted to be depickled, and if that fails, decoded in UTF-8.
        :return: The message object from a client
        """
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

    def message_clients(self, message: str):
        for client in self.clients:
            self.message_client(client, message)

    def message_client(self, client, message):
        log.debug(f"Sending client {client} message {message}")
        if not isinstance(message, str):
            log.debug(f"Object found, Pickling!")
            message = self.pickle(message)

        client.send(message.encode(self.ENCODING))

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

    def msg_client_i(self, int_to_pass, client):

        bytes_i = (int_to_pass).to_bytes(4, "big")
        self.message_client(client, message)

    def dead_response(self, data):

        if data == b"":
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

    def msg_client(self, msg, client):

        """ Encode the message (as a string) and send it to the client. """

        log.debug(f"Sending {msg} to client {client}.")
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
