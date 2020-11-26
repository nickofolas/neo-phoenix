import logging
import os
import sys

import discord
import toml
from discord.ext import commands

from fubuki import Fubuki
from fubuki.modules.args.commands import ArgCommand, ArgGroup
from fubuki.tools import Patcher

# Sect: Logging

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

# /Sect: Logging
# Sect: Monkeypatches

guild = Patcher(discord.Guild)
gateway = Patcher(discord.gateway.DiscordWebSocket)
group = Patcher(commands.Group)
message = Patcher(discord.Message)


@guild.attribute()
async def fetch_member(self, member_id):
    data = await self._state.http.get_member(self.id, member_id)
    mem = discord.Member(data=data, state=self._state, guild=self)
    self._members[mem.id] = mem
    return mem


@gateway.attribute()
async def identify(self):  # Mobile statuses are funny
    """Sends the IDENTIFY packet."""
    payload = {
        'op': self.IDENTIFY,
        'd': {
            'token': self.token,
            'properties': {
                '$os': sys.platform,
                '$browser': 'Discord iOS',
                '$device': 'discord.py',
                '$referrer': '',
                '$referring_domain': ''
            },
            'compress': True,
            'large_threshold': 250,
            'guild_subscriptions': self._connection.guild_subscriptions,
            'v': 3
        }
    }

    if not self._connection.is_bot:
        payload['d']['synced_guilds'] = []

    if self.shard_id is not None and self.shard_count is not None:
        payload['d']['shard'] = [self.shard_id, self.shard_count]

    state = self._connection
    if state._activity is not None or state._status is not None:
        payload['d']['presence'] = {
            'status': state._status,
            'game': state._activity,
            'since': 0,
            'afk': False
        }

    if state._intents is not None:
        payload['d']['intents'] = state._intents.value

    await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
    await self.send_as_json(payload)
    loggers[-1].info('Shard ID %s has sent the IDENTIFY payload.', self.shard_id)


@group.attribute()
def arg_command(self, **kwargs):
    def inner(func):
        cls = kwargs.get('cls', ArgCommand)
        kwargs['parent'] = self
        result = cls(func, **kwargs)
        self.add_command(result)
        return result
    return inner


@group.attribute()
def arg_group(self, **kwargs):
    def inner(func):
        cls = kwargs.get('cls', ArgGroup)
        kwargs['parent'] = self
        result = cls(func, **kwargs)
        self.add_command(result)
        return result
    return inner


@message.attribute(name='jump_url')
@property
def jump_url(self):
    """:class:`str`: Returns a URL that allows the client to jump to this message."""
    guild_id = getattr(self.guild, 'id', '@me')
    return 'https://canary.discord.com/channels/{0}/{1.channel.id}/{1.id}'.format(guild_id, self)


guild.patch()
gateway.patch()
group.patch()
message.patch()

# /Sect: Monkeypatches
# Sect: Running bot

with open("config.toml", "r") as file:
    config = toml.load(file)

bot = Fubuki(config)
bot.load_extension("jishaku")
bot.run()

# /Sect: Running bot
