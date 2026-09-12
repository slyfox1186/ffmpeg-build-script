from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from ffmpeg_build.cli import Arguments
from ffmpeg_build.config import BuildSettings, Selection
from ffmpeg_build.main import Orchestrator, _report_failure
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.exec import BASE_PATH, CommandFailed, base_environment
from ffmpeg_build.runtime.paths import DirectoryLock, safe_remove_tree
from ffmpeg_build.runtime.shellquote import quote, unquote
from ffmpeg_build.runtime.state import (
    BUILD_CONTEXT_NAME,
    BUILD_ROOT_MARKER_NAME,
    build_root_marker_matches,
    read_marker_version,
    write_build_root_marker,
)
from ffmpeg_build.runtime.versioncmp import version_sort
from tests.conftest import REPO, invoke


def test_empty_timeout_overrides_use_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "GIT_OPERATION_TIMEOUT",
        "GIT_CLONE_TIMEOUT",
        "VERSION_CHECK_MAX_TIME",
        "FREEDESKTOP_RELEASE_INDEX_MAX_TIME",
        "FREEDESKTOP_RELEASE_CONNECT_TIMEOUT",
        "DOWNLOAD_CONNECT_TIMEOUT",
        "HOST_MUTATION_LOCK_TIMEOUT",
    ):
        monkeypatch.setenv(name, "")
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = tmp_path / "build"
    ctx = orchestrator.build_context(Arguments(), BuildSettings(), Selection())
    assert ctx.resolver.git_timeout == 120 and ctx.cloner.clone_timeout == 1800

    def scrape(*args: object, **kwargs: object) -> str:
        assert kwargs["max_time"] == 5 and kwargs["connect_timeout"] == 2
        return "2.14.3"

    monkeypatch.setattr(ctx.resolver, "scrape_highest", scrape)
    assert ctx.versions.freetype() is not None
    with orchestrator.host_mutation_lock() as lock:
        assert lock.held


@pytest.mark.parametrize(
    "mode", ["unmarked", "scaffold", "foreign", "spaces", "ancestor", "home", "system"]
)
def test_cleanup_boundaries(tmp_path: Path, mode: str) -> None:
    root = tmp_path / "root"
    if mode == "ancestor":
        root = REPO.parent
    elif mode == "home":
        root = Path("/home")
    elif mode == "system":
        root = Path("/usr/local")
    else:
        if mode == "spaces":
            root = tmp_path / "build root with spaces"
        root.mkdir()
        if mode in ("scaffold", "foreign"):
            (root / "packages").mkdir()
            (root / "workspace").mkdir()
        if mode == "foreign":
            (root / "packages/user-file").write_text("mine")
        elif mode == "unmarked":
            (root / "user-file").write_text("mine")
    result = invoke(root, "--cleanup")
    assert result.returncode == (0 if mode == "scaffold" else 1), result.stdout
    if mode == "scaffold":
        assert "empty scaffolding from an interrupted run" in result.stdout
    if mode == "spaces":
        assert "may not contain whitespace" in result.stdout
    if mode in ("foreign", "unmarked"):
        assert list(root.rglob("user-file"))[0].read_text() == "mine"


def test_marker_path_binding_and_hardlinks(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    write_build_root_marker(first)
    marker = first / BUILD_ROOT_MARKER_NAME
    assert build_root_marker_matches(marker, first)
    copied = second / BUILD_ROOT_MARKER_NAME
    copied.write_bytes(marker.read_bytes())
    assert not build_root_marker_matches(copied, second)
    alias = first / "alias"
    os.link(marker, alias)
    assert not build_root_marker_matches(marker, first)


def test_directory_lock_contention_and_release(tmp_path: Path) -> None:
    first, second = DirectoryLock(tmp_path), DirectoryLock(tmp_path)
    assert first.acquire()
    try:
        assert not second.acquire(timeout=0.01)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os, fcntl, sys; f= os.open(sys.argv[1], os.O_RDONLY);\ntry: fcntl.flock(f, fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError: sys.exit(23)",
                str(tmp_path),
            ],
            check=False,
        )
        assert result.returncode == 23
    finally:
        first.release()
    assert second.acquire()
    second.release()


