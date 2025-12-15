# FFmpeg Build Script - Missing NVENC/CUDA Support Analysis

## Summary

The FFmpeg build at `/usr/local/bin/ffmpeg` was missing NVIDIA hardware acceleration (NVENC/CUDA) despite having:
- NVIDIA GPU detected (RTX 3090 Ti / RTX 4090)
- CUDA Toolkit installed (version 13.1)

## Status: FIXED

The following files have been updated to enable CUDA/NVENC support:
- `scripts/ffmpeg-build.sh` - Added CUDA/NVENC configure flags and paths
- `scripts/hardware-detection.sh` - Added `nvidia_architecture()` call to detect GPU architecture

## Root Cause (Original Issue)

The `scripts/ffmpeg-build.sh` file **never added CUDA/NVENC configure flags** to the FFmpeg build, even though `scripts/hardware-detection.sh` correctly detected the NVIDIA GPU and CUDA installation.

---

## File Analysis

### `scripts/hardware-detection.sh`
**Status:** Working correctly

- Detects NVIDIA GPU via `nvidia-smi`
- Detects CUDA installation via `version.json`
- Sets `gpu_flag=0` when NVIDIA GPU is found
- Sets `nvidia_arch_type` with compute capability
- **Problem:** These variables are never used in `ffmpeg-build.sh`

### `scripts/ffmpeg-build.sh`
**Status:** Missing CUDA/NVENC configuration

The `BASIC_CONFIG` array (lines 69-91) contains NO CUDA options:

```bash
BASIC_CONFIG=(
    --prefix=/usr/local
    --arch="$(uname -m)"
    # ... other options ...
    --enable-vdpau      # <-- Only VDPAU is enabled
    --enable-zlib
    # MISSING: --enable-cuda
    # MISSING: --enable-cuda-nvcc
    # MISSING: --enable-cuvid
    # MISSING: --enable-nvenc
    # MISSING: --enable-nvdec
    # MISSING: --enable-ffnvcodec
)
```

The `OPTIONAL_LIBS` array (lines 94-108) only checks for software libraries:

```bash
OPTIONAL_LIBS=()
[[ -f "$workspace/lib/libx264.a" ]] && OPTIONAL_LIBS+=(--enable-libx264)
[[ -f "$workspace/lib/libx265.a" ]] && OPTIONAL_LIBS+=(--enable-libx265)
# ... etc ...
# MISSING: Any CUDA/NVENC checks
```

The `--extra-cflags` and `--extra-ldflags` (lines 87-88) don't include CUDA paths:

```bash
--extra-cflags="-I$workspace/include"
# MISSING: -I/usr/local/cuda/include

--extra-ldflags="-L$workspace/lib64 -L$workspace/lib ..."
# MISSING: -L/usr/local/cuda/lib64
```

---

## Missing Configure Flags

The following flags need to be added to enable NVIDIA hardware acceleration:

| Flag | Purpose |
|------|---------|
| `--enable-cuda` | Enable CUDA support |
| `--enable-cuda-nvcc` | Enable CUDA compilation with nvcc |
| `--enable-cuvid` | Enable CUVID hardware decoding (h264_cuvid, hevc_cuvid) |
| `--enable-nvenc` | Enable NVENC hardware encoding (h264_nvenc, hevc_nvenc) |
| `--enable-nvdec` | Enable NVDEC hardware decoding |
| `--enable-ffnvcodec` | Enable FFmpeg NVIDIA codec headers |
| `--enable-libnpp` | (Optional) NVIDIA Performance Primitives for scale_npp |

---

## Missing Compiler/Linker Flags

```bash
--extra-cflags="-I/usr/local/cuda/include"
--extra-ldflags="-L/usr/local/cuda/lib64"
--nvccflags="-gencode arch=compute_86,code=sm_86"  # For RTX 3090
```

---

## Applied Fix

The following changes were made to `scripts/ffmpeg-build.sh` after the `OPTIONAL_LIBS` section:

