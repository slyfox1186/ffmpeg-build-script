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
import os
import sys
import unicodedata
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
    "Space toggle/fold  Tab category  / search  i info  ? help",
    "a/d category on/off  s save  b build  q quit",
)
_HELP = (
    "Package selection help",
    "Up/Down or j/k: move; PgUp/PgDn: page; Home/End: first/last.",
    "Tab / Shift-Tab: next / previous package category.",
    "Space or Enter: toggle one package, or expand/collapse a category.",
    "Left/Right: collapse/expand current category; [ / ]: collapse/expand all.",
    "a / d: enable/disable the ENTIRE current category, including hidden matches.",
    "/: search names, descriptions and categories; empty Enter clears; Esc cancels.",
    "p: choose template, all, minimal or none preset.",
    "g / l: toggle GPL/non-free authorization / latest-version checks.",
    "f: enable current package's requirements; F: fix all requirements.",
    "!: unmet requirement. GPL marks a licensing restriction; see package detail.",
    "i: read the full current package/category description and requirements.",
    "e: edit session launch settings (compiler, jobs, CUDA, build root).",
    "s: save TOML; b: validate, save and build; q: quit (confirm unsaved edits).",
    "Text fields: type to replace, arrows to edit, Ctrl-U to clear, Enter accept, Esc cancel.",
)


def _cursor(visible: bool) -> None:
    try:
        curses.curs_set(int(visible))
    except curses.error:
        # Some terminals cannot change cursor visibility; editing still works.
        pass


def _cell_width(text: str) -> int:
    return sum(
        0
        if unicodedata.combining(char)
        else (2 if unicodedata.east_asian_width(char) in ("W", "F") else 1)
        for char in text
    )


