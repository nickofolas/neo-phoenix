# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import traceback
from enum import Enum
from logging import Formatter, LogRecord
from typing import Optional, Union


def format_exception(exc: Union[BaseException, tuple]) -> Optional[str]:
    if isinstance(exc, tuple) and all(exc):
        exc_info = exc
    elif isinstance(exc, BaseException):
        exc_info = (type(exc), exc, exc.__traceback__)
    else:
        return None
    return "".join(traceback.format_exception(*exc_info)).rstrip()


class Table:
    __slots__ = ("columns", "rows", "widths", "border")

    def __init__(self):
        self.columns: list[str] = []
        self.rows: list[list[str]] = []
        self.widths: list[int] = []

    def init_columns(self, columns: list[str]):
        self.columns = columns
        self.widths = [len(col) + 4 for col in columns]

    def add_row(self, row: list[str]):
        if len(row) > len(self.columns):
            raise ValueError("Row has too many columns")
        self.rows.append(row)

        for index, item in enumerate(row):
            if (len(item) + 4) > self.widths[index]:
                self.widths[index] = len(item) + 4

    def build(self):
        cols = []
        for index, col in enumerate(self.columns):
            cols.append(col.center(self.widths[index]))
        self.columns = "|" + "|".join(cols) + "|"

        separator = "+".join("-" * w for w in self.widths)
        self.border = "+" + separator + "+"

        rows = []
        for row in self.rows:
            final_row = []
            for index, item in enumerate(row):
                final_row.append(item.center(self.widths[index]))
            rows.append("|" + "|".join(final_row) + "|")
        self.rows = rows

    def display(self):
        self.build()
        rows = "\n".join(self.rows)
        return (
            f"{self.border}\n"
            f"{self.columns}\n"
            f"{self.border}\n"
            f"{rows}\n"
            f"{self.border}"
        )


class Color(Enum):
    RESET = "0"
    PURPLE = "38;2;162;155;254"
    GREEN = "38;2;186;230;126"
    CYAN = "38;2;92;207;230"
    GREY = "38;2;112;122;140"
    SILVER = "38;2;92;103;115"
    TAN = "38;2;255;230;179"
    ORANGE = "38;2;255;167;89"
    RED = "38;2;255;51;51"

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = f"\033[{value}m"
        return obj

    def __call__(self, string: str):  # Is this considered a crime?
        return f"{self.value}{string}{Color.RESET.value}"


class NeoLoggingFormatter(Formatter):
    COLORS = {
        "DEBUG": Color.SILVER,
        "INFO": Color.GREEN,
        "WARNING": Color.TAN,
        "ERROR": Color.ORANGE,
        "CRITICAL": Color.RED
    }

    def __init__(self, **kwargs):
        kwargs["style"] = "{"
        kwargs["datefmt"] = Color.CYAN("%d-%m-%Y %H:%M:%S")
        super().__init__(**kwargs)

    def format(self, record: LogRecord):
        record.asctime = Color.CYAN(self.formatTime(record, self.datefmt))
        record.msg = Color.GREY(record.msg)
        record.name = Color.PURPLE(record.name)
        record.levelname = self.COLORS[record.levelname](record.levelname)
        return super().format(record)
