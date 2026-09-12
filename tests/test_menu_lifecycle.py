from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from ffmpeg_build import menu, registry
from ffmpeg_build.config import BuildSettings, default_states, load_config, render_config
from ffmpeg_build.main import Orchestrator
from ffmpeg_build.menu.app import MenuApp
from ffmpeg_build.menu.model import LaunchSettings, MenuModel
from ffmpeg_build.menu.session import MenuResult, MenuSession
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError, SignalStop, UsageError
from ffmpeg_build.runtime.logging import Logger
from tests.conftest import REPO


def test_reopened_menu_and_saved_build_reuse_identical_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BUILD_ROOT", str(tmp_path / "build"))
    settings = BuildSettings(compiler="clang", enable_gpl_and_non_free=True)
    states = dict.fromkeys(registry.PACKAGE_NAMES, True)
    path = tmp_path / "custom.toml"
    path.write_text(render_config(settings, states))
    seen: list[BuildContext] = []

    def verify_context(self: Orchestrator, context: BuildContext) -> None:
        context.packages.mkdir(parents=True, exist_ok=True)
        context.workspace.mkdir(exist_ok=True)
        self.configure_toolchain(context)
        self.source_compiler_flags(context)
        self.ensure_build_context(context)
        seen.append(context)

    def editor(
        states: dict[str, bool] | None,
        settings: BuildSettings,
        default_path: Path,
        launch: LaunchSettings,
    ) -> MenuResult:
        assert states == dict.fromkeys(registry.PACKAGE_NAMES, True)
        assert settings.compiler == "clang" and settings.enable_gpl_and_non_free
        assert default_path == path
        default_path.write_text(render_config(settings, states))
        return MenuResult(saved_path=path, start_build=True, settings=settings, launch=launch)

    monkeypatch.setattr(Orchestrator, "run_build", verify_context)
    monkeypatch.setattr(menu, "run_menu", editor)
    assert Orchestrator(REPO, ["--build", "--config", str(path)]).run() == 0
    marker = tmp_path / "build/packages/ffmpeg.done"
    marker.write_text("fixture-version\n")
    assert Orchestrator(REPO, ["--menu"]).run() == 0
    assert Orchestrator(REPO, ["--build", "--config", str(path)]).run() == 0
    assert len(seen) == 3
    assert all(context.compiler == "clang" and context.nonfree_and_gpl for context in seen)
    # A real compiler change must still reject old artifacts before reuse.
    with pytest.raises(BuildError, match="compiler was 'clang', is now 'gcc'"):
        Orchestrator(REPO, ["--build", "--config", str(path), "--gcc"]).run()
    assert marker.read_text() == "fixture-version\n"


@pytest.mark.parametrize("explicit", [False, True])
def test_menu_config_lookup_is_local_and_explicit_config_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "custom.toml").write_text("invalid config must never be read\n")
    invocation = tmp_path / "invocation"
    invocation.mkdir()
    monkeypatch.chdir(invocation)
    argv = ["--menu"]
    if explicit:
        (invocation / "custom.toml").write_text("invalid config must never be read\n")
        (invocation / "chosen.toml").write_text('[build]\ncompiler="clang"\n')
        argv.extend(["--config", "chosen.toml", "--gcc"])
    calls = []

    def editor(
        states: dict[str, bool] | None,
        settings: BuildSettings,
        default_path: Path,
        launch: LaunchSettings,
    ) -> MenuResult:
        assert settings.compiler == "gcc"
        assert states == (dict.fromkeys(registry.PACKAGE_NAMES, False) if explicit else None)
        assert default_path == invocation / ("chosen.toml" if explicit else "custom.toml")
        calls.append(default_path)
        return MenuResult()

    monkeypatch.setattr(menu, "run_menu", editor)
    assert Orchestrator(repo, argv).run() == 0
    assert len(calls) == 1


@pytest.mark.parametrize("invalid", ["syntax", "directory", "broken_symlink"])
def test_invalid_default_menu_config_is_not_silently_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "custom.toml"
    if invalid == "syntax":
        path.write_text('compiler="clang"\n')
    elif invalid == "directory":
        path.mkdir()
    else:
        path.symlink_to(tmp_path / "missing")

    def forbidden(*args: object) -> MenuResult:
        pytest.fail("Invalid saved config must not be replaced with the template")

    monkeypatch.setattr(menu, "run_menu", forbidden)
    with pytest.raises(UsageError):
        Orchestrator(REPO, ["--menu"]).run()
    if invalid == "syntax":
        assert path.read_text() == 'compiler="clang"\n'
    elif invalid == "directory":
        assert path.is_dir()
    else:
        assert path.is_symlink()


@pytest.mark.parametrize(
    "action", ["package", "category", "gpl", "latest", "compiler", "preset", "fix"]
)
def test_every_persistent_action_is_atomic_and_undoable(tmp_path: Path, action: str) -> None:
    model = MenuModel({"mediainfo-cli": True} if action == "fix" else {}, BuildSettings())
    session = MenuSession(model, tmp_path / "custom.toml")
    previous = session.snapshot()
    edits = {
        "package": lambda: model.toggle("cmake"),
        "category": lambda: model.set_group(registry.GROUPS[0].name, True),
        "gpl": lambda: setattr(model.settings, "enable_gpl_and_non_free", True),
        "latest": lambda: setattr(model.settings, "latest", True),
        "compiler": lambda: setattr(model.settings, "compiler", "clang"),
        "preset": lambda: model.apply_preset("all"),
        "fix": model.auto_fix_all,
    }
    assert session.change(edits[action], "Updated.")
    loaded = load_config(session.default_path, Logger())
    assert loaded.selection.states() == model.states
    assert render_config(loaded.settings, loaded.selection.states()) == render_config(
        model.settings, model.states
    )
    assert len(session.history) == 1
    assert session.undo()
    assert session.snapshot() == previous
    assert load_config(session.default_path, Logger()).selection.states() == previous[0]


