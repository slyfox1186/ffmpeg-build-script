#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Support Libraries
##  Supporting libraries and utility functions
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Helper functions that remain in main script
fix_libiconv() {
    if [[ -f "$workspace/lib/libiconv.so.2" ]]; then
        execute sudo cp -f "$workspace/lib/libiconv.so.2" "/usr/lib/libiconv.so.2"
        execute sudo ln -sf "/usr/lib/libiconv.so.2" "/usr/lib/libiconv.so"
    else
        fail "Unable to locate the file \"$workspace/lib/libiconv.so.2\""
    fi
}

fix_libstd_libs() {
    local libstdc_path
    libstdc_path=$(find /usr/lib/x86_64-linux-gnu/ -type f -name 'libstdc++.so.6.0.*' | sort -ruV | head -n1)
    if [[ ! -f "/usr/lib/x86_64-linux-gnu/libstdc++.so" ]] && [[ -f "$libstdc_path" ]]; then
        sudo ln -sf "$libstdc_path" "/usr/lib/x86_64-linux-gnu/libstdc++.so"
    fi
}

fix_x265_libs() {
    local x265_libs x265_libs_trim latest_system_lib
    x265_libs=$(find "$workspace/lib/" -type f -name 'libx265.so.*' | sort -rV | head -n1)
    x265_libs_trim=$(basename "$x265_libs" 2>/dev/null)

    # Copy custom built x265 to system directory
    if [[ -n "$x265_libs" && -f "$x265_libs" ]]; then
        sudo cp -f "$x265_libs" "/usr/lib/x86_64-linux-gnu"
    fi
    
    # Fix broken symlinks and create proper symlink to latest version
    sudo rm -f "/usr/lib/x86_64-linux-gnu/libx265.so"
    latest_system_lib=$(find /usr/lib/x86_64-linux-gnu/ -name 'libx265.so.*' | sort -rV | head -n1)
    if [[ -n "$latest_system_lib" ]]; then
        latest_system_lib_name=$(basename "$latest_system_lib")
        sudo ln -sf "$latest_system_lib_name" "/usr/lib/x86_64-linux-gnu/libx265.so"
        log "Fixed x265 library symlink: libx265.so -> $latest_system_lib_name"
    fi
    
    # Update library cache to prevent ldconfig errors
    sudo ldconfig 2>/dev/null || true
}

find_latest_nasm_version() {
    latest_nasm_version=$(
                    curl -fsS "https://www.nasm.us/pub/nasm/stable/" |
                    grep -oP 'nasm-\K[0-9]+\.[0-9]+\.[0-9]+(?=\.tar\.xz)' |
                    sort -ruV | head -n1
                )
}


