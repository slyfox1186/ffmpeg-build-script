"""The help screen and version string.

Deliberately plain: the launcher imports this module on whatever interpreter
the user happened to start, which on Ubuntu 22.04 is Python 3.10. `--help` and
`--version` are answered before any interpreter resolution, so this file must
parse on every interpreter the project can be launched from and must import
nothing that does not.

The layout is a contract. `README.md` reproduces it verbatim and the linter
diffs the two byte for byte, so descriptions start at column 37 and the widths
below are what put them there.
"""

from __future__ import annotations

SCRIPT_VERSION = "8.1.0"
SCRIPT_NAME = "build-ffmpeg.py"

LABEL_WIDTH = 33

ACTIONS = (
    ("-b, --build", "Build and install FFmpeg"),
    ("-c, --cleanup", "Remove this project's build root and build leftovers"),
    ("-m, --menu", "Choose packages in an interactive menu"),
)
OPTIONS = (
    ("-h, --help", "Show this help without changing the filesystem"),
    ("-v, --version", "Show the script version"),
    ("    --compiler <gcc|clang>", "Override the config compiler (default: gcc)"),
    ("    --gcc / --clang", "Aliases for --compiler gcc / --compiler clang"),
    ("    --config <path>", "Load build/package choices from TOML"),
    ("-j, --jobs <count>", "Set parallel build jobs (default: available CPUs)"),
    ("-l, --latest", "Refresh and rebuild outdated dependencies"),
    ("-n, --enable-gpl-and-non-free", "Enable GPL/non-free components"),
)
ENVIRONMENT = (
    ("BUILD_ROOT=/path", "Override the default ./build directory"),
    ("CUDA_INSTALL=ask|always|never", "Control CUDA toolkit installation (default: ask)"),
    ("CUDA_ARCH_MODE=native|all|custom", "Select CUDA code-generation targets"),
    ('CUDA_ARCHITECTURES="86 89"', "Targets for CUDA_ARCH_MODE=custom"),
    ("FFMPEG_BUILD_DEBUG=ON", "Stream commands while also logging them"),
)

# Options that take a separate argument. Every walk over the command line skips
# that argument and stops at `--`, so an option's value is never mistaken for an
# option: `--compiler -h` means a compiler named '-h', not a request for help.
TAKES_VALUE = frozenset(["--compiler", "--config", "-j", "--jobs"])


def _row(label: str, description: str) -> str:
    return "  " + label.ljust(LABEL_WIDTH) + " " + description


def usage_text() -> str:
    lines = [
        "",
        "FFmpeg Build Script " + SCRIPT_VERSION,
        "Usage: " + SCRIPT_NAME + " [options]",
        "",
        "Actions:",
    ]
    lines += [_row(label, description) for label, description in ACTIONS]
    lines += ["", "Options:"]
    lines += [_row(label, description) for label, description in OPTIONS]
    lines += [
        "",
        "Long options also accept --option=value (for example: --jobs=8).",
        "",
        "Environment:",
    ]
    lines += [_row(label, description) for label, description in ENVIRONMENT]
    lines += [
        "",
        "Example:",
        "  python3 " + SCRIPT_NAME + " --build --compiler clang --jobs 8 --config ./custom.toml",
        "  python3 " + SCRIPT_NAME + " --build --latest --enable-gpl-and-non-free",
        "",
    ]
    return "\n".join(lines) + "\n"


def metadata_response(argv: list[str]) -> str | None:
    """Answer `--help`/`--version`, or return None when neither was requested.

    This walk runs before the interpreter is resolved, so on that path it is
    the only thing standing between `-- -h` and a help screen.
    """
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--":
            return None
        if argument in ("-h", "--help"):
            return usage_text()
        if argument in ("-v", "--version"):
            return SCRIPT_VERSION + "\n"
        if argument in TAKES_VALUE:
            index += 1
        index += 1
    return None
