"""Upstream release discovery.

Every fetcher returns a version string or None. None means "upstream could not
be reached or published nothing usable". Enabled packages fail explicitly;
there is no fixed-version fallback that could masquerade as the latest release.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence

from .errors import BuildError
from .exec import Runner
from .logging import Logger
from .versioncmp import version_sort

GNU_PRIMARY_MIRROR = "https://mirrors.ibiblio.org/gnu"
GNU_FALLBACK_MIRROR = "https://mirror.team-cymru.com/gnu"

DEFAULT_VERSION_PATTERN = re.compile(r"^[0-9]+(\.[0-9]+){1,3}$")
_REPO_NAME = re.compile(r"^[a-zA-Z0-9._/-]+$")
_COMMIT = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")


class VersionResolver:
    """Queries upstream tag lists and release indexes."""

    def __init__(self, runner: Runner, logger: Logger, *, git_timeout: int = 120) -> None:
        self.runner = runner
        self.logger = logger
        self.git_timeout = git_timeout

    # -- transport -------------------------------------------------------

    def fetch_text(
        self, url: str, *, max_time: int | None = None, connect_timeout: int = 5
    ) -> str | None:
        """Fetch a release index page.

        HTTPS is pinned across redirects here exactly as it is for archive
        downloads: a version index that can be redirected to plain HTTP decides
        which bytes get compiled.
        """
        if max_time is None:
            max_time = int(os.environ.get("VERSION_CHECK_MAX_TIME") or "15")
        completed = self.runner.capture(
            [
                "curl",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--tlsv1.2",
                "-fsSL",
                "--max-time",
                str(max_time),
                "--connect-timeout",
                str(connect_timeout),
                url,
            ],
            timeout=max_time + connect_timeout + 10,
        )
        if completed.returncode != 0:
            if completed.stderr.strip():
                self.logger.warn(completed.stderr.strip())
            return None
        return completed.stdout

    def remote_tag_names(self, repository_url: str) -> list[str] | None:
        if not repository_url.startswith("https://"):
            return None
        completed = self.runner.capture(
            [
                "git",
                "-c",
                "protocol.allow=never",
                "-c",
                "protocol.https.allow=always",
                "ls-remote",
                "--tags",
                "--refs",
                repository_url,
            ],
            env_overrides={"GIT_TERMINAL_PROMPT": "0"},
            timeout=self.git_timeout,
        )
        if completed.returncode != 0:
            self.logger.warn(
                f"Git tag lookup failed for '{repository_url}' (exit {completed.returncode}): "
                f"{completed.stderr.strip() or 'no diagnostic output'}"
            )
            return None
        tags: list[str] = []
        for line in completed.stdout.splitlines():
            _, separator, reference = line.partition("refs/tags/")
            if separator and reference:
                tags.append(reference)
        return tags

    def remote_head_commit(self, repository_url: str, reference: str = "HEAD") -> str | None:
        completed = self.runner.capture(
            [
                "git",
                "-c",
                "protocol.allow=never",
                "-c",
                "protocol.https.allow=always",
                "ls-remote",
                repository_url,
                reference,
                *([reference + "^{}"] if reference.startswith("refs/tags/") else []),
            ],
            env_overrides={"GIT_TERMINAL_PROMPT": "0"},
            timeout=self.git_timeout,
        )
        if completed.returncode != 0:
            self.logger.warn(
                f"Git reference lookup failed for '{repository_url}' "
                f"('{reference}', exit {completed.returncode}): "
                f"{completed.stderr.strip() or 'no diagnostic output'}"
            )
            return None
        references = {}
        for line in completed.stdout.splitlines():
            fields = line.split()
            if len(fields) == 2 and _COMMIT.fullmatch(fields[0]):
                references[fields[1]] = fields[0]
        # Annotated tag objects are not commits. Prefer the peeled commit;
        # lightweight tags have only the unpeeled reference.
        return references.get(reference + "^{}") or references.get(reference)

    # -- selection -------------------------------------------------------

    @staticmethod
    def select_prefixed_version(
        references: Sequence[str],
        prefix: str = "v",
        exclude_pattern: str = "",
        version_pattern: re.Pattern[str] = DEFAULT_VERSION_PATTERN,
        index: int = 1,
    ) -> str | None:
        """Pick the nth-newest tag matching a prefix and shape."""
        if index < 1:
            raise BuildError("Version selection index must be a positive integer.")
        exclude = re.compile(exclude_pattern) if exclude_pattern else None
        versions: list[str] = []
        for reference in references:
            if not reference or reference == "null":
                continue
            if exclude is not None and exclude.search(reference):
                continue
            if prefix:
                if not reference.startswith(prefix):
                    continue
                version = reference[len(prefix) :]
            else:
                version = reference
            if not version_pattern.fullmatch(version):
                continue
            versions.append(version)
        if not versions:
            return None
        ordered = version_sort(versions, reverse=True, unique=True)
        return ordered[index - 1] if index <= len(ordered) else None

    # -- hosted forges ---------------------------------------------------

    def github_version(
        self,
        repository: str,
        prefix: str = "v",
        exclude_pattern: str = "",
        version_pattern: re.Pattern[str] = DEFAULT_VERSION_PATTERN,
        index: int = 1,
    ) -> str | None:
        if not _REPO_NAME.match(repository):
            raise BuildError(f"Invalid repository name format: '{repository}'.")
        tags = self.remote_tag_names(f"https://github.com/{repository}.git")
        if tags is None:
            self.logger.warn(f"Failed to fetch tags for GitHub repository '{repository}'.")
            return None
        version = self.select_prefixed_version(
            tags, prefix, exclude_pattern, version_pattern, index
        )
        if version is None:
            self.logger.warn(
                f"github_version: no version found for '{repository}' ('prefix={prefix}')."
            )
        return version

    def github_version_any_prefix(self, repository: str) -> str | None:
        """Try the `v` prefix first, then no prefix.

        This is the fallback dispatch the Bash `github_repo` used for
        repositories whose tagging convention is not recorded anywhere.
        """
        if not _REPO_NAME.fullmatch(repository):
            raise BuildError(f"Invalid repository name format: '{repository}'.")
        tags = self.remote_tag_names(f"https://github.com/{repository}.git")
        if tags is None:
            self.logger.warn(f"Failed to fetch tags for GitHub repository '{repository}'.")
            return None
        version = self.select_prefixed_version(tags, "v") or self.select_prefixed_version(tags, "")
        if version is None:
            self.logger.warn(f"github_version: no stable version found for '{repository}'.")
        return version

    def gitlab_version(
        self,
        base_url: str,
        project: str,
        prefix: str = "v",
        separator: str = ".",
        version_pattern: re.Pattern[str] | None = None,
        index: int = 1,
    ) -> str | None:
        if version_pattern is None:
            version_pattern = (
                re.compile(r"^[0-9]+(-[0-9]+){2,3}$")
                if separator == "-"
                else DEFAULT_VERSION_PATTERN
            )
        if not base_url.startswith("https://") or not _REPO_NAME.match(project):
            return None
        tags = self.remote_tag_names(f"{base_url}/{project}.git")
        if tags is None:
            self.logger.warn(
                f"gitlab_version: failed to fetch tags for '{project}' from '{base_url}'."
            )
            return None
        version = self.select_prefixed_version(tags, prefix, "", version_pattern, index)
        if version is None:
            self.logger.warn(
                f"gitlab_version: no version found for '{project}' "
                f"('prefix={prefix}', 'sep={separator}')."
            )
        return version

    # -- GNU mirrors -----------------------------------------------------

    def gnu_version(self, index_url: str) -> str | None:
        """Scrape a GNU mirror directory listing for the newest release.

        Mirrors are tried in a fixed order and ftp.gnu.org is used only when it
        was named explicitly: it rate-limits aggressively enough that a build
        touching four GNU packages regularly failed on it.
        """
        if not re.match(r"^https://[a-zA-Z0-9._/-]+\.[a-zA-Z0-9._/-]*$", index_url):
            raise BuildError(f"Invalid repository URL format: '{index_url}'.")

        candidates: list[str] = []
        if re.match(
            r"^https?://(ftp\.gnu\.org|mirror\.team-cymru\.com|mirrors\.ibiblio\.org)/gnu/",
            index_url,
        ):
            ibiblio = index_url.replace("ftp.gnu.org/gnu", "mirrors.ibiblio.org/gnu").replace(
                "mirror.team-cymru.com/gnu", "mirrors.ibiblio.org/gnu"
            )
            cymru = index_url.replace("ftp.gnu.org/gnu", "mirror.team-cymru.com/gnu").replace(
                "mirrors.ibiblio.org/gnu", "mirror.team-cymru.com/gnu"
            )
            candidates = [ibiblio, cymru]
            if not index_url.startswith("https://ftp.gnu.org/gnu/") and index_url not in candidates:
                candidates.append(index_url)
        else:
            candidates = [index_url]

        ordered_candidates = list(dict.fromkeys(candidates))
        for url in ordered_candidates:
            listing = self.fetch_text(url, max_time=10)
            if listing is None:
                continue
            if "libtool" in url:
                pattern = re.compile(r"libtool-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.tar\.xz")
            elif "m4" in url:
                pattern = re.compile(r"m4-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.tar\.xz")
            elif "autoconf" in url:
                pattern = re.compile(r"autoconf-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.tar\.xz")
            elif "libiconv" in url:
                pattern = re.compile(r"libiconv-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.tar\.gz")
            else:
                pattern = re.compile(
                    r"[a-z]+-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.(?:tar\.gz|tar\.bz2|tar\.xz)"
                )
            matches = pattern.findall(listing)
            ordered = version_sort(matches, reverse=True, unique=True)
            for candidate in ordered:
                if re.match(r"^[0-9]+(\.[0-9]+){1,2}$", candidate):
                    return candidate
        raise BuildError(
            f"Failed to detect latest version from '{index_url}' "
            f"(tried: '{' '.join(ordered_candidates)}')."
        )

    # -- index scrapers --------------------------------------------------

    def scrape_highest(
        self,
        url: str,
        pattern: str,
        *,
        max_time: int | None = None,
        connect_timeout: int = 5,
    ) -> str | None:
        listing = self.fetch_text(url, max_time=max_time, connect_timeout=connect_timeout)
        if listing is None:
            return None
        matches = re.findall(pattern, listing)
        ordered = version_sort(list(matches), reverse=True, unique=True)
        return ordered[0] if ordered else None
