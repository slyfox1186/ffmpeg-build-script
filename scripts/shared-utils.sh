#!/usr/bin/env bash
# shellcheck disable=SC2154,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Shared Utilities
##  Common functions used across all build scripts
##
####################################################################################

# Safer default pipeline behavior across all sourced scripts.
# We intentionally do NOT enable `set -e` or `set -u` because many build steps
# rely on optional probes failing without aborting the whole build.
set -o pipefail

# Source guard: prevent redundant re-sourcing when multiple scripts source this file.
# Each script sources shared-utils.sh for standalone usage, but during a full build
# the orchestrator (build-ffmpeg.sh) already sources it first.
if [[ -n "${_SHARED_UTILS_LOADED:-}" ]]; then
    return 0 2>/dev/null || true
fi
_SHARED_UTILS_LOADED=1

# Emit ANSI colors only to an interactive terminal and honor the standard
# NO_COLOR convention. Build logs and redirected output remain plain text.
if [[ -t 1 && "${TERM:-dumb}" != "dumb" && -z "${NO_COLOR:-}" ]]; then
    GREEN=$'\033[0;32m'
    RED=$'\033[0;31m'
    YELLOW=$'\033[0;33m'
    CYAN=$'\033[0;36m'
    NC=$'\033[0m'
else
    GREEN=""
    RED=""
    YELLOW=""
    CYAN=""
    NC=""
fi

# Resolve ownership from the effective account, not from the caller-controlled
# USER environment variable. A user's primary group is not necessarily named
# after the user, so retain both numeric IDs and display names.
BUILD_UID="$(id -u)"
BUILD_GID="$(id -g)"
BUILD_USER="$(id -un)"
BUILD_GROUP="$(id -gn)"
readonly BUILD_UID BUILD_GID BUILD_USER BUILD_GROUP
readonly BUILD_ROOT_MARKER_HEADER="ffmpeg-build-root:v1"
_BUILD_ROOT_LOCK_FD=""

# Debug flag
debug="${FFMPEG_BUILD_DEBUG:-OFF}"

# Versioned host-side build helpers. Keeping cargo-c inside the workspace avoids
# mutating the user's global Cargo installation and makes rav1e's C ABI build
# reproducible across otherwise identical runs.
readonly CARGO_C_VERSION="0.10.24+cargo-0.98.0"
readonly RUST_TOOLCHAIN_VERSION="1.95.0"

# GNU mirrors (override via environment variables if needed)
GNU_PRIMARY_MIRROR="${GNU_PRIMARY_MIRROR:-https://mirrors.ibiblio.org/gnu}"
GNU_FALLBACK_MIRROR="${GNU_FALLBACK_MIRROR:-https://mirror.team-cymru.com/gnu}"

# Optional build selection loaded from a minimal TOML config.
declare -Ag PACKAGE_SELECTION=()
PACKAGE_SELECTION_CONFIG_FILE=""
declare -Ag REQUIRED_FFMPEG_CONFIG_SYMBOLS=()

# Canonical package/feature keys accepted in [packages]. Keeping this registry
# beside the parser turns misspelled config entries into immediate errors rather
# than silently building an unintended default package.
readonly -a SUPPORTED_PACKAGE_NAMES=(
    m4 autoconf automake libtool pkgconf cmake meson ninja libzstd librist zlib openssl
    yasm nasm giflib libiconv libxml2 libpng libtiff libaribb24
    gmp nettle gnutls freetype fontconfig harfbuzz fribidi libass freeglut
    libwebp-git libhwy brotli lcms2 gflags opencl-sdk-git vulkan-headers-git
    libjpeg-turbo rubberband-git c-ares lv2-git serd pcre2 zix sord sratom lilv jemalloc
    libsoxr sdl2 libsndfile libogg libfdk-aac vorbis libopus libmysofa opencore-amr
    liblame libtheora av1-git libvmaf rav1e zimg-git avif kvazaar libdvdread udfread
    ant-git zenlib mediainfo-lib mediainfo-cli vid-stab x264 x265 nv-codec-headers
    vaapi amf-headers srt avisynth xvidcore gpac-git svt-av1 vapoursynth libgav1-git
    libheif openjpeg libbluray libvpx
    libdav1d libvpl libspeex libssh chromaprint libjxl libtesseract libzvbi libmodplug
    libgme libshine libcaca libbs2b libjack libv4l2 xlib libsnappy libtwolame
    libvo-amrwbenc libgsm ladspa opengl frei0r libopenh264 libopenmpt librtmp librsvg
    libflite alsa libpulse sndio libdrm vdpau libsmbclient libcdio
    vulkan libshaderc libplacebo ffmpeg
)
declare -Ag SUPPORTED_PACKAGES=()
for _supported_package_name in "${SUPPORTED_PACKAGE_NAMES[@]}"; do
    SUPPORTED_PACKAGES["$_supported_package_name"]=1
done
unset _supported_package_name

# Backward compatibility for the one historical key whose name did not match
# the build marker and therefore never actually disabled its package.
declare -Ar PACKAGE_KEY_ALIASES=(
    ["vulkan-headers"]="vulkan-headers-git"
)

