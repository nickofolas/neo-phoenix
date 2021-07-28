# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from inspect import iscoroutinefunction
from types import FunctionType, MethodType

from discord.ext import commands


class AddonMeta(commands.CogMeta):
    def __new__(cls, *args, **kwargs):
        _cls = commands.CogMeta.__new__(cls, *args, **kwargs)
        receivers = {}

        for base in _cls.__mro__:
            for attr in vars(base).values():
                if not isinstance(attr, FunctionType) or \
                        not getattr(attr, "__receiver__", False):
                    continue
                receivers[attr.__event_name__] = attr

        _cls.__receivers__ = receivers
        return _cls


class Addon(commands.Cog, metaclass=AddonMeta):
    def __init__(self, bot):
        """
        This just removes the mandatory __init__ for every single addon
        """
        self.bot = bot

    def add_command(self, command):
        """
        Add a commands.Command or a subclass of it to a loaded Addon

        If a commands.Group is encountered, all subcommands will also be recursively added
        """
        _original_command = command

        _current_commands = list(self.__cog_commands__)
        _current_commands.append(command)
        self.__cog_commands__ = tuple(_current_commands)

        for _command in self.__cog_commands__:
            self.bot.remove_command(_command.name)
            _command.cog = self
            if not _command.parent:
                self.bot.add_command(_command)

        if isinstance(_original_command, commands.Group):
            for subcmd in command.walk_commands():
                if isinstance(subcmd, commands.Group):  # Recursively add sub-groups
                    self.add_command(subcmd)
                subcmd.cog = self  # Update the subcmds

        return self.bot.get_command(command.name)

    def add_listener(self, listener, name=None):
        """
        Registers a listener to a loaded Addon
        """
        setattr(
            self,
            listener.__name__,
            MethodType(
                listener.__func__ if isinstance(
                    listener,
                    MethodType) else listener,
                self
            )
        )  # Bind the listener to the object as a method
        self.__cog_listeners__.append(
            (name or listener.__name__, listener.__name__)
        )  # Add it to the list

        for name, method_name in self.__cog_listeners__:
            self.bot.remove_listener(getattr(self, method_name))  # Just in case I guess
            self.bot.add_listener(getattr(self, method_name), name)  # Register it as a listener

    def _merge_addon(self, other):
        """
        Handles merging 2 addons together.
        Generally for internal use
        """
        self.bot.remove_cog(other.qualified_name)  # Consume the other addon
        for _cmd in other.__cog_commands__:  # Add all commands over
            self.add_command(_cmd)
        for name, method_name in other.__cog_listeners__:  # Add all listeners over
            self.add_listener(getattr(other, method_name), name)

    def __or__(self, other):
        """
        Uses the `|` operator to merge two addons together.
        When merged, all commands and listeners from the second addon
        will be added to the first addon, consuming the second addon
        in the process.
        """
        self._merge_addon(other)
        return self

    @classmethod
    def recv(cls, event: str):
        def inner(func):
            if not iscoroutinefunction(func):
                raise ValueError("Addon receiver must be a coroutine.")
            receiver = func
            receiver.__receiver__ = True
            receiver.__event_name__ = event
            return receiver
        return inner
