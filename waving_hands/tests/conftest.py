import pickle
from unittest.mock import Mock
import pytest

from waving_hands.gamemaster import Gamemaster
from waving_hands.server import Server


@pytest.fixture
def game(mock_server, client):
    """
    Mocked game client, where the server socket pieces are removed and replaced
    with mocks, including wizards.
    """
    gamemaster = Gamemaster()
    gamemaster.setup_game()
    for wizard in gamemaster.wizards:
        wizard.client = client()
    return gamemaster


@pytest.fixture
def client():
    """
    Mock a player client connection to the server. This is a fake socket connection that contains
    a mocked `recv` method, which can be used to send mock messages to a client.
    """
    class MockClient:
        def __init__(self):
            self.messages = []
            self.message_box = None

        def get_messages(self):
            if self.message_box is None:
                self.message_box = iter(self.messages)
            return next(self.message_box)

        def recv(self, buffsize):
            m = self.get_messages()
            print(m)
            return bytes(m, "utf-8")

        send = Mock()

    return MockClient


@pytest.fixture
def mock_server(monkeypatch):
    monkeypatch.setattr(
        Server, "wait_for_connections", Mock(return_value=[Mock(), Mock()])
    )
