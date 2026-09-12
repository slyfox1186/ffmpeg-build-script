"""Path canonicalization, bounded deletion, and directory locks.

The deletion and locking primitives here are the project's reason for existing:
nothing is removed without a containment check against an explicitly supplied
root, and locks are taken on directory file descriptors rather than on lock
files so a symlink cannot redirect them.
"""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import time
from pathlib import Path

from .errors import BuildError

# Directories a build root may never be, checked in addition to the repository
# and home-directory rules below.
UNSAFE_BUILD_ROOTS = frozenset(
    {
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/home",
        "/lib",
        "/lib64",
        "/opt",
        "/proc",
        "/root",
        "/run",
        "/sbin",
        "/srv",
        "/sys",
        "/tmp",
        "/usr",
        "/usr/local",
        "/var",
    }
)


def canonicalize(path: str | os.PathLike[str]) -> Path:
    """Resolve a path without requiring it to exist.

    Equivalent to `readlink -m`: `/nonexistent/a/../b` becomes `/nonexistent/b`
    rather than raising.
    """
    return Path(os.path.realpath(os.fspath(path), strict=False))


def path_is_within(candidate: str | os.PathLike[str], root: str | os.PathLike[str]) -> bool:
    """True when `candidate` resolves to a strict descendant of `root`.

    Resolving both sides first is what stops a string-prefix check from
    accepting `/tmp/packages-elsewhere` for a root of `/tmp/packages`.
    """
    resolved_candidate = canonicalize(candidate)
    resolved_root = canonicalize(root)
    if resolved_candidate == resolved_root:
        return False
    return resolved_root in resolved_candidate.parents


def _purge_directory(directory_fd: int, device: int) -> None:
    """Empty one directory, never following a symlink or crossing a mount.

    `shutil.rmtree` has no one-file-system guard and no `xdev` parameter, so
    the `rm -rf --one-file-system` behavior this project relies on has to be
    written out. Entries on another device are left intact exactly as GNU `rm`
    leaves them.
    """
    with os.scandir(directory_fd) as entries:
        children = list(entries)
    for entry in children:
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if entry_stat.st_dev != device:
            continue
        if stat.S_ISDIR(entry_stat.st_mode):
            try:
                child_fd = os.open(
                    entry.name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY,
                    dir_fd=directory_fd,
                )
            except OSError:
                continue
            try:
                _purge_directory(child_fd, device)
            finally:
                os.close(child_fd)
            try:
                os.rmdir(entry.name, dir_fd=directory_fd)
            except OSError:
                pass
        else:
            try:
                os.unlink(entry.name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def remove_tree_one_filesystem(target: Path) -> None:
    """Remove `target` and everything under it on the same filesystem."""
    try:
        target_stat = os.lstat(target)
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(target_stat.st_mode):
        os.unlink(target)
        return
    directory_fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
    try:
        _purge_directory(directory_fd, target_stat.st_dev)
    finally:
        os.close(directory_fd)
    os.rmdir(target)


def safe_remove_tree(target: str | os.PathLike[str], allowed_root: str | os.PathLike[str]) -> None:
    """Remove one path only when it is a strict descendant of `allowed_root`."""
    target_path = Path(target)
    if not target_path.exists() and not target_path.is_symlink():
        return
    # Every caller passes a directory this project created and manages. A
    # symlink there means something unexpected replaced it, and following one
    # would delete a tree the containment check never examined.
    if target_path.is_symlink():
        raise BuildError(f"Refusing to remove a symlinked path: '{target_path}'.")

    resolved_target = canonicalize(target_path)
    resolved_root = canonicalize(allowed_root)
    if str(resolved_root) == "/":
        raise BuildError("Refusing to use '/' as a removal root.")
    if resolved_target == resolved_root:
        raise BuildError(f"Refusing to remove the allowed root itself: '{resolved_target}'.")
    if not path_is_within(resolved_target, resolved_root):
        raise BuildError(f"Refusing to remove path outside '{resolved_root}': '{resolved_target}'.")

    # Remove the path that was actually validated. Passing the raw argument
    # would let the kernel re-resolve it after the containment check, so the
    # check and the deletion could disagree about which tree is being removed.
    try:
        remove_tree_one_filesystem(resolved_target)
    except OSError as error:
        raise BuildError(f"Failed to remove bounded path '{resolved_target}': {error}") from error


def is_exclusive_regular_file(path: Path) -> bool:
    """True for a regular file that is neither a symlink nor multiply linked.

    A second hard link means another name for the same inode exists, so writing
    through this path would change a file outside the build root as well.
    """
    try:
        file_stat = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(file_stat.st_mode) and file_stat.st_nlink == 1


class DirectoryLock:
    """An advisory lock held on an open directory file descriptor.

    Locking the already-validated directory itself, rather than a separately
    named lock file, means there is no path for a symlink to redirect between
    the containment check and the lock.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self, *, timeout: float | None = None) -> bool:
        """Take the lock, returning False on contention rather than raising.

        `fcntl.flock` offers no timeout, so a bounded wait is a non-blocking
        attempt inside a monotonic poll loop.
        """
        if self._fd is not None:
            return True
        # PEP 446 makes this descriptor non-inheritable, so no child and no
        # background helper can keep the lock alive past this process.
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN):
                    os.close(fd)
                    raise
                if deadline is not None and time.monotonic() >= deadline:
                    os.close(fd)
                    return False
                if deadline is None:
                    os.close(fd)
                    return False
                time.sleep(0.25)
                continue
            self._fd = fd
            return True

    def release(self) -> None:
        if self._fd is None:
            return
        os.close(self._fd)
        self._fd = None

    def __enter__(self) -> DirectoryLock:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()
