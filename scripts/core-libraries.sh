#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Core Libraries
##  Essential libraries for multimedia processing (yasm, nasm, image libs, etc.)
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install core libraries
install_core_libraries() {
    echo
    log "Installing Core Libraries"

    # Build yasm
    find_git_repo "yasm/yasm" "1" "T"
    if build "yasm" "$repo_version"; then
        download "http://www.tortall.net/projects/yasm/releases/yasm-$repo_version.tar.gz" "yasm-$repo_version.tar.gz"
        execute ./configure --prefix="$workspace"
        execute make "-j$threads"
        execute sudo make install
        build_done "yasm" "$repo_version"
    fi

    # Build nasm
    find_latest_nasm_version
    if build "nasm" "$latest_nasm_version"; then
        find_latest_nasm_version
        download "https://www.nasm.us/pub/nasm/stable/nasm-$latest_nasm_version.tar.xz"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-pedantic --enable-ccache
        execute make "-j$threads"
        execute sudo make install
        build_done "nasm" "$latest_nasm_version"
    fi

    # Build giflib
    if build "giflib" "5.2.2"; then
        download "https://cfhcable.dl.sourceforge.net/project/giflib/giflib-5.2.2.tar.gz?viasf=1"
        # Parallel building not available for this library
        execute make
        execute sudo make PREFIX="$workspace" install
        build_done "giflib" "5.2.2"
    fi

    # Build libiconv
    gnu_repo "https://ftp.gnu.org/gnu/libiconv/"
    if [[ -z "$repo_version" ]]; then
        repo_version=$(curl -fsS "https://gnu.mirror.constant.com/libiconv/" | grep -oP 'href="[^"]*-\K\d+\.\d+(?=\.tar\.gz)' | sort -ruV | head -n1)
        download_libiconv="https://gnu.mirror.constant.com/libiconv/libiconv-$repo_version.tar.gz"
    else
        download_libiconv="https://ftp.gnu.org/gnu/libiconv/libiconv-$repo_version.tar.gz"
    fi
    if build "libiconv" "$repo_version"; then
        download "$download_libiconv"
        execute ./configure --prefix="$workspace" --enable-static --with-pic
        execute make "-j$threads"
        execute sudo make install
        fix_libiconv
        build_done "libiconv" "$repo_version"
    fi

    # Build libxml2 (Ubuntu Bionic fails to build xml2)
    if [[ "$STATIC_VER" != "18.04" ]]; then
        libxml2_version
        if build "libxml2" "$repo_version"; then
            download "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v$repo_version/libxml2-v$repo_version.tar.bz2" "libxml2-$repo_version.tar.bz2"
            CFLAGS+=" -DNOLIBTOOL"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
            execute ninja "-j$threads" -C build
            execute sudo ninja -C build install
            build_done "libxml2" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libxml2")
    fi

    # Build libpng
    find_git_repo "pnggroup/libpng" "1" "T"
    if build "libpng" "$repo_version"; then
        download "https://github.com/pnggroup/libpng/archive/refs/tags/v1.6.43.tar.gz" "libpng-$repo_version.tar.gz"
        execute autoupdate
        execute autoreconf -fi
        execute ./configure --prefix="$workspace" --enable-hardware-optimizations=yes --with-pic
        execute make "-j$threads"
        execute sudo make install-header-links install-library-links install
        build_done "libpng" "$repo_version"
    fi

    # Build libtiff
    libtiff_version
    if build "libtiff" "$repo_version"; then
        download "https://gitlab.com/libtiff/libtiff/-/archive/v$repo_version/libtiff-v$repo_version.tar.bz2" "libtiff-$repo_version.tar.bz2"
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-{docs,sphinx,tests} --enable-cxx --with-pic
        execute make "-j$threads"
        execute sudo make install
        build_done "libtiff" "$repo_version"
    fi

    # Build aribb24 (GPL and non-free only)
    if "$NONFREE_AND_GPL"; then
        find_git_repo "nkoriyama/aribb24" "1" "T"
        if build "aribb24" "$repo_version"; then
            download "https://github.com/nkoriyama/aribb24/archive/refs/tags/v$repo_version.tar.gz" "aribb24-$repo_version.tar.gz"
            execute mkdir m4
            execute autoreconf -fi -I/usr/share/aclocal
            execute ./configure --prefix="$workspace" --disable-shared --enable-static
            execute make "-j$threads"
            execute sudo make install
            build_done "aribb24" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libaribb24")
    fi

    # Fix library issues
    fix_libstd_libs

    log "Core libraries installation completed"
}

# Library fix functions
fix_libiconv() {
    if [[ -f "$workspace/lib/libiconv.so.2" ]]; then
        execute sudo cp -f "$workspace/lib/libiconv.so.2" "/usr/lib/libiconv.so.2"
        execute sudo ln -sf "/usr/lib/libiconv.so.2" "/usr/lib/libiconv.so"
    else
        fail "Unable to locate the file \"$workspace/lib/libiconv.so.2\""
    fi
}

fix_libstd_libs() {
    local libstdc_path
    libstdc_path=$(find /usr/lib/x86_64-linux-gnu/ -type f -name 'libstdc++.so.6.0.*' | sort -ruV | head -n1)
    if [[ ! -f "/usr/lib/x86_64-linux-gnu/libstdc++.so" ]] && [[ -f "$libstdc_path" ]]; then
        sudo ln -sf "$libstdc_path" "/usr/lib/x86_64-linux-gnu/libstdc++.so"
    fi
}

fix_x265_libs() {
    local x265_libs x265_libs_trim
    x265_libs=$(find "$workspace/lib/" -type f -name 'libx265.so.*' | sort -rV | head -n1)
    x265_libs_trim=$(echo "$x265_libs" | sed "s:.*/::" | head -n1)

    sudo cp -f "$x265_libs" "/usr/lib/x86_64-linux-gnu"
    sudo ln -sf "/usr/lib/x86_64-linux-gnu/$x265_libs_trim" "/usr/lib/x86_64-linux-gnu/libx265.so"
}

# Version finding functions
find_latest_nasm_version() {
    latest_nasm_version=$(
                    curl -fsS "https://www.nasm.us/pub/nasm/stable/" |
                    grep -oP 'nasm-\K[0-9]+\.[0-9]+\.[0-9]+(?=\.tar\.xz)' |
                    sort -ruV | head -n1
                )
}

get_openssl_version() {
    openssl_version=$(
                curl -fsS "https://openssl-library.org/source/" |
                grep -oP 'openssl-\K3\.0\.[0-9]+' | sort -ruV |
                head -n1
            )
}