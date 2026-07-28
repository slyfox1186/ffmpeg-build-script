#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

################################################################################
# Host validation, package installation, and toolchain environment setup.
################################################################################

source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

APT_INDEX_UPDATED=false

apt_update_once() {
    if ! is_true "$APT_INDEX_UPDATED"; then
        log "Refreshing APT package metadata..."
        execute sudo apt-get update
        APT_INDEX_UPDATED=true
    fi
}

apt_package_available() {
    local package_name="${1:-}"

    [[ "$package_name" =~ ^[A-Za-z0-9][A-Za-z0-9+.-]*$ ]] || return 1
    apt-cache show "$package_name" >/dev/null 2>&1
}

apt_package_installed() {
    local package_name="${1:-}"

    dpkg-query -W -f='${Status}' "$package_name" 2>/dev/null |
        grep -q '^install ok installed$'
}

append_unique_packages() {
    local target_name="${1:-}"
    shift || true

    [[ "$target_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] ||
        fail "append_unique_packages() received an invalid array name."
    [[ "$(declare -p "$target_name" 2>/dev/null || true)" == "declare -a "* ]] ||
        fail "append_unique_packages() target is not an indexed array."
    local -n target_ref="$target_name"
    local package_name

    for package_name in "$@"; do
        [[ -n "$package_name" ]] || continue
        if [[ -z "${_APT_PACKAGE_SEEN[$package_name]+x}" ]]; then
            _APT_PACKAGE_SEEN["$package_name"]=1
            target_ref+=("$package_name")
        fi
    done
}

append_packages_if_enabled() {
    local target_name="${1:-}"
    local selection_name="${2:-}"
    shift 2 || true

    package_enabled "$selection_name" || return 0
    append_unique_packages "$target_name" "$@"
    if package_explicitly_enabled "$selection_name"; then
        mark_required_packages "$@"
    fi
}

append_required_packages() {
    local target_name="${1:-}"
    shift || true

    append_unique_packages "$target_name" "$@"
    mark_required_packages "$@"
}

mark_required_packages() {
    local package_name

    for package_name in "$@"; do
        _APT_PACKAGE_REQUIRED["$package_name"]=1
    done
}

install_apt_packages() {
    local package_name
    local -a requested_packages=("$@")
    local -a pending_packages=()
    local -a missing_packages=()
    local -a required_unavailable_packages=()
    local -a unavailable_packages=()

    for package_name in "${requested_packages[@]}"; do
        if apt_package_installed "$package_name"; then
            continue
        fi
        pending_packages+=("$package_name")
    done

    if ((${#pending_packages[@]} == 0)); then
        log "All requested host packages are already installed."
        return 0
    fi

    apt_update_once
    for package_name in "${pending_packages[@]}"; do
        if apt_package_available "$package_name"; then
            missing_packages+=("$package_name")
        elif [[ -n "${_APT_PACKAGE_REQUIRED[$package_name]+x}" ]]; then
            required_unavailable_packages+=("$package_name")
        else
            unavailable_packages+=("$package_name")
        fi
    done

    if ((${#required_unavailable_packages[@]} > 0)); then
        fail "Required host packages are unavailable on $OS $VER: ${required_unavailable_packages[*]}"
    fi
    if ((${#unavailable_packages[@]} > 0)); then
        warn "Optional packages unavailable on $OS $VER: ${unavailable_packages[*]}"
    fi
    if ((${#missing_packages[@]} == 0)); then
        log "All available host packages are already installed."
        return 0
    fi

    log "Installing ${#missing_packages[@]} host package(s): ${missing_packages[*]}"
    execute sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends "${missing_packages[@]}"
}

detect_operating_system() {
    local detected_id detected_version detected_like ubuntu_codename

    [[ -r /etc/os-release ]] ||
        fail "/etc/os-release is required for operating-system detection."
    # shellcheck source=/dev/null
    source /etc/os-release

    detected_id="${ID:-}"
    detected_version="${VERSION_ID:-}"
    detected_like="${ID_LIKE:-}"
    ubuntu_codename="${UBUNTU_CODENAME:-}"
    [[ -n "$detected_id" && -n "$detected_version" ]] ||
        fail "Unable to identify the operating system from /etc/os-release."

    VARIABLE_OS="$detected_id"
    case "$detected_id" in
        debian)
            OS=Debian
            VER="${detected_version%%.*}"
            case "$VER" in
                12|13) ;;
                *) fail "Unsupported Debian release '$detected_version'; supported releases are 12 and 13." ;;
            esac
            ;;
        ubuntu)
            OS=Ubuntu
            VER="$detected_version"
            case "$VER" in
                22.04|24.04|26.04) ;;
                *) fail "Unsupported Ubuntu release '$detected_version'; supported releases are 22.04, 24.04, and 26.04." ;;
            esac
            ;;
        linuxmint|zorin)
            [[ "$detected_like" == *ubuntu* ]] ||
                fail "Unsupported $detected_id base; an Ubuntu-compatible base is required."
            OS=Ubuntu
            case "$ubuntu_codename" in
                jammy) VER=22.04 ;;
                noble) VER=24.04 ;;
                resolute) VER=26.04 ;;
                *) fail "Unsupported Ubuntu derivative base '${ubuntu_codename:-unknown}'." ;;
            esac
            ;;
        *)
            fail "Unsupported operating system '$detected_id $detected_version'; use Debian or Ubuntu."
            ;;
    esac

    if grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
        [[ "$OS" == "Ubuntu" ]] ||
            fail "WSL builds require a supported Ubuntu userspace."
        VARIABLE_OS=WSL2
    fi
    STATIC_VER="$VER"
    export OS VER STATIC_VER VARIABLE_OS
}

collect_host_packages() {
    local target_name="${1:-}"
    [[ "$target_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] ||
        fail "collect_host_packages() received an invalid array name."
    [[ "$(declare -p "$target_name" 2>/dev/null || true)" == "declare -a "* ]] ||
        fail "collect_host_packages() target is not an indexed array."
    local -n output_ref="$target_name"
    local -a base_packages=(
        autoconf automake autopoint bison build-essential ca-certificates ccache
        cmake curl flex g++ gcc gettext git gnupg gperf libtool libtool-bin
        m4 meson nasm ninja-build patch pciutils perl pkgconf python3 python3-dev
        python3-venv tar xz-utils yasm
    )
    local -a essential_development_packages=(
        libbz2-dev liblzma-dev libssl-dev zlib1g-dev
    )

    declare -gA _APT_PACKAGE_SEEN=()
    declare -gA _APT_PACKAGE_REQUIRED=()
    # output_ref refers to the validated caller array.
    # shellcheck disable=SC2034
    output_ref=()
    append_unique_packages "$target_name" "${base_packages[@]}"
    append_unique_packages "$target_name" "${essential_development_packages[@]}"
    mark_required_packages "${base_packages[@]}" "${essential_development_packages[@]}"

    if [[ "$COMPILER_FLAG" == "clang" ]]; then
        append_unique_packages "$target_name" clang
        mark_required_packages clang
    fi

    append_packages_if_enabled "$target_name" "libaribb24" libaribb24-dev
    append_packages_if_enabled "$target_name" "libbluray" libbluray-dev
    append_packages_if_enabled "$target_name" "libdav1d" libdav1d-dev
    append_packages_if_enabled "$target_name" "libvpl" libvpl-dev
    append_packages_if_enabled "$target_name" "libspeex" libspeex-dev
    append_packages_if_enabled "$target_name" "libssh" libssh-dev
    append_packages_if_enabled "$target_name" "chromaprint" libchromaprint-dev
    append_packages_if_enabled "$target_name" "libjxl" libjxl-dev
    append_packages_if_enabled "$target_name" "libtesseract" libtesseract-dev
    append_packages_if_enabled "$target_name" "libzvbi" libzvbi-dev
    append_packages_if_enabled "$target_name" "libmodplug" libmodplug-dev
    append_packages_if_enabled "$target_name" "libgme" libgme-dev
    append_packages_if_enabled "$target_name" "libshine" libshine-dev
    append_packages_if_enabled "$target_name" "libcaca" libcaca-dev
    append_packages_if_enabled "$target_name" "libbs2b" libbs2b-dev
    append_packages_if_enabled "$target_name" "libjack" libjack-dev
    append_packages_if_enabled "$target_name" "libv4l2" libv4l-dev
    append_packages_if_enabled "$target_name" "libsnappy" libsnappy-dev
    append_packages_if_enabled "$target_name" "libtwolame" libtwolame-dev
    append_packages_if_enabled "$target_name" "libvo-amrwbenc" libvo-amrwbenc-dev
    append_packages_if_enabled "$target_name" "libgsm" libgsm1-dev
    append_packages_if_enabled "$target_name" "ladspa" ladspa-sdk
    append_packages_if_enabled "$target_name" "frei0r" frei0r-plugins-dev
    append_packages_if_enabled "$target_name" "libopenh264" libopenh264-dev
    append_packages_if_enabled "$target_name" "libopenmpt" libopenmpt-dev
    append_packages_if_enabled "$target_name" "librtmp" librtmp-dev
    append_packages_if_enabled "$target_name" "librsvg" librsvg2-dev
    append_packages_if_enabled "$target_name" "libflite" flite1-dev
    append_packages_if_enabled "$target_name" "alsa" libasound2-dev
    append_packages_if_enabled "$target_name" "libpulse" libpulse-dev
    append_packages_if_enabled "$target_name" "sndio" libsndio-dev
    append_packages_if_enabled "$target_name" "libdrm" libdrm-dev
    append_packages_if_enabled "$target_name" "vdpau" libvdpau-dev
    append_packages_if_enabled "$target_name" "vaapi" libva-dev
    append_packages_if_enabled "$target_name" "libvpx" libvpx-dev
    append_packages_if_enabled "$target_name" "libshaderc" libshaderc-dev
    append_packages_if_enabled "$target_name" "libplacebo" libplacebo-dev
    append_packages_if_enabled "$target_name" "vulkan" libvulkan-dev

    if package_enabled "xlib" || package_enabled "opengl" ||
        package_enabled "freeglut" || package_enabled "sdl2" ||
        package_enabled "gpac-git"; then
        append_unique_packages "$target_name" libx11-dev
    fi
    if package_enabled "xlib"; then
        append_unique_packages "$target_name" \
            libxcb-shape0-dev libxcb-shm0-dev libxcb-xfixes0-dev libxcb1-dev \
            libxext-dev libxv-dev
        if package_explicitly_enabled "xlib"; then
            mark_required_packages \
                libx11-dev \
                libxcb-shape0-dev libxcb-shm0-dev libxcb-xfixes0-dev libxcb1-dev \
                libxext-dev libxv-dev
        fi
    fi
    if package_enabled "opengl" || package_enabled "freeglut"; then
        append_unique_packages "$target_name" libgl1-mesa-dev libglu1-mesa-dev
    fi
    package_enabled "freeglut" &&
        append_unique_packages "$target_name" libxi-dev
    if package_enabled "sdl2"; then
        append_unique_packages "$target_name" \
            libasound2-dev libdecor-0-dev libdrm-dev libpulse-dev \
            libwayland-dev libx11-dev
    fi
    package_enabled "libheif" &&
        append_unique_packages "$target_name" libde265-dev

    if ! package_enabled "av1-git" && package_enabled "avif"; then
        append_required_packages "$target_name" libaom-dev
    fi
    if ! package_enabled "libogg" &&
        { package_enabled "vorbis" || package_enabled "libtheora"; }; then
        append_required_packages "$target_name" libogg-dev
    fi
    if ! package_enabled "gmp" && package_enabled "gnutls"; then
        append_required_packages "$target_name" libgmp-dev
    fi
    if ! package_enabled "nettle" && package_enabled "gnutls"; then
        append_required_packages "$target_name" nettle-dev
    fi
    if package_enabled "fontconfig"; then
        package_enabled "libxml2" ||
            append_required_packages "$target_name" libxml2-dev
        package_enabled "freetype" ||
            append_required_packages "$target_name" libfreetype-dev
    fi
    if package_enabled "libass"; then
        package_enabled "fontconfig" ||
            append_required_packages "$target_name" libfontconfig-dev
        package_enabled "freetype" ||
            append_required_packages "$target_name" libfreetype-dev
        package_enabled "fribidi" ||
            append_required_packages "$target_name" libfribidi-dev
        package_enabled "harfbuzz" ||
            append_required_packages "$target_name" libharfbuzz-dev
    fi
    if package_enabled "lilv" && ! package_enabled "lv2-git"; then
        append_required_packages "$target_name" lv2-dev
    fi
    if package_enabled "lilv"; then
        package_enabled "serd" ||
            append_required_packages "$target_name" libserd-dev
        package_enabled "zix" ||
            append_required_packages "$target_name" libzix-dev
        package_enabled "sord" ||
            append_required_packages "$target_name" libsord-dev
        package_enabled "sratom" ||
            append_required_packages "$target_name" libsratom-dev
    fi
    if package_enabled "sord"; then
        package_enabled "serd" ||
            append_required_packages "$target_name" libserd-dev
        package_enabled "zix" ||
            append_required_packages "$target_name" libzix-dev
    fi
    if package_enabled "sratom"; then
        package_enabled "lv2-git" ||
            append_required_packages "$target_name" lv2-dev
        package_enabled "serd" ||
            append_required_packages "$target_name" libserd-dev
    fi

    if is_true "$NONFREE_AND_GPL"; then
        append_packages_if_enabled "$target_name" "libsmbclient" libsmbclient-dev
        append_packages_if_enabled "$target_name" "libcdio" \
            libcdio-dev libcdio-paranoia-dev
    fi
    if package_enabled "ant-git"; then
        append_unique_packages "$target_name" default-jdk
        mark_required_packages default-jdk
    fi
}

verify_required_host_tools() {
    local -a required_tools=(
        ar awk bison cmake curl flex flock git make meson nasm ninja patch pkgconf
        python3 ranlib sed tar timeout xz yasm
    )

    case "$COMPILER_FLAG" in
        gcc) required_tools+=(gcc g++) ;;
        clang) required_tools+=(clang clang++) ;;
    esac
    require_commands "${required_tools[@]}"
}

check_avx512() {
    if [[ -r /proc/cpuinfo ]] && grep -qiw avx512f /proc/cpuinfo; then
        printf 'ON\n'
    else
        printf 'OFF\n'
    fi
}

set_java_variables() {
    local javac_path java_home

    javac_path="$(command -v javac 2>/dev/null || true)"
    [[ -n "$javac_path" ]] || fail "javac was not installed by the host setup."
    javac_path="$(readlink -f -- "$javac_path")" ||
        fail "Unable to resolve javac path."
    java_home="$(dirname -- "$(dirname -- "$javac_path")")"
    [[ -d "$java_home/include" ]] ||
        fail "Java include directory not found under '$java_home'."

    JAVA_HOME="$java_home"
    JDK_HOME="$java_home"
    export JAVA_HOME JDK_HOME
    path_prepend "$java_home/bin"
}

set_ant_path() {
    ANT_HOME="$workspace/ant"
    export ANT_HOME
    execute mkdir -p "$ANT_HOME/bin" "$ANT_HOME/lib"
}

initialize_system_setup() {
    local -a host_packages=()

    require_vars workspace COMPILER_FLAG
    require_commands apt-cache apt-get dpkg-query readlink
    detect_operating_system
    collect_host_packages host_packages
    install_apt_packages "${host_packages[@]}"
    verify_required_host_tools

    PKG_CONFIG_PATH="$workspace/lib/pkgconfig:$workspace/lib64/pkgconfig"
    PKG_CONFIG_PATH+=":$workspace/lib/x86_64-linux-gnu/pkgconfig:$workspace/share/pkgconfig"
    PKG_CONFIG_PATH+=":/usr/local/lib/pkgconfig:/usr/local/lib64/pkgconfig"
    PKG_CONFIG_PATH+=":/usr/local/lib/x86_64-linux-gnu/pkgconfig:/usr/local/share/pkgconfig"
    PKG_CONFIG_PATH+=":/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
    export PKG_CONFIG_PATH

    source_path
    if [[ "$VARIABLE_OS" == "WSL2" ]]; then
        path_prepend "/usr/lib/wsl/lib"
    fi
    if package_enabled "ant-git"; then
        set_java_variables
    fi

    log "Host setup complete: $OS $VER (${VARIABLE_OS})"
}
