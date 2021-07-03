# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import asyncio
import logging
import sys
from time import time

import discord
from aiohttp import ClientSession
from asyncpg import create_pool
from discord.ext import commands

from .modules import *  # noqa: F403
from .tools import *  # noqa: F403
from .types import Embed, containers, context, formatters, help_command

__version__ = "0.7.0"

log = logging.getLogger(__name__)


class Neo(commands.Bot):
    def __init__(self, config, **kwargs):
        self.cfg = config
        self.boot_time = int(time())
        self.session = None
        self.profiles: dict[int, containers.NeoUser] = {}
        self.servers: dict[int, containers.NeoServer] = {}

        kwargs.setdefault("command_prefix", self.get_prefix)
        kwargs.setdefault("activity", discord.Activity(
            name=config["bot"]["activity_name"],
            type=discord.ActivityType[config["bot"]["activity_type"]],
            url="https://twitch.tv/#"  # for spoofing Discord when activity type is streaming
        ))
        kwargs.setdefault("status", discord.Status[config["bot"]["status"]])
        kwargs.setdefault("allowed_mentions", discord.AllowedMentions.none())
        kwargs.setdefault("help_command", help_command.NeoHelpCommand())

        super().__init__(**kwargs)

        self.cooldown = commands.CooldownMapping.from_cooldown(
            1, 2.5, commands.BucketType.user)
        self.check(self.global_cooldown)  # Register global cooldown

        self._async_ready = asyncio.Event()
        self.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        self.session = ClientSession()
        self.db = await create_pool(**self.cfg["database"])

        for record in await self.db.fetch("SELECT * FROM profiles"):
            await self.add_profile(record["user_id"], record=record)

        for record in await self.db.fetch("SELECT * FROM servers"):
            await self.add_server(record["server_id"], record=record)

        self._async_ready.set()
        await self.verify_servers()

    async def wait_until_ready(self):
        await self._async_ready.wait()
        await self._ready.wait()

    async def verify_servers(self) -> None:
        await self.wait_until_ready()

        for server_id in self.servers.copy().keys():
            if not self.get_guild(server_id):
                await self.delete_server(server_id)

    def get_profile(self, user_id: int) -> containers.NeoUser:
        return self.profiles.get(user_id)

    def get_server(self, server_id: int) -> containers.NeoServer:
        return self.servers.get(server_id)

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
        self.profiles[user_id] = containers.NeoUser(pool=self.db, **record)
        return self.get_profile(user_id)

    async def delete_profile(self, user_id: int):
        self.profiles.pop(user_id, None)
        await self.db.execute(
            """
            DELETE FROM
                profiles
            WHERE
                user_id=$1
            """,
            user_id
        )
        self.dispatch("profile_delete", user_id)

    async def add_server(self, server_id: int, *, record=None):
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
        self.servers[server_id] = containers.NeoServer(pool=self.db, **record)
        return self.get_server(server_id)

    async def delete_server(self, server_id: int):
        self.servers.pop(server_id, None)
        await self.db.execute(
            """
            DELETE FROM
                servers
            WHERE
                server_id=$1
            """,
            server_id
        )
        self.dispatch("server_delete", server_id)

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

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.content != before.content:
            await self.process_commands(after)

    async def get_prefix(self, message: discord.Message) -> list[str]:
        if message.guild:
            return commands.when_mentioned_or(getattr(
                self.get_server(message.guild.id),
                "prefix",
                self.cfg["bot"]["prefix"]
            ))(self, message)

        return commands.when_mentioned_or(self.cfg["bot"]["prefix"])(self, message)

    async def on_error(self, error):
        log.error("\n" + formatters.format_exception(sys.exc_info()))

    async def on_command_error(self, ctx, error):
        real_error = getattr(error, "original", error)
        if real_error.__class__.__name__ in self.cfg["bot"]["ignored_exceptions"]:
            return  # Ignore exceptions specified in config

        await ctx.send(real_error)
        log.error("\n" + formatters.format_exception(error))

    async def get_context(self, message: discord.Message, *, cls=context.NeoContext):
        return await super().get_context(message, cls=cls)

    async def on_guild_remove(self, guild: discord.Guild):
        await self.delete_server(guild.id)

    async def global_cooldown(self, ctx: context.NeoContext):
        if await self.is_owner(ctx.author):
            return True

        retry_after = self.cooldown.update_rate_limit(ctx.message)
        if retry_after:
            raise commands.CommandOnCooldown(self.cooldown, retry_after)
        return True
