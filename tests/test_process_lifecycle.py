from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.exec import notify_failure


@pytest.mark.parametrize("mode", ["quiet", "debug", "terminal", "capture"])
def test_cancellation_stops_descendant_writes(context: BuildContext, mode: str) -> None:
    heartbeat = context.cwd / "heartbeat"
    child = (
        "import pathlib, time; p=pathlib.Path(" + repr(str(heartbeat)) + "); "
        "exec('while True:\\n p.write_text(str(time.monotonic()))\\n time.sleep(.01)')"
    )
    command = [
        sys.executable,
        "-c",
        "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', "
        + repr(child)
        + "]); time.sleep(30)",
    ]
    context.runner.log_file = None if mode == "terminal" else context.log_file
    context.runner.debug = mode == "debug"

    def interrupt(_number: int, _frame: object) -> None:
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGALRM, interrupt)
    try:
        signal.setitimer(signal.ITIMER_REAL, 1)
        with pytest.raises(KeyboardInterrupt):
            if mode == "capture":
                context.runner.capture(command)
            else:
                context.runner.run_logged(command)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    before = heartbeat.read_text()
    time.sleep(0.1)
    assert heartbeat.read_text() == before


def test_debug_large_input_and_output_do_not_deadlock(tmp_path: Path) -> None:
    # Bound the regression externally: a pipe deadlock must fail, not hang pytest.
    script = """
import sys
from pathlib import Path
from ffmpeg_build.runtime.exec import Runner, base_environment
from ffmpeg_build.runtime.logging import Logger
runner = Runner(Logger(), base_environment(), debug=True)
runner.log_file = Path(sys.argv[1])
code = "import sys; sys.stdout.write('x' * 200000); sys.stdout.flush(); assert len(sys.stdin.read()) == 200000"
assert runner.run_logged([sys.executable, '-c', code], stdin_text='y' * 200000) == 0
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "log")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    assert (tmp_path / "log").stat().st_size == 200000


def test_capture_non_utf8_output(context: BuildContext) -> None:
    result = context.runner.capture([sys.executable, "-c", "import os; os.write(1, b'\\xff')"])
    assert result.returncode == 0
    assert result.stdout == "\ufffd"


def test_capture_handles_large_duplex_input_and_timeout(context: BuildContext) -> None:
    code = "import sys; print('x' * 200000, end=''); sys.stdout.flush(); assert len(sys.stdin.read()) == 200000"
    result = context.runner.capture(
        [sys.executable, "-c", code], stdin_text="y" * 200000, timeout=5
    )
    assert result.returncode == 0 and len(result.stdout) == 200000
    timed_out = context.runner.capture(
        [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1
    )
    assert timed_out.returncode != 0 and "timed out" in timed_out.stderr


def test_notification_failure_does_not_mask_build_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/bin/notify-send")

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("desktop unavailable")

    monkeypatch.setattr(subprocess, "run", fail)
    notify_failure("original build failure")
