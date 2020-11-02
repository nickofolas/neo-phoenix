import re
import types


class ArgParser:  # Let's rewrite ArgParse from the ground up because why not
    """
    A weird clone of argparse.

    The key difference is that is parses full strings, not a split list.
    This means that newlines and such are preserved.
    """
    _args = {}

    def add_arg(
            self,
            *argnames,
            convert=None,
            default=None,
            choices=None,
            type='arg',
            required=False
    ):
        """
        Register a new argument to the parser.
        Any number of names can be passed, but the parsed namespace will
        use the longest name as its key.

        Parameters
        ----------
        convert
            Pass in a function or type that the argument will be run through
            to convert it
        default
            Pass in a default value for the argument if it is not provided
        choices
            Pass in a set list of choices that can be used. A TypeError
            will be raised if an invalid choice is passed.
        type
            Can be one of 'arg' or 'flag'. The 'arg' type will take
            values, and the 'flag' type acts as a simple toggle.
        required
            Specify if an argument is required. A TypeError will be
            raised if it is not found.
        """
        if type not in ('arg', 'flag'):
            raise TypeError('\'type\' must be one of [\'arg\', \'flag\']')

        argnames = [*map(lambda n: n.lstrip('-'), argnames)]
        _max = max(argnames, key=len)
        self._args[_max] = {
            'convert': convert,
            'default': default,
            'choices': choices,
            'type': type,
            'required': required,
            'patterns': []}
        for _name in argnames:
            self._args[_max]['patterns'].append(re.compile(r'^{}\b'.format(_name), re.I))

    def parse(self, to_parse):
        dash_split = re.compile(r'--?').split(to_parse)
        output = {}

        for k, v in self._args.items():

            value = None
            for string in dash_split:
                for p in v['patterns']:
                    if (match := p.search(string)):
                        break
                else:
                    continue
                no_arg = string[len(match.group(0)):].strip()

                if v['type'] == 'flag':
                    output[k] = True
                    dash_split[dash_split.index(string)] = no_arg
                    continue

                value = no_arg
                dash_split.remove(string)

                if (conv := v['convert']) is not None:
                    value = conv(value)
                if (chcs := v['choices']) is not None:
                    if value not in chcs:
                        raise TypeError(
                            'Argument \'{}\' must be one of [{!r}]'.format(
                                k, ', '.join(chcs)))

                output[k] = value

            if k not in [*output.keys()]:
                if v['required'] is True:
                    raise TypeError('Argument \'{}\' is required'.format(
                        k))
                if (_def := v['default']) is not None:
                    output[k] = _def

        return types.SimpleNamespace(**output, unused_strings=[*filter(None, dash_split)])
