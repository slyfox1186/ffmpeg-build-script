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

## High severity: deletion races and installation transactions

Deletion previously validated a canonical path and reopened it by absolute
name, allowing an ancestor symlink swap between validation and removal.
Directory traversal now pins each component with O_NOFOLLOW, compares opened
directory identities, and surfaces unexpected errors. Tests substitute an
ancestor at the open boundary and verify outside data survives. Lock acquisition
closes descriptors on interruption; ownership checks run under the build lock.
Noninteractive cleanup no longer upgrades a legacy marker before returning.

Host locks now fail closed (an intentional correction to the former
warn-and-continue behavior). Final installation additionally locks the shared
prefix inode across users/workspaces for the entire backup/promote/validate/
restore transaction. Restoration attempts the remaining programs after an
individual command or logging error. Contention and partial restoration are
covered by regressions. Real privileged installation/rollback is unverified.

## High severity: failed upgrades and static relinking

Remove completion markers before recipes can replace artifacts; also invalidate
FFmpeg and the transitive consumers declared in registry.REQUIREMENTS. Regression
coverage verifies a failed ZenLib upgrade forces MediaInfoLib, MediaInfo CLI and
FFmpeg to rebuild while preserving unrelated NASM state. This deliberately
corrects the incomplete documentation that described only changed versions.
Kimi's suggestion to preserve old markers was rejected: make install writes in
place and does not guarantee old artifacts survive failure. GLM identified this
failure path correctly. Unknown optional upstream dependency detection is not
modeled as a complete dependency graph; a clean workspace remains necessary for
guaranteed reconfiguration of those integrations.

## Medium severity: dependency-only completion

Selecting ffmpeg=false now produces a dependency-build summary without probing
an unrelated /usr/local/bin/ffmpeg. Success reporting precedes interactive
cleanup so it reads capabilities and the log while the workspace still exists.
Capability probes use bounded managed subprocesses and report failures instead
of silently displaying zero capabilities. Regression coverage forbids system
binary probes for a dependencies-only selection.

## High severity: archive expansion and source recovery

Compressed download limits did not bound expanded payloads or member counts.
Validation now enforces 8 GiB of declared data and 100,000 members, including
cached archives and pessimistic hard-link copy costs. These are new documented
environment overrides, not dependency changes. Tests use small limits and real
compressed archives to exercise rejection without consuming gigabytes.
Python's [tarfile security guidance](https://docs.python.org/3/library/tarfile.html#hints-for-further-verification)
and Context7 explicitly caution that data filters alone do not prevent resource
exhaustion; these bounds do not constitute an execution sandbox.

Extraction previously deleted the old source before publishing the replacement.
It now moves the old tree aside and restores it on publication failure; if
restoration fails, recovery files are retained and their location reported.
A rename-failure regression verifies the previous source survives.

## Requested improvement: readable build colors

Elapsed digits are green; package versions in STEP, OK and SKIP are bold yellow.
RUN highlighting uses original argv rather than reparsing shell text: cyan
executables/paths, magenta option names, yellow values, without the former dim
body. Tests verify ANSI-stripped output is byte-for-byte the original quoted
command, including spaces, quotes, control characters and shell syntax.
NO_COLOR and redirection remain plain, and file logs contain no added ANSI.
Real PTY output was captured and its SGR attributes rendered for visual review
at 1200 pixels (`/tmp/ffmpeg-color-preview.png`); exact hues depend on terminal
theme. The screenshots supplied by the user were inspected before this change.

## Requested improvement and medium-severity menu defects

The menu opens on all 15 package types with enabled counts, expands to 127
independent toggles, and supports category jumps, full details/help, presets and
search. Cyan categories and green checkboxes supplement the text indicators.
Narrow layouts retain counts, licensing/latest state and essential actions.

Fixed search clearing/cancellation, cursor-visibility failures, editing below
minimum terminal size, save-path exceptions, stale dirty flags, and hidden
scope of category actions. Text prompts now support immediate Escape,
replacement/editing, horizontal scrolling and Unicode cell widths. Relative
save paths use the invocation directory. The minimal preset previously enabled
all Kind.TOOL packages, including MediaInfo CLI without its required libraries;
it now follows its documented build-tools-and-FFmpeg definition. Normalizing
partial menu allowlists prevents omitted packages from being saved as enabled.

Real curses tests at 80x24 and 40x10 toggle every package off/on independently,
exercise categories, empty results, search clear/cancel, group scope, save
failure, save/reload and Build. A 24x6 test rejects edits and exits safely.
The existing external-keystroke test still verifies edited compiler/jobs reach
the build launcher. Actual screen buffers were inspected at both normal sizes.
The reviewers disagreed about narrow prompts: the old drawing call was inside
its error handler, but cursor visibility changes were outside it; the fix covers
both that verified failure and minimum-size input handling.

## Medium severity: interpreter fallback and numeric input

The launcher probes existing Conda interpreters before selecting them, with a
five-second deadline; stale environments no longer hide compatible system
Python. Bare invocation now reaches side-effect-free help directly. ASCII
integer parsing rejects newline suffixes, Unicode digit lookalikes and values
too large for downstream native settings, including Python's integer conversion
digit limit. Empty timeout overrides consistently use defaults instead of
passing int(""). Tests exercise these inputs before workspace creation and
verify empty Git/font/lock timeouts and stale-interpreter fallback.

## Medium severity: bounded native probes

Compiler/header probes, pkgconf path discovery, and FFmpeg installation checks
now share managed process cleanup with explicit deadlines. Captured probes
default to 30 seconds; FFmpeg checks use 20 seconds. Failed version commands
cannot certify an installed release merely by printing a plausible version.
Duplex input/output and timeout regressions exercise real subprocesses. Failure
log replay streams 64 KiB chunks rather than loading an entire failed build log.
Sudo keepalive shutdown waits for its bounded refresh to finish.

## Native FFmpeg verification

On 2026-09-12, the actual FFmpeg stage downloaded stable 9.0.1, configured and
compiled with GCC/eight jobs, installed into an isolated DESTDIR, and passed
its real version/encoder/decoder validation. A test-only subclass stopped at
the promotion boundary; no sudo/APT or system installation was performed.
The resulting binary encoded a 128x96, ten-frame FFV1 sample. ffprobe verified
codec/dimensions/frame count, and FFmpeg decoded all ten frames to framemd5.
Evidence is retained at `/tmp/ffmpeg-native-audit-_biue3qb/{build.log,result.json}`;
the build plus smoke test took approximately 74 seconds. This selected FFmpeg
alone, with system bzlib/lzma prerequisites; it does not verify 127 native
dependencies, physical GPU integrations, ffplay, or privileged rollback.

## Low severity: recipe consistency and unnecessary work

GitHub tag-prefix fallback now fetches one consistent tag list instead of making
the same network request twice for unprefixed releases or a failed lookup.
Version selection rejects nonpositive indexes and incomplete Git hashes.
Disabled VapourSynth no longer injects a nonexistent Python environment into
later recipes. AviSynth now applies the same CMake package-registry isolation
flags as other recipes, matching the documented policy.

Removed four unreferenced internal helpers/constants, including an unused
recursive replacement helper that bypassed guarded deletion. No public CLI,
configuration schema, or dependency versions changed. The registry contract
check examines raw declarations before dictionary deduplication so duplicate
keys can actually fail validation. The fixture capture wrapper now declares its
signature explicitly, removing its former type-ignore suppression.
