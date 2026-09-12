#!/usr/bin/env bash
# Literal bash -c programs and pkg-config variables in this test are intentional.
# shellcheck disable=SC2016

set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
temporary_parent="$(readlink -f -- "${TMPDIR:-/tmp}")"
temporary_root="$(mktemp -d --tmpdir="$temporary_parent")"

cleanup_temporary_root() {
    [[ -n "${temporary_root:-}" && -d "$temporary_root" ]] || return 0
    [[ "${temporary_root%/*}" == "$temporary_parent" &&
        "${temporary_root##*/}" == tmp.* ]] || {
        printf 'Refusing to remove unexpected test directory: %s\n' "$temporary_root" >&2
        return 1
    }
    rm -rf --one-file-system -- "$temporary_root"
}

trap cleanup_temporary_root EXIT

pass_count=0

pass() {
    ((pass_count += 1))
    printf 'ok %d - %s\n' "$pass_count" "$1"
}

fail_test() {
    printf 'not ok %d - %s\n' "$((pass_count + 1))" "$1" >&2
    exit 1
}

assert_equal() {
    local expected="${1-}" actual="${2-}" description="${3:-values match}"
    [[ "$actual" == "$expected" ]] || {
        printf 'expected: %q\nactual:   %q\n' "$expected" "$actual" >&2
        fail_test "$description"
    }
    pass "$description"
}

assert_contains() {
    local haystack="${1-}" needle="${2-}" description="${3:-text is present}"
    [[ "$haystack" == *"$needle"* ]] || {
        printf 'missing text: %q\noutput:       %q\n' "$needle" "$haystack" >&2
        fail_test "$description"
    }
    pass "$description"
}

assert_not_contains() {
    local haystack="${1-}" needle="${2-}" description="${3:-text is absent}"
    [[ "$haystack" != *"$needle"* ]] || {
        printf 'unexpected text: %q\noutput:          %q\n' "$needle" "$haystack" >&2
        fail_test "$description"
    }
    pass "$description"
}

assert_file() {
    local file="${1:-}" description="${2:-file exists}"
    [[ -f "$file" ]] || fail_test "$description"
    pass "$description"
}

assert_not_exists() {
    local path="${1:-}" description="${2:-path does not exist}"
    [[ ! -e "$path" && ! -L "$path" ]] || fail_test "$description"
    pass "$description"
}

# Rejects 127 as well as success. Every one of these drives a project function,
# so "command not found" means the function was renamed or its script failed to
# source, and accepting any non-zero status let that pass as a green assertion.
assert_command_fails() {
    local description="${1:-command fails}"
    local status
    shift

    if "$@" >/dev/null 2>&1; then
        status=0
    else
        status=$?
    fi
    if ((status == 0)); then
        fail_test "$description"
    fi
    if ((status == 127)); then
        printf 'command or function not found (exit 127): %q\n' "$1" >&2
        fail_test "$description"
    fi
    pass "$description"
}

help_root="$temporary_root/help-root"
help_output="$(BUILD_ROOT="$help_root" bash "$repo_root/build-ffmpeg.sh" --help)"
[[ "$help_output" == *"FFmpeg Build Script"* ]] || fail_test "--help prints usage"
assert_contains "$help_output" "--config ./custom.toml" \
    "--help uses the custom configuration filename"
printf -v retired_config_name '%s.%s' local toml
assert_not_contains "$help_output" "$retired_config_name" \
    "--help does not reference the retired local configuration filename"
help_descriptions=(
    'Build and install FFmpeg'
    "Remove this project's build root"
    'Show this help without changing the filesystem'
    'Show the script version'
    'Select the C/C++ compiler (default: gcc)'
    'Load build/package choices from TOML'
    'Set parallel build jobs (default: available CPUs)'
    'Refresh and rebuild outdated dependencies'
    'Enable GPL/non-free components'
    'Announce failures if google_speech is installed'
    'Override the default ./build directory'
    'Control CUDA toolkit installation (default: ask)'
    'Select CUDA code-generation targets'
    'Stream commands while also logging them'
)
for help_description in "${help_descriptions[@]}"; do
    help_description_column="$(
        awk -v needle="$help_description" \
            'index($0, needle) { print index($0, needle); exit }' <<<"$help_output"
    )"
    [[ "$help_description_column" == "37" ]] || {
        printf 'misaligned help description: %s (column %s)\n' \
            "$help_description" "${help_description_column:-missing}" >&2
        fail_test "--help aligns every table description"
    }
done
pass "--help aligns every table description"
assert_not_exists "$help_root" "--help has no filesystem side effects"

version_output="$(BUILD_ROOT="$temporary_root/version-root" bash "$repo_root/build-ffmpeg.sh" --version)"
assert_equal "6.0.0" "$version_output" "--version is exact and side-effect free"
assert_not_exists "$temporary_root/version-root" "--version does not create BUILD_ROOT"

unknown_option_root="$temporary_root/unknown-option-root"
if unknown_option_output="$(
    env BUILD_ROOT="$unknown_option_root" \
        bash "$repo_root/build-ffmpeg.sh" --definitely-unknown 2>&1
)"; then
    fail_test "unknown CLI options fail"
fi
pass "unknown CLI options fail"
assert_contains "$unknown_option_output" "Unknown option '--definitely-unknown'." \
    "unknown CLI option is quoted in diagnostics"
assert_not_exists "$unknown_option_root" "invalid CLI input has no filesystem side effects"

# FFMPEG_BUILD_DEBUG only selects log verbosity, so an invalid value must not
# abort a run that logs nothing. "With no action, the script prints help" is a
# documented contract and has to hold whatever this variable is set to.
debug_help_root="$temporary_root/debug-help-root"
debug_help_output="$(
    env BUILD_ROOT="$debug_help_root" FFMPEG_BUILD_DEBUG=on \
        bash "$repo_root/build-ffmpeg.sh" 2>&1
)" || fail_test "an invalid FFMPEG_BUILD_DEBUG value still prints help"
pass "an invalid FFMPEG_BUILD_DEBUG value still prints help"
assert_contains "$debug_help_output" "Usage: build-ffmpeg.sh [options]" \
    "the no-action help text is the usage table"
assert_not_exists "$debug_help_root" \
    "an invalid FFMPEG_BUILD_DEBUG value has no filesystem side effects"

debug_build_root="$temporary_root/debug-build-root"
if debug_build_output="$(
    env BUILD_ROOT="$debug_build_root" FFMPEG_BUILD_DEBUG=on \
        bash "$repo_root/build-ffmpeg.sh" --build 2>&1
)"; then
    fail_test "an invalid FFMPEG_BUILD_DEBUG value fails the build"
fi
pass "an invalid FFMPEG_BUILD_DEBUG value fails the build"
assert_contains "$debug_build_output" \
    "'FFMPEG_BUILD_DEBUG' must be 'ON' or 'OFF'; got 'on'" \
    "the rejected FFMPEG_BUILD_DEBUG value is quoted in diagnostics"
assert_not_exists "$debug_build_root" \
    "a rejected FFMPEG_BUILD_DEBUG value aborts before the build root is created"

