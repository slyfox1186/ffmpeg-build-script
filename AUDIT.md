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

The menu presents 15 package types and 127 independent toggles. At 80x24 and
larger, a category sidebar and package pane separate navigation from selection;
short category names, aligned counts, explicit states and a detail area improve
scanning. Wider screens show package descriptions in the list. Cyan frames,
green enabled states and yellow licensing/requirement notices supplement text
indicators. Compact layouts retain counts and essential actions.

Fixed search clearing/cancellation, cursor-visibility failures, editing below
minimum terminal size, save-path exceptions, stale dirty flags, and hidden
scope of category actions. Text prompts now support immediate Escape,
replacement/editing, horizontal scrolling and Unicode cell widths. Relative
save paths use the invocation directory. The minimal preset previously enabled
all Kind.TOOL packages, including MediaInfo CLI without its required libraries;
it now follows its documented build-tools-and-FFmpeg definition. Normalizing
partial menu allowlists prevents omitted packages from being saved as enabled.

Real curses tests at 120x36, 80x24 and 40x10 toggle every package off/on independently,
exercise categories, empty results, search clear/cancel, group scope, save
failure, save/reload and Build. A 24x6 test rejects edits and exits safely.
The external-keystroke test verifies edited compiler/jobs reach the build launcher.
Actual screen buffers and rendered previews were inspected at all three sizes;
`/tmp/ffmpeg-menu-120-overview.png` and `/tmp/ffmpeg-menu-80-gpu.png` retain examples.
The reviewers disagreed about narrow prompts: the old drawing call was inside
its error handler, but cursor visibility changes were outside it; the fix covers
both that verified failure and minimum-size input handling.

The second review's verified menu fixes add 50-step selection undo (including
bulk presets), freeze folds while searching, and validate candidate launch edits
before retaining them. Environment validation runs before opening the editor;
Build validates unsafe roots and bounded CUDA targets before saving. Build roots
expand tilde consistently with save paths. A summary warning names selected
FFmpeg integrations left inactive without GPL authorization. Tests cover both
license modes, invalid values, saved-file preservation and tilde launch paths.

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

## Requested compiler reporting and Clang verification

Startup now reports the selected C and C++ compiler version banners and their
PATH-resolved invocation names after host setup. Probes retain ccache symlink
names so they invoke the underlying compiler rather than querying ccache itself.
Tests cover GCC, G++, Clang, Clang++, wrapper symlinks, and failed probes.

The user's real M4 1.4.21 config.log records CC=clang, CXX=clang++ and Ubuntu
Clang 20.1.2; its generated Makefile uses `clang -std=gnu23`. The repository sets
CC/CXX in the child environment for Autotools, CMake and Meson; FFmpeg additionally
receives explicit --cc/--cxx. No recipe overrides to GCC were found. This setting
controls C/C++ compilation, not Rust, Java, assembly, or NVIDIA's nvcc.

A second isolated native FFmpeg 9.0.1 build with Clang 20.1.2 passed staged
installation checks and the same ten-frame FFV1 encode/probe/decode test.
`/tmp/ffmpeg-native-audit-7de6pm5p` retains logs, result.json, and ffbuild/config.mak
with CC=clang and CXX=clang++. No host installation was performed.

## High/medium severity: cancellation recovery and deep cleanup

Independent review reproduced a raw RecursionError on a valid 1,100-level source
tree. Deletion now uses iterative post-order traversal, retaining descriptor
pinning and inode/device checks. A real deep-tree regression verifies removal.
Personal follow-up found an interruption window immediately after moving the
old source aside: abort cleanup could remove its registered staging directory.
Staging leaves disposable cleanup before that move; an injected interrupt after
the actual rename proves recovery data survives teardown.

## High severity: privileged cancellation ordering

The installed sudo(8) manual confirms sudo relays signals and reports its
command's termination, but cannot relay SIGKILL. Logged sudo mutations now
receive TERM and are awaited without forcibly killing the signal relay. This
keeps rollback and lock release behind command termination. The review's
suggested 30-second grace only moves the same unsafe cutoff; it was not adopted.
Signal-permission errors are attached to the original failure instead of masking
it. A real process requiring more than one second to shut down verifies ordering.
Actual root-owned installer cancellation remains unverified. Kernel D-state or
a privileged command that never terminates can still block shutdown; abandoning
it and releasing locks would permit concurrent writes, so that is not treated
as a safe timeout optimization.

GLM's claimed backup-failure deletion was false: backup_installed_programs is
outside the promotion try/except. An injected backup failure now explicitly
tests that neither installation nor rollback runs and old programs survive.

## Medium severity: pinned repair behavior

GLM correctly identified that an artifact-missing normal resume discarded the
recorded release and queried upstream. It now repairs the pinned version;
build() remains responsible for artifact checks and consumer invalidation.
This also removes a redundant artifact probe on every normal version lookup.
The regression forbids the network fetcher and verifies consumer invalidation.

