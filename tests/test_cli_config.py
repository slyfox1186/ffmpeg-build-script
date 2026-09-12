from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from ffmpeg_build import registry
from ffmpeg_build.cli import parse_arguments
from ffmpeg_build.config import BuildSettings, Selection, default_states, load_config, render_config
from ffmpeg_build.main import Orchestrator, validate_build_settings
from ffmpeg_build.runtime.errors import UsageError
from ffmpeg_build.runtime.logging import Logger
from ffmpeg_build.usage import ACTIONS, ENVIRONMENT, OPTIONS, usage_text
from tests.conftest import REPO, invoke


@pytest.mark.parametrize("argv", [("--help",), ("--version",), (), ("--bad", "--help")])
def test_metadata_has_no_side_effects(tmp_path: Path, argv: tuple[str, ...]) -> None:
    root = tmp_path / "absent"
    result = invoke(root, *argv, FFMPEG_BUILD_DEBUG="on", DOWNLOAD_MAX_TIME="garbage")
    assert result.returncode == 0, result.stdout
    assert result.stdout == ("8.0.0\n" if argv == ("--version",) else usage_text())
    assert not root.exists()
    assert "--config ./custom.toml" in usage_text()
    assert "local.toml" not in usage_text()


def test_help_layout() -> None:
    for _label, description in (*ACTIONS, *OPTIONS, *ENVIRONMENT):
        line = next(line for line in usage_text().splitlines() if description in line)
        assert line.index(description) == 36


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (("--definitely-unknown",), "Unknown option '--definitely-unknown'."),
        (("--build", "--cleanup"), "'--build' and '--cleanup' are mutually exclusive."),
        (("--menu", "--build"), "'--build' and '--menu' are mutually exclusive."),
        (("--config",), "Missing value for '--config'."),
        (("--config", ""), "Invalid value for '--config'."),
        (("--config", "bad\tpath.toml"), "Invalid value for '--config'."),
        (("--compiler=bogus",), "Invalid compiler 'bogus'; expected 'gcc' or 'clang'."),
        (("--compiler", "bogus"), "Invalid compiler 'bogus'; expected 'gcc' or 'clang'."),
        (("--build", "--compiler", "-h"), "Invalid compiler '-h'"),
        (("--", "-h"), "Unexpected positional arguments: '-h'."),
        (("--", "--version"), "Unexpected positional arguments: '--version'."),
        (
            ("--config", "example.toml", "--definitely-unknown"),
            "Unknown option '--definitely-unknown'.",
        ),
        (("--jobs",), "Missing value for '--jobs'."),
        (("--compiler",), "Missing value for '--compiler'."),
        (("--config=a", "--config=b"), "'--config' may only be specified once."),
    ],
)
def test_invalid_cli(tmp_path: Path, argv: tuple[str, ...], message: str) -> None:
    root = tmp_path / "absent"
    result = invoke(root, *argv)
    assert result.returncode == 1, result.stdout
    assert message in result.stdout
    assert "Loaded package selection config" not in result.stdout
    assert "Usage:" not in result.stdout
    assert not root.exists()


@pytest.mark.parametrize("value", ["0", "-1", "abc", "8x", "", "08", "1\n"])
def test_invalid_jobs(tmp_path: Path, value: str) -> None:
    root = tmp_path / "absent"
    result = invoke(root, "--cleanup", f"--jobs={value}")
    assert result.returncode == 1
    assert f"Invalid jobs value '{value}'; expected a positive integer." in result.stdout.replace(
        "\n                 ", "\n"
    )
    assert not root.exists()


@pytest.mark.parametrize("argv", [("--jobs=8",), ("-j", "8"), ("--jobs", "8")])
def test_jobs_forms_reach_action(tmp_path: Path, argv: tuple[str, ...]) -> None:
    result = invoke(tmp_path / "absent", "--cleanup", *argv)
    assert result.returncode == 0
    assert "nothing to clean" in result.stdout
    assert parse_arguments(list(argv)).jobs == 8


def test_config_resolves_only_from_invocation_directory(tmp_path: Path) -> None:
    result = invoke(tmp_path / "absent", "--cleanup", "--config", "example.toml", cwd=tmp_path)
    assert result.returncode == 1
    assert f"Config file not found: '{tmp_path / 'example.toml'}'." in result.stdout
    assert "Loaded package selection config" not in result.stdout


