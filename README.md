# FFmpeg Build Script

A safety-focused, state-pinned FFmpeg source build for modern Debian and Ubuntu
systems. It builds a broad multimedia dependency stack into an isolated
workspace, configures FFmpeg from the latest stable release, installs FFmpeg
under `/usr/local`, and validates the installed binaries before marking the
build complete.

The project favors static dependency archives, but the final binary can still
link dynamically to selected operating-system libraries and GPU runtimes.

## Supported hosts

- x86_64
- Debian 12 and 13
- Ubuntu 22.04, 24.04, and 26.04
- Ubuntu-based Linux Mint and Zorin releases whose base maps to one of the
  supported Ubuntu versions
- WSL2 using a supported Ubuntu userspace

Run the script as a normal user with working `sudo` access. Do not run the
entire script as root.

## Quick start

```bash
git clone https://github.com/slyfox1186/ffmpeg-build-script.git
cd ffmpeg-build-script

# Review the package policy first.
cp example.toml local.toml

# Default LGPL-compatible build.
bash build-ffmpeg.sh --build --config ./local.toml

# Or explicitly opt into GPL and non-free components.
bash build-ffmpeg.sh --build \
  --enable-gpl-and-non-free \
  --config ./local.toml
```

The first build can take a long time and use substantial CPU, memory, and disk
space. Restrict parallelism on smaller machines:

```bash
bash build-ffmpeg.sh --build --jobs 8 --config ./local.toml
```

## Command-line interface

```text
Actions:
  -b, --build
  -c, --cleanup

Options:
  -h, --help
  -v, --version
      --compiler <gcc|clang>
      --config <path>
  -j, --jobs <positive integer>
  -l, --latest
  -n, --enable-gpl-and-non-free
  -g, --google-speech
```

`--help` and `--version` are side-effect free: they do not create a build
directory, truncate a log, request sudo, or load a config file.

With no action, the script prints help. `--build` and `--cleanup` are mutually
exclusive.

## Build state and version policy

The default build root is `./build`:

```text
build/
├── .ffmpeg-build-context
├── .ffmpeg-build-root
├── build.log
├── packages/
│   ├── <downloaded archives>
│   ├── <archive>.sha256
│   ├── <extracted sources>
│   └── <package>.done
└── workspace/
    ├── bin/
    ├── include/
    ├── lib/
    └── share/
```

Each successful component writes an atomic `.done` marker containing the exact
release version or Git commit used. A normal rerun reuses those versions and
does not contact every upstream service. `--latest` refreshes upstream versions
and rebuilds components whose recorded version changed.

Use a separate root when desired:

```bash
BUILD_ROOT=/mnt/fast-disk/ffmpeg-build \
  bash build-ffmpeg.sh --build --config ./local.toml
```

A custom, non-empty directory must already contain this project's
`.ffmpeg-build-root` marker. This prevents a typo from turning an unrelated
directory into a cleanup target.

## Package configuration

The config parser intentionally supports a small TOML subset:

```toml
[build]
latest = false
enable_gpl_and_non_free = false

[packages]
libopus = true
x264 = false
ffmpeg = true
```

Only `[build]` and `[packages]` are accepted, values must be literal `true` or
`false`, duplicate keys are rejected, and unknown package names are fatal.
With a config file, omitted package keys are disabled; the file is an explicit
allowlist. CLI opt-ins such as `--latest` and `--enable-gpl-and-non-free` take
precedence over a corresponding `false` build setting.
The licensing switch authorizes those components; it does not override
`[packages]` entries that remain `false`.

Start from [example.toml](./example.toml), which lists every supported package
key. When changing package choices for an existing workspace, clean first so
stale artifacts cannot satisfy a different dependency policy:

```bash
bash build-ffmpeg.sh --cleanup
```

Cleanup is interactive and removes only the validated build root. In a
non-interactive context it leaves files in place.

## CUDA and hardware acceleration

GPU discovery is advisory for compile-time feature selection. The script:

- detects NVIDIA, AMD, and Intel display controllers;
- enables VA-API, VDPAU, oneVPL, Vulkan, and related integrations only when
  their headers/libraries pass feature probes;
- never installs or replaces a display driver;
- never downloads Windows SDK headers into a Linux build;
- never guesses CUDA architecture support from a hard-coded GPU table.

If an NVIDIA GPU is present but `nvcc` is absent, the default behavior is to
ask before installing the CUDA toolkit from NVIDIA's signed APT repository.
Control that explicitly:

```bash
# Never modify CUDA packages.
CUDA_INSTALL=never bash build-ffmpeg.sh --build --config ./local.toml

# Install the toolkit non-interactively if missing (still does not install a driver).
CUDA_INSTALL=always bash build-ffmpeg.sh --build \
  --enable-gpl-and-non-free \
  --config ./local.toml
```

