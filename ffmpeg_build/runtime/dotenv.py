"""The checkout's `.env` file: what it may set, how it is read, and its template.

`.env` holds the same settings a user could export in the shell, so they need
not be typed before every run. Only the names a script declares are accepted;
anything else is reported and ignored, so a typo is visible and the file can
never inject variables such as PATH. The template, `.env.example`, is rendered
from the same declarations and checked by the linter, so every setting the
script reads is documented there.
"""

from __future__ import annotations

import os
import re
import textwrap
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .errors import UsageError

TEMPLATE_NAME = ".env.example"
_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")
_WIDTH = 79


@dataclass(frozen=True)
class Setting:
    section: str
    name: str
    value: str
    default: str
    help: str


def load_dotenv(
    path: Path,
    settings: Sequence[Setting],
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """Copy the declared assignments of `path` into `environ`; return warnings.

    A variable already set in `environ` wins, so the shell can override the
    file for one run. An empty value sets nothing, so the template's "an empty
    value means the default" holds for settings that reject an empty string.
    A missing file sets nothing. An unreadable one raises UsageError: silently
    falling back to defaults would, for example, build in another BUILD_ROOT
    than the one the file names.
    """
    target = os.environ if environ is None else environ
    try:
        # utf-8-sig: an editor's byte-order mark must not glue itself to the
        # first name and hide that setting.
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as error:
        raise UsageError(f"Unable to read the settings file '{path}': {error}") from error
    declared = {setting.name for setting in settings}
    values: dict[str, str] = {}
    warnings: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, assigned = line.partition("=")
        name = name.strip()
        where = f"'{path}' line {number}"
        if not separator or _NAME.fullmatch(name) is None:
            warnings.append(f"{where}: expected NAME=value; ignored.")
            continue
        if name not in declared:
            warnings.append(
                f"{where}: '{name}' is not a setting of this script (see {TEMPLATE_NAME}); ignored."
            )
            continue
        values[name] = _value(assigned)
    for name, value in values.items():
        if value and name not in target:
            target[name] = value
    return warnings


def _value(assigned: str) -> str:
    text = assigned.strip()
    if len(text) >= 2 and text[0] in "'\"" and text[0] in text[1:]:
        return text[1 : text.index(text[0], 1)]
    return text.split(" #", 1)[0].strip()


def render_dotenv_example(script: str, settings: Sequence[Setting]) -> str:
    """The text of `.env.example`: every declared setting, commented out."""
    lines = [
        f"# Settings for {script}, read from a file named .env beside the script.",
        "#",
        "# To use it:",
        f"#   cp {TEMPLATE_NAME} .env",
        '#   then, in .env, delete the "# " in front of each NAME=value line you want',
        "#   to change and edit its value.",
        "#",
        "# Every value shown below is the default (an empty value means the default),",
        "# so a setting uncommented unchanged changes nothing.",
        "#",
        "# Rules:",
        "#   - One NAME=value per line; do not write `export`.",
        '#   - Put quotes around a value that contains spaces: NAME="a b".',
        "#   - ~ and $VARIABLES are not expanded; write full paths.",
        "#   - A variable set in your shell wins over this file for that run:",
        f"#       BUILD_ROOT=/tmp/scratch python3 {script} --build",
        "#   - A name that is not listed here is reported and ignored.",
        "#   - Git ignores .env, so your settings stay on this computer.",
    ]
    section = ""
    for setting in settings:
        if setting.section != section:
            section = setting.section
            lines += ["", "", f"# ===== {section} ".ljust(_WIDTH, "=").rstrip()]
        lines.append("")
        lines += textwrap.wrap(setting.help, _WIDTH, initial_indent="# ", subsequent_indent="# ")
        lines.append(f"# Default: {setting.default}")
        lines.append(f"# {setting.name}={setting.value}")
    return "\n".join(lines) + "\n"
