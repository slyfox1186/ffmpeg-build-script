#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Video Libraries
##  Video codecs and processing libraries (AV1, rav1e, x264, x265, etc.)
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install video libraries
install_video_libraries() {
    echo
    box_out_banner_video "Installing Video Tools"
    require_vars workspace packages build_threads STATIC_VER

    # Build libaom (AV1)
    git_caller "https://aomedia.googlesource.com/aom" "av1-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" \
                      -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
                      -DCONFIG_AV1_{DECODER,ENCODER,HIGHBITDEPTH,TEMPORAL_DENOISING}=1 \
                      -DCONFIG_DENOISE=1 -DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1 \
                      -DENABLE_CCACHE=1 -DENABLE_{EXAMPLES,TESTS}=0 -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libaom")

    # Rav1e fails to build on Ubuntu Bionic and Debian 11 Bullseye
    if [[ "$STATIC_VER" != "11" ]]; then
        find_git_repo "xiph/rav1e" "1" "T" "enabled"
        if build "rav1e" "$repo_version"; then
            install_rustup
            source "$HOME/.cargo/env"
            [[ -f /usr/bin/rustc ]] && sudo rm -f /usr/bin/rustc
            check_and_install_cargo_c
            download "https://github.com/xiph/rav1e/archive/refs/tags/$repo_version.tar.gz" "rav1e-$repo_version.tar.gz"
            # Ensure workspace directories have proper permissions
            sudo chown -R "$USER:$USER" "$workspace"
            if ! execute cargo cinstall --prefix="$workspace" --library-type=staticlib --crt-static --release; then
                rm -fr "$HOME/.cargo/registry/index/"* "$HOME/.cargo/.package-cache"
                execute cargo cinstall --prefix="$workspace" --library-type=staticlib --crt-static --release
            fi
            build_done "rav1e" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-librav1e")
    fi

    # Build zimg
    git_caller "https://github.com/sekrit-twc/zimg.git" "zimg-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url" "zimg-git"
        execute autoupdate
        execute ./autogen.sh
        execute git submodule update --init --recursive
        execute ./configure --prefix="$workspace" --with-pic
        execute make "-j$build_threads"
        execute make install
        move_zimg_shared_file=$(find "$workspace/lib/" -type f -name 'libzimg.so.*')
        if [[ -n "$move_zimg_shared_file" ]]; then
            execute sudo cp -f "$move_zimg_shared_file" /usr/lib/x86_64-linux-gnu/
        fi
        build_done "$repo_name" "$version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libzimg")

    # Build libavif
    find_git_repo "AOMediaCodec/libavif" "1" "T"
    if build "avif" "$repo_version"; then
        download "https://github.com/AOMediaCodec/libavif/archive/refs/tags/v$repo_version.tar.gz" "avif-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DAVIF_CODEC_AOM=ON -DAVIF_CODEC_AOM_{DECODE,ENCODE}=ON \
                      -DAVIF_ENABLE_WERROR=OFF -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "avif" "$repo_version"
    fi

    # Build kvazaar
    find_git_repo "ultravideo/kvazaar" "1" "T"
    if build "kvazaar" "$repo_version"; then
        download "https://github.com/ultravideo/kvazaar/archive/refs/tags/v$repo_version.tar.gz" "kvazaar-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                               -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "kvazaar" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libkvazaar")

    # Build libdvdread (uses meson since v7.0.0)
    find_git_repo "76" "2" "T"
    if build "libdvdread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libdvdread/-/archive/$repo_version/libdvdread-$repo_version.tar.bz2"
        execute meson setup build --prefix="$workspace" --default-library=static --buildtype=release \
                      -Denable_docs=false
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "libdvdread" "$repo_version"
    fi

    # Build udfread (uses meson since v1.2.0)
    find_git_repo "363" "1" "T"
    if build "udfread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libudfread/-/archive/$repo_version/libudfread-$repo_version.tar.bz2"
        execute meson setup build --prefix="$workspace" --default-library=static --buildtype=release
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "udfread" "$repo_version"
    fi

    # Set ant path and build ant
    set_ant_path
    git_caller "https://github.com/apache/ant.git" "ant-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute chmod -R u+rwX,go+rX "$workspace/ant"
        execute sh build.sh install-lite
        build_done "$repo_name" "$version"
    fi
    PATH="$PATH:$workspace/ant/bin"
    remove_duplicate_paths

    # Ubuntu Jammy and Noble both give an error so instead we will use the APT version
    if [[ ! "$STATIC_VER" == "22.04" ]] && [[ ! "$STATIC_VER" == "24.04" ]]; then
        find_git_repo "206" "2" "T"
        if build "libbluray" "$repo_version"; then
            download "https://code.videolan.org/videolan/libbluray/-/archive/$repo_version/$repo_version.tar.gz" "libbluray-$repo_version.tar.gz"
            extracmds=("--disable-"{doxygen-doc,doxygen-dot,doxygen-html,doxygen-pdf,doxygen-ps,examples,extra-warnings,shared})
            execute autoupdate
            execute autoreconf -fi
            execute ./configure --prefix="$workspace" "${extracmds[@]}" --without-libxml2 --with-pic
            execute make "-j$build_threads"
            execute make install
            build_done "libbluray" "$repo_version"
        fi
    fi
    CONFIGURE_OPTIONS+=("--enable-libbluray")

    # Build zenlib
    find_git_repo "MediaArea/ZenLib" "1" "T"
    if build "zenlib" "$repo_version"; then
        download "https://github.com/MediaArea/ZenLib/archive/refs/tags/v$repo_version.tar.gz" "zenlib-$repo_version.tar.gz"
        cd Project/GNU/Library || fail "Failed to cd into Project/GNU/Library. Line: $LINENO"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "zenlib" "$repo_version"
    fi

    # Build mediainfo-lib
    find_git_repo "MediaArea/MediaInfoLib" "1" "T"
    if build "mediainfo-lib" "$repo_version"; then
        download "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v$repo_version.tar.gz" "mediainfo-lib-$repo_version.tar.gz"
        cd "Project/GNU/Library" || fail "Failed to cd into Project/GNU/Library. Line: $LINENO"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "mediainfo-lib" "$repo_version"
    fi

    # Build mediainfo-cli
    find_git_repo "MediaArea/MediaInfo" "1" "T"
    if build "mediainfo-cli" "$repo_version"; then
        download "https://github.com/MediaArea/MediaInfo/archive/refs/tags/v$repo_version.tar.gz" "mediainfo-cli-$repo_version.tar.gz"
        cd "Project/GNU/CLI" || fail "Failed to cd into Project/GNU/CLI. Line: $LINENO"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --enable-staticlibs --disable-shared
        execute make "-j$build_threads"
        execute make install
        execute sudo cp -f "$packages/mediainfo-cli-$repo_version/Project/GNU/CLI/mediainfo" "/usr/local/bin/"
        build_done "mediainfo-cli" "$repo_version"
    fi

    # GPL and non-free only libraries
    if "$NONFREE_AND_GPL"; then
        # Build vid-stab
        find_git_repo "georgmartius/vid.stab" "1" "T"
        if build "vid-stab" "$repo_version"; then
            download "https://github.com/georgmartius/vid.stab/archive/refs/tags/v$repo_version.tar.gz" "vid-stab-$repo_version.tar.gz"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DBUILD_SHARED_LIBS=OFF -DUSE_OMP=ON -G Ninja -Wno-dev
            execute ninja "-j$build_threads" -C build
            execute ninja -C build install
            build_done "vid-stab" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libvidstab")

        
        # Build x264
        find_git_repo "536" "2" "B"
        if build "x264" "$repo_version"; then
            download "https://code.videolan.org/videolan/x264/-/archive/$x264_full_commit/x264-$x264_full_commit.tar.bz2" "x264-$repo_version.tar.bz2"
            execute ./configure --prefix="$workspace" --bit-depth=all --chroma-format=all --enable-debug --enable-gprof \
                                --enable-lto --enable-pic --enable-static --enable-strip --extra-cflags="-O3 -pipe -fPIC -march=native"
            execute make "-j$build_threads"
            execute make install-lib-static install
            build_done "x264" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libx264")

        # Build x265
        if build "x265" "3.6"; then
            download "https://bitbucket.org/multicoreware/x265_git/downloads/x265_3.6.tar.gz" "x265-3.6.tar.gz"
            
            # Fix CMake policy issues for modern CMake
            sed -i 's/cmake_policy(SET CMP0025 OLD)/cmake_policy(SET CMP0025 NEW)/' source/CMakeLists.txt
            sed -i 's/cmake_policy(SET CMP0054 OLD)/cmake_policy(SET CMP0054 NEW)/' source/CMakeLists.txt
            
            fix_libstd_libs
            cd build/linux || fail "Failed to cd into build/linux. Line: $LINENO"
            rm -fr {8,10,12}bit 2>/dev/null
            mkdir -p {8,10,12}bit
            cd 12bit || fail "Failed to cd into 12bit. Line: $LINENO"
            echo "$ making 12bit binaries"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DENABLE_{CLI,LIBVMAF,SHARED}=OFF -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DMAIN12=ON \
                          -DNATIVE_BUILD=ON -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            echo "$ making 10bit binaries"
            cd ../10bit || fail "Failed to cd into 10bit. Line: $LINENO"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DENABLE_{CLI,LIBVMAF,SHARED}=OFF -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF \
                          -DHIGH_BIT_DEPTH=ON -DNATIVE_BUILD=ON -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            echo "$ making 8bit binaries"
            cd ../8bit || fail "Failed to cd into 8bit. Line: $LINENO"
            ln -sf "../10bit/libx265.a" "libx265_main10.a"
            ln -sf "../12bit/libx265.a" "libx265_main12.a"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DENABLE_LIBVMAF=OFF -DENABLE_{PIC,SHARED}=ON -DEXTRA_LIB="x265_main10.a;x265_main12.a" \
                          -DEXTRA_LINK_FLAGS="-L." -DHIGH_BIT_DEPTH=ON -DLINKED_{10BIT,12BIT}=ON -DNATIVE_BUILD=ON \
                          -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
            execute ninja "-j$build_threads"

            mv "libx265.a" "libx265_main.a"

            execute ar -M <<EOF
