"""Build-root markers, package markers, and the build-context record.

Nothing in this project is deleted without a path-bound marker match, and no
package is considered current without both a version marker and the workspace
artifact that marker claims. These are the files that make those two statements
true.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from . import shellquote
from .errors import BuildError
from .paths import (
    UNSAFE_BUILD_ROOTS,
    canonicalize,
    is_exclusive_regular_file,
    path_is_within,
)

BUILD_ROOT_MARKER_NAME = ".ffmpeg-build-root"
BUILD_ROOT_MARKER_HEADER = "ffmpeg-build-root:v1"
BUILD_CONTEXT_NAME = ".ffmpeg-build-context"
BUILD_CONTEXT_FORMAT = "ffmpeg-build-context:v2"
BUILD_CONTEXT_LEGACY_FORMAT = "ffmpeg-build-context:v1"

# v1 snapshotted the four flag variables before they were computed, so it
# recorded the inherited environment (normally empty) rather than what the build
# used. A v1 record therefore carries no usable flag data, which is why the
# migration ignores exactly these fields exactly once instead of reporting them
# as changed settings.
BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS = ("cflags", "cxxflags", "cppflags", "ldflags")

# Script versions whose recorded context this release can adopt. These releases
# changed discovery, diagnostics and FFmpeg integration; dependency ABI and
# build flags did not move, so the existing dependency builds stay valid and
# only FFmpeg is reconfigured.
MIGRATABLE_SCRIPT_VERSIONS = frozenset({"6.0.0", "7.0.0"})

# Cap on the differing fields listed in the mismatch message. A changed config
# can move a hundred of them, and a wall of those buries the one line the reader
# needs.
BUILD_CONTEXT_CHANGE_LIMIT = 10

_MARKER_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def publish_atomically(target: Path, content: str, *, mode: int = 0o600) -> None:
    """Write a file through a temporary in the same directory, then rename.

    An interrupted write must never leave a marker that claims more than the
    filesystem actually holds.
    """
    directory = target.parent
    handle, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            error.add_note(f"Unable to remove temporary file '{temporary}': {cleanup_error}")
        if isinstance(error, OSError):
            raise BuildError(f"Unable to publish '{target}': {error}") from error
        raise


def read_marker_version(marker_file: Path) -> str | None:
    """The version recorded in a `.done` marker, or None when unusable."""
    if not is_exclusive_regular_file(marker_file):
        return None
    try:
        lines = marker_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if len(lines) != 1:
        return None
    version = lines[0].strip()
    return version if _MARKER_VERSION.match(version) else None


def write_marker_version(marker_file: Path, version: str) -> None:
    publish_atomically(marker_file, f"{version}\n", mode=0o644)


def build_root_marker_matches(marker_file: Path, expected_root: Path) -> bool:
    """True when the marker names this exact build root.

    Binding the marker to its path is what stops a copied marker from
    authorizing deletion of an unrelated directory.
    """
    if not is_exclusive_regular_file(marker_file):
        return False
    try:
        lines = marker_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    if len(lines) != 2:
        return False
    return (
        lines[0] == BUILD_ROOT_MARKER_HEADER and lines[1] == f"root={canonicalize(expected_root)}"
    )


def legacy_build_root_marker(marker_file: Path) -> bool:
    """True for the empty marker written by releases before the path binding."""
    if not is_exclusive_regular_file(marker_file):
        return False
    try:
        return marker_file.stat().st_size == 0
    except OSError:
        return False


def write_build_root_marker(root: Path) -> None:
    resolved = canonicalize(root)
    if str(resolved) == "/" or not resolved.is_dir():
        raise BuildError(f"Refusing to write a marker for unsafe build root '{resolved}'.")
    marker_file = resolved / BUILD_ROOT_MARKER_NAME
    if marker_file.is_symlink():
        raise BuildError(f"Refusing symlink build-root marker '{marker_file}'.")
    publish_atomically(marker_file, f"{BUILD_ROOT_MARKER_HEADER}\nroot={resolved}\n")


def build_root_is_adoptable(root: Path) -> bool:
    """True for a root holding nothing but this project's empty scaffolding.

    A run interrupted before its marker was written otherwise leaves a
    populated unmarked directory that neither `--build` nor `--cleanup` will
    touch again, and a manual `rm -rf` is the only way out.
    """
    if not root.is_dir():
        return False
    try:
        entries = list(root.iterdir())
    except OSError:
        return False
    for entry in entries:
        if entry.name not in ("packages", "workspace"):
            return False
        if entry.is_symlink() or not entry.is_dir():
            return False
        try:
            if any(entry.iterdir()):
                return False
        except OSError:
            return False
    return True


def assert_safe_build_root(candidate: Path, repository_root: Path) -> None:
    """One refusal list shared by the build and cleanup paths.

    The repository is compared by containment rather than equality: a build
    root that is an *ancestor* of the repository must be refused too, or a
    later cleanup takes the repository with it.
    """
    resolved = canonicalize(candidate)
    repository = canonicalize(repository_root)
    home = os.environ.get("HOME", "")
    if not home.startswith("/"):
        raise BuildError("'HOME' must name an absolute user home directory.")

    # Named generically: with BUILD_ROOT unset this is the repository's own
    # ./build, and blaming BUILD_ROOT sent people looking for a variable they
    # never set.
    if any(character.isspace() for character in str(resolved)):
        raise BuildError(
            "The build root may not contain whitespace because several upstream "
            f"build systems cannot represent it safely: '{resolved}'."
        )
    if str(resolved) in UNSAFE_BUILD_ROOTS or resolved == canonicalize(home):
        raise BuildError(f"Refusing unsafe build root '{resolved}'.")
    if resolved == repository:
        raise BuildError(f"Refusing to use the repository root as a build root: '{resolved}'.")
    if path_is_within(repository, resolved):
        raise BuildError(f"Refusing a build root that contains this repository: '{resolved}'.")


# --------------------------------------------------------------------------
# Build context
# --------------------------------------------------------------------------


def render_build_context(fields: dict[str, str], package_states: dict[str, bool]) -> str:
    """Serialize the fingerprint exactly as every earlier release wrote it.

    The seven `%q`-encoded fields keep their Bash encoding so a workspace
    created by 7.0.0 still compares equal here.
    """
    lines = [BUILD_CONTEXT_FORMAT]
    for name in ("script_version", "compiler", "gpl_and_non_free", "rust_toolchain", "cargo_c"):
        lines.append(f"{name}={fields[name]}")
    for name in (
        "cflags",
        "cxxflags",
        "cppflags",
        "ldflags",
        "cuda_arch_mode",
        "cuda_architectures",
        "source_date_epoch",
    ):
        lines.append(f"{name}={shellquote.quote(fields.get(name, ''))}")
    # Sorted by key so the record cannot depend on the order packages happen to
    # be declared in. Reordering the registry is a readability change; it must
    # not read as a changed build and demand a clean rebuild.
    for package_name in sorted(package_states):
        lines.append(
            f"package.{package_name}={'true' if package_states[package_name] else 'false'}"
        )
    return "\n".join(lines) + "\n"


def parse_build_context(text: str) -> dict[str, str]:
    """Read a record into fields.

    The payload opens with a bare format tag rather than a `key=value` pair.
    Filing it under a synthetic key keeps a format change visible; skipping it
    would leave a version bump as a byte difference with nothing to report.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            line = f"format={line}"
        key, _, value = line.partition("=")
        fields[key] = value
    return fields


