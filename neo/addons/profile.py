from typing import Union

import neo
from discord.ext import commands
from neo.modules import Paginator
from neo.tools import convert_setting
from neo.types.converters import MentionConverter, TimezoneConverter

SETTINGS_MAPPING = {
    "receive_highlights": {
        "converter": commands.converter._convert_to_bool,
        "description": None
    },
    "timezone": {
        "converter": TimezoneConverter(),
        "description": None
    }
}


def is_registered_profile():
    """Verify the registration status of a user profile"""
    def predicate(ctx):
        if not ctx.bot.get_profile(ctx.author.id):
            raise commands.CommandInvokeError(AttributeError(
                "Looks like you don't have an existing profile! "
                "You can fix this with the `profile init` command."
            ))
        return True
    return commands.check(predicate)


class Profile(neo.Addon):
    """Contains everything needed for managing your neo profile"""

    def __init__(self, bot: neo.Neo):
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
    @is_registered_profile()
    async def settings(self, ctx):
        """
        Displays an overview of your profile settings

        Descriptions of the settings are also provided here
        """

        profile = self.bot.get_profile(ctx.author.id)
        embeds = []

        for setting, setting_info in SETTINGS_MAPPING.items():
            description = setting_info["description"].format(
                getattr(profile, setting)
            )
            embed = neo.Embed(
                title=f"Settings for {ctx.author}",
                description=f"**Setting: `{setting}`**\n\n" + description
            ).set_thumbnail(
                url=ctx.author.avatar
            )
            embeds.append(embed)

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @settings.command(name="set")
    @is_registered_profile()
    async def settings_set(self, ctx, setting, *, new_value):
        """
        Updates the value of a profile setting

        More information on the available settings and their functions is in the `settings` command
        """

        value = await convert_setting(ctx, SETTINGS_MAPPING, setting, new_value)
        profile = self.bot.get_profile(ctx.author.id)
        setattr(profile, setting, value)
        self.bot.dispatch("user_settings_update", ctx.author, profile)
        await ctx.send(f"Setting `{setting}` has been changed!")

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, *, user: Union[int, MentionConverter] = None):
        """Displays the neo profile of yourself, or a specified user."""
        if user is None:
            await is_registered_profile().predicate(ctx)

        profile = self.bot.get_profile(user or ctx.author.id)
        if profile is None:
            raise AttributeError("This user doesn't have a neo profile!")

    @profile.command(name="init")
    async def profile_init(self, ctx):
        """Creates your neo profile!"""

        if self.bot.get_profile(ctx.author.id):
            raise RuntimeError("You already have a profile!")

        await self.bot.add_profile(ctx.author.id)
        await ctx.send("Successfully initialized your profile!")


def setup(bot):
    bot.add_cog(Profile(bot))
