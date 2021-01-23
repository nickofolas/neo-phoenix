import fubuki
from discord.ext import commands
from fubuki.modules.eval import (Eval, clear_intersection, env_from_context,
                                 format_exception)
from fubuki.modules.paginator import Pages, Paginator
from fubuki.types.converters import CodeblockConverter


class Devel(fubuki.Addon):
    def __init__(self, bot):
        self.bot = bot
        self._eval_scope = {}
        self._last_eval_result = None

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.guild_only()
    @commands.command(name="cleanup", aliases=["clean"])
    async def dev_cleanup(self, ctx, amount: int = 5):
        """Cleanup the bot's messages from a channel"""

        can_manage = ctx.channel.permissions_for(ctx.me).manage_messages
        if can_manage:
            def check(message):
                return any([
                    message.author == ctx.me,
                    message.content.startswith(ctx.prefix)
                ])
        else:
            def check(message):
                return message.author == ctx.me

        purged = await ctx.channel.purge(
            limit=amount,
            bulk=can_manage,
            check=check
        )
        await ctx.send(f"Cleaned {len(purged)} message(s).", delete_after=5)

    @commands.command(name="eval", aliases=["e"])
    async def dev_eval(self, ctx, *, code: CodeblockConverter):
        """Executes some code, retaining the result"""

        clear_intersection(globals(), self._eval_scope)
        (environment := env_from_context(ctx)).update(**globals(), **self._eval_scope)

        pages = Pages(
            "\r",
            1500,
            prefix="```py\n",
            suffix="\n```",
            use_embed=True
        )
        menu = Paginator(pages, timeout=180)

        try:
            async for res in Eval(code, environment, self._eval_scope):
                if res is None:
                    continue

                self._last_eval_result = res
                res = repr(res) if not isinstance(res, str) else res
                menu.pages.append("\n{}".format(res))

                if not menu._running:
                    await menu.start(ctx, delay_add=True, as_reply=True)

            await ctx.message.add_reaction("\U00002611")

        except Exception as e:
            menu.pages.append("\n{}".format(format_exception(e)))
            await menu.start(ctx, delay_add=True, as_reply=True)

        finally:
            if menu._running:
                await menu.add_buttons()


def setup(bot):
    bot.add_cog(Devel(bot))
