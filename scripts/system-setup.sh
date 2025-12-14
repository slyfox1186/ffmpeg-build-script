#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - System Setup
##  OS detection, package installation, and environment setup functions
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Required build packages
apt_pkgs() {
    local -a pkgs=() available_packages=() unavailable_packages=() extra_pkgs=()
    local pkg

    # Function to find the latest version of a package by pattern
    find_latest_version() {
        apt-cache search "^$1" | sort -ruV | head -n1 | awk '{print $1}'
    }

    # Split any caller-provided package list into an array.
    if [[ -n "${1:-}" ]]; then
        read -r -a extra_pkgs <<< "$1"
    fi

    # Define an array of apt package names
    # Note: 'lex' and 'yacc' are virtual packages that resolve to flex/bison (already listed)
    pkgs=(
        "${extra_pkgs[@]}" "$(find_latest_version 'openjdk-[0-9]+-jdk')" autoconf
        autopoint bison build-essential ccache clang cmake curl flex
        gettext git gperf imagemagick-6.q16 ladspa-sdk
        libbluray-dev libbs2b-dev libbz2-dev libcaca-dev libcdio-dev
        libcdio-paranoia-dev libcdparanoia-dev libchromaprint-dev
        libdav1d-dev libgl1-mesa-dev libglu1-mesa-dev libgme-dev
        libcunit1-dev frei0r-plugins-dev libgsm1-dev libjack-dev libjansson-dev liblilv-dev libmodplug-dev libnghttp2-dev lv2-dev
        libnghttp3-dev libshine-dev libsmbclient-dev libsnappy-dev
        libspeex-dev libssh-dev libssl-dev libtesseract-dev libtool libaribb24-dev
        libtwolame-dev libv4l-dev libvdpau-dev libvo-amrwbenc-dev libvpl-dev
        libx11-dev libxi-dev libyuv-dev libzvbi-dev nvidia-driver
        python3 python3-dev python3-venv valgrind python3-pip
    )

    # Note: GPU detection happens later; keep package install independent from GPU probing.

    log "Checking package installation status..."

    # Find missing and categorize packages in one loop
    for pkg in "${pkgs[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "ok installed"; then
            if apt-cache show "$pkg" &>/dev/null; then
                available_packages+=("$pkg")
            else
                unavailable_packages+=("$pkg")
            fi
        fi
    done

    # Print unavailable packages
    if [[ ${#unavailable_packages[@]} -gt 0 ]]; then
        echo
        warn "Unavailable packages:"
        printf "          %s\n" "${unavailable_packages[@]}"
    fi

    # Install available packages
    if [[ ${#available_packages[@]} -gt 0 ]]; then
        echo
        log "Installing missing packages:"
        printf "          %s\n" "${available_packages[@]}"
        execute sudo apt-get update
        execute sudo apt-get -y install "${available_packages[@]}"
    else
        log "All required packages are already installed."
    fi

    # If the NVIDIA tools exist but the driver stack is in a bad state, prompt the user.
    if command -v nvidia-smi >/dev/null 2>&1; then
        if ! nvidia-smi &>/dev/null; then
            echo "The \"nvidia-smi\" command exists but is not working (this can happen after a driver update)."
            echo "Rebooting often resolves this. The script may require a working NVIDIA driver stack to complete GPU-enabled builds."
            echo
            read -r -p "Do you want to reboot now? (y/n): " reboot_choice
            [[ "$reboot_choice" =~ ^[Yy]$ ]] && execute sudo reboot
        fi
    fi
}

# Check AVX-512 CPU support
check_avx512() {
    # Checking if /proc/cpuinfo exists on the system
    if [[ ! -f "/proc/cpuinfo" ]]; then
        echo "Error: /proc/cpuinfo does not exist on this system."
        return 2
    fi

    # Search for AVX512 flag in cpuinfo
    if grep -q "avx512" "/proc/cpuinfo"; then
        echo "ON"
    else
        echo "OFF"
    fi
}

# Debian WSL package configuration
debian_msft() {
    case "$VER" in
        11) apt_pkgs "$debian_pkgs $1" ;;
        12) apt_pkgs "$debian_pkgs $1" ;;
        *) fail "Failed to parse the Debian MSFT version. Line: $LINENO" ;;
    esac
}

# Debian OS version handling
debian_os_version() {
    if [[ "$1" == "yes_wsl" ]]; then
        STATIC_VER="msft"
        debian_wsl_pkgs=$2
    fi

    debian_pkgs=(
                 cppcheck libsvtav1dec-dev libsvtav1-dev libsvtav1enc-dev libyuv-utils libyuv0
                 libhwy-dev libsrt-gnutls-dev libyuv-dev libsharp-dev libdmalloc5 libumfpack5
                 libsuitesparseconfig5 libcolamd2 libcholmod3 libccolamd2 libcamd2 libamd2
                 software-properties-common libclang-16-dev libgegl-0.4-0 libgoogle-perftools4
            )

    case "$STATIC_VER" in
        msft)          debian_msft "$debian_wsl_pkgs" ;;
        11)            apt_pkgs "$1 ${debian_pkgs[*]}" ;;
        12|trixie|sid) apt_pkgs "$1 ${debian_pkgs[*]} librist-dev" ;;
        *)             fail "Could not detect the Debian release version. Line: $LINENO" ;;
    esac
}

