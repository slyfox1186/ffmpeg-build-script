#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

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
    box_out_banner_audio "Installing Audio Tools"

    # Build libsoxr
    find_git_repo "chirlu/soxr" "1" "T"
    if build "libsoxr" "$repo_version"; then
        download "https://github.com/chirlu/soxr/archive/refs/tags/$repo_version.tar.gz" "libsoxr-$repo_version.tar.gz"
        mkdir build; cd build || exit 1
        execute cmake -S ../ -Wno-dev -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$workspace" -DBUILD_TESTS=OFF
        execute make "-j$threads"
        execute make install
        build_done "libsoxr" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libsoxr")

    # Build SDL2
    git_caller "https://github.com/libsdl-org/SDL.git" "sdl2-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DSDL_ALSA_SHARED=OFF -DSDL_CCACHE=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi

    # Build libsndfile
    find_git_repo "libsndfile/libsndfile" "1" "T"
    if build "libsndfile" "$repo_version"; then
        download "https://github.com/libsndfile/libsndfile/releases/download/$repo_version/libsndfile-$repo_version.tar.xz"
        execute /usr/bin/autoreconf -fi
        execute ./configure --prefix="$workspace" --enable-static --with-pic
        execute make "-j$threads"
        execute make install
        build_done "libsndfile" "$repo_version"
    fi

    # Build libogg
    find_git_repo "xiph/ogg" "1" "T"
    if build "libogg" "$repo_version"; then
        download "https://github.com/xiph/ogg/archive/refs/tags/v$repo_version.tar.gz" "libogg-$repo_version.tar.gz"
        execute autoreconf -fi
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=OFF -DCPACK_{BINARY_DEB,SOURCE_ZIP}=OFF \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libogg" "$repo_version"
    fi

    # Build libfdk-aac (GPL and non-free only)
    if "$NONFREE_AND_GPL"; then
        find_git_repo "mstorsjo/fdk-aac" "1" "T"
        if build "libfdk-aac" "$repo_version"; then
            download "https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v$repo_version.tar.gz" "libfdk-aac-$repo_version.tar.gz"
            execute autoupdate
            execute ./autogen.sh
            execute ./configure --prefix="$workspace" --disable-shared
            execute make "-j$threads"
            execute make install
            build_done "libfdk-aac" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libfdk-aac")
    fi

    # Build vorbis
    find_git_repo "xiph/vorbis" "1" "T"
    if build "vorbis" "$repo_version"; then
        download "https://github.com/xiph/vorbis/archive/refs/tags/v$repo_version.tar.gz" "vorbis-$repo_version.tar.gz"
        execute ./autogen.sh
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DOGG_INCLUDE_DIR="$workspace/include" \
                      -DOGG_LIBRARY="$workspace/lib/libogg.a" -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "vorbis" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libvorbis")

    # Build libopus
    find_git_repo "xiph/opus" "1" "T"
    if build "libopus" "$repo_version"; then
        download "https://github.com/xiph/opus/archive/refs/tags/v$repo_version.tar.gz" "libopus-$repo_version.tar.gz"
        execute autoreconf -fis
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libopus" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libopus")

    # Build libmysofa
    find_git_repo "hoene/libmysofa" "1" "T"
    if build "libmysofa" "$repo_version"; then
        download "https://github.com/hoene/libmysofa/archive/refs/tags/v$repo_version.tar.gz" "libmysofa-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libmysofa" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libmysofa")

    # Build opencore-amr
    find_git_repo "8143" "6"
    repo_version="${repo_version//debian\//}"
    if build "opencore-amr" "$repo_version"; then
        download "https://salsa.debian.org/multimedia-team/opencore-amr/-/archive/debian/$repo_version/opencore-amr-debian-$repo_version.tar.bz2" "opencore-amr-$repo_version.tar.bz2"
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j${threads}"
        execute make install
        build_done "opencore-amr" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libopencore-"{amrnb,amrwb})

    # Build liblame
    if build "liblame" "3.100"; then
        download "https://master.dl.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz?viasf=1" "liblame-3.100.tar.gz"
        execute ./configure --prefix="$workspace" --disable-{gtktest,shared} \
                            --enable-nasm --with-libiconv-prefix=/usr
        execute make "-j$threads"
        execute make install
        build_done "liblame" "3.100"
    fi
    CONFIGURE_OPTIONS+=("--enable-libmp3lame")

    # Build libtheora
    if build "libtheora" "1.1.1"; then
        download "https://github.com/xiph/theora/archive/refs/tags/v1.1.1.tar.gz" "libtheora-1.1.1.tar.gz"
        execute autoupdate
        execute ./autogen.sh
        sed "s/-fforce-addr//g" "configure" > "configure.patched"
        chmod +x "configure.patched"
        execute mv "configure.patched" "configure"
        execute rm "config.guess"
        execute curl -LSso "config.guess" "https://raw.githubusercontent.com/gcc-mirror/gcc/master/config.guess"
        chmod +x "config.guess"
        execute ./configure --prefix="$workspace" --disable-{examples,oggtest,sdltest,shared,vorbistest} \
                            --enable-static --with-ogg-includes="$workspace/include" --with-ogg-libraries="$workspace/lib" \
                            --with-ogg="$workspace" --with-sdl-prefix="$workspace" --with-vorbis-includes="$workspace/include" \
                            --with-vorbis-libraries="$workspace/lib" --with-vorbis="$workspace"
        execute make "-j$threads"
        execute make install
        build_done "libtheora" "1.1.1"
    fi
    CONFIGURE_OPTIONS+=("--enable-libtheora")

    log "Audio libraries installation completed"
}
