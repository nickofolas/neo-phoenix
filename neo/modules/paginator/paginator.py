import asyncio

import discord

from .pages import EmbedPages, Pages
from .ui import MenuActions


class Paginator:
    """
    A class which accomodates the creation of interactive menus.
    A constructed menu may be started by calling `await menu.start(ctx: commands.Context)`

    Parameters
    ----------
    pages: Pages
        The Pages object that is used as the pagination source.

    Classmethods
    ------------
    from_iterable(iterable, per_page, use_embed, joiner, **kwargs)
        Creates a Paginator object without the need for a premade Pages.
    from_embeds(iterable, **kwargs)
        Creates a Paginator object from a list of Embeds
    """
    def __init__(self, pages):
        self.pages = pages

        self.message = None
        self.ctx = None
        self.current_page = 0
        self.running = False

        self.update_lock = asyncio.Lock()
        self.pages.link(self)

    @classmethod
    def from_iterable(
            cls,
            iterable,
            *, per_page=1,
            use_embed=False,
            joiner="\n",
            **kwargs):
        _pages = Pages(iterable, per_page, use_embed=use_embed, joiner=joiner)
        return cls(_pages, **kwargs)

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

        self.buttons = MenuActions(self)
        self.message = await self.ctx.send(view=self.buttons, **send_kwargs)
        self.bot = self.ctx.bot
        self.author = self.ctx.author

        self.running = True

    def _get_msg_kwargs(self, item):
        if isinstance(item, discord.Embed):
            item.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)}")
            return {"embed": item}
        elif isinstance(item, (str, tuple)):
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
        self.running = False
        try:
            if manual is True:
                await self.message.delete()
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
