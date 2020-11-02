from argparse import ArgumentParser

import discord
from discord.ext import commands

class SafeArgParser(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class ArgCommand(commands.Command):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def signature(self):
        if self.usage is not None:
            return self.usage

        args = []

        for arg in reversed(self.callback.parser._actions):
            argname = '--%s' % arg.dest if arg.option_strings else arg.dest
            if arg.choices:
                argname += ' [%s]' % '|'.join(args.choices)
            if arg.required is True:
                argname = '<%s>' % argname
            else:
                argname = '[%s]' % argname
            args.append(argname)

        return ' '.join(args)

    async def _parse_arguments(self, ctx):

        ctx.args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.kwargs = {}

        kwargs = ctx.kwargs
        view = ctx.view
        iterator = iter(self.params.items())

        if self.cog is not None:
            try:
                next(iterator)
            except StopIteration:
                fmt = 'Callback for {0.name} command is missing "self" parameter.'
                raise discord.ClientException(fmt.format(self))

            try:
                next(iterator)
            except StopIteration:
                fmt = 'Callback for {0.name} command is missing "ctx" parameter.'
                raise discord.ClientException(fmt.format(self))

            for name, param in iterator:
                if param.kind == param.KEYWORD_ONLY:
                    if self.rest_is_raw:
                        converter = self._get_converter(param)
                        argument = view.read_rest()
                        to_parse = await self.do_conversion(ctx, converter, argument, param)
                    else:
                        to_parse = await self.transform(ctx, param)
                    to_parse = (to_parse or '').split(' ')
                    kwargs[name] = self.callback.parser.parse_args(to_parse)
                else:
                    fmt = 'Callback for {0.name} can only contain one keyword-only argument.'
                    raise discord.ClientException(fmt.format(self))


def add_arg(*args, **kwargs):
    def inner(func):
        _func = func.callback if isinstance(func, commands.Command) else func

        if not hasattr(_func, 'parser'):
            _func.parser = SafeArgParser(add_help=False)

        _func.parser.add_argument(*args, **kwargs)
        return func
    return inner


class ArgGroup(ArgCommand, commands.Group):
    def arg_command(self, **kwargs):
        def inner(func):
            cls = kwargs.get('cls', ArgCommand)
            kwargs['parent'] = self
            result = cls(func, **kwargs)
            self.add_command(result)
            return result
        return inner

    def arg_group(self, **kwargs):
        def inner(func):
            cls = kwargs.get('cls', ArgGroup)
            kwargs['parent'] = self
            result = cls(func, **kwargs)
            self.add_command(result)
            return result
        return inner


def command(**kwargs):
    def inner(func):
        cls = kwargs.get('cls', ArgCommand)
        return cls(func, **kwargs)
    return inner


def group(**kwargs):
    def inner(func):
        cls = kwargs.get('cls', ArgGroup)
        return cls(func, **kwargs)
    return inner
