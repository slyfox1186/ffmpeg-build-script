#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

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

    # Build libheif
    find_git_repo "strukturag/libheif" "1" "T"
    if build "libheif" "$repo_version"; then
        download "https://github.com/strukturag/libheif/archive/refs/tags/v$repo_version.tar.gz" "libheif-$repo_version.tar.gz"
        source_compiler_flags
        CFLAGS="-O2 -pipe -fno-lto -fPIC -march=native"
        CXXFLAGS="-O2 -pipe -fno-lto -fPIC -march=native"
        export CFLAGS CXXFLAGS
        libde265_libs=$(find /usr/ -type f -name 'libde265.s*')
        if [[ -f "$libde265_libs" ]] && [[ ! -e "/usr/lib/x86_64-linux-gnu/libde265.so" ]]; then
            sudo ln -sf "$libde265_libs" "/usr/lib/x86_64-linux-gnu/libde265.so"
            sudo chmod 755 "/usr/lib/x86_64-linux-gnu/libde265.so"
        fi

        case "$STATIC_VER" in
            20.04) pixbuf_switch=OFF ;;
            *)     pixbuf_switch=ON ;;
        esac

        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DWITH_AOM_{DECODER,ENCODER}=ON -DWITH_DAV1D=ON \
                      -DWITH_LIBDE265=ON -DWITH_RAV1E=ON -DWITH_X265=ON -DENABLE_PLUGIN_LOADING=OFF \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        source_compiler_flags
        build_done "libheif" "$repo_version"
    fi

    # Build openjpeg
    find_git_repo "uclouvain/openjpeg" "1" "T"
    if build "openjpeg" "$repo_version"; then
        download "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v$repo_version" "openjpeg-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_{SHARED_LIBS,TESTING}=OFF -DBUILD_THIRDPARTY=ON -DBUILD_JPIP=ON \
                      -DBUILD_JPWL=ON -DBUILD_MJ2=ON -DOPENJPEG_ENABLE_PNG=ON -DOPENJPEG_ENABLE_TIFF=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "openjpeg" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libopenjpeg")

    log "Image libraries installation completed"
}
