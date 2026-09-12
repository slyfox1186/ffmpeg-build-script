"""Fonts, text shaping, TLS, compression, and the LV2 plugin stack."""

from __future__ import annotations

from ..runtime.buildsys import meson_project_option_exists
from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.fetchers import (
    ResolvedVersion,
    find_git_repo,
    fontconfig_gitlab_archive_url,
    fontconfig_release_archive_url,
    freetype_gitlab_archive_url,
    freetype_release_archive_url,
    freetype_sourceforge_archive_url,
)
from ..runtime.versions import GNU_FALLBACK_MIRROR, GNU_PRIMARY_MIRROR
from .helpers import (
    cmake_ninja_install,
    configure_make_install,
    ensure_autotools,
    meson_ninja_install,
    pkgconfig_add_private_lib,
)

# Two mirrors are tried in sequence for the font packages, so the first attempt
# must give up quickly rather than wait out the default transfer timeout.
_FONT_MIRROR_SETTINGS = {
    "connect_timeout": 3,
    "max_time": 45,
    "retry": 0,
    "retry_delay": 3,
}


def install_support_libraries(context: BuildContext) -> None:
    print()
    context.logger.banner("Installing Miscellaneous Libraries")

    # GnuTLS is the free TLS stack. It stays available in GPL/non-free builds
    # whenever the user has not selected the optional OpenSSL build.
    if not context.nonfree_and_gpl or not context.package_enabled("openssl"):
        _install_gnutls_stack(context)

    _install_fonts(context)

    freeglut_version = context.fetch_version_if_enabled(
        "freeglut", lambda: find_git_repo(context.versions, "freeglut/freeglut", 1)
    )
    if context.build("freeglut", freeglut_version):
        source = context.download(
            f"https://github.com/freeglut/freeglut/releases/download/v{freeglut_version}"
            f"/freeglut-{freeglut_version}.tar.gz"
        )
        context.save_compiler_flags()
        context.append_flag("CFLAGS", "-DFREEGLUT_STATIC")
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DFREEGLUT_BUILD_DEMOS=OFF",
            "-DFREEGLUT_BUILD_SHARED_LIBS=OFF",
        )
        context.restore_compiler_flags()
        context.build_done("freeglut", freeglut_version)

    libwebp_commit = context.git_snapshot(
        "https://chromium.googlesource.com/webm/libwebp", "libwebp-git"
    )
    if context.build("libwebp-git", libwebp_commit):
        source = context.packages / "libwebp-git"
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            *[
                f"-DWEBP_BUILD_{target}=OFF"
                for target in (
                    "ANIM_UTILS",
                    "CWEBP",
                    "DWEBP",
                    "EXTRAS",
                    "GIF2WEBP",
                    "IMG2WEBP",
                    "VWEBP",
                    "WEBPINFO",
                    "WEBPMUX",
                )
            ],
            "-DWEBP_BUILD_FUZZTEST=OFF",
            "-DWEBP_BUILD_LIBWEBPMUX=ON",
            "-DWEBP_ENABLE_SWAP_16BIT_CSP=OFF",
            "-DWEBP_LINK_STATIC=ON",
        )
        context.build_done("libwebp-git", libwebp_commit)
    context.append_configure_options_if_enabled("libwebp-git", "--enable-libwebp")

    libhwy_version = context.fetch_version_if_enabled(
        "libhwy", lambda: find_git_repo(context.versions, "google/highway", 1)
    )
    if context.build("libhwy", libhwy_version):
        source = context.download(
            f"https://github.com/google/highway/archive/refs/tags/{libhwy_version}.tar.gz",
            f"libhwy-{libhwy_version}.tar.gz",
        )
        context.save_compiler_flags()
        context.append_flag("CFLAGS", "-DHWY_COMPILE_ALL_ATTAINABLE")
        context.append_flag("CXXFLAGS", "-DHWY_COMPILE_ALL_ATTAINABLE")
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_TESTING=OFF",
            "-DHWY_ENABLE_EXAMPLES=OFF",
            "-DHWY_ENABLE_TESTS=OFF",
            "-DHWY_FORCE_STATIC_LIBS=ON",
        )
        context.restore_compiler_flags()
        context.build_done("libhwy", libhwy_version)

    brotli_version = context.fetch_version_if_enabled(
        "brotli", lambda: find_git_repo(context.versions, "google/brotli", 1)
    )
    if context.build("brotli", brotli_version):
        source = context.download(
            f"https://github.com/google/brotli/archive/refs/tags/v{brotli_version}.tar.gz",
            f"brotli-{brotli_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBROTLI_BUILD_TOOLS=OFF",
            "-DBROTLI_DISABLE_TESTS=ON",
            "-DBUILD_SHARED_LIBS=OFF",
        )
        context.build_done("brotli", brotli_version)

    lcms2_version = context.fetch_version_if_enabled(
        "lcms2", lambda: find_git_repo(context.versions, "mm2/Little-CMS", 1)
    )
    if context.build("lcms2", lcms2_version):
        source = context.download(
            f"https://github.com/mm2/Little-CMS/archive/refs/tags/lcms{lcms2_version}.tar.gz",
            f"lcms2-{lcms2_version}.tar.gz",
        )
        context.execute(["sh", "autogen.sh"], cwd=source)
        # The threaded plugin is GPL-3-only upstream and does not belong in
        # this always-available path. FFmpeg needs the core static library, not
        # the JPEG/TIFF utilities or the plugin.
        configure_make_install(
            context,
            source,
            "--disable-shared",
            "--enable-static",
            "--without-jpeg",
            "--without-tiff",
            "--without-zlib",
        )
        context.build_done("lcms2", lcms2_version)
    context.append_configure_options_if_enabled("lcms2", "--enable-lcms2")

    gflags_version = context.fetch_version_if_enabled(
        "gflags", lambda: find_git_repo(context.versions, "gflags/gflags", 1)
    )
    if context.build("gflags", gflags_version):
        source = context.download(
            f"https://github.com/gflags/gflags/archive/refs/tags/v{gflags_version}.tar.gz",
            f"gflags-{gflags_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_gflags_LIB=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_STATIC_LIBS=ON",
            "-DINSTALL_HEADERS=ON",
            "-DREGISTER_BUILD_DIR=OFF",
            "-DREGISTER_INSTALL_PREFIX=OFF",
        )
        context.build_done("gflags", gflags_version)

    opencl_commit = context.git_snapshot(
        "https://github.com/KhronosGroup/OpenCL-SDK.git", "opencl-sdk-git", "recurse"
    )
    if context.build("opencl-sdk-git", opencl_commit):
        source = context.packages / "opencl-sdk-git"
        cmake_ninja_install(
            context,
            source,
            "build",
            "-S",
            ".",
            *[f"-DBUILD_{target}=OFF" for target in ("DOCS", "EXAMPLES", "SHARED_LIBS", "TESTING")],
            f"-DCMAKE_CXX_FLAGS={context.env.get('CXXFLAGS', '')}",
            f"-DCMAKE_C_FLAGS={context.env.get('CFLAGS', '')}",
            "-DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF",
            "-DOPENCL_ICD_LOADER_BUILD_SHARED_LIBS=OFF",
            "-DOPENCL_SDK_BUILD_OPENGL_SAMPLES=OFF",
            "-DOPENCL_SDK_BUILD_SAMPLES=OFF",
            "-DOPENCL_SDK_TEST_SAMPLES=OFF",
            "-DTHREADS_PREFER_PTHREAD_FLAG=ON",
        )
        context.build_done("opencl-sdk-git", opencl_commit)
    context.append_configure_options_if_enabled("opencl-sdk-git", "--enable-opencl")

    # Vulkan-Headers is header-only. Compile-time SDK support must not depend on
    # whether this host currently exposes a GPU; the resulting binary discovers
    # Vulkan devices at runtime.
    vulkan_commit = context.git_snapshot(
        "https://github.com/KhronosGroup/Vulkan-Headers.git", "vulkan-headers-git"
    )
    if context.build("vulkan-headers-git", vulkan_commit):
        source = context.packages / "vulkan-headers-git"
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DVULKAN_HEADERS_ENABLE_INSTALL=ON",
            "-DVULKAN_HEADERS_ENABLE_MODULE=OFF",
            "-DVULKAN_HEADERS_ENABLE_TESTS=OFF",
        )
        context.build_done("vulkan-headers-git", vulkan_commit)

    libjpeg_version = context.fetch_version_if_enabled(
        "libjpeg-turbo", lambda: find_git_repo(context.versions, "libjpeg-turbo/libjpeg-turbo", 1)
    )
    if context.build("libjpeg-turbo", libjpeg_version):
        source = context.download(
            f"https://github.com/libjpeg-turbo/libjpeg-turbo/archive/refs/tags/{libjpeg_version}.tar.gz",
            f"libjpeg-turbo-{libjpeg_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DENABLE_SHARED=OFF",
            "-DENABLE_STATIC=ON",
            "-DWITH_JPEG8=1",
            "-DWITH_TURBOJPEG=ON",
            "-DWITH_JAVA=OFF",
        )
        context.build_done("libjpeg-turbo", libjpeg_version)

    if context.nonfree_and_gpl:
        rubberband_commit = context.git_snapshot(
            "https://github.com/breakfastquay/rubberband.git", "rubberband-git"
        )
        if context.build("rubberband-git", rubberband_commit):
            source = context.packages / "rubberband-git"
            meson_ninja_install(
                context,
                source,
                "build",
                "--buildtype=release",
                "--default-library=static",
                "-Dauto_features=disabled",
                "-Dfft=builtin",
                "-Dresampler=builtin",
            )
            # Upstream's generated .pc links only -lrubberband even though the
            # static archive is C++; expose the runtime for C-driver consumers.
            pkgconfig_add_private_lib(context, "rubberband", "-lstdc++")
            context.build_done("rubberband-git", rubberband_commit)
        context.append_configure_options_if_enabled("rubberband-git", "--enable-librubberband")

    cares_version = context.fetch_version_if_enabled(
        "c-ares", lambda: find_git_repo(context.versions, "c-ares/c-ares", 1)
    )
    if context.build("c-ares", cares_version):
        source = context.download(
            f"https://github.com/c-ares/c-ares/archive/refs/tags/v{cares_version}.tar.gz",
            f"c-ares-{cares_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            *[
                f"-DCARES_{option}=OFF"
                for option in (
                    "BUILD_CONTAINER_TESTS",
                    "BUILD_TESTS",
                    "BUILD_TOOLS",
                    "SHARED",
                    "SYMBOL_HIDING",
                )
            ],
            *[f"-DCARES_{option}=ON" for option in ("STATIC", "STATIC_PIC", "THREADS")],
        )
        context.build_done("c-ares", cares_version)

    _install_lv2_stack(context)

    jemalloc_version = context.fetch_version_if_enabled(
        "jemalloc", lambda: find_git_repo(context.versions, "jemalloc/jemalloc", 1)
    )
    if context.build("jemalloc", jemalloc_version):
        source = context.download(
            f"https://github.com/jemalloc/jemalloc/archive/refs/tags/{jemalloc_version}.tar.gz",
            f"jemalloc-{jemalloc_version}.tar.gz",
        )
        ensure_autotools(context, source)
        configure_make_install(
            context,
            source,
            *[
                f"--disable-{feature}"
                for feature in ("debug", "doc", "fill", "log", "shared", "prof", "stats")
            ],
            *[f"--enable-{feature}" for feature in ("autogen", "static", "xmalloc")],
        )
        context.build_done("jemalloc", jemalloc_version)


