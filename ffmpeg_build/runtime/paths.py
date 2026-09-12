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


def _open_directory(path: Path) -> int:
    """Pin every path component without following even an ancestor symlink."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.absolute().parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _same_inode(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _remove_at(parent_fd: int, name: str, device: int) -> None:
    # Post-order traversal without Python recursion: valid source archives can
    # contain more directory levels than the interpreter's recursion limit.
    pending: list[tuple[int, str, os.stat_result | None, int | None]] = [
        (parent_fd, name, None, None)
    ]
    opened: set[int] = set()
    try:
        while pending:
            parent, child, expected, child_fd = pending.pop()
            if child_fd is not None:
                assert expected is not None
                if not _same_inode(expected, os.stat(child, dir_fd=parent, follow_symlinks=False)):
                    raise OSError(errno.ESTALE, "Directory changed during removal", child)
                os.rmdir(child, dir_fd=parent)
                os.close(child_fd)
                opened.remove(child_fd)
                continue
            try:
                inspected = os.stat(child, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if inspected.st_dev != device:
                continue
            if not stat.S_ISDIR(inspected.st_mode):
                try:
                    os.unlink(child, dir_fd=parent)
                except FileNotFoundError:
                    pass
                continue
            fd = os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=parent)
            opened.add(fd)
            if not _same_inode(inspected, os.fstat(fd)):
                raise OSError(errno.ESTALE, "Directory changed before removal", child)
            pending.append((parent, child, inspected, fd))
            with os.scandir(fd) as entries:
                pending.extend((fd, entry.name, None, None) for entry in entries)
    finally:
        for fd in opened:
            os.close(fd)


def remove_tree_one_filesystem(target: Path) -> None:
    """Remove through pinned directory descriptors, staying on one device.

    Device boundaries are preserved, as with rm --one-file-system. A bind
    mount of the same device is not distinguishable by st_dev.
    """
    if target.absolute() == Path("/"):
        raise BuildError("Refusing to remove '/'.")
    try:
        parent_fd = _open_directory(target.parent)
    except FileNotFoundError:
        return
    try:
        try:
            inspected = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        _remove_at(parent_fd, target.name, inspected.st_dev)
    finally:
        os.close(parent_fd)


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

    def _open(self) -> int:
        try:
            return _open_directory(self.directory)
        except OSError as error:
            raise BuildError(
                f"Unable to open lock directory '{self.directory}': {error}"
            ) from error

    def acquire(self, *, timeout: float | None = None) -> bool:
        """Take the lock, returning False on contention rather than raising.

        `fcntl.flock` offers no timeout, so a bounded wait is a non-blocking
        attempt inside a monotonic poll loop.
        """
        if self._fd is not None:
            return True
        # PEP 446 makes this descriptor non-inheritable, so no child and no
        # background helper can keep the lock alive past this process.
        fd = self._open()
        deadline = None if timeout is None else time.monotonic() + timeout
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN):
                        raise
                    if deadline is None:
                        return False
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    time.sleep(min(0.25, remaining))
                    continue
                self._fd = fd
                return True
        except OSError as error:
            raise BuildError(f"Unable to lock directory '{self.directory}': {error}") from error
        finally:
            if self._fd is None:
                os.close(fd)

    def release(self) -> None:
        if self._fd is None:
            return
        os.close(self._fd)
        self._fd = None

    def assert_current(self) -> None:
        """Reject a replaced path even though its original inode stays locked."""
        if self._fd is None:
            raise BuildError(f"Directory lock is not held: '{self.directory}'.")
        current_fd = self._open()
        try:
            if not _same_inode(os.fstat(self._fd), os.fstat(current_fd)):
                raise BuildError(f"Locked directory was replaced: '{self.directory}'.")
        finally:
            os.close(current_fd)

    def __enter__(self) -> DirectoryLock:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()
