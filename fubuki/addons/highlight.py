import asyncio
import re
from collections import defaultdict
from functools import cached_property

import fubuki
from discord import NotFound
from discord.ext import commands
from fubuki.modules import args
from fubuki.types.containers import TimedSet

DEFAULT_AVATARS = {  # TODO: Use actual icons for this?
    "red": "🔴",
    "orange": "🟠",
    "green": "🟢",
    "grey": "⚫",
    "blurple": "🔵"
}
EXCESSIVE_OR = re.compile(r"(?<!\\)\|")
EXCESSIVE_ESCAPES = re.compile(r"(?<!\\)\\s|\\d|\\w", re.I)
REGEX_CHECK = re.compile(
    r"""(?<!\\)[\*\+]|
        (?<!\\)\{\d*(\,\s?\d*)?\}|
        (?<!\\)\.""",
    re.I | re.X,
)


def check_regex(content):  # Using sre_parse.parse is too tedious
    """Make sure only permitted patterns are used"""
    if REGEX_CHECK.search(content):
        raise ValueError("Disallowed regex pattern")

    if any(map(
        lambda pattern: len(pattern.findall(content)) > 5,
        (EXCESSIVE_ESCAPES, EXCESSIVE_OR)
    )):
        raise ValueError("Disallowed regex pattern")


def format_hl_context(message, is_trigger=False):
    fmt = (
        "{0} **__{1.author.display_name}:__** {1.content}"
        if is_trigger else
        "{0} **{1.author.display_name}:** {1.content}"
    )
    if message.attachments:
        message.content += " *[Attachment x{}]*".format(len(message.attachments))
    if message.embeds:
        message.content += " *[Embed x{}]*".format(len(message.embeds))

    return fmt.format(
        DEFAULT_AVATARS[message.author.default_avatar.name],
        message
    )


class Highlight:
    def __init__(self, bot, *, content, is_regex, user_id):
        self.bot = bot

        self.content = content
        self.is_regex = is_regex
        self.user_id = user_id

    def __repr__(self):
        return ("<{0.__class__.__name__} user_id={0.user_id!r} "
                "is_regex={0.is_regex} content={0.content!r}>").format(self)

    @cached_property
    def pattern(self):
        if self.is_regex:
            return re.compile(self.content)

        return re.compile(fr"\b{self.content}\b")

    async def predicate(self, message):
        if not message.guild:
            return
        if any([message.author.id == self.user_id,
                message.author.bot]):
            return

        try:  # This lets us update the channel members and make sure the user exists
            member = await message.guild.fetch_member(self.user_id)
        except NotFound:
            return

        # TODO: Logic for highlight blocks

        if member not in message.channel.members:
            return

        return True

    async def to_send_kwargs(self, message):
        content = ""

        for m in reversed(await message.channel.history(limit=5).flatten()):

            formatted = format_hl_context(m, m.id == message.id)
            if len(content + formatted) > 1500:  # Don't exceed embed limits
                formatted = "{0.author.display_name}: *[Omitted due to length]*".format(m)

            content += "{}\n".format(formatted)

        embed = fubuki.Embed(
            title="Highlighted in #{0.channel.name}".format(message),
            description=content
        ).set_author(name=message.guild.name)

        return {
            "content": "{0.author}: {0.content}".format(message)[:1500],
            "embed": embed
        }

    def matches(self, other):
        return self.pattern.search(other)


class Highlights(fubuki.Addon):
    """Commands for managing highlights"""

    def __init__(self, bot):
        self.bot = bot

        self.highlights = []
        self.grace_periods = defaultdict(TimedSet)

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for record in await self.bot.db.fetch("SELECT * FROM highlights"):
            self.highlights.append(Highlight(self.bot, **record))

    @commands.Cog.listener("on_message")
    async def listen_for_highlights(self, message):
        if message.author.id in {hl.user_id for hl in self.highlights}:
            self.grace_periods[message.author.id].add(message.channel.id)

        for hl in filter(lambda hl: hl.matches(message.content), self.highlights):

            if await hl.predicate(message):
                if message.channel.id in self.grace_periods[hl.user_id]:
                    continue

                await self.bot.get_user(hl.user_id).send(
                    **await hl.to_send_kwargs(message)
                )

    @commands.group(aliases=["hl"], invoke_without_command=True)
    async def highlight(self, ctx):
        """List your highlights"""

        description = ""

        for index, hl in enumerate(filter(
            lambda hl: hl.user_id == ctx.author.id,
            self.highlights
        )):
            description += "`{0}` [{1}] `{2}`\n".format(
                index,
                "✓" if hl.is_regex else "⨉",
                hl.content
            )

        embed = fubuki.Embed(description=description or "You have no highlights")

        await ctx.send(embed=embed)

    @args.add_arg(
        "content",
        nargs="*",
        help="The content by which you will be highlighted"
    )
    @args.add_arg(
        "-re", "--regex",
        action="store_true",
        help="Toggles whether or not this highlight should be parsed as regex"
    )
    @highlight.arg_command(name="add")
    async def highlight_add(self, ctx, *, input):
        """Add a new highlight

        Actual documentation coming soonTM"""

        if input.regex:
            check_regex("".join(input.content))

        result = await self.bot.db.fetchrow(
            """
            INSERT INTO highlights (
                user_id,
                content,
                is_regex
            ) VALUES ( $1, $2, $3 )
            RETURNING *
            """,
            ctx.author.id,
            "".join(input.content),
            input.regex
        )
        self.highlights.append(Highlight(self.bot, **result))
        await ctx.message.add_reaction("\U00002611")

    @highlight.command(name="remove", aliases=["rm"])
    async def highlight_remove(self, ctx, hl_index: int):
        """Remove a highlight by its index"""

        to_remove = [*filter(
            lambda hl: hl.user_id == ctx.author.id,
            self.highlights
        )][hl_index]

        await self.bot.db.execute(
            """
            DELETE FROM
                highlights
            WHERE
                user_id = $1 AND
                content = $2 AND
                is_regex = $3
            """,
            to_remove.user_id,
            to_remove.content,
            to_remove.is_regex
        )
        self.highlights.remove(to_remove)
        await ctx.message.add_reaction("\U00002611")


def setup(bot):
    bot.add_cog(Highlights(bot))
