#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Shared Utilities
##  Common functions used across all build scripts
##
####################################################################################

# Pre-defined color variables
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Set a regex string to match and then exclude any found release candidate versions
git_regex='(Rc|rc|rC|RC|alpha|beta|early|init|next|pending|pre|tentative)+[0-9]*$'

# Debug flag
debug=OFF

# Banner functions
box_out_banner() {
    input_char=$(echo "$@" | wc -c)
    line=$(for i in $(seq 0 "$input_char"); do printf "-"; done)
    tput bold
    line="$(tput setaf 3)$line"
    space="${line//-/ }"
    echo " $line"
    printf "|" ; echo -n "$space" ; printf "%s\n" "|";
    printf "| " ;tput setaf 4; echo -n "$@"; tput setaf 3 ; printf "%s\n" " |";
    printf "|" ; echo -n "$space" ; printf "%s\n" "|";
    echo " $line"
    tput sgr 0
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
    printf '%s\n' "$1" | tee -a "$log_file"
}

log_update() {
    printf '%s\n' "$1" | tee -a "$log_file"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

fail() {
    echo
    echo -e "${RED}[ERROR]${NC} $1"
    echo
    echo -e "${GREEN}[INFO]${NC} For help or to report a bug create an issue at: https://github.com/slyfox1186/ffmpeg-build-script/issues"
    exit 1
}

exit_fn() {
    echo
    echo -e "${GREEN}[INFO]${NC} Make sure to ${YELLOW}star${NC} this repository to show your support!"
    echo -e "${GREEN}[INFO]${NC} https://github.com/slyfox1186/ffmpeg-build-script"
    echo
    exit 0
}

# Execution function with error handling
execute() {
    echo "$ $*"

    if [[ "$debug" == "ON" ]]; then
        if ! output=$("$@"); then
            notify-send -t 5000 "Failed to execute $*" 2>/dev/null
            fail "Failed to execute $*"
        fi
    else
        if ! output=$("$@" 2>/dev/null); then
            notify-send -t 5000 "Failed to execute $*" 2>/dev/null
            fail "Failed to execute $*"
        fi
    fi
}

# Build management functions
build() {
    echo
    echo -e "${GREEN}Building${NC} ${YELLOW}$1${NC} - ${GREEN}version ${YELLOW}$2${NC}"
    echo "========================================================"

    if [[ -f "$packages/$1.done" ]]; then
        if grep -Fx "$2" "$packages/$1.done" >/dev/null; then
            echo "$1 version $2 already built. Remove $packages/$1.done lockfile to rebuild it."
            return 1
        elif "$LATEST"; then
            echo "$1 is outdated and will be rebuilt with latest version $2"
            return 0
        else
            echo "$1 is outdated, but will not be rebuilt. Pass in --latest to rebuild it or remove $packages/$1.done lockfile."
            return 1
        fi
    fi

    return 0
}

build_done() {
    local temp_file
    temp_file=$(mktemp "$packages/$1.done.XXXXXX") || return 1
    echo "$2" > "$temp_file" && mv "$temp_file" "$packages/$1.done"
}

library_exists() {
    if pkg-config --exists --print-errors "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# File download and extraction
download() {
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

    # Atomic download to prevent TOCTOU race conditions
    local temp_target_file lock_acquired=false
    temp_target_file=$(mktemp "$target_file.XXXXXX") || fail "Failed to create temporary download file"

    # Check if file exists by trying to get exclusive lock
    if exec 3>>"$target_file" 2>/dev/null; then
        if flock -n 3; then
            lock_acquired=true
        fi
        # Always close file descriptor
        exec 3>&-
    fi

    if [[ "$lock_acquired" == "true" ]]; then
        log "Downloading \"$download_url\" saving as \"$download_file\""
        if ! download_with_bot_detection "$download_url" "$temp_target_file"; then
            rm -f "$temp_target_file"
            warn "Failed to download \"$download_file\". Second attempt in 3 seconds..."
            sleep 3
            if ! download_with_bot_detection "$download_url" "$temp_target_file"; then
                rm -f "$temp_target_file"
                fail "Failed to download \"$download_file\". Exiting... Line: $LINENO"
            fi
        fi

        # Atomic move with error handling
        if ! mv "$temp_target_file" "$target_file"; then
            rm -f "$temp_target_file"
            fail "Failed to move downloaded file to final location. Line: $LINENO"
        fi
        log "Download Completed"
    else
        # File exists or couldn't get lock
        rm -f "$temp_target_file"
        log "$download_file is already being downloaded or exists."
    fi

    if [[ "$download_file" =~ (\.tar(\.(bz2|gz|xz|lz|zst))?|\.tgz|\.tbz2)$ ]]; then
        if ! tar -tf "$target_file" >/dev/null 2>>"$log_file"; then
            warn "Archive validation failed for $download_file. Retrying without anti-bot headers."
            rm -f "$target_file"
            curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 600 \
                 --output "$target_file" "$download_url" || fail "Failed to download \"$download_file\" via fallback. Line: $LINENO"
            if ! tar -tf "$target_file" >/dev/null 2>>"$log_file"; then
                rm -f "$target_file"
                fail "Failed to validate archive \"$download_file\" after retry. Line: $LINENO"
            fi
        fi
    fi

    [[ -d "$target_directory" ]] && rm -fr "$target_directory"
    mkdir -p "$target_directory"

    if ! tar -xf "$target_file" -C "$target_directory" --strip-components 1 >>"$log_file" 2>&1; then
        rm "$target_file"
        fail "Failed to extract the tarball \"$download_file\" and was deleted. Re-run the script to try again. Line: $LINENO"
    fi

    log "File extracted: $download_file"

    cd "$target_directory" || fail "Failed to cd into \"$target_directory\". Line: $LINENO"
}

# Git repository management
git_caller() {
    git_url=$1
    repo_name=$2
    third_flag=$3
    recurse_flag=0

    [[ "$3" == "recurse" ]] && recurse_flag=1

    version=$(git_clone "$git_url" "$repo_name" "$third_flag")
    version="${version//Cloning completed: /}"
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

    [[ -f "$packages/$repo_name.done" ]] && store_prior_version=$(cat "$packages/$repo_name.done")

    if [[ ! "$version" == "$store_prior_version" ]]; then
        if [[ "$recurse_flag" -eq 1 ]]; then
            recurse="--recursive"
        elif [[ -n "$3" ]]; then
            target_directory="$packages/$3"
        fi
        [[ -d "$target_directory" ]] && rm -fr "$target_directory"
        if ! git clone --depth 1 $recurse -q "$repo_url" "$target_directory"; then
            warn "Failed to clone \"$target_directory\". Second attempt in 5 seconds..."
            sleep 5
            git clone --depth 1 $recurse -q "$repo_url" "$target_directory" || fail "Failed to clone \"$target_directory\". Exiting script. Line: $LINENO"
        fi
        cd "$target_directory" || fail "Failed to cd into \"$target_directory\". Line: $LINENO"
    fi

    echo "Cloning completed: $version"
}

# Repository version fetching
gnu_repo() {
    local repo
    repo=$1

    # Input validation
    if [[ -z "$repo" ]]; then
        fail "Repository URL is required. Line: $LINENO"
    fi

    # Validate URL format
    if [[ ! "$repo" =~ ^https?://[a-zA-Z0-9._/-]+\.[a-zA-Z0-9._/-]*$ ]]; then
        fail "Invalid repository URL format: $repo. Line: $LINENO"
    fi

    # Try primary mirror first, then fallback mirror
    local primary_repo="$repo"
    local fallback_repo="${primary_repo/ftp\.gnu\.org/mirror.team-cymru.com}"
    local version_result=""

    # Skip primary mirror (it's timing out) and go directly to Team-Cymru fallback
    if [[ "$fallback_repo" =~ libtool ]]; then
        version_result=$(curl -fsSL --max-time 5 --connect-timeout 2 "$fallback_repo" 2>/dev/null | grep -oP 'libtool-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
    elif [[ "$fallback_repo" =~ m4 ]]; then
        version_result=$(curl -fsSL --max-time 5 --connect-timeout 2 "$fallback_repo" 2>/dev/null | grep -oP 'm4-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
    elif [[ "$fallback_repo" =~ autoconf ]]; then
        version_result=$(curl -fsSL --max-time 5 --connect-timeout 2 "$fallback_repo" 2>/dev/null | grep -oP 'autoconf-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' | sort -Vr | head -n 1)
    elif [[ "$fallback_repo" =~ libiconv ]]; then
        version_result=$(curl -fsSL --max-time 5 --connect-timeout 2 "$fallback_repo" 2>/dev/null | grep -oP 'libiconv-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.gz)' | sort -Vr | head -n 1)
    else
        version_result=$(curl -fsSL --max-time 5 --connect-timeout 2 "$fallback_repo" 2>/dev/null | grep -oP '[a-z]+-\K\d+\.\d+(?:\.\d+)?(?=\.(tar\.gz|tar\.bz2|tar\.xz))' | sort -Vr | head -n 1)
    fi

    # Set the version result
    repo_version="$version_result"
}

github_repo() {
    local count max_attempts repo url url_flag
    repo=$1
    url=$2
    url_flag=$3
    count=1
    max_attempts=10

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

    while [[ "$count" -le "$max_attempts" ]]; do
        if [[ "$repo" == "xiph/rav1e" && "$url_flag" -eq 1 ]]; then
            repo_version=$(
                        curl -fsSL "https://github.com/xiph/rav1e/tags/" |
                        grep -oP 'p[0-9]+\.tar\.gz' | sed 's/\.tar\.gz//g' |
                        head -n1
                   )
            if [[ -n "$repo_version" ]]; then
                return 0
            else
                continue
            fi
        else
            if [[ "$repo" == "FFmpeg/FFmpeg" ]]; then
                curl_cmd=$(curl -fsSL "https://github.com/FFmpeg/FFmpeg/tags/" | grep -oP 'href="[^"]*[6-9]\..*\.tar\.gz"' | grep -v '\-dev' | sort -un)
            else
                curl_cmd=$(curl -fsSL "https://github.com/$repo/$url" | grep -oP 'href="[^"]*\.tar\.gz"')
            fi
        fi

        line=$(echo "$curl_cmd" | grep -oP 'href="[^"]*\.tar\.gz"' | sed -n "${count}p")
        if echo "$line" | grep -qP 'v*(\d+[._]\d+(?:[._]\d*){0,2})\.tar\.gz'; then
            repo_version=$(echo "$line" | grep -oP '(\d+[._]\d+(?:[._]\d+){0,2})')
            break
        else
            ((count++))
        fi
    done

    while [[ "$repo_version" =~ $git_regex ]]; do
        curl_cmd=$(curl -fsSL "https://github.com/$repo/$url" | grep -oP 'href="[^"]*\.tar\.gz"')
        line=$(echo "$curl_cmd" | grep -oP 'href="[^"]*\.tar\.gz"' | sed -n "${count}p")
        if echo "$line" | grep -qP 'v*(\d+[._]\d+(?:[._]\d*){0,2})\.tar\.gz'; then
            repo_version=$(echo "$line" | grep -oP '(\d+[._]\d+(?:[._]\d+){0,2})')
            break
        else
            ((count++))
        fi
    done
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
    while [[ "$version" =~ $git_regex ]]; do
        ((++count))
        version=$(echo "$response" | jq -r ".[$count]$version_jq_filter")
    done

    short_id=$(echo "$response" | jq -r ".[$count]$short_id_jq_filter")
    commit_id=$(echo "$response" | jq -r ".[$count]$commit_id_jq_filter")

    repo_version="$version"
}

cmake_repo_version() {
    repo_version=$(curl -fsS "https://github.com/Kitware/CMake/tags" | 
                   grep -oP 'href="/Kitware/CMake/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   grep -v 'rc' | 
                   sort -ruV | 
                   head -n1
                  )
}

meson_repo_version() {
    repo_version=$(curl -fsS "https://github.com/mesonbuild/meson/tags" | 
                   grep -oP 'href="/mesonbuild/meson/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   grep -v 'rc' | 
                   sort -ruV | 
                   head -n1
                  )
}

ninja_repo_version() {
    repo_version=$(curl -fsS "https://github.com/ninja-build/ninja/tags" | 
                   grep -oP 'href="/ninja-build/ninja/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

zstd_repo_version() {
    repo_version=$(curl -fsS "https://github.com/facebook/zstd/tags" | 
                   grep -oP 'href="/facebook/zstd/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

librist_repo_version() {
    repo_version=$(curl -fsS "https://code.videolan.org/rist/librist/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K0\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

zlib_repo_version() {
    repo_version=$(curl -fsS "https://github.com/madler/zlib/tags" | 
                   grep -oP 'href="/madler/zlib/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

yasm_repo_version() {
    repo_version=$(curl -fsS "https://github.com/yasm/yasm/tags" | 
                   grep -oP 'href="/yasm/yasm/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

# Generic function for standard GitHub repos with v{major}.{minor}.{patch} tags
generic_github_version() {
    local repo=$1
    repo_version=$(curl -fsS "https://github.com/$repo/tags" |
                   grep -oP 'href="/'"$repo"'/releases/tag/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' |
                   sort -ruV |
                   head -n1
                  )
}

# Version functions for specific repos
xiph_ogg_version() { generic_github_version "xiph/ogg"; }
xiph_opus_version() { generic_github_version "xiph/opus"; }  
xiph_vorbis_version() { generic_github_version "xiph/vorbis"; }
freeglut_version() { generic_github_version "freeglut/freeglut"; }
libass_version() { 
    repo_version=$(curl -fsS "https://github.com/libass/libass/tags" | 
                   grep -oP 'href="/libass/libass/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
harfbuzz_version() {
    repo_version=$(curl -fsS "https://github.com/harfbuzz/harfbuzz/tags" | 
                   grep -oP 'href="/harfbuzz/harfbuzz/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
fribidi_version() { generic_github_version "fribidi/fribidi"; }
brotli_version() { generic_github_version "google/brotli"; }
highway_version() {
    repo_version=$(curl -fsS "https://github.com/google/highway/tags" | 
                   grep -oP 'href="/google/highway/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
gflags_version() { generic_github_version "gflags/gflags"; }
libjpeg_turbo_version() {
    repo_version=$(curl -fsS "https://github.com/libjpeg-turbo/libjpeg-turbo/tags" | 
                   grep -oP 'href="/libjpeg-turbo/libjpeg-turbo/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
c_ares_version() { generic_github_version "c-ares/c-ares"; }
jansson_version() { generic_github_version "akheron/jansson"; }
jemalloc_version() {
    repo_version=$(curl -fsS "https://github.com/jemalloc/jemalloc/tags" | 
                   grep -oP 'href="/jemalloc/jemalloc/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
lcms2_version() { 
    repo_version=$(curl -fsS "https://github.com/mm2/Little-CMS/tags" | 
                   grep -oP 'href="/mm2/Little-CMS/releases/tag/lcms\K[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
libpng_version() { generic_github_version "pnggroup/libpng"; }
libheif_version() { generic_github_version "strukturag/libheif"; }
openjpeg_version() { generic_github_version "uclouvain/openjpeg"; }
kvazaar_version() { generic_github_version "ultravideo/kvazaar"; }
libavif_version() { generic_github_version "AOMediaCodec/libavif"; }
srt_version() { generic_github_version "Haivision/srt"; }
vid_stab_version() { generic_github_version "georgmartius/vid.stab"; }
fdk_aac_version() { generic_github_version "mstorsjo/fdk-aac"; }
libsndfile_version() {
    repo_version=$(curl -fsS "https://github.com/libsndfile/libsndfile/tags" | 
                   grep -oP 'href="/libsndfile/libsndfile/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
zix_version() {
    repo_version=$(curl -fsS "https://gitlab.com/drobilla/zix/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
soxr_version() {
    repo_version=$(curl -fsS "https://github.com/chirlu/soxr/tags" | 
                   grep -oP 'href="/chirlu/soxr/releases/tag/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}
libmysofa_version() { generic_github_version "hoene/libmysofa"; }
frei0r_version() { generic_github_version "dyne/frei0r"; }
aribb24_version() { generic_github_version "nkoriyama/aribb24"; }

libxml2_version() {
    repo_version=$(curl -fsS "https://gitlab.gnome.org/GNOME/libxml2/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

libtiff_version() {
    repo_version=$(curl -fsS "https://gitlab.com/libtiff/libtiff/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

freetype_version() {
    repo_version=$(curl -fsS "https://gitlab.freedesktop.org/freetype/freetype/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/VER-\K[0-9]+-[0-9]+-[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

fontconfig_version() {
    repo_version=$(curl -fsS "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | 
                   head -n1
                  )
}

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
    local full_commit=$(curl -sL "https://code.videolan.org/api/v4/projects/536/repository/branches" | 
                        jq -r '.[] | select(.name == "stable") | .commit.id')
    repo_version="${full_commit:0:7}"
    x264_full_commit="$full_commit"
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
        363)                  videolan_repo "363" "$url_choice" ;;
        536)                  x264_version ;;
        24327400)             svt_av1_version ;;
        *)                    github_repo "$repo_name" "releases" "$url_choice" ;;
    esac
}

# Cleanup function
cleanup() {
    local choice

    echo
    read -r -p "Do you want to clean up the build files? (yes/no): " choice

    case "$choice" in
        [yY]*|[yY][eE][sS]*)
            rm -fr "$cwd"
            ;;
        [nN]*|[nN][oO]*)
            ;;
        *)  unset choice
            cleanup
            ;;
    esac
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
    local file files
    files=( [0]=ffmpeg [1]=ffprobe [2]=ffplay )

    echo
    for file in "${files[@]}"; do
        if command -v "$file" >/dev/null 2>&1; then
            "$file" -version
            echo
        fi
    done
}

show_versions() {
    local choice

    echo
    read -r -p "Display the installed versions? (yes/no): " choice

    case "$choice" in
        [yY]*|[yY][eE][sS]*|"")
            display_ffmpeg_versions
            ;;
        [nN]*|[nN][oO]*)
            ;;
        *)  unset choice
            show_versions
            ;;
    esac
}

# Disk space checking
disk_space_requirements() {
    # Set the required install directory size in megabytes
    INSTALL_DIR_SIZE=7001
    log "Required install directory size: $(echo "$INSTALL_DIR_SIZE / 1024" | bc -l | awk '{printf "%.2f", $1}')G"

    # Calculate the minimum required disk space with a 20% buffer
    MIN_DISK_SPACE=$(echo "$INSTALL_DIR_SIZE * 1.2" | bc -l | awk '{print int($1)}')
    warn "Minimum required disk space (including 20% buffer): $(echo "$MIN_DISK_SPACE / 1024" | bc -l | awk '{printf "%.2f", $1}')G"

    # Get the available disk space in megabytes
    AVAILABLE_DISK_SPACE=$(df -BM . | awk '{print $4}' | tail -n1 | sed 's/M//')
    warn "Available disk space: $(echo "$AVAILABLE_DISK_SPACE / 1024" | bc -l | awk '{printf "%.2f", $1}')G"

    # Compare the available disk space with the minimum required
    if (( $(echo "$AVAILABLE_DISK_SPACE < $MIN_DISK_SPACE" | bc -l) )); then
        warn "Insufficient disk space."
        warn "Minimum required (including 20% buffer): $(echo "$MIN_DISK_SPACE / 1024" | bc -l | awk '{printf "%.2f", $1}')G"
        fail "Available disk space: $(echo "$AVAILABLE_DISK_SPACE / 1024" | bc -l | awk '{printf "%.2f", $1}')G"
    else
        log "Sufficient disk space available."
    fi
}

# Set up compiler flags
source_compiler_flags() {
    CFLAGS="-O3 -pipe -fPIC -march=native"
    CXXFLAGS="$CFLAGS"
    CPPFLAGS="-I$workspace/include -D_FORTIFY_SOURCE=2"
    LDFLAGS="-L$workspace/lib64 -L$workspace/lib -Wl,-O1,--sort-common,--as-needed,-z,relro,-z,now -pthread"
    EXTRALIBS="-ldl -lpthread -lm -lz"
    export CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
}

# PATH management
remove_duplicate_paths() {
    if [[ -n "$PATH" ]]; then
        old_PATH=$PATH:
        PATH=
        while [[ -n $old_PATH ]]; do
            x=${old_PATH%%:*}
            case $PATH: in
                *:"$x":*) ;;
                *) PATH=$PATH:$x;;
            esac
            old_PATH=${old_PATH#*:}
        done
        PATH=${PATH#:}
        export PATH
    fi
}

source_path() {
    PATH="/usr/lib/ccache:$workspace/bin:$PATH:/usr/local/cuda/bin:/opt/cuda/bin"
    export PATH
    remove_duplicate_paths
}

# Usage information
usage() {
    echo
    echo "Usage: $script_name [options]"
    echo
    echo "Options:"
    echo "  -h, --help                        Display usage information"
    echo "   --compiler=<gcc|clang>           Set the default CC and CXX compiler (default: gcc)"
    echo "  -b, --build                       Starts the build process"
    echo "  -c, --cleanup                     Remove all working dirs"
    echo "  -g, --google-speech               Enable Google Speech for audible error messages (google_speech must already be installed to work)."
    echo "  -j, --jobs <number>               Set the number of CPU threads for parallel processing"
    echo "  -l, --latest                      Force the script to build the latest version of dependencies if newer version is available"
    echo "  -n, --enable-gpl-and-non-free     Enable GPL and non-free codecs - https://ffmpeg.org/legal.html"
    echo "  -v, --version                     Display the current script version"
    echo
    echo "Example: bash $script_name --build --compiler=clang -j 8"
    echo
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
