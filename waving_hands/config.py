import pathlib

BASEPATH = pathlib.Path(__file__).parent
DATA_PATH = BASEPATH / "data"

LOGGING = {
    "version": 1,
    "formatters": {
        "basic": {
            "format": "[%(levelname)s] " "%(name)s::%(funcName)s() %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "basic",
        }
    },
    "loggers": {
        "waving_hands": {"level": "DEBUG", "handlers": ["console"]},
    },
}
DATA = {
    "spellbook": DATA_PATH / "spelllist.txt",
    "names": {
        "first": DATA_PATH / "groble_first_names.txt",
        "last_first": DATA_PATH / "groble_last_first_compound.txt",
        "last_second": DATA_PATH / "groble_last_second_compound.txt",
        # Not currently used anywhere, and can be removed
        "all": DATA_PATH / "groble_names.txt"
    }
}
