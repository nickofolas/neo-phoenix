import asyncio
import contextlib


class FubukiUser:
    __slots__ = ("ready", "pool", "user_id", "hl_blocks")

    def __init__(self, *, pool, **record):
        self.ready = False
        self.pool = pool

        for key, value in record.items():
            setattr(self, key, value)

        self.ready = True

    def __repr__(self):
        return "<{0.__class__.__name__} user_id={0.user_id}>".format(self)

    def __setattr__(self, attribute, value):
        if getattr(self, "ready", False):
            asyncio.create_task(self.update_relation(attribute, value))

        super().__setattr__(attribute, value)

    async def update_relation(self, attribute, value):
        await self.pool.execute(
            f"""
            UPDATE profiles
            SET
                {attribute}=$1
            WHERE
                user_id=$2
            """,    # While it isn't ideal to use string formatting with SQL,
            value,  # the class implements __slots__, so possible attribute names are restricted
            self.user_id
        )


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