# Every long option accepts both the separated and the "=" form. --cleanup on a
# build root that does not exist is the only action that exercises a full parse
# without needing sudo or the network.
for accepted_jobs_form in "--jobs=8" "-j 8" "--jobs 8"; do
    jobs_form_root="$temporary_root/jobs-form-root"
    # shellcheck disable=SC2086 # the forms under test are two separate words.
    jobs_form_output="$(
        env BUILD_ROOT="$jobs_form_root" \
            bash "$repo_root/build-ffmpeg.sh" --cleanup $accepted_jobs_form 2>&1
    )" || fail_test "the '$accepted_jobs_form' jobs form is accepted"
    pass "the '$accepted_jobs_form' jobs form is accepted"
    assert_contains "$jobs_form_output" "nothing to clean" \
        "the '$accepted_jobs_form' jobs form reaches the requested action"
done

for rejected_jobs_value in "0" "-1" "abc" "8x" ""; do
    jobs_value_root="$temporary_root/jobs-value-root"
    if jobs_value_output="$(
        env BUILD_ROOT="$jobs_value_root" \
            bash "$repo_root/build-ffmpeg.sh" --cleanup "--jobs=$rejected_jobs_value" 2>&1
    )"; then
        fail_test "'--jobs=$rejected_jobs_value' is rejected"
    fi
    pass "'--jobs=$rejected_jobs_value' is rejected"
    assert_contains "$jobs_value_output" \
        "Invalid jobs value '$rejected_jobs_value'; expected a positive integer." \
        "'--jobs=$rejected_jobs_value' quotes the offending value"
    assert_not_exists "$jobs_value_root" \
        "'--jobs=$rejected_jobs_value' has no filesystem side effects"
done

for rejected_compiler_form in "--compiler=bogus" "--compiler bogus"; do
    compiler_root="$temporary_root/compiler-root"
    # shellcheck disable=SC2086 # the forms under test are two separate words.
    if compiler_output="$(
        env BUILD_ROOT="$compiler_root" \
            bash "$repo_root/build-ffmpeg.sh" --cleanup $rejected_compiler_form 2>&1
    )"; then
        fail_test "'$rejected_compiler_form' is rejected"
    fi
    pass "'$rejected_compiler_form' is rejected"
    assert_contains "$compiler_output" \
        "Invalid compiler 'bogus'; expected 'gcc' or 'clang'." \
        "'$rejected_compiler_form' quotes the offending value"
    assert_not_exists "$compiler_root" \
        "'$rejected_compiler_form' has no filesystem side effects"
done

exclusive_root="$temporary_root/exclusive-root"
if exclusive_output="$(
    env BUILD_ROOT="$exclusive_root" \
        bash "$repo_root/build-ffmpeg.sh" --build --cleanup 2>&1
)"; then
    fail_test "'--build' and '--cleanup' are mutually exclusive"
fi
pass "'--build' and '--cleanup' are mutually exclusive"
assert_contains "$exclusive_output" "'--build' and '--cleanup' are mutually exclusive." \
    "the mutual-exclusion diagnostic names both actions"
assert_not_exists "$exclusive_root" \
    "requesting both actions has no filesystem side effects"

missing_config_root="$temporary_root/missing-config-root"
if missing_config_output="$(
    env BUILD_ROOT="$missing_config_root" \
        bash "$repo_root/build-ffmpeg.sh" --build --config 2>&1
)"; then
    fail_test "missing config values fail"
fi
pass "missing config values fail"
assert_contains "$missing_config_output" "Missing value for '--config'." \
    "CLI option is quoted in missing-value diagnostics"
assert_not_exists "$missing_config_root" "missing config values have no filesystem side effects"

# fail() ends in `exit 1`, which inside $(...) ends only the subshell: the
# caller keeps going with an empty PACKAGE_CONFIG_FILE, which package_enabled()
# reads as "no allowlist supplied" and so builds every package. Each rejected
# value must abort with a non-zero status instead.
for rejected_config_value in "" "$(printf 'bad\tpath.toml')"; do
    rejected_config_root="$temporary_root/rejected-config-root"
    if rejected_config_output="$(
        env BUILD_ROOT="$rejected_config_root" \
            bash "$repo_root/build-ffmpeg.sh" --build --config "$rejected_config_value" 2>&1
    )"; then
        fail_test "rejected --config value fails instead of building everything"
    fi
    pass "rejected --config value fails instead of building everything"
    assert_contains "$rejected_config_output" "Invalid value for '--config'." \
        "rejected --config value reports the offending option"
    assert_not_contains "$rejected_config_output" "Loaded package selection config" \
        "rejected --config value never loads a package selection"
    assert_not_exists "$rejected_config_root" \
        "rejected --config value has no filesystem side effects"
done

# Arguments are validated before the config is read, so an invalid request
# never gets as far as opening and applying a TOML file.
late_error_root="$temporary_root/late-error-root"
if late_error_output="$(
    env BUILD_ROOT="$late_error_root" \
        bash "$repo_root/build-ffmpeg.sh" \
        --config "$repo_root/example.toml" --definitely-unknown 2>&1
)"; then
    fail_test "an invalid argument is reported before any config is loaded"
fi
pass "an invalid argument is reported before any config is loaded"
assert_contains "$late_error_output" "Unknown option '--definitely-unknown'." \
    "the invalid argument is what gets reported"
assert_not_contains "$late_error_output" "Loaded package selection config" \
    "no package selection is loaded when the request is invalid"

# -h and -v are recognized as actions, never as another option's value and never
# after `--`. `--compiler -h` asks for a compiler named '-h', which is invalid.
for misplaced_help_form in "--build --compiler -h" "-- -h" "-- --version"; do
    misplaced_help_root="$temporary_root/misplaced-help-root"
    # shellcheck disable=SC2086 # the forms under test are separate words.
    if misplaced_help_output="$(
        env BUILD_ROOT="$misplaced_help_root" \
            bash "$repo_root/build-ffmpeg.sh" $misplaced_help_form 2>&1
    )"; then
        fail_test "'$misplaced_help_form' is not treated as a metadata request"
    fi
    pass "'$misplaced_help_form' is not treated as a metadata request"
    assert_not_contains "$misplaced_help_output" "Usage: build-ffmpeg.sh [options]" \
        "'$misplaced_help_form' does not print the usage table"
    assert_not_exists "$misplaced_help_root" \
        "'$misplaced_help_form' has no filesystem side effects"
done

# A relative --config resolves against the invocation directory only. Retrying
# under the script's own directory would pick up a stale custom.toml living
# next to build-ffmpeg.sh without saying so.
script_dir_config_root="$temporary_root/script-dir-config-root"
if script_dir_config_output="$(
    cd -- "$temporary_root" &&
        env BUILD_ROOT="$script_dir_config_root" \
            bash "$repo_root/build-ffmpeg.sh" --cleanup --config example.toml 2>&1
)"; then
    fail_test "a relative --config is not retried beside the script"
fi
pass "a relative --config is not retried beside the script"
assert_not_contains "$script_dir_config_output" "Loaded package selection config" \
    "a relative --config never loads the copy beside the script"

