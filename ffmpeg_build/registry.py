"""The package registry: every selectable key and what it means.

This is the single source of truth the configuration parser, the build stages,
the host-package collector and the interactive menu all read. Keeping the
metadata here as data rather than spread across imperative recipes is what lets
the menu compute licence gating and requirement closures without executing any
build code.

An unregistered key in a configuration file is a hard error by design: a
misspelled entry must not silently build an unintended default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Kind(Enum):
    """Where a package comes from."""

    SOURCE = "source"
    """Fetched and compiled into the workspace."""

    SYSTEM = "system"
    """Requested from the host archive; no source recipe exists."""

    TOOL = "tool"
    """A build-time program rather than a library FFmpeg links."""


class Gate(Enum):
    """How GPL/non-free authorization affects a package.

    Three states, not two. Rendering the middle one as "blocked" would be
    wrong: `libdvdread` and `libdvdnav` build in every configuration, and only
    their FFmpeg integration waits for the licence flag.
    """

    FREE = "free"
    REQUIRES_GPL = "requires-gpl"
    """The recipe itself is inside the licence gate; nothing happens without it."""

    FLAG_REQUIRES_GPL = "flag-requires-gpl"
    """Always built; only the FFmpeg option is gated."""

    SUPPRESSED_BY_GPL = "suppressed-by-gpl"
    """Skipped once GPL mode selects an alternative stack. Enabling GPL can
    therefore *remove* a package from the build."""


SOURCE = Kind.SOURCE
SYSTEM = Kind.SYSTEM
TOOL = Kind.TOOL
FREE = Gate.FREE
REQUIRES_GPL = Gate.REQUIRES_GPL
FLAG_REQUIRES_GPL = Gate.FLAG_REQUIRES_GPL
SUPPRESSED_BY_GPL = Gate.SUPPRESSED_BY_GPL


@dataclass(frozen=True)
class Package:
    """One selectable `[packages]` key."""

    key: str
    summary: str
    default_enabled: bool = True
    kind: Kind = Kind.SOURCE
    gate: Gate = Gate.FREE
    apt_packages: tuple[str, ...] = ()
    ffmpeg_flags: tuple[str, ...] = ()
    group: str = ""


@dataclass(frozen=True)
class Group:
    """A display grouping. Ordering here is for readability only.

    The stages resolve dependencies and build order themselves; nothing about
    the build depends on how these are grouped or sorted.
    """

    name: str
    packages: tuple[Package, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "Build systems, code generators, assemblers, and packaging tools",
        (
            Package("ant-git", "Apache Ant Java build tool", kind=TOOL),
            Package("autoconf", "Generates portable configure scripts", kind=TOOL),
            Package("automake", "Generates portable Makefile templates", kind=TOOL),
            Package("cmake", "Cross-platform build-system generator", kind=TOOL),
            Package("libtool", "Portable library build and linking helper", kind=TOOL),
            Package("m4", "Macro processor used by Autotools", kind=TOOL),
            Package("meson", "High-level build-system generator", kind=TOOL),
            Package("nasm", "Netwide x86/x86-64 assembler", kind=TOOL),
            Package("ninja", "Fast low-level build executor", kind=TOOL),
            Package("pkgconf", "pkg-config-compatible dependency resolver", kind=TOOL),
            Package("yasm", "Modular x86/x86-64 assembler", kind=TOOL),
        ),
    ),
    Group(
        "Compression, parsing, allocation, and other foundational libraries",
        (
            Package(
                "brotli",
                "Brotli compression; the freetype build here disables its only use",
                default_enabled=False,
            ),
            Package(
                "gflags",
                "C++ command-line flag processing; nothing built here links it",
                default_enabled=False,
            ),
            Package(
                "jemalloc",
                "Allocator reachable only via FFmpeg's --custom-allocator, which this build never passes",
                default_enabled=False,
            ),
            Package("libiconv", "Character-encoding conversion", ffmpeg_flags=("--enable-iconv",)),
            Package("libxml2", "XML parsing and processing", ffmpeg_flags=("--enable-libxml2",)),
            Package("libzstd", "Zstandard compression and decompression"),
            Package(
                "pcre2",
                "Perl-compatible regular expressions; nothing built here links it",
                default_enabled=False,
            ),
            Package(
                "zlib",
                "DEFLATE compression and decompression",
                ffmpeg_flags=("--enable-zlib",),
            ),
        ),
    ),
    Group(
        "Cryptography, TLS, name resolution, and network protocols",
        (
            Package(
                "c-ares",
                "Asynchronous DNS resolution; nothing built here links it",
                default_enabled=False,
            ),
            Package(
                "gmp",
                "Arbitrary-precision arithmetic used by Nettle and GnuTLS",
                gate=SUPPRESSED_BY_GPL,
                ffmpeg_flags=("--enable-gmp",),
            ),
            Package(
                "gnutls",
                "TLS and cryptographic protocol support",
                gate=SUPPRESSED_BY_GPL,
                ffmpeg_flags=("--enable-gnutls",),
            ),
            Package(
                "librist",
                "Reliable Internet Stream Transport",
                ffmpeg_flags=("--enable-librist",),
            ),
            Package(
                "librtmp",
                "RTMP and RTMPE streaming protocols",
                kind=SYSTEM,
                apt_packages=("librtmp-dev",),
                ffmpeg_flags=("--enable-librtmp",),
            ),
            Package(
                "libsmbclient",
                "SMB/CIFS access; enabled only in GPL/non-free mode",
                kind=SYSTEM,
                apt_packages=("libsmbclient-dev",),
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libsmbclient",),
            ),
            Package(
                "libssh",
                "SSH and SFTP protocol support",
                kind=SYSTEM,
                apt_packages=("libssh-dev",),
                ffmpeg_flags=("--enable-libssh",),
            ),
            Package(
                "nettle",
                "Low-level cryptographic primitives used by GnuTLS",
                gate=SUPPRESSED_BY_GPL,
            ),
            Package(
                "openssl",
                "Alternative TLS and cryptography implementation",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-openssl",),
            ),
            Package(
                "srt",
                "Secure Reliable Transport for low-latency streaming",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libsrt",),
            ),
        ),
    ),
    Group(
        "Fonts, subtitles, captions, teletext, and text recognition",
        (
            Package(
                "fontconfig",
                "Font discovery and configuration",
                ffmpeg_flags=("--enable-libfontconfig",),
            ),
            Package(
                "freetype",
                "Font loading and rasterization",
                ffmpeg_flags=("--enable-libfreetype",),
            ),
            Package(
                "fribidi",
                "Unicode bidirectional-text processing",
                ffmpeg_flags=("--enable-libfribidi",),
            ),
            Package("harfbuzz", "Complex text shaping", ffmpeg_flags=("--enable-libharfbuzz",)),
            Package(
                "libaribb24",
                "ARIB STD-B24 caption decoding",
                default_enabled=False,
                kind=SYSTEM,
                apt_packages=("libaribb24-dev",),
                ffmpeg_flags=("--enable-libaribb24",),
            ),
            Package("libass", "ASS and SSA subtitle rendering", ffmpeg_flags=("--enable-libass",)),
            Package(
                "libtesseract",
                "Optical character recognition for video filters",
                kind=SYSTEM,
                apt_packages=("libtesseract-dev",),
                ffmpeg_flags=("--enable-libtesseract",),
            ),
            Package(
                "libzvbi",
                "Teletext and vertical-blanking-interval decoding",
                kind=SYSTEM,
                apt_packages=("libzvbi-dev",),
                ffmpeg_flags=("--enable-libzvbi",),
            ),
        ),
    ),
    Group(
        "Still-image codecs, color management, and image containers",
        (
            Package("avif", "AV1 Image File Format encoding and decoding"),
            Package(
                "giflib",
                "GIF codec; FFmpeg carries its own and no component here links this one",
                default_enabled=False,
            ),
            Package(
                "lcms2",
                "ICC color management with Little CMS",
                ffmpeg_flags=("--enable-lcms2",),
            ),
            Package("libheif", "HEIF and AVIF image container support"),
            Package(
                "libhwy",
                "SIMD primitives for JPEG XL, which arrives as the system libjxl-dev package",
                default_enabled=False,
            ),
            Package("libjpeg-turbo", "SIMD-accelerated JPEG; gpac probes for -ljpeg and links it"),
            Package(
                "libjxl",
                "System libjxl-dev integration; unavailable on Ubuntu 22.04",
                default_enabled=False,
                kind=SYSTEM,
                apt_packages=("libjxl-dev",),
                ffmpeg_flags=("--enable-libjxl",),
            ),
            Package("libpng", "PNG codec; gpac probes for -lpng and links it"),
            Package(
                "librsvg",
                "SVG rasterization",
                kind=SYSTEM,
                apt_packages=("librsvg2-dev",),
                ffmpeg_flags=("--enable-librsvg",),
            ),
            Package(
                "libtiff",
                "TIFF codec; nothing built here links it, and the system copy serves leptonica",
                default_enabled=False,
            ),
            Package(
                "libwebp-git",
                "WebP image encoding and decoding",
                ffmpeg_flags=("--enable-libwebp",),
            ),
            Package(
                "openjpeg",
                "JPEG 2000 encoding and decoding",
                ffmpeg_flags=("--enable-libopenjpeg",),
            ),
        ),
    ),
    Group(
        "Audio codecs and audio container formats",
        (
            Package(
                "libfdk-aac",
                "Fraunhofer AAC codec; requires non-free authorization",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libfdk-aac",),
            ),
            Package(
                "libgsm",
                "GSM 06.10 speech codec",
                kind=SYSTEM,
                apt_packages=("libgsm1-dev",),
                ffmpeg_flags=("--enable-libgsm",),
            ),
            Package("liblame", "MP3 audio encoding", ffmpeg_flags=("--enable-libmp3lame",)),
            Package("libogg", "Ogg bitstream framing and container support"),
            Package(
                "libopus",
                "Opus audio encoding and decoding",
                ffmpeg_flags=("--enable-libopus",),
            ),
            Package(
                "libshine",
                "Fixed-point MP3 audio encoding",
                kind=SYSTEM,
                apt_packages=("libshine-dev",),
                ffmpeg_flags=("--enable-libshine",),
            ),
            Package(
                "libspeex",
                "Speex speech encoding and decoding",
                kind=SYSTEM,
                apt_packages=("libspeex-dev",),
                ffmpeg_flags=("--enable-libspeex",),
            ),
            Package(
                "libtwolame",
                "MPEG Layer II audio encoding",
                kind=SYSTEM,
                apt_packages=("libtwolame-dev",),
                ffmpeg_flags=("--enable-libtwolame",),
            ),
            Package(
                "libvo-amrwbenc",
                "AMR-WB speech encoding",
                kind=SYSTEM,
                apt_packages=("libvo-amrwbenc-dev",),
                ffmpeg_flags=("--enable-libvo-amrwbenc",),
            ),
            Package(
                "opencore-amr",
                "AMR-NB and AMR-WB speech codecs",
                ffmpeg_flags=("--enable-libopencore-amrnb", "--enable-libopencore-amrwb"),
            ),
            Package(
                "vorbis",
                "Vorbis audio encoding and decoding",
                ffmpeg_flags=("--enable-libvorbis",),
            ),
        ),
    ),
    Group(
        "Audio resampling, analysis, effects, and synthesis",
        (
            Package(
                "chromaprint",
                "Acoustic fingerprint generation",
                kind=SYSTEM,
                apt_packages=("libchromaprint-dev",),
                ffmpeg_flags=("--enable-chromaprint",),
            ),
            Package(
                "libbs2b",
                "Bauer stereo-to-binaural audio processing",
                kind=SYSTEM,
                apt_packages=("libbs2b-dev",),
                ffmpeg_flags=("--enable-libbs2b",),
            ),
            Package(
                "libflite",
                "Flite text-to-speech synthesis",
                kind=SYSTEM,
                apt_packages=("flite1-dev",),
                ffmpeg_flags=("--enable-libflite",),
            ),
            Package(
                "libgme",
                "Video-game music emulation",
                kind=SYSTEM,
                apt_packages=("libgme-dev",),
                ffmpeg_flags=("--enable-libgme",),
            ),
            Package(
                "libmodplug",
                "Tracker-module audio decoding",
                kind=SYSTEM,
                apt_packages=("libmodplug-dev",),
                ffmpeg_flags=("--enable-libmodplug",),
            ),
            Package(
                "libmysofa",
                "SOFA HRTF data for spatial audio",
                ffmpeg_flags=("--enable-libmysofa",),
            ),
            Package(
                "libopenmpt",
                "Tracker-module audio decoding and rendering",
                kind=SYSTEM,
                apt_packages=("libopenmpt-dev",),
                ffmpeg_flags=("--enable-libopenmpt",),
            ),
            Package(
                "libsndfile",
                "Sampled-audio file I/O; rubberband builds with auto_features disabled",
                default_enabled=False,
            ),
            Package(
                "libsoxr",
                "High-quality audio sample-rate conversion",
                ffmpeg_flags=("--enable-libsoxr",),
            ),
            Package(
                "rubberband-git",
                "Time stretching and pitch shifting",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-librubberband",),
            ),
        ),
    ),
    Group(
        "Audio plugin standards and the LV2 dependency stack",
        (
            Package(
                "ladspa",
                "LADSPA audio plugin API and filters",
                kind=SYSTEM,
                apt_packages=("ladspa-sdk",),
                ffmpeg_flags=("--enable-ladspa",),
            ),
            Package(
                "lilv",
                "LV2 plugin discovery, loading, and hosting",
                ffmpeg_flags=("--enable-lv2",),
            ),
            Package("lv2-git", "LV2 audio plugin specification and headers"),
            Package("serd", "Lightweight RDF syntax library used by LV2"),
            Package("sord", "In-memory RDF store used by LV2"),
            Package("sratom", "LV2 Atom serialization to and from RDF"),
            Package(
                "zix",
                "Portability utilities used by LV2; system libzix-dev is absent on Ubuntu 22.04 and Debian 12",
            ),
        ),
    ),
    Group(
        "Audio devices and sound servers",
        (
            Package(
                "alsa",
                "Linux ALSA audio input and output",
                kind=SYSTEM,
                apt_packages=("libasound2-dev",),
                ffmpeg_flags=("--enable-alsa",),
            ),
            Package(
                "libjack",
                "Low-latency JACK audio input and output",
                kind=SYSTEM,
                apt_packages=("libjack-dev",),
                ffmpeg_flags=("--enable-libjack",),
            ),
            Package(
                "libpulse",
                "PulseAudio input and output",
                kind=SYSTEM,
                apt_packages=("libpulse-dev",),
                ffmpeg_flags=("--enable-libpulse",),
            ),
            Package(
                "sndio",
                "sndio audio input and output",
                kind=SYSTEM,
                apt_packages=("libsndio-dev",),
                ffmpeg_flags=("--enable-sndio",),
            ),
        ),
    ),
    Group(
        "Video codecs and codec support libraries",
        (
            Package(
                "av1-git",
                "AOMedia AV1 encoding and decoding with libaom",
                ffmpeg_flags=("--enable-libaom",),
            ),
            Package("kvazaar", "HEVC/H.265 video encoding", ffmpeg_flags=("--enable-libkvazaar",)),
            Package(
                "libdav1d",
                "High-performance AV1 video decoding",
                kind=SYSTEM,
                apt_packages=("libdav1d-dev",),
                ffmpeg_flags=("--enable-libdav1d",),
            ),
            Package(
                "libgav1-git",
                "Standalone AV1 decoder; not used by FFmpeg",
                default_enabled=False,
            ),
            Package(
                "libopenh264",
                "Cisco H.264 encoding and decoding",
                kind=SYSTEM,
                apt_packages=("libopenh264-dev",),
                ffmpeg_flags=("--enable-libopenh264",),
            ),
            Package(
                "libsnappy",
                "Snappy compression required by the HAP decoder",
                kind=SYSTEM,
                apt_packages=("libsnappy-dev",),
                ffmpeg_flags=("--enable-libsnappy",),
            ),
            Package(
                "libtheora",
                "Theora video encoding and decoding",
                ffmpeg_flags=("--enable-libtheora",),
            ),
            Package(
                "libvpx",
                "VP8 and VP9 video encoding and decoding",
                kind=SYSTEM,
                apt_packages=("libvpx-dev",),
                ffmpeg_flags=("--enable-libvpx",),
            ),
            Package("rav1e", "Rust-based AV1 video encoding", ffmpeg_flags=("--enable-librav1e",)),
            Package(
                "svt-av1",
                "Scalable Video Technology AV1 encoding",
                ffmpeg_flags=("--enable-libsvtav1",),
            ),
            Package(
                "x264",
                "GPL H.264 video encoding; requires GPL/non-free mode",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libx264",),
            ),
            Package(
                "x265",
                "GPL HEVC/H.265 video encoding; requires GPL/non-free mode",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libx265",),
            ),
            Package(
                "xvidcore",
                "MPEG-4 Part 2 video encoding and decoding",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libxvid",),
            ),
        ),
    ),
    Group(
        "Video processing, quality analysis, and scripting frameworks",
        (
            Package(
                "avisynth",
                "AviSynth script and frame-server input",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-avisynth",),
            ),
            Package(
                "frei0r",
                "Video-effects plugin API; enabled only in GPL/non-free mode",
                kind=SYSTEM,
                apt_packages=("frei0r-plugins-dev",),
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-frei0r",),
            ),
            Package(
                "libvmaf",
                "Perceptual video quality measurement",
                ffmpeg_flags=("--enable-libvmaf",),
            ),
            Package(
                "vapoursynth",
                "VapourSynth script and frame-server input",
                ffmpeg_flags=("--enable-vapoursynth",),
            ),
            Package(
                "vid-stab",
                "Video stabilization and transform filters",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libvidstab",),
            ),
            Package(
                "zimg-git",
                "Scaling, colorspace conversion, and dithering",
                ffmpeg_flags=("--enable-libzimg",),
            ),
        ),
    ),
    Group(
        "Optical media, containers, packaging, and metadata tools",
        (
            Package("gpac-git", "GPAC and MP4Box multimedia packaging tools", kind=TOOL),
            Package(
                "libbluray",
                "Blu-ray disc navigation and access",
                kind=SYSTEM,
                apt_packages=("libbluray-dev",),
                ffmpeg_flags=("--enable-libbluray",),
            ),
            Package(
                "libcdio",
                "Audio CD input; enabled only in GPL/non-free mode",
                kind=SYSTEM,
                apt_packages=("libcdio-dev", "libcdio-paranoia-dev"),
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-libcdio",),
            ),
            Package(
                "libdvdread",
                "DVD disc structure and data access",
                gate=FLAG_REQUIRES_GPL,
                ffmpeg_flags=("--enable-libdvdread",),
            ),
            Package(
                "libdvdnav",
                "DVD navigation; with libdvdread it enables FFmpeg's dvdvideo demuxer (GPL)",
                gate=FLAG_REQUIRES_GPL,
                ffmpeg_flags=("--enable-libdvdnav",),
            ),
            Package("mediainfo-cli", "Command-line technical metadata inspector", kind=TOOL),
            Package("mediainfo-lib", "Library for reading technical media metadata"),
            Package("udfread", "Universal Disk Format filesystem reader"),
            Package("zenlib", "Utility library required by MediaInfoLib"),
        ),
    ),
    Group(
        "Playback, capture, window systems, and visual output",
        (
            Package(
                "freeglut",
                "GLUT toolkit; FFmpeg's OpenGL device needs GL/GLX instead",
                default_enabled=False,
            ),
            Package(
                "libcaca",
                "Color text and ASCII-art video output",
                kind=SYSTEM,
                apt_packages=("libcaca-dev",),
                ffmpeg_flags=("--enable-libcaca",),
            ),
            Package(
                "libv4l2",
                "Video4Linux2 capture and device access",
                kind=SYSTEM,
                apt_packages=("libv4l-dev",),
                ffmpeg_flags=("--enable-libv4l2",),
            ),
            Package(
                "opengl",
                "OpenGL video output",
                kind=SYSTEM,
                apt_packages=(),
                ffmpeg_flags=("--enable-opengl",),
            ),
            Package(
                "sdl2",
                "Window, audio, and input support required by ffplay",
                ffmpeg_flags=("--enable-sdl2",),
            ),
            Package(
                "xlib",
                "X11 and XCB screen capture",
                kind=SYSTEM,
                apt_packages=(),
                ffmpeg_flags=(
                    "--enable-xlib",
                    "--enable-libxcb",
                    "--enable-libxcb-shm",
                    "--enable-libxcb-shape",
                    "--enable-libxcb-xfixes",
                ),
            ),
        ),
    ),
    Group(
        "GPU APIs, codec SDK headers, and hardware acceleration",
        (
            Package(
                "amf-headers",
                "AMD Advanced Media Framework SDK headers",
                gate=REQUIRES_GPL,
                ffmpeg_flags=("--enable-amf",),
            ),
            Package(
                "libdrm",
                "Userspace Direct Rendering Manager interface",
                kind=SYSTEM,
                apt_packages=("libdrm-dev",),
                ffmpeg_flags=("--enable-libdrm",),
            ),
            Package(
                "libplacebo",
                "Vulkan-based GPU scaling and tone mapping",
                kind=SYSTEM,
                apt_packages=("libplacebo-dev",),
                ffmpeg_flags=("--enable-libplacebo",),
            ),
            Package(
                "libshaderc",
                "System libshaderc-dev integration; unavailable on Ubuntu 22.04",
                default_enabled=False,
                kind=SYSTEM,
                apt_packages=("libshaderc-dev",),
                ffmpeg_flags=("--enable-libshaderc",),
            ),
            Package(
                "libvpl",
                "oneVPL API for Intel Quick Sync acceleration",
                kind=SYSTEM,
                apt_packages=("libvpl-dev",),
                ffmpeg_flags=("--enable-libvpl",),
            ),
            Package(
                "nv-codec-headers",
                "NVIDIA codec SDK headers; requires GPL/non-free mode",
                default_enabled=False,
                gate=REQUIRES_GPL,
                ffmpeg_flags=(
                    "--enable-cuda",
                    "--enable-cuvid",
                    "--enable-ffnvcodec",
                    "--enable-nvdec",
                    "--enable-nvenc",
                ),
            ),
            Package(
                "opencl-sdk-git",
                "Khronos OpenCL headers, bindings, loader, and utilities",
                ffmpeg_flags=("--enable-opencl",),
            ),
            Package(
                "vaapi",
                "VA-API hardware-accelerated video processing",
                kind=SYSTEM,
                apt_packages=("libva-dev",),
                ffmpeg_flags=("--enable-vaapi",),
            ),
            Package(
                "vdpau",
                "VDPAU hardware-accelerated video decoding and presentation",
                kind=SYSTEM,
                apt_packages=("libvdpau-dev",),
                ffmpeg_flags=("--enable-vdpau",),
            ),
            Package(
                "vulkan",
                "Vulkan loader for hardware acceleration and GPU filters",
                kind=SYSTEM,
                apt_packages=("libvulkan-dev", "glslang-tools", "spirv-headers"),
                ffmpeg_flags=("--enable-vulkan",),
            ),
            Package("vulkan-headers-git", "Khronos Vulkan API headers"),
        ),
    ),
    Group(
        "Final application",
        (Package("ffmpeg", "FFmpeg command-line tools and multimedia libraries"),),
    ),
)


@dataclass(frozen=True)
class Requirement:
    """A cross-package rule checked before any work begins.

    One table, three consumers: pre-build validation, the menu's live checking,
    and the menu's one-key auto-fix.
    """

    package: str
    needs: str
    pkgconf_module: str | None = None
    """The system module that satisfies this instead, or None when only the
    source build will do."""

    alternative: str = ""
    """How the system fallback is described in the diagnostic."""

    condition: str = "always"
    """`always`, `gpl-openssl` (GPL mode with OpenSSL selected), `not-gpl-openssl`
    (the GnuTLS stack's window), or `gpl`."""

    def message(self) -> str:
        text = f"'packages.{self.package}=true' requires 'packages.{self.needs}=true'"
        return f"{text} or {self.alternative}" if self.alternative else text


REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("mediainfo-lib", "zenlib"),
    Requirement("mediainfo-cli", "mediainfo-lib"),
    Requirement("vorbis", "libogg", "ogg", "a system libogg development package"),
    Requirement("libtheora", "libogg", "ogg", "a system libogg development package"),
    Requirement(
        "openssl", "zlib", "zlib", "a system zlib development package", condition="gpl-openssl"
    ),
    Requirement(
        "gnutls", "gmp", "gmp", "a system GMP development package", condition="not-gpl-openssl"
    ),
    Requirement(
        "gnutls",
        "nettle",
        "nettle",
        "a system nettle development package",
        condition="not-gpl-openssl",
    ),
    Requirement(
        "srt", "openssl", "openssl", "a system OpenSSL development package", condition="gpl"
    ),
    Requirement("fontconfig", "libxml2", "libxml-2.0", "a system libxml2 development package"),
    Requirement("fontconfig", "freetype", "freetype2", "a system FreeType development package"),
    Requirement("libass", "fontconfig", "fontconfig", "a system fontconfig development package"),
    Requirement("libass", "freetype", "freetype2", "a system freetype development package"),
    Requirement("libass", "fribidi", "fribidi", "a system fribidi development package"),
    Requirement("libass", "harfbuzz", "harfbuzz", "a system harfbuzz development package"),
    Requirement("sord", "serd", "serd-0", "a system Serd development package"),
    Requirement("sord", "zix", "zix-0", "a system Zix development package"),
    Requirement("sratom", "lv2-git", "lv2", "system LV2 headers"),
    Requirement("sratom", "serd", "serd-0", "a system Serd development package"),
    Requirement("lilv", "lv2-git", "lv2", "system LV2 headers"),
    Requirement("lilv", "serd", "serd-0", "a system Serd development package"),
    Requirement("lilv", "zix", "zix-0", "a system Zix development package"),
    Requirement("lilv", "sord", "sord-0", "a system Sord development package"),
    Requirement("lilv", "sratom", "sratom-0", "a system Sratom development package"),
    Requirement("avif", "av1-git", "aom", "a system libaom development package"),
)

