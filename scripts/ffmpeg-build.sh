#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Final FFmpeg Build
##  Build FFmpeg with all compiled dependencies
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Build FFmpeg
build_ffmpeg() {
    echo
    box_out_banner_ffmpeg "Building FFmpeg"
    require_vars workspace build_threads CC CXX

    # Get DXVA2 and other essential Windows header files
    if [[ "$VARIABLE_OS" == "WSL2" ]]; then
        install_windows_hardware_acceleration
    fi

    # Fetch latest release once (avoids duplicate network calls).
    local ffmpeg_release_page ffmpeg_latest_version ffmpeg_installed_version
    ffmpeg_release_page=$(curl -fsS "https://ffmpeg.org/releases/" 2>/dev/null || true)
    if [[ -n "$ffmpeg_release_page" ]]; then
        ffmpeg_latest_version=$(
            printf '%s' "$ffmpeg_release_page" |
            grep -oP 'ffmpeg-\K\d+\.\d+(?:\.\d+)?(?=\.tar\.xz)' |
            sort -ruV | head -n1
        )
    fi

    echo
    if command -v ffmpeg >/dev/null 2>&1; then
        ffmpeg_installed_version=$(ffmpeg -version 2>/dev/null | grep -oP '\d+\.\d+(?:\.\d+)*' | head -n1)
        log_update "The installed FFmpeg version is: n${ffmpeg_installed_version:-Unknown}"
    else
        log_update "FFmpeg is not currently installed"
    fi

    if [[ -n "$ffmpeg_latest_version" ]]; then
        log_update "The latest FFmpeg release version available: n$ffmpeg_latest_version"
    else
        log_update "The latest FFmpeg release version available is: Unknown"
    fi

    repo_version="${ffmpeg_latest_version:-6.1.2}"
    log_update "Using FFmpeg version n$repo_version"

    if build "ffmpeg" "n${repo_version}"; then
        sudo chown -R "$USER:$USER" "$PWD"
        download "https://ffmpeg.org/releases/ffmpeg-$repo_version.tar.xz" "ffmpeg-n${repo_version}.tar.xz"
        # Create build directory idempotently (no error if exists)
        mkdir -p build
        cd build || fail "Failed to cd into build directory. Line: $LINENO"
        # Full FFmpeg configure with all built libraries - threading bug fixed in 7.0.2
        # Prefer system Python config to avoid Conda/toolchain contamination during linking.
        local python3_cflags python3_libs python3_config
        python3_config=/usr/bin/python3-config
        if [[ ! -x "$python3_config" ]]; then
            python3_config="$(command -v python3-config)" || fail "python3-config not found. Line: $LINENO"
        fi
        python3_cflags="$("$python3_config" --cflags)" || fail "python3-config --cflags failed. Line: $LINENO"
        python3_libs="$("$python3_config" --ldflags --embed 2>/dev/null || "$python3_config" --ldflags)" || fail "python3-config --ldflags failed. Line: $LINENO"
        PYTHON3_CFLAGS="$python3_cflags"
        PYTHON3_LIBS="$python3_libs"
        export PYTHON3_CFLAGS PYTHON3_LIBS
        # Ensure we prefer locally-built pkgconf metadata first.
        export PKG_CONFIG_PATH="$workspace/lib/pkgconfig:$workspace/lib64/pkgconfig:$workspace/share/pkgconfig:$PKG_CONFIG_PATH"
        # Start with basic configuration to ensure ffmpeg builds, then add libraries conditionally
        BASIC_CONFIG=(
            --prefix=/usr/local
            --arch="$(uname -m)"
            --cpu=native
            --cc="$CC"
            --cxx="$CXX"
            --disable-shared
            --enable-static
            --enable-pthreads
            --enable-ffmpeg
            --enable-ffplay
            --enable-ffprobe
            --enable-version3
            --enable-bzlib
            --enable-iconv
            --enable-lzma
            --enable-sdl2
            --enable-vdpau
            --enable-zlib
            --extra-cflags="-I$workspace/include"
            --extra-ldflags="-L$workspace/lib64 -L$workspace/lib -L/usr/lib/x86_64-linux-gnu -L/usr/lib"
            --extra-libs="-ldl -lpthread -lm -lz"
            --pkg-config-flags="--static"
        )

        # Add additional libraries only if they are available and built
        OPTIONAL_LIBS=()

        # Check if workspace libraries exist before enabling them
        [[ -f "$workspace/lib/libx264.a" ]] && OPTIONAL_LIBS+=(--enable-libx264)
        [[ -f "$workspace/lib/libx265.a" ]] && OPTIONAL_LIBS+=(--enable-libx265)
        [[ -f "$workspace/lib/libxvid.a" ]] && OPTIONAL_LIBS+=(--enable-libxvid)
        [[ -f "$workspace/lib/libass.a" ]] && OPTIONAL_LIBS+=(--enable-libass)
        [[ -f "$workspace/lib/libfreetype.a" ]] && OPTIONAL_LIBS+=(--enable-libfreetype)
        [[ -f "$workspace/lib/libfontconfig.a" ]] && OPTIONAL_LIBS+=(--enable-libfontconfig)
        [[ -f "$workspace/lib/libmp3lame.a" ]] && OPTIONAL_LIBS+=(--enable-libmp3lame)
        [[ -f "$workspace/lib/libopus.a" ]] && OPTIONAL_LIBS+=(--enable-libopus)
        [[ -f "$workspace/lib/libvorbis.a" ]] && OPTIONAL_LIBS+=(--enable-libvorbis)
        [[ -f "$workspace/lib/libvpx.a" ]] && OPTIONAL_LIBS+=(--enable-libvpx)
        [[ -f "$workspace/lib/libwebp.a" ]] && OPTIONAL_LIBS+=(--enable-libwebp)
        [[ -f "$workspace/lib/libxml2.a" ]] && OPTIONAL_LIBS+=(--enable-libxml2)

        # Check for system-installed libraries (from APT)
        pkgconf --exists libbluray 2>/dev/null && OPTIONAL_LIBS+=(--enable-libbluray)

        # ═══════════════════════════════════════════════════════════════════════════
        # CUDA/NVENC Hardware Acceleration Support
        # ═══════════════════════════════════════════════════════════════════════════
        # Add CUDA/NVENC support if NVIDIA GPU detected and CUDA installed
        if [[ "${gpu_flag:-1}" -eq 0 ]] && [[ -d /usr/local/cuda ]]; then
            if [[ "${NONFREE_AND_GPL:-false}" != "true" ]]; then
                warn "NVIDIA GPU detected, but CUDA/NVENC requires --enable-nonfree. Skipping CUDA/NVENC. Re-run with --enable-gpl-and-non-free to enable."
            else
                log "Enabling CUDA/NVENC hardware acceleration..."

                # Verify nv-codec-headers are installed (required for FFmpeg NVENC)
                if ! pkgconf --exists ffnvcodec 2>/dev/null; then
                    log "Installing nv-codec-headers (required for NVENC)..."
                    local ffmpeg_build_dir="$(pwd)"
                    local nvcodec_dir="$packages/nv-codec-headers"
                    if [[ ! -d "$nvcodec_dir" ]]; then
                        git clone --depth 1 https://github.com/FFmpeg/nv-codec-headers.git "$nvcodec_dir"
                    fi
                    cd "$nvcodec_dir" || fail "Failed to cd into nv-codec-headers directory. Line: $LINENO"
                    execute make PREFIX="$workspace" install
                    cd "$ffmpeg_build_dir" || fail "Failed to return to FFmpeg build directory. Line: $LINENO"
                    log "nv-codec-headers installed successfully"
                else
                    log "nv-codec-headers already installed"
                fi

                # Enable CUDA-related FFmpeg features
                OPTIONAL_LIBS+=(
                    --enable-cuda
                    --enable-cuda-nvcc
                    --enable-cuvid
                    --enable-nvenc
                    --enable-nvdec
                    --enable-ffnvcodec
                )
                if command -v llvm-config >/dev/null 2>&1; then
                    OPTIONAL_LIBS+=(--enable-cuda-llvm)
                else
                    log "llvm-config not found; skipping --enable-cuda-llvm"
                fi

                # Check for libnpp (NVIDIA Performance Primitives) for scale_npp filter
                # Note: CUDA 12+ removed deprecated NPP functions that FFmpeg still uses
                # (nppiFilterSharpenBorder_8u_C1R, nppiRotate_8u_C1R, nppiResizeSqrPixel_8u_C1R)
                # Only enable libnpp for CUDA 11.x and earlier
                if [[ -f /usr/local/cuda/lib64/libnppc.so ]] || [[ -f /usr/local/cuda/lib64/libnppc_static.a ]]; then
                    local cuda_major_ver
                    cuda_major_ver=$(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9]+' | head -n1)
                    if [[ -n "$cuda_major_ver" ]] && [[ "$cuda_major_ver" -lt 12 ]]; then
                        OPTIONAL_LIBS+=(--enable-libnpp)
                        log "NVIDIA Performance Primitives (libnpp) enabled (CUDA $cuda_major_ver)"
                    else
                        log "NVIDIA Performance Primitives (libnpp) disabled - CUDA ${cuda_major_ver:-unknown} has incompatible NPP API"
                    fi
                fi

                # Add CUDA paths to compiler/linker flags
                local cuda_cflags cuda_ldflags
                cuda_cflags="-I/usr/local/cuda/include"
                cuda_ldflags="-L/usr/local/cuda/lib64"

                # Update BASIC_CONFIG with CUDA paths (append to existing flags)
                for i in "${!BASIC_CONFIG[@]}"; do
                    if [[ "${BASIC_CONFIG[i]}" == --extra-cflags=* ]]; then
                        BASIC_CONFIG[i]="${BASIC_CONFIG[i]} $cuda_cflags"
                    elif [[ "${BASIC_CONFIG[i]}" == --extra-ldflags=* ]]; then
                        BASIC_CONFIG[i]="${BASIC_CONFIG[i]} $cuda_ldflags"
                    fi
                done

                # Add nvcc flags if GPU architecture was detected
                if [[ -n "${nvidia_arch_type:-}" ]]; then
                    BASIC_CONFIG+=("--nvccflags=$nvidia_arch_type")
                    log "NVCC architecture flags: $nvidia_arch_type"
                fi

                log "CUDA/NVENC support enabled successfully"
            fi
        elif [[ "${gpu_flag:-1}" -eq 0 ]] && [[ ! -d "/usr/local/cuda" ]]; then
            warn "NVIDIA GPU detected but CUDA not found at /usr/local/cuda - NVENC disabled"
        fi

        # FFmpeg's configure script uses a `threads` variable internally (expects "yes"/"no").
        # Some environments export `threads=<n>` (e.g. `threads=32`), which breaks FFmpeg's
        # dependency resolution and silently disables building the `ffmpeg` binary
        # (while `ffprobe`/`ffplay` may still build). Sanitize those env vars for configure.
        local -a FINAL_CONFIG=()
        local -A seen_flags=()
        local dup_count opt
        dup_count=0
        for opt in "${BASIC_CONFIG[@]}" "${OPTIONAL_LIBS[@]}" "${CONFIGURE_OPTIONS[@]}"; do
            if [[ -z "${seen_flags[$opt]+x}" ]]; then
                FINAL_CONFIG+=("$opt")
                seen_flags[$opt]=1
            else
                ((dup_count++))
            fi
        done
        if ((dup_count > 0)); then
            log "Removed $dup_count duplicate configure flags"
        fi

        execute env -u threads -u THREADS -u CONDA_PREFIX -u CONDA_DEFAULT_ENV \
                    -u PYTHONHOME -u PYTHONPATH -u VIRTUAL_ENV \
                    ../configure "${FINAL_CONFIG[@]}"

        # Fail fast if configure disabled the main `ffmpeg` program.
        if [[ -f ffbuild/config.mak ]] && ! grep -q '^CONFIG_FFMPEG=yes$' ffbuild/config.mak; then
            fail "FFmpeg configure disabled the 'ffmpeg' program (CONFIG_FFMPEG!=yes). If you have an env var like 'threads=32', run 'unset threads' and rebuild."
        fi
        execute make "-j$build_threads"
        execute sudo make install

        # Fix x265 library symlink issues
        if command -v fix_x265_libs >/dev/null 2>&1; then
            fix_x265_libs
        fi

        build_done "ffmpeg" "n${repo_version}"
    fi

    # Add PulseAudio library path if missing to fix libpulsecommon-15.99.so not found error
    if ! grep -q /usr/lib/x86_64-linux-gnu/pulseaudio /etc/ld.so.conf.d/custom_libs.conf 2>/dev/null; then
        echo /usr/lib/x86_64-linux-gnu/pulseaudio | sudo tee -a /etc/ld.so.conf.d/custom_libs.conf >/dev/null
        log "Added PulseAudio library path to ldconfig"
    fi

    # Execute to ensure that all library changes are detected by ffmpeg
    sudo ldconfig

    # Display the version of each of the programs
    show_versions

    # Prompt the user to clean up the build files
    cleanup

    # Show exit message (exit_fn calls exit 0 internally)
    exit_fn
}
