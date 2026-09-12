"""Build settings and package selection: reading and writing configuration.

The accepted format is a deliberately small TOML subset, and the parser here is
line-based rather than `tomllib`-based for two reasons. It has to reject
everything outside that subset — a nested table, arbitrary strings, an array —
rather than accept it and ignore it, and every diagnostic names the exact line
that caused it, which a document parser cannot report.

`tomllib` still has a job: the linter parses the generated template with it, so
the subset this writes stays real TOML.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import registry
from .runtime.errors import UsageError
from .runtime.logging import Logger

CLEANUP_COMMAND = "build-ffmpeg.py --cleanup"

_TABLE = re.compile(r"^\[([A-Za-z0-9._-]+)\]$")
_ASSIGNMENT = re.compile(r"^([A-Za-z0-9_-]+)[ \t]*=[ \t]*(.*)$")
_COMPILER = re.compile(r"""^(?:"(gcc|clang)"|'(gcc|clang)')$""")
_SUPPORTED_TABLES = ("build", "packages")
COMPILERS = ("gcc", "clang")


class Selection:
    """Which packages are on, and why.

    Without a configuration file every package is enabled. With one, the file
    is an allowlist: an omitted key is disabled. Those are opposite defaults, so
    whether a file was supplied is part of the state rather than something
    callers re-derive.
    """

    def __init__(
        self,
        explicit: dict[str, bool] | None = None,
        config_file: Path | None = None,
    ) -> None:
        self.explicit: dict[str, bool] = dict(explicit or {})
        self.config_file = config_file

    @property
    def has_config(self) -> bool:
        return self.config_file is not None

    def enabled(self, key: str) -> bool:
        canonical = registry.canonical_key(key)
        if canonical not in registry.PACKAGES:
            raise UsageError(f"Unsupported package '{key}'.")
        if canonical in self.explicit:
            return self.explicit[canonical]
        return not self.has_config

    def explicitly_enabled(self, key: str) -> bool:
        """True only when the user asked for this package by name.

        That distinction is what turns an unavailable host package from a
        warning into a failure: the user named it, so silently dropping it
        would produce a build they did not ask for.
        """
        return self.explicit.get(registry.canonical_key(key), False)

    def states(self) -> dict[str, bool]:
        return {key: self.enabled(key) for key in registry.PACKAGE_NAMES}

    def set(self, key: str, value: bool) -> None:
        self.explicit[registry.canonical_key(key)] = value


class BuildSettings:
    """Persistent `[build]` options; omitted keys keep their legacy defaults."""

    def __init__(
        self, *, compiler: str = "gcc", latest: bool = False, enable_gpl_and_non_free: bool = False
    ) -> None:
        self.compiler = compiler
        self.latest = latest
        self.enable_gpl_and_non_free = enable_gpl_and_non_free

    def validate(self) -> None:
        if self.compiler not in COMPILERS:
            raise UsageError("Compiler must be 'gcc' or 'clang'.")


class LoadedConfig:
    def __init__(self, settings: BuildSettings, selection: Selection) -> None:
        self.settings = settings
        self.selection = selection


def load_config(config_file: Path, logger: Logger) -> LoadedConfig:
    """Parse a selection file, rejecting anything outside the accepted subset."""
    if not config_file.is_file():
        raise UsageError(f"Config file not found: '{config_file}'.")
    try:
        text = config_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise UsageError(f"Config file is not readable: '{config_file}'. {error}") from error

    settings = BuildSettings()
    explicit: dict[str, bool] = {}
    seen_tables: set[str] = set()
    seen_entries: set[str] = set()
    current_table = ""

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        location = f"'{config_file}:{line_number}'"

        table_match = _TABLE.match(line)
        if table_match:
            current_table = table_match.group(1)
            if current_table not in _SUPPORTED_TABLES:
                raise UsageError(f"Unsupported TOML table '{current_table}' at {location}.")
            if current_table in seen_tables:
                raise UsageError(f"Duplicate TOML table '{current_table}' at {location}.")
            seen_tables.add(current_table)
            continue

        assignment = _ASSIGNMENT.match(line)
        if assignment is None:
            raise UsageError(f"Unsupported config syntax at {location}: '{raw_line}'.")
        key, value_text = assignment.group(1), assignment.group(2)
        if current_table == "build" and key == "compiler":
            entry_id = "build.compiler"
            if entry_id in seen_entries:
                raise UsageError(f"Duplicate config key '{entry_id}' at {location}.")
            seen_entries.add(entry_id)
            compiler_match = _COMPILER.fullmatch(value_text)
            if compiler_match is None:
                raise UsageError(
                    f"Invalid compiler at {location}; expected a quoted 'gcc' or 'clang'."
                )
            settings.compiler = compiler_match.group(1) or compiler_match.group(2)
            continue
        if value_text not in ("true", "false"):
            raise UsageError(f"Unsupported config syntax at {location}: '{raw_line}'.")
        value = value_text == "true"

        if current_table == "build":
            entry_id = f"build.{key}"
            if entry_id in seen_entries:
                raise UsageError(f"Duplicate config key '{entry_id}' at {location}.")
            seen_entries.add(entry_id)
            if key == "latest":
                settings.latest = value
            elif key == "enable_gpl_and_non_free":
                settings.enable_gpl_and_non_free = value
            else:
                raise UsageError(f"Unsupported '[build]' key '{key}' at {location}.")
        elif current_table == "packages":
            canonical = registry.canonical_key(key)
            if canonical not in registry.PACKAGES:
                raise UsageError(f"Unsupported '[packages]' key '{key}' at {location}.")
            entry_id = f"packages.{canonical}"
            if entry_id in seen_entries:
                raise UsageError(f"Duplicate config key '{entry_id}' at {location}.")
            seen_entries.add(entry_id)
            if canonical != key:
                logger.warn(
                    f"Config key 'packages.{key}' is deprecated; use 'packages.{canonical}'."
                )
            explicit[canonical] = value
        else:
            table_name = current_table or "<root>"
            raise UsageError(f"Unsupported TOML table '{table_name}' at {location}.")

    logger.info(f"Loaded package selection config: '{config_file}'")
    logger.info(
        "If you are changing package selections on an existing workspace, run "
        f"'{CLEANUP_COMMAND}' first to avoid reusing old build artifacts."
    )
    return LoadedConfig(settings, Selection(explicit, config_file))


_TEMPLATE_PREAMBLE = """\
# Copy this template to custom.toml, edit it, and then run:
# python3 build-ffmpeg.py --build --config ./custom.toml
#
# The interactive menu writes this file for you:
# python3 build-ffmpeg.py --menu
#
# This project accepts a deliberately small TOML subset:
#   [build]
#   [packages]
#   key = true|false
#   compiler = "gcc"|"clang" (only in [build])
#
# Package entries are an explicit allowlist: an omitted key is disabled. A true
# value either builds the component from source or requests its supported system
# development package, depending on the integration. Some source-built
# dependencies can fall back to compatible system libraries when disabled.
#
# The groups below are for readability, with package keys alphabetized inside
# each group. They do not control build order; the stages resolve dependencies
# and build order independently of TOML ordering.
# GPL/non-free authorization does not turn disabled packages on. Conversely,
# packages that require that authorization remain inactive until
# enable_gpl_and_non_free is true or --enable-gpl-and-non-free is passed.
#
# The build context records these choices. After changing this file for an
# existing workspace, clean that same build root before rebuilding:
# python3 build-ffmpeg.py --cleanup