# A shared helper called from thirty stage-script sites reports the same
# "Line: ${LINENO}" every time, so fail() also names the frame two levels up:
# the package recipe that invoked the helper.
fail_origin_script="$temporary_root/fail-origin-stage.sh"
printf '%s\n' \
    'source "$1/scripts/shared-utils.sh"' \
    'shared_helper() { fail "helper rejected its input"; }' \
    'package_recipe() { shared_helper; }' \
    'package_recipe' \
    >"$fail_origin_script"
if fail_origin_output="$(bash "$fail_origin_script" "$repo_root" 2>&1)"; then
    fail_test "fail() exits non-zero"
fi
pass "fail() exits non-zero"
assert_contains "$fail_origin_output" "Raised from: fail-origin-stage.sh:3" \
    "fail() names the recipe frame, not the shared helper"

# The resolve_*/git_clone helpers report with warn() and return non-zero rather
# than calling fail(), so a caller that checks the status actually aborts.
if captured_helper_output="$(
    bash -c '
        source "$1/scripts/shared-utils.sh"
        workspace="$2"
        resolved="$(resolve_tool_path definitely-absent-tool)" || exit 3
        printf "UNREACHABLE:%s\n" "$resolved"
    ' _ "$repo_root" "$temporary_root" 2>&1
)"; then
    fail_test "a failing resolve_* capture aborts its caller"
fi
pass "a failing resolve_* capture aborts its caller"
assert_not_contains "$captured_helper_output" "UNREACHABLE" \
    "a failing resolve_* capture does not fall through with an empty value"

# The root refusal has to sit in main(), not run_build(): --cleanup is the one
# destructive action in the project and it never reaches run_build().
if root_refusal_output="$(
    bash -c '
        source "$1/scripts/shared-utils.sh"
        require_non_root 0
        printf "UNREACHABLE\n"
    ' _ "$repo_root" 2>&1
)"; then
    fail_test "running as root is refused"
fi
pass "running as root is refused"
assert_contains "$root_refusal_output" "as a normal user" \
    "root refusal explains the requirement"
assert_not_contains "$root_refusal_output" "UNREACHABLE" \
    "root refusal stops execution"
if ! bash -c '
    source "$1/scripts/shared-utils.sh"
    require_non_root 1000
' _ "$repo_root" >/dev/null 2>&1; then
    fail_test "an unprivileged UID is accepted"
fi
pass "an unprivileged UID is accepted"

unmarked_root="$temporary_root/unmarked-root"
mkdir -p "$unmarked_root"
printf 'not build data\n' >"$unmarked_root/user-file"
assert_command_fails "cleanup refuses an unmarked build root" \
    env BUILD_ROOT="$unmarked_root" bash "$repo_root/build-ffmpeg.sh" --cleanup
assert_file "$unmarked_root/user-file" "refused cleanup preserves unrelated data"

# An interrupt between creating the build root and writing its marker left a
# populated unmarked directory that neither --build nor --cleanup would touch
# again. A root holding only this project's own empty scaffolding is adopted;
# one holding anything else is still refused.
wedged_root="$temporary_root/wedged-root"
mkdir -p "$wedged_root/packages" "$wedged_root/workspace"
wedged_output="$(
    env BUILD_ROOT="$wedged_root" bash "$repo_root/build-ffmpeg.sh" --cleanup 2>&1
)" || fail_test "cleanup adopts a root holding only empty scaffolding"
pass "cleanup adopts a root holding only empty scaffolding"
assert_contains "$wedged_output" "empty scaffolding from an interrupted run" \
    "adopted scaffolding is reported"
printf 'not build data\n' >"$wedged_root/packages/user-file"
assert_command_fails "cleanup still refuses scaffolding holding foreign data" \
    env BUILD_ROOT="$wedged_root" bash "$repo_root/build-ffmpeg.sh" --cleanup
assert_file "$wedged_root/packages/user-file" \
    "refused scaffolding cleanup preserves unrelated data"

# Both guards compared the repository root by equality only, so a build root
# that CONTAINS the repository was accepted and a later cleanup would have
# taken the repository with it.
assert_command_fails "a build root containing the repository is refused" \
    env BUILD_ROOT="$repo_root/.." bash "$repo_root/build-ffmpeg.sh" --cleanup
for unsafe_build_root in /home /usr/local; do
    assert_command_fails "'$unsafe_build_root' is refused as a build root" \
        env BUILD_ROOT="$unsafe_build_root" bash "$repo_root/build-ffmpeg.sh" --cleanup
done
whitespace_root="$temporary_root/build root with spaces"
mkdir -p "$whitespace_root"
whitespace_output="$(
    env BUILD_ROOT="$whitespace_root" bash "$repo_root/build-ffmpeg.sh" --cleanup 2>&1
)" && fail_test "a build root containing whitespace is refused on the cleanup path"
pass "a build root containing whitespace is refused on the cleanup path"
assert_contains "$whitespace_output" "may not contain whitespace" \
    "whitespace refusal explains the constraint"

# shellcheck source=scripts/shared-utils.sh
source "$repo_root/scripts/shared-utils.sh"
# Consumed by sourced shared utility functions.
# shellcheck disable=SC2034
script_dir="$repo_root"
packages="$temporary_root/packages"
workspace="$temporary_root/workspace"
# Consumed by sourced shared utility functions.
# shellcheck disable=SC2034
log_file="$temporary_root/test.log"
LATEST=false
# Consumed by sourced shared utility functions.
# shellcheck disable=SC2034
NONFREE_AND_GPL=false
# Consumed by sourced shared utility functions.
# shellcheck disable=SC2034
CONFIGURE_OPTIONS=()
mkdir -p "$packages" "$workspace"
: >"$log_file"

assert_equal "trimmed value" "$(trim_whitespace '  trimmed value  ')" "trim_whitespace"
is_true true || fail_test "is_true accepts true"
pass "is_true accepts true"
! is_true TRUE || fail_test "is_true rejects non-canonical values"
pass "is_true rejects non-canonical values"

marker_root="$temporary_root/marker-root"
marker_copy_root="$temporary_root/marker-copy-root"
mkdir -p "$marker_root" "$marker_copy_root"
write_build_root_marker "$marker_root"
build_root_marker_matches "$marker_root/.ffmpeg-build-root" "$marker_root" ||
    fail_test "path-bound build-root marker validates at its recorded root"
pass "path-bound build-root marker validates at its recorded root"
cp "$marker_root/.ffmpeg-build-root" "$marker_copy_root/.ffmpeg-build-root"
assert_command_fails "copied build-root markers do not validate elsewhere" \
    build_root_marker_matches "$marker_copy_root/.ffmpeg-build-root" "$marker_copy_root"

lock_root="$temporary_root/lock-root"
mkdir -p "$lock_root"
exec {held_lock_fd}<"$lock_root"
flock -n "$held_lock_fd"
assert_command_fails "a build root cannot be acquired by two processes" bash -c '
    source "$1/scripts/shared-utils.sh"
    acquire_build_root_lock "$2"
' _ "$repo_root" "$lock_root"
exec {held_lock_fd}>&-

selection_file="$temporary_root/selection.toml"
selection_output_file="$temporary_root/selection.out"
printf '%s\n' \
    '[build]' \
    'latest = true' \
    'enable_gpl_and_non_free = false' \
    '[packages]' \
    'ffmpeg = true' \
    'jemalloc = true' \
    'vulkan-headers = false' >"$selection_file"
