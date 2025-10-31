#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

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

    # Build libdvdread
    find_git_repo "76" "2" "T"
    if build "libdvdread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libdvdread/-/archive/$repo_version/libdvdread-$repo_version.tar.bz2"
        execute autoreconf -fi
        execute ./configure --prefix="$workspace" --disable-{apidoc,shared}
        execute make "-j$build_threads"
        execute make install
        build_done "libdvdread" "$repo_version"
    fi

    # Build udfread
    find_git_repo "363" "2" "T"
    if build "udfread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libudfread/-/archive/$repo_version/libudfread-$repo_version.tar.bz2"
        execute autoupdate
        execute autoreconf -fi
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "udfread" "$repo_version"
    fi

    # Set ant path and build ant
    set_ant_path
    git_caller "https://github.com/apache/ant.git" "ant-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute chmod 777 -R "$workspace/ant"
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
        cd Project/GNU/Library || exit 1
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
        cd "Project/GNU/Library" || exit 1
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
        cd "Project/GNU/CLI" || exit 1
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
        if build "x265" "3.5"; then
            download "https://bitbucket.org/multicoreware/x265_git/downloads/x265_3.5.tar.gz" "x265-3.5.tar.gz"
            
            # Fix CMake policy issues for modern CMake
            sed -i 's/cmake_policy(SET CMP0025 OLD)/cmake_policy(SET CMP0025 NEW)/' source/CMakeLists.txt
            sed -i 's/cmake_policy(SET CMP0054 OLD)/cmake_policy(SET CMP0054 NEW)/' source/CMakeLists.txt
            
            fix_libstd_libs
            cd build/linux || exit 1
            rm -fr {8,10,12}bit 2>/dev/null
            mkdir -p {8,10,12}bit
            cd 12bit || exit 1
            echo "$ making 12bit binaries"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DENABLE_{CLI,LIBVMAF,SHARED}=OFF -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DMAIN12=ON \
                          -DNATIVE_BUILD=ON -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            echo "$ making 10bit binaries"
            cd ../10bit || exit 1
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DENABLE_{CLI,LIBVMAF,SHARED}=OFF -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF \
                          -DHIGH_BIT_DEPTH=ON -DNATIVE_BUILD=ON -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            echo "$ making 8bit binaries"
            cd ../8bit || exit 1
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

            build_done "x265" "3.5"
        fi
        CONFIGURE_OPTIONS+=("--enable-libx265")

        # NVIDIA codec headers (CUDA only)
        if [[ -n "$iscuda" ]]; then
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

            if [[ -n "$LDEXEFLAGS" ]]; then
                CONFIGURE_OPTIONS+=("--enable-libnpp")
            fi

            PATH+=":$cuda_path"
            remove_duplicate_paths

            # Get the Nvidia GPU architecture to build CUDA
            nvidia_architecture
            CONFIGURE_OPTIONS+=("--nvccflags=-gencode arch=$nvidia_arch_type")
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

        # Build AMF headers
        find_git_repo "GPUOpen-LibrariesAndSDKs/AMF" "1" "T"
        if build "amf-headers" "$repo_version"; then
            download "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/archive/refs/tags/v$repo_version.tar.gz" "amf-headers-$repo_version.tar.gz"
            # Install AMF headers to the location FFmpeg expects
            execute rm -fr "$workspace/include/AMF"
            execute mkdir -p "$workspace/include/AMF"
            # Copy the AMF directory structure as FFmpeg expects it (AMF/core and AMF/components)
            execute cp -fr "amf/public/include/core" "$workspace/include/AMF/"
            execute cp -fr "amf/public/include/components" "$workspace/include/AMF/"
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
            cd "build/generic" || exit 1
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
        [[ -f "Build/linux/SvtAv1Enc.pc" ]] && cp -f "Build/linux/SvtAv1Enc.pc" "$workspace/lib/pkgconfig"
        [[ -f "$workspace/lib/pkgconfig" ]] && cp -f "Build/linux/SvtAv1Dec.pc" "$workspace/lib/pkgconfig"
        build_done "svt-av1" "$repo_version"
    fi
    # CONFIGURE_OPTIONS+=("--enable-libsvtav1") # Disabled due to API incompatibility with FFmpeg 6.1.2

    # Build VapourSynth
    find_git_repo "vapoursynth/vapoursynth" "1" "T"
    if build "vapoursynth" "R${repo_version}"; then
        download "https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R${repo_version}.tar.gz" "vapoursynth-R${repo_version}.tar.gz"

        venv_packages=("Cython==0.29.36")
        setup_python_venv_and_install_packages "$workspace/python_virtual_environment/vapoursynth" "${venv_packages[@]}"

        # Activate the virtual environment for the build process
        source "$workspace/python_virtual_environment/vapoursynth/bin/activate" || fail "Failed to re-activate virtual environment"

        # Explicitly set the PYTHON environment variable to the virtual environment's Python
        export PYTHON="$workspace/python_virtual_environment/vapoursynth/bin/python"

        PATH="$ccache_dir:$workspace/python_virtual_environment/vapoursynth/bin:$PATH"
        remove_duplicate_paths

        # Set Python flags for configure
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        export PYTHON3_CFLAGS=$(python3-config --cflags)
        export PYTHON3_LIBS=$(python3-config --ldflags --embed)
        
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

    log "Video libraries installation completed"
}

# NVIDIA codec headers helper functions (GPL and non-free only)
fetch_nv_codec_headers_versions() {
    # Fetch the HTML content of the GitHub tags page
    local scrape_html
    scrape_html=$(curl -fsSL "https://github.com/FFmpeg/nv-codec-headers/tags/")

    # Declare an array to store version and date pairs
    declare -a versions_and_dates

    # Read the HTML content into an array of lines
    IFS=$'\n' read -rd '' -a html_lines <<<"$scrape_html"

    # Iterate over each line to find version numbers and their corresponding dates
    local current_version=""
    local current_date=""
    local regex=""
    regex='href=\"/FFmpeg/nv-codec-headers/releases/tag/n([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\"'
    for line in "${html_lines[@]}"; do
        # Match the version number
        if [[ $line =~ $regex ]]; then
            current_version="${BASH_REMATCH[1]}"
        fi

        # Match the release date
        if [[ "$line" =~ datetime=\"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}:[0-9]{2}:[0-9]{2})Z\" ]]; then
            if [[ -n "$current_version" ]]; then
                local date="${BASH_REMATCH[1]}T${BASH_REMATCH[2]}Z"
                # Format the date as MM-DD-YYYY
                local formatted_date
                formatted_date=$(date -d "$date" +"%m-%d-%Y")
                # Store the version and formatted date
                versions_and_dates+=("$current_version;$formatted_date")
                # Reset current_version for the next iteration
                current_version=""
            fi
        fi
    done

    # Check if any versions were found
    if [[ ${#versions_and_dates[@]} -eq 0 ]]; then
        echo "No releases found."
        exit 1
    fi

    # Sort the versions in descending order based on version number
    IFS=$'\n' sorted_versions_and_dates=($(sort -t ';' -k1Vr <<<"${versions_and_dates[*]}"))
    unset IFS
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
