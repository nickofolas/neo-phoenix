from discord import Object, abc, User


class PartialUser(abc.Messageable, Object):
    """Represents a "partial" Discord user"""

    def __init__(self, *, state, id):
        self._state = state
        self.id = id

    def __repr__(self):
        return "<{0.__class__.__name__} id={0.id}>".format(self)

    @property
    def mention(self):
        return "<@{.id}>".format(self)

    async def fetch(self):
        """Fetches the partial user to a full User"""
        data = await self._state.http.get_user(self.id)
        return User(state=self._state, data=data)

    async def _get_channel(self):
        return await self.create_dm()

    @property
    def dm_channel(self):
        return self._state._get_private_channel_by_user(self.id)

    async def create_dm(self):
        found = self.dm_channel
        if found is not None:
            return found

        state = self._state
        data = await state.http.start_private_message(self.id)
        return state.add_dm_channel(data)
