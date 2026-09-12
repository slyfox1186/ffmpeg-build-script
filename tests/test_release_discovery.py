from __future__ import annotations

import subprocess

import pytest

from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError


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
