"""Terminal and build-log output.

Every structured record goes through `_emit` and `_record`, so the terminal
and the build log cannot drift. The terminal reads like a shell session: each
package opens with an underlined heading, commands echo after `$`, and short
bracketed tags mark everything else. The log file carries the timeline
instead, a wall-clock and elapsed stamp on every record.

    Building libfdk-aac - version 2.0.3
    ===================================
    [INFO] Downloading https://example.test/fdk-aac-2.0.3.tar.gz as 'fdk-aac-2.0.3.tar.gz'.
    $ make -j24
    [DONE] libfdk-aac 2.0.3 built in 8s

Colors are the standard ANSI set so they follow the terminal's own theme.
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

# Wrapped command arguments hang this far in, clear of the `$ ` prompt, so a
# continuation never reads as a new command.
COMMAND_INDENT = 4
MIN_WRAP_WIDTH = 20

# Terminal tag per record level. The log file keeps the level names.
_TAGS = {
    "STEP": "[STEP]",
    "OK": "[DONE]",
    "INFO": "[INFO]",
    "SKIP": "[SKIP]",
    "TIME": "[TIME]",
    "DEBUG": "[DEBUG]",
    "WARN": "[WARNING]",
    "FAIL": "[FAILED]",
    "ERROR": "[ERROR]",
    "PROMPT": "[PROMPT]",
}
_TAG_COLOR = {
    "STEP": "blue",
    "OK": "green",
    "INFO": "green",
    "SKIP": "cyan",
    "TIME": "dim",
    "DEBUG": "dim",
    "WARN": "yellow",
    "FAIL": "red",
    "ERROR": "red",
    "PROMPT": "magenta",
}
_BOLD_TAGS = ("OK", "WARN", "FAIL", "ERROR", "PROMPT")
_URL = re.compile(r"(https?://[^\s'\"]+)")


def _is_terminal(stream: TextIO) -> bool:
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _color_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM", "dumb") == "dumb":
        return False
    return _is_terminal(stream)


class Palette:
    """ANSI styles for one stream; every style is empty when color is off."""

    __slots__ = (
        "enabled",
        "green",
        "yellow",
        "red",
        "cyan",
        "blue",
        "magenta",
        "dim",
        "bold",
        "nc",
    )

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

        def sgr(code: str) -> str:
            return f"\033[{code}m" if enabled else ""

        self.green = sgr("32")
        self.yellow = sgr("33")
        self.red = sgr("31")
        self.cyan = sgr("36")
        self.blue = sgr("34")
        self.magenta = sgr("35")
        self.dim = sgr("2")
        self.bold = sgr("1")
        self.nc = sgr("0")

    def paint(self, style: str, text: str, *, bold: bool = False) -> str:
        if not self.enabled or not text or not (style or bold):
            return text
        return f"{self.bold if bold else ''}{style}{text}{self.nc}"


def format_elapsed(total: int) -> str:
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def format_duration(total: int) -> str:
    """Durations read better at the scale they occur."""
    if total >= 3600:
        return f"{total // 3600}h{total % 3600 // 60:02d}m"
    if total >= 60:
        return f"{total // 60}m{total % 60:02d}s"
    return f"{total}s"


# A fragment is (text, style name, bold); style names index the Palette.
# Fragments render back to back; `_spaced` puts a separator between words.
Fragment = tuple[str, str, bool]
# The separator `_spaced` inserts. Wrapping prefers these breaks, so a command
# folds between arguments rather than inside a quoted one.
_SEPARATOR: Fragment = (" ", "separator", False)


def _spaced(words: Sequence[Fragment]) -> list[Fragment]:
    parts: list[Fragment] = []
    for word in words:
        if parts:
            parts.append(_SEPARATOR)
        parts.append(word)
    return parts


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
        # Both streams share one screen, so one flag tracks whether the last
        # visible line was blank; separators never stack into double gaps.
        self._after_blank = True
        # Text column of the last tagged record, so a follow-up hint lines up.
        self._text_column = len(_TAGS["INFO"]) + 1

    @property
    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started)

    # -- rendering --------------------------------------------------------

    def _blank(self) -> None:
        if not self._after_blank:
            print(file=self._out, flush=True)
            self._after_blank = True

    def _width(self, stream: TextIO) -> int | None:
        """Wrap only on a terminal; redirected output keeps one record per line."""
        if not _is_terminal(stream):
            return None
        return shutil.get_terminal_size((80, 24)).columns

    @staticmethod
    def _wrap(parts: list[Fragment], available: int | None) -> list[list[Fragment]]:
        """Fold fragments into lines of at most `available` columns.

        Breaks at a word separator when one fits, then at any space, and only
        then mid-word. The space a line breaks at is dropped; every other
        space, including alignment padding, is kept.
        """
        text = "".join(fragment[0] for fragment in parts)
        if available is None or len(text) <= available:
            return [parts]
        separators: set[int] = set()
        position = 0
        for fragment in parts:
            if fragment is _SEPARATOR:
                separators.add(position)
            position += len(fragment[0])

        ranges: list[tuple[int, int]] = []
        start = 0
        while len(text) - start > available:
            limit = start + available
            cut = max((index for index in separators if start < index <= limit), default=-1)
            if cut < 0:
                cut = text.rfind(" ", start + 1, limit + 1)
            if cut < 0:
                ranges.append((start, limit))
                start = limit
                continue
            ranges.append((start, cut))
            start = cut + 1
        ranges.append((start, len(text)))

        lines: list[list[Fragment]] = []
        for low, high in ranges:
            line: list[Fragment] = []
            position = 0
            for fragment_text, style, bold in parts:
                end = position + len(fragment_text)
                if position < high and end > low:
                    piece = fragment_text[max(low, position) - position : min(high, end) - position]
                    line.append((piece, style, bold))
                position = end
            lines.append(line)
        return lines

    def _emit(
        self,
        lead: Fragment | None,
        parts: list[Fragment],
        *,
        stream: TextIO | None = None,
        indent: int | None = None,
    ) -> None:
        """Print one record: an optional lead such as a tag, then wrapped parts.

        Continuation lines hang at `indent`, by default under the first word
        after the lead. Without a lead every line starts at `indent`.
        """
        target = stream if stream is not None else self._out
        palette = self.err_palette if target is self._err else self.out_palette
        lead_width = len(lead[0]) + 1 if lead is not None else 0
        hang = lead_width if indent is None else indent
        width = self._width(target)
        available = None if width is None else max(width - max(hang, lead_width), MIN_WRAP_WIDTH)

        for index, line in enumerate(self._wrap(parts, available)):
            if index == 0 and lead is not None:
                text, style, bold = lead
                rendered = palette.paint(getattr(palette, style, ""), text, bold=bold) + " "
            else:
                rendered = " " * hang
            rendered += "".join(
                palette.paint(getattr(palette, style, ""), text, bold=bold)
                for text, style, bold in line
            )
            print(rendered, file=target, flush=True)
        self._after_blank = False
        if lead is not None:
            self._text_column = lead_width

    def _tag(self, level: str) -> Fragment:
        return (_TAGS.get(level, f"[{level}]"), _TAG_COLOR.get(level, ""), level in _BOLD_TAGS)

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

    @staticmethod
    def _text_parts(message: str, style: str = "") -> list[Fragment]:
        """Split only around URLs, so a message's own spacing survives verbatim.

        Aligned records such as the hardware summary pad with runs of spaces,
        and a URL inside quotes stays against its quotes.
        """
        return [
            (fragment, "cyan" if index % 2 else style, False)
            for index, fragment in enumerate(_URL.split(message))
            if fragment
        ]

    def line(
        self,
        level: str,
        message: str,
        *,
        stream: TextIO | None = None,
        command_arguments: Sequence[str] | None = None,
    ) -> None:
        """Render one record and append it to the build log."""
        if level == "RUN":
            self._command(message, command_arguments, stream=stream)
            return
        for index, text in enumerate(message.splitlines() or [""]):
            if index == 0:
                self._emit(self._tag(level), self._text_parts(text), stream=stream)
            else:
                self._emit(
                    None,
                    self._text_parts(text),
                    stream=stream,
                    indent=len(self._tag(level)[0]) + 1,
                )
        self._record(level, message)

    def _command(
        self,
        message: str,
        arguments: Sequence[str] | None,
        *,
        stream: TextIO | None = None,
        quiet: bool = False,
    ) -> None:
        if arguments is not None:
            message = shellquote.join(list(arguments))
            words = [shellquote.quote(word) for word in arguments]
            raw = list(arguments)
        else:
            words = raw = message.split(" ")
        if not quiet or self.debug_enabled:
            parts: list[Fragment] = []
            for position, (word, shown) in enumerate(zip(raw, words, strict=True)):
                if word.startswith(("http://", "https://")):
                    parts.append((shown, "cyan", False))
                else:
                    parts.append((shown, "", position == 0))
            self._emit(("$", "dim", False), _spaced(parts), stream=stream, indent=COMMAND_INDENT)
        self._record("RUN", message)

    # -- package lifecycle ------------------------------------------------

    def package_start(self, key: str, version: str, replacing: str = "") -> None:
        heading: list[Fragment] = [
            ("Building", "green", False),
            (key, "yellow", True),
            ("- version", "green", False),
            (version, "yellow", False),
        ]
        extra = f"(replacing {replacing})" if replacing else ""
        if extra:
            heading.append((extra, "dim", False))
        plain = " ".join(text for text, _, _ in heading)
        self._blank()
        self._emit(None, _spaced(heading))
        width = self._width(self._out)
        self._emit(None, [("=" * min(len(plain), width or len(plain)), "", False)])
        self._record("STEP", f"{key} {version}" + (f" {extra}" if extra else ""))

    def package_done(self, key: str, version: str, duration: str = "") -> None:
        parts: list[Fragment] = [(key, "yellow", True), (version, "yellow", False)]
        if duration:
            parts.append((f"built in {duration}", "", False))
        self._emit(self._tag("OK"), _spaced(parts))
        self._blank()
        self._record("OK", f"{key} {version}" + (f" in {duration}" if duration else ""))

    def package_reused(
        self, key: str, version: str, note: str = "is already built.", record: str = ""
    ) -> None:
        self._emit(
            self._tag("SKIP"),
            _spaced([(key, "yellow", True), (version, "yellow", False), (note, "", False)]),
        )
        self._record("SKIP", record or f"{key} {version} {note}")

    def package_failed(self, key: str, version: str, reason: str) -> None:
        name = f"{key} {version}".strip()
        self._emit(
            self._tag("FAIL"),
            [(f"{name}:", "red", True), (" ", "", False), *self._text_parts(reason)],
            stream=self._err,
        )
        self._record("ERROR", f"{name} {reason}")

    def summary(self, built: int, reused: int, failed: int, elapsed: str) -> None:
        segments: list[Fragment] = [(f"{built} built", "green", True)]
        if reused:
            segments.append((f"{reused} already built", "", False))
        if failed:
            segments.append((f"{failed} failed", "red", True))
        counts: list[Fragment] = [("Packages:", "", False)]
        for position, (text, style, bold) in enumerate(segments):
            comma = "," if position < len(segments) - 1 else ""
            counts.append((text + comma, style, bold))
        self._emit(self._tag("INFO"), _spaced(counts))
        self._emit(self._tag("INFO"), _spaced([("Total time:", "", False), (elapsed, "", True)]))
        self._record("INFO", f"{built} built, {reused} reused, {failed} failed, {elapsed} elapsed")

    def farewell(self, url: str) -> None:
        """The closing lines of a successful run, after any cleanup prompt."""
        self._blank()
        self._emit(
            self._tag("INFO"),
            _spaced(
                [
                    ("Make sure to", "", False),
                    ("star", "yellow", True),
                    ("this repository to show your support!", "", False),
                ]
            ),
        )
        self._emit(self._tag("INFO"), self._text_parts(url))
        self._blank()
        self._record("INFO", f"Make sure to star this repository to show your support! {url}")

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
        self.line("STEP", message)

    def ok(self, message: str) -> None:
        self.line("OK", message)

    def skip(self, message: str) -> None:
        self.line("SKIP", message)

    def run(
        self, message: str, *, arguments: Sequence[str] | None = None, quiet: bool = False
    ) -> None:
        """Echo a command as `$ command`.

        A quiet command, such as the download transport already announced by
        its own record, reaches the terminal only with --debug; the log file
        records it either way.
        """
        self._command(message, arguments, quiet=quiet)

    def time(self, message: str, *, quiet: bool = False) -> None:
        if quiet and not self.debug_enabled:
            self._record("TIME", message)
            return
        self.line("TIME", message)

    def debug(self, message: str) -> None:
        """Detail worth having in a bug report that would bury a normal run."""
        if self.debug_enabled:
            self.line("DEBUG", message)

    def prompt(self, question: str) -> str:
        """Ask on the terminal under a `[PROMPT]` tag and record the answer.

        EOFError propagates so each caller keeps its own no-answer policy.
        """
        palette = self.out_palette
        text, style, bold = self._tag("PROMPT")
        self._blank()
        answer = input(f"{palette.paint(getattr(palette, style), text, bold=bold)} {question}")
        self._after_blank = False
        self._record("PROMPT", f"{question}{answer}")
        return answer

    def hint(self, message: str) -> None:
        """A dim follow-up under the previous record's text, such as a log location."""
        self._emit(None, [(message, "dim", False)], indent=self._text_column)
        self._record("INFO", message)

    def warn(self, message: str) -> None:
        """Diagnostics go to stderr on purpose.

        Several helpers are consumed for their return value while a caller
        redirects stdout; a warning there would corrupt the captured result.
        """
        self.line("WARN", message, stream=self._err)

    def error(self, message: str) -> None:
        lines = message.splitlines() or [""]
        tag = self._tag("ERROR")
        self._emit(tag, self._text_parts(lines[0], "red"), stream=self._err)
        for text in lines[1:]:
            self._emit(
                None, self._text_parts(text, "dim"), stream=self._err, indent=len(tag[0]) + 1
            )
        self._record("ERROR", message)

    def banner(self, text: str) -> None:
        """A boxed section heading that stands out in a long scroll."""
        palette = self.out_palette
        rule = "─" * (len(text) + 4)
        self._blank()
        print(palette.paint(palette.dim, f"┌{rule}┐"), file=self._out)
        print(
            palette.paint(palette.dim, "│  ")
            + palette.paint(palette.cyan, text, bold=True)
            + palette.paint(palette.dim, "  │"),
            file=self._out,
        )
        print(palette.paint(palette.dim, f"└{rule}┘"), file=self._out, flush=True)
        self._after_blank = False
        self._blank()
        self._record("INFO", text)
