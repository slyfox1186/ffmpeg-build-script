from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, RadioSet, Switch

from ffmpeg_build.config import BuildSettings, default_states, load_config
from ffmpeg_build.menu.app import MenuApp
from ffmpeg_build.menu.dialogs import ImportScreen
from ffmpeg_build.menu.model import LaunchSettings, MenuModel
from ffmpeg_build.menu.session import MenuSession
from ffmpeg_build.runtime.logging import Logger
from tests.test_menu_terminal import Terminal

IMPORTED = (
    '[build]\ncompiler="clang"\nlatest=true\nenable_gpl_and_non_free=true\n'
    "[packages]\nlibopus=true\nvulkan-headers=true\n"
)


@pytest.mark.parametrize("source_kind", ["absolute", "relative", "symlink"])
def test_import_is_atomic_undoable_and_keeps_source_and_launch_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source_kind: str,
) -> None:
    source = tmp_path / "source.toml"
    source.write_text(IMPORTED)
    path = source
    if source_kind == "relative":
        monkeypatch.chdir(tmp_path)
        path = Path(source.name)
    elif source_kind == "symlink":
        path = tmp_path / "linked.toml"
        path.symlink_to(source)
    launch = LaunchSettings(jobs="3", cuda_install="never")
    session = MenuSession(
        MenuModel(default_states(), BuildSettings()), tmp_path / "active.toml", launch
    )
    before = session.snapshot()
    assert session.import_config(path)
    assert capsys.readouterr() == ("", "")
    assert session.model.settings.compiler == "clang"
    assert session.model.gpl and session.model.settings.latest
    assert {key for key, value in session.model.states.items() if value} == {
        "libopus",
        "vulkan-headers-git",
    }
    assert session.result.settings is session.model.settings
    assert session.result.launch is launch and launch.jobs == "3"
    assert session.default_path == tmp_path / "active.toml"
    assert "deprecated" in session.message
    assert "cleanup" in session.message
    assert source.read_text() == IMPORTED
    loaded = load_config(session.default_path, Logger())
    assert loaded.selection.states() == session.model.states
    assert loaded.settings.compiler == "clang"
    assert len(session.history) == 1
    assert session.undo() and session.snapshot() == before
    assert load_config(session.default_path, Logger()).selection.states() == before[0]
    assert source.read_text() == IMPORTED


@pytest.mark.parametrize(
    "invalid",
    ["missing", "directory", "unreadable", "utf8", "syntax", "compiler", "package", "duplicate"],
)
def test_invalid_import_preserves_configuration_and_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    source = tmp_path / "invalid.toml"
    if invalid == "directory":
        source.mkdir()
    elif invalid != "missing":
        source.write_bytes(
            {
                "utf8": b"\xff",
                "syntax": b"[build]\ncompiler = [",
                "compiler": b'[build]\ncompiler="invalid"\n',
                "package": b"[packages]\nunknown=true\n",
                "duplicate": b"[packages]\nlibopus=true\nlibopus=false\n",
            }.get(invalid, IMPORTED.encode())
        )
    session = MenuSession(MenuModel(default_states(), BuildSettings()), tmp_path / "active.toml")
    assert session.change(lambda: session.model.toggle("libopus"), "Edited.")
    before, history, data = (
        session.snapshot(),
        list(session.history),
        session.default_path.read_bytes(),
    )
    if invalid == "unreadable":

        def fail_read(*args: object, **kwargs: object) -> str:
            raise PermissionError("permission denied")

        monkeypatch.setattr(Path, "read_text", fail_read)
    assert not session.import_config(source)
    assert session.failed and session.message.startswith("Import failed:")
    assert session.snapshot() == before and session.history == history
    assert session.default_path.read_bytes() == data
    assert session.result.saved_path == session.default_path


