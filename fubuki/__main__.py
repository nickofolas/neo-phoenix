import os

import toml

from fubuki import Fubuki

with open("config.toml", "r") as file:
    config = toml.load(file)

os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'true'
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
os.environ['JISHAKU_RETAIN'] = 'true'

bot = Fubuki(config)
bot.load_extension('jishaku')
bot.run()