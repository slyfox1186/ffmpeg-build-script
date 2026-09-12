# Python migration audit

This audit uses the documented CLI, configuration and supported-host contracts
as its specification. Native builds and privileged installation require separate
evidence from the fixture suite. Findings below are updated as fixes land.

## High severity: process cancellation

Build commands now run in their own process groups. On cancellation or output
failure, the runner terminates the group, escalates to kill, and waits for the
direct child before unwinding. This covers ordinary compiler descendants;
programs that deliberately detach or change credentials require their own
shutdown protocol. Debug output uses bounded chunks and file-backed stdin to
avoid pipe deadlocks. Optional desktop notifications have a deadline and cannot
mask the original error. Captured non-UTF-8 diagnostics use replacement decoding.

Real subprocess regressions check descendant writes after cancellation in quiet,
debug, terminal and capture modes, plus simultaneous large input/output.
The Python [subprocess documentation](https://docs.python.org/3/library/subprocess.html)
and Context7's CPython documentation informed process-group and pipe handling.

## Review evidence

OpenRouter's coding panel reviewed PLAN.md and repository scripts, modules,
tests, configuration and documentation. Fixtures were sent in a second batch
because the tool's combined attachment limit is 600,000 characters. No ignored
credentials or local configuration were sent. Kimi K3 and GLM 5.3 returned final
reviews after earlier responses exhausted their reasoning budgets.

Their findings are advisory: subprocess.run does kill its direct child when a
BaseException escapes, contrary to one review's claim. The demonstrated gap is
descendant processes. Review disagreements and other accepted/rejected findings
are recorded with the corresponding fixes below.

## High severity: fresh-workspace tool discovery and ZenLib

The reported ZenLib 0.4.41 failure was reproduced in the saved build artifacts:
`Project/GNU/Library/libtool` and `ltmain.sh` contained system Libtool 2.4.7,
while `configure` and the generated script's macro_version contained 2.6.2.
The workspace had Libtool 2.6.2 and matching macros. SystemSetup.source_path
ran before workspace/bin existed; path_prepend skipped it, leaving system
tools active throughout the first build. ACLOCAL_PATH already included the
workspace macros, producing the mismatch. Existing-workspace tests missed it.

Create workspace/bin before adding it to PATH. This restores the documented
workspace-tool preference for every tool installed later, without patching
ZenLib, downgrading dependencies, or discarding the user's completed builds.
The regression installs executable tools after PATH setup and executes them,
then verifies rerun consistency. GNU Libtool and Automake documentation queried
through Context7 confirms that Libtool helpers and macros must be discoverable
from the intended installation; ZenLib's upstream autogen.sh invokes libtoolize
and autoreconf through PATH.

Native verification on 2026-09-12: the cached upstream ZenLib 0.4.41 archive
was extracted into `/tmp/ffmpeg-zenlib-audit-yp8zded8`. The project's real
ensure_autotools and configure_make_install helpers used workspace Libtool
2.6.2, compiled with GCC using eight jobs, installed libzen.a into that isolated
prefix, and passed the real pkgconf artifact/version check in six seconds.
The user's build tree and system installation were not modified by this smoke
build. Logs and result.json remain in that temporary directory.
