import asyncio
import contextlib


class TimedSet(set):
    def __init__(
        self,
        *args,
        decay_time: int = 60,
        loop: asyncio.AbstractEventLoop = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.decay_time = decay_time
        self.loop = loop or asyncio.get_event_loop()
        self.running = {}

        for item in self:
            self.add(item)

    def add(self, item):
        with contextlib.suppress(KeyError):
            con = self.running.pop(item)
            con.cancel()

        super().add(item)
        task = self.loop.create_task(self.decay(item))
        self.running[item] = task

    async def decay(self, item):
        await asyncio.sleep(self.decay_time)
        self.discard(item)
        self.running.pop(item, None)
