"""Isolated workspaces; subprocess fixtures never install software or use the network."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from ffmpeg_build.cli import Arguments
from ffmpeg_build.config import BuildSettings, Selection
from ffmpeg_build.main import Orchestrator
from ffmpeg_build.runtime.context import BuildContext

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in tuple(os.environ):
        if name.startswith(("CUDA_", "DOWNLOAD_", "FFMPEG_BUILD_")) or name in (
            "BUILD_ROOT",
            "VERSION_CHECK_MAX_TIME",
            "GIT_OPERATION_TIMEOUT",
            "GIT_CLONE_TIMEOUT",
            "HOST_MUTATION_LOCK_TIMEOUT",
            "FREEDESKTOP_RELEASE_CONNECT_TIMEOUT",
            "FREEDESKTOP_RELEASE_INDEX_MAX_TIME",
        ):
            monkeypatch.delenv(name)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("FFMPEG_BUILD_INTERPRETER_RESOLVED", "1")


@pytest.fixture
def context(tmp_path: Path) -> BuildContext:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = tmp_path / "build"
    context = orchestrator.build_context(Arguments(), BuildSettings(), Selection())
    context.packages.mkdir(parents=True)
    context.workspace.mkdir()
    context.log_file.touch()
    orchestrator.configure_toolchain(context)
    orchestrator.source_compiler_flags(context)
    return context


@pytest.fixture
def stub(tmp_path: Path) -> Callable[[str, str], Path]:
    """Create an executable Python fixture, bound to the test interpreter."""

    def create(name: str, source: str) -> Path:
        target = tmp_path / "bin" / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(f"#!{sys.executable}\n" + source, encoding="utf-8")
        target.chmod(0o755)
        return target

    return create


def invoke(
    root: Path,
    *argv: str,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    **overrides: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(REPO / "build-ffmpeg.py"), *argv],
        env={**os.environ, "BUILD_ROOT": str(root), **(environment or {}), **overrides},
        cwd=cwd or REPO,
        input="",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=20,
    )
