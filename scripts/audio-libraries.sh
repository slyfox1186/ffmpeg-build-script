#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Audio Libraries
##  Audio codecs and processing libraries (soxr, SDL2, ogg, vorbis, opus, etc.)
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install audio libraries
install_audio_libraries() {
    echo
    box_out_banner "Installing Audio Tools"
    require_vars workspace packages build_threads

    # Build libsoxr
    fetch_version_if_enabled "libsoxr" find_git_repo "chirlu/soxr" "1"
    if build "libsoxr" "$repo_version"; then
        download "https://github.com/chirlu/soxr/archive/refs/tags/$repo_version.tar.gz" "libsoxr-$repo_version.tar.gz"
        cmake_ninja_install "build" -S . \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF \
            -DWITH_OPENMP=OFF
        build_done "libsoxr" "$repo_version"
    fi
    append_configure_options_if_enabled "libsoxr" "--enable-libsoxr"

    # Build SDL2 (must use SDL2 branch - main branch is SDL3)
    fetch_version_if_enabled "sdl2" sdl2_repo_version || fail "Failed to detect SDL2 version. Line: ${LINENO}"
    local sdl2_version="$repo_version"
    if build "sdl2" "$sdl2_version"; then
        download "$(sdl2_download_url "$sdl2_version")" "SDL2-$sdl2_version.tar.gz"
        cmake_ninja_install "build" -S . \
            -DBUILD_SHARED_LIBS=OFF -DSDL_ALSA_SHARED=OFF -DSDL_CCACHE=ON \
            -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TESTS=OFF \
            -DSDL2_DISABLE_INSTALL_DOCS=ON
        # A static workspace libiconv must be represented in SDL's private link
        # dependencies; glibc-based system builds do not need -liconv.
        if package_enabled "libiconv" && [[ -f "$workspace/lib/libiconv.a" ]]; then
            pkgconfig_add_private_lib "sdl2" "-liconv"
        fi
        build_done "sdl2" "$sdl2_version"
    fi

    # Build libsndfile
    fetch_version_if_enabled "libsndfile" find_git_repo "libsndfile/libsndfile" "1"
    if build "libsndfile" "$repo_version"; then
        download "https://github.com/libsndfile/libsndfile/releases/download/$repo_version/libsndfile-$repo_version.tar.xz"
        execute sh configure --prefix="$workspace" \
            --disable-{alsa,full-suite,shared,sndio,sqlite} \
            --enable-static --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libsndfile" "$repo_version"
    fi

    # Build libogg
    fetch_version_if_enabled "libogg" find_git_repo "xiph/ogg" "1"
    if build "libogg" "$repo_version"; then
        download "https://github.com/xiph/ogg/archive/refs/tags/v$repo_version.tar.gz" "libogg-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_TESTING=OFF \
            -DBUILD_SHARED_LIBS=OFF -DINSTALL_DOCS=OFF
        build_done "libogg" "$repo_version"
    fi

    # Build libfdk-aac (GPL and non-free only)
    if is_true "$NONFREE_AND_GPL"; then
        fetch_version_if_enabled "libfdk-aac" find_git_repo "mstorsjo/fdk-aac" "1"
        if build "libfdk-aac" "$repo_version"; then
            download "https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v$repo_version.tar.gz" "libfdk-aac-$repo_version.tar.gz"
            ensure_autotools
            execute sh configure --prefix="$workspace" --disable-shared
            execute make "-j$build_threads"
            execute make install
            build_done "libfdk-aac" "$repo_version"
        fi
        append_configure_options_if_enabled "libfdk-aac" "--enable-libfdk-aac"
    fi

    # Build vorbis
    fetch_version_if_enabled "vorbis" find_git_repo "xiph/vorbis" "1"
    if build "vorbis" "$repo_version"; then
        local ogg_include_dir ogg_library
        download "https://github.com/xiph/vorbis/archive/refs/tags/v$repo_version.tar.gz" "vorbis-$repo_version.tar.gz"
        ogg_include_dir="$(resolve_workspace_or_pkgconf_include_dir "libogg" "ogg" "$workspace/lib/libogg.a")"
        ogg_library="$(resolve_workspace_or_pkgconf_library_file "libogg" "ogg" "ogg" "$workspace/lib/libogg.a")"
        cmake_ninja_install "build" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF \
            -DOGG_INCLUDE_DIR="$ogg_include_dir" -DOGG_LIBRARY="$ogg_library"
        build_done "vorbis" "$repo_version"
    fi
    append_configure_options_if_enabled "vorbis" "--enable-libvorbis"

    # Build libopus
    fetch_version_if_enabled "libopus" find_git_repo "xiph/opus" "1"
    if build "libopus" "$repo_version"; then
        download "https://github.com/xiph/opus/archive/refs/tags/v$repo_version.tar.gz" "libopus-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF \
            -DBUILD_TESTING=OFF -DOPUS_BUILD_PROGRAMS=OFF -DOPUS_BUILD_TESTING=OFF
        build_done "libopus" "$repo_version"
    fi
    append_configure_options_if_enabled "libopus" "--enable-libopus"

    # Build libmysofa
    fetch_version_if_enabled "libmysofa" find_git_repo "hoene/libmysofa" "1"
    if build "libmysofa" "$repo_version"; then
        download "https://github.com/hoene/libmysofa/archive/refs/tags/v$repo_version.tar.gz" "libmysofa-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -DBUILD_TESTS=OFF
        build_done "libmysofa" "$repo_version"
    fi
    append_configure_options_if_enabled "libmysofa" "--enable-libmysofa"

    # Build opencore-amr
    local opencore_version
    if fetch_version_if_enabled "opencore-amr" opencore_amr_version; then
        opencore_version="$repo_version"
    else
        opencore_version="0.1.6"
        warn "Falling back to opencore-amr $opencore_version because its official release index is unavailable."
    fi
    if build "opencore-amr" "$opencore_version"; then
        download \
            "https://downloads.sourceforge.net/project/opencore-amr/opencore-amr/opencore-amr-$opencore_version.tar.gz" \
            "opencore-amr-$opencore_version.tar.gz"
        execute sh configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "opencore-amr" "$opencore_version"
    fi
    append_configure_options_if_enabled "opencore-amr" "--enable-libopencore-amrnb" "--enable-libopencore-amrwb"

    # Build liblame
    if build "liblame" "3.100"; then
        local -a lame_iconv_options=()
        download "https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz" "liblame-3.100.tar.gz"
        if package_enabled "libiconv" && [[ -f "$workspace/lib/libiconv.a" ]]; then
            lame_iconv_options=(--with-libiconv-prefix="$workspace")
        fi
        execute sh configure --prefix="$workspace" \
                             --disable-{gtktest,shared} \
                             --enable-nasm \
                             "${lame_iconv_options[@]}"
        execute make "-j$build_threads"
        execute make install
        build_done "liblame" "3.100"
    fi
    append_configure_options_if_enabled "liblame" "--enable-libmp3lame"

    # Build libtheora
    fetch_version_if_enabled "libtheora" find_git_repo "xiph/theora" "1"
    local theora_version="$repo_version"
    if build "libtheora" "$theora_version"; then
        local ogg_include_dir ogg_library_dir
        download "https://github.com/xiph/theora/archive/refs/tags/v$theora_version.tar.gz" \
            "libtheora-$theora_version.tar.gz"
        ensure_autotools
        ogg_include_dir="$(resolve_workspace_or_pkgconf_include_dir "libogg" "ogg" "$workspace/lib/libogg.a")"
        ogg_library_dir="$(resolve_workspace_or_pkgconf_library_dir "libogg" "ogg" "$workspace/lib/libogg.a")"

        # Vorbis and SDL are requirements of upstream's example programs, not
        # of the core Theora/Ogg library consumed by FFmpeg.
        execute sh configure --prefix="$workspace" \
            --disable-{doc,examples,oggtest,sdltest,shared,spec,vorbistest} \
            --enable-static \
            --with-ogg-includes="$ogg_include_dir" \
            --with-ogg-libraries="$ogg_library_dir"
        execute make "-j$build_threads"
        execute make install
        build_done "libtheora" "$theora_version"
    fi
    append_configure_options_if_enabled "libtheora" "--enable-libtheora"
}
