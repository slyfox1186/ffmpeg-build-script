"""Terminal and build-log output.

Every structured record goes through `_emit`, so the terminal and the build log
cannot drift. The terminal gets elapsed time, which is the useful clock while
watching a long build; the log file additionally gets a wall-clock stamp so it
can be lined up with system logs after the fact.

Brightness tracks importance: package names and outcomes are bright, the wall
of command flags is dim, and red means failure and nothing else.

    [00:01:15] STEP  libfdk-aac 2.0.3
    [00:01:15] RUN   curl --fail --silent --output /path/to/archive.tar.gz
    [00:01:23] OK    libfdk-aac 2.0.3                                in 8s
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import shellquote

# Width of "[HH:MM:SS] LEVEL ", used to indent continuation lines so a wrapped
# or multi-line message stays in one visual column.
LOG_PREFIX_WIDTH = 17
TAG_WIDTH = 5
MAX_WIDTH = 120

# Background the palette was tuned against. Forced with OSC 11 so the ramp from
# bright package names to dim flags holds whatever theme the terminal starts in.
BACKGROUND = "#14161b"

_PACKAGE_VERSION = re.compile(
    r"(?<!\S)(?:[nRv]?[0-9]+(?:\.[0-9]+)*(?:[+.-][A-Za-z0-9.-]+)?|[0-9a-fA-F]{12,64})(?=[\s)]|$)"
)


def _color_enabled(stream: TextIO) -> bool:
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


def _to_256(red: int, green: int, blue: int) -> int:
    if abs(red - green) < 8 and abs(green - blue) < 8:
        return 232 + min(23, max(0, (red - 8) // 10))

    def level(value: int) -> int:
        if value < 48:
            return 0
        if value < 115:
            return 1
        return min(4, (value - 35) // 40) + 1

    return 16 + 36 * level(red) + 6 * level(green) + level(blue)


class Palette:
    """The build log's ramp, resolved once per stream.

    Color describes the role of a fragment, not the syntax of its arguments.
    Truecolor terminals get the exact values; the rest get the 256-color cube.
    """

    __slots__ = (
        "timestamp",
        "step",
        "package",
        "version",
        "info",
        "run",
        "binary",
        "flag",
        "value",
        "url",
        "ok",
        "ok_package",
        "duration",
        "warning",
        "error",
        "rail",
        "bold",
        "nc",
        "enabled",
    )

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        truecolor = os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")

        def color(value: str) -> str:
            if not enabled:
                return ""
            red, green, blue = (int(value[index : index + 2], 16) for index in (1, 3, 5))
            if truecolor:
                return f"\033[38;2;{red};{green};{blue}m"
            return f"\033[38;5;{_to_256(red, green, blue)}m"

        self.timestamp = color("#4a5262")
        self.step = color("#7aa2f7")
        self.package = color("#e6edf5")
        self.version = color("#6d7a8c")
        self.info = color("#4f6d7f")
        self.run = color("#49515f")
        self.binary = color("#98a7b8")
        self.flag = color("#5b6472")
        self.value = color("#75808f")
        self.url = color("#5f87a0")
        self.ok = color("#3fb984")
        self.ok_package = color("#c3cedb")
        self.duration = color("#5c6675")
        self.warning = color("#d3a04a")
        self.error = color("#f0616e")
        self.rail = color("#2b323f")
        self.bold = "\033[1m" if enabled else ""
        self.nc = "\033[0m" if enabled else ""

    def paint(self, color: str, text: str, *, bold: bool = False) -> str:
        if not self.enabled or not text:
            return text
        return f"{self.nc}{self.bold if bold else ''}{color}{text}{self.nc}"


# Each record's tag keeps one column and one color, so a scroll reads as a
# ladder of outcomes rather than a wall of equally loud lines.
_TAG_COLOR = {
    "STEP": "step",
    "OK": "ok",
    "INFO": "info",
    "RUN": "run",
    "SKIP": "info",
    "TIME": "run",
    "DEBUG": "run",
    "WARN": "warning",
    "FAIL": "error",
    "ERROR": "error",
}
_BOLD_TAGS = ("STEP", "OK", "WARN", "FAIL", "ERROR")


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
        self._background_set = False

    @property
    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started)

    # -- terminal ---------------------------------------------------------

    def force_background(self) -> None:
        """Set the terminal background the palette was tuned against."""
        if not self.out_palette.enabled or self._background_set:
            return
        self._out.write(f"\033]11;{BACKGROUND}\033\\")
        self._out.flush()
        self._background_set = True

    def restore_background(self) -> None:
        if not self._background_set:
            return
        self._background_set = False
        try:
            self._out.write("\033]111\033\\")
            self._out.flush()
        except (OSError, ValueError):
            pass

    def _width(self) -> int:
        return min(shutil.get_terminal_size((MAX_WIDTH, 40)).columns, MAX_WIDTH)

    # -- rendering --------------------------------------------------------

    def _wrap(self, parts: list[tuple[str, str]], available: int) -> list[list[tuple[str, str]]]:
        """Fold coloured fragments into lines, breaking at spaces where possible."""
        lines: list[list[tuple[str, str]]] = []
        current: list[tuple[str, str]] = []
        used = 0
        for text, color in parts:
            while len(text) > available:
                cut = text.rfind(" ", 0, available + 1)
                if cut <= 0:
                    cut = available
                    remainder = text[cut:]
                else:
                    remainder = text[cut + 1 :]
                if current:
                    lines.append(current)
                    current, used = [], 0
                lines.append([(text[:cut], color)])
                text = remainder
            if used and used + 1 + len(text) > available:
                lines.append(current)
                current, used = [(text, color)], len(text)
                continue
            if used:
                current.append((" ", ""))
                used += 1
            current.append((text, color))
            used += len(text)
        if current:
            lines.append(current)
        return lines or [[]]

    def _emit(
        self,
        level: str | None,
        parts: list[tuple[str, str]],
        *,
        stream: TextIO | None = None,
        bold_first: bool = False,
        right: str = "",
    ) -> None:
        target = stream if stream is not None else self._out
        palette = self.err_palette if target is self._err else self.out_palette
        width = self._width()
        elapsed = format_elapsed(self.elapsed_seconds)
        tag_color = getattr(palette, _TAG_COLOR.get(level or "", "info"))
        lines = self._wrap(parts, max(width - LOG_PREFIX_WIDTH, 20))

        for index, line in enumerate(lines):
            if index == 0 and level is not None:
                rendered = (
                    palette.paint(palette.timestamp, f"[{elapsed}]")
                    + " "
                    + palette.paint(tag_color, f"{level:<{TAG_WIDTH}}", bold=level in _BOLD_TAGS)
                    + " "
                )
            else:
                rendered = " " * LOG_PREFIX_WIDTH
            rendered += "".join(
                palette.paint(color, text, bold=bold_first and index == 0 and position == 0)
                if color
                else text
                for position, (text, color) in enumerate(line)
            )
            if right and index == len(lines) - 1:
                used = LOG_PREFIX_WIDTH + sum(len(text) for text, _ in line)
                if used + len(right) + 2 <= width:
                    rendered += " " * (width - used - len(right) - 1)
                    rendered += palette.paint(palette.duration, right)
            print(rendered, file=target, flush=True)

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

    def _record(self, level: str, message: str) -> None:
        self.write_log_records(
            level, message.splitlines() or [""], format_elapsed(self.elapsed_seconds)
        )

    def _text_parts(self, message: str, color: str) -> list[tuple[str, str]]:
        """Split only around URLs, so a message's own spacing survives verbatim.

        Aligned records such as the hardware summary pad with runs of spaces,
        and re-joining split words would collapse those columns.
        """
        parts: list[tuple[str, str]] = []
        for index, fragment in enumerate(re.split(r"(https?://[^\s'\"]+)", message)):
            # The renderer rejoins fragments with one space, so only the space
            # at a URL boundary is dropped; internal padding is untouched.
            fragment = fragment if index % 2 else fragment.strip(" ")
            if not fragment:
                continue
            parts.append((fragment, self.out_palette.url if index % 2 else color))
        return parts

    def line(
        self,
        level: str,
        message: str,
        *,
        stream: TextIO | None = None,
        command_arguments: Sequence[str] | None = None,
    ) -> None:
        """Render one record, colouring the fragments that carry meaning."""
        if level == "RUN" and command_arguments is not None:
            message = shellquote.join(list(command_arguments))
        palette = self.err_palette if stream is self._err else self.out_palette
        body = palette.value
        parts: list[tuple[str, str]] = []
        if level == "RUN":
            words = list(command_arguments) if command_arguments is not None else message.split(" ")
            for position, word in enumerate(words):
                shown = shellquote.quote(word) if command_arguments is not None else word
                if word.startswith(("http://", "https://")):
                    parts.append((shown, palette.url))
                elif position == 0:
                    parts.append((shown, palette.binary))
                elif word.startswith(("-", "+")):
                    parts.append((shown, palette.flag))
                else:
                    parts.append((shown, palette.value))
            self._emit(level, parts, stream=stream)
            self._record(level, message)
            return
        for index, text in enumerate(message.splitlines() or [""]):
            self._emit(level if index == 0 else None, self._text_parts(text, body), stream=stream)
        self._record(level, message)

    # -- package lifecycle ------------------------------------------------

    def _package_parts(
        self, key: str, version: str, name_color: str, extra: str = ""
    ) -> list[tuple[str, str]]:
        parts = [(key, name_color), (version, self.out_palette.version)]
        if extra:
            parts.append((extra, self.out_palette.version))
        return parts

    def package_start(self, key: str, version: str, replacing: str = "") -> None:
        print(file=self._out)
        extra = f"(replacing {replacing})" if replacing else ""
        self._emit(
            "STEP",
            self._package_parts(key, version, self.out_palette.package, extra),
            bold_first=True,
        )
        self._record("STEP", f"{key} {version}" + (f" {extra}" if extra else ""))

    def package_done(self, key: str, version: str, duration: str = "") -> None:
        self._emit(
            "OK",
            self._package_parts(key, version, self.out_palette.ok_package),
            bold_first=True,
            right=f"in {duration}" if duration else "",
        )
        self._record("OK", f"{key} {version}" + (f" in {duration}" if duration else ""))

    def package_reused(
        self, key: str, version: str, note: str = "is already built.", record: str = ""
    ) -> None:
        self._emit(
            "SKIP",
            self._package_parts(key, version, self.out_palette.ok_package)
            + [(note, self.out_palette.value)],
            bold_first=True,
        )
        self._record("SKIP", record or f"{key} {version} {note}")

    def package_failed(self, key: str, version: str, reason: str) -> None:
        parts: list[tuple[str, str]] = [(f"{key} {version}", self.err_palette.error)]
        parts += self._text_parts(reason, self.err_palette.value)
        self._emit("FAIL", parts, stream=self._err, bold_first=True)
        self._record("ERROR", f"{key} {version} {reason}")

    def summary(self, built: int, reused: int, failed: int, elapsed: str) -> None:
        palette = self.out_palette
        segments = [(f"{built} built", palette.ok)]
        if reused:
            segments.append((f"{reused} reused", palette.value))
        if failed:
            segments.append((f"{failed} failed", palette.error))
        segments.append((f"{elapsed} elapsed", palette.timestamp))
        parts: list[tuple[str, str]] = []
        for position, (text, color) in enumerate(segments):
            if position:
                parts.append(("·", palette.timestamp))
            parts.append((text, color))
        self._emit("OK", parts, bold_first=True)
        self._record("INFO", f"{built} built, {reused} reused, {failed} failed, {elapsed} elapsed")

    # -- records ----------------------------------------------------------

    def info(self, message: str) -> None:
        self.line("INFO", message)

    def get(self, url: str, filename: str = "", note: str = "") -> None:
        if note:
            self.line("INFO", f"{url} {note}.")
        elif filename:
            self.line("INFO", f"Downloading {url} as '{filename}'.")
        else:
            self.line("INFO", f"Downloading {url}.")

    def extracted(self, name: str) -> None:
        self.line("INFO", f"File extracted: '{name}'.")

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

    def hint(self, message: str) -> None:
        """A dim follow-up under a record, such as a log location."""
        self._emit("", [(message, self.out_palette.timestamp)])
        self._record("INFO", message)

    def warn(self, message: str) -> None:
        """Diagnostics go to stderr on purpose.

        Several helpers are consumed for their return value while a caller
        redirects stdout; a warning there would corrupt the captured result.
        """
        self.line("WARN", message, stream=self._err)

    def error(self, message: str) -> None:
        lines = message.splitlines() or [""]
        self._emit("ERROR", self._text_parts(lines[0], self.err_palette.error), stream=self._err)
        for text in lines[1:]:
            self._emit(None, self._text_parts(text, self.err_palette.timestamp), stream=self._err)
        self._record("ERROR", message)

    def banner(self, text: str) -> None:
        """A compact section heading, dim rules around a bright title."""
        palette = self.out_palette
        rule = palette.paint(palette.rail, "──")
        print(f"{rule} {palette.paint(palette.package, text, bold=True)} {rule}", file=self._out)
        self._record("INFO", text)
