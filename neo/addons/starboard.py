import asyncio
from datetime import datetime
import textwrap
from dataclasses import dataclass, field

import discord
from discord import reaction
import neo
from discord import utils
from discord.ext import commands


@dataclass
class Star:
    message_id: int
    starboard_message: discord.PartialMessage
    stars: int

    def __repr__(self):
        return (
            "<{0.__class__.__name__} stars={0.stars} "
            "message_id={0.message_id}>".format(self)
        )

    async def edit(self, **kwargs):
        await self.starboard_message.edit(**kwargs)


@dataclass
class Starboard:
    channel: discord.TextChannel
    stars: list
    threshold: int
    star_format: str
    max_days: int
    emoji: str

    cached_stars: dict[int, Star] = field(init=False)
    lock: asyncio.Lock = field(init=False)
    ready: bool = field(init=False)

    def __post_init__(self):
        self.lock = asyncio.Lock()
        self.cached_stars = {}
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
            self.cached_stars.get(message.id) is not None,
            self.lock.locked()
        ]):
            return

        async with self.lock:
            kwargs = {"message_id": message.id, "stars": stars}
            embed = neo.Embed() \
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
                    name=utils.escape_markdown(getattr(attachment, "filename", "Embed")),
                    value=f"[View]({attachment.url})"
                )

            kwargs["starboard_message"] = await self.channel.send(
                self.star_format.format(stars=stars),
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

        await star.edit(content=self.star_format.format(stars=star.stars))
        return star


class StarboardAddon(neo.Addon, name="Starboard"):
    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self.ready = False
        self.starboards: dict[int, Starboard] = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        starboard_settings = {}
        for record in await self.bot.db.fetch("SELECT * FROM starboards"):
            starboard_settings[record["server_id"]] = record

        for server_id, config in self.bot.servers.items():
            if config.starboard_enabled is False or \
                    server_id not in [*starboard_settings.keys()]:
                continue

            settings = starboard_settings[server_id]
            star_records = await self.bot.db.fetch(
                """
                SELECT
                    message_id,
                    stars,
                    starboard_message_id
                FROM stars
                WHERE server_id=$1
                """, server_id
            )

            kwargs = {
                "channel": self.bot.get_channel(settings["channel_id"]),
                "stars": star_records,
                "threshold": settings["threshold"],
                "star_format": settings["star_format"],
                "max_days": settings["max_days"],
                "emoji": settings["emoji"]
            }
            self.starboards[server_id] = Starboard(**kwargs)

        self.ready = True

    # Takes advantage of the better ratelimits of the history endpoint
    # versus the fetch message endpoint
    async def fetch_message(self, channel: discord.TextChannel, message_id: int):
        return await channel.history(
            limit=1, before=discord.Object(message_id + 1)
        ).next()

    def predicate(self, starboard: Starboard, payload):
        checks = [
            starboard is None,
            not getattr(starboard, "ready", False),
            not self.bot.get_server(starboard.channel.guild.id).starboard_enabled,
            payload.channel_id == starboard.channel.id,
            (datetime.utcnow() - discord.Object(payload.message_id)
             .created_at.replace(tzinfo=None)).days > starboard.max_days
        ]
        return not any(checks)

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
                utils.get(message.reactions, emoji=starboard.emoji),
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
                    server_id,
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


def setup(bot: neo.Neo):
    bot.add_cog(StarboardAddon(bot))
