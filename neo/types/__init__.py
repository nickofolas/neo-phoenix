# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import discord


class Embed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("colour", 0xA29BFE)
        super().__init__(**kwargs)

    @classmethod
    def from_dict(cls, data: dict):
        data.setdefault("color", 0xA29BFE)
        return super().from_dict(data)

del discord  # Avoids re-exporting discord
