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
    local apt_updated=false

    apt_update_once() {
        if [[ "$apt_updated" == "false" ]]; then
            sudo apt update
            apt_updated=true
        fi
    }

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
        gettext git gperf imagemagick jq ladspa-sdk
        libbluray-dev libbs2b-dev libbz2-dev libcaca-dev libcdio-dev
        libcdio-paranoia-dev libcdparanoia-dev libchromaprint-dev
	        libdav1d-dev libgl1-mesa-dev libglu1-mesa-dev libgme-dev
	        libcunit1-dev frei0r-plugins-dev libgsm1-dev libjack-dev libjansson-dev liblilv-dev libmodplug-dev libnghttp2-dev libde265-dev lv2-dev
	        libnghttp3-dev libshine-dev libsmbclient-dev libsnappy-dev
        libspeex-dev libssh-dev libssl-dev libtesseract-dev libtool libaribb24-dev
        libtwolame-dev libv4l-dev libvdpau-dev libvo-amrwbenc-dev libvpl-dev
        libx11-dev libxi-dev libyuv-dev libzvbi-dev
        perl python3 python3-dev python3-venv valgrind python3-pip
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
        echo
        # Run apt commands directly (not via execute) so user sees progress
        apt_update_once
        sudo DEBIAN_FRONTEND=noninteractive apt -y install "${available_packages[@]}"
    else
        log "All required packages are already installed."
    fi

    # Check if nvidia-smi is available; if not, try to install the appropriate package
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        local nvidia_pkg=""

        # Try Ubuntu-style nvidia-utils-XXX first
        nvidia_pkg=$(apt-cache search '^nvidia-utils-[0-9]+$' 2>/dev/null | sort -t'-' -k3 -rn | head -n1 | awk '{print $1}')

        # If not found, try Debian-style nvidia-driver-cuda
        if [[ -z "$nvidia_pkg" ]]; then
            if apt-cache show nvidia-driver-cuda &>/dev/null; then
                nvidia_pkg="nvidia-driver-cuda"
            fi
        fi

        if [[ -n "$nvidia_pkg" ]]; then
            log "nvidia-smi not found. Installing $nvidia_pkg..."
            apt_update_once
            sudo DEBIAN_FRONTEND=noninteractive apt -y install "$nvidia_pkg"
        else
            warn "nvidia-smi not found and no nvidia-utils/nvidia-driver-cuda package available."
            warn "NVIDIA GPU support may not work. Consider installing NVIDIA drivers manually."
        fi
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

# Debian OS version handling (Debian 12 and 13 only)
debian_os_version() {
    local -a debian_extra_pkgs=()

    case "$STATIC_VER" in
        12)
            debian_extra_pkgs=(
                cppcheck libsvtav1dec-dev libsvtav1-dev libsvtav1enc-dev libyuv-utils libyuv0
                libhwy-dev libsrt-gnutls-dev libsharp-dev libdmalloc5 libumfpack5
                libsuitesparseconfig5 libcolamd2 libcholmod3 libccolamd2 libcamd2 libamd2
                software-properties-common libclang-16-dev libgegl-0.4-0 libgoogle-perftools4 librist-dev
            )
            ;;
        13|trixie|sid)
            debian_extra_pkgs=(
                cppcheck libsvtav1enc-dev libyuv-utils libyuv0
                libhwy-dev libsrt-gnutls-dev libsharp-dev libdmalloc5 libumfpack6
                libsuitesparseconfig7 libcolamd3 libcholmod5 libccolamd3 libcamd3 libamd3
                libclang-dev libgegl-0.4-0t64 libgoogle-perftools4t64 librist-dev
            )
            ;;
        *)
            fail "Unsupported Debian version: $STATIC_VER. Only Debian 12 and 13 are supported. Line: $LINENO"
            ;;
    esac
    apt_pkgs "${debian_extra_pkgs[*]}"
}

