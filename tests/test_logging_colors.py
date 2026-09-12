from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

from ffmpeg_build.runtime import shellquote
from ffmpeg_build.runtime.logging import Logger

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.mark.parametrize("color", [True, False])
def test_build_colors_preserve_plain_log_and_quoted_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, color: bool
) -> None:
    terminal = Terminal()
    monkeypatch.setattr("sys.stdout", terminal)
    monkeypatch.setenv("TERM", "xterm-256color")
    if color:
        monkeypatch.delenv("NO_COLOR")
    logger = Logger()
    logger.log_file = tmp_path / "build.log"
    logger.log_file.touch()
    logger.step("zenlib 0.4.41")
    logger.ok("mediainfo-lib 26.05 in 6s")
    arguments = [
        "cmake",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        "-DCMAKE_INSTALL_PREFIX=/tmp/build/workspace",
        "-B",
        "build",
        "-G",
        "Ninja",
        "CFLAGS=-O2 -fPIC",
        "quote'and space",
        "$(not-executed)",
        "line\nbreak",
        "",
    ]
    command = shellquote.join(arguments)
    logger.run(command, arguments=arguments)
    output = terminal.getvalue()
    plain = ANSI.sub("", output)
    assert plain == (
        "[00:00:00] STEP  zenlib 0.4.41\n"
        "[00:00:00] OK    mediainfo-lib 26.05 in 6s\n"
        f"[00:00:00] RUN   {command}\n"
    )
    log = logger.log_file.read_text()
    assert command in log and "\x1b" not in log
    if color:
        assert "[\x1b[32m00:00:00\x1b[0m]" in output
        assert "\x1b[1m\x1b[33m0.4.41" in output
        assert "\x1b[1m\x1b[33m26.05" in output
        assert "\x1b[35m-DBUILD_SHARED_LIBS\x1b[0m=\x1b[0m\x1b[33mOFF" in output
    else:
        assert "\x1b" not in output


def test_redirected_output_has_no_ansi(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR")
    Logger().step("zenlib 0.4.41")
    assert "\x1b" not in stream.getvalue()
