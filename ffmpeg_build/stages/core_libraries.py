"""Assemblers and the foundational image and markup libraries."""

from __future__ import annotations

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.fetchers import find_git_repo, giflib_download_url
from ..runtime.versions import GNU_FALLBACK_MIRROR, GNU_PRIMARY_MIRROR
from .helpers import cmake_ninja_install, configure_make_install, ensure_autotools


def install_core_libraries(context: BuildContext) -> None:
    context.logger.banner("Installing Core Libraries")
    workspace = context.workspace

    yasm_version = context.fetch_version_if_enabled(
        "yasm", lambda: find_git_repo(context.versions, "yasm/yasm", 1)
    )
    if context.build("yasm", yasm_version):
        source = context.download(
            f"https://www.tortall.net/projects/yasm/releases/yasm-{yasm_version}.tar.gz",
            f"yasm-{yasm_version}.tar.gz",
        )
        configure_make_install(context, source)
        context.build_done("yasm", yasm_version)

    nasm_version = context.fetch_version_if_enabled("nasm", context.versions.nasm)
    if context.package_enabled("nasm") and nasm_version is None:
        raise BuildError("Failed to detect the NASM version; see the release-index error above.")
    if context.build("nasm", nasm_version):
        source = context.download(
            f"https://www.nasm.us/pub/nasm/releasebuilds/{nasm_version}/nasm-{nasm_version}.tar.xz"
        )
        ensure_autotools(context, source)
        # NASM has no --enable-ccache option; the compiler wrappers already on
        # PATH provide caching without passing a flag it would reject.
        configure_make_install(context, source, "--disable-pedantic")
        context.build_done("nasm", nasm_version)

    giflib_version = context.fetch_version_if_enabled("giflib", context.versions.giflib)
    if context.build("giflib", giflib_version):
        assert giflib_version is not None
        source = context.download(
            giflib_download_url(giflib_version), f"giflib-{giflib_version}.tar.gz"
        )
        # FFmpeg needs only the static library and public header. Upstream's
        # install-lib target also requires and installs libgif.so, so these two
        # artifacts are installed directly instead of building unused outputs.
        context.make(source, "libgif.a")
        context.execute(
            ["install", "-Dm0644", "libgif.a", str(workspace / "lib/libgif.a")], cwd=source
        )
        context.execute(
            ["install", "-Dm0644", "gif_lib.h", str(workspace / "include/gif_lib.h")], cwd=source
        )
        context.build_done("giflib", giflib_version)

    libiconv_version = context.fetch_version_if_enabled(
        "libiconv", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/libiconv/")
    )
    if context.build("libiconv", libiconv_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/libiconv/libiconv-{libiconv_version}.tar.gz",
            f"{GNU_FALLBACK_MIRROR}/libiconv/libiconv-{libiconv_version}.tar.gz",
        )
        configure_make_install(context, source, "--disable-shared", "--enable-static", "--with-pic")
        context.build_done("libiconv", libiconv_version)

    libxml2_version = context.fetch_version_if_enabled(
        "libxml2", lambda: find_git_repo(context.versions, "GNOME/libxml2", 1)
    )
    if context.build("libxml2", libxml2_version):
        source = context.download(
            f"https://gitlab.gnome.org/GNOME/libxml2/-/archive/v{libxml2_version}"
            f"/libxml2-v{libxml2_version}.tar.bz2?ref_type=tags",
            f"libxml2-{libxml2_version}.tar.bz2",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DLIBXML2_WITH_DOCS=OFF",
            "-DLIBXML2_WITH_MODULES=OFF",
            "-DLIBXML2_WITH_PROGRAMS=OFF",
            "-DLIBXML2_WITH_PYTHON=OFF",
            "-DLIBXML2_WITH_TESTS=OFF",
        )
        context.build_done("libxml2", libxml2_version)
    context.append_configure_options_if_enabled("libxml2", "--enable-libxml2")

    libpng_version = context.fetch_version_if_enabled(
        "libpng", lambda: find_git_repo(context.versions, "pnggroup/libpng", 1)
    )
    if context.build("libpng", libpng_version):
        source = context.download(
            f"https://github.com/pnggroup/libpng/archive/refs/tags/v{libpng_version}.tar.gz",
            f"libpng-{libpng_version}.tar.gz",
        )
        ensure_autotools(context, source)
        configure_make_install(
            context,
            source,
            "--disable-shared",
            "--enable-static",
            "--enable-hardware-optimizations=yes",
            "--with-pic",
        )
        context.build_done("libpng", libpng_version)

    libtiff_version = context.fetch_version_if_enabled(
        "libtiff", lambda: find_git_repo(context.versions, "libtiff/libtiff", 1)
    )
    if context.build("libtiff", libtiff_version):
        source = context.download(
            f"https://gitlab.com/libtiff/libtiff/-/archive/v{libtiff_version}"
            f"/libtiff-v{libtiff_version}.tar.bz2",
            f"libtiff-{libtiff_version}.tar.bz2",
        )
        # autoreconf rather than autogen.sh: the latter triggers downloads that
        # hang on some hosts.
        context.execute(["autoreconf", "-fi"], cwd=source)
        configure_make_install(
            context,
            source,
            *[
                f"--disable-{feature}"
                for feature in ("contrib", "cxx", "docs", "shared", "sphinx", "tests", "tools")
            ],
            "--enable-static",
            "--with-pic",
        )
        context.build_done("libtiff", libtiff_version)