load_package_selection_config "$selection_file" >"$selection_output_file"
selection_output="$(<"$selection_output_file")"
assert_contains "$selection_output" \
    "Loaded package selection config: '$selection_file'" \
    "loaded config paths are quoted"
assert_contains "$selection_output" \
    "run 'build-ffmpeg.sh --cleanup' first" \
    "config guidance quotes the cleanup command"
assert_not_contains "$selection_output" "run --cleanup" \
    "config guidance does not present an option as a command"
assert_equal "true" "$LATEST" "config loads build.latest"
# Held in a variable because shfmt 3.8.0 parses a hyphenated literal subscript
# as arithmetic and rewrites it to [vulkan - headers - git].
legacy_package_key="vulkan-headers-git"
assert_equal "false" "${PACKAGE_SELECTION[$legacy_package_key]}" \
    "legacy config key maps canonically"
assert_command_fails "an explicit config disables omitted package keys" \
    package_enabled libopus

if ! bash -c '
    source "$1/scripts/shared-utils.sh"
    LATEST=false
    NONFREE_AND_GPL=false
    CONFIGURE_OPTIONS=()
    load_package_selection_config "$1/example.toml" >/dev/null
    ! package_enabled libjxl && ! package_enabled libshaderc
' _ "$repo_root"; then
    fail_test "the portable example disables packages unavailable on Ubuntu 22.04"
fi
pass "the portable example disables packages unavailable on Ubuntu 22.04"

fake_bin="$temporary_root/fake-bin"
mkdir -p "$fake_bin"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    '[[ "${1:-}" != "-n" ]]' >"$fake_bin/sudo"
chmod +x "$fake_bin/sudo"

changed_context_root="$temporary_root/changed-context-root"
mkdir -p "$changed_context_root/packages" "$changed_context_root/workspace"
write_build_root_marker "$changed_context_root"
printf 'stale build context\n' >"$changed_context_root/.ffmpeg-build-context"
if changed_context_output="$(
    env PATH="$fake_bin:$PATH" BUILD_ROOT="$changed_context_root" \
        bash "$repo_root/build-ffmpeg.sh" -b -n -l --config "$selection_file" 2>&1
)"; then
    fail_test "changed build context is rejected"
fi
pass "changed build context is rejected"
assert_contains "$changed_context_output" \
    "Run 'build-ffmpeg.sh --cleanup' before rebuilding." \
    "changed-context failure quotes the cleanup command"
assert_not_contains "$changed_context_output" "Run --cleanup" \
    "changed-context failure does not present an option as a command"

# shellcheck source=scripts/hardware-detection.sh
source "$repo_root/scripts/hardware-detection.sh"
detect_gpu_vendors() {
    is_nvidia_gpu_present="NVIDIA GPU detected"
    is_amd_gpu_present="AMD GPU detected"
    is_intel_gpu_present="Intel GPU not detected"
    has_vulkan_gpu=1
}
hardware_summary_output="$(initialize_hardware_detection)"
assert_contains "$hardware_summary_output" \
    $' --------------------\n\nNVIDIA: NVIDIA GPU detected' \
    "hardware banner has one blank line before its summary"
assert_not_contains "$hardware_summary_output" \
    $' --------------------\n\n\nNVIDIA: NVIDIA GPU detected' \
    "hardware banner does not add a second blank line"

apt_fixture_bin="$temporary_root/apt-fixture-bin"
apt_fixture_log="$temporary_root/apt-fixture.log"
mkdir -p "$apt_fixture_bin"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'printf "%s\n" "$*" >>"$APT_FIXTURE_LOG"' >"$apt_fixture_bin/apt"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'exec "$@"' >"$apt_fixture_bin/sudo"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'exit 1' >"$apt_fixture_bin/dpkg-query"
chmod +x "$apt_fixture_bin/apt" "$apt_fixture_bin/sudo" \
    "$apt_fixture_bin/dpkg-query"
bash -c '
    PATH="$2:$PATH"
    export PATH APT_FIXTURE_LOG="$3"
    source "$1/scripts/system-setup.sh"
    log_file="$4"
    OS=Ubuntu
    VER=24.04
    APT_INDEX_UPDATED=false
    install_apt_packages shellcheck
' _ "$repo_root" "$apt_fixture_bin" "$apt_fixture_log" "$log_file" >/dev/null
apt_fixture_output="$(<"$apt_fixture_log")"
assert_contains "$apt_fixture_output" \
    "-o APT::Cmd::Disable-Script-Warning=1 update" \
    "host setup refreshes package metadata through apt"
assert_contains "$apt_fixture_output" \
    "-o APT::Cmd::Disable-Script-Warning=1 show shellcheck" \
    "host setup checks package availability through apt"
assert_contains "$apt_fixture_output" \
    "-o APT::Cmd::Disable-Script-Warning=1 install --assume-yes --no-install-recommends shellcheck" \
    "host setup installs packages noninteractively through apt"

expected_system_pkg_config_path="$(
    env -u PKG_CONFIG_PATH -u PKG_CONFIG_LIBDIR -u PKG_CONFIG_SYSROOT_DIR \
        /usr/bin/pkgconf --variable=pc_path pkgconf
)"
expected_workspace_pkg_config_path="$workspace/lib/pkgconfig:$workspace/lib64/pkgconfig"
expected_workspace_pkg_config_path+=":$workspace/lib/x86_64-linux-gnu/pkgconfig:$workspace/share/pkgconfig"
configured_pkg_config_paths="$(
    env PKG_CONFIG_PATH=/untrusted/high-priority \
        PKG_CONFIG_LIBDIR=/untrusted/low-priority \
        PKG_CONFIG_SYSROOT_DIR=/untrusted/sysroot \
        bash -c '
            source "$1/scripts/system-setup.sh"
            workspace="$2"
            configure_pkgconf_search_paths
            printf "%s|%s|%s|%s\n" \
                "$PKG_CONFIG_PATH" \
                "$SYSTEM_PKG_CONFIG_PATH" \
                "${PKG_CONFIG_LIBDIR+set}" \
                "${PKG_CONFIG_SYSROOT_DIR+set}"
        ' _ "$repo_root" "$workspace"
)"
assert_equal \
    "$expected_workspace_pkg_config_path|$expected_system_pkg_config_path||" \
    "$configured_pkg_config_paths" \
    "pkgconf keeps workspace overrides separate from sanitized host defaults"

mkdir -p "$workspace/bin"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    '[[ "$*" == "--variable=pc_path pkgconf" ]] || exit 64' \
    'printf "%s\n" "$PKGCONF_FIXTURE_DEFAULT_PATH"' \
    >"$workspace/bin/pkgconf"
chmod +x "$workspace/bin/pkgconf"
SYSTEM_PKG_CONFIG_PATH="/system/one/pkgconfig:/system/two/pkgconfig"
export PKGCONF_FIXTURE_DEFAULT_PATH="$SYSTEM_PKG_CONFIG_PATH"
package_artifacts_ready pkgconf ||
    fail_test "pkgconf artifacts with the host default path are reusable"