def _install_gnutls_stack(context: BuildContext) -> None:
    workspace = context.workspace

    gmp_version = context.fetch_version_if_enabled(
        "gmp", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/gmp/")
    )
    if context.build("gmp", gmp_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/gmp/gmp-{gmp_version}.tar.xz",
            f"{GNU_FALLBACK_MIRROR}/gmp/gmp-{gmp_version}.tar.xz",
        )
        configure_make_install(context, source, "--disable-shared", "--enable-static")
        context.build_done("gmp", gmp_version)

    nettle_version = context.fetch_version_if_enabled(
        "nettle", lambda: context.versions.resolver.gnu_version(f"{GNU_PRIMARY_MIRROR}/nettle/")
    )
    if context.build("nettle", nettle_version):
        source = context.downloader.download_with_fallback(
            f"{GNU_PRIMARY_MIRROR}/nettle/nettle-{nettle_version}.tar.gz",
            f"{GNU_FALLBACK_MIRROR}/nettle/nettle-{nettle_version}.tar.gz",
        )
        configure_make_install(
            context,
            source,
            "--enable-static",
            *[f"--disable-{feature}" for feature in ("documentation", "openssl", "shared")],
            f"--libdir={workspace}/lib",
            f"CPPFLAGS={context.env.get('CPPFLAGS', '')} -fno-lto",
            f"LDFLAGS={context.env.get('LDFLAGS', '')}",
        )
        context.build_done("nettle", nettle_version)

    gnutls_version = context.fetch_version_if_enabled("gnutls", context.versions.gnutls)
    if context.build("gnutls", gnutls_version):
        assert gnutls_version is not None
        series = ".".join(gnutls_version.split(".")[:2])
        source = context.download(
            f"https://www.gnupg.org/ftp/gcrypt/gnutls/v{series}/gnutls-{gnutls_version}.tar.xz"
        )
        configure_make_install(
            context,
            source,
            *[
                f"--disable-{feature}"
                for feature in (
                    "cxx",
                    "doc",
                    "gtk-doc-html",
                    "guile",
                    "libdane",
                    "nls",
                    "shared",
                    "tests",
                    "tools",
                )
            ],
            *[f"--enable-{feature}" for feature in ("local-libopts", "static")],
            *[f"--with-included-{component}" for component in ("libtasn1", "unistring")],
            "--without-p11-kit",
            f"CPPFLAGS={context.env.get('CPPFLAGS', '')}",
            f"LDFLAGS={context.env.get('LDFLAGS', '')}",
        )
        context.build_done("gnutls", gnutls_version)

    # Wire FFmpeg's TLS to the stack just built. Without this a default build
    # has no https/tls support at all; gmp additionally enables rtmpe/rtmpte.
    context.append_configure_options_if_enabled("gnutls", "--enable-gnutls")
    context.append_configure_options_if_enabled("gmp", "--enable-gmp")


