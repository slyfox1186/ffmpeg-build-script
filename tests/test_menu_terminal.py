"""Real PTY input, terminal restoration, and menu-to-build integration."""

from __future__ import annotations

import fcntl
import importlib
import json
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path
from typing import Any

import pytest

from ffmpeg_build.config import default_states, load_config
from ffmpeg_build.runtime.logging import Logger
from tests.conftest import REPO

CHILD = r"""
import json, os, pathlib, shutil, signal, sys, termios
from textual.binding import Binding
from ffmpeg_build.main import Orchestrator, _install_signal_handlers
from ffmpeg_build.runtime.errors import SignalStop
from ffmpeg_build.menu import app as module
root = pathlib.Path(sys.argv[1])
actual_clear = shutil.which('clear')
assert actual_clear
binary_dir = root / 'bin'; binary_dir.mkdir()
clear = binary_dir / 'clear'
clear.write_text('#!' + sys.executable + '\n' +
    'import json, pathlib, subprocess, sys, termios\n' +
    'flags = termios.tcgetattr(sys.stdout.fileno())[3]\n' +
    f'pathlib.Path({str(root / "clear.json")!r}).write_text(json.dumps({{"canonical": bool(flags & termios.ICANON), "echo": bool(flags & termios.ECHO)}}))\n' +
    f'subprocess.run([{actual_clear!r}], check=True)\n')
clear.chmod(0o755)
os.environ['PATH'] = str(binary_dir) + os.pathsep + os.environ['PATH']
class ObservedMenu(module.MenuApp):
    BINDINGS = [*module.MenuApp.BINDINGS, Binding('exclamation_mark', 'fixture_error', show=False)]
    def record(self):
        if self.focused is None: return
        state = {'focus':self.focused.id, 'compiler':self.model.settings.compiler,
                 'screen':type(self.screen).__name__, 'selected':sum(self.model.states.values())}
        target = root / 'state.json'
        pending = root / 'state.tmp'
        pending.write_text(json.dumps(state)); pending.replace(target)
    def on_mount(self):
        self.call_after_refresh(self.record)
    def on_descendant_focus(self,event):
        self.call_after_refresh(self.record)
    def _refresh_state(self):
        super()._refresh_state(); self.call_after_refresh(self.record)
    def action_fixture_error(self):
        raise ValueError('fixture UI failure')
module.MenuApp = ObservedMenu
class FixtureBuild(Orchestrator):
    def run_build(self,context):
        (root/'build-result.json').write_text(json.dumps({'compiler':context.compiler,
            'jobs':context.build_threads,'config':str(context.selection.config_file),
            'states':context.selection.states()}))
_install_signal_handlers()
try:
    result = FixtureBuild(pathlib.Path(sys.argv[2]), ['--menu','--gcc']).run()
except SignalStop as stop:
    result = stop.exit_code
except Exception as error:
    (root/'error.txt').write_text(str(error))
    result = 1
(root/'exit.json').write_text(json.dumps({'code':result}))
sys.exit(result)
"""


class Terminal:
    def __init__(self, root: Path, size: tuple[int, int]) -> None:
        self.root = root
        self.master, slave = pty.openpty()
        width, height = size
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        environment = {
            **os.environ,
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "PYTHONPATH": str(REPO),
            "BUILD_ROOT": str(root / "build"),
        }
        environment.pop("NO_COLOR", None)
        self.process = subprocess.Popen(
            [sys.executable, "-c", CHILD, str(root), str(REPO)],
            cwd=root,
            env=environment,
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        os.close(slave)
        self.transcript = bytearray()

    def drain(self, delay: float = 0.02) -> None:
        if select.select([self.master], [], [], delay)[0]:
            try:
                self.transcript.extend(os.read(self.master, 65536))
            except OSError:
                pass  # PTYs report EIO once their final slave closes.

    def send(self, keys: bytes) -> None:
        os.write(self.master, keys)

    def expect(self, **expected: object) -> dict[str, Any]:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.drain()
            path = self.root / "state.json"
            if path.exists():
                state: dict[str, Any] = json.loads(path.read_text())
                if all(state.get(key) == value for key, value in expected.items()):
                    return state
            assert self.process.poll() is None, self.transcript.decode(errors="replace")[-5000:]
        pytest.fail(f"No state {expected}: {self.transcript.decode(errors='replace')[-5000:]}")

    def finish(self, expected_code: int = 0) -> None:
        deadline = time.monotonic() + 8
        while self.process.poll() is None and time.monotonic() < deadline:
            self.drain()
        assert self.process.wait(timeout=1) == expected_code, self.transcript.decode(
            errors="replace"
        )[-5000:]
        self.drain(0)
        assert json.loads((self.root / "clear.json").read_text()) == {
            "canonical": True,
            "echo": True,
        }
        assert b"\x1b[<u" in self.transcript, "Keyboard protocol must be restored before leaving"
        (self.root / "terminal-output.txt").write_bytes(self.transcript)

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=2)
        os.close(self.master)