# Banner functions
box_out_banner() {
    local text="$*"
    local text_len=${#text}
    local inner_len=$((text_len + 2))
    local border color_border="" color_text="" color_reset=""

    if [[ -n "$NC" ]] && command -v tput >/dev/null 2>&1; then
        color_border="$(tput setaf 3 2>/dev/null || true)"
        color_text="$(tput setaf 4 2>/dev/null || true)"
        color_reset="$(tput sgr0 2>/dev/null || true)"
        tput bold 2>/dev/null || true
    fi

    printf -v border '%*s' "$inner_len" ''
    border=${border// /-}

    printf ' %b%s%b\n' "$color_border" "$border" "$color_reset"
    printf '|%*s|\n' "$inner_len" ''
    printf '| %b%s%b |\n' "$color_text" "$text" "$color_reset"
    printf '|%*s|\n' "$inner_len" ''
    printf ' %b%s%b\n' "$color_border" "$border" "$color_reset"
    if [[ -n "$color_reset" ]]; then
        printf '%b' "$color_reset"
    fi
}

# Logging functions
log() {
    printf '%s\n' "$1"
    if [[ -n "${log_file:-}" && -f "$log_file" ]]; then
        printf '%s\n' "$1" >>"$log_file"
    fi
}

# Diagnostics go to stderr: several helpers (git_clone, resolve_tool_path, the
# *_download_url builders, ...) are invoked inside $(...) command substitutions,
# and stdout warnings would be captured into the caller's variable (e.g. a
# clone-retry warning corrupting the detected version) instead of reaching the user.
warn() {
    printf '%s[WARNING]%s %s\n' "$YELLOW" "$NC" "$1" >&2
}

require_vars() {
    local var_name
    for var_name in "$@"; do
        if [[ -z "${!var_name:-}" ]]; then
            fail "Required variable '$var_name' is not set. Line: ${LINENO}"
        fi
    done
}

require_commands() {
    local command_name
    local -a missing_commands=()

    for command_name in "$@"; do
        command -v "$command_name" >/dev/null 2>&1 || missing_commands+=("$command_name")
    done

    if ((${#missing_commands[@]} > 0)); then
        fail "Required command(s) not found: ${missing_commands[*]}"
    fi
}

curl_https() {
    command curl --proto '=https' --proto-redir '=https' --tlsv1.2 "$@"
}

is_true() {
    [[ "${1:-false}" == "true" ]]
}

canonicalize_path() {
    local path="${1:-}"

    [[ -n "$path" ]] || return 1
    readlink -m -- "$path"
}

path_is_within() {
    local candidate="${1:-}"
    local allowed_root="${2:-}"
    local candidate_resolved root_resolved

    [[ -n "$candidate" && -n "$allowed_root" ]] || return 1
    candidate_resolved="$(canonicalize_path "$candidate")" || return 1
    root_resolved="$(canonicalize_path "$allowed_root")" || return 1

    [[ "$candidate_resolved" == "$root_resolved"/* ]]
}

build_root_marker_matches() {
    local marker_file="${1:-}"
    local expected_root="${2:-}"
    local expected_root_resolved
    local -a marker_lines=()

    [[ -n "$marker_file" && -n "$expected_root" ]] || return 1
    [[ -f "$marker_file" && ! -L "$marker_file" ]] || return 1
    [[ "$(stat -c '%h' "$marker_file" 2>/dev/null || true)" == "1" ]] || return 1
    expected_root_resolved="$(canonicalize_path "$expected_root")" || return 1
    mapfile -t marker_lines <"$marker_file" || return 1
    ((${#marker_lines[@]} == 2)) || return 1
    [[ "${marker_lines[0]}" == "$BUILD_ROOT_MARKER_HEADER" &&
        "${marker_lines[1]}" == "root=$expected_root_resolved" ]]
}

legacy_build_root_marker() {
    local marker_file="${1:-}"

    [[ -f "$marker_file" && ! -L "$marker_file" ]] || return 1
    [[ "$(stat -c '%h' "$marker_file" 2>/dev/null || true)" == "1" ]] || return 1
    [[ ! -s "$marker_file" ]]
}

write_build_root_marker() {
    local root="${1:-}"
    local root_resolved marker_file temp_file

    [[ -n "$root" ]] || fail "write_build_root_marker() requires a build root. Line: ${LINENO}"
    root_resolved="$(canonicalize_path "$root")" ||
        fail "Unable to canonicalize build root '$root'. Line: ${LINENO}"
    [[ "$root_resolved" != "/" && -d "$root_resolved" ]] ||
        fail "Refusing to write a marker for unsafe build root '$root_resolved'. Line: ${LINENO}"
    marker_file="$root_resolved/.ffmpeg-build-root"
    [[ ! -L "$marker_file" ]] ||
        fail "Refusing symlink build-root marker '$marker_file'. Line: ${LINENO}"

    temp_file="$(mktemp --tmpdir="$root_resolved" '.ffmpeg-build-root.XXXXXX')" ||
        fail "Unable to create a temporary build-root marker. Line: ${LINENO}"
    if ! printf '%s\nroot=%s\n' "$BUILD_ROOT_MARKER_HEADER" "$root_resolved" >"$temp_file" ||
        ! chmod 0600 "$temp_file" ||
        ! mv -f -- "$temp_file" "$marker_file"; then
        rm -f -- "$temp_file"
        fail "Unable to publish build-root marker '$marker_file'. Line: ${LINENO}"
    fi
}

acquire_build_root_lock() {
    local root="${1:-}"

    [[ -n "$root" && -d "$root" ]] ||
        fail "acquire_build_root_lock() requires an existing build root. Line: ${LINENO}"
    [[ -z "$_BUILD_ROOT_LOCK_FD" ]] || return 0
    require_commands flock

    exec {_BUILD_ROOT_LOCK_FD}<"$root" ||
        fail "Unable to open build root '$root' for locking. Line: ${LINENO}"
    if ! flock -n "$_BUILD_ROOT_LOCK_FD"; then
        exec {_BUILD_ROOT_LOCK_FD}>&-
        _BUILD_ROOT_LOCK_FD=""
        fail "Another process is already using build root '$root'."
    fi
}

# Remove one directory only when its canonical path is a strict descendant of
# the explicitly supplied root. This avoids vulnerable string-prefix checks
# such as /tmp/packages* also matching /tmp/packages-elsewhere.
safe_remove_tree() {
    local target="${1:-}"
    local allowed_root="${2:-}"
    local target_resolved root_resolved

    [[ -n "$target" ]] || fail "Refusing to remove an empty path. Line: ${LINENO}"
    [[ -n "$allowed_root" ]] || fail "safe_remove_tree() requires an allowed root. Line: ${LINENO}"
    [[ -e "$target" || -L "$target" ]] || return 0

    target_resolved="$(canonicalize_path "$target")" ||
        fail "Unable to canonicalize removal target '$target'. Line: ${LINENO}"
    root_resolved="$(canonicalize_path "$allowed_root")" ||
        fail "Unable to canonicalize allowed root '$allowed_root'. Line: ${LINENO}"

    [[ "$root_resolved" != "/" ]] ||
        fail "Refusing to use '/' as a removal root. Line: ${LINENO}"
    [[ "$target_resolved" != "$root_resolved" ]] ||
        fail "Refusing to remove the allowed root itself: '$target_resolved'. Line: ${LINENO}"
    path_is_within "$target_resolved" "$root_resolved" ||
        fail "Refusing to remove path outside '$root_resolved': '$target_resolved'. Line: ${LINENO}"

    rm -rf --one-file-system -- "$target" ||
        fail "Failed to remove bounded path '$target'. Line: ${LINENO}"
}

format_command() {
    local formatted=""

    printf -v formatted '%q ' "$@"
    printf '%s' "${formatted% }"
}

read_marker_version() {
    local marker_file="${1:-}"
    local marker_version=""
    local -a marker_lines=()

    [[ -f "$marker_file" && ! -L "$marker_file" ]] || return 1
    [[ "$(stat -c '%h' "$marker_file" 2>/dev/null || true)" == "1" ]] || return 1
    mapfile -t marker_lines <"$marker_file" || return 1
    ((${#marker_lines[@]} == 1)) || return 1
    marker_version="${marker_lines[0]}"
    marker_version="$(trim_whitespace "$marker_version")"
    [[ "$marker_version" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || return 1
    printf '%s\n' "$marker_version"
}

trim_whitespace() {
    local value="${1:-}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

enable_gpl_and_non_free() {
    if [[ "${NONFREE_AND_GPL:-false}" == "true" ]]; then
        return 0
    fi

    CONFIGURE_OPTIONS+=(--enable-gpl --enable-nonfree)
    NONFREE_AND_GPL=true
}

package_enabled() {
    local package_name="${1:-}"
    local selected_value

    [[ -n "$package_name" ]] || fail "package_enabled() called without a package name. Line: ${LINENO}"
    [[ -n "${SUPPORTED_PACKAGES[$package_name]+x}" ]] ||
        fail "package_enabled() received unsupported package '$package_name'. Line: ${LINENO}"

    if [[ -n "${PACKAGE_SELECTION[$package_name]+x}" ]]; then
        selected_value="${PACKAGE_SELECTION[$package_name]}"
    elif [[ -n "$PACKAGE_SELECTION_CONFIG_FILE" ]]; then
        selected_value=false
    else
        selected_value=true
    fi
    [[ "$selected_value" == "true" ]]
}

package_explicitly_enabled() {
    local package_name="${1:-}"

    [[ -n "$package_name" ]] ||
        fail "package_explicitly_enabled() called without a package name. Line: ${LINENO}"
    [[ -n "${SUPPORTED_PACKAGES[$package_name]+x}" ]] ||
        fail "package_explicitly_enabled() received unsupported package '$package_name'. Line: ${LINENO}"
    [[ "${PACKAGE_SELECTION[$package_name]:-false}" == "true" ]]
}

record_required_ffmpeg_config_option() {
    local option config_name

    for option in "$@"; do
        [[ "$option" == --enable-* ]] || continue
        config_name="${option#--enable-}"
        config_name="${config_name^^}"
        config_name="${config_name//-/_}"
        # This cross-script registry is consumed by scripts/ffmpeg-build.sh.
        # shellcheck disable=SC2034
        REQUIRED_FFMPEG_CONFIG_SYMBOLS["CONFIG_$config_name"]="$option"
    done
}

append_configure_options_if_enabled() {
    local package_name="${1:-}"

    [[ -n "$package_name" ]] || fail "append_configure_options_if_enabled() called without a package name. Line: ${LINENO}"
    shift || true

    package_enabled "$package_name" || return 0
    CONFIGURE_OPTIONS+=("$@")
    record_required_ffmpeg_config_option "$@"
}

resolve_tool_path() {
    local tool_name preferred_path resolved_path
    tool_name="${1:-}"
    preferred_path="${2:-}"

    [[ -n "$tool_name" ]] || fail "resolve_tool_path() called without a tool name. Line: ${LINENO}"

    if [[ -n "$preferred_path" ]] && [[ -x "$preferred_path" ]]; then
        printf '%s\n' "$preferred_path"
        return 0
    fi

    resolved_path="$(command -v "$tool_name" 2>/dev/null || true)"
    if [[ -n "$resolved_path" ]]; then
        printf '%s\n' "$resolved_path"
        return 0
    fi

    fail "Required tool '$tool_name' was not found. Enable its package in config or install it with your system package manager."
}

resolve_pkgconf_prefix() {
    local module_name prefix
    module_name="${1:-}"

    [[ -n "$module_name" ]] || fail "resolve_pkgconf_prefix() called without a module name. Line: ${LINENO}"

    prefix="$(pkgconf --variable=prefix "$module_name" 2>/dev/null || true)"
    [[ -n "$prefix" ]] || fail "Unable to resolve pkgconf prefix for '$module_name'. Install the matching development package or enable the local build dependency."
    printf '%s\n' "$prefix"
}

resolve_pkgconf_include_dir() {
    local module_name include_flags token include_dir
    module_name="${1:-}"

    [[ -n "$module_name" ]] || fail "resolve_pkgconf_include_dir() called without a module name. Line: ${LINENO}"

    include_flags="$(pkgconf --cflags-only-I "$module_name" 2>/dev/null || true)"
    for token in $include_flags; do
        if [[ "$token" == -I* ]]; then
            printf '%s\n' "${token#-I}"
            return 0
        fi
    done

    include_dir="$(pkgconf --variable=includedir "$module_name" 2>/dev/null || true)"
    [[ -n "$include_dir" ]] || fail "Unable to resolve include dir for pkgconf module '$module_name'."
    printf '%s\n' "$include_dir"
}

resolve_pkgconf_library_dir() {
    local module_name lib_flags token lib_dir
    module_name="${1:-}"

    [[ -n "$module_name" ]] || fail "resolve_pkgconf_library_dir() called without a module name. Line: ${LINENO}"

    lib_flags="$(pkgconf --libs-only-L "$module_name" 2>/dev/null || true)"
    for token in $lib_flags; do
        if [[ "$token" == -L* ]]; then
            printf '%s\n' "${token#-L}"
            return 0
        fi
    done

    lib_dir="$(pkgconf --variable=libdir "$module_name" 2>/dev/null || true)"
    [[ -n "$lib_dir" ]] || fail "Unable to resolve library dir for pkgconf module '$module_name'."
    printf '%s\n' "$lib_dir"
}

resolve_pkgconf_library_file() {
    local module_name library_basename library_dir candidate
    module_name="${1:-}"
    library_basename="${2:-}"

    [[ -n "$module_name" ]] || fail "resolve_pkgconf_library_file() called without a module name. Line: ${LINENO}"
    [[ -n "$library_basename" ]] || fail "resolve_pkgconf_library_file() called without a library basename. Line: ${LINENO}"

    library_dir="$(resolve_pkgconf_library_dir "$module_name")"
    for candidate in \
        "$library_dir/lib${library_basename}.a" \
        "$library_dir/lib${library_basename}.so" \
        "$library_dir/lib${library_basename}.so.0"; do
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    fail "Unable to locate lib${library_basename} in '$library_dir' for pkgconf module '$module_name'."
}

first_existing_path() {
    local candidate

    for candidate in "$@"; do
        if [[ -n "$candidate" ]] && [[ -e "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

resolve_workspace_or_pkgconf_include_dir() {
    local package_name module_name
    package_name="${1:-}"
    module_name="${2:-}"

    [[ -n "$package_name" ]] || fail "resolve_workspace_or_pkgconf_include_dir() called without a package name. Line: ${LINENO}"
    [[ -n "$module_name" ]] || fail "resolve_workspace_or_pkgconf_include_dir() called without a module name. Line: ${LINENO}"
    shift 2 || true
    require_vars workspace

    if package_enabled "$package_name" && first_existing_path "$@" >/dev/null; then
        printf '%s\n' "$workspace/include"
        return 0
    fi

    resolve_pkgconf_include_dir "$module_name"
}

resolve_workspace_or_pkgconf_library_dir() {
    local package_name module_name workspace_library
    package_name="${1:-}"
    module_name="${2:-}"

    [[ -n "$package_name" ]] || fail "resolve_workspace_or_pkgconf_library_dir() called without a package name. Line: ${LINENO}"
    [[ -n "$module_name" ]] || fail "resolve_workspace_or_pkgconf_library_dir() called without a module name. Line: ${LINENO}"
    shift 2 || true
    require_vars workspace

    if package_enabled "$package_name"; then
        workspace_library="$(first_existing_path "$@" || true)"
        if [[ -n "$workspace_library" ]]; then
            dirname -- "$workspace_library"
            return 0
        fi
    fi

    resolve_pkgconf_library_dir "$module_name"
}

resolve_workspace_or_pkgconf_library_file() {
    local package_name module_name library_basename workspace_library
    package_name="${1:-}"
    module_name="${2:-}"
    library_basename="${3:-}"

    [[ -n "$package_name" ]] || fail "resolve_workspace_or_pkgconf_library_file() called without a package name. Line: ${LINENO}"
    [[ -n "$module_name" ]] || fail "resolve_workspace_or_pkgconf_library_file() called without a module name. Line: ${LINENO}"
    [[ -n "$library_basename" ]] || fail "resolve_workspace_or_pkgconf_library_file() called without a library basename. Line: ${LINENO}"
    shift 3 || true
    require_vars workspace

    if package_enabled "$package_name"; then
        workspace_library="$(first_existing_path "$@" || true)"
        if [[ -n "$workspace_library" ]]; then
            printf '%s\n' "$workspace_library"
            return 0
        fi
    fi

    resolve_pkgconf_library_file "$module_name" "$library_basename"
}

load_package_selection_config() {
    local config_file current_table key canonical_key raw_line value line line_no entry_id
    local -A seen_entries=()
    local -A seen_tables=()
    config_file="${1:-}"
    line_no=0

    [[ -n "$config_file" ]] || fail "Missing config file path for --config. Line: ${LINENO}"
    [[ -f "$config_file" ]] || fail "Config file not found: $config_file. Line: ${LINENO}"
    [[ -r "$config_file" ]] || fail "Config file is not readable: $config_file. Line: ${LINENO}"

    PACKAGE_SELECTION_CONFIG_FILE="$(canonicalize_path "$config_file")"
    PACKAGE_SELECTION=()

    while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
        ((line_no += 1))
        line="${raw_line%%#*}"
        line="$(trim_whitespace "$line")"

        [[ -z "$line" ]] && continue

        if [[ "$line" =~ ^\[([A-Za-z0-9._-]+)\]$ ]]; then
            current_table="${BASH_REMATCH[1]}"
            case "$current_table" in
                build|packages) ;;
                *) fail "Unsupported TOML table '$current_table' in $config_file:$line_no" ;;
            esac
            [[ -z "${seen_tables[$current_table]+x}" ]] ||
                fail "Duplicate TOML table '$current_table' in $config_file:$line_no"
            seen_tables["$current_table"]=1
            continue
        fi

        if [[ "$line" =~ ^([A-Za-z0-9_-]+)[[:space:]]*=[[:space:]]*(true|false)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            case "$current_table" in
                build)
                    entry_id="build.$key"
                    if [[ -n "${seen_entries[$entry_id]+x}" ]]; then
                        fail "Duplicate config key '$entry_id' in $config_file:$line_no"
                    fi
                    seen_entries["$entry_id"]=1
                    case "$key" in
                        latest)
                            LATEST="$value"
                            ;;
                        enable_gpl_and_non_free)
                            if [[ "$value" == "true" ]]; then
                                enable_gpl_and_non_free
                            else
                                NONFREE_AND_GPL=false
                            fi
                            ;;
                        *)
                            fail "Unsupported [build] key '$key' in $config_file:$line_no"
                            ;;
                    esac
                    ;;
                packages)
                    canonical_key="${PACKAGE_KEY_ALIASES[$key]:-$key}"
                    if [[ -z "${SUPPORTED_PACKAGES[$canonical_key]+x}" ]]; then
                        fail "Unsupported [packages] key '$key' in $config_file:$line_no"
                    fi
                    entry_id="packages.$canonical_key"
                    if [[ -n "${seen_entries[$entry_id]+x}" ]]; then
                        fail "Duplicate config key '$entry_id' in $config_file:$line_no"
                    fi
                    seen_entries["$entry_id"]=1
                    if [[ "$canonical_key" != "$key" ]]; then
                        warn "Config key 'packages.$key' is deprecated; use 'packages.$canonical_key'."
                    fi
                    PACKAGE_SELECTION["$canonical_key"]="$value"
                    ;;
                *)
                    fail "Unsupported TOML table '${current_table:-<root>}' in $config_file:$line_no"
                    ;;
            esac
            continue
        fi

        fail "Unsupported config syntax in $config_file:$line_no -> $raw_line"
    done < "$config_file"

    log "Loaded package selection config: $config_file"
    log "If you are changing package selections on an existing workspace, run --cleanup first to avoid reusing old build artifacts."
}

validate_package_selection() {
    local -a issues=()

    if package_enabled "vorbis" && ! package_enabled "libogg" && ! pkgconf --exists ogg 2>/dev/null; then
        issues+=("packages.vorbis=true requires packages.libogg=true or a system libogg development package")
    fi

    if package_enabled "libtheora"; then
        if ! package_enabled "libogg" && ! pkgconf --exists ogg 2>/dev/null; then
            issues+=("packages.libtheora=true requires packages.libogg=true or a system libogg development package")
        fi
    fi

    if is_true "${NONFREE_AND_GPL:-false}" &&
        package_enabled "openssl" &&
        ! package_enabled "zlib" &&
        ! pkgconf --exists zlib 2>/dev/null; then
        issues+=("packages.openssl=true requires packages.zlib=true or a system zlib development package")
    fi

    if { ! is_true "${NONFREE_AND_GPL:-false}" || ! package_enabled "openssl"; } &&
        package_enabled "gnutls"; then
        if ! package_enabled "gmp" && ! pkgconf --exists gmp 2>/dev/null; then
            issues+=("packages.gnutls=true requires packages.gmp=true or a system GMP development package")
        fi
        if ! package_enabled "nettle" && ! pkgconf --exists nettle 2>/dev/null; then
            issues+=("packages.gnutls=true requires packages.nettle=true or a system nettle development package")
        fi
    fi

    if is_true "${NONFREE_AND_GPL:-false}" &&
        package_enabled "srt" &&
        ! package_enabled "openssl" &&
        ! pkgconf --exists openssl 2>/dev/null; then
        issues+=("packages.srt=true requires packages.openssl=true or a system OpenSSL development package")
    fi

    if package_enabled "fontconfig" && ! package_enabled "libxml2" && ! pkgconf --exists libxml-2.0 2>/dev/null; then
        issues+=("packages.fontconfig=true requires packages.libxml2=true or a system libxml2 development package")
    fi
    if package_enabled "fontconfig" && ! package_enabled "freetype" && ! pkgconf --exists freetype2 2>/dev/null; then
        issues+=("packages.fontconfig=true requires packages.freetype=true or a system FreeType development package")
    fi

    if package_enabled "libass"; then
        if ! package_enabled "fontconfig" && ! pkgconf --exists fontconfig 2>/dev/null; then
            issues+=("packages.libass=true requires packages.fontconfig=true or a system fontconfig development package")
        fi
        if ! package_enabled "freetype" && ! pkgconf --exists freetype2 2>/dev/null; then
            issues+=("packages.libass=true requires packages.freetype=true or a system freetype development package")
        fi
        if ! package_enabled "fribidi" && ! pkgconf --exists fribidi 2>/dev/null; then
            issues+=("packages.libass=true requires packages.fribidi=true or a system fribidi development package")
        fi
        if ! package_enabled "harfbuzz" && ! pkgconf --exists harfbuzz 2>/dev/null; then
            issues+=("packages.libass=true requires packages.harfbuzz=true or a system harfbuzz development package")
        fi
    fi

    if package_enabled "sord"; then
        if ! package_enabled "serd" && ! pkgconf --exists serd-0 2>/dev/null; then
            issues+=("packages.sord=true requires packages.serd=true or a system Serd development package")
        fi
        if ! package_enabled "zix" && ! pkgconf --exists zix-0 2>/dev/null; then
            issues+=("packages.sord=true requires packages.zix=true or a system Zix development package")
        fi
    fi

    if package_enabled "sratom"; then
        if ! package_enabled "lv2-git" && ! pkgconf --exists lv2 2>/dev/null; then
            issues+=("packages.sratom=true requires packages.lv2-git=true or system LV2 headers")
        fi
        if ! package_enabled "serd" && ! pkgconf --exists serd-0 2>/dev/null; then
            issues+=("packages.sratom=true requires packages.serd=true or a system Serd development package")
        fi
    fi

    if package_enabled "lilv"; then
        if ! package_enabled "lv2-git" && ! pkgconf --exists lv2 2>/dev/null; then
            issues+=("packages.lilv=true requires packages.lv2-git=true or system LV2 headers")
        fi
        if ! package_enabled "serd" && ! pkgconf --exists serd-0 2>/dev/null; then
            issues+=("packages.lilv=true requires packages.serd=true or a system Serd development package")
        fi
        if ! package_enabled "zix" && ! pkgconf --exists zix-0 2>/dev/null; then
            issues+=("packages.lilv=true requires packages.zix=true or a system Zix development package")
        fi
        if ! package_enabled "sord" && ! pkgconf --exists sord-0 2>/dev/null; then
            issues+=("packages.lilv=true requires packages.sord=true or a system Sord development package")
        fi
        if ! package_enabled "sratom" && ! pkgconf --exists sratom-0 2>/dev/null; then
            issues+=("packages.lilv=true requires packages.sratom=true or a system Sratom development package")
        fi
    fi

    if package_enabled "avif" && ! package_enabled "av1-git" && ! pkgconf --exists aom 2>/dev/null; then
        issues+=("packages.avif=true requires packages.av1-git=true or a system libaom development package")
    fi

    if package_enabled "mediainfo-lib" && ! package_enabled "zenlib"; then
        issues+=("packages.mediainfo-lib=true requires packages.zenlib=true")
    fi

    if package_enabled "mediainfo-cli" && ! package_enabled "mediainfo-lib"; then
        issues+=("packages.mediainfo-cli=true requires packages.mediainfo-lib=true")
    fi

    if is_true "${NONFREE_AND_GPL:-false}" &&
        package_enabled "x264" &&
        ! command -v yasm >/dev/null 2>&1 &&
        ! command -v nasm >/dev/null 2>&1; then
        issues+=("packages.x264=true requires yasm or nasm to be available")
    fi

    if ((${#issues[@]} > 0)); then
        fail "$(printf 'Package selection has unresolved dependencies:\n - %s\n' "${issues[@]}")"
    fi
}

# Background sudo credential refresher PID (see sudo_keepalive_start).
_SUDO_KEEPALIVE_PID=""

# Keep the cached sudo credential fresh for the whole build so long compile phases
# never trigger a mid-run "[sudo] password" re-prompt. Without this, the single
# `sudo -v` in require_sudo() expires (sudo's timestamp_timeout, ~15 min by default)
# and every later sudo step prompts again. The refresher polls the parent script's
# PID and exits on its own when the build finishes, so it needs no EXIT trap and
# cannot clobber the save/restore traps used elsewhere (e.g. CUDA temp cleanup).
sudo_keepalive_start() {
    [[ -n "$_SUDO_KEEPALIVE_PID" ]] && kill -0 "$_SUDO_KEEPALIVE_PID" 2>/dev/null && return 0
    local parent_pid=$$
    (
        while kill -0 "$parent_pid" 2>/dev/null; do
            # -n: never prompt. If the cached credential can't be refreshed
            # (e.g. timestamp_timeout=0), stop instead of spinning.
            sudo -n -v 2>/dev/null || break
            sleep 50
        done
    ) &
    _SUDO_KEEPALIVE_PID=$!
}

sudo_keepalive_stop() {
    if [[ -n "$_SUDO_KEEPALIVE_PID" ]] && kill -0 "$_SUDO_KEEPALIVE_PID" 2>/dev/null; then
        kill "$_SUDO_KEEPALIVE_PID" 2>/dev/null || true
        wait "$_SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
    _SUDO_KEEPALIVE_PID=""
}

require_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        fail "This script requires 'sudo' (run on a system with sudo configured). Line: ${LINENO}"
    fi
    # Prompt once up front (better UX than failing mid-build).
    sudo -v || fail "Unable to validate sudo credentials. Line: ${LINENO}"
    # Then keep that credential fresh so the long build never re-prompts.
    sudo_keepalive_start
}

fail() {
    printf '\n' >&2
    printf '%s[ERROR]%s %s\n' "$RED" "$NC" "$1" >&2
    printf '\n' >&2
    printf '%s[INFO]%s For help or to report a bug create an issue at: https://github.com/slyfox1186/ffmpeg-build-script/issues\n' "$GREEN" "$NC" >&2
    if [[ "${GOOGLE_SPEECH:-false}" == "true" ]] && command -v google_speech >/dev/null 2>&1; then
        google_speech "Build failed. $1" >/dev/null 2>&1 || true
    fi
    exit 1
}

command_not_found_handle() {
    fail "Command or function not found: $1"
}

exit_fn() {
    local ffmpeg_full_path="/usr/local/bin/ffmpeg"
    local version_line hardware_accels
    local encoder_count decoder_count filter_count
    local -a installed_tools=()
    local tool

    [[ -x "$ffmpeg_full_path" ]] ||
        fail "The build completed, but $ffmpeg_full_path is missing or not executable."

    version_line="$("$ffmpeg_full_path" -version 2>/dev/null | sed -n '1p')"
    encoder_count="$("$ffmpeg_full_path" -hide_banner -encoders 2>/dev/null | awk '/^[[:space:]][A-Z.]{6}[[:space:]]/ {count++} END {print count + 0}')"
    decoder_count="$("$ffmpeg_full_path" -hide_banner -decoders 2>/dev/null | awk '/^[[:space:]][A-Z.]{6}[[:space:]]/ {count++} END {print count + 0}')"
    filter_count="$("$ffmpeg_full_path" -hide_banner -filters 2>/dev/null | awk '/^[[:space:]][.A-Z|]{3}[[:space:]]/ {count++} END {print count + 0}')"
    hardware_accels="$(
        "$ffmpeg_full_path" -hide_banner -hwaccels 2>/dev/null |
            tail -n +2 |
            paste -sd ',' - |
            sed 's/,/, /g'
    )"
    hardware_accels="${hardware_accels:-none reported}"

    for tool in ffmpeg ffprobe ffplay; do
        [[ -x "/usr/local/bin/$tool" ]] && installed_tools+=("$tool")
    done

    printf '\n'
    box_out_banner "FFmpeg build completed successfully"
    printf '\n%s✓ Version:%s %s\n' "$GREEN" "$NC" "${version_line:-unknown}"
    printf '%s✓ Installation:%s /usr/local/bin\n' "$GREEN" "$NC"
    printf '%s✓ Installed tools:%s %s\n' "$GREEN" "$NC" "${installed_tools[*]:-none}"
    printf '%s✓ Encoders / decoders / filters:%s %s / %s / %s\n' \
        "$GREEN" "$NC" "$encoder_count" "$decoder_count" "$filter_count"
    printf '%s✓ Reported hardware accelerators:%s %s\n\n' "$GREEN" "$NC" "$hardware_accels"

    exit 0
}

# Desktop notification on failure. notify-send is an optional dependency (libnotify-bin
# is not in the apt package list); calling it unguarded triggers command_not_found_handle
# on headless systems, which prints a misleading "[ERROR] Command or function not found:
# notify-send" right before the real failure message.
notify_failure() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -t 5000 "$1" 2>/dev/null || true
    fi
}

# Execution function with error handling
# NOTE on exit-code capture: bash sets `$?` to the result of `! cmd` (the
# negation), not `cmd` itself. So `if ! "$@"; then exit_code=$?` always
# captures 0. We run the command first, save `$?` immediately, and only
# then test/branch. The debug pipeline snapshots both `PIPESTATUS` entries
# immediately and reports the command failure first, or a `tee`/log failure
# when the command itself succeeded.
execute() {
    (($# > 0)) || fail "execute() called without a command. Line: ${LINENO}"

    local command_display exit_code start_pos
    local -a pipeline_status=()
    command_display="$(format_command "$@")"
    printf '$'
    printf ' %q' "$@"
    printf '\n'

    if [[ "$debug" == "ON" ]]; then
        if [[ -n "${log_file:-}" ]]; then
            "$@" 2>&1 | tee -a "$log_file"
            pipeline_status=("${PIPESTATUS[@]}")
            if ((pipeline_status[0] != 0)); then
                exit_code=${pipeline_status[0]}
            else
                exit_code=${pipeline_status[1]}
            fi
        else
            if "$@"; then
                exit_code=0
            else
                exit_code=$?
            fi
        fi
    elif [[ -n "${log_file:-}" ]]; then
        start_pos="$(wc -c <"$log_file" 2>/dev/null || printf '0\n')"
        if "$@" >>"$log_file" 2>&1; then
            exit_code=0
        else
            exit_code=$?
            printf '\n' >&2
            if [[ -f "$log_file" && "$start_pos" =~ ^[0-9]+$ ]]; then
                tail -c "+$((start_pos + 1))" "$log_file" >&2 || true
            fi
        fi
    elif "$@"; then
        exit_code=0
    else
        exit_code=$?
    fi

    if (( exit_code != 0 )); then
        notify_failure "Command failed: $command_display"
        fail "Command failed with exit code $exit_code: $command_display"
    fi
}

workspace_pkgconf_modules_ready() {
    local module prefix pc_file_dir workspace_resolved

    require_vars workspace
    command -v pkgconf >/dev/null 2>&1 || return 1
    workspace_resolved="$(canonicalize_path "$workspace")" || return 1
    for module in "$@"; do
        pkgconf --exists "$module" 2>/dev/null || return 1
        prefix="$(pkgconf --variable=prefix "$module" 2>/dev/null || true)"
        if [[ -n "$prefix" ]]; then
            [[ "$(canonicalize_path "$prefix" 2>/dev/null || true)" == "$workspace_resolved" ]] ||
                return 1
            continue
        fi

        # Some valid upstream metadata, including SoXR 0.1.3's soxr.pc,
        # contains absolute Libs/Cflags paths but defines no prefix variable.
        # In that case, require the resolved metadata file itself to live
        # inside the workspace so a system module cannot satisfy the marker.
        pc_file_dir="$(pkgconf --variable=pcfiledir "$module" 2>/dev/null || true)"
        [[ -n "$pc_file_dir" ]] || return 1
        path_is_within "$pc_file_dir" "$workspace_resolved" || return 1
    done
}

package_artifacts_ready() {
    local package_name="${1:-}"
    local module_name

    require_vars workspace
    case "$package_name" in
        m4) [[ -x "$workspace/bin/m4" ]] ;;
        autoconf) [[ -x "$workspace/bin/autoconf" ]] ;;
        automake) [[ -x "$workspace/bin/automake" ]] ;;
        libtool) [[ -x "$workspace/bin/libtoolize" ]] ;;
        pkgconf) [[ -x "$workspace/bin/pkgconf" ]] ;;
        cmake) [[ -x "$workspace/bin/cmake" ]] ;;
        meson) [[ -x "$workspace/python_virtual_environment/build-tools/bin/meson" ]] ;;
        ninja) [[ -x "$workspace/bin/ninja" ]] ;;
        ant-git) [[ -x "$workspace/ant/bin/ant" ]] ;;
        mediainfo-cli) [[ -x "$workspace/bin/mediainfo" ]] ;;
        gpac-git) [[ -x "$workspace/bin/MP4Box" || -x "$workspace/bin/gpac" ]] ;;
        yasm) [[ -x "$workspace/bin/yasm" ]] ;;
        nasm) [[ -x "$workspace/bin/nasm" ]] ;;
        giflib) [[ -f "$workspace/lib/libgif.a" ]] ;;
        libiconv) [[ -f "$workspace/lib/libiconv.a" || -f "$workspace/lib64/libiconv.a" ]] ;;
        gmp) [[ -f "$workspace/lib/libgmp.a" || -f "$workspace/lib64/libgmp.a" ]] ;;
        liblame) [[ -f "$workspace/lib/libmp3lame.a" || -f "$workspace/lib64/libmp3lame.a" ]] ;;
        libtheora)
            [[ -f "$workspace/lib/libtheoraenc.a" || -f "$workspace/lib64/libtheoraenc.a" ]]
            ;;
        opencl-sdk-git)
            [[ -f "$workspace/include/CL/cl.h" ]] &&
                [[ -f "$workspace/lib/libOpenCL.a" || -f "$workspace/lib64/libOpenCL.a" ]]
            ;;
        vulkan-headers-git) [[ -f "$workspace/include/vulkan/vulkan.h" ]] ;;
        lv2-git) [[ -f "$workspace/include/lv2.h" || -d "$workspace/include/lv2" ]] ;;
        opencore-amr)
            workspace_pkgconf_modules_ready opencore-amrnb opencore-amrwb
            ;;
        nettle) workspace_pkgconf_modules_ready nettle hogweed ;;
        brotli)
            workspace_pkgconf_modules_ready libbrotlicommon libbrotlidec libbrotlienc
            ;;
        freeglut)
            workspace_pkgconf_modules_ready glut ||
                workspace_pkgconf_modules_ready freeglut
            ;;
        vorbis) workspace_pkgconf_modules_ready vorbis vorbisenc ;;
        lilv) workspace_pkgconf_modules_ready lilv-0 ;;
        av1-git) workspace_pkgconf_modules_ready aom ;;
        libvmaf) workspace_pkgconf_modules_ready libvmaf ;;
        rav1e) workspace_pkgconf_modules_ready rav1e ;;
        zimg-git) workspace_pkgconf_modules_ready zimg ;;
        x264) workspace_pkgconf_modules_ready x264 ;;
        x265) workspace_pkgconf_modules_ready x265 ;;
        nv-codec-headers) workspace_pkgconf_modules_ready ffnvcodec ;;
        amf-headers) [[ -f "$workspace/include/AMF/core/Version.h" ]] ;;
        libgav1-git)
            [[ -f "$workspace/lib/libgav1.a" || -f "$workspace/lib64/libgav1.a" ]]
            ;;
        avisynth) [[ -f "$workspace/include/avisynth/avisynth_c.h" ||
                      -f "$workspace/include/avisynth_c.h" ]] ;;
        xvidcore) [[ -f "$workspace/lib/libxvidcore.a" && -f "$workspace/include/xvid.h" ]] ;;
        vapoursynth) vapoursynth_sdk_ready_for_ffmpeg ;;
        ffmpeg) [[ -x /usr/local/bin/ffmpeg && -x /usr/local/bin/ffprobe ]] ;;
        libzstd|librist|zlib|openssl|libxml2|libpng|libtiff|gnutls|freetype|fontconfig|harfbuzz|fribidi|libass|libwebp-git|libhwy|lcms2|gflags|libjpeg-turbo|rubberband-git|c-ares|serd|pcre2|zix|sord|sratom|jemalloc|libsoxr|sdl2|libsndfile|libogg|libfdk-aac|libopus|libmysofa|avif|kvazaar|libdvdread|udfread|zenlib|mediainfo-lib|vid-stab|srt|svt-av1|libheif|openjpeg)
            module_name="$package_name"
            case "$package_name" in
                libxml2) module_name=libxml-2.0 ;;
                libtiff) module_name=libtiff-4 ;;
                freetype) module_name=freetype2 ;;
                libwebp-git) module_name=libwebp ;;
                libjpeg-turbo) module_name=libjpeg ;;
                rubberband-git) module_name=rubberband ;;
                c-ares) module_name=libcares ;;
                serd) module_name=serd-0 ;;
                pcre2) module_name=libpcre2-8 ;;
                zix) module_name=zix-0 ;;
                sord) module_name=sord-0 ;;
                sratom) module_name=sratom-0 ;;
                libsoxr) module_name=soxr ;;
                sdl2) module_name=sdl2 ;;
                libsndfile) module_name=sndfile ;;
                libogg) module_name=ogg ;;
                libfdk-aac) module_name=fdk-aac ;;
                libopus) module_name=opus ;;
                avif) module_name=libavif ;;
                libdvdread) module_name=dvdread ;;
                udfread) module_name=libudfread ;;
                zenlib) module_name=libzen ;;
                mediainfo-lib) module_name=libmediainfo ;;
                vid-stab) module_name=vidstab ;;
                svt-av1) module_name=SvtAv1Enc ;;
                libheif) module_name=libheif ;;
                openjpeg) module_name=libopenjp2 ;;
            esac
            workspace_pkgconf_modules_ready "$module_name"
            ;;
        *)
            # Ancillary tools and transitive libraries without a stable public
            # artifact contract still rely on their atomic version marker.
            return 0
            ;;
    esac
}

# Build management functions
build() {
    local package_name package_version stripped_version prior_version
    package_name="${1:-}"
    package_version="${2:-}"

    if [[ -z "$package_name" ]]; then
        fail "build() called without a package name. Line: ${LINENO}"
    fi
    [[ "$package_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "build() received an invalid package name: '$package_name'. Line: ${LINENO}"
    require_vars packages

    # Disabled packages are checked FIRST so callers can skip version detection
    # entirely for them (fetch_version_if_enabled leaves the version empty) without
    # tripping the empty-version guard below.
    if ! package_enabled "$package_name"; then
        echo
        echo "$package_name is disabled by config${PACKAGE_SELECTION_CONFIG_FILE:+ ($PACKAGE_SELECTION_CONFIG_FILE)}."
        return 1
    fi

    # Empty versions lead to broken URLs like `foo-.tar.gz` and confusing rebuild logic.
    # Treat this as a hard error so the root cause (version detection) is fixed instead
    # of silently building the wrong thing.
    stripped_version="${package_version//[[:space:]]/}"
    [[ -n "$stripped_version" && "$package_version" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "build() called for \"$package_name\" with an invalid version '$package_version'. Line: ${LINENO}"

    echo
    printf '%sBuilding%s %s%s%s - %sversion %s%s%s\n' \
        "$GREEN" "$NC" "$YELLOW" "$package_name" "$NC" \
        "$GREEN" "$YELLOW" "$package_version" "$NC"
    echo "========================================================"

    prior_version="$(read_marker_version "$packages/$package_name.done" || true)"
    if [[ -n "$prior_version" ]]; then
        if ! package_artifacts_ready "$package_name"; then
            warn "$package_name has a build marker but its required workspace artifacts are missing; rebuilding."
            rm -f -- "$packages/$package_name.done" ||
                fail "Unable to remove stale marker for '$package_name'. Line: ${LINENO}"
            return 0
        fi
        if [[ "$prior_version" == "$package_version" ]]; then
            echo "$package_name version $package_version already built. Remove $packages/$package_name.done lockfile to rebuild it."
            return 1
        elif is_true "${LATEST:-false}"; then
            echo "$package_name is outdated and will be rebuilt with latest version $package_version"
            return 0
        else
            echo "$package_name is outdated, but will not be rebuilt. Pass in --latest to rebuild it or remove $packages/$package_name.done lockfile."
            return 1
        fi
    fi

    return 0
}

build_done() {
    local package_name="${1:-}"
    local package_version="${2:-}"
    local temp_file

    [[ "$package_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "build_done() received an invalid package name: '$package_name'. Line: ${LINENO}"
    [[ -n "${SUPPORTED_PACKAGES[$package_name]+x}" ]] ||
        fail "build_done() received unsupported package '$package_name'. Line: ${LINENO}"
    [[ "$package_version" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "build_done() received an invalid version for '$package_name'. Line: ${LINENO}"
    require_vars packages
    package_artifacts_ready "$package_name" ||
        fail "Refusing to mark '$package_name' complete because its required artifacts are missing. Line: ${LINENO}"
    mkdir -p "$packages" ||
        fail "Failed to create build-marker directory '$packages'. Line: ${LINENO}"

    temp_file="$(mktemp --tmpdir="$packages" ".${package_name}.done.XXXXXX")" ||
        fail "Failed to create a temporary build marker for '$package_name'. Line: ${LINENO}"
    if ! printf '%s\n' "$package_version" >"$temp_file"; then
        rm -f -- "$temp_file"
        fail "Failed to write the build marker for '$package_name'. Line: ${LINENO}"
    fi
    if ! mv -f -- "$temp_file" "$packages/$package_name.done"; then
        rm -f -- "$temp_file"
        fail "Failed to publish the build marker for '$package_name'. Line: ${LINENO}"
    fi
}

# Run a version fetcher only when its package is enabled. Disabled packages skip
# the upstream network round-trip entirely: repo_version is cleared so the
# following build() call takes its disabled-by-config path (build() checks
# package_enabled before validating the version). Returns the fetcher's status
# when it runs, 0 when skipped.
fetch_version_if_enabled() {
    local package_name="${1:-}"
    local prior_version
    [[ -n "$package_name" ]] || fail "fetch_version_if_enabled() called without a package name. Line: ${LINENO}"
    shift
    [[ $# -gt 0 ]] || fail "fetch_version_if_enabled() called without a fetch command. Line: ${LINENO}"

    repo_version=""
    package_enabled "$package_name" || return 0

    # A normal rerun intentionally reuses its recorded version without hitting
    # dozens of upstream services. --latest opts into network discovery. A few
    # packages transform upstream tag names before writing their marker and must
    # always use their dedicated parser.
    if ! is_true "${LATEST:-false}"; then
        prior_version="$(read_marker_version "$packages/$package_name.done" || true)"
        if [[ -n "$prior_version" ]]; then
            if package_artifacts_ready "$package_name"; then
                case "$package_name" in
                    m4)
                        if [[ "$prior_version" != "latest" ]]; then
                            repo_version="$prior_version"
                            return 0
                        fi
                        warn "Replacing legacy mutable m4 marker with a versioned release marker."
                        ;;
                    vapoursynth)
                        repo_version="${prior_version#R}"
                        return 0
                        ;;
                    ffmpeg)
                        repo_version="${prior_version#n}"
                        return 0
                        ;;
                    *)
                        repo_version="$prior_version"
                        return 0
                        ;;
                esac
            else
                warn "$package_name has a build marker but its required artifacts are missing; refreshing its version and source."
            fi
            rm -f -- "$packages/$package_name.done" ||
                fail "Unable to remove stale marker for '$package_name'. Line: ${LINENO}"
        fi
    fi

    "$@"
}

library_exists() {
    (($# > 0)) || return 1
    command -v pkgconf >/dev/null 2>&1 || return 1
    pkgconf --exists "$@" >/dev/null 2>&1
}

# True if the active C toolchain can locate the given header (e.g. "frei0r.h",
# "gsm/gsm.h"). Used to gate FFmpeg options for system libraries that ship a
# header/static lib but no pkg-config file, mirroring how FFmpeg's own configure
# detects them. No hardcoded include paths: the compiler's search path decides.
header_exists() {
    local header="${1:-}"
    local -a include_args=()

    [[ "$header" =~ ^[A-Za-z0-9_+./-]+$ ]] || return 1
    command -v "${CC:-cc}" >/dev/null 2>&1 || return 1
    [[ -z "${workspace:-}" ]] || include_args+=("-I$workspace/include")
    printf '#include <%s>\n' "$header" |
        "${CC:-cc}" "${include_args[@]}" -E -x c - >/dev/null 2>&1
}

# True if the Vulkan headers on the workspace include path meet FFmpeg 8.0's floor
# for --enable-vulkan (VK_HEADER_VERSION >= 277, or Vulkan 1.4+). This is the exact
# condition FFmpeg's own configure uses; most distros ship older headers, so the
# workspace gets newer ones from the Vulkan-Headers build.
vulkan_headers_recent() {
    printf '#include <vulkan/vulkan.h>\n#if !(defined(VK_VERSION_1_4) || (defined(VK_VERSION_1_3) && VK_HEADER_VERSION >= 277))\n#error vulkan headers too old\n#endif\n' \
        | "${CC:-cc}" -I"${workspace:-/nonexistent}/include" -E -x c - >/dev/null 2>&1
}

# True if the installed libplacebo provides PL_ALPHA_NONE. FFmpeg 8.1+'s
# vf_libplacebo.c uses this enum unconditionally, yet FFmpeg's configure only
# requires libplacebo >= 5.229.0 — too low: distro libplacebo 6.x (e.g. Ubuntu
# 24.04's 6.338.2) passes configure but fails to compile ("PL_ALPHA_NONE
# undeclared"); the enum arrived in libplacebo 7.x. Feature-test the actual symbol
# (a compile check, not a version guess) so --enable-libplacebo is gated precisely.
libplacebo_has_pl_alpha_none() {
    local cflags
    cflags="$(pkgconf --cflags libplacebo 2>/dev/null)" || return 1
    # shellcheck disable=SC2086
    printf '#include <libplacebo/colorspace.h>\nint chk(void){ return (int) PL_ALPHA_NONE; }\n' \
        | "${CC:-cc}" $cflags -fsyntax-only -x c - >/dev/null 2>&1
}

# Append $2 (e.g. "-lstdc++") to the Libs.private of the workspace pkg-config file
# named $1 (e.g. "libvmaf"), creating the line if absent. Idempotent. Some libraries
# bundle C++ sources but ship a .pc that omits the C++ runtime, which breaks a static
# link via the C compiler driver (undefined operator new/delete); this declares the
# dependency the way x265/zimg/rubberband already do so `pkg-config --static` emits it.
pkgconfig_add_private_lib() {
    local pc_name="${1:-}" extra_lib="${2:-}" pc_file="" dir private_line token

    [[ "$pc_name" =~ ^[A-Za-z0-9_.+-]+$ ]] ||
        fail "pkgconfig_add_private_lib() received an invalid module name. Line: ${LINENO}"
    [[ "$extra_lib" =~ ^-l[A-Za-z0-9_+.-]+$ ]] ||
        fail "pkgconfig_add_private_lib() received an invalid linker flag. Line: ${LINENO}"
    require_vars workspace

    for dir in "$workspace/lib/pkgconfig" "$workspace/lib64/pkgconfig" \
               "$workspace/lib/x86_64-linux-gnu/pkgconfig" "$workspace/share/pkgconfig"; do
        if [[ -f "$dir/$pc_name.pc" ]]; then
            pc_file="$dir/$pc_name.pc"
            break
        fi
    done
    if [[ -z "$pc_file" ]]; then
        warn "pkgconfig_add_private_lib: $pc_name.pc not found in workspace; skipping"
        return 0
    fi
    private_line="$(sed -n 's/^Libs\.private:[[:space:]]*//p' "$pc_file" | sed -n '1p')"
    for token in $private_line; do
        [[ "$token" == "$extra_lib" ]] && return 0
    done
    if grep -q '^Libs.private:' "$pc_file"; then
        execute sed -i "/^Libs.private:/ s|\$| $extra_lib|" "$pc_file"
    elif ! printf 'Libs.private: %s\n' "$extra_lib" >>"$pc_file"; then
        fail "Unable to update '$pc_file'. Line: ${LINENO}"
    fi
}

# File download and extraction
archive_filename_supported() {
    case "${1:-}" in
        *.tar|*.tar.bz2|*.tar.gz|*.tar.xz) return 0 ;;
        *) return 1 ;;
    esac
}

archive_output_directory() {
    local filename="${1:-}"

    case "$filename" in
        *.tar.bz2|*.tar.gz|*.tar.xz) printf '%s\n' "${filename%.tar.*}" ;;
        *.tar) printf '%s\n' "${filename%.tar}" ;;
        *) return 1 ;;
    esac
}

file_sha256() {
    local file="${1:-}"
    local checksum

    [[ -f "$file" && ! -L "$file" ]] || return 1
    [[ "$(stat -c '%h' "$file" 2>/dev/null || true)" == "1" ]] || return 1
    checksum="$(sha256sum -- "$file" 2>/dev/null | awk 'NR == 1 {print $1}')" || return 1
    [[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || return 1
    printf '%s\n' "$checksum"
}

archive_checksum_matches() {
    local archive="${1:-}"
    local checksum_file="${2:-${archive}.sha256}"
    local expected actual
    local -a checksum_lines=()

    [[ -f "$archive" && ! -L "$archive" ]] || return 1
    [[ -f "$checksum_file" && ! -L "$checksum_file" ]] || return 1
    [[ "$(stat -c '%h' "$checksum_file" 2>/dev/null || true)" == "1" ]] || return 1
    mapfile -t checksum_lines <"$checksum_file" || return 1
    ((${#checksum_lines[@]} == 1)) || return 1
    expected="${checksum_lines[0]}"
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || return 1
    actual="$(file_sha256 "$archive")" || return 1
    [[ "$actual" == "$expected" ]]
}

write_archive_checksum() {
    local archive="${1:-}"
    local checksum_file="${2:-${archive}.sha256}"
    local checksum checksum_directory temp_file

    checksum="$(file_sha256 "$archive")" || return 1
    checksum_directory="$(dirname -- "$checksum_file")"
    temp_file="$(mktemp --tmpdir="$checksum_directory" '.archive-sha256.XXXXXX')" ||
        return 1
    if ! printf '%s\n' "$checksum" >"$temp_file" ||
        ! chmod 0600 "$temp_file" ||
        ! mv -f -- "$temp_file" "$checksum_file"; then
        rm -f -- "$temp_file"
        return 1
    fi
}

# Validate that every member stays under one archive root. GNU tar already
# rejects absolute and parent-traversal member names while extracting; this
# preflight makes that safety property explicit and also guarantees that
# --strip-components=1 cannot silently produce an empty source directory.
validate_tar_archive() {
    local archive="${1:-}"
    local entry normalized top_component="" archive_listing
    local has_payload=false

    [[ -f "$archive" ]] || return 1
    archive_listing="$(tar -tf "$archive" 2>>"${log_file:-/dev/null}")" ||
        return 1

    while IFS= read -r entry; do
        [[ -n "$entry" ]] || continue
        [[ ! "$entry" =~ [[:cntrl:]] ]] || return 1
        normalized="${entry#./}"
        [[ -n "$normalized" && "$normalized" != /* ]] || return 1
        [[ "$normalized" != ".." && "$normalized" != ../* && "$normalized" != */../* && "$normalized" != */.. ]] ||
            return 1

        if [[ -z "$top_component" ]]; then
            top_component="${normalized%%/*}"
            top_component="${top_component%/}"
            [[ -n "$top_component" && "$top_component" != "." && "$top_component" != ".." ]] || return 1
        fi

        [[ "$normalized" == "$top_component" || "$normalized" == "$top_component/"* ]] || return 1
        [[ "$normalized" == */* && "$normalized" != "$top_component/" ]] && has_payload=true
    done <<<"$archive_listing"

    [[ "$has_payload" == "true" ]]
}

download_archive_to_cache() {
    local download_url="${1:-}"
    local download_file="${2:-}"
    local target_file="${3:-}"
    local checksum_file lock_fd="" temp_target_file numeric_value downloaded_size
    local download_connect_timeout download_max_time download_max_bytes
    local download_retry download_retry_delay download_lock_timeout
    local -a curl_args=()

    [[ "$download_url" == https://* ]] ||
        fail "Only HTTPS download URLs are accepted: '$download_url'. Line: ${LINENO}"
    [[ ! "$download_url" =~ [[:cntrl:]] ]] ||
        fail "Download URLs may not contain control characters. Line: ${LINENO}"

    checksum_file="$target_file.sha256"
    download_connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"
    download_max_time="${DOWNLOAD_MAX_TIME:-1800}"
    download_max_bytes="${DOWNLOAD_MAX_BYTES:-1073741824}"
    download_retry="${DOWNLOAD_RETRY:-5}"
    download_retry_delay="${DOWNLOAD_RETRY_DELAY:-5}"
    download_lock_timeout="${DOWNLOAD_LOCK_TIMEOUT:-1800}"

    for numeric_value in "$download_connect_timeout" "$download_max_time" "$download_max_bytes" \
        "$download_lock_timeout"; do
        [[ "$numeric_value" =~ ^[1-9][0-9]*$ ]] ||
            fail "Download size limits and timeouts must be positive integers. Line: ${LINENO}"
    done
    for numeric_value in "$download_retry" "$download_retry_delay"; do
        [[ "$numeric_value" =~ ^[0-9]+$ ]] ||
            fail "Download retry values must be non-negative integers. Line: ${LINENO}"
    done
    require_commands sha256sum

    if [[ -z "$_BUILD_ROOT_LOCK_FD" ]]; then
        if command -v flock >/dev/null 2>&1; then
            # Lock the already-validated package-cache directory itself. Opening a
            # separately named lock file would follow a malicious symlink before
            # Bash gives us a file descriptor to pass to flock.
            exec {lock_fd}<"$packages" ||
                fail "Unable to open the package cache for locking. Line: ${LINENO}"
            if ! flock -w "$download_lock_timeout" "$lock_fd"; then
                exec {lock_fd}>&-
                warn "Timed out waiting for the package-cache download lock: $download_file"
                return 1
            fi
        else
            warn "'flock' is unavailable; atomic cache writes remain safe, but duplicate concurrent downloads are possible."
        fi
    fi

    # Another process may have populated the cache while this process waited.
    if validate_tar_archive "$target_file"; then
        if archive_checksum_matches "$target_file" "$checksum_file"; then
            [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
            log "$download_file already exists and matches its SHA-256 cache record."
            return 0
        fi
        if [[ -e "$checksum_file" || -L "$checksum_file" ]]; then
            warn "Cached archive checksum mismatch; downloading a clean copy: $download_file"
        else
            warn "Cached archive has no trusted local checksum record; downloading a clean copy: $download_file"
        fi
    fi
    rm -f -- "$target_file" "$checksum_file" || {
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Unable to remove invalid cached archive state: $target_file"
        return 1
    }

    temp_target_file="$(mktemp --tmpdir="$packages" ".${download_file}.part.XXXXXX")" || {
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Failed to create a temporary download file for $download_file."
        return 1
    }

    curl_args=(
        --fail --silent --show-error --location
        --proto "=https" --proto-redir "=https"
        --tlsv1.2
        --retry "$download_retry" --retry-delay "$download_retry_delay"
        --retry-max-time "$download_max_time"
        --retry-connrefused --retry-all-errors
        --connect-timeout "$download_connect_timeout" --max-time "$download_max_time"
        --max-filesize "$download_max_bytes"
    )

    log "Downloading \"$download_url\" as \"$download_file\""
    if ! curl "${curl_args[@]}" --output "$temp_target_file" "$download_url" \
        2>>"${log_file:-/dev/null}"; then
        rm -f -- "$temp_target_file"
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Failed to download \"$download_file\"."
        return 1
    fi

    downloaded_size="$(stat -c '%s' "$temp_target_file" 2>/dev/null || true)"
    if [[ ! "$downloaded_size" =~ ^[0-9]+$ ||
        "$downloaded_size" -gt "$download_max_bytes" ]]; then
        rm -f -- "$temp_target_file"
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Downloaded \"$download_file\" exceeds the configured size limit."
        return 1
    fi

    if ! validate_tar_archive "$temp_target_file"; then
        rm -f -- "$temp_target_file"
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Downloaded \"$download_file\", but it is not a safe, valid single-root tar archive."
        return 1
    fi

    if ! mv -f -- "$temp_target_file" "$target_file"; then
        rm -f -- "$temp_target_file"
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        return 1
    fi
    if ! write_archive_checksum "$target_file" "$checksum_file"; then
        rm -f -- "$target_file" "$checksum_file"
        [[ -n "$lock_fd" ]] && exec {lock_fd}>&-
        warn "Unable to record the downloaded archive's SHA-256 checksum."
        return 1
    fi

    if [[ -n "$lock_fd" ]]; then
        exec {lock_fd}>&-
    fi
    return 0
}

extract_archive_transactionally() {
    local archive="${1:-}"
    local target_directory="${2:-}"
    local extraction_directory extracted_path link_path link_target resolved_link special_path

    extraction_directory="$(mktemp -d --tmpdir="$packages" ".extract.XXXXXX")" ||
        return 1

    if ! tar -xf "$archive" -C "$extraction_directory" --strip-components=1 \
        --no-same-owner --no-same-permissions --delay-directory-restore \
        >>"${log_file:-/dev/null}" 2>&1; then
        safe_remove_tree "$extraction_directory" "$packages"
        return 1
    fi

    if [[ -z "$(find "$extraction_directory" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
        safe_remove_tree "$extraction_directory" "$packages"
        return 1
    fi

    while IFS= read -r -d '' extracted_path; do
        if [[ "$extracted_path" =~ [[:cntrl:]] ]]; then
            safe_remove_tree "$extraction_directory" "$packages"
            return 1
        fi
    done < <(find "$extraction_directory" -mindepth 1 -print0 2>/dev/null)

    # Validate link targets after the full tree exists so chained symlinks are
    # resolved accurately. Absolute/out-of-tree links and special filesystem
    # objects have no place in a source archive used by this build.
    while IFS= read -r -d '' link_path; do
        link_target="$(readlink -- "$link_path")" || {
            safe_remove_tree "$extraction_directory" "$packages"
            return 1
        }
        if [[ "$link_target" == /* || "$link_target" =~ [[:cntrl:]] ]]; then
            safe_remove_tree "$extraction_directory" "$packages"
            return 1
        fi
        resolved_link="$(canonicalize_path "$link_path")" || {
            safe_remove_tree "$extraction_directory" "$packages"
            return 1
        }
        if [[ "$resolved_link" != "$extraction_directory" &&
            "$resolved_link" != "$extraction_directory"/* ]]; then
            safe_remove_tree "$extraction_directory" "$packages"
            return 1
        fi
    done < <(find "$extraction_directory" -type l -print0 2>/dev/null)

    special_path="$(
        find "$extraction_directory" -mindepth 1 \
            ! -type d ! -type f ! -type l -print -quit 2>/dev/null
    )" || {
        safe_remove_tree "$extraction_directory" "$packages"
        return 1
    }
    if [[ -n "$special_path" ]]; then
        safe_remove_tree "$extraction_directory" "$packages"
        return 1
    fi

    safe_remove_tree "$target_directory" "$packages"
    if ! mv -- "$extraction_directory" "$target_directory"; then
        safe_remove_tree "$extraction_directory" "$packages"
        return 1
    fi
}

download_try() {
    local download_url="${1:-}"
    local download_file="${2:-}"
    local output_directory target_file target_directory

    require_vars packages
    [[ -n "$download_url" ]] || fail "Download URL is required. Line: ${LINENO}"
    download_file="${download_file:-${download_url##*/}}"
    download_file="${download_file%%\?*}"

    [[ "$download_file" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "Invalid download filename: '$download_file'. Line: ${LINENO}"
    archive_filename_supported "$download_file" ||
        fail "Unsupported archive format: '$download_file'. Line: ${LINENO}"

    output_directory="$(archive_output_directory "$download_file")" ||
        fail "Unable to derive extraction directory from '$download_file'. Line: ${LINENO}"
    target_file="$packages/$download_file"
    target_directory="$packages/$output_directory"
    mkdir -p "$packages" ||
        fail "Unable to create package cache '$packages'. Line: ${LINENO}"

    download_archive_to_cache "$download_url" "$download_file" "$target_file" || return 1

    if ! extract_archive_transactionally "$target_file" "$target_directory"; then
        rm -f -- "$target_file" "$target_file.sha256" ||
            fail "Unable to remove invalid cached archive '$target_file'. Line: ${LINENO}"
        warn "Failed to extract \"$download_file\" safely; the cached archive was removed."
        return 1
    fi

    log "File extracted: $download_file"
    cd "$target_directory" || return 1
}

download() {
    if ! download_try "$@"; then
        fail "Failed to download and extract \"$1\". Line: ${LINENO}"
    fi
}

# Download with fallback mirror support.
# This is a wrapper around `download` that prefers the primary URL but falls back
# to a secondary mirror if the primary download fails.
download_with_fallback() {
    local primary_url="${1:-}"
    local fallback_url="${2:-}"
    local archive_file

    if [[ -z "$primary_url" || -z "$fallback_url" ]]; then
        fail "Primary and fallback URLs are required. Line: ${LINENO}"
    fi

    archive_file="${primary_url##*/}"
    archive_file="${archive_file%%\?*}"

    # Try primary mirror first. If it fails, retry using the fallback mirror.
    log "Attempting download from primary mirror: $primary_url"
    if download_try "$primary_url" "$archive_file"; then
        return 0
    fi

    warn "Primary mirror failed, trying fallback mirror: $fallback_url"
    if download_try "$fallback_url" "$archive_file"; then
        return 0
    fi

    fail "Failed to download from both primary and fallback mirrors. Line: ${LINENO}"
}

# Git repository management. The repo name doubles as the package name for every
# caller, so disabled packages skip the ls-remote/clone round-trip here and the
# empty version routes the following build() call to its disabled-by-config path.
git_caller() {
    local clone_mode="${3:-shallow}"
    local prior_version source_commit source_directory

    git_url="${1:-}"
    repo_name="${2:-}"

    [[ "$git_url" == https://* ]] ||
        fail "git_caller() requires an HTTPS repository URL. Line: ${LINENO}"
    [[ ! "$git_url" =~ [[:cntrl:]] ]] ||
        fail "git_caller() repository URL contains control characters. Line: ${LINENO}"
    [[ "$repo_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "git_caller() received an invalid repository name: '$repo_name'. Line: ${LINENO}"
    case "$clone_mode" in
        shallow|recurse|full) ;;
        *) fail "Unsupported git clone mode '$clone_mode' for $repo_name. Line: ${LINENO}" ;;
    esac

    require_vars packages
    if ! package_enabled "$repo_name"; then
        version=""
        return 0
    fi

    prior_version="$(read_marker_version "$packages/$repo_name.done" || true)"
    source_directory="$packages/$repo_name"
    # Historical releases recorded human labels for mutable Git snapshots.
    # Only a commit-shaped marker is trustworthy enough to reuse.
    if [[ "$prior_version" =~ ^[0-9a-fA-F]{12,64}$ ]] &&
        ! is_true "${LATEST:-false}"; then
        source_commit="$(git -C "$source_directory" rev-parse HEAD 2>/dev/null || true)"
        if [[ "$source_commit" =~ ^[0-9a-fA-F]{40,64}$ &&
            "$source_commit" == "$prior_version"* ]] &&
            package_artifacts_ready "$repo_name"; then
            version="$prior_version"
            return 0
        fi
        warn "Git marker for '$repo_name' has no matching source checkout or is missing required artifacts; refreshing the snapshot."
        rm -f -- "$packages/$repo_name.done" ||
            fail "Unable to remove stale Git marker for '$repo_name'. Line: ${LINENO}"
    fi
    if [[ -n "$prior_version" &&
        ! "$prior_version" =~ ^[0-9a-fA-F]{12,64}$ ]]; then
        warn "Replacing legacy non-commit marker for Git snapshot '$repo_name'."
        rm -f -- "$packages/$repo_name.done" ||
            fail "Unable to remove legacy marker for '$repo_name'. Line: ${LINENO}"
    fi

    version="$(git_clone "$git_url" "$repo_name" "$clone_mode")"
}

git_clone() {
    local repo_url="${1:-}"
    local repo_name="${2:-}"
    local clone_mode="${3:-shallow}"
    local target_directory clone_parent clone_directory remote_commit actual_commit prior_version source_commit
    local git_timeout clone_timeout diagnostic_sink
    local -a clone_args=(
        env GIT_TERMINAL_PROMPT=0
        git
        -c protocol.allow=never
        -c protocol.https.allow=always
        clone --quiet
    )

    require_vars packages
    require_commands git timeout
    [[ "$repo_url" == https://* && ! "$repo_url" =~ [[:cntrl:]] ]] ||
        fail "git_clone() requires a valid HTTPS repository URL. Line: ${LINENO}"
    [[ "$repo_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] ||
        fail "git_clone() received an invalid repository name. Line: ${LINENO}"
    git_timeout="${GIT_OPERATION_TIMEOUT:-120}"
    clone_timeout="${GIT_CLONE_TIMEOUT:-1800}"
    [[ "$git_timeout" =~ ^[1-9][0-9]*$ && "$clone_timeout" =~ ^[1-9][0-9]*$ ]] ||
        fail "Git timeout values must be positive integers. Line: ${LINENO}"

    remote_commit="$(
        timeout --foreground "$git_timeout" env GIT_TERMINAL_PROMPT=0 \
            git -c protocol.allow=never -c protocol.https.allow=always \
            ls-remote "$repo_url" HEAD 2>/dev/null |
            awk 'NR == 1 {print $1}'
    )"
    [[ "$remote_commit" =~ ^[0-9a-fA-F]{40,64}$ ]] ||
        fail "Failed to resolve the HEAD commit for '$repo_url'. Line: ${LINENO}"

    target_directory="$packages/$repo_name"
    prior_version="$(read_marker_version "$packages/$repo_name.done" || true)"
    if [[ "$prior_version" =~ ^[0-9a-fA-F]{7,64}$ && "$remote_commit" == "$prior_version"* ]]; then
        source_commit="$(git -C "$target_directory" rev-parse HEAD 2>/dev/null || true)"
        if [[ "$source_commit" == "$remote_commit" ]] &&
            package_artifacts_ready "$repo_name"; then
            printf '%s\n' "$remote_commit"
            return 0
        fi
        warn "$repo_name is current remotely, but its source checkout or required artifacts are incomplete; cloning it again."
    fi

    clone_parent="$(mktemp -d --tmpdir="$packages" ".clone-${repo_name}.XXXXXX")" ||
        fail "Failed to create a temporary clone directory for $repo_name. Line: ${LINENO}"
    clone_directory="$clone_parent/repository"
    diagnostic_sink="${log_file:-/dev/stderr}"

    case "$clone_mode" in
        shallow)
            clone_args+=(--depth 1)
            ;;
        recurse)
            clone_args+=(--depth 1 --recurse-submodules --shallow-submodules)
            ;;
        full)
            ;;
        *)
            safe_remove_tree "$clone_parent" "$packages"
            fail "Unsupported git clone mode '$clone_mode'. Line: ${LINENO}"
            ;;
    esac
    clone_args+=(-- "$repo_url" "$clone_directory")

    if ! timeout --foreground "$clone_timeout" "${clone_args[@]}" 2>>"$diagnostic_sink"; then
        safe_remove_tree "$clone_parent" "$packages"
        warn "Failed to clone \"$repo_url\"; retrying once."
        clone_parent="$(mktemp -d --tmpdir="$packages" ".clone-${repo_name}.XXXXXX")" ||
            fail "Failed to create a retry directory for $repo_name. Line: ${LINENO}"
        clone_directory="$clone_parent/repository"
        clone_args[${#clone_args[@]} - 1]="$clone_directory"
        if ! timeout --foreground "$clone_timeout" "${clone_args[@]}" 2>>"$diagnostic_sink"; then
            safe_remove_tree "$clone_parent" "$packages"
            fail "Failed to clone \"$repo_url\" after two attempts. Line: ${LINENO}"
        fi
    fi

    actual_commit="$(git -C "$clone_directory" rev-parse HEAD 2>/dev/null || true)"
    [[ "$actual_commit" =~ ^[0-9a-fA-F]{40,64}$ ]] || {
        safe_remove_tree "$clone_parent" "$packages"
        fail "Cloned '$repo_url', but its checked-out commit could not be verified. Line: ${LINENO}"
    }

    # The branch can advance between ls-remote and clone. Record the commit that
    # was actually built so the marker is truthful and the next --latest run can
    # compare it with the then-current remote HEAD.
    if [[ "$actual_commit" != "$remote_commit" ]]; then
        warn "$repo_name advanced during clone; recording checked-out commit ${actual_commit:0:12}."
    fi

    safe_remove_tree "$target_directory" "$packages"
    if ! mv -- "$clone_directory" "$target_directory"; then
        safe_remove_tree "$clone_parent" "$packages"
        fail "Failed to publish the completed clone for $repo_name. Line: ${LINENO}"
    fi
    safe_remove_tree "$clone_parent" "$packages"

    printf '%s\n' "$actual_commit"
}

# Repository version fetching
gnu_repo() {
    local repo
    repo=$1
    repo_version=""
    local connect_timeout
    # Use longer timeout for version detection (some servers like freedesktop.org are slow)
    connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"

    # Input validation
    if [[ -z "$repo" ]]; then
        fail "Repository URL is required. Line: ${LINENO}"
    fi

    # Validate URL format
    if [[ ! "$repo" =~ ^https://[a-zA-Z0-9._/-]+\.[a-zA-Z0-9._/-]*$ ]]; then
        fail "Invalid repository URL format: $repo. Line: ${LINENO}"
    fi

    # Prefer a mirror (ibiblio), fall back to another mirror (team-cymru).
    local primary_repo="$repo"
    local ibiblio_repo cymru_repo
    local version_result="" url cand

    if [[ "$primary_repo" =~ ^https?://(ftp\.gnu\.org|mirror\.team-cymru\.com|mirrors\.ibiblio\.org)/gnu/ ]]; then
        ibiblio_repo="${primary_repo/ftp.gnu.org\/gnu/mirrors.ibiblio.org\/gnu}"
        ibiblio_repo="${ibiblio_repo/mirror.team-cymru.com\/gnu/mirrors.ibiblio.org\/gnu}"

        cymru_repo="${primary_repo/ftp.gnu.org\/gnu/mirror.team-cymru.com\/gnu}"
        cymru_repo="${cymru_repo/mirrors.ibiblio.org\/gnu/mirror.team-cymru.com\/gnu}"
    else
        ibiblio_repo="$primary_repo"
        cymru_repo=""
    fi

    # Deduplicate candidate URLs using an associative array
    local -A seen_urls=()
    local -a candidates=()
    local include_primary=true
    [[ "$primary_repo" =~ ^https?://ftp\.gnu\.org/gnu/ ]] && include_primary=false

    for cand in "$ibiblio_repo" "$cymru_repo"; do
        [[ -n "$cand" ]] || continue
        [[ -z "${seen_urls[$cand]+x}" ]] || continue
        seen_urls[$cand]=1
        candidates+=("$cand")
    done
    if [[ "$include_primary" == "true" && -z "${seen_urls[$primary_repo]+x}" ]]; then
        candidates+=("$primary_repo")
    fi

    for url in "${candidates[@]}"; do
        if [[ "$url" =~ libtool ]]; then
            version_result=$(curl_https -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'libtool-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | sed -n '1p')
        elif [[ "$url" =~ m4 ]]; then
            version_result=$(curl_https -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'm4-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | sed -n '1p')
        elif [[ "$url" =~ autoconf ]]; then
            version_result=$(curl_https -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'autoconf-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | sed -n '1p')
        elif [[ "$url" =~ libiconv ]]; then
            version_result=$(curl_https -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'libiconv-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.gz)' | sort -Vr | sed -n '1p')
        else
            version_result=$(curl_https -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP '[a-z]+-\K\d+\.\d+(?:\.\d+)?(?=\.(tar\.gz|tar\.bz2|tar\.xz))' | sort -Vr | sed -n '1p')
        fi

        # Normalize/validate to avoid whitespace-only or control-char results.
        version_result="$(printf '%s' "$version_result" | tr -d '\r' | sed -n '1p')"
        if [[ -n "${version_result//[[:space:]]/}" ]] && [[ "$version_result" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]]; then
            repo_version="$version_result"
            return 0
        fi
    done

    fail "Failed to detect latest version from $repo (tried: ${candidates[*]}). Line: ${LINENO}"
}

github_repo() {
    local repo="${1:-}"
    local url="${2:-releases}"
    local url_flag="${3:-1}"
    local selected_version index tag_names
    repo_version=""

    # Input validation to prevent injection
    if [[ -z "$repo" || -z "$url" ]]; then
        fail "Git repository and URL are required. Line: ${LINENO}"
    fi

    # Validate repository name format (only allow alphanumeric, dots, hyphens, forward slashes)
    if [[ ! "$repo" =~ ^[a-zA-Z0-9._/-]+$ ]]; then
        fail "Invalid repository name format: $repo. Line: ${LINENO}"
    fi

    # Validate URL parameter (only allow alphanumeric, hyphens, forward slashes)
    if [[ ! "$url" =~ ^[a-zA-Z0-9/-]+$ ]]; then
        fail "Invalid URL parameter: $url. Line: ${LINENO}"
    fi

    index=1
    if [[ "$url_flag" =~ ^[0-9]+$ ]] && [[ "$url_flag" -gt 0 ]]; then
        index="$url_flag"
    fi

    case "$url" in
        tags|releases) ;;
        *) fail "Unsupported GitHub ref source \"$url\". Line: ${LINENO}" ;;
    esac

    tag_names="$(git_remote_tag_names "https://github.com/$repo.git")" ||
        fail "Failed to fetch tags for GitHub repository '$repo'. Line: ${LINENO}"
    selected_version="$(run_github_version_helper "$repo" "$url" "v" "" '^[0-9]+(\.[0-9]+){1,3}$' "$index" "$tag_names" ||
                        run_github_version_helper "$repo" "$url" "" "" '^[0-9]+(\.[0-9]+){1,3}$' "$index" "$tag_names" ||
                        true)"
    if [[ -z "${selected_version//[[:space:]]/}" ]]; then
        fail "Failed to detect a usable version for GitHub repo \"$repo\" (url=$url). Line: ${LINENO}"
    fi

    repo_version="$selected_version"
}

###################################################################################
# Unified Version Extraction Functions
# These replace repetitive per-repo functions with parameterized, robust versions
###################################################################################

git_remote_tag_names() {
    local repo_url="${1:-}"
    local git_timeout="${GIT_OPERATION_TIMEOUT:-120}"

    [[ "$repo_url" == https://* ]] || return 1
    [[ "$git_timeout" =~ ^[1-9][0-9]*$ ]] || return 1
    require_commands git timeout

    timeout --foreground "$git_timeout" env GIT_TERMINAL_PROMPT=0 \
        git -c protocol.allow=never -c protocol.https.allow=always \
        ls-remote --tags --refs "$repo_url" 2>/dev/null |
        awk -F'refs/tags/' 'NF == 2 {print $2}'
}

run_github_version_helper() {
    local repo="${1:-}"
    local url_type="${2:-tags}"
    local prefix="${3-}"
    local exclude_pattern="${4:-}"
    local version_regex="${5:-}"
    local index="${6:-1}"
    local tag_names="${7:-}"
    local version

    [[ -n "$repo" ]] || fail "run_github_version_helper() called without a repo. Line: ${LINENO}"

    if [[ -z "$version_regex" ]]; then
        version_regex='^[0-9]+(\.[0-9]+){1,3}$'
    fi

    if [[ ! "$index" =~ ^[0-9]+$ ]] || [[ "$index" -lt 1 ]]; then
        index=1
    fi

    case "$url_type" in
        tags|releases) ;;
        *)
            return 1
            ;;
    esac

    if [[ -z "$tag_names" ]]; then
        tag_names="$(git_remote_tag_names "https://github.com/$repo.git")" || return 1
    fi
    version="$(
        printf '%s\n' "$tag_names" |
            select_prefixed_version "$prefix" "$exclude_pattern" "$version_regex" "$index"
    )" || return 1

    if [[ -n "$version_regex" ]] && [[ ! "$version" =~ $version_regex ]]; then
        return 1
    fi

    printf '%s\n' "$version"
}

select_prefixed_version() {
    local prefix=$1
    local exclude_pattern=$2
    local version_regex=$3
    local index=${4:-1}
    local ref version
    local -a versions=()

    while IFS= read -r ref; do
        [[ -n "$ref" && "$ref" != "null" ]] || continue

        if [[ -n "$exclude_pattern" ]] && [[ "$ref" =~ $exclude_pattern ]]; then
            continue
        fi

        if [[ -n "$prefix" ]]; then
            [[ "$ref" == "$prefix"* ]] || continue
            version="${ref#"$prefix"}"
        else
            version="$ref"
        fi

        [[ "$version" =~ $version_regex ]] || continue
        versions+=("$version")
    done

    [[ ${#versions[@]} -gt 0 ]] || return 1
    printf '%s\n' "${versions[@]}" | sort -ruV | sed -n "${index}p"
}

meson_project_option_exists() {
    local option_name="${1:-}"
    local options_file="${2:-}"

    [[ "$option_name" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || return 1
    if [[ -z "$options_file" ]]; then
        if [[ -f meson.options ]]; then
            options_file=meson.options
        else
            options_file=meson_options.txt
        fi
    fi
    [[ -f "$options_file" ]] || return 1
    grep -Eq "^[[:space:]]*option\\([\"']${option_name}[\"']" "$options_file"
}

append_meson_project_option_if_exists() {
    local target_array_name="${1:-}"
    local option_name="${2:-}"
    local option_value="${3:-}"
    local options_file="${4:-}"

    [[ -n "$target_array_name" ]] || fail "append_meson_project_option_if_exists() called without a target array. Line: ${LINENO}"
    [[ "$target_array_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] ||
        fail "append_meson_project_option_if_exists() received an invalid array name. Line: ${LINENO}"
    [[ -n "$option_name" ]] || fail "append_meson_project_option_if_exists() called without an option name. Line: ${LINENO}"
    [[ -n "$option_value" ]] || fail "append_meson_project_option_if_exists() called without an option value. Line: ${LINENO}"
    [[ "$(declare -p "$target_array_name" 2>/dev/null || true)" == "declare -a "* ]] ||
        fail "append_meson_project_option_if_exists() target is not an indexed array. Line: ${LINENO}"

    if meson_project_option_exists "$option_name" "$options_file"; then
        local -n target_array_ref="$target_array_name"
        target_array_ref+=("-D${option_name}=${option_value}")
    fi
}

find_vapoursynth_sdk_dir() {
    local header_path sdk_dir

    require_vars workspace

    while IFS= read -r header_path; do
        sdk_dir="${header_path%/include/VSScript4.h}"
        if [[ -f "$sdk_dir/include/VapourSynth4.h" ]]; then
            printf '%s\n' "$sdk_dir"
            return 0
        fi
    done < <(find "$workspace" -maxdepth 8 -type f -path '*/vapoursynth/include/VSScript4.h' 2>/dev/null | sort -V)

    return 1
}

vapoursynth_sdk_ready_for_ffmpeg() {
    require_vars workspace

    [[ -f "$workspace/include/vapoursynth/VSScript4.h" ]] || return 1
    [[ -f "$workspace/include/vapoursynth/VapourSynth4.h" ]] || return 1
    [[ -e "$workspace/lib/libvapoursynth-script.so" ]] || return 1
}

normalize_vapoursynth_sdk_for_ffmpeg() {
    local sdk_dir sdk_include sdk_pc pc_version libvsscript_so pc_file pc_temp

    require_vars workspace

    sdk_dir="$(find_vapoursynth_sdk_dir)" || return 1
    sdk_include="$sdk_dir/include"

    [[ -f "$sdk_include/VSScript4.h" ]] || return 1
    [[ -f "$sdk_include/VapourSynth4.h" ]] || return 1

    mkdir -p "$workspace/include/vapoursynth" "$workspace/lib" "$workspace/lib/pkgconfig" ||
        return 1
    cp -f "$sdk_include/"*.h "$workspace/include/vapoursynth/" || return 1

    while IFS= read -r lib_path; do
        cp -a "$lib_path" "$workspace/lib/" || return 1
    done < <(find "$sdk_dir" -maxdepth 1 \( -type f -o -type l \) \( -name 'libvsscript.so*' -o -name 'libvapoursynth.so*' \) 2>/dev/null | sort -V)

    libvsscript_so="$(find "$workspace/lib" -maxdepth 1 \( -type f -o -type l \) -name 'libvsscript.so*' 2>/dev/null | sort -V | sed -n '1p')"
    [[ -n "$libvsscript_so" ]] || return 1
    ln -sfn "$(basename "$libvsscript_so")" "$workspace/lib/libvapoursynth-script.so" ||
        return 1

    pc_version="unknown"
    sdk_pc="$sdk_dir/pkgconfig/vapoursynth.pc"
    if [[ -f "$sdk_pc" ]]; then
        pc_version="$(sed -n 's/^Version:[[:space:]]*//p' "$sdk_pc" | sed -n '1p')"
        [[ -n "$pc_version" ]] || pc_version="unknown"
    fi

    pc_file="$workspace/lib/pkgconfig/vapoursynth.pc"
    pc_temp="$(mktemp --tmpdir="$workspace/lib/pkgconfig" '.vapoursynth.pc.XXXXXX')" ||
        return 1
    if ! printf '%s\n' \
        "prefix=$workspace" \
        "includedir=\${prefix}/include" \
        "libdir=\${prefix}/lib" \
        '' \
        'Name: vapoursynth' \
        'Description: A frameserver for the 21st century' \
        "Version: $pc_version" \
        "Cflags: -I\${includedir}" \
        "Libs: -L\${libdir} -lvapoursynth-script" >"$pc_temp"; then
        rm -f -- "$pc_temp"
        return 1
    fi
    chmod 0644 "$pc_temp" || {
        rm -f -- "$pc_temp"
        return 1
    }
    mv -f -- "$pc_temp" "$pc_file" || {
        rm -f -- "$pc_temp"
        return 1
    }
}

# github_version - Unified GitHub version extractor
# Usage: github_version "owner/repo" [prefix] [exclude_pattern] [url_type] [version_regex] [index]
#   repo:            Repository path (e.g., "ninja-build/ninja")
#   prefix:          Tag prefix - "v" (default), "" (none), or custom (e.g., "lcms", "R")
#   exclude_pattern: Optional grep -v pattern (e.g., "rc|beta")
#   url_type:        "tags" (default) or "releases"
#   version_regex:   Optional regex applied after prefix removal
#   index:           Optional sorted match index (default 1)
# Sets: repo_version
github_version() {
    local repo="${1:-}"
    # Use ${2-v} not ${2:-v} so empty string "" is preserved, only unset defaults to "v"
    local prefix=${2-v}
    local exclude_pattern=${3:-}
    local url_type=${4:-tags}
    local version_regex="${5:-}"
    local index=${6:-1}
    local version
    repo_version=""

    if [[ -z "$version_regex" ]]; then
        version_regex='^[0-9]+(\.[0-9]+){1,3}$'
    fi

    case "$url_type" in
        tags|releases) ;;
        *)
            warn "github_version: Unsupported ref source \"$url_type\" for $repo"
            return 1
            ;;
    esac

    version="$(run_github_version_helper "$repo" "$url_type" "$prefix" "$exclude_pattern" "$version_regex" "$index" || true)"

    if [[ -z "$version" ]]; then
        warn "github_version: No version found for $repo (prefix='$prefix')"
        return 1
    fi

    repo_version="$version"
}

# gitlab_version - Unified GitLab version extractor
# Usage: gitlab_version "base_url" "project" [prefix] [separator] [version_regex] [index]
#   base_url:   GitLab instance (e.g., "https://gitlab.com", "https://code.videolan.org")
#   project:    Project path (e.g., "drobilla/zix", "AOMediaCodec/SVT-AV1")
#   prefix:     Tag prefix - "v" (default), "" (none), or custom (e.g., "VER-")
#   separator:  Version separator - "." (default) or "-"
#   version_regex: Optional regex applied after prefix removal
#   index:       Optional sorted match index (default 1)
# Sets: repo_version
gitlab_version() {
    local base_url="${1:-}"
    local project="${2:-}"
    # Use ${3-v} not ${3:-v} so empty string "" is preserved, only unset defaults to "v"
    local prefix=${3-v}
    local separator=${4:-.}
    local version_regex=${5:-}
    local index=${6:-1}
    local tag_names version
    repo_version=""

    if [[ -z "$version_regex" ]]; then
        case "$separator" in
            -) version_regex='^[0-9]+(-[0-9]+){2,3}$' ;;
            *) version_regex='^[0-9]+(\.[0-9]+){1,3}$' ;;
        esac
    fi

    [[ "$base_url" == https://* && "$project" =~ ^[A-Za-z0-9._/-]+$ ]] || return 1
    tag_names="$(git_remote_tag_names "$base_url/$project.git")" || {
        warn "gitlab_version: Failed to fetch tags for $project from $base_url"
        return 1
    }

    version="$(
        printf '%s\n' "$tag_names" |
            select_prefixed_version "$prefix" "" "$version_regex" "$index"
    )"

    if [[ -z "$version" ]]; then
        warn "gitlab_version: No version found for $project (prefix='$prefix', sep='$separator')"
        return 1
    fi

    repo_version="$version"
}

videolan_repo() {
    local project_id="${1:-}"
    local count="${2:-1}"
    local project tag_names

    [[ "$project_id" =~ ^[0-9]+$ && "$count" =~ ^[1-9][0-9]*$ ]] || return 1
    case "$project_id" in
        76) project="videolan/libdvdread" ;;
        206) project="videolan/libdvdnav" ;;
        363) project="videolan/libudfread" ;;
        *) return 1 ;;
    esac

    repo_version=""
    tag_names="$(git_remote_tag_names "https://code.videolan.org/$project.git")" || return 1
    repo_version="$(printf '%s\n' "$tag_names" | sort -ruV | sed -n "${count}p")"
    [[ -n "$repo_version" ]]
}

x264_version() {
    # x264 uses branches, not tags - get stable branch commit
    local full_commit
    local git_timeout="${GIT_OPERATION_TIMEOUT:-120}"

    repo_version=""
    [[ "$git_timeout" =~ ^[1-9][0-9]*$ ]] ||
        fail "GIT_OPERATION_TIMEOUT must be a positive integer. Line: ${LINENO}"
    require_commands git timeout
    full_commit="$(
        timeout --foreground "$git_timeout" env GIT_TERMINAL_PROMPT=0 \
            git -c protocol.allow=never -c protocol.https.allow=always ls-remote \
            "https://code.videolan.org/videolan/x264.git" refs/heads/stable 2>/dev/null |
            awk 'NR == 1 {print $1}'
    )"
    [[ "$full_commit" =~ ^[0-9a-fA-F]{40,64}$ ]] ||
        fail "Failed to detect x264 stable commit. Line: ${LINENO}"
    repo_version="$full_commit"
}

x265_version() {
    local tag_names

    repo_version=""
    tag_names="$(git_remote_tag_names "https://github.com/Multicorewareinc/x265.git")" ||
        return 1
    repo_version="$(
        printf '%s\n' "$tag_names" |
            select_prefixed_version "" 'alpha|beta|rc' '^[0-9]+(\.[0-9]+){1,2}$' 1
    )"
    [[ -n "$repo_version" ]]
}

nv_codec_headers_version() {
    github_version "FFmpeg/nv-codec-headers" "n" "" "tags" \
        '^[0-9]+(\.[0-9]+){3}$'
}

librist_repo_version() {
    gitlab_version "https://code.videolan.org" "rist/librist" "v"
}

freetype_release_version() {
    local connect_timeout max_time releases_html version

    repo_version=""
    connect_timeout="${FREEDESKTOP_RELEASE_CONNECT_TIMEOUT:-${DOWNLOAD_CONNECT_TIMEOUT:-2}}"
    max_time="${FREEDESKTOP_RELEASE_INDEX_MAX_TIME:-5}"

    if ! releases_html=$(curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
        "https://download.savannah.gnu.org/releases/freetype/" 2>/dev/null); then
        return 1
    fi

    version=$(
        printf '%s' "$releases_html" |
        grep -oE 'freetype-[0-9]+\.[0-9]+\.[0-9]+\.tar\.(xz|gz|bz2)' |
        sed -E 's/^freetype-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.(xz|gz|bz2)$/\1/' |
        sort -ruV |
        sed -n '1p'
    )

    if [[ -z "$version" ]]; then
        return 1
    fi

    repo_version="$version"
}

freetype_gitlab_version() {
    gitlab_version "https://gitlab.freedesktop.org" "freetype/freetype" \
        "VER-" "-" '^[0-9]+(-[0-9]+){2,3}$' "1"
}

freetype_version() {
    if freetype_release_version; then
        freetype_version_source="release"
        export freetype_version_source
        return 0
    fi

    warn "FreeType release archive is unavailable; trying FreeDesktop GitLab."
    if freetype_gitlab_version; then
        repo_version="${repo_version//-/.}"
        freetype_version_source="gitlab"
        export freetype_version_source
        return 0
    fi

    return 1
}

freetype_gitlab_archive_url() {
    local hyphen_version="${1:-}"

    [[ "$hyphen_version" =~ ^[0-9]+(-[0-9]+){2,3}$ ]] || return 1
    printf 'https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-%s/freetype-VER-%s.tar.bz2?ref_type=tags\n' \
        "$hyphen_version" "$hyphen_version"
}

freetype_release_archive_url() {
    local dotted_version="${1:-}"

    [[ "$dotted_version" =~ ^[0-9]+(\.[0-9]+){2,3}$ ]] || return 1
    printf 'https://download-mirror.savannah.gnu.org/releases/freetype/freetype-%s.tar.xz\n' "$dotted_version"
}

freetype_sourceforge_archive_url() {
    local dotted_version="${1:-}"

    [[ "$dotted_version" =~ ^[0-9]+(\.[0-9]+){2,3}$ ]] || return 1
    printf 'https://downloads.sourceforge.net/project/freetype/freetype2/%s/freetype-%s.tar.xz\n' \
        "$dotted_version" "$dotted_version"
}

fontconfig_release_version() {
    local connect_timeout max_time releases_html version

    repo_version=""
    connect_timeout="${FREEDESKTOP_RELEASE_CONNECT_TIMEOUT:-${DOWNLOAD_CONNECT_TIMEOUT:-2}}"
    max_time="${FREEDESKTOP_RELEASE_INDEX_MAX_TIME:-5}"

    if ! releases_html=$(curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
        "https://www.freedesktop.org/software/fontconfig/release/" 2>/dev/null); then
        return 1
    fi

    version=$(
        printf '%s' "$releases_html" |
        grep -oE 'fontconfig-[0-9]+\.[0-9]+\.[0-9]+\.tar\.(xz|gz|bz2)' |
        sed -E 's/^fontconfig-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.(xz|gz|bz2)$/\1/' |
        sort -ruV |
        sed -n '1p'
    )

    if [[ -z "$version" ]]; then
        return 1
    fi

    repo_version="$version"
}

fontconfig_gitlab_version() {
    gitlab_version "https://gitlab.freedesktop.org" "fontconfig/fontconfig" \
        "" "." '^[0-9]+(\.[0-9]+){1,3}$' "1"
}

fontconfig_version() {
    if fontconfig_release_version; then
        fontconfig_version_source="release"
        export fontconfig_version_source
        return 0
    fi

    warn "Fontconfig release archive is unavailable; trying FreeDesktop GitLab."
    if fontconfig_gitlab_version; then
        fontconfig_version_source="gitlab"
        export fontconfig_version_source
        return 0
    fi

    return 1
}

fontconfig_gitlab_archive_url() {
    local version="${1:-}"

    [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] || return 1
    printf 'https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/%s/fontconfig-%s.tar.gz\n' \
        "$version" "$version"
}

fontconfig_release_archive_url() {
    local version="${1:-}"

    [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] || return 1
    printf 'https://www.freedesktop.org/software/fontconfig/release/fontconfig-%s.tar.xz\n' "$version"
}

libxml2_version() {
    gitlab_version "https://gitlab.gnome.org" "GNOME/libxml2" "v"
}

libtiff_version() {
    gitlab_version "https://gitlab.com" "libtiff/libtiff" "v"
}

amf_version() {
    github_version "GPUOpen-LibrariesAndSDKs/AMF" "v" "" "releases"
}

avisynth_version() {
    github_version "AviSynth/AviSynthPlus" "v"
}

mediaarea_version() {
    local repo_name=$1
    github_version "$repo_name" "v"
}

svt_av1_version() {
    local index=${1:-1}
    gitlab_version "https://gitlab.com" "AOMediaCodec/SVT-AV1" "v" "." "" "$index"
}

vapoursynth_version() {
    github_version "vapoursynth/vapoursynth" "R" "[Rr][Cc]" "tags" '^[0-9]+$'
}

pkgconf_repo_version() {
    github_version "pkgconf/pkgconf" "pkgconf-"
}

sdl2_repo_version() {
    local release_page version
    local connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"
    local max_time="${VERSION_CHECK_MAX_TIME:-15}"
    repo_version=""

    release_page=$(curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
                        "https://www.libsdl.org/release/") || {
        warn "sdl2_repo_version: Failed to fetch SDL release archive"
        return 1
    }

    version=$(
        printf '%s' "$release_page" |
        grep -oE 'SDL2-[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz' |
        sed -E 's/^SDL2-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz$/\1/' |
        sort -uV |
        tail -n1
    )

    if [[ -z "$version" ]]; then
        warn "sdl2_repo_version: No SDL2 version found in SDL release archive"
        return 1
    fi

    repo_version="$version"
}

sdl2_download_url() {
    local version="${1:-}"

    [[ -n "$version" ]] || fail "sdl2_download_url() called without a version. Line: ${LINENO}"
    printf 'https://www.libsdl.org/release/SDL2-%s.tar.gz\n' "$version"
}

opencore_amr_version() {
    local release_page version
    local connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"
    local max_time="${VERSION_CHECK_MAX_TIME:-15}"

    repo_version=""
    release_page="$(
        curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
            "https://sourceforge.net/projects/opencore-amr/files/opencore-amr/"
    )" || return 1
    version="$(
        printf '%s' "$release_page" |
            grep -oE 'opencore-amr-[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz' |
            sed -E 's/^opencore-amr-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz$/\1/' |
            sort -ruV |
            sed -n '1p'
    )"
    [[ "$version" =~ ^[0-9]+(\.[0-9]+){2}$ ]] || return 1
    repo_version="$version"
}

xvidcore_version() {
    local release_page version
    local connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"
    local max_time="${VERSION_CHECK_MAX_TIME:-15}"

    repo_version=""
    release_page="$(
        curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
            "https://downloads.xvid.com/downloads/"
    )" || return 1
    version="$(
        printf '%s' "$release_page" |
            grep -oE 'xvidcore-[0-9]+\.[0-9]+\.[0-9]+\.tar\.bz2' |
            sed -E 's/^xvidcore-([0-9]+\.[0-9]+\.[0-9]+)\.tar\.bz2$/\1/' |
            sort -ruV |
            sed -n '1p'
    )"
    [[ "$version" =~ ^[0-9]+(\.[0-9]+){2}$ ]] || return 1
    repo_version="$version"
}

ffmpeg_repo_version() {
    github_version "FFmpeg/FFmpeg" "n"
}

rav1e_repo_version() {
    github_version "xiph/rav1e" "v" 'alpha|beta|rc' "releases" \
        '^[0-9]+(\.[0-9]+){1,3}$'
}

rav1e_download_url() {
    local version="${1:-}"

    [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] ||
        fail "rav1e_download_url() received an invalid release version: '$version'. Line: ${LINENO}"
    printf 'https://github.com/xiph/rav1e/archive/refs/tags/v%s.tar.gz\n' "$version"
}

openssl_lts_version() {
    github_version "openssl/openssl" "openssl-" "" "releases" '^3\.5\.[0-9]+$'
}

giflib_repo_version() {
    local rss_feed version
    local connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-5}"
    local max_time="${VERSION_CHECK_MAX_TIME:-15}"
    repo_version=""

    rss_feed=$(curl_https -fsSL --max-time "$max_time" --connect-timeout "$connect_timeout" \
                    "https://sourceforge.net/projects/giflib/rss?path=/") || {
        warn "giflib_repo_version: Failed to fetch SourceForge RSS feed"
        return 1
    }

    version=$(
        printf '%s' "$rss_feed" |
        grep -oP 'giflib-\K[0-9]+\.[0-9]+(?:\.[0-9]+)?(?=\.tar\.gz)' |
        sort -ruV | sed -n '1p'
    )

    if [[ -z "$version" ]]; then
        warn "giflib_repo_version: No version found in SourceForge RSS feed"
        return 1
    fi

    repo_version="$version"
}

giflib_download_url() {
    local version="${1:-}"
    local major_version

    [[ -n "$version" ]] || fail "giflib_download_url() called without a version. Line: ${LINENO}"
    [[ "$version" =~ ^([0-9]+)\.[0-9]+(\.[0-9]+)?$ ]] ||
        fail "giflib_download_url() received an invalid version: $version. Line: ${LINENO}"

    major_version="${BASH_REMATCH[1]}"
    printf 'https://sourceforge.net/projects/giflib/files/giflib-%s.x/giflib-%s.tar.gz/download\n' "$major_version" "$version"
}

# NASM version fetching
find_latest_nasm_version() {
    local connect_timeout
    connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-2}"
    latest_nasm_version=$(
        curl_https -fsS --max-time 10 --connect-timeout "$connect_timeout" "https://www.nasm.us/pub/nasm/stable/" 2>/dev/null |
        grep -oP 'nasm-\K[0-9]+\.[0-9]+(?:\.[0-9]+)?(?=\.tar\.xz)' |
        sort -ruV | sed -n '1p'
    )
    # Fallback to known stable version if fetch fails
    latest_nasm_version="${latest_nasm_version:-3.02}"
}

# Rust/Cargo installation functions
install_rustup() {
    local installer rustc_report

    require_vars workspace
    CARGO_HOME="$workspace/rust-toolchain/cargo"
    RUSTUP_HOME="$workspace/rust-toolchain/rustup"
    RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN_VERSION"
    export CARGO_HOME RUSTUP_HOME RUSTUP_TOOLCHAIN
    mkdir -p -- "$CARGO_HOME" "$RUSTUP_HOME" ||
        fail "Unable to create the isolated Rust toolchain directories. Line: ${LINENO}"
    path_prepend "$CARGO_HOME/bin"

    if [[ ! -x "$CARGO_HOME/bin/rustup" ]]; then
        installer="$(mktemp)" ||
            fail "Failed to create a temporary rustup installer file. Line: ${LINENO}"
        log "Downloading the official rustup installer into the isolated workspace..."
        if ! curl_https \
            --fail --silent --show-error --location \
            --retry 3 --retry-all-errors \
            --max-time 120 --connect-timeout "${DOWNLOAD_CONNECT_TIMEOUT:-5}" \
            --output "$installer" https://sh.rustup.rs; then
            rm -f -- "$installer"
            fail "Failed to download rustup. Line: ${LINENO}"
        fi
        execute sh "$installer" -y --no-modify-path --default-toolchain none --profile minimal
        rm -f -- "$installer"
    fi

    execute "$CARGO_HOME/bin/rustup" toolchain install "$RUST_TOOLCHAIN_VERSION" \
        --profile minimal
    path_prepend "$CARGO_HOME/bin"
    require_commands cargo rustc rustup
    rustc_report="$(rustc --version 2>/dev/null || true)"
    [[ "$rustc_report" == "rustc $RUST_TOOLCHAIN_VERSION "* ]] ||
        fail "Expected isolated Rust $RUST_TOOLCHAIN_VERSION, got '${rustc_report:-unavailable}'. Line: ${LINENO}"
    log "Using isolated $rustc_report."
}

check_and_install_cargo_c() {
    local cargo_c_root cargo_c_report installed_version

    require_vars workspace
    cargo_c_root="$workspace/cargo-tools"
    path_prepend "$cargo_c_root/bin"
    cargo_c_report="$(cargo cinstall --version 2>/dev/null || true)"
    installed_version="$(printf '%s\n' "$cargo_c_report" | awk 'NR == 1 {print $2}')"
    if [[ "$installed_version" == "$CARGO_C_VERSION" ]]; then
        log "Using cargo-c $CARGO_C_VERSION."
        return 0
    fi

    log "Installing cargo-c $CARGO_C_VERSION into the isolated workspace..."
    execute cargo install --force --locked --root "$cargo_c_root" \
        --version "$CARGO_C_VERSION" cargo-c
    path_prepend "$cargo_c_root/bin"
    cargo_c_report="$(cargo cinstall --version 2>/dev/null || true)"
    installed_version="$(printf '%s\n' "$cargo_c_report" | awk 'NR == 1 {print $2}')"
    [[ "$installed_version" == "$CARGO_C_VERSION" ]] ||
        fail "cargo-c installation did not produce the requested version $CARGO_C_VERSION. Line: ${LINENO}"
}

find_git_repo() {
    local repo_name="${1:-}"
    local url_choice="${2:-1}"

    [[ -n "$repo_name" ]] ||
        fail "find_git_repo() called without a repository name. Line: ${LINENO}"

    case "$repo_name" in
        # Special version detection (non-standard methods)
        FFmpeg/FFmpeg)        ffmpeg_repo_version ;;
        xiph/rav1e)           rav1e_repo_version ;;
        536)                  x264_version ;;
        GPUOpen-LibrariesAndSDKs/AMF) amf_version ;;
        avisynth/avisynthplus|AviSynth/AviSynthPlus) avisynth_version ;;
        vapoursynth/vapoursynth) vapoursynth_version ;;
        MediaArea/ZenLib|MediaArea/MediaInfoLib|MediaArea/MediaInfo) mediaarea_version "$repo_name" ;;
        24327400)             svt_av1_version "$url_choice" ;;

        # VideoLAN projects that do not use GitHub-style release tags.
        76)                   videolan_repo "76" "$url_choice" ;;
        206)                  videolan_repo "206" "$url_choice" ;;
        363)                  videolan_repo "363" "$url_choice" ;;

        # GitHub repos with custom prefix or exclude patterns (inlined from one-liner wrappers)
        Kitware/CMake)        github_version "Kitware/CMake" "v" "rc" ;;
        mesonbuild/meson)     github_version "mesonbuild/meson" "" "rc" ;;
        madler/zlib)          github_version "madler/zlib" "v" "" "releases" ;;
        mm2/Little-CMS)       github_version "mm2/Little-CMS" "lcms" ;;
        libass/libass|harfbuzz/harfbuzz|google/highway|jemalloc/jemalloc)
                              github_version "$repo_name" "" ;;
        libjpeg-turbo/libjpeg-turbo|libsndfile/libsndfile|chirlu/soxr)
                              github_version "$repo_name" "" ;;

        # GitLab repos (inlined from one-liner wrappers)
        drobilla/zix)         gitlab_version "https://gitlab.com" "drobilla/zix" ;;
        libtiff/libtiff)      gitlab_version "https://gitlab.com" "libtiff/libtiff" ;;
        GNOME/libxml2)        gitlab_version "https://gitlab.gnome.org" "GNOME/libxml2" ;;
        freetype/freetype)    freetype_version ;;
        fontconfig/fontconfig) fontconfig_version ;;
        rist/librist)         gitlab_version "https://code.videolan.org" "rist/librist" ;;

        # GitHub repos with default "v" prefix (inlined from one-liner wrappers)
        ninja-build/ninja|facebook/zstd|yasm/yasm|xiph/ogg|xiph/opus|xiph/vorbis|freeglut/freeglut|fribidi/fribidi|google/brotli|gflags/gflags|c-ares/c-ares|akheron/jansson|pnggroup/libpng|strukturag/libheif|uclouvain/openjpeg|ultravideo/kvazaar|AOMediaCodec/libavif|Haivision/srt|georgmartius/vid.stab|mstorsjo/fdk-aac|hoene/libmysofa|dyne/frei0r|nkoriyama/aribb24)
                              github_version "$repo_name" ;;

        # Default fallback
        *)                    github_repo "$repo_name" "releases" "$url_choice" ;;
    esac

    if [[ -z "${repo_version//[[:space:]]/}" ]]; then
        fail "Failed to detect a version for \"$repo_name\". Line: ${LINENO}"
    fi
}

