import discord
from discord.ext import commands

from .argparser import ArgParser


def add_arg(*args, **kwargs):
    def inner(func):
        if not hasattr(func, '__args'):
            func.__args = []
        func.__args.append((args, kwargs))
        return func
    return inner


class ArgCommand(commands.Command):

    def __init__(self, *args, accept_beyond_flags=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.accept_beyond_flags = accept_beyond_flags
        self.parser = ArgParser()
        for args, kwargs in vars(self._callback)['__args']:
            self.parser.add_arg(*args, **kwargs)

    @property
    def signature(self):
        if self.usage is not None:
            return self.usage

        args = []

        for arg, kwargs in reversed(self.parser._args.items()):
            argname = '--%s' % arg if kwargs['type'] != 'pos' else arg
            if kwargs['choices']:
                argname += ' [%s]' % '|'.join(kwargs['choices'])
            if kwargs['required'] is True:
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
                        kwargs[name] = self.parser.parse(await self.do_conversion(ctx, converter, argument, param))
                    else:
                        kwargs[name] = self.parser.parse(await self.transform(ctx, param))
                else:
                    fmt = 'Callback for {0.name} can only contain one keyword-only argument.'
                    raise discord.ClientException(fmt.format(self))
