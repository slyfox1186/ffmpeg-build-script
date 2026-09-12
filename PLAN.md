# Repository audit plan

Audit the Python migration against README.md, example.toml, pyproject.toml,
CI, the registry, and the tracked migration record. Preserve the standard-library
runtime, public CLI/TOML contracts, package versions, and existing user work.

## Ordered work and acceptance criteria

1. Read every tracked source, test, fixture, and configuration file. Record the
   architecture, documentation disagreements, and missing runtime evidence.
2. Run the existing full gate using
   `/home/jman/miniconda3/envs/install-ffmpeg/bin/python run_linter.py` and
   `/home/jman/miniconda3/envs/install-ffmpeg/bin/python -m pytest`.
3. Send this plan and all repository scripts, source modules, tests, configs,
   and documentation to OpenRouter's coding panel. Check every actionable claim
   personally against code, a reproduction, and current primary documentation;
   record accepted and rejected suggestions before relying on them.
4. Fix demonstrated correctness and safety defects first: launcher validation,
   path containment, locks, archive/Git transactions, subprocess cancellation,
   state reuse, native toolchain isolation, and staged install recovery. Add
   adversarial regressions for causal failure paths.
5. Audit host/compiler/CUDA compatibility and every package recipe against its
   callers and documented contracts. Consult Context7 and upstream documentation
   for uncertain APIs. Flag public interface, dependency version, or documented
   behavior changes explicitly; do not silently alter them.
6. Improve structure and performance only where the complete execution path
   demonstrates a benefit. Fix underlying lint/type issues without hiding them.
   Update affected documentation and preserve the Bash parity fixtures unless
   independent evidence establishes a defect in the baseline.
   Treat the terminal menu as a primary deliverable: retain all 127 individual
   toggles grouped by package type, verify category navigation and group versus
   package actions, search/reset, narrow terminals, save errors, and the complete
   save/reload/build selection path in real pseudo-terminals.
   Explicitly verify empty search clears, Escape preserves the existing filter,
   group actions state that hidden packages are included, and save failures
   retain their message and unsaved selection. Open on a category overview.
7. Commit each independently revertible fix after its focused regressions and
   full gate pass, then rerun the full gate on each commit. Review the complete
   changed paths again after the first green result. Perform a bounded native
   smoke build in an isolated temporary workspace if prerequisites permit;
   keep privileged host installation separate from fixture validation.
8. Fetch/rebase safely, push to the existing GitHub branch, verify upstream SHA
   equality and the exact commit's CI matrix. Establish whether a Railway
   service exists for this repository before claiming a deployment. Record
   remaining unverified native/platform/GPU behavior in AUDIT.md by severity.

## Initial evidence and boundaries

- Starting commit: `4ebede2`, branch `master`, origin
  `https://github.com/slyfox1186/ffmpeg-build-script.git`.
- The worktree already contains a user deletion of `WHERE_WE_LEFT_OFF.md`;
  inspect its HEAD contents for context and leave the deletion out of commits.
- The tracked migration record says there is no service deployment; CI is the
  release gate. No Railway config or server entry point is tracked.
- Local project interpreter: Python 3.12.14; pytest, Ruff, and mypy import.
- Full source compilation for 127 package choices, actual sudo/APT changes,
  privileged rollback, all supported distributions, and physical GPU execution
  require distinct evidence; a green fixture suite does not prove these paths.
- Runtime credentials and ignored local configuration must not be sent to
  reviewers or committed. This plan is a reviewable procedure, not an executable
  installer that could mutate the host merely by reviewing it.