pass "pkgconf artifacts with the host default path are reusable"
PKGCONF_FIXTURE_DEFAULT_PATH="$workspace/lib/pkgconfig:$SYSTEM_PKG_CONFIG_PATH"
export PKGCONF_FIXTURE_DEFAULT_PATH
assert_command_fails "pkgconf artifacts polluted with workspace defaults are rebuilt" \
    package_artifacts_ready pkgconf

# A .pc file comes from a downloaded tarball. Splitting pkgconf's output with an
# unquoted expansion would also glob it, replacing a '*' in Cflags or Libs with
# whatever sits in the current directory, and a file named '-Ibogus' looks
# exactly like an include flag.
glob_fixture_dir="$temporary_root/pkgconf-glob"
mkdir -p "$glob_fixture_dir/bin" "$glob_fixture_dir/work"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'case "${1:-}" in' \
    '    --cflags-only-I) printf -- "* -I/opt/real/include\n" ;;' \
    '    --libs-only-L) printf -- "* -L/opt/real/lib\n" ;;' \
    '    *) exit 1 ;;' \
    'esac' \
    >"$glob_fixture_dir/bin/pkgconf"
chmod +x "$glob_fixture_dir/bin/pkgconf"
touch -- "$glob_fixture_dir/work/-Ibogus" "$glob_fixture_dir/work/-Lbogus"
glob_resolution_output="$(
    cd -- "$glob_fixture_dir/work" &&
        PATH="$glob_fixture_dir/bin:$PATH" bash -c '
            source "$1/scripts/shared-utils.sh"
            include_dir="$(resolve_pkgconf_include_dir fixture)" || exit 3
            library_dir="$(resolve_pkgconf_library_dir fixture)" || exit 4
            printf "%s|%s\n" "$include_dir" "$library_dir"
        ' _ "$repo_root" 2>&1
)"
assert_equal "/opt/real/include|/opt/real/lib" "$glob_resolution_output" \
    "pkgconf flag splitting never expands globs against the current directory"

os_detect_dir="$temporary_root/os-detect"
mkdir -p "$os_detect_dir"
printf '6.8.0-52-generic\n' >"$os_detect_dir/kernel-osrelease"

run_os_detection() {
    bash -c '
        source "$1/scripts/system-setup.sh"
        OS_RELEASE_FILE="$2/os-release"
        KERNEL_RELEASE_FILE="$2/kernel-osrelease"
        detect_operating_system
        printf "%s|%s|%s|%s\n" "$OS" "$VER" "$OS_CODENAME" "$VARIABLE_OS"
    ' _ "$repo_root" "$os_detect_dir"
}

expect_os_detection() {
    local expected="$1" description="$2" detection_output

    detection_output="$(run_os_detection 2>&1)" || {
        printf 'detection failed: %q\n' "$detection_output" >&2
        fail_test "$description"
    }
    assert_equal "$expected" "$detection_output" "$description"
}

expect_os_detection_failure() {
    local needle="$1" description="$2" detection_output

    if detection_output="$(run_os_detection 2>&1)"; then
        printf 'unexpected success: %q\n' "$detection_output" >&2
        fail_test "$description"
    fi
    assert_contains "$detection_output" "$needle" "$description"
}

printf '%s\n' 'ID=debian' 'VERSION_ID="12"' 'VERSION_CODENAME=bookworm' \
    >"$os_detect_dir/os-release"
expect_os_detection "Debian|12|bookworm|debian" "detection accepts Debian 12"

printf '%s\n' 'ID=debian' 'VERSION_CODENAME=trixie' >"$os_detect_dir/os-release"
expect_os_detection "Debian|13|trixie|debian" \
    "detection accepts Debian 13 without VERSION_ID"

printf '%s\n' 'PRETTY_NAME="Debian GNU/Linux forky/sid"' 'ID=debian' \
    'VERSION_CODENAME=forky' >"$os_detect_dir/os-release"
expect_os_detection_failure "testing/unstable" "detection rejects Debian testing"

printf '%s\n' 'ID=ubuntu' 'ID_LIKE=debian' 'VERSION_ID="22.04"' \
    'VERSION_CODENAME=jammy' 'UBUNTU_CODENAME=jammy' >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|22.04|jammy|ubuntu" "detection accepts Ubuntu 22.04"

printf '%s\n' 'ID=ubuntu' 'ID_LIKE=debian' 'VERSION_ID="24.04"' \
    'VERSION_CODENAME=noble' 'UBUNTU_CODENAME=noble' >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|24.04|noble|ubuntu" "detection accepts Ubuntu 24.04"

printf '%s\n' 'ID=ubuntu' 'ID_LIKE=debian' 'VERSION_ID="26.04"' \
    'VERSION_CODENAME=resolute' 'UBUNTU_CODENAME=resolute' \
    >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|26.04|resolute|ubuntu" \
    "detection accepts Ubuntu 26.04"

printf '%s\n' 'ID=ubuntu' 'VERSION_ID="25.10"' 'VERSION_CODENAME=questing' \
    >"$os_detect_dir/os-release"
expect_os_detection_failure "Unsupported Ubuntu release '25.10'" \
    "detection rejects EOL interim Ubuntu releases"

printf '%s\n' 'ID=ubuntu' 'VERSION_ID="24.04"' 'VERSION_CODENAME=jammy' \
    >"$os_detect_dir/os-release"
expect_os_detection_failure "Inconsistent Ubuntu metadata" \
    "detection rejects mismatched Ubuntu version metadata"

printf '%s\n' 'ID=linuxmint' 'ID_LIKE="ubuntu debian"' 'VERSION_ID="22.3"' \
    'VERSION_CODENAME=zena' 'UBUNTU_CODENAME=noble' >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|24.04|noble|linuxmint" \
    "detection maps Mint through its Ubuntu base codename"

printf '%s\n' 'ID=zorin' 'ID_LIKE="ubuntu debian"' 'VERSION_ID="17"' \
    'UBUNTU_CODENAME=jammy' >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|22.04|jammy|zorin" \
    "detection maps ID_LIKE=ubuntu derivatives generically"

printf '%s\n' 'ID=arch' >"$os_detect_dir/os-release"
expect_os_detection_failure "Unsupported operating system 'arch'" \
    "detection rejects unsupported distros"

printf '%s\n' 'ID=ubuntu' 'VERSION_ID="24.04"' 'VERSION_CODENAME=noble' \
    'UBUNTU_CODENAME=noble' >"$os_detect_dir/os-release"
printf '5.15.167.4-microsoft-standard-WSL2\n' >"$os_detect_dir/kernel-osrelease"
expect_os_detection "Ubuntu|24.04|noble|WSL2" \
    "detection accepts WSL2 with an Ubuntu userspace"

printf '%s\n' 'ID=debian' 'VERSION_ID="13"' 'VERSION_CODENAME=trixie' \
    >"$os_detect_dir/os-release"
expect_os_detection "Debian|13|trixie|WSL2" \
    "detection accepts WSL2 with a Debian userspace"

printf '4.4.0-19041-Microsoft\n' >"$os_detect_dir/kernel-osrelease"
expect_os_detection_failure "wsl.exe --set-version" \
    "detection rejects WSL1 with upgrade guidance"