def test_cleanup_reuses_build_lock(context: BuildContext, monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = context.cwd
    write_build_root_marker(context.cwd)
    orchestrator._lock = DirectoryLock(context.cwd)
    assert orchestrator._lock.acquire()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    try:
        orchestrator.cleanup()
        assert context.cwd.exists()
        assert orchestrator._lock.held
    finally:
        orchestrator.teardown()


def test_host_lock_preserves_status_and_streams(
    context: BuildContext, capfd: pytest.CaptureFixture[str]
) -> None:
    orchestrator = Orchestrator(REPO, [])
    with orchestrator.host_mutation_lock():
        status = context.runner.run_logged(
            [
                sys.executable,
                "-c",
                "import sys; print('locked stdout'); print('locked stderr', file=sys.stderr); sys.exit(23)",
            ]
        )
    with orchestrator.host_mutation_lock():
        print("after lock stderr", file=sys.stderr)
    out, err = capfd.readouterr()
    assert status == 23
    assert "locked stdout" in out
    assert "locked stderr" in err
    assert "after lock stderr" in err


@pytest.mark.parametrize("debug", [False, True])
def test_failed_commands_preserve_log_and_status(
    context: BuildContext, capfd: pytest.CaptureFixture[str], debug: bool
) -> None:
    context.runner.debug = debug
    context.runner.log_file = context.log_file
    code = "import sys; print('command stdout'); print('command stderr', file=sys.stderr); sys.exit(37)"
    assert context.runner.run_logged([sys.executable, "-c", code]) == 37
    output = "".join(capfd.readouterr())
    log = context.log_file.read_text()
    for message in ("command stdout", "command stderr"):
        assert message in output
        assert message in log
    with pytest.raises(CommandFailed) as caught:
        context.runner.execute([sys.executable, "-c", "raise SystemExit(37)"])
    assert caught.value.exit_code == 37


def test_missing_executable_is_a_build_error(context: BuildContext) -> None:
    with pytest.raises(CommandFailed) as caught:
        context.runner.execute(["definitely-missing-build-command"])
    assert caught.value.exit_code == 127
    assert not context.runner.probe(["definitely-missing-build-command"])


def test_failed_log_writer_is_not_hidden(context: BuildContext) -> None:
    context.runner.debug = True
    context.runner.log_file = Path("/dev/full")
    with pytest.raises(BuildError, match="record command output"):
        context.runner.run_logged([sys.executable, "-c", "print('x' * 10000)"])


def test_failure_names_calling_recipe(
    context: BuildContext, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ffmpeg_build.main.notify_failure", lambda message: None)
    orchestrator = Orchestrator(REPO, [])
    orchestrator.context = context

    def helper() -> None:
        raise BuildError("helper rejected its input")

    def recipe() -> None:
        helper()

    try:
        recipe()
    except BuildError as error:
        _report_failure(orchestrator, error)
    output = capsys.readouterr().err
    assert "helper rejected its input" in output
    assert "Raised from: test_state_runtime.py:" in output
    assert f"Build log: {context.log_file}" in output
    assert "Report a bug:" in output


def test_context_mismatch_is_before_sudo_and_log_truncation(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = context.cwd
    write_build_root_marker(context.cwd)
    (context.cwd / BUILD_CONTEXT_NAME).write_text("stale build context\n")
    context.log_file.write_text("previous failure\n")

    def forbidden() -> None:
        pytest.fail("sudo must not be requested for a mismatched context")

    monkeypatch.setattr(orchestrator.runner, "require_sudo", forbidden)
    try:
        with pytest.raises(BuildError) as caught:
            orchestrator.run_build(context)
        message = str(caught.value)
        assert "Run 'build-ffmpeg.py --cleanup' before rebuilding." in message
        assert "cflags is new in this version of the script" in message
        assert "(now '-O2 -pipe" in message
        assert "-O2\\ -pipe" not in message
        assert " - and " in message
        assert "package.zlib is new" not in message
        assert context.log_file.read_text() == "previous failure\n"
    finally:
        orchestrator.teardown()


@pytest.mark.parametrize("version", ["6.0.0", "7.0.0"])
@pytest.mark.parametrize("change", ["compatible", "flags", "selection"])
def test_workspace_upgrade(
    context: BuildContext, version: str, change: str, capsys: pytest.CaptureFixture[str]
) -> None:
    orchestrator = Orchestrator(REPO, [])
    path = context.cwd / BUILD_CONTEXT_NAME
    previous = orchestrator.current_build_context(context).replace(
        "script_version=8.0.0", f"script_version={version}"
    )
    if change == "flags":
        previous = (
            "\n".join(
                "cflags='-O1'" if line.startswith("cflags=") else line
                for line in previous.splitlines()
            )
            + "\n"
        )
    elif change == "selection":
        previous = previous.replace("package.vulkan=true", "package.vulkan=false")
    path.write_text(previous)
    context.marker_path("ffmpeg").write_text("n9.0.1\n")
    context.marker_path("nasm").write_text("3.02\n")
    if change == "compatible":
        orchestrator.ensure_build_context(context)
        assert "Adopted this workspace" in capsys.readouterr().out
        assert "script_version=8.0.0" in path.read_text()
        assert not context.marker_path("ffmpeg").exists()
    else:
        with pytest.raises(BuildError, match="before rebuilding"):
            orchestrator.ensure_build_context(context)
        assert path.read_text() == previous
        assert context.marker_path("ffmpeg").exists()
    assert context.marker_path("nasm").read_text() == "3.02\n"


def test_v1_adoption_and_strict_settings(
    context: BuildContext, capsys: pytest.CaptureFixture[str]
) -> None:
    orchestrator = Orchestrator(REPO, [])
    path = context.cwd / BUILD_CONTEXT_NAME
    previous = orchestrator.current_build_context(context).replace(
        "ffmpeg-build-context:v2", "ffmpeg-build-context:v1"
    )
    lines = []
    for line in previous.splitlines():
        key = line.split("=", 1)[0]
        if key == "package.libdvdnav":
            continue
        lines.append(f"{key}=''" if key in ("cflags", "cxxflags", "cppflags", "ldflags") else line)
    previous = "\n".join(lines) + "\n"
    path.write_text(previous)
    context.marker_path("ffmpeg").write_text("n9.0.1\n")
    orchestrator.ensure_build_context(context)
    output = capsys.readouterr().out
    assert "Adopted this workspace" in output and "libdvdnav" in output
    assert not context.marker_path("ffmpeg").exists()
    assert path.read_text().startswith("ffmpeg-build-context:v2\n")
    path.write_text(previous.replace("compiler=gcc", "compiler=clang"))
    with pytest.raises(BuildError, match="compiler was 'clang', is now 'gcc'"):
        orchestrator.ensure_build_context(context)


def test_context_missing_with_package_markers_refuses(context: BuildContext) -> None:
    context.marker_path("jemalloc").write_text("1.2.3\n")
    with pytest.raises(BuildError, match="Run 'build-ffmpeg.py --cleanup' before rebuilding."):
        Orchestrator(REPO, []).ensure_build_context(context)


def test_affinity_determines_jobs(context: BuildContext, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "sched_getaffinity", lambda pid: {1, 2})
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = context.cwd
    assert orchestrator.build_context(Arguments(), BuildSettings(), Selection()).build_threads == 2


def test_child_environment_isolated_from_conda(monkeypatch: pytest.MonkeyPatch) -> None:
    polluted = (
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "LD_LIBRARY_PATH",
        "CMAKE_PREFIX_PATH",
        "PKG_CONFIG_PATH",
        "CONDA_BUILD_SYSROOT",
        "SSL_CERT_FILE",
        "CC",
        "CFLAGS",
        "LDFLAGS",
    )
    for name in polluted:
        monkeypatch.setenv(name, "/untrusted/conda")
    monkeypatch.setenv("PATH", "/untrusted/conda/bin")
    environment = base_environment()
    assert not set(polluted) & environment.keys()
    assert environment["PATH"] == BASE_PATH
    assert environment["LC_ALL"] == "C"
    assert environment["TZ"] == "UTC"


def test_temporary_registry_containment(context: BuildContext, tmp_path: Path) -> None:
    temporary = context.packages / ".clone-demo.123"
    real = context.packages / "real-source-tree"
    outside = tmp_path / "outside"
    for path in (temporary, real, outside):
        path.mkdir()
    context.register_temporary_path(temporary)
    context.register_temporary_path(outside)
    context.remove_registered_temporary_paths()
    assert not temporary.exists()
    assert real.is_dir() and outside.is_dir()


def test_deep_tree_deletion_does_not_recurse(tmp_path: Path) -> None:
    target = tmp_path / "deep"
    target.mkdir()
    child = target
    for _ in range(1100):
        child /= "d"
        child.mkdir()
    (child / "payload").write_text("deep source")
    safe_remove_tree(target, tmp_path)
    assert not target.exists() and tmp_path.exists()


def test_bounded_deletion(tmp_path: Path) -> None:
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    safe_remove_tree(child, root)
    assert not child.exists()
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    payload = sibling / "payload"
    payload.write_text("preserve")
    for target in (root, sibling):
        with pytest.raises(BuildError, match="Refusing"):
            safe_remove_tree(target, root)
    link = root / "link"
    link.symlink_to(sibling, target_is_directory=True)
    with pytest.raises(BuildError, match="symlinked"):
        safe_remove_tree(link, root)
    assert payload.read_text() == "preserve"

    # Nested symlinks are unlinked, never traversed.
    child.mkdir()
    (child / "link").symlink_to(sibling, target_is_directory=True)
    safe_remove_tree(child, root)
    assert payload.read_text() == "preserve"


def test_deletion_rejects_ancestor_swapped_for_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    (root / "parent/child").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "child").mkdir(parents=True)
    (outside / "child/keep").write_text("user data")
    real_open = os.open
    swapped = False

    def swap(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal swapped
        if str(path) == "parent" and not swapped:
            swapped = True
            (root / "parent").rename(root / "original")
            (root / "parent").symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", swap)
    with pytest.raises(BuildError, match="Failed to remove"):
        safe_remove_tree(root / "parent/child", root)
    assert swapped
    assert (outside / "child/keep").read_text() == "user data"


def test_interrupted_lock_wait_closes_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with DirectoryLock(tmp_path) as first:
        assert first.acquire()
        before = len(list(Path("/proc/self/fd").iterdir()))

        def interrupted(_delay: float) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr("ffmpeg_build.runtime.paths.time.sleep", interrupted)
        with pytest.raises(KeyboardInterrupt):
            DirectoryLock(tmp_path).acquire(timeout=1)
        assert len(list(Path("/proc/self/fd").iterdir())) == before


def test_host_lock_timeout_prevents_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    orch = Orchestrator(REPO, [])
    monkeypatch.setenv("HOST_MUTATION_LOCK_TIMEOUT", "0")
    with orch.host_mutation_lock():
        with pytest.raises(BuildError, match="Timed out"):
            orch.host_mutation_lock()


@pytest.mark.parametrize("payload", ["", "1.0\n2.0\n", "../bad\n", "1.0 x\n", "\xff"])
def test_invalid_markers(tmp_path: Path, payload: str) -> None:
    marker = tmp_path / "test.done"
    marker.write_bytes(payload.encode("latin-1"))
    assert read_marker_version(marker) is None


def test_shellquote_differential() -> None:
    generator = random.Random(923)
    values = ["", "a b", "~a:b=~c", "x#y", "#z", "'\\\"", "héllo\n\t"]
    values += [
        "".join(chr(generator.randrange(1, 256)) for _ in range(generator.randrange(1, 35)))
        for _ in range(300)
    ]
    result = subprocess.run(
        ["bash", "-c", 'printf "%q\\0" "$@"', "_", *values],
        env={**os.environ, "LC_ALL": "C"},
        capture_output=True,
        check=True,
    )
    expected = result.stdout.decode().split("\0")[:-1]
    assert [quote(value) for value in values] == expected
    assert [unquote(quote(value)) for value in values] == values


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("unique", [False, True])
def test_version_sort_differential(reverse: bool, unique: bool) -> None:
    generator = random.Random(91)
    values = [
        "3.10.2",
        "3.9",
        "VER-2-13-3",
        "n7.1",
        "R70",
        "pkgconf-2.1.0",
        "0.10.24+cargo-0.98.0",
        "1.00",
        "1.0",
        "1.0",
        ".",
        "..",
        ".a",
        ".1",
        "",
    ]
    alphabet = "0123456789.-~abcABC+_"
    values += [
        "".join(generator.choice(alphabet) for _ in range(generator.randrange(1, 20)))
        for _ in range(200)
    ]
    arguments = ["sort", "-V"] + (["-r"] if reverse else []) + (["-u"] if unique else [])
    result = subprocess.run(
        arguments,
        input="\n".join(values) + "\n",
        text=True,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
        check=True,
    )
    assert version_sort(values, reverse=reverse, unique=unique) == result.stdout.splitlines()


def test_transport_timeouts_and_failed_clone_preserve_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_OPERATION_TIMEOUT", "17")
    monkeypatch.setenv("GIT_CLONE_TIMEOUT", "19")
    monkeypatch.setenv("VERSION_CHECK_MAX_TIME", "23")
    orchestrator = Orchestrator(REPO, [])
    orchestrator.build_root = tmp_path / "build"
    ctx = orchestrator.build_context(Arguments(), BuildSettings(), Selection())
    ctx.packages.mkdir(parents=True)
    source = ctx.packages / "x264"
    source.mkdir()
    (source / "keep").write_text("previous checkout")
    commands: list[list[str]] = []
    deadlines: list[object] = []

    def capture(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(arguments)
        deadlines.append(kwargs.get("timeout"))
        return subprocess.CompletedProcess(arguments, 1, "", "fixture failure")

    def logged(arguments: list[str], **kwargs: object) -> int:
        commands.append(arguments.copy())
        Path(arguments[-1]).mkdir()
        return 124

    monkeypatch.setattr(ctx.runner, "capture", capture)
    monkeypatch.setattr(ctx.runner, "run_logged", logged)
    assert ctx.resolver.remote_head_commit("https://example.org/repo") is None
    assert ctx.cloner.local_head(source) is None
    assert ctx.resolver.fetch_text("https://example.org/releases") is None
    assert deadlines == [17, 17, 38]
    assert commands[-1][commands[-1].index("--max-time") + 1] == "23"
    assert ctx.cloner.clone("https://example.org/repo", "x264") is None
    assert [command[:3] for command in commands[-2:]] == [["timeout", "--foreground", "19"]] * 2
    assert commands[-1][-1] != commands[-2][-1]
    assert (source / "keep").read_text() == "previous checkout"
    assert list(ctx.packages.glob(".clone-*")) == []


@pytest.mark.parametrize("artifacts_ready", [True, False])
@pytest.mark.parametrize("latest", [True, False])
def test_latest_git_reuses_only_verified_current_checkout(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, artifacts_ready: bool, latest: bool
) -> None:
    commit = "a" * 40
    context.latest = latest
    context.marker_path("x264").write_text(commit + "\n")
    monkeypatch.setattr(context.resolver, "remote_head_commit", lambda url: commit)
    monkeypatch.setattr(context.cloner, "local_head", lambda path: commit)
    monkeypatch.setattr(context, "package_artifacts_ready", lambda key: artifacts_ready)
    clones: list[str] = []

    def clone(url: str, key: str, mode: str) -> str:
        clones.append(key)
        return commit

    monkeypatch.setattr(context.cloner, "clone", clone)
    assert context.git_snapshot("https://example.org/repo", "x264") == commit
    assert clones == []
    context.marker_path("ffmpeg").write_text("9.0.1\n")
    assert context.build("x264", commit) is not artifacts_ready
    assert context.marker_path("ffmpeg").exists() is artifacts_ready


@pytest.mark.parametrize("source_commit", [None, "b" * 40])
def test_git_resume_refuses_implicit_upgrade_without_pinned_source(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, source_commit: str | None
) -> None:
    commit = "a" * 40
    context.marker_path("av1-git").write_text(commit + "\n")
    monkeypatch.setattr(context.cloner, "local_head", lambda path: source_commit)

    def forbidden(*args: object) -> str:
        pytest.fail("A normal resume attempted to replace the pinned Git source")

    monkeypatch.setattr(context.cloner, "clone", forbidden)
    monkeypatch.setattr(context.resolver, "remote_head_commit", forbidden)
    with pytest.raises(BuildError, match="Restore that checkout.*--latest"):
        context.git_snapshot("https://example.org/repo", "av1-git")
    assert context.marker_path("av1-git").read_text() == commit + "\n"


@pytest.mark.parametrize("length", [12, 39, 40, 41, 63, 64, 65])
def test_local_git_head_requires_complete_object_id(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, length: int
) -> None:
    commit = "a" * length
    monkeypatch.setattr(
        context.runner,
        "capture",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, commit + "\n", ""),
    )
    assert context.cloner.local_head(context.packages) == (commit if length in (40, 64) else None)


@pytest.mark.parametrize("failure", ["publish", "restore", "backup_interrupt"])
def test_git_publication_retains_previous_source_on_failure(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    source = context.packages / "av1-git"
    source.mkdir()
    (source / "keep").write_text("previous checkout")

    def clone(arguments: list[str], **kwargs: object) -> int:
        new = Path(arguments[-1])
        new.mkdir()
        (new / "new").write_text("replacement checkout")
        return 0

    real_rename = os.rename

    def rename(old: Path, new: Path) -> None:
        if old == source and failure == "backup_interrupt":
            real_rename(old, new)
            raise KeyboardInterrupt
        if old.name == "repository" or (old.name == ".previous-checkout" and failure == "restore"):
            raise OSError("injected rename failure")
        real_rename(old, new)

    monkeypatch.setattr(context.runner, "run_logged", clone)
    monkeypatch.setattr(context.cloner, "local_head", lambda path: "a" * 40)
    monkeypatch.setattr("ffmpeg_build.runtime.git.os.rename", rename)
    if failure == "publish":
        assert context.cloner.clone("https://example.org/repo", "av1-git") is None
    else:
        with pytest.raises(KeyboardInterrupt if failure == "backup_interrupt" else BuildError):
            context.cloner.clone("https://example.org/repo", "av1-git")
    context.remove_registered_temporary_paths()
    recovery = (
        source
        if failure == "publish"
        else next(context.packages.glob(".clone-*/.previous-checkout"))
    )
    assert (recovery / "keep").read_text() == "previous checkout"