# Ubuntu WSL package configuration
ubuntu_msft() {
    case "$STATIC_VER" in
        23.04) apt_pkgs "$ubuntu_common_pkgs $jammy_pkgs $ubuntu_wsl_pkgs" ;;
        22.04) apt_pkgs "$ubuntu_common_pkgs $jammy_pkgs $ubuntu_wsl_pkgs" ;;
        20.04) apt_pkgs "$ubuntu_common_pkgs $focal_pkgs $ubuntu_wsl_pkgs" ;;
        *) fail "Failed to parse the Ubuntu MSFT version. Line: $LINENO" ;;
    esac
}

# Ubuntu OS version handling
ubuntu_os_version() {
    if [[ "$1" = "yes_wsl" ]]; then
        VER="msft"
        ubuntu_wsl_pkgs=$2
    fi

    # Note: Zorin OS 16.x is treated as Ubuntu 20.04
    # Linux Mint 21.x is treated as Ubuntu 22.04

    ubuntu_common_pkgs="cppcheck libgegl-0.4-0 libgoogle-perftools4"
    focal_pkgs="libcunit1 libcunit1-dev libcunit1-doc libdmalloc5 libhwy-dev libreadline-dev librust-jemalloc-sys-dev librust-malloc-buf-dev"
    focal_pkgs+=" libsrt-doc libsrt-gnutls-dev libvmmalloc-dev libvmmalloc1 libyuv-dev nvidia-utils-535 libcamd2 libccolamd2 libcholmod3"
    focal_pkgs+=" libcolamd2 libsuitesparseconfig5 libumfpack5 libamd2"
    jammy_pkgs="libacl1-dev libdecor-0-dev liblz4-dev libmimalloc-dev libpipewire-0.3-dev libpsl-dev libreadline-dev librust-jemalloc-sys-dev"
    jammy_pkgs+=" librust-malloc-buf-dev libsrt-doc libsvtav1-dev libsvtav1dec-dev libsvtav1enc-dev libtbbmalloc2 libwayland-dev libclang1-15"
    jammy_pkgs+=" libcamd2 libccolamd2 libcholmod3 libcolamd2 libsuitesparseconfig5 libumfpack5 libamd2"
    lunar_kenetic_pkgs="libhwy-dev libjxl-dev librist-dev libsrt-gnutls-dev libsvtav1-dev libsvtav1dec-dev libsvtav1enc-dev libyuv-dev"
    lunar_kenetic_pkgs+=" cargo-c libcamd2 libccolamd2 libcholmod3 libcolamd2 libsuitesparseconfig5 libumfpack5 libamd2"
    mantic_pkgs="libsvtav1dec-dev libsvtav1-dev libsvtav1enc-dev libhwy-dev libsrt-gnutls-dev libyuv-dev libcamd2"
    mantic_pkgs+=" libccolamd2 libcholmod3 cargo-c libsuitesparseconfig5 libumfpack5 libjxl-dev libamd2"
    noble_pkgs="cargo-c libcamd3 libccolamd3 libcholmod5 libcolamd3 libsuitesparseconfig7"
    noble_pkgs+=" libumfpack6 libjxl-dev libamd3 libgegl-0.4-0t64 libgoogle-perftools4t64"
    case "$STATIC_VER" in
        msft)
            ubuntu_msft
            ;;
        24.04)
            apt_pkgs "$2 $noble_pkgs"
            ;;
        23.10)
            apt_pkgs "$1 $mantic_pkgs $lunar_kenetic_pkgs $jammy_pkgs $focal_pkgs"
            ;;
        23.04|22.10)
            apt_pkgs "$1 $ubuntu_common_pkgs $lunar_kenetic_pkgs $jammy_pkgs"
            ;;
        22.04)
            apt_pkgs "$1 $ubuntu_common_pkgs $jammy_pkgs"
            ;;
        20.04)
            apt_pkgs "$1 $ubuntu_common_pkgs $focal_pkgs"
            ;;
        *)
            fail "Could not detect the Ubuntu release version. Line: $LINENO"
            ;;
    esac
}

