# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from collections import defaultdict
from datetime import datetime, timezone
from typing import Union

import discord
import neo
from discord.ext import commands
from discord.utils import snowflake_time
from neo.modules import ButtonsMenu
from neo.tools import is_registered_profile, shorten
from neo.tools.time_parse import parse_absolute, parse_relative

MAX_REMINDERS = 15
MAX_REMINDER_LEN = 1000


class Reminder:
    __slots__ = (
        "user_id",
        "message_id",
        "channel_id",
        "content",
        "end_time",
        "bot",
        "wait_task"
    )

    def __init__(
        self,
        *,
        user_id: int,
        message_id: int,
        channel_id: int,
        content: str,
        end_time: datetime,
        bot: neo.Neo
    ):
        self.user_id = user_id
        self.message_id = message_id
        self.channel_id = channel_id
        self.content = content
        self.end_time = end_time
        self.bot = bot

        self.wait_task = bot.loop.create_task(self.wait())

    @property
    def channel(self) -> Union[discord.TextChannel, discord.DMChannel]:
        if (channel := self.bot.get_channel(self.channel_id)) is not None:
            return channel
        return None

    @property
    def message(self) -> discord.PartialMessage:
        return self.channel.get_partial_message(self.message_id)

    async def wait(self):
        await discord.utils.sleep_until(self.end_time)
        await self.deliver()

    async def deliver(self):
        """Deliver a reminder, falling back to a primitive format if necessary"""
        try:
            sent = None
            if self.channel is not None:
                try:
                    sent = await self.message.reply(
                        f"**Reminder**:\n{self.content}",
                        allowed_mentions=discord.AllowedMentions(replied_user=True)
                    )
                except discord.HTTPException:
                    pass
            if sent is None:
                await self.fallback_deliver()

        finally:  # Ensure that the database entry is always deleted
            await self.delete()

    async def fallback_deliver(self) -> None:
        """Fallback to a primitive delivery format if normal deliver is impossible"""
        try:
            dest = self.channel or self.bot.get_user(self.user_id, as_partial=True)
            await dest.send(
                "<@{0}> **Reminder** [source deleted]:\n> {1}".format(
                    self.user_id,
                    self.content
                ),
                allowed_mentions=discord.AllowedMentions(
                    users=[discord.Object(self.user_id)]
                )
            )
        except discord.HTTPException:
            return

    async def delete(self):
        """Remove this reminder from the database"""
        await self.bot.db.execute(
            """
            DELETE FROM
                reminders
            WHERE
                user_id=$1 AND
                message_id=$2 AND
                content=$3 AND
                end_time=$4
            """,
            self.user_id,
            self.message_id,
            self.content,
            self.end_time
        )
        try:  # Need to cancel the task
            self.wait_task.cancel()
        finally:  # ...but need to ensure that dispatch is after cancel
            self.bot.dispatch("reminder_removed", self.user_id)


