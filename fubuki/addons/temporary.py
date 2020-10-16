from discord.ext import commands

import fubuki
from fubuki.modules import cse, Paginator

def _res_to_embed(result):
    embed = fubuki.Embed(
        title=result.title,
        description=result.snippet,
        url=result.url
    )
    embed.set_image(url=result.image_url)
    return embed

class Temp(fubuki.Addon):
    def __init__(self, bot):
        self.bot = bot

        self.search = cse.Search(
            key=bot.cfg['bot']['cse_tokens'],
            engine_id=bot.cfg['bot']['cse_engine'],
            session=bot.session
        )

    @commands.command(name='google', aliases=['g'])
    async def temp_google(self, ctx, *, query):
        _images = False
        if query.startswith(("-i ", "--image ")):
            query = ' '.join(query.split(' ')[1:])
            _images = True
        resp = await self.search.search(query, image=_images)
        embeds = [*map(_res_to_embed, resp)]
        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

def setup(bot):
    bot.add_cog(Temp(bot))
