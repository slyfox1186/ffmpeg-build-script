#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

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
    box_out_banner_images "Installing Image Tools"
    require_vars workspace build_threads STATIC_VER

    # Build libheif
    find_git_repo "strukturag/libheif" "1" "T"
	    if build "libheif" "$repo_version"; then
	        download "https://github.com/strukturag/libheif/archive/refs/tags/v$repo_version.tar.gz" "libheif-$repo_version.tar.gz"
	        # Save original flags before modification
	        save_compiler_flags
	        CFLAGS="-O2 -pipe -fno-lto -fPIC -march=native"
	        CXXFLAGS="-O2 -pipe -fno-lto -fPIC -march=native"
	        export CFLAGS CXXFLAGS
	        local with_aom with_dav1d with_libde265 with_rav1e with_x265
	        with_aom=OFF
	        with_dav1d=OFF
	        with_libde265=OFF
	        with_rav1e=OFF
	        with_x265=OFF

	        [[ -f "$workspace/lib/libaom.a" || -f "$workspace/lib64/libaom.a" ]] && with_aom=ON
	        pkg-config --exists dav1d 2>/dev/null && with_dav1d=ON
	        (pkg-config --exists libde265 2>/dev/null || ldconfig -p 2>/dev/null | grep -q 'libde265\.so') && with_libde265=ON
	        [[ -f "$workspace/lib/librav1e.a" || -f "$workspace/lib64/librav1e.a" ]] && with_rav1e=ON
	        # x265 disabled due to static linking issues with NUMA dependencies

	        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
	                      -DBUILD_SHARED_LIBS=OFF -DWITH_AOM_DECODER="$with_aom" -DWITH_AOM_ENCODER="$with_aom" \
	                      -DWITH_DAV1D="$with_dav1d" -DWITH_LIBDE265="$with_libde265" -DWITH_RAV1E="$with_rav1e" \
	                      -DWITH_X265="$with_x265" -DENABLE_PLUGIN_LOADING=OFF \
	                      -DWITH_GDK_PIXBUF=OFF -DWITH_EXAMPLES=OFF \
	                      -G Ninja -Wno-dev
	        execute ninja "-j$build_threads" -C build
	        execute ninja -C build install
        # Restore original compiler flags
        restore_compiler_flags
        build_done "libheif" "$repo_version"
    fi

    # Build openjpeg
    find_git_repo "uclouvain/openjpeg" "1" "T"
    if build "openjpeg" "$repo_version"; then
        download "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v$repo_version" "openjpeg-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_{JPIP,JPWL,MJ2,SHARED_LIBS,TESTING}=OFF -DBUILD_THIRDPARTY=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "openjpeg" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libopenjpeg")
}
