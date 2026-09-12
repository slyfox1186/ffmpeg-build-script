"""Textual configuration editor; persistence and build decisions live in MenuSession."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    OptionList,
    RadioButton,
    RadioSet,
    SelectionList,
    Static,
    Switch,
)
from textual.widgets.option_list import Option

from .. import registry
from ..config import COMPILERS
from ..registry import Package
from .dialogs import HelpScreen, PresetScreen, SaveScreen, SettingsScreen, plain
from .model import LaunchSettings, MenuModel
from .session import MenuResult, MenuSession


class CompilerChoices(RadioSet):
    def action_toggle_button(self) -> None:
        super().action_toggle_button()
        # A confirmed existing choice also returns to categories.
        self.call_after_refresh(self.post_message, self.Confirmed())

    class Confirmed(Message):
        pass

    def on_mount(self) -> None:
        # RadioSet initializes its cursor after subclass mount handlers.
        self.call_after_refresh(self._align_cursor)

    def _align_cursor(self) -> None:
        if self.pressed_index == 1:
            self.action_next_button()


class CompilerPane(Vertical):
    """Recompose from committed state after undo or a failed write.

    RadioSet change events suppress nested radio events; reconstructing the
    view avoids feeding rollback changes through its in-progress toggle event.
    """

    def __init__(self, compiler: str, *, id: str) -> None:
        super().__init__(id=id)
        self.compiler = compiler

    def compose(self) -> ComposeResult:
        yield CompilerChoices(
            RadioButton(
                "GCC   GNU C and C++ toolchain",
                value=self.compiler == "gcc",
                id="gcc",
            ),
            RadioButton(
                "Clang   LLVM C and C++ toolchain",
                value=self.compiler == "clang",
                id="clang",
            ),
            id="compiler-options",
        )


class MenuApp(App[MenuResult]):
    TITLE = "FFmpeg Build Configuration"
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    Screen { background: $background; color: $text; }
    #masthead { height: 3; padding: 1 2 0 2; }
    #brand { text-style: bold; color: $accent; width: 1fr; }
    #count { width: auto; color: $text-muted; }
    #toolbar { height: 3; padding: 0 2; align-vertical: middle; }
    #toolbar Label { width: auto; margin-right: 1; }
    #toolbar Switch { margin-right: 1; }
    #toolbar Button { margin-left: 1; min-width: 9; width: auto; padding: 0 1; }
    #launch-summary { width: 1fr; color: $text-muted; }
    #search { margin: 0 2; height: 3; }
    #workspace { height: 1fr; margin: 0 2; }
    #sidebar { width: 32; border: round $primary-lighten-1; padding: 0 1; }
    #sidebar:focus-within { border: round $accent; }
    #compiler-category { width: 1fr; height: 1; min-height: 1; border: none; text-align: left; padding: 0 1; }
    #compiler-category.active { background: $primary; color: $text; text-style: bold; }
    #package-heading { height: 2; border-top: solid $primary-lighten-1; color: $text-muted; margin-top: 1; }
    #categories { height: 1fr; padding: 0; border: none; background: $surface; }
    #no-categories { height: auto; color: $text-muted; }
    #options { width: 1fr; margin-left: 1; border: round $primary-lighten-1; padding: 0 1; }
    #options:focus-within { border: round $accent; }
    #compiler-pane { height: auto; }
    #compiler-options { border: none; height: auto; margin-top: 1; }
    #compiler-options RadioButton { height: 3; padding: 1; }
    #compiler-note { margin-top: 1; color: $text-muted; height: auto; }
    #packages { height: 1fr; border: none; padding: 0; background: $surface; }
    #empty { padding: 1; color: $text-muted; height: auto; }
    #details { height: 3; margin: 0 2; padding: 0 1; color: $text-muted; }
    #status { height: 1; margin: 0 2; color: $success; }
    #status.error { color: $error; text-style: bold; }
    #navigation { height: 1; margin: 0 2; color: $text-muted; }
    .narrow #launch-summary { display: none; }
    .short #masthead { height: 1; padding: 0 2; }
    .short #search { height: 1; border: none; padding: 0; margin: 1 2 0 2; }
    .short #details { height: 2; }
    .short #compiler-note { display: none; }
    .compact #masthead { height: 1; padding: 0 1; }
    .compact #brand { width: 1fr; }
    .compact #count { display: none; }
    .compact #toolbar, .compact #details { display: none; }
    .compact #search { height: 1; border: none; margin: 0 1; padding: 0; }
    .compact #workspace { margin: 0; }
    .compact #sidebar { width: 1fr; }
    .compact #options { display: none; margin-left: 0; }
    .compact.options-focused #sidebar { display: none; }
    .compact.options-focused #options { display: block; }
    .compact #package-heading { height: 1; margin-top: 0; }
    .compact #compiler-options { margin-top: 0; }
    .compact #compiler-options RadioButton { height: 1; padding: 0; }
    .compact #compiler-note { display: none; }
    .compact #status, .compact #navigation { margin: 0 1; }
    """
    BINDINGS = [
        Binding("b", "build", "Build"),
        Binding("q", "quit_menu", "Quit"),
        Binding("e", "settings", "Settings"),
        Binding("p", "presets", "Presets"),
        Binding("s", "save_as", "Save as"),
        Binding("u", "undo", "Undo"),
        Binding("ctrl+c,ctrl+d,ctrl+q", "quit_menu", "Quit", show=False, priority=True),
        Binding("escape,left,backspace,ctrl+h", "categories", "Back", show=False, priority=True),
        Binding("right", "options", "Browse", show=False, priority=True),
        Binding("up,k", "previous_category", "Previous", show=False, priority=True),
        Binding("down,j", "next_category", "Next", show=False, priority=True),
        Binding("slash", "search", "Search", show=False),
        Binding("c", "compilers", "Compilers", show=False),
        Binding("g", "toggle_gpl", "GPL/non-free", show=False),
        Binding("l", "toggle_latest", "Latest", show=False),
        Binding("a", "enable_category", "Enable category", show=False),
        Binding("d", "disable_category", "Disable category", show=False),
        Binding("f", "fix_current", "Fix package", show=False),
        Binding("F", "fix_all", "Fix requirements", show=False),
        Binding("question_mark", "help", "Help", show=False),
        Binding("i", "details", "Details", show=False),
    ]

    def __init__(
        self, model: MenuModel, default_path: Path, launch: LaunchSettings | None = None
    ) -> None:
        super().__init__()
        self.session = MenuSession(model, default_path, launch)
        self.model = model
        self.group_index: int | None = None
        self.visible_groups: list[int] = list(range(len(registry.GROUPS)))
        self.visible_packages: list[Package] = []
        self.theme = "textual-dark"

    def compose(self) -> ComposeResult:
        with Horizontal(id="masthead"):
            yield Static("FFMPEG / BUILD CONFIGURATION", id="brand")
            yield Static(id="count")
        with Horizontal(id="toolbar"):
            yield Label("GPL/non-free")
            yield Switch(self.model.gpl, id="gpl", animate=False)
            yield Label("Latest")
            yield Switch(self.model.settings.latest, id="latest", animate=False)
            yield Static(id="launch-summary")
            yield Button("Settings", id="settings-button")
            yield Button("Presets", id="presets-button")
            yield Button("Build", variant="primary", id="build-button")
        yield Input(placeholder="Search packages by name, description or category  /", id="search")
        with Horizontal(id="workspace"):
            with Vertical(id="sidebar"):
                yield Button("Compilers", id="compiler-category", classes="active")
                yield Static("PACKAGES", id="package-heading")
                yield OptionList(id="categories")
                yield Static(
                    "No packages match.\n/ change search · c compilers", id="no-categories"
                )
            with Vertical(id="options"):
                yield CompilerPane(self.model.settings.compiler, id="compiler-pane")
                yield Static(
                    "Select one compiler. Your choice is saved in the TOML configuration and used by the build.",
                    id="compiler-note",
                )
                yield SelectionList[str](id="packages")
                yield Static("No packages match this search. Press / to change it.", id="empty")
        yield Static(id="details", markup=False)
        yield Static(id="status", markup=False)
        yield Static(id="navigation")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#sidebar").border_title = "CONFIGURATION"
        self._refresh_categories()
        self._show_category()
        self._refresh_state()
        self.action_categories()
        self.on_resize()

    def on_resize(self) -> None:
        self.screen.set_class(self.size.width < 76 or self.size.height < 18, "compact")
        self.screen.set_class(self.size.width < 110, "narrow")
        self.screen.set_class(self.size.height < 28, "short")

    @property
    def failure(self) -> Exception | None:
        # Textual retains its fatal exception but run() only returns an exit code.
        # Expose it here so the caller can report it after the required clear.
        return self._exception

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "quit_menu":
            return True
        if len(self.screen_stack) > 1:
            return False
        if isinstance(self.focused, Input):
            return False
        if action in ("previous_category", "next_category"):
            return self.focused is not None and self.focused.id in (
                "compiler-category",
                "categories",
            )
        return True

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if len(self.screen_stack) > 1:
            return
        if event.widget.id in ("packages", "compiler-options"):
            self.screen.add_class("options-focused")
        elif event.widget.id in ("compiler-category", "categories"):
            self.screen.remove_class("options-focused")
        if event.widget.id == "compiler-category" and self.group_index is not None:
            self.group_index = None
            self._show_category()
        self._refresh_navigation()

    def _refresh_navigation(self) -> None:
        right = self.focused is not None and self.focused.id in ("packages", "compiler-options")
        text = (
            "Enter/Space select · Left/Esc/Backspace back"
            if right
            else "Right/Enter browse · / search · ? help"
        )
        if self.screen.has_class("compact"):
            text = (
                "Left/Esc/Backspace back · Enter select"
                if right
                else "Right/Enter browse · / search · ? help"
            )
        self.query_one("#navigation", Static).update(text)

    def _refresh_categories(self) -> None:
        categories = self.query_one("#categories", OptionList)
        self.visible_groups = [
            index
            for index, group in enumerate(registry.GROUPS)
            if any(self.model.matches_search(package) for package in group.packages)
        ]
        self.query_one("#no-categories").display = not self.visible_groups
        with self.prevent(OptionList.OptionHighlighted):
            categories.clear_options()
            categories.add_options(
                [
                    Option(self._category_label(index), id=str(index))
                    for index in self.visible_groups
                ]
            )
            if self.group_index in self.visible_groups:
                categories.highlighted = self.visible_groups.index(self.group_index)

    def _category_label(self, index: int) -> Text:
        group = registry.GROUPS[index]
        return Text(
            f"{(group.title or group.name):<20} {self.model.enabled_count(group):>2}/{len(group.packages)}"
        )

    def _package_label(self, package: Package) -> Text:
        note = self.model.status_note(package)
        issue = "! " if self.model.issues_for(package.key) else ""
        return Text(f"{issue}{package.key:<20} {package.summary}" + (f" · {note}" if note else ""))

    def _show_category(self) -> None:
        compiler = self.group_index is None
        self.query_one("#compiler-category").set_class(compiler, "active")
        self.query_one("#compiler-pane").display = compiler
        self.query_one("#compiler-note").display = compiler
        packages = self.query_one("#packages", SelectionList)
        self.visible_packages = (
            []
            if compiler
            else [
                package
                for package in registry.GROUPS[self.group_index or 0].packages
                if self.model.matches_search(package)
            ]
        )
        with self.prevent(SelectionList.SelectedChanged, SelectionList.SelectionHighlighted):
            packages.clear_options()
            packages.add_options(
                [
                    (self._package_label(package), package.key, self.model.enabled(package.key))
                    for package in self.visible_packages
                ]
            )
            packages.highlighted = 0 if self.visible_packages else None
        packages.display = not compiler and bool(self.visible_packages)
        self.query_one("#empty").display = not compiler and not self.visible_packages
        self.query_one("#options").border_title = (
            "COMPILERS"
            if compiler
            else (
                registry.GROUPS[self.group_index or 0].title
                or registry.GROUPS[self.group_index or 0].name
            ).upper()
        )
        self._refresh_details()

    def _refresh_state(self) -> None:
        categories = self.query_one("#categories", OptionList)
        for index in self.visible_groups:
            categories.replace_option_prompt(str(index), self._category_label(index))
        packages = self.query_one("#packages", SelectionList)
        with self.prevent(SelectionList.SelectedChanged):
            for index, package in enumerate(self.visible_packages):
                packages.replace_option_prompt_at_index(index, self._package_label(package))
                if self.model.enabled(package.key):
                    packages.select(package.key)
                else:
                    packages.deselect(package.key)
        with self.prevent(Switch.Changed):
            self.query_one("#gpl", Switch).value = self.model.gpl
            self.query_one("#latest", Switch).value = self.model.settings.latest
        pane = self.query_one(CompilerPane)
        pane.compiler = self.model.settings.compiler
        pressed = self.query_one("#compiler-options", RadioSet).pressed_button
        if pressed is not None and pressed.id != pane.compiler:
            pane.refresh(recompose=True)
        self.query_one(
            "#compiler-category", Button
        ).label = f"Compilers    {self.model.settings.compiler.upper()}"
        self.query_one("#count", Static).update(
            f"{sum(self.model.states.values())} / {len(registry.PACKAGES)} selected"
        )
        self.query_one("#launch-summary", Static).update(
            f"Jobs {self.session.result.launch.jobs or 'Auto'}"
        )
        status = self.query_one("#status", Static)
        status.update(plain(self.session.message))
        status.set_class(self.session.failed, "error")
        status.tooltip = plain(self.session.message + "\n" + str(self.session.default_path))
        self._refresh_details()

    def _current_package(self) -> Package | None:
        highlighted = self.query_one("#packages", SelectionList).highlighted
        if (
            self.group_index is None
            or highlighted is None
            or highlighted >= len(self.visible_packages)
        ):
            return None
        return self.visible_packages[highlighted]

    def _detail_text(self) -> str:
        package = self._current_package()
        if package is None:
            issues = self.model.issues()
            summary = (
                f"{len(issues)} unmet package requirements"
                if issues
                else "No missing package requirements"
            )
            return f"{summary} · Compiler {self.model.settings.compiler.upper()} · GPL/non-free {'ON' if self.model.gpl else 'OFF'}\n{self.session.default_path}"
        return "\n".join(
            filter(
                None,
                (
                    f"{package.key}: {package.summary}",
                    self.model.status_note(package),
                    *(issue.message for issue in self.model.issues_for(package.key)),
                ),
            )
        )

    def _refresh_details(self) -> None:
        self.query_one("#details", Static).update(plain(self._detail_text()))

    def _change(self, edit: Callable[[], object], message: str) -> None:
        self.session.change(edit, message)
        self._refresh_state()

    @on(OptionList.OptionHighlighted, "#categories")
    def category_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_id is not None and self.focused is self.query_one("#categories"):
            self.group_index = int(event.option_id)
            self._show_category()

    @on(OptionList.OptionSelected, "#categories")
    def category_selected(self) -> None:
        self.action_options()

    @on(Button.Pressed, "#compiler-category")
    def compiler_category_selected(self) -> None:
        self.group_index = None
        self._show_category()
        self.action_options()

    @on(RadioSet.Changed, "#compiler-options")
    def compiler_changed(self, event: RadioSet.Changed) -> None:
        compiler = COMPILERS[event.index]
        self._change(
            lambda: setattr(self.model.settings, "compiler", compiler),
            f"Compiler: {compiler.upper()}.",
        )
        self.call_after_refresh(self.action_categories)

    @on(SelectionList.SelectionToggled, "#packages")
    def package_toggled(self, event: SelectionList.SelectionToggled[str]) -> None:
        key = event.selection.value
        self._change(
            lambda: self.model.toggle(key),
            f"{'Disabled' if self.model.enabled(key) else 'Enabled'} {key}.",
        )
        self.call_after_refresh(self.action_categories)

    @on(SelectionList.SelectionHighlighted, "#packages")
    def package_highlighted(self) -> None:
        self._refresh_details()

    @on(Switch.Changed)
    def setting_toggled(self, event: Switch.Changed) -> None:
        name = "enable_gpl_and_non_free" if event.switch.id == "gpl" else "latest"
        self._change(
            lambda: setattr(self.model.settings, name, event.value), "Build setting updated."
        )

    @on(Input.Changed, "#search")
    def search_changed(self, event: Input.Changed) -> None:
        self.model.search = event.value
        self._refresh_categories()
        if self.group_index not in self.visible_groups:
            self.group_index = self.visible_groups[0] if self.visible_groups else 0
        self._show_category()

    @on(Input.Submitted, "#search")
    def search_submitted(self) -> None:
        self.action_categories()

    def on_key(self, event: events.Key) -> None:
        if (
            len(self.screen_stack) == 1
            and self.focused is self.query_one("#search")
            and event.key == "escape"
        ):
            event.stop()
            self.action_categories()

    def action_categories(self) -> None:
        self.screen.remove_class("options-focused")
        self.set_focus(
            self.query_one("#compiler-category" if self.group_index is None else "#categories")
        )
        self._refresh_navigation()

    def action_options(self) -> None:
        if self.group_index is not None and not self.visible_packages:
            return
        self.screen.add_class("options-focused")
        self.set_focus(
            self.query_one("#compiler-options" if self.group_index is None else "#packages")
        )
        self._refresh_navigation()

    @on(CompilerChoices.Confirmed)
    def compiler_confirmed(self) -> None:
        self.action_categories()

    def action_next_category(self) -> None:
        categories = self.query_one("#categories", OptionList)
        if self.focused is self.query_one("#compiler-category"):
            if self.visible_groups:
                self.group_index = self.visible_groups[0]
                categories.highlighted = 0
                self._show_category()
                self.set_focus(categories)
        else:
            categories.action_cursor_down()

    def action_previous_category(self) -> None:
        categories = self.query_one("#categories", OptionList)
        if categories.highlighted in (None, 0) or self.focused is self.query_one(
            "#compiler-category"
        ):
            self.action_compilers()
        else:
            categories.action_cursor_up()

    def action_compilers(self) -> None:
        self.group_index = None
        self._show_category()
        self.action_categories()

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_toggle_gpl(self) -> None:
        self._change(
            lambda: setattr(self.model.settings, "enable_gpl_and_non_free", not self.model.gpl),
            "GPL/non-free updated.",
        )

    def action_toggle_latest(self) -> None:
        self._change(
            lambda: setattr(self.model.settings, "latest", not self.model.settings.latest),
            "Latest-version checks updated.",
        )

    def _set_category(self, enabled: bool) -> None:
        if self.group_index is None:
            self.session.message = "Choose exactly one compiler with Enter or Space."
            self._refresh_state()
            return
        group = registry.GROUPS[self.group_index]
        self._change(
            lambda: self.model.set_group(group.name, enabled),
            f"{'Enabled' if enabled else 'Disabled'} entire category, including hidden matches.",
        )

    def action_enable_category(self) -> None:
        self._set_category(True)

    def action_disable_category(self) -> None:
        self._set_category(False)

    def action_fix_current(self) -> None:
        package = self._current_package()
        if package:
            self._change(
                lambda: self.model.auto_fix(package.key), f"Enabled requirements for {package.key}."
            )

    def action_fix_all(self) -> None:
        self._change(self.model.auto_fix_all, "Enabled missing requirements.")

    def action_undo(self) -> None:
        self.session.undo()
        self._refresh_state()

    @on(Button.Pressed, "#settings-button")
    def action_settings(self) -> None:
        self.push_screen(SettingsScreen(self.session.result.launch), self._settings_closed)

    def _settings_closed(self, launch: LaunchSettings | None) -> None:
        if launch is not None:
            self.session.result.launch = launch
            self.session.message, self.session.failed = (
                "Launch settings updated for this session.",
                False,
            )
        self._refresh_state()

    @on(Button.Pressed, "#presets-button")
    def action_presets(self) -> None:
        self.push_screen(PresetScreen(), self._preset_selected)

    def _preset_selected(self, preset: str | None) -> None:
        if preset is not None:
            self._change(lambda: self.model.apply_preset(preset), f"Applied the '{preset}' preset.")

    def action_save_as(self) -> None:
        self.push_screen(SaveScreen(self.session), lambda _: self._refresh_state())

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_details(self) -> None:
        self.push_screen(HelpScreen(self._detail_text()))

    @on(Button.Pressed, "#build-button")
    def action_build(self) -> None:
        if self.session.prepare_build():
            self.exit(self.session.result)
        else:
            self._refresh_state()
            self.push_screen(HelpScreen(self.session.message, title="Build needs attention"))

    def action_quit_menu(self) -> None:
        self.exit(self.session.result)
