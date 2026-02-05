#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Global Tools
##  Build system tools and core libraries (m4, autoconf, cmake, etc.)
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Install global build tools
install_global_tools() {
    echo
    box_out_banner "Installing Global Tools"
    require_vars workspace packages build_threads

    # Alert the user that an AMD GPU was found without a Geforce GPU present
    if [[ "${gpu_flag:-0}" -eq 1 ]]; then
        printf "\n%s\n" "An AMD GPU was detected without a Nvidia GPU present."
    fi

    # Source the compiler flags
    source_compiler_flags

    # Build m4
    if build "m4" "latest"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/m4/m4-latest.tar.xz" "$GNU_FALLBACK_MIRROR/m4/m4-latest.tar.xz"
        execute sh configure --prefix="$workspace" --enable-c++ --enable-threads=posix
        execute make "-j$build_threads"
        execute make install
        build_done "m4" "latest"
    fi

    # Build autoconf
    gnu_repo "$GNU_PRIMARY_MIRROR/autoconf/"
    local autoconf_version="$repo_version"
    if build "autoconf" "$autoconf_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/autoconf/autoconf-$autoconf_version.tar.xz" "$GNU_FALLBACK_MIRROR/autoconf/autoconf-$autoconf_version.tar.xz"
        execute sh configure --prefix="$workspace" M4="$workspace/bin/m4"
        execute make "-j$build_threads"
        execute make install
        build_done "autoconf" "$autoconf_version"
    fi

    # Build automake
    gnu_repo "$GNU_PRIMARY_MIRROR/automake/"
    local automake_version="$repo_version"
    if build "automake" "$automake_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/automake/automake-$automake_version.tar.xz" "$GNU_FALLBACK_MIRROR/automake/automake-$automake_version.tar.xz"
        execute sh configure --prefix="$workspace"
        execute make "-j$build_threads"
        execute make install
        build_done "automake" "$automake_version"
    fi

    # Build libtool
    gnu_repo "$GNU_PRIMARY_MIRROR/libtool/"
    local libtool_version="$repo_version"
    if build "libtool" "$libtool_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/libtool/libtool-$libtool_version.tar.xz" "$GNU_FALLBACK_MIRROR/libtool/libtool-$libtool_version.tar.xz"
        execute sh configure --prefix="$workspace" --with-pic M4="$workspace/bin/m4"
        execute make "-j$build_threads"
        execute make install
        build_done "libtool" "$libtool_version"
    fi

    # Build pkgconf (modern pkgconf replacement)
    # Tags are formatted as "pkgconf-X.Y.Z" so extract version directly
    local pkgconf_version
    pkgconf_version=$(curl -fsSL "https://github.com/pkgconf/pkgconf/tags" 2>/dev/null | grep -oP 'pkgconf-\K\d+\.\d+\.\d+(?=\.tar\.gz)' | head -1)
    [[ -z "$pkgconf_version" ]] && fail "Failed to detect pkgconf version from GitHub"
    if build "pkgconf" "$pkgconf_version"; then
        download "https://github.com/pkgconf/pkgconf/archive/refs/tags/pkgconf-$pkgconf_version.tar.gz" "pkgconf-$pkgconf_version.tar.gz"
        # Release tarballs from GitHub need autoreconf
        execute autoreconf -fi
        execute sh configure --prefix="$workspace" --enable-silent-rules \
            --with-pkgconf-dir="$PKG_CONFIG_PATH" \
            --with-system-libdir="/lib:/lib64:/usr/lib:/usr/lib64:/usr/lib/x86_64-linux-gnu" \
            --with-system-includedir="/usr/include:/usr/include/x86_64-linux-gnu"
        execute make "-j$build_threads"
        execute make install
        # Create pkg-config symlink for compatibility
        ln -sf "$workspace/bin/pkgconf" "$workspace/bin/pkg-config"
        build_done "pkgconf" "$pkgconf_version"
    fi

    # Build cmake
    find_git_repo "Kitware/CMake" "1" "T"
    if build "cmake" "$repo_version"; then
        download "https://github.com/Kitware/CMake/archive/refs/tags/v$repo_version.tar.gz" "cmake-$repo_version.tar.gz"
        execute ./bootstrap --prefix="$workspace" --parallel="$build_threads" --enable-ccache --no-qt-gui --no-debugger
        execute make "-j$build_threads"
        execute make install
        build_done "cmake" "$repo_version"
    fi

    # Build meson
    find_git_repo "mesonbuild/meson" "1" "T"
    if build "meson" "$repo_version"; then
        local meson_venv="$workspace/python_virtual_environment/build-tools"
        setup_python_venv_and_install_packages "$meson_venv" "meson==$repo_version"
        build_done "meson" "$repo_version"
    fi
    # Ensure the build-tools venv is first on PATH so `meson` is consistent across builds.
    if [[ -d "$workspace/python_virtual_environment/build-tools/bin" ]]; then
        PATH="$workspace/python_virtual_environment/build-tools/bin:$PATH"
        remove_duplicate_paths
    fi

    # Build ninja
    find_git_repo "ninja-build/ninja" "1" "T"
    if build "ninja" "$repo_version"; then
        download "https://github.com/ninja-build/ninja/archive/refs/tags/v$repo_version.tar.gz" "ninja-$repo_version.tar.gz"
        execute python3 configure.py --bootstrap
        execute install -m 0755 ninja "$workspace/bin/ninja"
        build_done "ninja" "$repo_version"
    fi

    # Build libzstd
    find_git_repo "facebook/zstd" "1" "T"
    if build "libzstd" "$repo_version"; then
        download "https://github.com/facebook/zstd/archive/refs/tags/v$repo_version.tar.gz" "libzstd-$repo_version.tar.gz"
        cd "build/meson" || fail "Failed to cd into build/meson. Line: $LINENO"
        local meson_dir="meson-build"
        rm -rf -- "$meson_dir"
        execute meson setup "$meson_dir" --prefix="$workspace" \
                                      --buildtype=release \
                                      --default-library=static \
                                      --strip \
                                      -Dbin_tests=false
        execute ninja "-j$build_threads" -C "$meson_dir"
        execute ninja -C "$meson_dir" install
        build_done "libzstd" "$repo_version"
    fi

    # Build librist
    librist_repo_version
    if build "librist" "$repo_version"; then
        download "https://code.videolan.org/rist/librist/-/archive/v$repo_version/librist-v$repo_version.tar.bz2" "librist-$repo_version.tar.bz2"
        execute meson setup build --prefix="$workspace" \
                                  --buildtype=release \
                                  --default-library=static \
                                  --strip \
                                  -Dbuilt_tools=false \
                                  -Dtest=false
        execute ninja "-j$build_threads" -C build
        execute ninja -C build install
        build_done "librist" "$repo_version"
    fi
    CONFIGURE_OPTIONS+=("--enable-librist")

	    # Build zlib
	    find_git_repo "madler/zlib" "1" "T"
	    if build "zlib" "$repo_version"; then
	        download "https://github.com/madler/zlib/releases/download/v$repo_version/zlib-$repo_version.tar.xz"
	        execute cmake -B build -DCMAKE_INSTALL_PREFIX="$workspace" -DCMAKE_BUILD_TYPE=Release \
	                      -DINSTALL_BIN_DIR="$workspace/bin" -DINSTALL_INC_DIR="$workspace/include" \
	                      -DINSTALL_LIB_DIR="$workspace/lib" -DINSTALL_MAN_DIR="$workspace/share/man" \
	                      -DINSTALL_PKGCONFIG_DIR="$workspace/share/pkgconfig" -DZLIB_BUILD_EXAMPLES=OFF \
	                      -G Ninja -Wno-dev
	        execute ninja "-j$build_threads" -C build
	        execute ninja -C build install
	        build_done "zlib" "$repo_version"
	    fi

    # Build openssl (if GPL and non-free enabled)
    if "$NONFREE_AND_GPL"; then
        get_openssl_version() {
            openssl_version=$(
                        curl -fsS https://openssl-library.org/source/ |
                        grep -oP 'openssl-\K3\.0\.[0-9]+' | sort -ruV |
                        head -n1
                    )
	        }
	        get_openssl_version
	        if build "openssl" "$openssl_version"; then
	            download "https://github.com/openssl/openssl/releases/download/openssl-$openssl_version/openssl-$openssl_version.tar.gz"
	            execute ./Configure --prefix="$workspace" \
                                        --openssldir="$workspace/ssl" \
	                                no-shared \
                                        no-pinshared \
                                        threads \
                                        zlib \
                                        --with-rand-seed=os \
	                                --with-zlib-include="$workspace/include" \
	                                --with-zlib-lib="$workspace/lib"
	            execute make "-j$build_threads"
	            execute make install_sw
	            build_done "openssl" "$openssl_version"
	        fi
	        CONFIGURE_OPTIONS+=("--enable-openssl")
	    fi
}
