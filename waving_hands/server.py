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
            done = set()
            server_responses = self.server.unstructured_command(
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
        self.message_clients(command)

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

        self.message_client(client, messages)
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
            message = pickle.loads(message)
        except pickle.UnpicklingError:
            message = message.decode(self.ENCODING)
        self.check_response(message, f"Client died during message {message}")
        return message

    def _get_command_default_ack(self, command):
        return f"{command}_ACK"

    def _get_command_default_complete(self, command):
        return f"{command}_COMPLETE"

    def message_clients(self, message: str):
        """
        Send a message to all clients in the server Message can be any entity, and will be automatically pickled if it
        is not a string.
        
        :param client: Client to send the message
        :param message: data to send to the client.
        """
        for client in self.clients:
            self.message_client(client, message)

    def encode_message(self, message: str):
        """
        Encode a message to be sent to a client. Typically should not be called externally.
        
        :param message: data to be encoded
        """
        return message.encode(self.ENCODING)

    def message_client(self, client, message):
        """
        Send a message to a given client. Message can be any entity, and will be automatically pickled if it
        is not a string.
        
        :param client: Client to send the message
        :param message: data to send to the client.
        """
        log.debug(f"Sending client {client} message {message}")
        if not isinstance(message, str):
            log.debug(f"Object found, Pickling!")
            message = pickle.dumps(message)

        client.send(self.encode_message(message))

    def check_response(self, data, msg=""):
        """ Kills the connection if the data is blank, otherwise returns True. """

        if self.dead_response(data):
            log.critical(f"Dead response received ({msg}), killing server...")
            self.shutdown()
        return True

    def dead_response(self, data):
        """Check for a "dead" response within the data, which will be represented as the empty string
        
        :param data: entity to check for dead response.
        :return: True if dead response, false otherwise
        """
        if data == b"":
            return True
        else:
            return False

    def shutdown(self):
        """Shutdown the server and kill all client connections."""
        log.critical(f"Server Shutdown initiating, killing all connections...")

        for client in self.clients():
            log.info(f"Shutting down client: {client}")
            client.shutdown(1)
            client.close()

        log.info(f"Shutting down server.")
        self.server.shutdown(1)
        self.server.close()
