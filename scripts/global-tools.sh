#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

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
    require_vars workspace packages build_threads SYSTEM_PKG_CONFIG_PATH

    # Alert the user that an AMD GPU was found without a Geforce GPU present.
    # gpu_flag=1 only means "no NVIDIA GPU" (also true on Intel-only and GPU-less
    # machines), so additionally require that an AMD GPU was actually detected.
    if [[ "${gpu_flag:-0}" -eq 1 && "${is_amd_gpu_present:-}" == "AMD GPU detected" ]]; then
        printf "\n%s\n" "An AMD GPU was detected without an NVIDIA GPU present."
    fi

    # Source the compiler flags
    source_compiler_flags

    # Build m4 from a versioned release. "m4-latest" is mutable and cannot be
    # represented truthfully by a durable build marker.
    fetch_version_if_enabled "m4" gnu_repo "$GNU_PRIMARY_MIRROR/m4/"
    local m4_version="$repo_version"
    if build "m4" "$m4_version"; then
        download_with_fallback \
            "$GNU_PRIMARY_MIRROR/m4/m4-$m4_version.tar.xz" \
            "$GNU_FALLBACK_MIRROR/m4/m4-$m4_version.tar.xz"
        execute sh configure --prefix="$workspace" --enable-threads=posix
        execute make "-j$build_threads"
        execute make install
        build_done "m4" "$m4_version"
    fi

    local m4_path
    m4_path="$(resolve_tool_path "m4" "$workspace/bin/m4")"
    if [[ "$m4_path" != "$workspace/bin/m4" ]]; then
        log "Using system 'm4' fallback: '$m4_path'."
    fi

    # Build autoconf
    fetch_version_if_enabled "autoconf" gnu_repo "$GNU_PRIMARY_MIRROR/autoconf/"
    local autoconf_version="$repo_version"
    if build "autoconf" "$autoconf_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/autoconf/autoconf-$autoconf_version.tar.xz" "$GNU_FALLBACK_MIRROR/autoconf/autoconf-$autoconf_version.tar.xz"
        execute sh configure --prefix="$workspace" M4="$m4_path"
        execute make "-j$build_threads"
        execute make install
        build_done "autoconf" "$autoconf_version"
    fi

    # Build automake
    fetch_version_if_enabled "automake" gnu_repo "$GNU_PRIMARY_MIRROR/automake/"
    local automake_version="$repo_version"
    if build "automake" "$automake_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/automake/automake-$automake_version.tar.xz" "$GNU_FALLBACK_MIRROR/automake/automake-$automake_version.tar.xz"
        execute sh configure --prefix="$workspace"
        execute make "-j$build_threads"
        execute make install
        build_done "automake" "$automake_version"
    fi

    # Build libtool
    fetch_version_if_enabled "libtool" gnu_repo "$GNU_PRIMARY_MIRROR/libtool/"
    local libtool_version="$repo_version"
    if build "libtool" "$libtool_version"; then
        download_with_fallback "$GNU_PRIMARY_MIRROR/libtool/libtool-$libtool_version.tar.xz" "$GNU_FALLBACK_MIRROR/libtool/libtool-$libtool_version.tar.xz"
        execute sh configure --prefix="$workspace" --with-pic M4="$m4_path"
        execute make "-j$build_threads"
        execute make install
        build_done "libtool" "$libtool_version"
    fi

    # Build pkgconf (modern pkgconf replacement)
    fetch_version_if_enabled "pkgconf" pkgconf_repo_version || fail "Failed to detect pkgconf version. Line: ${LINENO}"
    local pkgconf_version="$repo_version"
    if build "pkgconf" "$pkgconf_version"; then
        download "https://github.com/pkgconf/pkgconf/archive/refs/tags/pkgconf-$pkgconf_version.tar.gz" "pkgconf-$pkgconf_version.tar.gz"
        # Release tarballs from GitHub need autoreconf
        execute autoreconf -fi
        execute sh configure --prefix="$workspace" --enable-silent-rules \
            --with-pkg-config-dir="$SYSTEM_PKG_CONFIG_PATH" \
            --with-system-libdir="/lib:/lib64:/usr/lib:/usr/lib64:/usr/lib/x86_64-linux-gnu" \
            --with-system-includedir="/usr/include:/usr/include/x86_64-linux-gnu"
        execute make "-j$build_threads"
        execute make install
        # Create pkg-config symlink for compatibility
        execute ln -sf "$workspace/bin/pkgconf" "$workspace/bin/pkg-config"
        build_done "pkgconf" "$pkgconf_version"
    fi

    # Build cmake
    fetch_version_if_enabled "cmake" find_git_repo "Kitware/CMake" "1"
    if build "cmake" "$repo_version"; then
        download "https://github.com/Kitware/CMake/archive/refs/tags/v$repo_version.tar.gz" "cmake-$repo_version.tar.gz"
        # CMake bootstraps with its own bundled curl and must build as a standalone
        # host tool. A previous run may have installed a static OpenSSL (libcrypto.a,
        # built with zlib) into $workspace. While the workspace is visible, CMake's
        # bundled curl discovers that OpenSSL through pkg-config and links the static
        # libcrypto.a with the non-static flag set ("-lssl -lcrypto", no "-lz"),
        # leaving zlib symbols (inflate/deflate/...) undefined. Hide the workspace
        # from CMake's build (both pkg-config discovery and the -L link path) so it
        # falls back to the system OpenSSL, which resolves its own zlib dependency.
        local cmake_saved_pkg_config_path="${PKG_CONFIG_PATH:-}"
        save_compiler_flags
        CPPFLAGS="$(strip_workspace_entries "$CPPFLAGS")"
        LDFLAGS="$(strip_workspace_entries "$LDFLAGS")"
        PKG_CONFIG_PATH="$(strip_workspace_entries "${PKG_CONFIG_PATH:-}" ":")"
        export CPPFLAGS LDFLAGS PKG_CONFIG_PATH
        execute ./bootstrap --prefix="$workspace" --parallel="$build_threads" --enable-ccache --no-qt-gui --no-debugger
        execute make "-j$build_threads"
        execute make install
        restore_compiler_flags
        PKG_CONFIG_PATH="$cmake_saved_pkg_config_path"
        export PKG_CONFIG_PATH
        build_done "cmake" "$repo_version"
    fi

    # Build meson
    fetch_version_if_enabled "meson" find_git_repo "mesonbuild/meson" "1"
    if build "meson" "$repo_version"; then
        local meson_venv="$workspace/python_virtual_environment/build-tools"
        setup_python_venv_and_install_packages "$meson_venv" "meson==$repo_version"
        build_done "meson" "$repo_version"
    fi
    # Ensure the build-tools venv is first on PATH so `meson` is consistent across builds.
    path_prepend "$workspace/python_virtual_environment/build-tools/bin"

    # Build ninja
    fetch_version_if_enabled "ninja" find_git_repo "ninja-build/ninja" "1"
    if build "ninja" "$repo_version"; then
        download "https://github.com/ninja-build/ninja/archive/refs/tags/v$repo_version.tar.gz" "ninja-$repo_version.tar.gz"
        execute python3 configure.py --bootstrap
        execute install -Dm0755 ninja "$workspace/bin/ninja"
        build_done "ninja" "$repo_version"
    fi

    # Build libzstd
    fetch_version_if_enabled "libzstd" find_git_repo "facebook/zstd" "1"
    if build "libzstd" "$repo_version"; then
        download "https://github.com/facebook/zstd/archive/refs/tags/v$repo_version.tar.gz" "libzstd-$repo_version.tar.gz"
        cd "build/meson" || fail "Failed to cd into 'build/meson'. Line: $LINENO"
        local meson_dir="meson-build"
        safe_remove_tree "$PWD/$meson_dir" "$PWD"
        meson_ninja_install "$meson_dir" \
            --buildtype=release \
            --default-library=static \
            --strip \
            -Dbin_contrib=false \
            -Dbin_programs=false \
            -Dbin_tests=false
        build_done "libzstd" "$repo_version"
    fi

    # Build librist
    fetch_version_if_enabled "librist" librist_repo_version
    if build "librist" "$repo_version"; then
        download "https://code.videolan.org/rist/librist/-/archive/v$repo_version/librist-v$repo_version.tar.bz2" "librist-$repo_version.tar.bz2"
        meson_ninja_install "build" \
            --buildtype=release \
            --default-library=static \
            --strip \
            -Dbuilt_tools=false \
            -Dtest=false
        build_done "librist" "$repo_version"
    fi
    append_configure_options_if_enabled "librist" "--enable-librist"

    # Build zlib
    fetch_version_if_enabled "zlib" find_git_repo "madler/zlib" "1"
    if build "zlib" "$repo_version"; then
        download "https://github.com/madler/zlib/releases/download/v$repo_version/zlib-$repo_version.tar.xz"
        # zlib 1.3.x's CMake build always creates both explicit shared and
        # static targets. Its documented --static configure path builds only
        # the archive this workspace consumes.
        execute sh configure --prefix="$workspace" --static
        execute make "-j$build_threads"
        execute make install
        build_done "zlib" "$repo_version"
    fi

    # Build openssl (if GPL and non-free enabled)
    if is_true "$NONFREE_AND_GPL"; then
        fetch_version_if_enabled "openssl" openssl_lts_version ||
            fail "Failed to detect the latest OpenSSL 3.5 LTS release. Line: ${LINENO}"
        local openssl_version="$repo_version"
        if build "openssl" "$openssl_version"; then
            local zlib_include_dir zlib_library_dir
            zlib_include_dir="$(resolve_workspace_or_pkgconf_include_dir "zlib" "zlib" "$workspace/lib/libz.a" "$workspace/lib/libz.so")"
            zlib_library_dir="$(resolve_workspace_or_pkgconf_library_dir "zlib" "zlib" "$workspace/lib/libz.a" "$workspace/lib/libz.so")"
            download "https://github.com/openssl/openssl/releases/download/openssl-$openssl_version/openssl-$openssl_version.tar.gz"
            execute ./Configure --prefix="$workspace" \
                                        --openssldir="$workspace/ssl" \
                                        no-shared \
                                        no-pinshared \
                                        no-apps \
                                        no-docs \
                                        no-tests \
                                        threads \
                                        zlib \
                                        --with-rand-seed=os \
                                        --with-zlib-include="$zlib_include_dir" \
                                        --with-zlib-lib="$zlib_library_dir"
            execute make "-j$build_threads"
            execute make install_sw
            build_done "openssl" "$openssl_version"
        fi
        append_configure_options_if_enabled "openssl" "--enable-openssl"
    fi
}
