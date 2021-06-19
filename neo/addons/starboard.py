import asyncio
import textwrap
from dataclasses import dataclass, field

import discord
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
    stars: list[dict[str, int]]
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

    def __await__(self):
        return self.__ainit__().__await__()

    async def __ainit__(self):
        for star in self.stars:
            message = self.channel.get_partial_message(star["starboard_message_id"])
            self.cached_stars[star["message_id"]] = Star(
                message_id=star["message_id"],
                starboard_message=message,
                stars=star["stars"]
            )

        self.ready = True
        return self

    @property
    def stars(self):
        return self.cached_stars

    async def create_star(self, message: discord.Message, stars: int):
        if any([
            not self.ready,
            self.get_star(message.id) is not None,
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

        await star.edit(self.star_format.format(stars=star.stars))
        return star


class StarboardAddon(neo.Addon, name="Starboard"):
    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self.ready = False
        self.starboards: dict[int, Starboard] = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for server_id, config in self.bot.servers.items():
            if config.starboard_enabled is False:
                continue

            star_records = await self.bot.db.fetch(
                """
                SELECT
                    message_id,
                    stars,
                    starboard_message_id
                FROM stars
                WHERE guild_id=$1
                """, server_id
            )
