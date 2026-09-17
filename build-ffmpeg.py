#!/usr/bin/env python3
"""Launcher: answer metadata options, pick an interpreter, then run the build.

This is the only file that must parse and run on whatever `python3` the user
happens to have, so it stays syntactically conservative. Before an interpreter
of the required version is running it imports only `ffmpeg_build.usage`, which
is kept parseable on Python 3.10.

Ordering here is load-bearing. `--help` and `--version` are answered before any
interpreter resolution, because they are contractually free of side effects and
resolving an interpreter can mean creating an environment and asking a
question.

When Conda is available the build always runs in the Conda environment; a
system interpreter is used only on hosts without Conda.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys

# Metadata requests must not create bytecode caches on a fresh checkout.
sys.dont_write_bytecode = True

REQUIRED_VERSION = (3, 12)
CONDA_ENVIRONMENT = "install-ffmpeg"
# The newest stable Python that passes the project's lint and test gates.
CONDA_PYTHON_VERSION = "3.14"
# conda-forge needs no Terms of Service acceptance, unlike Anaconda's default
# channels, so a non-interactive `conda create` cannot stop on that prompt.
CONDA_CHANNEL = "conda-forge"
CONDA_ROOTS = ("~/miniconda3", "~/miniforge3", "~/anaconda3")

# Matches the `menu` extra in pyproject.toml; a test keeps the two identical.
# Command-line builds use only the standard library.
MENU_PACKAGES = ("textual>=8.2.8",)

# Set across the re-exec so a resolved interpreter cannot resolve again.
RESOLVED_GUARD = "FFMPEG_BUILD_INTERPRETER_RESOLVED"

# realpath so a symlinked launcher still finds the checkout's package.
REPOSITORY_ROOT = os.path.dirname(os.path.realpath(__file__))

SYSTEM_PYTHON_NAME = re.compile(r"^python3(\.[0-9]+)?$")


def interpreter_version(executable: str) -> tuple[int, int, bool] | None:
    """Report (major, minor, is_final_release) without importing anything from it."""
    try:
        completed = subprocess.run(
            [
                executable,
                "-c",
                "import sys; print('%d.%d %s' % (sys.version_info[:2] + (sys.version_info[3],)))",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    if completed.returncode != 0:
        return None
    fields = completed.stdout.strip().split(" ")
    if len(fields) != 2:
        return None
    parts = fields[0].split(".")
    if len(parts) != 2 or not all(part.isascii() and part.isdigit() for part in parts):
        return None
    try:
        return (int(parts[0]), int(parts[1]), fields[1] == "final")
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


def path_directories() -> list[str]:
    """PATH entries, skipping empty and relative ones that would resolve against the cwd."""
    return [
        directory
        for directory in os.environ.get("PATH", "").split(os.pathsep)
        if os.path.isabs(directory)
    ]


def conda_roots() -> list[str]:
    """Conda installations on this host: the active one first, then the usual install roots."""
    candidates: list[str] = []
    executables = [os.environ.get("CONDA_EXE", "")]
    executables.extend(os.path.join(directory, "conda") for directory in path_directories())
    for executable in executables:
        if executable and os.access(executable, os.X_OK):
            # bin/conda and condabin/conda both sit one level below the root.
            candidates.append(os.path.dirname(os.path.dirname(os.path.realpath(executable))))
    candidates.extend(os.path.realpath(os.path.expanduser(root)) for root in CONDA_ROOTS)
    roots: list[str] = []
    for root in candidates:
        if root not in roots and os.access(os.path.join(root, "bin", "conda"), os.X_OK):
            roots.append(root)
    return roots


def environment_python(root: str) -> str:
    return os.path.join(root, "envs", CONDA_ENVIRONMENT, "bin", "python")


def conda_create_command(root: str) -> list[str]:
    # An explicit prefix keeps the environment where `environment_python` looks,
    # whatever `envs_dirs` the user's .condarc configures.
    return [
        os.path.join(root, "bin", "conda"),
        "create",
        "-y",
        "-p",
        os.path.join(root, "envs", CONDA_ENVIRONMENT),
        "-c",
        CONDA_CHANNEL,
        "--override-channels",
        "python=" + CONDA_PYTHON_VERSION,
    ]


def create_conda_environment(root: str) -> bool:
    print("Creating the '%s' conda environment..." % CONDA_ENVIRONMENT)
    created = subprocess.run(conda_create_command(root), check=False)
    python = environment_python(root)
    if created.returncode != 0:
        sys.stderr.write("Could not create the '%s' conda environment.\n" % CONDA_ENVIRONMENT)
        return False
    if not os.access(python, os.X_OK):
        sys.stderr.write(
            "The '%s' conda environment was created without a usable interpreter.\n"
            % CONDA_ENVIRONMENT
        )
        return False
    installed = subprocess.run([python, "-m", "pip", "install"] + list(MENU_PACKAGES), check=False)
    if installed.returncode != 0:
        # A failed UI install does not invalidate the standard-library
        # builder. Menu entry reports the missing dependency with a remedy.
        sys.stderr.write("Menu packages could not be installed; CLI builds remain available.\n")
    return True


def resolve_conda_interpreter(roots: list[str]) -> str | None:
    """Return the Conda environment's interpreter, or None after explaining why not."""
    required = "%d.%d" % REQUIRED_VERSION
    for root in roots:
        python = environment_python(root)
        if not os.access(python, os.X_OK):
            continue
        version = interpreter_version(python)
        if version is None:
            sys.stderr.write("Could not determine the Python version of %s.\n" % python)
            return None
        if version[:2] < REQUIRED_VERSION:
            sys.stderr.write(
                "The '%s' conda environment has Python %d.%d; this project needs %s or newer.\n"
                "Remove it so this script can recreate it:\n  %s\n"
                % (
                    CONDA_ENVIRONMENT,
                    version[0],
                    version[1],
                    required,
                    shlex.join(
                        [
                            os.path.join(root, "bin", "conda"),
                            "env",
                            "remove",
                            "-y",
                            "-p",
                            os.path.dirname(os.path.dirname(python)),
                        ]
                    ),
                )
            )
            return None
        return python
    root = roots[0]
    question = "Create conda environment '%s' (python=%s) and install %s? [y/N]: " % (
        CONDA_ENVIRONMENT,
        CONDA_PYTHON_VERSION,
        ", ".join(MENU_PACKAGES),
    )
    if not ask_consent(question):
        sys.stderr.write(
            "Conda is available, so this project runs in the '%s' conda environment.\n"
            "Create it by answering yes interactively, or run:\n  %s\n"
            % (CONDA_ENVIRONMENT, shlex.join(conda_create_command(root)))
        )
        return None
    if not create_conda_environment(root):
        return None
    return environment_python(root)


