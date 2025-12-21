# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FFmpeg Build Script - builds a static FFmpeg binary from source with GPL and non-free codecs. Automatically downloads and compiles all dependencies including audio/video codecs, hardware acceleration (NVIDIA CUDA, AMD AMF), and support libraries.

**Supported platforms:** Debian 11/12, Ubuntu 22.04/24.04 (x86_64 only)

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

Runs `bash -n` syntax check and `shellcheck -x` on all shell scripts.

## Architecture

### Main Entry Point
- `build-ffmpeg.sh` - Orchestrator script that sources all other scripts and drives the build

### Build Scripts (scripts/)
| File | Purpose |
|------|---------|
| `shared-utils.sh` | Common functions: logging, downloads, `build()`, `execute()`, `library_exists()` |
| `system-setup.sh` | OS detection, APT package installation |
| `hardware-detection.sh` | GPU detection (NVIDIA/AMD), CUDA installation |
| `global-tools.sh` | Build toolchain (m4, autoconf, automake, cmake, etc.) |
| `core-libraries.sh` | Core dependencies (zlib, bzip2, etc.) |
| `support-libraries.sh` | Support libraries (fontconfig, freetype, fribidi, etc.) |
| `audio-libraries.sh` | Audio codecs (libmp3lame, opus, vorbis, etc.) |
| `video-libraries.sh` | Video codecs (x264, x265, vpx, aom, svtav1, NVENC) |
| `image-libraries.sh` | Image format libraries (libjpeg, libpng, etc.) |
| `ffmpeg-build.sh` | Final FFmpeg configure and compile |

### Directory Structure During Build
- `build/` - Build root (override with `BUILD_ROOT` env var)
- `build/packages/` - Downloaded and extracted source tarballs
- `build/workspace/` - Compiled libraries (`lib/`, `include/`, `bin/`)
- `build/build.log` - Build log output

### Key Patterns

**Adding a new library:**
1. Use the `build "libname" "version"` wrapper to check if rebuild is needed
2. Use `download "url" "filename.tar.xz"` to fetch sources
3. Use `execute ./configure ...` or `execute cmake ...` for build commands
4. Use `library_exists "libname"` to conditionally enable FFmpeg flags

**GPU/CUDA detection:**
- `gpu_flag=0` means NVIDIA GPU detected (counter-intuitive but intentional)
- CUDA toolkit path exported as `cuda_path`
- `nvccflags` contains compute capability flags for the detected GPU

**Build vs installed version check:**
- The `build()` function compares installed version against requested version
- Returns success (0) if rebuild needed, failure (1) if current version exists

## Important Variables

- `$workspace` - Path to compiled output (`build/workspace`)
- `$packages` - Path to source packages (`build/packages`)
- `$NONFREE_AND_GPL` - Boolean for enabling non-free codecs
- `$LATEST` - Boolean to force building latest versions
- `$CC`, `$CXX` - Compiler (gcc/g++ or clang/clang++)

## Notes

- Script must NOT be run as root (will exit with error)
- Uses `sudo` internally for package installation and final FFmpeg install to `/usr/local`
- Hardware detection sets exports used by video-libraries.sh for NVENC support
