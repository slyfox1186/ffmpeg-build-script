# FFmpeg Build Script

[![Star](https://img.shields.io/github/stars/slyfox1186/ffmpeg-build-script?style=social)](https://github.com/slyfox1186/ffmpeg-build-script)

This repository provides a **streamlined script** to build a static FFmpeg binary with both non-free and GPL codecs. The script simplifies the process by automatically downloading the latest version of each required repository.

## Key Features

- **Builds FFmpeg** with a wide range of **essential codecs and libraries**
- Supports **hardware acceleration** using **Nvidia CUDA** and **AMD AMF**
- Designed for **easy installation** on ***supported*** operating systems

## Recent Changes

- **Debian 13 (Trixie) Support**: Added support for the latest Debian testing/unstable release
- **CUDA/NVENC Fixes**: Fixed GPU detection and NVENC support for hardware-accelerated encoding
- **pkgconf**: Replaced legacy pkg-config with modern pkgconf from GitHub
- **Build Chain Updates**: Added automake to the build toolchain for improved autotools support
- **Improved Version Detection**: Enhanced reliability of upstream version detection with fallbacks

## Supported Operating Systems

| Distribution | Versions                 | Codenames                                        |
|--------------|--------------------------|--------------------------------------------------|
| **Debian**   | 11                       | Bullseye                                         |
|              | 12                       | Bookworm                                         |
|              | 13                       | Trixie                                           |
| **Ubuntu**   | 22.04                    | Jammy Jellyfish                                  |
|              | 24.04                    | Noble Numbat                                     |

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/slyfox1186/ffmpeg-build-script.git
   cd ffmpeg-build-script
   ```

2. Run the build script:
   ```bash
   bash build-ffmpeg.sh --build --enable-gpl-and-non-free --latest
   ```

## Supported Codecs and Libraries

| Library / Codec | Description |
|-----------------|-------------|
| **alsa** | Advanced Linux Sound Architecture (ALSA) project |
| **aom** | AV1 Video Codec (Experimental and very slow!) |
| **avisynth** | A powerful tool for video post-production |
| **bzlib** | A general-purpose data compression library |
| **chromaprint** | Audio fingerprinting library |
| **cuda** | Hardware acceleration for Nvidia graphics cards |
| **dav1d** | Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities |
| **ff-nvcodec-headers** | Headers for Nvidia codec APIs (Hardware Acceleration) |
| **flac** | Free Lossless Audio Codec |
| **fontconfig** | Font configuration and customization library |
| **freetype** | A freely available software library to render fonts |
| **frei0r** | A collection of free and open-source video effects plugins |
| **fribidi** | The Free Implementation of the Unicode Bidirectional Algorithm |
| **harfbuzz** | Text shaping image processor |
| **iconv** | Used for converting text between encodings |
| **jxl** | JPEG XL, a better image quality and compression ratio compared to legacy JPEG |
| **kvazaar** | An open-source HEVC encoder |
| **ladspa** | Linux Audio Developer's Simple Plugin API |
| **lcms2** | A free, open-source, CMM engine for fast color transforms |
| **libaribb24** | A library for ARIB STD-B24, decoding JIS 8 bit characters and parsing MPEG-TS stream |
| **libass** | A portable subtitle renderer for the ASS/SSA subtitle format |
| **libbluray** | An open-source library for Blu-Ray Discs playback |
| **libbs2b** | Designed to improve headphone listening of stereo audio records |
| **libcaca** | A graphics library that outputs text instead of pixels |
| **libcdio** | A library for CD-ROM and CD image access |
| **libfdk_aac** | Fraunhofer FDK AAC Codec |
| **libflite** | Provides a high-level text-to-speech interface for English |
| **libgme** | A collection of video game music file emulators |
| **libmodplug** | A library for playing tracker music |
| **libmp3lame** | MPEG-1 or MPEG-2 Audio Layer III |
| **libmysofa** | A library to read AES SOFA files containing HRTFs |
| **libopencore_amr** | OpenCORE Adaptive Multi-Rate (AMR) speech codec library |
| **libopenmpt** | A library to render tracker music |
| **libopus** | Lossy audio coding format |
| **libpulse** | A featureful, general-purpose sound server |
| **librubberband** | An audio time-stretching and pitch-shifting library |
| **libshine** | Fixed-point MP3 encoder |
| **libsmbclient** | A library for manipulating CIFS/SMB network resources |
| **libsnappy** | Snappy compression/decompression library |
| **libsoxr** | The SoX Resampler library for sample-rate conversion |
| **libspeex** | Open Source/Free Software patent-free audio compression format |
| **libssh** | Multiplatform C library implementing the SSHv2 protocol |
| **libtesseract** | OCR engine and command-line program |
| **libtiff** | Support for the Tag Image File Format (TIFF) |
| **libtwolame** | Optimized MPEG Audio Layer 2 (MP2) encoder |
| **libv4l2** | A collection of libraries for video4linux2 devices |
| **libvo_amrwbenc** | Adaptive Multi-Rate Wideband (AMR-WB) audio codec encoder |
| **libvpx** | VP8 / VP9 Video Codec for the WebM video file format |
| **libwebp** | Image format for both lossless and lossy compression |
| **libx264** | H.264 Video Codec (MPEG-4 AVC) |
| **libx265** | H.265 Video Codec (HEVC) |
| **libxcb** | A C language interface to the X Window System protocol |
| **libxvid** | Xvid MPEG-4 Part 2 encoder wrapper |
| **libzimg** | The "z" library for image processing basics |
| **lv2** | An extensible open standard for audio plugins |
| **lzma** | An algorithm for lossless data compression |
| **mediainfo** | Unified display of technical and tag data for video and audio files |
| **mp4box/gpac** | Multimedia framework for packaging, streaming, and playback |
| **ogg** | Free, open container format |
| **opencl** | Open-source project for rendering 2D and 3D vector graphics |
| **opencore-amr** | Adaptive Multi-Rate (AMR) speech codec library implementation |
| **opengl** | Cross-language, cross-platform API for rendering 2D and 3D vector graphics |
| **openjpeg** | Open-source JPEG 2000 codec |
| **openssl** | Secure communications library |
| **rav1e** | Rust-based AV1 encoder |
| **sdl2** | Cross-platform development library for low-level access to hardware |
| **sndio** | Small audio and MIDI framework from the OpenBSD project |
| **srt** | Secure Reliable Transport (SRT) protocol for low-latency live streaming |
| **svtav1** | SVT-AV1 Encoder and Decoder |
| **theora** | Free lossy video compression format |
| **vapoursynth** | Application for video manipulation |
| **vidstab** | Video stabilization library |
| **vorbis** | Lossy audio compression format |
| **vpx** | VP8 / VP9 Video Codec for the WebM video file format |
| **webp** | Image format for both lossless and lossy compression |
| **x264** | H.264 Video Codec (MPEG-4 AVC) |
| **x265** | H.265 Video Codec (HEVC) |
| **xcb** | C language interface to the X Window System protocol |
| **xlib** | C subroutine library for interfacing with the X Window System |
| **xml2** | XML parser and toolkit |
| **xvidcore** | MPEG-4 video coding standard |
| **zlib** | General-purpose data compression library |

For a complete list of supported codecs and libraries, please refer to the [FFmpeg Legal Documents](https://ffmpeg.org/legal.html).

## Hardware Acceleration

The script provides options for hardware acceleration using Nvidia's CUDA SDK Toolkit or AMD's AMF.

### NVIDIA CUDA / NVENC

- **Automatic GPU Detection**: The script automatically detects NVIDIA GPUs and their compute capabilities
- **CUDA Toolkit**: If CUDA is not installed, the script will prompt to install the latest CUDA toolkit
- **NVENC Support**: Hardware-accelerated H.264/H.265 encoding via NVENC
- **Optimized Builds**: FFmpeg is compiled with architecture-specific CUDA optimizations for your GPU
- [CUDA SDK Toolkit Download](https://developer.nvidia.com/cuda-downloads)

### AMD AMF

- **AMF Support**: Hardware-accelerated encoding on AMD GPUs
- Requires AMD GPU drivers with AMF support

## Disclaimer

This script downloads packages under various licenses from different sources, which might track your usage. Please be aware that some of these sources are beyond our control. By using this script, you acknowledge that it allows the creation of a non-free binary and assume all associated risks.

## License

This project is licensed under the [MIT License](https://github.com/slyfox1186/ffmpeg-build-script/blob/main/LICENSE).

## Support

This is a community-supported project, and support is limited to Debian-based operating systems. For any questions or issues, please open an issue on the [GitHub repository](https://github.com/slyfox1186/ffmpeg-build-script/issues).

## Requirements

The script is designed to handle all necessary package downloads automatically with minimal user input required. Please ensure your system meets the supported operating systems criteria for a smooth installation process.

Example Output
-------

```bash
 ------------------------------
|                              |
| FFmpeg Build Script - v3.6.2 |
|                              |
 ------------------------------

[INFO] Utilizing 32 CPU threads

[WARNING] With GPL and non-free codecs enabled

Installing the required APT packages
========================================================
[INFO] Checking installation status of each package...
[INFO] Checking package installation status...

[WARNING] Unavailable packages:
          cargo-c
          libjxl-dev
[INFO] No missing packages to install or all missing packages are unavailable.

[INFO] Checking GPU Status
========================================================
[INFO] Nvidia GPU detected
[INFO] Determining if CUDA is installed...
[INFO] CUDA is already installed and up to date.

 -------------------------
|                         |
| Installing Global Tools |
|                         |
 -------------------------

Building m4 - version latest
========================================================
Downloading "https://mirrors.ibiblio.org/gnu/m4/m4-latest.tar.xz" saving as "m4-latest.tar.xz"
Download Completed
File extracted: m4-latest.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-nls --enable-c++ --enable-threads=posix
$ make -j32
$ make install

Building autoconf - version 2.71
========================================================
Downloading "https://mirrors.ibiblio.org/gnu/autoconf/autoconf-2.71.tar.xz" saving as "autoconf-2.71.tar.xz"
Download Completed
File extracted: autoconf-2.71.tar.xz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building automake - version 1.17
========================================================
Downloading "https://mirrors.ibiblio.org/gnu/automake/automake-1.17.tar.xz" saving as "automake-1.17.tar.xz"
Download Completed
File extracted: automake-1.17.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

Building libtool - version 2.5.4
========================================================
Downloading "https://mirrors.ibiblio.org/gnu/libtool/libtool-2.5.4.tar.xz" saving as "libtool-2.5.4.tar.xz"
Download Completed
File extracted: libtool-2.5.4.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pic M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building pkgconf - version 2.5.1
========================================================
Downloading "https://github.com/pkgconf/pkgconf/archive/refs/tags/pkgconf-2.5.1.tar.gz" saving as "pkgconf-2.5.1.tar.gz"
Download Completed
File extracted: pkgconf-2.5.1.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-silent-rules
$ make -j32
$ make install

Building meson - version 1.4.0
========================================================
Downloading "https://github.com/mesonbuild/meson/archive/refs/tags/1.4.0.tar.gz" saving as "meson-1.4.0.tar.gz"
Download Completed
File extracted: meson-1.4.0.tar.gz

$ python3 setup.py build
$ python3 setup.py install --prefix=/home/jman/tmp/ffmpeg-build-script/workspace

Building libzstd - version 1.5.6
========================================================
Downloading "https://github.com/facebook/zstd/archive/refs/tags/v1.5.6.tar.gz" saving as "libzstd-1.5.6.tar.gz"
Download Completed
File extracted: libzstd-1.5.6.tar.gz

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=both --strip -Dbin_tests=false
$ ninja -j32 -C build
$ ninja -C build install

Building librist - version 0.2.10
========================================================
Downloading "https://code.videolan.org/rist/librist/-/archive/v0.2.10/librist-v0.2.10.tar.bz2" saving as "librist-0.2.10.tar.bz2"
Download Completed
File extracted: librist-0.2.10.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbuilt_tools=false -Dtest=false
$ ninja -j32 -C build
$ ninja -C build install

Building zlib - version 1.3.1
========================================================
Downloading "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz" saving as "zlib-1.3.1.tar.gz"
Download Completed
File extracted: zlib-1.3.1.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

Building openssl - version 3.1.5
========================================================
Downloading "https://www.openssl.org/source/openssl-3.1.5.tar.gz" saving as "openssl-3.1.5.tar.gz"
Download Completed
File extracted: openssl-3.1.5.tar.gz

$ ./Configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace enable-egd enable-fips enable-md2 enable-rc5 enable-trace threads zlib --with-rand-seed=os --with-zlib-include=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-zlib-lib=/home/jman/tmp/ffmpeg-build-script/workspace/lib
$ make -j32
$ make install_sw install_fips

Building cmake - version 3.29.2
========================================================
Downloading "https://github.com/Kitware/CMake/archive/refs/tags/v3.29.2.tar.gz" saving as "cmake-3.29.2.tar.gz"
Download Completed
File extracted: cmake-3.29.2.tar.gz

$ ./bootstrap --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --parallel=32 --enable-ccache
$ make -j32
$ make install

Building yasm - version 1.3.0
========================================================
Downloading "https://github.com/yasm/yasm/archive/refs/tags/v1.3.0.tar.gz" saving as "yasm-1.3.0.tar.gz"
Download Completed
File extracted: yasm-1.3.0.tar.gz

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DYASM_BUILD_TESTS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building nasm - version 2.16.03
========================================================
2.16.03
Downloading "https://www.nasm.us/pub/nasm/stable/nasm-2.16.03.tar.xz" saving as "nasm-2.16.03.tar.xz"
Download Completed
File extracted: nasm-2.16.03.tar.xz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-pedantic --enable-ccache
$ make -j32
$ make install

Building giflib - version 5.2.1
========================================================
Downloading "https://cfhcable.dl.sourceforge.net/project/giflib/giflib-5.2.1.tar.gz" saving as "giflib-5.2.1.tar.gz"
Download Completed
File extracted: giflib-5.2.1.tar.gz

$ make
$ make PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install

Building libxml2 - version 2.12.6
========================================================
Downloading "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v2.12.6/libxml2-v2.12.6.tar.bz2" saving as "libxml2-2.12.6.tar.bz2"
Download Completed
File extracted: libxml2-2.12.6.tar.bz2

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libpng - version 1.6.43
========================================================
Downloading "https://github.com/pnggroup/libpng/archive/refs/tags/v1.6.43.tar.gz" saving as "libpng-1.6.43.tar.gz"
Download Completed
File extracted: libpng-1.6.43.tar.gz

$ autoupdate
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-hardware-optimizations=yes --with-pic
$ make -j32
$ make install-header-links install-library-links install

Building libtiff - version 4.6.0
========================================================
Downloading "https://gitlab.com/libtiff/libtiff/-/archive/v4.6.0/libtiff-v4.6.0.tar.bz2" saving as "libtiff-4.6.0.tar.bz2"
Download Completed
File extracted: libtiff-4.6.0.tar.bz2

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-docs --disable-sphinx --disable-tests --enable-cxx --with-pic
$ make -j32
$ make install

Building aribb24 - version 1.0.3
========================================================
Downloading "https://github.com/nkoriyama/aribb24/archive/refs/tags/v1.0.3.tar.gz" saving as "aribb24-1.0.3.tar.gz"
Download Completed
File extracted: aribb24-1.0.3.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --enable-static
$ make -j32
$ make install

Building freetype - version 2.13.2
========================================================
Downloading "https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-2-13-2/freetype-VER-2-13-2.tar.bz2" saving as "freetype-2.13.2.tar.bz2"
Download Completed
File extracted: freetype-2.13.2.tar.bz2

$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dharfbuzz=disabled -Dpng=disabled -Dbzip2=disabled -Dbrotli=disabled -Dzlib=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building fontconfig - version 2.15.0
========================================================
Downloading "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/2.15.0/fontconfig-2.15.0.tar.bz2" saving as "fontconfig-2.15.0.tar.bz2"
Download Completed
File extracted: fontconfig-2.15.0.tar.bz2

$ ./autogen.sh --noconf
$ autoupdate
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-docbook --disable-docs --disable-nls --disable-shared --enable-iconv --enable-static --with-arch=x86_64 --with-libiconv-prefix=/usr
$ make -j32
$ make install

Building harfbuzz - version 8.4.0
========================================================
Downloading "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/8.4.0.tar.gz" saving as "harfbuzz-8.4.0.tar.gz"
Download Completed
File extracted: harfbuzz-8.4.0.tar.gz

$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbenchmark=disabled -Dcairo=disabled -Ddocs=disabled -Dglib=disabled -Dgobject=disabled -Dicu=disabled -Dintrospection=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building c2man-git - version 577ed40
========================================================
Cloning "c2man-git" saving version "577ed40"
Cloning completed: 577ed40
$ ./Configure -desO -D bin=/home/jman/tmp/ffmpeg-build-script/workspace/bin -D cc=/usr/bin/cc -D d_gnu=/usr/lib/x86_64-linux-gnu -D gcc=/usr/bin/gcc -D installmansrc=/home/jman/tmp/ffmpeg-build-script/workspace/share/man -D ldflags=-L/home/jman/tmp/ffmpeg-build-script/workspace/lib64 -L/home/jman/tmp/ffmpeg-build-script/workspace/lib -Wl,-O1,--sort-common,--as-needed,-z,relro,-z,now -DLIBXML_STATIC -D libpth=/usr/lib64 /usr/lib /lib64 /lib -D locincpth=/home/jman/tmp/ffmpeg-build-script/workspace/include /usr/local/include /usr/include -D loclibpth=/home/jman/tmp/ffmpeg-build-script/workspace/lib64 /home/jman/tmp/ffmpeg-build-script/workspace/lib /usr/local/lib64 /usr/local/lib -D osname=Ubuntu -D prefix=/home/jman/tmp/ffmpeg-build-script/workspace -D privlib=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man -D privlibexp=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man
$ make depend
$ make -j32
$ make install

Building fribidi - version 1.0.13
========================================================
Downloading "https://github.com/fribidi/fribidi/archive/refs/tags/v1.0.13.tar.gz" saving as "fribidi-1.0.13.tar.gz"
Download Completed
File extracted: fribidi-1.0.13.tar.gz

$ autoreconf -fi
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=false -Dtests=false
$ ninja -j32 -C build
$ ninja -C build install

Building libass - version 0.17.1
========================================================
Downloading "https://github.com/libass/libass/archive/refs/tags/0.17.1.tar.gz" saving as "libass-0.17.1.tar.gz"
Download Completed
File extracted: libass-0.17.1.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building freeglut - version 3.4.0
========================================================
Downloading "https://github.com/freeglut/freeglut/releases/download/v3.4.0/freeglut-3.4.0.tar.gz" saving as "freeglut-3.4.0.tar.gz"
Download Completed
File extracted: freeglut-3.4.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_DEMOS=OFF -DFREEGLUT_BUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_ERRORS=OFF -DFREEGLUT_BUILD_WARNINGS=OFF -DFREEGLUT_BUILD_TESTS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libwebp-git - version 1.4.0
========================================================
Cloning "libwebp-git" saving version "1.4.0"
Cloning completed: 1.4.0
$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DZLIB_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DWEBP_BUILD_ANIM_UTILS=OFF -DWEBP_BUILD_EXTRAS=OFF -DWEBP_BUILD_VWEBP=OFF -DWEBP_BUILD_CWEBP=ON -DWEBP_BUILD_DWEBP=ON -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libhwy - version 1.1.0
========================================================
Downloading "https://github.com/google/highway/archive/refs/tags/1.1.0.tar.gz" saving as "libhwy-1.1.0.tar.gz"
Download Completed
File extracted: libhwy-1.1.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DHWY_ENABLE_EXAMPLES=OFF -DHWY_ENABLE_TESTS=OFF -DHWY_FORCE_STATIC_LIBS=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building brotli - version 1.1.0
========================================================
Downloading "https://github.com/google/brotli/archive/refs/tags/v1.1.0.tar.gz" saving as "brotli-1.1.0.tar.gz"
Download Completed
File extracted: brotli-1.1.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building lcms2 - version 2.16
========================================================
Downloading "https://github.com/mm2/Little-CMS/archive/refs/tags/lcms2.16.tar.gz" saving as "lcms2-2.16.tar.gz"
Download Completed
File extracted: lcms2-2.16.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --enable-static --with-threaded
$ make -j32
$ make install

Building gflags - version 2.2.2
========================================================
Downloading "https://github.com/gflags/gflags/archive/refs/tags/v2.2.2.tar.gz" saving as "gflags-2.2.2.tar.gz"
Download Completed
File extracted: gflags-2.2.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_gflags_LIB=ON -DBUILD_STATIC_LIBS=ON -DINSTALL_HEADERS=ON -DREGISTER_BUILD_DIR=ON -DREGISTER_INSTALL_PREFIX=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building opencl-sdk-git - version 2023.12.14
========================================================
Cloning "opencl-sdk-git" saving version "2023.12.14"
Cloning completed: 2023.12.14
$ cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_DOCS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DCMAKE_CXX_FLAGS=-O3 -pipe -fPIC -march=native -DHWY_COMPILE_ALL_ATTAINABLE -DCMAKE_C_FLAGS=-O3 -pipe -fPIC -march=native -DNOLIBTOOL -DFREEGLUT_STATIC -DHWY_COMPILE_ALL_ATTAINABLE -DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF -DOPENCL_ICD_LOADER_BUILD_SHARED_LIBS=OFF -DOPENCL_SDK_BUILD_OPENGL_SAMPLES=OFF -DOPENCL_SDK_BUILD_SAMPLES=OFF -DOPENCL_SDK_TEST_SAMPLES=OFF -DTHREADS_PREFER_PTHREAD_FLAG=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building jpeg-turbo-git - version 390ed2f
========================================================
Cloning "jpeg-turbo-git" saving version "390ed2f"
Cloning completed: 390ed2f
$ cmake -S . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -G Ninja -Wno-dev
$ ninja -j32
$ ninja -j32 install

Building rubberband-git - version 6c80b8d
========================================================
Cloning "rubberband-git" saving version "6c80b8d"
Cloning completed: 6c80b8d
$ make -j32 PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install-static

Building c-ares - version 1.28.1
========================================================
Downloading "https://github.com/c-ares/c-ares/archive/refs/tags/cares-1_28_1.tar.gz" saving as "c-ares-1.28.1.tar.gz"
Download Completed
File extracted: c-ares-1.28.1.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-debug --disable-shared --disable-warnings --enable-static --with-pic
$ make -j32
$ make install

Building lv2-git - version 1.18.10
========================================================
Cloning "lv2-git" saving version "1.18.10"
Cloning completed: 1.18.10
Creating a Python virtual environment at /home/jman/tmp/ffmpeg-build-script/workspace/python_virtual_environment/lv2-git...
Activating the virtual environment...
Installing Python packages: lxml Markdown Pygments rdflib...
Collecting lxml
  Using cached lxml-5.2.1-cp310-cp310-manylinux_2_28_x86_64.whl (5.0 MB)
Collecting Markdown
  Using cached Markdown-3.6-py3-none-any.whl (105 kB)
Collecting Pygments
  Using cached pygments-2.17.2-py3-none-any.whl (1.2 MB)
Collecting rdflib
  Using cached rdflib-7.0.0-py3-none-any.whl (531 kB)
Collecting pyparsing<4,>=2.1.0
  Using cached pyparsing-3.1.2-py3-none-any.whl (103 kB)
Collecting isodate<0.7.0,>=0.6.0
  Using cached isodate-0.6.1-py2.py3-none-any.whl (41 kB)
Collecting six
  Using cached six-1.16.0-py2.py3-none-any.whl (11 kB)
Installing collected packages: six, pyparsing, Pygments, Markdown, lxml, isodate, rdflib
Successfully installed Markdown-3.6 Pygments-2.17.2 isodate-0.6.1 lxml-5.2.1 pyparsing-3.1.2 rdflib-7.0.0 six-1.16.0
Deactivating the virtual environment...
Python virtual environment setup and package installation completed.
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dtests=disabled -Donline_docs=false -Dplugins=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building waflib - version 2.0.27
========================================================
Downloading "https://gitlab.com/ita1024/waf/-/archive/waf-2.0.27/waf-waf-2.0.27.tar.bz2" saving as "waflib-2.0.27.tar.bz2"
Download Completed
File extracted: waflib-2.0.27.tar.bz2


Building serd - version 0.32.2
========================================================
Downloading "https://gitlab.com/drobilla/serd/-/archive/v0.32.2/serd-v0.32.2.tar.bz2" saving as "serd-0.32.2.tar.bz2"
Download Completed
File extracted: serd-0.32.2.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dstatic=true -Ddocs=disabled -Dhtml=disabled -Dman=disabled -Dman_html=disabled -Dsinglehtml=disabled -Dtests=disabled -Dtools=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building pcre2 - version 10.43
========================================================
Downloading "https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-10.43.tar.gz" saving as "pcre2-10.43.tar.gz"
Download Completed
File extracted: pcre2-10.43.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-jit --enable-valgrind --disable-shared
$ make -j32
$ make install

Building zix - version 0.4.2
========================================================
Downloading "https://gitlab.com/drobilla/zix/-/archive/v0.4.2/zix-v0.4.2.tar.bz2" saving as "zix-0.4.2.tar.bz2"
Download Completed
File extracted: zix-0.4.2.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbenchmarks=disabled -Ddocs=disabled -Dsinglehtml=disabled -Dtests=disabled -Dtests_cpp=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building sord - version c7f822f1
========================================================
Downloading "https://gitlab.com/drobilla/sord/-/archive/c7f822f14aae0367e184c847379496bc28adf63d/sord-c7f822f14aae0367e184c847379496bc28adf63d.tar.bz2" saving as "sord-c7f822f1.tar.bz2"
Download Completed
File extracted: sord-c7f822f1.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dtests=disabled -Dtools=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building sratom - version 0.6.16
========================================================
Downloading "https://gitlab.com/lv2/sratom/-/archive/v0.6.16/sratom-v0.6.16.tar.bz2" saving as "sratom-0.6.16.tar.bz2"
Download Completed
File extracted: sratom-0.6.16.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dhtml=disabled -Dsinglehtml=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building lilv - version 0.24.24
========================================================
Downloading "https://gitlab.com/lv2/lilv/-/archive/v0.24.24/lilv-v0.24.24.tar.bz2" saving as "lilv-0.24.24.tar.bz2"
Download Completed
File extracted: lilv-0.24.24.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dhtml=disabled -Dsinglehtml=disabled -Dtests=disabled -Dtools=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building libmpg123-git - version 8cbf2fa
========================================================
Cloning "libmpg123-git" saving version "8cbf2fa"
Cloning completed: 8cbf2fa
$ rm -fr aclocal.m4
$ aclocal --force -I m4
$ autoconf -f -W all,no-obsolete
$ autoheader -f -W all
$ automake -a -c -f -W all,no-portability
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-static
$ make -j32
$ make install

Building jansson - version 2.14
========================================================
Downloading "https://github.com/akheron/jansson/archive/refs/tags/v2.14.tar.gz" saving as "jansson-2.14.tar.gz"
Download Completed
File extracted: jansson-2.14.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building jemalloc - version 5.3.0
========================================================
Downloading "https://github.com/jemalloc/jemalloc/archive/refs/tags/5.3.0.tar.gz" saving as "jemalloc-5.3.0.tar.gz"
Download Completed
File extracted: jemalloc-5.3.0.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-debug --disable-doc --disable-fill --disable-log --disable-shared --disable-prof --disable-stats --enable-autogen --enable-static --enable-xmalloc
$ make -j32
$ make install

Building cunit-git - version 2.1-3
========================================================
Cloning "cunit-git" saving version "2.1-3"
Cloning completed: 2.1-3
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Audio Tools |
|                        |
 ------------------------

Building sdl2-git - version a923db9
========================================================
Cloning "sdl2-git" saving version "a923db9"
Cloning completed: a923db9
$ cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DSDL_ALSA_SHARED=OFF -DSDL_CCACHE=ON -DSDL_DISABLE_INSTALL_DOCS=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libsndfile - version 1.2.2
========================================================
Downloading "https://github.com/libsndfile/libsndfile/releases/download/1.2.2/libsndfile-1.2.2.tar.xz" saving as "libsndfile-1.2.2.tar.xz"
Download Completed
File extracted: libsndfile-1.2.2.tar.xz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-static --with-pic
$ make -j32
$ make install

Building pulseaudio-git - version 17.0
========================================================
Cloning "pulseaudio-git" saving version "17.0"
Cloning completed: 17.0
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddaemon=false -Ddoxygen=false -Dipv6=false -Dman=false -Dtests=false
$ ninja -j32 -C build
$ ninja -C build install
$ cp -f /home/jman/tmp/ffmpeg-build-script/workspace/lib/x86_64-linux-gnu/pulseaudio/libpulsecommon-.0.so /usr/lib/x86_64-linux-gnu/pulseaudio/libpulsecommon-17.0.so
$ ln -sf /usr/lib/x86_64-linux-gnu/pulseaudio/libpulsecommon-17.0.so /usr/lib/x86_64-linux-gnu

Building libogg - version 1.3.5
========================================================
Downloading "https://github.com/xiph/ogg/archive/refs/tags/v1.3.5.tar.gz" saving as "libogg-1.3.5.tar.gz"
Download Completed
File extracted: libogg-1.3.5.tar.gz

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DCPACK_BINARY_DEB=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libfdk-aac - version 2.0.3
========================================================
Downloading "https://phoenixnap.dl.sourceforge.net/project/opencore-amr/fdk-aac/fdk-aac-2.0.3.tar.gz" saving as "libfdk-aac-2.0.3.tar.gz"
Download Completed
File extracted: libfdk-aac-2.0.3.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building vorbis - version 1.3.7
========================================================
Downloading "https://github.com/xiph/vorbis/archive/refs/tags/v1.3.7.tar.gz" saving as "vorbis-1.3.7.tar.gz"
Download Completed
File extracted: vorbis-1.3.7.tar.gz

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DOGG_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DOGG_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libogg.so -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building opus - version 1.5.2
========================================================
Downloading "https://github.com/xiph/opus/archive/refs/tags/v1.5.2.tar.gz" saving as "opus-1.5.2.tar.gz"
Download Completed
File extracted: opus-1.5.2.tar.gz

$ autoreconf -fis
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libmysofa - version 1.3.2
========================================================
Downloading "https://github.com/hoene/libmysofa/archive/refs/tags/v1.3.2.tar.gz" saving as "libmysofa-1.3.2.tar.gz"
Download Completed
File extracted: libmysofa-1.3.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building libvpx - version 1.14.0
========================================================
Downloading "https://github.com/webmproject/libvpx/archive/refs/tags/v1.14.0.tar.gz" saving as "libvpx-1.14.0.tar.gz"
Download Completed
File extracted: libvpx-1.14.0.tar.gz

$ sed -i s/#include "\.\/vpx_tpl\.h"/#include ".\/vpx\/vpx_tpl.h"/ vpx/vpx_ext_ratectrl.h
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --as=yasm --disable-examples --disable-shared --disable-unit-tests --enable-better-hw-compatibility --enable-libyuv --enable-multi-res-encoding --enable-postproc --enable-small --enable-vp8 --enable-vp9 --enable-vp9-highbitdepth --enable-vp9-postproc --enable-webm-io
$ make -j32
$ make install

Building opencore-amr - version 0.1.6-1
========================================================
Downloading "https://salsa.debian.org/multimedia-team/opencore-amr/-/archive/debian/0.1.6-1/opencore-amr-debian-0.1.6-1.tar.bz2" saving as "opencore-amr-0.1.6-1.tar.bz2"
Download Completed
File extracted: opencore-amr-0.1.6-1.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building liblame - version 3.100
========================================================
Downloading "https://master.dl.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz?viasf=1" saving as "liblame-3.100.tar.gz"
Download Completed
File extracted: liblame-3.100.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-gtktest --disable-shared --enable-nasm --with-libiconv-prefix=/usr
$ make -j32
$ make install

Building libtheora - version 1.1.1
========================================================
Downloading "https://github.com/xiph/theora/archive/refs/tags/v1.1.1.tar.gz" saving as "libtheora-1.1.1.tar.gz"
Download Completed
File extracted: libtheora-1.1.1.tar.gz

$ ./autogen.sh
$ mv configure.patched configure
$ rm config.guess
$ curl -LSso config.guess https://raw.githubusercontent.com/gcc-mirror/gcc/master/config.guess
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-examples --disable-oggtest --disable-sdltest --disable-shared --disable-vorbistest --enable-static --with-ogg-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-ogg-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-ogg=/home/jman/tmp/ffmpeg-build-script/workspace --with-sdl-prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-vorbis-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-vorbis-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-vorbis=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Video Tools |
|                        |
 ------------------------

Building av1-git - version 3.8.2
========================================================
Cloning "av1-git" saving version "3.8.2"
Cloning completed: 3.8.2
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCONFIG_AV1_DECODER=1 -DCONFIG_AV1_ENCODER=1 -DCONFIG_AV1_HIGHBITDEPTH=1 -DCONFIG_AV1_TEMPORAL_DENOISING=1 -DCONFIG_DENOISE=1 -DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1 -DENABLE_CCACHE=1 -DENABLE_EXAMPLES=0 -DENABLE_TESTS=0 -G Ninja -Wno-dev /home/jman/tmp/ffmpeg-build-script/packages/av1
$ ninja -j32 -C build
$ ninja -C build install

Building rav1e - version p20240416
========================================================
Installing RustUp
[INFO] cargo-c is already installed.
Downloading "https://github.com/xiph/rav1e/archive/refs/tags/p20240416.tar.gz" saving as "rav1e-p20240416.tar.gz"
Download Completed
File extracted: rav1e-p20240416.tar.gz

$ cargo cinstall --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --library-type=staticlib --crt-static --release

Building zimg-git - version 7143181
========================================================
Cloning "zimg-git" saving version "7143181"
Cloning completed: 7143181
$ ./autogen.sh
$ git submodule update --init --recursive
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pic
$ make -j32
$ make install

Building avif - version 1.0.4
========================================================
Downloading "https://github.com/AOMediaCodec/libavif/archive/refs/tags/v1.0.4.tar.gz" saving as "avif-1.0.4.tar.gz"
Download Completed
File extracted: avif-1.0.4.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DAVIF_CODEC_AOM=ON -DAVIF_CODEC_AOM_DECODE=ON -DAVIF_CODEC_AOM_ENCODE=ON -DAVIF_ENABLE_GTEST=OFF -DAVIF_ENABLE_WERROR=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building kvazaar-git - version 2.3.1
========================================================
Cloning "kvazaar-git" saving version "2.3.1"
Cloning completed: 2.3.1
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building libdvdread - version 6.1.3
========================================================
Downloading "https://code.videolan.org/videolan/libdvdread/-/archive/6.1.3/libdvdread-6.1.3.tar.bz2" saving as "libdvdread-6.1.3.tar.bz2"
Download Completed
File extracted: libdvdread-6.1.3.tar.bz2

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-apidoc --disable-shared
$ make -j32
$ make install

Building udfread - version 1.1.2
========================================================
Downloading "https://code.videolan.org/videolan/libudfread/-/archive/1.1.2/libudfread-1.1.2.tar.bz2" saving as "libudfread-1.1.2.tar.bz2"
Download Completed
File extracted: libudfread-1.1.2.tar.bz2

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building ant-git - version 1.10.14
========================================================
Cloning "ant-git" saving version "1.10.14"
Cloning completed: rel
$ sh build.sh install-lite

Building zenlib - version 0.4.41
========================================================
Downloading "https://github.com/MediaArea/ZenLib/archive/refs/tags/v0.4.41.tar.gz" saving as "zenlib-0.4.41.tar.gz"
Download Completed
File extracted: zenlib-0.4.41.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfo-lib - version 24.03
========================================================
Downloading "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v24.03.tar.gz" saving as "mediainfo-lib-24.03.tar.gz"
Download Completed
File extracted: mediainfo-lib-24.03.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfo-cli - version 24.03
========================================================
Downloading "https://github.com/MediaArea/MediaInfo/archive/refs/tags/v24.03.tar.gz" saving as "mediainfo-cli-24.03.tar.gz"
Download Completed
File extracted: mediainfo-cli-24.03.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-staticlibs --disable-shared
$ make -j32
$ make install
$ cp -f /home/jman/tmp/ffmpeg-build-script/packages/mediainfo-cli-24.03/Project/GNU/CLI/mediainfo /usr/local/bin/

Building vid-stab - version 1.1.1
========================================================
Downloading "https://github.com/georgmartius/vid.stab/archive/refs/tags/v1.1.1.tar.gz" saving as "vid-stab-1.1.1.tar.gz"
Download Completed
File extracted: vid-stab-1.1.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DUSE_OMP=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building frei0r - version 2.3.2
========================================================
Downloading "https://github.com/dyne/frei0r/archive/refs/tags/v2.3.2.tar.gz" saving as "frei0r-2.3.2.tar.gz"
Download Completed
File extracted: frei0r-2.3.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DWITHOUT_OPENCV=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building gpac-git - version 2.4.0
========================================================
Cloning "gpac-git" saving version "2.4.0"
Cloning completed: 2.4.0
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --static-bin --static-modules --use-a52=local --use-faad=local --use-freetype=local --use-mad=local --sdl-cfg=/home/jman/tmp/ffmpeg-build-script/workspace/bin/sdl2-config
$ make -j32
$ make install
$ cp -f bin/gcc/MP4Box /usr/local/bin

Building svt-av1 - version 1.8.0
========================================================
Downloading "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.8.0/SVT-AV1-v1.8.0.tar.bz2" saving as "svt-av1-1.8.0.tar.bz2"
Download Completed
File extracted: svt-av1-1.8.0.tar.bz2

$ cmake -S . -B Build/linux -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_APPS=OFF -DBUILD_DEC=ON -DBUILD_ENC=ON -DBUILD_TESTING=OFF -DENABLE_AVX512=ON -DENABLE_NASM=ON -DNATIVE=ON -G Ninja -Wno-dev
$ ninja -j32 -C Build/linux
$ ninja -j32 -C Build/linux install

Building x264 - version 7ed753b1
========================================================
Downloading "https://code.videolan.org/videolan/x264/-/archive/7ed753b10a61d0be95f683289dfb925b800b0676/x264-7ed753b10a61d0be95f683289dfb925b800b0676.tar.bz2" saving as "x264-7ed753b1.tar.bz2"
Download Completed
File extracted: x264-7ed753b1.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --bit-depth=all --chroma-format=all --enable-debug --enable-gprof --enable-lto --enable-pic --enable-static --enable-strip CFLAGS=-O3 -pipe -fPIC -march=native -DNOLIBTOOL -DFREEGLUT_STATIC -DHWY_COMPILE_ALL_ATTAINABLE -I/home/jman/tmp/ffmpeg-build-script/workspace/include/serd-0 CXXFLAGS=-O3 -pipe -fPIC -march=native -DHWY_COMPILE_ALL_ATTAINABLE
$ make -j32
$ make install
$ make install-lib-static

Building x265 - version 3.6
========================================================
Downloading "https://bitbucket.org/multicoreware/x265_git/downloads/x265_3.6.tar.gz" saving as "x265-3.6.tar.gz"
Download Completed
File extracted: x265-3.6.tar.gz

$ making 12bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_CLI=OFF -DENABLE_LIBVMAF=OFF -DENABLE_SHARED=OFF -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DMAIN12=ON -DNATIVE_BUILD=ON -G Ninja -Wno-dev
$ ninja -j32
$ making 10bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_CLI=OFF -DENABLE_LIBVMAF=OFF -DENABLE_SHARED=OFF -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DNATIVE_BUILD=ON -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
$ ninja -j32
$ making 8bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_LIBVMAF=OFF -DENABLE_PIC=ON -DENABLE_SHARED=ON -DEXTRA_LIB=x265_main10.a;x265_main12.a -DEXTRA_LINK_FLAGS=-L. -DHIGH_BIT_DEPTH=ON -DLINKED_10BIT=ON -DLINKED_12BIT=ON -DNATIVE_BUILD=ON -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
$ ninja -j32
$ ar -M
$ ninja install

Building nv-codec-headers - version 12.1.14.0
========================================================
Downloading "https://github.com/FFmpeg/nv-codec-headers/releases/download/n12.1.14.0/nv-codec-headers-12.1.14.0.tar.gz" saving as "nv-codec-headers-12.1.14.0.tar.gz"
Download Completed
File extracted: nv-codec-headers-12.1.14.0.tar.gz

$ make -j32
$ make PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install

Building srt - version 1.5.3
========================================================
Downloading "https://github.com/Haivision/srt/archive/refs/tags/v1.5.3.tar.gz" saving as "srt-1.5.3.tar.gz"
Download Completed
File extracted: srt-1.5.3.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DENABLE_APPS=OFF -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DUSE_STATIC_LIBSTDCXX=ON -G Ninja -Wno-dev
$ ninja -C build -j32
$ ninja -C build -j32 install

Building avisynth - version 3.7.3
========================================================
Downloading "https://github.com/AviSynth/AviSynthPlus/archive/refs/tags/v3.7.3.tar.gz" saving as "avisynth-3.7.3.tar.gz"
Download Completed
File extracted: avisynth-3.7.3.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DHEADERS_ONLY=OFF
$ make -j32 -C build VersionGen install

Building vapoursynth - version R65
========================================================
Downloading "https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R65.tar.gz" saving as "vapoursynth-R65.tar.gz"
Download Completed
File extracted: vapoursynth-R65.tar.gz

Creating a Python virtual environment at /home/jman/tmp/ffmpeg-build-script/workspace/python_virtual_environment/vapoursynth...
Activating the virtual environment...
Installing Python packages: Cython==0.29.36...
Collecting Cython==0.29.36
  Using cached Cython-0.29.36-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (1.9 MB)
Installing collected packages: Cython
Successfully installed Cython-0.29.36
Deactivating the virtual environment...
Python virtual environment setup and package installation completed.
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building libgav1-git - version 0.19.0
========================================================
Cloning "libgav1-git" saving version "0.19.0"
Cloning completed: 0.19.0
$ git clone -q -b 20220623.1 --depth 1 https://github.com/abseil/abseil-cpp.git third_party/abseil-cpp
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DABSL_ENABLE_INSTALL=ON -DABSL_PROPAGATE_CXX_STD=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INSTALL_SBINDIR=sbin -DLIBGAV1_ENABLE_TESTS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building xvidcore - version 1.3.7-1
========================================================
Downloading "https://salsa.debian.org/multimedia-team/xvidcore/-/archive/debian/2%251.3.7-1/xvidcore-debian-2%251.3.7-1.tar.bz2" saving as "xvidcore-1.3.7-1.tar.bz2"
Download Completed
File extracted: xvidcore-1.3.7-1.tar.bz2

$ ./bootstrap.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Image Tools |
|                        |
 ------------------------

Building libheif - version 1.17.6
========================================================
Downloading "https://github.com/strukturag/libheif/archive/refs/tags/v1.17.6.tar.gz" saving as "libheif-1.17.6.tar.gz"
Download Completed
File extracted: libheif-1.17.6.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DAOM_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DAOM_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libaom.a -DBUILD_SHARED_LIBS=OFF -DLIBDE265_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DLIBDE265_LIBRARY=/usr/lib/x86_64-linux-gnu/libde265.so -DLIBSHARPYUV_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include/webp -DLIBSHARPYUV_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libsharpyuv.so -DWITH_AOM_DECODER=ON -DWITH_AOM_ENCODER=ON -DWITH_DAV1D=OFF -DWITH_EXAMPLES=OFF -DWITH_REDUCED_VISIBILITY=OFF -DWITH_SvtEnc=OFF -DWITH_SvtEnc_PLUGIN=OFF -DWITH_X265=OFF -DWITH_GDK_PIXBUF=ON -DWITH_LIBDE265=ON -DWITH_LIBSHARPYUV=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

Building openjpeg - version 2.5.2
========================================================
Downloading "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v2.5.2" saving as "openjpeg-2.5.2.tar.gz"
Download Completed
File extracted: openjpeg-2.5.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DBUILD_THIRDPARTY=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -C build install

 -----------------
|                 |
| Building FFmpeg |
|                 |
 -----------------

[UPDATE] Installed FFmpeg version: Not installed
[UPDATE] Latest FFmpeg release version available: n7.0

Building ffmpeg - version n6.1.1
========================================================
Downloading "https://ffmpeg.org/releases/ffmpeg-6.1.1.tar.xz" saving as "ffmpeg-n6.1.1.tar.xz"
Download Completed
File extracted: ffmpeg-n6.1.1.tar.xz

install prefix            /usr/local
source path               /home/jman/tmp/ffmpeg-build-script/packages/ffmpeg-n6.1.1
C compiler                gcc
C library                 glibc
ARCH                      x86 (generic)
big-endian                no
runtime cpu detection     yes
standalone assembly       yes
x86 assembler             nasm
MMX enabled               yes
MMXEXT enabled            yes
3DNow! enabled            yes
3DNow! extended enabled   yes
SSE enabled               yes
SSSE3 enabled             yes
AESNI enabled             yes
AVX enabled               yes
AVX2 enabled              yes
AVX-512 enabled           yes
AVX-512ICL enabled        yes
XOP enabled               yes
FMA3 enabled              yes
FMA4 enabled              yes
i686 features enabled     yes
CMOV is fast              yes
EBX available             yes
EBP available             yes
debug symbols             no
strip symbols             yes
optimize for size         yes
optimizations             yes
static                    yes
shared                    no
postprocessing support    yes
network support           yes
threading support         pthreads
safe bitstream reader     yes
texi2html enabled         no
perl enabled              yes
pod2man enabled           yes
makeinfo enabled          yes
makeinfo supports HTML    yes
xmllint enabled           yes

External libraries:
alsa                    libaribb24              libfribidi              libopenjpeg             libsnappy               libv4l2                 libxcb_shm              sndio
avisynth                libass                  libgme                  libopus                 libsoxr                 libvidstab              libxml2                 vapoursynth
bzlib                   libbluray               libharfbuzz             libpulse                libspeex                libvo_amrwbenc          libxvid                 zlib
chromaprint             libbs2b                 libkvazaar              librav1e                libsrt                  libvorbis               libzimg
frei0r                  libcaca                 libmodplug              librist                 libssh                  libvpx                  libzvbi
iconv                   libcdio                 libmp3lame              librubberband           libsvtav1               libwebp                 lv2
ladspa                  libfdk_aac              libmysofa               libshine                libtesseract            libx264                 lzma
lcms2                   libfontconfig           libopencore_amrnb       libsmbclient            libtheora               libx265                 opengl
libaom                  libfreetype             libopencore_amrwb       libsmbclient            libtwolame              libxcb                  openssl

External libraries providing hardware acceleration:
cuda                    cuda_nvcc               ffnvcodec               nvenc                   v4l2_m2m                vdpau
cuda_llvm               cuvid                   nvdec                   opencl                  vaapi

Libraries:
avcodec                 avdevice                avfilter                avformat                avutil                  postproc                swresample              swscale

Programs:
ffmpeg                  ffprobe

Enabled decoders:
aac                     amv                     dolby_e                 hdr                     mp2float                pcm_s24daud             sbc                     vcr1
aac_fixed               anm                     dpx                     hevc                    mp3                     pcm_s24le               scpr                    vmdaudio
aac_latm                ansi                    dsd_lsbf                hevc_cuvid              mp3adu                  pcm_s24le_planar        screenpresso            vmdvideo
aasc                    anull                   dsd_lsbf_planar         hevc_v4l2m2m            mp3adufloat             pcm_s32be               sdx2_dpcm               vmix
ac3                     apac                    dsd_msbf                hnm4_video              mp3float                pcm_s32le               sga                     vmnc
ac3_fixed               ape                     dsd_msbf_planar         hq_hqa                  mp3on4                  pcm_s32le_planar        sgi                     vnull
acelp_kelvin            apng                    dsicinaudio             hqx                     mp3on4float             pcm_s64be               sgirle                  vorbis
adpcm_4xm               aptx                    dsicinvideo             huffyuv                 mpc7                    pcm_s64le               sheervideo              vp3
adpcm_adx               aptx_hd                 dss_sp                  hymt                    mpc8                    pcm_s8                  shorten                 vp4
adpcm_afc               arbc                    dst                     iac                     mpeg1_cuvid             pcm_s8_planar           simbiosis_imx           vp5
adpcm_agm               argo                    dvaudio                 idcin                   mpeg1_v4l2m2m           pcm_sga                 sipr                    vp6
adpcm_aica              ass                     dvbsub                  idf                     mpeg1video              pcm_u16be               siren                   vp6a
adpcm_argo              asv1                    dvdsub                  iff_ilbm                mpeg2_cuvid             pcm_u16le               smackaud                vp6f
adpcm_ct                asv2                    dvvideo                 ilbc                    mpeg2_v4l2m2m           pcm_u24be               smacker                 vp7
adpcm_dtk               atrac1                  dxa                     imc                     mpeg2video              pcm_u24le               smc                     vp8
adpcm_ea                atrac3                  dxtory                  imm4                    mpeg4                   pcm_u32be               smvjpeg                 vp8_cuvid
adpcm_ea_maxis_xa       atrac3al                dxv                     imm5                    mpeg4_cuvid             pcm_u32le               snow                    vp8_v4l2m2m
adpcm_ea_r1             atrac3p                 eac3                    indeo2                  mpeg4_v4l2m2m           pcm_u8                  sol_dpcm                vp9
adpcm_ea_r2             atrac3pal               eacmv                   indeo3                  mpegvideo               pcm_vidc                sonic                   vp9_cuvid
adpcm_ea_r3             atrac9                  eamad                   indeo4                  mpl2                    pcx                     sp5x                    vp9_v4l2m2m
adpcm_ea_xas            aura                    eatgq                   indeo5                  msa1                    pdv                     speedhq                 vplayer
adpcm_g722              aura2                   eatgv                   interplay_acm           mscc                    pfm                     speex                   vqa
adpcm_g726              av1                     eatqi                   interplay_dpcm          msmpeg4v1               pgm                     srgc                    vqc
adpcm_g726le            av1_cuvid               eightbps                interplay_video         msmpeg4v2               pgmyuv                  srt                     wady_dpcm
adpcm_ima_acorn         avrn                    eightsvx_exp            ipu                     msmpeg4v3               pgssub                  ssa                     wavarc
adpcm_ima_alp           avrp                    eightsvx_fib            jacosub                 msnsiren                pgx                     stl                     wavpack
adpcm_ima_amv           avs                     escape124               jpeg2000                msp2                    phm                     subrip                  wbmp
adpcm_ima_apc           avui                    escape130               jpegls                  msrle                   photocd                 subviewer               wcmv
adpcm_ima_apm           ayuv                    evrc                    jv                      mss1                    pictor                  subviewer1              webp
adpcm_ima_cunning       bethsoftvid             exr                     kgv1                    mss2                    pixlet                  sunrast                 webvtt
adpcm_ima_dat4          bfi                     fastaudio               kmvc                    msvideo1                pjs                     svq1                    wmalossless
adpcm_ima_dk3           bink                    ffv1                    lagarith                mszh                    png                     svq3                    wmapro
adpcm_ima_dk4           binkaudio_dct           ffvhuff                 libaom_av1              mts2                    ppm                     tak                     wmav1
adpcm_ima_ea_eacs       binkaudio_rdft          ffwavesynth             libaribb24              mv30                    prores                  targa                   wmav2
adpcm_ima_ea_sead       bintext                 fic                     libfdk_aac              mvc1                    prosumer                targa_y216              wmavoice
adpcm_ima_iss           bitpacked               fits                    libopencore_amrnb       mvc2                    psd                     tdsc                    wmv1
adpcm_ima_moflex        bmp                     flac                    libopencore_amrwb       mvdv                    ptx                     text                    wmv2
adpcm_ima_mtf           bmv_audio               flashsv                 libopus                 mvha                    qcelp                   theora                  wmv3
adpcm_ima_oki           bmv_video               flashsv2                libspeex                mwsc                    qdm2                    thp                     wmv3image
adpcm_ima_qt            bonk                    flic                    libvorbis               mxpeg                   qdmc                    tiertexseqvideo         wnv1
adpcm_ima_rad           brender_pix             flv                     libvpx_vp8              nellymoser              qdraw                   tiff                    wrapped_avframe
adpcm_ima_smjpeg        c93                     fmvc                    libvpx_vp9              notchlc                 qoi                     tmv                     ws_snd1
adpcm_ima_ssi           cavs                    fourxm                  libzvbi_teletext        nuv                     qpeg                    truehd                  xan_dpcm
adpcm_ima_wav           cbd2_dpcm               fraps                   loco                    on2avc                  qtrle                   truemotion1             xan_wc3
adpcm_ima_ws            ccaption                frwu                    lscr                    opus                    r10k                    truemotion2             xan_wc4
adpcm_ms                cdgraphics              ftr                     m101                    osq                     r210                    truemotion2rt           xbin
adpcm_mtaf              cdtoons                 g2m                     mace3                   paf_audio               ra_144                  truespeech              xbm
adpcm_psx               cdxl                    g723_1                  mace6                   paf_video               ra_288                  tscc                    xface
adpcm_sbpro_2           cfhd                    g729                    magicyuv                pam                     ralf                    tscc2                   xl
adpcm_sbpro_3           cinepak                 gdv                     mdec                    pbm                     rasc                    tta                     xma1
adpcm_sbpro_4           clearvideo              gem                     media100                pcm_alaw                rawvideo                twinvq                  xma2
adpcm_swf               cljr                    gif                     metasound               pcm_bluray              realtext                txd                     xpm
adpcm_thp               cllc                    gremlin_dpcm            microdvd                pcm_dvd                 rka                     ulti                    xsub
adpcm_thp_le            comfortnoise            gsm                     mimic                   pcm_f16le               rl2                     utvideo                 xwd
adpcm_vima              cook                    gsm_ms                  misc4                   pcm_f24le               roq                     v210                    y41p
adpcm_xa                cpia                    h261                    mjpeg                   pcm_f32be               roq_dpcm                v210x                   ylc
adpcm_xmd               cri                     h263                    mjpeg_cuvid             pcm_f32le               rpza                    v308                    yop
adpcm_yamaha            cscd                    h263_v4l2m2m            mjpegb                  pcm_f64be               rscc                    v408                    yuv4
adpcm_zork              cyuv                    h263i                   mlp                     pcm_f64le               rtv1                    v410                    zero12v
agm                     dca                     h263p                   mmvideo                 pcm_lxf                 rv10                    vb                      zerocodec
aic                     dds                     h264                    mobiclip                pcm_mulaw               rv20                    vble                    zlib
alac                    derf_dpcm               h264_cuvid              motionpixels            pcm_s16be               rv30                    vbn                     zmbv
alias_pix               dfa                     h264_v4l2m2m            movtext                 pcm_s16be_planar        rv40                    vc1
als                     dfpwm                   hap                     mp1                     pcm_s16le               s302m                   vc1_cuvid
amrnb                   dirac                   hca                     mp1float                pcm_s16le_planar        sami                    vc1_v4l2m2m
amrwb                   dnxhd                   hcom                    mp2                     pcm_s24be               sanm                    vc1image

Enabled encoders:
a64multi                asv1                    flv                     libsvtav1               msrle                   pcm_s8_planar           rv10                    vnull
a64multi5               asv2                    g723_1                  libtheora               msvideo1                pcm_u16be               rv20                    vorbis
aac                     av1_nvenc               gif                     libtwolame              nellymoser              pcm_u16le               s302m                   vp8_v4l2m2m
ac3                     av1_vaapi               h261                    libvo_amrwbenc          opus                    pcm_u24be               sbc                     vp8_vaapi
ac3_fixed               avrp                    h263                    libvorbis               pam                     pcm_u24le               sgi                     vp9_vaapi
adpcm_adx               avui                    h263_v4l2m2m            libvpx_vp8              pbm                     pcm_u32be               smc                     wavpack
adpcm_argo              ayuv                    h263p                   libvpx_vp9              pcm_alaw                pcm_u32le               snow                    wbmp
adpcm_g722              bitpacked               h264_nvenc              libwebp                 pcm_bluray              pcm_u8                  sonic                   webvtt
adpcm_g726              bmp                     h264_v4l2m2m            libwebp_anim            pcm_dvd                 pcm_vidc                sonic_ls                wmav1
adpcm_g726le            cfhd                    h264_vaapi              libx264                 pcm_f32be               pcx                     speedhq                 wmav2
adpcm_ima_alp           cinepak                 hap                     libx264rgb              pcm_f32le               pfm                     srt                     wmv1
adpcm_ima_amv           cljr                    hdr                     libx265                 pcm_f64be               pgm                     ssa                     wmv2
adpcm_ima_apm           comfortnoise            hevc_nvenc              libxvid                 pcm_f64le               pgmyuv                  subrip                  wrapped_avframe
adpcm_ima_qt            dca                     hevc_v4l2m2m            ljpeg                   pcm_mulaw               phm                     sunrast                 xbm
adpcm_ima_ssi           dfpwm                   hevc_vaapi              magicyuv                pcm_s16be               png                     svq1                    xface
adpcm_ima_wav           dnxhd                   huffyuv                 mjpeg                   pcm_s16be_planar        ppm                     targa                   xsub
adpcm_ima_ws            dpx                     jpeg2000                mjpeg_vaapi             pcm_s16le               prores                  text                    xwd
adpcm_ms                dvbsub                  jpegls                  mlp                     pcm_s16le_planar        prores_aw               tiff                    y41p
adpcm_swf               dvdsub                  libaom_av1              movtext                 pcm_s24be               prores_ks               truehd                  yuv4
adpcm_yamaha            dvvideo                 libfdk_aac              mp2                     pcm_s24daud             qoi                     tta                     zlib
alac                    eac3                    libkvazaar              mp2fixed                pcm_s24le               qtrle                   ttml                    zmbv
alias_pix               exr                     libmp3lame              mpeg1video              pcm_s24le_planar        r10k                    utvideo
amv                     ffv1                    libopencore_amrnb       mpeg2_vaapi             pcm_s32be               r210                    v210
anull                   ffvhuff                 libopenjpeg             mpeg2video              pcm_s32le               ra_144                  v308
apng                    fits                    libopus                 mpeg4                   pcm_s32le_planar        rawvideo                v408
aptx                    flac                    librav1e                mpeg4_v4l2m2m           pcm_s64be               roq                     v410
aptx_hd                 flashsv                 libshine                msmpeg4v2               pcm_s64le               roq_dpcm                vbn
ass                     flashsv2                libspeex                msmpeg4v3               pcm_s8                  rpza                    vc2

Enabled hwaccels:
av1_nvdec               h264_vaapi              hevc_vdpau              mpeg1_vdpau             mpeg4_nvdec             vc1_vaapi               vp9_nvdec               wmv3_vaapi
av1_vaapi               h264_vdpau              mjpeg_nvdec             mpeg2_nvdec             mpeg4_vaapi             vc1_vdpau               vp9_vaapi               wmv3_vdpau
h263_vaapi              hevc_nvdec              mjpeg_vaapi             mpeg2_vaapi             mpeg4_vdpau             vp8_nvdec               vp9_vdpau
h264_nvdec              hevc_vaapi              mpeg1_nvdec             mpeg2_vdpau             vc1_nvdec               vp8_vaapi               wmv3_nvdec

Enabled parsers:
aac                     bmp                     dpx                     g723_1                  hevc                    mpegaudio               sipr                    webp
aac_latm                cavsvideo               dvaudio                 g729                    ipu                     mpegvideo               tak                     xbm
ac3                     cook                    dvbsub                  gif                     jpeg2000                opus                    vc1                     xma
adx                     cri                     dvd_nav                 gsm                     jpegxl                  png                     vorbis                  xwd
amr                     dca                     dvdsub                  h261                    misc4                   pnm                     vp3
av1                     dirac                   evc                     h263                    mjpeg                   qoi                     vp8
avs2                    dnxhd                   flac                    h264                    mlp                     rv34                    vp9
avs3                    dolby_e                 ftr                     hdr                     mpeg4video              sbc                     vvc

Enabled demuxers:
aa                      bfi                     filmstrip               image_j2k_pipe          live_flv                nsv                     rsd                     tta
aac                     bfstm                   fits                    image_jpeg_pipe         lmlm4                   nut                     rso                     tty
aax                     bink                    flac                    image_jpegls_pipe       loas                    nuv                     rtp                     txd
ac3                     binka                   flic                    image_jpegxl_pipe       lrc                     obu                     rtsp                    ty
ac4                     bintext                 flv                     image_pam_pipe          luodat                  ogg                     s337m                   usm
ace                     bit                     fourxm                  image_pbm_pipe          lvf                     oma                     sami                    v210
acm                     bitpacked               frm                     image_pcx_pipe          lxf                     osq                     sap                     v210x
act                     bmv                     fsb                     image_pfm_pipe          m4v                     paf                     sbc                     vag
adf                     boa                     fwse                    image_pgm_pipe          matroska                pcm_alaw                sbg                     vapoursynth
adp                     bonk                    g722                    image_pgmyuv_pipe       mca                     pcm_f32be               scc                     vc1
ads                     brstm                   g723_1                  image_pgx_pipe          mcc                     pcm_f32le               scd                     vc1t
adx                     c93                     g726                    image_phm_pipe          mgsts                   pcm_f64be               sdns                    vividas
aea                     caf                     g726le                  image_photocd_pipe      microdvd                pcm_f64le               sdp                     vivo
afc                     cavsvideo               g729                    image_pictor_pipe       mjpeg                   pcm_mulaw               sdr2                    vmd
aiff                    cdg                     gdv                     image_png_pipe          mjpeg_2000              pcm_s16be               sds                     vobsub
aix                     cdxl                    genh                    image_ppm_pipe          mlp                     pcm_s16le               sdx                     voc
alp                     cine                    gif                     image_psd_pipe          mlv                     pcm_s24be               segafilm                vpk
amr                     codec2                  gsm                     image_qdraw_pipe        mm                      pcm_s24le               ser                     vplayer
amrnb                   codec2raw               gxf                     image_qoi_pipe          mmf                     pcm_s32be               sga                     vqf
amrwb                   concat                  h261                    image_sgi_pipe          mods                    pcm_s32le               shorten                 vvc
anm                     dash                    h263                    image_sunrast_pipe      moflex                  pcm_s8                  siff                    w64
apac                    data                    h264                    image_svg_pipe          mov                     pcm_u16be               simbiosis_imx           wady
apc                     daud                    hca                     image_tiff_pipe         mp3                     pcm_u16le               sln                     wav
ape                     dcstr                   hcom                    image_vbn_pipe          mpc                     pcm_u24be               smacker                 wavarc
apm                     derf                    hevc                    image_webp_pipe         mpc8                    pcm_u24le               smjpeg                  wc3
apng                    dfa                     hls                     image_xbm_pipe          mpegps                  pcm_u32be               smush                   webm_dash_manifest
aptx                    dfpwm                   hnm                     image_xpm_pipe          mpegts                  pcm_u32le               sol                     webvtt
aptx_hd                 dhav                    ico                     image_xwd_pipe          mpegtsraw               pcm_u8                  sox                     wsaud
aqtitle                 dirac                   idcin                   imf                     mpegvideo               pcm_vidc                spdif                   wsd
argo_asf                dnxhd                   idf                     ingenient               mpjpeg                  pdv                     srt                     wsvqa
argo_brp                dsf                     iff                     ipmovie                 mpl2                    pjs                     stl                     wtv
argo_cvg                dsicin                  ifv                     ipu                     mpsub                   pmp                     str                     wv
asf                     dss                     ilbc                    ircam                   msf                     pp_bnk                  subviewer               wve
asf_o                   dts                     image2                  iss                     msnwc_tcp               pva                     subviewer1              xa
ass                     dtshd                   image2_alias_pix        iv8                     msp                     pvf                     sup                     xbin
ast                     dv                      image2_brender_pix      ivf                     mtaf                    qcp                     svag                    xmd
au                      dvbsub                  image2pipe              ivr                     mtv                     r3d                     svs                     xmv
av1                     dvbtxt                  image_bmp_pipe          jacosub                 musx                    rawvideo                swf                     xvag
avi                     dxa                     image_cri_pipe          jpegxl_anim             mv                      realtext                tak                     xwma
avisynth                ea                      image_dds_pipe          jv                      mvi                     redspark                tedcaptions             yop
avr                     ea_cdata                image_dpx_pipe          kux                     mxf                     rka                     thp                     yuv4mpegpipe
avs                     eac3                    image_exr_pipe          kvag                    mxg                     rl2                     threedostr
avs2                    epaf                    image_gem_pipe          laf                     nc                      rm                      tiertexseq
avs3                    evc                     image_gif_pipe          libgme                  nistsphere              roq                     tmv
bethsoftvid             ffmetadata              image_hdr_pipe          libmodplug              nsp                     rpl                     truehd

Enabled muxers:
a64                     avs2                    filmstrip               image2                  mpeg1system             pcm_f64be               rtp                     ttml
ac3                     avs3                    fits                    image2pipe              mpeg1vcd                pcm_f64le               rtp_mpegts              uncodedframecrc
ac4                     bit                     flac                    ipod                    mpeg1video              pcm_mulaw               rtsp                    vc1
adts                    caf                     flv                     ircam                   mpeg2dvd                pcm_s16be               sap                     vc1t
adx                     cavsvideo               framecrc                ismv                    mpeg2svcd               pcm_s16le               sbc                     voc
aiff                    chromaprint             framehash               ivf                     mpeg2video              pcm_s24be               scc                     vvc
alp                     codec2                  framemd5                jacosub                 mpeg2vob                pcm_s24le               segafilm                w64
amr                     codec2raw               g722                    kvag                    mpegts                  pcm_s32be               segment                 wav
amv                     crc                     g723_1                  latm                    mpjpeg                  pcm_s32le               smjpeg                  webm
apm                     dash                    g726                    lrc                     mxf                     pcm_s8                  smoothstreaming         webm_chunk
apng                    data                    g726le                  m4v                     mxf_d10                 pcm_u16be               sox                     webm_dash_manifest
aptx                    daud                    gif                     matroska                mxf_opatom              pcm_u16le               spdif                   webp
aptx_hd                 dfpwm                   gsm                     matroska_audio          null                    pcm_u24be               spx                     webvtt
argo_asf                dirac                   gxf                     md5                     nut                     pcm_u24le               srt                     wsaud
argo_cvg                dnxhd                   h261                    microdvd                obu                     pcm_u32be               stream_segment          wtv
asf                     dts                     h263                    mjpeg                   oga                     pcm_u32le               streamhash              wv
asf_stream              dv                      h264                    mkvtimestamp_v2         ogg                     pcm_u8                  sup                     yuv4mpegpipe
ass                     eac3                    hash                    mlp                     ogv                     pcm_vidc                swf
ast                     evc                     hds                     mmf                     oma                     psp                     tee
au                      f4v                     hevc                    mov                     opus                    rawvideo                tg2
avi                     ffmetadata              hls                     mp2                     pcm_alaw                rm                      tgp
avif                    fifo                    ico                     mp3                     pcm_f32be               roq                     truehd
avm2                    fifo_test               ilbc                    mp4                     pcm_f32le               rso                     tta

Enabled protocols:
async                   data                    gopher                  icecast                 libssh                  rtmp                    rtp                     tls
bluray                  fd                      gophers                 ipfs_gateway            md5                     rtmpe                   sctp                    udp
cache                   ffrtmpcrypt             hls                     ipns_gateway            mmsh                    rtmps                   srtp                    udplite
concat                  ffrtmphttp              http                    librist                 mmst                    rtmpt                   subfile                 unix
concatf                 file                    httpproxy               libsmbclient            pipe                    rtmpte                  tcp
crypto                  ftp                     https                   libsrt                  prompeg                 rtmpts                  tee

Enabled filters:
a3dscope                aperms                  cellauto                dilation_opencl         hilbert                 mptestsrc               scale_cuda              swapuv
abench                  aphasemeter             channelmap              displace                histeq                  msad                    scale_vaapi             tblend
abitscope               aphaser                 channelsplit            dnn_classify            histogram               multiply                scdet                   telecine
acompressor             aphaseshift             chorus                  dnn_detect              hqdn3d                  negate                  scharr                  testsrc
acontrast               apsnr                   chromahold              dnn_processing          hqx                     nlmeans                 scroll                  testsrc2
acopy                   apsyclip                chromakey               doubleweave             hstack                  nlmeans_opencl          segment                 thistogram
acrossfade              apulsator               chromakey_cuda          drawbox                 hstack_vaapi            nnedi                   select                  threshold
acrossover              arealtime               chromanr                drawgraph               hsvhold                 noformat                selectivecolor          thumbnail
acrusher                aresample               chromashift             drawgrid                hsvkey                  noise                   sendcmd                 thumbnail_cuda
acue                    areverse                ciescope                drawtext                hue                     normalize               separatefields          tile
addroi                  arls                    codecview               drmeter                 huesaturation           null                    setdar                  tiltshelf
adeclick                arnndn                  color                   dynaudnorm              hwdownload              nullsink                setfield                tinterlace
adeclip                 asdr                    colorbalance            earwax                  hwmap                   nullsrc                 setparams               tlut2
adecorrelate            asegment                colorchannelmixer       ebur128                 hwupload                ocr                     setpts                  tmedian
adelay                  aselect                 colorchart              edgedetect              hwupload_cuda           openclsrc               setrange                tmidequalizer
adenorm                 asendcmd                colorcontrast           elbg                    hysteresis              oscilloscope            setsar                  tmix
aderivative             asetnsamples            colorcorrect            entropy                 iccdetect               overlay                 settb                   tonemap
adrawgraph              asetpts                 colorhold               epx                     iccgen                  overlay_cuda            sharpness_vaapi         tonemap_opencl
adrc                    asetrate                colorize                eq                      identity                overlay_opencl          shear                   tonemap_vaapi
adynamicequalizer       asettb                  colorkey                equalizer               idet                    overlay_vaapi           showcqt                 tpad
adynamicsmooth          ashowinfo               colorkey_opencl         erosion                 il                      owdenoise               showcwt                 transpose
aecho                   asidedata               colorlevels             erosion_opencl          inflate                 pad                     showfreqs               transpose_opencl
aemphasis               asisdr                  colormap                estdif                  interlace               pad_opencl              showinfo                transpose_vaapi
aeval                   asoftclip               colormatrix             exposure                interleave              pal100bars              showpalette             treble
aevalsrc                aspectralstats          colorspace              extractplanes           join                    pal75bars               showspatial             tremolo
aexciter                asplit                  colorspace_cuda         extrastereo             kerndeint               palettegen              showspectrum            trim
afade                   ass                     colorspectrum           fade                    kirsch                  paletteuse              showspectrumpic         unpremultiply
afdelaysrc              astats                  colortemperature        feedback                ladspa                  pan                     showvolume              unsharp
afftdn                  astreamselect           compand                 fftdnoiz                lagfun                  perms                   showwaves               unsharp_opencl
afftfilt                asubboost               compensationdelay       fftfilt                 latency                 perspective             showwavespic            untile
afifo                   asubcut                 concat                  field                   lenscorrection          phase                   shuffleframes           uspp
afir                    asupercut               convolution             fieldhint               life                    photosensitivity        shufflepixels           v360
afireqsrc               asuperpass              convolution_opencl      fieldmatch              limitdiff               pixdesctest             shuffleplanes           vaguedenoiser
afirsrc                 asuperstop              convolve                fieldorder              limiter                 pixelize                sidechaincompress       varblur
aformat                 atadenoise              copy                    fifo                    loop                    pixscope                sidechaingate           vectorscope
afreqshift              atempo                  corr                    fillborders             loudnorm                pp                      sidedata                vflip
afwtdn                  atilt                   cover_rect              find_rect               lowpass                 pp7                     sierpinski              vfrdet
agate                   atrim                   crop                    firequalizer            lowshelf                premultiply             signalstats             vibrance
agraphmonitor           avectorscope            cropdetect              flanger                 lumakey                 prewitt                 signature               vibrato
ahistogram              avgblur                 crossfeed               floodfill               lut                     prewitt_opencl          silencedetect           vidstabdetect
aiir                    avgblur_opencl          crystalizer             format                  lut1d                   procamp_vaapi           silenceremove           vidstabtransform
aintegral               avsynctest              cue                     fps                     lut2                    program_opencl          sinc                    vif
ainterleave             axcorrelate             curves                  framepack               lut3d                   pseudocolor             sine                    vignette
alatency                backgroundkey           datascope               framerate               lutrgb                  psnr                    siti                    virtualbass
alimiter                bandpass                dblur                   framestep               lutyuv                  pullup                  smartblur               vmafmotion
allpass                 bandreject              dcshift                 freezedetect            lv2                     qp                      smptebars               volume
allrgb                  bass                    dctdnoiz                freezeframes            mandelbrot              random                  smptehdbars             volumedetect
allyuv                  bbox                    deband                  frei0r                  maskedclamp             readeia608              sobel                   vstack
aloop                   bench                   deblock                 frei0r_src              maskedmax               readvitc                sobel_opencl            vstack_vaapi
alphaextract            bilateral               decimate                fspp                    maskedmerge             realtime                sofalizer               w3fdif
alphamerge              bilateral_cuda          deconvolve              gblur                   maskedmin               remap                   spectrumsynth           waveform
amerge                  biquad                  dedot                   geq                     maskedthreshold         remap_opencl            speechnorm              weave
ametadata               bitplanenoise           deesser                 gradfun                 maskfun                 removegrain             split                   xbr
amix                    blackdetect             deflate                 gradients               mcdeint                 removelogo              spp                     xcorrelate
amovie                  blackframe              deflicker               graphmonitor            mcompand                repeatfields            sr                      xfade
amplify                 blend                   deinterlace_vaapi       grayworld               median                  replaygain              ssim                    xfade_opencl
amultiply               blockdetect             dejudder                greyedge                mergeplanes             reverse                 ssim360                 xmedian
anequalizer             blurdetect              delogo                  guided                  mestimate               rgbashift               stereo3d                xstack
anlmdn                  bm3d                    denoise_vaapi           haas                    metadata                rgbtestsrc              stereotools             xstack_vaapi
anlmf                   boxblur                 derain                  haldclut                midequalizer            roberts                 stereowiden             yadif
anlms                   boxblur_opencl          deshake                 haldclutsrc             minterpolate            roberts_opencl          streamselect            yadif_cuda
anoisesrc               bs2b                    deshake_opencl          hdcd                    mix                     rotate                  subtitles               yaepblur
anull                   bwdif                   despill                 headphone               monochrome              rubberband              super2xsai              yuvtestsrc
anullsink               bwdif_cuda              detelecine              hflip                   morpho                  sab                     superequalizer          zoneplate
anullsrc                cas                     dialoguenhance          highpass                movie                   scale                   surround                zoompan
apad                    ccrepack                dilation                highshelf               mpdecimate              scale2ref               swaprect                zscale

Enabled bsfs:
aac_adtstoasc           dts2pts                 filter_units            hevc_mp4toannexb        mp3_header_decompress   pcm_rechunk             trace_headers           vvc_metadata
av1_frame_merge         dump_extradata          h264_metadata           imx_dump_header         mpeg2_metadata          pgs_frame_merge         truehd_core             vvc_mp4toannexb
av1_frame_split         dv_error_marker         h264_mp4toannexb        media100_to_mjpegb      mpeg4_unpack_bframes    prores_metadata         vp9_metadata
av1_metadata            eac3_core               h264_redundant_pps      mjpeg2jpeg              noise                   remove_extradata        vp9_raw_reorder
chomp                   evc_frame_merge         hapqa_extract           mjpega_dump_header      null                    setts                   vp9_superframe
dca_core                extract_extradata       hevc_metadata           mov2textsub             opus_metadata           text2movsub             vp9_superframe_split

Enabled indevs:
alsa                    lavfi                   oss                     sndio                   xcbgrab
fbdev                   libcdio                 pulse                   v4l2

Enabled outdevs:
alsa                    caca                    fbdev                   opengl                  oss                     pulse                   sndio                   v4l2

License: nonfree and unredistributable
$ make -j32
$ make install

Display the installed versions? (yes/no): yes

ffmpeg version 6.1.1 Copyright (c) 2000-2023 the FFmpeg developers
built with gcc 11 (Ubuntu 11.4.0-1ubuntu1~22.04)
configuration: --prefix=/usr/local --arch=x86_64 --cc=gcc --cxx=g++ --disable-debug --disable-doc --disable-large-tests --disable-shared --enable-ladspa --enable-gpl --enable-libsmbclient --enable-libcdio --enable-nonfree --enable-librist --enable-openssl --enable-libxml2 --enable-libaribb24 --enable-libfreetype --enable-libfontconfig --enable-libharfbuzz --enable-libfribidi --enable-libass --enable-libwebp --enable-lcms2 --enable-opencl --enable-librubberband --enable-lv2 --enable-libpulse --enable-libfdk-aac --enable-libvorbis --enable-libopus --enable-libmysofa --enable-libvpx --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libaom --enable-librav1e --enable-libzimg --enable-libkvazaar --enable-libbluray --enable-libvidstab --enable-frei0r --enable-libsvtav1 --enable-libx264 --enable-libx265 --enable-cuda-nvcc --enable-cuda-llvm --enable-cuvid --enable-nvdec --enable-nvenc --enable-ffnvcodec --nvccflags='-gencode arch=compute_86,code=sm_86' --enable-libsrt --enable-avisynth --enable-vapoursynth --enable-libxvid --enable-libopenjpeg --enable-chromaprint --enable-libbs2b --enable-libcaca --enable-libgme --enable-libmodplug --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtwolame --enable-libv4l2 --enable-libvo-amrwbenc --enable-libzvbi --enable-lto --enable-opengl --enable-pic --enable-pthreads --enable-small --enable-rpath --enable-libssh --enable-static --enable-libtesseract --enable-version3 --enable-libzimg --extra-cflags='-O3 -pipe -fPIC -march=native -flto -DCL_TARGET_OPENCL_VERSION=300 -DX265_DEPTH=12 -DENABLE_LIBVMAF=0' --extra-cxxflags='-O3 -pipe -fPIC -march=native -flto -DCL_TARGET_OPENCL_VERSION=300 -DX265_DEPTH=12 -DENABLE_LIBVMAF=0' --extra-libs='-ldl -lpthread -lm -lz' --pkg-config-flags=--static --pkg-config=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config --pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig --strip=/usr/bin/strip
libavutil      58. 29.100 / 58. 29.100
libavcodec     60. 31.102 / 60. 31.102
libavformat    60. 16.100 / 60. 16.100
libavdevice    60.  3.100 / 60.  3.100
libavfilter     9. 12.100 /  9. 12.100
libswscale      7.  5.100 /  7.  5.100
libswresample   4. 12.100 /  4. 12.100
libpostproc    57.  3.100 / 57.  3.100

ffprobe version 6.1.1 Copyright (c) 2007-2023 the FFmpeg developers
built with gcc 11 (Ubuntu 11.4.0-1ubuntu1~22.04)
configuration: --prefix=/usr/local --arch=x86_64 --cc=gcc --cxx=g++ --disable-debug --disable-doc --disable-large-tests --disable-shared --enable-ladspa --enable-gpl --enable-libsmbclient --enable-libcdio --enable-nonfree --enable-librist --enable-openssl --enable-libxml2 --enable-libaribb24 --enable-libfreetype --enable-libfontconfig --enable-libharfbuzz --enable-libfribidi --enable-libass --enable-libwebp --enable-lcms2 --enable-opencl --enable-librubberband --enable-lv2 --enable-libpulse --enable-libfdk-aac --enable-libvorbis --enable-libopus --enable-libmysofa --enable-libvpx --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libaom --enable-librav1e --enable-libzimg --enable-libkvazaar --enable-libbluray --enable-libvidstab --enable-frei0r --enable-libsvtav1 --enable-libx264 --enable-libx265 --enable-cuda-nvcc --enable-cuda-llvm --enable-cuvid --enable-nvdec --enable-nvenc --enable-ffnvcodec --nvccflags='-gencode arch=compute_86,code=sm_86' --enable-libsrt --enable-avisynth --enable-vapoursynth --enable-libxvid --enable-libopenjpeg --enable-chromaprint --enable-libbs2b --enable-libcaca --enable-libgme --enable-libmodplug --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtwolame --enable-libv4l2 --enable-libvo-amrwbenc --enable-libzvbi --enable-lto --enable-opengl --enable-pic --enable-pthreads --enable-small --enable-rpath --enable-libssh --enable-static --enable-libtesseract --enable-version3 --enable-libzimg --extra-cflags='-O3 -pipe -fPIC -march=native -flto -DCL_TARGET_OPENCL_VERSION=300 -DX265_DEPTH=12 -DENABLE_LIBVMAF=0' --extra-cxxflags='-O3 -pipe -fPIC -march=native -flto -DCL_TARGET_OPENCL_VERSION=300 -DX265_DEPTH=12 -DENABLE_LIBVMAF=0' --extra-libs='-ldl -lpthread -lm -lz' --pkg-config-flags=--static --pkg-config=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config --pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig --strip=/usr/bin/strip
libavutil      58. 29.100 / 58. 29.100
libavcodec     60. 31.102 / 60. 31.102
libavformat    60. 16.100 / 60. 16.100
libavdevice    60.  3.100 / 60.  3.100
libavfilter     9. 12.100 /  9. 12.100
libswscale      7.  5.100 /  7.  5.100
libswresample   4. 12.100 /  4. 12.100
libpostproc    57.  3.100 / 57.  3.100

ffplay version 4.4.2-0ubuntu0.22.04.1+esm3 Copyright (c) 2003-2021 the FFmpeg developers
built with gcc 11 (Ubuntu 11.4.0-1ubuntu1~22.04)
configuration: --prefix=/usr --extra-version=0ubuntu0.22.04.1+esm3 --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --enable-gnutls --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libcodec2 --enable-libdav1d --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libgme --enable-libgsm --enable-libjack --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libpulse --enable-librabbitmq --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libssh --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzmq --enable-libzvbi --enable-lv2 --enable-omx --enable-openal --enable-opencl --enable-opengl --enable-sdl2 --enable-pocketsphinx --enable-librsvg --enable-libmfx --enable-libdc1394 --enable-libdrm --enable-libiec61883 --enable-chromaprint --enable-frei0r --enable-libx264 --enable-shared
libavutil      56. 70.100 / 56. 70.100
libavcodec     58.134.100 / 58.134.100
libavformat    58. 76.100 / 58. 76.100
libavdevice    58. 13.100 / 58. 13.100
libavfilter     7.110.100 /  7.110.100
libswscale      5.  9.100 /  5.  9.100
libswresample   3.  9.100 /  3.  9.100
libpostproc    55.  9.100 / 55.  9.100


Do you want to clean up the build files? (yes/no): no

[INFO] Make sure to star this repository to show your support!
[INFO] https://github.com/slyfox1186/script-repo
```