```bash
# ═══════════════════════════════════════════════════════════════════════════
# CUDA/NVENC Hardware Acceleration Support
# ═══════════════════════════════════════════════════════════════════════════
# Add CUDA/NVENC support if NVIDIA GPU detected and CUDA installed
if [[ "${gpu_flag:-1}" -eq 0 ]] && [[ -d "/usr/local/cuda" ]]; then
    log "Enabling CUDA/NVENC hardware acceleration..."

    # Verify nv-codec-headers are installed (required for FFmpeg NVENC)
    if ! pkg-config --exists ffnvcodec 2>/dev/null; then
        log "Installing nv-codec-headers (required for NVENC)..."
        local nvcodec_dir="$packages/nv-codec-headers"
        if [[ ! -d "$nvcodec_dir" ]]; then
            git clone --depth 1 https://github.com/FFmpeg/nv-codec-headers.git "$nvcodec_dir"
        fi
        cd "$nvcodec_dir" || fail "Failed to cd into nv-codec-headers directory. Line: $LINENO"
        sudo make install PREFIX=/usr/local
        cd "$cwd/packages/ffmpeg-n${repo_version}" || fail "Failed to return to FFmpeg directory. Line: $LINENO"
        log "nv-codec-headers installed successfully"
    else
        log "nv-codec-headers already installed"
    fi

    # Enable CUDA-related FFmpeg features
    OPTIONAL_LIBS+=(
        --enable-cuda
        --enable-cuda-nvcc
        --enable-cuvid
        --enable-nvenc
        --enable-nvdec
        --enable-ffnvcodec
    )

    # Check for libnpp (NVIDIA Performance Primitives) for scale_npp filter
    if [[ -f "/usr/local/cuda/lib64/libnppc.so" ]] || [[ -f "/usr/local/cuda/lib64/libnppc_static.a" ]]; then
        OPTIONAL_LIBS+=(--enable-libnpp)
        log "NVIDIA Performance Primitives (libnpp) enabled"
    fi

    # Add CUDA paths to compiler/linker flags
    local cuda_cflags="-I/usr/local/cuda/include"
    local cuda_ldflags="-L/usr/local/cuda/lib64"

    # Update BASIC_CONFIG with CUDA paths (append to existing flags)
    for i in "${!BASIC_CONFIG[@]}"; do
        if [[ "${BASIC_CONFIG[$i]}" == --extra-cflags=* ]]; then
            BASIC_CONFIG[$i]="${BASIC_CONFIG[$i]} $cuda_cflags"
        elif [[ "${BASIC_CONFIG[$i]}" == --extra-ldflags=* ]]; then
            BASIC_CONFIG[$i]="${BASIC_CONFIG[$i]} $cuda_ldflags"
        fi
    done

    # Add nvcc flags if GPU architecture was detected
    if [[ -n "${nvidia_arch_type:-}" ]]; then
        BASIC_CONFIG+=("--nvccflags=$nvidia_arch_type")
        log "NVCC architecture flags: $nvidia_arch_type"
    fi

    log "CUDA/NVENC support enabled successfully"
elif [[ "${gpu_flag:-1}" -eq 0 ]] && [[ ! -d "/usr/local/cuda" ]]; then
    warn "NVIDIA GPU detected but CUDA not found at /usr/local/cuda - NVENC disabled"
fi
```

Additionally, `scripts/hardware-detection.sh` was updated to call `nvidia_architecture()` during initialization to properly set the `nvidia_arch_type` variable.

---

## Prerequisites

Before rebuilding, ensure these are installed:

1. **CUDA Toolkit** (already installed: 13.1)
   ```bash
   ls /usr/local/cuda/include/cuda.h
   ```

2. **nv-codec-headers** (FFmpeg NVIDIA codec headers)
   ```bash
   git clone https://github.com/FFmpeg/nv-codec-headers.git
   cd nv-codec-headers
   sudo make install
   ```

3. **NVIDIA Driver** (already installed: 590.44.01)
   ```bash
   nvidia-smi
   ```

---

## Verification After Rebuild

After rebuilding FFmpeg with the fix, verify NVENC support:

```bash
/usr/local/bin/ffmpeg -encoders 2>/dev/null | grep nvenc
# Should show: h264_nvenc, hevc_nvenc, av1_nvenc

/usr/local/bin/ffmpeg -decoders 2>/dev/null | grep cuvid
# Should show: h264_cuvid, hevc_cuvid, etc.

/usr/local/bin/ffmpeg -hwaccels 2>/dev/null
# Should include: cuda
```

---

## Build Configuration Comparison

| Feature | Before Fix | After Fix |
|---------|------------|-----------|
| `--enable-cuda` | NO | YES |
| `--enable-cuda-nvcc` | NO | YES |
| `--enable-cuvid` | NO | YES |
| `--enable-nvenc` | NO | YES |
| `--enable-nvdec` | NO | YES |
| `--enable-ffnvcodec` | NO | YES |
| `--enable-libnpp` | NO | YES (if available) |
| `--enable-vdpau` | YES | YES |
| `--enable-vaapi` | YES | YES |
| CUDA include path | NO | YES |
| CUDA lib64 path | NO | YES |
| nvccflags | NO | YES (auto-detected) |

## Next Steps

To rebuild FFmpeg with NVENC support:

```bash
cd /home/jman/tmp/ffmpeg-build-script
./build-ffmpeg.sh --build -n
```

The script will now automatically:
1. Detect your NVIDIA GPU
2. Prompt for CUDA architecture selection
3. Install nv-codec-headers if needed
4. Configure FFmpeg with CUDA/NVENC flags
5. Build FFmpeg with full hardware acceleration support

---

## Report Generated
- Date: 2025-12-15
- System: Ubuntu with CUDA 13.1, NVIDIA Driver 590.44.01
- GPUs: RTX 4090, RTX 3090
