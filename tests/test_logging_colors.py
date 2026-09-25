from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from ffmpeg_build.runtime import shellquote
from ffmpeg_build.runtime.logging import Logger

ANSI = re.compile(r"\x1b\[[0-9;]*m")

GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
CYAN = "\x1b[36m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Terminal:
    stream = Terminal()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    return stream


def logger_for(terminal: Terminal, *, debug: bool = False) -> Logger:
    """Bind a logger to `terminal`.

    Pytest rebinds `sys.stdout` between the setup and call phases, so the swap
    only holds when it happens inside the test body.
    """
    original = sys.stdout
    sys.stdout = terminal
    try:
        return Logger(debug=debug)
    finally:
        sys.stdout = original


def plain(stream: io.StringIO) -> str:
    return ANSI.sub("", stream.getvalue())


def test_package_opens_with_an_underlined_heading_and_closes_with_its_duration(
    terminal: Terminal,
) -> None:
    logger = logger_for(terminal)
    logger.package_start("libfdk-aac", "2.0.3")
    logger.run("", arguments=["make", "-j24"])
    logger.package_done("libfdk-aac", "2.0.3", "8s")
    assert plain(terminal) == (
        "Building libfdk-aac - version 2.0.3\n"
        "===================================\n"
        "$ make -j24\n"
        "[DONE] libfdk-aac 2.0.3 built in 8s\n"
        "\n"
    )
    heading = terminal.getvalue().splitlines()[0]
    assert heading == (
        f"{GREEN}Building{RESET} {BOLD}{YELLOW}libfdk-aac{RESET} "
        f"{GREEN}- version{RESET} {YELLOW}2.0.3{RESET}"
    )
    assert f"{BOLD}{GREEN}[DONE]{RESET}" in terminal.getvalue()


def test_upgrade_heading_names_the_version_it_replaces(terminal: Terminal) -> None:
    logger_for(terminal).package_start("libheif", "1.23.5", "1.23.4")
    heading, rule = plain(terminal).splitlines()
    assert heading == "Building libheif - version 1.23.5 (replacing 1.23.4)"
    assert rule == "=" * len(heading)


def test_commands_echo_after_a_shell_prompt(terminal: Terminal) -> None:
    arguments = ["curl", "--silent", "https://example.test/a.tar.gz", "/tmp/a b.tar.gz"]
    logger_for(terminal).run("", arguments=arguments)
    output = terminal.getvalue()
    assert output.startswith(f"{DIM}${RESET} {BOLD}curl{RESET} --silent ")
    assert f"{CYAN}https://example.test/a.tar.gz{RESET}" in output
    assert plain(terminal) == f"$ {shellquote.join(arguments)}\n"


def test_quiet_commands_reach_the_log_but_not_the_terminal(
    terminal: Terminal, tmp_path: Path
) -> None:
    logger = logger_for(terminal)
    logger.log_file = tmp_path / "build.log"
    logger.log_file.touch()
    logger.run("", arguments=["curl", "--silent", "https://example.test/a"], quiet=True)
    logger.time("finished in 45s", quiet=True)
    assert terminal.getvalue() == ""
    log = logger.log_file.read_text()
    assert "RUN   curl --silent https://example.test/a\n" in log
    assert "TIME  finished in 45s\n" in log


def test_debug_shows_quiet_commands(terminal: Terminal) -> None:
    logger_for(terminal, debug=True).run("", arguments=["curl", "--silent"], quiet=True)
    assert plain(terminal) == "$ curl --silent\n"


def test_message_urls_are_painted_inside_info_records(terminal: Terminal) -> None:
    logger_for(terminal).get("https://example.test/a.tar.gz", "a.tar.gz")
    output = terminal.getvalue()
    assert output.startswith(f"{GREEN}[INFO]{RESET} Downloading ")
    assert f"{CYAN}https://example.test/a.tar.gz{RESET}" in output
    assert plain(terminal) == "[INFO] Downloading https://example.test/a.tar.gz as 'a.tar.gz'.\n"


