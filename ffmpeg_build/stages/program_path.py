"""Make this build's FFmpeg programs the ones the user's shell runs (`--set-path`).

Another copy earlier on PATH, typically a Conda environment's `ffmpeg`
package, hides the programs in /usr/local/bin. Only the user's shell startup
file controls that order, and update-alternatives cannot change it: it manages
links such as /usr/bin/ffmpeg, which the shell never reaches.

The fix promotes exactly the three programs, never all of /usr/local/bin: a
private directory holds links to them, an app-owned script moves that directory
to the front of PATH, and the startup file gets one appended block that
sources the script. The startup file is only ever appended to, so its inode,
owner, symlink target and every existing byte stay as they were. Nothing here
uses sudo or fails the build: every problem is reported with what to do.
"""

from __future__ import annotations

import os
import shlex
import stat
from pathlib import Path

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.state import publish_atomically
from .ffmpeg_build import INSTALL_PREFIX, INSTALLED_PROGRAMS

APP_NAME = "ffmpeg-build-script"
BLOCK_START = "# >>> ffmpeg-build-script PATH >>>"
BLOCK_END = "# <<< ffmpeg-build-script PATH <<<"
_SETUP_ERRORS = (OSError, UnicodeError, ValueError, BuildError)


def resolve_program(name: str, path_value: str, invocation_dir: Path) -> Path | None:
    """What the shell runs for `name`: the first executable file along PATH.

    An empty entry means the current directory and a relative entry is taken
    from it, as the shell does; both are read from the directory the build was
    started in.
    """
    for entry in path_value.split(":"):
        directory = Path(entry) if entry.startswith("/") else invocation_dir / entry
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def hidden_programs(
    path_value: str, invocation_dir: Path, install_bin: Path
) -> list[tuple[str, Path | None]]:
    """Installed programs PATH does not resolve to `install_bin`, with what it finds instead."""
    hidden: list[tuple[str, Path | None]] = []
    for name in INSTALLED_PROGRAMS:
        installed = install_bin / name
        if not (installed.is_file() and os.access(installed, os.X_OK)):
            continue
        found = resolve_program(name, path_value, invocation_dir)
        if found is None or found.resolve() != installed.resolve():
            hidden.append((name, found))
    return hidden


def app_directory(environ: dict[str, str] | os._Environ[str], home: Path) -> Path:
    data_home = environ.get("XDG_DATA_HOME", "")
    # The XDG specification says a relative value is invalid and is ignored.
    base = Path(data_home) if data_home.startswith("/") else home / ".local/share"
    return base / APP_NAME


def startup_file(environ: dict[str, str] | os._Environ[str], home: Path) -> Path | None:
    shell = os.path.basename(environ.get("SHELL", ""))
    if shell == "bash":
        return home / ".bashrc"
    if shell == "zsh":
        zdotdir = environ.get("ZDOTDIR", "")
        return (Path(zdotdir) if zdotdir.startswith("/") else home) / ".zshrc"
    return None


def render_env_script(link_dir: Path) -> str:
    """POSIX sh that moves `link_dir` to the front of PATH, once.

    Component by component rather than with `${PATH//...}`, whose pattern would
    treat the directory's slashes as separators. Moving instead of skipping when
    present keeps it first in a nested shell whose own Conda activation
    re-prepended its directory. Empty entries elsewhere in PATH are kept.
    """
    quoted = shlex.quote(str(link_dir))
    return f"""# Managed by build-ffmpeg.py --set-path; rewritten on each run.
_ffbs_dir={quoted}
if [ -d "$_ffbs_dir" ]; then
    if [ -z "${{PATH-}}" ]; then
        PATH=$_ffbs_dir
    else
        _ffbs_rest="$PATH:"
        _ffbs_path=$_ffbs_dir
        while [ -n "$_ffbs_rest" ]; do
            _ffbs_entry=${{_ffbs_rest%%:*}}
            _ffbs_rest=${{_ffbs_rest#*:}}
            if [ "$_ffbs_entry" != "$_ffbs_dir" ]; then
                _ffbs_path="$_ffbs_path:$_ffbs_entry"
            fi
        done
        PATH=$_ffbs_path
    fi
    export PATH
fi
unset _ffbs_dir _ffbs_rest _ffbs_path _ffbs_entry
"""


