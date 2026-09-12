"""The interactive package menu.

Editing 127 boolean keys by hand gives no feedback until the build runs, and
the cross-package requirements are invisible until they fail. This screen makes
the selection direct, shows what the licence mode does to each package, and
validates the whole selection as it is edited.

It writes the same file format the build reads, through the same generator that
produces the tracked template, so what the menu saves and what the project
ships cannot drift apart.
"""

from __future__ import annotations

import curses
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _curses import window as _CursesWindow

from .. import registry
from ..config import BuildSettings, default_states, render_config
from ..registry import Gate, Package
from ..runtime.errors import BuildError, UsageError
from ..runtime.state import publish_atomically
from .model import LaunchSettings, MenuModel

_PRESETS = (
    ("t", "template", "what example.toml ships"),
    ("a", "all", "every package"),
    ("m", "minimal", "build tools and FFmpeg only"),
    ("n", "none", "nothing"),
)

_KEY_HELP = (
    "space toggle  ←/→ fold  a/d group on/off  g GPL  l latest  "
    "/ search  p preset  f fix  F fix all  e launch settings  s save  b build  q quit"
)


@dataclass
class MenuResult:
    """What the user asked for on the way out."""

    saved_path: Path | None = None
    start_build: bool = False
    settings: BuildSettings = field(default_factory=BuildSettings)
    launch: LaunchSettings = field(default_factory=LaunchSettings)


@dataclass
class Row:
    """One visible line: either a group heading or a package."""

    group: str
    package: Package | None = None

    @property
    def is_group(self) -> bool:
        return self.package is None


