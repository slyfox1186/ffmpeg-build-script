#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Support Libraries
##  Supporting libraries and utility functions
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install miscellaneous libraries
install_miscellaneous_libraries() {
    local serd_version pcre2_version sord_version sratom_version lilv_version
    local -a extracmds=()

    echo
    box_out_banner "Installing Miscellaneous Libraries"
    require_vars workspace packages build_threads NONFREE_AND_GPL

    # GnuTLS is the free TLS stack. Keep it available in GPL/non-free builds
    # whenever the user has not selected the optional OpenSSL build.
    if ! is_true "$NONFREE_AND_GPL" || ! package_enabled "openssl"; then
        fetch_version_if_enabled "gmp" gnu_repo "$GNU_PRIMARY_MIRROR/gmp/"
        if build "gmp" "$repo_version"; then
            download_with_fallback "$GNU_PRIMARY_MIRROR/gmp/gmp-$repo_version.tar.xz" "$GNU_FALLBACK_MIRROR/gmp/gmp-$repo_version.tar.xz"
            execute sh configure --prefix="$workspace" --disable-shared --enable-static
            execute make "-j$build_threads"
            execute make install
            build_done "gmp" "$repo_version"
        fi

        fetch_version_if_enabled "nettle" gnu_repo "$GNU_PRIMARY_MIRROR/nettle/"
        if build "nettle" "$repo_version"; then
            download_with_fallback "$GNU_PRIMARY_MIRROR/nettle/nettle-$repo_version.tar.gz" "$GNU_FALLBACK_MIRROR/nettle/nettle-$repo_version.tar.gz"
            execute sh configure --prefix="$workspace" --enable-static --disable-{documentation,openssl,shared} \
                                --libdir="$workspace/lib" \
                                CPPFLAGS="${CPPFLAGS:-} -fno-lto" LDFLAGS="$LDFLAGS"
            execute make "-j$build_threads"
            execute make install
            build_done "nettle" "$repo_version"
        fi

        fetch_version_if_enabled "gnutls" gnu_repo "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/"
        if build "gnutls" "$repo_version"; then
            download "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-$repo_version.tar.xz"
            execute sh configure --prefix="$workspace" --disable-{cxx,doc,gtk-doc-html,guile,libdane,nls,shared,tests,tools} \
                                --enable-{local-libopts,static} --with-included-{libtasn1,unistring} --without-p11-kit \
                                CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS"
            execute make "-j$build_threads"
            execute make install
            build_done "gnutls" "$repo_version"
        fi

        # Wire FFmpeg's TLS to the gnutls stack just built (free builds only; GPL/non-free
        # builds use OpenSSL instead). Without this, a default build has no https/tls
        # support at all. gmp additionally enables rtmpe/rtmpte.
        append_configure_options_if_enabled "gnutls" "--enable-gnutls"
        append_configure_options_if_enabled "gmp" "--enable-gmp"
    fi

    # Build freetype
    freetype_version_source=""
    fetch_version_if_enabled "freetype" freetype_version ||
        fail "Failed to detect FreeType version from the official FreeType release archive or FreeDesktop GitLab. Line: ${LINENO}"
    repo_version_1="$repo_version"
    if package_enabled "freetype"; then
        [[ "$repo_version_1" =~ ^[0-9]+(\.[0-9]+){2,3}$ ]] ||
            fail "Invalid FreeType version detected: '$repo_version_1'. Line: ${LINENO}"
    fi
    if build "freetype" "$repo_version_1"; then
        if [[ "${freetype_version_source:-}" == "gitlab" ]]; then
            DOWNLOAD_CONNECT_TIMEOUT=3 DOWNLOAD_MAX_TIME=45 DOWNLOAD_RETRY=0 DOWNLOAD_RETRY_DELAY=3 \
                download_with_fallback \
                    "$(freetype_gitlab_archive_url "${repo_version//./-}")" \
                    "$(freetype_release_archive_url "$repo_version_1")"
        else
            DOWNLOAD_CONNECT_TIMEOUT=3 DOWNLOAD_MAX_TIME=45 DOWNLOAD_RETRY=0 DOWNLOAD_RETRY_DELAY=3 \
                download_with_fallback \
                    "$(freetype_release_archive_url "$repo_version_1")" \
                    "$(freetype_sourceforge_archive_url "$repo_version_1")"
        fi
        extracmds=("-D"{harfbuzz,png,bzip2,brotli,zlib,tests}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        build_done "freetype" "$repo_version_1"
    fi
    append_configure_options_if_enabled "freetype" "--enable-libfreetype"

    # Build fontconfig
    fontconfig_version_source=""
    fetch_version_if_enabled "fontconfig" fontconfig_version ||
        fail "Failed to detect Fontconfig version from the official Fontconfig release archive or FreeDesktop GitLab. Line: ${LINENO}"
    if package_enabled "fontconfig"; then
        [[ "$repo_version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] ||
            fail "Invalid Fontconfig version detected: '$repo_version'. Line: ${LINENO}"
    fi
    if build "fontconfig" "$repo_version"; then
        if [[ "${fontconfig_version_source:-}" == "gitlab" ]]; then
            DOWNLOAD_CONNECT_TIMEOUT=3 DOWNLOAD_MAX_TIME=45 DOWNLOAD_RETRY=0 DOWNLOAD_RETRY_DELAY=3 \
                download_with_fallback \
                    "$(fontconfig_gitlab_archive_url "$repo_version")" \
                    "$(fontconfig_release_archive_url "$repo_version")"
        else
            DOWNLOAD_CONNECT_TIMEOUT=3 DOWNLOAD_MAX_TIME=45 DOWNLOAD_RETRY=0 DOWNLOAD_RETRY_DELAY=3 \
                download "$(fontconfig_release_archive_url "$repo_version")" "fontconfig-$repo_version.tar.xz"
        fi

        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=static \
            --strip -Diconv=enabled \
            -Ddoc=disabled \
            -Dxml-backend=libxml2
        build_done "fontconfig" "$repo_version"
    fi
    append_configure_options_if_enabled "fontconfig" "--enable-libfontconfig"

    # Build harfbuzz
    fetch_version_if_enabled "harfbuzz" find_git_repo "harfbuzz/harfbuzz" "1"
    if build "harfbuzz" "$repo_version"; then
        download "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/$repo_version.tar.gz" "harfbuzz-$repo_version.tar.gz"
        extracmds=("-D"{benchmark,cairo,docs,glib,gobject,icu,introspection,tests,utilities}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        build_done "harfbuzz" "$repo_version"
    fi
    append_configure_options_if_enabled "harfbuzz" "--enable-libharfbuzz"

    # Note: c2man is skipped - it has compatibility issues with modern systems
    # and is not needed since fribidi is built with -Ddocs=false

    # Build fribidi
    fetch_version_if_enabled "fribidi" find_git_repo "fribidi/fribidi" "1"
    if build "fribidi" "$repo_version"; then
        download "https://github.com/fribidi/fribidi/archive/refs/tags/v$repo_version.tar.gz" "fribidi-$repo_version.tar.gz"
        extracmds=("-D"{bin,docs,tests}"=false")
        meson_ninja_install "build" --buildtype=release --default-library=static "${extracmds[@]}"
        build_done "fribidi" "$repo_version"
    fi
    append_configure_options_if_enabled "fribidi" "--enable-libfribidi"

    # Build libass
    fetch_version_if_enabled "libass" find_git_repo "libass/libass" "1"
    if build "libass" "$repo_version"; then
        download "https://github.com/libass/libass/archive/refs/tags/$repo_version.tar.gz" "libass-$repo_version.tar.gz"
        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=static \
            -Dauto_features=disabled \
            -Dfontconfig=enabled
        build_done "libass" "$repo_version"
    fi
    append_configure_options_if_enabled "libass" "--enable-libass"

    # Build freeglut
    fetch_version_if_enabled "freeglut" find_git_repo "freeglut/freeglut" "1"
    if build "freeglut" "$repo_version"; then
        download "https://github.com/freeglut/freeglut/releases/download/v$repo_version/freeglut-$repo_version.tar.gz"
        save_compiler_flags
        CFLAGS+=" -DFREEGLUT_STATIC"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_{DEMOS,SHARED_LIBS}=OFF
        restore_compiler_flags
        build_done "freeglut" "$repo_version"
    fi

    # Build libwebp
    git_caller "https://chromium.googlesource.com/webm/libwebp" "libwebp-git"
    if build "$repo_name" "$version"; then
        cd "$packages/libwebp-git" || fail "Failed to cd into libwebp-git. Line: ${LINENO}"
        cmake_ninja_install "build" \
            -DBUILD_SHARED_LIBS=OFF \
            -DWEBP_BUILD_{ANIM_UTILS,CWEBP,DWEBP,EXTRAS,GIF2WEBP,IMG2WEBP,VWEBP,WEBPINFO,WEBPMUX}=OFF \
            -DWEBP_BUILD_FUZZTEST=OFF -DWEBP_BUILD_LIBWEBPMUX=ON \
            -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=ON
        build_done "$repo_name" "$version"
    fi
    append_configure_options_if_enabled "libwebp-git" "--enable-libwebp"

    # Build libhwy
    fetch_version_if_enabled "libhwy" find_git_repo "google/highway" "1"
    if build "libhwy" "$repo_version"; then
        download "https://github.com/google/highway/archive/refs/tags/$repo_version.tar.gz" "libhwy-$repo_version.tar.gz"
        save_compiler_flags
        CFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        CXXFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        cmake_ninja_install "build" \
            -DBUILD_TESTING=OFF -DHWY_ENABLE_{EXAMPLES,TESTS}=OFF -DHWY_FORCE_STATIC_LIBS=ON
        restore_compiler_flags
        build_done "libhwy" "$repo_version"
    fi

    # Build brotli
    fetch_version_if_enabled "brotli" find_git_repo "google/brotli" "1"
    if build "brotli" "$repo_version"; then
        download "https://github.com/google/brotli/archive/refs/tags/v$repo_version.tar.gz" "brotli-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBROTLI_BUILD_TOOLS=OFF \
            -DBROTLI_DISABLE_TESTS=ON \
            -DBUILD_SHARED_LIBS=OFF
        build_done "brotli" "$repo_version"
    fi

    # Build lcms2
    fetch_version_if_enabled "lcms2" find_git_repo "mm2/Little-CMS" "1"
    if build "lcms2" "$repo_version"; then
        download "https://github.com/mm2/Little-CMS/archive/refs/tags/lcms$repo_version.tar.gz" "lcms2-$repo_version.tar.gz"
        execute sh autogen.sh
        # The threaded plugin is GPL-3-only according to upstream and does not
        # belong in this always-available library path. FFmpeg needs the core
        # static lcms2 library, not its JPEG/TIFF utilities or plugin.
        execute sh configure --prefix="$workspace" --disable-shared --enable-static \
            --without-jpeg --without-tiff --without-zlib
        execute make "-j$build_threads"
        execute make install
        build_done "lcms2" "$repo_version"
    fi
    append_configure_options_if_enabled "lcms2" "--enable-lcms2"

    # Build gflags
    fetch_version_if_enabled "gflags" find_git_repo "gflags/gflags" "1"
    if build "gflags" "$repo_version"; then
        download "https://github.com/gflags/gflags/archive/refs/tags/v$repo_version.tar.gz" "gflags-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DBUILD_gflags_LIB=ON \
            -DBUILD_SHARED_LIBS=OFF \
            -DBUILD_STATIC_LIBS=ON \
            -DINSTALL_HEADERS=ON \
            -DREGISTER_BUILD_DIR=OFF \
            -DREGISTER_INSTALL_PREFIX=OFF
        build_done "gflags" "$repo_version"
    fi

    # Build OpenCL SDK
    git_caller "https://github.com/KhronosGroup/OpenCL-SDK.git" "opencl-sdk-git" "recurse"
    if build "$repo_name" "$version"; then
        cd "$packages/opencl-sdk-git" || fail "Failed to cd into opencl-sdk-git. Line: ${LINENO}"
        cmake_ninja_install "build" -S . \
            -DBUILD_{DOCS,EXAMPLES,SHARED_LIBS,TESTING}=OFF -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
            -DCMAKE_C_FLAGS="$CFLAGS" -DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF \
            -DOPENCL_ICD_LOADER_BUILD_SHARED_LIBS=OFF -DOPENCL_SDK_BUILD_{OPENGL_SAMPLES,SAMPLES}=OFF \
            -DOPENCL_SDK_TEST_SAMPLES=OFF -DTHREADS_PREFER_PTHREAD_FLAG=ON
        build_done "$repo_name" "$version"
    fi
    append_configure_options_if_enabled "opencl-sdk-git" "--enable-opencl"

    # Build Vulkan-Headers (header-only). Compile-time SDK support should not
    # depend on whether this particular host currently exposes a GPU; the
    # resulting FFmpeg binary discovers Vulkan devices at runtime.
    git_caller "https://github.com/KhronosGroup/Vulkan-Headers.git" "vulkan-headers-git"
    if build "$repo_name" "$version"; then
        cd "$packages/vulkan-headers-git" ||
            fail "Failed to cd into vulkan-headers-git. Line: ${LINENO}"
        cmake_ninja_install "build" \
            -DVULKAN_HEADERS_ENABLE_INSTALL=ON \
            -DVULKAN_HEADERS_ENABLE_MODULE=OFF \
            -DVULKAN_HEADERS_ENABLE_TESTS=OFF
        build_done "$repo_name" "$version"
    fi

    # Build libjpeg-turbo
    fetch_version_if_enabled "libjpeg-turbo" find_git_repo "libjpeg-turbo/libjpeg-turbo" "1"
    if build "libjpeg-turbo" "$repo_version"; then
        download "https://github.com/libjpeg-turbo/libjpeg-turbo/archive/refs/tags/$repo_version.tar.gz" "libjpeg-turbo-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DENABLE_SHARED=OFF \
            -DENABLE_STATIC=ON \
            -DWITH_JPEG8=1 \
            -DWITH_TURBOJPEG=ON \
            -DWITH_JAVA=OFF
        build_done "libjpeg-turbo" "$repo_version"
    fi

    # Build rubberband (GPL and non-free only)
    if is_true "$NONFREE_AND_GPL"; then
        git_caller "https://github.com/breakfastquay/rubberband.git" "rubberband-git"
        if build "$repo_name" "$version"; then
            cd "$packages/rubberband-git" || fail "Failed to cd into rubberband-git. Line: ${LINENO}"
            meson_ninja_install "build" \
                --buildtype=release \
                --default-library=static \
                -Dauto_features=disabled \
                -Dfft=builtin \
                -Dresampler=builtin
            # Upstream's generated .pc links only -lrubberband even though the
            # static archive is C++; expose the runtime for C-driver consumers.
            pkgconfig_add_private_lib "rubberband" "-lstdc++"
            build_done "$repo_name" "$version"
        fi
        append_configure_options_if_enabled "rubberband-git" "--enable-librubberband"
    fi

    # Build c-ares
    fetch_version_if_enabled "c-ares" find_git_repo "c-ares/c-ares" "1"
    if build "c-ares" "$repo_version"; then
        download "https://github.com/c-ares/c-ares/archive/refs/tags/v$repo_version.tar.gz" "c-ares-$repo_version.tar.gz"
        cmake_ninja_install "build" \
            -DCARES_{BUILD_CONTAINER_TESTS,BUILD_TESTS,BUILD_TOOLS,SHARED,SYMBOL_HIDING}=OFF \
            -DCARES_{STATIC,STATIC_PIC,THREADS}=ON
        build_done "c-ares" "$repo_version"
    fi

    # Build lv2
    git_caller "https://github.com/lv2/lv2.git" "lv2-git"
    if build "$repo_name" "$version"; then
        cd "$packages/lv2-git" || fail "Failed to cd into lv2-git. Line: ${LINENO}"

        # Documentation/tests are the only upstream consumers of the optional
        # Python modules, so a library/header-only build needs no private venv.
        meson_ninja_install "build" --buildtype=release --default-library=static --strip \
            -Ddocs=disabled -Dtests=disabled -Dtools=disabled -Donline_docs=false
        build_done "$repo_name" "$version"
    fi

    # Build serd
    fetch_version_if_enabled "serd" gitlab_version "https://gitlab.com" "drobilla/serd" "v"
    serd_version="$repo_version"
    if build "serd" "$serd_version"; then
        download "https://gitlab.com/drobilla/serd/-/archive/v$serd_version/serd-v$serd_version.tar.bz2" "serd-$serd_version.tar.bz2"
        extracmds=("-D"{docs,html,man,man_html,singlehtml,tests,tools}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip -Dstatic=true "${extracmds[@]}"
        build_done "serd" "$serd_version"
    fi

    # Build pcre2
    fetch_version_if_enabled "pcre2" github_version "PCRE2Project/pcre2" "pcre2-" "RC"
    pcre2_version="$repo_version"
    if build "pcre2" "$pcre2_version"; then
        download "https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-$pcre2_version.tar.gz" "pcre2-$pcre2_version.tar.gz"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-shared
        execute make "-j$build_threads"
        execute make install
        build_done "pcre2" "$pcre2_version"
    fi

    # Build zix
    fetch_version_if_enabled "zix" find_git_repo "drobilla/zix" "1"
    if build "zix" "$repo_version"; then
        download "https://gitlab.com/drobilla/zix/-/archive/v$repo_version/zix-v$repo_version.tar.bz2" "zix-$repo_version.tar.bz2"
        extracmds=("-D"{benchmarks,docs,singlehtml,tests,tests_cpp}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        build_done "zix" "$repo_version"
    fi

    # Build sord
    fetch_version_if_enabled "sord" gitlab_version "https://gitlab.com" "drobilla/sord" "v"
    sord_version="$repo_version"
    if build "sord" "$sord_version"; then
        save_compiler_flags
        CFLAGS+=" -I$workspace/include/serd-0"
        download "https://gitlab.com/drobilla/sord/-/archive/v$sord_version/sord-v$sord_version.tar.bz2" "sord-$sord_version.tar.bz2"
        extracmds=("-D"{docs,tests,tools}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        restore_compiler_flags
        build_done "sord" "$sord_version"
    fi

    # Build sratom
    fetch_version_if_enabled "sratom" gitlab_version "https://gitlab.com" "lv2/sratom" "v"
    sratom_version="$repo_version"
    if build "sratom" "$sratom_version"; then
        download "https://gitlab.com/lv2/sratom/-/archive/v$sratom_version/sratom-v$sratom_version.tar.bz2" "sratom-$sratom_version.tar.bz2"
        extracmds=("-D"{docs,html,singlehtml,tests}"=disabled")
        meson_ninja_install "build" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        build_done "sratom" "$sratom_version"
    fi

    # Build Lilv against the same LV2/Serd/Zix/Sord/Sratom stack installed in
    # this workspace. Linking a distro Lilv against newer workspace transitive
    # libraries can silently mix ABI generations.
    fetch_version_if_enabled "lilv" gitlab_version "https://gitlab.com" "lv2/lilv" "v"
    lilv_version="$repo_version"
    if build "lilv" "$lilv_version"; then
        download "https://gitlab.com/lv2/lilv/-/archive/v$lilv_version/lilv-v$lilv_version.tar.bz2" \
            "lilv-$lilv_version.tar.bz2"
        extracmds=("-D"{bindings_cpp,bindings_py,docs,html,singlehtml,tests,tools}"=disabled")
        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=static \
            --strip \
            -Dauto_features=disabled \
            -Ddynmanifest=disabled \
            "${extracmds[@]}"
        build_done "lilv" "$lilv_version"
    fi
    append_configure_options_if_enabled "lilv" "--enable-lv2"


    # Build jemalloc
    fetch_version_if_enabled "jemalloc" find_git_repo "jemalloc/jemalloc" "1"
    if build "jemalloc" "$repo_version"; then
        download "https://github.com/jemalloc/jemalloc/archive/refs/tags/$repo_version.tar.gz" "jemalloc-$repo_version.tar.gz"
        ensure_autotools
        execute sh configure --prefix="$workspace" --disable-{debug,doc,fill,log,shared,prof,stats} --enable-{autogen,static,xmalloc}
        execute make "-j$build_threads"
        execute make install
        build_done "jemalloc" "$repo_version"
    fi
}
