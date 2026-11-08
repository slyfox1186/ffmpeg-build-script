"""Bounded integer and switch parsing, and every setting a user can put in `.env`."""

from __future__ import annotations

import re
import sys

from .dotenv import Setting

MAX_PROCESS_INTEGER = 2**31 - 1
BYPASS_CACHE_DELETE = "BYPASS_CACHE_DELETE"
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("", "0", "false", "no", "off")

_WORKSPACE = "Workspace"
_OUTPUT = "Terminal output"
_CUDA = "NVIDIA CUDA"
_LOOKUPS = "Release lookups"
_DOWNLOADS = "Downloads"
_GIT = "Git"
_WAITING = "Waiting for other runs"
_DEVELOPERS = "Developers of this repository"

# Every environment setting the build reads, in the order `.env.example` lists
# them. The defaults restate the code's own; the linter keeps the template equal
# to this table.
DOTENV_SETTINGS = (
    Setting(
        _WORKSPACE,
        "BUILD_ROOT",
        "",
        "build/ in this checkout",
        "Folder that holds the downloaded sources, the compiled libraries and the "
        "build log. A relative path is taken from the folder you run the script "
        "from. The path may not contain spaces. Keep using the same value for later "
        "builds and for --cleanup.",
    ),
    Setting(
        _OUTPUT,
        "NO_COLOR",
        "",
        "empty (color on a terminal)",
        "Set to 1 to never color the output, for example when your terminal shows "
        "stray characters.",
    ),
    Setting(
        _OUTPUT,
        "FORCE_COLOR",
        "",
        "empty (color only on a terminal)",
        "Set to 1 to color the output even when it is piped or redirected. NO_COLOR "
        "wins when both are set.",
    ),
    Setting(
        _OUTPUT,
        "FFMPEG_BUILD_DEBUG",
        "OFF",
        "OFF",
        "ON streams every command's full output to the terminal while it runs, "
        "for troubleshooting a failed build. The build log is written either way. "
        "Allowed: ON or OFF.",
    ),
    Setting(
        _CUDA,
        "CUDA_INSTALL",
        "ask",
        "ask",
        "CUDA is used only with --enable-gpl-and-non-free and nv-codec-headers = "
        "true. What to do when this computer has an NVIDIA GPU and either no CUDA "
        "toolkit or an older one than NVIDIA's repository offers for its driver: ask "
        "asks before installing from NVIDIA's signed APT repository, always installs "
        "without asking, never leaves CUDA alone and checks nothing. The NVIDIA "
        "display driver is never installed or changed. Allowed: ask, always or never.",
    ),
    Setting(
        _CUDA,
        "CUDA_ARCH_MODE",
        "native",
        "native",
        "Which GPUs the CUDA code is compiled for: native for the GPUs in this "
        "computer, all for every GPU the toolkit supports (runs anywhere, builds "
        "slower), custom for the list in CUDA_ARCHITECTURES. Allowed: native, all "
        "or custom.",
    ),
    Setting(
        _CUDA,
        "CUDA_ARCHITECTURES",
        "",
        "empty (used only with CUDA_ARCH_MODE=custom, which requires it)",
        "GPU compute capabilities without the dot, separated by spaces and quoted, "
        'for example "86 89" for RTX 30 and RTX 40 series cards. Read only when '
        "CUDA_ARCH_MODE is custom.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_CONNECT_TIMEOUT",
        "5",
        "5",
        "Seconds to wait for a download server to answer.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_MAX_TIME",
        "1800",
        "1800 (30 minutes)",
        "Seconds one download may take in total. Raise it on a slow connection.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_RETRY",
        "5",
        "5",
        "How many times a failed download is retried. 0 turns retries off.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_RETRY_DELAY",
        "5",
        "5",
        "Seconds to wait between download retries. 0 retries at once.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_MAX_BYTES",
        "1073741824",
        "1073741824 (1 GiB)",
        "Largest source archive, in bytes, that will be downloaded. A larger file "
        "is refused as a safety limit.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_MAX_EXTRACTED_BYTES",
        "8589934592",
        "8589934592 (8 GiB)",
        "Largest total size, in bytes, that one archive may unpack to. Raise it "
        "only for an unusually large source release.",
    ),
    Setting(
        _DOWNLOADS,
        "DOWNLOAD_MAX_MEMBERS",
        "100000",
        "100000",
        "Most files and folders one archive may contain. Raise it only for an "
        "unusually large source release.",
    ),
    Setting(
        _LOOKUPS,
        "VERSION_CHECK_MAX_TIME",
        "15",
        "15",
        "Seconds one check for a project's newest release may take.",
    ),
    Setting(
        _LOOKUPS,
        "FREEDESKTOP_RELEASE_INDEX_MAX_TIME",
        "5",
        "5",
        "Seconds to read FreeType's release list from savannah.gnu.org before "
        "trying FreeDesktop's GitLab instead.",
    ),
    Setting(
        _LOOKUPS,
        "FREEDESKTOP_RELEASE_CONNECT_TIMEOUT",
        "",
        "DOWNLOAD_CONNECT_TIMEOUT when set, otherwise 2",
        "Seconds to wait for savannah.gnu.org to answer that FreeType release check.",
    ),
    Setting(
        _GIT,
        "GIT_OPERATION_TIMEOUT",
        "120",
        "120 (2 minutes)",
        "Seconds one Git command other than a clone may take, such as looking up "
        "a project's newest release.",
    ),
    Setting(
        _GIT,
        "GIT_CLONE_TIMEOUT",
        "1800",
        "1800 (30 minutes)",
        "Seconds one Git clone may take. Raise it on a slow connection.",
    ),
    Setting(
        _WAITING,
        "HOST_MUTATION_LOCK_TIMEOUT",
        "3600",
        "3600 (1 hour)",
        "Seconds to wait for another run of this script, from any build folder, "
        "that is installing system packages or installing FFmpeg into /usr/local.",
    ),
    Setting(
        _DEVELOPERS,
        BYPASS_CACHE_DELETE,
        "false",
        "false",
        "Set to true to keep the checkout's cache folders (ffbuild, __pycache__, "
        ".pytest_cache, .ruff_cache, .mypy_cache, *.egg-info), which every build "
        "and --cleanup otherwise delete. Only useful when you run this "
        "repository's linter and tests.",
    ),
)


def parse_integer(value: str, *, minimum: int = 1, maximum: int = sys.maxsize) -> int | None:
    pattern = r"[1-9][0-9]*" if minimum else r"[0-9]+"
    if not re.fullmatch(pattern, value):
        return None
    if len(value) > len(str(maximum)):
        return None
    number = int(value)
    return number if minimum <= number <= maximum else None


def parse_switch(value: str) -> bool | None:
    """true/false (also 1/0, yes/no, on/off; empty is false); None when unrecognized."""
    choice = value.strip().lower()
    if choice in _TRUE:
        return True
    if choice in _FALSE:
        return False
    return None
