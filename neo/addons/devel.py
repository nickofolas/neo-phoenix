import neo
from discord.ext import commands
from neo.modules.eval import Eval, env_from_context
from neo.modules.paginator import Pages, Paginator
from neo.types.converters import codeblock_converter
from neo.types.formatters import Table, format_exception


class Devel(neo.Addon):
    """Developer-only utility commands"""

    def __init__(self, bot):
        self.bot = bot
        self._eval_scope = {}
        self._last_eval_result = None

    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner("You do not own this bot.")
        return True

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
    async def dev_eval(self, ctx, *, code: codeblock_converter):
        """Executes some code, retaining the result"""
        (environment := env_from_context(ctx)).update(**(self._eval_scope | globals()))
        pages = Pages(
            "\r",
            1500,
            prefix="```py\n",
            suffix="\n```",
            use_embed=True
        )
        menu = Paginator(pages)

        try:
            async for res in Eval(code, environment, self._eval_scope):
                if res is None:
                    continue

                self._last_eval_result = res
                res = repr(res) if not isinstance(res, str) else res
                menu.pages.append("\n{}".format(res))

                if not menu.running:
                    await menu.start(ctx, as_reply=True)

            await ctx.message.add_reaction("\U00002611")

        except BaseException as e:  # Safely handle all errors
            menu.pages.append("\n{}".format(format_exception(e)))
            await menu.start(ctx, as_reply=True)

    @commands.command(name="sql")
    async def dev_sql(self, ctx, *, query: codeblock_converter):
        """Perform an SQL query"""
        data = await self.bot.db.fetch(query)
        if len(data) == 0:
            return await ctx.send("Query executed successfully")

        table = Table()
        table.init_columns([*data[0].keys()])
        for row in data:
            table.add_row([*map(str, row.values())])

        pages = Pages(
            table.display(),
            1500,
            prefix="```py\n",
            suffix="\n```"
        )
        menu = Paginator(pages)
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Devel(bot))
