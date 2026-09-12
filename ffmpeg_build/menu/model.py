"""Selection state and live requirement evaluation for the interactive menu.

Everything here is pure: it reads the registry and a set of booleans and
returns what should be displayed. No build code runs, which is exactly why the
registry keeps licence gating and requirement rules as data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import registry
from ..config import BuildSettings, Selection
from ..registry import Gate, Package
from ..runtime.errors import UsageError


@dataclass
class LaunchSettings:
    """Session-only options; the TOML schema remains the two build booleans."""

    compiler: str = "gcc"
    jobs: str = ""
    cuda_install: str = "ask"
    cuda_arch_mode: str = "native"
    cuda_architectures: str = ""
    build_root: str = ""

    def validate(self) -> None:
        if self.compiler not in ("gcc", "clang"):
            raise UsageError("Compiler must be 'gcc' or 'clang'.")
        if self.jobs and not re.fullmatch(r"[1-9][0-9]*", self.jobs):
            raise UsageError("Jobs must be a positive integer, or empty for available CPUs.")
        if self.cuda_install not in ("ask", "always", "never"):
            raise UsageError("CUDA installation must be 'ask', 'always', or 'never'.")
        if self.cuda_arch_mode not in ("native", "all", "custom"):
            raise UsageError("CUDA architecture mode must be 'native', 'all', or 'custom'.")
        if self.cuda_arch_mode == "custom" and not re.fullmatch(
            r"[0-9]+(?:\s+[0-9]+)*", self.cuda_architectures
        ):
            raise UsageError("Custom CUDA architectures need numeric targets, for example '86 89'.")
        if any(character.isspace() or ord(character) < 32 for character in self.build_root):
            raise UsageError("The build root may not contain whitespace or control characters.")


@dataclass(frozen=True)
class Issue:
    """One unmet requirement.

    `blocking` separates a rule that can only be satisfied by enabling the
    other package from one a host development package can also satisfy. The
    build treats both as fatal when nothing provides them, but the menu cannot
    see the host's packages, so it must not claim a warning is an error.
    """

    package: str
    needs: str
    message: str
    blocking: bool

    def summary(self) -> str:
        return f"{self.package} needs {self.needs}"


class MenuModel:
    """The editable configuration behind the menu."""

    def __init__(self, states: dict[str, bool], settings: BuildSettings) -> None:
        # Normalize the allowlist before rendering/saving: omitted choices are
        # off in the menu, whereas render_config's defaults build the template.
        self.states = {key: states.get(key, False) for key in registry.PACKAGE_NAMES}
        self.settings = settings
        self.collapsed = {group.name for group in registry.GROUPS}
        self.search = ""

    # -- selection -------------------------------------------------------

    def enabled(self, key: str) -> bool:
        return self.states.get(key, False)

    def toggle(self, key: str) -> None:
        self.states[key] = not self.states.get(key, False)

    def set_group(self, group_name: str, value: bool) -> None:
        for package in self.group(group_name).packages:
            self.states[package.key] = value

    def group(self, name: str) -> registry.Group:
        for group in registry.GROUPS:
            if group.name == name:
                return group
        raise KeyError(name)

    def enabled_count(self, group: registry.Group) -> int:
        return sum(1 for package in group.packages if self.enabled(package.key))

    # -- presets ---------------------------------------------------------

    def apply_preset(self, name: str) -> None:
        """Presets are starting points, not policies.

        `template` restores what the tracked example ships, `all` and `none`
        are the extremes, and `minimal` keeps only the build tools plus FFmpeg
        itself, which is the smallest selection that still produces a binary.
        """
        if name == "all":
            self.states = {key: True for key in registry.PACKAGE_NAMES}
        elif name == "none":
            self.states = {key: False for key in registry.PACKAGE_NAMES}
        elif name == "template":
            self.states = {
                package.key: package.default_enabled for package in registry.PACKAGES.values()
            }
        elif name == "minimal":
            tools = {tool.key for tool in registry.GROUPS[0].packages}
            self.states = {
                package.key: package.key in tools or package.key == "ffmpeg"
                for package in registry.PACKAGES.values()
            }

    # -- licence gating --------------------------------------------------

    @property
    def gpl(self) -> bool:
        return self.settings.enable_gpl_and_non_free

    def status_note(self, package: Package) -> str:
        """What the licence mode currently does to this package."""
        if not self.enabled(package.key):
            return ""
        if package.gate is Gate.REQUIRES_GPL and not self.gpl:
            return "waiting for GPL/non-free"
        if package.gate is Gate.FLAG_REQUIRES_GPL and not self.gpl:
            return "builds, FFmpeg option needs GPL/non-free"
        if package.gate is Gate.SUPPRESSED_BY_GPL and self.gpl and self.enabled("openssl"):
            return "skipped: OpenSSL is the TLS stack in GPL mode"
        return ""

    # -- requirements ----------------------------------------------------

    def issues(self) -> list[Issue]:
        """Every unmet requirement for the current selection."""
        found: list[Issue] = []
        gpl_openssl = self.gpl and self.enabled("openssl")
        for rule in registry.REQUIREMENTS:
            if rule.condition == "gpl-openssl" and not gpl_openssl:
                continue
            if rule.condition == "not-gpl-openssl" and gpl_openssl:
                continue
            if rule.condition == "gpl" and not self.gpl:
                continue
            if not self.enabled(rule.package) or self.enabled(rule.needs):
                continue
            found.append(
                Issue(
                    package=rule.package,
                    needs=rule.needs,
                    message=rule.message(),
                    blocking=rule.pkgconf_module is None,
                )
            )
        return found

    def issues_for(self, key: str) -> list[Issue]:
        return [issue for issue in self.issues() if issue.package == key]

    def requirement_closure(self, key: str) -> list[str]:
        """Every package that has to be on for `key` to build, transitively."""
        needed: list[str] = []
        pending = [key]
        seen = {key}
        while pending:
            current = pending.pop()
            for rule in registry.requirements_for(current):
                gpl_openssl = self.gpl and self.enabled("openssl")
                if rule.condition == "gpl-openssl" and not gpl_openssl:
                    continue
                if rule.condition == "not-gpl-openssl" and gpl_openssl:
                    continue
                if rule.condition == "gpl" and not self.gpl:
                    continue
                if rule.needs in seen:
                    continue
                seen.add(rule.needs)
                needed.append(rule.needs)
                pending.append(rule.needs)
        return needed

    def auto_fix(self, key: str) -> list[str]:
        """Enable the transitive closure, reporting what changed."""
        changed = [needed for needed in self.requirement_closure(key) if not self.enabled(needed)]
        for needed in changed:
            self.states[needed] = True
        return changed

    def auto_fix_all(self) -> list[str]:
        changed: list[str] = []
        # Repeat until stable: enabling one package can introduce requirements
        # of its own.
        while True:
            outstanding = self.issues()
            if not outstanding:
                return changed
            progressed = False
            for issue in outstanding:
                if not self.enabled(issue.needs):
                    self.states[issue.needs] = True
                    changed.append(issue.needs)
                    progressed = True
            if not progressed:
                return changed

    # -- output ----------------------------------------------------------

    def to_selection(self) -> Selection:
        return Selection({key: self.enabled(key) for key in registry.PACKAGE_NAMES}, None)

    def matches_search(self, package: Package) -> bool:
        if not self.search:
            return True
        needle = self.search.lower()
        return any(
            needle in text.lower()
            for text in (package.key, package.summary, registry.PACKAGES[package.key].group)
        )
