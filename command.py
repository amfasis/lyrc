from collections import namedtuple

CommandItem = namedtuple("CommandItem", [
    "directive",
    "remote",
    "key_code",
    "future"
])