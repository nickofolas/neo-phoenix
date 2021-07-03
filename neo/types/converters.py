# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import re
import zoneinfo

CODEBLOCK_REGEX = re.compile(r"^\w*\n", re.I)
EXTRACT_MENTION_REGEX = re.compile(r"<@!?(\d+)>")


def codeblock_converter(codeblock: str) -> str:
    new = None
    if all([codeblock.startswith("`"), codeblock.endswith("`")]):
        new = codeblock.strip("`")
        return re.sub(CODEBLOCK_REGEX, "", new)
    return codeblock


def timezone_converter(timezone: str) -> str:
    try:
        zone = zoneinfo.ZoneInfo(timezone)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValueError("Provided timezone was invalid.")
    return str(zone)


def mention_converter(mention: str) -> int:
    return int(EXTRACT_MENTION_REGEX.match(mention)[1])


def timeout_converter(timeout: str) -> int:
    if not timeout.isdigit():
        raise ValueError
    timeout = int(timeout)
    if not (timeout >= 1 and timeout <= 5):
        raise ValueError
    return timeout


def max_days_converter(max_days: str) -> int:
    if not max_days.isdigit():
        raise ValueError
    max_days = int(max_days)
    if not max_days > 1:
        raise ValueError
    return max_days