CUDA code targets come directly from `nvcc --list-gpu-code`, while native GPU
capabilities come from `nvidia-smi`.

```bash
# Default: all GPUs installed in this host, plus PTX for the highest target.
CUDA_ARCH_MODE=native bash build-ffmpeg.sh --build ...

# Every architecture supported by the installed toolkit.
CUDA_ARCH_MODE=all bash build-ffmpeg.sh --build ...

# An explicit, validated list.
CUDA_ARCH_MODE=custom CUDA_ARCHITECTURES="86 89" \
  bash build-ffmpeg.sh --build ...
```

CUDA/NVENC integration also requires
`--enable-gpl-and-non-free` and `nv-codec-headers = true`.
NVENC/NVDEC can use those headers without a CUDA toolkit; `nvcc` is required
only for CUDA-compiled filters.

## Safety model

The build performs unavoidable system changes only in narrowly defined places:

- APT installs missing host development packages.
- An opted-in CUDA setup installs NVIDIA's repository keyring and the
  `cuda-toolkit` package, not a display driver.
- FFmpeg's final `make install` writes under `/usr/local`.

All third-party archives must use HTTPS, pass a tar listing check, contain one
top-level source tree, and extract into a temporary directory before being
published. Concurrent downloads use a directory-level advisory lock and atomic
cache writes. A locally recorded SHA-256 detects cache damage or tampering
between runs; it is not a substitute for an upstream signature. Git snapshot
builds are cloned transactionally and recorded by commit.

The project does **not** copy workspace libraries over distribution libraries,
replace `libstdc++`, delete a system Rust compiler, wipe Cargo caches, or append
ad hoc linker paths under `/etc`.

## Validation

Static checks and regression tests:

```bash
python3 run_linter.py
bash tests/test-scripts.sh
```

The linter requires ShellCheck and validates every tracked shell script with
both `bash -n` and ShellCheck. The regression suite covers side-effect-free CLI
metadata, strict config parsing, bounded deletion, safe transactional archive
extraction, and atomic build markers.

After the full build, the script itself verifies:

- `ffmpeg` and `ffprobe` exist under `/usr/local/bin`;
- their reported release matches the selected release;
- FFmpeg reports non-empty encoder and decoder registries;
- every automatically requested external FFmpeg integration remained enabled
  after configure;
- requested `ffmpeg`, `ffprobe`, and (when SDL2 is available) `ffplay` targets
  remained enabled;
- a complete staged install passes those checks before `/usr/local` is changed.

Useful manual checks:

```bash
/usr/local/bin/ffmpeg -version
/usr/local/bin/ffmpeg -buildconf
/usr/local/bin/ffmpeg -hide_banner -encoders
/usr/local/bin/ffmpeg -hide_banner -decoders
/usr/local/bin/ffmpeg -hide_banner -filters
/usr/local/bin/ffmpeg -hide_banner -hwaccels
```

## Upstream design references

The implementation follows the interfaces and safety controls documented by
the projects it invokes:

- [FFmpeg 8.1.2 configure options and dependency checks](https://github.com/FFmpeg/FFmpeg/blob/n8.1.2/configure)
- [CMake package-registry controls](https://cmake.org/cmake/help/latest/manual/cmake-packages.7.html#package-registry)
- [Meson subproject and wrap-mode controls](https://mesonbuild.com/Subprojects.html#command-line-options)
- [GNU tar security guidance](https://www.gnu.org/software/tar/manual/html_node/Security.html)
- [NVIDIA's FFmpeg/CUDA integration guidance](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/ffmpeg-with-nvidia-gpu/index.html)
- [pip repeatable-install guidance](https://pip.pypa.io/en/stable/topics/repeatable-installs/)

## Troubleshooting

The quiet build log is at `build/build.log`. On command failure, the script
prints the output generated by that command before exiting. Stream all command
output while retaining the log with:

```bash
FFMPEG_BUILD_DEBUG=ON bash build-ffmpeg.sh --build --config ./local.toml
```

Common recovery actions:

```bash
# Retry only one component.
rm -f build/packages/<package>.done
bash build-ffmpeg.sh --build --config ./local.toml

# Re-evaluate all upstream versions.
bash build-ffmpeg.sh --build --latest --config ./local.toml

# Start with an entirely clean workspace.
bash build-ffmpeg.sh --cleanup
```

Do not remove a `.done` marker unless you intend to rebuild that component.
When reporting a failure, include the failing command, its emitted output, the
host release, compiler choice, and relevant config entries.

## Licensing

FFmpeg and its optional dependencies have different license terms. The default
configuration avoids the explicit GPL/non-free switch. Enabling
`--enable-gpl-and-non-free` changes the resulting binary's redistribution
constraints. Review FFmpeg's licensing guidance and each enabled dependency
before distributing a build.
