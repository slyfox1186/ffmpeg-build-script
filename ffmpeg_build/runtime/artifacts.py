"""What has to exist in the workspace for a build marker to be believed.

A `.done` marker records a version; it does not prove the files that version
produced are still there. Checking the artifact as well is what turns a
workspace someone partially deleted into an automatic rebuild instead of a link
failure hours later.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

# Packages whose artifact is a pkg-config module under a different name.
PKGCONF_MODULES: dict[str, tuple[str, ...]] = {
    "opencore-amr": ("opencore-amrnb", "opencore-amrwb"),
    "nettle": ("nettle", "hogweed"),
    "brotli": ("libbrotlicommon", "libbrotlidec", "libbrotlienc"),
    "vorbis": ("vorbis", "vorbisenc"),
    "lilv": ("lilv-0",),
    "av1-git": ("aom",),
    "libvmaf": ("libvmaf",),
    "rav1e": ("rav1e",),
    "zimg-git": ("zimg",),
    "x264": ("x264",),
    "x265": ("x265",),
    "nv-codec-headers": ("ffnvcodec",),
    "libxml2": ("libxml-2.0",),
    "libtiff": ("libtiff-4",),
    "freetype": ("freetype2",),
    "libwebp-git": ("libwebp",),
    "libjpeg-turbo": ("libjpeg",),
    "rubberband-git": ("rubberband",),
    "c-ares": ("libcares",),
    "serd": ("serd-0",),
    "pcre2": ("libpcre2-8",),
    "zix": ("zix-0",),
    "sord": ("sord-0",),
    "sratom": ("sratom-0",),
    "libsoxr": ("soxr",),
    "sdl2": ("sdl2",),
    "libsndfile": ("sndfile",),
    "libogg": ("ogg",),
    "libfdk-aac": ("fdk-aac",),
    "libopus": ("opus",),
    "avif": ("libavif",),
    "libdvdread": ("dvdread",),
    "libdvdnav": ("dvdnav",),
    "udfread": ("libudfread",),
    "zenlib": ("libzen",),
    "mediainfo-lib": ("libmediainfo",),
    "vid-stab": ("vidstab",),
    "svt-av1": ("SvtAv1Enc",),
    "libheif": ("libheif",),
    "openjpeg": ("libopenjp2",),
}

# Packages whose own name is the pkg-config module name.
for _same_name in (
    "libzstd",
    "librist",
    "zlib",
    "openssl",
    "libpng",
    "fontconfig",
    "harfbuzz",
    "fribidi",
    "libass",
    "gnutls",
    "libhwy",
    "lcms2",
    "gflags",
    "jemalloc",
    "libmysofa",
    "kvazaar",
    "srt",
):
    PKGCONF_MODULES.setdefault(_same_name, (_same_name,))


def _any_file(workspace: Path, *candidates: str) -> bool:
    return any((workspace / candidate).is_file() for candidate in candidates)


def _executable(workspace: Path, candidate: str) -> bool:
    path = workspace / candidate
    return path.is_file() and path.stat().st_mode & 0o111 != 0


# Packages proven by a file rather than by pkg-config metadata.
FILE_ARTIFACTS: dict[str, Callable[[Path], bool]] = {
    "m4": lambda workspace: _executable(workspace, "bin/m4"),
    "autoconf": lambda workspace: _executable(workspace, "bin/autoconf"),
    "automake": lambda workspace: _executable(workspace, "bin/automake"),
    "libtool": lambda workspace: _executable(workspace, "bin/libtoolize"),
    "cmake": lambda workspace: _executable(workspace, "bin/cmake"),
    "meson": lambda workspace: _executable(
        workspace, "python_virtual_environment/build-tools/bin/meson"
    ),
    "ninja": lambda workspace: _executable(workspace, "bin/ninja"),
    "ant-git": lambda workspace: _executable(workspace, "ant/bin/ant"),
    "mediainfo-cli": lambda workspace: _executable(workspace, "bin/mediainfo"),
    "gpac-git": lambda workspace: (
        _executable(workspace, "bin/MP4Box") or _executable(workspace, "bin/gpac")
    ),
    "yasm": lambda workspace: _executable(workspace, "bin/yasm"),
    "nasm": lambda workspace: _executable(workspace, "bin/nasm"),
    "giflib": lambda workspace: _any_file(workspace, "lib/libgif.a"),
    "libiconv": lambda workspace: _any_file(workspace, "lib/libiconv.a", "lib64/libiconv.a"),
    "gmp": lambda workspace: _any_file(workspace, "lib/libgmp.a", "lib64/libgmp.a"),
    "liblame": lambda workspace: _any_file(workspace, "lib/libmp3lame.a", "lib64/libmp3lame.a"),
    "libtheora": lambda workspace: _any_file(
        workspace, "lib/libtheoraenc.a", "lib64/libtheoraenc.a"
    ),
    "opencl-sdk-git": lambda workspace: (
        _any_file(workspace, "include/CL/cl.h")
        and _any_file(workspace, "lib/libOpenCL.a", "lib64/libOpenCL.a")
    ),
    "vulkan-headers-git": lambda workspace: _any_file(workspace, "include/vulkan/vulkan.h"),
    "lv2-git": lambda workspace: (
        _any_file(workspace, "include/lv2.h") or (workspace / "include/lv2").is_dir()
    ),
    "amf-headers": lambda workspace: _any_file(workspace, "include/AMF/core/Version.h"),
    "libgav1-git": lambda workspace: _any_file(workspace, "lib/libgav1.a", "lib64/libgav1.a"),
    "avisynth": lambda workspace: _any_file(
        workspace, "include/avisynth/avisynth_c.h", "include/avisynth_c.h"
    ),
    "xvidcore": lambda workspace: (
        _any_file(workspace, "lib/libxvidcore.a") and _any_file(workspace, "include/xvid.h")
    ),
    "freeglut": lambda _workspace: False,
}

# freeglut installs its metadata under either name depending on the release.
FREEGLUT_MODULE_ALTERNATIVES = (("glut",), ("freeglut",))


def vapoursynth_sdk_ready(workspace: Path) -> bool:
    """The three files FFmpeg's configure needs from a VapourSynth install."""
    return (
        (workspace / "include/vapoursynth/VSScript4.h").is_file()
        and (workspace / "include/vapoursynth/VapourSynth4.h").is_file()
        and (workspace / "lib/libvapoursynth-script.so").exists()
    )
