"""Force takeover of one build root without signalling unrelated processes."""

from __future__ import annotations

import ctypes
import os
import signal
import time
from dataclasses import dataclass

from .errors import BuildError
from .logging import Logger
from .paths import DirectoryLock

# Linux's syscall number for pidfd_send_signal on x86_64. Some CPython builds,
# including conda-forge's and python-build-standalone's, omit
# `signal.pidfd_send_signal` although the kernel provides the call.
_PIDFD_SEND_SIGNAL_SYSCALL = 424


def pidfd_send_signal(fd: int, signum: int) -> None:
    """Signal the process behind a pidfd or /proc/<pid> descriptor."""
    wrapper = getattr(signal, "pidfd_send_signal", None)
    if wrapper is not None:
        wrapper(fd, signum)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(
        ctypes.c_long(_PIDFD_SEND_SIGNAL_SYSCALL),
        ctypes.c_int(fd),
        ctypes.c_int(signum),
        None,
        ctypes.c_uint(0),
    )
    if result != 0:
        error = ctypes.get_errno()
        # OSError maps ESRCH to ProcessLookupError, matching the wrapper.
        raise OSError(error, os.strerror(error))


@dataclass
class _Process:
    pid: int
    fd: int

    def read(self, name: str) -> str:
        with os.fdopen(os.open(name, os.O_RDONLY, dir_fd=self.fd)) as stream:
            return stream.read()

    def status(self) -> tuple[str, int]:
        try:
            fields = self.read("stat").rsplit(")", 1)[1].split()
            return fields[0], int(fields[1])
        except (FileNotFoundError, ProcessLookupError):
            return "Z", 0

    def send(self, signum: signal.Signals) -> None:
        try:
            # A pinned /proc descriptor prevents a reused PID being signalled.
            pidfd_send_signal(self.fd, signum)
        except ProcessLookupError:
            pass

    def children(self) -> set[int]:
        task_fd = os.open("task", os.O_RDONLY | os.O_DIRECTORY, dir_fd=self.fd)
        try:
            result: set[int] = set()
            for task in os.listdir(task_fd):
                try:
                    with os.fdopen(
                        os.open(f"{task}/children", os.O_RDONLY, dir_fd=task_fd)
                    ) as stream:
                        result.update(int(pid) for pid in stream.read().split())
                except (FileNotFoundError, ProcessLookupError):
                    continue
            return result
        finally:
            os.close(task_fd)


def _open_process(pid: int) -> _Process:
    fd = os.open(f"/proc/{pid}", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    if os.fstat(fd).st_uid != os.geteuid():
        os.close(fd)
        raise BuildError(f"Competing build has a process owned by another user: PID {pid}.")
    return _Process(pid, fd)


def take_over_build_lock(lock: DirectoryLock, logger: Logger, *, timeout: float = 10) -> bool:
    """Stop and kill the verified owner and descendants, then acquire its lock.

    Each parent is stopped before enumerating its children so it cannot fork
    new workers during takeover. Subprocesses are killed before the owner;
    the new build starts only after all captured workers have exited and the
    kernel grants the directory lock. Download and host locks never use this.
    """
    if lock.acquire():
        return True
    owner = lock.owner_pid()
    if owner is None:
        return lock.acquire(timeout=timeout)
    if owner <= 1 or owner == os.getpid():
        raise BuildError(f"Refusing to force-kill build lock owner PID {owner}.")

    processes: list[_Process] = []
    deadline = time.monotonic() + timeout
    try:
        try:
            root = _open_process(owner)
        except (FileNotFoundError, ProcessLookupError):
            return lock.acquire(timeout=timeout)
        processes.append(root)
        # Revalidate after opening the process descriptor: the previous owner
        # may have exited while we were discovering it.
        if lock.owner_pid() != owner:
            return lock.acquire(timeout=timeout)
        logger.warn(f"Force-killing competing build PID {owner} using {lock.directory}.")
        index = 0
        while index < len(processes):
            if time.monotonic() >= deadline:
                raise BuildError("Timed out stopping competing build processes.")
            process = processes[index]
            index += 1
            if process.pid == os.getpid():
                raise BuildError("Refusing to kill an ancestor of the current build.")
            process.send(signal.SIGSTOP)
            while process.status()[0] not in ("T", "t", "Z", "X"):
                if time.monotonic() >= deadline:
                    raise BuildError(f"Competing process PID {process.pid} could not be stopped.")
                time.sleep(0.01)
            if process.status()[0] in ("Z", "X"):
                continue
            for pid in process.children():
                try:
                    child = _open_process(pid)
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if child.status()[1] != process.pid:
                    os.close(child.fd)
                    continue
                processes.append(child)

        for process in reversed(processes):
            process.send(signal.SIGKILL)
        while any(process.status()[0] not in ("Z", "X") for process in processes):
            if time.monotonic() >= deadline:
                raise BuildError(
                    "Competing build processes have not exited; refusing to overlap builds."
                )
            time.sleep(0.05)
        if not lock.acquire(timeout=timeout):
            return False
        logger.info(
            f"Stopped competing build and {len(processes) - 1} subprocesses; acquired build root."
        )
        return True
    except OSError as error:
        raise BuildError(f"Unable to stop competing build PID {owner}: {error}") from error
    finally:
        for process in reversed(processes):
            try:
                # On an interrupted or rejected takeover, never leave a
                # surviving process frozen. Killed processes return ESRCH.
                process.send(signal.SIGCONT)
            except OSError as error:
                logger.warn(
                    f"Could not resume surviving competing process PID {process.pid}: {error}"
                )
            finally:
                os.close(process.fd)