def render_block(env_script: Path) -> str:
    quoted = shlex.quote(str(env_script))
    return (
        f"{BLOCK_START}\n"
        "# Added by build-ffmpeg.py --set-path: runs this build's ffmpeg, ffprobe and\n"
        "# ffplay ahead of other copies on PATH. Delete this block to undo.\n"
        f"if [ -f {quoted} ]; then\n"
        f"    . {quoted}\n"
        "fi\n"
        f"{BLOCK_END}\n"
    )


def existing_block(text: str) -> str | None:
    """The one complete managed block, '' when there is none, None when ambiguous."""
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == BLOCK_START]
    ends = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == BLOCK_END]
    if not starts and not ends:
        return ""
    if len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        return "".join(lines[starts[0] : ends[0] + 1])
    return None


def _check_private_directory(directory: Path) -> None:
    """Refuse a directory someone else could swap programs into."""
    status = directory.lstat()
    if not stat.S_ISDIR(status.st_mode):
        raise BuildError(f"'{directory}' exists and is not a directory.")
    if status.st_uid != os.geteuid():
        raise BuildError(f"'{directory}' is owned by another user.")
    if status.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise BuildError(f"'{directory}' is writable by other users.")


def update_links(link_dir: Path, install_bin: Path) -> list[str]:
    """Point `link_dir`'s entries at the installed programs; return foreign entries.

    Only symlinks into `install_bin` are created or removed. Anything else in
    the directory would be promoted along with them, so it is reported.
    """
    # The data home itself may be missing on a fresh account.
    link_dir.parent.parent.mkdir(parents=True, exist_ok=True)
    for directory in (link_dir.parent, link_dir):
        directory.mkdir(mode=0o755, exist_ok=True)
        _check_private_directory(directory)
    foreign: list[str] = []
    for name in INSTALLED_PROGRAMS:
        link = link_dir / name
        target = install_bin / name
        ours = link.is_symlink() and Path(os.readlink(link)) == target
        if os.path.lexists(link) and not ours:
            foreign.append(name)
            continue
        if target.is_file() and os.access(target, os.X_OK):
            if not ours:
                # The directory is private to this user, and the host-mutation
                # lock serializes builds, so a per-process name cannot collide.
                temporary = link_dir / f".{name}.{os.getpid()}"
                if os.path.lexists(temporary):
                    temporary.unlink()
                os.symlink(target, temporary)
                os.replace(temporary, link)
        elif ours:
            link.unlink()
    foreign.extend(
        entry.name
        for entry in link_dir.iterdir()
        if entry.name not in INSTALLED_PROGRAMS and not entry.name.startswith(".")
    )
    return sorted(set(foreign))


