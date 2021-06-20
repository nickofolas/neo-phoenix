import re

from discord.ext import commands

CODEBLOCK_REGEX = re.compile(r"^\w*\n", re.I)
EXTRACT_MENTION_REGEX = re.compile(r"<@!?(\d+)>")


class CodeblockConverter(commands.Converter):
    async def convert(self, ctx, argument):
        new = None
        if all([argument.startswith("`"), argument.endswith("`")]):
            new = argument.strip("`")
            return re.sub(CODEBLOCK_REGEX, "", new)
        return argument


class MentionConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return EXTRACT_MENTION_REGEX.match(argument)[1]


class PartialEmojiStrConverter(commands.PartialEmojiConverter):
    async def convert(self, ctx, argument):
        emoji = await super().convert(ctx, argument)
        return str(emoji)
