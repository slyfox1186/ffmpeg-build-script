"""Git snapshot management for the `*-git` packages.

A Git package's "version" is the commit that was actually checked out, not the
commit the remote advertised: a branch can advance between `ls-remote` and
`clone`, and recording the advertised one would make the marker a claim the
workspace does not support.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from .errors import BuildError
from .exec import Runner
from .http import user_agent_arguments
from .logging import Logger
from .paths import safe_remove_tree

_REPO_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_COMMIT = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")

CLONE_MODES = ("shallow", "recurse", "full")


class GitCloner:
    """Clones an upstream repository into the package cache."""

    def __init__(
        self,
        *,
        runner: Runner,
        logger: Logger,
        packages: Path,
        clone_timeout: int = 1800,
        operation_timeout: int = 120,
        register_temporary: Callable[[Path], None] | None = None,
        unregister_temporary: Callable[[Path], None] | None = None,
    ) -> None:
        self.runner = runner
        self.logger = logger
        self.packages = packages
        self.clone_timeout = clone_timeout
        self.operation_timeout = operation_timeout
        self._register = register_temporary or (lambda _path: None)
        self._unregister = unregister_temporary or (lambda _path: None)

    def local_head(self, directory: Path) -> str | None:
        completed = self.runner.capture(
            ["git", "-C", str(directory), "rev-parse", "HEAD"], timeout=self.operation_timeout
        )
        if completed.returncode != 0:
            return None
        commit = completed.stdout.strip()
        return commit if _COMMIT.fullmatch(commit) else None

    def clone(self, repository_url: str, repository_name: str, mode: str = "shallow") -> str | None:
        """Clone and publish a snapshot, returning the checked-out commit."""
        if not repository_url.startswith("https://") or any(
            ord(character) < 0x20 for character in repository_url
        ):
            self.logger.warn("git clone requires a valid HTTPS repository URL.")
            return None
        if not _REPO_NAME.match(repository_name):
            self.logger.warn("git clone received an invalid repository name.")
            return None
        if mode not in CLONE_MODES:
            raise BuildError(f"Unsupported git clone mode '{mode}' for '{repository_name}'.")

        target_directory = self.packages / repository_name
        clone_parent = Path(
            tempfile.mkdtemp(prefix=f".clone-{repository_name}.", dir=self.packages)
        )
        self._register(clone_parent)
        clone_directory = clone_parent / "repository"

        arguments = [
            "timeout",
            "--foreground",
            str(self.clone_timeout),
            "git",
            *user_agent_arguments(repository_url, git=True),
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "clone",
            "--quiet",
        ]
        if mode == "shallow":
            arguments += ["--depth", "1"]
        elif mode == "recurse":
            arguments += ["--depth", "1", "--recurse-submodules", "--shallow-submodules"]
        arguments += ["--", repository_url, str(clone_directory)]

        environment = {"GIT_TERMINAL_PROMPT": "0"}
        if self.runner.run_logged(arguments, env_overrides=environment) != 0:
            safe_remove_tree(clone_parent, self.packages)
            self._unregister(clone_parent)
            self.logger.warn(f"Failed to clone '{repository_url}'; retrying once.")
            clone_parent = Path(
                tempfile.mkdtemp(prefix=f".clone-{repository_name}.", dir=self.packages)
            )
            self._register(clone_parent)
            clone_directory = clone_parent / "repository"
            arguments[-1] = str(clone_directory)
            if self.runner.run_logged(arguments, env_overrides=environment) != 0:
                safe_remove_tree(clone_parent, self.packages)
                self._unregister(clone_parent)
                self.logger.warn(f"Failed to clone '{repository_url}' after two attempts.")
                return None

        actual_commit = self.local_head(clone_directory)
        if actual_commit is None:
            safe_remove_tree(clone_parent, self.packages)
            self._unregister(clone_parent)
            self.logger.warn(
                f"Cloned '{repository_url}', but its checked-out commit could not be verified."
            )
            return None

        if target_directory.is_symlink():
            raise BuildError(f"Refusing a symlinked Git destination: '{target_directory}'.")
        previous = clone_parent / ".previous-checkout"
        had_previous = target_directory.exists()
        # Once this directory can hold the old source, abort cleanup must leave
        # it alone. This also covers a signal immediately after the first rename.
        self._unregister(clone_parent)
        try:
            if had_previous:
                os.rename(target_directory, previous)
            try:
                os.rename(clone_directory, target_directory)
            except BaseException:
                if had_previous:
                    try:
                        os.rename(previous, target_directory)
                    except OSError as restore_error:
                        raise BuildError(
                            f"Git source restoration failed; recovery files remain at '{previous}'."
                        ) from restore_error
                raise
        except OSError as error:
            safe_remove_tree(clone_parent, self.packages)
            self._unregister(clone_parent)
            self.logger.warn(
                f"Failed to publish the completed clone for '{repository_name}': {error}"
            )
            return None
        safe_remove_tree(clone_parent, self.packages)
        self._unregister(clone_parent)
        return actual_commit
