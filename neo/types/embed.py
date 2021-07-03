# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from discord import Embed


class Embed(Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("colour", 0xA29BFE)
        super().__init__(**kwargs)
