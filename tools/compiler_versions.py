#!/usr/bin/env python3
"""Report the highest installed and APT-visible versions of GCC and Clang."""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ffmpeg_build.runtime.shellquote import quote
from ffmpeg_build.runtime.versioncmp import version_sort

COMPILERS = ("gcc", "g++", "clang", "clang++")


def collect_search_roots() -> list[Path]:
    home = os.environ.get("HOME", "")
    candidates = os.environ.get("PATH", "").split(os.pathsep)
    candidates += ["/usr/bin", "/usr/local/bin", "/opt/bin"]
    patterns = ["/opt/*/bin", "/opt/llvm*/bin"]
    if home:
        candidates += [f"{home}/bin", f"{home}/.local/bin"]
        patterns += [f"{home}/opt/*/bin", f"{home}/toolchains/*/bin"]
    for pattern in patterns:
        candidates.extend(sorted(glob.glob(pattern)))
    candidates.extend(os.environ.get("COMPILER_SEARCH_DIRS", "").split(os.pathsep))
    roots: list[Path] = []
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute() or not path.is_dir():
            continue
        resolved = path.resolve()
        if resolved not in roots:
            roots.append(resolved)
    return roots


def compiler_basename_matches(compiler: str, name: str) -> bool:
    return compiler in COMPILERS and bool(re.fullmatch(re.escape(compiler) + r"(-[0-9]+)?", name))


def capture(arguments: list[str]) -> str:
    try:
        completed = subprocess.run(
            arguments, capture_output=True, text=True, check=False, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout if completed.returncode == 0 else ""


def compiler_version(compiler: str, binary: Path) -> str | None:
    if compiler not in COMPILERS or not os.access(binary, os.X_OK):
        return None
    options = ["-dumpfullversion", "-dumpversion"] if compiler in ("gcc", "g++") else ["--version"]
    output = capture([str(binary), *options]).splitlines()
    if not output:
        return None
    version = output[0]
    if compiler.startswith("clang"):
        match = re.search(r"[0-9]+(?:\.[0-9]+){0,2}", version)
        version = match.group() if match else ""
    return version if re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,3}", version) else None


def discover_installed_highest(compiler: str, roots: Sequence[Path]) -> tuple[str, Path] | None:
    best: tuple[str, Path] | None = None
    seen: set[Path] = set()
    for root in roots:
        try:
            candidates = sorted(root.iterdir())
        except OSError:
            continue
        for candidate in candidates:
            if not candidate.is_file() or not compiler_basename_matches(compiler, candidate.name):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            version = compiler_version(compiler, candidate)
            if version is not None and (
                best is None
                or (version != best[0] and version_sort([best[0], version])[-1] == version)
            ):
                best = version, candidate
    return best


def highest_repository_major(compiler: str) -> str | None:
    if compiler not in COMPILERS:
        return None
    package = "clang" if compiler == "clang++" else compiler
    output = capture(["apt", "-o", "APT::Cmd::Disable-Script-Warning=1", "list", f"{package}-*"])
    versions = []
    for line in output.splitlines():
        match = re.fullmatch(re.escape(package) + r"-([0-9]+)", line.split("/", 1)[0])
        if match:
            versions.append(match.group(1))
    return version_sort(versions)[-1] if versions else None


def main(argv: list[str]) -> int:
    if argv:
        print("Usage: compiler_versions.py", file=sys.stderr)
        return 2
    roots = collect_search_roots()
    for compiler in COMPILERS:
        installed = discover_installed_highest(compiler, roots)
        version, path = (
            (installed[0], str(installed[1])) if installed else ("unavailable", "unavailable")
        )
        repository = highest_repository_major(compiler) or "unavailable"
        print(
            f"{compiler} installed_highest={version} installed_path={quote(path)} repo_highest={repository}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