# Cleanup function
cleanup() {
    local choice cwd_resolved script_dir_resolved home_resolved repo_root

    [[ -n "${cwd:-}" ]] || fail "Build root is not defined; cleanup cannot continue."
    [[ -e "$cwd" ]] || {
        log "Build root does not exist; nothing to clean: $cwd"
        return 0
    }

    cwd_resolved="$(canonicalize_path "$cwd")" ||
        fail "Unable to resolve build root '$cwd'."
    repo_root="${REPO_ROOT:-${SCRIPT_DIR:-${script_dir:-}}}"
    [[ -n "$repo_root" ]] ||
        fail "Repository root is not defined; cleanup cannot verify its deletion boundary."
    script_dir_resolved="$(canonicalize_path "$repo_root")" ||
        fail "Unable to resolve repository root '$repo_root'."
    [[ "${HOME:-}" == /* ]] ||
        fail "HOME must name an absolute user home directory before cleanup."
    home_resolved="$(canonicalize_path "${HOME:-}")" ||
        fail "HOME must name an absolute user home directory before cleanup."

    [[ "$cwd_resolved" != "/" && "$cwd_resolved" != "$home_resolved" ]] ||
        fail "Refusing to remove unsafe build root: '$cwd_resolved'"
    case "$cwd_resolved" in
        /bin|/boot|/dev|/etc|/lib|/lib64|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/var)
            fail "Refusing to remove unsafe build root: '$cwd_resolved'"
            ;;
    esac
    [[ "$cwd_resolved" != "$script_dir_resolved" ]] ||
        fail "Refusing to remove the repository root: '$cwd_resolved'"
    acquire_build_root_lock "$cwd_resolved"
    if build_root_marker_matches "$cwd_resolved/.ffmpeg-build-root" "$cwd_resolved"; then
        :
    elif [[ "$cwd_resolved" == "$script_dir_resolved/build" ]] &&
        legacy_build_root_marker "$cwd_resolved/.ffmpeg-build-root"; then
        warn "Upgrading the legacy marker in the repository's default build directory before cleanup."
        write_build_root_marker "$cwd_resolved"
    else
        fail "Refusing to clean a build root without a valid path-bound marker: '$cwd_resolved'"
    fi

    if [[ ! -t 0 ]]; then
        log "Standard input is not interactive; leaving build files in place at $cwd_resolved."
        return 0
    fi

    while true; do
        printf '\n'
        if ! read -r -p "Remove all build files under '$cwd_resolved'? (yes/no): " choice; then
            printf '\n'
            log "No cleanup response received; leaving build files in place."
            return 0
        fi

        case "$choice" in
            y|Y|yes|YES|Yes)
                if ! rm -rf --one-file-system -- "$cwd_resolved"; then
                    fail "Failed to remove build root '$cwd_resolved'."
                fi
                log "Removed build root: $cwd_resolved"
                return 0
                ;;
            n|N|no|NO|No)
                return 0
                ;;
            *)
                warn "Invalid input. Please enter 'yes' or 'no'."
                ;;
        esac
    done
}

# Version display functions
display_ffmpeg_versions() {
    local file files install_path
    files=(ffmpeg ffprobe ffplay)
    install_path="/usr/local/bin"

    echo
    for file in "${files[@]}"; do
        if [[ -x "$install_path/$file" ]]; then
            printf '%s%s%s (%s%s%s):\n' "$GREEN" "$file" "$NC" "$CYAN" "$install_path/$file" "$NC"
            "$install_path/$file" -version | sed -n '1p'
            echo
        elif command -v "$file" >/dev/null 2>&1; then
            printf '%s%s%s (%s):\n' "$YELLOW" "$file" "$NC" "$(command -v -- "$file")"
            "$file" -version | sed -n '1p'
            echo
        fi
    done
}

show_versions() {
    # Always display the installed versions (no prompt).
    display_ffmpeg_versions
}

# Saved compiler flags for restoration
_SAVED_CFLAGS=""
_SAVED_CXXFLAGS=""
_SAVED_CPPFLAGS=""
_SAVED_LDFLAGS=""

# Set up compiler flags
source_compiler_flags() {
    save_compiler_flags
    CFLAGS="${CFLAGS:--O2 -pipe -march=native}"
    [[ "$CFLAGS" == *-fPIC* ]] || CFLAGS+=" -fPIC"
    CXXFLAGS="${CXXFLAGS:-$CFLAGS}"
    [[ "$CXXFLAGS" == *-fPIC* ]] || CXXFLAGS+=" -fPIC"
    CPPFLAGS="-I$workspace/include${CPPFLAGS:+ $CPPFLAGS}"
    LDFLAGS="-L$workspace/lib64 -L$workspace/lib${LDFLAGS:+ $LDFLAGS} -Wl,-O1,--as-needed,-z,relro,-z,now -pthread"
    export CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
}

# Save current compiler flags before modification
save_compiler_flags() {
    _SAVED_CFLAGS="${CFLAGS:-}"
    _SAVED_CXXFLAGS="${CXXFLAGS:-}"
    _SAVED_CPPFLAGS="${CPPFLAGS:-}"
    _SAVED_LDFLAGS="${LDFLAGS:-}"
}

# Restore compiler flags to saved state
restore_compiler_flags() {
    CFLAGS="$_SAVED_CFLAGS"
    CXXFLAGS="$_SAVED_CXXFLAGS"
    CPPFLAGS="$_SAVED_CPPFLAGS"
    LDFLAGS="$_SAVED_LDFLAGS"
    export CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
}

# Echo a separator-delimited list ($1) with every entry that points inside
# $workspace removed. $2 is the separator (defaults to a space). Matches both
# bare paths (e.g. PKG_CONFIG_PATH entries) and -I/-L flags. Used to build host
# tools without exposing the half-built dependency tree we install in $workspace.
strip_workspace_entries() {
    local input="${1:-}" sep="${2:- }"
    local -a parts=()
    local part result=""
    IFS="$sep" read -ra parts <<<"$input"
    for part in "${parts[@]}"; do
        [[ -n "$part" ]] || continue
        case "$part" in
            "$workspace"/*|"$workspace"|-I"$workspace"|-I"$workspace"/*|-L"$workspace"|-L"$workspace"/*) continue ;;
        esac
        result="${result:+$result$sep}$part"
    done
    printf '%s' "$result"
}

# Autotools helper: avoid running `autoupdate` (it rewrites upstream build files).
# Prefer a shipped `configure` when present; otherwise generate one.
ensure_autotools() {
    if [[ -f configure ]]; then
        return 0
    fi

    if [[ -f autogen.sh ]]; then
        execute sh autogen.sh
        return 0
    fi

    execute autoreconf -fi
}

cmake_ninja_install() {
    local build_dir
    build_dir="${1:-}"

    [[ -n "$build_dir" ]] || fail "cmake_ninja_install() called without a build directory. Line: ${LINENO}"
    shift || true
    require_vars workspace build_threads

    execute cmake "$@" -B "$build_dir" \
        -DCMAKE_INSTALL_PREFIX="$workspace" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON \
        -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF \
        -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
        -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
        -G Ninja \
        -Wno-dev
    execute ninja "-j$build_threads" -C "$build_dir"
    execute ninja -C "$build_dir" install
}

meson_ninja_install() {
    local build_dir
    build_dir="${1:-}"

    [[ -n "$build_dir" ]] || fail "meson_ninja_install() called without a build directory. Line: ${LINENO}"
    shift || true
    require_vars workspace build_threads

    execute meson setup "$build_dir" --prefix="$workspace" --wrap-mode=nofallback "$@"
    execute ninja "-j$build_threads" -C "$build_dir"
    execute ninja -C "$build_dir" install
}

# PATH management
remove_duplicate_paths() {
    if [[ -n "$PATH" ]]; then
        local -A seen=()
        local -a parts=() unique_parts=()
        local p

        IFS=':' read -ra parts <<<"$PATH"
        for p in "${parts[@]}"; do
            [[ -n "$p" ]] || continue
            if [[ -z "${seen[$p]+x}" ]]; then
                seen[$p]=1
                unique_parts+=("$p")
            fi
        done

        PATH="$(IFS=:; printf '%s' "${unique_parts[*]}")"
        export PATH
    fi
}

path_prepend() {
    local directory="${1:-}"

    [[ -n "$directory" && -d "$directory" ]] || return 0
    PATH="$directory${PATH:+:$PATH}"
    remove_duplicate_paths
}

source_path() {
    # Supported hosts provide the bootstrap toolchain in these administrator-
    # controlled locations. Starting from a deterministic base PATH prevents an
    # unrelated user-local executable from silently replacing a build tool.
    PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin"
    export PATH

    # Prefer ccache wrappers when present (distro-dependent paths).
    if [[ -d /usr/lib/ccache/bin ]]; then
        ccache_dir=/usr/lib/ccache/bin
    elif [[ -d /usr/lib/ccache ]]; then
        ccache_dir=/usr/lib/ccache
    else
        ccache_dir=""
    fi

    export ccache_dir
    path_prepend "$workspace/bin"
    path_prepend "/opt/cuda/bin"
    path_prepend "/usr/local/cuda/bin"
    [[ -n "$ccache_dir" ]] && path_prepend "$ccache_dir"
}

# Python virtualenv helper (used by multiple build stages)
setup_python_venv_and_install_packages() {
    local venv_path="${1:-}"
    shift
    local -a packages_to_install=("$@")
    local pip_cache_dir venv_python

    [[ -n "$venv_path" ]] || fail "Virtual environment path is required. Line: ${LINENO}"
    [[ ${#packages_to_install[@]} -gt 0 ]] || fail "At least one Python package is required. Line: ${LINENO}"
    require_vars workspace

    remove_duplicate_paths

    if [[ ! -x "$venv_path/bin/python" ]]; then
        log "Creating a Python virtual environment at $venv_path..."
        execute python3 -m venv "$venv_path"
    fi
    venv_python="$venv_path/bin/python"
    pip_cache_dir="$workspace/python-package-cache"
    mkdir -p -- "$pip_cache_dir" ||
        fail "Unable to create the workspace Python package cache. Line: ${LINENO}"

    log "Installing Python packages: ${packages_to_install[*]}"
    execute env \
        -u PIP_EXTRA_INDEX_URL \
        -u PIP_FIND_LINKS \
        -u PIP_NO_INDEX \
        -u PIP_TRUSTED_HOST \
        PIP_CACHE_DIR="$pip_cache_dir" \
        PIP_CONFIG_FILE=/dev/null \
        PIP_INDEX_URL=https://pypi.org/simple \
        PYTHONNOUSERSITE=1 \
        "$venv_python" -m pip install --disable-pip-version-check \
        --no-input "${packages_to_install[@]}"
}
# Ensure managed paths are writable by the current user. Directory ownership is
# corrected without crossing filesystem boundaries.
ensure_user_ownership() {
    local path owner_uid owner_gid

    for path in "$@"; do
        [[ -e "$path" && ! -L "$path" ]] || continue
        owner_uid="$(stat -c '%u' "$path" 2>/dev/null || true)"
        owner_gid="$(stat -c '%g' "$path" 2>/dev/null || true)"
        if [[ "$owner_uid" != "$BUILD_UID" || "$owner_gid" != "$BUILD_GID" || ! -w "$path" ]]; then
            if command -v sudo >/dev/null 2>&1; then
                if [[ -d "$path" ]]; then
                    execute sudo chown -R --one-file-system "$BUILD_UID:$BUILD_GID" "$path"
                else
                    execute sudo chown "$BUILD_UID:$BUILD_GID" "$path"
                fi
            else
                fail "Path '$path' is not writable by $BUILD_USER:$BUILD_GROUP and sudo is unavailable."
            fi
        fi
    done
}
