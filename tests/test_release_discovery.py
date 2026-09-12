from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.http import HTTP_USER_AGENT


@pytest.mark.parametrize(
    "tags,expected", [(["1.0", "2.0"], "2.0"), (["v1.0", "2.0"], "1.0"), (None, None)]
)
def test_prefix_fallback_fetches_one_consistent_tag_list(
    context: BuildContext,
    monkeypatch: pytest.MonkeyPatch,
    tags: list[str] | None,
    expected: str | None,
) -> None:
    calls: list[str] = []

    def fetch(url: str) -> list[str] | None:
        calls.append(url)
        return tags

    monkeypatch.setattr(context.resolver, "remote_tag_names", fetch)
    assert context.resolver.github_version_any_prefix("example/project") == expected
    assert calls == ["https://github.com/example/project.git"]


@pytest.mark.parametrize("index", [0, -1])
def test_version_selection_rejects_invalid_index(context: BuildContext, index: int) -> None:
    with pytest.raises(BuildError, match="positive integer"):
        context.resolver.select_prefixed_version(["v1.0", "v2.0"], index=index)


@pytest.mark.parametrize("length", [39, 40, 41, 63, 64, 65])
def test_remote_commit_accepts_only_complete_git_hashes(
    context: BuildContext,
    monkeypatch: pytest.MonkeyPatch,
    length: int,
) -> None:
    commit = "a" * length
    monkeypatch.setattr(
        context.runner,
        "capture",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, commit + "\tHEAD\n", ""),
    )
    assert context.resolver.remote_head_commit("https://example.org/project.git") == (
        commit if length in (40, 64) else None
    )


@pytest.mark.parametrize("lookup", ["tags", "head"])
@pytest.mark.parametrize("diagnostic", ["fatal: HTTP 418 from upstream", ""])
def test_git_lookup_failure_diagnostics_reach_terminal_and_log(
    context: BuildContext,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    lookup: str,
    diagnostic: str,
) -> None:
    context.logger.log_file = context.log_file
    context.logger._err = sys.stderr
    monkeypatch.setattr(
        context.runner,
        "capture",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 128, "", diagnostic),
    )
    url = "https://code.videolan.org/rist/librist.git"
    result = (
        context.resolver.remote_tag_names(url)
        if lookup == "tags"
        else context.resolver.remote_head_commit(url)
    )
    assert result is None
    for output in ("".join(capfd.readouterr()), context.log_file.read_text()):
        assert url in output and "exit 128" in output
        assert (diagnostic or "no diagnostic output") in output


@pytest.mark.parametrize("host", ["code.videolan.org", "github.com"])
def test_clone_and_retry_use_host_compatible_identity(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    calls: list[list[str]] = []

    def logged(arguments: list[str], **kwargs: object) -> int:
        calls.append(arguments.copy())
        Path(arguments[-1]).mkdir()
        return 128

    monkeypatch.setattr(context.runner, "run_logged", logged)
    assert context.cloner.clone(f"https://{host}/project/repo.git", "repo") is None
    assert len(calls) == 2
    for arguments in calls:
        assert (f"http.userAgent={HTTP_USER_AGENT}" in arguments) == (host == "github.com")
        assert "protocol.allow=never" in arguments and "protocol.https.allow=always" in arguments
    assert not list(context.packages.glob(".clone-*"))
