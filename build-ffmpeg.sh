#!/usr/bin/env bash
# shellcheck source=/dev/null

set -o pipefail

readonly SCRIPT_VERSION="6.0.0"
# Cap on the differing build-context fields listed in the mismatch message. A
# changed config can move a hundred of them, and a wall of those buries the one
# line the reader needs.
readonly BUILD_CONTEXT_CHANGE_LIMIT=10
# v1 snapshotted CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS before source_compiler_flags
# computed them, so it recorded the inherited environment (normally empty) and
# not what the build used. v2 records the real flags. A v1 record therefore
# carries no usable flag data, which is why the migration below ignores those
# four fields exactly once instead of reporting them as changed settings.
readonly BUILD_CONTEXT_FORMAT="ffmpeg-build-context:v2"
readonly BUILD_CONTEXT_LEGACY_FORMAT="ffmpeg-build-context:v1"
readonly -a BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS=(
    cflags cxxflags cppflags ldflags
)
readonly SCRIPT_NAME="${0##*/}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR
readonly REPO_ROOT="$SCRIPT_DIR"
readonly INVOCATION_DIR="$PWD"

# Shared state consumed by the sourced build stages.
COMPILER_FLAG="gcc"
CONFIGURE_OPTIONS=()
LATEST=false
NONFREE_AND_GPL=false
GOOGLE_SPEECH=false
DO_BUILD=false
DO_CLEANUP=false
PACKAGE_CONFIG_FILE=""
build_threads=""
cwd=""
packages=""
workspace=""
log_file=""
SYSTEM_PKG_CONFIG_PATH=""

# shellcheck source=scripts/shared-utils.sh
source "$SCRIPT_DIR/scripts/shared-utils.sh"

print_usage_row() {
    printf '  %-33s %s\n' "$1" "$2"
}

usage() {
    printf '\nFFmpeg Build Script %s\n' "$SCRIPT_VERSION"
    printf 'Usage: %s [options]\n\n' "$SCRIPT_NAME"
    printf 'Actions:\n'
    print_usage_row '-b, --build' 'Build and install FFmpeg'
    print_usage_row '-c, --cleanup' "Remove this project's build root"
    printf '\nOptions:\n'
    print_usage_row '-h, --help' 'Show this help without changing the filesystem'
    print_usage_row '-v, --version' 'Show the script version'
    print_usage_row '    --compiler <gcc|clang>' 'Select the C/C++ compiler (default: gcc)'
    print_usage_row '    --config <path>' 'Load build/package choices from TOML'
    print_usage_row '-j, --jobs <count>' 'Set parallel build jobs (default: available CPUs)'
    print_usage_row '-l, --latest' 'Refresh and rebuild outdated dependencies'
    print_usage_row '-n, --enable-gpl-and-non-free' 'Enable GPL/non-free components'
    print_usage_row '-g, --google-speech' 'Announce failures if google_speech is installed'
    printf '\nLong options also accept --option=value (for example: --jobs=8).\n'
    printf '\nEnvironment:\n'
    print_usage_row 'BUILD_ROOT=/path' 'Override the default ./build directory'
    print_usage_row 'CUDA_INSTALL=ask|always|never' 'Control CUDA toolkit installation (default: ask)'
    print_usage_row 'CUDA_ARCH_MODE=native|all|custom' 'Select CUDA code-generation targets'
    print_usage_row 'CUDA_ARCHITECTURES="86 89"' 'Targets for CUDA_ARCH_MODE=custom'
    print_usage_row 'FFMPEG_BUILD_DEBUG=ON' 'Stream commands while also logging them'
    printf '\nExample:\n'
    printf '  bash %s --build --compiler clang --jobs 8 --config ./custom.toml\n\n' \
        "$SCRIPT_NAME"
}