@pytest.mark.parametrize(
    "level,tag,color,bold",
    [
        ("INFO", "[INFO]", GREEN, False),
        ("SKIP", "[SKIP]", CYAN, False),
        ("TIME", "[TIME]", DIM, False),
        ("WARN", "[WARNING]", YELLOW, True),
        ("ERROR", "[ERROR]", RED, True),
    ],
)
def test_every_level_keeps_its_own_tag(
    monkeypatch: pytest.MonkeyPatch,
    terminal: Terminal,
    level: str,
    tag: str,
    color: str,
    bold: bool,
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger = logger_for(terminal)
    diagnostic = level in ("WARN", "ERROR")
    logger.line(level, "message", stream=stream if diagnostic else None)
    target = stream if diagnostic else terminal
    weight = BOLD if bold else ""
    assert target.getvalue().startswith(f"{weight}{color}{tag}{RESET} ")
    assert plain(target) == f"{tag} message\n"


def test_failure_names_the_package_in_red(
    monkeypatch: pytest.MonkeyPatch, terminal: Terminal
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger_for(terminal).package_failed("libmysofa", "1.3.5", "cmake: could not find zlib >= 1.2.9")
    output = stream.getvalue()
    assert f"{BOLD}{RED}[FAILED]{RESET}" in output
    assert f"{BOLD}{RED}libmysofa 1.3.5:{RESET}" in output
    assert plain(stream) == "[FAILED] libmysofa 1.3.5: cmake: could not find zlib >= 1.2.9\n"


def test_long_commands_wrap_at_the_terminal_width_under_a_hanging_indent(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLUMNS", "60")
    arguments = ["cmake", *(f"-DOPTION_NUMBER_{index}=ON" for index in range(12))]
    logger_for(terminal).run("", arguments=arguments)
    lines = plain(terminal).splitlines()
    assert len(lines) > 1
    assert lines[0].startswith("$ cmake -DOPTION_NUMBER_0=ON")
    assert all(len(line) <= 60 for line in lines)
    assert all(line.startswith("    -D") for line in lines[1:])
    assert " ".join(line.strip() for line in lines) == "$ " + shellquote.join(arguments)


def test_redirected_output_is_not_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setenv("COLUMNS", "40")
    Logger().info("Build root: " + "x" * 200)
    assert stream.getvalue() == "[INFO] Build root: " + "x" * 200 + "\n"


def test_multi_line_records_keep_their_own_spacing(terminal: Terminal) -> None:
    logger_for(terminal).info("NVIDIA: NVIDIA GPU detected\nAMD:    AMD GPU detected")
    assert plain(terminal) == (
        "[INFO] NVIDIA: NVIDIA GPU detected\n       AMD:    AMD GPU detected\n"
    )


def test_sections_and_packages_never_stack_blank_lines(terminal: Terminal) -> None:
    logger = logger_for(terminal)
    logger.info("Parallel jobs: 24")
    logger.banner("Installing Image Tools")
    logger.package_reused("openjpeg", "2.5.4")
    logger.package_start("libheif", "1.23.5")
    logger.package_done("libheif", "1.23.5", "10s")
    logger.package_start("libwebp", "1.6.0")
    assert plain(terminal) == (
        "[INFO] Parallel jobs: 24\n"
        "\n"
        "┌──────────────────────────┐\n"
        "│  Installing Image Tools  │\n"
        "└──────────────────────────┘\n"
        "\n"
        "[SKIP] openjpeg 2.5.4 is already built.\n"
        "\n"
        "Building libheif - version 1.23.5\n"
        "=================================\n"
        "[DONE] libheif 1.23.5 built in 10s\n"
        "\n"
        "Building libwebp - version 1.6.0\n"
        "================================\n"
    )


def test_summary_and_farewell(terminal: Terminal) -> None:
    logger = logger_for(terminal)
    logger.summary(built=3, reused=120, failed=0, elapsed="1m30s")
    logger.farewell("https://github.com/slyfox1186/ffmpeg-build-script")
    assert plain(terminal) == (
        "[INFO] Packages: 3 built, 120 already built\n"
        "[INFO] Total time: 1m30s\n"
        "\n"
        "[INFO] Make sure to star this repository to show your support!\n"
        "[INFO] https://github.com/slyfox1186/ffmpeg-build-script\n"
        "\n"
    )


def test_failed_summary_counts_the_failure(terminal: Terminal) -> None:
    logger_for(terminal).summary(built=2, reused=0, failed=1, elapsed="40s")
    assert plain(terminal).splitlines()[0] == "[INFO] Packages: 2 built, 1 failed"
    assert f"{BOLD}{RED}1 failed{RESET}" in terminal.getvalue()


def test_plain_log_file_and_redirected_output_carry_no_escapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    logger = Logger()
    logger.log_file = tmp_path / "build.log"
    logger.log_file.touch()
    logger.banner("Installing Image Tools")
    logger.package_start("zenlib", "0.4.41")
    logger.package_done("zenlib", "0.4.41", "6s")
    logger.run("", arguments=["make", "-j24"])
    assert "\x1b" not in stream.getvalue()
    assert "Building zenlib - version 0.4.41\n" in stream.getvalue()
    assert "[DONE] zenlib 0.4.41 built in 6s\n" in stream.getvalue()
    assert "\x1b" not in logger.log_file.read_text()
    assert logger.log_file.read_text().endswith("RUN   make -j24\n")


def test_no_color_keeps_the_terminal_plain(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    logger = logger_for(terminal)
    logger.package_start("x264", "0.165")
    logger.warn("careful")
    assert "\x1b" not in terminal.getvalue()


def test_quoted_urls_stay_against_their_quotes(
    monkeypatch: pytest.MonkeyPatch, terminal: Terminal
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger_for(terminal).warn("Trying fallback mirror: 'https://mirror.test/x.tar.xz'.")
    assert f"'{CYAN}https://mirror.test/x.tar.xz{RESET}'." in stream.getvalue()
    assert plain(stream) == "[WARNING] Trying fallback mirror: 'https://mirror.test/x.tar.xz'.\n"


def test_wrapping_breaks_between_arguments_and_keeps_every_character(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLUMNS", "60")
    arguments = [
        "curl",
        "-DPREFIX=" + "/deep" * 7,
        "--write-out",
        "HTTP %{http_code}; bytes: %{size}",
        "-G",
        "https://example.test/archive.tar.gz",
    ]
    logger_for(terminal).run("", arguments=arguments)
    lines = plain(terminal).splitlines()
    words = [shellquote.quote(word) for word in arguments]
    assert all(len(line) <= 60 for line in lines)
    assert "\n".join(lines) == (
        f"$ {words[0]} {words[1]}\n    {words[2]} {words[3]} {words[4]}\n    {words[5]}"
    )


def test_failure_details_line_up_under_the_failure(
    monkeypatch: pytest.MonkeyPatch, terminal: Terminal
) -> None:
    stream = Terminal()
    monkeypatch.setattr("sys.stderr", stream)
    logger = logger_for(terminal)
    logger.package_failed("x265", "4.1", "Command failed.")
    logger.hint("Build log: /tmp/build.log")
    assert plain(terminal) == "         Build log: /tmp/build.log\n"


def test_prompts_carry_a_tag_and_record_the_answer(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    asked: list[str] = []

    def reply(prompt: str = "") -> str:
        asked.append(prompt)
        return "no"

    monkeypatch.setattr("builtins.input", reply)
    logger = logger_for(terminal)
    logger.log_file = tmp_path / "build.log"
    logger.log_file.touch()
    logger.info("Build complete.")
    assert logger.prompt("Remove all build files? (yes/no): ") == "no"
    assert asked == [f"{BOLD}\x1b[35m[PROMPT]{RESET} Remove all build files? (yes/no): "]
    assert plain(terminal) == "[INFO] Build complete.\n\n"
    assert logger.log_file.read_text().endswith("PROMPT Remove all build files? (yes/no): no\n")
