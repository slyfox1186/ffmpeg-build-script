"""The help screen, the version string, and the terminal color policy.

The launcher imports this module on whatever interpreter the user happened to
start, which on Ubuntu 22.04 is Python 3.10. `--help` and `--version` are
answered before any interpreter resolution, so this file must parse on every
interpreter the project can be launched from and must import nothing that does
not.

The plain layout is a contract. `README.md` reproduces it verbatim and the
linter diffs the two byte for byte, so the text is wrapped to a fixed WIDTH
rather than to the terminal. Color is added only on top of that layout: the
escape codes wrap tokens in place and never change the visible text.
"""

from __future__ import annotations

import os
import re
import textwrap
from typing import TextIO

SCRIPT_VERSION = "8.1.0"
SCRIPT_NAME = "build-ffmpeg.py"
COMMAND = "python3 " + SCRIPT_NAME

WIDTH = 80
INDENT = "  "
LABEL_WIDTH = 30
DESCRIPTION_COLUMN = len(INDENT) + LABEL_WIDTH + 2

SUMMARY = (
    "Builds FFmpeg and its libraries from source and installs FFmpeg under "
    "/usr/local. Run it as a normal user with sudo access. Choose exactly one "
    "action; with none, this help is shown."
)
ACTIONS = (
    ("-b, --build", "Build and install FFmpeg"),
    ("-m, --menu", "Pick packages in a menu, then build"),
    ("-c, --cleanup", "Delete the build root and build leftovers"),
)
BUILD_OPTIONS = (
    (
        "    --config <file>",
        "Build only the packages this TOML file enables; start from example.toml "
        "(default: every package)",
    ),
    ("    --compiler <gcc|clang>", "Compiler to use (default: gcc)"),
    ("    --gcc, --clang", "Same as --compiler gcc / --compiler clang"),
    ("-j, --jobs <count>", "Parallel build jobs (default: available CPUs)"),
    ("-l, --latest", "Check upstream for newer releases and rebuild outdated dependencies"),
    (
        "-n, --enable-gpl-and-non-free",
        "Allow GPL and non-free components, required for x264, x265, fdk-aac and "
        "CUDA/NVENC; the result may not be redistributable",
    ),
)
GENERAL_OPTIONS = (
    ("-h, --help", "Show this help; changes nothing on disk"),
    ("-v, --version", "Show the script version"),
)
VALUE_NOTE = "Options that take a value also accept --option=value, for example --jobs=8."
ENVIRONMENT = (
    ("BUILD_ROOT=<dir>", "Build workspace (default: build/ in this checkout)"),
    (
        "CUDA_INSTALL=<mode>",
        "Install a missing CUDA toolkit: ask, always or never (default: ask)",
    ),
    ("CUDA_ARCH_MODE=<mode>", "GPU code targets: native, all or custom (default: native)"),
    ('CUDA_ARCHITECTURES="<list>"', 'Targets for custom mode, for example "86 89"'),
    (
        "FFMPEG_BUILD_DEBUG=ON",
        "Stream all command output to the terminal; the build log is still written (default: OFF)",
    ),
)
EXAMPLES = (
    (
        "Build the packages enabled in your config (copy example.toml first)",
        COMMAND + " --build --config ./custom.toml",
    ),
    ("Pick packages interactively, then build", COMMAND + " --menu"),
    (
        "Build with clang on 8 cores, including GPL and non-free components",
        COMMAND + " --build --clang --jobs 8 --enable-gpl-and-non-free",
    ),
    (
        "Update outdated dependencies to their newest upstream releases",
        COMMAND + " --build --latest --config ./custom.toml",
    ),
    (
        "Never install or modify CUDA packages",
        "CUDA_INSTALL=never " + COMMAND + " --build --config ./custom.toml",
    ),
    ("Start over with an empty workspace", COMMAND + " --cleanup"),
)
FOOTER = "Build log: $BUILD_ROOT/build.log    Full guide: README.md"

# Options that take a separate argument. Every walk over the command line skips
# that argument and stops at `--`, so an option's value is never mistaken for an
# option: `--compiler -h` means a compiler named '-h', not a request for help.
TAKES_VALUE = frozenset(["--compiler", "--config", "-j", "--jobs"])

# Line kinds. BODY lines are colored token by token; the others as a whole.
TITLE, HEADING, BODY, COMMENT = "title", "heading", "body", "comment"

