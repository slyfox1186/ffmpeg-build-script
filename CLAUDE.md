Last Updated: 2025-12-24

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

FFmpeg Build Script - builds a static FFmpeg binary from source with GPL and non-free codecs. Automatically downloads and compiles all dependencies including audio/video codecs, hardware acceleration (NVIDIA CUDA, AMD AMF), and support libraries.

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
- CUDA toolkit path is added to `PATH` in `source_path`
- `nvidia_arch_type` contains compute capability flags for the detected GPU (used as `--nvccflags`)

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