The same review's Git aside exposed another inconsistency: a matching cached
checkout was recloned when only its installed artifacts were missing. Git repairs
now retain that checkout and let build() handle artifacts and invalidation.
When no matching checkout exists, normal resume preserves the marker and fails
with restore/--latest guidance instead of silently upgrading. This intentionally
changes the old refresh behavior to satisfy README's pinned-version contract;
the code was wrong, not that promise. Local Git object IDs must be exactly 40 or
64 hex digits. Source publication now retains the old checkout until rename
succeeds, restores it on failure, and preserves recovery after an interrupt.
Tests cover missing artifacts, missing/mismatched source, object ID lengths,
publication/restore failures and interruption immediately after the backup move.

## Second review disposition

The completed core and integration panels returned 15 numbered findings. Each
was checked against its actual caller and behavior; the table records decisions
in addition to the causal explanations and regressions above.

| Review finding | Verification and disposition |
| --- | --- |
| Kimi: privileged child may outlive forcibly killed sudo | Confirmed signal-relay risk using sudo(8); fixed ordering. Rejected a longer arbitrary kill deadline and the suggestion that sudo -k terminates a session: it invalidates cached credentials. |
| Kimi: initial sudo authentication is unbounded | True that require_sudo has no timeout; false that it is the only unbounded command. It is interactive authentication, not a native probe. Retained human-controlled authentication rather than inventing a 60-second password deadline. A hung PAM service remains unverified. |
| Kimi: recursive cleanup can crash | Reproduced with 1,100 nested directories; replaced Python recursion with iterative traversal. |
| Kimi: duplicate archive validation | Confirmed. Three validation passes on the 12,036,420-byte native FFmpeg archive took 0.400, 0.392 and 0.391 seconds each with the local cache warm. Kept validation at independent cache/extraction boundaries; the proposed inode/size/mtime cache is not proof of unchanged content. Larger archives remain a possible optimization, not a measured multi-minute defect here. |
| GLM: failed backup enters destructive rollback | False: the backup call is outside the promotion exception handler. A regression injects backup failure and forbids install/rollback, preserving all originals. |
| GLM: artifact repair discards the pinned release | Confirmed and fixed for releases and matching Git checkouts. The suggested example of deleting libzen.a alone is not covered by metadata-only artifact detection; this remains a limitation. |
| GLM: forward hard links should be accepted | The real Python 3.12 data-filter extractor raises KeyError when a hard link precedes its target. Retained rejection; no supplied upstream archive demonstrated a need for a different extraction engine. |
| GLM: final wait can hang on kernel D-state | Correct residual limitation. Documented; rejected abandoning a writer and releasing locks before it stops. |
| Kimi: presets can lose unsaved selections | Confirmed; added 50-step undo covering individual and bulk changes, instead of another confirmation prompt. |
| Kimi: search hides persistent fold changes | Confirmed; fold commands preserve the pre-search state. |
| Kimi: invalid launch edits remain applied | Confirmed; validate a candidate copy before retaining it. |
| Kimi: relative save directory is only accidentally correct | Not a current defect: production code never changes process cwd. Child cwd arguments do not change the parent. Kept invocation-relative saving without a speculative extra parameter. |
| GLM: invalid request fails only after menu saves | Confirmed for environment and edited-root inputs; now validate before editor entry or before Build saves, respectively. |
| GLM: build-root tilde is treated literally | Confirmed; expand it on validation and launch, with an actual menu-to-context regression. |
| GLM: GPL-gated choices vanish from the summary | Confirmed as a reporting gap; added a warning naming inactive FFmpeg integrations while preserving documented licensing behavior. |

The reviewers' agreement on host-satisfiable requirements matches the README:
the menu warns and the build checks the host. It must not reject those choices
unconditionally. Their numeric per-keystroke timing estimates were not measured
by the reviewers and are not treated as benchmark evidence; no selection cache
was introduced for the 127-package model.

## Behavior changes and remaining verification

The requested AMF default is now true in example.toml and the menu template;
GPL authorization and AMD hardware gates still apply. The help includes the
requested latest/GPL example. New archive expansion/member limits and fail-closed
host locks are explicit safety behavior changes. No dependency version or
existing CLI/TOML key was silently changed; the two new limit environment
overrides and menu undo key are documented. No ignored config.toml was created.

Native GCC and Clang FFmpeg builds and the ZenLib build above passed. These do
not prove all 127 native builds, all advertised Debian/Ubuntu/WSL combinations,
GPU paths, ffplay, or real privileged install/rollback. Artifact metadata checks
do not certify every installed archive/header; undeclared optional dependency
relationships still require a clean workspace. Prefix rollback covers the three
programs, not an entire /usr/local snapshot. Advisory locks are cooperative;
same-device bind mounts and hostile processes are not a sandbox boundary.
Archive limits do not fully bound decompressor/PAX-header CPU or memory usage.

Railway CLI reports no linked project for this checkout. Read-only service-source
queries covered all 18 accessible services in six projects, with no source
repository matching this one. No Railway config/server entry point is tracked.
GitHub CI is the available release gate; a Railway deployment cannot be claimed
without a configured service association. No unrelated service was created.
