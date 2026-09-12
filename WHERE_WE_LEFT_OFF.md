# Python migration completion record

Updated: 2026-09-12. Release: 8.0.0. Branch: `master`.

The Bash-to-Python migration is implemented. This file replaces the earlier
unfinished-work handoff. Git history and the GitHub Actions run for the release
commit are the source of truth for shipping status.

## Delivered

- `build-ffmpeg.py` is the entry point. Python 3.12 is the minimum; CI covers
  Python 3.12, 3.13, and 3.14. Metadata requests remain side-effect free and the
  bootstrap parses on Python 3.10 so older hosts receive an actionable message.
- The launcher prefers `~/miniconda3/envs/install-ffmpeg`, requests explicit
  consent before creating it, and falls back to a compatible system interpreter
  when creation is declined. Core operation and the curses menu use only the
  standard library. Development tools are optional.
- All 127 package selections are represented in `ffmpeg_build/registry.py`.
  The full menu supports search, groups, presets, dependency checks, licensing,
  config load/save, session build settings, and launching the selected build.
- The runtime preserves workspace/context migration from releases 6 and 7,
  directory locks, host-mutation locking, safe cleanup, isolated child
  environments, download integrity, bounded transport operations, Git snapshot
  identity, diagnostics, GPU/CUDA handling, and staged FFmpeg validation.
- Installation failure, post-install validation failure, and interruption trigger
  restoration of the prior FFmpeg programs. Recovery files survive teardown;
  incomplete restoration is reported explicitly.
- All Bash entry points, implementation files, and Bash tests are removed.
  Python diagnostic tools replace the compiler and Git-tag helper scripts.
- README, generated `example.toml`, strict typing/lint checks, regression tests,
  and the Python CI matrix are updated. Local ignored `CLAUDE.md` guidance was
  updated without changing its existing ignored status.

## Verification evidence

Local environment: Python 3.12.14 in the dedicated `install-ffmpeg` Conda
environment; pytest 9.1.1, Ruff 0.16.7, mypy 2.3.1.

```text
python run_linter.py
  Ruff checks and formatting passed.
  Strict mypy passed for 50 Python files.
  Repository contracts passed for 127 packages.
python -m pytest -q
  212 passed.
```

The contracts check registry/template identity, FFmpeg flag coverage, exact
README/live-help equality, whitespace, and prohibited package-manager commands.
Tests cover validation and side effects, marker migration, lock contention,
cleanup boundaries, malicious archives, cache integrity, environment isolation,
version ordering, diagnostics, hardware/host fixtures, dependency stages,
installation recovery, and real pseudo-terminal menu editing/save/build.

Before removing Bash, its regression suite passed 286 assertions. Captured
Bash outputs match Python for 12 host-package selections and 8 ordered FFmpeg
configure cases. The saved fixtures keep these comparisons in CI; see
`tests/fixtures/README.md` for their provenance and controlled probes.

A native upstream FFmpeg 9.0.1 smoke build completed download, configure,
compilation, DESTDIR installation, and staged binary/version/codec validation.
It used FFmpeg with zlib and stopped at the backup boundary before privileged
promotion. The existing `/usr/local` installation was preserved.

## Verification limits

This work did not rebuild all 127 packages from source or perform a real
privileged replacement of the installed FFmpeg programs. Full dependency-stage
reuse was exercised with isolated workspaces containing actual pkgconf metadata
and inert native artifacts. Installation recovery was tested with controlled
command fixtures. These are distinct from a complete native host installation.

No service deployment is associated with this repository. Release verification
uses GitHub Actions for the exact pushed commit and checks upstream equality.
