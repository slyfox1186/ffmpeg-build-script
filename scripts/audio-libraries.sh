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
    require_vars workspace packages build_threads STATIC_VER

    # Build libsoxr
    find_git_repo "chirlu/soxr" "1" "T"
    if build "libsoxr" "$repo_version"; then
        download "https://github.com/chirlu/soxr/archive/refs/tags/$repo_version.tar.gz" "libsoxr-$repo_version.tar.gz"
        cmake_ninja_install "build" -S . \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF \
            -DWITH_OPENMP=OFF
        build_done "libsoxr" "$repo_version"
    fi
    append_configure_options_if_enabled "libsoxr" "--enable-libsoxr"

    # Build SDL2 (must use SDL2 branch - main branch is SDL3)
    sdl2_repo_version || fail "Failed to detect SDL2 version. Line: ${LINENO}"
    local sdl2_version="$repo_version"
    if build "sdl2" "$sdl2_version"; then
        download "$(sdl2_download_url "$sdl2_version")" "SDL2-$sdl2_version.tar.gz"
        cmake_ninja_install "build" -S . \
            -DBUILD_SHARED_LIBS=OFF -DSDL_ALSA_SHARED=OFF -DSDL_CCACHE=ON \
            -DSDL2_DISABLE_INSTALL_DOCS=ON
        # Fix missing iconv dependency in pkgconf (SDL2 uses iconv but doesn't declare it)
        if ! grep -q -- "-liconv" "$workspace/lib/pkgconfig/sdl2.pc" 2>/dev/null; then
            sed -i 's/^Libs:.*/& -liconv/' "$workspace/lib/pkgconfig/sdl2.pc"
        fi
        build_done "sdl2" "$sdl2_version"
    fi

    # Build libsndfile
    find_git_repo "libsndfile/libsndfile" "1" "T"
    if build "libsndfile" "$repo_version"; then
        download "https://github.com/libsndfile/libsndfile/releases/download/$repo_version/libsndfile-$repo_version.tar.xz"
        execute autoreconf -fi
        execute sh configure --prefix="$workspace" --enable-static --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libsndfile" "$repo_version"
    fi

    # Build libogg
    find_git_repo "xiph/ogg" "1" "T"
    if build "libogg" "$repo_version"; then
        download "https://github.com/xiph/ogg/archive/refs/tags/v$repo_version.tar.gz" "libogg-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=OFF \
            -DCPACK_{BINARY_DEB,SOURCE_ZIP}=OFF
        build_done "libogg" "$repo_version"
    fi

    # Build libfdk-aac (GPL and non-free only)
    if "$NONFREE_AND_GPL"; then
        find_git_repo "mstorsjo/fdk-aac" "1" "T"
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
    find_git_repo "xiph/vorbis" "1" "T"
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
    find_git_repo "xiph/opus" "1" "T"
    if build "libopus" "$repo_version"; then
        download "https://github.com/xiph/opus/archive/refs/tags/v$repo_version.tar.gz" "libopus-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF \
            -DCPACK_SOURCE_ZIP=OFF
        build_done "libopus" "$repo_version"
    fi
    append_configure_options_if_enabled "libopus" "--enable-libopus"

    # Build libmysofa
    find_git_repo "hoene/libmysofa" "1" "T"
    if build "libmysofa" "$repo_version"; then
        download "https://github.com/hoene/libmysofa/archive/refs/tags/v$repo_version.tar.gz" "libmysofa-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON
        build_done "libmysofa" "$repo_version"
    fi
    append_configure_options_if_enabled "libmysofa" "--enable-libmysofa"

    # Build opencore-amr
    find_git_repo "8143" "6"
    repo_version="${repo_version//debian\//}"
    if build "opencore-amr" "$repo_version"; then
        download "https://salsa.debian.org/multimedia-team/opencore-amr/-/archive/debian/$repo_version/opencore-amr-debian-$repo_version.tar.bz2" "opencore-amr-$repo_version.tar.bz2"
        execute sh configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "opencore-amr" "$repo_version"
    fi
    append_configure_options_if_enabled "opencore-amr" "--enable-libopencore-amrnb" "--enable-libopencore-amrwb"

    # Build liblame
    if build "liblame" "3.100"; then
        download "https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz" "liblame-3.100.tar.gz"
        execute sh configure --prefix="$workspace" \
                             --disable-{gtktest,shared} \
                             --enable-nasm \
                             --with-libiconv-prefix=/usr
        execute make "-j$build_threads"
        execute make install
        build_done "liblame" "3.100"
    fi
    append_configure_options_if_enabled "liblame" "--enable-libmp3lame"

    # Build libtheora
    if build "libtheora" "1.1.1"; then
        local ogg_include_dir ogg_library_dir vorbis_include_dir vorbis_library_dir sdl_prefix
        download "https://github.com/xiph/theora/archive/refs/tags/v1.1.1.tar.gz" "libtheora-1.1.1.tar.gz"
        ensure_autotools
        sed 's/-fforce-addr//g' configure > configure.patched
        chmod +x configure.patched
        execute mv configure.patched configure
        execute rm config.guess
        execute curl -LSso config.guess https://raw.githubusercontent.com/gcc-mirror/gcc/master/config.guess
        chmod +x config.guess
        ogg_include_dir="$(resolve_workspace_or_pkgconf_include_dir "libogg" "ogg" "$workspace/lib/libogg.a")"
        ogg_library_dir="$(resolve_workspace_or_pkgconf_library_dir "libogg" "ogg" "$workspace/lib/libogg.a")"

        vorbis_include_dir="$(resolve_workspace_or_pkgconf_include_dir "vorbis" "vorbis" "$workspace/lib/libvorbis.a")"
        vorbis_library_dir="$(resolve_workspace_or_pkgconf_library_dir "vorbis" "vorbis" "$workspace/lib/libvorbis.a")"

        if package_enabled "sdl2" && [[ -x "$workspace/bin/sdl2-config" ]]; then
            sdl_prefix="$workspace"
        elif command -v sdl2-config >/dev/null 2>&1; then
            sdl_prefix="$(sdl2-config --prefix)"
        else
            sdl_prefix="$(resolve_pkgconf_prefix "sdl2")"
        fi
        execute sh configure --prefix="$workspace" --disable-{examples,oggtest,sdltest,shared,vorbistest} \
                             --enable-static --with-ogg-includes="$ogg_include_dir" --with-ogg-libraries="$ogg_library_dir" \
                             --with-sdl-prefix="$sdl_prefix" --with-vorbis-includes="$vorbis_include_dir" \
                             --with-vorbis-libraries="$vorbis_library_dir"
        execute make "-j$build_threads"
        execute make install
        build_done "libtheora" "1.1.1"
    fi
    append_configure_options_if_enabled "libtheora" "--enable-libtheora"
}
