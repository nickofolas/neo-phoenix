from aiohttp import ClientSession
from yarl import URL

from .objects import DictionaryResponse

BASE = URL("https://api.dictionaryapi.dev/api/v2/entries/")
DefinitionError = type("DefinitionError", (Exception,), {})


class Define:
    def __init__(self, session: ClientSession = None):
        self.session = session or ClientSession()

    async def _do_definition(self, query, *, lang_code="en"):
        url = BASE / lang_code / query

        async with self.session.get(url) as resp:

            _data = await resp.json()
            if resp.status != 200:
                raise DefinitionError(f"Error fetching definition ({resp.status})")

        return DictionaryResponse(_data)

    def define(self, query, *, lang_code="en"):
        return self._do_definition(query, lang_code=lang_code)
