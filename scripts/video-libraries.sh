#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

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
    local vmaf_version x265_release selected_version xvidcore_release
    local vapoursynth_package_version
    local PYTHON PYTHON3_CFLAGS PYTHON3_LIBS
    local -a venv_packages=()

    echo
    box_out_banner "Installing Video Tools"
    require_vars workspace packages build_threads

    # Build libaom (AV1)
    git_caller "https://aomedia.googlesource.com/aom" "av1-git"
    if build "$repo_name" "$version"; then
        cd "$packages/av1-git" || fail "Failed to cd into av1-git. Line: ${LINENO}"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF \
            -DCONFIG_AV1_{DECODER,ENCODER,HIGHBITDEPTH,TEMPORAL_DENOISING}=1 \
            -DCONFIG_DENOISE=1 \
            -DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1 \
            -DCONFIG_PIC=1 \
            -DCONFIG_SHARED=0 \
            -DENABLE_CCACHE=1 \
            -DENABLE_DOCS=0 \
            -DENABLE_EXAMPLES=0 \
            -DENABLE_NASM=1 \
            -DENABLE_TESTDATA=0 \
            -DENABLE_TESTS=0 \
            -DENABLE_TOOLS=0
        build_done "$repo_name" "$version"
    fi
    append_configure_options_if_enabled "av1-git" "--enable-libaom"

    # Build libvmaf (VMAF perceptual quality metric → FFmpeg vmaf/libvmaf filter).
    # Not packaged for Debian/Ubuntu, so build from source. built_in_models embeds the
    # default models so the filter works without external model files; enable_float adds
    # the float feature extractors the standard VMAF model needs.
    fetch_version_if_enabled "libvmaf" find_git_repo "Netflix/vmaf" "1"
    vmaf_version="$repo_version"
    if build "libvmaf" "$vmaf_version"; then
        download "https://github.com/Netflix/vmaf/archive/refs/tags/v$vmaf_version.tar.gz" "libvmaf-$vmaf_version.tar.gz"
        cd "libvmaf" || fail "Failed to cd into libvmaf. Line: $LINENO"
        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=static \
            -Denable_tests=false \
            -Denable_docs=false \
            -Denable_tools=false \
            -Dbuilt_in_models=true \
            -Denable_float=true
        build_done "libvmaf" "$vmaf_version"
    fi
    # libvmaf bundles C++ (libsvm) but its generated .pc omits the C++ runtime, so a
    # static link through FFmpeg's C driver fails with undefined operator new[]/delete[].
    # Declare it the way x265/zimg/rubberband do. Run unconditionally and idempotently so
    # an already-installed libvmaf is fixed without forcing a rebuild.
    package_enabled "libvmaf" && pkgconfig_add_private_lib "libvmaf" "-lstdc++"
    append_configure_options_if_enabled "libvmaf" "--enable-libvmaf"

    # Build rav1e (Rust-based AV1 encoder)
    fetch_version_if_enabled "rav1e" find_git_repo "xiph/rav1e" "1"
    if build "rav1e" "$repo_version"; then
        download "$(rav1e_download_url "$repo_version")" "rav1e-$repo_version.tar.gz"
        install_rustup
        check_and_install_cargo_c
        execute cargo cinstall --locked --prefix="$workspace" \
            --libdir="$workspace/lib" --library-type=staticlib --release
        build_done "rav1e" "$repo_version"
    fi
    append_configure_options_if_enabled "rav1e" "--enable-librav1e"

    # Build zimg
    git_caller "https://github.com/sekrit-twc/zimg.git" "zimg-git" "recurse"
    if build "$repo_name" "$version"; then
        cd "$packages/zimg-git" || fail "Failed to cd into zimg-git. Line: ${LINENO}"
        ensure_autotools
        execute sh configure --prefix="$workspace" --with-pic --disable-shared --enable-static
        execute make "-j$build_threads"
        execute make install
        build_done "$repo_name" "$version"
    fi
    append_configure_options_if_enabled "zimg-git" "--enable-libzimg"

    # Build libavif
    fetch_version_if_enabled "avif" find_git_repo "AOMediaCodec/libavif" "1"
    if build "avif" "$repo_version"; then
        download "https://github.com/AOMediaCodec/libavif/archive/refs/tags/v$repo_version.tar.gz" "avif-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DAVIF_BUILD_APPS=OFF \
            -DAVIF_BUILD_EXAMPLES=OFF \
            -DAVIF_BUILD_MAN_PAGES=OFF \
            -DAVIF_BUILD_TESTS=OFF \
            -DAVIF_CODEC_AOM=SYSTEM \
            -DAVIF_CODEC_AOM_DECODE=ON \
            -DAVIF_CODEC_AOM_ENCODE=ON \
            -DAVIF_CODEC_AVM=OFF \
            -DAVIF_CODEC_DAV1D=OFF \
            -DAVIF_CODEC_LIBGAV1=OFF \
            -DAVIF_CODEC_RAV1E=OFF \
            -DAVIF_CODEC_SVT=OFF \
            -DAVIF_ENABLE_WERROR=OFF \
            -DAVIF_JPEG=OFF \
            -DAVIF_LIBYUV=OFF \
            -DAVIF_ZLIBPNG=OFF \
            -DBUILD_SHARED_LIBS=OFF
        build_done "avif" "$repo_version"
    fi

    # Build kvazaar
    fetch_version_if_enabled "kvazaar" find_git_repo "ultravideo/kvazaar" "1"
    if build "kvazaar" "$repo_version"; then
        download "https://github.com/ultravideo/kvazaar/archive/refs/tags/v$repo_version.tar.gz" "kvazaar-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBUILD_KVAZAAR_BINARY=OFF \
            -DBUILD_SHARED_LIBS=OFF \
            -DBUILD_TESTS=OFF
        build_done "kvazaar" "$repo_version"
    fi
    append_configure_options_if_enabled "kvazaar" "--enable-libkvazaar"

    # Build libdvdread (uses meson since v7.0.0)
    fetch_version_if_enabled "libdvdread" find_git_repo "76" "1"
    if build "libdvdread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libdvdread/-/archive/$repo_version/libdvdread-$repo_version.tar.bz2"
        meson_ninja_install "build" \
            --default-library=static \
            --buildtype=release \
            -Denable_docs=false \
            -Dlibdvdcss=disabled
        build_done "libdvdread" "$repo_version"
    fi

    # Build udfread (uses meson since v1.2.0)
    fetch_version_if_enabled "udfread" find_git_repo "363" "1"
    if build "udfread" "$repo_version"; then
        download "https://code.videolan.org/videolan/libudfread/-/archive/$repo_version/libudfread-$repo_version.tar.bz2"
        meson_ninja_install "build" \
            --default-library=static \
            --buildtype=release \
            -Denable_examples=false
        build_done "udfread" "$repo_version"
    fi

    # Build Ant only when selected; no other recipe should force a JDK install
    # or create an Ant prefix for a disabled ancillary tool.
    if package_enabled "ant-git"; then
        set_ant_path
        git_caller "https://github.com/apache/ant.git" "ant-git"
        if build "$repo_name" "$version"; then
            cd "$packages/ant-git" || fail "Failed to cd into ant-git. Line: ${LINENO}"
            execute chmod -R u+rwX,go+rX "$workspace/ant"
            execute sh build.sh install-lite
            build_done "$repo_name" "$version"
        fi
        path_prepend "$workspace/ant/bin"
    fi


    # Build zenlib
    fetch_version_if_enabled "zenlib" find_git_repo "MediaArea/ZenLib" "1"
    if build "zenlib" "$repo_version"; then
        download "https://github.com/MediaArea/ZenLib/archive/refs/tags/v$repo_version.tar.gz" "zenlib-$repo_version.tar.gz"
        cd Project/GNU/Library || fail "Failed to cd into Project/GNU/Library. Line: $LINENO"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "zenlib" "$repo_version"
    fi

    # Build mediainfo-lib
    fetch_version_if_enabled "mediainfo-lib" find_git_repo "MediaArea/MediaInfoLib" "1"
    if build "mediainfo-lib" "$repo_version"; then
        download "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v$repo_version.tar.gz" "mediainfo-lib-$repo_version.tar.gz"
        cd "Project/GNU/Library" || fail "Failed to cd into Project/GNU/Library. Line: $LINENO"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "mediainfo-lib" "$repo_version"
    fi

    # Build mediainfo-cli
    fetch_version_if_enabled "mediainfo-cli" find_git_repo "MediaArea/MediaInfo" "1"
    if build "mediainfo-cli" "$repo_version"; then
        download "https://github.com/MediaArea/MediaInfo/archive/refs/tags/v$repo_version.tar.gz" "mediainfo-cli-$repo_version.tar.gz"
        cd "Project/GNU/CLI" || fail "Failed to cd into Project/GNU/CLI. Line: $LINENO"
        ensure_autotools
        execute sh configure --prefix="$workspace" --enable-staticlibs --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "mediainfo-cli" "$repo_version"
    fi

    # GPL and non-free only libraries
    if is_true "$NONFREE_AND_GPL"; then
        # Build vid-stab
        fetch_version_if_enabled "vid-stab" find_git_repo "georgmartius/vid.stab" "1"
        if build "vid-stab" "$repo_version"; then
            download "https://github.com/georgmartius/vid.stab/archive/refs/tags/v$repo_version.tar.gz" "vid-stab-$repo_version.tar.gz"
            cmake_ninja_install "build" \
                -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF -DUSE_OMP=ON
            build_done "vid-stab" "$repo_version"
        fi
        append_configure_options_if_enabled "vid-stab" "--enable-libvidstab"

        # Build x264
        fetch_version_if_enabled "x264" find_git_repo "536"
        if build "x264" "$repo_version"; then
            download "https://code.videolan.org/videolan/x264/-/archive/$repo_version/x264-$repo_version.tar.bz2"
            # Default to a release-style build (debug/profiling can be enabled by users when needed).
            execute sh configure --prefix="$workspace" --bit-depth=all --chroma-format=all \
                                --enable-pic --enable-static --enable-strip \
                                --disable-bashcompletion --disable-cli \
                                --extra-cflags="$CFLAGS" --extra-ldflags="$LDFLAGS"
            execute make "-j$build_threads"
            execute make install-lib-static
            build_done "x264" "$repo_version"
        fi
        append_configure_options_if_enabled "x264" "--enable-libx264"

        # Build x265 as a combined 8/10/12-bit static archive.
        fetch_version_if_enabled "x265" x265_version ||
            fail "Failed to detect the latest stable x265 release. Line: ${LINENO}"
        x265_release="$repo_version"
        if build "x265" "$x265_release"; then
            download "https://github.com/Multicorewareinc/x265/archive/refs/tags/$x265_release.tar.gz" \
                "x265-$x265_release.tar.gz"

            cd build/linux || fail "Failed to cd into build/linux. Line: $LINENO"
            safe_remove_tree "$PWD/8bit" "$PWD"
            safe_remove_tree "$PWD/10bit" "$PWD"
            safe_remove_tree "$PWD/12bit" "$PWD"
            execute mkdir -p {8,10,12}bit
            cd 12bit || fail "Failed to cd into 12bit. Line: $LINENO"
            log "Building x265 12-bit library"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DENABLE_{CLI,LIBVMAF,SHARED}=OFF \
                          -DENABLE_PIC=ON -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DMAIN12=ON \
                          -DENABLE_LIBNUMA=OFF -DNATIVE_BUILD=ON \
                          -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON \
                          -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
                          -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            log "Building x265 10-bit library"
            cd ../10bit || fail "Failed to cd into 10bit. Line: $LINENO"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DENABLE_{CLI,LIBVMAF,SHARED}=OFF \
                          -DENABLE_HDR10_PLUS=ON -DENABLE_PIC=ON -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON \
                          -DENABLE_LIBNUMA=OFF -DNATIVE_BUILD=ON \
                          -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON \
                          -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
                          -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            log "Building x265 8-bit library"
            cd ../8bit || fail "Failed to cd into 8bit. Line: $LINENO"
            execute ln -sf "../10bit/libx265.a" "libx265_main10.a"
            execute ln -sf "../12bit/libx265.a" "libx265_main12.a"
            execute cmake ../../../source -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                          -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DENABLE_{CLI,LIBVMAF}=OFF -DENABLE_PIC=ON \
                          -DENABLE_SHARED=OFF -DEXTRA_LIB="x265_main10.a;x265_main12.a" \
                          -DEXTRA_LINK_FLAGS="-L." -DLINKED_{10BIT,12BIT}=ON -DNATIVE_BUILD=ON \
                          -DENABLE_LIBNUMA=OFF \
                          -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON \
                          -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
                          -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
                          -G Ninja -Wno-dev
            execute ninja "-j$build_threads"
            # Install headers and metadata while Ninja's declared 8-bit archive
            # still exists, then replace only the installed archive with the
            # verified combined 8/10/12-bit result below.
            execute ninja install

            execute mv "libx265.a" "libx265_main.a"

            execute ar -M <<EOF
