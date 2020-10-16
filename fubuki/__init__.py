import asyncio
import logging

import discord
from discord.ext import commands

from .modules import *  # noqa: F401, F403
from .types import Embed  # noqa: F401, F403

log = logging.getLogger(__name__)

class Fubuki(commands.Bot):
    def __init__(self, config, **kwargs):

        self.cfg = config
        self._last_eval_result = None

        kwargs.setdefault('command_prefix', self.get_prefix)
        kwargs.setdefault('activity', discord.Game(config['bot']['playing_name']))

        super().__init__(**kwargs)

    def run(self):
        for addon in self.cfg['addons']:
            self.load_extension(addon)

        super().run(self.cfg['bot']['token'])

    async def close(self):
        [task.cancel() for task in asyncio.all_tasks(self.loop)]

    async def on_ready(self):
        log.info('{} has received ready event'.format(self.user))

    async def on_message_edit(self, before, after):
        if after.content != before.content:
            await self.process_commands(after)

    async def get_prefix(self, message):
        return commands.when_mentioned_or(self.cfg['bot']['prefix'])(self, message)
