#!/usr/bin/env python3
"""Launcher: answer metadata options, pick an interpreter, then run the build.

This is the only file that must parse and run on whatever `python3` the user
happens to have, so it stays syntactically conservative and imports nothing
from the build package until an interpreter of the required version is running.

Ordering here is load-bearing. `--help` and `--version` are answered before any
interpreter resolution, because they are contractually free of side effects and
resolving an interpreter can mean creating an environment and asking a
question.
"""

from __future__ import annotations

import os
import subprocess
import sys

# Metadata requests must not create bytecode caches on a fresh checkout.
sys.dont_write_bytecode = True

REQUIRED_VERSION = (3, 12)
CONDA_ROOT = os.path.expanduser("~/miniconda3")
CONDA_ENVIRONMENT = "install-ffmpeg"
CONDA_PYTHON_VERSION = "3.12"

# The environment includes the interactive UI and optional development tools.
# Command-line builds themselves still use only the standard library.
PIP_PACKAGES = ("textual>=8.2.8", "pytest", "ruff", "mypy", "pyte>=0.8")

# Set across the re-exec so a resolved interpreter cannot resolve again.
RESOLVED_GUARD = "FFMPEG_BUILD_INTERPRETER_RESOLVED"

REPOSITORY_ROOT = os.path.dirname(os.path.abspath(__file__))


def interpreter_version(executable: str) -> tuple[int, int] | None:
    """Report an interpreter's version without importing anything from it."""
    try:
        completed = subprocess.run(
            [executable, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    if completed.returncode != 0:
        return None
    parts = completed.stdout.strip().split(".")
    if len(parts) != 2 or not all(part.isascii() and part.isdigit() for part in parts):
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def ask_consent(question: str) -> bool:
    """Ask once, and treat a non-interactive stdin as a refusal.

    Every other prompt in this project behaves the same way, so an automated
    run never blocks and never quietly opts into something it was not told to
    do.
    """
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(question)
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower() in ("y", "yes")


def create_conda_environment(conda_executable: str, environment_python: str) -> bool:
    print("Creating the '%s' conda environment..." % CONDA_ENVIRONMENT)
    created = subprocess.run(
        [
            conda_executable,
            "create",
            "-y",
            "-n",
            CONDA_ENVIRONMENT,
            "python=" + CONDA_PYTHON_VERSION,
        ],
        check=False,
    )
    if created.returncode != 0:
        sys.stderr.write(
            "Could not create the '%s' conda environment; using the system interpreter.\n"
            % CONDA_ENVIRONMENT
        )
        return False
    if not os.access(environment_python, os.X_OK):
        sys.stderr.write(
            "The '%s' conda environment was created without a usable interpreter; "
            "using the system interpreter.\n" % CONDA_ENVIRONMENT
        )
        return False
    installed = subprocess.run(
        [environment_python, "-m", "pip", "install"] + list(PIP_PACKAGES), check=False
    )
    if installed.returncode != 0:
        # A failed UI/tool install does not invalidate the standard-library
        # builder. Menu entry reports the missing dependency with a remedy.
        sys.stderr.write(
            "Menu/development packages could not be installed; CLI builds remain available.\n"
        )
    return True


def resolve_conda_interpreter() -> str | None:
    """Return the conda environment's interpreter, or None to fall back."""
    conda_executable = os.path.join(CONDA_ROOT, "bin", "conda")
    if not os.access(conda_executable, os.X_OK):
        return None
    environment_python = os.path.join(CONDA_ROOT, "envs", CONDA_ENVIRONMENT, "bin", "python")
    if os.access(environment_python, os.X_OK):
        if (interpreter_version(environment_python) or (0, 0)) >= REQUIRED_VERSION:
            return environment_python
        sys.stderr.write(
            "The existing Conda interpreter is incompatible; checking system Python.\n"
        )
        return None
    question = "Create conda environment '%s' (python=%s) and install %s? [y/N]: " % (
        CONDA_ENVIRONMENT,
        CONDA_PYTHON_VERSION,
        ", ".join(PIP_PACKAGES),
    )
    if not ask_consent(question):
        return None
    if not create_conda_environment(conda_executable, environment_python):
        return None
    return environment_python


def resolve_system_interpreter() -> str | None:
    """Find a system interpreter new enough to run the build."""
    candidates = ["/usr/bin/python3", "/usr/bin/python3.12", sys.executable]
    path_python = None
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, "python3")
        if os.access(candidate, os.X_OK):
            path_python = candidate
            break
    if path_python is not None:
        candidates.append(path_python)
    for candidate in candidates:
        if (
            os.access(candidate, os.X_OK)
            and (interpreter_version(candidate) or (0, 0)) >= REQUIRED_VERSION
        ):
            return candidate
    return None


def report_missing_interpreter() -> None:
    found = "%d.%d" % sys.version_info[:2]
    required = "%d.%d" % REQUIRED_VERSION
    sys.stderr.write(
        "This project needs Python %s or newer; the interpreter found is %s.\n"
        "Install a newer interpreter, or let this script create the '%s' conda\n"
        "environment for you by installing Miniconda at %s.\n"
        "On Ubuntu 22.04 and Debian 12, 'python3' is older than %s, so one of those\n"
        "two paths is required there.\n"
        % (required, found, CONDA_ENVIRONMENT, CONDA_ROOT, required)
    )


def reexec(interpreter: str, argv: list[str]) -> None:
    os.environ[RESOLVED_GUARD] = "1"
    os.execv(interpreter, [interpreter, os.path.abspath(__file__)] + argv)


def main(argv: list[str]) -> int:
    if REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, REPOSITORY_ROOT)

    from ffmpeg_build.usage import metadata_response

    answer = metadata_response(argv or ["--help"])
    if answer is not None:
        sys.stdout.write(answer)
        return 0

    if not os.environ.get(RESOLVED_GUARD):
        interpreter = resolve_conda_interpreter()
        if interpreter is None:
            interpreter = resolve_system_interpreter()
        if interpreter is None:
            report_missing_interpreter()
            return 1
        if os.path.realpath(interpreter) != os.path.realpath(sys.executable):
            reexec(interpreter, argv)
        os.environ[RESOLVED_GUARD] = "1"

    if sys.version_info[:2] < REQUIRED_VERSION:
        report_missing_interpreter()
        return 1

    from ffmpeg_build.main import main as run_build

    return run_build(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
