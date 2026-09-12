from __future__ import annotations

import errno
import os
import subprocess
import tarfile
from collections.abc import Sequence
from pathlib import Path

import pytest

from ffmpeg_build.main import Orchestrator
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.download import write_archive_checksum
from ffmpeg_build.runtime.errors import BuildError, SignalStop
from ffmpeg_build.runtime.exec import base_environment, strip_workspace_entries
from ffmpeg_build.runtime.paths import DirectoryLock
from ffmpeg_build.runtime.state import build_root_is_adoptable, write_build_root_marker
from tests.conftest import REPO
from tests.test_downloads import archive_at


def test_host_lock_accepts_symlinked_cache_parent_but_rejects_symlinked_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, cache = tmp_path / "home", tmp_path / "cache"
    home.mkdir()
    cache.mkdir()
    (home / ".cache").symlink_to(cache, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    orchestrator = Orchestrator(REPO, [])
    with orchestrator.host_mutation_lock() as lock:
        assert lock.directory == cache / "ffmpeg-build-script"
        lock.assert_current()
    target = cache / "ffmpeg-build-script"
    target.rmdir()
    target.symlink_to(home, target_is_directory=True)
    with pytest.raises(BuildError, match="Unable to open lock directory"):
        orchestrator.host_mutation_lock()


def test_directory_lock_reports_disappearing_path_and_closes_failed_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "locked"
    root.mkdir()
    with DirectoryLock(root) as lock:
        assert lock.acquire()
        root.rmdir()
        with pytest.raises(BuildError, match="Unable to open lock directory"):
            lock.assert_current()
    root.mkdir()
    before = len(list(Path("/proc/self/fd").iterdir()))

    def denied(*args: object) -> None:
        raise OSError(errno.EPERM, "fixture lock refusal")

    monkeypatch.setattr("ffmpeg_build.runtime.paths.fcntl.flock", denied)
    with pytest.raises(BuildError, match="Unable to lock directory"):
        DirectoryLock(root).acquire()
    assert len(list(Path("/proc/self/fd").iterdir())) == before


@pytest.mark.parametrize("writer", ["marker", "context", "checksum"])
def test_interrupted_atomic_writers_remove_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer: str
) -> None:
    archive = tmp_path / "source.tar.gz"
    if writer == "checksum":
        archive.write_bytes(b"fixture")

    def interrupted(*args: object) -> None:
        raise SignalStop("TERM", 143)

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", interrupted)
        with pytest.raises(SignalStop):
            if writer == "marker":
                write_build_root_marker(tmp_path)
            elif writer == "context":
                Orchestrator(REPO, [])._publish_context(tmp_path / ".ffmpeg-build-context", "state")
            else:
                write_archive_checksum(archive)
    assert not list(tmp_path.glob(".*"))
    if writer == "marker":
        assert build_root_is_adoptable(tmp_path)
        write_build_root_marker(tmp_path)


@pytest.mark.parametrize("local_failure", [False, True])
def test_cache_distinguishes_invalid_extraction_from_local_disk_failure(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, local_failure: bool
) -> None:
    archive = archive_at(
        context.packages / "source.tar.gz", [("source/file", b"payload", tarfile.REGTYPE)]
    )
    assert write_archive_checksum(archive)
    target = context.packages / "source"
    target.mkdir()
    (target / "keep").write_text("old source")

    def fail(*args: object, **kwargs: object) -> None:
        if local_failure:
            raise OSError(errno.ENOSPC, "fixture disk full")
        raise tarfile.FilterError("fixture extraction-time safety rejection")

    monkeypatch.setattr(tarfile.TarFile, "extractall", fail)
    assert context.downloader.try_download("https://example.test/source.tar.gz") is None
    assert archive.exists() is local_failure
    assert Path(f"{archive}.sha256").exists() is local_failure
    assert (target / "keep").read_text() == "old source"
    assert not list(context.packages.glob(".extract.*"))


def test_unsafe_cached_archive_is_removed_before_retry(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = archive_at(context.packages / "bad.tar.gz", [("bad/fifo", b"", tarfile.FIFOTYPE)])
    assert write_archive_checksum(archive)
    monkeypatch.setattr(context.runner, "run_logged", lambda *args, **kwargs: 1)
    assert context.downloader.try_download("https://example.test/bad.tar.gz") is None
    assert not archive.exists() and not Path(f"{archive}.sha256").exists()


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        ("-I /ws/include -L/ws/lib -O2", "-O2"),
        (
            "-I/usr/include -L /usr/lib -I/ws-other/include -pthread",
            "-I/usr/include -L /usr/lib -I/ws-other/include -pthread",
        ),
        ("-isystem /ws/include -iquote/ws/include --sysroot=/ws -fPIC", "-fPIC"),
    ],
)
def test_removing_workspace_flags_never_orphans_an_option(flags: str, expected: str) -> None:
    assert strip_workspace_entries(flags, Path("/ws")) == expected
    assert (
        strip_workspace_entries("/ws/lib:/ws-other/lib:/usr/lib", Path("/ws"), ":")
        == "/ws-other/lib:/usr/lib"
    )


def test_network_proxy_settings_survive_without_inheriting_conda_or_cgi_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy_names = (
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    )
    for name in proxy_names:
        monkeypatch.setenv(name, "fixture-proxy-setting")
    monkeypatch.setenv("HTTP_PROXY", "untrusted-cgi-value")
    monkeypatch.setenv("CONDA_PREFIX", "/untrusted/conda")
    environment = base_environment()
    assert all(environment[name] == "fixture-proxy-setting" for name in proxy_names)
    assert "HTTP_PROXY" not in environment and "CONDA_PREFIX" not in environment


@pytest.mark.parametrize(
    "host",
    [
        "github.com",
        "code.videolan.org",
        "sourceforge.net",
        "downloads.sourceforge.net",
        "gitlab.freedesktop.org",
    ],
)
def test_release_retrieval_commands_use_host_compatible_user_agent(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    calls: list[list[str]] = []

    def capture(arguments: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(arguments))
        return subprocess.CompletedProcess(arguments, 0, "a" * 40 + "\trefs/tags/v1.0\n", "")

    monkeypatch.setattr(context.runner, "capture", capture)
    context.resolver.fetch_text(f"https://{host}/releases")
    context.resolver.remote_tag_names(f"https://{host}/source.git")
    context.resolver.remote_head_commit(f"https://{host}/source.git")
    assert "--user-agent" not in calls[0]
    assert all(not any("http.userAgent=" in arg for arg in command) for command in calls[1:])
