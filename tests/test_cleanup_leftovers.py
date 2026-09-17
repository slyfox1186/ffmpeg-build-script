from __future__ import annotations

from pathlib import Path

import pytest

from ffmpeg_build.main import Orchestrator
from ffmpeg_build.runtime.state import write_build_root_marker

# Repository content that a sweep must never touch, mirroring the published
# tree: directories, a tracked config and the user's own local config.
REPOSITORY_CONTENT = ("docs", "ffmpeg_build", "tests", "tools", ".github")


def make_checkout(root: Path) -> Path:
    for name in REPOSITORY_CONTENT:
        (root / name).mkdir(parents=True)
        (root / name / "keep.py").write_text("tracked\n")
    (root / ".git").mkdir()
    (root / ".git/__pycache__").mkdir()
    (root / "example.toml").write_text("tracked\n")
    (root / "custom.toml").write_text("mine\n")
    for name in ("ffbuild", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"):
        (root / name).mkdir()
        (root / name / "junk").write_text("junk\n")
    (root / "ffmpeg_build_script.egg-info").mkdir()
    (root / "ffmpeg_build/__pycache__").mkdir()
    (root / "tools/__pycache__").mkdir()
    build_root = root / "build"
    (build_root / "workspace").mkdir(parents=True)
    write_build_root_marker(build_root)
    return build_root


def orchestrator_for(root: Path, build_root: Path) -> Orchestrator:
    orchestrator = Orchestrator(root, ["--cleanup"])
    orchestrator.build_root = build_root
    return orchestrator


def answer(monkeypatch: pytest.MonkeyPatch, reply: str) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": reply)


def leftovers_remaining(root: Path) -> list[str]:
    return [
        name
        for name in (
            "ffbuild",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "ffmpeg_build_script.egg-info",
            "ffmpeg_build/__pycache__",
            "tools/__pycache__",
            "build",
        )
        if (root / name).exists()
    ]


def assert_checkout_intact(root: Path) -> None:
    for name in REPOSITORY_CONTENT:
        assert (root / name / "keep.py").read_text() == "tracked\n"
    assert (root / "example.toml").read_text() == "tracked\n"
    assert (root / "custom.toml").read_text() == "mine\n"
    assert (root / ".git/__pycache__").is_dir()


def test_cleanup_removes_build_root_and_every_leftover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    build_root = make_checkout(tmp_path)
    answer(monkeypatch, "yes")
    orchestrator_for(tmp_path, build_root).cleanup()
    assert leftovers_remaining(tmp_path) == []
    assert_checkout_intact(tmp_path)
    assert "Removed build leftover" in capsys.readouterr().out


def test_declining_keeps_every_leftover(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_root = make_checkout(tmp_path)
    answer(monkeypatch, "no")
    orchestrator_for(tmp_path, build_root).cleanup()
    assert "build" in leftovers_remaining(tmp_path)
    assert (tmp_path / "ffbuild/junk").is_file()


def test_leftovers_are_swept_without_a_build_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_root = make_checkout(tmp_path)
    (build_root / "workspace").rmdir()
    (build_root / ".ffmpeg-build-root").unlink()
    build_root.rmdir()
    answer(monkeypatch, "yes")
    orchestrator_for(tmp_path, build_root).cleanup()
    assert leftovers_remaining(tmp_path) == []
    assert_checkout_intact(tmp_path)


def test_non_interactive_cleanup_removes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_root = make_checkout(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    orchestrator_for(tmp_path, build_root).cleanup()
    assert (tmp_path / "ffbuild").is_dir()
    assert build_root.is_dir()


def test_symlinked_leftover_is_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    build_root = make_checkout(checkout)
    outside = tmp_path / "outside"
    (outside / "keep").mkdir(parents=True)
    (checkout / ".ruff_cache/junk").unlink()
    (checkout / ".ruff_cache").rmdir()
    (checkout / ".ruff_cache").symlink_to(outside, target_is_directory=True)
    answer(monkeypatch, "yes")
    orchestrator_for(checkout, build_root).cleanup()
    assert (checkout / ".ruff_cache").is_symlink()
    assert (outside / "keep").is_dir()


@pytest.mark.parametrize("state", ["marked", "empty", "user-owned"])
def test_legacy_roots_go_only_when_they_are_ours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    build_root = make_checkout(tmp_path)
    legacy = tmp_path / "workspace"
    legacy.mkdir()
    if state == "marked":
        write_build_root_marker(legacy)
    elif state == "user-owned":
        (legacy / "notes.txt").write_text("mine\n")
    answer(monkeypatch, "yes")
    orchestrator_for(tmp_path, build_root).cleanup()
    assert legacy.exists() == (state == "user-owned")
    if state == "user-owned":
        assert (legacy / "notes.txt").read_text() == "mine\n"
