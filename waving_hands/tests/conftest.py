import pickle
import select
from unittest.mock import Mock
import pytest
import logging

from waving_hands.gamemaster import Gamemaster
from waving_hands.server import Server


@pytest.fixture
def game(mock_server, client):
    """
    Mocked game client, where the server socket pieces are removed and replaced
    with mocks, including wizards.
    """
    gamemaster = Gamemaster(pregame=False, customize_wizards=False)
    gamemaster.setup_game()
    for wizard in gamemaster.wizards:
        wizard.client = client()
    return gamemaster


@pytest.fixture
def wizard(game):
    """
    Typically in testing we'll only want to run one turn with a single wizard. The first
    wizard will always get input first. This probably isn't the best assumption to make in
    game, but for the current turn order it will always work.
    """
    wiz1, wiz2 = game.wizards
    return wiz1


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
            self.send = Mock()

        def get_messages(self):
            if self.message_box is None:
                self.message_box = iter(self.messages)
            try:
                return next(self.message_box)
            except StopIteration:
                raise StopIteration(
                    f"Ran out of messages. Original messages: \n[{list(self.message_box)}.\n"
                    f"Sent: [{self.send.call_args_list}]"
                )

        def recv(self, buffsize):
            return self.get_messages()

    return MockClient


@pytest.fixture
def mock_pickle(monkeypatch):
    monkeypatch.setattr(pickle, "dumps", lambda msg: msg)
    monkeypatch.setattr(pickle, "loads", lambda msg: msg)
    return pickle


@pytest.fixture
def mock_select(monkeypatch):
    monkeypatch.setattr(
        select,
        "select",
        lambda rlist, wlist, xlist, timeout=None: (rlist, wlist, xlist),
    )
    return select.select


@pytest.fixture
def mock_server(monkeypatch, mock_pickle, mock_select):
    monkeypatch.setattr(
        Server, "wait_for_connections", Mock(return_value=[Mock(), Mock()])
    )
    # Mock pickled data so we can see the raw stuff within tests
    monkeypatch.setattr(Server, "encode_message", lambda self, msg: msg)
    return Server