def summarize_build_context_changes(previous_text: str, current_text: str) -> list[str]:
    """Name the fields that actually differ.

    The record is well over a hundred fields, so "something changed" leaves the
    reader nothing to act on and no way to tell a stale workspace from a newly
    registered package.
    """
    previous = parse_build_context(previous_text)
    current = parse_build_context(current_text)
    changes: list[str] = []
    for key, value in current.items():
        if key not in previous:
            changes.append(
                f"{key} is new in this version of the script (now {shellquote.readable(value)})"
            )
        elif previous[key] != value:
            changes.append(
                f"{key} was {shellquote.readable(previous[key])}, is now {shellquote.readable(value)}"
            )
    for key, value in previous.items():
        if key not in current:
            changes.append(f"{key} is no longer recorded (was {shellquote.readable(value)})")
    if not changes:
        return []

    # Sorted for a stable message regardless of dictionary order, and by code
    # point so the list and the cap do not move between locales.
    changes.sort()
    omitted = len(changes) - BUILD_CONTEXT_CHANGE_LIMIT
    # Truncating a single field costs a line to say so and saves nothing.
    if omitted > 1:
        changes = changes[:BUILD_CONTEXT_CHANGE_LIMIT] + [f"and {omitted} more"]
    return changes


class ContextMismatch(Exception):
    """The recorded context cannot be reconciled with the current one."""


def migratable_added_packages(
    previous_text: str, current_text: str, script_version: str
) -> list[str]:
    """Package keys gained since the record was written.

    Raises `ContextMismatch` when the difference is anything other than
    bookkeeping: a changed setting must still force a clean rebuild.
    """
    previous = parse_build_context(previous_text)
    current = parse_build_context(current_text)
    previous_format = previous.get("format", "")
    legacy_context = previous_format == BUILD_CONTEXT_LEGACY_FORMAT
    if not legacy_context:
        if previous_format != BUILD_CONTEXT_FORMAT:
            raise ContextMismatch
        if previous.get("script_version") not in MIGRATABLE_SCRIPT_VERSIONS:
            raise ContextMismatch

    remaining = dict(previous)
    added_packages: list[str] = []
    for key, value in current.items():
        if key == "format":
            continue
        if (
            key == "script_version"
            and remaining.get(key) in MIGRATABLE_SCRIPT_VERSIONS
            and value == script_version
        ):
            remaining.pop(key, None)
            continue
        if legacy_context and key in BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS:
            remaining.pop(key, None)
            continue
        if key not in remaining:
            # Only the registry growing is additive. A brand new non-package
            # field means the payload changed shape in a way this cannot reason
            # about, so it is not migratable.
            if not key.startswith("package."):
                raise ContextMismatch
            added_packages.append(key[len("package.") :])
            continue
        if remaining[key] != value:
            raise ContextMismatch
        remaining.pop(key)

    # Anything left over was recorded before and is absent now. A shrinking
    # registry does not invalidate artifacts, but it is rare enough that a clean
    # rebuild is the honest answer rather than a guess.
    for key in remaining:
        if key == "format":
            continue
        if legacy_context and key in BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS:
            continue
        raise ContextMismatch
    return added_packages
