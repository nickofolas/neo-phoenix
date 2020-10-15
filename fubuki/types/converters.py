import re

from discord.ext import commands

codeblock_regex = re.compile(r"^\w*\n", re.I)


class CodeblockConverter(commands.Converter):
    async def convert(self, ctx, arg):
        new = None
        if all([arg.startswith("`"), arg.endswith("`")]):
            new = arg.strip("`")
            return re.sub(codeblock_regex, "", new)
        return arg