# Main OS detection function
get_os_version() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS_TMP="$NAME"
        VER_TMP="$VERSION_ID"
        OS=$(echo "$OS_TMP" | awk '{print $1}')
        VER=$(echo "$VER_TMP" | awk '{print $1}')
        VARIABLE_OS="$OS"
        STATIC_VER="$VER"

        # Add detection for Zorin and Mint
        if [[ "$OS" == "Zorin" ]]; then
            OS="Ubuntu"
            if [[ "$VER" == "17" ]]; then
                VER="22.04"  # Zorin OS 17 is based on Ubuntu 22.04
            else
                VER="20.04"  # Zorin OS 16 is based on Ubuntu 20.04
            fi
            STATIC_VER="$VER"
        elif [[ "$OS" == "Linux" && "$NAME" == "Linux Mint" ]]; then
            OS="Ubuntu"
            VER="22.04"  # Mint 21.x is based on Ubuntu 22.04
        fi
    elif [[ -n "$find_lsb_release" ]]; then
        OS=$(lsb_release -d | awk '{print $2}')
        VER=$(lsb_release -r | awk '{print $2}')
    else
        fail "Failed to define \"\$OS\" and/or \"\$VER\". Line: $LINENO"
    fi
}

# Set up Java environment variables
set_java_variables() {
    source_path
    if [[ -d "/usr/lib/jvm/" ]]; then
        locate_java=$(
                     find /usr/lib/jvm/ -type d -name "java-*-openjdk*" |
                     sort -ruV | head -n1
                  )
    else
        latest_openjdk_version=$(
                                 apt-cache search '^openjdk-[0-9]+-jdk-headless$' |
                                 sort -ruV | head -n1 | awk '{print $1}'
                             )
        if execute sudo apt-get -y install "$latest_openjdk_version"; then
            set_java_variables
        else
            fail "Could not install openjdk. Line: $LINENO"
        fi
    fi
    java_include=$(
                  find /usr/lib/jvm/ -type f -name "javac" |
                  sort -ruV | head -n1 | xargs dirname |
                  sed 's/bin/include/'
              )
    CPPFLAGS+=" -I$java_include"
    JDK_HOME="$locate_java"
    JAVA_HOME="$locate_java"
    PATH="$PATH:$JAVA_HOME/bin"
    export CPPFLAGS JDK_HOME JAVA_HOME PATH
    remove_duplicate_paths
}

# Set up Apache Ant paths
set_ant_path() {
    export ANT_HOME="$workspace/ant"
    if [[ ! -d "$workspace/ant/bin" ]] || [[ ! -d "$workspace/ant/lib" ]]; then
        mkdir -p "$workspace/ant/bin" "$workspace/ant/lib" 2>/dev/null
    fi
}

