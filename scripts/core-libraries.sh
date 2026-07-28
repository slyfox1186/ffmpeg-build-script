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
    require_vars workspace packages build_threads

    # Build yasm
    fetch_version_if_enabled "yasm" find_git_repo "yasm/yasm" "1"
    if build "yasm" "$repo_version"; then
        download "https://www.tortall.net/projects/yasm/releases/yasm-$repo_version.tar.gz" "yasm-$repo_version.tar.gz"
        execute sh configure --prefix="$workspace"
        execute make "-j$build_threads"
        execute make install
        build_done "yasm" "$repo_version"
    fi

    # Build nasm
    local nasm_version=""
    if package_enabled "nasm"; then
        find_latest_nasm_version
        nasm_version="$latest_nasm_version"
    fi
    if build "nasm" "$nasm_version"; then
        download "https://www.nasm.us/pub/nasm/releasebuilds/$nasm_version/nasm-$nasm_version.tar.xz"
        ensure_autotools
        # NASM has no --enable-ccache configure option. The compiler wrappers
        # already placed on PATH provide caching without passing an unknown flag.
        execute sh configure --prefix="$workspace" --disable-pedantic
        execute make "-j$build_threads"
        execute make install
        build_done "nasm" "$nasm_version"
    fi

    # Build giflib
    local giflib_version
    if fetch_version_if_enabled "giflib" giflib_repo_version; then
        giflib_version="$repo_version"
    else
        giflib_version="5.2.2"
        warn "Falling back to giflib version $giflib_version because upstream version detection failed."
    fi
    if build "giflib" "$giflib_version"; then
        download "$(giflib_download_url "$giflib_version")" "giflib-$giflib_version.tar.gz"
        # FFmpeg needs only the static library and public header. Upstream's
        # install-lib target also requires and installs libgif.so, so install
        # these two artifacts directly instead of building unused shared/tools/docs.
        execute make "-j$build_threads" libgif.a
        execute install -Dm0644 libgif.a "$workspace/lib/libgif.a"
        execute install -Dm0644 gif_lib.h "$workspace/include/gif_lib.h"
        build_done "giflib" "$giflib_version"
    fi

    # Build libiconv
    fetch_version_if_enabled "libiconv" gnu_repo "$GNU_PRIMARY_MIRROR/libiconv/"
    if build "libiconv" "$repo_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/libiconv/libiconv-$repo_version.tar.gz" "$GNU_FALLBACK_MIRROR/libiconv/libiconv-$repo_version.tar.gz"
        execute sh configure --prefix="$workspace" --disable-shared --enable-static --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libiconv" "$repo_version"
    fi

    # Build libxml2
    fetch_version_if_enabled "libxml2" libxml2_version
    if build "libxml2" "$repo_version"; then
        download "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v$repo_version/libxml2-v$repo_version.tar.bz2?ref_type=tags" "libxml2-$repo_version.tar.bz2"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF \
            -DLIBXML2_WITH_DOCS=OFF \
            -DLIBXML2_WITH_MODULES=OFF \
            -DLIBXML2_WITH_PROGRAMS=OFF \
            -DLIBXML2_WITH_PYTHON=OFF \
            -DLIBXML2_WITH_TESTS=OFF
        build_done "libxml2" "$repo_version"
    fi
    append_configure_options_if_enabled "libxml2" "--enable-libxml2"

    # Build libpng
    fetch_version_if_enabled "libpng" find_git_repo "pnggroup/libpng" "1"
    if build "libpng" "$repo_version"; then
        download "https://github.com/pnggroup/libpng/archive/refs/tags/v$repo_version.tar.gz" "libpng-$repo_version.tar.gz"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-shared --enable-static \
            --enable-hardware-optimizations=yes --with-pic
        execute make "-j$build_threads"
        # Upstream wires both link targets into install-data/install-exec hooks.
        execute make install
        build_done "libpng" "$repo_version"
    fi

    # Build libtiff
    fetch_version_if_enabled "libtiff" libtiff_version
    if build "libtiff" "$repo_version"; then
        download "https://gitlab.com/libtiff/libtiff/-/archive/v$repo_version/libtiff-v$repo_version.tar.bz2" "libtiff-$repo_version.tar.bz2"
        # Use autoreconf instead of autogen.sh to avoid hanging downloads
        execute autoreconf -fi
        execute sh configure --prefix="$workspace" \
            --disable-{contrib,cxx,docs,shared,sphinx,tests,tools} \
            --enable-static \
            --with-pic
        execute make "-j$build_threads"
        execute make install
        build_done "libtiff" "$repo_version"
    fi

    # aribb24 is a version-3 dependency, not a GPL-only dependency. FFmpeg is
    # already configured with --enable-version3 in both licensing modes.
    append_configure_options_if_enabled "libaribb24" "--enable-libaribb24"
}
