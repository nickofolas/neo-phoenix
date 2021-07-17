# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from discord import Object, User, abc


class PartialUser(abc.Messageable, Object):
    """Represents a "partial" Discord user"""

    def __init__(self, *, state, id):
        self._state = state
        self.id = id

    def __repr__(self):
        return "<{0.__class__.__name__} id={0.id}>".format(self)

    @property
    def mention(self):
        return f"<@{self.id}>"

    async def fetch(self):
        """Fetches the partial user to a full User"""
        data = await self._state.http.get_user(self.id)
        return User(state=self._state, data=data)

    _get_channel = User._get_channel
    dm_channel = User.dm_channel
    create_dm = User.create_dm
