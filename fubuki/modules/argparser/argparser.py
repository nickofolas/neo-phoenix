import re
import types


class ArgParser:  # Let's rewrite ArgParse from the ground up because why not
    _args = {}

    def add_arg(
            self,
            *argnames,
            convert=None,
            default=None,
            choices=None,
            type='arg'
    ):
        if type not in ('arg', 'flag'):
            raise TypeError('\'type\' must be one of [\'arg\', \'flag\']')

        argnames = [*map(lambda n: n.lstrip('-'), argnames)]
        _max = max(argnames, key=len)
        self._args[_max] = {
            'convert': convert,
            'default': default,
            'choices': choices,
            'type': type,
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
                if (_def := v['default']) is not None:
                    output[k] = _def

        return types.SimpleNamespace(**output, unused_strings=[*filter(None, dash_split)])
