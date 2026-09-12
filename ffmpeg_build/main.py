"""The orchestrator: validate the request, prepare the build root, run stages."""

from __future__ import annotations

import os
import re
import signal
import sys
import tempfile
from pathlib import Path
from types import FrameType

from . import registry
from .cli import (
    SCRIPT_NAME,
    SCRIPT_VERSION,
    Arguments,
    parse_arguments,
    requested_metadata,
    resolve_config_path,
    usage_text,
)
from .config import CLEANUP_COMMAND, BuildSettings, Selection, load_config
from .runtime.context import CARGO_C_VERSION, RUST_TOOLCHAIN_VERSION, BuildContext
from .runtime.errors import BuildError, UsageError
from .runtime.exec import Runner, base_environment, notify_failure
from .runtime.logging import Logger
from .runtime.paths import DirectoryLock, canonicalize, is_exclusive_regular_file
from .runtime.state import (
    BUILD_CONTEXT_NAME,
    BUILD_ROOT_MARKER_NAME,
    ContextMismatch,
    assert_safe_build_root,
    build_root_is_adoptable,
    build_root_marker_matches,
    legacy_build_root_marker,
    migratable_added_packages,
    parse_build_context,
    render_build_context,
    summarize_build_context_changes,
    write_build_root_marker,
)
from .stages.ffmpeg_build import FFmpegStage, report_success
from .stages.hardware import HardwareDetection
from .stages.system_setup import SystemSetup

_POSITIVE_INTEGER_SETTINGS = (
    "DOWNLOAD_CONNECT_TIMEOUT",
    "DOWNLOAD_MAX_TIME",
    "DOWNLOAD_MAX_BYTES",
    "DOWNLOAD_LOCK_TIMEOUT",
    "HOST_MUTATION_LOCK_TIMEOUT",
    "VERSION_CHECK_MAX_TIME",
    "GIT_OPERATION_TIMEOUT",
    "GIT_CLONE_TIMEOUT",
    "FREEDESKTOP_RELEASE_CONNECT_TIMEOUT",
    "FREEDESKTOP_RELEASE_INDEX_MAX_TIME",
)
_NON_NEGATIVE_INTEGER_SETTINGS = ("DOWNLOAD_RETRY", "DOWNLOAD_RETRY_DELAY")


class SignalStop(BaseException):
    """A termination signal, carrying the exit status it should produce."""

    def __init__(self, name: str, exit_code: int) -> None:
        super().__init__(name)
        self.name = name
        self.exit_code = exit_code


def validate_build_settings(selection: Selection, debug_value: str) -> None:
    """Check everything derivable from the request alone.

    These run before the first host mutation, so an unsatisfiable build fails
    without having installed packages or asked for a password first. A typo in
    `CUDA_ARCH_MODE` has to be caught here rather than inside the CUDA stage,
    which runs after dozens of APT packages are already installed.
    """
    issues: list[str] = []

    # Checked here rather than during argument parsing, which runs on every
    # invocation: a log-verbosity setting must not abort a run that logs
    # nothing, such as the documented "with no action, print help".
    if debug_value not in ("ON", "OFF"):
        issues.append(f"'FFMPEG_BUILD_DEBUG' must be 'ON' or 'OFF'; got '{debug_value}'")

    cuda_install = os.environ.get("CUDA_INSTALL", "ask")
    if cuda_install not in ("ask", "always", "never"):
        issues.append(f"'CUDA_INSTALL' must be 'ask', 'always', or 'never'; got '{cuda_install}'")

    mode = os.environ.get("CUDA_ARCH_MODE", "native")
    if mode == "custom":
        values = os.environ.get("CUDA_ARCHITECTURES", "").split()
        if not values:
            issues.append(
                "'CUDA_ARCH_MODE=custom' requires 'CUDA_ARCHITECTURES' (for example: '86 89')"
            )
        for value in values:
            if not value.isdigit():
                issues.append(f"'CUDA_ARCHITECTURES' entry '{value}' is not a number")
    elif mode not in ("native", "all"):
        issues.append(f"'CUDA_ARCH_MODE' must be 'native', 'all', or 'custom'; got '{mode}'")

    # Garbage in an unchecked timeout reaches curl, where it becomes a usage
    # error the fetchers report as "failed to detect version", naming the wrong
    # subsystem entirely.
    for name in _POSITIVE_INTEGER_SETTINGS:
        value = os.environ.get(name, "")
        if value and not re.match(r"^[1-9][0-9]*$", value):
            issues.append(f"'{name}' must be a positive integer; got '{value}'")
    for name in _NON_NEGATIVE_INTEGER_SETTINGS:
        value = os.environ.get(name, "")
        if value and not value.isdigit():
            issues.append(f"'{name}' must be a non-negative integer; got '{value}'")

    for rule in registry.SETTINGS_REQUIREMENTS:
        if selection.enabled(rule.package) and not selection.enabled(rule.needs):
            issues.append(rule.message())

    if issues:
        listed = "\n - ".join(issues)
        raise UsageError(f"Build settings have unresolved problems:\n - {listed}\n")


