"""Bounded ASCII integer parsing shared by CLI, menu and environment settings."""

from __future__ import annotations

import re
import sys

MAX_PROCESS_INTEGER = 2**31 - 1


def parse_integer(value: str, *, minimum: int = 1, maximum: int = sys.maxsize) -> int | None:
    pattern = r"[1-9][0-9]*" if minimum else r"[0-9]+"
    if not re.fullmatch(pattern, value):
        return None
    if len(value) > len(str(maximum)):
        return None
    number = int(value)
    return number if minimum <= number <= maximum else None