def test_root_refusal(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    assert Orchestrator(REPO, ["--cleanup"]).run() == 1
    assert "as a normal user" in capsys.readouterr().err


def test_config_allowlist_and_alias(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "selection.toml"
    path.write_text(
        "[build]\nlatest = true\nenable_gpl_and_non_free = false\n[packages]\nffmpeg = true\njemalloc = true\nvulkan-headers = false\n"
    )
    loaded = load_config(path, Logger())
    output = capsys.readouterr().out
    assert f"Loaded package selection config: '{path}'" in output
    assert "run 'build-ffmpeg.py --cleanup' first" in output
    assert "run --cleanup" not in output
    assert loaded.settings.latest
    assert not loaded.settings.enable_gpl_and_non_free
    assert not loaded.selection.enabled("vulkan-headers-git")
    assert not loaded.selection.enabled("libopus")
    assert loaded.selection.explicitly_enabled("ffmpeg")
    assert Selection().enabled("libopus")
    with pytest.raises(UsageError, match="Unsupported package 'ffmepg'"):
        loaded.selection.enabled("ffmepg")


@pytest.mark.parametrize(
    ("text", "line", "message"),
    [
        (
            "[packages]\nvulkan-headers = true\nvulkan-headers-git = false\n",
            3,
            "Duplicate config key 'packages.vulkan-headers-git'",
        ),
        ("[packages]\nffmepg = true\n", 2, "Unsupported '[packages]' key 'ffmepg'"),
        ("[package]\n", 1, "Unsupported TOML table 'package'"),
        ("[build]\njobs = true\n", 2, "Unsupported '[build]' key 'jobs'"),
        ("[packages]\nffmpeg = TRUE\n", 2, "Unsupported config syntax"),
        ("[packages]\nffmpeg = 'true'\n", 2, "Unsupported config syntax"),
        ("[packages]\nffmpeg = [true]\n", 2, "Unsupported config syntax"),
        ("[packages]\n[packages]\n", 2, "Duplicate TOML table 'packages'"),
        ("ffmpeg = true\n", 1, "Unsupported TOML table '<root>'"),
        ("[build]\nlatest=true\nlatest=false\n", 3, "Duplicate config key 'build.latest'"),
    ],
)
def test_config_errors_name_exact_line(tmp_path: Path, text: str, line: int, message: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(text)
    with pytest.raises(UsageError) as caught:
        load_config(path, Logger())
    assert message in str(caught.value)
    assert f"'{path}:{line}'" in str(caught.value)


def test_generated_template_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "generated.toml"
    path.write_text(render_config(BuildSettings(), default_states()))
    loaded = load_config(path, Logger())
    assert set(loaded.selection.states()) == set(registry.PACKAGE_NAMES)
    assert len(loaded.selection.states()) == 127
    assert loaded.selection.states() == default_states()
    assert not loaded.selection.enabled("libjxl")
    assert not loaded.selection.enabled("libshaderc")


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("FFMPEG_BUILD_DEBUG", "on", "'FFMPEG_BUILD_DEBUG' must be 'ON' or 'OFF'; got 'on'"),
        ("CUDA_INSTALL", "maybe", "'CUDA_INSTALL' must be 'ask', 'always', or 'never'"),
        ("CUDA_ARCH_MODE", "bogus", "'CUDA_ARCH_MODE' must be 'native', 'all', or 'custom'"),
        ("CUDA_ARCH_MODE", "custom", "requires 'CUDA_ARCHITECTURES'"),
        ("DOWNLOAD_MAX_TIME", "abc", "'DOWNLOAD_MAX_TIME' must be a positive integer"),
        ("DOWNLOAD_RETRY", "-1", "'DOWNLOAD_RETRY' must be a non-negative integer"),
    ],
)
def test_settings_rejected_before_workspace(
    tmp_path: Path, name: str, value: str, message: str
) -> None:
    root = tmp_path / "absent"
    result = invoke(root, "--build", environment={name: value})
    assert result.returncode == 1
    assert message in result.stdout
    assert "Traceback" not in result.stdout
    assert not root.exists()


def test_valid_cuda_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_ARCH_MODE", "custom")
    monkeypatch.setenv("CUDA_ARCHITECTURES", "86 89")
    validate_build_settings(Selection(), "OFF")


def test_launcher_and_help_parse_on_old_python() -> None:
    for path in (
        REPO / "build-ffmpeg.py",
        REPO / "ffmpeg_build/usage.py",
        REPO / "ffmpeg_build/__init__.py",
    ):
        ast.parse(path.read_text(), feature_version=(3, 10))


def test_noninteractive_menu_fails_cleanly(tmp_path: Path) -> None:
    result = invoke(tmp_path / "absent", "--menu")
    assert result.returncode == 1
    assert "interactive menu needs a terminal" in result.stdout
    assert "Traceback" not in result.stdout
    assert not (tmp_path / "absent").exists()