# Install miscellaneous libraries
install_miscellaneous_libraries() {
    echo
    log "Installing Miscellaneous Libraries"

    # Build additional libraries when not using GPL/non-free
    if ! "$NONFREE_AND_GPL"; then
        gnu_repo "https://ftp.gnu.org/gnu/gmp/"
        if build "gmp" "$repo_version"; then
            download "https://ftp.gnu.org/gnu/gmp/gmp-$repo_version.tar.xz"
            execute ./configure --prefix="$workspace" --disable-shared --enable-static
            execute make "-j$threads"
            execute make install
            build_done "gmp" "$repo_version"
        fi
        gnu_repo "https://ftp.gnu.org/gnu/nettle/"
        if build "nettle" "$repo_version"; then
            download "https://ftp.gnu.org/gnu/nettle/nettle-$repo_version.tar.gz"
            execute ./configure --prefix="$workspace" --enable-static --disable-{documentation,openssl,shared} \
                                --libdir="$workspace/lib" CPPFLAGS="-O2 -fno-lto -fPIC -march=native" LDFLAGS="$LDFLAGS"
            execute make "-j$threads"
            execute make install
            build_done "nettle" "$repo_version"
        fi
        gnu_repo "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/"
        if build "gnutls" "$repo_version"; then
            download "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-$repo_version.tar.xz"
            execute ./configure --prefix="$workspace" --disable-{cxx,doc,gtk-doc-html,guile,libdane,nls,shared,tests,tools} \
                                --enable-{local-libopts,static} --with-included-{libtasn1,unistring} --without-p11-kit \
                                CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS"
            execute make "-j$threads"
            execute make install
            build_done "gnutls" "$repo_version"
        fi
    fi

    # Build freetype
    freetype_version
    repo_version_1="${repo_version//-/.}"
    if build "freetype" "$repo_version_1"; then
        download "https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-$repo_version/freetype-VER-$repo_version.tar.bz2" "freetype-$repo_version_1.tar.bz2"
        extracmds=("-D"{harfbuzz,png,bzip2,brotli,zlib,tests}"=disabled")
        execute ./autogen.sh
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "freetype" "$repo_version_1"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfreetype")

    # Build fontconfig
    fontconfig_version
    if build "fontconfig" "$repo_version"; then
        download "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/$repo_version/fontconfig-$repo_version.tar.bz2"
        extracmds=("--disable-"{docbook,docs,nls,shared})
        LDFLAGS+=" -DLIBXML_STATIC"
        sed -i "s|Cflags:|& -DLIBXML_STATIC|" "fontconfig.pc.in"
        execute meson setup build --prefix="$workspace" \
                                  --buildtype=release \
                                  --default-library=static \
                                  --strip -Diconv=enabled \
                                  -Ddoc=disabled \
                                  -Dxml-backend=libxml2
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "fontconfig" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfontconfig")

    # Build harfbuzz
    find_git_repo "harfbuzz/harfbuzz" "1" "T"
    if build "harfbuzz" "$repo_version"; then
        download "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/$repo_version.tar.gz" "harfbuzz-$repo_version.tar.gz"
        extracmds=("-D"{benchmark,cairo,docs,glib,gobject,icu,introspection,tests}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "harfbuzz" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libharfbuzz")

    # Build c2man
    git_caller "https://github.com/fribidi/c2man.git" "c2man-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute ./Configure -desO \
                            -D bin="$workspace/bin" \
                            -D cc="/usr/bin/cc" \
                            -D d_gnu="/usr/lib/x86_64-linux-gnu" \
                            -D gcc="/usr/bin/gcc" \
                            -D installmansrc="$workspace/share/man" \
                            -D ldflags="$LDFLAGS" \
                            -D libpth="/usr/lib64 /usr/lib" \
                            -D locincpth="$workspace/include /usr/local/include /usr/include" \
                            -D loclibpth="$workspace/lib64 $workspace/lib /usr/local/lib64 /usr/local/lib" \
                            -D osname="$OS" \
                            -D prefix="$workspace" \
                            -D privlib="$workspace/lib/c2man" \
                            -D privlibexp="$workspace/lib/c2man"
        execute sudo make depend
        execute sudo make "-j$threads"
        execute sudo make install
        build_done "$repo_name" "$version"
    fi

    # Build fribidi
    find_git_repo "fribidi/fribidi" "1" "T"
    if build "fribidi" "$repo_version"; then
        download "https://github.com/fribidi/fribidi/archive/refs/tags/v$repo_version.tar.gz" "fribidi-$repo_version.tar.gz"
        extracmds=("-D"{docs,tests}"=false")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "fribidi" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libfribidi")

    # Build libass
    find_git_repo "libass/libass" "1" "T"
    if build "libass" "$repo_version"; then
        download "https://github.com/libass/libass/archive/refs/tags/$repo_version.tar.gz" "libass-$repo_version.tar.gz"
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static -Dfontconfig=enabled
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libass" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libass")

    # Build freeglut
    find_git_repo "freeglut/freeglut" "1" "T"
    if build "freeglut" "$repo_version"; then
        download "https://github.com/freeglut/freeglut/releases/download/v$repo_version/freeglut-$repo_version.tar.gz"
        CFLAGS+=" -DFREEGLUT_STATIC"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_{DEMOS,SHARED_LIBS}=OFF \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "freeglut" "$repo_version"
    fi

    # Build libwebp
    git_caller "https://chromium.googlesource.com/webm/libwebp" "libwebp-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"  "libwebp-git"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DZLIB_INCLUDE_DIR="$workspace/include" \
                      -DWEBP_BUILD_{ANIM_UTILS,EXTRAS,VWEBP}=OFF -DWEBP_BUILD_{CWEBP,DWEBP}=ON \
                      -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=ON -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "$repo_name" "$version"
    fi
    CONFIGURE_OPTIONS+=("--enable-libwebp")

    # Build libhwy
    find_git_repo "google/highway" "1" "T"
    if build "libhwy" "$repo_version"; then
        download "https://github.com/google/highway/archive/refs/tags/$repo_version.tar.gz" "libhwy-$repo_version.tar.gz"
        CFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        CXXFLAGS+=" -DHWY_COMPILE_ALL_ATTAINABLE"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_TESTING=OFF -DHWY_ENABLE_{EXAMPLES,TESTS}=OFF -DHWY_FORCE_STATIC_LIBS=ON \
                      -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libhwy" "$repo_version"
    fi

    # Build brotli
    find_git_repo "google/brotli" "1" "T"
    if build "brotli" "$repo_version"; then
        download "https://github.com/google/brotli/archive/refs/tags/v$repo_version.tar.gz" "brotli-$repo_version.tar.gz"
        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
                      -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -G Ninja -Wno-dev
        execute ninja "-j$threads" -C build
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
        execute make "-j$threads"
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
        execute ninja "-j$threads" -C build
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
        execute ninja "-j$threads" -C build
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
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "libjpeg-turbo" "$repo_version"
    fi

    # Build rubberband (GPL and non-free only)
    if "$NONFREE_AND_GPL"; then
        git_caller "https://github.com/m-ab-s/rubberband.git" "rubberband-git"
        if build "$repo_name" "${version//\$ /}"; then
            echo "Cloning \"$repo_name\" saving version \"$version\""
            git_clone "$git_url"
            execute make "-j$threads" PREFIX="$workspace" install-static
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
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "c-ares" "$repo_version"
    fi

    # Build lv2
    git_caller "https://github.com/lv2/lv2.git" "lv2-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        case "$STATIC_VER" in
            11) lv2_switch=enabled ;;
            *)  lv2_switch=disabled ;;
        esac

        venv_packages=("lxml" "Markdown" "Pygments" "rdflib")
        setup_python_venv_and_install_packages "$workspace/python_virtual_environment/lv2-git" "${venv_packages[@]}"

        # Set PYTHONPATH to include the virtual environment's site-packages directory
        PYTHONPATH="$workspace/python_virtual_environment/lv2-git/lib/python$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')/site-packages"
        export PYTHONPATH

        PATH="$ccache_dir:$workspace/python_virtual_environment/lv2-git/bin:$PATH"
        remove_duplicate_paths

        # Assuming the build process continues here with Meson and Ninja
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip \
                                  -D{docs,tests}=disabled -Donline_docs=false -Dplugins="$lv2_switch"
        execute ninja "-j$threads" -C build
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
    waf_version=$(curl -fsS "https://gitlab.com/ita1024/waf/-/tags" | 
                  grep -oP 'href="[^"]*/-/tags/waf-\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                  sort -ruV | head -n1)
    if build "waflib" "$waf_version"; then
        download "https://gitlab.com/ita1024/waf/-/archive/waf-$waf_version/waf-waf-$waf_version.tar.bz2" "waflib-$waf_version.tar.bz2"
        build_done "waflib" "$waf_version"
    fi

    # Build serd
    serd_version=$(curl -fsS "https://gitlab.com/drobilla/serd/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | head -n1)
    if build "serd" "$serd_version"; then
        download "https://gitlab.com/drobilla/serd/-/archive/v$serd_version/serd-v$serd_version.tar.bz2" "serd-$serd_version.tar.bz2"
        extracmds=("-D"{docs,html,man,man_html,singlehtml,tests,tools}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip -Dstatic=true "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "serd" "$serd_version"
    fi

    # Build pcre2
    pcre2_version=$(curl -fsS "https://github.com/PCRE2Project/pcre2/tags" | 
                    grep -oP 'href="/PCRE2Project/pcre2/releases/tag/pcre2-\K[0-9]+\.[0-9]+(?=")' | 
                    grep -v 'RC' | sort -ruV | head -n1)
    if build "pcre2" "$pcre2_version"; then
        download "https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-$pcre2_version.tar.gz" "pcre2-$pcre2_version.tar.gz"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$threads"
        execute make install
        build_done "pcre2" "$pcre2_version"
    fi

    # Build zix
    find_git_repo "drobilla/zix" "1" "T"
    if build "zix" "$repo_version"; then
        download "https://gitlab.com/drobilla/zix/-/archive/v$repo_version/zix-v$repo_version.tar.bz2" "zix-$repo_version.tar.bz2"
        extracmds=("-D"{benchmarks,docs,singlehtml,tests,tests_cpp}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "zix" "$repo_version"
    fi

    # Build sord
    sord_version=$(curl -fsS "https://gitlab.com/drobilla/sord/-/tags" | 
                   grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                   sort -ruV | head -n1)
    if build "sord" "$sord_version"; then
        CFLAGS+=" -I$workspace/include/serd-0"
        download "https://gitlab.com/drobilla/sord/-/archive/v$sord_version/sord-v$sord_version.tar.bz2" "sord-$sord_version.tar.bz2"
        extracmds=("-D"{docs,tests,tools}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "sord" "$sord_version"
    fi

    # Build sratom
    sratom_version=$(curl -fsS "https://gitlab.com/lv2/sratom/-/tags" | 
                     grep -oP 'href="[^"]*/-/tags/v\K[0-9]+\.[0-9]+\.[0-9]+(?=")' | 
                     sort -ruV | head -n1)
    if build "sratom" "$sratom_version"; then
        download "https://gitlab.com/lv2/sratom/-/archive/v$sratom_version/sratom-v$sratom_version.tar.bz2" "sratom-$sratom_version.tar.bz2"
        extracmds=("-D"{docs,html,singlehtml,tests}"=disabled")
        execute meson setup build --prefix="$workspace" --buildtype=release --default-library=static --strip "${extracmds[@]}"
        execute ninja "-j$threads" -C build
        execute ninja -C build install
        build_done "sratom" "$sratom_version"
    fi

    # Build lilv - Using system package instead of building from source
    # The system liblilv-dev package is sufficient for FFmpeg's LV2 support
    log "Using system lilv package (liblilv-dev) for LV2 support"
    CONFIGURE_OPTIONS+=("--enable-lv2")

    # Build libmpg123 - Using system package instead of problematic git version
    # The gypified fork has autotools configuration issues
    log "Installing libmpg123 using system package manager"
    execute sudo apt-get install -y libmpg123-dev
    log "libmpg123 system package installed successfully"

    # Build jansson
    find_git_repo "akheron/jansson" "1" "T"
    if build "jansson" "$repo_version"; then
        download "https://github.com/akheron/jansson/archive/refs/tags/v$repo_version.tar.gz" "jansson-$repo_version.tar.gz"
        execute autoupdate
        execute libtoolize --force
        execute aclocal -I /usr/share/aclocal
        execute autoheader
        execute automake --add-missing --copy
        execute autoconf
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$threads"
        execute make install
        build_done "jansson" "$repo_version"
    fi

    # Build jemalloc
    find_git_repo "jemalloc/jemalloc" "1" "T"
    if build "jemalloc" "$repo_version"; then
        download "https://github.com/jemalloc/jemalloc/archive/refs/tags/$repo_version.tar.gz" "jemalloc-$repo_version.tar.gz"
        execute autoupdate
        execute ./autogen.sh
        execute ./configure --prefix="$workspace" --disable-{debug,doc,fill,log,shared,prof,stats} --enable-{autogen,static,xmalloc}
        execute make "-j$threads"
        execute make install
        build_done "jemalloc" "$repo_version"
    fi

    # Build cunit
    git_caller "https://github.com/jacklicn/cunit.git" "cunit-git"
    if build "$repo_name" "${version//\$ /}"; then
        echo "Cloning \"$repo_name\" saving version \"$version\""
        git_clone "$git_url"
        execute autoupdate
        execute libtoolize --force --copy
        execute aclocal -I /usr/share/aclocal
        execute autoheader
        execute automake --add-missing --copy --force-missing
        execute autoconf
        execute ./configure --prefix="$workspace" --disable-shared
        execute make "-j$threads"
        execute make install
        build_done "$repo_name" "$version"
    fi

    log "Miscellaneous libraries installation completed"
}
