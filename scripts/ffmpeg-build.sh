#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

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

    # Get DXVA2 and other essential Windows header files
    if [[ "$VARIABLE_OS" == "WSL2" ]]; then
        install_windows_hardware_acceleration
    fi

    # Run the 'ffmpeg -version' command and capture its output
    if ffmpeg_version=$(curl -fsS "https://github.com/FFmpeg/FFmpeg/tags/" | grep -Ev '\-dev' | grep -oP '/tag/n\K\d+\.\d+[\d\.]*' | sort -ruV | head -n1); then

        # Get the installed version
        ffmpeg_installed_version=$(ffmpeg -version 2>/dev/null | grep -oP '\d+\.\d+[\d\.]*' | head -n1)
        # Format the version number with the desired prefix
        ffmpeg_version_formatted="n$ffmpeg_version"

        echo
        log_update "The installed FFmpeg version is: n$ffmpeg_installed_version"
        log_update "The latest FFmpeg release version available: $ffmpeg_version_formatted"
    else
        echo
        log_update "Failed to retrieve an installed FFmpeg version"
        log_update "The latest FFmpeg release version available is: Unknown"
    fi

    # Minimal flags for debugging - remove complex optimizations
    CC="$CC"
    CXX="$CXX"

    # Force FFmpeg version 6.1.2 for stable threading support
    repo_version="6.1.2"
    log_update "Using FFmpeg version n$repo_version for stable threading support"

    if build "ffmpeg" "n${repo_version}"; then
        sudo chmod -R 777 "$PWD"
        download "https://ffmpeg.org/releases/ffmpeg-$repo_version.tar.xz" "ffmpeg-n${repo_version}.tar.xz"
        mkdir build
        cd build || exit 1
        # Full FFmpeg configure with all built libraries - threading bug fixed in 7.0.2
        # Set environment for Conda Python 3.12 (needed for build dependencies)
        export PYTHON3_CFLAGS="$(python3-config --cflags)"
        export PYTHON3_LIBS="$(python3-config --ldflags)"
        # Detect Conda environment dynamically
        CONDA_PREFIX="${CONDA_PREFIX:-$(dirname $(dirname $(which python3)))}"
        # Force use of system Python libraries instead of Conda for final linking
        export PKG_CONFIG_PATH="$workspace/lib/pkgconfig:$workspace/lib64/pkgconfig:$workspace/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig:$CONDA_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH"
        # Start with basic configuration to ensure ffmpeg builds, then add libraries conditionally
        BASIC_CONFIG=(
            --prefix=/usr/local
            --arch="$(uname -m)"
            --cpu=native
            --cc="$CC" --cxx="$CXX"
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
        
        ../configure "${BASIC_CONFIG[@]}" "${OPTIONAL_LIBS[@]}" "${CONFIGURE_OPTIONS[@]}"
        execute make "-j$threads"
        execute sudo make install
        
        # Fix x265 library symlink issues
        fix_x265_libs
        
        build_done "ffmpeg" "n${repo_version}"
    fi

    # Add PulseAudio library path if missing to fix libpulsecommon-15.99.so not found error
    if ! grep -q "/usr/lib/x86_64-linux-gnu/pulseaudio" /etc/ld.so.conf.d/custom_libs.conf 2>/dev/null; then
        echo "/usr/lib/x86_64-linux-gnu/pulseaudio" | sudo tee -a /etc/ld.so.conf.d/custom_libs.conf >/dev/null
        log "Added PulseAudio library path to ldconfig"
    fi

    # Execute to ensure that all library changes are detected by ffmpeg
    sudo ldconfig

    # Display the version of each of the programs
    show_versions

    # Prompt the user to clean up the build files
    cleanup

    # Show exit message
    exit_fn

    log "FFmpeg build completed"
}