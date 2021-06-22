import re
from collections import defaultdict
from functools import cached_property
from operator import attrgetter

import neo
from discord import NotFound
from discord.ext import commands
from neo.modules import paginator
from neo.types.containers import TimedSet

DEFAULT_AVATARS = ["🔵", "⚫", "🟢", "🟠", "🔴"]
MAX_TRIGGERS = 10


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
        DEFAULT_AVATARS[int(message.author.default_avatar.key)],
        message
    )


class Highlight:
    def __init__(self, bot, *, content, user_id):
        self.bot = bot

        self.content = content
        self.user_id = user_id

    def __repr__(self):
        return ("<{0.__class__.__name__} user_id={0.user_id!r} "
                "content={0.content!r}>").format(self)

    @cached_property
    def pattern(self):
        return re.compile(fr"\b{self.content}\b")

    async def predicate(self, message):
        if not message.guild:
            return
        if any([message.author.id == self.user_id,
                message.author.bot]):
            return

        if self.bot.get_profile(self.user_id).receive_highlights is False:
            return  # Don't highlight users who have disabled highlight receipt

        blacklist = self.bot.get_profile(self.user_id).hl_blocks
        if any(attrgetter(attr)(message) in blacklist for attr in (
                "id", "guild.id", "channel.id", "author.id")
               ):
            return

        try:  # This lets us update the channel members and make sure the user exists
            member = await message.guild.fetch_member(self.user_id, cache=True)
        except NotFound:
            return

        if member not in message.channel.members:
            return

        if member in message.mentions:
            return  # Don't highlight users with messages they are mentioned in

        return True

    async def to_send_kwargs(self, message):
        content = ""

        for m in reversed(await message.channel.history(limit=5).flatten()):

            formatted = format_hl_context(m, m.id == message.id)
            if len(content + formatted) > 1500:  # Don't exceed embed limits
                formatted = "{0.author.display_name}: *[Omitted due to length]*".format(m)

            content += "{}\n".format(formatted)

        content += f"[Jump]({message.jump_url})"

        embed = neo.Embed(
            title="In {0.guild.name}/#{0.channel.name}".format(message),
            description=content
        )

        return {
            "content": "{0.author}: {0.content}".format(message)[:1500],
            "embed": embed
        }

    def matches(self, other):
        return self.pattern.search(other)