# os-release is read as data. Sourcing it would run its contents as code in a
# shell that goes on to execute sudo-authorized steps.
printf '6.8.0-52-generic\n' >"$os_detect_dir/kernel-osrelease"
printf '%s\n' \
    'ID=ubuntu' \
    'VERSION_ID="24.04"' \
    'VERSION_CODENAME=noble' \
    'UBUNTU_CODENAME=noble' \
    "touch '$os_detect_dir/executed'" \
    'HOME=/nowhere' \
    >"$os_detect_dir/os-release"
expect_os_detection "Ubuntu|24.04|noble|ubuntu" \
    "detection ignores non-assignment lines in os-release"
assert_not_exists "$os_detect_dir/executed" \
    "os-release contents are never executed"
unrelated_key_output="$(
    bash -c '
        source "$1/scripts/system-setup.sh"
        OS_RELEASE_FILE="$2/os-release"
        KERNEL_RELEASE_FILE="$2/kernel-osrelease"
        detect_operating_system
        printf "%s\n" "$HOME"
    ' _ "$repo_root" "$os_detect_dir"
)"
assert_not_contains "$unrelated_key_output" "/nowhere" \
    "os-release assignments never leak into the calling shell"

release_gap_output="$(
    bash -c '
        source "$1/scripts/system-setup.sh"
        OS=Ubuntu OS_CODENAME=jammy release_unavailable_packages
    ' _ "$repo_root"
)"
assert_equal $'libjxl-dev\nlibshaderc-dev\nlibzix-dev' "$release_gap_output" \
    "jammy reports its known-absent packages"

release_gap_output="$(
    bash -c '
        source "$1/scripts/system-setup.sh"
        OS=Debian OS_CODENAME=bookworm release_unavailable_packages
    ' _ "$repo_root"
)"
assert_equal "libzix-dev" "$release_gap_output" \
    "bookworm reports its known-absent package"

release_gap_output="$(
    bash -c '
        source "$1/scripts/system-setup.sh"
        OS=Ubuntu OS_CODENAME=noble release_unavailable_packages
    ' _ "$repo_root"
)"
assert_equal "" "$release_gap_output" "noble has no known-absent packages"

unavailable_fixture_bin="$temporary_root/unavailable-fixture-bin"
mkdir -p "$unavailable_fixture_bin"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'printf "%s\n" "$*" >>"$APT_FIXTURE_LOG"' \
    '[[ "$*" != *" show "* ]]' >"$unavailable_fixture_bin/apt"
chmod +x "$unavailable_fixture_bin/apt"
cp -- "$apt_fixture_bin/sudo" "$apt_fixture_bin/dpkg-query" \
    "$unavailable_fixture_bin/"

absent_fixture_log="$temporary_root/absent-fixture.log"
: >"$absent_fixture_log"
if absent_output="$(
    env PATH="$unavailable_fixture_bin:$PATH" APT_FIXTURE_LOG="$absent_fixture_log" \
        bash -c '
            source "$1/scripts/system-setup.sh"
            log_file=""
            OS=Ubuntu VER=22.04 OS_CODENAME=jammy
            declare -A _APT_PACKAGE_REQUIRED=([libzix-dev]=1)
            install_apt_packages libzix-dev
        ' _ "$repo_root" 2>&1
)"; then
    fail_test "required release-absent package fails fast"
fi
pass "required release-absent package fails fast"
assert_contains "$absent_output" "Enable the 'zix' source build" \
    "release-absent failure names the source-build alternative"
assert_not_contains "$(<"$absent_fixture_log")" "update" \
    "release-absent failure precedes the APT metadata refresh"

if release_absent_ppa_output="$(
    env PATH="$apt_fixture_bin:$PATH" APT_FIXTURE_LOG="$absent_fixture_log" \
        bash -c '
            source "$1/scripts/system-setup.sh"
            log_file=""
            OS=Ubuntu VER=22.04 OS_CODENAME=jammy
            declare -A _APT_PACKAGE_REQUIRED=([libzix-dev]=1)
            install_apt_packages libzix-dev
        ' _ "$repo_root" 2>&1
)"; then
    pass "release-absent package visible to APT installs normally"
else
    printf 'unexpected failure: %q\n' "$release_absent_ppa_output" >&2
    fail_test "release-absent package visible to APT installs normally"
fi
assert_contains "$release_absent_ppa_output" \
    "install --assume-yes --no-install-recommends libzix-dev" \
    "APT visibility overrides the archive-verified absence list"

universe_fixture_log="$temporary_root/universe-fixture.log"
: >"$universe_fixture_log"
universe_output="$(
    env PATH="$unavailable_fixture_bin:$PATH" APT_FIXTURE_LOG="$universe_fixture_log" \
        bash -c '
            source "$1/scripts/system-setup.sh"
            log_file=""
            OS=Ubuntu VER=24.04 OS_CODENAME=noble
            APT_INDEX_UPDATED=false
            install_apt_packages not-a-real-package 2>&1
        ' _ "$repo_root"
)"
assert_contains "$universe_output" \
    "Ensure APT's 'universe' component is enabled" \
    "Ubuntu unavailability guidance mentions the universe component"

legacy_context_root="$temporary_root/legacy-context-root"
mkdir -p "$legacy_context_root/packages" "$legacy_context_root/workspace"
write_build_root_marker "$legacy_context_root"
printf '1.2.3\n' >"$legacy_context_root/packages/jemalloc.done"
if legacy_context_output="$(
    env PATH="$fake_bin:$PATH" BUILD_ROOT="$legacy_context_root" \
        bash "$repo_root/build-ffmpeg.sh" --build --config "$selection_file" 2>&1
)"; then
    fail_test "legacy build context is rejected"
fi
pass "legacy build context is rejected"
assert_contains "$legacy_context_output" \
    "Run 'build-ffmpeg.sh --cleanup' before rebuilding." \
    "legacy-context failure quotes the cleanup command"
assert_not_contains "$legacy_context_output" "Run --cleanup" \
    "legacy-context failure does not present an option as a command"

duplicate_selection_file="$temporary_root/duplicate-selection.toml"
printf '%s\n' \
    '[packages]' \
    'vulkan-headers = true' \
    'vulkan-headers-git = false' >"$duplicate_selection_file"
if bash -c '
    source "$1/scripts/shared-utils.sh"
    LATEST=false
    NONFREE_AND_GPL=false
    CONFIGURE_OPTIONS=()
    load_package_selection_config "$2"
' _ "$repo_root" "$duplicate_selection_file" >/dev/null 2>&1; then
    fail_test "canonical duplicate config keys are rejected"
fi
pass "canonical duplicate config keys are rejected"

unknown_selection_file="$temporary_root/unknown-selection.toml"
printf '%s\n' \
    '[packages]' \
    'ffmepg = true' >"$unknown_selection_file"
assert_command_fails "unknown config package names are rejected" bash -c '
    source "$1/scripts/shared-utils.sh"
    LATEST=false
    NONFREE_AND_GPL=false
    CONFIGURE_OPTIONS=()
    load_package_selection_config "$2"
' _ "$repo_root" "$unknown_selection_file"

unknown_table_file="$temporary_root/unknown-table.toml"
printf '%s\n' '[package]' >"$unknown_table_file"
assert_command_fails "unknown config tables are rejected even when empty" bash -c '
    source "$1/scripts/shared-utils.sh"
    LATEST=false
    NONFREE_AND_GPL=false
    CONFIGURE_OPTIONS=()
    load_package_selection_config "$2"