def _put(
    screen: "_CursesWindow", y: int, x: int, text: str, width: int, attribute: int = 0
) -> None:
    """Clip by display cells, keeping terminal controls out of UI text."""
    if width <= 0:
        return
    rendered: list[str] = []
    used = 0
    for character in text:
        if unicodedata.category(character).startswith("C"):
            character = "?"
        cells = (
            0
            if unicodedata.combining(character)
            else (2 if unicodedata.east_asian_width(character) in ("W", "F") else 1)
        )
        if used + cells > width:
            break
        rendered.append(character)
        used += cells
    try:
        screen.addstr(y, x, "".join(rendered), attribute)
    except curses.error:
        # A resize can invalidate the dimensions between layout and drawing.
        # KEY_RESIZE causes the next loop to lay out the complete screen again.
        pass


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
        self.default_path = default_path.absolute()
        self.result = MenuResult(settings=model.settings, launch=launch or LaunchSettings())
        self.cursor = 0
        self.top = 0
        self.message = ""
        self._saved_config = render_config(model.settings, model.states)
        self.category_style = 0
        self.enabled_style = 0

    @property
    def dirty(self) -> bool:
        return render_config(self.model.settings, self.model.states) != self._saved_config

    # -- layout ----------------------------------------------------------

    def rows(self) -> list[Row]:
        rows: list[Row] = []
        for group in registry.GROUPS:
            visible = [package for package in group.packages if self.model.matches_search(package)]
            if not visible:
                continue
            rows.append(Row(group.name))
            if self.model.search or group.name not in self.model.collapsed:
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
            _put(screen, 0, 0, "Resize terminal to at least 40 x 10; q quits.", max(0, width - 1))
            screen.refresh()
            return
        rows = self.rows()
        self.current(rows)
        issues = self.model.issues()
        selected = sum(1 for key in registry.PACKAGE_NAMES if self.model.enabled(key))

        header = f" FFmpeg package selection  {selected}/{len(registry.PACKAGE_NAMES)} enabled"
        if width < 50:
            header = f" FFmpeg package selection {selected}/{len(registry.PACKAGE_NAMES)}"
        _put(screen, 0, 0, header.ljust(width - 1), width - 1, curses.A_REVERSE)
        options = f" Categories by type | GPL: {'on' if self.model.gpl else 'off'} | latest: {'on' if self.model.settings.latest else 'off'}"
        if width < 60:
            options = f" Types | GPL {'on' if self.model.gpl else 'off'} | latest {'on' if self.model.settings.latest else 'off'}"
        if self.model.search:
            options = f" Filter: {self.model.search} (empty search clears)"
        _put(screen, 1, 0, options, width - 1)

        body_height = max(1, height - 7)
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
            line = 2 + offset
            attribute = curses.A_REVERSE if index == self.cursor else curses.A_NORMAL
            if row.is_group:
                group = self.model.group(row.group)
                marker = "+" if row.group in self.model.collapsed and not self.model.search else "-"
                name = row.group if width >= 70 else row.group.split(",", 1)[0]
                text = f" {marker} [{self.model.enabled_count(group):2}/{len(group.packages):2}] {name}"
                _put(
                    screen,
                    line,
                    0,
                    text.ljust(width - 1),
                    width - 1,
                    attribute | curses.A_BOLD | self.category_style,
                )
                continue
            package = row.package
            assert package is not None
            gate = self._gate_label(package)
            flag = "!" if package.key in blocked else " "
            text = f"   {self._status_glyph(package)} {flag} {package.key:<22} {gate:<8} {package.summary}"
            _put(screen, line, 0, text.ljust(width - 1), width - 1, attribute)
            if self.model.enabled(package.key):
                _put(screen, line, 3, "[x]", 3, attribute | self.enabled_style | curses.A_BOLD)

        if not rows:
            _put(screen, 3, 0, " No matches. / then Enter clears search.", width - 1)
        detail_line = height - 5
        current_row = self.current(rows)
        detail = ""
        if current_row is not None and current_row.is_group:
            detail = " Category: " + current_row.group
        if current_row is not None and current_row.package is not None:
            package = current_row.package
            note = self.model.status_note(package)
            detail = f" {package.key}: {package.summary}"
            if note:
                detail += f"  [{note}]"
            package_issues = self.model.issues_for(package.key)
            if package_issues:
                detail += "  " + "; ".join(issue.summary() for issue in package_issues)
        _put(screen, detail_line, 0, detail.ljust(width - 1), width - 1, curses.A_DIM)

        summary = f" {len(issues)} unmet requirement(s)" if issues else " selection is consistent"
        if width < 60:
            summary = f" {len(issues)} requirement(s)" if issues else " Ready"
        summary += f" | {self.cursor + 1 if rows else 0}/{len(rows)}"
        if self.dirty:
            summary += " | unsaved changes"
        _put(screen, height - 4, 0, summary.ljust(width - 1), width - 1)
        _put(screen, height - 3, 0, self.message.ljust(width - 1), width - 1)
        help_lines = (
            _KEY_HELP
            if width >= 70
            else ("Space toggle  / search  ? help", "s save  b build  q quit")
        )
        for offset, chunk in enumerate(help_lines):
            _put(
                screen, height - 2 + offset, 0, chunk.ljust(width - 1), width - 1, curses.A_REVERSE
            )
        screen.refresh()

    # -- input -----------------------------------------------------------

    def prompt(self, screen: "_CursesWindow", label: str, initial: str = "") -> str | None:
        value = initial
        position = len(value)
        replace = True
        _cursor(True)
        try:
            while True:
                height, width = screen.getmaxyx()
                if height < 10 or width < 40:
                    return None
                # Keep the input visible even for a long path or prompt label.
                caption = label[: max(1, width // 2)]
                available = width - len(caption) - 2
                start = max(0, position - available + 1)
                while _cell_width(value[start:position]) >= available:
                    start += 1
                _put(screen, height - 3, 0, " " * (width - 1), width - 1)
                _put(screen, height - 3, 0, caption, len(caption))
                _put(screen, height - 3, len(caption), value[start:], available)
                try:
                    screen.move(height - 3, len(caption) + _cell_width(value[start:position]))
                    screen.refresh()
                    key = screen.get_wch()
                except curses.error:
                    continue
                if key in ("\n", "\r", curses.KEY_ENTER):
                    return value.strip()
                if key == "\x1b":
                    return None
                if key == curses.KEY_RESIZE:
                    continue
                if key == "\x15":
                    value, position = "", 0
                elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                    if replace:
                        value, position = "", 0
                    elif position:
                        value = value[: position - 1] + value[position:]
                        position -= 1
                elif key == curses.KEY_DC:
                    value = value[:position] + value[position + 1 :]
                elif key == curses.KEY_LEFT:
                    position = max(0, position - 1)
                elif key == curses.KEY_RIGHT:
                    position = min(len(value), position + 1)
                elif key == curses.KEY_HOME:
                    position = 0
                elif key == curses.KEY_END:
                    position = len(value)
                elif isinstance(key, str) and key.isprintable():
                    if replace:
                        value, position = "", 0
                    if len(value) < 256:
                        value = value[:position] + key + value[position:]
                        position += len(key)
                replace = False
        finally:
            _cursor(False)

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
                _put(screen, 0, 0, "Resize terminal; q returns.", max(0, width - 1))
            else:
                _put(
                    screen,
                    0,
                    0,
                    "Launch settings (this session only; q returns)",
                    width - 1,
                    curses.A_REVERSE,
                )
                for index, (key, name, label) in enumerate(fields, 1):
                    value = getattr(launch, name) or "auto"
                    _put(screen, index, 0, f"{key}  {label}: {value}", width - 1)
                _put(screen, height - 2, 0, self.message, width - 1)
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
        try:
            target = Path(answer).expanduser()
            if not target.is_absolute():
                target = Path.cwd() / target
            if target.is_symlink():
                raise BuildError("Refusing to replace a symlinked configuration file.")
            publish_atomically(
                target, render_config(self.model.settings, self.model.states), mode=0o644
            )
        except (OSError, BuildError, ValueError, RuntimeError) as error:
            self.message = f"Save failed: {error}"
            return False
        self.result.saved_path = target
        self.default_path = target
        self._saved_config = render_config(self.model.settings, self.model.states)
        self.message = f"Saved '{target}'."
        return True

    def choose_preset(self, screen: "_CursesWindow") -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        _put(screen, 0, 0, "Choose a preset", width - 1, curses.A_REVERSE)
        for index, (key, name, note) in enumerate(_PRESETS, 2):
            _put(screen, index, 0, f" {key}  {name}: {note}", width - 1)
        _put(screen, height - 1, 0, "Press a preset key; Esc cancels", width - 1)
        screen.refresh()
        pressed = screen.getch()
        for key, name, _note in _PRESETS:
            if pressed == ord(key):
                self.model.apply_preset(name)
                self.message = f"Applied the '{name}' preset."
                return
        self.message = "Preset cancelled."

    def handle(self, screen: "_CursesWindow", pressed: int) -> bool:
        """Act on one keystroke. Returns False to leave the menu."""
        rows = self.rows()
        row = self.current(rows)
        height, width = screen.getmaxyx()
        if height < 10 or width < 40:
            return not (pressed in (ord("q"), 27) and not self.dirty)
        page = max(1, height - 7)

        if pressed in (curses.KEY_UP, ord("k")):
            self.cursor = max(0, self.cursor - 1)
        elif pressed in (curses.KEY_DOWN, ord("j")):
            self.cursor = max(0, min(len(rows) - 1, self.cursor + 1))
        elif pressed == curses.KEY_PPAGE:
            self.cursor = max(0, self.cursor - page)
        elif pressed == curses.KEY_NPAGE:
            self.cursor = max(0, min(len(rows) - 1, self.cursor + page))
        elif pressed == curses.KEY_HOME:
            self.cursor = 0
        elif pressed == curses.KEY_END:
            self.cursor = max(0, len(rows) - 1)
        elif pressed in (9, curses.KEY_BTAB):
            headings = [i for i, candidate in enumerate(rows) if candidate.is_group]
            candidates = (
                [i for i in headings if i > self.cursor]
                if pressed == 9
                else [i for i in headings if i < self.cursor]
            )
            if headings:
                self.cursor = (
                    (candidates[0] if candidates else headings[0])
                    if pressed == 9
                    else (candidates[-1] if candidates else headings[-1])
                )
        elif pressed in (ord("["), ord("]")):
            self.model.collapsed = (
                {group.name for group in registry.GROUPS} if pressed == ord("[") else set()
            )
            self.cursor = 0
        elif pressed == ord("?"):
            self.show_help(screen)
        elif pressed == ord("i") and row is not None:
            if row.package is None:
                group = self.model.group(row.group)
                self.show_help(
                    screen, (group.name, *(f"{p.key}: {p.summary}" for p in group.packages))
                )
            else:
                package = row.package
                self.show_help(
                    screen,
                    (
                        package.key,
                        package.summary,
                        self.model.status_note(package),
                        *(issue.message for issue in self.model.issues_for(package.key)),
                    ),
                )
        elif pressed in (ord(" "), curses.KEY_ENTER, 10, 13):
            if row is None:
                pass
            elif row.is_group:
                self._toggle_fold(row.group)
            else:
                assert row.package is not None
                self.model.toggle(row.package.key)
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
                state = "Enabled" if pressed == ord("a") else "Disabled"
                self.message = f"{state} entire category ({len(self.model.group(row.group).packages)} packages), including hidden matches."
        elif pressed == ord("g"):
            self.model.settings.enable_gpl_and_non_free = not self.model.gpl
        elif pressed == ord("l"):
            self.model.settings.latest = not self.model.settings.latest
        elif pressed == ord("/"):
            answer = self.prompt(screen, "Filter: ")
            if answer is not None:
                self.model.search = answer
                self.cursor = 0
                self.top = 0
                self.message = (
                    "Search cleared." if not answer else f"Showing matches for '{answer}'."
                )
        elif pressed == ord("p"):
            self.choose_preset(screen)
        elif pressed == ord("f"):
            if row is not None and row.package is not None:
                changed = self.model.auto_fix(row.package.key)
                self.message = (
                    f"Enabled {', '.join(changed)}." if changed else "Nothing to fix here."
                )
        elif pressed == ord("F"):
            changed = self.model.auto_fix_all()
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

    def show_help(self, screen: "_CursesWindow", paragraphs: tuple[str, ...] = _HELP) -> None:
        top = 0
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            lines = [
                line for paragraph in paragraphs for line in _wrap(paragraph, max(1, width - 2))
            ]
            page = max(1, height - 2)
            top = min(top, max(0, len(lines) - page))
            for offset, line in enumerate(lines[top : top + page]):
                _put(screen, offset, 0, line, width - 1)
            _put(
                screen, height - 1, 0, "Up/Down scroll; q/Esc returns", width - 1, curses.A_REVERSE
            )
            screen.refresh()
            pressed = screen.getch()
            if pressed in (ord("q"), 27, ord("?")):
                return
            if pressed in (curses.KEY_DOWN, ord("j"), curses.KEY_NPAGE):
                top += page if pressed == curses.KEY_NPAGE else 1
            elif pressed in (curses.KEY_UP, ord("k"), curses.KEY_PPAGE):
                top = max(0, top - (page if pressed == curses.KEY_PPAGE else 1))

    def _toggle_fold(self, group_name: str) -> None:
        if group_name in self.model.collapsed:
            self.model.collapsed.discard(group_name)
        else:
            self.model.collapsed.add(group_name)

    def loop(self, screen: "_CursesWindow") -> MenuResult:
        _cursor(False)
        screen.keypad(True)
        if not os.environ.get("NO_COLOR") and curses.has_colors():
            try:
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_CYAN, -1)
                curses.init_pair(2, curses.COLOR_GREEN, -1)
                self.category_style = curses.color_pair(1)
                self.enabled_style = curses.color_pair(2)
            except curses.error:
                # Monochrome terminals retain headings, counts and checkboxes.
                pass
        while True:
            try:
                self.draw(screen)
                pressed = screen.getch()
                if not self.handle(screen, pressed):
                    return self.result
            except KeyboardInterrupt:
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