CREATE libx265.a
ADDLIB libx265_main.a
ADDLIB libx265_main10.a
ADDLIB libx265_main12.a
SAVE
EOF

            execute ninja install

            [[ -n "$LDEXEFLAGS" ]] && sed -i.backup "s/lgcc_s/lgcc_eh/g" "$workspace/lib/pkgconfig/x265.pc"

            fix_x265_libs # Fix the x265 shared library issue

            build_done "x265" "3.6"
        fi
        CONFIGURE_OPTIONS+=("--enable-libx265")

        # NVIDIA codec headers (CUDA only)
        # Check if NVIDIA GPU was detected (gpu_flag=0) and CUDA toolkit is installed
        if [[ "${gpu_flag:-1}" -eq 0 ]] && [[ -d "/usr/local/cuda" ]]; then
            # Define CUDA paths
            cuda_path="/usr/local/cuda/bin"
            # Check if nv-codec-headers was already built
            if [[ -f "$packages/nv-codec-headers.done" ]]; then
                # Read the previously selected version from the lock file
                selected_version=$(cat "$packages/nv-codec-headers.done")
                
                # Use the build function to check if we should rebuild
                if ! build "nv-codec-headers" "$selected_version"; then
                    # Already built with this version, skip prompting
                    :
                else
                    # Lock file was deleted or version changed, prompt for new version
                    fetch_nv_codec_headers_versions
                    prompt_user_for_version
                    
                    download_url="https://github.com/FFmpeg/nv-codec-headers/archive/refs/tags/n${selected_version}.tar.gz"
                    download_file="nv-codec-headers-${selected_version}.tar.gz"
                    download "$download_url" "$download_file"
                    execute make "-j$build_threads"
                    execute make PREFIX="$workspace" install
                    build_done "nv-codec-headers" "$selected_version"
                fi
            else
                # First time building, fetch versions and prompt user
                fetch_nv_codec_headers_versions
                prompt_user_for_version

                if build "nv-codec-headers" "$selected_version"; then
                    download_url="https://github.com/FFmpeg/nv-codec-headers/archive/refs/tags/n${selected_version}.tar.gz"
                    download_file="nv-codec-headers-${selected_version}.tar.gz"
                    download "$download_url" "$download_file"
                    execute make "-j$build_threads"
                    execute make PREFIX="$workspace" install
                    build_done "nv-codec-headers" "$selected_version"
                fi
            fi

            CONFIGURE_OPTIONS+=("--enable-"{cuda-nvcc,cuda-llvm,cuvid,nvdec,nvenc,ffnvcodec})

            # libnpp only works with CUDA 11.x and earlier (deprecated NPP functions removed in CUDA 12+)
            if [[ -n "$LDEXEFLAGS" ]]; then
                local cuda_major_ver
                cuda_major_ver=$(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9]+' | head -1)
                if [[ -n "$cuda_major_ver" ]] && [[ "$cuda_major_ver" -lt 12 ]]; then
                    CONFIGURE_OPTIONS+=("--enable-libnpp")
                fi
            fi

            PATH+=":$cuda_path"
            remove_duplicate_paths

            # Use the nvidia_arch_type already set by hardware-detection.sh
            if [[ -n "${nvidia_arch_type:-}" ]]; then
                CONFIGURE_OPTIONS+=("--nvccflags=$nvidia_arch_type")
            fi
        fi

        # Vaapi doesn't work well with static links FFmpeg.
        if [[ -z "$LDEXEFLAGS" ]]; then
            # If the libva development SDK is installed, enable vaapi.
            if library_exists "libva"; then
                if build "vaapi" "1"; then
                    build_done "vaapi" "1"
                fi
                CONFIGURE_OPTIONS+=("--enable-vaapi")
            fi
        fi

        # Build AMF headers (use official headers-only tarball)
        find_git_repo "GPUOpen-LibrariesAndSDKs/AMF" "1" "T"
        if build "amf-headers" "$repo_version"; then
            download "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/releases/download/v$repo_version/AMF-headers-v$repo_version.tar.gz"
            # Install AMF headers to the location FFmpeg expects
            execute rm -fr "$workspace/include/AMF"
            execute cp -fr AMF "$workspace/include/"
            build_done "amf-headers" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-amf")

        # Build SRT
        find_git_repo "Haivision/srt" "1" "T"
        if build "srt" "$repo_version"; then
            download "https://github.com/Haivision/srt/archive/refs/tags/v$repo_version.tar.gz" "srt-$repo_version.tar.gz"
            export OPENSSL_ROOT_DIR="$workspace"
            export OPENSSL_LIB_DIR="$workspace/lib"
            export OPENSSL_INCLUDE_DIR="$workspace/include"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DBUILD_SHARED_LIBS=OFF -DENABLE_{APPS,SHARED}=OFF -DENABLE_STATIC=ON \
                          -DUSE_STATIC_LIBSTDCXX=ON -DENABLE_ENCRYPTION=ON -DENABLE_CXX11=ON \
                          -DUSE_OPENSSL_PC=ON -DENABLE_UNITTESTS=OFF -DENABLE_LOGGING=ON \
                          -DENABLE_HEAVY_LOGGING=OFF -G Ninja -Wno-dev
            execute ninja -C build "-j$build_threads"
            execute ninja -C build "-j$build_threads" install
            if [[ -n "$LDEXEFLAGS" ]]; then
                sed -i.backup "s/-lgcc_s/-lgcc_eh/g" "$workspace/lib/pkgconfig/srt.pc"
            fi
            build_done "srt" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libsrt")

        # Build Avisynth
        find_git_repo "avisynth/avisynthplus" "1" "T"
        if build "avisynth" "$repo_version"; then
            download "https://github.com/AviSynth/AviSynthPlus/archive/refs/tags/v$repo_version.tar.gz" "avisynth-$repo_version.tar.gz"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DBUILD_SHARED_LIBS=OFF -DHEADERS_ONLY=OFF -DENABLE_PLUGINS=OFF -Wno-dev
            execute make "-j$build_threads" -C build VersionGen install
            build_done "avisynth" "$repo_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-avisynth")

        # Build xvidcore
        find_git_repo "8268" "2"
        clean_version="${repo_version//debian\/2%/}"  # Remove debian/2% prefix
        url_version="${repo_version//\%/%25}"  # URL-encode the % character
        if build "xvidcore" "$clean_version"; then
            download "https://salsa.debian.org/multimedia-team/xvidcore/-/archive/$url_version/xvidcore-${url_version//\//-}.tar.bz2" "xvidcore-$clean_version.tar.bz2"
            cd "build/generic" || fail "Failed to cd into build/generic. Line: $LINENO"
            execute ./bootstrap.sh
            execute ./configure --prefix="$workspace"
            execute make "-j$build_threads"
            [[ -f "$workspace/lib/libxvidcore.so" ]] && rm "$workspace/lib/libxvidcore.so" "$workspace/lib/libxvidcore.so.4"
            execute make install
            build_done "xvidcore" "$clean_version"
        fi
        CONFIGURE_OPTIONS+=("--enable-libxvid")
    fi

    # Build gpac
    git_caller "https://github.com/gpac/gpac.git" "gpac-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        # Remove existing directory if it exists
        [[ -d "$packages/gpac-git" ]] && rm -fr "$packages/gpac-git"
        # Do a full clone instead of shallow clone for gpac
        git clone -q "$git_url" "$packages/gpac-git"
        cd "$packages/gpac-git" || fail "Failed to cd into gpac-git directory"
        # Create the include directory and empty revision.h to prevent rm error
        mkdir -p include/gpac
        touch include/gpac/revision.h
        execute ./configure --prefix="$workspace" --static-{bin,modules} --use-{a52,faad,freetype,mad}=local --sdl-cfg="$workspace/include/SDL3"
        execute make "-j$build_threads"
        execute make install
        execute sudo cp -f bin/gcc/MP4Box /usr/local/bin
        build_done "$repo_name" "$version"
    fi

    # Build SVT-AV1
    find_git_repo "24327400" "3" "T"
    if build "svt-av1" "$repo_version"; then
        download "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v$repo_version/SVT-AV1-v$repo_version.tar.bz2" "svt-av1-$repo_version.tar.bz2"
        execute cmake -S . -B Build/linux \
                      -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_{APPS,SHARED_LIBS,TESTING}=OFF -DENABLE_AVX512="$(check_avx512)" \
                      -DNATIVE=ON -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C Build/linux
        execute ninja "-j$build_threads" -C Build/linux install
        [[ -f "Build/linux/SvtAv1Enc.pc" ]] && cp -f "Build/linux/SvtAv1Enc.pc" "$workspace/lib/pkgconfig/"
        [[ -d "$workspace/lib/pkgconfig" ]] && [[ -f "Build/linux/SvtAv1Dec.pc" ]] && cp -f "Build/linux/SvtAv1Dec.pc" "$workspace/lib/pkgconfig/"
        build_done "svt-av1" "$repo_version"
    fi
    # CONFIGURE_OPTIONS+=("--enable-libsvtav1") # Disabled due to API incompatibility with FFmpeg 6.1.2

    # Build VapourSynth
    find_git_repo "vapoursynth/vapoursynth" "1" "T"
    if build "vapoursynth" "R${repo_version}"; then
        download "https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R${repo_version}.tar.gz" "vapoursynth-R${repo_version}.tar.gz"

        venv_packages=("Cython>=3.0")
        setup_python_venv_and_install_packages "$workspace/python_virtual_environment/vapoursynth" "${venv_packages[@]}"

        # Activate the virtual environment for the build process
        source "$workspace/python_virtual_environment/vapoursynth/bin/activate" || fail "Failed to re-activate virtual environment"

        # Explicitly set the PYTHON environment variable to the virtual environment's Python
        export PYTHON="$workspace/python_virtual_environment/vapoursynth/bin/python"

        PATH="$ccache_dir:$workspace/python_virtual_environment/vapoursynth/bin:$PATH"
        remove_duplicate_paths

        # Set Python flags for configure
        PYTHON3_CFLAGS="$(python3-config --cflags)" || fail "python3-config --cflags failed. Line: $LINENO"
        export PYTHON3_CFLAGS
        PYTHON3_LIBS="$(python3-config --ldflags --embed 2>/dev/null || python3-config --ldflags)" || fail "python3-config --ldflags failed. Line: $LINENO"
        export PYTHON3_LIBS
        
        # Assuming autogen, configure, make, and install steps for VapourSynth
        execute autoupdate
        execute ./autogen.sh || fail "Failed to execute autogen.sh"
        execute ./configure --prefix="$workspace" --disable-shared || fail "Failed to configure"
        execute make -j"$build_threads" || fail "Failed to make"
        execute make install || fail "Failed to make install"

        # Deactivate the virtual environment after the build
        deactivate

        build_done "vapoursynth" "R${repo_version}"
    else
        # Explicitly set the PYTHON environment variable to the virtual environment's Python
        PYTHON="$workspace/python_virtual_environment/vapoursynth/bin/python"
        export PYTHON
        PATH="$ccache_dir:$workspace/python_virtual_environment/vapoursynth/bin:$PATH"
        remove_duplicate_paths
    fi
    CONFIGURE_OPTIONS+=("--enable-vapoursynth")

    # Build libgav1
    git_caller "https://chromium.googlesource.com/codecs/libgav1" "libgav1-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute git clone -q -b "20220623.1" --depth 1 "https://github.com/abseil/abseil-cpp.git" "third_party/abseil-cpp"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DABSL_{ENABLE_INSTALL,PROPAGATE_CXX_STD}=ON -DBUILD_SHARED_LIBS=OFF \
                      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INSTALL_SBINDIR=sbin \
                      -DLIBGAV1_ENABLE_TESTS=OFF -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi
}

