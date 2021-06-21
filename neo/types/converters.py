import re
import zoneinfo

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
        return int(EXTRACT_MENTION_REGEX.match(argument)[1])


class PartialEmojiStrConverter(commands.PartialEmojiConverter):
    async def convert(self, ctx, argument):
        emoji = await super().convert(ctx, argument)
        return str(emoji)


class TimezoneConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        try:
            zone = zoneinfo.ZoneInfo(argument)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError("Provided timezone was invalid.")
        return str(zone)


def timeout_converter(timeout: str) -> int:
    if not timeout.isdigit():
        raise ValueError
    timeout = int(timeout)
    if not (timeout >= 1 and timeout <= 5):
        raise ValueError
    return timeout


def max_days_converter(max_days: str) -> int:
    if not max_days.isdigit():
        raise ValueError
    max_days = int(max_days)
    if not max_days > 1:
        raise ValueError
    return max_days
