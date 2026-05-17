#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

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
        execute sh configure --prefix="$workspace"
        execute make "-j$build_threads"
        execute make install
        build_done "yasm" "$repo_version"
    fi

    # Build nasm
    find_latest_nasm_version
    local nasm_version="$latest_nasm_version"
    if build "nasm" "$nasm_version"; then
        download "https://www.nasm.us/pub/nasm/releasebuilds/$nasm_version/nasm-$nasm_version.tar.xz"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-pedantic --enable-ccache
        execute make "-j$build_threads"
        execute make install
        build_done "nasm" "$nasm_version"
    fi

    # Build giflib
    local giflib_version
    if giflib_repo_version; then
        giflib_version="$repo_version"
    else
        giflib_version="5.2.2"
        warn "Falling back to giflib version $giflib_version because upstream version detection failed."
    fi
    if build "giflib" "$giflib_version"; then
        download "$(giflib_download_url "$giflib_version")" "giflib-$giflib_version.tar.gz"
        # Build only the library, skip documentation (requires ImageMagick)
        execute make libgif.a libgif.so
        execute make PREFIX="$workspace" install-lib install-include
        build_done "giflib" "$giflib_version"
    fi

    # Build libiconv
    gnu_repo "$GNU_PRIMARY_MIRROR/libiconv/"
    if build "libiconv" "$repo_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/libiconv/libiconv-$repo_version.tar.gz" "$GNU_FALLBACK_MIRROR/libiconv/libiconv-$repo_version.tar.gz"
        execute sh configure --prefix="$workspace" --enable-static --with-pic
        execute make "-j$build_threads"
        execute make install
        fix_libiconv
        build_done "libiconv" "$repo_version"
    fi

    # Build libxml2
    libxml2_version
    if build "libxml2" "$repo_version"; then
        download "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v$repo_version/libxml2-v$repo_version.tar.bz2?ref_type=tags" "libxml2-$repo_version.tar.bz2"
        # Save flags before modification and restore after build
        save_compiler_flags
        CFLAGS+=" -DNOLIBTOOL"
        cmake_ninja_install "build" -DBUILD_SHARED_LIBS=OFF
        restore_compiler_flags
        build_done "libxml2" "$repo_version"
    fi
    append_configure_options_if_enabled "libxml2" "--enable-libxml2"

    # Build libpng
    find_git_repo "pnggroup/libpng" "1" "T"
    if build "libpng" "$repo_version"; then
        download "https://github.com/pnggroup/libpng/archive/refs/tags/v$repo_version.tar.gz" "libpng-$repo_version.tar.gz"
        ensure_autotools
        execute sh configure --prefix="$workspace" --enable-hardware-optimizations=yes --with-pic
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
        execute sh configure --prefix="$workspace" --disable-{docs,sphinx,tests} --enable-cxx --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libtiff" "$repo_version"
    fi

    # aribb24 is now installed via system package manager (libaribb24-dev)
    if "$NONFREE_AND_GPL"; then
        append_configure_options_if_enabled "libaribb24" "--enable-libaribb24"
    fi

    # Fix library issues
    fix_libstd_libs
}

# Note: Library fix functions (fix_libiconv, fix_libstd_libs, fix_x265_libs, find_latest_nasm_version)
# are defined in support-libraries.sh to avoid duplicates