def _version_and_source(
    resolved: ResolvedVersion | str | None, *, marker_source: str = "release"
) -> tuple[str | None, str]:
    """Normalize what `fetch_version_if_enabled` returned for a font package.

    A fresh lookup reports which upstream answered, because FreeType and
    Fontconfig publish differently named archives on their release mirror and
    on GitLab. A marker has no source metadata, so use the package's current
    archive host if missing artifacts require that recorded version to rebuild.
    """
    if resolved is None:
        return None, "release"
    if isinstance(resolved, ResolvedVersion):
        return resolved.version, resolved.source
    return resolved, marker_source


def _install_fonts(context: BuildContext) -> None:
    freetype_version, freetype_source = _version_and_source(
        context.fetch_version_if_enabled("freetype", context.versions.freetype)
    )
    if context.package_enabled("freetype") and freetype_version is None:
        raise BuildError(
            "Failed to detect FreeType version from the official FreeType release archive or "
            "FreeDesktop GitLab."
        )
    if context.build("freetype", freetype_version):
        assert freetype_version is not None
        with context.downloader.temporary_settings(**_FONT_MIRROR_SETTINGS):
            if freetype_source == "gitlab":
                source = context.downloader.download_with_fallback(
                    freetype_gitlab_archive_url(freetype_version),
                    freetype_release_archive_url(freetype_version),
                )
            else:
                source = context.downloader.download_with_fallback(
                    freetype_release_archive_url(freetype_version),
                    freetype_sourceforge_archive_url(freetype_version),
                )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            *[
                f"-D{feature}=disabled"
                for feature in ("harfbuzz", "png", "bzip2", "brotli", "zlib", "tests")
            ],
        )
        context.build_done("freetype", freetype_version)
    context.append_configure_options_if_enabled("freetype", "--enable-libfreetype")

    fontconfig_version, fontconfig_source = _version_and_source(
        context.fetch_version_if_enabled("fontconfig", context.versions.fontconfig),
        marker_source="gitlab",
    )
    if context.package_enabled("fontconfig") and fontconfig_version is None:
        raise BuildError(
            "Failed to detect Fontconfig version from the official Fontconfig release archive "
            "or FreeDesktop GitLab."
        )
    if context.build("fontconfig", fontconfig_version):
        assert fontconfig_version is not None
        with context.downloader.temporary_settings(**_FONT_MIRROR_SETTINGS):
            if fontconfig_source == "gitlab":
                source = context.downloader.download_with_fallback(
                    fontconfig_gitlab_archive_url(fontconfig_version),
                    fontconfig_release_archive_url(fontconfig_version),
                )
            else:
                source = context.download(
                    fontconfig_release_archive_url(fontconfig_version),
                    f"fontconfig-{fontconfig_version}.tar.xz",
                )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Diconv=enabled",
            "-Ddoc=disabled",
            "-Dxml-backend=libxml2",
        )
        context.build_done("fontconfig", fontconfig_version)
    context.append_configure_options_if_enabled("fontconfig", "--enable-libfontconfig")

    harfbuzz_version = context.fetch_version_if_enabled(
        "harfbuzz", lambda: find_git_repo(context.versions, "harfbuzz/harfbuzz", 1)
    )
    if context.build("harfbuzz", harfbuzz_version):
        source = context.download(
            f"https://github.com/harfbuzz/harfbuzz/archive/refs/tags/{harfbuzz_version}.tar.gz",
            f"harfbuzz-{harfbuzz_version}.tar.gz",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            *[
                f"-D{feature}=disabled"
                for feature in (
                    "benchmark",
                    "cairo",
                    "docs",
                    "glib",
                    "gobject",
                    "icu",
                    "introspection",
                    "tests",
                    "utilities",
                )
            ],
        )
        context.build_done("harfbuzz", harfbuzz_version)
    context.append_configure_options_if_enabled("harfbuzz", "--enable-libharfbuzz")

    # c2man is deliberately skipped: it does not build on modern systems and is
    # only needed for the documentation this build disables.
    fribidi_version = context.fetch_version_if_enabled(
        "fribidi", lambda: find_git_repo(context.versions, "fribidi/fribidi", 1)
    )
    if context.build("fribidi", fribidi_version):
        source = context.download(
            f"https://github.com/fribidi/fribidi/archive/refs/tags/v{fribidi_version}.tar.gz",
            f"fribidi-{fribidi_version}.tar.gz",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            *[f"-D{feature}=false" for feature in ("bin", "docs", "tests")],
        )
        context.build_done("fribidi", fribidi_version)
    context.append_configure_options_if_enabled("fribidi", "--enable-libfribidi")

    libass_version = context.fetch_version_if_enabled(
        "libass", lambda: find_git_repo(context.versions, "libass/libass", 1)
    )
    if context.build("libass", libass_version):
        source = context.download(
            f"https://github.com/libass/libass/archive/refs/tags/{libass_version}.tar.gz",
            f"libass-{libass_version}.tar.gz",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "-Dauto_features=disabled",
            "-Dfontconfig=enabled",
        )
        context.build_done("libass", libass_version)
    context.append_configure_options_if_enabled("libass", "--enable-libass")


