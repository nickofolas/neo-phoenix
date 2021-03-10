from discord import Embed


class Embed(Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("colour", 0xA29BFE)
        super().__init__(**kwargs)