def validate_package_selection(context: BuildContext) -> None:
    """Cross-package rules that need to probe the host.

    These can only run once the host packages are installed, because a rule is
    satisfied either by the source build or by a system development package.
    """
    issues: list[str] = []
    gpl_openssl = context.nonfree_and_gpl and context.package_enabled("openssl")

    for rule in registry.SELECTION_REQUIREMENTS:
        if rule.condition == "gpl-openssl" and not gpl_openssl:
            continue
        if rule.condition == "not-gpl-openssl" and gpl_openssl:
            continue
        if rule.condition == "gpl" and not context.nonfree_and_gpl:
            continue
        if not context.package_enabled(rule.package):
            continue
        if context.package_enabled(rule.needs):
            continue
        if rule.pkgconf_module and context.library_exists(rule.pkgconf_module):
            continue
        issues.append(rule.message())

    if (
        context.nonfree_and_gpl
        and context.package_enabled("x264")
        and context.runner.which("yasm") is None
        and context.runner.which("nasm") is None
    ):
        issues.append("'packages.x264=true' requires 'yasm' or 'nasm' to be available")

    if issues:
        listed = "\n - ".join(issues)
        raise BuildError(f"Package selection has unresolved dependencies:\n - {listed}\n")


class Orchestrator:
    def __init__(self, repo_root: Path, argv: list[str]) -> None:
        self.repo_root = repo_root
        self.argv = argv
        self.invocation_dir = Path.cwd()
        self.debug_value = os.environ.get("FFMPEG_BUILD_DEBUG", "OFF")
        self.logger = Logger(debug=self.debug_value == "ON")
        self.runner = Runner(self.logger, base_environment(), debug=self.debug_value == "ON")
        self.build_root = Path()
        self.context: BuildContext | None = None
        self._lock: DirectoryLock | None = None

    # -- setup -----------------------------------------------------------

    def resolve_build_root(self) -> None:
        requested = os.environ.get("BUILD_ROOT") or str(self.repo_root / "build")
        if not requested.startswith("/"):
            requested = str(self.invocation_dir / requested)
        self.build_root = canonicalize(requested)

    def validate_build_root(self) -> None:
        root = self.build_root
        assert_safe_build_root(root, self.repo_root)
        if root.exists() and not root.is_dir():
            raise BuildError(f"'BUILD_ROOT' exists but is not a directory: '{root}'.")
        if not root.is_dir():
            return
        if not os.access(root, os.R_OK | os.X_OK):
            raise BuildError(
                f"'BUILD_ROOT' cannot be inspected safely by the current user: '{root}'."
            )
        try:
            occupied = any(root.iterdir())
        except OSError as error:
            raise BuildError(f"Unable to inspect existing 'BUILD_ROOT' '{root}'.") from error
        if not occupied:
            return
        if build_root_marker_matches(root / BUILD_ROOT_MARKER_NAME, root):
            return
        if legacy_build_root_marker(root / BUILD_ROOT_MARKER_NAME):
            self.logger.warn(
                f"'BUILD_ROOT' '{root}' uses a legacy empty marker; this build will upgrade "
                "it to a path-bound marker."
            )
            return
        if build_root_is_adoptable(root):
            self.logger.warn(
                f"'{root}' holds only this project's empty scaffolding from an interrupted "
                "run; adopting it."
            )
            return
        raise BuildError(
            f"'BUILD_ROOT' '{root}' already contains data and lacks a valid path-bound "
            "FFmpeg build-root marker."
        )

    def initialize_build_root(self) -> None:
        root = self.build_root
        packages = root / "packages"
        workspace = root / "workspace"
        log_file = root / "build.log"
        self.validate_build_root()

        # The build root is created empty first and nothing is put inside it
        # until its marker exists: an interrupt here leaves an empty directory
        # the next run accepts, rather than a populated unmarked one that
        # neither --build nor --cleanup would touch again.
        if not root.is_dir():
            try:
                root.mkdir(parents=True)
            except OSError as error:
                raise BuildError(f"Unable to create the build root '{root}'.") from error

        # Deliberately no `sudo mkdir`/`sudo chown` fallback. Escalating here
        # would let a build root the invoking user does not own be taken over,
        # marked as ours, and so become a legitimate --cleanup target. The
        # marker means "this project created it", not "this project annexed it".
        if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            raise BuildError(
                f"Build root '{root}' is not writable by the current user. Choose a different "
                "'BUILD_ROOT' or grant ownership yourself; this script will not take it with "
                "'sudo'."
            )

        self._lock = DirectoryLock(root)
        if not self._lock.acquire():
            self._lock = None
            raise BuildError(f"Another process is already using build root '{root}'.")

        self._lock.assert_current()
        self.validate_build_root()
        for managed in (
            packages,
            workspace,
            log_file,
            root / BUILD_ROOT_MARKER_NAME,
            root / BUILD_CONTEXT_NAME,
        ):
            if managed.is_symlink():
                raise BuildError(f"Refusing symlink at managed build path '{managed}'.")

        if log_file.exists() and not log_file.is_file():
            raise BuildError(f"Build log path is not a regular file: '{log_file}'.")
        marker = root / BUILD_ROOT_MARKER_NAME
        if marker.exists() and not marker.is_file():
            raise BuildError("Build-root marker is not a regular file.")
        for managed in (log_file, marker, root / BUILD_CONTEXT_NAME):
            if managed.exists() and not is_exclusive_regular_file(managed):
                raise BuildError(f"Refusing multiply-linked managed file '{managed}'.")

        write_build_root_marker(root)
        packages.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)
        log_file.touch(exist_ok=True)

    def configure_toolchain(self, context: BuildContext) -> None:
        environment = context.env
        if context.compiler == "gcc":
            environment["CC"], environment["CXX"] = "gcc", "g++"
        else:
            environment["CC"], environment["CXX"] = "clang", "clang++"
        environment["MAKEFLAGS"] = f"-j{context.build_threads}"
        environment["ACLOCAL_PATH"] = ":".join(
            [
                f"{context.workspace}/share/aclocal",
                "/usr/local/share/aclocal",
                "/usr/share/aclocal",
            ]
        )

    def source_compiler_flags(self, context: BuildContext) -> None:
        environment = context.env
        cflags = environment.get("CFLAGS") or "-O2 -pipe -march=native"
        if "-fPIC" not in cflags:
            cflags += " -fPIC"
        cxxflags = environment.get("CXXFLAGS") or cflags
        if "-fPIC" not in cxxflags:
            cxxflags += " -fPIC"
        existing_cppflags = environment.get("CPPFLAGS", "")
        cppflags = f"-I{context.workspace}/include"
        if existing_cppflags:
            cppflags += f" {existing_cppflags}"
        existing_ldflags = environment.get("LDFLAGS", "")
        ldflags = f"-L{context.workspace}/lib64 -L{context.workspace}/lib"
        if existing_ldflags:
            ldflags += f" {existing_ldflags}"
        ldflags += " -Wl,-O1,--as-needed,-z,relro,-z,now -pthread"
        environment.update(
            {"CFLAGS": cflags, "CXXFLAGS": cxxflags, "CPPFLAGS": cppflags, "LDFLAGS": ldflags}
        )

    # -- build context ---------------------------------------------------

    def current_build_context(self, context: BuildContext) -> str:
        environment = context.env
        return render_build_context(
            {
                "script_version": SCRIPT_VERSION,
                "compiler": context.compiler,
                "gpl_and_non_free": "true" if context.nonfree_and_gpl else "false",
                "rust_toolchain": RUST_TOOLCHAIN_VERSION,
                "cargo_c": CARGO_C_VERSION,
                "cflags": environment.get("CFLAGS", ""),
                "cxxflags": environment.get("CXXFLAGS", ""),
                "cppflags": environment.get("CPPFLAGS", ""),
                "ldflags": environment.get("LDFLAGS", ""),
                "cuda_arch_mode": os.environ.get("CUDA_ARCH_MODE", "native"),
                "cuda_architectures": os.environ.get("CUDA_ARCHITECTURES", ""),
                "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", ""),
            },
            context.selection.states(),
        )

    def ensure_build_context(self, context: BuildContext) -> None:
        context_file = context.cwd / BUILD_CONTEXT_NAME
        if context_file.is_symlink():
            raise BuildError(f"Refusing symlink build-context file '{context_file}'.")
        if context_file.exists():
            if not context_file.is_file():
                raise BuildError(f"Build-context path is not a regular file: '{context_file}'.")
            if not is_exclusive_regular_file(context_file):
                raise BuildError(f"Refusing multiply-linked build-context file '{context_file}'.")

        current = self.current_build_context(context)
        if not context_file.is_file():
            prior_marker = next(context.packages.glob("*.done"), None)
            if prior_marker is not None:
                raise BuildError(
                    "This legacy workspace has package markers but no build-context record. "
                    f"Run '{CLEANUP_COMMAND}' before rebuilding."
                )
            self._publish_context(context_file, current)
            return

        previous = context_file.read_text(encoding="utf-8", errors="replace")
        if previous == current:
            return

        try:
            added_packages = migratable_added_packages(previous, current, SCRIPT_VERSION)
        except ContextMismatch:
            changes = summarize_build_context_changes(previous, current)
            # Every recorded line is compared, so an empty summary means the
            # records differ in a way this cannot attribute. Say that rather
            # than blaming settings the reader may not have touched.
            if not changes:
                raise BuildError(
                    "This workspace's build-context record differs from the current one in a "
                    "way that cannot be attributed to a specific setting. Run "
                    f"'{CLEANUP_COMMAND}' before rebuilding."
                ) from None
            listed = "\n".join(f" - {change}" for change in changes)
            raise BuildError(
                f"This workspace was built with different settings:\n{listed}\n"
                f"Run '{CLEANUP_COMMAND}' before rebuilding."
            ) from None

        self._adopt_context(context, context_file, current, previous, added_packages)

    def _publish_context(self, context_file: Path, payload: str) -> None:
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{BUILD_CONTEXT_NAME}.", dir=context_file.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.chmod(temporary, 0o600)
            os.replace(temporary, context_file)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise BuildError(f"Unable to publish build-context file '{context_file}'.") from error

    def _adopt_context(
        self,
        context: BuildContext,
        context_file: Path,
        current: str,
        previous: str,
        added_packages: list[str],
    ) -> None:
        """Upgrade the record and, when the registry grew, relink FFmpeg.

        A newly enabled package contributes a `--enable-*` option that FFmpeg
        only picks up by configuring again; without this the workspace would
        build the new dependency and link an FFmpeg that ignores it.
        """
        previous_fields = parse_build_context(previous)
        reconfigure = previous_fields.get("script_version") != SCRIPT_VERSION
        for package_name in added_packages:
            if context.package_enabled(package_name):
                reconfigure = True

        # Invalidate before publishing: an interruption between these writes
        # must never leave a new context paired with an old, reusable marker.
        ffmpeg_marker = context.marker_path("ffmpeg")
        if reconfigure and context.package_enabled("ffmpeg") and ffmpeg_marker.is_file():
            try:
                ffmpeg_marker.unlink()
            except OSError as error:
                raise BuildError(
                    "Unable to clear the FFmpeg build marker for a reconfigure."
                ) from error

        self._publish_context(context_file, current)
        self.logger.info("Adopted this workspace: existing dependency builds remain valid.")
        self.logger.debug(f"Upgraded '{context_file}' to the current build-context format.")
        if added_packages:
            self.logger.info(
                "Newly available since that workspace was created: " + ", ".join(added_packages)
            )
        if reconfigure and context.package_enabled("ffmpeg"):
            self.logger.info(
                "FFmpeg will be reconfigured and relinked for the updated build integration."
            )

    # -- actions ---------------------------------------------------------

    def cleanup(self) -> None:
        root = self.build_root
        if not root.exists():
            self.logger.info(f"Build root does not exist; nothing to clean: '{root}'.")
            return
        resolved = canonicalize(root)
        repository = canonicalize(self.repo_root)
        assert_safe_build_root(resolved, repository)

        # A build already holds this directory lock through all stages. Opening
        # another descriptor here would contend with our own lock on success.
        lock = self._lock if self._lock is not None and self._lock.held else DirectoryLock(resolved)
        owns_lock = lock is not self._lock
        if not lock.acquire():
            raise BuildError(f"Another process is already using build root '{resolved}'.")
        try:
            lock.assert_current()
            # Verify ownership while holding the directory lock.
            if build_root_marker_matches(resolved / BUILD_ROOT_MARKER_NAME, resolved):
                pass
            elif resolved == repository / "build" and legacy_build_root_marker(
                resolved / BUILD_ROOT_MARKER_NAME
            ):
                self.logger.warn("Recognized legacy marker in the default build directory.")
            elif build_root_is_adoptable(resolved):
                self.logger.warn(
                    f"'{resolved}' holds only this project's empty scaffolding from an interrupted "
                    "run; cleaning it up."
                )
            else:
                raise BuildError(
                    f"Refusing to clean a build root without a valid path-bound marker: '{resolved}'"
                )

            if not sys.stdin.isatty():
                self.logger.info(
                    f"Standard input is not interactive; leaving build files in place at "
                    f"'{resolved}'."
                )
                return
            while True:
                print()
                try:
                    choice = input(f"Remove all build files under '{resolved}'? (yes/no): ")
                except EOFError:
                    print()
                    self.logger.info("No cleanup response received; leaving build files in place.")
                    return
                if choice.strip().lower() in ("y", "yes"):
                    from .runtime.paths import remove_tree_one_filesystem

                    try:
                        lock.assert_current()
                        remove_tree_one_filesystem(resolved)
                    except OSError as error:
                        raise BuildError(f"Failed to remove build root '{resolved}'.") from error
                    lock.release()
                    if self.logger.log_file is not None:
                        self.logger.log_file = None
                    self.runner.log_file = None
                    self.logger.info(f"Removed build root: '{resolved}'.")
                    return
                if choice.strip().lower() in ("n", "no"):
                    return
                self.logger.warn("Invalid input. Please enter 'yes' or 'no'.")
        finally:
            if owns_lock:
                lock.release()

    def run_build(self, context: BuildContext) -> None:
        machine = os.uname().machine
        if machine != "x86_64":
            raise BuildError(f"This build currently supports 'x86_64' only; detected '{machine}'.")
        os.umask(0o022)
        # Everything checkable from the request alone is checked before the
        # first host mutation, so an unsatisfiable build fails without having
        # installed packages or prompted for sudo first.
        validate_build_settings(context.selection, self.debug_value)

        self.initialize_build_root()
        self.configure_toolchain(context)
        # Before the context check: the record has to hold the flags the build
        # actually uses. Snapshotting the inherited environment meant a change
        # in the computed defaults, such as reusing a workspace on a different
        # CPU with -march=native, went undetected.
        self.source_compiler_flags(context)
        self.ensure_build_context(context)
        # Last of the pure checks, so this is the first point where a password
        # is worth asking for. Everything above either validates the request or
        # writes inside a build root the user already owns.
        self.runner.require_sudo()
        # After the context check, so a failing run's log survives the abort.
        context.log_file.write_text("", encoding="utf-8")
        self.logger.log_file = context.log_file
        self.runner.log_file = context.log_file

        print()
        self.logger.banner(f"FFmpeg Build Script {SCRIPT_VERSION}")
        print()
        self.logger.info(f"Build root: '{context.cwd}'.")
        self.logger.info(f"Parallel jobs: '{context.build_threads}'.")
        self.logger.info(f"Compiler family: '{context.compiler}'.")
        if context.nonfree_and_gpl:
            self.logger.warn("GPL and non-free components are enabled.")

        setup = SystemSetup(context)
        with self.host_mutation_lock():
            setup.run()
        validate_package_selection(context)

        hardware = HardwareDetection(context, setup)
        hardware.run()
        with self.host_mutation_lock():
            hardware.install_cuda()

        from .stages.audio_libraries import install_audio_libraries
        from .stages.core_libraries import install_core_libraries
        from .stages.global_tools import install_global_tools
        from .stages.image_libraries import install_image_libraries
        from .stages.support_libraries import install_support_libraries
        from .stages.video_libraries import install_video_libraries

        install_global_tools(context)
        install_core_libraries(context)
        install_support_libraries(context)
        install_audio_libraries(context)
        install_video_libraries(context)
        install_image_libraries(context)
        FFmpegStage(context, hardware).run()

        self.cleanup()
        report_success(context)

    def host_mutation_lock(self) -> DirectoryLock:
        """Serialize the host-mutating sections across every run by this user.

        The build-root lock is per build root, so two builds with different
        roots both pass it and then collide on dpkg's own lock, where the
        failure surfaces only as a generic command error. The lock lives in the
        per-user runtime directory rather than /tmp, which is world-writable
        and would let anyone pre-create the path.
        """
        lock_dir = (
            Path(os.environ.get("XDG_RUNTIME_DIR") or f"{os.environ.get('HOME', '/tmp')}/.cache")
            / "ffmpeg-build-script"
        )
        try:
            lock_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise BuildError(f"Unable to create the host-mutation lock in '{lock_dir}'.") from error
        lock = DirectoryLock(lock_dir)
        timeout = int(os.environ.get("HOST_MUTATION_LOCK_TIMEOUT", "3600"))
        if not lock.acquire(timeout=timeout):
            raise BuildError("Timed out waiting for the host-mutation lock; no host changes made.")
        return lock

    # -- entry point -----------------------------------------------------

    def build_context(
        self, arguments: Arguments, settings: BuildSettings, selection: Selection
    ) -> BuildContext:
        # The affinity mask, not the CPU count: under `taskset -c 0,1` a host
        # with 24 cores must launch 2 compile jobs, not 24.
        threads = arguments.jobs or len(os.sched_getaffinity(0))
        context = BuildContext(
            repo_root=self.repo_root,
            invocation_dir=self.invocation_dir,
            build_root=self.build_root,
            logger=self.logger,
            runner=self.runner,
            selection=selection,
            compiler=arguments.compiler,
            build_threads=threads,
            latest=arguments.latest or settings.latest,
            nonfree_and_gpl=arguments.nonfree_and_gpl or settings.enable_gpl_and_non_free,
            script_version=SCRIPT_VERSION,
        )
        if context.nonfree_and_gpl:
            context.configure_options.extend(["--enable-gpl", "--enable-nonfree"])
        self.context = context
        return context

    def run(self) -> int:
        metadata = requested_metadata(self.argv)
        if metadata is not None:
            sys.stdout.write(metadata)
            return 0

        # Checked here, not inside run_build: --cleanup is dispatched without
        # ever reaching it, and it is the one destructive action in the project.
        if os.geteuid() == 0:
            self.logger.error(
                f"Run '{SCRIPT_NAME}' as a normal user; it invokes 'sudo' only for system changes."
            )
            return 1

        arguments = parse_arguments(self.argv)
        settings = BuildSettings()
        selection = Selection()
        if arguments.config_path is not None:
            config_file = resolve_config_path(arguments.config_path, self.invocation_dir)
            loaded = load_config(config_file, self.logger)
            settings, selection = loaded.settings, loaded.selection

        self.resolve_build_root()

        if arguments.cleanup:
            self.cleanup()
            return 0
        if arguments.menu:
            return self.run_menu(arguments, settings, selection)
        if not arguments.build:
            sys.stdout.write(usage_text())
            return 0

        validate_build_settings(selection, self.debug_value)
        context = self.build_context(arguments, settings, selection)
        self.run_build(context)
        return 0

    def run_menu(self, arguments: Arguments, settings: BuildSettings, selection: Selection) -> int:
        """Edit the selection, then build exactly what was saved.

        The build reads the saved file back through the normal configuration
        path rather than using the in-memory state, so the run that happens is
        the one the file on disk describes.
        """
        from .menu.app import run_menu
        from .menu.model import LaunchSettings

        states = selection.states() if selection.has_config else None
        default_path = (
            selection.config_file
            if selection.config_file is not None
            else self.invocation_dir / "custom.toml"
        )
        try:
            settings.latest = settings.latest or arguments.latest
            settings.enable_gpl_and_non_free = (
                settings.enable_gpl_and_non_free or arguments.nonfree_and_gpl
            )
            launch = LaunchSettings(
                compiler=arguments.compiler,
                jobs=str(arguments.jobs) if arguments.jobs else "",
                build_root=str(self.build_root),
                cuda_install=os.environ.get("CUDA_INSTALL", "ask"),
                cuda_arch_mode=os.environ.get("CUDA_ARCH_MODE", "native"),
                cuda_architectures=os.environ.get("CUDA_ARCHITECTURES", ""),
            )
            result = run_menu(states, settings, default_path, launch)
        except RuntimeError as error:
            raise UsageError(str(error)) from error
        if not result.start_build or result.saved_path is None:
            return 0

        loaded = load_config(result.saved_path, self.logger)
        result.launch.validate()
        arguments.compiler = result.launch.compiler
        arguments.jobs = int(result.launch.jobs) if result.launch.jobs else None
        # The editor's final choices supersede the CLI values it was seeded with.
        arguments.latest = False
        arguments.nonfree_and_gpl = False
        os.environ.update(
            {
                "BUILD_ROOT": result.launch.build_root,
                "CUDA_INSTALL": result.launch.cuda_install,
                "CUDA_ARCH_MODE": result.launch.cuda_arch_mode,
                "CUDA_ARCHITECTURES": result.launch.cuda_architectures,
            }
        )
        self.resolve_build_root()
        validate_build_settings(loaded.selection, self.debug_value)
        context = self.build_context(arguments, loaded.settings, loaded.selection)
        self.run_build(context)
        return 0

    def teardown(self) -> None:
        self.runner.stop_sudo_keepalive()
        if self.context is not None:
            self.context.remove_registered_temporary_paths()
        if self._lock is not None:
            self._lock.release()
            self._lock = None


