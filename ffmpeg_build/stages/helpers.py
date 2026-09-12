"""Recipe helpers shared by the library stages."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from ..runtime.buildsys import CMAKE_NO_PACKAGE_REGISTRY_OPTIONS
from ..runtime.context import CARGO_C_VERSION, RUST_TOOLCHAIN_VERSION, BuildContext
from ..runtime.errors import BuildError

_PC_NAME = re.compile(r"^[A-Za-z0-9_.+-]+$")
_LINKER_FLAG = re.compile(r"^-l[A-Za-z0-9_+.-]+$")


def ensure_autotools(context: BuildContext, source: Path) -> None:
    """Produce a `configure` without running `autoupdate`.

    `autoupdate` rewrites upstream build files, so a shipped `configure` is
    preferred and one is generated only when none exists.
    """
    if (source / "configure").is_file():
        return
    if (source / "autogen.sh").is_file():
        context.execute(["sh", "autogen.sh"], cwd=source)
        return
    context.execute(["autoreconf", "-fi"], cwd=source)


def configure_make_install(
    context: BuildContext,
    source: Path,
    *options: str,
    prefix: bool = True,
    install_target: str = "install",
    env_overrides: dict[str, str] | None = None,
) -> None:
    arguments = ["sh", "configure"]
    if prefix:
        arguments.append(f"--prefix={context.workspace}")
    arguments.extend(options)
    context.execute(arguments, cwd=source, env_overrides=env_overrides)
    context.make(source)
    context.make(source, install_target, jobs=False)


def cmake_ninja_install(context: BuildContext, source: Path, build_dir: str, *options: str) -> None:
    context.execute(
        [
            "cmake",
            *options,
            "-B",
            build_dir,
            f"-DCMAKE_INSTALL_PREFIX={context.workspace}",
            "-DCMAKE_BUILD_TYPE=Release",
            *CMAKE_NO_PACKAGE_REGISTRY_OPTIONS,
            "-G",
            "Ninja",
            "-Wno-dev",
        ],
        cwd=source,
    )
    context.execute(["ninja", f"-j{context.build_threads}", "-C", build_dir], cwd=source)
    context.execute(["ninja", "-C", build_dir, "install"], cwd=source)


def meson_ninja_install(context: BuildContext, source: Path, build_dir: str, *options: str) -> None:
    context.execute(
        [
            "meson",
            "setup",
            build_dir,
            f"--prefix={context.workspace}",
            "--wrap-mode=nofallback",
            *options,
        ],
        cwd=source,
    )
    context.execute(["ninja", f"-j{context.build_threads}", "-C", build_dir], cwd=source)
    context.execute(["ninja", "-C", build_dir, "install"], cwd=source)


def pkgconfig_add_private_lib(context: BuildContext, pc_name: str, extra_lib: str) -> None:
    """Declare a runtime the generated `.pc` omits. Idempotent.

    Several libraries bundle C++ sources but ship metadata that names no C++
    runtime, which breaks a static link through the C compiler driver with
    undefined `operator new`/`delete`. This states the dependency the way
    x265, zimg and rubberband already do, so `pkg-config --static` emits it.
    """
    if not _PC_NAME.match(pc_name):
        raise BuildError("pkgconfig_add_private_lib() received an invalid module name.")
    if not _LINKER_FLAG.match(extra_lib):
        raise BuildError("pkgconfig_add_private_lib() received an invalid linker flag.")

    pc_file: Path | None = None
    for directory in (
        context.workspace / "lib/pkgconfig",
        context.workspace / "lib64/pkgconfig",
        context.workspace / "lib/x86_64-linux-gnu/pkgconfig",
        context.workspace / "share/pkgconfig",
    ):
        candidate = directory / f"{pc_name}.pc"
        if candidate.is_file():
            pc_file = candidate
            break
    if pc_file is None:
        context.logger.warn(
            f"pkgconfig_add_private_lib: '{pc_name}.pc' not found in workspace; skipping"
        )
        return

    lines = pc_file.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Libs.private:"):
            if extra_lib in line.split():
                return
            lines[index] = f"{line} {extra_lib}"
            break
    else:
        lines.append(f"Libs.private: {extra_lib}")
    pc_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def first_existing(*candidates: Path) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def pkgconf_include_dir(context: BuildContext, module: str) -> str | None:
    """Resolve a module's include directory without shell globbing.

    The `.pc` file comes from a downloaded tarball, so splitting its `Cflags`
    the way a shell would means a `*` there is expanded against the current
    directory — and a file named `-Ibogus` looks exactly like an include flag.
    """
    completed = context.runner.capture(["pkgconf", "--cflags-only-I", module])
    if completed.returncode == 0:
        for token in completed.stdout.split():
            if token.startswith("-I"):
                return token[2:]
    include_dir = context.pkgconf_variable(module, "includedir")
    if include_dir:
        return include_dir
    context.logger.warn(f"Unable to resolve include dir for pkgconf module '{module}'.")
    return None


def pkgconf_library_dir(context: BuildContext, module: str) -> str | None:
    completed = context.runner.capture(["pkgconf", "--libs-only-L", module])
    if completed.returncode == 0:
        for token in completed.stdout.split():
            if token.startswith("-L"):
                return token[2:]
    library_dir = context.pkgconf_variable(module, "libdir")
    if library_dir:
        return library_dir
    context.logger.warn(f"Unable to resolve library dir for pkgconf module '{module}'.")
    return None


def pkgconf_library_file(context: BuildContext, module: str, basename: str) -> str | None:
    library_dir = pkgconf_library_dir(context, module)
    if library_dir is None:
        return None
    for suffix in (".a", ".so", ".so.0"):
        candidate = Path(library_dir) / f"lib{basename}{suffix}"
        if candidate.is_file():
            return str(candidate)
    context.logger.warn(
        f"Unable to locate 'lib{basename}' in '{library_dir}' for pkgconf module '{module}'."
    )
    return None


def workspace_or_pkgconf_include_dir(
    context: BuildContext, key: str, module: str, *workspace_artifacts: Path
) -> str | None:
    """Prefer the workspace copy when it is actually there, else the host's."""
    if context.package_enabled(key) and first_existing(*workspace_artifacts) is not None:
        return f"{context.workspace}/include"
    return pkgconf_include_dir(context, module)