class Highlights(neo.Addon):
    """Commands for managing highlights"""

    def __init__(self, bot: neo.Neo):
        self.bot = bot

        self.highlights = []
        self.grace_periods: dict[int, TimedSet] = {}  # TODO: Configurable timeouts?

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for record in await self.bot.db.fetch("SELECT * FROM highlights"):
            self.highlights.append(Highlight(self.bot, **record))

        for profile in self.bot.profiles.values():
            self.grace_periods[profile.user_id] = TimedSet(
                decay_time=profile.hl_timeout * 60
            )

    def get_user_highlights(self, user_id):
        return [*filter(
            lambda hl: hl.user_id == user_id,
            self.highlights
        )]

    @commands.Cog.listener("on_message")
    async def listen_for_highlights(self, message):
        if message.author.id in {hl.user_id for hl in self.highlights}:
            self.grace_periods[message.author.id].add(message.channel.id)

        to_deliver = {}  # Collect all highlights so only one message is sent per user
        for hl in filter(lambda hl: hl.matches(message.content), self.highlights):

            if await hl.predicate(message):
                if message.channel.id in self.grace_periods[hl.user_id]:
                    continue
                to_deliver[hl.user_id] = (hl, message)

        for hl, message in to_deliver.values():
            await self.bot.get_user(hl.user_id, as_partial=True).send(
                **await hl.to_send_kwargs(message)
            )

    @commands.Cog.listener("on_user_settings_update")
    async def handle_update_profile(self, user, profile):
        if self.grace_periods.get(user.id):
            current_timeout = self.grace_periods[user.id].decay_time
            if (profile.hl_timeout * 60) == current_timeout:
                return
            for item in (t_set := self.grace_periods.pop(user.id)):
                t_set.running.pop(item).cancel()

        self.grace_periods[profile.user_id] = TimedSet(
            decay_time=profile.hl_timeout * 60
        )

    # Need to dynamically account for deleted profiles
    @commands.Cog.listener("on_profile_delete")
    async def handle_deleted_profile(self, user_id: int):
        self.grace_periods.pop(user_id, None)
        to_delete = [*filter(lambda hl: hl.user_id == user_id, self.highlights)]
        for hl in to_delete:
            self.highlights.remove(hl)

    async def cog_check(self, ctx):
        if not self.bot.get_profile(ctx.author.id):
            raise commands.CommandInvokeError(AttributeError(
                "Looks like you don't have an existing profile! "
                "You can fix this with the `profile create` command."
            ))
        return True

    @commands.group(aliases=["hl"], invoke_without_command=True)
    async def highlight(self, ctx):
        """List your highlights"""

        description = ""
        user_highlights = self.get_user_highlights(ctx.author.id)

        for index, hl in enumerate(user_highlights):
            description += "`{0}` `{1}`\n".format(
                index,
                hl.content
            )

        embed = neo.Embed(description=description or "You have no highlights")
        embed.set_footer(text=f"{len(user_highlights)}/{MAX_TRIGGERS} slots used")
        await ctx.send(embed=embed)

    @highlight.command(name="add")
    async def highlight_add(self, ctx, *, content):
        """
        Add a new highlight

        Highlights will notify you when the word/phrase you add is mentioned
        """

        if len(content) <= 1:
            raise ValueError("Highlights must contain more than 1 character.")

        if len(self.get_user_highlights(ctx.author.id)) >= MAX_TRIGGERS:
            raise ValueError("You've used up all of your highlight slots!")

        if content in [hl.content for hl in self.get_user_highlights(ctx.author.id)]:
            raise ValueError("Cannot have multiple highlights with the same content.")

        result = await self.bot.db.fetchrow(
            """
            INSERT INTO highlights (
                user_id,
                content
            ) VALUES ( $1, $2 )
            RETURNING *
            """,
            ctx.author.id,
            content
        )
        self.highlights.append(Highlight(self.bot, **result))
        await ctx.message.add_reaction("\U00002611")

    # TODO: This needs to support index chaining.
    @highlight.command(name="remove", aliases=["rm"])
    async def highlight_remove(self, ctx, hl_index: int):
        """Remove a **single** highlight by its index"""

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
                content = $2
            """,
            to_remove.user_id,
            to_remove.content
        )
        self.highlights.remove(to_remove)
        await ctx.message.add_reaction("\U00002611")

    def perform_blocklist_action(self, *, profile, ids, action="block"):
        blacklist = {*profile.hl_blocks, }
        ids = {*ids, }

        if action == "unblock":
            blacklist -= ids
        else:
            blacklist |= ids

        profile.hl_blocks = [*blacklist]

    @highlight.command(name="block")
    async def highlight_block(self, ctx, ids: commands.Greedy[int]):
        """
        Manage a blocklist for highlights. Run with no arguments for a list of your blocks

        Servers, users, and channels can all be blocked via ID

        A variable number of IDs can be provided to this command
        """

        profile = self.bot.get_profile(ctx.author.id)

        if not ids:

            def transform_mention(id):
                mention = getattr(self.bot.get_guild(id), "name",
                                  getattr(self.bot.get_channel(id), "mention",
                                          f"<@{id}>"))  # Yes, this could lead to fake user mentions
                return "`{0}` [{1}]".format(id, mention)

            menu = paginator.Paginator.from_iterable(
                [*map(transform_mention, profile.hl_blocks)] or ["No highlight blocks"],
                per_page=10,
                use_embed=True
            )
            await menu.start(ctx)
            return

        self.perform_blocklist_action(profile=profile, ids=ids)
        await ctx.message.add_reaction("\U00002611")

    @highlight.command(name="unblock")
    async def highlight_unblock(self, ctx, ids: commands.Greedy[int]):
        """
        Unblock entities from triggering your highlights

        Servers, users, and channels can all be unblocked via ID

        A variable number of IDs can be provided to this command
        """

        profile = self.bot.get_profile(ctx.author.id)

        self.perform_blocklist_action(profile=profile, ids=ids, action="unblock")
        await ctx.message.add_reaction("\U00002611")


def setup(bot):
    bot.add_cog(Highlights(bot))
