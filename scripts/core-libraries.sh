#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

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
    box_out_banner "Installing Core Libraries"
    require_vars workspace packages build_threads STATIC_VER

    # Build yasm
    find_git_repo "yasm/yasm" "1" "T"
    if build "yasm" "$repo_version"; then
        download "https://www.tortall.net/projects/yasm/releases/yasm-$repo_version.tar.gz" "yasm-$repo_version.tar.gz"
        execute ./configure --prefix="$workspace"
        execute make "-j$build_threads"
        execute make install
        build_done "yasm" "$repo_version"
    fi

    # Build nasm
    find_latest_nasm_version
    if build "nasm" "$latest_nasm_version"; then
        find_latest_nasm_version
        download "https://www.nasm.us/pub/nasm/releasebuilds/$latest_nasm_version/nasm-$latest_nasm_version.tar.xz"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-pedantic --enable-ccache
        execute make "-j$build_threads"
        execute make install
        build_done "nasm" "$latest_nasm_version"
    fi

    # Build giflib
    giflib_version=$(curl -fsS "https://sourceforge.net/projects/giflib/files/" 2>/dev/null | grep -oP 'giflib-\K([0-9]+\.[0-9]+(?:\.[0-9]+)?)' | sort -ruV | head -n1)
    giflib_version="${giflib_version:-5.2.2}"
    if build "giflib" "$giflib_version"; then
        download "https://gigenet.dl.sourceforge.net/project/giflib/giflib-$giflib_version.tar.gz?viasf=1"
        # Install ImageMagick for giflib documentation
        if ! command -v convert >/dev/null 2>&1; then
            log "Installing ImageMagick for giflib documentation"
            execute sudo apt update
            execute sudo apt -y install imagemagick
        fi
        # Parallel building not available for this library
        execute make
        execute make PREFIX="$workspace" install
        build_done "giflib" "$giflib_version"
    fi

    # Build libiconv
    gnu_repo "https://ftp.gnu.org/gnu/libiconv/"
    if build "libiconv" "$repo_version"; then
        download_with_fallback "https://ftp.gnu.org/gnu/libiconv/libiconv-$repo_version.tar.gz" "https://mirror.team-cymru.com/gnu/libiconv/libiconv-$repo_version.tar.gz"
        execute ./configure --prefix="$workspace" --enable-static --with-pic
        execute make "-j$build_threads"
        execute make install
        fix_libiconv
        build_done "libiconv" "$repo_version"
    fi

    # Build libxml2 (Ubuntu Bionic fails to build xml2)
    if [[ "$STATIC_VER" != "18.04" ]]; then
        libxml2_version
        if build "libxml2" "$repo_version"; then
            download "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v$repo_version/libxml2-v$repo_version.tar.bz2" "libxml2-$repo_version.tar.bz2"
            # Save flags before modification and restore after build
            save_compiler_flags
            CFLAGS+=" -DNOLIBTOOL"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
            execute ninja "-j$build_threads" -C build
            execute ninja -C build install
            restore_compiler_flags
            build_done "libxml2" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libxml2")
    fi

    # Build libpng
    find_git_repo "pnggroup/libpng" "1" "T"
    if build "libpng" "$repo_version"; then
        download "https://github.com/pnggroup/libpng/archive/refs/tags/v$repo_version.tar.gz" "libpng-$repo_version.tar.gz"
        execute autoupdate
        execute autoreconf -fi
        execute ./configure --prefix="$workspace" --enable-hardware-optimizations=yes --with-pic
        execute make "-j$build_threads"
        execute make install-header-links install-library-links install
        build_done "libpng" "$repo_version"
    fi

    # Build libtiff
    libtiff_version
    if build "libtiff" "$repo_version"; then
        download "https://gitlab.com/libtiff/libtiff/-/archive/v$repo_version/libtiff-v$repo_version.tar.bz2" "libtiff-$repo_version.tar.bz2"
        # Use autoreconf instead of autogen.sh to avoid hanging downloads
        execute autoreconf -fi
        execute ./configure --prefix="$workspace" --disable-{docs,sphinx,tests} --enable-cxx --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libtiff" "$repo_version"
    fi

    # aribb24 is now installed via system package manager (libaribb24-dev)
    if "$NONFREE_AND_GPL"; then
        CONFIGURE_OPTIONS+=("--enable-libaribb24")
    fi

    # Fix library issues
    fix_libstd_libs

    log "Core libraries installation completed"
}

# Note: Library fix functions (fix_libiconv, fix_libstd_libs, fix_x265_libs, find_latest_nasm_version)
# are defined in support-libraries.sh to avoid duplicates
