# Bash parity fixtures

These JSON files were captured before removing the Bash implementation based on
commit `b0dbef5` (release 7.0.0), with the already-requested obsolete speech hook
removed. They are reference outputs from Bash, not expectations generated from
the Python implementation.

- `host-packages.json`: 12 sorted host-package lists for GCC/Clang, GPL on/off,
  and all/template/empty package selections.
- `configure-options.json`: 8 ordered FFmpeg configure argument lists for
  all/template selections, GPL on/off, and GPU absent/present.

The configure capture sourced the Bash stages with completed workspace markers,
controlled dependency probes, and recorded the final configure command. The
Python comparison runs the corresponding stages against a completed workspace
with real pkgconf metadata. Host-dependent compiler and GPU probes are held
constant, including the executable search path, and temporary workspace paths
are normalized. Argument order remains significant.

`tests/test_workspace.py` checks these reference files on every CI interpreter.
The independent native smoke build is documented in `WHERE_WE_LEFT_OFF.md`; it
is not performed by these fixtures or CI.