class Reminders(neo.Addon):
    """Contains everything related to reminders"""

    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self.reminders: dict[int, list[Reminder]] = defaultdict(list)

        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for record in await self.bot.db.fetch("SELECT * FROM reminders"):
            reminder = Reminder(bot=self.bot, **record)
            self.reminders[record["user_id"]].append(reminder)

    @commands.Cog.listener("on_profile_delete")
    async def handle_deleted_profile(self, user_id: int):
        for reminder in self.reminders.pop(user_id, []):
            await reminder.delete()

    @commands.Cog.listener("on_reminder_removed")
    async def handle_removed_reminder(self, user_id: int):
        self.reminders[user_id] = [*filter(
            lambda r: not r.wait_task.done(),
            self.reminders[user_id].copy()
        )]

    async def cog_check(self, ctx):
        return await is_registered_profile().predicate(ctx)

    def cog_unload(self):
        for reminders in self.reminders.values():
            for reminder in reminders:
                reminder.wait_task.cancel()

    async def add_reminder(self, *, user_id, message_id, channel_id, content, end_time):
        data = await self.bot.db.fetchrow(
            """
            INSERT INTO reminders (
                user_id,
                message_id,
                channel_id,
                content,
                end_time
            ) VALUES (
                $1, $2, $3, $4, $5
            ) RETURNING *
            """,
            user_id,
            message_id,
            channel_id,
            content,
            end_time
        )
        reminder = Reminder(bot=self.bot, **data)
        self.reminders[user_id].append(reminder)

    @commands.group(invoke_without_command=True, usage="<offset> <content>")
    async def remind(self, ctx, *, input: str):
        """
        Schedule a reminder for a relative offset

        Offsets have the following requirements:
        - Must be one of `years`, `weeks`, `days`,
        `hours`, `minutes`, and `seconds`
        - Not all time units have to be used
        - Time units have to be ordered by magnitude

        **Examples**
        `remind 5 years Hey, hello!`
        `remind 4h30m Check what time it is`
        `remind 3 weeks, 2 days Do something funny`
        """
        if len(self.reminders[ctx.author.id]) >= MAX_REMINDERS:
            raise ValueError("You've used up all of your reminder slots!")

        (delta, remainder) = parse_relative(input)
        if len(remainder) > MAX_REMINDER_LEN:
            raise ValueError(f"Reminders cannot be longer than {MAX_REMINDER_LEN:,} characters!")

        future_time: datetime = datetime.now(timezone.utc) + delta
        timestamp: int = int(future_time.timestamp())
        await self.add_reminder(
            user_id=ctx.author.id,
            message_id=ctx.message.id,
            channel_id=ctx.channel.id,
            content=remainder or "...",
            end_time=future_time
        )
        await ctx.reply(f"Your reminder will be delivered <t:{timestamp}:R> [<t:{timestamp}>]")

    @remind.command(name="on", aliases=["at"], usage="<absolute time> <content>")
    async def remind_absolute(self, ctx, *, input: str):
        """
        Schedule a reminder for an absolute date/time

        A select few date/time formats are supported:
        - `month date, year`
        Ex: `remind on Mar 2, 2022 Dance`
        - `hour:minute`
        Ex: `remind at 14:08 Do something obscure`
        - `month date, year at hour:minute`
        Ex: `remind on January 19, 2038 at 3:14 Y2k38`

        All times are required to be in 24-hour format.

        **Note**
        If you have configured a timezone in your neo
        profile, it will be used to localize date/time.
        Otherwise, date/times will be in UTC.
        """
        if len(self.reminders[ctx.author.id]) >= MAX_REMINDERS:
            raise ValueError("You've used up all of your reminder slots!")

        (future_time, remainder) = parse_absolute(input)
        if len(remainder) > MAX_REMINDER_LEN:
            raise ValueError(f"Reminders cannot be longer than {MAX_REMINDER_LEN:,} characters!")

        profile = self.bot.profiles[ctx.author.id]
        future_time = future_time.replace(
            tzinfo=profile.timezone or timezone.utc
        )
        timestamp: int = int(future_time.timestamp())
        await self.add_reminder(
            user_id=ctx.author.id,
            message_id=ctx.message.id,
            channel_id=ctx.channel.id,
            content=remainder or "...",
            end_time=future_time
        )
        await ctx.reply(f"Your reminder will be delivered <t:{timestamp}:R> [<t:{timestamp}>]")

    @remind.command(name="list")
    async def remind_list(self, ctx):
        """Lists your active reminders"""
        reminders = self.reminders[ctx.author.id].copy()
        formatted_reminders: list[str] = []

        for index, reminder in enumerate(reminders, 1):
            formatted_reminders.append(
                "`{0}` {1}\n> Triggers <t:{2}:R>".format(
                    index, shorten(reminder.content, 50), int(reminder.end_time.timestamp())
                ))
        menu = ButtonsMenu.from_iterable(
            formatted_reminders or ["No reminders"],
            per_page=5,
            use_embed=True,
            template_embed=neo.Embed().set_author(
                name=f"{ctx.author}'s reminders",
                icon_url=ctx.author.avatar
            )
        )
        await menu.start(ctx)

    @remind.command(name="view", aliases=["show"])
    async def remind_view(self, ctx, index: int):
        """View the full content of a reminder, accessed by index"""
        try:
            reminder = self.reminders[ctx.author.id][index - 1]
        except IndexError:
            raise IndexError("Couldn't find that reminder.")

        embed = neo.Embed(
            description=reminder.content
        ).add_field(
            name=f"Created on <t:{int(snowflake_time(reminder.message_id).timestamp())}>",
            value=f"Triggers on <t:{int(reminder.end_time.timestamp())}>"
        ).set_author(
            name="Viewing a reminder",
            icon_url=ctx.author.avatar
        )
        await ctx.send(embed=embed)

    @remind.command(name="cancel")
    async def remind_cancel(self, ctx, *indices: Union[int, str]):
        """
        Cancel 1 or more reminder by index

        Passing `~` will cancel all reminders at once
        """
        if "~" in indices:
            reminders = self.reminders[ctx.author.id].copy()
        else:
            (indices := [*map(str, indices)]).sort(reverse=True)
            try:
                reminders = [self.reminders[ctx.author.id].pop(index - 1) for index in map(
                    int, filter(str.isdigit, indices))]
            except IndexError:
                raise IndexError("One or more of the provided indices is invalid.")

        for reminder in reminders:
            await reminder.delete()
        await ctx.message.add_reaction("\U00002611")


def setup(bot: neo.Neo):
    bot.add_cog(Reminders(bot))
