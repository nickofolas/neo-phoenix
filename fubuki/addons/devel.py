from discord.ext import commands

from fubuki.modules.paginator import Paginator
from fubuki.types.converters import CodeblockConverter

class Devel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name='cleanup')
    async def dev_cleanup(self, ctx, amount: int = 5):
        purged = await ctx.channel.purge(
            limit = amount,
            bulk = False,
            check = lambda m: m.author == ctx.me)
        await ctx.send(f'Cleaned {len(purged)} message(s).', delete_after = 5)

    @commands.command(name='eval')
    async def dev_eval(self, ctx, *, code: CodeblockConverter):
        """SoonTM"""
        await ctx.send(code)

def setup(bot):
    bot.add_cog(Devel(bot))