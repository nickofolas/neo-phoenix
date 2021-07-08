# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import re
from collections import defaultdict
from functools import cached_property
from operator import attrgetter

import discord
import neo
from discord.ext import commands
from neo.modules import ButtonsMenu
from neo.tools import is_registered_profile
from neo.types.containers import TimedSet
from neo.types.timer import periodic

DEFAULT_AVATARS = [
    "<:def0:842552954389266442>",
    "<:def1:842552984369496084>",
    "<:def2:842553028581130260>",
    "<:def3:842553081681543169>",
    "<:def4:842553168105570304>"
]
MAX_TRIGGERS = 10
MAX_TRIGGER_LEN = 100


def format_hl_context(message: discord.Message, is_trigger=False):
    fmt = (
        "[{0} **{1.author.display_name}**]({1.jump_url}) {1.content}"
        if is_trigger else
        "{0} **{1.author.display_name}** {1.content}"
    )
    if message.attachments:
        message.content += " *[Attachment x{}]*".format(len(message.attachments))
    if message.embeds:
        message.content += " *[Embed x{}]*".format(len(message.embeds))
    if message.stickers:
        message.content += " *[Sticker x{}]*".format(len(message.stickers))

    return fmt.format(
        DEFAULT_AVATARS[int(message.author.default_avatar.key)],
        message
    )


