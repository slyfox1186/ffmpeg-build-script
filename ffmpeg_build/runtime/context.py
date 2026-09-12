"""The build context every stage receives.

The Bash stages communicated through a dozen globals. Passing one object
instead is what makes a stage testable in isolation and what lets the
fixture-workspace dry run exercise stage ordering without touching the host.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TypeVar

from .. import registry
from ..config import CLEANUP_COMMAND, Selection
from . import artifacts, shellquote
from .download import Downloader, DownloadSettings
from .errors import BuildError
from .exec import Runner, path_prepend
from .fetchers import PackageVersions
from .git import GitCloner
from .logging import Logger, format_duration
from .paths import canonicalize, path_is_within, safe_remove_tree
from .state import read_marker_version, write_marker_version
from .versions import VersionResolver

# Versioned host-side build helpers. Keeping cargo-c inside the workspace avoids
# mutating the user's global Cargo installation and makes rav1e's C ABI build
# reproducible across otherwise identical runs.
CARGO_C_VERSION = "0.10.24+cargo-0.98.0"
RUST_TOOLCHAIN_VERSION = "1.95.0"

_Version = TypeVar("_Version")

_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


class BuildContext:
    """Shared state and services for one build."""

    def __init__(
        self,
        *,
        repo_root: Path,
        invocation_dir: Path,
        build_root: Path,
        logger: Logger,
        runner: Runner,
        selection: Selection,
        compiler: str,
        build_threads: int,
        latest: bool,
        nonfree_and_gpl: bool,
        script_version: str,
    ) -> None:
        self.repo_root = repo_root
        self.invocation_dir = invocation_dir
        self.cwd = build_root
        self.packages = build_root / "packages"
        self.workspace = build_root / "workspace"
        self.log_file = build_root / "build.log"
        self.logger = logger
        self.runner = runner
        self.selection = selection
        self.compiler = compiler
        self.build_threads = build_threads
        self.latest = latest
        self.nonfree_and_gpl = nonfree_and_gpl
        self.script_version = script_version

        self.configure_options: list[str] = []
        self.required_symbols: dict[str, str] = {}
        self.system_pkg_config_path = ""
        self.operating_system = ""
        self.release_version = ""
        self.release_codename = ""
        self.variable_os = ""
        self.cuda_root: Path | None = None
        self.nvidia_arch_flags = ""
        self.nvidia_gpu_present = False
        self.amd_gpu_present = False
        self.intel_gpu_present = False
        self.has_vulkan_gpu = False

        self.packages_built = 0
        self.packages_already_built = 0
        self.packages_disabled = 0
        self._package_started = 0
        self._package_in_progress = ""
        self._temporary_paths: list[Path] = []
        self._saved_flags: dict[str, str] = {}

        self.download_settings = DownloadSettings(dict(os.environ))
        self.resolver = VersionResolver(
            runner, logger, git_timeout=int(os.environ.get("GIT_OPERATION_TIMEOUT") or "120")
        )
        self.versions = PackageVersions(self.resolver)
        self.downloader = Downloader(
            runner=runner,
            logger=logger,
            packages=self.packages,
            settings=self.download_settings,
            register_temporary=self.register_temporary_path,
            unregister_temporary=self.unregister_temporary_path,
            build_root_locked=True,
        )
        self.cloner = GitCloner(
            clone_timeout=int(os.environ.get("GIT_CLONE_TIMEOUT") or "1800"),
            operation_timeout=self.resolver.git_timeout,
            runner=runner,
            logger=logger,
            packages=self.packages,
            register_temporary=self.register_temporary_path,
            unregister_temporary=self.unregister_temporary_path,
        )

    # -- environment -----------------------------------------------------

    @property
    def env(self) -> dict[str, str]:
        return self.runner.environment

    def path_prepend(self, directory: str | os.PathLike[str]) -> None:
        path_prepend(self.env, directory)

    def save_compiler_flags(self) -> None:
        self._saved_flags = {
            name: self.env.get(name, "") for name in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS")
        }

    def restore_compiler_flags(self) -> None:
        for name, value in self._saved_flags.items():
            self.env[name] = value

    def append_flag(self, name: str, addition: str) -> None:
        current = self.env.get(name, "")
        self.env[name] = f"{current} {addition}".strip()

    # -- temporary paths -------------------------------------------------

    def register_temporary_path(self, path: Path) -> None:
        """Track a path so an abort cannot strand it.

        Partial clones are the expensive case: two of the Git packages reach
        gigabytes, and a stranded one is invisible until a disk fills up.
        """
        self._temporary_paths.append(Path(path))

    def unregister_temporary_path(self, path: Path) -> None:
        """Called once a path has been published or removed deliberately."""
        target = Path(path)
        self._temporary_paths = [entry for entry in self._temporary_paths if entry != target]

    def remove_registered_temporary_paths(self) -> None:
        """Runs on the way out, so it never raises.

        Aborting here would mask whatever failure triggered the exit.
        Containment is still enforced: only paths inside the package cache or
        the workspace are removed.
        """
        for entry in self._temporary_paths:
            if not entry.exists() and not entry.is_symlink():
                continue
            if path_is_within(entry, self.packages) or path_is_within(entry, self.workspace):
                try:
                    safe_remove_tree(entry, entry.parent)
                except (BuildError, OSError):
                    pass
        self._temporary_paths = []

    # -- selection -------------------------------------------------------

    def package_enabled(self, key: str) -> bool:
        return self.selection.enabled(key)

    def package_explicitly_enabled(self, key: str) -> bool:
        return self.selection.explicitly_enabled(key)

    # -- FFmpeg configure options ----------------------------------------

    def record_required_config_symbols(self, options: Sequence[str]) -> None:
        """Register the `CONFIG_*` symbol each `--enable-X` should produce.

        After configure runs, every recorded symbol is checked in
        `ffbuild/config.mak`, so a feature FFmpeg silently dropped fails the
        build instead of shipping a quietly reduced binary.
        """
        for option in options:
            if not option.startswith("--enable-"):
                continue
            name = option[len("--enable-") :].upper().replace("-", "_")
            self.required_symbols[f"CONFIG_{name}"] = option

    def append_configure_options_if_enabled(self, key: str, *options: str) -> None:
        if not self.package_enabled(key):
            return
        self.configure_options.extend(options)
        self.record_required_config_symbols(options)

    # -- workspace probes ------------------------------------------------

    def pkgconf_available(self) -> bool:
        return self.runner.which("pkgconf") is not None

    def library_exists(self, *modules: str) -> bool:
        """True when pkg-config can satisfy every module.

        A probe never raises: these feed long boolean chains that are written
        to continue when an optional feature is unavailable.
        """
        if not modules or not self.pkgconf_available():
            return False
        return self.runner.probe(["pkgconf", "--exists", *modules])

    def header_exists(self, header: str) -> bool:
        """True when the active C toolchain can find a header.

        No hardcoded include paths: the compiler's own search path decides,
        which mirrors how FFmpeg's configure detects these libraries.
        """
        if not all(character.isalnum() or character in "_+./-" for character in header):
            return False
        compiler = self.env.get("CC", "cc")
        if self.runner.which(compiler) is None:
            return False
        return (
            self.runner.capture(
                [compiler, f"-I{self.workspace}/include", "-E", "-x", "c", "-"],
                stdin_text=f"#include <{header}>\n",
                timeout=30,
            ).returncode
            == 0
        )

    def compile_probe(self, source: str, extra_arguments: Sequence[str] = ()) -> bool:
        """Compile a fragment to test for a symbol rather than guess a version."""
        compiler = self.env.get("CC", "cc")
        if self.runner.which(compiler) is None:
            return False
        return (
            self.runner.capture(
                [compiler, *extra_arguments, "-fsyntax-only", "-x", "c", "-"],
                stdin_text=source,
                timeout=30,
            ).returncode
            == 0
        )

    def pkgconf_variable(self, module: str, variable: str) -> str:
        completed = self.runner.capture(["pkgconf", f"--variable={variable}", module])
        return completed.stdout.strip() if completed.returncode == 0 else ""

    def workspace_pkgconf_modules_ready(self, *modules: str) -> bool:
        """True when every module resolves to metadata inside the workspace.

        Some valid upstream metadata declares absolute paths but no `prefix`
        variable. In that case the resolved `.pc` file itself must live inside
        the workspace, so a system module cannot satisfy a workspace marker.
        """
        if not self.pkgconf_available():
            return False
        workspace_resolved = canonicalize(self.workspace)
        for module in modules:
            if not self.runner.probe(["pkgconf", "--exists", module]):
                return False
            prefix = self.pkgconf_variable(module, "prefix")
            if prefix:
                if canonicalize(prefix) != workspace_resolved:
                    return False
                continue
            pc_file_dir = self.pkgconf_variable(module, "pcfiledir")
            if not pc_file_dir or not path_is_within(pc_file_dir, workspace_resolved):
                return False
        return True

    def pkgconf_uses_system_default_path(self, pkgconf_binary: Path) -> bool:
        """True when the workspace pkgconf kept the host's compiled defaults.

        A pkgconf built with the workspace baked into its default search path
        would make every later probe find workspace metadata even with
        `PKG_CONFIG_PATH` unset, which hides missing host packages.
        """
        if not pkgconf_binary.is_file() or not self.system_pkg_config_path:
            return False
        environment = self.runner.child_environment()
        for name in ("PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR", "PKG_CONFIG_SYSROOT_DIR"):
            environment.pop(name, None)
        completed = Runner(self.logger, environment).capture(
            [str(pkgconf_binary), "--variable=pc_path", "pkgconf"],
            timeout=30,
        )
        if completed.returncode != 0:
            return False
        return completed.stdout.strip() == self.system_pkg_config_path

    def package_artifacts_ready(self, key: str) -> bool:
        """True when the workspace still holds what this package installed."""
        if key == "pkgconf":
            return self.pkgconf_uses_system_default_path(self.workspace / "bin/pkgconf")
        if key == "vapoursynth":
            return artifacts.vapoursynth_sdk_ready(self.workspace)
        if key == "ffmpeg":
            return os.access("/usr/local/bin/ffmpeg", os.X_OK) and os.access(
                "/usr/local/bin/ffprobe", os.X_OK
            )
        if key == "freeglut":
            return any(
                self.workspace_pkgconf_modules_ready(*alternative)
                for alternative in artifacts.FREEGLUT_MODULE_ALTERNATIVES
            )
        checker = artifacts.FILE_ARTIFACTS.get(key)
        if checker is not None:
            return checker(self.workspace)
        modules = artifacts.PKGCONF_MODULES.get(key)
        if modules is not None:
            return self.workspace_pkgconf_modules_ready(*modules)
        # Ancillary tools and system packages have no stable workspace artifact
        # contract, so their atomic version marker is the whole story.
        return True

    # -- build bookkeeping -----------------------------------------------

    def marker_path(self, key: str) -> Path:
        return self.packages / f"{key}.done"

    def fetch_version_if_enabled(
        self, key: str, fetcher: Callable[[], _Version | None]
    ) -> str | _Version | None:
        """Resolve a version only when the package is selected.

        A normal rerun intentionally reuses its recorded version instead of
        hitting dozens of upstream services; `--latest` opts into network
        discovery. Two packages transform the upstream tag before recording it
        and must have that transformation undone here.
        """
        if not self.package_enabled(key):
            return None

        if not self.latest:
            marker = self.marker_path(key)
            prior_version = read_marker_version(marker)
            if prior_version is not None:
                if key == "m4" and prior_version == "latest":
                    self.logger.warn(
                        "Replacing legacy mutable m4 marker with a versioned release marker."
                    )
                    marker.unlink(missing_ok=True)
                elif key == "vapoursynth":
                    return prior_version.removeprefix("R")
                elif key == "ffmpeg":
                    return prior_version.removeprefix("n")
                else:
                    # build() checks artifacts and invalidates consumers. A
                    # missing artifact needs repair, not an implicit upgrade.
                    return prior_version
        return fetcher()

    def git_snapshot(self, repository_url: str, key: str, mode: str = "shallow") -> str | None:
        """Resolve the commit to build for a Git-tracked package.

        Historical releases recorded human labels for mutable snapshots, so
        only a commit-shaped marker is trustworthy enough to reuse.
        """
        if not self.package_enabled(key):
            return None
        marker = self.marker_path(key)
        prior_version = read_marker_version(marker)
        source_directory = self.packages / key

        if (
            prior_version
            and len(prior_version) >= 12
            and all(character in "0123456789abcdefABCDEF" for character in prior_version)
        ):
            if self.latest:
                remote_commit = self.resolver.remote_head_commit(repository_url)
                if remote_commit is None:
                    raise BuildError(f"Unable to resolve the remote HEAD for '{key}'.")
                if (
                    remote_commit.startswith(prior_version)
                    and self.cloner.local_head(source_directory) == remote_commit
                ):
                    # build() decides whether installed artifacts need repair;
                    # a matching source checkout does not need another clone.
                    return remote_commit
            else:
                source_commit = self.cloner.local_head(source_directory)
                if source_commit and source_commit.startswith(prior_version):
                    return prior_version
                raise BuildError(
                    f"Git marker for '{key}' records '{prior_version}', but its matching "
                    f"source checkout is unavailable at '{source_directory}'. Restore that "
                    "checkout to repair the pinned build, or use '--latest' to refresh it."
                )
        elif prior_version:
            self.logger.warn(f"Replacing legacy non-commit marker for Git snapshot '{key}'.")
            marker.unlink(missing_ok=True)

        commit = self.cloner.clone(repository_url, key, mode)
        if commit is None:
            raise BuildError(
                f"Unable to obtain a Git snapshot for '{key}' from '{repository_url}'."
            )
        return commit

    def build(self, key: str, version: str | None) -> bool:
        """Decide whether this package's recipe should run.

        Disabled packages are checked first so callers can skip version
        detection entirely for them without tripping the empty-version guard.
        """
        if key not in registry.PACKAGES:
            raise BuildError(f"build() received unsupported package '{key}'.")
        if not self.package_enabled(key):
            # A filtered config disables dozens of packages. Announcing each one
            # at INFO buried the packages that were actually building, so the
            # detail is debug-only and the run-end summary reports the count.
            self.packages_disabled += 1
            if self.selection.config_file is not None:
                self.logger.debug(f"{key} is disabled by config '{self.selection.config_file}'.")
            else:
                self.logger.debug(f"{key} is disabled by config.")
            return False

        # An empty version leads to broken URLs like `foo-.tar.gz` and confusing
        # rebuild logic, so it is a hard error rather than a silent wrong build.
        if version is None:
            raise BuildError(
                f"Unable to resolve an upstream version for enabled package '{key}'. "
                "Check the lookup warnings above and retry."
            )
        if not is_valid_version(version):
            raise BuildError(f"build() called for \"{key}\" with an invalid version '{version}'.")

        marker = self.marker_path(key)
        prior_version = read_marker_version(marker)
        if prior_version is not None:
            if not self.package_artifacts_ready(key):
                self.logger.warn(
                    f"{key} has a build marker but its workspace artifacts are missing; rebuilding."
                )
                marker.unlink(missing_ok=True)
                self._start_package_build(key, version)
                return True
            if prior_version == version:
                self.packages_already_built += 1
                self.logger.skip(f"{key} {version} is already built.")
                self.logger.debug(
                    "Force a rebuild with: " + shellquote.join(["rm", "-f", "--", str(marker)])
                )
                return False
            if self.latest:
                self._start_package_build(key, version, prior_version)
                return True
            self.packages_already_built += 1
            self.logger.skip(
                f"{key} {prior_version} -> {version} is outdated; keeping the existing build."
            )
            self.logger.debug(
                "Rebuild with '--latest', or: " + shellquote.join(["rm", "-f", "--", str(marker)])
            )
            return False

        self._start_package_build(key, version)
        return True

    def _start_package_build(self, key: str, version: str, prior_version: str = "") -> None:
        """Announce the package and start its clock.

        Split out because three branches of `build` reach this point and the
        counter must advance exactly once per package that actually builds.
        """
        # Recipes install in place. Invalidate before any write, including on
        # --latest: a failed upgrade may leave new artifacts beside old ones.
        # Consumers must also rebuild when a dependency's static archive changes.
        invalidated = {key, "ffmpeg"}
        while True:
            consumers = {
                rule.package for rule in registry.REQUIREMENTS if rule.needs in invalidated
            }
            expanded = invalidated | consumers
            if expanded == invalidated:
                break
            invalidated = expanded
        for package in sorted(invalidated):
            self.marker_path(package).unlink(missing_ok=True)
        self.packages_built += 1
        self._package_started = self.logger.elapsed_seconds
        self._package_in_progress = key
        print()
        if prior_version:
            self.logger.step(f"{key} {version} (replacing {prior_version})")
        else:
            self.logger.step(f"{key} {version}")

    def build_done(self, key: str, version: str | None) -> None:
        """Publish the marker, but only once the artifact is actually there."""
        if key not in registry.PACKAGES:
            raise BuildError(f"build_done() received unsupported package '{key}'.")
        if version is None or not is_valid_version(version):
            raise BuildError(f"build_done() received an invalid version for '{key}'.")
        if not self.package_artifacts_ready(key):
            raise BuildError(
                f"Refusing to mark '{key}' complete because its required artifacts are missing."
            )
        self.packages.mkdir(parents=True, exist_ok=True)
        write_marker_version(self.marker_path(key), version)

        # Only time packages this run actually started. A recipe that finishes
        # outside a `build` branch would otherwise report the elapsed time of
        # whichever package ran before it.
        if self._package_in_progress == key:
            duration = format_duration(self.logger.elapsed_seconds - self._package_started)
            self.logger.ok(f"{key} {version} in {duration}")
            self._package_in_progress = ""
        else:
            self.logger.ok(f"{key} {version}")

    # -- convenience -----------------------------------------------------

    def execute(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        stdin_text: str | None = None,
    ) -> None:
        self.runner.execute(arguments, cwd=cwd, env_overrides=env_overrides, stdin_text=stdin_text)

    def make(self, cwd: Path, *targets: str, jobs: bool = True, **variables: str) -> None:
        arguments = ["make"]
        if jobs:
            arguments.append(f"-j{self.build_threads}")
        arguments.extend(f"{name}={value}" for name, value in variables.items())
        arguments.extend(targets)
        self.execute(arguments, cwd=cwd)

    def download(self, url: str, filename: str | None = None) -> Path:
        return self.downloader.download(url, filename)

    def cleanup_command(self) -> str:
        return CLEANUP_COMMAND


def is_valid_version(version: str) -> bool:
    """Match the marker grammar: a leading alphanumeric, then `A-Za-z0-9._+-`."""
    return bool(_VERSION_PATTERN.fullmatch(version))