class MenuApp:
    def __init__(
        self, model: MenuModel, default_path: Path, launch: LaunchSettings | None = None
    ) -> None:
        self.model = model
        self.default_path = default_path
        self.result = MenuResult(settings=model.settings, launch=launch or LaunchSettings())
        self.cursor = 0
        self.top = 0
        self.message = ""
        self.dirty = False

    # -- layout ----------------------------------------------------------

    def rows(self) -> list[Row]:
        rows: list[Row] = []
        for group in registry.GROUPS:
            visible = [package for package in group.packages if self.model.matches_search(package)]
            if not visible:
                continue
            rows.append(Row(group.name))
            if group.name not in self.model.collapsed:
                rows.extend(Row(group.name, package) for package in visible)
        return rows

    def current(self, rows: list[Row]) -> Row | None:
        if not rows:
            return None
        self.cursor = max(0, min(self.cursor, len(rows) - 1))
        return rows[self.cursor]

    # -- rendering -------------------------------------------------------

    def _status_glyph(self, package: Package) -> str:
        return "[x]" if self.model.enabled(package.key) else "[ ]"

    def _gate_label(self, package: Package) -> str:
        if package.gate is Gate.REQUIRES_GPL:
            return "GPL"
        if package.gate is Gate.FLAG_REQUIRES_GPL:
            return "gpl-flag"
        if package.gate is Gate.SUPPRESSED_BY_GPL:
            return "non-GPL"
        return ""

    def draw(self, screen: "_CursesWindow") -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        if height < 10 or width < 40:
            screen.addnstr(0, 0, "Resize terminal to at least 40 x 10; q quits.", max(0, width - 1))
            screen.refresh()
            return
        rows = self.rows()
        issues = self.model.issues()
        selected = sum(1 for key in registry.PACKAGE_NAMES if self.model.enabled(key))

        header = (
            f" FFmpeg package selection — {selected}/{len(registry.PACKAGE_NAMES)} enabled"
            f"   GPL/non-free: {'on' if self.model.gpl else 'off'}"
            f"   latest: {'on' if self.model.settings.latest else 'off'}"
        )
        if self.model.search:
            header += f"   filter: {self.model.search}"
        screen.addnstr(0, 0, header.ljust(width - 1), width - 1, curses.A_REVERSE)

        body_height = max(1, height - 6)
        if self.cursor < self.top:
            self.top = self.cursor
        if self.cursor >= self.top + body_height:
            self.top = self.cursor - body_height + 1
        self.top = max(0, min(self.top, max(0, len(rows) - body_height)))

        blocked = {issue.package for issue in issues}
        for offset in range(body_height):
            index = self.top + offset
            if index >= len(rows):
                break
            row = rows[index]
            line = 1 + offset
            attribute = curses.A_REVERSE if index == self.cursor else curses.A_NORMAL
            if row.is_group:
                group = self.model.group(row.group)
                marker = "+" if row.group in self.model.collapsed else "-"
                text = (
                    f" {marker} {row.group}  "
                    f"({self.model.enabled_count(group)}/{len(group.packages)})"
                )
                screen.addnstr(line, 0, text.ljust(width - 1), width - 1, attribute | curses.A_BOLD)
                continue
            package = row.package
            assert package is not None
            gate = self._gate_label(package)
            flag = "!" if package.key in blocked else " "
            text = f"   {self._status_glyph(package)} {flag} {package.key:<22} {gate:<8} {package.summary}"
            screen.addnstr(line, 0, text.ljust(width - 1), width - 1, attribute)

        detail_line = height - 5
        current_row = self.current(rows)
        detail = ""
        if current_row is not None and current_row.package is not None:
            package = current_row.package
            note = self.model.status_note(package)
            detail = f" {package.key}: {package.summary}"
            if note:
                detail += f"  [{note}]"
            package_issues = self.model.issues_for(package.key)
            if package_issues:
                detail += "  " + "; ".join(issue.summary() for issue in package_issues)
        screen.addnstr(detail_line, 0, detail.ljust(width - 1), width - 1, curses.A_DIM)

        summary = f" {len(issues)} unmet requirement(s)" if issues else " selection is consistent"
        if self.dirty:
            summary += "   (unsaved changes)"
        screen.addnstr(height - 4, 0, summary.ljust(width - 1), width - 1)
        screen.addnstr(height - 3, 0, self.message.ljust(width - 1), width - 1)
        for offset, chunk in enumerate(_wrap(_KEY_HELP, width - 1)[:2]):
            screen.addnstr(
                height - 2 + offset, 0, chunk.ljust(width - 1), width - 1, curses.A_REVERSE
            )
        screen.refresh()

    # -- input -----------------------------------------------------------

    def prompt(self, screen: "_CursesWindow", label: str, initial: str = "") -> str | None:
        height, width = screen.getmaxyx()
        label = f"{label}[{initial}] " if initial else label
        label = label[: max(1, width - 4)]
        curses.echo()
        curses.curs_set(1)
        try:
            screen.addnstr(height - 3, 0, label.ljust(width - 1), width - 1)
            screen.move(height - 3, min(len(label), width - 2))
            screen.refresh()
            raw = screen.getstr(height - 3, len(label), 256)
        except curses.error:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)
        if raw is None:
            return None
        answer = raw.decode("utf-8", "replace").strip()
        if "\x1b" in answer:
            return None
        return answer or initial

    def edit_launch_settings(self, screen: "_CursesWindow") -> None:
        launch = self.result.launch
        fields = (
            ("c", "compiler", "Compiler (gcc/clang)"),
            ("j", "jobs", "Jobs (auto for available CPUs)"),
            ("i", "cuda_install", "CUDA install (ask/always/never)"),
            ("a", "cuda_arch_mode", "CUDA architecture mode (native/all/custom)"),
            ("t", "cuda_architectures", "Custom targets (space-separated numbers)"),
            ("r", "build_root", "Build root"),
        )
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            if height < 10 or width < 40:
                screen.addnstr(0, 0, "Resize terminal; q returns.", max(0, width - 1))
            else:
                screen.addnstr(
                    0,
                    0,
                    "Launch settings (this session only; q returns)",
                    width - 1,
                    curses.A_REVERSE,
                )
                for index, (key, name, label) in enumerate(fields, 1):
                    value = getattr(launch, name) or "auto"
                    screen.addnstr(index, 0, f"{key}  {label}: {value}", width - 1)
                screen.addnstr(height - 2, 0, self.message, width - 1)
            screen.refresh()
            pressed = screen.getch()
            if pressed in (ord("q"), 27):
                return
            if height < 10 or width < 40:
                continue
            for key, name, label in fields:
                if pressed == ord(key):
                    answer = self.prompt(screen, label + ": ", str(getattr(launch, name)))
                    if answer is not None:
                        setattr(launch, name, "" if answer == "auto" and name == "jobs" else answer)
                    try:
                        launch.validate()
                        self.message = "Launch settings updated."
                    except UsageError as error:
                        self.message = str(error)

    def save(self, screen: "_CursesWindow") -> bool:
        answer = self.prompt(screen, "Save to: ", str(self.default_path))
        if not answer:
            self.message = "Save cancelled."
            return False
        target = Path(answer).expanduser()
        if not target.is_absolute():
            target = self.default_path.parent / target
        try:
            if target.is_symlink():
                raise BuildError("Refusing to replace a symlinked configuration file.")
            publish_atomically(
                target, render_config(self.model.settings, self.model.states), mode=0o644
            )
        except (OSError, BuildError) as error:
            self.message = f"Could not write '{target}': {error}"
            return False
        self.result.saved_path = target
        self.default_path = target
        self.dirty = False
        self.message = f"Saved '{target}'."
        return True

    def choose_preset(self, screen: "_CursesWindow") -> None:
        options = "  ".join(f"{key}={name} ({note})" for key, name, note in _PRESETS)
        self.message = f"Preset: {options}"
        self.draw(screen)
        pressed = screen.getch()
        for key, name, _note in _PRESETS:
            if pressed == ord(key):
                self.model.apply_preset(name)
                self.dirty = True
                self.message = f"Applied the '{name}' preset."
                return
        self.message = "Preset cancelled."

    def handle(self, screen: "_CursesWindow", pressed: int) -> bool:
        """Act on one keystroke. Returns False to leave the menu."""
        rows = self.rows()
        row = self.current(rows)
        height = screen.getmaxyx()[0]
        page = max(1, height - 7)

        if pressed in (curses.KEY_UP, ord("k")):
            self.cursor = max(0, self.cursor - 1)
        elif pressed in (curses.KEY_DOWN, ord("j")):
            self.cursor = min(len(rows) - 1, self.cursor + 1)
        elif pressed == curses.KEY_PPAGE:
            self.cursor = max(0, self.cursor - page)
        elif pressed == curses.KEY_NPAGE:
            self.cursor = min(len(rows) - 1, self.cursor + page)
        elif pressed == curses.KEY_HOME:
            self.cursor = 0
        elif pressed == curses.KEY_END:
            self.cursor = max(0, len(rows) - 1)
        elif pressed in (ord(" "), curses.KEY_ENTER, 10, 13):
            if row is None:
                pass
            elif row.is_group:
                self._toggle_fold(row.group)
            else:
                assert row.package is not None
                self.model.toggle(row.package.key)
                self.dirty = True
        elif pressed == curses.KEY_RIGHT:
            if row is not None:
                self.model.collapsed.discard(row.group)
        elif pressed == curses.KEY_LEFT:
            if row is not None:
                self.model.collapsed.add(row.group)
                self.cursor = next(
                    (
                        index
                        for index, candidate in enumerate(self.rows())
                        if candidate.is_group and candidate.group == row.group
                    ),
                    self.cursor,
                )
        elif pressed in (ord("a"), ord("d")):
            if row is not None:
                self.model.set_group(row.group, pressed == ord("a"))
                self.dirty = True
        elif pressed == ord("g"):
            self.model.settings.enable_gpl_and_non_free = not self.model.gpl
            self.dirty = True
        elif pressed == ord("l"):
            self.model.settings.latest = not self.model.settings.latest
            self.dirty = True
        elif pressed == ord("/"):
            answer = self.prompt(screen, "Filter: ", self.model.search)
            self.model.search = answer or ""
            self.cursor = 0
        elif pressed == ord("p"):
            self.choose_preset(screen)
        elif pressed == ord("f"):
            if row is not None and row.package is not None:
                changed = self.model.auto_fix(row.package.key)
                self.dirty = self.dirty or bool(changed)
                self.message = (
                    f"Enabled {', '.join(changed)}." if changed else "Nothing to fix here."
                )
        elif pressed == ord("F"):
            changed = self.model.auto_fix_all()
            self.dirty = self.dirty or bool(changed)
            self.message = f"Enabled {len(changed)} package(s)." if changed else "Nothing to fix."
        elif pressed == ord("s"):
            self.save(screen)
        elif pressed == ord("e"):
            self.edit_launch_settings(screen)
        elif pressed == ord("b"):
            try:
                self.result.launch.validate()
            except UsageError as error:
                self.message = str(error)
                return True
            blocking = [issue for issue in self.model.issues() if issue.blocking]
            if blocking:
                self.message = "Resolve required packages before building: " + "; ".join(
                    issue.summary() for issue in blocking
                )
                return True
            if self.save(screen):
                self.result.start_build = True
                return False
        elif pressed in (ord("q"), 27):
            if self.dirty:
                answer = self.prompt(screen, "Discard unsaved changes? [y/N]: ")
                if (answer or "").lower() not in ("y", "yes"):
                    self.message = "Still editing."
                    return True
            return False
        return True

    def _toggle_fold(self, group_name: str) -> None:
        if group_name in self.model.collapsed:
            self.model.collapsed.discard(group_name)
        else:
            self.model.collapsed.add(group_name)

    def loop(self, screen: "_CursesWindow") -> MenuResult:
        curses.curs_set(0)
        screen.keypad(True)
        while True:
            self.draw(screen)
            try:
                pressed = screen.getch()
            except KeyboardInterrupt:
                return self.result
            self.message = ""
            if not self.handle(screen, pressed):
                return self.result


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def run_menu(
    states: dict[str, bool] | None,
    settings: BuildSettings,
    default_path: Path,
    launch: LaunchSettings | None = None,
) -> MenuResult:
    """Show the menu, refusing a non-interactive terminal rather than degrading.

    A silently non-interactive editor would produce an empty selection that
    looks deliberate, which is worse than saying the terminal cannot host it.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError(
            "The interactive menu needs a terminal. Edit a TOML file and pass it with "
            "'--config' instead."
        )
    model = MenuModel(states if states is not None else default_states(), settings)
    application = MenuApp(model, default_path, launch)
    try:
        return curses.wrapper(application.loop)
    except curses.error as error:
        raise RuntimeError(f"Unable to initialize the terminal menu: {error}") from error
