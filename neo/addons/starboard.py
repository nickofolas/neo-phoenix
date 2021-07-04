# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import asyncio
import textwrap
from datetime import datetime, timezone
from typing import Union

import discord
import neo
from discord.ext import commands
from neo.modules import Paginator
from neo.tools import convert_setting
from neo.types.converters import max_days_converter

SETTINGS_MAPPING = {
    "channel": {
        "converter": commands.TextChannelConverter(),
        "description": None
    },
    "threshold": {
        "converter": int,
        "description": None
    },
    "format": {
        "converter": str,
        "description": None
    },
    "max_days": {
        "converter": max_days_converter,
        "description": None
    },
    "emoji": {
        "converter": discord.PartialEmoji.from_str,
        "description": None
    }
}


class Star:
    __slots__ = ("message_id", "starboard_message", "stars")

    def __init__(
        self,
        *,
        message_id: int,
        starboard_message: discord.PartialMessage,
        stars: int
    ):
        self.message_id = message_id
        self.starboard_message = starboard_message
        self.stars = stars

    def __repr__(self):
        return (
            "<{0.__class__.__name__} stars={0.stars} "
            "message_id={0.message_id}>".format(self)
        )

    async def edit(self, **kwargs):
        await self.starboard_message.edit(**kwargs)


class Starboard:
    __slots__ = (
        "channel",
        "stars",
        "threshold",
        "format",
        "max_days",
        "emoji",
        "ignored",
        "cached_stars",
        "lock",
        "ready"
    )

    def __init__(
        self,
        *,
        channel: discord.TextChannel,
        stars: list,
        threshold: int,
        format: str,
        max_days: int,
        emoji: discord.PartialEmoji,
        ignored: list[str]
    ):
        self.channel = channel
        self.stars = stars
        self.threshold = threshold
        self.format = format
        self.max_days = max_days
        self.emoji = emoji
        self.ignored = ignored

        self.cached_stars = {}
        self.lock = asyncio.Lock()
        self.ready = False

        for star in self.stars:
            message = self.channel.get_partial_message(star["starboard_message_id"])
            self.cached_stars[star["message_id"]] = Star(
                message_id=star["message_id"],
                starboard_message=message,
                stars=star["stars"]
            )

        self.ready = True

    async def create_star(self, message: discord.Message, stars: int):
        if any([
            not self.ready,
            message.id in self.cached_stars,
            self.lock.locked()
        ]):
            return

        async with self.lock:
            kwargs = {"message_id": message.id, "stars": stars}
            embed = neo.Embed(description="") \
                .set_author(
                    name=message.author,
                    icon_url=message.author.avatar
            )

            if message.content:
                embed.description = textwrap.shorten(message.content, 1900) + "\n\n"
            embed.description += f"[Jump]({message.jump_url})"

            for attachment in (*message.attachments, *message.embeds):
                if not embed.image:
                    embed.set_image(url=attachment.url)
                embed.add_field(
                    name=discord.utils.escape_markdown(
                        getattr(attachment, "filename", "Embed")),
                    value=f"[View]({attachment.url})"
                )

            kwargs["starboard_message"] = await self.channel.send(
                self.format.format(stars=stars),
                embed=embed
            )
            star = Star(**kwargs)
            self.cached_stars[message.id] = star
            return star

    async def delete_star(self, id: int):
        if not self.ready:
            return

        star = self.cached_stars.pop(id)
        try:
            await star.starboard_message.delete()
        finally:
            return star

    async def edit_star(self, id: int, stars: int):
        if not self.ready:
            return

        star = self.cached_stars.get(id)
        star.stars = stars

        await star.edit(content=self.format.format(stars=star.stars))
        return star