CREATE libx265.a
ADDLIB libx265_main.a
ADDLIB libx265_main10.a
ADDLIB libx265_main12.a
SAVE
EOF
            execute ranlib libx265.a

            execute install -Dm0644 libx265.a "$workspace/lib/libx265.a"
            pkgconfig_add_private_lib "x265" "-lstdc++"
            build_done "x265" "$x265_release"
        fi
        append_configure_options_if_enabled "x265" "--enable-libx265"

        # NVIDIA codec interfaces need these headers even when the optional CUDA
        # toolkit (used for CUDA-compiled filters) is not installed.
        if [[ "${gpu_flag:-1}" -eq 0 ]] &&
            package_enabled "nv-codec-headers"; then
            fetch_version_if_enabled "nv-codec-headers" nv_codec_headers_version ||
                fail "Failed to detect nv-codec-headers version. Line: ${LINENO}"
            selected_version="$repo_version"
            if build "nv-codec-headers" "$selected_version"; then
                download "https://github.com/FFmpeg/nv-codec-headers/archive/refs/tags/n${selected_version}.tar.gz" \
                         "nv-codec-headers-${selected_version}.tar.gz"
                execute make "-j$build_threads"
                execute make PREFIX="$workspace" install
                build_done "nv-codec-headers" "$selected_version"
            fi
        fi

        # Build AMF headers (AMD's Media Framework encoder) — only on AMD GPUs.
        if [[ "${is_amd_gpu_present:-}" == "AMD GPU detected" ]]; then
            fetch_version_if_enabled "amf-headers" find_git_repo "GPUOpen-LibrariesAndSDKs/AMF" "1"
            if build "amf-headers" "$repo_version"; then
                download "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/releases/download/v$repo_version/AMF-headers-v$repo_version.tar.gz"
                # Install AMF headers to the location FFmpeg expects
                safe_remove_tree "$workspace/include/AMF" "$workspace"
                execute cp -fr AMF "$workspace/include/"
                build_done "amf-headers" "$repo_version"
            fi
            append_configure_options_if_enabled "amf-headers" "--enable-amf"
        else
            log "No AMD GPU detected — skipping AMF (AMD encoder) headers and --enable-amf."
        fi

        # Build SRT
        fetch_version_if_enabled "srt" find_git_repo "Haivision/srt" "1"
        if build "srt" "$repo_version"; then
            local use_workspace_openssl
            use_workspace_openssl=false
            download "https://github.com/Haivision/srt/archive/refs/tags/v$repo_version.tar.gz" "srt-$repo_version.tar.gz"
            if package_enabled "openssl" &&
                [[ -f "$workspace/lib/libssl.a" || -f "$workspace/lib/libssl.so" ||
                    -f "$workspace/lib64/libssl.a" || -f "$workspace/lib64/libssl.so" ]]; then
                export OPENSSL_ROOT_DIR="$workspace"
                if [[ -f "$workspace/lib64/libssl.a" || -f "$workspace/lib64/libssl.so" ]]; then
                    export OPENSSL_LIB_DIR="$workspace/lib64"
                else
                    export OPENSSL_LIB_DIR="$workspace/lib"
                fi
                export OPENSSL_INCLUDE_DIR="$workspace/include"
                use_workspace_openssl=true
            else
                unset OPENSSL_ROOT_DIR OPENSSL_LIB_DIR OPENSSL_INCLUDE_DIR
            fi
            cmake_ninja_install "build" \
                -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
                -DBUILD_SHARED_LIBS=OFF \
                -DENABLE_APPS=OFF \
                -DENABLE_ENCRYPTION=ON \
                -DENABLE_HEAVY_LOGGING=OFF \
                -DENABLE_LOGGING=ON \
                -DENABLE_SHARED=OFF \
                -DENABLE_STATIC=ON \
                -DENABLE_UNITTESTS=OFF \
                -DOPENSSL_USE_STATIC_LIBS=TRUE \
                -DUSE_OPENSSL_PC=ON
            if [[ "$use_workspace_openssl" == "false" ]]; then
                log "Using system OpenSSL fallback for SRT"
            fi
            unset OPENSSL_ROOT_DIR OPENSSL_LIB_DIR OPENSSL_INCLUDE_DIR
            build_done "srt" "$repo_version"
        fi
        append_configure_options_if_enabled "srt" "--enable-libsrt"

        # Build Avisynth
        fetch_version_if_enabled "avisynth" find_git_repo "avisynth/avisynthplus" "1"
        if build "avisynth" "$repo_version"; then
            download "https://github.com/AviSynth/AviSynthPlus/archive/refs/tags/v$repo_version.tar.gz" "avisynth-$repo_version.tar.gz"
            execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                -DBUILD_SHARED_LIBS=OFF -DHEADERS_ONLY=OFF -DENABLE_PLUGINS=OFF -Wno-dev
            execute make "-j$build_threads" -C build VersionGen install
            build_done "avisynth" "$repo_version"
        fi
        append_configure_options_if_enabled "avisynth" "--enable-avisynth"

        # Build xvidcore
        if fetch_version_if_enabled "xvidcore" xvidcore_version; then
            xvidcore_release="$repo_version"
        else
            xvidcore_release="1.3.7"
            warn "Falling back to Xvid $xvidcore_release because its official release index is unavailable."
        fi
        if build "xvidcore" "$xvidcore_release"; then
            download "https://downloads.xvid.com/downloads/xvidcore-$xvidcore_release.tar.bz2"
            cd "build/generic" || fail "Failed to cd into build/generic. Line: $LINENO"
            execute sh bootstrap.sh
            execute sh configure --prefix="$workspace"
            # Upstream's all/install targets unconditionally build and install
            # both variants. FFmpeg needs only xvid.h and libxvidcore.a.
            execute make "-j$build_threads" libxvidcore.a
            execute install -Dm0644 =build/libxvidcore.a "$workspace/lib/libxvidcore.a"
            execute install -Dm0644 ../../src/xvid.h "$workspace/include/xvid.h"
            build_done "xvidcore" "$xvidcore_release"
        fi
        append_configure_options_if_enabled "xvidcore" "--enable-libxvid"
    fi

    # Build gpac
    git_caller "https://github.com/gpac/gpac.git" "gpac-git"
    if build "$repo_name" "$version"; then
        cd "$packages/gpac-git" || fail "Failed to cd into gpac-git directory"
        local -a gpac_sdl_cfg=()
        if package_enabled "sdl2" && [[ -x "$workspace/bin/sdl2-config" ]]; then
            gpac_sdl_cfg=(--sdl-cfg="$workspace/bin/sdl2-config")
        elif package_enabled "sdl2" && command -v sdl2-config >/dev/null 2>&1; then
            gpac_sdl_cfg=(--sdl-cfg="$(command -v sdl2-config)")
        fi
        # --use-ogg=no prevents symbol conflicts with libogg.a (GPAC has an
        # internal Ogg implementation). Let configure discover the remaining
        # optional libraries instead of claiming nonexistent "local" copies.
        execute sh configure --prefix="$workspace" --static-bin --static-modules \
            --use-ogg=no "${gpac_sdl_cfg[@]}"
        execute make "-j$build_threads"
        execute make install
        build_done "$repo_name" "$version"
    fi

    # Build SVT-AV1
    fetch_version_if_enabled "svt-av1" find_git_repo "24327400" "1"
    if build "svt-av1" "$repo_version"; then
        download "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v$repo_version/SVT-AV1-v$repo_version.tar.bz2" "svt-av1-$repo_version.tar.bz2"
        cmake_ninja_install "Build/linux" -S . \
            -DBUILD_APPS=OFF \
            -DBUILD_SHARED_LIBS=OFF \
            -DBUILD_TESTING=OFF \
            -DENABLE_AVX512="$(check_avx512)" \
            -DEXCLUDE_HASH=ON \
            -DNATIVE=ON \
            -DREPRODUCIBLE_BUILDS=ON
        build_done "svt-av1" "$repo_version"
    fi
    # FFmpeg 8.1 has explicit SVT-AV1 4.x API compatibility and links the
    # current stable encoder normally through SvtAv1Enc.pc.
    append_configure_options_if_enabled "svt-av1" "--enable-libsvtav1"

    # Build VapourSynth
    fetch_version_if_enabled "vapoursynth" find_git_repo "vapoursynth/vapoursynth" "1"
    vapoursynth_package_version="R${repo_version}"
    if build "vapoursynth" "$vapoursynth_package_version"; then
        download "https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R${repo_version}.tar.gz" "vapoursynth-R${repo_version}.tar.gz"

        venv_packages=("Cython==3.2.8")
        setup_python_venv_and_install_packages "$workspace/python_virtual_environment/vapoursynth" "${venv_packages[@]}"

        # Explicitly set the PYTHON environment variable to the virtual environment's Python
        export PYTHON="$workspace/python_virtual_environment/vapoursynth/bin/python"

        path_prepend "$workspace/python_virtual_environment/vapoursynth/bin"
        [[ -n "${ccache_dir:-}" ]] && path_prepend "$ccache_dir"

        # Set Python flags for Meson dependency detection
        PYTHON3_CFLAGS="$(python3-config --cflags)" || fail "python3-config --cflags failed. Line: $LINENO"
        export PYTHON3_CFLAGS
        PYTHON3_LIBS="$(python3-config --ldflags --embed 2>/dev/null || python3-config --ldflags)" || fail "python3-config --ldflags failed. Line: $LINENO"
        export PYTHON3_LIBS

        local vapoursynth_meson_options=()
        append_meson_project_option_if_exists vapoursynth_meson_options "enable_python_module" "false"
        append_meson_project_option_if_exists vapoursynth_meson_options "enable_vspipe" "false"

        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=both \
            --strip \
            "${vapoursynth_meson_options[@]}"

        normalize_vapoursynth_sdk_for_ffmpeg ||
            fail "VapourSynth built, but its FFmpeg SDK files could not be exposed from the Python site-packages install. Line: ${LINENO}"

        build_done "vapoursynth" "$vapoursynth_package_version"
    else
        if package_enabled "vapoursynth"; then
            normalize_vapoursynth_sdk_for_ffmpeg ||
                fail "VapourSynth is enabled but its FFmpeg SDK files are missing. Remove $packages/vapoursynth.done to rebuild it. Line: ${LINENO}"
        fi

        # Explicitly set the PYTHON environment variable to the virtual environment's Python
        PYTHON="$workspace/python_virtual_environment/vapoursynth/bin/python"
        export PYTHON
        path_prepend "$workspace/python_virtual_environment/vapoursynth/bin"
        [[ -n "${ccache_dir:-}" ]] && path_prepend "$ccache_dir"
    fi
    append_configure_options_if_enabled "vapoursynth" "--enable-vapoursynth"

    # Build libgav1
    git_caller "https://chromium.googlesource.com/codecs/libgav1" "libgav1-git"
    if build "$repo_name" "$version"; then
        cd "$packages/libgav1-git" || fail "Failed to cd into libgav1-git. Line: ${LINENO}"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF \
            -DLIBGAV1_ENABLE_EXAMPLES=OFF \
            -DLIBGAV1_ENABLE_TESTS=OFF \
            -DLIBGAV1_THREADPOOL_USE_STD_MUTEX=1
        build_done "$repo_name" "$version"
    fi
}
