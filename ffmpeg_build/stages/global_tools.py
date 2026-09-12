"""Build-system tools: m4, autotools, pkgconf, cmake, meson, ninja, zlib, TLS.

Stage order is load-bearing across the whole build: later stages use the
`cmake`, `meson`, `ninja`, `pkgconf` and `nasm` that this stage installs into
the workspace.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.exec import strip_workspace_entries
from ..runtime.fetchers import find_git_repo
from ..runtime.paths import safe_remove_tree
from ..runtime.versions import GNU_FALLBACK_MIRROR, GNU_PRIMARY_MIRROR
from .helpers import (
    configure_make_install,
    meson_ninja_install,
    setup_python_venv,
    workspace_or_pkgconf_include_dir,
    workspace_or_pkgconf_library_dir,
)


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
    print()
    context.logger.banner("Installing Global Tools")
    workspace = context.workspace

    # `nvidia_gpu_present` being false also covers Intel-only and GPU-less
    # machines, so an actual AMD detection is required before saying this.
    if not context.nvidia_gpu_present and context.amd_gpu_present:
        print("\nAn AMD GPU was detected without an NVIDIA GPU present.\n")

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

    pkgconf_version = context.fetch_version_if_enabled("pkgconf", context.versions.pkgconf)
    if context.package_enabled("pkgconf") and pkgconf_version is None:
        raise BuildError("Failed to detect pkgconf version.")
    if context.build("pkgconf", pkgconf_version):
        source = context.download(
            f"https://github.com/pkgconf/pkgconf/archive/refs/tags/pkgconf-{pkgconf_version}.tar.gz",
            f"pkgconf-{pkgconf_version}.tar.gz",
        )
        # Release tarballs from GitHub ship no configure script.
        context.execute(["autoreconf", "-fi"], cwd=source)
        configure_make_install(
            context,
            source,
            "--enable-silent-rules",
            f"--with-pkg-config-dir={context.system_pkg_config_path}",
            "--with-system-libdir=/lib:/lib64:/usr/lib:/usr/lib64:/usr/lib/x86_64-linux-gnu",
            "--with-system-includedir=/usr/include:/usr/include/x86_64-linux-gnu",
        )
        context.execute(
            ["ln", "-sf", str(workspace / "bin/pkgconf"), str(workspace / "bin/pkg-config")]
        )
        context.build_done("pkgconf", pkgconf_version)

    cmake_version = context.fetch_version_if_enabled(
        "cmake", lambda: find_git_repo(context.versions, "Kitware/CMake", 1)
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
        "meson", lambda: find_git_repo(context.versions, "mesonbuild/meson", 1)
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
        "ninja", lambda: find_git_repo(context.versions, "ninja-build/ninja", 1)
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
        "libzstd", lambda: find_git_repo(context.versions, "facebook/zstd", 1)
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
        "zlib", lambda: find_git_repo(context.versions, "madler/zlib", 1)
    )
    if context.build("zlib", zlib_version):
        source = context.download(
            f"https://github.com/madler/zlib/releases/download/v{zlib_version}"
            f"/zlib-{zlib_version}.tar.xz"
        )
        # zlib 1.3.x's CMake build always creates both shared and static
        # targets. Its documented --static configure path builds only the
        # archive this workspace consumes.
        configure_make_install(context, source, "--static")
        context.build_done("zlib", zlib_version)

    if context.nonfree_and_gpl:
        _install_openssl(context)


def _install_openssl(context: BuildContext) -> None:
    workspace = context.workspace
    openssl_version = context.fetch_version_if_enabled("openssl", context.versions.openssl_lts)
    if context.package_enabled("openssl") and openssl_version is None:
        raise BuildError("Failed to detect the latest OpenSSL 3.5 LTS release.")
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
                f"--openssldir={workspace}/ssl",
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
