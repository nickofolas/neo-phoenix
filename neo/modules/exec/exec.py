# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from inspect import isasyncgenfunction

from .compiler import compile_all


def env_from_context(ctx):
    return {
        "ctx": ctx,
        "author": ctx.author,
        "guild": ctx.guild,
        "message": ctx.message,
        "channel": ctx.channel,
        "bot": ctx.bot,
        "_": ctx.cog._last_exec_result,
    }


class ExecWrapper:
    __slots__ = ("compiled", "globals_", "locals_")

    def __init__(self, code_input, globals_={}, locals_={}):
        self.compiled = compile_all(code_input)
        self.globals_ = globals_
        self.locals_ = locals_

    def __aiter__(self):
        exec(compile(self.compiled, "<exec>", "exec"), self.globals_, exec_locals := {})
        _aexec = exec_locals["__aexec__"]
        return self.walk_results(_aexec, self.locals_)

    async def walk_results(self, coro, *args, **kwargs):
        try:
            if isasyncgenfunction(coro):
                async for result in coro(*args, **kwargs):
                    yield result
            else:
                yield await coro(*args, **kwargs)

        finally:
            if "scope" in self.locals_:
                del self.locals_["scope"]
