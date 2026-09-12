from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input, OptionList, RadioSet, SelectionList, Switch

from ffmpeg_build import registry
from ffmpeg_build.config import BuildSettings, load_config
from ffmpeg_build.menu.app import MenuApp
from ffmpeg_build.menu.dialogs import HelpScreen, SaveScreen, SettingsScreen
from ffmpeg_build.menu.model import MenuModel
from ffmpeg_build.runtime.logging import Logger


@pytest.mark.parametrize("size", [(210, 44), (120, 36), (80, 24), (60, 20), (40, 10)])
def test_render_navigation_single_escape_and_compiler_autosave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)

    async def check() -> None:
        app = MenuApp(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            assert app.focused is app.query_one("#compiler-category")
            assert not app.session.default_path.exists()
            assert app.query_one("#compiler-category").region.height > 0
            (tmp_path / "initial.svg").write_text(app.export_screenshot())
            for back in ("escape", "left", "backspace", "ctrl+h"):
                await pilot.press("right")
                assert app.focused is app.query_one("#compiler-options")
                assert app.query_one("#compiler-options").region.height > 0
                await pilot.press(back)
                assert app.focused is app.query_one("#compiler-category")
                await pilot.press(back)
                assert app.focused is app.query_one("#compiler-category")
            await pilot.press("right", "down", "space")
            assert app.model.settings.compiler == "clang"
            assert app.focused is app.query_one("#compiler-category")
            assert load_config(app.session.default_path, Logger()).settings.compiler == "clang"
            await pilot.press("right", "enter")
            assert app.focused is app.query_one("#compiler-category")
            assert len(app.session.history) == 1
            await pilot.press("u")
            await pilot.pause()
            assert app.model.settings.compiler == "gcc"
            assert app.query_one(RadioSet).pressed_index == 0
            await pilot.press("down", "right")
            assert app.focused is app.query_one("#packages")
            for back in ("escape", "left", "backspace", "ctrl+h"):
                await pilot.press(back)
                assert app.focused is app.query_one("#categories")
                await pilot.press("right")
                assert app.focused is app.query_one("#packages")
            (tmp_path / "packages.svg").write_text(app.export_screenshot())
            await pilot.press("enter")
            assert app.model.enabled(registry.GROUPS[0].packages[0].key)
            assert app.focused is app.query_one("#categories")
            before = app.session.default_path.read_bytes()
            await pilot.press("q")
            assert not app.session.result.start_build
            assert app.session.default_path.read_bytes() == before

    asyncio.run(check())


def test_compact_empty_search_explains_results_and_allows_return_to_compilers(
    tmp_path: Path,
) -> None:
    async def check() -> None:
        app = MenuApp(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
        async with app.run_test(size=(40, 10)) as pilot:
            await pilot.press("slash")
            app.query_one("#search", Input).value = "no package matches this"
            await pilot.press("escape")
            assert app.query_one("#no-categories").region.height > 0
            assert app.query_one("#categories", OptionList).option_count == 0
            await pilot.press("up")
            assert app.focused is app.query_one("#compiler-category")
            await pilot.press("right", "escape")
            assert app.focused is app.query_one("#compiler-category")
            assert not app.session.default_path.exists()

    asyncio.run(check())


def test_search_empty_results_category_edits_and_all_127_packages(tmp_path: Path) -> None:
    async def check() -> None:
        app = MenuApp(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            for group_index, group in enumerate(registry.GROUPS):
                app.group_index = group_index
                app._show_category()
                app.action_options()
                packages = app.query_one("#packages", SelectionList)
                for index, package in enumerate(group.packages):
                    packages.highlighted = index
                    await pilot.press("space")
                    assert app.model.enabled(package.key)
                    assert load_config(app.session.default_path, Logger()).selection.enabled(
                        package.key
                    )
                    app.action_options()
            assert all(app.model.states.values())
            await pilot.press("slash")
            search = app.query_one("#search", Input)
            search.value = "cmake"
            await pilot.press("enter", "right", "escape")
            assert app.focused is app.query_one("#categories")
            assert app.model.search == "cmake"
            await pilot.press("d")
            assert all(not app.model.enabled(p.key) for p in registry.GROUPS[0].packages)
            assert "including hidden matches" in app.session.message
            search.value = "does not match any package"
            await pilot.pause()
            assert app.query_one("#empty").display
            assert app.query_one("#categories", OptionList).option_count == 0
            await pilot.press("right", "escape", "backspace")
            assert app.focused is app.query_one("#categories")
            await pilot.press("slash")
            search.value = ""
            await pilot.press("escape")
            assert app.query_one("#categories", OptionList).option_count == len(registry.GROUPS)
            await pilot.press("q")

    asyncio.run(check())


def test_mouse_persistent_settings_presets_and_autosave_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def check() -> None:
        app = MenuApp(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.click("#clang")
            assert app.model.settings.compiler == "clang"
            await pilot.click("#gpl")
            await pilot.click("#latest")
            settings = load_config(app.session.default_path, Logger()).settings
            assert (
                settings.compiler == "clang"
                and settings.latest
                and settings.enable_gpl_and_non_free
            )
            await pilot.press("p", "a")
            assert all(app.model.states.values())
            await pilot.press("u")
            assert not any(app.model.states.values())
            before = app.session.default_path.read_bytes()
            history = list(app.session.history)

            def fail(*args: object, **kwargs: object) -> None:
                raise OSError("disk full [link=https://example.invalid]untrusted[/link]\x1b[2J")

            monkeypatch.setattr("ffmpeg_build.menu.session.publish_atomically", fail)
            await pilot.click("#gcc")
            await pilot.pause()
            assert app.model.settings.compiler == "clang"
            assert app.query_one(RadioSet).pressed_index == 1
            assert app.session.default_path.read_bytes() == before
            assert app.session.history == history
            await pilot.click("#gpl")
            await pilot.pause()
            assert app.model.gpl and app.query_one("#gpl", Switch).value
            assert app.session.failed
            await pilot.press("q")

    asyncio.run(check())


def test_dialogs_text_editing_and_build_validation(tmp_path: Path) -> None:
    async def check() -> None:
        app = MenuApp(MenuModel({"mediainfo-cli": True}, BuildSettings()), tmp_path / "custom.toml")
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("e")
            assert isinstance(app.screen, SettingsScreen)
            jobs = app.screen.query_one("#jobs", Input)
            jobs.value = "0"
            await pilot.press("enter")
            assert isinstance(app.screen, SettingsScreen)
            jobs.value = "31"
            await pilot.press("end", "left", "backspace")
            assert jobs.value == "1"
            jobs.value = "3"
            await pilot.press("enter")
            assert app.session.result.launch.jobs == "3"
            await pilot.press("s")
            assert isinstance(app.screen, SaveScreen)
            target = tmp_path / "different.toml"
            app.screen.query_one(Input).value = str(target)
            await pilot.press("enter")
            assert app.session.default_path == target
            await pilot.press("b")
            assert isinstance(app.screen, HelpScreen)
            assert not app.session.result.start_build
            await pilot.press("escape", "F", "b")
            assert app.session.result.start_build
            assert app.session.result.saved_path == target
            assert load_config(target, Logger()).selection.enabled("zenlib")

    asyncio.run(check())


@pytest.mark.parametrize("size", [(120, 36), (80, 24), (40, 10)])
def test_save_dialog_arrow_focus_and_text_editing(tmp_path: Path, size: tuple[int, int]) -> None:
    async def check() -> None:
        original = tmp_path / "custom.toml"
        target = tmp_path / "saved [draft].toml"
        app = MenuApp(MenuModel({}, BuildSettings()), original)
        async with app.run_test(size=size) as pilot:
            await pilot.press("s")
            path = app.screen.query_one("#save-path", Input)
            path.value = str(target)
            await pilot.press("end", "left", "left", "right")
            assert app.focused is path
            assert path.cursor_position == len(str(target)) - 1
            assert path.value == str(target)
            for key, expected in (
                ("down", "cancel"),
                ("left", "cancel"),
                ("right", "save"),
                ("right", "save"),
                ("up", "save-path"),
                ("down", "save"),
                ("down", "save-path"),
                ("up", "save"),
                ("left", "cancel"),
                ("up", "save-path"),
                ("tab", "cancel"),
                ("tab", "save"),
                ("tab", "save-path"),
                ("shift+tab", "save"),
                ("left", "cancel"),
            ):
                await pilot.press(key)
                assert app.focused is app.screen.query_one(f"#{expected}")
            assert path.value == str(target)
            assert not target.exists() and not original.exists()
            await pilot.press("enter")
            assert not isinstance(app.screen, SaveScreen)
            assert app.session.default_path == original
            assert not target.exists()

            await pilot.press("s")
            app.screen.query_one("#save-path", Input).value = str(target)
            await pilot.press("down", "right", "enter")
            assert not isinstance(app.screen, SaveScreen)
            assert app.session.default_path == target
            assert load_config(target, Logger()).settings.compiler == "gcc"

    asyncio.run(check())


def test_save_dialog_arrows_allow_recovery_after_save_errors(tmp_path: Path) -> None:
    async def check() -> None:
        original = tmp_path / "custom.toml"
        app = MenuApp(MenuModel({}, BuildSettings()), original)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("s")
            path = app.screen.query_one("#save-path", Input)
            for invalid_path in ("", str(tmp_path)):
                path.value = invalid_path
                await pilot.press("down")
                if app.focused is app.screen.query_one("#cancel"):
                    await pilot.press("right")
                await pilot.press("enter")
                assert isinstance(app.screen, SaveScreen)
                assert app.focused is app.screen.query_one("#save")
                assert app.session.default_path == original
                error = app.screen.query_one("#save-error").render_line(0).text.strip()
                assert error.startswith(
                    "Enter a file path." if not invalid_path else "Save failed:"
                )
                # Button ignores repeat presses during its active animation.
                await pilot.pause(app.screen.query_one("#save", Button).active_effect_duration)
                await pilot.press("up")
                assert app.focused is path
            path.value = str(tmp_path / "recovered.toml")
            await pilot.press("down", "enter")
            assert not isinstance(app.screen, SaveScreen)
            assert app.session.default_path == tmp_path / "recovered.toml"
            assert app.session.default_path.is_file()

    asyncio.run(check())


def test_opening_saved_clang_config_never_rewrites_it(tmp_path: Path) -> None:
    async def check() -> None:
        path = tmp_path / "custom.toml"
        original = (
            '[build]\ncompiler="clang"\nenable_gpl_and_non_free=true\n[packages]\nffmpeg=true\n'
        )
        path.write_text(original)
        stamp = path.stat().st_mtime_ns
        app = MenuApp(
            MenuModel(
                {"ffmpeg": True}, BuildSettings(compiler="clang", enable_gpl_and_non_free=True)
            ),
            path,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.query_one(RadioSet).pressed_index == 1
            assert app.model.settings.compiler == "clang"
            assert not app.session.history
            assert path.read_text() == original and path.stat().st_mtime_ns == stamp
            await pilot.press("right", "enter")
            assert app.model.settings.compiler == "clang"
            assert app.focused is app.query_one("#compiler-category")
            assert not app.session.history
            assert path.read_text() == original and path.stat().st_mtime_ns == stamp

    asyncio.run(check())


@pytest.mark.parametrize("keys", [("p", "a", "b"), ("p", "down", "enter", "b")])
def test_all_preset_saves_every_package_before_build(tmp_path: Path, keys: tuple[str, ...]) -> None:
    async def check() -> None:
        path = tmp_path / "custom.toml"
        app = MenuApp(
            MenuModel(
                {}, BuildSettings(compiler="clang", latest=True, enable_gpl_and_non_free=True)
            ),
            path,
        )
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.press(*keys)
            assert app.session.result.start_build
            assert app.session.result.saved_path == path
            loaded = load_config(path, Logger())
            assert loaded.selection.states() == dict.fromkeys(registry.PACKAGE_NAMES, True)
            assert loaded.settings.compiler == "clang"
            assert loaded.settings.latest and loaded.settings.enable_gpl_and_non_free

    asyncio.run(check())