# Rules that can be evaluated without probing the host. These run before the
# first host mutation, so an unsatisfiable request fails without having
# installed packages or asked for a password first.
SETTINGS_REQUIREMENTS = tuple(
    requirement for requirement in REQUIREMENTS if requirement.pkgconf_module is None
)
SELECTION_REQUIREMENTS = tuple(
    requirement for requirement in REQUIREMENTS if requirement.pkgconf_module is not None
)

# The one historical key whose name did not match its build marker, so setting
# it never actually disabled anything.
KEY_ALIASES = {"vulkan-headers": "vulkan-headers-git"}

PACKAGES: dict[str, Package] = {}
for _group in GROUPS:
    for _package in _group.packages:
        PACKAGES[_package.key] = Package(
            key=_package.key,
            summary=_package.summary,
            default_enabled=_package.default_enabled,
            kind=_package.kind,
            gate=_package.gate,
            apt_packages=_package.apt_packages,
            ffmpeg_flags=_package.ffmpeg_flags,
            group=_group.name,
        )

PACKAGE_NAMES: tuple[str, ...] = tuple(PACKAGES)


def canonical_key(key: str) -> str:
    """Map a deprecated key onto the name the build actually uses."""
    return KEY_ALIASES.get(key, key)


def is_supported(key: str) -> bool:
    return canonical_key(key) in PACKAGES


def get(key: str) -> Package:
    return PACKAGES[canonical_key(key)]


def requirements_for(package: str) -> tuple[Requirement, ...]:
    return tuple(rule for rule in REQUIREMENTS if rule.package == package)
