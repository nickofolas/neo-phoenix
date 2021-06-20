import neo
from discord.ext import commands
from neo.modules import Paginator
from neo.tools import convert_setting

SETTINGS_MAPPING = {
    "receive_highlights": {
        "converter": commands.converter._convert_to_bool,
        "description": None
    }
}


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


def setup(bot):
    bot.add_cog(UserSettings(bot))
