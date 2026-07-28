#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Image Libraries
##  Image processing libraries (libheif, openjpeg, etc.)
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install image libraries
install_image_libraries() {
    echo
    box_out_banner "Installing Image Tools"
    require_vars workspace build_threads

    # Build libheif
    fetch_version_if_enabled "libheif" find_git_repo "strukturag/libheif" "1"
    if build "libheif" "$repo_version"; then
        download "https://github.com/strukturag/libheif/archive/refs/tags/v$repo_version.tar.gz" "libheif-$repo_version.tar.gz"
        local with_aom with_dav1d with_libde265 with_rav1e with_x265
        with_aom=OFF
        with_dav1d=OFF
        with_libde265=OFF
        with_rav1e=OFF
        with_x265=OFF

        package_enabled "av1-git" && [[ -f "$workspace/lib/libaom.a" || -f "$workspace/lib64/libaom.a" ]] && with_aom=ON
        library_exists dav1d && with_dav1d=ON
        library_exists libde265 && with_libde265=ON
        package_enabled "rav1e" && [[ -f "$workspace/lib/librav1e.a" || -f "$workspace/lib64/librav1e.a" ]] && with_rav1e=ON
        is_true "$NONFREE_AND_GPL" && package_enabled "x265" &&
            library_exists x265 && with_x265=ON

        cmake_ninja_install "build" \
            -DBUILD_DEVELOPMENT_TOOLS=OFF -DBUILD_DOCUMENTATION=OFF \
            -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF \
            -DWITH_AOM_DECODER="$with_aom" -DWITH_AOM_ENCODER="$with_aom" \
            -DWITH_DAV1D="$with_dav1d" -DWITH_LIBDE265="$with_libde265" -DWITH_RAV1E="$with_rav1e" \
            -DWITH_X264=OFF -DWITH_X265="$with_x265" -DENABLE_PLUGIN_LOADING=OFF \
            -DWITH_FUZZERS=OFF -DWITH_GDK_PIXBUF=OFF -DWITH_EXAMPLES=OFF \
            -DWITH_LIBSHARPYUV=OFF -DWITH_OpenH264_DECODER=OFF
        build_done "libheif" "$repo_version"
    fi

    # Build openjpeg
    fetch_version_if_enabled "openjpeg" find_git_repo "uclouvain/openjpeg" "1"
    if build "openjpeg" "$repo_version"; then
        download "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v$repo_version" "openjpeg-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBUILD_CODEC=OFF \
            -DBUILD_DOC=OFF \
            -DBUILD_JAVA=OFF \
            -DBUILD_JPIP=OFF \
            -DBUILD_SHARED_LIBS=OFF \
            -DBUILD_STATIC_LIBS=ON \
            -DBUILD_TESTING=OFF \
            -DBUILD_UNIT_TESTS=OFF \
            -DBUILD_VIEWER=OFF
        build_done "openjpeg" "$repo_version"
    fi
    append_configure_options_if_enabled "openjpeg" "--enable-libopenjpeg"
}
