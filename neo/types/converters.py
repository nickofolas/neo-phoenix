import re

from discord.ext import commands

CODEBLOCK_REGEX = re.compile(r"^\w*\n", re.I)
EXTRACT_MENTION_REGEX = re.compile(r"<@!?(\d+)>")


class CodeblockConverter(commands.Converter):
    async def convert(self, ctx, arg):
        new = None
        if all([arg.startswith("`"), arg.endswith("`")]):
            new = arg.strip("`")
            return re.sub(CODEBLOCK_REGEX, "", new)
        return arg


class MentionConverter(commands.Converter):
    async def convert(self, ctx, arg):
        return EXTRACT_MENTION_REGEX.match(arg)[1]