class Highlight:
    __slots__ = ("bot", "content", "user_id", "pattern")

    def __init__(self, bot: neo.Neo, *, content, user_id):
        self.bot = bot
        self.content = content
        self.user_id = user_id
        self.pattern = re.compile(fr"\b{self.content}\b")

    def __repr__(self):
        return ("<{0.__class__.__name__} user_id={0.user_id!r} "
                "content={0.content!r}>").format(self)

    async def predicate(self, message):
        if not message.guild:
            return
        if any([message.author.id == self.user_id,
                message.author.bot]):
            return
        if self.bot.profiles[self.user_id].receive_highlights is False:
            return  # Don't highlight users who have disabled highlight receipt

        blacklist = self.bot.profiles[self.user_id].hl_blocks
        if any(attrgetter(attr)(message) in blacklist for attr in (
                "id", "guild.id", "channel.id", "author.id")
               ):
            return

        if self.user_id in [m.id for m in message.mentions]:
            return  # Don't highlight users with messages they are mentioned in

        try:  # This lets us update the channel members and make sure the user exists
            member = await message.guild.fetch_member(self.user_id, cache=True)
        except discord.NotFound:
            return

        if isinstance(message.channel, discord.Thread):
            if message.channel.is_private():  # Ignore private threads
                return
            members = message.channel.parent.members
        else:
            members = message.channel.members
        if member not in members:  # Check channel membership
            return

        return True

    async def to_send_kwargs(self, message):
        content = ""
        for m in await message.channel.history(limit=5).flatten():
            if len(content + m.content) > 1500:  # Don't exceed embed limits
                m.content = "*[Omitted due to length]*"
            formatted = format_hl_context(
                m, self.matches(m.content) and m.id >= message.id)
            content = f"{formatted}\n{content}"

        embed = neo.Embed(
            title="In {0.guild.name}/#{0.channel.name}".format(message),
            description=content,
            timestamp=message.created_at
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
        self.highlights: defaultdict[str, list[Highlight]] = defaultdict(list)
        self.grace_periods: dict[int, TimedSet] = {}
        self.queued_highlights: defaultdict[int, dict] = defaultdict(dict)
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for record in await self.bot.db.fetch("SELECT * FROM highlights"):
            self.highlights[record["user_id"]].append(Highlight(self.bot, **record))

        for profile in self.bot.profiles.values():
            self.grace_periods[profile.user_id] = TimedSet(
                decay_time=profile.hl_timeout * 60
            )

        self.send_queued_highlights.start()

    def cog_unload(self):
        self.send_queued_highlights.shutdown()

    def get_user_highlights(self, user_id):
        return self.highlights.get(user_id, [])

    @cached_property  # Cache this so it isn't re-computed after every message
    def flat_highlights(self):
        return [hl for hl_list in self.highlights.values() for hl in hl_list]

    def recompute_flattened(self):
        if hasattr(self, "flat_highlights"):
            del self.flat_highlights
        self.flat_highlights

    @commands.Cog.listener("on_message")
    async def listen_for_highlights(self, message):
        if message.author.id in {hl.user_id for hl in self.flat_highlights}:
            self.grace_periods[message.author.id].add(message.channel.id)

        for hl in filter(lambda hl: hl.matches(message.content), self.flat_highlights):
            if message.channel.id in self.grace_periods[hl.user_id]:
                continue
            if not await hl.predicate(message):
                continue
            if not self.queued_highlights[message.channel.id] \
                    .get(hl.user_id):
                self.queued_highlights[message.channel.id][hl.user_id] = \
                    (hl, message)

    @periodic(5)
    async def send_queued_highlights(self):
        queue = self.queued_highlights.copy()
        self.queued_highlights.clear()
        for hl, message in [pair for nested in queue.values() for pair in nested.values()]:
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
        self.highlights.pop(user_id, None)
        self.recompute_flattened()

    async def cog_check(self, ctx):
        return await is_registered_profile().predicate(ctx)

    @commands.group(aliases=["hl"], invoke_without_command=True)
    async def highlight(self, ctx):
        """List your highlights"""
        description = ""
        user_highlights = self.get_user_highlights(ctx.author.id)

        for index, hl in enumerate(user_highlights, 1):
            description += "`{0}` `{1}`\n".format(
                index,
                hl.content
            )

        embed = neo.Embed(description=description or "You have no highlights") \
            .set_footer(text=f"{len(user_highlights)}/{MAX_TRIGGERS} slots used") \
            .set_author(name=f"{ctx.author}'s highlights", icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @highlight.command(name="add")
    async def highlight_add(self, ctx, *, content):
        """
        Add a new highlight

        Highlights will notify you when the word/phrase you add is mentioned

        **Note**
        Highlights will __never__ be triggered from private threads.
        """
        if len(content) <= 1:
            raise ValueError("Highlights must contain more than 1 character.")
        elif len(content) >= MAX_TRIGGER_LEN:
            raise ValueError(
                f"Highlights cannot be longer than {MAX_TRIGGER_LEN:,} characters!")

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
        self.highlights[ctx.author.id].append(Highlight(self.bot, **result))
        self.recompute_flattened()
        await ctx.message.add_reaction("\U00002611")

    @highlight.command(name="remove", aliases=["rm"])
    async def highlight_remove(self, ctx, *indices):
        """
        Remove 1 or more highlight by index

        Passing `~` will remove all highlights at once
        """
        if "~" in indices:
            highlights = self.get_user_highlights(ctx.author.id).copy()
            self.highlights.pop(ctx.author.id, None)

        else:
            (indices := [*map(str, indices)]).sort(reverse=True)  # Pop in an way that preserves the list's original order
            try:
                highlights = [self.highlights[ctx.author.id].pop(index - 1) for index in map(
                    int, filter(str.isdigit, indices))
                ]
            except IndexError:
                raise IndexError("One or more of the provided indices is invalid.")

        await self.bot.db.execute(
            """
            DELETE FROM
                highlights
            WHERE
                user_id = $1 AND
                content = ANY($2::TEXT[])
            """,
            ctx.author.id,
            [*map(attrgetter("content"), highlights)]
        )
        self.recompute_flattened()
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
        profile = self.bot.profiles[ctx.author.id]

        if not ids:

            def transform_mention(id):
                mention = getattr(self.bot.get_guild(id), "name",
                                  getattr(self.bot.get_channel(id), "mention",
                                          f"<@{id}>"))  # Yes, this could lead to fake user mentions
                return "`{0}` [{1}]".format(id, mention)

            menu = ButtonsMenu.from_iterable(
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
        profile = self.bot.profiles[ctx.author.id]

        self.perform_blocklist_action(profile=profile, ids=ids, action="unblock")
        await ctx.message.add_reaction("\U00002611")


def setup(bot):
    bot.add_cog(Highlights(bot))
