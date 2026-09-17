from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from ffmpeg_build import registry
from ffmpeg_build.cli import Arguments
from ffmpeg_build.config import BuildSettings, Selection, default_states
from ffmpeg_build.main import Orchestrator
from ffmpeg_build.menu.model import LaunchSettings, MenuModel
from ffmpeg_build.menu.session import MenuResult
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError, UsageError
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
    network = registry.GROUPS[2]
    model.search = network.title
    assert all(model.matches_search(package) for package in network.packages)


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


@pytest.mark.parametrize("gpl", [False, True])
def test_fix_srt_requirements_includes_newly_enabled_tls_dependencies(gpl: bool) -> None:
    model = MenuModel({"srt": True}, BuildSettings(enable_gpl_and_non_free=gpl))
    assert set(model.auto_fix("srt")) == ({"openssl", "zlib"} if gpl else set())
    assert not model.issues()


@pytest.mark.parametrize(
    ("field", "value"),
    [
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


@pytest.mark.parametrize("targets", ["89 9999999999999999999999", "８９", "-1"])
def test_custom_cuda_menu_targets_rejected_before_save(targets: str) -> None:
    with pytest.raises(UsageError, match="numeric targets"):
        LaunchSettings(cuda_arch_mode="custom", cuda_architectures=targets).validate()


@pytest.mark.parametrize("tilde", [False, True])
def test_menu_build_uses_edited_settings(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tilde: bool
) -> None:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = context.cwd
    path = tmp_path / "custom.toml"
    path.write_text(
        '[build]\ncompiler="clang"\nlatest=false\nenable_gpl_and_non_free=false\n[packages]\nffmpeg=true\n'
    )
    root = str(tmp_path / "edited-build")
    if tilde:
        monkeypatch.setenv("HOME", str(tmp_path))
    launch = LaunchSettings(
        jobs="3",
        cuda_install="never",
        build_root="~/edited-build" if tilde else root,
    )
    monkeypatch.setattr(
        "ffmpeg_build.menu.run_menu",
        lambda *args: MenuResult(saved_path=path, start_build=True, launch=launch),
    )
    seen: list[BuildContext] = []
    monkeypatch.setattr(orchestrator, "run_build", seen.append)
    args = Arguments()
    args.compiler = "gcc"
    args.latest = True
    args.nonfree_and_gpl = True
    orchestrator.run_menu(args, BuildSettings(), Selection())
    built = seen[0]
    assert built.compiler == "clang" and built.build_threads == 3
    assert built.cwd == Path(root)
    assert not built.latest and not built.nonfree_and_gpl
    assert os.environ["CUDA_INSTALL"] == "never"
    assert built.selection.enabled("ffmpeg") and not built.selection.enabled("x264")


def test_invalid_environment_is_rejected_before_menu_can_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOWNLOAD_MAX_TIME", "invalid")

    def forbidden(*args: object) -> MenuResult:
        pytest.fail("Invalid environment opened an editor that can overwrite configuration")

    monkeypatch.setattr("ffmpeg_build.menu.run_menu", forbidden)
    with pytest.raises(UsageError, match="DOWNLOAD_MAX_TIME"):
        Orchestrator(REPO, []).run_menu(Arguments(), BuildSettings(), Selection())


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
