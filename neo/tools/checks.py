# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from discord.ext import commands


def is_registered_profile():
    """Verify the registration status of a user profile"""
    def predicate(ctx):
        if ctx.author.id not in ctx.bot.profiles:
            raise commands.CommandInvokeError(AttributeError(
                "Looks like you don't have an existing profile! "
                "You can fix this with the `profile create` command."
            ))
        return True
    return commands.check(predicate)


def is_registered_guild():
    """Verify the registration status of a guild"""
    def predicate(ctx):
        if ctx.guild.id not in ctx.bot.servers:
            raise commands.CommandInvokeError(AttributeError(
                "Looks like this server doesn't have an existing config entry. "
                "You can fix this with the `server create` command."
            ))
        return True
    return commands.check(predicate)