# NVIDIA codec headers helper functions (GPL and non-free only)
fetch_nv_codec_headers_versions() {
    # Build the `sorted_versions_and_dates` array in "version;MM-DD-YYYY" format.
    declare -a versions_and_dates=()
    local scrape_html

    # Prefer the GitHub API (more stable than scraping HTML); fall back to HTML if rate-limited or jq unavailable.
    if command -v jq >/dev/null 2>&1; then
        local api_json
        if api_json="$(curl -fsSL "https://api.github.com/repos/FFmpeg/nv-codec-headers/releases?per_page=100" 2>/dev/null)"; then
            local -a api_lines=()
            mapfile -t api_lines < <(printf '%s' "$api_json" | jq -r '.[] | select(.tag_name | test("^n[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$")) | "\(.tag_name);\(.published_at)"')
            local entry tag iso_date version formatted_date
            for entry in "${api_lines[@]}"; do
                tag="${entry%%;*}"
                iso_date="${entry##*;}"
                version="${tag#n}"
                iso_date="${iso_date%%T*}"
                formatted_date="$(date -d "$iso_date" +"%m-%d-%Y" 2>/dev/null || echo "$iso_date")"
                versions_and_dates+=("$version;$formatted_date")
            done
        fi
    fi

    if [[ ${#versions_and_dates[@]} -eq 0 ]]; then
        scrape_html=$(curl -fsSL "https://github.com/FFmpeg/nv-codec-headers/tags/")
        local -a html_lines=()
        mapfile -t html_lines <<<"$scrape_html"

        local current_version=""
        local regex='href=\"/FFmpeg/nv-codec-headers/releases/tag/n([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\"'
        local line
        for line in "${html_lines[@]}"; do
            if [[ $line =~ $regex ]]; then
                current_version="${BASH_REMATCH[1]}"
            fi

            if [[ "$line" =~ datetime=\"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}:[0-9]{2}:[0-9]{2})Z\" ]]; then
                if [[ -n "$current_version" ]]; then
                    local date="${BASH_REMATCH[1]}T${BASH_REMATCH[2]}Z"
                    local formatted_date
                    formatted_date=$(date -d "$date" +"%m-%d-%Y")
                    versions_and_dates+=("$current_version;$formatted_date")
                    current_version=""
                fi
            fi
        done
    fi

    # Check if any versions were found
    if [[ ${#versions_and_dates[@]} -eq 0 ]]; then
        warn "No nv-codec-headers releases found."
        return 1
    fi

    # Sort the versions in descending order based on version number
    mapfile -t sorted_versions_and_dates < <(printf '%s\n' "${versions_and_dates[@]}" | sort -t ';' -k1Vr)
}

prompt_user_for_version() {
    echo
    echo -e "${GREEN}Available ${YELLOW}nv-codec-headers ${GREEN}versions${NC}:"
    echo "------------------------------------"

    local index
    index=1

    echo -e "\n${GREEN}     Version        ${YELLOW}Date${NC}"
    for vd in "${sorted_versions_and_dates[@]}"; do
        local formatted_date version
        version="${vd%%;*}"
        formatted_date="${vd##*;}"
        # Pad the index with a leading zero if it's less than 10
        # Use a fixed-width field for the version (e.g., 12 characters, left-aligned)
        printf "%02d) %-12s %s\n" "$index" "$version" "$formatted_date"
        ((index++))
    done

    echo
    local choice regex_choice
    regex_choice='^[0-9]+$'
    while true; do
        read -rp "Select a version by number (1-10): " choice
        if [[ "$choice" =~ $regex_choice ]] && ((choice >= 1 && choice <= index - 1)); then
            local selected_vd="${sorted_versions_and_dates[$((choice - 1))]}"
            selected_version="${selected_vd%%;*}"
            selected_date="${selected_vd##*;}"
            break
        else
            printf "\n%s\n\n" "Invalid selection. Please enter a number between 1 and $((index - 1))."
        fi
    done

    echo "You selected version: $selected_version (Released on $selected_date)"
}