def _install_signal_handlers() -> None:
    def handler(signal_number: int, _frame: FrameType | None) -> None:
        name = signal.Signals(signal_number).name.removeprefix("SIG")
        raise SignalStop(name, {"HUP": 129, "INT": 130, "TERM": 143}.get(name, 1))

    for signal_name in ("SIGHUP", "SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, signal_name), handler)


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    orchestrator = Orchestrator(repo_root, argv)
    _install_signal_handlers()
    try:
        return orchestrator.run()
    except SignalStop as stop:
        orchestrator.logger.warn(
            f"Received '{stop.name}'; stopping after preserving build files in "
            f"'{orchestrator.build_root}'."
        )
        return stop.exit_code
    except UsageError as error:
        orchestrator.logger.error(str(error))
        return 1
    except BuildError as error:
        _report_failure(orchestrator, error)
        return 1
    finally:
        orchestrator.teardown()


def _report_failure(orchestrator: Orchestrator, error: BuildError) -> None:
    """Report a fatal failure as one record.

    The location and the bug-report pointer belong under the message rather
    than arriving as three separately tagged lines that read like three
    separate failures.
    """
    from .runtime.errors import ISSUE_TRACKER_URL

    detail = [str(error)]
    traceback = error.__traceback__
    frames = []
    while traceback is not None:
        frames.append(traceback)
        traceback = traceback.tb_next
    if frames:
        raise_frame = frames[-1]
        origin = f"{Path(raise_frame.tb_frame.f_code.co_filename).name}:{raise_frame.tb_lineno}"
        if len(frames) > 1:
            caller = frames[-2]
            caller_name = Path(caller.tb_frame.f_code.co_filename).name
            detail.append(f"Raised from: {caller_name}:{caller.tb_lineno} (check at {origin})")
        else:
            detail.append(f"Raised from: {origin}")
    context = orchestrator.context
    if context is not None and context.log_file.is_file():
        detail.append(f"Build log: {context.log_file}")
    detail.append(f"Report a bug: {ISSUE_TRACKER_URL}")

    print(file=sys.stderr)
    orchestrator.logger.error("\n".join(detail))
    print(file=sys.stderr)
    notify_failure(str(error))
