from __future__ import annotations

import importlib.util
import json
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from ffmpeg_build import registry
from ffmpeg_build.cli import Arguments
from ffmpeg_build.config import BuildSettings, Selection, default_states, load_config
from ffmpeg_build.main import Orchestrator
from ffmpeg_build.menu.app import MenuResult
from ffmpeg_build.menu.model import LaunchSettings, MenuModel
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError, UsageError
from ffmpeg_build.runtime.logging import Logger
from tests.conftest import REPO
from tools import compiler_versions, git_repo_version


def test_menu_selection_presets_and_search() -> None:
    model = MenuModel({}, BuildSettings())
    for preset in ("all", "none", "template", "minimal"):
        model.apply_preset(preset)
        if preset == "all":
            assert all(model.enabled(key) for key in registry.PACKAGE_NAMES)
        elif preset == "none":
            assert not any(model.enabled(key) for key in registry.PACKAGE_NAMES)
        elif preset == "template":
            assert model.states == default_states()
        else:
            assert model.enabled("ffmpeg") and model.enabled("cmake")
            assert not model.enabled("x264")
    model.apply_preset("none")
    model.toggle("libopus")
    assert model.enabled("libopus")
    assert not model.to_selection().enabled("ffmpeg")
    model.search = "OPUS"
    assert model.matches_search(registry.PACKAGES["libopus"])
    assert not model.matches_search(registry.PACKAGES["x264"])
    group = registry.GROUPS[0]
    model.set_group(group.name, True)
    assert model.enabled_count(group) == len(group.packages)
    model.set_group(group.name, False)
    assert model.enabled_count(group) == 0


def test_menu_transitive_and_conditional_requirements() -> None:
    model = MenuModel({"mediainfo-cli": True}, BuildSettings())
    assert model.issues()[0].blocking
    assert set(model.auto_fix("mediainfo-cli")) == {"mediainfo-lib", "zenlib"}
    assert not model.issues()
    model = MenuModel({"lilv": True}, BuildSettings())
    assert not model.issues()[0].blocking
    assert {"lv2-git", "serd", "zix", "sord", "sratom"} <= set(model.auto_fix_all())
    assert not model.issues()
    model = MenuModel(
        {"gnutls": True, "openssl": True}, BuildSettings(enable_gpl_and_non_free=True)
    )
    assert model.auto_fix("gnutls") == []
    assert model.auto_fix("openssl") == ["zlib"]
    assert "skipped: OpenSSL" in model.status_note(registry.PACKAGES["gnutls"])
    model.states.update(x264=True, libdvdread=True)
    model.settings.enable_gpl_and_non_free = False
    assert "waiting for GPL" in model.status_note(registry.PACKAGES["x264"])
    assert "builds, FFmpeg option needs GPL" in model.status_note(registry.PACKAGES["libdvdread"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("compiler", "bad"),
        ("jobs", "0"),
        ("cuda_install", "yes"),
        ("cuda_arch_mode", "bad"),
        ("cuda_arch_mode", "custom"),
        ("build_root", "/path with spaces"),
    ],
)
def test_launch_settings_validation(field: str, value: str) -> None:
    launch = LaunchSettings()
    setattr(launch, field, value)
    with pytest.raises(UsageError):
        launch.validate()


