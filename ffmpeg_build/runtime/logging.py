"""Terminal and build-log output.

Every line the build prints goes through `log_line`, so the terminal and the
build log cannot drift. The terminal gets elapsed time, which is the useful
clock while watching a long build; the log file additionally gets a wall-clock
stamp so it can be lined up with system logs after the fact.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import TextIO

# Width of "[HH:MM:SS] LEVEL ", used to indent continuation lines so a wrapped
# or multi-line message stays in one visual column.
LOG_PREFIX_WIDTH = 17


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
    """ANSI attributes, or empty strings when color is suppressed.

    The colors set a foreground and nothing else: the common "0;3xm" spelling
    leads with a reset, which silently cancels any attribute it is combined
    with, so BOLD+GREEN renders as plain green. Callers that need a clean slate
    say `nc` explicitly instead.
    """

    __slots__ = ("green", "red", "yellow", "magenta", "cyan", "bold", "dim", "nc")

    def __init__(self, enabled: bool) -> None:
        self.green = "\033[32m" if enabled else ""
        self.red = "\033[31m" if enabled else ""
        self.yellow = "\033[33m" if enabled else ""
        self.magenta = "\033[35m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.dim = "\033[2m" if enabled else ""
        self.nc = "\033[0m" if enabled else ""


# Each level paints three separate things, because they answer three different
# questions: the tag says what kind of line this is, the body tint says how much
# attention it deserves, and the subject color marks the one token worth finding
# when the line is skimmed rather than read.
#
# The hue map is deliberately small enough to state in a sentence: green is
# forward progress, cyan is information and the values inside it, magenta is a
# command or internal machinery, yellow and red are trouble, and dim is
# de-emphasis. Nothing else gets a color, so a color always means something.
_TAG_STYLE = {
    "STEP": ("bold", "green"),
    "OK": ("green",),
    "INFO": ("cyan",),
    "RUN": ("magenta",),
    "SKIP": ("dim", "cyan"),
    "TIME": ("dim",),
    "DEBUG": ("dim", "magenta"),
    "WARN": ("bold", "yellow"),
    "ERROR": ("bold", "red"),
}
_BODY_STYLE = {
    "STEP": ("bold",),
    "OK": ("green",),
    "INFO": (),
    "RUN": ("dim",),
    "SKIP": ("dim",),
    "TIME": ("dim",),
    "DEBUG": ("dim",),
    "WARN": ("yellow",),
    "ERROR": ("red",),
}
_SUBJECT_STYLE = {
    "STEP": ("bold", "cyan"),
    "OK": ("bold", "green"),
    "INFO": ("cyan",),
    "RUN": ("bold",),
    "SKIP": ("cyan",),
    "TIME": ("dim",),
    "DEBUG": ("magenta",),
    "WARN": ("bold", "yellow"),
    "ERROR": ("bold", "red"),
}

# Levels whose message leads with its own subject: a package name for STEP, OK
# and SKIP, a program name for RUN. Coloring that leading token puts the
# identity of every line in one column, so a long scroll can be read down the
# left edge without parsing the prose beside it.
_SUBJECT_IS_LEADING = frozenset({"STEP", "OK", "RUN", "SKIP"})


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

    def _colorize_subject(self, text: str, body: str, subject: str, nc: str) -> str:
        head, separator, tail = text.partition(" ")
        remainder = f"{separator}{tail}" if separator else ""
        return f"{subject}{head}{body}{remainder}{nc}"

    def _colorize_values(self, text: str, body: str, value: str, nc: str) -> str:
        """Lift quoted payloads out of the surrounding prose.

        Quotes are consumed in pairs and an unpaired one ends the scan, so an
        apostrophe in prose recolors nothing after it.
        """
        rendered: list[str] = []
        remaining = text
        while True:
            prose, quote, after = remaining.partition("'")
            if not quote:
                break
            inner, closing, rest = after.partition("'")
            if not closing:
                break
            rendered.append(f"{prose}{value}'{inner}'{body}")
            remaining = rest
        return f"{body}{''.join(rendered)}{remaining}{nc}"

    def line(self, level: str, message: str, *, stream: TextIO | None = None) -> None:
        target = stream if stream is not None else self._out
        palette = self.err_palette if target is self._err else self.out_palette
        tag = self._styles(palette, _TAG_STYLE[level])
        body = self._styles(palette, _BODY_STYLE[level])
        subject = self._styles(palette, _SUBJECT_STYLE[level])
        elapsed = format_elapsed(self.elapsed_seconds)
        indent = " " * LOG_PREFIX_WIDTH

        # splitlines(), never split("\n"): a trailing newline must not produce a
        # phantom final record.
        message_lines = message.splitlines() or [""]
        for index, text in enumerate(message_lines):
            # Only the first line of a record carries the subject; a
            # continuation line is prose or a list item, so it takes the value
            # treatment.
            if index == 0 and level in _SUBJECT_IS_LEADING:
                rendered = self._colorize_subject(text, body, subject, palette.nc)
            else:
                rendered = self._colorize_values(text, body, subject, palette.nc)
            if index == 0:
                prefix = f"{palette.dim}[{elapsed}]{palette.nc} {tag}{level:<5}{palette.nc} "
                print(f"{prefix}{rendered}", file=target, flush=True)
            else:
                print(f"{indent}{rendered}", file=target, flush=True)

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

    def run(self, message: str) -> None:
        self.line("RUN", message)

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
        """Stage heading.

        The box is structure rather than content, so it is dimmed and only the
        title carries a color; drawing it from the same palette as every log
        line is what keeps a stage heading recognizably part of the same output.
        """
        palette = self.out_palette
        inner = len(text) + 2
        border = "-" * inner
        blank = " " * inner
        print(f"{palette.dim} {border}{palette.nc}")
        print(f"{palette.dim}|{blank}|{palette.nc}")
        print(
            f"{palette.dim}|{palette.nc} {palette.bold}{palette.cyan}{text}"
            f"{palette.nc} {palette.dim}|{palette.nc}"
        )
        print(f"{palette.dim}|{blank}|{palette.nc}")
        print(f"{palette.dim} {border}{palette.nc}", flush=True)
