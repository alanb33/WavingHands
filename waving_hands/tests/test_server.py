import pytest
from unittest.mock import call
from waving_hands import server


def test_server_unstructured_command_basic(mock_server, client):
    """
    Test a very basic unstructured server command with a client
    """
    server = mock_server("localhost", 12345)
    # Fake client will only send the proper "hello" messages
    c1 = client()
    c1.messages = ["HELLO"]
    server.clients = [c1]

    # This defines the base case for when the server should stop collecting messages
    # from a client -- when client is added to "done".
    done = set()
    server_responses = server.unstructured_command(
        "SAY_HELLO", lambda client: client in done
    )

    # Messages will be collected from server responses. And this will happen forever
    # for each client until all clients say "HELLO".
    for client, message in server_responses:
        if message == "HELLO":
            server.message_client(client, "WE ARE NOW FRIENDS")
            done.add(client)
        else:
            server.message_client(client, f"{message} is NOT a Greeting!")

    assert c1.send.call_args_list == [call("SAY_HELLO"), call("WE ARE NOW FRIENDS")]


def test_server_unstructured_command_multiple_clients(mock_server, client):
    """
    Test multiple clients with unstructured commands
    """
    server = mock_server("localhost", 12345)
    # Fake client will only send the proper "hello" messages
    c1 = client()
    c1.messages = ["HELLO"]
    c2 = client()
    c2.messages = ["Umm", "HELLO"]
    server.clients = [c1, c2]

    # This defines the base case for when the server should stop collecting messages
    # from a client -- when client is added to "done".
    done = set()
    server_responses = server.unstructured_command(
        "SAY_HELLO", lambda client: client in done
    )

    # Messages will be collected from server responses. And this will happen forever
    # for each client until all clients say "HELLO".
    for client, message in server_responses:
        if message == "HELLO":
            server.message_client(client, "WE ARE NOW FRIENDS")
            done.add(client)
        else:
            server.message_client(client, f"{message} is NOT a Greeting!")

    assert c1.send.call_args_list == [call("SAY_HELLO"), call("WE ARE NOW FRIENDS")]
    assert c2.send.call_args_list == [
        call("SAY_HELLO"),
        call("Umm is NOT a Greeting!"),
        call("WE ARE NOW FRIENDS"),
    ]


def test_server_command_client(mock_server, client):
    """
    Test multiple clients with unstructured commands
    """
    server = mock_server("localhost", 12345)
    # Fake client will only send the proper "hello" messages
    c1 = client()
    c1.messages = [
        "EAT_YOUR_VEGGIES_ACK",
        "EAT_YOUR_VEGGIES_COMPLETE",
        "I ate my veggies.",
    ]

    response = server.command_client(
        c1, "EAT_YOUR_VEGGIES", "You better eat your veggies."
    )
    assert response == "I ate my veggies."
    assert c1.send.call_args_list == [
        call("EAT_YOUR_VEGGIES"),
        call("You better eat your veggies."),
    ]


@pytest.mark.xfail
def test_server_message_client(mock_server, client):
    """
    Test sending a client a message
    """
    server = mock_server("localhost", 12345)
    # Fake client will only send the proper "hello" messages
    c1 = client()

    assert c1.send.call_args_list == [call("Hello!")]


@pytest.mark.xfail
def test_server_message_client_with_object(mock_server, client):
    """
    Test sending a client a message
    """
    assert False


@pytest.mark.xfail
def test_server_check_response():
    """Test the server will be shut down if it receives a dead response"""
    assert False


@pytest.mark.xfail
def test_server_dead_response_with_dead_response():
    """Test that a dead response will return True"""
    assert False


@pytest.mark.xfail
def test_server_dead_response_with_good_data():
    """Test that a dead response will return False"""
    assert False


@pytest.mark.xfail
def test_server_shutdown():
    """Test that a server will properly call shutdown on all clients and then itself"""
    assert False
