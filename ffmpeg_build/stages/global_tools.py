"""Build-system tools: m4, autotools, pkg-config, cmake, meson, ninja, zlib, TLS.

Stage order is load-bearing across the whole build: later stages use the
`cmake`, `meson`, `ninja`, `pkg-config` and `nasm` that this stage installs
into the workspace.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..runtime.artifacts import OPENSSL_DIRECTORY
from ..runtime.buildsys import meson_project_option_exists
from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.exec import strip_workspace_entries
from ..runtime.fetchers import (
    FREEDESKTOP_SOURCE,
    PKGCONF_SOURCE,
    ResolvedVersion,
    find_git_repo,
)
from ..runtime.paths import safe_remove_tree
from ..runtime.versions import GNU_FALLBACK_MIRROR, GNU_PRIMARY_MIRROR, is_full_commit
from .helpers import (
    QUICK_MIRROR_SETTINGS,
    configure_make_install,
    ensure_autotools,
    meson_ninja_install,
    setup_python_venv,
    workspace_or_pkgconf_include_dir,
    workspace_or_pkgconf_library_dir,
)

PKGCONF_REPOSITORY = "https://github.com/pkgconf/pkgconf"
FREEDESKTOP_PKG_CONFIG_ARCHIVES = "https://gitlab.freedesktop.org/pkg-config/pkg-config/-/archive"
# Host directories compiled into the workspace pkg-config. Flags naming them are
# filtered from its output, as the host's own resolver does.
SYSTEM_LIBRARY_PATH = (
    "/lib:/lib64:/lib/x86_64-linux-gnu:/usr/lib:/usr/lib64:/usr/lib/x86_64-linux-gnu"
)
SYSTEM_INCLUDE_PATH = "/usr/include:/usr/include/x86_64-linux-gnu"
PROVIDER_NAMES = {PKGCONF_SOURCE: "pkgconf", FREEDESKTOP_SOURCE: "freedesktop pkg-config"}


def resolve_tool_path(context: BuildContext, tool: str, preferred: Path) -> str | None:
    if os.access(preferred, os.X_OK):
        return str(preferred)
    resolved = context.runner.which(tool)
    if resolved is not None:
        return resolved
    context.logger.warn(
        f"Required tool '{tool}' was not found. Enable its package in config or install it "
        "with your system package manager."
    )
    return None


def install_global_tools(context: BuildContext) -> None:
    context.logger.banner("Installing Global Tools")
    workspace = context.workspace

    # `nvidia_gpu_present` being false also covers Intel-only and GPU-less
    # machines, so an actual AMD detection is required before saying this.
    if not context.nvidia_gpu_present and context.amd_gpu_present:
        context.logger.info("An AMD GPU was detected without an NVIDIA GPU present.")

    # Build m4 from a versioned release. "m4-latest" is mutable and cannot be
    # represented truthfully by a durable build marker.
    m4_version = context.fetch_version_if_enabled(
        "m4", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/m4/")
    )
    if context.build("m4", m4_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/m4/m4-{m4_version}.tar.xz",
            f"{GNU_FALLBACK_MIRROR}/m4/m4-{m4_version}.tar.xz",
        )
        configure_make_install(context, source, "--enable-threads=posix")
        context.build_done("m4", m4_version)

    m4_path = resolve_tool_path(context, "m4", workspace / "bin/m4")
    if m4_path is None:
        raise BuildError("'m4' is required to configure autoconf and libtool.")
    if m4_path != str(workspace / "bin/m4"):
        context.logger.info(f"Using system 'm4' fallback: '{m4_path}'.")

    autoconf_version = context.fetch_version_if_enabled(
        "autoconf", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/autoconf/")
    )
    if context.build("autoconf", autoconf_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/autoconf/autoconf-{autoconf_version}.tar.xz",
            f"{GNU_FALLBACK_MIRROR}/autoconf/autoconf-{autoconf_version}.tar.xz",
        )
        configure_make_install(context, source, f"M4={m4_path}")
        context.build_done("autoconf", autoconf_version)

    automake_version = context.fetch_version_if_enabled(
        "automake", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/automake/")
    )
    if context.build("automake", automake_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/automake/automake-{automake_version}.tar.xz",
            f"{GNU_FALLBACK_MIRROR}/automake/automake-{automake_version}.tar.xz",
        )
        configure_make_install(context, source)
        context.build_done("automake", automake_version)

    libtool_version = context.fetch_version_if_enabled(
        "libtool", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/libtool/")
    )
    if context.build("libtool", libtool_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/libtool/libtool-{libtool_version}.tar.xz",
            f"{GNU_FALLBACK_MIRROR}/libtool/libtool-{libtool_version}.tar.xz",
        )
        configure_make_install(context, source, "--with-pic", f"M4={m4_path}")
        context.build_done("libtool", libtool_version)

    _install_pkg_config(context)

    cmake_version = context.fetch_version_if_enabled(
        "cmake", lambda: find_git_repo(context.versions, "Kitware/CMake")
    )
    if context.build("cmake", cmake_version):
        source = context.download(
            f"https://github.com/Kitware/CMake/archive/refs/tags/v{cmake_version}.tar.gz",
            f"cmake-{cmake_version}.tar.gz",
        )
        # CMake bootstraps with its own bundled curl and must build as a
        # standalone host tool. A previous run may have installed a static
        # OpenSSL into the workspace; CMake's bundled curl would discover it
        # through pkg-config and link the static libcrypto.a without -lz,
        # leaving zlib symbols undefined. Hiding the workspace makes it fall
        # back to the system OpenSSL, which resolves its own zlib dependency.
        saved_pkg_config_path = context.env.get("PKG_CONFIG_PATH", "")
        context.save_compiler_flags()
        context.env["CPPFLAGS"] = strip_workspace_entries(
            context.env.get("CPPFLAGS", ""), workspace
        )
        context.env["LDFLAGS"] = strip_workspace_entries(context.env.get("LDFLAGS", ""), workspace)
        context.env["PKG_CONFIG_PATH"] = strip_workspace_entries(
            saved_pkg_config_path, workspace, ":"
        )
        context.execute(
            [
                "./bootstrap",
                f"--prefix={workspace}",
                f"--parallel={context.build_threads}",
                "--enable-ccache",
                "--no-qt-gui",
                "--no-debugger",
            ],
            cwd=source,
        )
        context.make(source)
        context.make(source, "install", jobs=False)
        context.restore_compiler_flags()
        context.env["PKG_CONFIG_PATH"] = saved_pkg_config_path
        context.build_done("cmake", cmake_version)

    meson_version = context.fetch_version_if_enabled(
        "meson", lambda: find_git_repo(context.versions, "mesonbuild/meson")
    )
    if context.build("meson", meson_version):
        setup_python_venv(
            context,
            workspace / "python_virtual_environment/build-tools",
            [f"meson=={meson_version}"],
        )
        context.build_done("meson", meson_version)
    # Outside the build block on purpose: a rerun that skips the build still
    # has to put this venv first on PATH, or `meson` resolves differently
    # between the first run and every later one.
    context.path_prepend(workspace / "python_virtual_environment/build-tools/bin")

    ninja_version = context.fetch_version_if_enabled(
        "ninja", lambda: find_git_repo(context.versions, "ninja-build/ninja")
    )
    if context.build("ninja", ninja_version):
        source = context.download(
            f"https://github.com/ninja-build/ninja/archive/refs/tags/v{ninja_version}.tar.gz",
            f"ninja-{ninja_version}.tar.gz",
        )
        context.execute(["python3", "configure.py", "--bootstrap"], cwd=source)
        context.execute(["install", "-Dm0755", "ninja", str(workspace / "bin/ninja")], cwd=source)
        context.build_done("ninja", ninja_version)

    zstd_version = context.fetch_version_if_enabled(
        "libzstd", lambda: find_git_repo(context.versions, "facebook/zstd")
    )
    if context.build("libzstd", zstd_version):
        source = context.download(
            f"https://github.com/facebook/zstd/archive/refs/tags/v{zstd_version}.tar.gz",
            f"libzstd-{zstd_version}.tar.gz",
        )
        meson_source = source / "build/meson"
        safe_remove_tree(meson_source / "meson-build", meson_source)
        meson_ninja_install(
            context,
            meson_source,
            "meson-build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Dbin_contrib=false",
            "-Dbin_programs=false",
            "-Dbin_tests=false",
        )
        context.build_done("libzstd", zstd_version)

    librist_version = context.fetch_version_if_enabled(
        "librist",
        lambda: context.versions.resolver.gitlab_version(
            "https://code.videolan.org", "rist/librist", "v"
        ),
    )
    if context.build("librist", librist_version):
        source = context.download(
            f"https://code.videolan.org/rist/librist/-/archive/v{librist_version}"
            f"/librist-v{librist_version}.tar.bz2",
            f"librist-{librist_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Dbuilt_tools=false",
            "-Dtest=false",
        )
        context.build_done("librist", librist_version)
    context.append_configure_options_if_enabled("librist", "--enable-librist")

    zlib_version = context.fetch_version_if_enabled(
        "zlib", lambda: find_git_repo(context.versions, "madler/zlib")
    )
    if context.build("zlib", zlib_version):
        source = context.download(
            f"https://github.com/madler/zlib/releases/download/v{zlib_version}"
            f"/zlib-{zlib_version}.tar.xz"
        )
        # The documented --static configure path builds only the archive this
        # workspace consumes, with no CMake option set to keep in step.
        configure_make_install(context, source, "--static")
        context.build_done("zlib", zlib_version)

    if context.nonfree_and_gpl:
        _install_openssl(context)


def pkg_config_version_and_source(
    resolved: ResolvedVersion | str | None,
) -> tuple[str | None, str]:
    """Normalize what `fetch_version_if_enabled` returned for `pkgconf`.

    A recorded marker carries no source, but the two implementations record
    different shapes: pkgconf a dotted release, freedesktop pkg-config the full
    commit it was built from, since it has published no release since 2017.
    """
    if resolved is None:
        return None, PKGCONF_SOURCE
    if isinstance(resolved, ResolvedVersion):
        return resolved.version, resolved.source
    return resolved, FREEDESKTOP_SOURCE if is_full_commit(resolved) else PKGCONF_SOURCE


def _install_pkg_config(context: BuildContext) -> None:
    """Build the workspace pkg-config: pkgconf, else freedesktop pkg-config.

    Only a source that cannot be obtained switches implementation; a failed
    configure or compile is reported as it is.
    """
    version, provider = pkg_config_version_and_source(
        context.fetch_version_if_enabled("pkgconf", context.versions.pkgconf)
    )
    if context.package_enabled("pkgconf") and version is None:
        raise BuildError("Failed to detect a pkgconf or freedesktop pkg-config version.")
    if not context.build("pkgconf", version):
        return
    assert version is not None
    provider, version, source = _acquire_pkg_config(context, provider, version)
    if provider == FREEDESKTOP_SOURCE:
        _build_freedesktop_pkg_config(context, source, version)
    else:
        _build_pkgconf(context, source)
    context.build_done("pkgconf", version)


def _download_pkg_config(context: BuildContext, provider: str, version: str) -> Path | None:
    # Every attempt here has another behind it, so none may stall the build.
    with context.downloader.temporary_settings(**QUICK_MIRROR_SETTINGS):
        if provider == FREEDESKTOP_SOURCE:
            return context.downloader.try_download(
                f"{FREEDESKTOP_PKG_CONFIG_ARCHIVES}/{version}/pkg-config-{version}.tar.bz2",
                f"pkg-config-{version}.tar.bz2",
            )
        # The uploaded release ships a generated configure and is the smallest
        # archive; older releases were never uploaded, so the tag snapshot follows.
        source = context.downloader.try_download(
            f"{PKGCONF_REPOSITORY}/releases/download/pkgconf-{version}/pkgconf-{version}.tar.xz",
            f"pkgconf-{version}.tar.xz",
        )
        if source is not None:
            return source
        return context.downloader.try_download(
            f"{PKGCONF_REPOSITORY}/archive/refs/tags/pkgconf-{version}.tar.gz",
            f"pkgconf-{version}.tar.gz",
        )


def _acquire_pkg_config(
    context: BuildContext, provider: str, version: str
) -> tuple[str, str, Path]:
    """Download the selected implementation, or the other one when it is unavailable."""
    source = _download_pkg_config(context, provider, version)
    if source is not None:
        return provider, version, source
    if provider == FREEDESKTOP_SOURCE:
        fallback, fallback_version = PKGCONF_SOURCE, context.versions.pkgconf_release()
    else:
        fallback, fallback_version = (
            FREEDESKTOP_SOURCE,
            context.versions.freedesktop_pkg_config_commit(),
        )
    context.logger.warn(
        f"{PROVIDER_NAMES[provider]} {version} could not be downloaded; "
        f"falling back to {PROVIDER_NAMES[fallback]}."
    )
    if fallback_version is None:
        raise BuildError(
            f"Failed to download {PROVIDER_NAMES[provider]} {version}, and no "
            f"{PROVIDER_NAMES[fallback]} version could be resolved."
        )
    context.replace_package_version("pkgconf", fallback_version)
    source = _download_pkg_config(context, fallback, fallback_version)
    if source is None:
        raise BuildError("Failed to download both pkgconf and freedesktop pkg-config.")
    return fallback, fallback_version, source


def _build_pkgconf(context: BuildContext, source: Path) -> None:
    workspace = context.workspace
    # pkgconf's autotools build is deprecated in 3.0 and announced for removal
    # in 3.1. Meson is used once the release declares the search-path option,
    # which older Meson files lack.
    if meson_project_option_exists(source, "with-pkg-config-dir"):
        # A static libpkgconf keeps the installed tool runnable without the
        # workspace on the loader path.
        meson_ninja_install(
            context,
            source,
            "build",
            "--libdir=lib",
            "--buildtype=release",
            "-Ddefault_library=static",
            f"-Dwith-pkg-config-dir={context.system_pkg_config_path}",
            f"-Dwith-system-libdir={SYSTEM_LIBRARY_PATH}",
            f"-Dwith-system-includedir={SYSTEM_INCLUDE_PATH}",
        )
    else:
        ensure_autotools(context, source)
        configure_make_install(
            context,
            source,
            "--enable-silent-rules",
            f"--with-pkg-config-dir={context.system_pkg_config_path}",
            f"--with-system-libdir={SYSTEM_LIBRARY_PATH}",
            f"--with-system-includedir={SYSTEM_INCLUDE_PATH}",
        )
    context.execute(
        ["ln", "-sf", str(workspace / "bin/pkgconf"), str(workspace / "bin/pkg-config")]
    )


def _build_freedesktop_pkg_config(context: BuildContext, source: Path, commit: str) -> None:
    """Build freedesktop pkg-config against the host GLib.

    Its bundled 2013 GLib no longer compiles with current GCC or Clang, so the
    host's development package is required instead.
    """
    if not context.runner.probe(["/usr/bin/pkgconf", "--exists", "glib-2.0"]):
        raise BuildError(
            "freedesktop pkg-config needs the host GLib development files; "
            "install 'libglib2.0-dev' and retry."
        )
    workspace = context.workspace
    context.logger.info(f"pkgconf: building freedesktop pkg-config at commit {commit[:12]}.")
    # The bundled GLib's m4 macros clash with the host's glib-gettext.m4, and
    # that subproject is never configured here.
    context.execute(["autoreconf", "-fi", "--no-recursive"], cwd=source)
    # The host tool finds the host GLib; workspace metadata and flags stay out.
    configure_make_install(
        context,
        source,
        "--disable-host-tool",
        f"--with-pc-path={context.system_pkg_config_path}",
        f"--with-system-include-path={SYSTEM_INCLUDE_PATH}",
        f"--with-system-library-path={SYSTEM_LIBRARY_PATH}",
        "PKG_CONFIG=/usr/bin/pkgconf",
        env_overrides={
            "PKG_CONFIG_PATH": strip_workspace_entries(
                context.env.get("PKG_CONFIG_PATH", ""), workspace, ":"
            ),
            "CPPFLAGS": strip_workspace_entries(context.env.get("CPPFLAGS", ""), workspace),
            "LDFLAGS": strip_workspace_entries(context.env.get("LDFLAGS", ""), workspace),
        },
    )


def _install_openssl(context: BuildContext) -> None:
    workspace = context.workspace
    openssl_version = context.fetch_version_if_enabled("openssl", context.versions.openssl)
    if context.package_enabled("openssl") and openssl_version is None:
        raise BuildError("Failed to detect the latest stable OpenSSL release.")
    if context.build("openssl", openssl_version):
        zlib_include_dir = workspace_or_pkgconf_include_dir(
            context, "zlib", "zlib", workspace / "lib/libz.a", workspace / "lib/libz.so"
        )
        if zlib_include_dir is None:
            raise BuildError(
                "OpenSSL needs zlib headers; enable 'packages.zlib' or install a system "
                "zlib development package."
            )
        zlib_library_dir = workspace_or_pkgconf_library_dir(
            context, "zlib", "zlib", workspace / "lib/libz.a", workspace / "lib/libz.so"
        )
        if zlib_library_dir is None:
            raise BuildError(
                "OpenSSL needs the zlib library; enable 'packages.zlib' or install a system "
                "zlib development package."
            )
        source = context.download(
            f"https://github.com/openssl/openssl/releases/download/openssl-{openssl_version}"
            f"/openssl-{openssl_version}.tar.gz"
        )
        context.execute(
            [
                "./Configure",
                f"--prefix={workspace}",
                # The system CA store, not the workspace: FFmpeg's TLS
                # verification relies on this compiled-in default.
                f"--openssldir={OPENSSL_DIRECTORY}",
                "no-shared",
                "no-pinshared",
                "no-apps",
                "no-docs",
                "no-tests",
                "threads",
                "zlib",
                "--with-rand-seed=os",
                f"--with-zlib-include={zlib_include_dir}",
                f"--with-zlib-lib={zlib_library_dir}",
            ],
            cwd=source,
        )
        context.make(source)
        context.make(source, "install_sw", jobs=False)
        context.build_done("openssl", openssl_version)
    context.append_configure_options_if_enabled("openssl", "--enable-openssl")
