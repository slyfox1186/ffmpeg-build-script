# FFmpeg Build Script Guide

If you find this script useful, please $\textcolor{yellow}{\textsf{★}}$ this project!

## Introduction

This guide helps you to build a static FFmpeg binary with both non-free and GPL codecs using our FFmpeg build script. It simplifies the process by downloading the latest version of each required repository.

**Supported Operating Systems:**
- Arch Linux
- Debian (Versions 11 and 12)
- Ubuntu (Versions 20, 22, 23.04)

### Legal Disclaimer and Data Privacy

The script downloads packages under various licenses from different sources, which might track your usage. Please be aware that some of these sources are beyond our control.

**Important:**
- The script allows the creation of a **non-free** binary. By using this script, you acknowledge this fact and assume all associated risks.
- This is a community-supported project and support is limited to Debian-based and Arch Linux systems.
- To ensure compliance with all applicable laws and intellectual property rights, you may need to perform additional research. For a GPL-compliant build, omit `--enable-gpl-and-non-free` from the script arguments.

## Installation

### Standard Installation

To build FFmpeg with GPL and non-free codecs:

1. Clone the repository:
```bash
git clone https://github.com/slyfox1186/ffmpeg-build-script.git
cd ffmpeg-build-script || exit
sudo bash build-ffmpeg.sh --build --enable-gpl-and-non-free --latest
```

### NDI Support

The **NDI build script** offers functionality not officially supported by FFmpeg or NDI developers. Use it within legal boundaries and at your own risk.

