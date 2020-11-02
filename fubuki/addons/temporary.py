import fubuki
from discord.ext import commands
from fubuki.modules import Paginator, args, cse


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
        self.google = cse.Search(
            key=bot.cfg['bot']['cse_keys'],
            engine_id=bot.cfg['bot']['cse_engine'],
            session=bot.session
        )

    @args.add_arg('query', nargs='*')
    @args.add_arg('-i', '--image', action='store_true')
    @args.command(name='google', aliases=['g'])
    async def temp_google(self, ctx, *, query):
        resp = await self.google.search(
            ' '.join(query.query),
            image=query.image)

        embeds = [*map(_res_to_embed, resp)]
        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Temp(bot))
