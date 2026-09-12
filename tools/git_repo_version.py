#!/usr/bin/env python3
"""Print the newest stable numeric tag of an HTTPS Git repository."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Standalone diagnostics share the builder's transport and version ordering.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.exec import Runner, base_environment
from ffmpeg_build.runtime.logging import Logger
from ffmpeg_build.runtime.versions import VersionResolver


def latest_stable_version(repository_url: str, prefix: str = "") -> str | None:
    if not repository_url.startswith("https://"):
        raise BuildError("Repository URL must use HTTPS.")
    if any(ord(character) < 32 or ord(character) == 127 for character in repository_url + prefix):
        raise BuildError("Repository URL and tag prefix may not contain control characters.")
    timeout = os.environ.get("GIT_OPERATION_TIMEOUT", "120")
    if not re.fullmatch(r"[1-9][0-9]*", timeout):
        raise BuildError("'GIT_OPERATION_TIMEOUT' must be a positive integer.")
    logger = Logger()
    resolver = VersionResolver(Runner(logger, base_environment()), logger, git_timeout=int(timeout))
    tags = resolver.remote_tag_names(repository_url)
    if tags is None:
        return None
    if not prefix:
        tags = [re.sub(r"^[^0-9]*", "", tag) for tag in tags]
    return resolver.select_prefixed_version(tags, prefix)


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print("Usage: git_repo_version.py <https-git-url> [tag-prefix]", file=sys.stderr)
        return 2
    try:
        version = latest_stable_version(*argv)
    except BuildError as error:
        print(error, file=sys.stderr)
        return 1
    if version is None:
        print(f"No stable numeric release tag found for '{argv[0]}'.", file=sys.stderr)
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
