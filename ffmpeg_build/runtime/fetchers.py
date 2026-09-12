"""Per-package release discovery.

Most packages resolve through `github_version` or `gitlab_version`. The rest
publish no tag list this project can read and need a dedicated index scraper,
which is what the functions below are. `find_git_repo` reproduces the Bash
dispatch table, including the opaque numeric project identifiers that stand in
for VideoLAN and SVT-AV1 repositories.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass

from .errors import BuildError
from .versioncmp import version_sort
from .versions import DEFAULT_VERSION_PATTERN, VersionResolver

_THREE_PART = re.compile(r"^[0-9]+(\.[0-9]+){2}$")

# These are upstream tag naming conventions, never fixed release versions.
GIT_RELEASE_PREFIXES = {
    "av1-git": "v",
    "zimg-git": "release-",
    "ant-git": "rel/",
    "gpac-git": "v",
    "libgav1-git": "v",
    "libwebp-git": "v",
    "opencl-sdk-git": "v",
    "vulkan-headers-git": "v",
    "rubberband-git": "v",
    "lv2-git": "v",
}


@dataclass(frozen=True)
class ResolvedVersion:
    """A version plus which upstream produced it.

    FreeType and Fontconfig publish both release tarballs and GitLab archives
    under different names, so the download URL depends on which source answered.
    """

    version: str
    source: str = "release"


class PackageVersions:
    """Version fetchers for packages that need more than a tag list."""

    def __init__(self, resolver: VersionResolver) -> None:
        self.resolver = resolver
        self.logger = resolver.logger

    # -- freedesktop -----------------------------------------------------

    def freetype(self) -> ResolvedVersion | None:
        version = self.resolver.scrape_highest(
            "https://download.savannah.gnu.org/releases/freetype/",
            r"freetype-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.(?:xz|gz|bz2)",
            max_time=int(os.environ.get("FREEDESKTOP_RELEASE_INDEX_MAX_TIME") or "5"),
            connect_timeout=int(
                os.environ.get("FREEDESKTOP_RELEASE_CONNECT_TIMEOUT")
                or os.environ.get("DOWNLOAD_CONNECT_TIMEOUT")
                or "2"
            ),
        )
        if version:
            return ResolvedVersion(version, "release")
        self.logger.warn("FreeType release archive is unavailable; trying FreeDesktop GitLab.")
        hyphenated = self.resolver.gitlab_version(
            "https://gitlab.freedesktop.org",
            "freetype/freetype",
            "VER-",
            "-",
            re.compile(r"^[0-9]+(-[0-9]+){2,3}$"),
        )
        if hyphenated:
            return ResolvedVersion(hyphenated.replace("-", "."), "gitlab")
        return None

    def fontconfig(self) -> ResolvedVersion | None:
        # The legacy release directory stopped updating before the GitLab
        # releases. Prefer upstream tags so a reachable old mirror cannot
        # silently select an obsolete version.
        version = self.resolver.gitlab_version(
            "https://gitlab.freedesktop.org", "fontconfig/fontconfig", "", "."
        )
        if version:
            return ResolvedVersion(version, "gitlab")
        self.logger.warn("Unable to discover the latest Fontconfig release from upstream tags.")
        return None

    # -- release indexes -------------------------------------------------

    def sdl2(self) -> str | None:
        listing = self.resolver.fetch_text("https://www.libsdl.org/release/")
        if listing is None:
            self.logger.warn("sdl2_repo_version: failed to fetch the SDL release archive.")
            return None
        from .versioncmp import version_sort

        matches = re.findall(r"SDL2-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz", listing)
        ordered = version_sort(list(matches), unique=True)
        if not ordered:
            self.logger.warn("sdl2_repo_version: no SDL2 version found in the SDL release archive.")
            return None
        return ordered[-1]

    def lame(self) -> str | None:
        # Require both the release directory and filename to be numeric. The
        # feed also includes old beta releases in their own directories.
        return self.resolver.scrape_highest(
            "https://sourceforge.net/projects/lame/rss?path=/lame",
            r"/lame/[0-9]+(?:\.[0-9]+)+/lame-([0-9]+(?:\.[0-9]+)+)\.tar\.gz",
        )

    def gnutls(self) -> str | None:
        root = "https://www.gnupg.org/ftp/gcrypt/gnutls/"
        listing = self.resolver.fetch_text(root)
        if listing is None:
            return None
        series = re.findall(r'href="v([0-9]+\.[0-9]+)/?"', listing)
        for branch in version_sort(series, reverse=True, unique=True):
            releases = self.resolver.fetch_text(f"{root}v{branch}/")
            if releases is None:
                # A failed newer-series lookup must not silently choose an old series.
                return None
            matches = re.findall(rf"gnutls-({re.escape(branch)}\.[0-9]+)\.tar\.xz", releases)
            ordered = version_sort(matches, reverse=True, unique=True)
            if ordered:
                return ordered[0]
        return None

    def rust(self) -> str | None:
        text = self.resolver.fetch_text(
            "https://static.rust-lang.org/dist/channel-rust-stable.toml"
        )
        if text is None:
            return None
        try:
            report = tomllib.loads(text)["pkg"]["rust"]["version"]
            version = report.split()[0] if isinstance(report, str) else ""
        except (tomllib.TOMLDecodeError, KeyError, TypeError, IndexError):
            return None
        return version if _THREE_PART.fullmatch(version) else None

    def cargo_c(self) -> str | None:
        # The official sparse registry includes the full Cargo build metadata
        # and yanked status, unlike Git tags or a hardcoded compatible version.
        text = self.resolver.fetch_text("https://index.crates.io/ca/rg/cargo-c")
        if text is None:
            return None
        versions: list[str] = []
        try:
            for line in text.splitlines():
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    return None
                version = entry.get("vers")
                if (
                    entry.get("yanked") is False
                    and isinstance(version, str)
                    and re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}(?:\+[A-Za-z0-9.-]+)?", version)
                ):
                    versions.append(version)
        except json.JSONDecodeError:
            return None
        ordered = version_sort(versions, reverse=True, unique=True)
        return ordered[0] if ordered else None

    def cython(self) -> str | None:
        text = self.resolver.fetch_text("https://pypi.org/pypi/Cython/json")
        if text is None:
            return None
        try:
            releases = json.loads(text)["releases"]
            if not isinstance(releases, dict):
                return None
            versions = [
                version
                for version, files in releases.items()
                if _THREE_PART.fullmatch(version)
                and isinstance(files, list)
                and any(isinstance(file, dict) and file.get("yanked") is False for file in files)
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
        ordered = version_sort(versions, reverse=True, unique=True)
        return ordered[0] if ordered else None

    def opencore_amr(self) -> str | None:
        version = self.resolver.scrape_highest(
            "https://sourceforge.net/projects/opencore-amr/files/opencore-amr/",
            r"opencore-amr-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz",
        )
        return version if version and _THREE_PART.match(version) else None

    def xvidcore(self) -> str | None:
        version = self.resolver.scrape_highest(
            "https://downloads.xvid.com/downloads/",
            r"xvidcore-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.bz2",
        )
        return version if version and _THREE_PART.match(version) else None

    def giflib(self) -> str | None:
        version = self.resolver.scrape_highest(
            "https://sourceforge.net/projects/giflib/rss?path=/",
            r"giflib-([0-9]+\.[0-9]+(?:\.[0-9]+)?)\.tar\.gz",
        )
        if version is None:
            self.logger.warn("giflib_repo_version: no version found in the SourceForge RSS feed.")
        return version

    def nasm(self) -> str | None:
        """Discover NASM releases from the same index used for downloads.

        `/pub/nasm/stable/` no longer exists. Prereleases and dated snapshots
        are ignored, and the HTTP result is checked before parsing because a
        failed transfer can contain a partial listing that must not be mistaken
        for the newest release.
        """
        index_url = "https://www.nasm.us/pub/nasm/releasebuilds/"
        listing = self.resolver.fetch_text(index_url, connect_timeout=2)
        if listing is None:
            self.logger.warn(f"Failed to fetch the NASM release index '{index_url}'.")
            return None
        from .versioncmp import version_sort

        matches = re.findall(r'href="([0-9]+(?:\.[0-9]+){1,2})/"', listing)
        ordered = version_sort(list(matches), reverse=True, unique=True)
        if not ordered:
            self.logger.warn(f"No stable NASM release was found in '{index_url}'.")
            return None
        return ordered[0]

    # -- forge-specific shapes -------------------------------------------

    def openssl(self) -> str | None:
        return self.resolver.github_version("openssl/openssl", "openssl-")

    def rav1e(self) -> str | None:
        return self.resolver.github_version("xiph/rav1e", "v", "alpha|beta|rc")

    def vapoursynth(self) -> str | None:
        return self.resolver.github_version(
            "vapoursynth/vapoursynth", "R", "[Rr][Cc]", re.compile(r"^[0-9]+$")
        )

    def pkgconf(self) -> str | None:
        return self.resolver.github_version("pkgconf/pkgconf", "pkgconf-")

    def nv_codec_headers(self) -> str | None:
        return self.resolver.github_version(
            "FFmpeg/nv-codec-headers", "n", "", re.compile(r"^[0-9]+(\.[0-9]+){3}$")
        )

    def ffmpeg(self) -> str | None:
        return self.resolver.github_version("FFmpeg/FFmpeg", "n")

    def x265(self) -> str | None:
        tags = self.resolver.remote_tag_names("https://github.com/Multicorewareinc/x265.git")
        if tags is None:
            return None
        return self.resolver.select_prefixed_version(
            tags, "", "alpha|beta|rc", re.compile(r"^[0-9]+(\.[0-9]+){1,2}$")
        )

    def x264(self) -> str:
        """x264 publishes branches, not release tags.

        The 40-character commit on `refs/heads/stable` is both the download
        component and the recorded marker version, so a failure here is fatal
        rather than recoverable.
        """
        commit = self.resolver.remote_head_commit(
            "https://code.videolan.org/videolan/x264.git", "refs/heads/stable"
        )
        if commit is None:
            raise BuildError("Failed to detect x264 stable commit.")
        return commit

    def videolan(self, project_id: str, count: int = 1) -> str | None:
        """Resolve one of VideoLAN's numeric project identifiers.

        These identifiers are opaque keys carried over from the original
        script's dispatch table, not repository names.
        """
        projects = {
            "76": "videolan/libdvdread",
            "206": "videolan/libdvdnav",
            "363": "videolan/libudfread",
        }
        project = projects.get(project_id)
        if project is None:
            return None
        tags = self.resolver.remote_tag_names(f"https://code.videolan.org/{project}.git")
        if not tags:
            return None
        return self.resolver.select_prefixed_version(tags, "", index=count)

    def svt_av1(self, index: int = 1) -> str | None:
        return self.resolver.gitlab_version(
            "https://gitlab.com", "AOMediaCodec/SVT-AV1", "v", ".", None, index
        )


# --------------------------------------------------------------------------
# Archive URL builders for sources whose name depends on where it came from
# --------------------------------------------------------------------------


def freetype_gitlab_archive_url(dotted_version: str) -> str:
    hyphenated = dotted_version.replace(".", "-")
    return (
        f"https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-{hyphenated}"
        f"/freetype-VER-{hyphenated}.tar.bz2?ref_type=tags"
    )


def freetype_release_archive_url(version: str) -> str:
    return f"https://download-mirror.savannah.gnu.org/releases/freetype/freetype-{version}.tar.xz"


def freetype_sourceforge_archive_url(version: str) -> str:
    return (
        f"https://downloads.sourceforge.net/project/freetype/freetype2/{version}"
        f"/freetype-{version}.tar.xz"
    )


def fontconfig_gitlab_archive_url(version: str) -> str:
    return (
        f"https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/{version}"
        f"/fontconfig-{version}.tar.gz"
    )


def fontconfig_release_archive_url(version: str) -> str:
    return f"https://www.freedesktop.org/software/fontconfig/release/fontconfig-{version}.tar.xz"


def sdl2_download_url(version: str) -> str:
    return f"https://www.libsdl.org/release/SDL2-{version}.tar.gz"


def rav1e_download_url(version: str) -> str:
    if not DEFAULT_VERSION_PATTERN.match(version):
        raise BuildError(f"rav1e_download_url() received an invalid release version: '{version}'.")
    return f"https://github.com/xiph/rav1e/archive/refs/tags/v{version}.tar.gz"


def giflib_download_url(version: str) -> str:
    match = re.match(r"^([0-9]+)\.[0-9]+(\.[0-9]+)?$", version)
    if match is None:
        raise BuildError(f"giflib_download_url() received an invalid version: '{version}'.")
    major = match.group(1)
    return (
        f"https://downloads.sourceforge.net/project/giflib/giflib-{major}.x/giflib-{version}.tar.gz"
    )


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

# Repositories whose tags carry no prefix at all.
_UNPREFIXED_GITHUB = frozenset(
    {
        "libass/libass",
        "harfbuzz/harfbuzz",
        "google/highway",
        "jemalloc/jemalloc",
        "libjpeg-turbo/libjpeg-turbo",
        "libsndfile/libsndfile",
        "chirlu/soxr",
        "mesonbuild/meson",
    }
)

# Repositories using the conventional "v" prefix and nothing else.
_V_PREFIXED_GITHUB = frozenset(
    {
        "ninja-build/ninja",
        "facebook/zstd",
        "yasm/yasm",
        "xiph/ogg",
        "xiph/opus",
        "xiph/vorbis",
        "xiph/theora",
        "freeglut/freeglut",
        "fribidi/fribidi",
        "google/brotli",
        "gflags/gflags",
        "c-ares/c-ares",
        "akheron/jansson",
        "pnggroup/libpng",
        "strukturag/libheif",
        "uclouvain/openjpeg",
        "ultravideo/kvazaar",
        "AOMediaCodec/libavif",
        "Haivision/srt",
        "georgmartius/vid.stab",
        "mstorsjo/fdk-aac",
        "hoene/libmysofa",
        "dyne/frei0r",
        "nkoriyama/aribb24",
        "Netflix/vmaf",
    }
)

_GITLAB_PROJECTS = {
    "drobilla/zix": ("https://gitlab.com", "drobilla/zix"),
    "libtiff/libtiff": ("https://gitlab.com", "libtiff/libtiff"),
    "GNOME/libxml2": ("https://gitlab.gnome.org", "GNOME/libxml2"),
    "rist/librist": ("https://code.videolan.org", "rist/librist"),
}


def find_git_repo(
    versions: PackageVersions,
    repository: str,
    choice: int = 1,
) -> str | None:
    """Resolve a version for one of the registry's upstream identifiers."""
    resolver = versions.resolver
    if repository == "FFmpeg/FFmpeg":
        return versions.ffmpeg()
    if repository == "xiph/rav1e":
        return versions.rav1e()
    if repository == "536":
        return versions.x264()
    if repository == "GPUOpen-LibrariesAndSDKs/AMF":
        return resolver.github_version("GPUOpen-LibrariesAndSDKs/AMF", "v")
    if repository in ("avisynth/avisynthplus", "AviSynth/AviSynthPlus"):
        return resolver.github_version("AviSynth/AviSynthPlus", "v")
    if repository == "vapoursynth/vapoursynth":
        return versions.vapoursynth()
    if repository in ("MediaArea/ZenLib", "MediaArea/MediaInfoLib", "MediaArea/MediaInfo"):
        return resolver.github_version(repository, "v")
    if repository == "24327400":
        return versions.svt_av1(choice)
    if repository in ("76", "206", "363"):
        return versions.videolan(repository, choice)
    if repository == "Kitware/CMake":
        return resolver.github_version("Kitware/CMake", "v", "rc")
    if repository == "mesonbuild/meson":
        return resolver.github_version("mesonbuild/meson", "", "rc")
    if repository == "madler/zlib":
        return resolver.github_version("madler/zlib", "v")
    if repository == "mm2/Little-CMS":
        return resolver.github_version("mm2/Little-CMS", "lcms")
    if repository == "freetype/freetype":
        resolved = versions.freetype()
        return resolved.version if resolved else None
    if repository == "fontconfig/fontconfig":
        resolved = versions.fontconfig()
        return resolved.version if resolved else None
    if repository in _GITLAB_PROJECTS:
        base_url, project = _GITLAB_PROJECTS[repository]
        return resolver.gitlab_version(base_url, project, "v")
    if repository in _UNPREFIXED_GITHUB:
        return resolver.github_version(repository, "")
    if repository in _V_PREFIXED_GITHUB:
        return resolver.github_version(repository, "v")
    return resolver.github_version_any_prefix(repository)
