"""Wrappers for the build systems the dependencies use.

Every configure in this project disables CMake's package registries: they let a
host-installed config package satisfy a `find_package()` that must resolve
inside the workspace.
"""

from __future__ import annotations

import re
from pathlib import Path

CMAKE_NO_PACKAGE_REGISTRY_OPTIONS = (
    "-DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON",
    "-DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF",
    "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF",
    "-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF",
)

_MESON_OPTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def meson_project_option_exists(source: Path, option_name: str) -> bool:
    """True when this release's meson options actually declare the option.

    Upstream renames and removes project options between releases, and passing
    an unknown one is a hard configure error.
    """
    if not _MESON_OPTION_NAME.match(option_name):
        return False
    for candidate in ("meson.options", "meson_options.txt"):
        options_file = source / candidate
        if options_file.is_file():
            pattern = re.compile(rf"^[ \t]*option\([\"']{re.escape(option_name)}[\"']", re.M)
            try:
                return bool(
                    pattern.search(options_file.read_text(encoding="utf-8", errors="replace"))
                )
            except OSError:
                return False
    return False


def expand_options(template: str, values: tuple[str, ...]) -> list[str]:
    """Expand what Bash wrote as a brace expansion.

    `-D{a,b,c}=disabled` is a shell feature, not a build-system one. Writing the
    expansion out here keeps the option list a real list rather than a string
    that only a shell could interpret.
    """
    return [template.format(value=value) for value in values]
