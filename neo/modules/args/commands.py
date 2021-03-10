from inspect import isawaitable

import discord
from discord.ext import commands

from .parser import Parser


class ArgCommand(commands.Command):

    @property
    def signature(self):
        if self.usage is not None:
            return self.usage

        args = []

        for arg in reversed(self.callback.parser._actions):
            argname = f"--{arg.dest}" if arg.option_strings else arg.dest

            if arg.choices:
                argname += " [{}]".format("|".join(args.choices))

            if arg.required:
                argname = f"<{argname}>"
            else:
                argname = f"[{argname}]"

            args.append(argname)

        return " ".join(args)

    def get_args_help(self):

        for action in reversed(self.callback.parser._actions):
            if not hasattr(action, "dest"):  # Logically this shouldn't happen
                continue

            yield (action.dest, getattr(action, "help", None))

    async def _parse_arguments(self, ctx):

        self.callback.parser.ctx = ctx

        ctx.args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.kwargs = {}

        kwargs = ctx.kwargs
        view = ctx.view
        iterator = iter(self.params.items())

        if self.cog is not None:
            try:
                next(iterator)
            except StopIteration:
                fmt = "Callback for {0.name} command is missing \"self\" parameter."
                raise discord.ClientException(fmt.format(self))

            try:
                next(iterator)
            except StopIteration:
                fmt = "Callback for {0.name} command is missing \"ctx\" parameter."
                raise discord.ClientException(fmt.format(self))

            fmt = "Callback for {0.name} must contain one keyword-only argument."
            try:
                name, param = next(iterator)
                if param.kind != param.KEYWORD_ONLY:
                    raise discord.ClientException(fmt.format(self))

                to_parse = view.read_rest().strip()
                if to_parse is None:
                    kwargs[name] = None
                    return

                try:
                    parsed = self.callback.parser.parse_args(to_parse.split(" "))
                except Exception as e:
                    kwargs[name] = None
                    await self.dispatch_error(ctx, e)
                    return
                else:
                    for k, v in vars(parsed).items():

                        if not isinstance(v, list):
                            if isawaitable(v):
                                try:
                                    vars(parsed)[k] = await v
                                except Exception as e:
                                    await self.dispatch_error(ctx, e)
                            continue

                        values = []
                        for result in v:

                            if isawaitable(result):
                                try:
                                    values.append(await result)
                                    continue
                                except Exception as e:
                                    await self.dispatch_error(ctx, e)
                                    return

                            values.append(result)
                        vars(parsed)[k] = values

                    kwargs[name] = parsed

            except StopIteration:
                raise discord.ClientException(fmt.format(self))


def add_arg(*args, **kwargs):
    """
    Add an argument to this command's arguments.

    Parameters are just those of argparse's parser.add_argument.

    Note: The `type` kwarg can be a commands.Converter subclass,
    and will attempt to convert the given values.
    """
    def inner(func):
        _func = func.callback if isinstance(func, commands.Command) else func

        if not hasattr(_func, "parser"):
            _func.parser = Parser()

        _func.parser.add_argument(*args, **kwargs)
        return func
    return inner


class ArgGroup(ArgCommand, commands.Group):
    def arg_command(self, **kwargs):
        def inner(func):
            cls = kwargs.get("cls", ArgCommand)
            kwargs["parent"] = self
            result = cls(func, **kwargs)
            self.add_command(result)
            return result
        return inner

    def arg_group(self, **kwargs):
        def inner(func):
            cls = kwargs.get("cls", ArgGroup)
            kwargs["parent"] = self
            result = cls(func, **kwargs)
            self.add_command(result)
            return result
        return inner


def command(**kwargs):
    def inner(func):
        cls = kwargs.get("cls", ArgCommand)
        return cls(func, **kwargs)
    return inner


def group(**kwargs):
    def inner(func):
        cls = kwargs.get("cls", ArgGroup)
        return cls(func, **kwargs)
    return inner
