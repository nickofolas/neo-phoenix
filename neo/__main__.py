import logging

import discord
import toml
from discord.ext import commands

from neo import Neo
from neo.modules.args.commands import ArgCommand, ArgGroup
from neo.tools import Patcher
from neo.types.partials import PartialUser

# Sect: Logging

loggers = [logging.getLogger("discord"), logging.getLogger("neo")]

formatter = logging.Formatter(
    fmt="{asctime} [{levelname}/{module}] {message:<5}",
    datefmt="%d/%m/%Y %H:%M:%S",
    style="{",
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

[(logger.setLevel(logging.INFO), logger.addHandler(handler)) for logger in loggers]

# /Sect: Logging
# Sect: Monkeypatches

guild = Patcher(discord.Guild)
gateway = Patcher(discord.gateway.DiscordWebSocket)
group = Patcher(commands.Group)
client = Patcher(discord.Client)


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


guild.patch()
gateway.patch()
group.patch()
client.patch()

# /Sect: Monkeypatches
# Sect: Running bot

with open("config.toml", "r") as file:
    config = toml.load(file)

bot = Neo(config)
bot.run()

# /Sect: Running bot
