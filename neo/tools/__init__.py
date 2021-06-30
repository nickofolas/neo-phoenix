from discord.ext import commands

from .checks import is_registered_guild, is_registered_profile
from .patcher import Patcher


def try_or_none(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


async def convert_setting(ctx, mapping, setting, new_value):
    if not (valid_setting := mapping.get(setting)):
        raise commands.BadArgument(
            "That's not a valid setting! "
            "Try `settings` for a list of settings!"
        )

    converter = valid_setting["converter"]
    if isinstance(converter, commands.Converter):
        if (converted := await converter.convert(ctx, new_value)) is not None:
            value = converted

    elif (converted := try_or_none(converter, new_value)) is not None:
        value = converted

    else:
        raise commands.BadArgument(
            "Bad value provided for setting `{}`".format(setting)
        )

    return value