# Ubuntu OS version handling (Ubuntu 22.04 and 24.04 only, plus WSL)
ubuntu_os_version() {
    # Linux Mint 21.x is treated as Ubuntu 22.04
    # Zorin OS 17 is treated as Ubuntu 22.04

    local jammy_pkgs noble_pkgs

    # Ubuntu 22.04 (Jammy) packages
    jammy_pkgs="libacl1-dev libdecor-0-dev liblz4-dev libmimalloc-dev libpipewire-0.3-dev libpsl-dev libreadline-dev"
    jammy_pkgs+=" librust-jemalloc-sys-dev librust-malloc-buf-dev libsrt-doc libsvtav1-dev libsvtav1dec-dev libsvtav1enc-dev"
    jammy_pkgs+=" libtbbmalloc2 libwayland-dev libclang1-15 libcamd2 libccolamd2 libcholmod3 libcolamd2"
    jammy_pkgs+=" libsuitesparseconfig5 libumfpack5 libamd2 cppcheck libgegl-0.4-0 libgoogle-perftools4"

    # Ubuntu 24.04 (Noble) packages
    noble_pkgs="cargo-c libcamd3 libccolamd3 libcholmod5 libcolamd3 libsuitesparseconfig7"
    noble_pkgs+=" libumfpack6 libjxl-dev libamd3 libgegl-0.4-0t64 libgoogle-perftools4t64"

    case "$STATIC_VER" in
        msft)
            # WSL uses jammy packages as baseline
            apt_pkgs "$jammy_pkgs"
            ;;
        24.04)
            apt_pkgs "$noble_pkgs"
            ;;
        22.04)
            apt_pkgs "$jammy_pkgs"
            ;;
        *)
            fail "Unsupported Ubuntu version: $STATIC_VER. Only Ubuntu 22.04 and 24.04 are supported. Line: $LINENO"
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

        # Add detection for Zorin and Mint (only supported versions)
        if [[ "$OS" == "Zorin" ]]; then
            if [[ "$VER" == "17" ]]; then
                OS="Ubuntu"
                VER="22.04"  # Zorin OS 17 is based on Ubuntu 22.04
                STATIC_VER="$VER"
            else
                fail "Unsupported Zorin OS version: $VER. Only Zorin OS 17 is supported. Line: $LINENO"
            fi
        elif [[ "$OS" == "Linux" && "$NAME" == "Linux Mint" ]]; then
            OS="Ubuntu"
            VER="22.04"  # Mint 21.x is based on Ubuntu 22.04
            STATIC_VER="$VER"
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
    # Recursion guard to prevent infinite loop if JVM install fails unexpectedly
    if [[ "${_java_setup_in_progress:-}" == "1" ]]; then
        fail "Java setup failed: /usr/lib/jvm/ still does not exist after installing openjdk. Line: $LINENO"
    fi

    source_path
    if [[ -d "/usr/lib/jvm/" ]]; then
        locate_java=$(
                     find /usr/lib/jvm/ -type d -name "java-*-openjdk*" |
                     sort -ruV | head -n1
                  )
        if [[ -z "$locate_java" ]]; then
            fail "Found /usr/lib/jvm/ but no openjdk installation detected. Line: $LINENO"
        fi
    else
        latest_openjdk_version=$(
                                 apt-cache search '^openjdk-[0-9]+-jdk-headless$' |
                                 sort -ruV | head -n1 | awk '{print $1}'
                             )
        if [[ -z "$latest_openjdk_version" ]]; then
            fail "No openjdk package found in apt repositories. Line: $LINENO"
        fi
        if execute sudo apt -y install "$latest_openjdk_version"; then
            _java_setup_in_progress=1
            set_java_variables
            unset _java_setup_in_progress
            return
        else
            fail "Could not install openjdk. Line: $LINENO"
        fi
    fi
    java_include=$(
                  find /usr/lib/jvm/ -type f -name "javac" |
                  sort -ruV | head -n1 | xargs dirname |
                  sed 's/bin/include/'
              )
    if [[ -z "$java_include" || ! -d "$java_include" ]]; then
        warn "Java include directory not found, some features may not work"
    else
        CPPFLAGS+=" -I$java_include"
    fi
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

# Note: `source_path`, `remove_duplicate_paths`, and Python venv helpers live in shared-utils.sh
# so they behave consistently across all scripts.

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

    # WSL2: ensure WSL library path is on PATH for NVIDIA Video Codec SDK tooling.
    if [[ "${VARIABLE_OS:-}" == "WSL2" && -d "/usr/lib/wsl/lib" ]]; then
        PATH="/usr/lib/wsl/lib:$PATH"
        export PATH
        remove_duplicate_paths
    fi
    
    # Set up Java environment
    set_java_variables
    remove_duplicate_paths

    # Always install required system packages
    case "$OS" in
        Ubuntu)
            ubuntu_os_version
            ;;
        Debian)
            debian_os_version
            ;;
    esac

    log "System setup initialized: $OS $VER"
}
