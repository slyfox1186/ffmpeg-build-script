from __future__ import annotations

import fcntl
import json
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest

from tests.conftest import REPO


def terminal_script(code: str, tmp_path: Path, height: int, width: int) -> dict[str, object]:
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=tmp_path,
        env={**os.environ, "TERM": "xterm-256color", "PYTHONPATH": str(REPO)},
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    transcript = bytearray()
    deadline = time.monotonic() + 20
    try:
        while process.poll() is None:
            assert time.monotonic() < deadline, transcript.decode(errors="replace")
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    transcript.extend(os.read(master, 65536))
                except OSError:
                    break
        assert process.wait(timeout=2) == 0, transcript.decode(errors="replace")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
    result: dict[str, object] = json.loads((tmp_path / "result.json").read_text())
    return result


@pytest.mark.parametrize(("height", "width"), [(36, 120), (24, 80), (10, 40)])
def test_real_menu_all_packages_search_categories_save_and_build(
    tmp_path: Path, height: int, width: int
) -> None:
    code = r"""
import curses, json, pathlib, sys
from ffmpeg_build import registry
from ffmpeg_build.config import BuildSettings, load_config
from ffmpeg_build.menu.app import MenuApp
from ffmpeg_build.menu.model import MenuModel
from ffmpeg_build.runtime.logging import Logger
root = pathlib.Path(sys.argv[1])
model = MenuModel({}, BuildSettings())
app = MenuApp(model, root / 'custom.toml')
snapshots = {}
def text(screen):
    return [screen.instr(y, 0).decode(errors='replace').rstrip() for y in range(screen.getmaxyx()[0])]
def keys(value):
    for character in reversed(value): curses.unget_wch(character)
def check(screen):
    screen.keypad(True)
    assert len(app.rows()) == len(registry.GROUPS) == 15
    app.draw(screen); snapshots['overview'] = text(screen)
    if screen.getmaxyx()[1] >= 80:
        app.handle(screen, 10)
        assert app.current(app.rows()).package is not None
        app.handle(screen, 9)
        assert app.current(app.rows()).group == registry.GROUPS[1].name
        app.handle(screen, curses.KEY_UP)
        assert app.current(app.rows()).is_group and app.cursor == 0
        app.handle(screen, 10)
        assert app.current(app.rows()).package is not None
        app.handle(screen, curses.KEY_LEFT)
    app.handle(screen, 9)
    assert app.current(app.rows()).group == registry.GROUPS[1].name
    app.handle(screen, curses.KEY_BTAB)
    assert app.cursor == 0
    app.handle(screen, ord(']'))
    assert sum(row.package is not None for row in app.rows()) == 127
    app.draw(screen); snapshots['expanded'] = text(screen)
    for key in registry.PACKAGE_NAMES:
        app.cursor = next(i for i, row in enumerate(app.rows()) if row.package and row.package.key == key)
        before = sum(model.enabled(name) for name in registry.PACKAGE_NAMES)
        app.handle(screen, ord(' ')); assert model.enabled(key)
        assert sum(model.enabled(name) for name in registry.PACKAGE_NAMES) == before + 1
        app.handle(screen, ord(' ')); assert not model.enabled(key)
        assert not app.dirty
    app.handle(screen, ord('a')); before_preset = dict(model.states)
    keys('n'); app.handle(screen, ord('p'))
    assert not any(model.states.values())
    app.handle(screen, ord('u')); assert model.states == before_preset
    app.handle(screen, ord('u')); assert not any(model.states.values())
    folds = set(model.collapsed); model.search = 'm4'; app.cursor = 0
    for key in [' ', '[', ']', curses.KEY_LEFT, curses.KEY_RIGHT]:
        app.handle(screen, ord(key) if isinstance(key, str) else key)
    assert model.collapsed == folds
    model.search = ''
    keys('cbogus\nq'); app.handle(screen, ord('e'))
    assert app.result.launch.compiler == 'gcc' and 'Compiler must' in app.message
    app.result.launch.build_root = '/etc'
    assert app.handle(screen, ord('b')) and 'unsafe build root' in app.message
    assert not (root / 'custom.toml').exists()
    app.result.launch.build_root = str(root / 'build')
    model.search = 'opus'
    app.cursor = 0
    keys('\x1b'); app.handle(screen, ord('/'))
    assert model.search == 'opus'
    keys('\n'); app.handle(screen, ord('/'))
    assert model.search == ''
    model.search = 'a name with no matches'
    app.handle(screen, curses.KEY_DOWN); app.draw(screen)
    assert app.cursor == 0
    snapshots['empty'] = text(screen)
    model.search = 'Audio devices'
    assert len(app.rows()) == 1 + len(registry.GROUPS[8].packages)
    app.handle(screen, ord('a'))
    assert 'entire category' in app.message
    assert model.enabled_count(registry.GROUPS[8]) == len(registry.GROUPS[8].packages)
    model.apply_preset('minimal')
    assert not model.issues() and not model.enabled('mediainfo-cli')
    model.apply_preset('none'); model.search = ''; app.handle(screen, ord(']'))
    for key in registry.PACKAGE_NAMES:
        app.cursor = next(i for i, row in enumerate(app.rows()) if row.package and row.package.key == key)
        app.handle(screen, ord(' '))
    keys('~ffmpeg_audit_nonexistent_user/config.toml\n')
    assert not app.save(screen) and 'Save failed' in app.message and app.dirty
    app.draw(screen); snapshots['save_error'] = text(screen)
    keys('selection.toml\n')
    assert app.save(screen) and not app.dirty
    assert app.result.saved_path == root / 'selection.toml'
    assert all(load_config(app.result.saved_path, Logger()).selection.states().values())
    keys('\n'); assert not app.handle(screen, ord('b'))
    assert app.result.start_build
curses.wrapper(check)
(root / 'result.json').write_text(json.dumps({'packages':127, 'build':app.result.start_build, 'snapshots':snapshots}))
"""
    result = terminal_script(code, tmp_path, height, width)
    assert result["packages"] == 127 and result["build"] is True
    (tmp_path / "screen-evidence.json").write_text(json.dumps(result, indent=2))


def test_too_small_terminal_ignores_edits_and_can_quit(tmp_path: Path) -> None:
    code = r"""
import curses, json, pathlib, sys
from ffmpeg_build.config import BuildSettings
from ffmpeg_build.menu.app import MenuApp
from ffmpeg_build.menu.model import MenuModel
root = pathlib.Path(sys.argv[1])
app = MenuApp(MenuModel({}, BuildSettings()), root / 'custom.toml')
def check(screen):
    app.draw(screen)
    for key in '/sebgla ': assert app.handle(screen, ord(key))
    assert not app.dirty
    assert not app.handle(screen, ord('q'))
    assert app.prompt(screen, 'Too small: ') is None
curses.wrapper(check)
(root / 'result.json').write_text(json.dumps({'small': 'PASS'}))
"""
    assert terminal_script(code, tmp_path, 6, 24) == {"small": "PASS"}
