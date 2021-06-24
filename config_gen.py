# Generates a file from an existing config file.
#
# The file to be read as input is sys.argv[1], or "config.toml" if that doesn't exist.
# The filename is sys.argv[2], or "example_config.toml" if that doesn't exist.
# If the output filename is provided, an input filename must also be provided.
#
# The generated file contains a recursively constructed copy of the input file,
# omitting the values, and replacing them with the expected type of the value.
from sys import argv

import toml

INPUT_FILE = next(iter(argv[1:]), "config.toml")
OUTPUT_FILE = next(iter(argv[2:]), "example_config.toml")

ORIGINAL = toml.load("config.toml")


class PrettyListEncoder(toml.TomlEncoder):  # Dump lists with newlines
    def dump_list(self, v):
        retval = "["
        endpoint = len(v)
        for i in range(endpoint):
            u = v[i]
            lineterm = ","
            if (i + 1) == endpoint:
                lineterm = ""
            retval += "\n    " + str(self.dump_value(u)) + lineterm
        retval += "\n]"
        return retval


def generate_template(data: dict) -> dict:
    data = data.copy()  # Preserve original
    for k, v in data.items():
        if isinstance(v, dict):
            v = generate_template(v)
        elif isinstance(v, list):
            v = v.copy()
            for index, value in enumerate(v):
                if isinstance(value, dict):
                    v[index] = generate_template(value)
                else:
                    v[index] = type(value).__name__
        else:
            v = type(v).__name__
        data[k] = v
    return data

toml.dump(
    generate_template(ORIGINAL),
    open(OUTPUT_FILE, "w"),
    encoder=PrettyListEncoder()
)
