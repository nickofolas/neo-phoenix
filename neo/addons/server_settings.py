import neo
from discord.ext import commands
from neo.modules import Paginator
from neo.tools import try_or_none

SETTINGS_MAPPING = {
    "prefix": {
        "converter": str,
        "description": None
    },
    "starboard_enabled": {
        "converter": commands.converter._convert_to_bool,
        "description": None
    }
}


class ServerSettings(neo.Addon):
    """Contains everything needed for managing your server's settings"""

    def __init__(self, bot):
        self.bot = bot

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for col_name in SETTINGS_MAPPING.keys():
            col_desc = await self.bot.db.fetchval(
                """
                SELECT get_column_description(
                    $1, 'servers', $2
                )
                """,
                self.bot.cfg["database"]["database"],
                col_name
            )

            SETTINGS_MAPPING[col_name]["description"] = col_desc

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        if not any([
            ctx.author.guild_permissions.administrator,
            await self.bot.is_owner(ctx.author)
        ]):
            raise commands.MissingPermissions(["administrator"])

        return True

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def server(self, ctx):
        """Displays an overview of your server's settings

        Descriptions of the settings are also provided here"""

        server = self.bot.get_server(ctx.guild.id)
        embeds = []

        for setting, setting_info in SETTINGS_MAPPING.items():
            description = setting_info["description"].format(
                getattr(server, setting)
            )
            embed = neo.Embed(
                title=f"Settings for {ctx.guild}",
                description=f"**Setting: `{setting}`**\n\n" + description
            ).set_thumbnail(
                url=ctx.guild.icon
            )
            embeds.append(embed)

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @server.command(name="set")
    async def server_set(self, ctx, setting, *, new_value):
        """Updates the value of a server setting

        More information on the available settings and their functions is in the `server` command"""

        if not (valid_setting := SETTINGS_MAPPING.get(setting)):
            raise commands.BadArgument(
                "That's not a valid setting! "
                "Try `server` for a list of settings!"
            )

        converter = valid_setting["converter"]
        if isinstance(converter, commands.Converter):
            if (converted := await converter.convert(ctx, new_value)) is not None:
                value = converted

        elif (converted := try_or_none(converter, new_value)) is not None:
            value = converted

        else:
            raise commands.BadArgument(
                "Bad value provided for setting `{}`".format(setting)
            )

        server = self.bot.get_server(ctx.guild.id)
        setattr(server, setting, value)
        self.bot.dispatch("server_settings_update", server)
        await ctx.send(f"Setting `{setting}` has been changed!")


def setup(bot):
    bot.add_cog(ServerSettings(bot))
