# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import asyncio

import discord
from neo.tools import shorten

from .pages import EmbedPages, Pages


class BaseMenu(discord.ui.View):
    __slots__ = (
        "pages",
        "message",
        "ctx",
        "current_page",
        "running",
        "update_lock",
        "buttons",
        "bot",
        "author"
    )

    def __init__(self, pages: Pages):
        super().__init__()
        self.pages = pages

        self.message = None
        self.ctx = None
        self.current_page = 0
        self.running = False

        self.update_lock = asyncio.Lock()
        self.pages.link(self)

    @classmethod
    def from_iterable(cls, iterable, *, per_page=1, **kwargs):
        _pages = Pages(iterable, per_page, **kwargs)
        return cls(_pages)

    @classmethod
    def from_embeds(cls, iterable, **kwargs):
        _pages = EmbedPages(iterable)
        return cls(_pages, **kwargs)

    async def start(self, _ctx, *, as_reply=False):
        self.ctx = _ctx

        send_kwargs = self._get_msg_kwargs(self.pages[0])
        if as_reply:
            send_kwargs.update(
                reference=discord.MessageReference(
                    message_id=self.ctx.message.id,
                    channel_id=self.ctx.channel.id
                )
            )

        self.message = await self.ctx.send(view=self, **send_kwargs)
        self.bot = self.ctx.bot
        self.author = self.ctx.author

        self.running = True

    def _get_msg_kwargs(self, item):
        if isinstance(item, discord.Embed):
            item.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)}")
            return {"embed": item}
        elif isinstance(item, str):
            item += f"\nPage {self.current_page + 1}/{len(self.pages)}"
            return {"content": item}

    def get_current_page(self, index):
        if index < 0:
            index = len(self.pages) - 1
        if index > (len(self.pages) - 1):
            index = 0
        self.current_page = index
        return self.pages[index]

    async def refresh_page(self):
        kwargs = self._get_msg_kwargs(self.pages[self.current_page])
        await self.message.edit(**kwargs)

    async def close(self, manual=False):
        self.stop()
        self.running = False
        try:
            if manual is True:
                await self.message.delete()
            else:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
        except discord.NotFound:
            return

    def dispatch_update(self):
        async def inner():
            if self.update_lock.locked():
                return

            async with self.update_lock:
                if self.update_lock.locked():
                    await asyncio.sleep(1)

                self.bot.loop.create_task(self.refresh_page())

        self.bot.loop.create_task(inner())

    async def interaction_check(self, interaction):
        (predicates := []).append(interaction.user.id in (
            self.author.id,
            *self.bot.owner_ids,
            self.bot.owner_id)
        )
        return all(predicates)

    async def on_timeout(self):
        await self.close()


class ButtonsMenu(BaseMenu):

    @discord.ui.button(label="<", row=4)
    async def previous_button(self, button, interaction):
        current_page = self.get_current_page(self.current_page - 1)
        send_kwargs = self._get_msg_kwargs(current_page)
        await interaction.response.edit_message(**send_kwargs)

    @discord.ui.button(label="⨉", row=4)
    async def close_button(self, button, interaction):
        self.stop()
        await self.close(manual=True)

    @discord.ui.button(label=">", row=4)
    async def next_button(self, button, interaction):
        current_page = self.get_current_page(self.current_page + 1)
        send_kwargs = self._get_msg_kwargs(current_page)
        await interaction.response.edit_message(**send_kwargs)


class DropdownMenuItem(discord.ui.Select):
    def __init__(self, menu: BaseMenu, **kwargs):
        kwargs["placeholder"] = "Choose a page"
        super().__init__(**kwargs)
        self.menu = menu

    async def callback(self, interaction: discord.Interaction):
        current_page = self.menu.get_current_page(int(self.values[0]))
        send_kwargs = self.menu._get_msg_kwargs(current_page)
        await interaction.response.edit_message(**send_kwargs)


class DropdownMenu(ButtonsMenu, BaseMenu):

    @classmethod
    def from_pages(
        cls,
        pages: Pages,
        *,
        embed_auto_label: bool = False,
        embed_auto_desc: bool = False
    ):
        options: list[discord.SelectOption] = []
        for index, page in enumerate(pages.items, 1):
            label = f"Page {index}"
            description = None
            if isinstance(page, discord.Embed):
                if embed_auto_label:
                    label = shorten(page.title or f"Page {index}", 25)
                if embed_auto_desc:
                    description = shorten(page.description or "", 50)
            options.append(discord.SelectOption(
                label=label, value=index - 1, description=description))

        return cls.from_options(options=options, pages=pages)

    @classmethod
    def from_options(cls, *, options: list[discord.SelectOption], pages: Pages):
        if len(options) > 25:
            raise ValueError("Cannot have more than 25 items")
        instance = cls(pages)

        select = DropdownMenuItem(instance, options=options, row=0)
        instance.add_item(select)

        return instance

    @classmethod
    def from_embeds(cls, *args, **kwargs):
        # This might be something to consider eventually
        raise NotImplementedError

    from_iterable = from_embeds
