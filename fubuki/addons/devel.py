from discord.ext import commands

from fubuki.modules.paginator import Paginator

class Devel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def menu_test(self, ctx):
        menu = Paginator.from_iterable(ctx.message.content, use_embed=True)
        await menu.start(ctx)

def setup(bot):
    bot.add_cog(Devel(bot))