' _ "$repo_root" "$unknown_table_file"

# CUDA_INSTALL and CUDA_ARCH_MODE are pure checks on the request, so they have
# to be rejected before initialize_system_setup() installs dozens of APT
# packages. Validating them inside install_cuda() is too late.
for invalid_setting in "CUDA_INSTALL=maybe" "CUDA_ARCH_MODE=bogus" "CUDA_ARCH_MODE=custom"; do
    assert_command_fails "'$invalid_setting' is rejected before any host mutation" bash -c '
        source "$1/scripts/shared-utils.sh"
        export "${2?}"
        validate_build_settings
    ' _ "$repo_root" "$invalid_setting"
done
if ! bash -c '
    source "$1/scripts/shared-utils.sh"
    CUDA_ARCH_MODE=custom CUDA_ARCHITECTURES="86 89" validate_build_settings
' _ "$repo_root" >/dev/null 2>&1; then
    fail_test "a valid custom CUDA architecture list is accepted"
fi
pass "a valid custom CUDA architecture list is accepted"

temp_registry_root="$temporary_root/temp-registry"
mkdir -p "$temp_registry_root/packages" "$temp_registry_root/outside"
bash -c '
    source "$1/scripts/shared-utils.sh"
    packages="$2/packages"
    workspace="$2/workspace"
    trap "remove_registered_temporary_paths" EXIT
    stranded="$(mktemp -d --tmpdir="$packages" ".clone-demo.XXXXXX")"
    register_temporary_path "$stranded"
    mkdir -p "$stranded/partial"
    mkdir -p "$packages/real-source-tree"
    register_temporary_path "$3"
    exit 1
' _ "$repo_root" "$temp_registry_root" "$temp_registry_root/outside" >/dev/null 2>&1 || true
assert_equal "0" \
    "$(find "$temp_registry_root/packages" -mindepth 1 -maxdepth 1 -name '.clone-demo.*' | wc -l)" \
    "registered temporary trees are removed when the shell exits"
[[ -d "$temp_registry_root/packages/real-source-tree" ]] ||
    fail_test "unregistered build output survives the cleanup trap"
pass "unregistered build output survives the cleanup trap"
[[ -d "$temp_registry_root/outside" ]] ||
    fail_test "the cleanup trap refuses paths outside the build root"
pass "the cleanup trap refuses paths outside the build root"

removal_root="$temporary_root/removal-root"
mkdir -p "$removal_root/child"
safe_remove_tree "$removal_root/child" "$removal_root"
assert_not_exists "$removal_root/child" "safe_remove_tree removes a bounded child"
mkdir -p "$removal_root/child" "$temporary_root/removal-sibling"
assert_command_fails "safe_remove_tree refuses its allowed root" bash -c '
    source "$1/scripts/shared-utils.sh"
    safe_remove_tree "$2" "$2"
' _ "$repo_root" "$removal_root"
assert_command_fails "safe_remove_tree refuses a sibling path" bash -c '
    source "$1/scripts/shared-utils.sh"
    safe_remove_tree "$2" "$3"
' _ "$repo_root" "$temporary_root/removal-sibling" "$removal_root"
[[ -d "$removal_root/child" && -d "$temporary_root/removal-sibling" ]] ||
    fail_test "refused removals preserve both trees"
pass "refused removals preserve both trees"

# The containment check ran against the resolved path while rm removed the raw
# one, so a symlinked target passed validation and then deleted only the link,
# leaving the real tree in place right before a publishing mv.
mkdir -p "$removal_root/real"
printf 'payload\n' >"$removal_root/real/payload.txt"
ln -sfn "$removal_root/real" "$removal_root/link"
assert_command_fails "safe_remove_tree refuses a symlinked target" bash -c '
    source "$1/scripts/shared-utils.sh"
    safe_remove_tree "$2" "$3"
' _ "$repo_root" "$removal_root/link" "$removal_root"
[[ -f "$removal_root/real/payload.txt" ]] ||
    fail_test "refused symlink removal preserves the real tree"
pass "refused symlink removal preserves the real tree"

archive_source="$temporary_root/archive-source"
mkdir -p "$archive_source/project/sub"
printf 'payload\n' >"$archive_source/project/sub/file.txt"
archive="$packages/project.tar.gz"
tar -czf "$archive" -C "$archive_source" project
validate_tar_archive "$archive" || fail_test "valid single-root archive is accepted"
pass "valid single-root archive is accepted"
write_archive_checksum "$archive" || fail_test "archive checksum record is written"
pass "archive checksum record is written"
archive_checksum_matches "$archive" ||
    fail_test "archive checksum record validates unchanged content"
pass "archive checksum record validates unchanged content"
printf 'tamper\n' >>"$archive"
assert_command_fails "archive checksum detects changed content" \
    archive_checksum_matches "$archive"
tar -czf "$archive" -C "$archive_source" project
write_archive_checksum "$archive" || fail_test "archive checksum can be refreshed for test extraction"
extract_archive_transactionally "$archive" "$packages/project"
assert_file "$packages/project/sub/file.txt" "transactional extraction publishes payload"

