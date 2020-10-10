import pathlib
import asyncio

import discord
from discord.ext import commands

from .modules import *

class Fubuki(commands.Bot):
    def __init__(self, config, **kwargs):

        self.cfg = config
        kwargs.setdefault('command_prefix', self.get_prefix)

        super().__init__(**kwargs)

    async def get_prefix(self, message):
        return self.cfg['bot']['prefix']

    def run(self):
        WD = pathlib.Path(__file__).parent / "addons"
        CWD = pathlib.Path(__file__).parents[1]

        for addon in WD.iterdir():
            if addon.name.endswith('.py') and not addon.is_dir():
                _to_load = addon.relative_to(CWD).as_posix().replace('/', '.')[:-3]
                self.load_extension(_to_load)

        super().run(self.cfg['bot']['token'])

    async def close(self):
        [task.cancel() for task in asyncio.all_tasks(self.loop)]