@pytest.mark.parametrize("modern", [False, True], ids=["legacy", "kitty-protocol"])
def test_physical_keys_single_escape_autosave_and_build_handoff(
    tmp_path: Path, modern: bool
) -> None:
    terminal = Terminal(tmp_path, (120, 36))
    try:
        terminal.expect(focus="compiler-category")
        assert b"\x1b[>25u" in terminal.transcript
        # Decode the actual rendered terminal output, including the persistent
        # Compilers entry and both exclusive options.
        pyte = importlib.import_module("pyte")
        screen = pyte.Screen(120, 36)
        pyte.Stream(screen).feed(terminal.transcript.decode(errors="replace"))
        rendered = "\n".join(screen.display)
        assert all(text in rendered for text in ("GCC", "Clang", "PACKAGES", "CONFIGURATION"))
        (tmp_path / "rendered.txt").write_text(rendered)
        # A split arrow sequence must not become an Escape followed by text.
        terminal.send(b"\x1b")
        terminal.drain(0.02)
        terminal.send(b"[C")
        terminal.expect(focus="compiler-options")
        for back in (b"\x1b[D", b"\x7f", b"\x08"):
            terminal.send(back)
            terminal.expect(focus="compiler-category")
            terminal.send(b"\x1b[C")
            terminal.expect(focus="compiler-options")
        started = time.monotonic()
        terminal.send(b"\x1b[27u" if modern else b"\x1b")
        terminal.expect(focus="compiler-category")
        elapsed = time.monotonic() - started
        assert elapsed < 0.5, f"One Escape took {elapsed:.3f}s"
        (tmp_path / "escape-timing.json").write_text(
            json.dumps({"modern": modern, "elapsed_ms": elapsed * 1000})
        )
        terminal.send(b"\x1b[C\x1b[B ")
        terminal.expect(focus="compiler-category", compiler="clang")
        config = tmp_path / "custom.toml"
        assert load_config(config, Logger()).settings.compiler == "clang"
        terminal.send(b"e")
        terminal.expect(focus="jobs", screen="SettingsScreen")
        terminal.send(b"3\r")
        terminal.expect(screen="Screen")
        terminal.send(b"b")
        terminal.finish()
        result = json.loads((tmp_path / "build-result.json").read_text())
        assert result == {
            "compiler": "clang",
            "jobs": 3,
            "config": str(config),
            "states": default_states(),
        }
    finally:
        terminal.close()


@pytest.mark.parametrize(
    "action",
    [
        "quit",
        "toggle_quit",
        "ctrl_d",
        "ctrl_c",
        "settings_ctrl_q",
        "save_quit",
        "sigterm",
        "sighup",
        "sigint",
        "error",
    ],
)
def test_exit_paths_restore_terminal_and_run_clear(tmp_path: Path, action: str) -> None:
    terminal = Terminal(tmp_path, (80, 24))
    try:
        terminal.expect(focus="compiler-category")
        code = 0
        if action == "toggle_quit":
            terminal.send(b"gq")
        elif action == "settings_ctrl_q":
            terminal.send(b"e")
            terminal.expect(focus="jobs")
            terminal.send(b"\x11")
        elif action == "save_quit":
            terminal.send(b"s")
            terminal.expect(focus="save-path")
            terminal.send(b"\r")
            terminal.expect(screen="Screen")
            terminal.send(b"q")
        elif action in ("sigterm", "sighup", "sigint"):
            number = {"sigterm": signal.SIGTERM, "sighup": signal.SIGHUP, "sigint": signal.SIGINT}[
                action
            ]
            os.kill(terminal.process.pid, number)
            code = 128 + number
        else:
            terminal.send(
                {"quit": b"q", "ctrl_d": b"\x04", "ctrl_c": b"\x03", "error": b"!"}[action]
            )
            if action == "error":
                code = 1
        terminal.finish(code)
        if action == "error":
            assert "fixture UI failure" in (tmp_path / "error.txt").read_text()
        assert not (tmp_path / "build-result.json").exists()
        assert (tmp_path / "custom.toml").exists() == (action in ("toggle_quit", "save_quit"))
    finally:
        terminal.close()