@pytest.mark.parametrize("undo", [False, True])
def test_failed_autosave_restores_disk_ui_state_and_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, undo: bool
) -> None:
    session = MenuSession(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
    assert session.save(session.default_path)
    if undo:
        session.change(lambda: setattr(session.model.settings, "compiler", "clang"), "Compiler.")
    data, state, history = (
        session.default_path.read_bytes(),
        session.snapshot(),
        list(session.history),
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("fixture disk full")

    monkeypatch.setattr("ffmpeg_build.menu.session.publish_atomically", fail)
    assert not (
        session.undo() if undo else session.change(lambda: session.model.toggle("cmake"), "Toggle.")
    )
    assert session.failed and "Change reverted" in session.message
    assert session.default_path.read_bytes() == data
    assert session.snapshot() == state and session.history == history


def test_save_as_and_symlink_failure(tmp_path: Path) -> None:
    session = MenuSession(MenuModel({}, BuildSettings()), tmp_path / "original.toml")
    assert session.save(session.default_path)
    original = session.default_path
    data = original.read_bytes()
    link = tmp_path / "link.toml"
    link.symlink_to(original)
    assert not session.save(link)
    assert session.default_path == original and original.read_bytes() == data
    target = tmp_path / "new.toml"
    assert session.save(target)
    assert session.change(lambda: session.model.toggle("ffmpeg"), "FFmpeg.")
    assert load_config(target, Logger()).selection.enabled("ffmpeg")
    assert original.read_bytes() == data


def test_invalid_save_and_following_noop_preserve_file_and_clear_stale_error(
    tmp_path: Path,
) -> None:
    session = MenuSession(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
    assert session.save(session.default_path)
    previous = session.default_path.read_bytes()
    session.model.settings.compiler = "invalid"
    assert not session.save(tmp_path / "other.toml")
    assert session.failed and "Compiler must be" in session.message
    assert not (tmp_path / "other.toml").exists()
    session.model.settings.compiler = "gcc"
    assert session.change(session.model.auto_fix_all, "Requirements checked.")
    assert not session.failed and session.message == "No changes to save."
    assert not session.history and session.default_path.read_bytes() == previous


def test_repeated_build_preparation_never_retains_success_after_failure(tmp_path: Path) -> None:
    session = MenuSession(MenuModel({}, BuildSettings()), tmp_path / "custom.toml")
    assert session.prepare_build()
    previous = session.default_path.read_bytes()
    session.result.launch.jobs = "invalid"
    assert not session.prepare_build()
    assert not session.result.start_build
    assert session.failed and session.default_path.read_bytes() == previous


@pytest.mark.parametrize("invalid", ["requirements", "launch"])
def test_build_validation_preserves_config(tmp_path: Path, invalid: str) -> None:
    session = MenuSession(
        MenuModel({"mediainfo-cli": True} if invalid == "requirements" else {}, BuildSettings()),
        tmp_path / "custom.toml",
    )
    session.save(session.default_path)
    before = session.default_path.read_bytes()
    if invalid == "launch":
        session.result.launch.build_root = "/etc"
    assert not session.prepare_build()
    assert not session.result.start_build and session.failed
    assert session.default_path.read_bytes() == before


@pytest.mark.parametrize(
    "failure",
    [None, KeyboardInterrupt(), EOFError(), SignalStop("TERM", 143), ValueError("fixture")],
)
def test_clear_runs_after_terminal_restoration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: BaseException | None
) -> None:
    events: list[str] = []
    result = MenuResult(saved_path=tmp_path / "saved.toml", start_build=True)

    def run(self: MenuApp) -> MenuResult:
        try:
            if failure is not None:
                raise failure
            return result
        finally:
            events.append("restored")

    def clear(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["clear"] and events == ["restored"]
        events.append("clear")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(MenuApp, "run", run)
    monkeypatch.setattr(subprocess, "run", clear)
    if isinstance(failure, (SignalStop, ValueError)):
        with pytest.raises(type(failure)):
            menu.run_menu(None, BuildSettings(), tmp_path / "custom.toml")
    else:
        returned = menu.run_menu(None, BuildSettings(), tmp_path / "custom.toml")
        assert returned.start_build is (failure is None)
    assert events == ["restored", "clear"]


@pytest.mark.parametrize("failure", ["missing", "failed", "timeout"])
def test_clear_failure_warns_and_preserves_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    result = MenuResult(saved_path=tmp_path / "saved.toml", start_build=True)

    def clear(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if failure == "missing":
            raise FileNotFoundError("clear")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 5)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(MenuApp, "run", lambda self: result)
    monkeypatch.setattr(subprocess, "run", clear)
    assert menu.run_menu(default_states(), BuildSettings(), tmp_path / "custom.toml") is result
    assert "Warning:" in capsys.readouterr().err


@pytest.mark.parametrize("tty", [False, True])
def test_unavailable_menu_fails_before_clear_or_config_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tty: bool
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: tty)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: tty)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(menu, "_clear_terminal", lambda: pytest.fail("No active terminal to clear"))
    with pytest.raises(RuntimeError, match="requires Textual" if tty else "needs a terminal"):
        menu.run_menu(None, BuildSettings(), tmp_path / "custom.toml")
    assert not (tmp_path / "custom.toml").exists()
