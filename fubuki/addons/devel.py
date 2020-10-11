from discord.ext import commands

from fubuki.modules.paginator import Paginator, Pages
from fubuki.types.converters import CodeblockConverter
from fubuki.modules.eval import Eval, format_exception, env_from_context

class Devel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._eval_scope = {}

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name = 'cleanup')
    async def dev_cleanup(self, ctx, amount: int = 5):
        purged = await ctx.channel.purge(
            limit = amount,
            bulk = False,
            check = lambda m: m.author == ctx.me)
        await ctx.send(f'Cleaned {len(purged)} message(s).', delete_after = 5)

    @commands.command(name = 'eval', aliases = ['e'])
    async def dev_eval(self, ctx, *, code: CodeblockConverter):
        """SoonTM"""
        (environment := env_from_context(ctx)).update(
            **globals(), **self._eval_scope)
        results = []
        return_value = None
        try:
            async for res in Eval(code, environment, self._eval_scope):
                if res is None: continue
                self.bot._last_eval_result = res
                res = repr(res) if not isinstance(res, str) else res
                results.append(res)
            return_value = '\n'.join(results)
        except Exception as e:
            return_value = format_exception(e)
        finally:
            if not return_value: return
            pages = Pages(
                return_value, 1500, use_embed=True,
                prefix = '```py\n', suffix = '\n```'
            )
            menu = Paginator(pages, timeout = 180)
            await menu.start(ctx)


def setup(bot):
    bot.add_cog(Devel(bot))