def workspace_or_pkgconf_library_dir(
    context: BuildContext, key: str, module: str, *workspace_artifacts: Path
) -> str | None:
    if context.package_enabled(key):
        found = first_existing(*workspace_artifacts)
        if found is not None:
            return str(found.parent)
    return pkgconf_library_dir(context, module)


def workspace_or_pkgconf_library_file(
    context: BuildContext, key: str, module: str, basename: str, *workspace_artifacts: Path
) -> str | None:
    if context.package_enabled(key):
        found = first_existing(*workspace_artifacts)
        if found is not None:
            return str(found)
    return pkgconf_library_file(context, module, basename)


def setup_python_venv(context: BuildContext, venv_path: Path, requirements: list[str]) -> None:
    """Create an isolated virtual environment and install into it.

    The pip invocation drops every index-redirecting variable and pins PyPI, so
    a user's global pip configuration cannot substitute a different package into
    a build that is otherwise fully specified.
    """
    if not requirements:
        raise BuildError("At least one Python package is required.")
    if not os.access(venv_path / "bin/python", os.X_OK):
        context.logger.info(f"Creating a Python virtual environment at '{venv_path}'...")
        context.execute(["python3", "-m", "venv", str(venv_path)])
    cache_dir = context.workspace / "python-package-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    context.logger.info(f"Installing Python packages: '{' '.join(requirements)}'.")
    context.execute(
        [
            str(venv_path / "bin/python"),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            *requirements,
        ],
        env_overrides={
            "PIP_CACHE_DIR": str(cache_dir),
            "PIP_CONFIG_FILE": "/dev/null",
            "PIP_INDEX_URL": "https://pypi.org/simple",
            "PYTHONNOUSERSITE": "1",
        },
    )


