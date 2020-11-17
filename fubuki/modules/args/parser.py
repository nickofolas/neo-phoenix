from argparse import ArgumentError, ArgumentParser

from discord.ext.commands import Converter


class Parser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.ctx = None
        kwargs.setdefault('add_help', False)
        super().__init__(*args, **kwargs)

    def error(self, message, _error=RuntimeError):
        raise _error(message)

    def _get_value(self, action, arg_string):
        converter = self._registry_get('type', action.type, action.type)

        if not callable(converter):
            msg = '%r is not callable'
            raise ArgumentError(action, msg % converter)

        try:
            if isinstance(converter, type) and issubclass(converter, Converter):
                result = converter().convert(self.ctx, arg_string)
                # Above tries to return an awaitable from a converter
            else:
                result = converter(arg_string)

        except Exception as e:
            raise e

        return result
