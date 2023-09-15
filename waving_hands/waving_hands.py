import argparse
import logging
import logging.config

from waving_hands import gamemaster
from waving_hands.spellbinder_client import main as client_main
from waving_hands import config

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description="P2P Multiplayer Python implementation of Richard Bartle's Waving Hands"
)
parser.add_argument(
    "--host", default="localhost", help="Location to host the server, or connect if using --client. Default: localhost"
)
parser.add_argument(
    "--port", type=int, default=12345, help="Port to run the server. Defalut: 12345"
)
parser.add_argument(
    "--client", action="store_true", help="Connect to another host instead using the --host and --port args"
)
parser.add_argument(
    "--skip-pregame", action="store_true", help="Skip the pre-game introductions"
)
parser.add_argument(
    "--skip-customize",
    action="store_true",
    help="Skip phase where players customize their wizards",
)
parser.add_argument(
    "--players",
    type=int,
    default=2,
    help="Number of players to use for the game. Should always be 2.",
)
parser.add_argument("--log", default="INFO", help="Set Logging level for the server")


def main():
    args = parser.parse_args()
    log_cfg = config.LOGGING.copy()
    log_cfg["handlers"]["console"]["level"] = args.log
    logging.config.dictConfig(log_cfg)

    if args.client:
        client_main(args.host, args.port)
    else:
        pregame, customize = not args.skip_pregame, not args.skip_customize
        game = gamemaster.Gamemaster(
            host=args.host,
            port=args.port,
            pregame=pregame,
            customize_wizards=customize,
            players=args.players,
        )
        game.setup_game()  # create wizards, customize, etc
        game.play_game()


if __name__ == "__main__":
    main()
