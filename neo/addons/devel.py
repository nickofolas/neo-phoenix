# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import neo
from discord.ext import commands
from neo.modules import ButtonsMenu, Pages, args
from neo.modules.exec import ExecWrapper, env_from_context
from neo.types.converters import codeblock_converter
from neo.types.formatters import Table, format_exception


class Devel(neo.Addon):
    """Developer-only utility commands"""

    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self._exec_scope = {}
        self._last_exec_result = None

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

    @commands.command(name="exec", aliases=["e"])
    async def dev_exec(self, ctx, *, code: codeblock_converter):
        """Executes some code, retaining the result"""
        (globals_ := env_from_context(ctx)).update(**(self._exec_scope | globals()))
        pages = Pages(
            "\r",
            1500,
            joiner="",
            prefix="```py\n",
            suffix="\n```",
            use_embed=True
        )
        menu = ButtonsMenu(pages)

        try:
            async for res in ExecWrapper(code, globals_, self._exec_scope):
                if res is None:
                    continue

                self._last_exec_result = res
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
        table.init_columns(*data[0].keys())
        for row in data:
            table.add_row(*map(str, row.values()))

        pages = Pages(
            table.display(),
            1500,
            joiner="",
            prefix="```py\n",
            suffix="\n```"
        )
        menu = ButtonsMenu(pages)
        await menu.start(ctx)

    @args.add_arg(
        "-a", "--action",
        choices=["reload", "load", "unload"],
        default="reload",
        help="Controls the action to perform"
    )
    @args.add_arg("addons", nargs="+", help="Addons to action, `~ = all`")
    @args.command(name="addon")
    async def dev_addon(self, ctx, *, args):
        """
        Manage addons

        It's not a great idea to unload everything
        """
        action = getattr(self.bot, f"{args.action}_extension")
        failed = []
        if "~" in args.addons:
            args.addons = self.bot.extensions.copy().keys()
        for addon in args.addons:
            try:
                action(addon)
            except BaseException as e:
                failed.append("```py\n" + format_exception(e) + "\n```")

        if failed:
            menu = ButtonsMenu.from_iterable(failed, use_embed=True)
            await menu.start(ctx)
            return
        await ctx.message.add_reaction("\U00002611")


def setup(bot):
    bot.add_cog(Devel(bot))
