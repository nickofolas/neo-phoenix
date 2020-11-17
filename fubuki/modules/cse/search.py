from random import choice

from aiohttp import ClientSession
from yarl import URL

from .objects import GoogleResponse

search_base = URL('https://www.googleapis.com/customsearch/v1')


_safe = lambda _input: 'active' if _input else 'off'


class Search:
    def __init__(self, *, key, engine_id, session: ClientSession = None):
        self.key = key
        self.engine_id = engine_id
        self.session = session or ClientSession()

    async def _perform_search(self, query, *, safesearch=True, image=False):

        key = self._get_key()
        params = dict(
            q=query,
            key=key,
            cx=self.engine_id,
            safe=_safe(safesearch)
        )

        if image is True:
            params.update(searchType='image')

        async with self.session.get(search_base.with_query(**params)) as resp:

            _data = await resp.json()
            if isinstance((error := _data.get('error')), dict):
                if error['code'] == 429 and error['status'] == 'RESOURCE_EXHAUSTED':
                    if isinstance(self.key, list):
                        self.key.remove(key)
                        return await self._perform_search(
                            query,
                            safesearch=safesearch,
                            image=image
                        )  # Try to get a new key to use
                    raise NotImplementedError()  # TODO: Put a proper error here

        return GoogleResponse(_data)

    def search(self, *args, **kwargs):
        return self._perform_search(*args, **kwargs)

    def _get_key(self):
        if isinstance(self.key, list):
            return choice(self.key)
        return self.key