def test_menu_build_uses_edited_settings(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = context.cwd
    path = tmp_path / "custom.toml"
    path.write_text(
        "[build]\nlatest=false\nenable_gpl_and_non_free=false\n[packages]\nffmpeg=true\n"
    )
    root = str(tmp_path / "edited-build")
    launch = LaunchSettings(compiler="clang", jobs="3", cuda_install="never", build_root=root)
    monkeypatch.setattr(
        "ffmpeg_build.menu.app.run_menu",
        lambda *args: MenuResult(saved_path=path, start_build=True, launch=launch),
    )
    seen: list[BuildContext] = []
    monkeypatch.setattr(orchestrator, "run_build", seen.append)
    args = Arguments()
    args.latest = True
    args.nonfree_and_gpl = True
    orchestrator.run_menu(args, BuildSettings(), Selection())
    built = seen[0]
    assert built.compiler == "clang" and built.build_threads == 3
    assert built.cwd == Path(root)
    assert not built.latest and not built.nonfree_and_gpl
    assert os.environ["CUDA_INSTALL"] == "never"
    assert built.selection.enabled("ffmpeg") and not built.selection.enabled("x264")


def test_real_terminal_menu_save_and_launch(tmp_path: Path) -> None:
    import fcntl

    output = tmp_path / "result.json"
    config = tmp_path / "custom.toml"
    code = """import json, pathlib, sys
from ffmpeg_build.config import BuildSettings
from ffmpeg_build.menu.app import run_menu
result=run_menu(None, BuildSettings(), pathlib.Path(sys.argv[1]))
pathlib.Path(sys.argv[2]).write_text(json.dumps({'build':result.start_build, 'path':str(result.saved_path), 'compiler':result.launch.compiler, 'jobs':result.launch.jobs}))
"""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 140, 0, 0))
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(config), str(output)],
        cwd=REPO,
        env={**os.environ, "TERM": "xterm-256color"},
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    transcript = bytearray()

    def expect(needle: bytes) -> None:
        deadline = time.monotonic() + 10
        while needle not in transcript:
            assert process.poll() is None, transcript.decode(errors="replace")
            assert time.monotonic() < deadline, transcript.decode(errors="replace")
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                transcript.extend(os.read(master, 65536))
        transcript.clear()

    try:
        expect(b"FFmpeg package selection")
        os.write(master, b"e")
        expect(b"Launch settings")
        os.write(master, b"c")
        expect(b"Compiler (gcc/clang)")
        os.write(master, b"clang\n")
        expect(b"updated")
        os.write(master, b"j")
        expect(b"Jobs (auto")
        os.write(master, b"3\n")
        os.write(master, b"q")
        expect(b"FFmpeg package selection")
        os.write(master, b"b")
        expect(b"Save to:")
        os.write(master, b"\n")
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
    result = json.loads(output.read_text())
    assert result == {"build": True, "path": str(config), "compiler": "clang", "jobs": "3"}
    loaded = load_config(config, Logger())
    assert loaded.selection.states() == default_states()


def launcher_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launcher", REPO / "build-ffmpeg.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_metadata_never_resolves_interpreter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = launcher_module()

    def forbidden() -> None:
        pytest.fail("Metadata must not resolve interpreters or ask for consent")

    monkeypatch.setattr(module, "resolve_conda_interpreter", forbidden)
    assert module.main(["--version"]) == 0
    assert capsys.readouterr().out == "8.0.0\n"


def test_launcher_declined_environment_is_not_created(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = launcher_module()
    conda = tmp_path / "bin/conda"
    conda.parent.mkdir()
    conda.touch()
    conda.chmod(0o755)
    monkeypatch.setattr(module, "CONDA_ROOT", str(tmp_path))
    monkeypatch.setattr(module, "ask_consent", lambda question: False)

    def forbidden(*args: object) -> None:
        pytest.fail("Declining consent must not create the environment")

    monkeypatch.setattr(module, "create_conda_environment", forbidden)
    assert module.resolve_conda_interpreter() is None


@pytest.mark.parametrize(
    "url", ["http://example.test/repo", "ssh://example.test/repo", "https://example.test/repo\n"]
)
def test_git_diagnostic_rejects_unsafe_url(url: str) -> None:
    with pytest.raises(BuildError):
        git_repo_version.latest_stable_version(url)


def test_git_diagnostic_selects_stable_numeric_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ffmpeg_build.runtime.versions.VersionResolver.remote_tag_names",
        lambda *args: ["v3.9", "v3.10", "v4.0rc1", "v9.0^{}", "v3.10.2"],
    )
    assert git_repo_version.latest_stable_version("https://example.test/repo", "v") == "3.10.2"
    assert git_repo_version.latest_stable_version("https://example.test/repo") == "3.10.2"
    assert git_repo_version.main([]) == 2


def test_compiler_diagnostic(
    stub: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    old = stub("gcc-9", "print('9.5.0')\n")
    new = stub("gcc-13", "print('13.3.0')\n")
    stub("gcc-untrusted", "print('99.0.0')\n")
    assert compiler_versions.discover_installed_highest("gcc", [old.parent]) == ("13.3.0", new)
    assert not compiler_versions.compiler_basename_matches("gcc", "gcc-untrusted")
    assert compiler_versions.compiler_basename_matches("clang++", "clang++-20")
    monkeypatch.setattr(
        compiler_versions, "capture", lambda args: "gcc-9/noble\ngcc-13/noble\ngcc-999-doc/noble\n"
    )
    assert compiler_versions.highest_repository_major("gcc") == "13"
    assert compiler_versions.main(["unexpected"]) == 2


def test_launcher_prefers_compatible_system_python(monkeypatch: pytest.MonkeyPatch) -> None:
    module = launcher_module()
    monkeypatch.setattr(module.os, "access", lambda path, mode: True)
    monkeypatch.setattr(module, "interpreter_version", lambda path: (3, 12))
    assert module.resolve_system_interpreter() == "/usr/bin/python3"
