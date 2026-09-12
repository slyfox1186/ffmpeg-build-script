from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from ffmpeg_build.runtime.build_lock import take_over_build_lock
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.logging import Logger
from ffmpeg_build.runtime.paths import DirectoryLock


def test_force_takeover_kills_only_the_lock_holder_and_its_workers(tmp_path: Path) -> None:
    root = tmp_path / "build"
    root.mkdir()
    holder = tmp_path / "holder.py"
    holder.write_text(
        "import fcntl, json, os, signal, subprocess, sys, time\n"
        "fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX)\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "worker = subprocess.Popen([sys.executable, '-c', "
        "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'], "
        "start_new_session=True)\n"
        "print(json.dumps({'owner': os.getpid(), 'worker': worker.pid}), flush=True)\n"
        "time.sleep(60)\n"
    )
    competitor = subprocess.Popen(
        [sys.executable, str(holder), str(root)], stdout=subprocess.PIPE, text=True
    )
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    worker_fd: int | None = None
    lock = DirectoryLock(root)
    try:
        assert competitor.stdout is not None
        assert select.select([competitor.stdout], [], [], 5)[0]
        processes = json.loads(competitor.stdout.readline())
        worker_fd = os.open(f"/proc/{processes['worker']}", os.O_RDONLY | os.O_DIRECTORY)
        assert lock.owner_pid() == competitor.pid
        assert take_over_build_lock(lock, Logger(), timeout=5)
        assert competitor.wait(timeout=5) == -signal.SIGKILL
        assert unrelated.poll() is None
        assert lock.held and lock.owner_pid() == os.getpid()
        try:
            with os.fdopen(os.open("stat", os.O_RDONLY, dir_fd=worker_fd)) as stream:
                assert stream.read().rsplit(")", 1)[1].split()[0] in ("Z", "X")
        except (FileNotFoundError, ProcessLookupError):
            pass
    finally:
        lock.release()
        for process in (competitor, unrelated):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        if competitor.stdout is not None:
            competitor.stdout.close()
        if worker_fd is not None:
            try:
                signal.pidfd_send_signal(worker_fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.close(worker_fd)


def test_takeover_does_not_signal_its_own_process(tmp_path: Path) -> None:
    original, contender = DirectoryLock(tmp_path), DirectoryLock(tmp_path)
    assert original.acquire()
    try:
        with pytest.raises(BuildError, match="Refusing to force-kill"):
            take_over_build_lock(contender, Logger())
        assert original.held and not contender.held
    finally:
        original.release()


def test_uncontended_takeover_needs_no_process_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = DirectoryLock(tmp_path)

    def forbidden() -> int:
        pytest.fail("An uncontended build must not inspect or signal other processes")

    monkeypatch.setattr(lock, "owner_pid", forbidden)
    try:
        assert take_over_build_lock(lock, Logger())
    finally:
        lock.release()


def test_takeover_resumes_owner_when_worker_cannot_be_signalled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from ffmpeg_build.runtime import build_lock

    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import fcntl,os,subprocess,sys,time; "
            "fd=os.open(sys.argv[1],os.O_RDONLY); fcntl.flock(fd,fcntl.LOCK_EX); "
            "worker=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
            "print(worker.pid,flush=True); time.sleep(60)",
            str(tmp_path),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    worker = None
    owner = None
    lock = DirectoryLock(tmp_path)
    try:
        assert child.stdout is not None
        assert select.select([child.stdout], [], [], 5)[0]
        worker_pid = int(child.stdout.readline())
        open_process = build_lock._open_process
        worker, owner = open_process(worker_pid), open_process(child.pid)

        def denied(pid: int) -> build_lock._Process:
            if pid == worker_pid:
                raise PermissionError("fixture worker cannot be signalled")
            return open_process(pid)

        monkeypatch.setattr(build_lock, "_open_process", denied)
        with pytest.raises(BuildError, match="Unable to stop competing build"):
            take_over_build_lock(lock, Logger())
        deadline = time.monotonic() + 3
        while owner.status()[0] in ("T", "t") and time.monotonic() < deadline:
            time.sleep(0.01)
        assert owner.status()[0] not in ("T", "t", "Z", "X")
        assert child.poll() is None and lock.owner_pid() == child.pid
        assert not lock.held
    finally:
        lock.release()
        for process in (worker, owner):
            if process is not None:
                process.send(signal.SIGKILL)
                os.close(process.fd)
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
        if child.stdout is not None:
            child.stdout.close()
