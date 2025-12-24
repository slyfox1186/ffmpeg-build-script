#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Support Libraries
##  Supporting libraries and utility functions
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Note: Helper functions (fix_libiconv, fix_libstd_libs, fix_x265_libs, find_latest_nasm_version)
# are now defined in shared-utils.sh to ensure they're available to all scripts

# Install miscellaneous libraries
install_miscellaneous_libraries() {
    echo
    box_out_banner "Installing Miscellaneous Libraries"
    require_vars workspace packages build_threads NONFREE_AND_GPL

    # Build additional libraries when not using GPL/non-free
    if ! "$NONFREE_AND_GPL"; then
        gnu_repo "$GNU_PRIMARY_MIRROR/gmp/"
        if build "gmp" "$repo_version"; then
            download_with_fallback "$GNU_PRIMARY_MIRROR/gmp/gmp-$repo_version.tar.xz" "$GNU_FALLBACK_MIRROR/gmp/gmp-$repo_version.tar.xz"
            execute ./configure --prefix="$workspace" --disable-shared --enable-static
            execute make "-j$build_threads"
            execute make install
            build_done "gmp" "$repo_version"
        fi

        gnu_repo "$GNU_PRIMARY_MIRROR/nettle/"
        if build "nettle" "$repo_version"; then
            download_with_fallback "$GNU_PRIMARY_MIRROR/nettle/nettle-$repo_version.tar.gz" "$GNU_FALLBACK_MIRROR/nettle/nettle-$repo_version.tar.gz"
            execute ./configure --prefix="$workspace" --enable-static --disable-{documentation,openssl,shared} \
                                --libdir="$workspace/lib" CPPFLAGS="-O2 -fno-lto -fPIC -march=native" LDFLAGS="$LDFLAGS"
            execute make "-j$build_threads"
            execute make install
            build_done "nettle" "$repo_version"
        fi

        gnu_repo "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/"
        if build "gnutls" "$repo_version"; then
            download "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-$repo_version.tar.xz"
            execute ./configure --prefix="$workspace" --disable-{cxx,doc,gtk-doc-html,guile,libdane,nls,shared,tests,tools} \
                                --enable-{local-libopts,static} --with-included-{libtasn1,unistring} --without-p11-kit \
                                CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS"
            execute make "-j$build_threads"
            execute make install
            build_done "gnutls" "$repo_version"
        fi
    fi

    # Build freetype
    freetype_version
    repo_version_1="${repo_version//-/.}"
    if build "freetype" "$repo_version_1"; then
        download "https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-$repo_version/freetype-VER-$repo_version.tar.bz2?ref_type=tags" "freetype-$repo_version_1.tar.bz2"
        extracmds=("-D"{harfbuzz,png,bzip2,brotli,zlib,tests}"=disabled")
        execute ./autogen.sh
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "freetype" "$repo_version_1"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfreetype")

    # Build fontconfig
    fontconfig_version
    if build "fontconfig" "$repo_version"; then
        download "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/$repo_version/fontconfig-$repo_version.tar.gz" "fontconfig-$repo_version.tar.gz"
        # Save flags before modification and restore after
        save_compiler_flags
        # -D flags belong in CFLAGS/CPPFLAGS, not LDFLAGS
        CPPFLAGS+=" -DLIBXML_STATIC"
        sed -i "s|Cflags:|& -DLIBXML_STATIC|" "fontconfig.pc.in"
        execute meson setup build --prefix="$workspace" \
                                  --buildtype=release \
                                  --default-library=static \
                                  --strip -Diconv=enabled \
                                  -Ddoc=disabled \
                                  -Dxml-backend=libxml2
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        restore_compiler_flags
        build_done "fontconfig" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfontconfig")

    # Build harfbuzz
    find_git_repo "harfbuzz/harfbuzz" "1" "T"
    if build "harfbuzz" "$repo_version"; then
        download "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/$repo_version.tar.gz" "harfbuzz-$repo_version.tar.gz"
        extracmds=("-D"{benchmark,cairo,docs,glib,gobject,icu,introspection,tests}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "harfbuzz" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libharfbuzz")

    # Note: c2man is skipped - it has compatibility issues with modern systems
    # and is not needed since fribidi is built with -Ddocs=false

    # Build fribidi
    find_git_repo "fribidi/fribidi" "1" "T"
    if build "fribidi" "$repo_version"; then
        download "https://github.com/fribidi/fribidi/archive/refs/tags/v$repo_version.tar.gz" "fribidi-$repo_version.tar.gz"
        extracmds=("-D"{docs,tests}"=false")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "fribidi" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfribidi")

    # Build libass
    find_git_repo "libass/libass" "1" "T"
    if build "libass" "$repo_version"; then
        download "https://github.com/libass/libass/archive/refs/tags/$repo_version.tar.gz" "libass-$repo_version.tar.gz"
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static -Dfontconfig=enabled
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "libass" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libass")

    # Build freeglut
    find_git_repo "freeglut/freeglut" "1" "T"
    if build "freeglut" "$repo_version"; then
        download "https://github.com/freeglut/freeglut/releases/download/v$repo_version/freeglut-$repo_version.tar.gz"
        save_compiler_flags
        CFLAGS+=" -DFREEGLUT_STATIC"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_{DEMOS,SHARED_LIBS}=OFF \
                      -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        restore_compiler_flags
        build_done "freeglut" "$repo_version"
    fi

    # Build libwebp
    git_caller "https://chromium.googlesource.com/webm/libwebp" "libwebp-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"  "libwebp-git"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DZLIB_INCLUDE_DIR="$workspace/include" \
                      -DWEBP_BUILD_{ANIM_UTILS,CWEBP,DWEBP,EXTRAS,VWEBP}=OFF \
                      -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=ON -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libwebp")

    # Build libhwy
    find_git_repo "google/highway" "1" "T"
    if build "libhwy" "$repo_version"; then
        download "https://github.com/google/highway/archive/refs/tags/$repo_version.tar.gz" "libhwy-$repo_version.tar.gz"
        save_compiler_flags
        CFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        CXXFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_TESTING=OFF -DHWY_ENABLE_{EXAMPLES,TESTS}=OFF -DHWY_FORCE_STATIC_LIBS=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        restore_compiler_flags
        build_done "libhwy" "$repo_version"
    fi

    # Build brotli
    find_git_repo "google/brotli" "1" "T"
    if build "brotli" "$repo_version"; then
        download "https://github.com/google/brotli/archive/refs/tags/v$repo_version.tar.gz" "brotli-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "brotli" "$repo_version"
    fi

    # Build lcms2
    find_git_repo "mm2/Little-CMS" "1" "T"
    if build "lcms2" "$repo_version"; then
        download "https://github.com/mm2/Little-CMS/archive/refs/tags/lcms$repo_version.tar.gz" "lcms2-$repo_version.tar.gz"
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-shared --enable-static --with-threaded \
                        PKG_CONFIG_PATH="$workspace/lib/pkgconfig:$PKG_CONFIG_PATH" \
                        LDFLAGS="$LDFLAGS" \
                        LIBS="-lwebp -lsharpyuv"
        execute make "-j$build_threads"
        execute make install
        build_done "lcms2" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-lcms2")

    # Build gflags
    find_git_repo "gflags/gflags" "1" "T"
    if build "gflags" "$repo_version"; then
        download "https://github.com/gflags/gflags/archive/refs/tags/v$repo_version.tar.gz" "gflags-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_gflags_LIB=ON -DBUILD_STATIC_LIBS=ON -DINSTALL_HEADERS=ON \
                      -DREGISTER_{BUILD_DIR,INSTALL_PREFIX}=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "gflags" "$repo_version"
    fi

    # Build OpenCL SDK
    git_caller "https://github.com/KhronosGroup/OpenCL-SDK.git" "opencl-sdk-git" "recurse"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                -DBUILD_{DOCS,EXAMPLES,SHARED_LIBS,TESTING}=OFF -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
                -DCMAKE_C_FLAGS="$CFLAGS" -DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF \
                -DOPENCL_ICD_LOADER_BUILD_SHARED_LIBS=OFF -DOPENCL_SDK_BUILD_{OPENGL_SAMPLES,SAMPLES}=OFF \
                -DOPENCL_SDK_TEST_SAMPLES=OFF -DTHREADS_PREFER_PTHREAD_FLAG=ON -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi
    CONFIGURE_OPTIONS+=("--enable-opencl")

    # Build libjpeg-turbo
    find_git_repo "libjpeg-turbo/libjpeg-turbo" "1" "T"
    if build "libjpeg-turbo" "$repo_version"; then
        download "https://github.com/libjpeg-turbo/libjpeg-turbo/archive/refs/tags/$repo_version.tar.gz" "libjpeg-turbo-$repo_version.tar.gz"
        execute cmake -B build \
                -DCMAKE_INSTALL_PREFIX="$workspace" \
                -DCMAKE_BUILD_TYPE=Release \
                -DENABLE_SHARED=OFF \
                -DENABLE_STATIC=ON \
                -DWITH_JPEG8=1 \
                -DWITH_TURBOJPEG=ON \
                -DWITH_JAVA=OFF \
                -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "libjpeg-turbo" "$repo_version"
    fi

    # Build rubberband (GPL and non-free only)
    if "$NONFREE_AND_GPL"; then
        git_caller "https://github.com/m-ab-s/rubberband.git" "rubberband-git"
        if build "$repo_name" "${version//\$ /}"; then
            echo "Cloning \"$repo_name\" saving version \"$version\""
            git_clone "$git_url"
            execute make "-j$build_threads" PREFIX="$workspace" install-static
            build_done "$repo_name" "$version"
        fi
        CONFIGURE_OPTIONS+=("--enable-librubberband")
    fi

    # Build c-ares
    find_git_repo "c-ares/c-ares" "1" "T"
    if build "c-ares" "$repo_version"; then
        download "https://github.com/c-ares/c-ares/archive/refs/tags/v$repo_version.tar.gz" "c-ares-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                               -DCARES_{BUILD_CONTAINER_TESTS,BUILD_TESTS,SHARED,SYMBOL_HIDING}=OFF \
                               -DCARES_{BUILD_TOOLS,STATIC,STATIC_PIC,THREADS}=ON -G Ninja -Wno-dev
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "c-ares" "$repo_version"
    fi

    # Build lv2
    git_caller "https://github.com/lv2/lv2.git" "lv2-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"

        venv_packages=("lxml" "Markdown" "Pygments" "rdflib")
        setup_python_venv_and_install_packages "$workspace/python_virtual_environment/lv2-git" "${venv_packages[@]}"

        # Set PYTHONPATH to include the virtual environment's site-packages directory
        PYTHONPATH="$workspace/python_virtual_environment/lv2-git/lib/python$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')/site-packages"
        export PYTHONPATH

        PATH="$ccache_dir:$workspace/python_virtual_environment/lv2-git/bin:$PATH"
        remove_duplicate_paths

        # Build with meson - removed deprecated 'plugins' option
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip \
                                  -Ddocs=disabled -Dtests=disabled -Donline_docs=false
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    else
        # Set PYTHONPATH to include the virtual environment's site-packages directory
        PYTHONPATH="$workspace/python_virtual_environment/lv2-git/lib/python$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')/site-packages"
        export PYTHONPATH
        PATH="$ccache_dir:$workspace/python_virtual_environment/lv2-git/bin:$PATH"
        remove_duplicate_paths
    fi

    # Build waflib (duplicate entries combined)
    gitlab_version "https://gitlab.com" "ita1024/waf" "waf-"
    waf_version="$repo_version"
    if build "waflib" "$waf_version"; then
        download "https://gitlab.com/ita1024/waf/-/archive/waf-$waf_version/waf-waf-$waf_version.tar.bz2" "waflib-$waf_version.tar.bz2"
        build_done "waflib" "$waf_version"
    fi

    # Build serd
    gitlab_version "https://gitlab.com" "drobilla/serd" "v"
    serd_version="$repo_version"
    if build "serd" "$serd_version"; then
        download "https://gitlab.com/drobilla/serd/-/archive/v$serd_version/serd-v$serd_version.tar.bz2" "serd-$serd_version.tar.bz2"
        extracmds=("-D"{docs,html,man,man_html,singlehtml,tests,tools}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip -Dstatic=true "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "serd" "$serd_version"
    fi

    # Build pcre2
    github_version "PCRE2Project/pcre2" "pcre2-" "RC"
    pcre2_version="$repo_version"
	    if build "pcre2" "$pcre2_version"; then
	        download "https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-$pcre2_version.tar.gz" "pcre2-$pcre2_version.tar.gz"
	        ensure_autotools
	        execute ./configure --prefix="$workspace" --disable-shared
	        execute make "-j$build_threads"
	        execute make install
	        build_done "pcre2" "$pcre2_version"
	    fi

    # Build zix
    find_git_repo "drobilla/zix" "1" "T"
    if build "zix" "$repo_version"; then
        download "https://gitlab.com/drobilla/zix/-/archive/v$repo_version/zix-v$repo_version.tar.bz2" "zix-$repo_version.tar.bz2"
        extracmds=("-D"{benchmarks,docs,singlehtml,tests,tests_cpp}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "zix" "$repo_version"
    fi

    # Build sord
    gitlab_version "https://gitlab.com" "drobilla/sord" "v"
    sord_version="$repo_version"
    if build "sord" "$sord_version"; then
        save_compiler_flags
        CFLAGS+=" -I$workspace/include/serd-0"
        download "https://gitlab.com/drobilla/sord/-/archive/v$sord_version/sord-v$sord_version.tar.bz2" "sord-$sord_version.tar.bz2"
        extracmds=("-D"{docs,tests,tools}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        restore_compiler_flags
        build_done "sord" "$sord_version"
    fi

    # Build sratom
    gitlab_version "https://gitlab.com" "lv2/sratom" "v"
    sratom_version="$repo_version"
    if build "sratom" "$sratom_version"; then
        download "https://gitlab.com/lv2/sratom/-/archive/v$sratom_version/sratom-v$sratom_version.tar.bz2" "sratom-$sratom_version.tar.bz2"
        extracmds=("-D"{docs,html,singlehtml,tests}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "sratom" "$sratom_version"
    fi

    # lilv: Using system liblilv-dev package (installed via apt)
    CONFIGURE_OPTIONS+=("--enable-lv2")

    # Build libmpg123 - Using system package instead of problematic git version
    # The gypified fork has autotools configuration issues
    if build "libmpg123" "system"; then
        # Check if already installed on system
        if dpkg -s libmpg123-dev &>/dev/null; then
            log "libmpg123-dev already installed on system"
        else
            log "Installing libmpg123 using system package manager"
            execute sudo apt install -y libmpg123-dev
            log "libmpg123 system package installed successfully"
        fi
        build_done "libmpg123" "system"
    fi

    
	    # Build jemalloc
	    find_git_repo "jemalloc/jemalloc" "1" "T"
	    if build "jemalloc" "$repo_version"; then
	        download "https://github.com/jemalloc/jemalloc/archive/refs/tags/$repo_version.tar.gz" "jemalloc-$repo_version.tar.gz"
	        ensure_autotools
	        execute ./configure --prefix="$workspace" --disable-{debug,doc,fill,log,shared,prof,stats} --enable-{autogen,static,xmalloc}
	        execute make "-j$build_threads"
	        execute make install
	        build_done "jemalloc" "$repo_version"
	    fi
}
