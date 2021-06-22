"""
Implements an extremely simple mechanism for parsing a datetime object out of
a string of text.
"""
import re
from datetime import datetime, timedelta
from typing import Optional

from neo.tools import try_or_none

CURRENT_YEAR = datetime.now().year
ABSOLUTE_FORMATS = {  # Use a set so %H:%M doesn't get duplicated
    "%a %b %d",
    "%a %b %d %Y",
    "%H:%M",
    "%a %b %d at %H:%M",
    "%a %b %d %Y at %H:%M"
}  # Define a very rigid set of formats that can be passed
ABSOLUTE_FORMATS |= {i.replace("%a %b", "%A %B") for i in ABSOLUTE_FORMATS}
RELATIVE_FORMATS = re.compile(
    r"""
    ((?P<years>[0-9]{1,2})(?:y(ears?)?))?      # Parse years, allow 1-2 digits
    ((?P<weeks>[0-9]{1,2})(?:w(eeks?)?))?      # Parse weeks, allow 1-2 digits
    ((?P<days>[0-9]{1,4})(?:d(ays?)?))?        # Parse days, allow 1-4 digits
    ((?P<hours>[0-9]{1,4})(?:h(ours?)?))?      # Parse hours, allow 1-4 digits
    ((?P<minutes>[0-9]{1,4})(?:m(inutes?)?))?  # Parse minutes, allow 1-4 digits
    ((?P<seconds>[0-9]{1,4})(?:s(econds?)?))?  # Parse seconds, allow 1-4 digits
    """,
    re.X | re.I
)


class TimedeltaWithYears(timedelta):
    def __new__(
        cls,
        *,
        years: float = 0,
        weeks: float = 0,
        days: float = 0,
        hours: float = 0,
        minutes: float = 0,
        seconds: float = 0,
    ):
        days = days + (years * 365)
        return super().__new__(
            cls,
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )


def parse_absolute(string: str) -> Optional[datetime]:
    split = string.replace(",", "").split(" ")  # Allow commas because they can be more ergonomic
    endpoint = len(split)

    for _ in range(len(split)):  # Check for every possible chunk size
        to_parse = split[:endpoint]  # Check the string in left-to-right increments

        for format in ABSOLUTE_FORMATS:
            if (dt := try_or_none(datetime.strptime, " ".join(to_parse), format)):
                if dt.year < CURRENT_YEAR:  # If a year isn't explicitly provided, add it
                    dt = dt.replace(year=CURRENT_YEAR)
                break

        if dt is not None:  # We got a hit
            break
        endpoint -= 1  # Increase the size of the chunk by one word

    else:
        raise ValueError("An invalid date format was provided.")
    return dt


def parse_relative(string: str) -> Optional[TimedeltaWithYears]:
    to_parse = string \
        .replace(" ", "") \
        .replace(",", "") \
        .replace("and", "")  # Remove "and", commas, and whitespace to prepare for parsing
    if any((parsed := RELATIVE_FORMATS.match(to_parse)).groups()):
        data = {k: float(v) for k, v in parsed.groupdict().items() if v}
        return TimedeltaWithYears(**data)

    else:  # Nothing matched
        raise ValueError("Failed to find a valid offset.")