_BOLD = "1"
_STYLES = {
    "title": "1;32",
    "heading": "1;33",
    "flag": "1;36",
    "variable": "1;36",
    "placeholder": "35",
    "default": "2",
    "comment": "2",
}
# Flags need a non-word character before the dash so hyphenated words such as
# "non-free" and "build-ffmpeg.py" stay plain.
_DEFAULT = re.compile(r"\(default: [^)]*\)")
# textwrap breaks only on ASCII whitespace, so this joins words it must not split.
_GLUE = "\x00"
_TOKENS = re.compile(
    r"(?P<placeholder><[^>\s]+>)"
    r"|(?P<default>" + _DEFAULT.pattern + r")"
    r"|(?P<flag>(?<![\w./-])--?[A-Za-z][A-Za-z0-9-]*)"
    r"|(?P<variable>\$?\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b)"
)


def color_enabled(stream: TextIO) -> bool:
    """Decide whether `stream` gets ANSI color; the build log applies the same policy."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM", "dumb") == "dumb":
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _sgr(code: str, text: str) -> str:
    return "\033[" + code + "m" + text + "\033[0m"


def _paint_tokens(text: str) -> str:
    return _TOKENS.sub(
        lambda match: _sgr(_STYLES[str(match.lastgroup)], match.group(0)),
        text,
    )


def _paint(kind: str, text: str) -> str:
    if not text.strip():
        return text
    if kind == TITLE:
        name, _, version = text.rpartition(" ")
        return _sgr(_STYLES["title"], name) + " " + _sgr(_BOLD, version)
    if kind == BODY:
        return _paint_tokens(text)
    indent = text[: len(text) - len(text.lstrip())]
    return indent + _sgr(_STYLES[kind], text.lstrip())


def _wrap(text: str, indent: str) -> list[str]:
    # A "(default: ...)" note moves to the next line whole rather than
    # splitting, so it reads as one unit and stays one colored token.
    glued = _DEFAULT.sub(lambda match: match.group(0).replace(" ", _GLUE), text)
    lines = textwrap.wrap(
        glued,
        WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [line.replace(_GLUE, " ") for line in lines]


def _rows(entries: tuple[tuple[str, str], ...]) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for label, description in entries:
        wrapped = _wrap(description, " " * DESCRIPTION_COLUMN)
        head = (INDENT + label).ljust(DESCRIPTION_COLUMN) + wrapped[0].lstrip()
        lines.append((BODY, head))
        lines.extend((BODY, line) for line in wrapped[1:])
    return lines


def _section(title: str, body: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(BODY, ""), (HEADING, title)] + body


def help_lines() -> list[tuple[str, str]]:
    """The help screen as (kind, plain text) pairs."""
    examples: list[tuple[str, str]] = []
    for comment, command in EXAMPLES:
        if examples:
            examples.append((BODY, ""))
        examples += [(COMMENT, INDENT + "# " + comment), (BODY, INDENT + command)]
    return (
        [(BODY, ""), (TITLE, "FFmpeg Build Script " + SCRIPT_VERSION), (BODY, "")]
        + [(BODY, "Usage: " + COMMAND + " <action> [options]"), (BODY, "")]
        + [(BODY, line) for line in _wrap(SUMMARY, INDENT)]
        + _section("Actions:", _rows(ACTIONS))
        + _section("Build options:", _rows(BUILD_OPTIONS))
        + _section("General options:", _rows(GENERAL_OPTIONS))
        + [(BODY, "")]
        + [(BODY, line) for line in _wrap(VALUE_NOTE, INDENT)]
        + _section("Environment variables:", _rows(ENVIRONMENT))
        + _section("Examples:", examples)
        + [(BODY, ""), (BODY, FOOTER), (BODY, "")]
    )


def usage_text(color: bool = False) -> str:
    return "".join((_paint(kind, text) if color else text) + "\n" for kind, text in help_lines())


def metadata_response(argv: list[str], color: bool = False) -> str | None:
    """Answer `--help`/`--version`, or return None when neither was requested.

    This walk runs before the interpreter is resolved, so on that path it is
    the only thing standing between `-- -h` and a help screen.
    """
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            return None
        if argument in ("-h", "--help"):
            return usage_text(color)
        if argument in ("-v", "--version"):
            return SCRIPT_VERSION + "\n"
        if argument in TAKES_VALUE:
            index += 1
        index += 1
    return None