def resolve_system_interpreter() -> str | None:
    """Return the newest stable system interpreter new enough to run the build."""
    candidates: list[str] = []
    for directory in path_directories() + ["/usr/bin"]:
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            continue
        candidates.extend(
            os.path.join(directory, name) for name in names if SYSTEM_PYTHON_NAME.match(name)
        )
    candidates.append(sys.executable)
    best: tuple[tuple[int, int], str] | None = None
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        real = os.path.realpath(candidate)
        if real in seen or not os.access(candidate, os.X_OK):
            continue
        seen.add(real)
        version = interpreter_version(candidate)
        if version is None or not version[2] or version[:2] < REQUIRED_VERSION:
            continue
        if best is None or version[:2] > best[0]:
            best = (version[:2], candidate)
    return None if best is None else best[1]


def report_missing_interpreter() -> None:
    required = "%d.%d" % REQUIRED_VERSION
    sys.stderr.write(
        "This project needs Python %s or newer, and no conda installation or compatible\n"
        "system interpreter was found (this launcher is running on Python %d.%d).\n"
        "Install Miniconda at ~/miniconda3 so this script can create the '%s'\n"
        "conda environment, or install Python %s or newer.\n"
        "On Ubuntu 22.04 and Debian 12, 'python3' is older than %s.\n"
        % (
            required,
            sys.version_info[0],
            sys.version_info[1],
            CONDA_ENVIRONMENT,
            required,
            required,
        )
    )


def reexec(interpreter: str, argv: list[str]) -> None:
    os.environ[RESOLVED_GUARD] = "1"
    # Interpreter options such as -X or -W are not forwarded; the build needs none.
    os.execv(interpreter, [interpreter, os.path.realpath(__file__)] + argv)


def resolve_interpreter() -> str | None:
    roots = conda_roots()
    if roots:
        return resolve_conda_interpreter(roots)
    interpreter = resolve_system_interpreter()
    if interpreter is None:
        report_missing_interpreter()
    return interpreter


def main(argv: list[str]) -> int:
    if REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, REPOSITORY_ROOT)

    from ffmpeg_build.usage import metadata_response

    answer = metadata_response(argv or ["--help"])
    if answer is not None:
        sys.stdout.write(answer)
        return 0

    if not os.environ.get(RESOLVED_GUARD):
        interpreter = resolve_interpreter()
        if interpreter is None:
            return 1
        if os.path.realpath(interpreter) != os.path.realpath(sys.executable):
            reexec(interpreter, argv)
    # The guard only spans the re-exec; build subprocesses must not inherit it.
    os.environ.pop(RESOLVED_GUARD, None)

    if sys.version_info[:2] < REQUIRED_VERSION:
        sys.stderr.write(
            "This project needs Python %d.%d or newer; this interpreter is Python %d.%d.\n"
            % (REQUIRED_VERSION + sys.version_info[:2])
        )
        return 1

    from ffmpeg_build.main import main as run_build

    return run_build(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
