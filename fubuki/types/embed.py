from discord import Embed

class Embed(Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault('colour', 0xa29bfe)
        super().__init__(**kwargs)