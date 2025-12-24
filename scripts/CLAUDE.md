Last Updated: 2025-12-24

# scripts/

Build orchestration modules for FFmpeg compilation. Each sources `shared-utils.sh` for common functions.

## Core Infrastructure

**shared-utils.sh** - Foundation: logging (`log()`, `warn()`, `fail()`), downloads (`download()`, `download_with_fallback()`), build orchestration (`build()`, `build_done()`, `execute()`), version detection (`find_git_repo()`, `gnu_repo()`), library checks (`library_exists()`). Defines `$workspace`, `$packages`, colors, GNU mirrors. All scripts depend on this.

**system-setup.sh** - OS/APT: `apt_pkgs()` installs build deps (compilers, dev libs, tools). Auto-detects latest JDK, checks availability, handles missing packages. Must run before builds.

**hardware-detection.sh** - GPU/CUDA: `check_nvidia_gpu()`, `check_amd_gpu()` detect hardware. `install_cuda_toolkit()` downloads CUDA from NVIDIA if GPU found. Exports `$gpu_flag` (0=NVIDIA, 1=AMD) and `$nvidia_arch_type` for FFmpeg `--nvccflags`.

## Build Toolchain

**global-tools.sh** - `install_global_tools()`: Builds build-system tools (m4→autoconf→automake→libtool→pkgconf, cmake, meson, ninja, nasm, yasm). Required before library builds.

**core-libraries.sh** - `install_core_libraries()`: Foundational libs (yasm, nasm, giflib, libiconv, zlib, bzip2, libxml2, expat, libpng, libjpeg-turbo). Image/text/compression basics.

**support-libraries.sh** - `install_miscellaneous_libraries()`: Font/text rendering (freetype, fontconfig, fribidi, harfbuzz), conditional crypto (gmp, nettle, gnutls if not GPL).

**audio-libraries.sh** - `install_audio_libraries()`: Audio codecs/processors (libsoxr, SDL2, libsndfile, ogg, vorbis, opus, lame, fdk-aac, flac, mpg123, etc.). Appends to `$CONFIGURE_OPTIONS`.

**video-libraries.sh** - `install_video_libraries()`: Video codecs (libaom AV1, rav1e, x264, x265, vpx, svt-av1/vp9/heif, dav1d, xvid). Builds nv-codec-headers when CUDA is present. FFmpeg NVENC flags are set in `ffmpeg-build.sh`.

**image-libraries.sh** - `install_image_libraries()`: Advanced image formats (libheif HEIF/AVIF, openjpeg JPEG2000, libjxl JPEG XL). Conditional codec detection for libheif.

## Final Build

**ffmpeg-build.sh** - `build_ffmpeg()`: Fetches FFmpeg from ffmpeg.org, runs `./configure` with `$CONFIGURE_OPTIONS` array (populated by library scripts), compiles, installs to `/usr/local`. WSL2 hardware accel support.

## Linting

**lint.sh** - Runs `bash -n` (syntax check) + `shellcheck -x` on build-ffmpeg.sh + scripts/*.sh. Called via `bash scripts/lint.sh`.

## Key Patterns

- **Build wrapper**: `build "name" "ver"` checks if rebuild needed (compares versions), returns 0=build, 1=skip
- **Downloads**: `download "url" ["output.tar.xz"]` fetches+extracts; `download_with_fallback` tries mirrors
- **Execution**: `execute <cmd>` runs with logging+error handling; fails build on error
- **Version fetch**: `find_git_repo "user/repo" "1" "T"` → `$repo_version`, `gnu_repo "url"` → `$repo_version`
- **Library check**: `library_exists "libname"` tests pkg-config; used for conditional FFmpeg flags
- **Build flow**: `if build "lib" "ver"; then download...; execute...; build_done "lib" "ver"; fi`

## Critical Variables (exported/shared)

- `$workspace` - Install prefix for compiled libs (`build/workspace`)
- `$packages` - Source download/extract dir (`build/packages`)
- `$build_threads` - Parallel make jobs
- `$CC`, `$CXX` - Compiler (gcc/clang)
- `$CONFIGURE_OPTIONS` - Array of FFmpeg `./configure` flags (appended by library scripts)
- `$gpu_flag` - 0=NVIDIA, 1=AMD (set by hardware-detection.sh)
- `$nvidia_arch_type` - CUDA compute capability flags (used for `--nvccflags`)
- `$NONFREE_AND_GPL` - Boolean for non-free codec enablement
- `$STATIC_VER` - Debian/Ubuntu version (affects compatibility)

## Execution Order (build-ffmpeg.sh)

1. shared-utils.sh (sourced by all)
2. system-setup.sh → apt_pkgs()
3. hardware-detection.sh → GPU detection
4. global-tools.sh → install_global_tools()
5. core-libraries.sh → install_core_libraries()
6. support-libraries.sh → install_miscellaneous_libraries()
7. audio-libraries.sh → install_audio_libraries()
8. video-libraries.sh → install_video_libraries()
9. image-libraries.sh → install_image_libraries()
10. ffmpeg-build.sh → build_ffmpeg()

Each appends to `$CONFIGURE_OPTIONS`; ffmpeg-build.sh consumes final array.
