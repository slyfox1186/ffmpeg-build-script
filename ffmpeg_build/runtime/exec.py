"""Subprocess execution, child environments, and the sudo credential cache.

Child environments are composed from an allowlist rather than scrubbed of named
variables. A denylist is whack-a-mole: beyond the five variables the Bash build
removed before FFmpeg's `configure`, a Conda environment reaches a native build
through `LD_LIBRARY_PATH`, `CMAKE_PREFIX_PATH`, `PKG_CONFIG_PATH`,
`CONDA_BUILD_SYSROOT`, `SSL_CERT_FILE` and activation-set `CC`/`CFLAGS`/
`LDFLAGS`. Starting from a curated base makes that leakage structurally
impossible instead of enumerably unlikely, and it generalizes the instinct the
Bash `source_path` already had when it reset `PATH` rather than filtering it.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

from . import shellquote
from .errors import BuildError, SignalStop
from .logging import Logger, format_duration

# Supported hosts provide the bootstrap toolchain in these administrator-
# controlled locations. Starting from a deterministic base prevents an
# unrelated user-local executable from silently replacing a build tool.
BASE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin"

# Variables a build legitimately needs from the invoking session. Everything
# else is dropped, including every variable a Python environment manager sets.
_INHERITED_EXACT = (
    "HOME",
    "USER",
    "LOGNAME",
    "TERM",
    "SHELL",
    "TMPDIR",
    "NO_COLOR",
    "SOURCE_DATE_EPOCH",
    "GIT_TERMINAL_PROMPT",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
)
_INHERITED_PREFIXES = ("LC_", "LANG", "XDG_", "SUDO_")


def base_environment() -> dict[str, str]:
    """The starting environment for every child process this build runs."""
    environment: dict[str, str] = {}
    for name, value in os.environ.items():
        if name in _INHERITED_EXACT or name.startswith(_INHERITED_PREFIXES):
            environment[name] = value
    environment["PATH"] = BASE_PATH
    # Deterministic collation and timestamps: a locale-dependent sort would
    # reorder generated lists between hosts, and a local time zone would change
    # bytes in build output that is otherwise reproducible.
    environment["LC_ALL"] = "C"
    environment["TZ"] = "UTC"
    return environment


def path_prepend(environment: dict[str, str], directory: str | os.PathLike[str]) -> None:
    """Put an existing directory first on PATH, removing any later duplicate."""
    candidate = os.fspath(directory)
    if not candidate or not os.path.isdir(candidate):
        return
    entries = [candidate]
    for entry in environment.get("PATH", "").split(":"):
        if entry and entry not in entries:
            entries.append(entry)
    environment["PATH"] = ":".join(entries)


def strip_workspace_entries(value: str, workspace: Path, separator: str = " ") -> str:
    """Drop workspace paths and their include/library search options together.

    Used to build a host tool against system libraries while a half-built
    dependency tree is already installed in the workspace.
    """
    workspace_text = str(workspace)

    def inside(path: str) -> bool:
        return path == workspace_text or path.startswith(workspace_text + "/")

    if separator != " ":
        return separator.join(part for part in value.split(separator) if part and not inside(part))
    parts = value.split()
    kept: list[str] = []
    index = 0
    path_options = ("-I", "-L", "-isystem", "-iquote", "--sysroot")
    prefixes = ("", "-I", "-L", "-isystem", "-iquote", "--sysroot=")
    while index < len(parts):
        part = parts[index]
        if part in path_options and index + 1 < len(parts):
            if not inside(parts[index + 1]):
                kept.extend(parts[index : index + 2])
            index += 2
            continue
        if not any(part.startswith(prefix) and inside(part[len(prefix) :]) for prefix in prefixes):
            kept.append(part)
        index += 1
    return separator.join(kept)


class CommandFailed(BuildError):
    """A logged command exited non-zero."""

    def __init__(self, message: str, exit_code: int, command: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.command = command


def _terminate_process(
    process: subprocess.Popen[bytes], signal_relay: bool, original: BaseException
) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError as error:
        original.add_note(f"Unable to signal every process in group {process.pid}: {error}")
    if signal_relay:
        # sudo relays TERM and waits for its privileged command, but cannot
        # relay KILL. Killing sudo could orphan an installer and let it race
        # rollback. Retain locks until sudo confirms command termination.
        process.wait()
        return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            original.add_note(f"Unable to kill every process in group {process.pid}: {error}")
        process.wait()


@contextmanager
def managed_process(
    process: subprocess.Popen[bytes], *, signal_relay: bool = False
) -> Iterator[subprocess.Popen[bytes]]:
    """Reap the command and stop its process group before unwinding a build.

    Callers create a new process group, retaining the controlling terminal for
    sudo. Killing only make leaves its compiler children writing after locks
    have been released or installation rollback has started.
    """
    try:
        yield process
    except BaseException as original:
        while True:
            try:
                _terminate_process(process, signal_relay, original)
                break
            except (KeyboardInterrupt, SignalStop):
                # A second cancellation must not release locks or start rollback
                # while the original command can still write. Retry shutdown;
                # the first exception is reported once termination is confirmed.
                continue
        raise
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


class Runner:
    """Runs commands with this project's logging and environment behavior."""

    def __init__(self, logger: Logger, environment: dict[str, str], *, debug: bool = False) -> None:
        self.logger = logger
        self.environment = environment
        self.debug = debug
        self.log_file: Path | None = None
        self._keepalive_stop = threading.Event()
        self._keepalive_thread: threading.Thread | None = None

    # -- environment -----------------------------------------------------

    def child_environment(self, overrides: Mapping[str, str] | None = None) -> dict[str, str]:
        environment = dict(self.environment)
        if overrides:
            for name, value in overrides.items():
                if value is None:
                    environment.pop(name, None)
                else:
                    environment[name] = value
        return environment

    # -- logging helpers -------------------------------------------------

    def _log_size(self) -> int:
        if self.log_file is None or not self.log_file.is_file():
            return 0
        try:
            return self.log_file.stat().st_size
        except OSError:
            return 0

    def _replay_log(self, start: int) -> None:
        """Replay only the failed command's newly appended output.

        The original stays in the log, so this is written straight to stderr
        rather than through the logger, which would duplicate it there.
        """
        if self.log_file is None or not self.log_file.is_file():
            return
        try:
            with self.log_file.open("rb") as handle:
                handle.seek(start)
                sys.stderr.write("\n")
                for payload in iter(lambda: handle.read(65536), b""):
                    sys.stderr.buffer.write(payload)
                sys.stderr.flush()
        except OSError:
            return

    # -- execution -------------------------------------------------------

    def run_logged(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        stdin_text: str | None = None,
    ) -> int:
        try:
            return self._run_logged(
                arguments, cwd=cwd, env_overrides=env_overrides, stdin_text=stdin_text
            )
        except FileNotFoundError as error:
            self.logger.error(f"Unable to run command: {error}")
            return 127
        except OSError as error:
            raise BuildError(f"Unable to run or record command output: {error}") from error

    def _run_logged(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        stdin_text: str | None = None,
    ) -> int:
        """Run a command, log it, and return its status instead of raising.

        Callers that must recover from a failure rather than abort on it — the
        staged install, which has to restore its backup first — use this
        directly; `execute` is this plus fail-on-non-zero.
        """
        if not arguments:
            raise BuildError("run_logged() called without a command.")
        command_display = shellquote.join(list(arguments))
        self.logger.run(command_display, arguments=arguments)
        started = self.logger.elapsed_seconds
        environment = self.child_environment(env_overrides)
        working_directory = str(cwd) if cwd is not None else None

        if self.debug and self.log_file is not None:
            exit_code = self._run_teed(arguments, working_directory, environment, stdin_text)
        elif self.log_file is not None:
            start = self._log_size()
            with self.log_file.open("ab") as sink:
                with managed_process(
                    subprocess.Popen(
                        list(arguments),
                        cwd=working_directory,
                        env=environment,
                        stdout=sink,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.PIPE if stdin_text is not None else None,
                        process_group=0,
                    ),
                    signal_relay=Path(arguments[0]).name == "sudo",
                ) as process:
                    process.communicate(stdin_text.encode() if stdin_text is not None else None)
                    exit_code = process.wait()
            if exit_code != 0:
                self._replay_log(start)
        else:
            with managed_process(
                subprocess.Popen(
                    list(arguments),
                    cwd=working_directory,
                    env=environment,
                    stdin=subprocess.PIPE if stdin_text is not None else None,
                    process_group=0,
                ),
                signal_relay=Path(arguments[0]).name == "sudo",
            ) as process:
                process.communicate(stdin_text.encode() if stdin_text is not None else None)
                exit_code = process.wait()

        # Only the slow commands get a timing line. A compile that ran for
        # twenty minutes is worth recording; a version probe that took no
        # measurable time would push the useful output off the screen.
        duration = self.logger.elapsed_seconds - started
        if exit_code == 0 and duration >= 30:
            self.logger.time(f"finished in {format_duration(duration)}")
        return exit_code

    def _run_teed(
        self,
        arguments: Sequence[str],
        cwd: str | None,
        environment: Mapping[str, str],
        stdin_text: str | None,
    ) -> int:
        """Stream a command's output while also recording it.

        A log write that fails here takes the command down with it: under the
        debug flag the log is the artifact the user asked for, and silently
        producing a partial one would make a bug report misleading.
        """
        assert self.log_file is not None
        # A file-backed input avoids a pipe deadlock when a child produces
        # output before reading all its input. Output remains bounded chunks.
        with self.log_file.open("ab") as sink, tempfile.TemporaryFile() as source:
            if stdin_text is not None:
                source.write(stdin_text.encode())
                source.seek(0)
            with managed_process(
                subprocess.Popen(
                    list(arguments),
                    cwd=cwd,
                    env=dict(environment),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=source if stdin_text is not None else None,
                    process_group=0,
                ),
                signal_relay=Path(arguments[0]).name == "sudo",
            ) as process:
                assert process.stdout is not None
                output = process.stdout
                for chunk in iter(lambda: os.read(output.fileno(), 65536), b""):
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.flush()
                    sink.write(chunk)
                sink.flush()
                return process.wait()

    def execute(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        stdin_text: str | None = None,
    ) -> None:
        """Run a command and abort the build if it fails."""
        command_display = shellquote.join(list(arguments))
        exit_code = self.run_logged(
            arguments, cwd=cwd, env_overrides=env_overrides, stdin_text=stdin_text
        )
        if exit_code != 0:
            notify_failure(f"Command failed: '{command_display}'.")
            raise CommandFailed(
                f"Command failed with exit code {exit_code}: '{command_display}'.",
                exit_code,
                command_display,
            )

    def capture(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        timeout: float | None = 30,
        stdin_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command for its output, never raising.

        Probes feed long boolean chains in the FFmpeg stage. Turning a missing
        optional feature into an exception would abort builds the recipe
        deliberately wrote to continue, so a missing executable and a non-zero
        exit are reported the same way: through the returned status.
        """
        try:
            with managed_process(
                subprocess.Popen(
                    list(arguments),
                    cwd=str(cwd) if cwd is not None else None,
                    env=self.child_environment(env_overrides),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE if stdin_text is not None else None,
                    process_group=0,
                )
            ) as process:
                stdout, stderr = process.communicate(
                    stdin_text.encode() if stdin_text is not None else None, timeout=timeout
                )
                return subprocess.CompletedProcess(
                    list(arguments),
                    process.returncode,
                    stdout.decode(errors="replace"),
                    stderr.decode(errors="replace"),
                )
        except (OSError, subprocess.SubprocessError) as error:
            return subprocess.CompletedProcess(list(arguments), 127, "", str(error))

    def probe(self, arguments: Sequence[str], *, timeout: float | None = 30) -> bool:
        return self.capture(arguments, timeout=timeout).returncode == 0

    def which(self, tool: str) -> str | None:
        return shutil.which(tool, path=self.environment.get("PATH", BASE_PATH))

    # -- sudo ------------------------------------------------------------

    def require_sudo(self) -> None:
        if self.which("sudo") is None:
            raise BuildError("This script requires 'sudo' (run on a system with sudo configured).")
        # Prompt once up front; failing mid-build after an hour of compiling is
        # a worse experience than a password prompt before any work starts.
        completed = subprocess.run(["sudo", "-v"], env=self.child_environment(), check=False)
        if completed.returncode != 0:
            raise BuildError("Unable to validate 'sudo' credentials.")
        self.start_sudo_keepalive()

    def start_sudo_keepalive(self) -> None:
        """Keep the cached credential fresh for the whole build.

        Without this the single `sudo -v` above expires (sudo's
        `timestamp_timeout`, 15 minutes by default) and every later step
        prompts again in the middle of a compile.
        """
        if self._keepalive_thread is not None:
            return

        def refresh() -> None:
            while not self._keepalive_stop.wait(50):
                # -n never prompts. If the credential cannot be refreshed
                # without one, stop instead of spinning.
                if self.capture(["sudo", "-n", "-v"], timeout=10).returncode != 0:
                    return

        self._keepalive_thread = threading.Thread(
            target=refresh, name="sudo-keepalive", daemon=True
        )
        self._keepalive_thread.start()

    def stop_sudo_keepalive(self) -> None:
        if self._keepalive_thread is None:
            return
        self._keepalive_stop.set()
        # A refresh has a ten-second deadline plus process cleanup time.
        self._keepalive_thread.join(timeout=12)
        self._keepalive_thread = None


def notify_failure(message: str) -> None:
    """Desktop notification on failure, when one is available.

    `notify-send` is optional and absent on headless systems, so its absence
    must not itself become a reported error right before the real one.
    """
    if shutil.which("notify-send") is None:
        return
    try:
        subprocess.run(
            ["notify-send", "-t", "5000", "--", message],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        # Desktop notification is best-effort and must never mask build failure.
        pass