curl_invocation="$temporary_root/curl-invocation"
downloaded_archive="$packages/user-agent-download.tar.gz"
if ! (
    curl() {
        local argument output_file=""

        while (($# > 0)); do
            argument="$1"
            printf '%s\n' "$argument" >>"$curl_invocation"
            shift
            if [[ "$argument" == "--output" ]]; then
                output_file="${1:-}"
            fi
        done

        [[ -n "$output_file" ]] || return 1
        cp -- "$archive" "$output_file"
    }

    download_archive_to_cache \
        "https://example.test/user-agent-download.tar.gz" \
        "user-agent-download.tar.gz" \
        "$downloaded_archive"
); then
    fail_test "archive downloads invoke curl successfully"
fi
pass "archive downloads invoke curl successfully"
assert_contains "$(<"$curl_invocation")" \
    $'--user-agent\nMozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0' \
    "archive downloads use the configured browser user agent"
assert_file "$downloaded_archive" "archive downloads publish the validated payload"

multi_root_source="$temporary_root/multi-root-source"
mkdir -p "$multi_root_source/root-a" "$multi_root_source/root-b"
printf 'a\n' >"$multi_root_source/root-a/file"
printf 'b\n' >"$multi_root_source/root-b/file"
multi_root_archive="$packages/multi-root.tar.gz"
tar -czf "$multi_root_archive" -C "$multi_root_source" root-a root-b
assert_command_fails "multi-root archives are rejected" \
    validate_tar_archive "$multi_root_archive"

relative_link_source="$temporary_root/relative-link-source"
mkdir -p "$relative_link_source/project"
ln -s ../../outside "$relative_link_source/project/escape"
relative_link_archive="$packages/relative-link.tar.gz"
tar -czf "$relative_link_archive" -C "$relative_link_source" project
assert_command_fails "out-of-tree relative archive symlinks are rejected" \
    extract_archive_transactionally "$relative_link_archive" "$packages/relative-link"
assert_not_exists "$packages/relative-link" "rejected relative symlink archive is not published"

absolute_link_source="$temporary_root/absolute-link-source"
mkdir -p "$absolute_link_source/project"
ln -s /etc/passwd "$absolute_link_source/project/escape"
absolute_link_archive="$packages/absolute-link.tar.gz"
tar -czf "$absolute_link_archive" -C "$absolute_link_source" project
assert_command_fails "absolute archive symlinks are rejected" \
    extract_archive_transactionally "$absolute_link_archive" "$packages/absolute-link"
assert_not_exists "$packages/absolute-link" "rejected absolute symlink archive is not published"

special_source="$temporary_root/special-source"
mkdir -p "$special_source/project"
mkfifo "$special_source/project/fifo"
special_archive="$packages/special.tar.gz"
tar -czf "$special_archive" -C "$special_source" project
assert_command_fails "special filesystem objects in archives are rejected" \
    extract_archive_transactionally "$special_archive" "$packages/special"
assert_not_exists "$packages/special" "rejected special-object archive is not published"

mkdir -p "$workspace/lib/pkgconfig"
printf '%s\n' \
    "prefix=$workspace" \
    'libdir=${prefix}/lib' \
    'includedir=${prefix}/include' \
    'Name: jemalloc' \
    'Description: test-only jemalloc artifact' \
    'Version: 1.2.3' \
    'Libs: -L${libdir} -ljemalloc' \
    'Cflags: -I${includedir}' >"$workspace/lib/pkgconfig/jemalloc.pc"
PKG_CONFIG_PATH="$workspace/lib/pkgconfig"
export PKG_CONFIG_PATH

printf '%s\n' \
    'Name: prefixless-workspace-module' \
    'Description: test-only prefixless workspace metadata' \
    'Version: 1.0.0' \
    "Libs: -L$workspace/lib -lprefixless" \
    "Cflags: -I$workspace/include" >"$workspace/lib/pkgconfig/prefixless-workspace-module.pc"
workspace_pkgconf_modules_ready prefixless-workspace-module ||
    fail_test "prefixless pkg-config metadata inside the workspace is accepted"
pass "prefixless pkg-config metadata inside the workspace is accepted"

external_pkgconfig="$temporary_root/external-pkgconfig"
mkdir -p "$external_pkgconfig"
printf '%s\n' \
    'Name: prefixless-external-module' \
    'Description: test-only prefixless external metadata' \
    'Version: 1.0.0' \
    'Libs: -lexternal' >"$external_pkgconfig/prefixless-external-module.pc"
assert_command_fails \
    "prefixless pkg-config metadata outside the workspace is rejected" \
    env PKG_CONFIG_PATH="$external_pkgconfig:$PKG_CONFIG_PATH" bash -c '
        source "$1/scripts/shared-utils.sh"
        workspace="$2"
        workspace_pkgconf_modules_ready prefixless-external-module
    ' _ "$repo_root" "$workspace"

build_done jemalloc 1.2.3
assert_equal "1.2.3" "$(read_marker_version "$packages/jemalloc.done")" "build markers are atomic and readable"
if build_output="$(build jemalloc 1.2.3)"; then
    fail_test "matching build marker skips rebuild"
fi
pass "matching build marker skips rebuild"
assert_contains "$build_output" "Building jemalloc (version 1.2.3)" \
    "build heading labels the package version clearly"
assert_contains "$build_output" "Already built: jemalloc 1.2.3" \
    "matching build marker reports the package status clearly"
assert_contains "$build_output" \
    "Rebuild: run 'rm -f -- $packages/jemalloc.done'." \
    "matching build marker quotes its actionable rebuild command"
assert_not_contains "$build_output" "lockfile" \
    "build markers are not mislabeled as lockfiles"

printf '1.2.2\n' >"$packages/jemalloc.done"
LATEST=false
if outdated_build_output="$(build jemalloc 1.2.3)"; then
    fail_test "outdated build markers preserve pinned versions by default"
fi
pass "outdated build markers preserve pinned versions by default"
assert_contains "$outdated_build_output" \
    "add '--latest' to your 'build-ffmpeg.sh' command" \
    "outdated-package guidance quotes the option and script name"
assert_contains "$outdated_build_output" \
    "or run 'rm -f -- $packages/jemalloc.done'." \
    "outdated-package guidance quotes the alternate command"

# shellcheck source=scripts/ffmpeg-build.sh
source "$repo_root/scripts/ffmpeg-build.sh"
ffmpeg_test_prefix="$temporary_root/ffmpeg-prefix"
mkdir -p "$ffmpeg_test_prefix/bin"
for ffmpeg_test_tool in ffmpeg ffprobe ffplay; do
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'set -euo pipefail' \
        'tool_name="${0##*/}"' \
        'case "${2:-}" in' \
        '    -version)' \
        '        printf "%s version 8.1.2 Copyright test fixture\n" "$tool_name"' \
        '        printf "configuration: --fake-%s\n" "$tool_name"' \
        '        ;;' \
        '    -encoders)' \
        '        printf "Encoders:\n V..... test_encoder\n"' \
        '        ;;' \
        '    -decoders)' \
        '        printf "Decoders:\n V..... test_decoder\n"' \
        '        ;;' \
        '    *) exit 64 ;;' \
        'esac' >"$ffmpeg_test_prefix/bin/$ffmpeg_test_tool"
    chmod +x "$ffmpeg_test_prefix/bin/$ffmpeg_test_tool"
done

: >"$log_file"
ffmpeg_validation_output="$(
    validate_ffmpeg_installation 8.1.2 true "$ffmpeg_test_prefix"
)"
assert_contains "$ffmpeg_validation_output" \
    "FFmpeg installation verified ($ffmpeg_test_prefix/bin):" \
    "FFmpeg validation has a readable result heading"
for ffmpeg_test_tool in ffmpeg ffprobe ffplay; do
    assert_contains "$ffmpeg_validation_output" \
        "$ffmpeg_test_tool version 8.1.2 Copyright test fixture" \
        "$ffmpeg_test_tool validation displays its version result"
    assert_not_contains "$ffmpeg_validation_output" \
        "$ $ffmpeg_test_prefix/bin/$ffmpeg_test_tool -hide_banner -version" \
        "$ffmpeg_test_tool validation does not display a raw command trace"
    assert_contains "$(<"$log_file")" "configuration: --fake-$ffmpeg_test_tool" \
        "$ffmpeg_test_tool validation retains full output in the build log"
    # Pairs with the assertion above: the trace has to exist somewhere, or
    # "absent from stdout" would hold even if validation never ran the command.
    assert_contains "$(<"$log_file")" \
        "$ $ffmpeg_test_prefix/bin/$ffmpeg_test_tool -hide_banner -version" \
        "$ffmpeg_test_tool validation records the command trace in the build log"
done

sed -i 's/version 8\.1\.2/version 8.1.1/' "$ffmpeg_test_prefix/bin/ffprobe"
assert_command_fails "FFmpeg validation rejects a mismatched companion-tool version" bash -c '
    source "$1/scripts/shared-utils.sh"
    source "$1/scripts/ffmpeg-build.sh"
    validate_ffmpeg_installation 8.1.2 true "$2" false
' _ "$repo_root" "$ffmpeg_test_prefix"

printf '1..%d\n' "$pass_count"
