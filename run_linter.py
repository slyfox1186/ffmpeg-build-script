#!/usr/bin/env python3
"""Run static analysis and the repository's generated-contract checks."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from ffmpeg_build import registry
from ffmpeg_build.config import BuildSettings, default_states, render_config

REPO_ROOT = Path(__file__).resolve().parent


def contract_errors(root: Path) -> list[str]:
    errors: list[str] = []
    template = (root / "example.toml").read_text(encoding="utf-8")
    keys = set(tomllib.loads(template)["packages"])
    registered = set(registry.PACKAGE_NAMES)
    if keys != registered or len(registered) != len(registry.PACKAGE_NAMES):
        errors.append(
            f"Template/registry mismatch: template-only={sorted(keys - registered)}, "
            f"registry-only={sorted(registered - keys)}; duplicate registry keys are forbidden."
        )
    if template != render_config(BuildSettings(), default_states()):
        errors.append(
            "example.toml differs from config.render_config() with the template defaults."
        )

    completed = subprocess.run(
        [sys.executable, "-B", str(root / "build-ffmpeg.py"), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    blocks = [
        block
        for block in re.findall(r"```text\n(.*?)\n```", readme, re.S)
        if "Usage: build-ffmpeg.py" in block
    ]
    if completed.returncode != 0 or blocks != [completed.stdout]:
        errors.append("README.md CLI block must match live --help byte for byte.")

    stage_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (root / "ffmpeg_build/stages").glob("*.py")
    )
    for package in registry.PACKAGES.values():
        for flag in package.ffmpeg_flags:
            if flag not in stage_text:
                errors.append(
                    f"{package.key} advertises {flag}, which is absent from build stages."
                )

    files = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    # Assembling the tokens keeps this checker from flagging its own source.
    forbidden = ("apt" + "-get", "apt" + "-cache")
    for raw_name in sorted(set(files.stdout.split(b"\0")) - {b""}):
        path = root / raw_name.decode("utf-8", "surrogateescape")
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(content.splitlines(), 1):
            if line.rstrip(" \t") != line:
                errors.append(f"{path.relative_to(root)}:{number}: trailing whitespace")
            if path.suffix in (".py", ".sh", ".yml", ".yaml"):
                for token in forbidden:
                    if token in line:
                        errors.append(
                            f"{path.relative_to(root)}:{number}: use apt instead of {token}"
                        )
    return errors


def main() -> int:
    failed = False
    for command in (("ruff", "check", "."), ("ruff", "format", "--check", "."), ("mypy",)):
        result = subprocess.run([sys.executable, "-m", *command], cwd=REPO_ROOT, check=False)
        failed |= result.returncode != 0
    try:
        errors = contract_errors(REPO_ROOT)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        errors = [f"Unable to check repository contracts: {error}"]
    for diagnostic in errors:
        print(diagnostic, file=sys.stderr)
    if not errors:
        print(f"Repository contracts: OK ({len(registry.PACKAGE_NAMES)} packages)")
    return int(failed or bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
