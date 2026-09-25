"""Failure types shared by every module.

`BuildError` replaces the Bash `fail()` helper. Raising rather than exiting is
what makes the recovery sites (a staged install that must restore its backup, a
probe whose failure is expected) expressible at all: Bash had to choose between
`fail`, which exits, and `warn` plus a return code, which callers could forget
to check.
"""

from __future__ import annotations

REPOSITORY_URL = "https://github.com/slyfox1186/ffmpeg-build-script"
ISSUE_TRACKER_URL = f"{REPOSITORY_URL}/issues"


class SignalStop(BaseException):
    """A termination signal, carrying the exit status it should produce."""

    def __init__(self, name: str, exit_code: int) -> None:
        super().__init__(name)
        self.name = name
        self.exit_code = exit_code


class BuildError(Exception):
    """A fatal, reportable build failure.

    `origin` names the frame that raised it, reproducing what Bash derived from
    `BASH_SOURCE[2]`: a helper called from thirty recipe sites otherwise reports
    the same location every time and never names the recipe that invoked it.
    """

    def __init__(self, message: str, origin: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.origin = origin


class UsageError(BuildError):
    """An invalid command line or configuration file.

    Separate from `BuildError` so the launcher can report it without the
    bug-report footer: a mistyped option is not a defect worth filing.
    """
