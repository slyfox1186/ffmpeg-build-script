#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

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

# Pre-defined color variables
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Set a regex string to match and then exclude any found release candidate versions
git_regex='(Rc|rc|rC|RC|alpha|beta|early|init|next|pending|pre|tentative)+[0-9]*$'

# Debug flag
debug=OFF

# GNU mirrors (override via environment variables if needed)
GNU_PRIMARY_MIRROR="${GNU_PRIMARY_MIRROR:-https://mirrors.ibiblio.org/gnu}"
GNU_FALLBACK_MIRROR="${GNU_FALLBACK_MIRROR:-https://mirror.team-cymru.com/gnu}"

# Banner functions
box_out_banner() {
    local text="$*"
    local text_len=${#text}
    local inner_len=$((text_len + 2))
    local border color_border color_text color_reset

    color_border="$(tput setaf 3 2>/dev/null || true)"
    color_text="$(tput setaf 4 2>/dev/null || true)"
    color_reset="$(tput sgr0 2>/dev/null || true)"

    printf -v border '%*s' "$inner_len" ''
    border=${border// /-}

    tput bold 2>/dev/null || true
    printf ' %b%s%b\n' "$color_border" "$border" "$color_reset"
    printf '|%*s|\n' "$inner_len" ''
    printf '| %b%s%b |\n' "$color_text" "$text" "$color_reset"
    printf '|%*s|\n' "$inner_len" ''
    printf ' %b%s%b\n' "$color_border" "$border" "$color_reset"
    tput sgr0 2>/dev/null || true
}

box_out_banner_global() {
    box_out_banner "Installing Global Tools"
}

box_out_banner_audio() {
    box_out_banner "Installing Audio Tools"
}

box_out_banner_video() {
    box_out_banner "Installing Video Tools"
}

box_out_banner_images() {
    box_out_banner "Installing Image Tools"
}

box_out_banner_ffmpeg() {
    box_out_banner "Building FFmpeg"
}

# Logging functions
log() {
    if [[ -n "${log_file:-}" ]]; then
        printf '%s\n' "$1" | tee -a "$log_file"
    else
        printf '%s\n' "$1"
    fi
}

log_update() {
    log "$1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

require_vars() {
    local var_name
    for var_name in "$@"; do
        if [[ -z "${!var_name:-}" ]]; then
            fail "Required variable '$var_name' is not set. Line: $LINENO"
        fi
    done
}

# Validate repo_version is set and looks like a version number
# Call this after any *_version() function to ensure version detection succeeded
validate_repo_version() {
    local context="${1:-unknown}"
    if [[ -z "${repo_version:-}" ]]; then
        fail "Version detection failed for $context: repo_version is empty. Line: $LINENO"
    fi
    # Basic validation: should contain at least one digit
    if [[ ! "$repo_version" =~ [0-9] ]]; then
        fail "Version detection failed for $context: repo_version '$repo_version' does not look like a version. Line: $LINENO"
    fi
}

require_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        fail "This script requires 'sudo' (run on a system with sudo configured). Line: $LINENO"
    fi
    # Prompt once up front (better UX than failing mid-build).
    sudo -v || fail "Unable to validate sudo credentials. Line: $LINENO"
}

fail() {
    echo
    echo -e "${RED}[ERROR]${NC} $1"
    echo
    echo -e "${GREEN}[INFO]${NC} For help or to report a bug create an issue at: https://github.com/slyfox1186/ffmpeg-build-script/issues"
    if [[ "${GOOGLE_SPEECH:-false}" == "true" ]] && command -v google_speech >/dev/null 2>&1; then
        google_speech "Build failed. $1" >/dev/null 2>&1 || true
    fi
    exit 1
}

exit_fn() {
    local ffmpeg_full_path="/usr/local/bin/ffmpeg"
    echo
    box_out_banner "🎉 FFmpeg Build Completed Successfully! 🎉"
    echo
    echo -e "${GREEN}✓ FFmpeg version:${NC} $("$ffmpeg_full_path" -version 2>/dev/null | grep -oP 'ffmpeg version \K\d+\.\d+(?:\.\d+)?' || echo 'Unknown')"
    echo -e "${GREEN}✓ Installation path:${NC} /usr/local/bin"
    echo -e "${GREEN}✓ Built tools:${NC} ffmpeg, ffprobe, ffplay"
    echo -e "${GREEN}✓ Configuration:${NC} Static build with all supported codecs"
    echo
    echo -e "${GREEN}✓ Available encoders:${NC} $("$ffmpeg_full_path" -encoders 2>/dev/null | grep -c . || echo 'N/A')"
    echo -e "${GREEN}✓ Available decoders:${NC} $("$ffmpeg_full_path" -decoders 2>/dev/null | grep -c . || echo 'N/A')"
    echo -e "${GREEN}✓ Available filters:${NC} $("$ffmpeg_full_path" -filters 2>/dev/null | grep -c . || echo 'N/A')"
    echo
    echo -e "${GREEN}✓ Hardware acceleration:${NC} CUDA, NVENC/NVDEC, VDPAU, AMF (if available)"
    echo -e "${GREEN}✓ Key libraries:${NC} x264, x265, libopus, libvorbis, webp, SDL2, and more"
    echo
    echo -e "${YELLOW}You can now use FFmpeg, ffprobe, and ffplay from anywhere in your terminal!${NC}"
    echo
    echo -e "${GREEN}[INFO]${NC} Make sure to ${YELLOW}star${NC} this repository to show your support!"
    echo -e "${GREEN}[INFO]${NC} https://github.com/slyfox1186/ffmpeg-build-script"
    echo
    exit 0
}

# Execution function with error handling
execute() {
    printf '$'
    printf ' %q' "$@"
    printf '\n'

    local exit_code=0

    if [[ "$debug" == "ON" ]]; then
        if [[ -n "${log_file:-}" ]]; then
            if ! "$@" 2>&1 | tee -a "$log_file"; then
                exit_code=${PIPESTATUS[0]}
                notify-send -t 5000 "Failed to execute $*" 2>/dev/null
                fail "Failed to execute $* (exit code: $exit_code)"
            fi
        else
            if ! "$@"; then
                exit_code=$?
                notify-send -t 5000 "Failed to execute $*" 2>/dev/null
                fail "Failed to execute $* (exit code: $exit_code)"
            fi
        fi
        return 0
    fi

    if [[ -n "${log_file:-}" ]]; then
        local start_pos
        start_pos=$(wc -c <"$log_file" 2>/dev/null || echo 0)
        if ! "$@" >>"$log_file" 2>>"$log_file"; then
            exit_code=$?
            notify-send -t 5000 "Failed to execute $*" 2>/dev/null
            echo >&2
            if [[ -f "$log_file" ]]; then
                tail -c +$((start_pos + 1)) "$log_file" >&2 || true
            fi
            fail "Failed to execute $* (exit code: $exit_code)"
        fi
        return 0
    fi

    if ! "$@"; then
        exit_code=$?
        notify-send -t 5000 "Failed to execute $*" 2>/dev/null
        fail "Failed to execute $* (exit code: $exit_code)"
    fi
}

# Build management functions
build() {
    local package_name package_version stripped_version
    package_name="${1:-}"
    package_version="${2:-}"

    if [[ -z "$package_name" ]]; then
        fail "build() called without a package name. Line: $LINENO"
    fi

    # Empty versions lead to broken URLs like `foo-.tar.gz` and confusing rebuild logic.
    # Treat this as a hard error so the root cause (version detection) is fixed instead
    # of silently building the wrong thing.
    stripped_version="$(printf '%s' "$package_version" | tr -d '[:space:]')"
    if [[ -z "$stripped_version" ]]; then
        fail "build() called for \"$package_name\" with an empty version (version detection failed). Line: $LINENO"
    fi

    echo
    echo -e "${GREEN}Building${NC} ${YELLOW}$package_name${NC} - ${GREEN}version ${YELLOW}$package_version${NC}"
    echo "========================================================"

    if [[ -f "$packages/$package_name.done" ]]; then
        if grep -Fx "$package_version" "$packages/$package_name.done" >/dev/null; then
            echo "$package_name version $package_version already built. Remove $packages/$package_name.done lockfile to rebuild it."
            return 1
        elif "$LATEST"; then
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
    local temp_file
    temp_file=$(mktemp "$packages/$1.done.XXXXXX") || {
        warn "Failed to create temp file for build tracking"
        return 1
    }
    if ! echo "$2" > "$temp_file"; then
        warn "Failed to write version to temp file"
        rm -f "$temp_file"
        return 1
    fi
    if ! mv "$temp_file" "$packages/$1.done"; then
        warn "Failed to move temp file to final location"
        rm -f "$temp_file"
        return 1
    fi
}

library_exists() {
    if pkg-config --exists --print-errors "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# File download and extraction
download_try() {
    local download_file download_path download_url output_directory target_directory target_file
    download_path="$packages"
    download_url=$1
    download_file="${2:-"${1##*/}"}"
    # Strip query parameters from filename
    download_file="${download_file%%\?*}"

    # Input validation to prevent injection
    if [[ -z "$download_url" ]]; then
        fail "Download URL is required. Line: $LINENO"
    fi

    
    # Validate filename (prevent directory traversal and special characters)
    if [[ "$download_file" =~ [\|\&\$\;\`\\]|\.\./|/\.\./ ]]; then
        fail "Invalid filename: $download_file. Dangerous characters not allowed. Line: $LINENO"
    fi

    if [[ "$download_file" =~ tar\. ]]; then
        output_directory="${download_file%.*}"
        output_directory="${output_directory%.*}"
    else
        output_directory="${download_file%.*}"
    fi

    # Sanitize directory name (remove special characters)
    output_directory="${output_directory//[^a-zA-Z0-9._-]/_}"

    target_file="$download_path/$download_file"
    target_directory="$download_path/$output_directory"

    safe_rm_rf() {
        local target=$1
        local target_resolved packages_resolved

        [[ -n "$target" ]] || fail "Refusing to remove empty path. Line: $LINENO"
        target_resolved="$(readlink -f -- "$target" 2>/dev/null || echo "$target")"
        [[ "$target_resolved" != "/" ]] || fail "Refusing to remove '/'. Line: $LINENO"

        packages_resolved="$(readlink -f -- "$packages" 2>/dev/null || echo "$packages")"
        if [[ -n "$packages_resolved" ]] && [[ "$target_resolved" != "$packages_resolved"* ]]; then
            fail "Refusing to remove path outside packages dir: '$target_resolved'. Line: $LINENO"
        fi

        rm -rf -- "$target"
    }

    # Check if file already exists and is valid
    if [[ -f "$target_file" ]]; then
        # Validate existing archive file
        if [[ "$download_file" =~ (\.tar(\.(bz2|gz|xz|lz|zst))?|\.tgz|\.tbz2)$ ]]; then
            if ! tar -tf "$target_file" >/dev/null 2>>"${log_file:-/dev/null}"; then
                warn "Existing archive file $download_file is corrupted. Deleting and re-downloading."
                rm -f "$target_file"
                safe_rm_rf "$target_directory"
            else
                log "$download_file already exists and is valid, skipping download."
            fi
        else
            log "$download_file already exists, skipping download."
        fi
    fi

    if [[ ! -f "$target_file" ]]; then
        # Atomic download with proper locking to prevent race conditions
        local temp_target_file lock_file
        temp_target_file=$(mktemp "$target_file.XXXXXX") || fail "Failed to create temporary download file"
        lock_file="$target_file.lock"

        # Download tuning knobs (override via environment variables).
        # `DOWNLOAD_CONNECT_TIMEOUT` is the max time allowed to establish a connection.
        local download_connect_timeout download_max_time download_retry download_retry_delay
        download_connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-2}"
        download_max_time="${DOWNLOAD_MAX_TIME:-1800}"
        download_retry="${DOWNLOAD_RETRY:-5}"
        download_retry_delay="${DOWNLOAD_RETRY_DELAY:-5}"

        # Use a separate lock file and hold the lock during the entire download
        (
            # Acquire exclusive lock with fallback for systems without flock
            if command -v flock >/dev/null 2>&1; then
                exec 200>"$lock_file"
                if ! flock -n 200; then
                    # Another process is downloading, wait for it
                    log "$download_file is being downloaded by another process, waiting..."
                    flock 200  # This blocks until lock is released
                    # After getting the lock, check if file was created by other process
                    if [[ -f "$target_file" ]]; then
                        rm -f "$temp_target_file"
                        exit 0  # File was downloaded by other process
                    fi
                fi
            else
                # Fallback: simple spinlock using mkdir (atomic on POSIX)
                local lock_dir="${lock_file}.d"
                local max_wait=300  # 5 minutes max wait
                local waited=0
                while ! mkdir "$lock_dir" 2>/dev/null; do
                    if [[ -f "$target_file" ]]; then
                        # File was downloaded by another process
                        rm -f "$temp_target_file"
                        exit 0
                    fi
                    if ((waited >= max_wait)); then
                        # Stale lock - remove and retry
                        rm -rf "$lock_dir"
                        continue
                    fi
                    sleep 1
                    ((waited++))
                done
                # Clean up lock dir on exit from subshell
                trap 'rm -rf "$lock_dir"' EXIT
            fi

            # We have the lock, proceed with download
            log "Downloading \"$download_url\" saving as \"$download_file\""
            local download_success=false

            if command -v download_with_bot_detection >/dev/null 2>&1; then
                if download_with_bot_detection "$download_url" "$temp_target_file"; then
                    download_success=true
                else
                    warn "Failed to download \"$download_file\". Second attempt in 3 seconds..."
                    sleep 3
                    if download_with_bot_detection "$download_url" "$temp_target_file"; then
                        download_success=true
                    fi
                fi
            else
                # Default to plain curl (no browser-like headers).
                # Some hosts (e.g., GitLab instances with JS challenges) will return an HTML "bot check"
                # page if we pretend to be a browser. Plain curl is more reliable for fetching archives.
                local -a curl_args=(
                    -fsSL --retry "$download_retry" --retry-delay "$download_retry_delay" --retry-connrefused
                    --connect-timeout "$download_connect_timeout" --max-time "$download_max_time"
                )
                if curl "${curl_args[@]}" --output "$temp_target_file" "$download_url"; then
                    download_success=true
                else
                    warn "Failed to download \"$download_file\". Second attempt in 3 seconds..."
                    sleep 3
                    if curl "${curl_args[@]}" --output "$temp_target_file" "$download_url"; then
                        download_success=true
                    fi
                fi
            fi

            if [[ "$download_success" != "true" ]] || [[ ! -f "$temp_target_file" ]]; then
                rm -f "$temp_target_file"
                exit 1
            fi

            # Validate newly-downloaded archives before moving into place.
            if [[ "$download_file" =~ (\.tar(\.(bz2|gz|xz|lz|zst))?|\.tgz|\.tbz2)$ ]]; then
                if ! tar -tf "$temp_target_file" >/dev/null 2>>"${log_file:-/dev/null}"; then
                    warn "Downloaded \"$download_file\" but it is not a valid tar archive (often an HTML bot-check page)."
                    rm -f "$temp_target_file"
                    exit 1
                fi
            fi

            
            # Atomic move with error handling
            if ! mv "$temp_target_file" "$target_file"; then
                rm -f "$temp_target_file"
                exit 1
            fi
            # Lock is automatically released when subshell exits
        )
        local subshell_exit=$?
        rm -f "$lock_file" 2>/dev/null  # Clean up lock file

        if [[ $subshell_exit -ne 0 ]] && [[ ! -f "$target_file" ]]; then
            warn "Failed to download \"$download_file\"."
            return 1
        fi
    fi

    
    [[ -d "$target_directory" ]] && safe_rm_rf "$target_directory"
    mkdir -p "$target_directory"

    if ! tar -xf "$target_file" -C "$target_directory" --strip-components 1 >>"${log_file:-/dev/null}" 2>&1; then
        rm -f -- "$target_file"
        safe_rm_rf "$target_directory"
        warn "Failed to extract the tarball \"$download_file\" (deleted corrupted file and directory). Re-run the script to try again."
        return 1
    fi

    log "File extracted: $download_file"

    cd "$target_directory" || return 1
}

download() {
    if ! download_try "$@"; then
        fail "Failed to download and extract \"$1\". Line: $LINENO"
    fi
}

# Download with fallback mirror support.
# This is a wrapper around `download` that prefers the primary URL but falls back
# to a secondary mirror if the primary download fails.
download_with_fallback() {
    local primary_url=$1
    local fallback_url=$2
    local primary_file fallback_file

    if [[ -z "$primary_url" || -z "$fallback_url" ]]; then
        fail "Primary and fallback URLs are required. Line: $LINENO"
    fi

    primary_file="${primary_url##*/}"
    fallback_file="${fallback_url##*/}"

    # Try primary mirror first. If it fails, retry using the fallback mirror.
    log "Attempting download from primary mirror: $primary_url"
    if download_try "$primary_url" "$primary_file"; then
        return 0
    fi

    warn "Primary mirror failed, trying fallback mirror: $fallback_url"
    if download_try "$fallback_url" "$fallback_file"; then
        return 0
    fi

    fail "Failed to download from both primary and fallback mirrors. Line: $LINENO"
}

# Git repository management
git_caller() {
    git_url=$1
    repo_name=$2
    third_flag=$3
    recurse_flag=0

    [[ "$3" == "recurse" ]] && recurse_flag=1

    version=$(git_clone "$git_url" "$repo_name" "$third_flag")
}

git_clone() {
    local repo_flag repo_name repo_url target_directory version
    repo_url=$1
    repo_name="${2:-${1##*/}}"
    repo_name="${repo_name//\./-}"
    repo_flag=$3
    target_directory="$packages/$repo_name"

    case "$repo_flag" in
        ant)
            version=$(git ls-remote --tags "https://github.com/apache/ant.git" |
                      awk -F'/' '/\/v?[0-9]+\.[0-9]+(\.[0-9]+)?(\^\{\})?$/ {tag = $4; sub(/^v/, "", tag); if (tag !~ /\^\{\}$/) print tag}' |
                      sort -ruV | head -n1)
            ;;
        ffmpeg)
            version=$(git ls-remote --tags "https://git.ffmpeg.org/ffmpeg.git" |
                      awk -F/ '/\/n?[0-9]+\.[0-9]+(\.[0-9]+)?(\^\{\})?$/ {tag = $3; sub(/^[v]/, "", tag); print tag}' |
                      grep -v '\^{}' | sort -ruV | head -n1)
            ;;
        *)
            version=$(git ls-remote --tags "$repo_url" |
                      awk -F'/' '/\/v?[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?(\^\{\})?$/ {tag = $3; sub(/^v/, "", tag); print tag}' |
                      grep -v '\^{}' | sort -ruV | head -n1)
            [[ -z "$version" ]] && version=$(git ls-remote "$repo_url" | awk '/HEAD/ {print substr($1,1,7)}')
            [[ -z "$version" ]] && version="unknown"
            ;;
    esac

    local store_prior_version=""
    [[ -f "$packages/$repo_name.done" ]] && store_prior_version=$(cat "$packages/$repo_name.done")

    if [[ ! "$version" == "$store_prior_version" ]]; then
        local -a clone_args
        if [[ "$recurse_flag" -eq 1 ]]; then
            clone_args=(git clone --depth 1 --recursive -q "$repo_url" "$target_directory")
        else
            clone_args=(git clone --depth 1 -q "$repo_url" "$target_directory")
        fi

        if [[ -n "$3" && "$recurse_flag" -ne 1 ]]; then
            target_directory="$packages/$3"
            clone_args=(git clone --depth 1 -q "$repo_url" "$target_directory")
        fi
        [[ -d "$target_directory" ]] && rm -rf -- "$target_directory"
        if ! "${clone_args[@]}"; then
            warn "Failed to clone \"$target_directory\". Second attempt in 5 seconds..."
            sleep 5
            "${clone_args[@]}" || fail "Failed to clone \"$target_directory\". Exiting script. Line: $LINENO"
        fi
        cd "$target_directory" || fail "Failed to cd into \"$target_directory\". Line: $LINENO"
    fi

    echo "$version"
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
        fail "Repository URL is required. Line: $LINENO"
    fi

    # Validate URL format
    if [[ ! "$repo" =~ ^https?://[a-zA-Z0-9._/-]+\.[a-zA-Z0-9._/-]*$ ]]; then
        fail "Invalid repository URL format: $repo. Line: $LINENO"
    fi

    # Prefer a mirror (ibiblio), fall back to another mirror (team-cymru).
    local primary_repo="$repo"
    local ibiblio_repo cymru_repo
    local version_result="" url

    if [[ "$primary_repo" =~ ^https?://(ftp\.gnu\.org|mirror\.team-cymru\.com|mirrors\.ibiblio\.org)/gnu/ ]]; then
        ibiblio_repo="${primary_repo/ftp.gnu.org\/gnu/mirrors.ibiblio.org\/gnu}"
        ibiblio_repo="${ibiblio_repo/mirror.team-cymru.com\/gnu/mirrors.ibiblio.org\/gnu}"

        cymru_repo="${primary_repo/ftp.gnu.org\/gnu/mirror.team-cymru.com\/gnu}"
        cymru_repo="${cymru_repo/mirrors.ibiblio.org\/gnu/mirror.team-cymru.com\/gnu}"
    else
        ibiblio_repo="$primary_repo"
        cymru_repo=""
    fi

    local -a candidates=()
    local cand seen include_primary
    include_primary=true
    [[ "$primary_repo" =~ ^https?://ftp\.gnu\.org/gnu/ ]] && include_primary=false

    for cand in "$ibiblio_repo" "$cymru_repo"; do
        [[ -n "$cand" ]] || continue
        seen=false
        for url in "${candidates[@]}"; do
            if [[ "$url" == "$cand" ]]; then
                seen=true
                break
            fi
        done
        if [[ "$seen" == "false" ]]; then
            candidates+=("$cand")
        fi
    done
    if [[ "$include_primary" == "true" ]]; then
        seen=false
        for url in "${candidates[@]}"; do
            if [[ "$url" == "$primary_repo" ]]; then
                seen=true
                break
            fi
        done
        if [[ "$seen" == "false" ]]; then
            candidates+=("$primary_repo")
        fi
    fi

    for url in "${candidates[@]}"; do
        if [[ "$url" =~ libtool ]]; then
            version_result=$(curl -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'libtool-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
        elif [[ "$url" =~ m4 ]]; then
            version_result=$(curl -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'm4-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
        elif [[ "$url" =~ autoconf ]]; then
            version_result=$(curl -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'autoconf-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
        elif [[ "$url" =~ libiconv ]]; then
            version_result=$(curl -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP 'libiconv-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.gz)' | sort -Vr | head -n 1)
        else
            version_result=$(curl -fsSL --max-time 10 --connect-timeout "$connect_timeout" "$url" 2>/dev/null | grep -oP '[a-z]+-\K\d+\.\d+(?:\.\d+)?(?=\.(tar\.gz|tar\.bz2|tar\.xz))' | sort -Vr | head -n 1)
        fi

        # Normalize/validate to avoid whitespace-only or control-char results.
        version_result="$(printf '%s' "$version_result" | tr -d '\r' | head -n 1)"
        if [[ -n "${version_result//[[:space:]]/}" ]] && [[ "$version_result" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]]; then
            repo_version="$version_result"
            return 0
        fi
    done

    fail "Failed to detect latest version from $repo (tried: ${candidates[*]}). Line: $LINENO"
}

github_repo() {
    local repo url url_flag
    local page version_candidates selected_version index
    repo=$1
    url=$2
    url_flag=$3
    repo_version=""

    # Input validation to prevent injection
    if [[ -z "$repo" || -z "$url" ]]; then
        fail "Git repository and URL are required. Line: $LINENO"
    fi

    # Validate repository name format (only allow alphanumeric, dots, hyphens, forward slashes)
    if [[ ! "$repo" =~ ^[a-zA-Z0-9._/-]+$ ]]; then
        fail "Invalid repository name format: $repo. Line: $LINENO"
    fi

    # Validate URL parameter (only allow alphanumeric, hyphens, forward slashes)
    if [[ ! "$url" =~ ^[a-zA-Z0-9/-]+$ ]]; then
        fail "Invalid URL parameter: $url. Line: $LINENO"
    fi

    index=1
    if [[ "$url_flag" =~ ^[0-9]+$ ]] && [[ "$url_flag" -gt 0 ]]; then
        index="$url_flag"
    fi

    if [[ "$repo" == "xiph/rav1e" && "$index" -eq 1 ]]; then
        page=$(curl -fsSL "https://github.com/xiph/rav1e/tags/") || fail "Failed to fetch tags for $repo. Line: $LINENO"
        repo_version=$(
            printf '%s' "$page" |
            grep -oP 'p[0-9]+(?=\.tar\.gz")' |
            head -n1
        )
        if [[ -n "$repo_version" ]]; then
            return 0
        fi
        fail "Failed to detect a usable version for GitHub repo \"$repo\" (url=$url). Line: $LINENO"
    fi

    page=$(curl -fsSL "https://github.com/$repo/$url") || fail "Failed to fetch tags for $repo (url=$url). Line: $LINENO"
    version_candidates=$(
        printf '%s' "$page" |
        grep -oP 'href="[^"]*\.tar\.gz"' |
        grep -oP 'v?\K[0-9]+(?:[._][0-9]+){1,2}(?=\.tar\.gz")'
    )

    selected_version=$(printf '%s\n' "$version_candidates" | sort -ruV | sed -n "${index}p")
    if [[ -z "${selected_version//[[:space:]]/}" ]]; then
        fail "Failed to detect a usable version for GitHub repo \"$repo\" (url=$url). Line: $LINENO"
    fi

    repo_version="$selected_version"

    if [[ -z "${repo_version//[[:space:]]/}" ]]; then
        fail "Failed to detect a usable version for GitHub repo \"$repo\" (url=$url). Line: $LINENO"
    fi
}

fetch_repo_version() {
    local api_path base_url commit_id_jq_filter count project short_id_jq_filter version_jq_filter
    base_url=$1
    project=$2
    api_path=$3
    version_jq_filter=$4
    short_id_jq_filter=$5
    commit_id_jq_filter=$6
    count=0

    response=$(curl -fsS "$base_url/$project/$api_path") || fail "Failed to fetch data from $base_url/$project/$api_path in the function \"fetch_repo_version\". Line: $LINENO"

    version=$(echo "$response" | jq -r ".[$count]$version_jq_filter")
    if [[ -z "$version" || "$version" == "null" ]]; then
        fail "Failed to parse a version from $base_url/$project/$api_path (got: \"$version\"). Line: $LINENO"
    fi
    while [[ "$version" =~ $git_regex ]]; do
        ((++count))
        version=$(echo "$response" | jq -r ".[$count]$version_jq_filter")
        if [[ -z "$version" || "$version" == "null" ]]; then
            fail "Failed to parse a non-pre-release version from $base_url/$project/$api_path (got: \"$version\"). Line: $LINENO"
        fi
    done

    repo_short_id=$(echo "$response" | jq -r ".[$count]$short_id_jq_filter")
    repo_commit_id=$(echo "$response" | jq -r ".[$count]$commit_id_jq_filter")
    export repo_short_id repo_commit_id

    repo_version="$version"
}

cmake_repo_version() { github_version "Kitware/CMake" "v" "rc"; }
meson_repo_version() { github_version "mesonbuild/meson" "" "rc"; }
ninja_repo_version() { github_version "ninja-build/ninja" "v"; }
zstd_repo_version() { github_version "facebook/zstd" "v"; }
librist_repo_version() { gitlab_version "https://code.videolan.org" "rist/librist" "v"; }
# zlib: Prefer releases over tags (tags can exist without published release assets)
zlib_repo_version() { github_version "madler/zlib" "v" "" "releases"; }
yasm_repo_version() { github_version "yasm/yasm" "v"; }

###################################################################################
# Unified Version Extraction Functions
# These replace repetitive per-repo functions with parameterized, robust versions
###################################################################################

# github_version - Unified GitHub version extractor
# Usage: github_version "owner/repo" [prefix] [exclude_pattern] [url_type]
#   repo:            Repository path (e.g., "ninja-build/ninja")
#   prefix:          Tag prefix - "v" (default), "" (none), or custom (e.g., "lcms", "R")
#   exclude_pattern: Optional grep -v pattern (e.g., "rc|beta")
#   url_type:        "tags" (default) or "releases"
# Sets: repo_version
github_version() {
    local repo=$1
    # Use ${2-v} not ${2:-v} so empty string "" is preserved, only unset defaults to "v"
    local prefix=${2-v}
    local exclude_pattern=${3:-}
    local url_type=${4:-tags}
    local page pattern version

    page=$(curl -fsS "https://github.com/$repo/$url_type") || {
        warn "github_version: Failed to fetch $url_type for $repo"
        return 1
    }

    # Build regex pattern based on prefix
    # The \K resets match start, (?=") is lookahead to ensure we stop at quote
    if [[ -z "$prefix" ]]; then
        pattern='href="/'"$repo"'/releases/tag/\K[0-9]+\.[0-9]+(?:\.[0-9]+){0,2}(?=")'
    else
        pattern='href="/'"$repo"'/releases/tag/'"$prefix"'\K[0-9]+\.[0-9]+(?:\.[0-9]+){0,2}(?=")'
    fi

    if [[ -n "$exclude_pattern" ]]; then
        version=$(printf '%s' "$page" | grep -oP "$pattern" | grep -Ev "$exclude_pattern" | sort -ruV | head -n1)
    else
        version=$(printf '%s' "$page" | grep -oP "$pattern" | sort -ruV | head -n1)
    fi

    if [[ -z "$version" ]]; then
        warn "github_version: No version found for $repo (prefix='$prefix')"
        return 1
    fi

    repo_version="$version"
}

# gitlab_version - Unified GitLab version extractor
# Usage: gitlab_version "base_url" "project" [prefix] [separator]
#   base_url:   GitLab instance (e.g., "https://gitlab.com", "https://code.videolan.org")
#   project:    Project path (e.g., "drobilla/zix", "AOMediaCodec/SVT-AV1")
#   prefix:     Tag prefix - "v" (default), "" (none), or custom (e.g., "VER-")
#   separator:  Version separator - "." (default) or "-"
# Sets: repo_version
gitlab_version() {
    local base_url=$1
    local project=$2
    # Use ${3-v} not ${3:-v} so empty string "" is preserved, only unset defaults to "v"
    local prefix=${3-v}
    local separator=${4:-.}
    local page pattern version

    page=$(curl -fsS "$base_url/$project/-/tags") || {
        warn "gitlab_version: Failed to fetch tags for $project from $base_url"
        return 1
    }

    # Build regex based on separator type
    if [[ "$separator" == "-" ]]; then
        pattern='href="[^"]*/-/tags/'"$prefix"'\K[0-9]+-[0-9]+-[0-9]+(?=")'
    else
        pattern='href="[^"]*/-/tags/'"$prefix"'\K[0-9]+\.[0-9]+\.[0-9]+(?=")'
    fi

    version=$(printf '%s' "$page" | grep -oP "$pattern" | sort -ruV | head -n1)

    if [[ -z "$version" ]]; then
        warn "gitlab_version: No version found for $project (prefix='$prefix', sep='$separator')"
        return 1
    fi

    repo_version="$version"
}

# Legacy wrapper - kept for backward compatibility
generic_github_version() {
    github_version "$1" "v"
}

# Version functions for specific repos
xiph_ogg_version() { generic_github_version "xiph/ogg"; }
xiph_opus_version() { generic_github_version "xiph/opus"; }  
xiph_vorbis_version() { generic_github_version "xiph/vorbis"; }
freeglut_version() { generic_github_version "freeglut/freeglut"; }
libass_version() { github_version "libass/libass" ""; }
harfbuzz_version() { github_version "harfbuzz/harfbuzz" ""; }
fribidi_version() { generic_github_version "fribidi/fribidi"; }
brotli_version() { generic_github_version "google/brotli"; }
highway_version() { github_version "google/highway" ""; }
gflags_version() { generic_github_version "gflags/gflags"; }
libjpeg_turbo_version() { github_version "libjpeg-turbo/libjpeg-turbo" ""; }
c_ares_version() { generic_github_version "c-ares/c-ares"; }
jansson_version() { generic_github_version "akheron/jansson"; }
jemalloc_version() { github_version "jemalloc/jemalloc" ""; }
lcms2_version() { github_version "mm2/Little-CMS" "lcms"; }
libpng_version() { generic_github_version "pnggroup/libpng"; }
libheif_version() { generic_github_version "strukturag/libheif"; }
openjpeg_version() { generic_github_version "uclouvain/openjpeg"; }
kvazaar_version() { generic_github_version "ultravideo/kvazaar"; }
libavif_version() { generic_github_version "AOMediaCodec/libavif"; }
srt_version() { generic_github_version "Haivision/srt"; }
vid_stab_version() { generic_github_version "georgmartius/vid.stab"; }
fdk_aac_version() { generic_github_version "mstorsjo/fdk-aac"; }
libsndfile_version() { github_version "libsndfile/libsndfile" ""; }
zix_version() { gitlab_version "https://gitlab.com" "drobilla/zix" "v"; }
soxr_version() { github_version "chirlu/soxr" ""; }
libmysofa_version() { generic_github_version "hoene/libmysofa"; }
frei0r_version() { generic_github_version "dyne/frei0r"; }
aribb24_version() { generic_github_version "nkoriyama/aribb24"; }

libxml2_version() { gitlab_version "https://gitlab.gnome.org" "GNOME/libxml2" "v"; }
libtiff_version() { gitlab_version "https://gitlab.com" "libtiff/libtiff" "v"; }
freetype_version() { gitlab_version "https://gitlab.freedesktop.org" "freetype/freetype" "VER-" "-"; }
fontconfig_version() { gitlab_version "https://gitlab.freedesktop.org" "fontconfig/fontconfig" ""; }

debian_salsa_repo() {
    local project_id=$1
    local count=$2
    repo_version=$(curl -sL "https://salsa.debian.org/api/v4/projects/$project_id/repository/tags" | 
                   jq -r '.[].name' | 
                   grep -E '^debian/' | 
                   head -n"${count:-1}" | 
                   tail -n1
                  )
}

videolan_repo() {
    local project_id=$1
    local count=$2
    repo_version=$(curl -sL "https://code.videolan.org/api/v4/projects/$project_id/repository/tags" | 
                   jq -r '.[].name' | 
                   head -n"${count:-1}" | 
                   tail -n1
                  )
}

x264_version() {
    # x264 uses branches, not tags - get stable branch commit
    local full_commit
    full_commit=$(curl -sL "https://code.videolan.org/api/v4/projects/536/repository/branches" |
                  jq -r '.[] | select(.name == "stable") | .commit.id')
    [[ -n "$full_commit" && "$full_commit" != "null" ]] || fail "Failed to detect x264 stable commit. Line: $LINENO"
    repo_version="${full_commit:0:7}"
    x264_full_commit="$full_commit"
    export x264_full_commit
}

amf_version() {
    repo_version=$(curl -sL "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/tags" | 
                   grep -oP '/AMF/releases/tag/v\K[0-9.]+(?=")' | 
                   head -n1
                  )
}

avisynth_version() {
    repo_version=$(curl -sL "https://github.com/AviSynth/AviSynthPlus/tags" | 
                   grep -oP '/AviSynthPlus/releases/tag/v\K[0-9.]+(?=")' | 
                   head -n1
                  )
}

mediaarea_version() {
    local repo_name=$1
    repo_version=$(curl -sL "https://github.com/$repo_name/tags" | 
                   grep -oP "/$repo_name/releases/tag/v\K[0-9.]+(?=\")" | 
                   head -n1
                  )
}

svt_av1_version() {
    repo_version=$(curl -sL "https://gitlab.com/AOMediaCodec/SVT-AV1/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9.]+(?=")' | 
                   head -n1
                  )
}

vapoursynth_version() {
    repo_version=$(curl -sL "https://github.com/vapoursynth/vapoursynth/tags" |
                   grep -oP '/vapoursynth/releases/tag/R\K[0-9]+(?=")' |
                   head -n1
                  )
}

# NASM version fetching
find_latest_nasm_version() {
    local connect_timeout
    connect_timeout="${DOWNLOAD_CONNECT_TIMEOUT:-2}"
    latest_nasm_version=$(
        curl -fsS --max-time 10 --connect-timeout "$connect_timeout" "https://www.nasm.us/pub/nasm/stable/" 2>/dev/null |
        grep -oP 'nasm-\K[0-9]+\.[0-9]+\.[0-9]+(?=\.tar\.xz)' |
        sort -ruV | head -n1
    )
    # Fallback to known stable version if fetch fails
    latest_nasm_version="${latest_nasm_version:-2.16.03}"
}

# Library fix functions
fix_libiconv() {
    if [[ -f "$workspace/lib/libiconv.so.2" ]]; then
        execute sudo cp -f "$workspace/lib/libiconv.so.2" "/usr/lib/libiconv.so.2"
        execute sudo ln -sf "/usr/lib/libiconv.so.2" "/usr/lib/libiconv.so"
    else
        fail "Unable to locate the file \"$workspace/lib/libiconv.so.2\""
    fi
}

fix_libstd_libs() {
    local libstdc_path
    libstdc_path=$(find /usr/lib/x86_64-linux-gnu/ -type f -name 'libstdc++.so.6.0.*' 2>/dev/null | sort -ruV | head -n1)
    if [[ ! -f "/usr/lib/x86_64-linux-gnu/libstdc++.so" ]] && [[ -f "$libstdc_path" ]]; then
        sudo ln -sf "$libstdc_path" "/usr/lib/x86_64-linux-gnu/libstdc++.so"
    fi
}

fix_x265_libs() {
    local x265_libs latest_system_lib latest_system_lib_name
    x265_libs=$(find "$workspace/lib/" -type f -name 'libx265.so.*' 2>/dev/null | sort -rV | head -n1)

    # Only touch system paths if we actually built a shared library.
    # Many users build fully-static FFmpeg and do not want /usr modified.
    # Static builds (-DENABLE_SHARED=OFF) will not produce .so files - this is expected.
    if [[ -z "$x265_libs" || ! -f "$x265_libs" ]]; then
        return 0
    fi

    # Copy custom built x265 to system directory
    execute sudo cp -f "$x265_libs" "/usr/lib/x86_64-linux-gnu"

    # Fix broken symlinks and create proper symlink to latest version
    execute sudo rm -f "/usr/lib/x86_64-linux-gnu/libx265.so"
    latest_system_lib=$(find /usr/lib/x86_64-linux-gnu/ -name 'libx265.so.*' 2>/dev/null | sort -rV | head -n1)
    if [[ -n "$latest_system_lib" ]]; then
        latest_system_lib_name=$(basename "$latest_system_lib")
        execute sudo ln -sf "$latest_system_lib_name" "/usr/lib/x86_64-linux-gnu/libx265.so"
        log "Fixed x265 library symlink: libx265.so -> $latest_system_lib_name"
    fi

    # Update library cache to prevent ldconfig errors
    sudo ldconfig >/dev/null 2>&1 || true
}

# Rust/Cargo installation functions
install_rustup() {
    if ! command -v rustup &>/dev/null; then
        log "Installing rustup..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        source "$HOME/.cargo/env"
    else
        log "Rustup is already installed"
    fi
}

check_and_install_cargo_c() {
    if ! cargo install --list | grep -q "cargo-c"; then
        log "Installing cargo-c..."
        execute cargo install cargo-c
    else
        log "cargo-c is already installed"
    fi
}

find_git_repo() {
    local count repo_name third_flag url_choice
    repo_name=$1
    url_choice=$2
    third_flag=$3
    count=1

    case "$repo_name" in
        apache/ant)           git_caller "https://github.com/apache/ant.git" "" ant ;;
        FFmpeg/FFmpeg)        github_repo "$repo_name" "tags" "$url_choice" ;;
        xiph/rav1e)           github_repo "$repo_name" "tags" "$url_choice" ;;
        Kitware/CMake)        cmake_repo_version ;;
        mesonbuild/meson)     meson_repo_version ;;
        ninja-build/ninja)    ninja_repo_version ;;
        facebook/zstd)        zstd_repo_version ;;
        madler/zlib)          zlib_repo_version ;;
        yasm/yasm)            yasm_repo_version ;;
        xiph/ogg)             xiph_ogg_version ;;
        xiph/opus)            xiph_opus_version ;;
        xiph/vorbis)          xiph_vorbis_version ;;
        freeglut/freeglut)    freeglut_version ;;
        libass/libass)        libass_version ;;
        harfbuzz/harfbuzz)    harfbuzz_version ;;
        fribidi/fribidi)      fribidi_version ;;
        google/brotli)        brotli_version ;;
        google/highway)       highway_version ;;
        gflags/gflags)        gflags_version ;;
        libjpeg-turbo/libjpeg-turbo) libjpeg_turbo_version ;;
        c-ares/c-ares)        c_ares_version ;;
        akheron/jansson)      jansson_version ;;
        jemalloc/jemalloc)    jemalloc_version ;;
        mm2/Little-CMS)       lcms2_version ;;
        pnggroup/libpng)      libpng_version ;;
        strukturag/libheif)   libheif_version ;;
        uclouvain/openjpeg)   openjpeg_version ;;
        ultravideo/kvazaar)   kvazaar_version ;;
        AOMediaCodec/libavif) libavif_version ;;
        Haivision/srt)        srt_version ;;
        georgmartius/vid.stab) vid_stab_version ;;
        mstorsjo/fdk-aac)     fdk_aac_version ;;
        libsndfile/libsndfile) libsndfile_version ;;
        drobilla/zix)         zix_version ;;
        chirlu/soxr)          soxr_version ;;
        hoene/libmysofa)      libmysofa_version ;;
        dyne/frei0r)          frei0r_version ;;
        nkoriyama/aribb24)    aribb24_version ;;
        MediaArea/ZenLib)     mediaarea_version "$repo_name" ;;
        MediaArea/MediaInfoLib) mediaarea_version "$repo_name" ;;
        MediaArea/MediaInfo)  mediaarea_version "$repo_name" ;;
        GPUOpen-LibrariesAndSDKs/AMF) amf_version ;;
        avisynth/avisynthplus|AviSynth/AviSynthPlus) avisynth_version ;;
        vapoursynth/vapoursynth) vapoursynth_version ;;
        8143)                 debian_salsa_repo "8143" "$url_choice" ;;
        8268)                 debian_salsa_repo "8268" "$url_choice" ;;
        76)                   videolan_repo "76" "$url_choice" ;;
        206)                  videolan_repo "206" "$url_choice" ;;
        363)                  videolan_repo "363" "$url_choice" ;;
        536)                  x264_version ;;
        24327400)             svt_av1_version ;;
        *)                    github_repo "$repo_name" "releases" "$url_choice" ;;
    esac
}

# Cleanup function
cleanup() {
    local choice
    local cwd_resolved script_dir_resolved

    # Use loop instead of recursion to prevent stack exhaustion
    while true; do
        echo
        read -r -p "Do you want to clean up the build files? (yes/no): " choice

        case "$choice" in
            [yY]*|[yY][eE][sS]*)
                cwd_resolved="$(readlink -f -- "${cwd:-}" 2>/dev/null || echo "${cwd:-}")"
                if [[ -z "$cwd_resolved" || "$cwd_resolved" == "/" ]]; then
                    fail "Refusing to remove unsafe directory: '${cwd_resolved:-<empty>}'"
                fi
                if [[ -n "${script_dir:-}" ]]; then
                    script_dir_resolved="$(readlink -f -- "$script_dir" 2>/dev/null || echo "$script_dir")"
                    if [[ "$cwd_resolved" == "$script_dir_resolved" ]]; then
                        fail "Refusing to remove repo directory: '$cwd_resolved'"
                    fi
                fi
                rm -fr -- "${cwd:?}"
                return 0
                ;;
            [nN]*|[nN][oO]*)
                return 0
                ;;
            *)
                warn "Invalid input. Please enter 'yes' or 'no'."
                ;;
        esac
    done
}

# FFmpeg version checking
check_ffmpeg_version() {
    local ffmpeg_repo
    ffmpeg_repo=$1

    ffmpeg_git_version=$(git ls-remote --tags "$ffmpeg_repo" |
                         awk -F'/' '/n[0-9]+(\.[0-9]+)*(-dev)?$/ {print $3}' |
                         grep -Ev '\-dev' | sort -ruV | head -n1)
    echo "$ffmpeg_git_version"
}

# Version display functions
display_ffmpeg_versions() {
    local file files install_path
    files=(ffmpeg ffprobe ffplay)
    install_path="/usr/local/bin"

    echo
    for file in "${files[@]}"; do
        if [[ -x "$install_path/$file" ]]; then
            echo -e "${GREEN}$file${NC} (${CYAN}$install_path/$file${NC}):"
            "$install_path/$file" -version | head -1
            echo
        elif command -v "$file" >/dev/null 2>&1; then
            echo -e "${YELLOW}$file${NC} ($(which "$file")):"
            "$file" -version | head -1
            echo
        fi
    done
}

show_versions() {
    local choice

    # Use loop instead of recursion to prevent stack exhaustion
    while true; do
        echo
        read -r -p "Display the installed versions? (yes/no): " choice

        case "$choice" in
            [yY]*|[yY][eE][sS]*|"")
                display_ffmpeg_versions
                return 0
                ;;
            [nN]*|[nN][oO]*)
                return 0
                ;;
            *)
                warn "Invalid input. Please enter 'yes' or 'no'."
                ;;
        esac
    done
}

# Disk space checking
disk_space_requirements() {
    # Set the required install directory size in megabytes
    INSTALL_DIR_SIZE=7001
    log "Required install directory size: $(awk -v mb="$INSTALL_DIR_SIZE" 'BEGIN{printf "%.2fG", mb/1024}')"

    # Calculate the minimum required disk space with a 20% buffer
    MIN_DISK_SPACE=$(( (INSTALL_DIR_SIZE * 120 + 99) / 100 ))
    warn "Minimum required disk space (including 20% buffer): $(awk -v mb="$MIN_DISK_SPACE" 'BEGIN{printf "%.2fG", mb/1024}')"

    # Get the available disk space in megabytes
    AVAILABLE_DISK_SPACE=$(df -PM . | awk 'NR==2 {print $4}')
    warn "Available disk space: $(awk -v mb="$AVAILABLE_DISK_SPACE" 'BEGIN{printf "%.2fG", mb/1024}')"

    # Compare the available disk space with the minimum required
    if (( AVAILABLE_DISK_SPACE < MIN_DISK_SPACE )); then
        warn "Insufficient disk space."
        warn "Minimum required (including 20% buffer): $(awk -v mb="$MIN_DISK_SPACE" 'BEGIN{printf "%.2fG", mb/1024}')"
        fail "Available disk space: $(awk -v mb="$AVAILABLE_DISK_SPACE" 'BEGIN{printf "%.2fG", mb/1024}')"
    else
        log "Sufficient disk space available."
    fi
}

# Saved compiler flags for restoration
_SAVED_CFLAGS=""
_SAVED_CXXFLAGS=""
_SAVED_CPPFLAGS=""
_SAVED_LDFLAGS=""

# Set up compiler flags
source_compiler_flags() {
    save_compiler_flags
    CFLAGS="-O3 -pipe -fPIC -march=native"
    CXXFLAGS="$CFLAGS"
    CPPFLAGS="-I$workspace/include -D_FORTIFY_SOURCE=2"
    LDFLAGS="-L$workspace/lib64 -L$workspace/lib -Wl,-O1,--sort-common,--as-needed,-z,relro,-z,now -pthread"
    export CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
}

# Save current compiler flags before modification
save_compiler_flags() {
    _SAVED_CFLAGS="$CFLAGS"
    _SAVED_CXXFLAGS="$CXXFLAGS"
    _SAVED_CPPFLAGS="$CPPFLAGS"
    _SAVED_LDFLAGS="$LDFLAGS"
}

# Restore compiler flags to saved state
restore_compiler_flags() {
    CFLAGS="$_SAVED_CFLAGS"
    CXXFLAGS="$_SAVED_CXXFLAGS"
    CPPFLAGS="$_SAVED_CPPFLAGS"
    LDFLAGS="$_SAVED_LDFLAGS"
    export CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
}

# Autotools helper: avoid running `autoupdate` (it rewrites upstream build files).
# Prefer a shipped `configure` when present; otherwise generate one.
ensure_autotools() {
    if [[ -f "./configure" ]]; then
        return 0
    fi

    if [[ -f "./autogen.sh" ]]; then
        execute sh ./autogen.sh
        return 0
    fi

    execute autoreconf -fi
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

        PATH="$(IFS=:; echo "${unique_parts[*]}")"
        export PATH
    fi
}

source_path() {
    # Prefer ccache wrappers when present (distro-dependent paths).
    if [[ -d "/usr/lib/ccache/bin" ]]; then
        ccache_dir="/usr/lib/ccache/bin"
    elif [[ -d "/usr/lib/ccache" ]]; then
        ccache_dir="/usr/lib/ccache"
    else
        ccache_dir=""
    fi

    PATH="${ccache_dir:+$ccache_dir:}/usr/local/cuda/bin:/opt/cuda/bin:$workspace/bin:$HOME/.local/bin:$PATH"
    export ccache_dir PATH
    remove_duplicate_paths
}

# Python virtualenv helper (used by multiple build stages)
setup_python_venv_and_install_packages() {
    local venv_path=$1
    shift
    local -a packages_to_install=("$@")

    [[ -n "$venv_path" ]] || fail "Virtual environment path is required. Line: $LINENO"
    [[ ${#packages_to_install[@]} -gt 0 ]] || fail "At least one Python package is required. Line: $LINENO"

    remove_duplicate_paths

    log "Creating a Python virtual environment at $venv_path..."
    execute python3 -m venv "$venv_path"

    log "Activating the virtual environment..."
    # shellcheck source=/dev/null
    source "$venv_path/bin/activate" || fail "Failed to activate virtual environment. Line: $LINENO"

    log "Upgrading pip..."
    execute pip install --quiet --disable-pip-version-check --upgrade pip

    log "Installing Python packages: ${packages_to_install[*]}"
    execute pip install --disable-pip-version-check "${packages_to_install[@]}"

    log "Deactivating the virtual environment..."
    deactivate
}
# Ensure directories are writable by the current user
ensure_user_ownership() {
    local dir owner

    for dir in "$@"; do
        [[ -d "$dir" ]] || continue
        owner=$(stat -c '%U' "$dir" 2>/dev/null || echo "")
        if [[ "$owner" != "$USER" || ! -w "$dir" ]]; then
            if command -v sudo >/dev/null 2>&1; then
                sudo chown -R "$USER:$USER" "$dir"
            else
                warn "Directory $dir is not writable and sudo is unavailable."
            fi
        fi
    done
}
