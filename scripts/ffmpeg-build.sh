#!/usr/bin/env bash
# shellcheck disable=SC2154,SC2178 source=/dev/null

################################################################################
# Configure, compile, install, and validate FFmpeg.
################################################################################

source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

append_unique_configure_options() {
    local target_name="${1:-}"
    local seen_name="${2:-}"
    shift 2 || true

    [[ "$target_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] ||
        fail "Invalid configure-option array name '$target_name'."
    [[ "$seen_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] ||
        fail "Invalid configure-option index name '$seen_name'."
    [[ "$target_name" != "$seen_name" ]] ||
        fail "Configure-option output and index arrays must be distinct."
    [[ "$(declare -p "$target_name" 2>/dev/null || true)" == "declare -a "* ]] ||
        fail "Configure-option output must be an indexed array."
    [[ "$(declare -p "$seen_name" 2>/dev/null || true)" == "declare -A "* ]] ||
        fail "Configure-option index must be an associative array."

    local -n target_ref="$target_name"
    local -n seen_ref="$seen_name"
    local option

    for option in "$@"; do
        [[ -n "$option" ]] || continue
        if [[ -z "${seen_ref[$option]+x}" ]]; then
            seen_ref["$option"]=1
            target_ref+=("$option")
        fi
    done
}

append_required_configure_options() {
    local target_name="${1:-}"
    shift || true

    [[ "$target_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] ||
        fail "Invalid configure-option array name '$target_name'."
    [[ "$(declare -p "$target_name" 2>/dev/null || true)" == "declare -a "* ]] ||
        fail "Configure-option output must be an indexed array."

    local -n target_ref="$target_name"
    target_ref+=("$@")
    record_required_ffmpeg_config_option "$@"
}

validate_required_ffmpeg_features() {
    local config_file="${1:-}"
    local config_symbol option
    local -a missing_features=()

    [[ -f "$config_file" ]] ||
        fail "FFmpeg configuration file is missing: '$config_file'."
    for config_symbol in "${!REQUIRED_FFMPEG_CONFIG_SYMBOLS[@]}"; do
        grep -q "^${config_symbol}=yes$" "$config_file" && continue
        option="${REQUIRED_FFMPEG_CONFIG_SYMBOLS[$config_symbol]}"
        missing_features+=("'$option' ('$config_symbol')")
    done
    if ((${#missing_features[@]} > 0)); then
        fail "FFmpeg configure did not retain requested feature(s): ${missing_features[*]}"
    fi
}

ffmpeg_installed_version() {
    local binary="${1:-/usr/local/bin/ffmpeg}"

    [[ -x "$binary" ]] || return 1
    "$binary" -hide_banner -version 2>/dev/null |
        sed -nE '1s/^ffmpeg version n?([0-9]+(\.[0-9]+){1,3}).*/\1/p'
}

validate_ffmpeg_installation() {
    local expected_version="${1:-}"
    local require_ffplay="${2:-false}"
    local install_prefix="${3:-/usr/local}"
    local display_results="${4:-true}"
    local binary binary_path command_display exit_code reported_version
    local version_output version_line
    local -a required_binaries=(ffmpeg ffprobe)
    local -a version_lines=()

    [[ -n "$expected_version" ]] ||
        fail "validate_ffmpeg_installation() requires an expected version."
    [[ "$install_prefix" == /* ]] ||
        fail "validate_ffmpeg_installation() requires an absolute install prefix."
    [[ "$display_results" == "true" || "$display_results" == "false" ]] ||
        fail "validate_ffmpeg_installation() requires a 'true'/'false' display setting."
    if is_true "$require_ffplay"; then
        required_binaries+=(ffplay)
    fi
    for binary in "${required_binaries[@]}"; do
        binary_path="$install_prefix/bin/$binary"
        [[ -x "$binary_path" ]] ||
            fail "FFmpeg installation is incomplete: '$binary_path' is missing."
    done

    for binary in "${required_binaries[@]}"; do
        binary_path="$install_prefix/bin/$binary"
        command_display="$(format_command "$binary_path" -hide_banner -version)"
        if version_output="$("$binary_path" -hide_banner -version 2>&1)"; then
            exit_code=0
        else
            exit_code=$?
        fi

        if [[ -n "${log_file:-}" && -f "$log_file" ]]; then
            {
                printf '$ %s\n' "$command_display"
                [[ -z "$version_output" ]] || printf '%s\n' "$version_output"
            } >>"$log_file" ||
                fail "Unable to record the '$binary' version check in '$log_file'."
        fi
        if ((exit_code != 0)); then
            [[ -z "$version_output" ]] || printf '\n%s\n' "$version_output" >&2
            fail "'$binary' version check failed with exit code $exit_code: '$command_display'."
        fi

        version_line="${version_output%%$'\n'*}"
        [[ -n "$version_line" ]] ||
            fail "'$binary' version check returned no output: '$command_display'."
        reported_version="$(
            printf '%s\n' "$version_line" |
                sed -nE "s/^${binary} version n?([0-9]+(\.[0-9]+){1,3}).*/\1/p"
        )"
        [[ "$reported_version" == "$expected_version" ]] ||
            fail "'$binary' reported version '${reported_version:-unknown}', expected '$expected_version'."
        version_lines+=("$version_line")
    done

    grep -E '^[[:space:]][A-Z.]{6}[[:space:]]' <(
        "$install_prefix/bin/ffmpeg" -hide_banner -encoders 2>/dev/null
    ) >/dev/null ||
        fail "Installed FFmpeg did not report any encoders."
    grep -E '^[[:space:]][A-Z.]{6}[[:space:]]' <(
        "$install_prefix/bin/ffmpeg" -hide_banner -decoders 2>/dev/null
    ) >/dev/null ||
        fail "Installed FFmpeg did not report any decoders."

    if is_true "$display_results"; then
        printf '\n%sFFmpeg installation verified%s (%s/bin):\n' \
            "$GREEN" "$NC" "$install_prefix"
        for version_line in "${version_lines[@]}"; do
            printf '  %s\n' "$version_line"
        done
    fi
}

build_ffmpeg() {
    local ffmpeg_version marker_file installed_version recorded_version
    local source_directory extra_cflags extra_cxxflags extra_ldflags extra_libs
    local cuda_version cuda_major
    local staging_root staged_prefix
    local ffplay_enabled=false
    local -a base_config=()
    local -a detected_config=()
    local -a final_config=()
    local -A _FFMPEG_CONFIGURE_OPTION_SEEN=()

    echo
    box_out_banner "Building FFmpeg"
    require_vars workspace packages build_threads CC CXX

    if ! package_enabled "ffmpeg"; then
        log "FFmpeg is disabled by config; dependency build is complete."
        return 0
    fi

    fetch_version_if_enabled "ffmpeg" ffmpeg_repo_version ||
        fail "Unable to determine the latest stable FFmpeg release."
    ffmpeg_version="$repo_version"
    [[ "$ffmpeg_version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] ||
        fail "Invalid FFmpeg release version '$ffmpeg_version'."

    installed_version="$(ffmpeg_installed_version /usr/local/bin/ffmpeg || true)"
    [[ -z "$installed_version" ]] ||
        log "Installed FFmpeg version: '$installed_version'."
    log "Selected FFmpeg release: '$ffmpeg_version'."

    marker_file="$packages/ffmpeg.done"
    if package_enabled "sdl2" && library_exists sdl2; then
        ffplay_enabled=true
    fi
    recorded_version="$(read_marker_version "$marker_file" || true)"
    if [[ "$recorded_version" == "n$ffmpeg_version" ]] &&
        { [[ "$installed_version" != "$ffmpeg_version" ]] ||
          [[ ! -x /usr/local/bin/ffprobe ]] ||
          { is_true "$ffplay_enabled" && [[ ! -x /usr/local/bin/ffplay ]]; }; }; then
        warn "FFmpeg's build marker exists, but its required installed programs are incomplete; rebuilding."
        execute rm -f -- "$marker_file"
    fi

    if build "ffmpeg" "n$ffmpeg_version"; then
        download "https://ffmpeg.org/releases/ffmpeg-$ffmpeg_version.tar.xz" \
            "ffmpeg-$ffmpeg_version.tar.xz"
        source_directory="$PWD"
        execute mkdir -p build
        cd build || fail "Unable to enter FFmpeg build directory."

        extra_cflags="-I$workspace/include ${CPPFLAGS:-} ${CFLAGS:-}"
        extra_cxxflags="-I$workspace/include ${CPPFLAGS:-} ${CXXFLAGS:-}"
        extra_ldflags="-L$workspace/lib64 -L$workspace/lib ${LDFLAGS:-}"
        extra_libs="-ldl -lpthread -lm"

        base_config=(
            --prefix=/usr/local
            --arch=x86_64
            --cpu=native
            --cc="$CC"
            --cxx="$CXX"
            --pkg-config=pkgconf
            --pkg-config-flags=--static
            --disable-autodetect
            --disable-debug
            --disable-doc
            --disable-shared
            --enable-static
            --enable-pic
            --enable-pthreads
            --enable-ffmpeg
            --enable-ffprobe
            --enable-version3
            --enable-bzlib
            --enable-lzma
        )

        if is_true "$ffplay_enabled"; then
            append_required_configure_options base_config --enable-sdl2
            base_config+=(--enable-ffplay)
        else
            base_config+=(--disable-ffplay --disable-sdl2)
            warn "SDL2 is unavailable or disabled; 'ffplay' will not be built."
        fi
        if package_enabled "libiconv" && header_exists iconv.h; then
            append_required_configure_options detected_config --enable-iconv
        fi
        if package_enabled "zlib" && library_exists zlib; then
            append_required_configure_options detected_config --enable-zlib
        fi

        # Source-built and system-provided optional dependencies. Every option is
        # gated on both user selection and an actual SDK/header probe; FFmpeg's own
        # configure then performs the authoritative compile/link check.
        package_enabled "libbluray" && library_exists libbluray &&
            append_required_configure_options detected_config --enable-libbluray
        package_enabled "libdav1d" && library_exists dav1d &&
            append_required_configure_options detected_config --enable-libdav1d
        package_enabled "libvpl" && library_exists vpl &&
            append_required_configure_options detected_config --enable-libvpl
        package_enabled "libspeex" && library_exists speex &&
            append_required_configure_options detected_config --enable-libspeex
        package_enabled "libssh" && library_exists libssh &&
            append_required_configure_options detected_config --enable-libssh
        package_enabled "chromaprint" && library_exists libchromaprint &&
            append_required_configure_options detected_config --enable-chromaprint
        package_enabled "libjxl" && library_exists libjxl && library_exists libjxl_threads &&
            append_required_configure_options detected_config --enable-libjxl
        package_enabled "libtesseract" && library_exists tesseract &&
            append_required_configure_options detected_config --enable-libtesseract
        package_enabled "libzvbi" && library_exists zvbi-0.2 &&
            append_required_configure_options detected_config --enable-libzvbi
        package_enabled "libmodplug" && library_exists libmodplug &&
            append_required_configure_options detected_config --enable-libmodplug
        package_enabled "libgme" && library_exists libgme &&
            append_required_configure_options detected_config --enable-libgme
        package_enabled "libshine" && library_exists shine &&
            append_required_configure_options detected_config --enable-libshine
        package_enabled "libcaca" && library_exists caca &&
            append_required_configure_options detected_config --enable-libcaca
        package_enabled "libbs2b" && library_exists libbs2b &&
            append_required_configure_options detected_config --enable-libbs2b
        package_enabled "libjack" && library_exists jack &&
            append_required_configure_options detected_config --enable-libjack
        package_enabled "libv4l2" && library_exists libv4l2 &&
            append_required_configure_options detected_config --enable-libv4l2
        if package_enabled "xlib"; then
            if library_exists x11 xext xv; then
                append_required_configure_options detected_config --enable-xlib
            fi
            if library_exists xcb xcb-shm xcb-shape xcb-xfixes; then
                append_required_configure_options detected_config \
                    --enable-libxcb \
                    --enable-libxcb-shm \
                    --enable-libxcb-shape \
                    --enable-libxcb-xfixes
            fi
        fi
        package_enabled "libvpx" && library_exists vpx &&
            append_required_configure_options detected_config --enable-libvpx
        package_enabled "libopenh264" && library_exists "openh264 >= 1.3.0" &&
            append_required_configure_options detected_config --enable-libopenh264
        package_enabled "libopenmpt" && library_exists "libopenmpt >= 0.2.6557" &&
            append_required_configure_options detected_config --enable-libopenmpt
        package_enabled "librtmp" && library_exists librtmp &&
            append_required_configure_options detected_config --enable-librtmp
        package_enabled "librsvg" && library_exists librsvg-2.0 &&
            append_required_configure_options detected_config --enable-librsvg
        package_enabled "alsa" && library_exists alsa &&
            append_required_configure_options detected_config --enable-alsa
        package_enabled "libpulse" && library_exists libpulse &&
            append_required_configure_options detected_config --enable-libpulse
        package_enabled "sndio" && library_exists sndio &&
            append_required_configure_options detected_config --enable-sndio
        package_enabled "vaapi" && library_exists libva &&
            append_required_configure_options detected_config --enable-vaapi
        package_enabled "vdpau" && library_exists vdpau &&
            append_required_configure_options detected_config --enable-vdpau
        package_enabled "libdrm" && library_exists libdrm &&
            append_required_configure_options detected_config --enable-libdrm

        package_enabled "libsnappy" && header_exists snappy-c.h &&
            append_required_configure_options detected_config --enable-libsnappy
        package_enabled "libtwolame" && header_exists twolame.h &&
            append_required_configure_options detected_config --enable-libtwolame
        package_enabled "libvo-amrwbenc" && header_exists vo-amrwbenc/enc_if.h &&
            append_required_configure_options detected_config --enable-libvo-amrwbenc
        package_enabled "libgsm" &&
            { header_exists gsm.h || header_exists gsm/gsm.h; } &&
            append_required_configure_options detected_config --enable-libgsm
        package_enabled "ladspa" && header_exists ladspa.h &&
            append_required_configure_options detected_config --enable-ladspa
        package_enabled "opengl" && header_exists GL/glx.h &&
            append_required_configure_options detected_config --enable-opengl
        package_enabled "libflite" && header_exists flite/flite.h &&
            append_required_configure_options detected_config --enable-libflite
        is_true "$NONFREE_AND_GPL" && package_enabled "frei0r" &&
            header_exists frei0r.h &&
            append_required_configure_options detected_config --enable-frei0r
        if is_true "$NONFREE_AND_GPL"; then
            package_enabled "libsmbclient" && library_exists smbclient &&
                append_required_configure_options detected_config --enable-libsmbclient
            package_enabled "libcdio" && library_exists libcdio_paranoia &&
                append_required_configure_options detected_config --enable-libcdio
        fi

        if package_enabled "vulkan" && vulkan_headers_recent; then
            append_required_configure_options detected_config --enable-vulkan
            package_enabled "libshaderc" && library_exists "shaderc >= 2019.1" &&
                append_required_configure_options detected_config --enable-libshaderc
            package_enabled "libplacebo" &&
                library_exists "libplacebo >= 5.229.0" &&
                libplacebo_has_pl_alpha_none &&
                append_required_configure_options detected_config --enable-libplacebo
        fi

        # FFmpeg's NVENC/NVDEC/CUVID interfaces require ffnvcodec headers, not
        # nvcc. CUDA-compiled filters are a separate capability and are enabled
        # only when a validated toolkit and architecture flags are available.
        if [[ "${gpu_flag:-1}" -eq 0 ]] &&
            is_true "$NONFREE_AND_GPL" &&
            package_enabled "nv-codec-headers" &&
            library_exists ffnvcodec; then
            append_required_configure_options detected_config \
                --enable-cuda \
                --enable-cuvid \
                --enable-ffnvcodec \
                --enable-nvdec \
                --enable-nvenc

            if [[ -n "${CUDA_ROOT:-}" && -x "$CUDA_ROOT/bin/nvcc" &&
                -n "${nvidia_arch_type:-}" ]]; then
                append_required_configure_options detected_config --enable-cuda-nvcc
                detected_config+=(
                    --nvcc="$CUDA_ROOT/bin/nvcc"
                    "--nvccflags=-O2 $nvidia_arch_type"
                )
                extra_cflags+=" -I$CUDA_ROOT/include"
                extra_ldflags+=" -L$CUDA_ROOT/lib64"

                cuda_version="$(get_local_cuda_version "$CUDA_ROOT" || true)"
                cuda_major="${cuda_version%%.*}"
                if [[ "$cuda_major" =~ ^[0-9]+$ && "$cuda_major" -lt 13 ]] &&
                    [[ -e "$CUDA_ROOT/lib64/libnppc.so" ||
                        -e "$CUDA_ROOT/lib64/libnppc_static.a" ]]; then
                    append_required_configure_options detected_config --enable-libnpp
                elif [[ "$cuda_major" =~ ^[0-9]+$ && "$cuda_major" -ge 13 ]]; then
                    log "Skipping deprecated 'libnpp' integration because FFmpeg does not support it with CUDA 13+."
                fi
            else
                log "CUDA toolkit compilation is unavailable; retaining NVENC/NVDEC support from 'nv-codec-headers'."
            fi
        elif [[ "${gpu_flag:-1}" -eq 0 ]] &&
            is_true "$NONFREE_AND_GPL" &&
            package_enabled "nv-codec-headers"; then
            warn "'nv-codec-headers' are unavailable; omitting NVIDIA codec interfaces."
        fi

        base_config+=(
            "--extra-cflags=$(trim_whitespace "$extra_cflags")"
            "--extra-cxxflags=$(trim_whitespace "$extra_cxxflags")"
            "--extra-ldflags=$(trim_whitespace "$extra_ldflags")"
            "--extra-libs=$extra_libs"
        )

        append_unique_configure_options final_config _FFMPEG_CONFIGURE_OPTION_SEEN \
            "${base_config[@]}" "${detected_config[@]}" "${CONFIGURE_OPTIONS[@]}"

        execute env -u threads -u THREADS -u CONDA_PREFIX -u CONDA_DEFAULT_ENV \
            -u PYTHONHOME -u PYTHONPATH -u VIRTUAL_ENV \
            "$source_directory/configure" "${final_config[@]}"

        [[ -f ffbuild/config.mak ]] ||
            fail "FFmpeg configure did not produce 'ffbuild/config.mak'."
        grep -q '^CONFIG_FFMPEG=yes$' ffbuild/config.mak ||
            fail "FFmpeg configure disabled the 'ffmpeg' program."
        grep -q '^CONFIG_FFPROBE=yes$' ffbuild/config.mak ||
            fail "FFmpeg configure disabled 'ffprobe'."
        if is_true "$ffplay_enabled"; then
            grep -q '^CONFIG_FFPLAY=yes$' ffbuild/config.mak ||
                fail "FFmpeg configure disabled 'ffplay' despite SDL2 being selected."
        fi
        validate_required_ffmpeg_features ffbuild/config.mak

        execute make "-j$build_threads"
        staging_root="$(mktemp -d --tmpdir="$packages" ".ffmpeg-install-${ffmpeg_version}.XXXXXX")" ||
            fail "Unable to create an FFmpeg staging directory."
        staged_prefix="$staging_root/usr/local"
        execute make DESTDIR="$staging_root" install
        validate_ffmpeg_installation "$ffmpeg_version" "$ffplay_enabled" "$staged_prefix" false

        # Only mutate /usr/local after the complete staged install has passed
        # binary/version/capability checks.
        execute sudo make install
        validate_ffmpeg_installation "$ffmpeg_version" "$ffplay_enabled"
        safe_remove_tree "$staging_root" "$packages"
        build_done "ffmpeg" "n$ffmpeg_version"
    else
        validate_ffmpeg_installation "$ffmpeg_version" "$ffplay_enabled"
    fi

    cleanup
    exit_fn
}
