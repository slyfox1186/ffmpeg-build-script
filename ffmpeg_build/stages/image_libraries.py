"""Image containers and codecs built after the video codecs they can use."""

from __future__ import annotations

from ..runtime.context import BuildContext
from ..runtime.fetchers import find_git_repo
from .helpers import cmake_ninja_install


def install_image_libraries(context: BuildContext) -> None:
    print()
    context.logger.banner("Installing Image Tools")
    workspace = context.workspace

    libheif_version = context.fetch_version_if_enabled(
        "libheif", lambda: find_git_repo(context.versions, "strukturag/libheif", 1)
    )
    if context.build("libheif", libheif_version):
        source = context.download(
            f"https://github.com/strukturag/libheif/archive/refs/tags/v{libheif_version}.tar.gz",
            f"libheif-{libheif_version}.tar.gz",
        )
        # Each codec is enabled only when it was actually built or installed:
        # libheif's CMake happily configures against a codec it then cannot
        # link, and this stage runs after every one of them.
        with_aom = context.package_enabled("av1-git") and (
            (workspace / "lib/libaom.a").is_file() or (workspace / "lib64/libaom.a").is_file()
        )
        with_dav1d = context.package_enabled("libdav1d") and context.library_exists("dav1d")
        with_libde265 = context.library_exists("libde265")
        with_rav1e = context.package_enabled("rav1e") and (
            (workspace / "lib/librav1e.a").is_file() or (workspace / "lib64/librav1e.a").is_file()
        )
        with_x265 = (
            context.nonfree_and_gpl
            and context.package_enabled("x265")
            and context.library_exists("x265")
        )

        def switch(enabled: bool) -> str:
            return "ON" if enabled else "OFF"

        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_DEVELOPMENT_TOOLS=OFF",
            "-DBUILD_DOCUMENTATION=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTING=OFF",
            f"-DWITH_AOM_DECODER={switch(with_aom)}",
            f"-DWITH_AOM_ENCODER={switch(with_aom)}",
            f"-DWITH_DAV1D={switch(with_dav1d)}",
            f"-DWITH_LIBDE265={switch(with_libde265)}",
            f"-DWITH_RAV1E={switch(with_rav1e)}",
            "-DWITH_X264=OFF",
            f"-DWITH_X265={switch(with_x265)}",
            "-DENABLE_PLUGIN_LOADING=OFF",
            "-DWITH_FUZZERS=OFF",
            "-DWITH_GDK_PIXBUF=OFF",
            "-DWITH_EXAMPLES=OFF",
            "-DWITH_LIBSHARPYUV=OFF",
            "-DWITH_OpenH264_DECODER=OFF",
        )
        context.build_done("libheif", libheif_version)

    openjpeg_version = context.fetch_version_if_enabled(
        "openjpeg", lambda: find_git_repo(context.versions, "uclouvain/openjpeg", 1)
    )
    if context.build("openjpeg", openjpeg_version):
        source = context.download(
            f"https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v{openjpeg_version}",
            f"openjpeg-{openjpeg_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_CODEC=OFF",
            "-DBUILD_DOC=OFF",
            "-DBUILD_JAVA=OFF",
            "-DBUILD_JPIP=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_STATIC_LIBS=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_UNIT_TESTS=OFF",
            "-DBUILD_VIEWER=OFF",
        )
        context.build_done("openjpeg", openjpeg_version)
    context.append_configure_options_if_enabled("openjpeg", "--enable-libopenjpeg")
