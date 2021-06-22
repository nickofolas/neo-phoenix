import neo
from discord.ext import commands
from neo.modules.paginator import Paginator


def format_command(command):
    fmt = "[{0}] {1.name}"

    if isinstance(command, commands.Group):
        symbol = "\U00002443"
    else:
        symbol = "\U00002444"

    return fmt.format(symbol, command)


class NeoHelpCommand(commands.HelpCommand):

    def __init__(self):
        description = """Displays help for the bot.

        __**Command Lists**__
        In a list of commands, command types are identified symbolically:
        - A `⑄` symbol next to a listed command identifies it as a standalone command.
        - A `⑃` symbol next to a listed command identifies it as a command group.

        __**Command Help**__
        There are several elements of a command's help page to consider.

        __Description__
        Stable (completed) commands will have a description to explain
        the command's function and purpose.

        __Arguments__
        Arguments represent the relevant information that you pass to neo.
        When reading a command's arguments, the order they are listed is also
        the order in which you must provide them.

        Arguments also have some identifiers to them:
        - An argument surrounded by angle brackets (`<>`) is **required**.
        The command will not run if you do not provide this argument.
        - An argument surrounded by square brackets (`[]`) is **optional**.
        The command will run without them, or they can be provided to
        alter the result of the command.

        A unique argument type is a *flag argument*, identified by `--`

        Flag arguments are special in that they can be used
        at any spot in the arguments input, unlike non-flag (positional) arguments.
        When a command takes a flag argument, you pass it like so:
        > <command> <positional argument> **--<flag argument>**

        The input value type of a flag command may differ by command, so make sure
        to read the explanation for the argument at the bottom of the command's
        help page.
        """

        super().__init__(command_attrs={"help": description})

    async def send_bot_help(self, mapping):
        embeds = []

        for cog, _commands in mapping.items():

            if not (cog_commands := await self.filter_commands(_commands)):
                continue

            cog_name = getattr(cog, "qualified_name", "Uncategorized")

            embeds.append(
                neo.Embed(
                    title=cog_name,
                    description=getattr(cog, "description", "No description")
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

        embed = neo.Embed(
            title=cog_name,
            description=getattr(cog, "description", "No description")
        ).add_field(
            name="Commands",
            value="\n".join(map(
                format_command,
                cog_commands
            ))
        )

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = neo.Embed(
            title=f"{self.context.clean_prefix}{command.qualified_name} {command.signature}",
            description="{}\n".format(command.help or "No description")
        )

        if isinstance(command, commands.Group):
            embed.add_field(
                name="Subcommands",
                value="\n".join(map(
                    lambda sub: f"{sub.full_parent_name} **{sub.name}**",
                    command.walk_commands()
                )) or "No subcommands"
            )

        if hasattr(command, "get_args_help"):
            for dest, help in command.get_args_help():
                embed.description += f"\n**{dest}** {help}"

        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        await self.send_command_help(group)