def append_block(rc_file: Path, block: str) -> str:
    """Add `block` to `rc_file` once. Returns 'added', 'present' or why it was not edited."""
    if rc_file.exists():
        resolved = rc_file.resolve()
        status = resolved.stat()
        if not stat.S_ISREG(status.st_mode):
            return f"'{resolved}' is not a regular file"
        if status.st_uid != os.geteuid():
            return f"'{resolved}' is owned by another user"
        data = resolved.read_bytes()
        current = existing_block(data.decode("utf-8", errors="surrogateescape"))
        if current is None:
            return f"'{resolved}' has an incomplete or repeated '{BLOCK_START}' block"
        if current:
            if current.replace("\r\n", "\n") == block:
                return "present"
            return f"'{resolved}' already has a different '{BLOCK_START}' block"
        separator = b"" if not data else (b"\n" if data.endswith(b"\n") else b"\n\n")
        with open(resolved, "ab") as stream:
            stream.write(separator + block.encode("utf-8"))
        return "added"
    descriptor = os.open(rc_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(block)
    return "added"


def _bash_login_skips_bashrc(home: Path) -> Path | None:
    """The login file bash reads instead of .bashrc, when it never mentions .bashrc."""
    for name in (".bash_profile", ".bash_login", ".profile"):
        candidate = home / name
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None
            return None if ".bashrc" in text else candidate
    return None


def apply_program_path(context: BuildContext, invocation_dir: Path) -> None:
    """Report, and with `--set-path` fix, other copies that hide the installed programs."""
    logger = context.logger
    install_bin = INSTALL_PREFIX / "bin"
    hidden = hidden_programs(os.environ.get("PATH", ""), invocation_dir, install_bin)
    if not context.set_path:
        for name, found in hidden:
            winner = f"'{found}'" if found is not None else "nothing"
            logger.warn(f"'{name}' on your PATH runs {winner}, not '{install_bin / name}'.")
        if hidden:
            logger.hint(
                "Run the build again with --set-path (-s) to put this build first, "
                "or remove the other copy."
            )
        return
    try:
        _set_program_path(context, hidden, install_bin)
    except _SETUP_ERRORS as error:
        logger.warn(f"FFmpeg is installed, but setting up your PATH failed: {error}")


def _set_program_path(
    context: BuildContext, hidden: list[tuple[str, Path | None]], install_bin: Path
) -> None:
    logger = context.logger
    home = Path(os.path.expanduser("~"))
    app_dir = app_directory(os.environ, home)
    link_dir = app_dir / "bin"
    env_script = app_dir / "env.sh"
    rc_file = startup_file(os.environ, home)
    block = render_block(env_script)
    managed = False
    if rc_file is not None and rc_file.is_file():
        text = rc_file.read_bytes().decode("utf-8", errors="surrogateescape")
        managed = bool(existing_block(text))
    if not hidden and not managed:
        logger.info(
            f"ffmpeg, ffprobe and ffplay already run from '{install_bin}'; "
            "your shell startup file was not changed."
        )
        return
    if any(character in str(app_dir) for character in ":\n"):
        raise BuildError(f"'{app_dir}' cannot be placed on PATH because it contains ':'.")

    foreign = update_links(link_dir, install_bin)
    publish_atomically(env_script, render_env_script(link_dir), mode=0o644)
    for name, found in hidden:
        before = f"'{found}'" if found is not None else "nothing"
        logger.info(
            f"'{name}' ran {before}; new shells run '{link_dir / name}' -> '{install_bin / name}'."
        )
    if foreign:
        logger.warn(
            f"'{link_dir}' also holds {', '.join(foreign)}, which this script did not create and "
            "which would be promoted too; remove them and run the build again. Your shell "
            "startup file was not changed."
        )
        return

    if rc_file is None:
        shell = os.path.basename(os.environ.get("SHELL", "")) or "your shell"
        if shell == "fish":
            line = f"fish_add_path --move --prepend {shlex.quote(str(link_dir))}"
        else:
            line = f"put {shlex.quote(str(link_dir))} first on PATH"
        logger.warn(
            f"{shell} is not bash or zsh, so no startup file was changed. To finish, {line} "
            "in its startup file."
        )
        return

    outcome = append_block(rc_file, block)
    if outcome not in ("added", "present"):
        logger.warn(f"{outcome}, so it was not changed. Add these lines at its end:\n{block}")
        return
    if outcome == "added":
        logger.info(f"Added the PATH block to the end of '{rc_file}'.")
    else:
        logger.info(f"'{rc_file}' already has the PATH block; the links were refreshed.")
    if hidden:
        # The shell that started the build keeps its own PATH and command cache.
        context.closing_actions.append(
            (
                "This terminal still runs the old ffmpeg. Run this now; new terminals "
                "already use this build:",
                f"source {shlex.quote(str(rc_file))} && hash -r",
            )
        )
    logger.hint(
        f"To undo: delete the '{BLOCK_START}' block from '{rc_file}', then remove '{app_dir}'. "
        "These links stay first even after 'conda activate'; run an environment's own copy "
        "by its full path."
    )
    if rc_file.name == ".bashrc":
        login_file = _bash_login_skips_bashrc(home)
        if login_file is not None:
            logger.warn(
                f"Bash login shells, such as SSH sessions, read '{login_file}', which never "
                f"loads '{rc_file}'; add '. ~/.bashrc' to it for those shells too."
            )
