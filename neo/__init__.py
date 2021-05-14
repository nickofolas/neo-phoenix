import logging
from asyncio import all_tasks

import discord
from aiohttp import ClientSession
from asyncpg import create_pool
from discord.ext import commands

from .modules import *  # noqa: F403
from .tools import *  # noqa: F403
from .types import Embed, help_command, containers

log = logging.getLogger(__name__)
# intents = discord.Intents.all()


class Neo(commands.Bot):
    def __init__(self, config, **kwargs):

        self.cfg = config
        self.session = None
        self._profiles = {}
        self._servers = {}

        kwargs.setdefault("command_prefix", self.get_prefix)
        kwargs.setdefault("activity", discord.Activity(
            name=config["bot"]["activity_name"],
            type=discord.ActivityType[config["bot"]["activity_type"]],
            url="https://twitch.tv/#"  # for spoofing Discord when activity type is streaming
        ))
        kwargs.setdefault("status", discord.Status[config["bot"]["status"]])
        kwargs.setdefault("allowed_mentions", discord.AllowedMentions.none())
        kwargs.setdefault("help_command", help_command.NeoHelpCommand())
        # kwargs.setdefault("intents", intents)

        super().__init__(**kwargs)

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        self.session = ClientSession()
        self.db = await create_pool(**self.cfg["database"])

        for record in await self.db.fetch("SELECT * FROM profiles"):
            await self.add_profile(record["user_id"], record=record)

        for record in await self.db.fetch("SELECT * FROM servers"):
            await self.add_server(record["server_id"], record=record)

    def get_profile(self, user_id):
        return self._profiles.get(user_id)

    def get_server(self, server_id):
        return self._servers.get(server_id)

    async def add_profile(self, user_id, *, record=None):
        if not record:
            record = await self.db.fetchrow(
                """
                INSERT INTO profiles (
                    user_id
                ) VALUES (
                    $1
                ) RETURNING *
                """,
                user_id
            )

        self._profiles[user_id] = containers.NeoUser(pool=self.db, **record)
        return self.get_profile(user_id)

    async def add_server(self, server_id, *, record=None):
        if not record:
            record = await self.db.fetchrow(
                """
                INSERT INTO servers (
                    server_id
                ) VALUES (
                    $1
                ) RETURNING *
                """,
                server_id
            )

        self._servers[server_id] = containers.NeoServer(pool=self.db, **record)
        return self.get_server(server_id)

    def run(self):
        for addon in self.cfg["addons"]:
            self.load_extension(addon)

        super().run(self.cfg["bot"]["token"])

    async def close(self):
        await self.session.close()
        await self.db.close()
        await super().close()

    async def on_ready(self):
        log.info(f"{self.user} has received ready event")

    async def on_message_edit(self, before, after):
        if after.content != before.content:
            await self.process_commands(after)

    async def get_prefix(self, message):
        if message.guild:
            return commands.when_mentioned_or(getattr(
                self.get_server(message.guild.id),
                "prefix",
                self.cfg["bot"]["prefix"]
            ))(self, message)

        return commands.when_mentioned_or(self.cfg["bot"]["prefix"])(self, message)

    async def on_command_error(self, ctx, error):
        await ctx.send(repr(getattr(error, "original", error)))