resolve_config_path() {
    local input_path="${1:-}"
    local candidate_path

    # Callers capture this in $(...), where fail()'s exit would end only the
    # subshell and hand back an empty path. Report and return instead; the
    # caller turns a non-zero status into a real abort.
    [[ -n "$input_path" ]] || {
        warn "Missing config path for '--config'."
        return 1
    }
    [[ ! "$input_path" =~ [[:cntrl:]] ]] || {
        warn "Config paths may not contain control characters."
        return 1
    }
    if [[ "$input_path" == /* ]]; then
        candidate_path="$input_path"
    else
        # Invocation directory only. Retrying a missing relative path under the
        # script's own directory would let a stale custom.toml sitting next to
        # build-ffmpeg.sh supply a different package selection, with nothing in
        # the output naming the file that won.
        candidate_path="$INVOCATION_DIR/$input_path"
    fi

    canonicalize_path "$candidate_path"
}

# Both walks below skip the value of every option that takes a separate
# argument, and stop at `--`, so an option's value is never mistaken for an
# option (`--compiler -h` means a compiler named '-h', not a request for help).
# The metadata walk runs before parse_arguments, so on that path it is the only
# thing standing between `-- -h` and a help screen.
metadata_or_config_walk_skips_value() {
    case "${1-}" in
        --compiler | --config | -j | --jobs) return 0 ;;
    esac
    return 1
}

show_requested_metadata_and_exit() {
    local -a arguments=("$@")
    local index

    for ((index = 0; index < ${#arguments[@]}; index++)); do
        case "${arguments[index]}" in
            --)
                break
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            -v | --version)
                printf '%s\n' "$SCRIPT_VERSION"
                exit 0
                ;;
            *)
                if metadata_or_config_walk_skips_value "${arguments[index]}"; then
                    ((index += 1))
                fi
                ;;
        esac
    done
}

load_requested_config() {
    local -a arguments=("$@")
    local index

    for ((index = 0; index < ${#arguments[@]}; index++)); do
        case "${arguments[index]}" in
            --)
                break
                ;;
            --config)
                ((index + 1 < ${#arguments[@]})) ||
                    fail "Missing value for '--config'."
                [[ -z "$PACKAGE_CONFIG_FILE" ]] ||
                    fail "'--config' may only be specified once."
                PACKAGE_CONFIG_FILE="$(resolve_config_path "${arguments[index + 1]}")" ||
                    fail "Invalid value for '--config'."
                ((index += 1))
                ;;
            --config=*)
                [[ -z "$PACKAGE_CONFIG_FILE" ]] ||
                    fail "'--config' may only be specified once."
                PACKAGE_CONFIG_FILE="$(resolve_config_path "${arguments[index]#*=}")" ||
                    fail "Invalid value for '--config'."
                ;;
            *)
                if metadata_or_config_walk_skips_value "${arguments[index]}"; then
                    ((index += 1))
                fi
                ;;
        esac
    done

    [[ -z "$PACKAGE_CONFIG_FILE" ]] || load_package_selection_config "$PACKAGE_CONFIG_FILE"
}

# Validated at the point of assignment. Once parsing ends, an empty value is
# indistinguishable from an omitted option, and `--jobs=` would quietly mean
# "auto-detect" rather than being rejected.
set_build_threads() {
    local requested="${1-}"

    [[ "$requested" =~ ^[1-9][0-9]*$ ]] ||
        fail "Invalid jobs value '$requested'; expected a positive integer."
    build_threads="$requested"
}

parse_arguments() {
    while (($# > 0)); do
        case "$1" in
            -b | --build)
                DO_BUILD=true
                shift
                ;;
            -c | --cleanup)
                DO_CLEANUP=true
                shift
                ;;
            -g | --google-speech)
                GOOGLE_SPEECH=true
                shift
                ;;
            -l | --latest)
                LATEST=true
                shift
                ;;
            -n | --enable-gpl-and-non-free)
                enable_gpl_and_non_free
                shift
                ;;
            --compiler)
                (($# >= 2)) || fail "Missing value for '--compiler'."
                COMPILER_FLAG="$2"
                shift 2
                ;;
            --compiler=*)
                COMPILER_FLAG="${1#*=}"
                shift
                ;;
            -j | --jobs)
                (($# >= 2)) || fail "Missing value for '$1'."
                set_build_threads "$2"
                shift 2
                ;;
            --jobs=*)
                set_build_threads "${1#*=}"
                shift
                ;;
            --config)
                (($# >= 2)) || fail "Missing value for '--config'."
                shift 2
                ;;
            --config=*)
                shift
                ;;
            -h | --help | -v | --version)
                # Handled before config loading so these options remain side-effect free.
                shift
                ;;
            --)
                shift
                (($# == 0)) || fail "Unexpected positional arguments: '$*'."
                ;;
            *)
                fail "Unknown option '$1'."
                ;;
        esac
    done

    [[ "$COMPILER_FLAG" == "gcc" || "$COMPILER_FLAG" == "clang" ]] ||
        fail "Invalid compiler '$COMPILER_FLAG'; expected 'gcc' or 'clang'."
    if is_true "$DO_BUILD" && is_true "$DO_CLEANUP"; then
        fail "'--build' and '--cleanup' are mutually exclusive."
    fi
}

resolve_build_root() {
    local requested_root="${BUILD_ROOT:-$REPO_ROOT/build}"

    if [[ "$requested_root" != /* ]]; then
        requested_root="$INVOCATION_DIR/$requested_root"
    fi
    cwd="$(canonicalize_path "$requested_root")" ||
        fail "Unable to resolve build root '$requested_root'."
    packages="$cwd/packages"
    workspace="$cwd/workspace"
    log_file="$cwd/build.log"
}

validate_build_root() {
    local first_entry

    assert_safe_build_root "$cwd" "$REPO_ROOT"

    [[ ! -e "$cwd" || -d "$cwd" ]] ||
        fail "'BUILD_ROOT' exists but is not a directory: '$cwd'."
    if [[ -d "$cwd" ]]; then
        [[ -r "$cwd" && -x "$cwd" ]] ||
            fail "'BUILD_ROOT' cannot be inspected safely by the current user: '$cwd'."
        if ! first_entry="$(find "$cwd" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)"; then
            fail "Unable to inspect existing 'BUILD_ROOT' '$cwd'."
        fi
        if [[ -n "$first_entry" ]]; then
            if build_root_marker_matches "$cwd/.ffmpeg-build-root" "$cwd"; then
                :
            elif legacy_build_root_marker "$cwd/.ffmpeg-build-root"; then
                warn "'BUILD_ROOT' '$cwd' uses a legacy empty marker; this build will upgrade it to a path-bound marker."
            elif build_root_is_adoptable "$cwd"; then
                warn "'$cwd' holds only this project's empty scaffolding from an interrupted run; adopting it."
            else
                fail "'BUILD_ROOT' '$cwd' already contains data and lacks a valid path-bound FFmpeg build-root marker."
            fi
        fi
    fi
}

write_build_context_payload() {
    local package_name

    printf '%s\n' \
        "$BUILD_CONTEXT_FORMAT" \
        "script_version=$SCRIPT_VERSION" \
        "compiler=$COMPILER_FLAG" \
        "gpl_and_non_free=$NONFREE_AND_GPL" \
        "rust_toolchain=$RUST_TOOLCHAIN_VERSION" \
        "cargo_c=$CARGO_C_VERSION"
    printf 'cflags=%q\n' "${CFLAGS:-}"
    printf 'cxxflags=%q\n' "${CXXFLAGS:-}"
    printf 'cppflags=%q\n' "${CPPFLAGS:-}"
    printf 'ldflags=%q\n' "${LDFLAGS:-}"
    printf 'cuda_arch_mode=%q\n' "${CUDA_ARCH_MODE:-native}"
    printf 'cuda_architectures=%q\n' "${CUDA_ARCHITECTURES:-}"
    printf 'source_date_epoch=%q\n' "${SOURCE_DATE_EPOCH:-}"
    for package_name in "${SUPPORTED_PACKAGE_NAMES[@]}"; do
        if package_enabled "$package_name"; then
            printf 'package.%s=true\n' "$package_name"
        else
            printf 'package.%s=false\n' "$package_name"
        fi
    done
}

# Payload values are %q-encoded so they round-trip exactly. That encoding turns
# a flag list into backslash noise for a reader, so undo it for the message.
# Each escape is consumed as a pair rather than by deleting every backslash,
# which would render a literal one as nothing at all.
readable_context_value() {
    local value="$1"
    local rendered=""

    if [[ -z "$value" || "$value" == "''" ]]; then
        printf "''"
        return 0
    fi
    # %q switches to $'...' when the value holds a control character, and those
    # escapes are not single-character pairs. Show that form verbatim; mangling
    # it would be worse than leaving it encoded.
    if [[ "$value" == \$\'* ]]; then
        printf '%s' "$value"
        return 0
    fi
    while [[ "$value" == *\\* ]]; do
        rendered+="${value%%\\*}"
        value="${value#*\\}"
        rendered+="${value:0:1}"
        value="${value:1}"
    done
    printf "'%s'" "$rendered$value"
}

# The recorded payload is well over a hundred fields, so "something changed"
# leaves the reader nothing to act on and no way to tell a stale workspace from
# a newly registered package. Name the fields that actually differ.
summarize_build_context_changes() {
    local previous_file="$1" current_file="$2"
    local -A previous_fields=() current_fields=()
    local -a changes=()
    local line key value omitted

    # The payload opens with a bare format tag rather than a key=value pair.
    # Filing it under a synthetic key keeps a format change visible; skipping it
    # would leave a version bump as a byte difference with nothing to report.
    while IFS= read -r line; do
        [[ "$line" == *=* ]] || line="format=$line"
        previous_fields["${line%%=*}"]="${line#*=}"
    done <"$previous_file"

    while IFS= read -r line; do
        [[ "$line" == *=* ]] || line="format=$line"
        key="${line%%=*}"
        value="${line#*=}"
        current_fields["$key"]=1
        if [[ -z "${previous_fields[$key]+x}" ]]; then
            changes+=("$key is new in this version of the script (now $(readable_context_value "$value"))")
        elif [[ "${previous_fields[$key]}" != "$value" ]]; then
            changes+=("$key was $(readable_context_value "${previous_fields[$key]}"), is now $(readable_context_value "$value")")
        fi
    done <"$current_file"

    for key in "${!previous_fields[@]}"; do
        if [[ -z "${current_fields[$key]+x}" ]]; then
            changes+=("$key is no longer recorded (was $(readable_context_value "${previous_fields[$key]}"))")
        fi
    done

    ((${#changes[@]} > 0)) || return 1

    # Associative-array iteration order is unspecified, so sort for a stable
    # message. LC_ALL=C because a locale-dependent collation would reorder the
    # list between hosts and change which fields the cap keeps.
    mapfile -t changes < <(printf '%s\n' "${changes[@]}" | LC_ALL=C sort)
    omitted=$((${#changes[@]} - BUILD_CONTEXT_CHANGE_LIMIT))
    # Truncating a single field costs a line to say so and saves nothing.
    if ((omitted > 1)); then
        changes=("${changes[@]:0:BUILD_CONTEXT_CHANGE_LIMIT}" "and $omitted more")
    fi
    printf ' - %s\n' "${changes[@]}"
}

# A workspace written by an older script is not the same thing as a workspace
# built with different settings. Two differences are bookkeeping: the four flag
# fields v1 never meaningfully recorded, and package keys that did not exist in
# the registry when the record was written. When those are the only differences,
# nothing already built is invalid, so accept the workspace instead of charging
# the user a multi-hour rebuild for a script update. Prints the package keys that
# were added; returns non-zero when any other field moved, which still aborts.
build_context_is_migratable() {
    local previous_file="$1" current_file="$2"
    local -A previous_fields=()
    local -a added_package_keys=()
    local line key value field ignored

    while IFS= read -r line; do
        [[ "$line" == *=* ]] || line="format=$line"
        previous_fields["${line%%=*}"]="${line#*=}"
    done <"$previous_file"
    [[ "${previous_fields[format]:-}" == "$BUILD_CONTEXT_LEGACY_FORMAT" ]] || return 1

    while IFS= read -r line; do
        [[ "$line" == *=* ]] || line="format=$line"
        key="${line%%=*}"
        value="${line#*=}"
        [[ "$key" != "format" ]] || continue

        ignored=0
        for field in "${BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS[@]}"; do
            [[ "$key" != "$field" ]] || ignored=1
        done
        ((!ignored)) || continue

        if [[ -z "${previous_fields[$key]+x}" ]]; then
            # Only the registry growing is additive. A brand new non-package
            # field means the payload changed shape in some way this cannot
            # reason about, so it is not migratable.
            [[ "$key" == package.* ]] || return 1
            added_package_keys+=("${key#package.}")
            continue
        fi
        [[ "${previous_fields[$key]}" == "$value" ]] || return 1
        unset "previous_fields[$key]"
    done <"$current_file"

    # Anything left over was recorded before and is absent now. A shrinking
    # registry does not invalidate artifacts, but it is rare enough that a clean
    # rebuild is the honest answer rather than a guess.
    for key in "${!previous_fields[@]}"; do
        [[ "$key" == "format" ]] && continue
        ignored=0
        for field in "${BUILD_CONTEXT_LEGACY_UNRECORDED_FIELDS[@]}"; do
            [[ "$key" != "$field" ]] || ignored=1
        done
        ((ignored)) || return 1
    done

    ((${#added_package_keys[@]} == 0)) || printf '%s\n' "${added_package_keys[@]}"
}

# Publishes the upgraded record and, when the registry grew, drops the FFmpeg
# marker. A newly enabled package contributes a --enable-* option, and FFmpeg
# only picks that up by configuring again; without this the workspace would
# build the new dependency and link an FFmpeg that ignores it.
adopt_migrated_build_context() {
    local context_file="$1" temporary_context="$2" added_packages="$3"
    local package_name

    if ! mv -f -- "$temporary_context" "$context_file"; then
        rm -f -- "$temporary_context"
        fail "Unable to publish the upgraded build-context file '$context_file'."
    fi
    log "Adopted this workspace: it was recorded by an older version of this script, and nothing already built is affected."
    log_debug "Upgraded '$context_file' to $BUILD_CONTEXT_FORMAT."

    [[ -n "$added_packages" ]] || return 0
    log "Newly available since that workspace was created: ${added_packages//$'\n'/, }"
    while IFS= read -r package_name; do
        [[ -n "$package_name" ]] || continue
        package_enabled "$package_name" || continue
        [[ -f "$packages/ffmpeg.done" ]] || continue
        rm -f -- "$packages/ffmpeg.done" ||
            fail "Unable to clear the FFmpeg build marker for a reconfigure. Line: ${LINENO}"
        log "FFmpeg will be reconfigured and relinked so it picks those up."
        return 0
    done <<<"$added_packages"
}

ensure_build_context() {
    local context_file="$cwd/.ffmpeg-build-context"
    local temporary_context prior_marker context_changes added_packages

    [[ ! -L "$context_file" ]] ||
        fail "Refusing symlink build-context file '$context_file'."
    if [[ -e "$context_file" ]]; then
        [[ -f "$context_file" ]] ||
            fail "Build-context path is not a regular file: '$context_file'."
        [[ "$(stat -c '%h' "$context_file" 2>/dev/null || true)" == "1" ]] ||
            fail "Refusing multiply-linked build-context file '$context_file'."
    fi

    temporary_context="$(mktemp --tmpdir="$cwd" '.ffmpeg-build-context.XXXXXX')" ||
        fail "Unable to create a temporary build-context file."
    if ! write_build_context_payload >"$temporary_context" ||
        ! chmod 0600 "$temporary_context"; then
        rm -f -- "$temporary_context"
        fail "Unable to record the current build context."
    fi

    if [[ -f "$context_file" ]]; then
        if cmp -s -- "$context_file" "$temporary_context"; then
            rm -f -- "$temporary_context"
            return 0
        fi
        added_packages=""
        if added_packages="$(build_context_is_migratable "$context_file" "$temporary_context")"; then
            adopt_migrated_build_context "$context_file" "$temporary_context" "$added_packages"
            return 0
        fi
        context_changes=""
        context_changes="$(summarize_build_context_changes "$context_file" "$temporary_context")" ||
            context_changes=""
        rm -f -- "$temporary_context"
        # Every recorded line is compared, so an empty summary means the files
        # differ in a way this cannot attribute. Say that rather than blaming
        # settings the reader may not have touched.
        [[ -n "$context_changes" ]] ||
            fail "This workspace's build-context record differs from the current one in a way that cannot be attributed to a specific setting. Run '$CLEANUP_COMMAND' before rebuilding."
        fail "$(printf 'This workspace was built with different settings:\n%s\nRun %s before rebuilding.' \
            "$context_changes" "'$CLEANUP_COMMAND'")"
    fi

    prior_marker="$(find "$packages" -maxdepth 1 -type f -name '*.done' -print -quit 2>/dev/null || true)"
    if [[ -n "$prior_marker" ]]; then
        rm -f -- "$temporary_context"
        fail "This legacy workspace has package markers but no build-context record. Run '$CLEANUP_COMMAND' before rebuilding."
    fi
    mv -f -- "$temporary_context" "$context_file" ||
        fail "Unable to publish build-context file '$context_file'."
}

initialize_build_root() {
    local managed_file managed_path parent

    validate_build_root
    for managed_path in \
        "$packages" \
        "$workspace" \
        "$log_file" \
        "$cwd/.ffmpeg-build-root" \
        "$cwd/.ffmpeg-build-context"; do
        [[ ! -L "$managed_path" ]] ||
            fail "Refusing symlink at managed build path '$managed_path'."
    done
    # The build root is created empty first, and nothing is put inside it until
    # its marker exists: an interrupt here leaves an empty directory that the
    # next run accepts, rather than a populated unmarked one that neither
    # --build nor --cleanup would touch again.
    if [[ ! -d "$cwd" ]]; then
        parent="$(dirname -- "$cwd")"
        [[ -d "$parent" ]] || mkdir -p -- "$parent" ||
            fail "Unable to create build-root parent '$parent'."
        mkdir -p -- "$cwd" ||
            fail "Unable to create the build root '$cwd'."
    fi
    # Deliberately no `sudo mkdir`/`sudo chown` fallback. Escalating here would
    # let a build root the invoking user does not own be taken over, marked as
    # ours, and so become a legitimate --cleanup target. The marker means "this
    # project created it", not "this project annexed it".
    [[ -w "$cwd" && -r "$cwd" && -x "$cwd" ]] ||
        fail "Build root '$cwd' is not writable by '$BUILD_USER:$BUILD_GROUP'. Choose a different 'BUILD_ROOT' or grant ownership yourself; this script will not take it with 'sudo'."
    acquire_build_root_lock "$cwd"
    [[ ! -e "$log_file" || -f "$log_file" ]] ||
        fail "Build log path is not a regular file: '$log_file'."
    [[ ! -e "$cwd/.ffmpeg-build-root" || -f "$cwd/.ffmpeg-build-root" ]] ||
        fail "Build-root marker is not a regular file."
    for managed_file in "$log_file" "$cwd/.ffmpeg-build-root" "$cwd/.ffmpeg-build-context"; do
        if [[ -e "$managed_file" &&
            "$(stat -c '%h' "$managed_file" 2>/dev/null || true)" != "1" ]]; then
            fail "Refusing multiply-linked managed file '$managed_file'."
        fi
    done
    write_build_root_marker "$cwd"
    mkdir -p -- "$packages" "$workspace" ||
        fail "Unable to create the build-root scaffolding under '$cwd'."
    ensure_user_ownership \
        "$packages" \
        "$workspace" \
        "$log_file" \
        "$cwd/.ffmpeg-build-root" \
        "$cwd/.ffmpeg-build-context"
    cd -- "$cwd" || fail "Unable to enter build root '$cwd'."
}

# Kept out of initialize_build_root() so the previous build.log survives until
# ensure_build_context() has decided whether to abort. Truncating first
# destroyed the log of the very run the user is being told to investigate.
truncate_build_log() {
    : >"$log_file" || fail "Unable to initialize build log '$log_file'."
}

handle_signal() {
    local signal_name="${1:-TERM}"
    local exit_code

    case "$signal_name" in
        HUP) exit_code=129 ;;
        INT) exit_code=130 ;;
        TERM) exit_code=143 ;;
        *) exit_code=1 ;;
    esac
    warn "Received '$signal_name'; stopping after preserving build files in '$cwd'."
    exit "$exit_code"
}

configure_toolchain() {
    build_threads="${build_threads:-$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN)}"
    [[ "$build_threads" =~ ^[1-9][0-9]*$ ]] ||
        fail "Unable to determine a valid parallel job count."

    case "$COMPILER_FLAG" in
        gcc)
            CC=gcc
            CXX=g++
            ;;
        clang)
            CC=clang
            CXX=clang++
            ;;
    esac

    MAKEFLAGS="-j$build_threads"
    LC_ALL=C
    TZ=UTC
    export CC CXX MAKEFLAGS LATEST NONFREE_AND_GPL GOOGLE_SPEECH LC_ALL TZ
    ACLOCAL_PATH="$workspace/share/aclocal:/usr/local/share/aclocal:/usr/share/aclocal"
    export ACLOCAL_PATH
}

run_build() {
    [[ "$(uname -m)" == "x86_64" ]] ||
        fail "This build currently supports 'x86_64' only; detected '$(uname -m)'."

    umask 022
    # Everything checkable from the request alone is checked before the first
    # host mutation, so an unsatisfiable build fails without having installed
    # packages or prompted for sudo first.
    validate_build_settings
    initialize_build_root
    configure_toolchain
    # Before ensure_build_context: the context has to record the flags the
    # build actually uses. Snapshotting the inherited environment (normally
    # empty) meant a change in the computed defaults, such as reusing a
    # workspace on a different CPU with -march=native, went undetected.
    source_compiler_flags
    ensure_build_context
    # Last of the pure checks, so this is the first point where a password is
    # worth asking for. Everything above either validates the request or writes
    # inside a build root the user already owns, and a context mismatch aborts
    # the run outright.
    require_sudo
    truncate_build_log

    printf '\n'
    box_out_banner "FFmpeg Build Script $SCRIPT_VERSION"
    printf '\n'
    log "Build root: '$cwd'."
    log "Parallel jobs: '$build_threads'."
    log "Compiler family: '$COMPILER_FLAG'."
    is_true "$NONFREE_AND_GPL" && warn "GPL and non-free components are enabled."

    # shellcheck source=scripts/system-setup.sh
    source "$SCRIPT_DIR/scripts/system-setup.sh"
    with_host_mutation_lock initialize_system_setup
    validate_package_selection

    # shellcheck source=scripts/hardware-detection.sh
    source "$SCRIPT_DIR/scripts/hardware-detection.sh"
    initialize_hardware_detection
    with_host_mutation_lock install_cuda

    # shellcheck source=scripts/global-tools.sh
    source "$SCRIPT_DIR/scripts/global-tools.sh"
    install_global_tools

    # shellcheck source=scripts/core-libraries.sh
    source "$SCRIPT_DIR/scripts/core-libraries.sh"
    install_core_libraries

    # shellcheck source=scripts/support-libraries.sh
    source "$SCRIPT_DIR/scripts/support-libraries.sh"
    install_miscellaneous_libraries

    # shellcheck source=scripts/audio-libraries.sh
    source "$SCRIPT_DIR/scripts/audio-libraries.sh"
    install_audio_libraries

    # shellcheck source=scripts/video-libraries.sh
    source "$SCRIPT_DIR/scripts/video-libraries.sh"
    install_video_libraries

    # shellcheck source=scripts/image-libraries.sh
    source "$SCRIPT_DIR/scripts/image-libraries.sh"
    install_image_libraries

    # shellcheck source=scripts/ffmpeg-build.sh
    source "$SCRIPT_DIR/scripts/ffmpeg-build.sh"
    build_ffmpeg
}

main() {
    show_requested_metadata_and_exit "$@"
    # Checked here, not in run_build(): --cleanup is dispatched below without
    # ever reaching run_build, and it is the one destructive action in the
    # project. --help and --version have already exited above and stay usable
    # for any user.
    require_non_root "$EUID"
    # Arguments are validated before the config is read, so an invalid request
    # never opens, parses and applies a TOML file on its way to the error.
    parse_arguments "$@"
    load_requested_config "$@"
    resolve_build_root

    # Composed rather than replaced: handle_signal exits, so the EXIT trap runs
    # for Ctrl-C and SIGTERM too and every registered temporary tree is removed
    # on any exit path.
    trap 'sudo_keepalive_stop; remove_registered_temporary_paths' EXIT
    trap 'handle_signal INT' INT
    trap 'handle_signal TERM' TERM
    trap 'handle_signal HUP' HUP

    if is_true "$DO_CLEANUP"; then
        cleanup
        return 0
    fi
    if ! is_true "$DO_BUILD"; then
        usage
        return 0
    fi

    run_build
}

main "$@"
