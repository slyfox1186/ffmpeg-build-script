from __future__ import annotations

import ast
import importlib.util
import os
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

from tests.conftest import REPO


def launcher_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launcher", REPO / "build-ffmpeg.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def executable(path: Path, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def fake_python(path: Path, version: str, level: str = "final") -> Path:
    return executable(path, f"echo '{version} {level}'\n")


@pytest.fixture
def launcher(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    """A launcher that sees only the conda installs and interpreters a test creates."""
    module = launcher_module()
    monkeypatch.delenv("CONDA_EXE", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "path"))
    monkeypatch.setattr(module, "CONDA_ROOTS", (str(tmp_path / "home/miniconda3"),))
    monkeypatch.setattr(module.sys, "executable", str(tmp_path / "missing/python3"))
    original_listdir = os.listdir

    def listdir(directory: str) -> list[str]:
        if directory == "/usr/bin":
            raise FileNotFoundError(directory)
        return original_listdir(directory)

    monkeypatch.setattr(module.os, "listdir", listdir)
    return module


def conda_install(root: Path) -> Path:
    executable(root / "bin/conda")
    return root


def test_launcher_and_usage_parse_on_python_310() -> None:
    for path in (REPO / "build-ffmpeg.py", REPO / "ffmpeg_build/usage.py"):
        ast.parse(path.read_text(), filename=str(path), feature_version=(3, 10))
    assert (REPO / "ffmpeg_build/__init__.py").read_text() == ""


def test_menu_packages_match_pyproject_extra() -> None:
    project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    assert list(launcher_module().MENU_PACKAGES) == project["optional-dependencies"]["menu"]


def test_launcher_metadata_never_resolves_interpreter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = launcher_module()

    def forbidden() -> None:
        pytest.fail("Metadata must not resolve interpreters or ask for consent")

    monkeypatch.setattr(module, "resolve_interpreter", forbidden)
    assert module.main(["--version"]) == 0
    assert capsys.readouterr().out == "8.1.0\n"
    assert module.main([]) == 0
    assert "--build" in capsys.readouterr().out


def test_conda_roots_come_from_conda_exe_path_and_home(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    active = conda_install(tmp_path / "active")
    on_path = conda_install(tmp_path / "forge")
    home = conda_install(tmp_path / "home/miniconda3")
    executable(on_path / "condabin/conda")
    monkeypatch.setenv("CONDA_EXE", str(active / "bin/conda"))
    monkeypatch.setenv("PATH", os.pathsep.join(["", "relative", str(on_path / "condabin")]))
    assert launcher.conda_roots() == [str(active), str(on_path), str(home)]
    monkeypatch.setenv("CONDA_EXE", str(home / "bin/conda"))
    monkeypatch.setenv("PATH", "")
    assert launcher.conda_roots() == [str(home)]


def test_existing_conda_environment_is_used_over_system_python(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = conda_install(tmp_path / "home/miniconda3")
    python = fake_python(root / "envs/install-ffmpeg/bin/python", "3.14")
    fake_python(tmp_path / "path/python3.14", "3.14")

    def forbidden() -> None:
        pytest.fail("System Python must not be used while conda is available")

    monkeypatch.setattr(launcher, "resolve_system_interpreter", forbidden)
    assert launcher.resolve_interpreter() == str(python)


def test_system_python_is_used_only_without_conda(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = fake_python(tmp_path / "path/python3", "3.12")
    assert launcher.conda_roots() == []
    monkeypatch.setattr(
        launcher, "resolve_conda_interpreter", lambda roots: pytest.fail("no conda exists")
    )
    assert launcher.resolve_interpreter() == str(python)


@pytest.mark.parametrize("answer", [False, True])
def test_missing_environment_needs_consent_and_never_falls_back(
    launcher: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    answer: bool,
) -> None:
    root = conda_install(tmp_path / "home/miniconda3")
    fake_python(tmp_path / "path/python3", "3.14")
    monkeypatch.setattr(launcher, "ask_consent", lambda question: answer)
    created: list[str] = []

    def create(conda_root: str) -> bool:
        created.append(conda_root)
        return False

    monkeypatch.setattr(launcher, "create_conda_environment", create)
    assert launcher.resolve_interpreter() is None
    assert created == ([str(root)] if answer else [])
    if not answer:
        error = capsys.readouterr().err
        assert "-c conda-forge --override-channels python=3.14" in error
        assert f"-p {root}/envs/install-ffmpeg" in error


def test_created_environment_installs_only_menu_packages(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = conda_install(tmp_path / "home/miniconda3")
    commands: list[list[str]] = []

    class Completed:
        returncode = 0

    def run(command: list[str], check: bool) -> Completed:
        commands.append(command)
        if command[1] == "create":
            fake_python(root / "envs/install-ffmpeg/bin/python", "3.14")
        return Completed()

    monkeypatch.setattr(launcher.subprocess, "run", run)
    assert launcher.create_conda_environment(str(root))
    assert commands == [
        launcher.conda_create_command(str(root)),
        [str(root / "envs/install-ffmpeg/bin/python"), "-m", "pip", "install", "textual>=8.2.8"],
    ]


def test_incompatible_conda_environment_reports_remedy_without_fallback(
    launcher: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = conda_install(tmp_path / "home/miniconda3")
    fake_python(root / "envs/install-ffmpeg/bin/python", "3.11")
    fake_python(tmp_path / "path/python3", "3.14")
    assert launcher.resolve_interpreter() is None
    error = capsys.readouterr().err
    assert "has Python 3.11" in error
    assert f"env remove -y -p {root}/envs/install-ffmpeg" in error


def test_unreadable_conda_version_is_not_reported_as_too_old(
    launcher: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = conda_install(tmp_path / "home/miniconda3")
    executable(root / "envs/install-ffmpeg/bin/python", "exit 1\n")
    assert launcher.resolve_interpreter() is None
    assert "Could not determine the Python version" in capsys.readouterr().err


def test_system_python_prefers_newest_stable_release(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first, second = tmp_path / "path", tmp_path / "later"
    fake_python(first / "python3", "3.10")
    fake_python(first / "python3.15", "3.15", "candidate")
    fake_python(second / "python3.12", "3.12")
    newest = fake_python(second / "python3.13", "3.13")
    fake_python(tmp_path / "python3.99", "3.99")
    monkeypatch.setenv("PATH", os.pathsep.join(["", str(first), "relative", str(second)]))
    monkeypatch.chdir(tmp_path)
    assert launcher.resolve_system_interpreter() == str(newest)


def test_system_python_ties_keep_path_order(
    launcher: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = fake_python(tmp_path / "path/python3", "3.12")
    fake_python(tmp_path / "later/python3", "3.12")
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path / "path"), str(tmp_path / "later")]))
    assert launcher.resolve_system_interpreter() == str(first)


def test_no_conda_and_no_compatible_python_reports_both_remedies(
    launcher: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_python(tmp_path / "path/python3", "3.11")
    assert launcher.resolve_interpreter() is None
    error = capsys.readouterr().err
    assert "Install Miniconda at ~/miniconda3" in error
    assert "install Python 3.12 or newer" in error


def test_resolution_guard_is_not_inherited_by_the_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = launcher_module()
    seen: list[str | None] = []

    def run_build(argv: list[str]) -> int:
        seen.append(os.environ.get(module.RESOLVED_GUARD))
        return 0

    monkeypatch.setenv(module.RESOLVED_GUARD, "1")
    monkeypatch.setattr("ffmpeg_build.main.main", run_build)
    assert module.main(["--build"]) == 0
    assert seen == [None]
