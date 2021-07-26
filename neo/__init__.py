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

__version__ = "0.10.1"

log = logging.getLogger(__name__)
intents = discord.Intents(
    **dict.fromkeys(["messages", "guilds", "guild_reactions"], True))


class Neo(commands.Bot):
    def __init__(self, config, **kwargs):
        self.cfg = config
        self.boot_time = int(time())
        self.session = None
        self.profiles: dict[int, containers.NeoUser] = {}
        self.configs: dict[int, containers.NeoGuildConfig] = {}

        kwargs["command_prefix"] = self.get_prefix
        kwargs["activity"] = discord.Activity(
            name=config["bot"]["activity_name"],
            type=discord.ActivityType[config["bot"]["activity_type"]],
            url="https://twitch.tv/#"  # for spoofing Discord when activity type is streaming
        )
        kwargs["status"] = discord.Status[config["bot"]["status"]]
        kwargs["allowed_mentions"] = discord.AllowedMentions.none()
        kwargs["help_command"] = help_command.NeoHelpCommand()
        kwargs["intents"] = intents

        super().__init__(**kwargs)

        self.cooldown = commands.CooldownMapping.from_cooldown(
            2, 4, commands.BucketType.user)
        self.add_check(self.global_cooldown, call_once=True)  # Register global cooldown

        self._async_ready = asyncio.Event()
        self.loop.create_task(self.__ainit__())

    async def __ainit__(self) -> None:
        self.session = ClientSession()
        self.db = await create_pool(**self.cfg["database"])

        for record in await self.db.fetch("SELECT * FROM profiles"):
            await self.add_profile(record["user_id"], record=record)

        for record in await self.db.fetch("SELECT * FROM guild_configs"):
            await self.add_config(record["guild_id"], record=record)

        self._async_ready.set()
        await self.verify_configs()

    async def wait_until_ready(self):
        await self._async_ready.wait()
        await self._ready.wait()

    async def verify_configs(self) -> None:
        await self.wait_until_ready()

        for guild_id in self.configs.copy():
            if not self.get_guild(guild_id):
                await self.delete_config(guild_id)

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
        profile = containers.NeoUser(pool=self.db, **record)
        self.profiles[user_id] = profile
        return profile

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

    async def add_config(self, guild_id: int, *, record=None):
        if not record:
            record = await self.db.fetchrow(
                """
                INSERT INTO guild_configs (
                    guild_id
                ) VALUES (
                    $1
                ) RETURNING *
                """,
                guild_id
            )
        config = containers.NeoGuildConfig(pool=self.db, **record)
        self.configs[guild_id] = config
        return config

    async def delete_config(self, guild_id: int):
        self.configs.pop(guild_id, None)
        await self.db.execute(
            """
            DELETE FROM
                guild_configs
            WHERE
                guild_id=$1
            """,
            guild_id
        )
        self.dispatch("config_delete", guild_id)

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
                self.configs.get(message.guild.id),
                "prefix",
                self.cfg["bot"]["prefix"]
            ))(self, message)

        return commands.when_mentioned_or(self.cfg["bot"]["prefix"])(self, message)

    async def on_error(self, *args, **kwargs):
        log.error("\n" + formatters.format_exception(sys.exc_info()))

    async def on_command_error(self, ctx, error):
        real_error = getattr(error, "original", error)
        if real_error.__class__.__name__ in self.cfg["bot"]["ignored_exceptions"]:
            return  # Ignore exceptions specified in config

        try:
            await ctx.send(real_error)
        except discord.Forbidden:
            pass  # Maybe we can't send messages in the channel
        log.error(f"In command invocation: {ctx.message.content}\n" + formatters
                  .format_exception(real_error))

    async def get_context(self, message: discord.Message, *, cls=context.NeoContext):
        return await super().get_context(message, cls=cls)

    async def on_guild_remove(self, guild: discord.Guild):
        await self.delete_config(guild.id)

    async def global_cooldown(self, ctx: context.NeoContext):
        if await self.is_owner(ctx.author):
            return True

        retry_after = self.cooldown.update_rate_limit(ctx.message)
        if retry_after:
            raise commands.CommandOnCooldown(
                self.cooldown, retry_after, commands.BucketType.user)
        return True
