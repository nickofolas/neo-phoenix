import os
import logging

import toml

from fubuki import Fubuki

with open("config.toml", "r") as file:
    config = toml.load(file)

loggers = [logging.getLogger("discord"), logging.getLogger("fubuki")]

formatter = logging.Formatter(
    fmt="{asctime} [{levelname}/{module}] {message:<5}",
    datefmt="%d/%m/%Y %H:%M:%S",
    style="{",
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

[(logger.setLevel(logging.INFO), logger.addHandler(handler)) for logger in loggers]

os.environ["JISHAKU_NO_DM_TRACEBACK"] = "true"
os.environ["JISHAKU_NO_UNDERSCORE"] = "true"
os.environ["JISHAKU_RETAIN"] = "true"

bot = Fubuki(config)
bot.load_extension("jishaku")
bot.run()
