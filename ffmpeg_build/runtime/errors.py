"""Failure types shared by every module.

A fatal failure is raised rather than exited, so the recovery sites (a staged
install that must restore its backup, a probe whose failure is expected) can
catch it and finish their cleanup before the run ends.
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

    The failure report derives the raising location from the traceback, so a
    helper called from many recipe sites still names the recipe that invoked it.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UsageError(BuildError):
    """An invalid command line or configuration file.

    Separate from `BuildError` so the launcher can report it without the
    bug-report footer: a mistyped option is not a defect worth filing.
    """
