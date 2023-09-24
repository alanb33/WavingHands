import logging.config
from waving_hands.config import LOGGING


LOGGING["handlers"]["console"]["level"] = "DEBUG"
logging.config.dictConfig(LOGGING)
