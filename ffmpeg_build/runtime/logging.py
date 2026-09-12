"""Terminal and build-log output.

Every structured log line goes through `line`, so the terminal and the
build log cannot drift. The terminal gets elapsed time, which is the useful
clock while watching a long build; the log file additionally gets a wall-clock
stamp so it can be lined up with system logs after the fact.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import shellquote

# Width of "[HH:MM:SS] LEVEL ", used to indent continuation lines so a wrapped
# or multi-line message stays in one visual column.
LOG_PREFIX_WIDTH = 17

_PACKAGE_VERSION = re.compile(
    r"(?<!\S)(?:[nRv]?[0-9]+(?:\.[0-9]+)*(?:[+.-][A-Za-z0-9.-]+)?|[0-9a-fA-F]{12,64})(?=[\s)]|$)"
)


def _color_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "dumb") == "dumb":
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


class Palette:
    """Bright text and a small status palette for a dark build terminal.

    Color describes the kind of record, never the syntax of its arguments.
    Extended terminals get consistent colors; basic terminals use ANSI colors.
    """

    __slots__ = ("text", "muted", "accent", "success", "warning", "error", "bold", "nc")

    def __init__(self, enabled: bool) -> None:
        extended = "256color" in os.environ.get("TERM", "") or os.environ.get("COLORTERM", "") in (
            "truecolor",
            "24bit",
        )

        def color(index: int, basic: int) -> str:
            if not enabled:
                return ""
            return f"\033[38;5;{index}m" if extended else f"\033[{basic}m"

        self.text = color(255, 97)
        self.muted = color(246, 90)
        self.accent = color(75, 94)
        self.success = color(78, 92)
        self.warning = color(221, 93)
        self.error = color(204, 91)
        self.bold = "\033[1m" if enabled else ""
        self.nc = "\033[0m" if enabled else ""


# Status colors stay in one column. Package versions share one yellow accent;
# command arguments and other message text keep a uniform white foreground.
_TAG_STYLE = {
    "STEP": ("bold", "accent"),
    "OK": ("success",),
    "INFO": ("accent",),
    "RUN": ("muted",),
    "SKIP": ("muted",),
    "TIME": ("muted",),
    "DEBUG": ("muted",),
    "WARN": ("bold", "warning"),
    "ERROR": ("bold", "error"),
}


def format_elapsed(total: int) -> str:
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def format_duration(total: int) -> str:
    """Durations read better at the scale they occur."""
    if total >= 3600:
        return f"{total // 3600}h{total % 3600 // 60:02d}m"
    if total >= 60:
        return f"{total // 60}m{total % 60:02d}s"
    return f"{total}s"


class Logger:
    """Formats and duplicates every build message."""

    def __init__(self, *, debug: bool = False) -> None:
        self.debug_enabled = debug
        self.log_file: Path | None = None
        self._started = time.monotonic()
        self._out = sys.stdout
        self._err = sys.stderr
        self.out_palette = Palette(_color_enabled(sys.stdout))
        self.err_palette = Palette(_color_enabled(sys.stderr))

    @property
    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started)

    def _styles(self, palette: Palette, names: tuple[str, ...]) -> str:
        # Every run starts with `nc` because these are concatenated after an
        # arbitrary preceding style: an attribute like bold or dim adds to what
        # is already set rather than replacing it, so without the reset a
        # colored value would bleed into the rest of the line.
        return palette.nc + "".join(getattr(palette, name) for name in names)

    def line(
        self,
        level: str,
        message: str,
        *,
        stream: TextIO | None = None,
        command_arguments: Sequence[str] | None = None,
    ) -> None:
        target = stream if stream is not None else self._out
        palette = self.err_palette if target is self._err else self.out_palette
        tag = self._styles(palette, _TAG_STYLE[level])
        elapsed = format_elapsed(self.elapsed_seconds)
        indent = " " * LOG_PREFIX_WIDTH
        body = palette.text + (palette.bold if level == "STEP" else "")

        if level == "RUN" and command_arguments is not None:
            message = shellquote.join(list(command_arguments))
        # A trailing newline must not produce a phantom final record.
        message_lines = message.splitlines() or [""]
        for index, text in enumerate(message_lines):
            if index == 0:
                if level in ("STEP", "OK", "SKIP"):
                    text = _PACKAGE_VERSION.sub(
                        lambda match: f"{palette.warning}{match[0]}{body}", text
                    )
                prefix = f"{palette.nc}{palette.muted}[{elapsed}]{palette.nc} {tag}{level:<5}{palette.nc} "
                print(f"{prefix}{body}{text}{palette.nc}", file=target, flush=True)
            else:
                print(
                    f"{indent}{palette.nc}{palette.text}{text}{palette.nc}", file=target, flush=True
                )

        self.write_log_records(level, message_lines, elapsed)

    def write_log_records(self, level: str, lines: list[str], elapsed: str) -> None:
        if self.log_file is None or not self.log_file.is_file():
            return
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self.log_file.open("a", encoding="utf-8") as handle:
                for text in lines:
                    handle.write(f"{stamp} [{elapsed}] {level:<5} {text}\n")
        except OSError:
            # A log that cannot be written must not take the build down; the
            # terminal copy of every record has already been printed.
            pass

    def info(self, message: str) -> None:
        self.line("INFO", message)

    def step(self, message: str) -> None:
        """A stage or package heading, bold enough to find in a long scroll."""
        self.line("STEP", message)

    def ok(self, message: str) -> None:
        self.line("OK", message)

    def skip(self, message: str) -> None:
        self.line("SKIP", message)

    def run(self, message: str, *, arguments: Sequence[str] | None = None) -> None:
        self.line("RUN", message, command_arguments=arguments)

    def time(self, message: str) -> None:
        self.line("TIME", message)

    def debug(self, message: str) -> None:
        """Detail worth having in a bug report that would bury a normal run."""
        if self.debug_enabled:
            self.line("DEBUG", message)

    def warn(self, message: str) -> None:
        """Diagnostics go to stderr on purpose.

        Several helpers are consumed for their return value while a caller
        redirects stdout; a warning there would corrupt the captured result.
        """
        self.line("WARN", message, stream=self._err)

    def error(self, message: str) -> None:
        self.line("ERROR", message, stream=self._err)

    def banner(self, text: str) -> None:
        """A compact section heading using the same accent as package steps."""
        palette = self.out_palette
        print(
            f"{palette.nc}{palette.accent}──{palette.nc} "
            f"{palette.bold}{palette.text}{text}{palette.nc} {palette.accent}──{palette.nc}",
            file=self._out,
            flush=True,
        )
