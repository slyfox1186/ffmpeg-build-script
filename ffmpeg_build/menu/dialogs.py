"""Focused Textual dialogs for presets, launch settings, help and Save as."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Select, Static
from textual.widgets.option_list import Option

from ..runtime.errors import UsageError
from .model import LaunchSettings
from .session import MenuSession


def plain(value: str) -> Text:
    """Treat paths and errors as text, never markup or terminal controls."""
    return Text(
        "".join(
            character
            if character in "\n\t" or not unicodedata.category(character).startswith("C")
            else "?"
            for character in value
        )
    )


DIALOG_CSS = """
    ModalScreen { align: center middle; background: $background; }
    .dialog { width: 76; max-width: 100%; height: auto; max-height: 100%; border: round $accent; padding: 1 2; background: $surface; }
    .dialog Label { height: auto; margin-top: 1; }
    .dialog .title { text-style: bold; color: $accent; margin-top: 0; }
    .dialog .hint { color: $text-muted; height: auto; }
    .dialog .error { color: $error; height: auto; }
    .dialog Input, .dialog Select { width: 1fr; }
    .dialog .buttons { height: 3; align-horizontal: right; margin-top: 1; }
    .dialog Button { margin-left: 1; }
    #preset-list { height: 10; }
    #help-text { height: auto; }
"""


class PresetScreen(ModalScreen[str | None]):
    AUTO_FOCUS = "#preset-list"
    CSS = DIALOG_CSS
    BINDINGS = [
        Binding("escape,q", "dismiss(None)", "Close", show=False),
        Binding("t", "preset('template')", "Template", show=False),
        Binding("a", "preset('all')", "All", show=False),
        Binding("m", "preset('minimal')", "Minimal", show=False),
        Binding("n", "preset('none')", "None", show=False),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="dialog"):
            yield Label("Package presets", classes="title")
            yield Static(
                "Selecting a preset saves immediately. Press u afterwards to undo. Compiler and build settings are preserved. Completed packages are reused when building.",
                classes="hint",
            )
            yield OptionList(
                Option("Template   Defaults from example.toml", id="template"),
                Option("All        Every package", id="all"),
                Option("Minimal    Build tools and FFmpeg", id="minimal"),
                Option("None       Start with an empty selection", id="none"),
                id="preset-list",
            )
            yield Button("Cancel", id="cancel")

    @on(OptionList.OptionSelected)
    def selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)

    def action_preset(self, name: str) -> None:
        self.dismiss(name)

    @on(Button.Pressed)
    def cancel(self) -> None:
        self.dismiss(None)


class FileForm(VerticalScroll, can_focus=False):
    """Route arrows through the focused control before navigating the form."""

    BINDINGS = [
        Binding("up,down", "screen.switch_row", "Change row", show=False),
        Binding("left", "screen.focus_button('cancel')", "Cancel button", show=False),
        Binding("right", "screen.focus_button('confirm')", "Confirm button", show=False),
    ]


class FileScreen(ModalScreen[None]):
    """A shared path field and action row for saving and importing configuration."""

    AUTO_FOCUS = "Input"
    CSS = DIALOG_CSS
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel", show=False)]

    def __init__(
        self,
        session: MenuSession,
        *,
        operation: str,
        heading: str,
        hint: str,
        initial_path: str,
        submit: Callable[[str], bool],
    ) -> None:
        super().__init__()
        self.session = session
        self.operation = operation
        self.heading = heading
        self.hint = hint
        self.initial_path = initial_path
        self.submit_path = submit
        self._last_button = "cancel"

    def compose(self) -> ComposeResult:
        with FileForm(classes="dialog"):
            yield Label(self.heading, classes="title")
            yield Static(plain(self.hint), classes="hint")
            yield Input(
                self.initial_path,
                id=f"{self.operation}-path",
                placeholder="Relative or full path (~/... also works)",
                select_on_focus=True,
            )
            yield Static(
                plain(f"Relative paths use: {Path.cwd()}"),
                classes="hint",
                id="file-path-base",
            )
            yield Static(
                "Up/Down: path/buttons · Left/Right: cursor/buttons",
                classes="hint",
            )
            yield Static(classes="error", id=f"{self.operation}-error", markup=False)
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button(self.operation.title(), id=self.operation, variant="primary")

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "focus_button":
            return isinstance(self.focused, Button)
        return super().check_action(action, parameters)

    def action_switch_row(self) -> None:
        if isinstance(self.focused, Button):
            self._last_button = self.focused.id or "cancel"
            self.set_focus(self.query_one(Input))
        else:
            self.set_focus(self.query_one(f"#{self._last_button}", Button))

    def action_focus_button(self, button_id: str) -> None:
        if button_id == "confirm":
            button_id = self.operation
        self.set_focus(self.query_one(f"#{button_id}", Button))

    @on(Input.Submitted)
    def submit(self) -> None:
        path = self.query_one(Input).value
        if path and self.submit_path(path):
            self.dismiss(None)
        else:
            self.query_one(f"#{self.operation}-error", Static).update(
                plain(self.session.message if path else "Enter a file path.")
            )

    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == self.operation:
            self.submit()


class SaveScreen(FileScreen):
    def __init__(self, session: MenuSession) -> None:
        super().__init__(
            session,
            operation="save",
            heading="Save configuration as",
            hint="Future changes will automatically save to this file.",
            initial_path=str(session.default_path),
            submit=session.save,
        )


class ImportScreen(FileScreen):
    def __init__(self, session: MenuSession) -> None:
        super().__init__(
            session,
            operation="import",
            heading="Import TOML configuration",
            hint=(
                "Replace packages, compiler, GPL/non-free and latest.\n"
                f"Press u afterwards to undo. Saves to: {session.default_path}"
            ),
            initial_path="",
            submit=session.import_config,
        )


class SettingsScreen(ModalScreen[LaunchSettings | None]):
    AUTO_FOCUS = "#jobs"
    CSS = DIALOG_CSS
    BINDINGS = [Binding("escape", "dismiss(None)", "Close", show=False)]

    def __init__(self, launch: LaunchSettings) -> None:
        super().__init__()
        self.launch = launch

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="dialog"):
            yield Label("Build and launch settings", classes="title")
            yield Static(
                "These launch options apply to this session. Compiler, GPL/non-free and latest-version choices are saved automatically in the main menu.",
                classes="hint",
            )
            yield Label("Parallel jobs · leave empty for available CPUs")
            yield Input(self.launch.jobs, id="jobs", placeholder="Auto", select_on_focus=True)
            yield Label("CUDA installation")
            yield Select(
                [(value.title(), value) for value in ("ask", "always", "never")],
                value=self.launch.cuda_install,
                allow_blank=False,
                id="cuda-install",
            )
            yield Label("CUDA architecture mode")
            yield Select(
                [(value.title(), value) for value in ("native", "all", "custom")],
                value=self.launch.cuda_arch_mode,
                allow_blank=False,
                id="cuda-mode",
            )
            yield Label("Custom CUDA targets · space-separated numbers")
            yield Input(
                self.launch.cuda_architectures,
                id="cuda-targets",
                placeholder="86 89",
                select_on_focus=True,
            )
            yield Label("Build root · leave empty for the default")
            yield Input(self.launch.build_root, id="build-root", select_on_focus=True)
            yield Static(id="settings-error", classes="error", markup=False)
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Apply", id="apply", variant="primary")

    @on(Input.Submitted)
    @on(Button.Pressed, "#apply")
    def apply(self) -> None:
        launch = LaunchSettings(
            jobs=self.query_one("#jobs", Input).value,
            cuda_install=str(self.query_one("#cuda-install", Select).value),
            cuda_arch_mode=str(self.query_one("#cuda-mode", Select).value),
            cuda_architectures=self.query_one("#cuda-targets", Input).value,
            build_root=self.query_one("#build-root", Input).value,
        )
        try:
            launch.validate()
        except UsageError as error:
            self.query_one("#settings-error", Static).update(plain(str(error)))
            return
        self.dismiss(launch)

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)


HELP = """Choose Compilers or a package category on the left.
Right or Enter opens its options. Up/Down moves within a list.
Enter or Space selects an option and returns to the category list.
Left, Escape or Backspace returns without changing the selection.
Tab / Shift+Tab moves between controls. Mouse clicks and scrolling work too.

