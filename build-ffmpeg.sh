#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

# Enable debug output to see what's happening
# set -x
set -o pipefail

####################################################################################
##
##  Purpose: Build FFmpeg from source code with addon libraries which are
##           also compiled from source to help ensure the latest functionality
##           possible
##
##  GitHub: https://github.com/slyfox1186/ffmpeg-build-script
##
##  Script version: 4.2.0
##
##  Updated: 10.31.2025
##
##  CUDA SDK Toolkit version: 12.3.1
##
##  Supported Distros: Debian 12
##                     Ubuntu (20|22|24).04
##                     (Other Debian-based distributions may also work)
##
##  Supported architecture: x86_64
##
####################################################################################

if [[ "$EUID" -eq 0 ]]; then
    echo "You must run this script without root or sudo."
    exit 1
fi

# Define global variables
script_name="${0##*/}"
script_version="4.2.0"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Keep build artifacts out of the repo root (prevents cleanup from deleting the repo).
# Override with BUILD_ROOT=/path/to/dir if desired.
repo_root="$script_dir"
cwd="${BUILD_ROOT:-"$repo_root/build"}"
mkdir -p "$cwd"
cd "$cwd" || exit 1

packages="$cwd/packages"
workspace="$cwd/workspace"
log_file="$cwd/build.log"

# Source shared utilities
source "$script_dir/scripts/shared-utils.sh"

# Print script banner
echo
box_out_banner "FFmpeg Build Script - v$script_version"

# Create output directories
mkdir -p "$packages" "$workspace"

# Ensure staging directories remain writable between runs
ensure_user_ownership "$packages" "$workspace"

# Automatically overwrite the log file each time
log_file="$cwd/build.log"
rm -f "$log_file"
touch "$log_file"


# PRINT THE SCRIPT OPTIONS
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

COMPILER_FLAG=""
CONFIGURE_OPTIONS=()
LATEST=false
LDEXEFLAGS=""
NONFREE_AND_GPL=false
GOOGLE_SPEECH=false
DO_BUILD=false

while (("$#" > 0)); do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--version)
            echo
            echo "The script version is: $script_version"
            exit 0
            ;;
        -n|--enable-gpl-and-non-free)
            CONFIGURE_OPTIONS+=("--enable-"{gpl,libsmbclient,libcdio,nonfree})
            NONFREE_AND_GPL=true
            shift
            ;;
        -b|--build)
            DO_BUILD=true
            shift
            ;;
        -c|--cleanup)
            cleanup
            shift
            exit 0
            ;;
        -g|--google-speech)
            GOOGLE_SPEECH=true
            shift
            ;;
        -l|--latest)
            LATEST=true
            shift
            ;;
        --compiler=gcc|--compiler=clang)
            COMPILER_FLAG="${1#*=}"
            shift
            ;;
        -j|--jobs)
            if [[ -z "${2:-}" ]]; then
                fail "Missing value for $1 (expected a number)."
            fi
            if [[ ! "$2" =~ ^[0-9]+$ ]] || [[ "$2" -lt 1 ]]; then
                fail "Invalid jobs value: '$2' (expected a positive integer)."
            fi
            build_threads="$2"
            shift 2
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

if ! "$DO_BUILD"; then
    usage
    exit 0
fi

if [[ -z "$build_threads" ]]; then
    # Set the available CPU thread and core count for parallel processing (speeds up the build process)
    build_threads=$(nproc --all)
fi

MAKEFLAGS="-j$build_threads"

if [[ -z "$COMPILER_FLAG" ]] || [[ "$COMPILER_FLAG" == "gcc" ]]; then
    CC="gcc"
    CXX="g++"
elif [[ "$COMPILER_FLAG" == "clang" ]]; then
    CC="clang"
    CXX="clang++"
else
    fail "Invalid compiler specified. Valid options are 'gcc' or 'clang'."
fi
export CC CXX MAKEFLAGS
export LATEST NONFREE_AND_GPL
export GOOGLE_SPEECH

# Set ACLOCAL_PATH to include workspace m4 files
export ACLOCAL_PATH="$workspace/share/aclocal:/usr/share/aclocal"

# Create cmake wrapper function to include policy version
cmake() {
    command cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "$@"
}
export -f cmake

# Create download function with bot detection avoidance
download_with_bot_detection() {
    local url=$1
    local output=$2

    # Input validation to prevent injection
    if [[ -z "$url" || -z "$output" ]]; then
        fail "URL and output file are required. Line: $LINENO"
    fi

    
    # Validate output path (prevent directory traversal)
    if [[ "$output" =~ \.\./|\.\.\|/\.\./ ]]; then
        fail "Invalid output path: $output. Directory traversal not allowed. Line: $LINENO"
    fi

    # Random delay between 0.5-2 seconds to avoid rate limiting
    sleep "$(awk 'BEGIN{srand(); print 0.5 + rand() * 1.5}')"

    # Use common browser user agents randomly
    local user_agents=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0"
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/137.0.3296.52"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/119.0.0.0"
    )
    local ua="${user_agents[$((RANDOM % ${#user_agents[@]}))]}"

    # Download with anti-bot headers and retries (fail on HTTP errors)
    curl -fLSs --retry 3 --retry-delay 2 --retry-connrefused -o "$output" \
        -H "User-Agent: $ua" \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
        -H "Accept-Language: en-US,en;q=0.5" \
        -H "Accept-Encoding: gzip, deflate, br" \
        -H "DNT: 1" \
        -H "Connection: keep-alive" \
        -H "Upgrade-Insecure-Requests: 1" \
        --connect-timeout 15 \
        --max-time 600 \
        "$url"
}

export -f download_with_bot_detection

echo
log "Utilizing $build_threads CPU threads"
echo

if "$NONFREE_AND_GPL"; then
    warn "With GPL and non-free codecs enabled"
    echo
fi

if [[ -n "$LDEXEFLAGS" ]]; then
    echo "The script has been configured to run in full static mode."
    echo
fi

[[ -t 1 ]] && clear

# Validate sudo credentials once up front (many steps require sudo for installs).
require_sudo

# Initialize system setup (OS detection, package installation, etc.)
source "$script_dir/scripts/system-setup.sh"
initialize_system_setup

# Initialize hardware detection and CUDA setup
source "$script_dir/scripts/hardware-detection.sh" 
initialize_hardware_detection

# Prompt the user to install the GeForce CUDA SDK-Toolkit
install_cuda

# Update the ld linker search paths
sudo ldconfig

# Install Global Tools
source "$script_dir/scripts/global-tools.sh"
install_global_tools

# Install Core Libraries
source "$script_dir/scripts/core-libraries.sh"
install_core_libraries

# Install Support Libraries
source "$script_dir/scripts/support-libraries.sh"
install_miscellaneous_libraries

# Install Audio Libraries
source "$script_dir/scripts/audio-libraries.sh"
install_audio_libraries

# Install Video Libraries  
source "$script_dir/scripts/video-libraries.sh"
install_video_libraries

# Install Image Libraries
source "$script_dir/scripts/image-libraries.sh"
install_image_libraries

# Build FFmpeg
source "$script_dir/scripts/ffmpeg-build.sh"
build_ffmpeg
