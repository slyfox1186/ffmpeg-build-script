#!/usr/bin/env bash
# shellcheck source=/dev/null

set -o pipefail

readonly SCRIPT_VERSION="6.0.0"
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
    printf '\nEnvironment:\n'
    print_usage_row 'BUILD_ROOT=/path' 'Override the default ./build directory'
    print_usage_row 'CUDA_INSTALL=ask|always|never' 'Control CUDA toolkit installation (default: ask)'
    print_usage_row 'CUDA_ARCH_MODE=native|all|custom' 'Select CUDA code-generation targets'
    print_usage_row 'FFMPEG_BUILD_DEBUG=ON' 'Stream commands while also logging them'
    printf '\nExample:\n'
    printf '  bash %s --build --compiler clang --jobs 8 --config ./custom.toml\n\n' \
        "$SCRIPT_NAME"
}

resolve_config_path() {
    local input_path="${1:-}"
    local candidate_path

    [[ -n "$input_path" ]] || fail "Missing config path for '--config'."
    [[ ! "$input_path" =~ [[:cntrl:]] ]] ||
        fail "Config paths may not contain control characters."
    if [[ "$input_path" == /* ]]; then
        candidate_path="$input_path"
    elif [[ -f "$INVOCATION_DIR/$input_path" ]]; then
        candidate_path="$INVOCATION_DIR/$input_path"
    else
        candidate_path="$SCRIPT_DIR/$input_path"
    fi

    canonicalize_path "$candidate_path"
}

show_requested_metadata_and_exit() {
    local arg

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--version)
                printf '%s\n' "$SCRIPT_VERSION"
                exit 0
                ;;
        esac
    done
}

prescan_config() {
    local -a arguments=("$@")
    local index

    for ((index = 0; index < ${#arguments[@]}; index++)); do
        case "${arguments[index]}" in
            --config)
                ((index + 1 < ${#arguments[@]})) ||
                    fail "Missing value for '--config'."
                [[ -z "$PACKAGE_CONFIG_FILE" ]] ||
                    fail "'--config' may only be specified once."
                PACKAGE_CONFIG_FILE="$(resolve_config_path "${arguments[index + 1]}")"
                ((index += 1))
                ;;
            --config=*)
                [[ -z "$PACKAGE_CONFIG_FILE" ]] ||
                    fail "'--config' may only be specified once."
                PACKAGE_CONFIG_FILE="$(resolve_config_path "${arguments[index]#*=}")"
                ;;
        esac
    done

    [[ -z "$PACKAGE_CONFIG_FILE" ]] || load_package_selection_config "$PACKAGE_CONFIG_FILE"
}

parse_arguments() {
    while (($# > 0)); do
        case "$1" in
            -b|--build)
                DO_BUILD=true
                shift
                ;;
            -c|--cleanup)
                DO_CLEANUP=true
                shift
                ;;
            -g|--google-speech)
                GOOGLE_SPEECH=true
                shift
                ;;
            -l|--latest)
                LATEST=true
                shift
                ;;
            -n|--enable-gpl-and-non-free)
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
            -j|--jobs)
                (($# >= 2)) || fail "Missing value for '$1'."
                build_threads="$2"
                shift 2
                ;;
            --config)
                (($# >= 2)) || fail "Missing value for '--config'."
                shift 2
                ;;
            --config=*)
                shift
                ;;
            -h|--help|-v|--version)
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
    if [[ -n "$build_threads" ]]; then
        [[ "$build_threads" =~ ^[1-9][0-9]*$ ]] ||
            fail "Invalid jobs value '$build_threads'; expected a positive integer."
    fi
    if is_true "$DO_BUILD" && is_true "$DO_CLEANUP"; then
        fail "'--build' and '--cleanup' are mutually exclusive."
    fi
    [[ "$debug" == "ON" || "$debug" == "OFF" ]] ||
        fail "Invalid 'FFMPEG_BUILD_DEBUG' value '$debug'; expected 'ON' or 'OFF'."
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
    local home_resolved parent first_entry

    [[ "${HOME:-}" == /* ]] ||
        fail "'HOME' must name an absolute user home directory."
    home_resolved="$(canonicalize_path "${HOME:-}")" ||
        fail "'HOME' must name an absolute user home directory."
    [[ "$cwd" != *[[:space:]]* ]] ||
        fail "'BUILD_ROOT' may not contain whitespace because several upstream build systems cannot represent it safely: '$cwd'."
    case "$cwd" in
        /|/bin|/boot|/dev|/etc|/lib|/lib64|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/var)
            fail "Refusing unsafe build root '$cwd'."
            ;;
    esac
    [[ "$cwd" != "$home_resolved" && "$cwd" != "$REPO_ROOT" ]] ||
        fail "Refusing unsafe build root '$cwd'."

    parent="$(dirname -- "$cwd")"
    [[ -d "$parent" ]] ||
        mkdir -p -- "$parent" ||
        fail "Unable to create build-root parent '$parent'."

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
            else
                fail "'BUILD_ROOT' '$cwd' already contains data and lacks a valid path-bound FFmpeg build-root marker."
            fi
        fi
    fi
}

write_build_context_payload() {
    local package_name

    printf '%s\n' \
        "ffmpeg-build-context:v1" \
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

ensure_build_context() {
    local context_file="$cwd/.ffmpeg-build-context"
    local temporary_context prior_marker

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
        rm -f -- "$temporary_context"
        fail "Compiler, flags, licensing mode, CUDA targets, or package selections changed for this workspace. Run '$CLEANUP_COMMAND' before rebuilding."
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
    local managed_file managed_path

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
    if ! mkdir -p -- "$packages" "$workspace"; then
        execute sudo mkdir -p -- "$packages" "$workspace"
    fi
    if [[ "$(stat -c '%u' "$cwd" 2>/dev/null || true)" != "$BUILD_UID" ||
        ! -w "$cwd" ]]; then
        execute sudo chown "$BUILD_UID:$BUILD_GID" "$cwd"
    fi
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
    ensure_user_ownership \
        "$packages" \
        "$workspace" \
        "$log_file" \
        "$cwd/.ffmpeg-build-root" \
        "$cwd/.ffmpeg-build-context"
    : >"$log_file" || fail "Unable to initialize build log '$log_file'."
    cd -- "$cwd" || fail "Unable to enter build root '$cwd'."
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
    [[ "$EUID" -ne 0 ]] ||
        fail "Run '$SCRIPT_NAME' as a normal user; it invokes 'sudo' only for system changes."
    [[ "$(uname -m)" == "x86_64" ]] ||
        fail "This build currently supports 'x86_64' only; detected '$(uname -m)'."

    umask 022
    require_sudo
    initialize_build_root
    configure_toolchain
    ensure_build_context

    printf '\n'
    box_out_banner "FFmpeg Build Script $SCRIPT_VERSION"
    printf '\n'
    log "Build root: '$cwd'."
    log "Parallel jobs: '$build_threads'."
    log "Compiler family: '$COMPILER_FLAG'."
    is_true "$NONFREE_AND_GPL" && warn "GPL and non-free components are enabled."

    # shellcheck source=scripts/system-setup.sh
    source "$SCRIPT_DIR/scripts/system-setup.sh"
    initialize_system_setup
    validate_package_selection

    # shellcheck source=scripts/hardware-detection.sh
    source "$SCRIPT_DIR/scripts/hardware-detection.sh"
    initialize_hardware_detection
    install_cuda

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
    prescan_config "$@"
    parse_arguments "$@"
    resolve_build_root

    trap sudo_keepalive_stop EXIT
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