/ searches packages by name, description or category. Enter or Escape leaves the search field; clear its text to show all packages.
c opens Compilers. g toggles GPL/non-free; l toggles latest-version checks.
a / d enables or disables the entire category, including hidden search matches.
p opens package presets. u undoes the last saved change (up to 50).
f enables the current package's requirements; F fixes all requirements.
D shows the full description and dependency details.
e edits jobs, CUDA and build root for this session.

Every package, compiler, licence, latest-version, preset and undo change saves immediately. A failed save reverts the change and shows an error.
s saves to another file and makes it the new autosave destination.
i imports a TOML file into the current configuration; u undoes the import.
b validates the configuration, saves it and starts the build.
q quits immediately. Ctrl+C, Ctrl+D or Ctrl+Q exits from any screen.
The terminal is restored and cleared when the menu closes.
"""


class HelpScreen(ModalScreen[None]):
    CSS = DIALOG_CSS
    BINDINGS = [Binding("escape,q,question_mark", "dismiss(None)", "Close", show=False)]

    def __init__(self, text: str = HELP, *, title: str = "Menu help") -> None:
        super().__init__()
        self.text = text
        self.heading = title

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="dialog"):
            yield Label(self.heading, classes="title")
            yield Static(plain(self.text), id="help-text")
            yield Button("Close", id="close", variant="primary")

    @on(Button.Pressed)
    def close(self) -> None:
        self.dismiss(None)
