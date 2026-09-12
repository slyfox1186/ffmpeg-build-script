"""Lazy entry point: command-line builds do not import Textual or its dependencies."""

from __future__ import annotations

import importlib.util
import shlex
import signal
import subprocess
import sys
from pathlib import Path
from types import FrameType

from ..config import BuildSettings, default_states
from ..runtime.errors import BuildError, SignalStop
from .model import LaunchSettings, MenuModel
from .session import MenuResult


def _clear_terminal() -> None:
    """Run clear only after Textual has restored terminal modes and its screen."""
    try:
        completed = subprocess.run(
            ["clear"], stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Warning: unable to clear the terminal: {error}", file=sys.stderr)
    else:
        if completed.returncode:
            print(f"Warning: 'clear' exited with status {completed.returncode}.", file=sys.stderr)


def run_menu(
    states: dict[str, bool] | None,
    settings: BuildSettings,
    default_path: Path,
    launch: LaunchSettings | None = None,
) -> MenuResult:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError(
            "The interactive menu needs a terminal. Edit a TOML file and pass it with '--config' instead."
        )
    if importlib.util.find_spec("textual") is None:
        command = shlex.join([sys.executable, "-m", "pip", "install", "textual>=8.2.8"])
        raise RuntimeError(f"The interactive menu requires Textual. Install it using:\n  {command}")
    from .app import MenuApp

    application = MenuApp(
        MenuModel(states if states is not None else default_states(), settings),
        default_path,
        launch,
    )
    interrupted: SignalStop | None = None
    previous_handlers = {
        number: signal.getsignal(number)
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }

    def stop_menu(number: int, frame: FrameType | None) -> None:
        nonlocal interrupted
        interrupted = SignalStop(signal.Signals(number).name.removeprefix("SIG"), 128 + number)
        if not application.is_running:
            raise interrupted
        # Raising through asyncio can strand Textual's input/writer threads.
        # Request its normal shutdown, then propagate the signal after teardown.
        application.exit(return_code=interrupted.exit_code)

    try:
        for number in previous_handlers:
            signal.signal(number, stop_menu)
        result = application.run()
        if interrupted is not None:
            raise interrupted
        if application.failure is not None:
            raise BuildError(
                f"Terminal menu failed: {application.failure}"
            ) from application.failure
        if application.return_code:
            raise BuildError(f"Terminal menu exited with status {application.return_code}.")
        return result or application.session.result
    except (KeyboardInterrupt, EOFError):
        return application.session.result
    finally:
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)
        _clear_terminal()
