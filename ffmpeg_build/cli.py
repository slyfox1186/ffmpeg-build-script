"""Command-line parsing.

The help screen itself lives in `usage`, which the launcher can import on any
interpreter. `argparse` is not used at all: its formatter rewraps, re-sorts and
re-indents, and it cannot reproduce the layout `README.md` pins byte for byte.

Parsing runs in three passes for a reason the tests pin down: metadata options
are answered before anything else so `--help` and `--version` stay free of side
effects, the whole command line is validated next, and only then is a
configuration file opened. An invalid request must never cause a TOML file to
be read and applied on its way to the error.
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import COMPILERS
from .runtime.errors import UsageError
from .runtime.settings import MAX_PROCESS_INTEGER, parse_integer
from .usage import SCRIPT_NAME, SCRIPT_VERSION, metadata_response, usage_text

__all__ = [
    "Arguments",
    "SCRIPT_NAME",
    "SCRIPT_VERSION",
    "parse_arguments",
    "requested_metadata",
    "resolve_config_path",
    "usage_text",
]


class Arguments:
    """The parsed command line."""

    def __init__(self) -> None:
        self.build = False
        self.cleanup = False
        self.menu = False
        self.compiler: str | None = None
        self.jobs: int | None = None
        self.latest = False
        self.nonfree_and_gpl = False
        self.config_path: str | None = None


def requested_metadata(argv: list[str]) -> str | None:
    """Answer `--help`/`--version` before any other work happens."""
    return metadata_response(argv)


def parse_arguments(argv: list[str]) -> Arguments:
    arguments = Arguments()
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ("-b", "--build"):
            arguments.build = True
        elif argument in ("-c", "--cleanup"):
            arguments.cleanup = True
        elif argument in ("-m", "--menu"):
            arguments.menu = True
        elif argument in ("-l", "--latest"):
            arguments.latest = True
        elif argument in ("-n", "--enable-gpl-and-non-free"):
            arguments.nonfree_and_gpl = True
        elif argument in ("--gcc", "--clang"):
            arguments.compiler = argument.removeprefix("--")
        elif argument == "--compiler":
            if index + 1 >= len(argv):
                raise UsageError("Missing value for '--compiler'.")
            arguments.compiler = argv[index + 1]
            index += 1
        elif argument.startswith("--compiler="):
            arguments.compiler = argument.split("=", 1)[1]
        elif argument in ("-j", "--jobs"):
            if index + 1 >= len(argv):
                raise UsageError(f"Missing value for '{argument}'.")
            arguments.jobs = _parse_jobs(argv[index + 1])
            index += 1
        elif argument.startswith("--jobs="):
            arguments.jobs = _parse_jobs(argument.split("=", 1)[1])
        elif argument == "--config":
            if index + 1 >= len(argv):
                raise UsageError("Missing value for '--config'.")
            if arguments.config_path is not None:
                raise UsageError("'--config' may only be specified once.")
            arguments.config_path = argv[index + 1]
            index += 1
        elif argument.startswith("--config="):
            if arguments.config_path is not None:
                raise UsageError("'--config' may only be specified once.")
            arguments.config_path = argument.split("=", 1)[1]
        elif argument in ("-h", "--help", "-v", "--version"):
            # Already answered before the config is loaded, so these stay
            # side-effect free.
            pass
        elif argument == "--":
            remainder = argv[index + 1 :]
            if remainder:
                raise UsageError(f"Unexpected positional arguments: '{' '.join(remainder)}'.")
            break
        else:
            raise UsageError(f"Unknown option '{argument}'.")
        index += 1

    if arguments.compiler is not None and arguments.compiler not in COMPILERS:
        raise UsageError(f"Invalid compiler '{arguments.compiler}'; expected 'gcc' or 'clang'.")
    chosen = [
        name
        for name, selected in (
            ("--build", arguments.build),
            ("--cleanup", arguments.cleanup),
            ("--menu", arguments.menu),
        )
        if selected
    ]
    if len(chosen) > 1:
        raise UsageError(f"'{chosen[0]}' and '{chosen[1]}' are mutually exclusive.")
    return arguments


def _parse_jobs(value: str) -> int:
    parsed = parse_integer(value, maximum=MAX_PROCESS_INTEGER)
    if parsed is None:
        raise UsageError(f"Invalid jobs value '{value}'; expected a positive integer.")
    return parsed


def resolve_config_path(raw_path: str, invocation_dir: Path) -> Path:
    """Resolve `--config` against the invocation directory only.

    Retrying a missing relative path under the script's own directory would let
    a stale `custom.toml` sitting next to the launcher supply a different
    package selection, with nothing in the output naming the file that won.
    """
    if not raw_path:
        raise UsageError("Invalid value for '--config'.")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in raw_path):
        raise UsageError("Invalid value for '--config'.")
    candidate = Path(raw_path) if raw_path.startswith("/") else invocation_dir / raw_path
    return Path(os.path.realpath(candidate, strict=False))
