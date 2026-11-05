"""Bounded integer and switch parsing shared by the CLI, environment settings and `.env`."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

MAX_PROCESS_INTEGER = 2**31 - 1
# Set to true by someone who develops in the checkout, so a finished build keeps
# the linter and test caches instead of deleting them.
BYPASS_CACHE_DELETE = "BYPASS_CACHE_DELETE"
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("", "0", "false", "no", "off")


def parse_integer(value: str, *, minimum: int = 1, maximum: int = sys.maxsize) -> int | None:
    pattern = r"[1-9][0-9]*" if minimum else r"[0-9]+"
    if not re.fullmatch(pattern, value):
        return None
    if len(value) > len(str(maximum)):
        return None
    number = int(value)
    return number if minimum <= number <= maximum else None


def parse_switch(value: str) -> bool | None:
    """true/false (also 1/0, yes/no, on/off; empty is false); None when unrecognized."""
    choice = value.strip().lower()
    if choice in _TRUE:
        return True
    if choice in _FALSE:
        return False
    return None


def checkout_setting(repository: Path, name: str) -> str:
    """`name` from the environment, else from the checkout's untracked `.env`.

    Only `NAME=value` lines are read; quotes around the value and a trailing
    ` # comment` are dropped, and the last assignment wins. Nothing else in the
    file is loaded, so a `.env` kept for other tools cannot change a build. A
    missing file means unset; any other read error is raised.
    """
    if name in os.environ:
        return os.environ[name]
    try:
        text = (repository / ".env").read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    value = ""
    for line in text.splitlines():
        key, separator, assigned = line.partition("=")
        if separator and key.strip() == name:
            value = assigned.split(" #", 1)[0].strip().strip("'\"")
    return value