def install_rustup(context: BuildContext) -> None:
    """Install a pinned Rust toolchain inside the workspace.

    Keeping it here rather than in the user's `~/.cargo` means a build never
    mutates a toolchain the user maintains for something else.
    """
    cargo_home = context.workspace / "rust-toolchain/cargo"
    rustup_home = context.workspace / "rust-toolchain/rustup"
    context.env["CARGO_HOME"] = str(cargo_home)
    context.env["RUSTUP_HOME"] = str(rustup_home)
    context.env["RUSTUP_TOOLCHAIN"] = RUST_TOOLCHAIN_VERSION
    cargo_home.mkdir(parents=True, exist_ok=True)
    rustup_home.mkdir(parents=True, exist_ok=True)
    context.path_prepend(cargo_home / "bin")

    if not os.access(cargo_home / "bin/rustup", os.X_OK):
        # Staged in the workspace rather than $TMPDIR so the cleanup trap can
        # reach it; this is the one installer that used to escape the build root.
        handle, installer_name = tempfile.mkstemp(prefix=".rustup-init.", dir=context.workspace)
        os.close(handle)
        installer = Path(installer_name)
        context.register_temporary_path(installer)
        context.logger.info(
            "Downloading the official rustup installer into the isolated workspace..."
        )
        exit_code = context.runner.run_logged(
            [
                "curl",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--tlsv1.2",
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--retry",
                "3",
                "--retry-all-errors",
                "--max-time",
                "120",
                "--connect-timeout",
                str(context.download_settings.connect_timeout),
                "--output",
                str(installer),
                "https://sh.rustup.rs",
            ]
        )
        if exit_code != 0:
            installer.unlink(missing_ok=True)
            context.unregister_temporary_path(installer)
            raise BuildError("Failed to download rustup.")
        context.execute(
            [
                "sh",
                str(installer),
                "-y",
                "--no-modify-path",
                "--default-toolchain",
                "none",
                "--profile",
                "minimal",
            ]
        )
        installer.unlink(missing_ok=True)
        context.unregister_temporary_path(installer)

    context.execute(
        [
            str(cargo_home / "bin/rustup"),
            "toolchain",
            "install",
            RUST_TOOLCHAIN_VERSION,
            "--profile",
            "minimal",
        ]
    )
    context.path_prepend(cargo_home / "bin")
    report = context.runner.capture(["rustc", "--version"]).stdout.strip()
    if not report.startswith(f"rustc {RUST_TOOLCHAIN_VERSION} "):
        raise BuildError(
            f"Expected isolated Rust '{RUST_TOOLCHAIN_VERSION}', got '{report or 'unavailable'}'."
        )
    context.logger.info(f"Using isolated '{report}'.")


def check_and_install_cargo_c(context: BuildContext) -> None:
    cargo_c_root = context.workspace / "cargo-tools"
    context.path_prepend(cargo_c_root / "bin")

    def installed_version() -> str:
        report = context.runner.capture(["cargo", "cinstall", "--version"]).stdout
        parts = report.split("\n", 1)[0].split()
        return parts[1] if len(parts) > 1 else ""

    if installed_version() == CARGO_C_VERSION:
        context.logger.info(f"Using cargo-c '{CARGO_C_VERSION}'.")
        return
    context.logger.info(f"Installing cargo-c '{CARGO_C_VERSION}' into the isolated workspace...")
    context.execute(
        [
            "cargo",
            "install",
            "--force",
            "--locked",
            "--root",
            str(cargo_c_root),
            "--version",
            CARGO_C_VERSION,
            "cargo-c",
        ]
    )
    context.path_prepend(cargo_c_root / "bin")
    if installed_version() != CARGO_C_VERSION:
        raise BuildError(
            f"cargo-c installation did not produce the requested version '{CARGO_C_VERSION}'."
        )
