#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  Purpose: Build FFmpeg from source code with addon libraries which are
##           also compiled from source to help ensure the latest functionality
##           possible
##
##  GitHub: https://github.com/slyfox1186/ffmpeg-build-script
##
##  Script version: 4.1.0
##
##  Updated: 03.21.2025
##
##  CUDA SDK Toolkit version: 12.8.1
##
##  Supported Distros: Debian 12
##                     Ubuntu (20|22|24).04
##                     Linux Mint 21.x
##                     Zorin OS 16.x
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
script_version="4.1.0"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cwd="$PWD/ffmpeg-build-script"
mkdir -p "$cwd"; cd "$cwd" || exit 1
test_regex='ffmpeg-build-script\/ffmpeg-build-script'
if [[ "$PWD" =~ $test_regex ]]; then
    cd ../
    rm -fr ffmpeg-build-script
    cwd="$PWD"
fi
packages="$cwd/packages"
workspace="$cwd/workspace"
# Set a regex string to match and then exclude any found release candidate versions of a program. We are only utilizing stable releases.
git_regex='(Rc|rc|rC|RC|alpha|beta|early|init|next|pending|pre|tentative)+[0-9]*$'
debug=ON

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
log_file="$PWD/build.log"
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

while (("$#" > 0)); do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--version)
            echo
            log "The script version is: $script_version"
            exit 0
            ;;
        -n|--enable-gpl-and-non-free)
            CONFIGURE_OPTIONS+=("--enable-"{gpl,libsmbclient,libcdio,nonfree})
            NONFREE_AND_GPL=true
            shift
            ;;
        -b|--build)
            bflag="-b"
            shift
            ;;
        -c|--cleanup)
            cflag="-c"
            cleanup
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
build_threads=$2
            shift 2
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

MAX_THREADS="$(nproc --all)"

if [[ -z "$build_threads" ]]; then
    # Set the available CPU thread and core count for parallel processing (speeds up the build process)
    if [[ -f /proc/cpuinfo ]]; then
        build_threads=$(grep --count ^processor /proc/cpuinfo)
    else
        build_threads=$(nproc --all)
    fi
fi

# Cap the number of threads to MAX_THREADS
if (( build_threads > MAX_THREADS )); then
    build_threads=$MAX_THREADS
    warn "Thread count capped to $MAX_THREADS to prevent excessive parallelism."
fi

MAKEFLAGS="-j$build_threads"
unset threads

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
    
    # Random delay between 0.5-2 seconds to avoid rate limiting
    sleep $(awk 'BEGIN{srand(); print 0.5 + rand() * 1.5}')
    
    # Use common browser user agents randomly
    local user_agents=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0"
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/137.0.3296.52"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/119.0.0.0"
    )
    local ua="${user_agents[$((RANDOM % ${#user_agents[@]}))]}"
    
    # Download with anti-bot headers
    curl -LSso "$output" \
        -H "User-Agent: $ua" \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
        -H "Accept-Language: en-US,en;q=0.5" \
        -H "Accept-Encoding: gzip, deflate, br" \
        -H "DNT: 1" \
        -H "Connection: keep-alive" \
        -H "Upgrade-Insecure-Requests: 1" \
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

clear

# Initialize system setup (OS detection, package installation, etc.)
source "$script_dir/scripts/system-setup.sh"
initialize_system_setup

# Initialize hardware detection and CUDA setup
source "$script_dir/scripts/hardware-detection.sh" 
initialize_hardware_detection

# Check if the CUDA folder exists to determine the installation status
iscuda=$(find /usr/local/cuda/ -type f -name nvcc 2>/dev/null | sort -ruV | head -n1)
cuda_path=$(find /usr/local/cuda/ -type f -name nvcc 2>/dev/null | sort -ruV | head -n1 | grep -oP '^.*/bin?')

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
