from discord.ext import commands

import fubuki
from fubuki.modules import cse, Paginator, argparser


def _res_to_embed(result):
    embed = fubuki.Embed(
        title=result.title,
        description=result.snippet,
        url=result.url
    )
    embed.set_image(url=result.image_url or '')
    return embed


class Temp(fubuki.Addon):
    def __init__(self, bot):
        self.bot = bot
        self.parser = argparser.ArgParser()
        self.parser.add_arg('-i', '--image', type='flag', default=False)

        self.google = cse.Search(
            key=bot.cfg['bot']['cse_keys'],
            engine_id=bot.cfg['bot']['cse_engine'],
            session=bot.session
        )

    @commands.command(name='google', aliases=['g'], usage='[--image] <query>')
    async def temp_google(self, ctx, *, query):
        query = self.parser.parse(query)
        resp = await self.google.search(
            ''.join(query.unused_strings),
            image=query.image)
        embeds = [*map(_res_to_embed, resp)]
        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Temp(bot))
