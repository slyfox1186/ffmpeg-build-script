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
        assert "\x1b[38;5;246m[00:00:00]\x1b[0m" in output
        assert (
            "\x1b[38;5;75mSTEP \x1b[0m \x1b[38;5;255m\x1b[1mzenlib \x1b[38;5;221m0.4.41\x1b[38;5;255m\x1b[1m\x1b[0m\n"
            in output
        )
        assert (
            "\x1b[38;5;78mOK   \x1b[0m \x1b[38;5;255mmediainfo-lib \x1b[38;5;221m26.05\x1b[38;5;255m in 6s\x1b[0m\n"
            in output
        )
        assert output.split("RUN  ", 1)[1] == f"\x1b[0m \x1b[38;5;255m{command}\x1b[0m\n"
    else:
        assert "\x1b" not in output


def test_redirected_output_has_no_ansi(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR")
    Logger().step("zenlib 0.4.41")
    assert "\x1b" not in stream.getvalue()


@pytest.mark.parametrize(
    "level", ["STEP", "OK", "INFO", "RUN", "SKIP", "TIME", "DEBUG", "WARN", "ERROR"]
)
@pytest.mark.parametrize("term", ["xterm-256color", "xterm", "dumb"])
def test_every_log_body_uses_one_uniform_white_foreground(
    monkeypatch: pytest.MonkeyPatch, level: str, term: str
) -> None:
    out, err = Terminal(), Terminal()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    monkeypatch.setenv("TERM", term)
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.delenv("NO_COLOR")
    logger = Logger()
    message = "package 1.2.3 --flag=OFF '/path with spaces'\nMore 'detail' and --options"
    logger.line(level, message, stream=err if level in ("WARN", "ERROR") else out)
    output = (err if level in ("WARN", "ERROR") else out).getvalue()
    reset = "" if term == "dumb" else "\x1b[0m"
    white = {"dumb": "", "xterm": "\x1b[97m", "xterm-256color": "\x1b[38;5;255m"}[term]
    bold = "\x1b[1m" if level == "STEP" and term != "dumb" else ""
    yellow = {"dumb": "", "xterm": "\x1b[93m", "xterm-256color": "\x1b[38;5;221m"}[term]
    version = f"{yellow}1.2.3{white}{bold}" if level in ("STEP", "OK", "SKIP") else "1.2.3"
    assert output.split(f"{level:<5}", 1)[1] == (
        f"{reset} {white}{bold}package {version} --flag=OFF '/path with spaces'{reset}\n"
        f"{' ' * 17}{reset}{white}More 'detail' and --options{reset}\n"
    )
    if term == "dumb":
        assert "\x1b" not in output
    elif term == "xterm":
        assert "38;5;" not in output


def test_color_output_and_redirected_errors_are_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out, err = Terminal(), io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR")
    logger = Logger()
    logger.step("package 1.2.3")
    logger.error("Failure\nDetails")
    assert "\x1b" in out.getvalue()
    assert err.getvalue() == "[00:00:00] ERROR Failure\n                 Details\n"


@pytest.mark.parametrize(
    "level,message,versions",
    [
        ("STEP", "pkg 2.0.0 (replacing 1.9.9)", ["2.0.0", "1.9.9"]),
        ("SKIP", "pkg 1.9.9 -> 2.0.0 is outdated; keeping the existing build.", ["1.9.9", "2.0.0"]),
        ("OK", "pkg a123456789abcdef in 18s", ["a123456789abcdef"]),
    ],
)
def test_all_package_version_tokens_share_yellow(
    monkeypatch: pytest.MonkeyPatch, level: str, message: str, versions: list[str]
) -> None:
    terminal = Terminal()
    monkeypatch.setattr("sys.stdout", terminal)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR")
    Logger().line(level, message)
    output = terminal.getvalue()
    for version in versions:
        assert f"\x1b[38;5;221m{version}\x1b[38;5;255m" in output
    assert "\x1b[38;5;221m18s" not in output
    assert ANSI.sub("", output) == f"[00:00:00] {level:<5} {message}\n"
