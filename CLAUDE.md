Last Updated: 2026-02-05

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## MANDATORY: Context7 MCP Server Usage

**THIS IS A NON-NEGOTIABLE REQUIREMENT. YOU MUST FOLLOW THESE INSTRUCTIONS.**

Before writing, modifying, or suggesting ANY code in this repository, you **MUST** use the `context7` MCP server to gather the latest best practices, documentation, and usage patterns for the relevant technologies.

### Required Actions

1. **ALWAYS** call `mcp__context7__resolve-library-id` first to resolve the correct library ID for the technology you're working with (e.g., "ffmpeg", "bash", "cmake", "autoconf", "x264", "x265", etc.)

2. **ALWAYS** call `mcp__context7__get-library-docs` with the resolved library ID to fetch current documentation and best practices

3. **NEVER** rely solely on your training data for build configurations, compiler flags, library APIs, or FFmpeg options - these change frequently

4. **NEVER** skip the context7 lookup step, even for "simple" changes

### When to Query Context7

You **MUST** query context7 when:
- Modifying any `./configure` flags or options
- Adding or updating library build procedures
- Working with FFmpeg configuration options
- Dealing with CUDA/NVENC/hardware acceleration
- Updating codec libraries (x264, x265, aom, svt-av1, etc.)
- Modifying CMake or Meson build configurations
- Working with shell scripting best practices

### Example Workflow

```
1. User asks to add a new codec library
2. YOU MUST: Call mcp__context7__resolve-library-id for that library
3. YOU MUST: Call mcp__context7__get-library-docs for current build instructions
4. THEN: Implement the changes using the retrieved best practices
```

**FAILURE TO USE CONTEXT7 WILL RESULT IN OUTDATED OR INCORRECT CODE.**

---

## Project Overview

FFmpeg Build Script (v4.3.1) - builds a static FFmpeg binary from source with GPL and non-free codecs. Automatically downloads and compiles ~60+ dependencies including audio/video codecs, hardware acceleration (NVIDIA CUDA/NVENC, AMD AMF), and support libraries.

**Supported platforms:** Debian 12/13, Ubuntu 22.04/24.04, WSL (x86_64 only)

## Build Commands

```bash
# Standard build with all codecs
bash build-ffmpeg.sh --build --enable-gpl-and-non-free --latest

# Build with specific compiler
bash build-ffmpeg.sh --build --enable-gpl-and-non-free --latest --compiler=clang

# Build with custom thread count
bash build-ffmpeg.sh --build --enable-gpl-and-non-free --latest -j 8

# Clean all build artifacts
bash build-ffmpeg.sh --cleanup
```

## Linting

```bash
bash scripts/lint.sh
```

Runs `bash -n` syntax check and `shellcheck -x` on `build-ffmpeg.sh` and all `scripts/*.sh`.

## Architecture

### Execution Order (build-ffmpeg.sh)

`build-ffmpeg.sh` is the orchestrator. It sources each script in order and calls its entry function:

1. `shared-utils.sh` (sourced first - all scripts depend on it)
2. `system-setup.sh` -> `initialize_system_setup()` (OS detection, APT packages)
3. `hardware-detection.sh` -> `initialize_hardware_detection()` + `install_cuda()`
4. `global-tools.sh` -> `install_global_tools()` (m4, autoconf, cmake, meson, nasm, etc.)
5. `core-libraries.sh` -> `install_core_libraries()` (zlib, bzip2, libxml2, libpng, etc.)
6. `support-libraries.sh` -> `install_miscellaneous_libraries()` (freetype, fontconfig, harfbuzz, etc.)
7. `audio-libraries.sh` -> `install_audio_libraries()` (lame, opus, vorbis, fdk-aac, etc.)
8. `video-libraries.sh` -> `install_video_libraries()` (x264, x265, vpx, aom, svt-av1, etc.)
9. `image-libraries.sh` -> `install_image_libraries()` (libheif, openjpeg, libjxl)
10. `ffmpeg-build.sh` -> `build_ffmpeg()` (final FFmpeg configure + compile)

Each library script appends to the `$CONFIGURE_OPTIONS` array. `ffmpeg-build.sh` consumes the final accumulated array plus its own `BASIC_CONFIG` and `OPTIONAL_LIBS` arrays, deduplicates them, and passes them to FFmpeg's `./configure`.

### Core Pattern: Library Build Lifecycle

Every library follows this pattern:
```bash
# 1. Detect latest version (sets $repo_version)
find_git_repo "owner/repo" "1" "T"
# -- or for GNU projects --
gnu_repo "https://mirrors.ibiblio.org/gnu/libname"
validate_repo_version "libname"

# 2. Check if rebuild needed (returns 0=build, 1=skip)
if build "libname" "$repo_version"; then
    # 3. Download and extract
    download "https://example.com/lib-$repo_version.tar.xz" "lib-$repo_version.tar.xz"
    # 4. Configure + compile + install to $workspace
    execute ./configure --prefix="$workspace" --disable-shared --enable-static
    execute make "-j$build_threads"
    execute make install
    # 5. Mark as built (creates .done lockfile)
    build_done "libname" "$repo_version"
fi
# 6. Append FFmpeg configure flag
CONFIGURE_OPTIONS+=("--enable-libname")
```

### Version Detection Dispatch

