#!/usr/bin/env python3
"""Run the repository's complete static-analysis gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    lint_script = repo_root / "scripts" / "lint.sh"
    if not lint_script.is_file():
        print(f"Missing lint entrypoint: {lint_script}", file=sys.stderr)
        return 2

    completed = subprocess.run(
        ["bash", str(lint_script)],
        cwd=repo_root,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