class StarboardAddon(neo.Addon, name="Starboard"):
    """
    Manages your server's starboard

    If `starboard` is set to False in server
    settings, none of the commands from this category
    will be accessible
    """

    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self.ready = False
        self.starboards: dict[int, Starboard] = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        # Setup starboards
        starboard_settings = {}
        for record in await self.bot.db.fetch("SELECT * FROM starboards"):
            starboard_settings[record["guild_id"]] = record

        for guild_id in self.bot.configs.keys():
            if guild_id not in [*starboard_settings.keys()]:
                continue

            settings = starboard_settings[guild_id]
            self.starboards[guild_id] = await self.create_starboard(
                guild_id,
                settings
            )
        self.ready = True

        # Initialize settings
        for col_name in SETTINGS_MAPPING.keys():
            col_desc = await self.bot.db.fetchval(
                """
                SELECT get_column_description(
                    $1, 'starboards', $2
                )
                """,
                self.bot.cfg["database"]["database"],
                col_name
            )
            SETTINGS_MAPPING[col_name]["description"] = col_desc

    async def create_starboard(self, guild_id, starboard_settings):
        star_records = await self.bot.db.fetch(
            """
            SELECT
                message_id,
                stars,
                starboard_message_id
            FROM stars
            WHERE guild_id=$1
            """, guild_id
        )
        kwargs = {
            "channel": self.bot.get_channel(starboard_settings["channel"]),
            "stars": star_records,
            "threshold": starboard_settings["threshold"],
            "format": starboard_settings["format"],
            "max_days": starboard_settings["max_days"],
            "emoji": discord.PartialEmoji.from_str(starboard_settings["emoji"]),
            "ignored": starboard_settings["ignored"]
        }
        return Starboard(**kwargs)

    # Sect: Event handling

    # Takes advantage of the better ratelimits of the history endpoint
    # versus the fetch message endpoint
    @staticmethod
    async def fetch_message(channel: discord.TextChannel, message_id: int):
        return await channel.history(
            limit=1, before=discord.Object(message_id + 1)
        ).next()

    def predicate(self, starboard: Starboard, payload):
        if starboard is None or starboard.channel is None:
            return False
        checks = [
            not getattr(starboard, "ready", False),
            not self.bot.configs[starboard.channel.guild.id].starboard,
            payload.channel_id == starboard.channel.id,
            (datetime.now(timezone.utc) - discord.Object(payload.message_id)
             .created_at).days > starboard.max_days
        ]
        check_ignored = [  # Ensure the channel/message isn't ignored
            payload.message_id in starboard.ignored,
            payload.channel_id in starboard.ignored
        ]
        checks.append(any(check_ignored))
        return not any(checks)

    @staticmethod
    def reaction_check(starboard: Starboard, emoji):
        if isinstance(emoji, str):
            emoji = discord.PartialEmoji.from_str(emoji)
        return emoji == starboard.emoji

    @commands.Cog.listener("on_raw_reaction_add")
    @commands.Cog.listener("on_raw_reaction_remove")
    async def handle_individual_reaction(self, payload: discord.RawReactionActionEvent):
        starboard: Starboard = self.starboards.get(payload.guild_id)

        if not self.predicate(starboard, payload):
            return

        star = starboard.cached_stars.get(payload.message_id)
        if star is None:
            message = await self.fetch_message(
                self.bot.get_channel(payload.channel_id),
                payload.message_id
            )
            reaction_count = getattr(
                next(filter(
                    lambda r: self.reaction_check(starboard, r.emoji),
                    message.reactions
                ), None),
                "count",
                0
            )
            if reaction_count < starboard.threshold:
                return

            star = await starboard.create_star(message, reaction_count)
            if not star:
                return

            await self.bot.db.execute(
                """
                INSERT INTO stars (
                    guild_id,
                    message_id,
                    channel_id,
                    stars,
                    starboard_message_id
                ) VALUES (
                    $1, $2, $3, $4, $5
                )
                """,
                message.guild.id,
                message.id,
                message.channel.id,
                reaction_count,
                star.starboard_message.id
            )

        else:
            if not self.reaction_check(starboard, payload.emoji):
                return

            # Eventually replace this with a patma
            if payload.event_type == "REACTION_ADD":
                star.stars += 1
            else:
                star.stars -= 1

            if star.stars < starboard.threshold:
                await starboard.delete_star(star.message_id)
                await self.bot.db.execute(
                    "DELETE FROM stars WHERE message_id=$1",
                    star.message_id
                )
            else:
                await starboard.edit_star(star.message_id, star.stars)
                await self.bot.db.execute(
                    """
                    UPDATE stars
                    SET stars=$1
                    WHERE message_id=$2
                    """,
                    star.stars,
                    star.message_id
                )

    @commands.Cog.listener("on_raw_reaction_clear")
    @commands.Cog.listener("on_raw_reaction_clear_emoji")
    @commands.Cog.listener("on_raw_message_delete")
    async def handle_terminations(self, payload):
        starboard: Starboard = self.starboards.get(payload.guild_id)

        if not self.predicate(starboard, payload):
            return

        if isinstance(payload, discord.RawReactionClearEmojiEvent):
            if not self.reaction_check(payload.emoji):
                return

        star = starboard.cached_stars.get(payload.message_id)
        if not star:
            return

        await starboard.delete_star(star.message_id)
        await self.bot.db.execute(
            "DELETE FROM stars WHERE message_id=$1",
            star.message_id
        )

    @commands.Cog.listener("on_config_update")
    async def handle_starboard_setting(self, guild, settings):
        if settings.starboard is True:
            if guild.id in self.starboards:
                return

            # Create a new starboard if one doesn't exist
            starboard_data = await self.bot.db.fetchrow(
                """
                INSERT INTO starboards (
                    guild_id
                ) VALUES ($1)
                RETURNING *
                """,
                guild.id
            )

            self.starboards[guild.id] = await self.create_starboard(
                guild.id,
                starboard_data
            )

    @commands.Cog.listener("on_config_delete")
    async def handle_deleted_config(self, guild_id: int):
        self.starboards.pop(guild_id, None)

    # /Sect: Event Handling
    # Sect: Commands

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        config = self.bot.configs.get(ctx.guild.id)
        if not getattr(config, "starboard", False):
            raise commands.CommandInvokeError(AttributeError(
                "Starboard is not enabled for this server!"
            ))
        return True

    @commands.group(invoke_without_command=True)
    async def starboard(self, ctx):
        """
        Displays an overview of your server's starboard settings

        Descriptions of the settings are also provided here
        """
        starboard = self.starboards[ctx.guild.id]
        embeds = []

        for setting, setting_info in SETTINGS_MAPPING.items():
            description = setting_info["description"].format(
                getattr(starboard, setting)
            )
            embed = neo.Embed(
                title=f"Starboard settings for {ctx.guild}",
                description=f"**Setting: `{setting}`**\n\n" + description
            ).set_thumbnail(
                url=ctx.guild.icon
            )
            embeds.append(embed)

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @starboard.command(name="set")
    @commands.has_permissions(manage_channels=True)
    async def starboard_set(self, ctx, setting, *, new_value):
        """
        Updates the value of a starboard setting

        More information on the available settings and their functions is in the `starboard` command
        """
        value = await convert_setting(ctx, SETTINGS_MAPPING, setting, new_value)
        starboard = self.starboards[ctx.guild.id]
        setattr(starboard, setting, value)

        if setting == "emoji":
            value = str(value)
        await self.bot.db.execute(
            f"""
            UPDATE starboards
            SET
                {setting}=$1
            WHERE
                guild_id=$2
            """,
            getattr(value, "id", value),
            ctx.guild.id
        )
        # ^ Using string formatting in SQL is safe here because
        # the setting is thoroughly validated
        if setting in ["channel", "emoji"]:
            await self.bot.db.execute("DELETE FROM stars WHERE guild_id=$1", ctx.guild.id)
            starboard.cached_stars.clear()
            starboard.stars.clear()

        await ctx.send(f"Setting `{setting}` has been changed!")

    @starboard.command(name="ignore")
    @commands.has_permissions(manage_messages=True)
    async def starboard_ignore(self, ctx, to_ignore: Union[discord.TextChannel, discord.PartialMessage]):
        """
        Ignores a channel or message

        Messages from the channel/the message are prevented
        from being sent to starboard

        Note: If an already starred message is ignored, the
        star will be deleted, *and* the message will be ignored
        """
        starboard = self.starboards[ctx.guild.id]
        id = to_ignore.id

        starboard.ignored.append(id)
        await self.bot.db.execute(
            """
            UPDATE starboards
            SET
                ignored=array_append(ignored, $1)
            WHERE
                guild_id=$2
            """,
            id,
            ctx.guild.id
        )

        if isinstance(to_ignore, discord.PartialMessage) \
                and starboard.cached_stars.get(id):
            await starboard.delete_star(id)
            await self.bot.db.execute(
                "DELETE FROM stars WHERE message_id=$1",
                id
            )

        await ctx.send("Successfully ignored the provided entity!")

    @starboard.command(name="unignore")
    @commands.has_permissions(manage_messages=True)
    async def starboard_unignore(self, ctx, to_ignore: Union[discord.TextChannel, discord.PartialMessage, int]):
        """Unignores a channel or message"""
        starboard = self.starboards[ctx.guild.id]
        id = to_ignore.id

        starboard.ignored.remove(id)
        await self.bot.db.execute(
            """
            UPDATE starboards
            SET
                ignored=array_remove(ignored, $1)
            WHERE
                guild_id=$2
            """,
            id,
            ctx.guild.id
        )

        await ctx.send("Successfully unignored the provided entity!")

    @starboard.command(name="ignored")
    @commands.has_permissions(manage_messages=True)
    async def starboard_ignored(self, ctx):
        """Displays a list of all ignored items"""
        starboard = self.starboards[ctx.guild.id]

        formatted: list[str] = []
        for id in starboard.ignored:
            if (channel := self.bot.get_channel(id)):
                formatted.append(f"Channel: {channel.mention}")
            else:
                formatted.append(f"Message: {id}")

        menu = Paginator.from_iterable(
            formatted or ["No ignored items"],
            per_page=10,
            use_embed=True
        )
        await menu.start(ctx)


def setup(bot: neo.Neo):
    bot.add_cog(StarboardAddon(bot))