`find_git_repo()` in `shared-utils.sh` is a large case dispatch that routes to specialized version fetchers:
- **`github_version()`** - Unified GitHub tag scraper. Params: `"owner/repo" [prefix] [exclude_pattern] [url_type]`
- **`gitlab_version()`** - Unified GitLab tag scraper. Params: `"base_url" "project" [prefix] [separator]`
- **`gnu_repo()`** - Scrapes GNU mirror directory listings with ibiblio/team-cymru fallback
- **`fetch_repo_version()`** - JSON API-based (uses `jq`), for VideoLAN/Debian Salsa repos
- **`git_caller()`/`git_clone()`** - For repos that need actual `git clone --depth 1`

All version functions set the global `$repo_version` variable. Call `validate_repo_version "context"` after to assert it succeeded.

### Compiler Flags Management

`source_compiler_flags()` sets optimized CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS. Some libraries need custom flags:
- Call `save_compiler_flags()` before modifying
- Call `restore_compiler_flags()` after the library build completes

### Shell Conventions

- All scripts use `set -o pipefail` but intentionally **do NOT** use `set -e` or `set -u` because many build steps rely on optional probes failing without aborting
- Common shellcheck directives: `# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null`
- The `execute()` function wraps commands with logging + error handling; always use it instead of running build commands directly

### Build Scripts (scripts/)

| File | Purpose |
|------|---------|
| `shared-utils.sh` | Foundation: logging, downloads, `build()`/`build_done()`, `execute()`, `library_exists()`, all version fetchers, compiler flag management, PATH/cleanup utilities |
| `system-setup.sh` | OS detection (`$VARIABLE_OS`, `$STATIC_VER`), APT package installation |
| `hardware-detection.sh` | GPU detection (NVIDIA/AMD), CUDA toolkit installation, `nvidia_architecture()` for compute capability |
| `global-tools.sh` | Build toolchain (m4->autoconf->automake->libtool->pkgconf, cmake, meson, ninja, nasm, yasm) |
| `core-libraries.sh` | Core dependencies (zlib, bzip2, giflib, libiconv, libxml2, expat, libpng, libjpeg-turbo) |
| `support-libraries.sh` | Font/text rendering (freetype, fontconfig, fribidi, harfbuzz), conditional crypto (gmp, nettle, gnutls if not GPL) |
| `audio-libraries.sh` | Audio codecs (libsoxr, SDL2, ogg, vorbis, opus, lame, fdk-aac, flac, etc.) |
| `video-libraries.sh` | Video codecs (aom, rav1e, x264, x265, vpx, svt-av1, dav1d, xvid, kvazaar) |
| `image-libraries.sh` | Image formats (libheif, openjpeg, libjxl) |
| `ffmpeg-build.sh` | Final FFmpeg configure with `BASIC_CONFIG` + `OPTIONAL_LIBS` + `CONFIGURE_OPTIONS`, compile, install to `/usr/local` |
| `lint.sh` | `bash -n` syntax check + `shellcheck -x` on all scripts |

### Directory Structure During Build

- `build/` - Build root (override with `BUILD_ROOT` env var)
- `build/packages/` - Downloaded source tarballs + extracted source dirs
- `build/packages/<lib>.done` - Lockfiles tracking built versions (delete to force rebuild)
- `build/workspace/` - Compiled output (`lib/`, `lib64/`, `include/`, `bin/`, `share/`)
- `build/build.log` - Build log output

### GPU/CUDA Detection

- `gpu_flag=0` means NVIDIA GPU detected (counter-intuitive but intentional; `1` = no NVIDIA)
- `nvidia_architecture()` interactively prompts user to select CUDA compute capabilities
- `nvidia_arch_type` contains `-gencode arch=compute_XX,code=sm_XX` flags (used as `--nvccflags` in FFmpeg configure)
- CUDA/NVENC flags are added in `ffmpeg-build.sh`'s `build_ffmpeg()`, not in `video-libraries.sh`
- nv-codec-headers are cloned and installed inline in `build_ffmpeg()` if not already present

## Important Variables

- `$workspace` - Install prefix for compiled libraries (`build/workspace`)
- `$packages` - Source download/extract directory (`build/packages`)
- `$CONFIGURE_OPTIONS` - Array of FFmpeg `./configure` flags (accumulated by library scripts)
- `$build_threads` - Parallel make jobs (default: `nproc --all`)
- `$CC`, `$CXX` - Compiler (gcc/g++ or clang/clang++)
- `$NONFREE_AND_GPL` - Boolean string for enabling non-free codecs
- `$LATEST` - Boolean string; when true, rebuilds outdated libraries
- `$STATIC_VER` - Debian/Ubuntu version number (affects compatibility decisions)
- `$gpu_flag` - 0=NVIDIA detected, 1=no NVIDIA (set by `hardware-detection.sh`)
- `$nvidia_arch_type` - CUDA compute capability flags for `--nvccflags`
- `$VARIABLE_OS` - Detected OS string (e.g., "Ubuntu", "Debian", "WSL2")

## Notes

- Script must NOT be run as root (exits immediately with error)
- Uses `sudo` internally for APT installation and final FFmpeg install to `/usr/local`
- Download function uses atomic writes (temp file + `mv`) with `flock`-based locking for concurrent safety
- The `build()` function stores versions in `$packages/<lib>.done` lockfiles; `--latest` flag causes outdated lockfiles to trigger rebuilds
- FFmpeg `./configure` is run with `env -u threads -u THREADS` to prevent environment variable contamination that silently disables the `ffmpeg` binary build
