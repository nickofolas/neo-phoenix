import operator

import fubuki
from discord.ext import commands
from fubuki.modules.paginator import Paginator


def format_command(command):
    fmt = "[{0}] {1.name}"

    if isinstance(command, commands.Group):
        symbol = "\U00002443"
    else:
        symbol = "\U00002444"

    return fmt.format(symbol, command)


class FubukiHelpCommand(commands.HelpCommand):

    def __init__(self):
        description = """Displays help for the bot.

        Some symbols are used to identify commands:
        - A `⑄` symbol next to a listed command identifies it as a standalone command.
        - A `⑃` symbol next to a listed command identifies it as a command group."""

        super().__init__(command_attrs={"help": description})

    async def send_bot_help(self, mapping):
        embeds = []

        for cog, _commands in mapping.items():

            if not (cog_commands := await self.filter_commands(_commands)):
                continue

            cog_name = getattr(cog, "qualified_name", "Uncategorized")

            embeds.append(
                fubuki.Embed(
                    title=cog_name,
                    description=getattr(cog, "description", None)
                ).add_field(
                    name="Commands",
                    value="\n".join(map(
                        format_command,
                        cog_commands
                    ))
                ))

        menu = Paginator.from_embeds(embeds)
        await menu.start(self.context)

    async def send_cog_help(self, cog):
        cog_name = cog.qualified_name
        cog_commands = await self.filter_commands(cog.get_commands())

        embed = fubuki.Embed(
            title=cog_name,
            description=getattr(cog, "description", None)
        ).add_field(
            name="Commands",
            value="\n".join(map(
                format_command,
                cog_commands
            ))
        )

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = fubuki.Embed(
            title=f"{self.clean_prefix}{command.qualified_name} {command.signature}",
            description="{}\n".format(command.help or "No description")
        )

        if isinstance(command, commands.Group):
            embed.add_field(
                name="Subcommands",
                value="\n".join(map(
                    lambda sub: f"{sub.full_parent_name} **{sub.name}**",
                    command.walk_commands()
                ))
            )

        if hasattr(command, "get_args_help"):
            for dest, help in command.get_args_help():
                embed.description += f"\n**{dest}** {help}"

        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        await self.send_command_help(group)
