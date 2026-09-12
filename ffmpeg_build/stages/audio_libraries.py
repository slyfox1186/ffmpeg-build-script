"""Audio codecs, containers, and resampling."""

from __future__ import annotations

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.fetchers import find_git_repo, sdl2_download_url
from .helpers import (
    cmake_ninja_install,
    configure_make_install,
    ensure_autotools,
    pkgconfig_add_private_lib,
    workspace_or_pkgconf_include_dir,
    workspace_or_pkgconf_library_dir,
    workspace_or_pkgconf_library_file,
)

# LAME publishes no version index and 3.100 (2017) is still the current
# release, so `--latest` cannot move it. Update this literal when upstream
# ships a new one.
LAME_VERSION = "3.100"

# Used when SourceForge's release index is unreachable.
OPENCORE_AMR_FALLBACK_VERSION = "0.1.6"


def install_audio_libraries(context: BuildContext) -> None:
    print()
    context.logger.banner("Installing Audio Tools")
    workspace = context.workspace

    libsoxr_version = context.fetch_version_if_enabled(
        "libsoxr", lambda: find_git_repo(context.versions, "chirlu/soxr", 1)
    )
    if context.build("libsoxr", libsoxr_version):
        source = context.download(
            f"https://github.com/chirlu/soxr/archive/refs/tags/{libsoxr_version}.tar.gz",
            f"libsoxr-{libsoxr_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-S",
            ".",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTS=OFF",
            "-DWITH_OPENMP=OFF",
        )
        context.build_done("libsoxr", libsoxr_version)
    context.append_configure_options_if_enabled("libsoxr", "--enable-libsoxr")

    # SDL2 specifically: upstream's main branch is SDL3.
    sdl2_version = context.fetch_version_if_enabled("sdl2", context.versions.sdl2)
    if context.package_enabled("sdl2") and sdl2_version is None:
        raise BuildError("Failed to detect SDL2 version.")
    if context.build("sdl2", sdl2_version):
        assert sdl2_version is not None
        source = context.download(sdl2_download_url(sdl2_version), f"SDL2-{sdl2_version}.tar.gz")
        cmake_ninja_install(
            context,
            source,
            "build",
            "-S",
            ".",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DSDL_ALSA_SHARED=OFF",
            "-DSDL_CCACHE=ON",
            "-DSDL_SHARED=OFF",
            "-DSDL_STATIC=ON",
            "-DSDL_TESTS=OFF",
            "-DSDL2_DISABLE_INSTALL_DOCS=ON",
        )
        # A static workspace libiconv has to appear in SDL's private link
        # dependencies; glibc-based system builds do not need -liconv.
        if context.package_enabled("libiconv") and (workspace / "lib/libiconv.a").is_file():
            pkgconfig_add_private_lib(context, "sdl2", "-liconv")
        context.build_done("sdl2", sdl2_version)

    libsndfile_version = context.fetch_version_if_enabled(
        "libsndfile", lambda: find_git_repo(context.versions, "libsndfile/libsndfile", 1)
    )
    if context.build("libsndfile", libsndfile_version):
        source = context.download(
            f"https://github.com/libsndfile/libsndfile/releases/download/{libsndfile_version}"
            f"/libsndfile-{libsndfile_version}.tar.xz"
        )
        configure_make_install(
            context,
            source,
            *[
                f"--disable-{feature}"
                for feature in ("alsa", "full-suite", "shared", "sndio", "sqlite")
            ],
            "--enable-static",
            "--with-pic",
        )
        context.build_done("libsndfile", libsndfile_version)

    libogg_version = context.fetch_version_if_enabled(
        "libogg", lambda: find_git_repo(context.versions, "xiph/ogg", 1)
    )
    if context.build("libogg", libogg_version):
        source = context.download(
            f"https://github.com/xiph/ogg/archive/refs/tags/v{libogg_version}.tar.gz",
            f"libogg-{libogg_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DINSTALL_DOCS=OFF",
        )
        context.build_done("libogg", libogg_version)

    if context.nonfree_and_gpl:
        fdk_version = context.fetch_version_if_enabled(
            "libfdk-aac", lambda: find_git_repo(context.versions, "mstorsjo/fdk-aac", 1)
        )
        if context.build("libfdk-aac", fdk_version):
            source = context.download(
                f"https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v{fdk_version}.tar.gz",
                f"libfdk-aac-{fdk_version}.tar.gz",
            )
            ensure_autotools(context, source)
            configure_make_install(context, source, "--disable-shared")
            context.build_done("libfdk-aac", fdk_version)
        context.append_configure_options_if_enabled("libfdk-aac", "--enable-libfdk-aac")

    vorbis_version = context.fetch_version_if_enabled(
        "vorbis", lambda: find_git_repo(context.versions, "xiph/vorbis", 1)
    )
    if context.build("vorbis", vorbis_version):
        source = context.download(
            f"https://github.com/xiph/vorbis/archive/refs/tags/v{vorbis_version}.tar.gz",
            f"vorbis-{vorbis_version}.tar.gz",
        )
        ogg_include_dir = workspace_or_pkgconf_include_dir(
            context, "libogg", "ogg", workspace / "lib/libogg.a"
        )
        if ogg_include_dir is None:
            raise BuildError(
                "Vorbis needs Ogg headers; enable 'packages.libogg' or install a system "
                "libogg development package."
            )
        ogg_library = workspace_or_pkgconf_library_file(
            context, "libogg", "ogg", "ogg", workspace / "lib/libogg.a"
        )
        if ogg_library is None:
            raise BuildError(
                "Vorbis needs the Ogg library; enable 'packages.libogg' or install a system "
                "libogg development package."
            )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=OFF",
            f"-DOGG_INCLUDE_DIR={ogg_include_dir}",
            f"-DOGG_LIBRARY={ogg_library}",
        )
        context.build_done("vorbis", vorbis_version)
    context.append_configure_options_if_enabled("vorbis", "--enable-libvorbis")

    libopus_version = context.fetch_version_if_enabled(
        "libopus", lambda: find_git_repo(context.versions, "xiph/opus", 1)
    )
    if context.build("libopus", libopus_version):
        source = context.download(
            f"https://github.com/xiph/opus/archive/refs/tags/v{libopus_version}.tar.gz",
            f"libopus-{libopus_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTING=OFF",
            "-DOPUS_BUILD_PROGRAMS=OFF",
            "-DOPUS_BUILD_TESTING=OFF",
        )
        context.build_done("libopus", libopus_version)
    context.append_configure_options_if_enabled("libopus", "--enable-libopus")

    libmysofa_version = context.fetch_version_if_enabled(
        "libmysofa", lambda: find_git_repo(context.versions, "hoene/libmysofa", 1)
    )
    if context.build("libmysofa", libmysofa_version):
        source = context.download(
            f"https://github.com/hoene/libmysofa/archive/refs/tags/v{libmysofa_version}.tar.gz",
            f"libmysofa-{libmysofa_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_STATIC_LIBS=ON",
            "-DBUILD_TESTS=OFF",
        )
        context.build_done("libmysofa", libmysofa_version)
    context.append_configure_options_if_enabled("libmysofa", "--enable-libmysofa")

    opencore_version = context.fetch_version_if_enabled(
        "opencore-amr", context.versions.opencore_amr
    )
    if context.package_enabled("opencore-amr") and opencore_version is None:
        opencore_version = OPENCORE_AMR_FALLBACK_VERSION
        context.logger.warn(
            f"Falling back to opencore-amr '{opencore_version}' because its official release "
            "index is unavailable."
        )
    if context.build("opencore-amr", opencore_version):
        source = context.download(
            "https://downloads.sourceforge.net/project/opencore-amr/opencore-amr"
            f"/opencore-amr-{opencore_version}.tar.gz",
            f"opencore-amr-{opencore_version}.tar.gz",
        )
        configure_make_install(context, source, "--disable-shared")
        context.build_done("opencore-amr", opencore_version)
    context.append_configure_options_if_enabled(
        "opencore-amr", "--enable-libopencore-amrnb", "--enable-libopencore-amrwb"
    )

    if context.build("liblame", LAME_VERSION):
        source = context.download(
            f"https://downloads.sourceforge.net/project/lame/lame/{LAME_VERSION}"
            f"/lame-{LAME_VERSION}.tar.gz",
            f"liblame-{LAME_VERSION}.tar.gz",
        )
        iconv_options: list[str] = []
        if context.package_enabled("libiconv") and (workspace / "lib/libiconv.a").is_file():
            iconv_options.append(f"--with-libiconv-prefix={workspace}")
        configure_make_install(
            context,
            source,
            *[f"--disable-{feature}" for feature in ("gtktest", "shared")],
            "--enable-nasm",
            *iconv_options,
        )
        context.build_done("liblame", LAME_VERSION)
    context.append_configure_options_if_enabled("liblame", "--enable-libmp3lame")

    theora_version = context.fetch_version_if_enabled(
        "libtheora", lambda: find_git_repo(context.versions, "xiph/theora", 1)
    )
    if context.build("libtheora", theora_version):
        source = context.download(
            f"https://github.com/xiph/theora/archive/refs/tags/v{theora_version}.tar.gz",
            f"libtheora-{theora_version}.tar.gz",
        )
        ensure_autotools(context, source)
        ogg_include_dir = workspace_or_pkgconf_include_dir(
            context, "libogg", "ogg", workspace / "lib/libogg.a"
        )
        if ogg_include_dir is None:
            raise BuildError(
                "Theora needs Ogg headers; enable 'packages.libogg' or install a system "
                "libogg development package."
            )
        ogg_library_dir = workspace_or_pkgconf_library_dir(
            context, "libogg", "ogg", workspace / "lib/libogg.a"
        )
        if ogg_library_dir is None:
            raise BuildError(
                "Theora needs the Ogg library; enable 'packages.libogg' or install a system "
                "libogg development package."
            )
        # Vorbis and SDL are requirements of upstream's example programs, not of
        # the core Theora/Ogg library FFmpeg consumes.
        configure_make_install(
            context,
            source,
            *[
                f"--disable-{feature}"
                for feature in (
                    "doc",
                    "examples",
                    "oggtest",
                    "sdltest",
                    "shared",
                    "spec",
                    "vorbistest",
                )
            ],
            "--enable-static",
            f"--with-ogg-includes={ogg_include_dir}",
            f"--with-ogg-libraries={ogg_library_dir}",
        )
        context.build_done("libtheora", theora_version)
    context.append_configure_options_if_enabled("libtheora", "--enable-libtheora")