def test_import_rolls_back_when_autosave_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.toml"
    source.write_text(IMPORTED)
    session = MenuSession(MenuModel(default_states(), BuildSettings()), tmp_path / "active.toml")
    assert session.save(session.default_path)
    before, data = session.snapshot(), session.default_path.read_bytes()

    def fail_write(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("ffmpeg_build.menu.session.publish_atomically", fail_write)
    assert not session.import_config(source)
    assert session.failed and "disk full" in session.message and "reverted" in session.message
    assert session.snapshot() == before and not session.history
    assert session.default_path.read_bytes() == data
    assert source.read_text() == IMPORTED


def test_import_identical_settings_still_saves_without_an_undo_entry(tmp_path: Path) -> None:
    source = tmp_path / "empty.toml"
    source.write_text("[packages]\n")
    session = MenuSession(MenuModel({}, BuildSettings()), tmp_path / "active.toml")
    assert session.import_config(source)
    assert session.default_path.is_file() and not session.history
    assert not any(load_config(session.default_path, Logger()).selection.states().values())
    assert source.read_text() == "[packages]\n"


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (40, 10)])
def test_import_dialog_keyboard_errors_refresh_and_undo(
    tmp_path: Path, size: tuple[int, int]
) -> None:
    async def check() -> None:
        source = tmp_path / "source [draft].toml"
        source.write_text(IMPORTED)
        app = MenuApp(MenuModel(default_states(), BuildSettings()), tmp_path / "active.toml")
        before = app.session.snapshot()
        async with app.run_test(size=size) as pilot:
            if size[0] >= 110:
                await pilot.click("#import-button")
            else:
                await pilot.press("o")
            assert isinstance(app.screen, ImportScreen)
            path = app.screen.query_one(Input)
            path.value = str(source)
            await pilot.press("end", "left", "right", "down")
            assert app.focused is app.screen.query_one("#cancel")
            await pilot.press("enter")
            assert not isinstance(app.screen, ImportScreen)
            assert app.session.snapshot() == before and not app.session.default_path.exists()
            await pilot.press("o", "enter")
            assert isinstance(app.screen, ImportScreen)
            assert "Enter a file path" in app.screen.query_one("#import-error").render_line(0).text
            path = app.screen.query_one(Input)
            path.value = str(source)
            await pilot.press("down", "right", "up")
            assert app.focused is path and path.value == str(source)
            await pilot.press("down")
            assert app.focused is app.screen.query_one("#import")
            await pilot.press("enter")
            assert not isinstance(app.screen, ImportScreen)
            await pilot.pause()
            assert app.model.settings.compiler == "clang"
            assert app.query_one(RadioSet).pressed_index == 1
            assert app.query_one("#gpl", Switch).value and app.query_one("#latest", Switch).value
            assert len(app.session.history) == 1 and not app.session.failed
            assert app.session.default_path == tmp_path / "active.toml"
            assert source.read_text() == IMPORTED
            await pilot.press("u")
            await pilot.pause()
            assert app.session.snapshot() == before
            assert app.query_one(RadioSet).pressed_index == 0
            for button in app.query("#toolbar Button").results(Button):
                if button.display and app.query_one("#toolbar").display:
                    assert button.region.right <= size[0]

    asyncio.run(check())


def test_import_physical_arrows_and_build_handoff(tmp_path: Path) -> None:
    source = tmp_path / "source.toml"
    source.write_text('[build]\ncompiler="clang"\n[packages]\nffmpeg=true\n')
    terminal = Terminal(tmp_path, (80, 24))
    try:
        terminal.expect(focus="compiler-category")
        terminal.send(b"o")
        terminal.expect(focus="import-path", screen="ImportScreen")
        terminal.send(str(source).encode() + b"\x1b[B\x1b[C\r")
        terminal.expect(screen="Screen", compiler="clang", selected=1)
        terminal.send(b"b")
        terminal.finish()
        result = json.loads((tmp_path / "build-result.json").read_text())
        assert result["compiler"] == "clang"
        assert result["config"] == str(tmp_path / "custom.toml")
        assert result["states"]["ffmpeg"] and sum(result["states"].values()) == 1
        assert source.read_text() == '[build]\ncompiler="clang"\n[packages]\nffmpeg=true\n'
    finally:
        terminal.close()