# Enhanced source_path function with ccache detection
source_path() {
    if [[ -d "/usr/lib/ccache/bin/" ]]; then
        ccache_dir="/usr/lib/ccache/bin"
    else
        ccache_dir="/usr/lib/ccache"
    fi
    PATH="$ccache_dir:/usr/local/cuda/bin:$workspace/bin:$HOME/.local/bin:$PATH"
    export PATH
}

# Enhanced remove_duplicate_paths function
remove_duplicate_paths() {
    local -a path_array=()
    local new_path=""
    local p
    declare -A seen=()

    # Properly split PATH by colon into array
    IFS=':' read -ra path_array <<< "$PATH"

    for p in "${path_array[@]}"; do
        # Skip empty paths and already-seen paths
        if [[ -n "$p" && -z "${seen[$p]+x}" ]]; then
            seen[$p]=1
            if [[ -z "$new_path" ]]; then
                new_path="$p"
            else
                new_path="$new_path:$p"
            fi
        fi
    done

    PATH="$new_path"
    export PATH
}

# Function to setup a python virtual environment and install packages with pip
setup_python_venv_and_install_packages() {
    local -a parse_package=()
    local parse_path=$1
    shift
    parse_package=("$@")

    remove_duplicate_paths

    echo "Creating a Python virtual environment at $parse_path..."
    python3 -m venv "$parse_path" || fail "Failed to create virtual environment"

    echo "Activating the virtual environment..."
    source "$parse_path/bin/activate" || fail "Failed to activate virtual environment"

    echo "Upgrading pip..."
    pip install --quiet --disable-pip-version-check --upgrade pip || fail "Failed to upgrade pip"

    echo "Installing Python packages: ${parse_package[*]}..."
    pip install --disable-pip-version-check "${parse_package[@]}" || fail "Failed to install packages"

    echo "Deactivating the virtual environment..."
    deactivate

    echo "Python virtual environment setup and package installation completed."
}

# Initialize system setup
initialize_system_setup() {
    require_vars workspace
    # Test the OS and its version
    find_lsb_release=$(find /usr/bin/ -type f -name lsb_release)
    
    get_os_version
    
    # Check if running Windows WSL2
    if grep -qi "Microsoft" /proc/version; then
        VARIABLE_OS="WSL2"
    fi
    export OS VER STATIC_VER VARIABLE_OS
    
    # Set up PKG_CONFIG_PATH
    PKG_CONFIG_PATH="$workspace/lib64/pkgconfig:$workspace/lib/x86_64-linux-gnu/pkgconfig:$workspace/lib/pkgconfig:$workspace/share/pkgconfig"
    PKG_CONFIG_PATH+=":/usr/local/lib64/x86_64-linux-gnu:/usr/local/lib64/pkgconfig:/usr/local/lib/x86_64-linux-gnu/pkgconfig:/usr/local/lib/pkgconfig"
    PKG_CONFIG_PATH+=":/usr/local/share/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
    export PKG_CONFIG_PATH
    
    # Set up paths
    source_path
    
    # Set up Java environment
    set_java_variables
    remove_duplicate_paths

    # Always install required system packages
    case "$OS" in
        Ubuntu)
            case "$STATIC_VER" in
                24.04)
                    ubuntu_os_version "desktop" "$noble_pkgs"
                    ;;
                23.10)
                    ubuntu_os_version "desktop" "$mantic_pkgs $lunar_kenetic_pkgs $jammy_pkgs $focal_pkgs"
                    ;;
                23.04|22.10)
                    ubuntu_os_version "desktop" "$ubuntu_common_pkgs $lunar_kenetic_pkgs $jammy_pkgs"
                    ;;
                22.04)
                    ubuntu_os_version "desktop" "$ubuntu_common_pkgs $jammy_pkgs"
                    ;;
                20.04)
                    ubuntu_os_version "desktop" "$ubuntu_common_pkgs $focal_pkgs"
                    ;;
            esac
            ;;
        Debian)
            case "$STATIC_VER" in
                11)
                    debian_os_version "no_wsl" "${debian_pkgs[*]}"
                    ;;
                12|trixie|sid)
                    debian_os_version "no_wsl" "${debian_pkgs[*]} librist-dev"
                    ;;
            esac
            ;;
    esac

    log "System setup initialized: $OS $VER"
}