def _install_lv2_stack(context: BuildContext) -> None:
    workspace = context.workspace

    lv2_commit = context.git_snapshot("https://github.com/lv2/lv2.git", "lv2-git")
    if context.build("lv2-git", lv2_commit):
        source = context.packages / "lv2-git"
        # Documentation and tests are the only upstream consumers of the
        # optional Python modules, so a header-only build needs no venv.
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Ddocs=disabled",
            "-Dtests=disabled",
            *[
                f"-D{option}=disabled"
                for option in ("tools", "plugins")
                if meson_project_option_exists(source, option)
            ],
            "-Donline_docs=false",
        )
        context.build_done("lv2-git", lv2_commit)

    serd_version = context.fetch_version_if_enabled(
        "serd",
        lambda: context.versions.resolver.gitlab_version(
            "https://gitlab.com", "drobilla/serd", "v"
        ),
    )
    if context.build("serd", serd_version):
        source = context.download(
            f"https://gitlab.com/drobilla/serd/-/archive/v{serd_version}/serd-v{serd_version}.tar.bz2",
            f"serd-{serd_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Dstatic=true",
            *[
                f"-D{feature}=disabled"
                for feature in ("docs", "html", "man", "man_html", "singlehtml", "tests", "tools")
            ],
        )
        context.build_done("serd", serd_version)

    pcre2_version = context.fetch_version_if_enabled(
        "pcre2",
        lambda: context.versions.resolver.github_version("PCRE2Project/pcre2", "pcre2-", "RC"),
    )
    if context.build("pcre2", pcre2_version):
        source = context.download(
            f"https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-{pcre2_version}.tar.gz",
            f"pcre2-{pcre2_version}.tar.gz",
        )
        ensure_autotools(context, source)
        configure_make_install(context, source, "--disable-shared")
        context.build_done("pcre2", pcre2_version)

    zix_version = context.fetch_version_if_enabled(
        "zix", lambda: find_git_repo(context.versions, "drobilla/zix", 1)
    )
    if context.build("zix", zix_version):
        source = context.download(
            f"https://gitlab.com/drobilla/zix/-/archive/v{zix_version}/zix-v{zix_version}.tar.bz2",
            f"zix-{zix_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            *[
                f"-D{feature}=disabled"
                for feature in ("benchmarks", "docs", "singlehtml", "tests", "tests_cpp")
            ],
        )
        context.build_done("zix", zix_version)

    sord_version = context.fetch_version_if_enabled(
        "sord",
        lambda: context.versions.resolver.gitlab_version(
            "https://gitlab.com", "drobilla/sord", "v"
        ),
    )
    if context.build("sord", sord_version):
        context.save_compiler_flags()
        context.append_flag("CFLAGS", f"-I{workspace}/include/serd-0")
        source = context.download(
            f"https://gitlab.com/drobilla/sord/-/archive/v{sord_version}/sord-v{sord_version}.tar.bz2",
            f"sord-{sord_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            *[f"-D{feature}=disabled" for feature in ("docs", "tests", "tools")],
        )
        context.restore_compiler_flags()
        context.build_done("sord", sord_version)

    sratom_version = context.fetch_version_if_enabled(
        "sratom",
        lambda: context.versions.resolver.gitlab_version("https://gitlab.com", "lv2/sratom", "v"),
    )
    if context.build("sratom", sratom_version):
        source = context.download(
            f"https://gitlab.com/lv2/sratom/-/archive/v{sratom_version}"
            f"/sratom-v{sratom_version}.tar.bz2",
            f"sratom-{sratom_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            *[f"-D{feature}=disabled" for feature in ("docs", "html", "singlehtml", "tests")],
        )
        context.build_done("sratom", sratom_version)

    # Lilv builds against the same LV2/Serd/Zix/Sord/Sratom stack installed in
    # this workspace. Linking a distro Lilv against newer workspace transitive
    # libraries can silently mix ABI generations.
    lilv_version = context.fetch_version_if_enabled(
        "lilv",
        lambda: context.versions.resolver.gitlab_version("https://gitlab.com", "lv2/lilv", "v"),
    )
    if context.build("lilv", lilv_version):
        source = context.download(
            f"https://gitlab.com/lv2/lilv/-/archive/v{lilv_version}/lilv-v{lilv_version}.tar.bz2",
            f"lilv-{lilv_version}.tar.bz2",
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=static",
            "--strip",
            "-Dauto_features=disabled",
            "-Ddynmanifest=disabled",
            *[
                f"-D{feature}=disabled"
                for feature in (
                    "bindings_cpp",
                    "bindings_py",
                    "docs",
                    "html",
                    "singlehtml",
                    "tests",
                    "tools",
                )
            ],
        )
        context.build_done("lilv", lilv_version)
    context.append_configure_options_if_enabled("lilv", "--enable-lv2")