You can find the NDI build script on my other GitHub project [script-repo](https://github.com/slyfox1186/script-repo/blob/main/Bash/Installer%20Scripts/FFmpeg/build-ffmpeg-NDI)

## Supported Codecs and Features

This script supports a wide range of codecs and features, including x264, x265, CUDA for Nvidia hardware acceleration, and many others. For a complete list, please refer to the [FFmpeg Legal Documents](https://ffmpeg.org/legal.html).

* `alsa`: Advanced Linux Sound Architecture (ALSA) project. A library to interface with ALSA in the Linux kernel and virtual devices using a plugin system
* `aom`: AV1 Video Codec (Experimental and very slow!)
* `avisynth`: A powerful tool for video post-production
* `bzlib` A general-purpose data compression library
* `chromaprint`: Is an audio fingerprinting library that calculates fingerprints used by the Acoustid service. It's the core component of the AcoustID project.
* `cuda`: Hardware acceleration for Nvidia graphics cards
* `dav1d`: Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities and sponsored by the AOMedia (only available if `meson` and `ninja` are installed)
* `DeckLink`: DeckLink cards are open standard capture cards and are perfect for the development of Linux based video applications
* `ff-nvcodec-headers`: FFmpeg version of headers required to interface with Nvidias codec APIs (Hardware Acceleration)
* `flac`: Free Lossless Audio Codec is open-source software that can reduce the amount of storage space needed to store digital audio signals without needing to remove information in doing so
* `fontconfig`: Font configuration and customization library
* `freetype`: A freely available software library to render fonts
* `frei0r` A collection of free and open source video effects plugins that can be used with a variety of video editing and processing software
* `fribidi`: The Free Implementation of the Unicode Bidirectional Algorithm
* `harfbuzz`: Text shaping image processor
* `iconv`: Used to convert some text in one encoding into another encoding
* `jxl`: JPEG XL offers significantly better image quality and compression ratios than legacy JPEG, plus a shorter specification
* `kvazaar`: An open-source HEVC encoder licensed under 3-clause BSD
* `ladspa`: Is an acronym for Linux Audio Developer's Simple Plugin API
* `lcms2`: A free, open-source, CMM engine. It provides fast transforms between ICC profiles
* `libaribb24`: A library for ARIB STD-B24, decoding JIS 8 bit characters and parsing MPEG-TS stream
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format
* `libbluray`: An open-source library designed for Blu-Ray Discs playback
* `libbs2b`: Is designed to improve headphone listening of stereo audio records
* `libcaca`: Is a graphics library that outputs text instead of pixels, so that it can work on older video cards or text terminals
* `libcdio`: Is a library for CD-ROM and CD image access
* `libfdk_aac`: Fraunhofer FDK AAC Codec
* `libflite`: Provides a high-level text-to-speech interface for English based on the 'libflite' library
* `libgme`: Is a collection of video game music file emulators
* `libmodplug`: A library which was part of the Modplug-xmms project: http://modplug-xmms.sf.net/
* `libmp3lame`: MPEG-1 or MPEG-2 Audio Layer III
* `libmysofa`: Is a simple set of C functions to read AES SOFA files, if they contain HRTFs stored according to the AES69-2015 standard
* `libopencore_amr`: OpenCORE Adaptive Multi-Rate (AMR) speech codec library implementation
* `libopus`: Lossy audio coding format
* `libpulse`: A featureful, general-purpose sound server
* `librubberband`: An audio time-stretching and pitch-shifting library and utility program
* `libshine`: Shine is a fixed-point MP3 encoder. It has a far better performance on platforms without an FPU, e.g. armel CPUs, and some phones and tablets
* `libsmbclient`: Is a library toolset that permits applications to manipulate CIFS/SMB network resources using many of the standards POSIX functions available for manipulating local UNIX/Linux files
* `libsnappy`: Snappy is a compression/decompression library
* `libsoxr`: The SoX Resampler library `libsoxr' performs one-dimensional sample-rate conversion
* `libspeex`: Is an Open Source/Free Software patent-free audio compression format designed for speech
* `libssh`: Is a multiplatform C library implementing the SSHv2 protocol on the client and server side
* `libtesseract`: This package contains an OCR engine - libtesseract and a command line program - tesseract
* `libtiff`: This software provides support for the Tag Image File Format (TIFF), a widely used format for storing image data
* `libtwolame`: Is an optimized MPEG Audio Layer 2 (MP2) encoder based on tooLAME by Mike Cheng, which in turn is based upon the ISO dist10 code and portions of LAME
* `libv4l2`: Is a collection of libraries that adds a thin abstraction layer on top of video4linux2 devices
* `libvo_amrwbenc`: This library contains an encoder implementation of the Adaptive Multi-Rate Wideband (AMR-WB) audio codec
* `libxvid`: Xvid MPEG-4 Part 2 encoder wrapper
* `libzimg`: The "z" library implements the commonly required image processing basics of scaling, colorspace conversion, and depth conversion
* `lv2`: Is an extensible open standard for audio plugins
* `lzma`: Is an algorithm used to perform lossless data compression
* `mediainfo`: A convenient unified display of the most relevant technical and tag data for video and audio files
* `mp4box/gpac`: Modular Multimedia framework for packaging, streaming, and playing your favorite content, see http://netflix.gpac.io
* `ogg`: Free, open container format
* `opencl`: An open-source project that uses Boost. Compute as a high-level C++ wrapper over the OpenCL API
* `opencore-amr`: Adaptive Multi-Rate (AMR) speech codec library implementation
* `opengl`: Is a cross-language, cross-platform application programming interface for rendering 2D and 3D vector graphics
* `openjpeg`: Is an open-source JPEG 2000 codec written in C language
* `openssl`: Is a software library for applications that provide secure communications over computer networks against eavesdropping, and identify the party at the other end
* `rav1e`: rust based AV1 encoder
* `sdl2`: A cross-platform development library designed to provide low-level access to audio, keyboard, mouse, joystick, and graphics hardware via OpenGL and Direct3D
* `sndio`: Is a small audio and MIDI framework part of the OpenBSD project and ported to FreeBSD, Linux and NetBSD
* `srt`: Secure Reliable Transport (SRT) is a transport protocol for ultra-low (sub-second) latency live video and audio streaming, as well as for generic bulk data transfer
* `svtav1`: SVT-AV1 Encoder and Decoder
* `theora`: Free lossy video compression format
* `vapoursynth`: An application for video manipulation.
* `vidstab`: A video stabilization library which can be plugged in with Ffmpeg and Transcode
* `vorbis`: Lossy audio compression format
* `vpx`: VP8 / VP9 Video Codec for the WebM video file format
* `webp`: Image format both lossless and lossy
* `x264`: H.264 Video Codec (MPEG-4 AVC)
* `x265`: H.265 Video Codec (HEVC)
* `xcb`: A C language interface to the X Window System protocol, which replaces the traditional Xlib interface
* `xlib`: Is a C subroutine library that application programs (clients) use to interface with the window system by means of a stream connection
* `xml2`: XML parser and toolkit
* `xvidcore`: MPEG-4 video coding standard
* `zlib`: Is a general-purpose data compression library


### Hardware Acceleration

#### The script provides options for hardware acceleration using Nvidia's CUDA SDK Toolkit or AMD's AMF. Make sure to follow the installation instructions closely to enable these features.

 - [CUDA SDK Toolkit Download](https://developer.nvidia.com/cuda-downloads)
 - Follow the script's instructions to install the latest updates.
 - These encoders/decoders will only be available if a CUDA installation was found while building ffmpeg.
   * Decoders
        * H264 `h264_cuvid`
        * H265 `hevc_cuvid`
        * Motion JPEG `mjpeg_cuvid`
        * MPEG1 video `mpeg1_cuvid`
        * MPEG2 video `mpeg2_cuvid`
        * MPEG4 part 2 video `mepg4_cuvid`
        * VC-1 `vc1_cuvid`
        * VP8 `vp8_cuvid`
        * VP9 `vp9_cuvid`
    * Encoders
        * H264 `nvenc_h264`
        * H265 `nvenc_hevc`
**vaapi**: [Video Acceleration API](https://trac.ffmpeg.org/wiki/Hardware/VAAPI). These encoders/decoders will only be
  available if a libva driver installation was found while building the binary. Follow [these](#Vaapi-installation)
  instructions for installation.
    * Encoders
        * H264 `h264_vaapi`
        * H265 `hevc_vaapi`
        * Motion JPEG `mjpeg_vaapi`
        * MPEG2 video `mpeg2_vaapi`
        * VP8 `vp8_vaapi`
        * VP9 `vp9_vaapi`
**AMF**: [AMD's Advanced Media Framework](https://github.com/GPUOpen-LibrariesAndSDKs/AMF).
  These encoders will only be available if `amdgpu` drivers are detected during the build.
    * Encoders
        * H264 `h264_amf`

## Requirements

The script is designed to handle all necessary package downloads automatically. Ensure your system meets the supported operating systems criteria for a smooth installation process.

Example Output
-------

```bash
 ------------------------------
|                              |
| FFmpeg Build Script - v3.5.2 |
|                              |
 ------------------------------

[INFO] Utilizing 32 CPU threads
[WARNING] With GPL and non-free codecs enabled

Installing the required APT packages
========================================================
[INFO] Checking installation status of each package...
[INFO] No missing packages to install or all missing packages are unavailable.

Checking GPU Status
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
Downloading "https://ftp.gnu.org/gnu/m4/m4-latest.tar.xz" saving as "m4-latest.tar.xz"
Download Completed
File extracted: m4-latest.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-nls --enable-c++ --enable-threads=posix
$ make -j32
$ make install

Building autoconf - version latest
========================================================
Downloading "http://ftp.gnu.org/gnu/autoconf/autoconf-latest.tar.xz" saving as "autoconf-latest.tar.xz"
Download Completed
File extracted: autoconf-latest.tar.xz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building libtool - version 2.4.7
========================================================
Downloading "https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz" saving as "libtool-2.4.7.tar.xz"
Download Completed
File extracted: libtool-2.4.7.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pic M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building pkg-config - version 0.29.2
========================================================
Downloading "https://pkgconfig.freedesktop.org/releases/pkg-config-0.29.2.tar.gz" saving as "pkg-config-0.29.2.tar.gz"
Download Completed
File extracted: pkg-config-0.29.2.tar.gz

$ autoconf
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-silent-rules --with-pc-path=/home/jman/tmp/ffmpeg-build-script/workspace/lib64/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/lib/x86_64-linux-gnu/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/share/pkgconfig:/usr/local/lib64/pkgconfig:/usr/local/lib/x86_64-linux-gnu/pkgconfig:/usr/local/lib/pkgconfig:/usr/local/share/pkgconfig:/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/share/pkgconfig:/lib64/pkgconfig:/lib/x86_64-linux-gnu/pkgconfig:/lib/pkgconfig
$ make -j32
$ make install

Building meson - version 1.3.2
========================================================
Downloading "https://github.com/mesonbuild/meson/archive/refs/tags/1.3.2.tar.gz" saving as "meson-1.3.2.tar.gz"
Download Completed
File extracted: meson-1.3.2.tar.gz

$ python3 setup.py build
$ python3 setup.py install --prefix=/home/jman/tmp/ffmpeg-build-script/workspace

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

Building yasm - version 1.3.0
========================================================
Downloading "https://github.com/yasm/yasm/archive/refs/tags/v1.3.0.tar.gz" saving as "yasm-1.3.0.tar.gz"
Download Completed
File extracted: yasm-1.3.0.tar.gz

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building nasm - version 2.16.01
========================================================
2.16.01
Downloading "https://www.nasm.us/pub/nasm/stable/nasm-2.16.01.tar.xz" saving as "nasm-2.16.01.tar.xz"
Download Completed
File extracted: nasm-2.16.01.tar.xz

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

Building libxml2 - version 2.11.7
========================================================
Downloading "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v2.11.7/libxml2-v2.11.7.tar.bz2" saving as "libxml2-2.11.7.tar.bz2"
Download Completed
File extracted: libxml2-2.11.7.tar.bz2

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja
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
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --with-pic
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

Building harfbuzz - version 8.3.0
========================================================
Downloading "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/8.3.0.tar.gz" saving as "harfbuzz-8.3.0.tar.gz"
Download Completed
File extracted: harfbuzz-8.3.0.tar.gz

$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbenchmark=disabled -Dcairo=disabled -Ddocs=disabled -Dglib=disabled -Dgobject=disabled -Dicu=disabled -Dintrospection=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -C build install

Building c2man-git - version 577ed40
========================================================
Cloning "c2man-git" saving version "577ed40"
Cloning completed: 577ed40
$ ./Configure -desO -D bin=/home/jman/tmp/ffmpeg-build-script/workspace/bin -D cc=/usr/bin/cc -D d_gnu=/usr/lib/x86_64-linux-gnu -D gcc=/usr/bin/gcc -D installmansrc=/home/jman/tmp/ffmpeg-build-script/workspace/share/man -D ldflags=-L/home/jman/tmp/ffmpeg-build-script/workspace/lib64 -L/home/jman/tmp/ffmpeg-build-script/workspace/lib -DLIBXML_STATIC -D libpth=/usr/lib64 /usr/lib /lib64 /lib -D locincpth=/home/jman/tmp/ffmpeg-build-script/workspace/include /usr/local/include /usr/include -D loclibpth=/home/jman/tmp/ffmpeg-build-script/workspace/lib64 /home/jman/tmp/ffmpeg-build-script/workspace/lib /usr/local/lib64 /usr/local/lib -D osname=Debian -D prefix=/home/jman/tmp/ffmpeg-build-script/workspace -D privlib=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man -D privlibexp=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man
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

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DFREEGLUT_BUILD_SHARED_LIBS=OFF -DFREEGLUT_BUILD_STATIC_LIBS=ON -DFREEGLUT_PRINT_ERRORS=OFF -DFREEGLUT_PRINT_WARNINGS=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libwebp-git - version 1.3.2
========================================================
Cloning "libwebp-git" saving version "1.3.2"
Cloning completed: 1.3.2
$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DZLIB_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DWEBP_BUILD_ANIM_UTILS=OFF -DWEBP_BUILD_CWEBP=ON -DWEBP_BUILD_DWEBP=ON -DWEBP_BUILD_EXTRAS=OFF -DWEBP_BUILD_VWEBP=OFF -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libhwy - version 1.1.0
========================================================
Downloading "https://github.com/google/highway/archive/refs/tags/1.1.0.tar.gz" saving as "libhwy-1.1.0.tar.gz"
Download Completed
File extracted: libhwy-1.1.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DHWY_ENABLE_TESTS=OFF -DBUILD_TESTING=OFF -DHWY_ENABLE_EXAMPLES=OFF -DHWY_FORCE_STATIC_LIBS=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building brotli - version 1.1.0
========================================================
Downloading "https://github.com/google/brotli/archive/refs/tags/v1.1.0.tar.gz" saving as "brotli-1.1.0.tar.gz"
Download Completed
File extracted: brotli-1.1.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building lcms2 - version 2.16
========================================================
Downloading "https://github.com/mm2/Little-CMS/archive/refs/tags/lcms2.16.tar.gz" saving as "lcms2-2.16.tar.gz"
Download Completed
File extracted: lcms2-2.16.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pic --with-threaded
$ make -j32
$ make install

Building gflags - version 2.2.2
========================================================
Downloading "https://github.com/gflags/gflags/archive/refs/tags/v2.2.2.tar.gz" saving as "gflags-2.2.2.tar.gz"
Download Completed
File extracted: gflags-2.2.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_gflags_LIB=ON -DBUILD_STATIC_LIBS=ON -DINSTALL_HEADERS=ON -DREGISTER_BUILD_DIR=ON -DREGISTER_INSTALL_PREFIX=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building opencl-sdk-git - version 1.3.2
========================================================
Cloning "opencl-sdk-git" saving version "1.3.2"
Cloning completed: 2023.12.14
$ cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -DBUILD_DOCS=OFF -DBUILD_EXAMPLES=OFF -DOPENCL_SDK_BUILD_SAMPLES=ON -DOPENCL_SDK_TEST_SAMPLES=OFF -DCMAKE_C_FLAGS=-g -O3 -march=native -DNOLIBTOOL -DFREEGLUT_STATIC -DHWY_COMPILE_ALL_ATTAINABLE -DCMAKE_CXX_FLAGS=-g -O3 -march=native -DHWY_COMPILE_ALL_ATTAINABLE -DOPENCL_HEADERS_BUILD_CXX_TESTS=OFF -DOPENCL_ICD_LOADER_BUILD_SHARED_LIBS=ON -DOPENCL_SDK_BUILD_OPENGL_SAMPLES=OFF -DOPENCL_SDK_BUILD_SAMPLES=OFF -DOPENCL_SDK_TEST_SAMPLES=OFF -DTHREADS_PREFER_PTHREAD_FLAG=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building leptonica - version 1.84.1
========================================================
Downloading "https://github.com/DanBloomberg/leptonica/archive/refs/tags/1.84.1.tar.gz" saving as "leptonica-1.84.1.tar.gz"
Download Completed
File extracted: leptonica-1.84.1.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pic
$ make -j32
$ make install

Building tesseract - version 5.3.4
========================================================
Downloading "https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.3.4.tar.gz" saving as "tesseract-5.3.4.tar.gz"
Download Completed
File extracted: tesseract-5.3.4.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-doc --with-extra-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-extra-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-pic --without-archive --without-curl
$ make -j32
$ make install

Building jpeg-turbo-git - version 575eddd
========================================================
Cloning "jpeg-turbo-git" saving version "575eddd"
Cloning completed: 575eddd
$ cmake -S . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_SHARED=ON -DENABLE_STATIC=ON -G Ninja
$ ninja -j32
$ ninja -j32 install
build-ffmpeg.sh: line 1925: jpeg-turbo-git: command not found

Building rubberband-git - version 6c80b8d
========================================================
Cloning "rubberband-git" saving version "6c80b8d"
Cloning completed: 6c80b8d
$ make -j32 PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install-static

Building c-ares - version 1.27.0
========================================================
Downloading "https://github.com/c-ares/c-ares/archive/refs/tags/cares-1_27_0.tar.gz" saving as "c-ares-1_27_0.tar.gz"
Download Completed
File extracted: c-ares-1_27_0.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-debug --disable-warnings --with-pic
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
  Using cached lxml-5.1.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (8.1 MB)
Collecting Markdown
  Using cached Markdown-3.5.2-py3-none-any.whl (103 kB)
Collecting Pygments
  Using cached pygments-2.17.2-py3-none-any.whl (1.2 MB)
Collecting rdflib
  Using cached rdflib-7.0.0-py3-none-any.whl (531 kB)
Collecting isodate<0.7.0,>=0.6.0
  Using cached isodate-0.6.1-py2.py3-none-any.whl (41 kB)
Collecting pyparsing<4,>=2.1.0
  Using cached pyparsing-3.1.2-py3-none-any.whl (103 kB)
Collecting six
  Using cached six-1.16.0-py2.py3-none-any.whl (11 kB)
Installing collected packages: six, pyparsing, Pygments, Markdown, lxml, isodate, rdflib
Successfully installed Markdown-3.5.2 Pygments-2.17.2 isodate-0.6.1 lxml-5.1.0 pyparsing-3.1.2 rdflib-7.0.0 six-1.16.0
Deactivating the virtual environment...
Python virtual environment setup and package installation completed.
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Donline_docs=false -Dplugins=disabled -Dtests=disabled
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
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-static --with-cpu=x86-64
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

Building sdl2-git - version b9ab326
========================================================
Cloning "sdl2-git" saving version "b9ab326"
Cloning completed: b9ab326
$ cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DSDL_ALSA_SHARED=OFF -DSDL_DISABLE_INSTALL_DOCS=ON -DSDL_CCACHE=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libsndfile - version 1.2.2
========================================================
Downloading "https://github.com/libsndfile/libsndfile/releases/download/1.2.2/libsndfile-1.2.2.tar.xz" saving as "libsndfile-1.2.2.tar.xz"
Download Completed
File extracted: libsndfile-1.2.2.tar.xz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-static --with-pic --with-pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig
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
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -DCPACK_BINARY_DEB=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libflac - version 1.4.3
========================================================
Downloading "https://github.com/xiph/flac/archive/refs/tags/1.4.3.tar.gz" saving as "libflac-1.4.3.tar.gz"
Download Completed
File extracted: libflac-1.4.3.tar.gz

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DINSTALL_CMAKE_CONFIG_MODULE=ON -DINSTALL_MANPAGES=OFF -DBUILD_CXXLIBS=ON -DBUILD_PROGRAMS=ON -DWITH_ASM=ON -DWITH_AVX=ON -DWITH_FORTIFY_SOURCE=ON -DWITH_STACK_PROTECTOR=ON -DWITH_OGG=ON -DENABLE_64_BIT_WORDS=ON -DBUILD_DOCS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF -G Ninja
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
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DOGG_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DOGG_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libogg.so -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building opus - version 1.5.1
========================================================
Downloading "https://github.com/xiph/opus/archive/refs/tags/v1.5.1.tar.gz" saving as "opus-1.5.1.tar.gz"
Download Completed
File extracted: opus-1.5.1.tar.gz

$ autoreconf -fis
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libmysofa - version 1.3.2
========================================================
Downloading "https://github.com/hoene/libmysofa/archive/refs/tags/v1.3.2.tar.gz" saving as "libmysofa-1.3.2.tar.gz"
Download Completed
File extracted: libmysofa-1.3.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building libvpx - version 1.14.0
========================================================
Downloading "https://github.com/webmproject/libvpx/archive/refs/tags/v1.14.0.tar.gz" saving as "libvpx-1.14.0.tar.gz"
Download Completed
File extracted: libvpx-1.14.0.tar.gz

$ sed -i s/#include "\.\/vpx_tpl\.h"/#include ".\/vpx\/vpx_tpl.h"/ vpx/vpx_ext_ratectrl.h
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --as=yasm --disable-unit-tests --disable-shared --disable-examples --enable-small --enable-multi-res-encoding --enable-webm-io --enable-libyuv --enable-vp8 --enable-vp9 --enable-postproc --enable-vp9-postproc --enable-better-hw-compatibility --enable-vp9-highbitdepth
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
Downloading "https://zenlayer.dl.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz" saving as "lame-3.100.tar.gz"
Download Completed
File extracted: lame-3.100.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --disable-gtktest --enable-nasm --with-libiconv-prefix=/usr
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
$ curl -sSLo config.guess https://raw.githubusercontent.com/gcc-mirror/gcc/master/config.guess
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-examples --disable-oggtest --disable-sdltest --disable-vorbistest --with-ogg=/home/jman/tmp/ffmpeg-build-script/workspace --with-ogg-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-ogg-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-vorbis=/home/jman/tmp/ffmpeg-build-script/workspace --with-vorbis-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-vorbis-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-pic
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Video Tools |
|                        |
 ------------------------

Building av1-git - version 3.8.1
========================================================
Cloning "av1-git" saving version "3.8.1"
Cloning completed: 3.8.1
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCONFIG_AV1_DECODER=1 -DCONFIG_AV1_ENCODER=1 -DCONFIG_AV1_HIGHBITDEPTH=1 -DCONFIG_AV1_TEMPORAL_DENOISING=1 -DCONFIG_DENOISE=1 -DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1 -DENABLE_CCACHE=1 -DENABLE_EXAMPLES=0 -DENABLE_TESTS=0 -G Ninja /home/jman/tmp/ffmpeg-build-script/packages/av1
$ ninja -j32 -C build
$ ninja -C build install

Building rav1e - version 0.7.1
========================================================
Installing RustUp
[INFO] cargo-c is already installed.
Downloading "https://github.com/xiph/rav1e/archive/refs/tags/v0.7.1.tar.gz" saving as "rav1e-0.7.1.tar.gz"
Download Completed
File extracted: rav1e-0.7.1.tar.gz

$ cargo cinstall --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --library-type=staticlib --crt-static --release

Building avif - version 1.0.4
========================================================
Downloading "https://github.com/AOMediaCodec/libavif/archive/refs/tags/v1.0.4.tar.gz" saving as "avif-1.0.4.tar.gz"
Download Completed
File extracted: avif-1.0.4.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DAVIF_CODEC_AOM=ON -DAVIF_CODEC_AOM_DECODE=ON -DAVIF_CODEC_AOM_ENCODE=ON -DAVIF_ENABLE_GTEST=OFF -DAVIF_ENABLE_WERROR=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building kvazaar-git - version 2.3.0
========================================================
Cloning "kvazaar-git" saving version "2.3.0"
Cloning completed: 2.3.0
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

Building libbluray - version 1.3.4
========================================================
Downloading "https://code.videolan.org/videolan/libbluray/-/archive/1.3.4/1.3.4.tar.gz" saving as "libbluray-1.3.4.tar.gz"
Download Completed
File extracted: libbluray-1.3.4.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-doxygen-doc --disable-doxygen-dot --disable-doxygen-html --disable-doxygen-ps --disable-doxygen-pdf --disable-examples --disable-extra-warnings --disable-shared --without-libxml2
$ make -j32
$ make install

Building zenlib - version 0.4.41
========================================================
Downloading "https://github.com/MediaArea/ZenLib/archive/refs/tags/v0.4.41.tar.gz" saving as "zenlib-0.4.41.tar.gz"
Download Completed
File extracted: zenlib-0.4.41.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfo-lib - version 24.01
========================================================
Downloading "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v24.01.tar.gz" saving as "mediainfo-lib-24.01.tar.gz"
Download Completed
File extracted: mediainfo-lib-24.01.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfo-cli - version 24.01.1
========================================================
Downloading "https://github.com/MediaArea/MediaInfo/archive/refs/tags/v24.01.1.tar.gz" saving as "mediainfo-cli-24.01.1.tar.gz"
Download Completed
File extracted: mediainfo-cli-24.01.1.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-staticlibs --disable-shared
$ make -j32
$ make install
$ cp -f /home/jman/tmp/ffmpeg-build-script/packages/mediainfo-cli-24.01.1/Project/GNU/CLI/mediainfo /usr/local/bin/

Building vid-stab - version 1.1.1
========================================================
Downloading "https://github.com/georgmartius/vid.stab/archive/refs/tags/v1.1.1.tar.gz" saving as "vid-stab-1.1.1.tar.gz"
Download Completed
File extracted: vid-stab-1.1.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DUSE_OMP=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building frei0r - version 2.3.2
========================================================
Downloading "https://github.com/dyne/frei0r/archive/refs/tags/v2.3.2.tar.gz" saving as "frei0r-2.3.2.tar.gz"
Download Completed
File extracted: frei0r-2.3.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DWITHOUT_OPENCV=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building gpac-git - version 2.2.1
========================================================
Cloning "gpac-git" saving version "2.2.1"
Cloning completed: 2.2.1
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --static-bin --static-modules --use-a52=local --use-faad=local --use-freetype=local --use-mad=local --sdl-cfg=/home/jman/tmp/ffmpeg-build-script/workspace/include/SDL3
$ make -j32
$ make install
$ cp -f bin/gcc/MP4Box /usr/local/

Building svt-av1 - version 1.8.0
========================================================
Downloading "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.8.0/SVT-AV1-v1.8.0.tar.bz2" saving as "svt-av1-1.8.0.tar.bz2"
Download Completed
File extracted: svt-av1-1.8.0.tar.bz2

$ cmake -S . -B Build/linux -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_APPS=OFF -DBUILD_DEC=ON -DBUILD_ENC=ON -DBUILD_TESTING=OFF -DENABLE_AVX512=OFF -DENABLE_NASM=ON -DNATIVE=ON -G Ninja
$ ninja -j32 -C Build/linux
$ ninja -j32 -C Build/linux install

Building x264 - version be4f0200
========================================================
Downloading "https://code.videolan.org/videolan/x264/-/archive/be4f0200ed007c466fd96185c39cde2a2d60ef50/x264-be4f0200ed007c466fd96185c39cde2a2d60ef50.tar.bz2" saving as "x264-be4f0200.tar.bz2"
Download Completed
File extracted: x264-be4f0200.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --bit-depth=all --chroma-format=all --enable-debug --enable-gprof --enable-lto --enable-pic --enable-static --enable-strip CFLAGS=-g -O3 -march=native -DNOLIBTOOL -DFREEGLUT_STATIC -DHWY_COMPILE_ALL_ATTAINABLE -I/home/jman/tmp/ffmpeg-build-script/workspace/include/serd-0 -fPIC CXXFLAGS=-g -O3 -march=native -DHWY_COMPILE_ALL_ATTAINABLE
$ make -j32
$ make install
$ make install-lib-static

Building x265 - version 3.5
========================================================
Downloading "https://bitbucket.org/multicoreware/x265_git/downloads/x265_3.5.tar.gz" saving as "x265-3.5.tar.gz"
Download Completed
File extracted: x265-3.5.tar.gz

$ making 12bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_LIBVMAF=OFF -DENABLE_CLI=OFF -DENABLE_SHARED=OFF -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DNATIVE_BUILD=ON -DMAIN12=ON -G Ninja -Wno-dev
$ ninja -j32
$ making 10bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DENABLE_LIBVMAF=OFF -DENABLE_CLI=OFF -DENABLE_HDR10_PLUS=ON -DENABLE_SHARED=OFF -DEXPORT_C_API=OFF -DHIGH_BIT_DEPTH=ON -DNATIVE_BUILD=ON -DNUMA_ROOT_DIR=/usr -G Ninja -Wno-dev
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

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DENABLE_APPS=OFF -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DUSE_STATIC_LIBSTDCXX=ON -G Ninja
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
  Using cached Cython-0.29.36-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (1.9 MB)
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
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DABSL_ENABLE_INSTALL=ON -DABSL_PROPAGATE_CXX_STD=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INSTALL_SBINDIR=sbin -DLIBGAV1_ENABLE_TESTS=OFF -G Ninja
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

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DAOM_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DAOM_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libaom.a -DLIBDE265_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DLIBDE265_LIBRARY=/usr/lib/x86_64-linux-gnu/libde265.so -DLIBSHARPYUV_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include/webp -DLIBSHARPYUV_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib/libsharpyuv.so -DWITH_AOM_DECODER=ON -DWITH_AOM_ENCODER=ON -DWITH_DAV1D=OFF -DWITH_EXAMPLES=OFF -DWITH_GDK_PIXBUF=ON -DWITH_LIBDE265=ON -DWITH_X265=OFF -DWITH_LIBSHARPYUV=ON -DWITH_REDUCED_VISIBILITY=OFF -DWITH_SvtEnc=OFF -DWITH_SvtEnc_PLUGIN=OFF -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

Building openjpeg - version 2.5.2
========================================================
Downloading "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/v2.5.2" saving as "openjpeg-2.5.2.tar.gz"
Download Completed
File extracted: openjpeg-2.5.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DBUILD_THIRDPARTY=ON -G Ninja
$ ninja -j32 -C build
$ ninja -C build install

 -----------------
|                 |
| Building FFmpeg |
|                 |
 -----------------

[UPDATE] The current installed version of FFmpeg: Not installed
[UPDATE] The latest release version of FFmpeg: n6.1.1

Building ffmpeg-git - version n6.1.1
========================================================
Cloning "ffmpeg-git" saving version "n6.1.1"
Cloning completed: n6.1.1
install prefix            /usr/local
source path               /home/jman/tmp/ffmpeg-build-script/packages/ffmpeg
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
alsa                    libaribb24              libfribidi              libopus                 libspeex                libvo_amrwbenc          libxvid
avisynth                libass                  libgme                  libpulse                libsrt                  libvorbis               libzvbi
bzlib                   libbluray               libkvazaar              librav1e                libssh                  libvpx                  lv2
chromaprint             libbs2b                 libmodplug              librubberband           libsvtav1               libwebp                 lzma
frei0r                  libcaca                 libmp3lame              libshine                libtesseract            libx264                 opengl
iconv                   libcdio                 libmysofa               libsmbclient            libtheora               libx265                 openssl
ladspa                  libfdk_aac              libopencore_amrnb       libsmbclient            libtwolame              libxcb                  sndio
lcms2                   libfontconfig           libopencore_amrwb       libsnappy               libv4l2                 libxcb_shm              vapoursynth
libaom                  libfreetype             libopenjpeg             libsoxr                 libvidstab              libxml2                 zlib

External libraries providing hardware acceleration:
cuda                    cuda_nvcc               ffnvcodec               nvdec                   v4l2_m2m                vdpau
cuda_llvm               cuvid                   libdrm                  nvenc                   vaapi

Libraries:
avcodec                 avfilter                avutil                  swresample
avdevice                avformat                postproc                swscale

Programs:
ffmpeg                  ffprobe

Enabled decoders:
aac                     argo                    eatgv                   lagarith                nellymoser              rasc                    vb
aac_fixed               ass                     eatqi                   lead                    notchlc                 rawvideo                vble
aac_latm                asv1                    eightbps                libaom_av1              nuv                     realtext                vbn
aasc                    asv2                    eightsvx_exp            libaribb24              on2avc                  rka                     vc1
ac3                     atrac1                  eightsvx_fib            libfdk_aac              opus                    rl2                     vc1_cuvid
ac3_fixed               atrac3                  escape124               libopencore_amrnb       osq                     roq                     vc1_v4l2m2m
acelp_kelvin            atrac3al                escape130               libopencore_amrwb       paf_audio               roq_dpcm                vc1image
adpcm_4xm               atrac3p                 evrc                    libopus                 paf_video               rpza                    vcr1
adpcm_adx               atrac3pal               exr                     libspeex                pam                     rscc                    vmdaudio
adpcm_afc               atrac9                  fastaudio               libvorbis               pbm                     rtv1                    vmdvideo
adpcm_agm               aura                    ffv1                    libvpx_vp8              pcm_alaw                rv10                    vmix
adpcm_aica              aura2                   ffvhuff                 libvpx_vp9              pcm_bluray              rv20                    vmnc
adpcm_argo              av1                     ffwavesynth             libzvbi_teletext        pcm_dvd                 rv30                    vnull
adpcm_ct                av1_cuvid               fic                     loco                    pcm_f16le               rv40                    vorbis
adpcm_dtk               avrn                    fits                    lscr                    pcm_f24le               s302m                   vp3
adpcm_ea                avrp                    flac                    m101                    pcm_f32be               sami                    vp4
adpcm_ea_maxis_xa       avs                     flashsv                 mace3                   pcm_f32le               sanm                    vp5
adpcm_ea_r1             avui                    flashsv2                mace6                   pcm_f64be               sbc                     vp6
adpcm_ea_r2             bethsoftvid             flic                    magicyuv                pcm_f64le               scpr                    vp6a
adpcm_ea_r3             bfi                     flv                     mdec                    pcm_lxf                 screenpresso            vp6f
adpcm_ea_xas            bink                    fmvc                    media100                pcm_mulaw               sdx2_dpcm               vp7
adpcm_g722              binkaudio_dct           fourxm                  metasound               pcm_s16be               sga                     vp8
adpcm_g726              binkaudio_rdft          fraps                   microdvd                pcm_s16be_planar        sgi                     vp8_cuvid
adpcm_g726le            bintext                 frwu                    mimic                   pcm_s16le               sgirle                  vp8_v4l2m2m
adpcm_ima_acorn         bitpacked               ftr                     misc4                   pcm_s16le_planar        sheervideo              vp9
adpcm_ima_alp           bmp                     g2m                     mjpeg                   pcm_s24be               shorten                 vp9_cuvid
adpcm_ima_amv           bmv_audio               g723_1                  mjpeg_cuvid             pcm_s24daud             simbiosis_imx           vp9_v4l2m2m
adpcm_ima_apc           bmv_video               g729                    mjpegb                  pcm_s24le               sipr                    vplayer
adpcm_ima_apm           bonk                    gdv                     mlp                     pcm_s24le_planar        siren                   vqa
adpcm_ima_cunning       brender_pix             gem                     mmvideo                 pcm_s32be               smackaud                vqc
adpcm_ima_dat4          c93                     gif                     mobiclip                pcm_s32le               smacker                 vvc
adpcm_ima_dk3           cavs                    gremlin_dpcm            motionpixels            pcm_s32le_planar        smc                     wady_dpcm
adpcm_ima_dk4           cbd2_dpcm               gsm                     movtext                 pcm_s64be               smvjpeg                 wavarc
adpcm_ima_ea_eacs       ccaption                gsm_ms                  mp1                     pcm_s64le               snow                    wavpack
adpcm_ima_ea_sead       cdgraphics              h261                    mp1float                pcm_s8                  sol_dpcm                wbmp
adpcm_ima_iss           cdtoons                 h263                    mp2                     pcm_s8_planar           sonic                   wcmv
adpcm_ima_moflex        cdxl                    h263_v4l2m2m            mp2float                pcm_sga                 sp5x                    webp
adpcm_ima_mtf           cfhd                    h263i                   mp3                     pcm_u16be               speedhq                 webvtt
adpcm_ima_oki           cinepak                 h263p                   mp3adu                  pcm_u16le               speex                   wmalossless
adpcm_ima_qt            clearvideo              h264                    mp3adufloat             pcm_u24be               srgc                    wmapro
adpcm_ima_rad           cljr                    h264_cuvid              mp3float                pcm_u24le               srt                     wmav1
adpcm_ima_smjpeg        cllc                    h264_v4l2m2m            mp3on4                  pcm_u32be               ssa                     wmav2
adpcm_ima_ssi           comfortnoise            hap                     mp3on4float             pcm_u32le               stl                     wmavoice
adpcm_ima_wav           cook                    hca                     mpc7                    pcm_u8                  subrip                  wmv1
adpcm_ima_ws            cpia                    hcom                    mpc8                    pcm_vidc                subviewer               wmv2
adpcm_ms                cri                     hdr                     mpeg1_cuvid             pcx                     subviewer1              wmv3
adpcm_mtaf              cscd                    hevc                    mpeg1_v4l2m2m           pdv                     sunrast                 wmv3image
adpcm_psx               cyuv                    hevc_cuvid              mpeg1video              pfm                     svq1                    wnv1
adpcm_sbpro_2           dca                     hevc_v4l2m2m            mpeg2_cuvid             pgm                     svq3                    wrapped_avframe
adpcm_sbpro_3           dds                     hnm4_video              mpeg2_v4l2m2m           pgmyuv                  tak                     ws_snd1
adpcm_sbpro_4           derf_dpcm               hq_hqa                  mpeg2video              pgssub                  targa                   xan_dpcm
adpcm_swf               dfa                     hqx                     mpeg4                   pgx                     targa_y216              xan_wc3
adpcm_thp               dfpwm                   huffyuv                 mpeg4_cuvid             phm                     tdsc                    xan_wc4
adpcm_thp_le            dirac                   hymt                    mpeg4_v4l2m2m           photocd                 text                    xbin
adpcm_vima              dnxhd                   iac                     mpegvideo               pictor                  theora                  xbm
adpcm_xa                dolby_e                 idcin                   mpl2                    pixlet                  thp                     xface
adpcm_xmd               dpx                     idf                     msa1                    pjs                     tiertexseqvideo         xl
adpcm_yamaha            dsd_lsbf                iff_ilbm                mscc                    png                     tiff                    xma1
adpcm_zork              dsd_lsbf_planar         ilbc                    msmpeg4v1               ppm                     tmv                     xma2
agm                     dsd_msbf                imc                     msmpeg4v2               prores                  truehd                  xpm
aic                     dsd_msbf_planar         imm4                    msmpeg4v3               prosumer                truemotion1             xsub
alac                    dsicinaudio             imm5                    msnsiren                psd                     truemotion2             xwd
alias_pix               dsicinvideo             indeo2                  msp2                    ptx                     truemotion2rt           y41p
als                     dss_sp                  indeo3                  msrle                   qcelp                   truespeech              ylc
amrnb                   dst                     indeo4                  mss1                    qdm2                    tscc                    yop
amrwb                   dvaudio                 indeo5                  mss2                    qdmc                    tscc2                   yuv4
amv                     dvbsub                  interplay_acm           msvideo1                qdraw                   tta                     zero12v
anm                     dvdsub                  interplay_dpcm          mszh                    qoa                     twinvq                  zerocodec
ansi                    dvvideo                 interplay_video         mts2                    qoi                     txd                     zlib
anull                   dxa                     ipu                     mv30                    qpeg                    ulti                    zmbv
apac                    dxtory                  jacosub                 mvc1                    qtrle                   utvideo
ape                     dxv                     jpeg2000                mvc2                    r10k                    v210
apng                    eac3                    jpegls                  mvdv                    r210                    v210x
aptx                    eacmv                   jv                      mvha                    ra_144                  v308
aptx_hd                 eamad                   kgv1                    mwsc                    ra_288                  v408
arbc                    eatgq                   kmvc                    mxpeg                   ralf                    v410

Enabled encoders:
a64multi                av1_vaapi               h263p                   libx264                 pcm_f64le               ppm                     truehd
a64multi5               avrp                    h264_nvenc              libx264rgb              pcm_mulaw               prores                  tta
aac                     avui                    h264_v4l2m2m            libx265                 pcm_s16be               prores_aw               ttml
ac3                     bitpacked               h264_vaapi              libxvid                 pcm_s16be_planar        prores_ks               utvideo
ac3_fixed               bmp                     hap                     ljpeg                   pcm_s16le               qoi                     v210
adpcm_adx               cfhd                    hdr                     magicyuv                pcm_s16le_planar        qtrle                   v308
adpcm_argo              cinepak                 hevc_nvenc              mjpeg                   pcm_s24be               r10k                    v408
adpcm_g722              cljr                    hevc_v4l2m2m            mjpeg_vaapi             pcm_s24daud             r210                    v410
adpcm_g726              comfortnoise            hevc_vaapi              mlp                     pcm_s24le               ra_144                  vbn
adpcm_g726le            dca                     huffyuv                 movtext                 pcm_s24le_planar        rawvideo                vc2
adpcm_ima_alp           dfpwm                   jpeg2000                mp2                     pcm_s32be               roq                     vnull
adpcm_ima_amv           dnxhd                   jpegls                  mp2fixed                pcm_s32le               roq_dpcm                vorbis
adpcm_ima_apm           dpx                     libaom_av1              mpeg1video              pcm_s32le_planar        rpza                    vp8_v4l2m2m
adpcm_ima_qt            dvbsub                  libfdk_aac              mpeg2_vaapi             pcm_s64be               rv10                    vp8_vaapi
adpcm_ima_ssi           dvdsub                  libkvazaar              mpeg2video              pcm_s64le               rv20                    vp9_vaapi
adpcm_ima_wav           dvvideo                 libmp3lame              mpeg4                   pcm_s8                  s302m                   wavpack
adpcm_ima_ws            dxv                     libopencore_amrnb       mpeg4_v4l2m2m           pcm_s8_planar           sbc                     wbmp
adpcm_ms                eac3                    libopenjpeg             msmpeg4v2               pcm_u16be               sgi                     webvtt
adpcm_swf               exr                     libopus                 msmpeg4v3               pcm_u16le               smc                     wmav1
adpcm_yamaha            ffv1                    librav1e                msrle                   pcm_u24be               snow                    wmav2
alac                    ffvhuff                 libshine                msvideo1                pcm_u24le               sonic                   wmv1
alias_pix               fits                    libspeex                nellymoser              pcm_u32be               sonic_ls                wmv2
amv                     flac                    libsvtav1               opus                    pcm_u32le               speedhq                 wrapped_avframe
anull                   flashsv                 libtheora               pam                     pcm_u8                  srt                     xbm
apng                    flashsv2                libtwolame              pbm                     pcm_vidc                ssa                     xface
aptx                    flv                     libvo_amrwbenc          pcm_alaw                pcx                     subrip                  xsub
aptx_hd                 g723_1                  libvorbis               pcm_bluray              pfm                     sunrast                 xwd
ass                     gif                     libvpx_vp8              pcm_dvd                 pgm                     svq1                    y41p
asv1                    h261                    libvpx_vp9              pcm_f32be               pgmyuv                  targa                   yuv4
asv2                    h263                    libwebp                 pcm_f32le               phm                     text                    zlib
av1_nvenc               h263_v4l2m2m            libwebp_anim            pcm_f64be               png                     tiff                    zmbv

Enabled hwaccels:
av1_nvdec               h264_vaapi              mjpeg_nvdec             mpeg2_vaapi             vc1_nvdec               vp9_nvdec               wmv3_vdpau
av1_vaapi               h264_vdpau              mjpeg_vaapi             mpeg2_vdpau             vc1_vaapi               vp9_vaapi
av1_vdpau               hevc_nvdec              mpeg1_nvdec             mpeg4_nvdec             vc1_vdpau               vp9_vdpau
h263_vaapi              hevc_vaapi              mpeg1_vdpau             mpeg4_vaapi             vp8_nvdec               wmv3_nvdec
h264_nvdec              hevc_vdpau              mpeg2_nvdec             mpeg4_vdpau             vp8_vaapi               wmv3_vaapi

Enabled parsers:
aac                     cavsvideo               dvbsub                  gsm                     misc4                   qoi                     vp9
aac_latm                cook                    dvd_nav                 h261                    mjpeg                   rv34                    vvc
ac3                     cri                     dvdsub                  h263                    mlp                     sbc                     webp
adx                     dca                     evc                     h264                    mpeg4video              sipr                    xbm
amr                     dirac                   flac                    hdr                     mpegaudio               tak                     xma
av1                     dnxhd                   ftr                     hevc                    mpegvideo               vc1                     xwd
avs2                    dolby_e                 g723_1                  ipu                     opus                    vorbis
avs3                    dpx                     g729                    jpeg2000                png                     vp3
bmp                     dvaudio                 gif                     jpegxl                  pnm                     vp8

Enabled demuxers:
aa                      bmv                     gdv                     image_sunrast_pipe      mpegtsraw               pvf                     thp
aac                     boa                     genh                    image_svg_pipe          mpegvideo               qcp                     threedostr
aax                     bonk                    gif                     image_tiff_pipe         mpjpeg                  qoa                     tiertexseq
ac3                     brstm                   gsm                     image_vbn_pipe          mpl2                    r3d                     tmv
ac4                     c93                     gxf                     image_webp_pipe         mpsub                   rawvideo                truehd
ace                     caf                     h261                    image_xbm_pipe          msf                     realtext                tta
acm                     cavsvideo               h263                    image_xpm_pipe          msnwc_tcp               redspark                tty
act                     cdg                     h264                    image_xwd_pipe          msp                     rka                     txd
adf                     cdxl                    hca                     imf                     mtaf                    rl2                     ty
adp                     cine                    hcom                    ingenient               mtv                     rm                      usm
ads                     codec2                  hevc                    ipmovie                 musx                    roq                     v210
adx                     codec2raw               hls                     ipu                     mv                      rpl                     v210x
aea                     concat                  hnm                     ircam                   mvi                     rsd                     vag
afc                     dash                    iamf                    iss                     mxf                     rso                     vapoursynth
aiff                    data                    ico                     iv8                     mxg                     rtp                     vc1
aix                     daud                    idcin                   ivf                     nc                      rtsp                    vc1t
alp                     dcstr                   idf                     ivr                     nistsphere              s337m                   vividas
amr                     derf                    iff                     jacosub                 nsp                     sami                    vivo
amrnb                   dfa                     ifv                     jpegxl_anim             nsv                     sap                     vmd
amrwb                   dfpwm                   ilbc                    jv                      nut                     sbc                     vobsub
anm                     dhav                    image2                  kux                     nuv                     sbg                     voc
apac                    dirac                   image2_alias_pix        kvag                    obu                     scc                     vpk
apc                     dnxhd                   image2_brender_pix      laf                     ogg                     scd                     vplayer
ape                     dsf                     image2pipe              libgme                  oma                     sdns                    vqf
apm                     dsicin                  image_bmp_pipe          libmodplug              osq                     sdp                     vvc
apng                    dss                     image_cri_pipe          live_flv                paf                     sdr2                    w64
aptx                    dts                     image_dds_pipe          lmlm4                   pcm_alaw                sds                     wady
aptx_hd                 dtshd                   image_dpx_pipe          loas                    pcm_f32be               sdx                     wav
aqtitle                 dv                      image_exr_pipe          lrc                     pcm_f32le               segafilm                wavarc
argo_asf                dvbsub                  image_gem_pipe          luodat                  pcm_f64be               ser                     wc3
argo_brp                dvbtxt                  image_gif_pipe          lvf                     pcm_f64le               sga                     webm_dash_manifest
argo_cvg                dxa                     image_hdr_pipe          lxf                     pcm_mulaw               shorten                 webvtt
asf                     ea                      image_j2k_pipe          m4v                     pcm_s16be               siff                    wsaud
asf_o                   ea_cdata                image_jpeg_pipe         matroska                pcm_s16le               simbiosis_imx           wsd
ass                     eac3                    image_jpegls_pipe       mca                     pcm_s24be               sln                     wsvqa
ast                     epaf                    image_jpegxl_pipe       mcc                     pcm_s24le               smacker                 wtv
au                      evc                     image_pam_pipe          mgsts                   pcm_s32be               smjpeg                  wv
av1                     ffmetadata              image_pbm_pipe          microdvd                pcm_s32le               smush                   wve
avi                     filmstrip               image_pcx_pipe          mjpeg                   pcm_s8                  sol                     xa
avisynth                fits                    image_pfm_pipe          mjpeg_2000              pcm_u16be               sox                     xbin
avr                     flac                    image_pgm_pipe          mlp                     pcm_u16le               spdif                   xmd
avs                     flic                    image_pgmyuv_pipe       mlv                     pcm_u24be               srt                     xmv
avs2                    flv                     image_pgx_pipe          mm                      pcm_u24le               stl                     xvag
avs3                    fourxm                  image_phm_pipe          mmf                     pcm_u32be               str                     xwma
bethsoftvid             frm                     image_photocd_pipe      mods                    pcm_u32le               subviewer               yop
bfi                     fsb                     image_pictor_pipe       moflex                  pcm_u8                  subviewer1              yuv4mpegpipe
bfstm                   fwse                    image_png_pipe          mov                     pcm_vidc                sup
bink                    g722                    image_ppm_pipe          mp3                     pdv                     svag
binka                   g723_1                  image_psd_pipe          mpc                     pjs                     svs
bintext                 g726                    image_qdraw_pipe        mpc8                    pmp                     swf
bit                     g726le                  image_qoi_pipe          mpegps                  pp_bnk                  tak
bitpacked               g729                    image_sgi_pipe          mpegts                  pva                     tedcaptions

Enabled muxers:
a64                     caf                     framemd5                latm                    mxf_opatom              pcm_u32be               sup
ac3                     cavsvideo               g722                    lrc                     null                    pcm_u32le               swf
ac4                     chromaprint             g723_1                  m4v                     nut                     pcm_u8                  tee
adts                    codec2                  g726                    matroska                obu                     pcm_vidc                tg2
adx                     codec2raw               g726le                  matroska_audio          oga                     psp                     tgp
aiff                    crc                     gif                     md5                     ogg                     rawvideo                truehd
alp                     dash                    gsm                     microdvd                ogv                     rcwt                    tta
amr                     data                    gxf                     mjpeg                   oma                     rm                      ttml
amv                     daud                    h261                    mkvtimestamp_v2         opus                    roq                     uncodedframecrc
apm                     dfpwm                   h263                    mlp                     pcm_alaw                rso                     vc1
apng                    dirac                   h264                    mmf                     pcm_f32be               rtp                     vc1t
aptx                    dnxhd                   hash                    mov                     pcm_f32le               rtp_mpegts              voc
aptx_hd                 dts                     hds                     mp2                     pcm_f64be               rtsp                    vvc
argo_asf                dv                      hevc                    mp3                     pcm_f64le               sap                     w64
argo_cvg                eac3                    hls                     mp4                     pcm_mulaw               sbc                     wav
asf                     evc                     iamf                    mpeg1system             pcm_s16be               scc                     webm
asf_stream              f4v                     ico                     mpeg1vcd                pcm_s16le               segafilm                webm_chunk
ass                     ffmetadata              ilbc                    mpeg1video              pcm_s24be               segment                 webm_dash_manifest
ast                     fifo                    image2                  mpeg2dvd                pcm_s24le               smjpeg                  webp
au                      fifo_test               image2pipe              mpeg2svcd               pcm_s32be               smoothstreaming         webvtt
avi                     filmstrip               ipod                    mpeg2video              pcm_s32le               sox                     wsaud
avif                    fits                    ircam                   mpeg2vob                pcm_s8                  spdif                   wtv
avm2                    flac                    ismv                    mpegts                  pcm_u16be               spx                     wv
avs2                    flv                     ivf                     mpjpeg                  pcm_u16le               srt                     yuv4mpegpipe
avs3                    framecrc                jacosub                 mxf                     pcm_u24be               stream_segment
bit                     framehash               kvag                    mxf_d10                 pcm_u24le               streamhash

Enabled protocols:
async                   fd                      hls                     libsmbclient            prompeg                 rtp                     udplite
bluray                  ffrtmpcrypt             http                    libsrt                  rtmp                    srtp                    unix
cache                   ffrtmphttp              httpproxy               libssh                  rtmpe                   subfile
concat                  file                    https                   md5                     rtmps                   tcp
concatf                 ftp                     icecast                 mmsh                    rtmpt                   tee
crypto                  gopher                  ipfs_gateway            mmst                    rtmpte                  tls
data                    gophers                 ipns_gateway            pipe                    rtmpts                  udp

Enabled filters:
a3dscope                arealtime               colorcorrect            fftfilt                 lowpass                 realtime                stereowiden
aap                     aresample               colorhold               field                   lowshelf                remap                   streamselect
abench                  areverse                colorize                fieldhint               lumakey                 removegrain             subtitles
abitscope               arls                    colorkey                fieldmatch              lut                     removelogo              super2xsai
acompressor             arnndn                  colorlevels             fieldorder              lut1d                   repeatfields            superequalizer
acontrast               asdr                    colormap                fillborders             lut2                    replaygain              surround
acopy                   asegment                colormatrix             find_rect               lut3d                   reverse                 swaprect
acrossfade              aselect                 colorspace              firequalizer            lutrgb                  rgbashift               swapuv
acrossover              asendcmd                colorspace_cuda         flanger                 lutyuv                  rgbtestsrc              tblend
acrusher                asetnsamples            colorspectrum           floodfill               lv2                     roberts                 telecine
acue                    asetpts                 colortemperature        format                  mandelbrot              rotate                  testsrc
addroi                  asetrate                compand                 fps                     maskedclamp             rubberband              testsrc2
adeclick                asettb                  compensationdelay       framepack               maskedmax               sab                     thistogram
adeclip                 ashowinfo               concat                  framerate               maskedmerge             scale                   threshold
adecorrelate            asidedata               convolution             framestep               maskedmin               scale2ref               thumbnail
adelay                  asisdr                  convolve                freezedetect            maskedthreshold         scale_cuda              thumbnail_cuda
adenorm                 asoftclip               copy                    freezeframes            maskfun                 scale_vaapi             tile
aderivative             aspectralstats          corr                    frei0r                  mcdeint                 scdet                   tiltandshift
adrawgraph              asplit                  cover_rect              frei0r_src              mcompand                scharr                  tiltshelf
adrc                    ass                     crop                    fspp                    median                  scroll                  tinterlace
adynamicequalizer       astats                  cropdetect              fsync                   mergeplanes             segment                 tlut2
adynamicsmooth          astreamselect           crossfeed               gblur                   mestimate               select                  tmedian
aecho                   asubboost               crystalizer             geq                     metadata                selectivecolor          tmidequalizer
aemphasis               asubcut                 cue                     gradfun                 midequalizer            sendcmd                 tmix
aeval                   asupercut               curves                  gradients               minterpolate            separatefields          tonemap
aevalsrc                asuperpass              datascope               graphmonitor            mix                     setdar                  tonemap_vaapi
aexciter                asuperstop              dblur                   grayworld               monochrome              setfield                tpad
afade                   atadenoise              dcshift                 greyedge                morpho                  setparams               transpose
afdelaysrc              atempo                  dctdnoiz                guided                  movie                   setpts                  transpose_vaapi
afftdn                  atilt                   deband                  haas                    mpdecimate              setrange                treble
afftfilt                atrim                   deblock                 haldclut                mptestsrc               setsar                  tremolo
afir                    avectorscope            decimate                haldclutsrc             msad                    settb                   trim
afireqsrc               avgblur                 deconvolve              hdcd                    multiply                sharpness_vaapi         unpremultiply
afirsrc                 avsynctest              dedot                   headphone               negate                  shear                   unsharp
aformat                 axcorrelate             deesser                 hflip                   nlmeans                 showcqt                 untile
afreqshift              backgroundkey           deflate                 highpass                nnedi                   showcwt                 uspp
afwtdn                  bandpass                deflicker               highshelf               noformat                showfreqs               v360
agate                   bandreject              deinterlace_vaapi       hilbert                 noise                   showinfo                vaguedenoiser
agraphmonitor           bass                    dejudder                histeq                  normalize               showpalette             varblur
ahistogram              bbox                    delogo                  histogram               null                    showspatial             vectorscope
aiir                    bench                   denoise_vaapi           hqdn3d                  nullsink                showspectrum            vflip
aintegral               bilateral               derain                  hqx                     nullsrc                 showspectrumpic         vfrdet
ainterleave             bilateral_cuda          deshake                 hstack                  ocr                     showvolume              vibrance
alatency                biquad                  despill                 hstack_vaapi            oscilloscope            showwaves               vibrato
alimiter                bitplanenoise           detelecine              hsvhold                 overlay                 showwavespic            vidstabdetect
allpass                 blackdetect             dialoguenhance          hsvkey                  overlay_cuda            shuffleframes           vidstabtransform
allrgb                  blackframe              dilation                hue                     overlay_vaapi           shufflepixels           vif
allyuv                  blend                   displace                huesaturation           owdenoise               shuffleplanes           vignette
aloop                   blockdetect             dnn_classify            hwdownload              pad                     sidechaincompress       virtualbass
alphaextract            blurdetect              dnn_detect              hwmap                   pal100bars              sidechaingate           vmafmotion
alphamerge              bm3d                    dnn_processing          hwupload                pal75bars               sidedata                volume
amerge                  boxblur                 doubleweave             hwupload_cuda           palettegen              sierpinski              volumedetect
ametadata               bs2b                    drawbox                 hysteresis              paletteuse              signalstats             vstack
amix                    bwdif                   drawgraph               iccdetect               pan                     signature               vstack_vaapi
amovie                  bwdif_cuda              drawgrid                iccgen                  perms                   silencedetect           w3fdif
amplify                 cas                     drmeter                 identity                perspective             silenceremove           waveform
amultiply               ccrepack                dynaudnorm              idet                    phase                   sinc                    weave
anequalizer             cellauto                earwax                  il                      photosensitivity        sine                    xbr
anlmdn                  channelmap              ebur128                 inflate                 pixdesctest             siti                    xcorrelate
anlmf                   channelsplit            edgedetect              interlace               pixelize                smartblur               xfade
anlms                   chorus                  elbg                    interleave              pixscope                smptebars               xmedian
anoisesrc               chromahold              entropy                 join                    pp                      smptehdbars             xstack
anull                   chromakey               epx                     kerndeint               pp7                     sobel                   xstack_vaapi
anullsink               chromakey_cuda          eq                      kirsch                  premultiply             sofalizer               yadif
anullsrc                chromanr                equalizer               ladspa                  prewitt                 spectrumsynth           yadif_cuda
apad                    chromashift             erosion                 lagfun                  procamp_vaapi           speechnorm              yaepblur
aperms                  ciescope                estdif                  latency                 pseudocolor             split                   yuvtestsrc
aphasemeter             codecview               exposure                lenscorrection          psnr                    spp                     zoneplate
aphaser                 color                   extractplanes           life                    pullup                  sr                      zoompan
aphaseshift             colorbalance            extrastereo             limitdiff               qp                      ssim
apsnr                   colorchannelmixer       fade                    limiter                 random                  ssim360
apsyclip                colorchart              feedback                loop                    readeia608              stereo3d
apulsator               colorcontrast           fftdnoiz                loudnorm                readvitc                stereotools

Enabled bsfs:
aac_adtstoasc           dump_extradata          h264_mp4toannexb        mjpeg2jpeg              opus_metadata           text2movsub             vvc_metadata
av1_frame_merge         dv_error_marker         h264_redundant_pps      mjpega_dump_header      pcm_rechunk             trace_headers           vvc_mp4toannexb
av1_frame_split         eac3_core               hapqa_extract           mov2textsub             pgs_frame_merge         truehd_core
av1_metadata            evc_frame_merge         hevc_metadata           mpeg2_metadata          prores_metadata         vp9_metadata
chomp                   extract_extradata       hevc_mp4toannexb        mpeg4_unpack_bframes    remove_extradata        vp9_raw_reorder
dca_core                filter_units            imx_dump_header         noise                   setts                   vp9_superframe
dts2pts                 h264_metadata           media100_to_mjpegb      null                    showinfo                vp9_superframe_split

Enabled indevs:
alsa                    kmsgrab                 libcdio                 pulse                   v4l2
fbdev                   lavfi                   oss                     sndio                   xcbgrab

Enabled outdevs:
alsa                    fbdev                   oss                     sndio
caca                    opengl                  pulse                   v4l2

License: nonfree and unredistributable
$ make -j32
$ make install

Do you want to print the installed FFmpeg & FFprobe versions? (yes/no): yes

========================================================
                     FFmpeg Version
========================================================

ffmpeg version git-2024-03-10-2c82ec9 Copyright (c) 2000-2024 the FFmpeg developers
built with gcc 12 (Debian 12.2.0-14)
configuration: --prefix=/usr/local --arch=x86_64 --cc=gcc --cxx=g++ --disable-debug --disable-doc --disable-large-tests --disable-shared --enable-ladspa --enable-gpl --enable-libsmbclient --enable-libcdio --enable-nonfree --enable-openssl --enable-libxml2 --enable-libaribb24 --enable-libfreetype --enable-libfontconfig --enable-libfribidi --enable-libass --enable-libwebp --enable-lcms2 --enable-libtesseract --enable-librubberband --enable-lv2 --enable-libpulse --enable-libfdk-aac --enable-libvorbis --enable-libopus --enable-libmysofa --enable-libvpx --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libaom --enable-librav1e --enable-libkvazaar --enable-libbluray --enable-libvidstab --enable-frei0r --enable-libsvtav1 --enable-libx264 --enable-libx265 --enable-cuda-nvcc --enable-cuda-llvm --enable-cuvid --enable-nvdec --enable-nvenc --enable-ffnvcodec --nvccflags='-gencode arch=compute_86,code=sm_86' --enable-libsrt --enable-avisynth --enable-vapoursynth --enable-libxvid --enable-libopenjpeg --enable-chromaprint --enable-libbs2b --enable-libcaca --enable-libgme --enable-libmodplug --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtwolame --enable-libv4l2 --enable-libvo-amrwbenc --enable-libzvbi --enable-lto --enable-opengl --enable-pic --enable-pthreads --enable-small --enable-static --enable-version3 --extra-cflags='-g -O3 -march=native' --extra-cxxflags='-g -O3 -march=native' --extra-libs='-ldl -lpthread -lm -lz' --extra-ldflags=-pie --pkg-config-flags=--static --pkg-config=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config --pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig --strip=/bin/strip
libavutil      59.  1.100 / 59.  1.100
libavcodec     61.  1.100 / 61.  1.100
libavformat    61.  0.100 / 61.  0.100
libavdevice    61.  0.100 / 61.  0.100
libavfilter    10.  0.100 / 10.  0.100
libswscale      8.  0.100 /  8.  0.100
libswresample   5.  0.100 /  5.  0.100
libpostproc    58.  0.100 / 58.  0.100

ffprobe version git-2024-03-10-2c82ec9 Copyright (c) 2007-2024 the FFmpeg developers
built with gcc 12 (Debian 12.2.0-14)
configuration: --prefix=/usr/local --arch=x86_64 --cc=gcc --cxx=g++ --disable-debug --disable-doc --disable-large-tests --disable-shared --enable-ladspa --enable-gpl --enable-libsmbclient --enable-libcdio --enable-nonfree --enable-openssl --enable-libxml2 --enable-libaribb24 --enable-libfreetype --enable-libfontconfig --enable-libfribidi --enable-libass --enable-libwebp --enable-lcms2 --enable-libtesseract --enable-librubberband --enable-lv2 --enable-libpulse --enable-libfdk-aac --enable-libvorbis --enable-libopus --enable-libmysofa --enable-libvpx --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libaom --enable-librav1e --enable-libkvazaar --enable-libbluray --enable-libvidstab --enable-frei0r --enable-libsvtav1 --enable-libx264 --enable-libx265 --enable-cuda-nvcc --enable-cuda-llvm --enable-cuvid --enable-nvdec --enable-nvenc --enable-ffnvcodec --nvccflags='-gencode arch=compute_86,code=sm_86' --enable-libsrt --enable-avisynth --enable-vapoursynth --enable-libxvid --enable-libopenjpeg --enable-chromaprint --enable-libbs2b --enable-libcaca --enable-libgme --enable-libmodplug --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtwolame --enable-libv4l2 --enable-libvo-amrwbenc --enable-libzvbi --enable-lto --enable-opengl --enable-pic --enable-pthreads --enable-small --enable-static --enable-version3 --extra-cflags='-g -O3 -march=native' --extra-cxxflags='-g -O3 -march=native' --extra-libs='-ldl -lpthread -lm -lz' --extra-ldflags=-pie --pkg-config-flags=--static --pkg-config=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config --pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig --strip=/bin/strip
libavutil      59.  1.100 / 59.  1.100
libavcodec     61.  1.100 / 61.  1.100
libavformat    61.  0.100 / 61.  0.100
libavdevice    61.  0.100 / 61.  0.100
libavfilter    10.  0.100 / 10.  0.100
libswscale      8.  0.100 /  8.  0.100
libswresample   5.  0.100 /  5.  0.100
libpostproc    58.  0.100 / 58.  0.100


========================================================
        Do you want to clean up the build files?
========================================================

[1] Yes
[2] No

Your choices are (1 or 2): 2

[INFO] Make sure to star this repository to show your support!
[INFO] https://github.com/slyfox1186/script-repo
```
