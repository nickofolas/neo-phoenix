import neo
from discord.ext import commands

SETTINGS_MAPPING = {
    "receive_highlights": commands.core._convert_to_bool
}


def try_or_none(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


class UserSettings(neo.Addon):
    """Contains everything needed for managing your neo profile"""

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def settings(self, ctx):
        """Displays an overview of your profile settings"""

        profile = self.bot.get_profile(ctx.author.id)
        description = ""

        for setting in SETTINGS_MAPPING.keys():
            description += "`{0}` = `{1}`\n".format(
                setting, getattr(profile, setting)
            )

        embed = neo.Embed(
            title="Settings for {}".format(ctx.author),
            description=description.strip()
        ).set_thumbnail(
            url=ctx.author.avatar_url
        )

        await ctx.send(embed=embed)

    @settings.command(name="set")
    async def settings_set(self, ctx, setting, *, new_value):
        """Updates the value of a profile setting

        More information on what the available settings are, and their functions, are in the `settings list` command"""

        if not (converter := SETTINGS_MAPPING.get(setting)):
            raise commands.BadArgument(
                "That's not a valid setting! "
                "Try `settings list` for a list of settings!"
            )

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

    @settings.command(name="list")
    async def settings_list(self, ctx):
        """Lists out available settings, their value types, and describes their function"""

        # TODO: All of it.
        # TODO: Decide best method of implementation:
        #       - * Database column comments with get_comment function?
        #       - Store descriptions in some other file that's loaded in?
        #       - Write descriptions into this file itself?


def setup(bot):
    bot.add_cog(UserSettings(bot))
