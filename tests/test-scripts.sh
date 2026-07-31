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

assert_command_fails() {
    local description="${1:-command fails}"
    shift

    if "$@" >/dev/null 2>&1; then
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

unmarked_root="$temporary_root/unmarked-root"
mkdir -p "$unmarked_root"
printf 'not build data\n' >"$unmarked_root/user-file"
assert_command_fails "cleanup refuses an unmarked build root" \
    env BUILD_ROOT="$unmarked_root" bash "$repo_root/build-ffmpeg.sh" --cleanup
assert_file "$unmarked_root/user-file" "refused cleanup preserves unrelated data"

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
assert_equal "false" "${PACKAGE_SELECTION[vulkan-headers-git]}" "legacy config key maps canonically"
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
done

sed -i 's/version 8\.1\.2/version 8.1.1/' "$ffmpeg_test_prefix/bin/ffprobe"
assert_command_fails "FFmpeg validation rejects a mismatched companion-tool version" bash -c '
    source "$1/scripts/shared-utils.sh"
    source "$1/scripts/ffmpeg-build.sh"
    validate_ffmpeg_installation 8.1.2 true "$2" false
' _ "$repo_root" "$ffmpeg_test_prefix"

printf '1..%d\n' "$pass_count"
