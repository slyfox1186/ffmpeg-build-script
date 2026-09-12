"""Configuration transactions shared by the terminal UI and its tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..config import BuildSettings, render_config
from ..runtime.errors import BuildError, UsageError
from ..runtime.state import publish_atomically
from .model import LaunchSettings, MenuModel


@dataclass
class MenuResult:
    """The saved configuration and the requested action after terminal restoration."""

    saved_path: Path | None = None
    start_build: bool = False
    settings: BuildSettings = field(default_factory=BuildSettings)
    launch: LaunchSettings = field(default_factory=LaunchSettings)


Snapshot = tuple[dict[str, bool], bool, bool, str]


class MenuSession:
    """Publish each persistent edit before reporting success, with rollback and undo."""

    def __init__(
        self, model: MenuModel, default_path: Path, launch: LaunchSettings | None = None
    ) -> None:
        self.model = model
        self.default_path = default_path.absolute()
        self.result = MenuResult(settings=model.settings, launch=launch or LaunchSettings())
        self.history: list[Snapshot] = []
        self.message = "Changes save automatically."
        self.failed = False

    def snapshot(self) -> Snapshot:
        return (
            dict(self.model.states),
            self.model.gpl,
            self.model.settings.latest,
            self.model.settings.compiler,
        )

    def restore(self, snapshot: Snapshot) -> None:
        states, gpl, latest, compiler = snapshot
        self.model.states = dict(states)
        self.model.settings.enable_gpl_and_non_free = gpl
        self.model.settings.latest = latest
        self.model.settings.compiler = compiler

    def change(self, edit: Callable[[], object], message: str) -> bool:
        previous = self.snapshot()
        try:
            edit()
            self.model.settings.validate()
        except (UsageError, ValueError) as error:
            self.restore(previous)
            self.message, self.failed = str(error), True
            return False
        if previous == self.snapshot():
            self.message, self.failed = "No changes to save.", False
            return True
        if not self.save(self.default_path):
            self.restore(previous)
            self.message += " Change reverted."
            return False
        self.history.append(previous)
        self.history = self.history[-50:]
        self.message = message + " Saved."
        return True

    def undo(self) -> bool:
        if not self.history:
            self.message, self.failed = "No changes to undo.", False
            return True
        previous = self.snapshot()
        self.restore(self.history[-1])
        if not self.save(self.default_path):
            self.restore(previous)
            self.message += " Change reverted."
            return False
        self.history.pop()
        self.message = "Undid the last change. Saved."
        return True

    def save(self, path: str | Path) -> bool:
        try:
            target = Path(path).expanduser().absolute()
            if target.is_symlink():
                raise BuildError("Refusing to replace a symlinked configuration file.")
            publish_atomically(
                target, render_config(self.model.settings, self.model.states), mode=0o644
            )
        except (OSError, BuildError, ValueError, RuntimeError) as error:
            self.message, self.failed = f"Save failed: {error}", True
            return False
        self.result.saved_path = self.default_path = target
        self.message, self.failed = f"Saved '{target}'.", False
        return True

    def prepare_build(self) -> bool:
        self.result.start_build = False
        try:
            self.model.settings.validate()
            self.result.launch.validate()
        except UsageError as error:
            self.message, self.failed = str(error), True
            return False
        blocking = [issue for issue in self.model.issues() if issue.blocking]
        if blocking:
            self.message = "Resolve required packages before building: " + "; ".join(
                issue.summary() for issue in blocking
            )
            self.failed = True
            return False
        if not self.save(self.default_path):
            return False
        self.result.start_build = True
        return True
