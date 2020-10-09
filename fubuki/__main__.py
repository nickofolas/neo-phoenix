import toml

from fubuki import Fubuki

with open("config.toml", "r") as file:
    config = toml.load(file)

bot = Fubuki(config)
bot.load_extension('jishaku')
bot.run()