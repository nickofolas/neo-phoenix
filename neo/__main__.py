import logging
import os

import discord
import toml
from discord.ext import commands

from neo import Neo
from neo.modules.args.commands import ArgCommand, ArgGroup
from neo.tools import Patcher
from neo.types.formatters import NeoLoggingFormatter
from neo.types.partials import PartialUser

# Sect: Logging
if os.name == "nt":
    os.system("color")  # Enable ANSI escapes on win32

loggers = [logging.getLogger("discord"),
           logging.getLogger("neo")]

formatter = NeoLoggingFormatter(
    fmt="[{asctime}] [{levelname} {name} {funcName}] {message}")
handler = logging.StreamHandler()
handler.setFormatter(formatter)

[(logger.setLevel(logging.INFO),
  logger.addHandler(handler)) for logger in loggers]

# /Sect: Logging
# Sect: Monkeypatches

guild = Patcher(discord.Guild)
gateway = Patcher(discord.gateway.DiscordWebSocket)
group = Patcher(commands.Group)
client = Patcher(discord.Client)
message = Patcher(discord.Message)


@guild.attribute()
async def fetch_member(self, member_id, *, cache=False):
    data = await self._state.http.get_member(self.id, member_id)
    mem = discord.Member(data=data, state=self._state, guild=self)
    if cache:
        self._members[mem.id] = mem
    return mem


@group.attribute()
def arg_command(self, **kwargs):
    def inner(func):
        cls = kwargs.get("cls", ArgCommand)
        kwargs["parent"] = self
        result = cls(func, **kwargs)
        self.add_command(result)
        return result
    return inner


@group.attribute()
def arg_group(self, **kwargs):
    def inner(func):
        cls = kwargs.get("cls", ArgGroup)
        kwargs["parent"] = self
        result = cls(func, **kwargs)
        self.add_command(result)
        return result
    return inner


@client.attribute()
def get_user(self, id, *, as_partial=False):
    user = self._connection.get_user(id)
    if as_partial or not user:
        user = PartialUser(state=self._connection, id=id)
    return user


@message.attribute()
async def add_reaction(self, emoji):
    emoji = discord.message.convert_emoji_reaction(emoji)
    try:
        await self._state.http.add_reaction(self.channel.id, self.id, emoji)
    except discord.HTTPException as e:
        if e.code == 90001:
            return  # Ignore errors from trying to react to blocked users
        raise e  # If not 90001, re-raise

guild.patch()
gateway.patch()
group.patch()
client.patch()
message.patch()

# /Sect: Monkeypatches
# Sect: Running bot

with open("config.toml", "r") as file:
    config = toml.load(file)

bot = Neo(config)
bot.run()

# /Sect: Running bot
