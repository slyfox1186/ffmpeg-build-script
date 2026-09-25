"""Video codecs, quality metrics, and frame-server integrations."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from ..runtime.buildsys import CMAKE_NO_PACKAGE_REGISTRY_OPTIONS, meson_project_option_exists
from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.fetchers import find_git_repo, rav1e_download_url
from ..runtime.paths import safe_remove_tree
from ..runtime.versioncmp import version_sort
from .helpers import (
    check_and_install_cargo_c,
    cmake_ninja_install,
    configure_make_install,
    ensure_autotools,
    install_rustup,
    meson_ninja_install,
    pkgconfig_add_private_lib,
    require_release,
    setup_python_venv,
)
from .system_setup import check_avx512, set_ant_path


def use_vapoursynth_python_environment(context: BuildContext) -> None:
    """Put VapourSynth's virtual environment on PATH.

    Both branches of its build need this: one to build it, the other because
    FFmpeg's configure still has to find it on a rerun that skips the build.
    """
    venv_bin = context.workspace / "python_virtual_environment/vapoursynth/bin"
    context.env["PYTHON"] = str(venv_bin / "python")
    context.path_prepend(venv_bin)
    ccache_directory = context.env.get("ccache_dir", "")
    if ccache_directory:
        context.path_prepend(ccache_directory)


def install_video_libraries(context: BuildContext) -> None:
    context.logger.banner("Installing Video Tools")
    workspace = context.workspace
    packages = context.packages

    av1_commit = context.git_snapshot("https://aomedia.googlesource.com/aom", "av1-git")
    if context.build("av1-git", av1_commit):
        cmake_ninja_install(
            context,
            packages / "av1-git",
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            *[
                f"-DCONFIG_AV1_{feature}=1"
                for feature in ("DECODER", "ENCODER", "HIGHBITDEPTH", "TEMPORAL_DENOISING")
            ],
            "-DCONFIG_DENOISE=1",
            "-DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1",
            "-DCONFIG_PIC=1",
            "-DCONFIG_SHARED=0",
            "-DENABLE_CCACHE=1",
            "-DENABLE_DOCS=0",
            "-DENABLE_EXAMPLES=0",
            "-DENABLE_NASM=1",
            "-DENABLE_TESTDATA=0",
            "-DENABLE_TESTS=0",
            "-DENABLE_TOOLS=0",
        )
        context.build_done("av1-git", av1_commit)
    context.append_configure_options_if_enabled("av1-git", "--enable-libaom")

    # VMAF is not packaged for Debian or Ubuntu. `built_in_models` embeds the
    # default models so the filter works without external files, and
    # `enable_float` adds the extractors the standard VMAF model needs.
    vmaf_version = context.fetch_version_if_enabled(
        "libvmaf", lambda: find_git_repo(context.versions, "Netflix/vmaf", 1)
    )
    if context.build("libvmaf", vmaf_version):
        source = context.download(
            f"https://github.com/Netflix/vmaf/archive/refs/tags/v{vmaf_version}.tar.gz",
            f"libvmaf-{vmaf_version}.tar.gz",
        )
        meson_ninja_install(
            context,
            source / "libvmaf",
            "build",
            "--buildtype=release",
            "--default-library=static",
            "-Denable_tests=false",
            "-Denable_docs=false",
            "-Denable_tools=false",
            "-Dbuilt_in_models=true",
            "-Denable_float=true",
        )
        context.build_done("libvmaf", vmaf_version)
    # libvmaf bundles C++ but its generated .pc omits the C++ runtime, so a
    # static link through FFmpeg's C driver fails with undefined operator
    # new[]/delete[]. Run this on the skip path too, and idempotently, so an
    # already-installed libvmaf is fixed without forcing a rebuild.
    if context.package_enabled("libvmaf"):
        pkgconfig_add_private_lib(context, "libvmaf", "-lstdc++")
    context.append_configure_options_if_enabled("libvmaf", "--enable-libvmaf")

    rav1e_version = context.fetch_version_if_enabled(
        "rav1e", lambda: find_git_repo(context.versions, "xiph/rav1e", 1)
    )
    if context.build("rav1e", rav1e_version):
        assert rav1e_version is not None
        source = context.download(
            rav1e_download_url(rav1e_version), f"rav1e-{rav1e_version}.tar.gz"
        )
        install_rustup(context)
        check_and_install_cargo_c(context)
        context.execute(
            [
                "cargo",
                "cinstall",
                "--locked",
                f"--prefix={workspace}",
                f"--libdir={workspace}/lib",
                "--library-type=staticlib",
                "--release",
            ],
            cwd=source,
        )
        context.build_done("rav1e", rav1e_version)
    context.append_configure_options_if_enabled("rav1e", "--enable-librav1e")

    zimg_commit = context.git_snapshot(
        "https://github.com/sekrit-twc/zimg.git", "zimg-git", "recurse"
    )
    if context.build("zimg-git", zimg_commit):
        source = packages / "zimg-git"
        ensure_autotools(context, source)
        configure_make_install(context, source, "--with-pic", "--disable-shared", "--enable-static")
        context.build_done("zimg-git", zimg_commit)
    context.append_configure_options_if_enabled("zimg-git", "--enable-libzimg")

    avif_version = context.fetch_version_if_enabled(
        "avif", lambda: find_git_repo(context.versions, "AOMediaCodec/libavif", 1)
    )
    if context.build("avif", avif_version):
        source = context.download(
            f"https://github.com/AOMediaCodec/libavif/archive/refs/tags/v{avif_version}.tar.gz",
            f"avif-{avif_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DAVIF_BUILD_APPS=OFF",
            "-DAVIF_BUILD_EXAMPLES=OFF",
            "-DAVIF_BUILD_MAN_PAGES=OFF",
            "-DAVIF_BUILD_TESTS=OFF",
            "-DAVIF_CODEC_AOM=SYSTEM",
            "-DAVIF_CODEC_AOM_DECODE=ON",
            "-DAVIF_CODEC_AOM_ENCODE=ON",
            "-DAVIF_CODEC_AVM=OFF",
            "-DAVIF_CODEC_DAV1D=OFF",
            "-DAVIF_CODEC_LIBGAV1=OFF",
            "-DAVIF_CODEC_RAV1E=OFF",
            "-DAVIF_CODEC_SVT=OFF",
            "-DAVIF_ENABLE_WERROR=OFF",
            "-DAVIF_JPEG=OFF",
            "-DAVIF_LIBYUV=OFF",
            "-DAVIF_ZLIBPNG=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
        )
        context.build_done("avif", avif_version)

    kvazaar_version = context.fetch_version_if_enabled(
        "kvazaar", lambda: find_git_repo(context.versions, "ultravideo/kvazaar", 1)
    )
    if context.build("kvazaar", kvazaar_version):
        source = context.download(
            f"https://github.com/ultravideo/kvazaar/archive/refs/tags/v{kvazaar_version}.tar.gz",
            f"kvazaar-{kvazaar_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DBUILD_KVAZAAR_BINARY=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTS=OFF",
        )
        context.build_done("kvazaar", kvazaar_version)
    context.append_configure_options_if_enabled("kvazaar", "--enable-libkvazaar")

    # libdvdread and libdvdnav build in every configuration. Only their FFmpeg
    # integration waits for the licence flag, which the FFmpeg stage applies.
    dvdread_version = context.fetch_version_if_enabled(
        "libdvdread", lambda: find_git_repo(context.versions, "76", 1)
    )
    if context.build("libdvdread", dvdread_version):
        source = context.download(
            f"https://code.videolan.org/videolan/libdvdread/-/archive/{dvdread_version}"
            f"/libdvdread-{dvdread_version}.tar.bz2"
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--default-library=static",
            "--buildtype=release",
            "-Denable_docs=false",
            "-Dlibdvdcss=disabled",
        )
        context.build_done("libdvdread", dvdread_version)

    dvdnav_version = context.fetch_version_if_enabled(
        "libdvdnav", lambda: find_git_repo(context.versions, "206", 1)
    )
    if context.build("libdvdnav", dvdnav_version):
        source = context.download(
            f"https://code.videolan.org/videolan/libdvdnav/-/archive/{dvdnav_version}"
            f"/libdvdnav-{dvdnav_version}.tar.bz2"
        )
        meson_ninja_install(
            context, source, "build", "--default-library=static", "--buildtype=release"
        )
        context.build_done("libdvdnav", dvdnav_version)

    udfread_version = context.fetch_version_if_enabled(
        "udfread", lambda: find_git_repo(context.versions, "363", 1)
    )
    if context.build("udfread", udfread_version):
        source = context.download(
            f"https://code.videolan.org/videolan/libudfread/-/archive/{udfread_version}"
            f"/libudfread-{udfread_version}.tar.bz2"
        )
        meson_ninja_install(
            context,
            source,
            "build",
            "--default-library=static",
            "--buildtype=release",
            "-Denable_examples=false",
        )
        context.build_done("udfread", udfread_version)

    # Ant is built only when selected: no other recipe should force a JDK
    # install or create an Ant prefix for a disabled ancillary tool.
    if context.package_enabled("ant-git"):
        set_ant_path(context)
        ant_commit = context.git_snapshot("https://github.com/apache/ant.git", "ant-git")
        if context.build("ant-git", ant_commit):
            source = packages / "ant-git"
            context.execute(["chmod", "-R", "u+rwX,go+rX", str(workspace / "ant")])
            context.execute(["sh", "build.sh", "install-lite"], cwd=source)
            context.build_done("ant-git", ant_commit)
        # Outside the build block: a rerun that skips the build still has to
        # expose the installed Ant to everything that follows.
        context.path_prepend(workspace / "ant/bin")

    _install_mediaarea(context)

    if context.nonfree_and_gpl:
        _install_gpl_video(context)

    gpac_commit = context.git_snapshot("https://github.com/gpac/gpac.git", "gpac-git")
    if context.build("gpac-git", gpac_commit):
        source = packages / "gpac-git"
        sdl_options: list[str] = []
        if context.package_enabled("sdl2") and os.access(workspace / "bin/sdl2-config", os.X_OK):
            sdl_options.append(f"--sdl-cfg={workspace}/bin/sdl2-config")
        elif context.package_enabled("sdl2"):
            system_sdl_config = context.runner.which("sdl2-config")
            if system_sdl_config is not None:
                sdl_options.append(f"--sdl-cfg={system_sdl_config}")
        # --use-ogg=no prevents symbol conflicts with libogg.a: GPAC carries an
        # internal Ogg implementation. The remaining optional libraries are left
        # for configure to discover rather than claimed as nonexistent "local"
        # copies.
        configure_make_install(
            context, source, "--static-bin", "--static-modules", "--use-ogg=no", *sdl_options
        )
        context.build_done("gpac-git", gpac_commit)

    svt_version = context.fetch_version_if_enabled(
        "svt-av1", lambda: find_git_repo(context.versions, "24327400", 1)
    )
    if context.build("svt-av1", svt_version):
        source = context.download(
            f"https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v{svt_version}"
            f"/SVT-AV1-v{svt_version}.tar.bz2",
            f"svt-av1-{svt_version}.tar.bz2",
        )
        cmake_ninja_install(
            context,
            source,
            "Build/linux",
            "-S",
            ".",
            "-DBUILD_APPS=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTING=OFF",
            # FFmpeg links with the host linker; LLVM bitcode from SVT's
            # default LTO cannot be consumed by a normal GNU ld link.
            "-DSVT_AV1_LTO=OFF",
            f"-DENABLE_AVX512={check_avx512()}",
            "-DEXCLUDE_HASH=ON",
            "-DNATIVE=ON",
            "-DREPRODUCIBLE_BUILDS=ON",
        )
        context.build_done("svt-av1", svt_version)
    context.append_configure_options_if_enabled("svt-av1", "--enable-libsvtav1")

    _install_vapoursynth(context)

    libgav1_commit = context.git_snapshot(
        "https://chromium.googlesource.com/codecs/libgav1", "libgav1-git"
    )
    if context.build("libgav1-git", libgav1_commit):
        cmake_ninja_install(
            context,
            packages / "libgav1-git",
            "build",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DLIBGAV1_ENABLE_EXAMPLES=OFF",
            "-DLIBGAV1_ENABLE_TESTS=OFF",
            "-DLIBGAV1_THREADPOOL_USE_STD_MUTEX=1",
        )
        context.build_done("libgav1-git", libgav1_commit)


def _install_mediaarea(context: BuildContext) -> None:
    zenlib_version = context.fetch_version_if_enabled(
        "zenlib", lambda: find_git_repo(context.versions, "MediaArea/ZenLib", 1)
    )
    if context.build("zenlib", zenlib_version):
        source = context.download(
            f"https://github.com/MediaArea/ZenLib/archive/refs/tags/v{zenlib_version}.tar.gz",
            f"zenlib-{zenlib_version}.tar.gz",
        )
        project = source / "Project/GNU/Library"
        ensure_autotools(context, project)
        configure_make_install(context, project, "--disable-shared")
        context.build_done("zenlib", zenlib_version)

    mediainfo_lib_version = context.fetch_version_if_enabled(
        "mediainfo-lib", lambda: find_git_repo(context.versions, "MediaArea/MediaInfoLib", 1)
    )
    if context.build("mediainfo-lib", mediainfo_lib_version):
        source = context.download(
            "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/"
            f"v{mediainfo_lib_version}.tar.gz",
            f"mediainfo-lib-{mediainfo_lib_version}.tar.gz",
        )
        project = source / "Project/GNU/Library"
        ensure_autotools(context, project)
        configure_make_install(context, project, "--disable-shared")
        context.build_done("mediainfo-lib", mediainfo_lib_version)

    mediainfo_cli_version = context.fetch_version_if_enabled(
        "mediainfo-cli", lambda: find_git_repo(context.versions, "MediaArea/MediaInfo", 1)
    )
    if context.build("mediainfo-cli", mediainfo_cli_version):
        source = context.download(
            f"https://github.com/MediaArea/MediaInfo/archive/refs/tags/v{mediainfo_cli_version}.tar.gz",
            f"mediainfo-cli-{mediainfo_cli_version}.tar.gz",
        )
        project = source / "Project/GNU/CLI"
        ensure_autotools(context, project)
        configure_make_install(context, project, "--enable-staticlibs", "--disable-shared")
        context.build_done("mediainfo-cli", mediainfo_cli_version)


def _install_gpl_video(context: BuildContext) -> None:
    workspace = context.workspace

    vid_stab_version = context.fetch_version_if_enabled(
        "vid-stab", lambda: find_git_repo(context.versions, "georgmartius/vid.stab", 1)
    )
    if context.build("vid-stab", vid_stab_version):
        source = context.download(
            f"https://github.com/georgmartius/vid.stab/archive/refs/tags/v{vid_stab_version}.tar.gz",
            f"vid-stab-{vid_stab_version}.tar.gz",
        )
        cmake_ninja_install(
            context,
            source,
            "build",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DUSE_OMP=ON",
        )
        context.build_done("vid-stab", vid_stab_version)
    context.append_configure_options_if_enabled("vid-stab", "--enable-libvidstab")

    # x264's "version" is the 40-character commit on its stable branch; it has
    # no release tags.
    x264_version = context.fetch_version_if_enabled(
        "x264", lambda: find_git_repo(context.versions, "536", 1)
    )
    if context.build("x264", x264_version):
        source = context.download(
            f"https://code.videolan.org/videolan/x264/-/archive/{x264_version}"
            f"/x264-{x264_version}.tar.bz2"
        )
        configure_make_install(
            context,
            source,
            "--bit-depth=all",
            "--chroma-format=all",
            "--enable-pic",
            "--enable-static",
            "--enable-strip",
            "--disable-bashcompletion",
            "--disable-cli",
            f"--extra-cflags={context.env.get('CFLAGS', '')}",
            f"--extra-ldflags={context.env.get('LDFLAGS', '')}",
            install_target="install-lib-static",
        )
        context.build_done("x264", x264_version)
    context.append_configure_options_if_enabled("x264", "--enable-libx264")

    x265_release = context.fetch_version_if_enabled("x265", context.versions.x265)
    if context.package_enabled("x265") and x265_release is None:
        raise BuildError("Failed to detect the latest stable 'x265' release.")
    if context.build("x265", x265_release):
        assert x265_release is not None
        _build_x265(context, x265_release)

    context.append_configure_options_if_enabled("x265", "--enable-libx265")

    # NVIDIA codec interfaces need these headers even when the optional CUDA
    # toolkit, used for CUDA-compiled filters, is not installed.
    if context.nvidia_gpu_present and context.package_enabled("nv-codec-headers"):
        nv_version = context.fetch_version_if_enabled(
            "nv-codec-headers", context.versions.nv_codec_headers
        )
        if nv_version is None:
            raise BuildError("Failed to detect 'nv-codec-headers' version.")
        if context.build("nv-codec-headers", nv_version):
            source = context.download(
                f"https://github.com/FFmpeg/nv-codec-headers/archive/refs/tags/n{nv_version}.tar.gz",
                f"nv-codec-headers-{nv_version}.tar.gz",
            )
            context.make(source)
            context.make(source, "install", jobs=False, PREFIX=str(workspace))
            context.build_done("nv-codec-headers", nv_version)

    if context.amd_gpu_present:
        amf_version = context.fetch_version_if_enabled(
            "amf-headers",
            lambda: find_git_repo(context.versions, "GPUOpen-LibrariesAndSDKs/AMF", 1),
        )
        if context.build("amf-headers", amf_version):
            source = context.download(
                "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/releases/download/"
                f"v{amf_version}/AMF-headers-v{amf_version}.tar.gz"
            )
            safe_remove_tree(workspace / "include/AMF", workspace)
            context.execute(["cp", "-fr", "AMF", f"{workspace}/include/"], cwd=source)
            context.build_done("amf-headers", amf_version)
        context.append_configure_options_if_enabled("amf-headers", "--enable-amf")
    else:
        context.logger.info(
            "No AMD GPU detected; skipping AMF (AMD encoder) headers and '--enable-amf'."
        )

    srt_version = context.fetch_version_if_enabled(
        "srt", lambda: find_git_repo(context.versions, "Haivision/srt", 1)
    )
    if context.build("srt", srt_version):
        source = context.download(
            f"https://github.com/Haivision/srt/archive/refs/tags/v{srt_version}.tar.gz",
            f"srt-{srt_version}.tar.gz",
        )
        openssl_overrides: dict[str, str] = {}
        workspace_ssl = any(
            (workspace / candidate).is_file()
            for candidate in ("lib/libssl.a", "lib/libssl.so", "lib64/libssl.a", "lib64/libssl.so")
        )
        if context.package_enabled("openssl") and workspace_ssl:
            library_dir = (
                "lib64"
                if (
                    (workspace / "lib64/libssl.a").is_file()
                    or (workspace / "lib64/libssl.so").is_file()
                )
                else "lib"
            )
            openssl_overrides = {
                "OPENSSL_ROOT_DIR": str(workspace),
                "OPENSSL_LIB_DIR": f"{workspace}/{library_dir}",
                "OPENSSL_INCLUDE_DIR": f"{workspace}/include",
            }
        else:
            context.logger.info("Using system OpenSSL fallback for SRT")
        previous = {
            name: context.env.get(name)
            for name in ("OPENSSL_ROOT_DIR", "OPENSSL_LIB_DIR", "OPENSSL_INCLUDE_DIR")
        }
        context.env.update(openssl_overrides)
        try:
            cmake_ninja_install(
                context,
                source,
                "build",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DENABLE_APPS=OFF",
                "-DENABLE_ENCRYPTION=ON",
                "-DENABLE_HEAVY_LOGGING=OFF",
                "-DENABLE_LOGGING=ON",
                "-DENABLE_SHARED=OFF",
                "-DENABLE_STATIC=ON",
                "-DENABLE_UNITTESTS=OFF",
                "-DOPENSSL_USE_STATIC_LIBS=TRUE",
                "-DUSE_OPENSSL_PC=ON",
            )
        finally:
            for name, value in previous.items():
                if value is None:
                    context.env.pop(name, None)
                else:
                    context.env[name] = value
        context.build_done("srt", srt_version)
    context.append_configure_options_if_enabled("srt", "--enable-libsrt")

    avisynth_version = context.fetch_version_if_enabled(
        "avisynth", lambda: find_git_repo(context.versions, "AviSynth/AviSynthPlus", 1)
    )
    if context.build("avisynth", avisynth_version):
        source = context.download(
            f"https://github.com/AviSynth/AviSynthPlus/archive/refs/tags/v{avisynth_version}.tar.gz",
            f"avisynth-{avisynth_version}.tar.gz",
        )
        context.execute(
            [
                "cmake",
                "-B",
                "build",
                f"-DCMAKE_INSTALL_PREFIX={workspace}",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DHEADERS_ONLY=OFF",
                "-DENABLE_PLUGINS=OFF",
                *CMAKE_NO_PACKAGE_REGISTRY_OPTIONS,
                "-Wno-dev",
            ],
            cwd=source,
        )
        context.execute(
            ["make", f"-j{context.build_threads}", "-C", "build", "VersionGen", "install"],
            cwd=source,
        )
        context.build_done("avisynth", avisynth_version)
    context.append_configure_options_if_enabled("avisynth", "--enable-avisynth")

    xvidcore_release = context.fetch_version_if_enabled("xvidcore", context.versions.xvidcore)
    if context.build("xvidcore", xvidcore_release):
        source = context.download(
            f"https://downloads.xvid.com/downloads/xvidcore-{xvidcore_release}.tar.bz2"
        )
        generic = source / "build/generic"
        context.execute(["sh", "bootstrap.sh"], cwd=generic)
        # Xvid's bool typedef predates C23. Keep its int representation and
        # constrain only this recipe when newer Autoconf selects GNU C23.
        context.execute(
            ["sh", "configure", f"--prefix={workspace}"],
            cwd=generic,
            env_overrides={"CFLAGS": f"{context.env.get('CFLAGS', '')} -std=gnu17".strip()},
        )
        # Upstream's all/install targets unconditionally build and install both
        # variants. FFmpeg needs only xvid.h and libxvidcore.a.
        context.make(generic, "libxvidcore.a")
        context.execute(
            ["install", "-Dm0644", "=build/libxvidcore.a", str(workspace / "lib/libxvidcore.a")],
            cwd=generic,
        )
        context.execute(
            ["install", "-Dm0644", "../../src/xvid.h", str(workspace / "include/xvid.h")],
            cwd=generic,
        )
        context.build_done("xvidcore", xvidcore_release)
    context.append_configure_options_if_enabled("xvidcore", "--enable-libxvid")


def _build_x265(context: BuildContext, release: str) -> None:
    """Build x265 as one static archive covering 8, 10 and 12-bit depths.

    Upstream supports only one bit depth per library, so the 10- and 12-bit
    libraries are built with their C API hidden, linked into the 8-bit build,
    and then merged with `ar -M` into a single archive FFmpeg can link once.
    """
    workspace = context.workspace
    source = context.download(
        f"https://github.com/Multicorewareinc/x265/archive/refs/tags/{release}.tar.gz",
        f"x265-{release}.tar.gz",
    )
    linux_build = source / "build/linux"
    for depth in ("8bit", "10bit", "12bit"):
        safe_remove_tree(linux_build / depth, linux_build)
        (linux_build / depth).mkdir(parents=True)

    shared_options = [
        f"-DCMAKE_INSTALL_PREFIX={workspace}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        "-DENABLE_PIC=ON",
        "-DENABLE_LIBNUMA=OFF",
        "-DNATIVE_BUILD=ON",
        *CMAKE_NO_PACKAGE_REGISTRY_OPTIONS,
        "-G",
        "Ninja",
        "-Wno-dev",
    ]

    context.logger.info("Building x265 12-bit library")
    context.execute(
        [
            "cmake",
            "../../../source",
            *[f"-DENABLE_{option}=OFF" for option in ("CLI", "LIBVMAF", "SHARED")],
            "-DEXPORT_C_API=OFF",
            "-DHIGH_BIT_DEPTH=ON",
            "-DMAIN12=ON",
            *shared_options,
        ],
        cwd=linux_build / "12bit",
    )
    context.execute(["ninja", f"-j{context.build_threads}"], cwd=linux_build / "12bit")

    context.logger.info("Building x265 10-bit library")
    context.execute(
        [
            "cmake",
            "../../../source",
            *[f"-DENABLE_{option}=OFF" for option in ("CLI", "LIBVMAF", "SHARED")],
            "-DENABLE_HDR10_PLUS=ON",
            "-DEXPORT_C_API=OFF",
            "-DHIGH_BIT_DEPTH=ON",
            *shared_options,
        ],
        cwd=linux_build / "10bit",
    )
    context.execute(["ninja", f"-j{context.build_threads}"], cwd=linux_build / "10bit")

    context.logger.info("Building x265 8-bit library")
    eight_bit = linux_build / "8bit"
    context.execute(["ln", "-sf", "../10bit/libx265.a", "libx265_main10.a"], cwd=eight_bit)
    context.execute(["ln", "-sf", "../12bit/libx265.a", "libx265_main12.a"], cwd=eight_bit)
    context.execute(
        [
            "cmake",
            "../../../source",
            *[f"-DENABLE_{option}=OFF" for option in ("CLI", "LIBVMAF")],
            "-DENABLE_SHARED=OFF",
            "-DEXTRA_LIB=x265_main10.a;x265_main12.a",
            "-DEXTRA_LINK_FLAGS=-L.",
            *[f"-DLINKED_{depth}=ON" for depth in ("10BIT", "12BIT")],
            *shared_options,
        ],
        cwd=eight_bit,
    )
    context.execute(["ninja", f"-j{context.build_threads}"], cwd=eight_bit)
    # Install headers and metadata while Ninja's declared 8-bit archive still
    # exists, then replace only the installed archive with the merged result.
    context.execute(["ninja", "install"], cwd=eight_bit)

    context.execute(["mv", "libx265.a", "libx265_main.a"], cwd=eight_bit)
    context.execute(
        ["ar", "-M"],
        cwd=eight_bit,
        stdin_text=(
            "CREATE libx265.a\n"
            "ADDLIB libx265_main.a\n"
            "ADDLIB libx265_main10.a\n"
            "ADDLIB libx265_main12.a\n"
            "SAVE\n"
        ),
    )
    context.execute(["ranlib", "libx265.a"], cwd=eight_bit)
    context.execute(
        ["install", "-Dm0644", "libx265.a", str(workspace / "lib/libx265.a")], cwd=eight_bit
    )
    pkgconfig_add_private_lib(context, "x265", "-lstdc++")
    context.build_done("x265", release)


def _install_vapoursynth(context: BuildContext) -> None:
    workspace = context.workspace
    version = context.fetch_version_if_enabled(
        "vapoursynth", lambda: find_git_repo(context.versions, "vapoursynth/vapoursynth", 1)
    )
    marker_version = f"R{version}" if version else None
    if context.build("vapoursynth", marker_version):
        source = context.download(
            f"https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R{version}.tar.gz",
            f"vapoursynth-R{version}.tar.gz",
        )
        setup_python_venv(
            context,
            workspace / "python_virtual_environment/vapoursynth",
            [f"Cython=={require_release(context.versions.cython(), 'Cython')}"],
        )
        use_vapoursynth_python_environment(context)

        # Meson's Python dependency detection reads these.
        cflags = context.runner.capture(["python3-config", "--cflags"])
        if cflags.returncode != 0:
            raise BuildError("'python3-config --cflags' failed.")
        context.env["PYTHON3_CFLAGS"] = cflags.stdout.strip()
        ldflags = context.runner.capture(["python3-config", "--ldflags", "--embed"])
        if ldflags.returncode != 0:
            ldflags = context.runner.capture(["python3-config", "--ldflags"])
        if ldflags.returncode != 0:
            raise BuildError("'python3-config --ldflags' failed.")
        context.env["PYTHON3_LIBS"] = ldflags.stdout.strip()

        options: list[str] = []
        for option_name in ("enable_python_module", "enable_vspipe"):
            if meson_project_option_exists(source, option_name):
                options.append(f"-D{option_name}=false")

        meson_ninja_install(
            context,
            source,
            "build",
            "--buildtype=release",
            "--default-library=both",
            "--strip",
            *options,
        )
        if not normalize_vapoursynth_sdk(context):
            raise BuildError(
                "VapourSynth built, but its FFmpeg SDK files could not be exposed from the "
                "Python site-packages install."
            )
        context.build_done("vapoursynth", marker_version)
    else:
        if context.package_enabled("vapoursynth"):
            if not normalize_vapoursynth_sdk(context):
                raise BuildError(
                    "VapourSynth is enabled but its FFmpeg SDK files are missing. Run "
                    f"'rm -f -- {context.packages}/vapoursynth.done' to rebuild it."
                )
            use_vapoursynth_python_environment(context)
    context.append_configure_options_if_enabled("vapoursynth", "--enable-vapoursynth")


def find_vapoursynth_sdk_dir(workspace: Path) -> Path | None:
    """Locate the SDK VapourSynth installs under its Python site-packages."""
    candidates: list[Path] = []
    for directory, _directories, files in os.walk(workspace):
        if "VSScript4.h" not in files:
            continue
        header = Path(directory) / "VSScript4.h"
        if header.parent.name != "include" or header.parent.parent.name != "vapoursynth":
            continue
        sdk_dir = header.parent.parent
        if (sdk_dir / "include/VapourSynth4.h").is_file():
            candidates.append(sdk_dir)
    if not candidates:
        return None
    ordered = version_sort([str(candidate) for candidate in candidates])
    return Path(ordered[0])


def normalize_vapoursynth_sdk(context: BuildContext) -> bool:
    """Expose VapourSynth's headers, library and metadata where FFmpeg looks.

    Upstream installs the SDK beside its Python module rather than under the
    prefix, and publishes no usable `.pc`, so this copies the pieces into the
    workspace and writes the metadata FFmpeg's configure expects.
    """
    workspace = context.workspace
    sdk_dir = find_vapoursynth_sdk_dir(workspace)
    if sdk_dir is None:
        return False
    sdk_include = sdk_dir / "include"
    if (
        not (sdk_include / "VSScript4.h").is_file()
        or not (sdk_include / "VapourSynth4.h").is_file()
    ):
        return False

    (workspace / "include/vapoursynth").mkdir(parents=True, exist_ok=True)
    (workspace / "lib/pkgconfig").mkdir(parents=True, exist_ok=True)
    for header in sdk_include.glob("*.h"):
        shutil.copy2(header, workspace / "include/vapoursynth" / header.name)

    libraries = [
        entry
        for entry in sdk_dir.iterdir()
        if entry.name.startswith(("libvsscript.so", "libvapoursynth.so"))
    ]
    for entry in sorted(libraries, key=lambda item: item.name):
        destination = workspace / "lib" / entry.name
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        if entry.is_symlink():
            os.symlink(os.readlink(entry), destination)
        else:
            shutil.copy2(entry, destination)

    script_libraries = version_sort(
        [
            entry.name
            for entry in (workspace / "lib").iterdir()
            if entry.name.startswith("libvsscript.so")
        ]
    )
    if not script_libraries:
        return False
    link_path = workspace / "lib/libvapoursynth-script.so"
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    os.symlink(script_libraries[0], link_path)

    pc_version = "unknown"
    sdk_pc = sdk_dir / "pkgconfig/vapoursynth.pc"
    if sdk_pc.is_file():
        for line in sdk_pc.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Version:"):
                pc_version = line.split(":", 1)[1].strip() or "unknown"
                break

    payload = (
        "\n".join(
            [
                f"prefix={workspace}",
                "includedir=${prefix}/include",
                "libdir=${prefix}/lib",
                "",
                "Name: vapoursynth",
                "Description: A frameserver for the 21st century",
                f"Version: {pc_version}",
                "Cflags: -I${includedir}",
                "Libs: -L${libdir} -lvapoursynth-script",
            ]
        )
        + "\n"
    )
    pc_directory = workspace / "lib/pkgconfig"
    handle, temporary_name = tempfile.mkstemp(prefix=".vapoursynth.pc.", dir=pc_directory)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(payload)
    os.chmod(temporary_name, 0o644)
    os.replace(temporary_name, pc_directory / "vapoursynth.pc")
    return True
