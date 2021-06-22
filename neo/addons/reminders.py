from dataclasses import dataclass
from datetime import datetime
from typing import Union

import discord
import neo


@dataclass
class Reminder:
    user_id: int
    message_id: int
    channel_id: int
    content: str
    end_time: datetime
    bot: neo.Neo

    def __post_init__(self):
        self.bot.loop.create_task(self.wait())

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
        await self.delete()  # Ensure that the database entry is always deleted

        if self.channel is not None:
            try:
                await self.message.reply(
                    self.content,
                    allowed_mentions=discord.AllowedMentions(replied_user=True)
                )
            except discord.HTTPException:
                await self.fallback_deliver()
        else:
            await self.fallback_deliver()

    async def fallback_deliver(self) -> None:
        """Fallback to a primitive delivery format if normal deliver is impossible"""
        try:
            dest = self.channel or self.bot.get_user(self.user_id, as_partial=True)
            await dest.send(
                "<@{0}> **Reminder** [source deleted]\n> {1}".format(
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
