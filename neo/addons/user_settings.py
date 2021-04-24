import neo
from discord.ext import commands
from neo.modules import Paginator

SETTINGS_MAPPING = {
    "receive_highlights": {
        "converter": commands.core._convert_to_bool,
        "description": None
    }
}


def try_or_none(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


class UserSettings(neo.Addon):
    """Contains everything needed for managing your neo profile"""

    def __init__(self, bot):
        self.bot = bot

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for col_name in SETTINGS_MAPPING.keys():
            col_desc = await self.bot.db.fetchval(
                """
                SELECT get_column_description(
                    $1, 'profiles', $2
                )
                """,
                self.bot.cfg["database"]["database"],
                col_name
            )

            SETTINGS_MAPPING[col_name]["description"] = col_desc

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def settings(self, ctx):
        """Displays an overview of your profile settings

        Descriptions of the settings is also provided here"""

        profile = self.bot.get_profile(ctx.author.id)
        embeds = []

        for setting, setting_info in SETTINGS_MAPPING.items():
            description = setting_info["description"].format(
                getattr(profile, setting)
            )
            embed = neo.Embed(
                title="Settings for {}".format(ctx.author),
                description=description
            ).set_thumbnail(
                url=ctx.author.avatar_url
            )
            embeds.append(embed)

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @settings.command(name="set")
    async def settings_set(self, ctx, setting, *, new_value):
        """Updates the value of a profile setting

        More information on what the available settings are, and their functions, are in the `settings` command"""

        if not (valid_setting := SETTINGS_MAPPING.get(setting)):
            raise commands.BadArgument(
                "That's not a valid setting! "
                "Try `settings` for a list of settings!"
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

        profile = self.bot.get_profile(ctx.author.id)
        setattr(profile, setting, value)
        await ctx.send(f"Setting `{setting}` has been changed!")


def setup(bot):
    bot.add_cog(UserSettings(bot))
