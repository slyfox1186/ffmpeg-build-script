from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from ffmpeg_build import registry
from ffmpeg_build.cli import Arguments
from ffmpeg_build.config import BuildSettings, Selection
from ffmpeg_build.main import Orchestrator
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.fetchers import GIT_RELEASE_PREFIXES
from tests.conftest import REPO


@pytest.mark.parametrize("version", ["1.98.1", "2.0.0"])
def test_rust_tracks_official_stable_channel(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    monkeypatch.setattr(
        context.resolver,
        "fetch_text",
        lambda url: f'[pkg.rust]\nversion="{version} (commit date)"\n',
    )
    assert context.versions.rust() == version


@pytest.mark.parametrize(
    "payload", ["", "not TOML", '[pkg.rust]\nversion="2.0.0-beta.1"', "[pkg.rust]\nversion=12"]
)
def test_invalid_rust_channel_is_not_a_release(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    monkeypatch.setattr(context.resolver, "fetch_text", lambda url: payload)
    assert context.versions.rust() is None


def test_cargo_c_and_cython_ignore_prereleases_and_yanked_files(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    cargo = "\n".join(
        json.dumps({"vers": version, "yanked": yanked})
        for version, yanked in (
            ("0.10.24+cargo-0.98.0", False),
            ("0.11.0+cargo-1.0.0", False),
            ("1.0.0-beta.1", False),
            ("0.12.0+cargo-1.1.0", True),
        )
    )
    cython = json.dumps(
        {
            "releases": {
                "3.2.8": [{"yanked": False}],
                "3.10.0": [{"yanked": False}],
                "4.0.0rc1": [{"yanked": False}],
                "3.11.0": [{"yanked": True}],
                "3.12.0": [],
            }
        }
    )

    def fetch(url: str) -> str:
        return cargo if "index.crates.io" in url else cython

    monkeypatch.setattr(context.resolver, "fetch_text", fetch)
    assert context.versions.cargo_c() == "0.11.0+cargo-1.0.0"
    assert context.versions.cython() == "3.10.0"


@pytest.mark.parametrize(
    "method", ["rust", "cargo_c", "cython", "lame", "gnutls", "giflib", "opencore_amr", "xvidcore"]
)
def test_unreachable_indexes_never_choose_a_fixed_fallback(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    monkeypatch.setattr(context.resolver, "fetch_text", lambda *args, **kwargs: None)
    assert getattr(context.versions, method)() is None


def test_lame_advances_between_series_and_ignores_beta_directories(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        context.resolver,
        "fetch_text",
        lambda *args, **kwargs: "\n".join(
            (
                "/lame/3.100/lame-3.100.tar.gz",
                "/lame/4.0/lame-4.0.tar.gz",
                "/lame/5.0beta/lame-5.0.tar.gz",
                "/lame/4.1/lame-4.1rc1.tar.gz",
            )
        ),
    )
    assert context.versions.lame() == "4.0"


@pytest.mark.parametrize("newest", [None, "gnutls-4.1.2.tar.xz gnutls-4.1.3-rc1.tar.xz"])
def test_gnutls_discovers_new_series_without_silent_network_downgrade(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, newest: str | None
) -> None:
    def fetch(url: str) -> str | None:
        if url.endswith("gnutls/"):
            return '<a href="v3.8">old</a><a href="v4.1/">new</a>'
        assert url.endswith("v4.1/"), "A failed latest lookup must not silently downgrade"
        return newest

    monkeypatch.setattr(context.resolver, "fetch_text", fetch)
    assert context.versions.gnutls() == ("4.1.2" if newest else None)


def test_openssl_and_videolan_select_only_the_newest_stable_tags(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        context.resolver,
        "remote_tag_names",
        lambda url: (
            ["openssl-3.5.8", "openssl-4.0.2", "openssl-4.1.0-alpha1"]
            if "openssl" in url
            else ["7.1.0", "7.2.0", "8.0.0-rc1", "9.0.0\n"]
        ),
    )
    assert context.versions.openssl() == "4.0.2"
    assert context.versions.videolan("76") == "7.2.0"


@pytest.mark.parametrize("key,prefix", GIT_RELEASE_PREFIXES.items())
def test_git_packages_clone_the_latest_stable_tag(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, key: str, prefix: str
) -> None:
    expected = "a" * 40
    context.latest = True
    monkeypatch.setattr(
        context.resolver,
        "remote_tag_names",
        lambda url: [prefix + suffix for suffix in ("1.2.0", "1.10.0", "2.0.0-rc1")],
    )

    def remote(url: str, reference: str) -> str:
        assert reference == f"refs/tags/{prefix}1.10.0"
        return expected

    def clone(url: str, name: str, mode: str, *, reference: str, expected_commit: str) -> str:
        assert name == key and reference == prefix + "1.10.0" and expected_commit == expected
        return expected

    monkeypatch.setattr(context.resolver, "remote_head_commit", remote)
    monkeypatch.setattr(context.cloner, "clone", clone)
    assert context.git_snapshot("https://example.org/project", key) == expected


def test_all_git_recipes_have_stable_discovery_rules() -> None:
    keys = set()
    for path in (REPO / "ffmpeg_build/stages").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "git_snapshot"
            ):
                keys.add(ast.literal_eval(node.args[1]))
    assert keys == set(GIT_RELEASE_PREFIXES)
    assert keys <= set(registry.PACKAGE_NAMES)


def test_annotated_tag_uses_peeled_commit(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = "refs/tags/v1.2.3"

    def capture(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert arguments[-2:] == [reference, reference + "^{}"]
        return subprocess.CompletedProcess(
            arguments, 0, f"{'b' * 40}\t{reference}\n{'a' * 40}\t{reference}^{{}}\n", ""
        )

    monkeypatch.setattr(context.runner, "capture", capture)
    assert context.resolver.remote_head_commit("https://example.org/repo", reference) == "a" * 40


@pytest.mark.parametrize("changed_setting", [False, True])
def test_dynamic_tool_migration_preserves_native_packages_and_rejects_other_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_setting: bool
) -> None:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = tmp_path / "build"
    context = orchestrator.build_context(
        Arguments(),
        BuildSettings(),
        Selection(),
    )
    context.packages.mkdir(parents=True)
    context.workspace.mkdir()
    orchestrator.configure_toolchain(context)
    orchestrator.source_compiler_flags(context)
    current = orchestrator.current_build_context(context)
    prior = current.replace("rust_toolchain=latest-stable", "rust_toolchain=1.95.0").replace(
        "cargo_c=latest-stable", "cargo_c=0.10.24+cargo-0.98.0"
    )
    if changed_setting:
        prior = prior.replace("compiler=gcc", "compiler=clang")
    path = context.cwd / ".ffmpeg-build-context"
    path.write_text(prior)
    for key in ("rav1e", "sdl2", "ffmpeg"):
        context.marker_path(key).write_text("1.2.3\n")
    if changed_setting:
        with pytest.raises(BuildError, match="different settings"):
            orchestrator.ensure_build_context(context)
        assert path.read_text() == prior and context.marker_path("rav1e").exists()
    else:
        orchestrator.ensure_build_context(context)
        assert path.read_text() == current
        assert (
            not context.marker_path("rav1e").exists() and not context.marker_path("ffmpeg").exists()
        )
    assert context.marker_path("sdl2").read_text() == "1.2.3\n"


def test_every_source_recipe_uses_dynamic_release_discovery() -> None:
    discovered = set()
    for path in (REPO / "ffmpeg_build/stages").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == "fetch_version_if_enabled":
                discovered.add(ast.literal_eval(node.args[0]))
            elif node.func.attr == "git_snapshot":
                discovered.add(ast.literal_eval(node.args[1]))
    assert discovered == {
        key for key, package in registry.PACKAGES.items() if package.kind != registry.Kind.SYSTEM
    }


def test_moved_release_tag_does_not_replace_a_verified_checkout(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = context.packages / "av1-git"
    previous.mkdir()
    (previous / "keep").write_text("previous source")

    def logged(arguments: list[str], **kwargs: object) -> int:
        assert arguments[arguments.index("--branch") + 1] == "v9.8.7"
        Path(arguments[-1]).mkdir()
        return 0

    monkeypatch.setattr(context.runner, "run_logged", logged)
    monkeypatch.setattr(context.cloner, "local_head", lambda path: "b" * 40)
    assert (
        context.cloner.clone(
            "https://example.org/aom", "av1-git", reference="v9.8.7", expected_commit="a" * 40
        )
        is None
    )
    assert (previous / "keep").read_text() == "previous source"
    assert not list(context.packages.glob(".clone-*"))


@pytest.mark.parametrize(
    "listing",
    [None, "cuda-keyring_1.1-1_all.deb cuda-keyring_2.0-9_all.deb cuda-keyring_3.0-beta1_all.deb"],
)
def test_cuda_keyring_is_discovered_before_any_host_install(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, listing: str | None
) -> None:
    from ffmpeg_build.stages.hardware import HardwareDetection
    from ffmpeg_build.stages.system_setup import SystemSetup

    context.operating_system = "Ubuntu"
    context.release_version = "24.04"
    monkeypatch.setattr(context.resolver, "fetch_text", lambda *args, **kwargs: listing)
    calls = []

    def download(arguments: list[str]) -> int:
        calls.append(arguments)
        assert arguments[0] == "curl"
        assert arguments[-1].endswith("/ubuntu2404/x86_64/cuda-keyring_2.0-9_all.deb")
        return 1

    monkeypatch.setattr(context.runner, "run_logged", download)
    with pytest.raises(BuildError, match="Unable to download" if listing else "Unable to discover"):
        HardwareDetection(context, SystemSetup(context)).install_cuda_toolkit()
    assert len(calls) == bool(listing)
    assert not list(context.packages.glob(".cuda-keyring.*"))
