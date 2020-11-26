import asyncio

import discord

from .pages import EmbedPages, Pages


class Paginator:
    """
    A class which accomodates the creation of interactive reaction menus.
    A constructed menu may be started by calling `await menu.start(ctx: commands.Context)`

    Parameters:
    - pages: Pages
        The Pages object that is used as the pagination source.
    - timeout: int
        Allowed seconds of inactivity before the menu terminates itself.
        Default: 60

    Classmethods:
    - from_iterable(iterable, per_page, use_embed, joiner, **kwargs)
        Creates a Paginator object without the need for a premade Pages.
    - from_embeds(iterable, **kwargs)
        Creates a Paginator object from a list of Embeds
    """

    def __init__(self, pages, *, timeout: int = 60):
        self.pages = pages
        self.timeout = timeout

        self.message = None
        self.ctx = None
        self.current_page = 0
        self._running = False

        self.emoji_map = {  # ◀️▶️⏮️⏭️⏹️
            '⏪': lambda: self.show_page(0),
            '⬅️': lambda: self.show_page(self.current_page - 1),
            '🚮': lambda: self.close(manual=True),
            '➡️': lambda: self.show_page(self.current_page + 1),
            '⏩': lambda: self.show_page(len(self.pages) - 1)
        }

        self.pages.link(self)

    @classmethod
    def from_iterable(
            cls,
            iterable,
            *, per_page=1,
            use_embed=False,
            joiner='\n',
            **kwargs):
        _pages = Pages(iterable, per_page, use_embed=use_embed, joiner=joiner)
        return cls(_pages, **kwargs)

    @classmethod
    def from_embeds(cls, iterable, **kwargs):
        _pages = EmbedPages(iterable)
        return cls(_pages, **kwargs)

    async def start(self, _ctx, *, delay_add=False):
        self.ctx = _ctx
        self.message = await self.ctx.send(**self._get_msg_kwargs(self.pages[0]))
        self.bot = self.ctx.bot
        self.author = self.ctx.author
        self._remove_reactions = self.ctx.channel.permissions_for(self.ctx.me).manage_messages
        if delay_add is False:
            await self.add_buttons()
        self._running = True
        self._loop_task = self.bot.loop.create_task(self._create_loop())

    async def add_buttons(self):
        _buttons = list(self.emoji_map.items())
        if len(self.pages) == 1:
            buttons = dict([_buttons[2]])
        elif len(self.pages) == 2:
            buttons = dict(_buttons[1:4])
        else:
            buttons = dict(_buttons)
        for emoji in buttons.keys():
            await self.message.add_reaction(emoji)

    async def clear_reactions(self):
        if self._remove_reactions:
            await self.message.clear_reactions()
        else:
            for reaction in self.emoji_map.keys():
                await self.message.remove_reaction(reaction, self.ctx.me)

    def _get_msg_kwargs(self, item):
        if isinstance(item, discord.Embed):
            item.set_footer(text=f'Page {self.current_page + 1}/{len(self.pages)}')
            return {'embed': item}
        elif isinstance(item, (str, tuple)):
            return {'content': item}

    async def show_page(self, index):
        if not self._running:
            return
        if index < 0:
            index = len(self.pages) - 1
        if index > (len(self.pages) - 1):
            index = 0
        self.current_page = index
        await self.message.edit(**self._get_msg_kwargs(self.pages[index]))

    async def close(self, manual=False):
        self._running = False
        try:
            if manual is True:
                await self.message.delete()
            else:
                await self.clear_reactions()
        except discord.NotFound:
            return

    def reactions_pred(self, payload):
        preds = []
        preds.append(payload.user_id in (self.author.id, *self.bot.owner_ids))
        preds.append(payload.message_id == self.message.id)
        return all(preds)

    async def _create_loop(self):
        if not self._running:
            return
        try:
            while self._running:
                tasks = [asyncio.create_task(self.bot.wait_for('raw_reaction_add', check=self.reactions_pred))]
                if not self._remove_reactions:
                    tasks.append(asyncio.create_task(self.bot.wait_for('raw_reaction_remove', check=self.reactions_pred)))
                done, running = await asyncio.wait(tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    raise asyncio.TimeoutError
                [task.cancel() for task in running]
                payload = done.pop().result()

                if self._remove_reactions:
                    await self.message.remove_reaction(payload.emoji, type('', (), {'id': payload.user_id}))

                if (coro := self.emoji_map.get(payload.emoji.name)):
                    await coro()
                else:
                    continue
        except asyncio.TimeoutError:
            await self.close()
        finally:
            [task.cancel() for task in tasks]
            self._loop_task.cancel()

    def dispatch_update(self):
        self.bot.loop.create_task(self.show_page(self.current_page))
