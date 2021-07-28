# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import neo
from discord.ext import commands
from neo.modules import ButtonsMenu
from neo.tools import convert_setting, is_registered_guild

SETTINGS_MAPPING = {
    "prefix": {
        "converter": str,
        "description": None
    },
    "starboard": {
        "converter": commands.converter._convert_to_bool,
        "description": None
    }
}


class ServerSettings(neo.Addon):
    """
    neo phoenix's server config management module

    Create a server config to use features such as starboards and custom prefixes!
    """

    def __init__(self, bot: neo.Neo):
        self.bot = bot
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for col_name in SETTINGS_MAPPING.keys():
            col_desc = await self.bot.db.fetchval(
                """
                SELECT get_column_description(
                    $1, 'guild_configs', $2
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
        """
        Displays an overview of your server's settings

        Descriptions of the settings are also provided here
        """
        await is_registered_guild().predicate(ctx)
        config = self.bot.configs[ctx.guild.id]
        embeds = []

        for setting, setting_info in SETTINGS_MAPPING.items():
            description = setting_info["description"].format(
                getattr(config, setting)
            )
            embed = neo.Embed(
                title=f"Settings for {ctx.guild}",
                description=f"**Setting: `{setting}`**\n\n" + description
            ).set_thumbnail(
                url=ctx.guild.icon or neo.Embed.Empty
            )
            embeds.append(embed)

        menu = ButtonsMenu.from_embeds(embeds)
        await menu.start(ctx)

    @server.command(name="set")
    @is_registered_guild()
    async def server_set(self, ctx, setting, *, new_value):
        """
        Updates the value of a server setting

        More information on the available settings and their functions is in the `server` command
        """
        value = await convert_setting(ctx, SETTINGS_MAPPING, setting, new_value)
        config = self.bot.configs[ctx.guild.id]
        setattr(config, setting, value)
        self.bot.broadcast("config_update", ctx.guild, config)
        await ctx.send(f"Setting `{setting}` has been changed!")

    @server.command(name="reset")
    @is_registered_guild()
    async def server_reset(self, ctx, setting):
        """
        Resets the value of a server setting to its default

        Defaults can be found in the `server` command
        """
        if not SETTINGS_MAPPING.get(setting):
            raise commands.BadArgument(
                "That's not a valid setting! "
                "Try `server` for a list of settings!"
            )
        config = self.bot.configs[ctx.guild.id]
        await config.reset_attribute(setting)
        self.bot.broadcast("config_update", ctx.guild, config)
        await ctx.send(f"Setting `{setting}` has been reset!")

    @server.command(name="create")
    async def server_create(self, ctx):
        """
        Creates a config entry for the server

        Run this command when neo phoenix first
        joins your server, so you can start
        configuring your server
        """
        if ctx.guild.id in self.bot.configs:
            raise RuntimeError("Your server already has a config entry!")

        config = await self.bot.add_config(ctx.guild.id)
        self.bot.broadcast("config_update", ctx.guild, config)
        await ctx.send("Successfully initialized your server's config!")

    @server.command(name="delete")
    @is_registered_guild()
    async def server_delete(self, ctx):
        """__Permanently__ deletes this server's config"""
        if await ctx.prompt_user(
            "Are you sure you want to delete the config?"
            "\nThis will delete your config and all associated "
            "data (starboard, stars, etc), and **cannot** be undone.",
            label_confirm="I'm sure. Delete my server config.",
            label_cancel="Nevermind, don't delete my server config.",
            content_confirmed="Confirmed. Your server config is being deleted."
        ) is False:
            return

        await self.bot.delete_config(ctx.guild.id)


def setup(bot):
    bot.add_cog(ServerSettings(bot))