[build]
# C/C++ compiler family. CLI --compiler (or --gcc/--clang) overrides this value.
# Omitted compiler keys default to gcc for compatibility with older configs.
compiler = "{compiler}"

# Recheck upstream releases and rebuild components whose recorded versions differ.
latest = {latest}

# Authorize GPL and non-free FFmpeg components; review licensing before enabling.
enable_gpl_and_non_free = {gpl}

[packages]
"""


def render_config(settings: BuildSettings, states: dict[str, bool]) -> str:
    """Emit a configuration file from the registry.

    One generator produces both `example.toml` and whatever the menu saves, so
    the 127-key parity the linter checks is generated rather than
    hand-maintained, and the two files cannot drift in shape.
    """
    settings.validate()
    parts = [
        _TEMPLATE_PREAMBLE.format(
            compiler=settings.compiler,
            latest="true" if settings.latest else "false",
            gpl="true" if settings.enable_gpl_and_non_free else "false",
        )
    ]
    for group in registry.GROUPS:
        parts.append(f"\n# {group.name}\n")
        for package in sorted(group.packages, key=lambda item: item.key):
            value = "true" if states.get(package.key, package.default_enabled) else "false"
            parts.append(f"{package.key} = {value}  # {package.summary}\n")
    return "".join(parts)


def default_states() -> dict[str, bool]:
    return {package.key: package.default_enabled for package in registry.PACKAGES.values()}
