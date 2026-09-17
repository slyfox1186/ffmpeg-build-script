from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from ffmpeg_build.runtime import shellquote
from ffmpeg_build.runtime.logging import BACKGROUND, Logger

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# The palette every assertion below pins, as truecolor escapes.
TIMESTAMP = "\x1b[38;2;74;82;98m"
STEP = "\x1b[38;2;122;162;247m"
PACKAGE = "\x1b[38;2;230;237;245m"
VERSION = "\x1b[38;2;109;122;140m"
INFO = "\x1b[38;2;79;109;127m"
RUN = "\x1b[38;2;73;81;95m"
BINARY = "\x1b[38;2;152;167;184m"
FLAG = "\x1b[38;2;91;100;114m"
VALUE = "\x1b[38;2;117;128;143m"
URL = "\x1b[38;2;95;135;160m"
OK = "\x1b[38;2;63;185;132m"
OK_PACKAGE = "\x1b[38;2;195;206;219m"
DURATION = "\x1b[38;2;92;102;117m"
WARNING = "\x1b[38;2;211;160;74m"
ERROR = "\x1b[38;2;240;97;110m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Terminal:
    stream = Terminal()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.delenv("NO_COLOR", raising=False)
    return stream


def logger_for(terminal: Terminal) -> Logger:
    """Bind a logger to `terminal`.

    Pytest rebinds `sys.stdout` between the setup and call phases, so the swap
    only holds when it happens inside the test body.
    """
    original = sys.stdout
    sys.stdout = terminal
    try:
        return Logger()
    finally:
        sys.stdout = original


def test_package_records_paint_name_version_and_duration(terminal: Terminal) -> None:
    logger = logger_for(terminal)
    logger.package_start("libfdk-aac", "2.0.3")
    logger.package_done("libfdk-aac", "2.0.3", "8s")
    step, done = terminal.getvalue().splitlines()[1:3]
    assert step == (
        f"{RESET}{TIMESTAMP}[00:00:00]{RESET} {RESET}{BOLD}{STEP}STEP {RESET} "
        f"{RESET}{BOLD}{PACKAGE}libfdk-aac{RESET} {RESET}{VERSION}2.0.3{RESET}"
    )
    assert done.startswith(
        f"{RESET}{TIMESTAMP}[00:00:00]{RESET} {RESET}{BOLD}{OK}OK   {RESET} "
        f"{RESET}{BOLD}{OK_PACKAGE}libfdk-aac{RESET} {RESET}{VERSION}2.0.3{RESET}"
    )
    assert done.endswith(f"{RESET}{DURATION}in 8s{RESET}")
    assert ANSI.sub("", done).rstrip().endswith("in 8s")


def test_command_words_are_painted_by_role(terminal: Terminal) -> None:
    arguments = ["curl", "--silent", "https://example.test/a.tar.gz", "/tmp/a.tar.gz"]
    logger_for(terminal).run("", arguments=arguments)
    output = terminal.getvalue()
    assert f"{RESET}{BINARY}curl{RESET}" in output
    assert f"{RESET}{FLAG}--silent{RESET}" in output
    assert f"{RESET}{URL}https://example.test/a.tar.gz{RESET}" in output
    assert f"{RESET}{VALUE}/tmp/a.tar.gz{RESET}" in output
    assert ANSI.sub("", output) == f"[00:00:00] RUN   {shellquote.join(arguments)}\n"


def test_message_urls_are_painted_inside_info_records(terminal: Terminal) -> None:
    logger_for(terminal).get("https://example.test/a.tar.gz", "a.tar.gz")
    output = terminal.getvalue()
    assert f"{RESET}{INFO}INFO {RESET}" in output
    assert f"{RESET}{URL}https://example.test/a.tar.gz{RESET}" in output
    assert f"{RESET}{VALUE}Downloading{RESET}" in output
    assert (
        ANSI.sub("", output)
        == "[00:00:00] INFO  Downloading https://example.test/a.tar.gz as 'a.tar.gz'.\n"
    )


@pytest.mark.parametrize(
    "level,color,bold",
    [
        ("INFO", INFO, False),
        ("RUN", RUN, False),
        ("SKIP", INFO, False),
        ("TIME", RUN, False),
        ("WARN", WARNING, True),
        ("ERROR", ERROR, True),
    ],
)
def test_every_tag_keeps_its_own_color(
    monkeypatch: pytest.MonkeyPatch, terminal: Terminal, level: str, color: str, bold: bool
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger = logger_for(terminal)
    target = stream if level in ("WARN", "ERROR") else terminal
    logger.line(level, "message", stream=stream if level in ("WARN", "ERROR") else None)
    weight = BOLD if bold else ""
    assert f"{RESET}{weight}{color}{level:<5}{RESET}" in target.getvalue()


def test_failure_names_the_package_in_red(
    monkeypatch: pytest.MonkeyPatch, terminal: Terminal
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger_for(terminal).package_failed("libmysofa", "1.3.5", "cmake: could not find zlib >= 1.2.9")
    output = stream.getvalue()
    assert f"{RESET}{BOLD}{ERROR}FAIL {RESET}" in output
    assert f"{RESET}{BOLD}{ERROR}libmysofa 1.3.5{RESET}" in output
    assert (
        ANSI.sub("", output)
        == "[00:00:00] FAIL  libmysofa 1.3.5 cmake: could not find zlib >= 1.2.9\n"
    )


def test_wrapped_records_hang_under_the_text_column(terminal: Terminal) -> None:
    logger_for(terminal).info("Build root: " + "x" * 200)
    lines = ANSI.sub("", terminal.getvalue()).splitlines()
    assert lines[0] == "[00:00:00] INFO  Build root:"
    assert all(len(line) <= 120 for line in lines)
    assert all(line.startswith(" " * 17) and line[17] != " " for line in lines[1:])


def test_multi_line_records_keep_their_own_spacing(terminal: Terminal) -> None:
    logger_for(terminal).info("NVIDIA: NVIDIA GPU detected\nAMD:    AMD GPU detected")
    assert ANSI.sub("", terminal.getvalue()) == (
        "[00:00:00] INFO  NVIDIA: NVIDIA GPU detected\n                 AMD:    AMD GPU detected\n"
    )


def test_plain_log_file_and_redirected_output_carry_no_escapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    logger = Logger()
    logger.log_file = tmp_path / "build.log"
    logger.log_file.touch()
    logger.package_done("zenlib", "0.4.41", "6s")
    logger.run("", arguments=["make", "-j24"])
    assert "\x1b" not in stream.getvalue()
    assert "\x1b" not in logger.log_file.read_text()
    assert logger.log_file.read_text().endswith("RUN   make -j24\n")


@pytest.mark.parametrize("color", [True, False])
def test_background_is_forced_and_restored_only_with_color(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch, color: bool
) -> None:
    if not color:
        monkeypatch.setenv("NO_COLOR", "1")
    logger = logger_for(terminal)
    logger.force_background()
    logger.restore_background()
    expected = f"\033]11;{BACKGROUND}\033\\\033]111\033\\" if color else ""
    assert terminal.getvalue() == expected
