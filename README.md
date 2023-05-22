[![build test](https://github.com/markus-perl/ffmpeg-build-script/workflows/build%20test/badge.svg?branch=master)](https://github.com/markus-perl/ffmpeg-build-script/actions)

# FFmpeg Build Script

### If you like the script, please "★" this project!

build-ffmpeg
==========

The FFmpeg build script provides an easy way to build a **static** FFmpeg on **Linux Ubuntu 22.04** based systems with **non-free and GPL codecs**, see https://ffmpeg.org/legal.html) included. It uses API calls to get you the latest version of each package available at the time of building.

## Disclaimer And Data Privacy Notice

This script will download different packages with different licenses from various sources, which may track your usage. This includes prompting the user on wether to install the CUDA SDK Toolkit.
These sources are out of control by the developers of this script. Also, this script can create a non-free and unredistributable binary.
By downloading and using this script, you are fully aware of this.

Use this script at your own risk. I maintain this script in my spare time. Please do not file bug reports for systems
other than Debian based OS's.

## Installation

### Quick install and run

Open your command line and run (wget needs to be installed):

#### With GPL and non-free software, see https://ffmpeg.org/legal.html 
```bash
bash <(curl -sSL https://ffmpeg.optimizethis.net)
```

This command downloads the build script and automatically starts the build process.

### Common installation (Linux)

```bash
git clone https://github.com/slyfox1186/ffmpeg-build-script.git
cd ffmpeg-build-script || exit 1
bash build-ffmpeg --build --enable-gpl-and-non-free --latest
```

## Supported Codecs

* `x264`: H.264 Video Codec (MPEG-4 AVC)
* `x265`: H.265 Video Codec (HEVC)
* `frei0r` A collection of free and open source video effects plugins that can be used with a variety of video editing and processing software
* `cuda` : Hardware acceleration for Nvidia graphics cards
* `ff-nvcodec-headers`: FFmpeg version of headers required to interface with Nvidias codec APIs (Hardware Acceleration)
* `opencl`: An open source project that uses Boost.Compute as a high level C++ wrapper over the OpenCL API
* `avisynth`: A powerful tool for video post-production
* `kvazaar`: An open-source HEVC encoder licensed under 3-clause BSD
* `aom`: AV1 Video Codec (Experimental and very slow!)
* `svtav1`: SVT-AV1 Encoder and Decoder
* `rav1e`: rust based AV1 encoder
* `dav1d`: Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities and sponsored by the AOMedia (only available if `meson` and `ninja` are installed)
* `VP8/VP9/webm`: VP8 / VP9 Video Codec for the WebM video file format
* `webp`: Image format both lossless and lossy
* `xvidcore`: MPEG-4 video coding standard
* `theora`: Free lossy video compression format
* `faac`: Is based on the ISO MPEG-4 reference code.
* `fdk_aac`: Fraunhofer FDK AAC Codec
* `opus`: Lossy audio coding format
* `mp3`: MPEG-1 or MPEG-2 Audio Layer III
* `flac`: Free Lossless Audio Codec is open source software that can reduce the amount of storage space needed to store digital audio signals without needing to remove information in doing so
* `ogg`: Free, open container format
* `opencore-amr`: Adaptive Multi Rate (AMR) speech codec library implementation
* `vorbis`: Lossy audio compression format
* `srt`: Secure Reliable Transport (SRT) is a transport protocol for ultra low (sub-second) latency live video and audio streaming, as well as for generic bulk data transfer
* `harfbuzz`: Text shaping image processor
* `fontconfig`: Font configuration and customization library
* `freetype`: A freely available software library to render fonts
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format
* `bluray`: An open-source library designed for Blu-Ray Discs playback
* `fribidi`: The Free Implementation of the Unicode Bidirectional Algorithm
* `sdl`: A cross-platform development library designed to provide low level access to audio, keyboard, mouse, joystick, and graphics hardware via OpenGL and Direct3D
* `openjpeg`: Is an open-source JPEG 2000 codec written in C language
* `mediainfo`: A convenient unified display of the most relevant technical and tag data for video and audio files
* `xml2`: XML parser and toolkit
* `tiff`: This software provides support for the Tag Image File Format (TIFF), a widely used format for storing image data
* `mp4box/gpac`: Modular Multimedia framework for packaging, streaming and playing your favorite content, see http://netflix.gpac.io

### HardwareAccel

* `nv-codec`: [CUDA SDK Toolkit Download](https://developer.nvidia.com/cuda-downloads/).
  Follow the script's instructions to install the latest updates.
  These encoders/decoders will only be available if a CUDA installation was found while building the binary so install the kit to unlock hardware acceleration!.
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
* `vaapi`: [Video Acceleration API](https://trac.ffmpeg.org/wiki/Hardware/VAAPI). These encoders/decoders will only be
  available if a libva driver installation was found while building the binary. Follow [these](#Vaapi-installation)
  instructions for installation. Supported codecs in vaapi:
    * Encoders
        * H264 `h264_vaapi`
        * H265 `hevc_vaapi`
        * Motion JPEG `mjpeg_vaapi`
        * MPEG2 video `mpeg2_vaapi`
        * VP8 `vp8_vaapi`
        * VP9 `vp9_vaapi`
* `AMF`: [AMD's Advanced Media Framework](https://github.com/GPUOpen-LibrariesAndSDKs/AMF). These encoders will only 
  be available if `amdgpu` drivers are detected in use on the system with `lspci -v`. 
    * Encoders
        * H264 `h264_amf` 

## Requirements
  - All required packages will be made available to download by the user's choice.
    - The packages are required for a successful build.

### Tested on Ubuntu 22.04.2

Example Output
-------

```bash
ffmpeg-build-script-downloader v0.1
=============================================

First we create the ffmpeg build directory
==============================================

Now we download and execute the build script
==============================================

ffmpeg-build-script v3.3
======================================

The script will utilize 32 CPU cores for parallel processing to accelerate the build speed.

The script has been configured to run with GPL and non-free codecs enabled


The cuda-sdk-toolkit v12.1 is already installed.
=================================================

Do you want to update/reinstall it?

[1] Yes
[2] No

Your choices are (1 or 2): 2

Continuing the build...

Installing required development packages
==========================================
The required development packages are already installed.

building giflib - version 5.2.1
====================================
Downloading https://cfhcable.dl.sourceforge.net/project/giflib/giflib-5.2.1.tar.gz as giflib-5.2.1.tar.gz
Download Completed

File extracted: giflib-5.2.1.tar.gz
$ make
$ make PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace install

building pkg-config - version 1.9.4
====================================
Downloading https://github.com/pkgconf/pkgconf/archive/refs/heads/master.tar.gz as pkgconf-1.9.4.tar.gz
Download Completed

File extracted: pkgconf-1.9.4.tar.gz
$ ./autogen.sh
$ ./configure --silent --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    --with-pc-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig/ --with-internal-glib
$ make -j 32
$ sudo make install

building yasm - version 1.3.0
====================================
Downloading https://github.com/yasm/yasm/archive/refs/heads/master.tar.gz as yasm-1.3.0.tar.gz
Download Completed

File extracted: yasm-1.3.0.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
$ make -j 32
$ sudo make install

building nasm - version 2.16.02rc1
====================================
Downloading https://www.nasm.us/pub/nasm/releasebuilds/2.16.02rc1/nasm-2.16.02rc1.tar.xz as nasm-2.16.02rc1.tar.xz
Download Completed

File extracted: nasm-2.16.02rc1.tar.xz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building zlib - version 1.2.13
====================================
Downloading https://github.com/madler/zlib/releases/download/v1.2.13/zlib-1.2.13.tar.gz as zlib-1.2.13.tar.gz
Download Completed

File extracted: zlib-1.2.13.tar.gz
$ ./configure --static --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
$ make -j 32
$ sudo make install

building m4 - version 1.4.19
====================================
Downloading https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.xz as m4-1.4.19.tar.xz
Download Completed

File extracted: m4-1.4.19.tar.xz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-c++ --with-dmalloc
$ make -j 32
$ sudo make install

building autoconf - version 2.71
====================================
Downloading https://ftp.gnu.org/gnu/autoconf/autoconf-2.71.tar.xz as autoconf-2.71.tar.xz
Download Completed

File extracted: autoconf-2.71.tar.xz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
$ make -j 32
$ sudo make install

building automake - version 1.16.5
====================================
Downloading https://ftp.gnu.org/gnu/automake/automake-1.16.5.tar.xz as automake-1.16.5.tar.xz
Download Completed

File extracted: automake-1.16.5.tar.xz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
^T$ make -j 32
^T$ sudo make install

building libtool - version 2.4.7
====================================
Downloading https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz as libtool-2.4.7.tar.xz
Download Completed

File extracted: libtool-2.4.7.tar.xz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-static --disable-shared
$ make -j 32
$ sudo make install

building openssl - version 3.1.0
====================================
Downloading https://github.com/openssl/openssl/archive/refs/heads/master.tar.gz as openssl-3.1.0.tar.gz
Download Completed

File extracted: openssl-3.1.0.tar.gz
$ ./config --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --openssldir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    --with-zlib-include=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/ --with-zlib-lib=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib no-shared zlib
$ make -j 32
$ sudo make install_sw

building cmake - version 3.26.3
====================================
Downloading https://github.com/kitware/cmake/archive/refs/tags/v3.26.3.tar.gz as cmake-3.26.3.tar.gz
Download Completed

File extracted: cmake-3.26.3.tar.gz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --parallel=32 --enable-ccache -- -DCMAKE_USE_OPENSSL=OFF
$ make -j 32
$ sudo make install

building dav1d - version 9593e625
====================================
Downloading https://code.videolan.org/videolan/dav1d/-/archive/9593e625b75d498d1edea544da21ea764b98d507/9593e625b75d498d1edea544da21ea764b98d507.tar.bz2 as dav1d-9593e625.tar.bz2
Download Completed

File extracted: dav1d-9593e625.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release \
    --default-library=static --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib --strip
$ ninja -C build
$ sudo ninja -C build install

building svtav1 - version 1.4.1
====================================
Downloading https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.4.1/SVT-AV1-v1.4.1.tar.bz2 as SVT-AV1-1.4.1.tar.bz2
Download Completed

File extracted: SVT-AV1-1.4.1.tar.bz2
$ cmake -S . -B Build/linux -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    -DBUILD_SHARED_LIBS=OFF ../.. -GUnix Makefiles -DCMAKE_BUILD_TYPE=Release
$ make -j 32
$ sudo make install
$ sudo cp SvtAv1Enc.pc /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig/
$ sudo cp SvtAv1Dec.pc /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig/

building rav1e - version 0.6.4
====================================
Downloading https://github.com/xiph/rav1e/archive/refs/tags/v0.6.4.tar.gz as rav1e-0.6.4.tar.gz
Download Completed

File extracted: rav1e-0.6.4.tar.gz
$ cargo install --version 0.9.14+cargo-0.66 cargo-c
$ cargo cinstall --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --library-type=staticlib --crt-static --release

building x264 - version a8b68ebf
====================================
Downloading https://code.videolan.org/videolan/x264/-/archive/a8b68ebfaa68621b5ac8907610d3335971839d52/x264-a8b68ebfaa68621b5ac8907610d3335971839d52.tar.bz2 as x264-a8b68ebf.tar.bz2
Download Completed

File extracted: x264-a8b68ebf.tar.bz2
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-static --enable-pic CXXFLAGS=-fPIC 
$ make -j 32
$ sudo make install
$ sudo make install-lib-static

building x265 - version 3.5
====================================
Downloading https://github.com/videolan/x265/archive/Release_3.5.tar.gz as x265-3.5.tar.gz
Download Completed

File extracted: x265-3.5.tar.gz
$ making 12bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DHIGH_BIT_DEPTH=ON -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF -DENABLE_CLI=OFF -DMAIN12=ON
$ make -j 32
$ making 10bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DHIGH_BIT_DEPTH=ON -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF -DENABLE_CLI=OFF
$ make -j 32
$ making 8bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DEXTRA_LIB=x265_main10.a;x265_main12.a;-ldl -DEXTRA_LINK_FLAGS=-L. -DLINKED_10BIT=ON -DLINKED_12BIT=ON
$ make -j 32
$ ar -M
$ sudo make install

building SVT-HEVC - version 1.5.1
====================================
Downloading https://github.com/openvisualcloud/svt-hevc/archive/refs/heads/master.tar.gz as SVT-HEVC-1.5.1.tar.gz
Download Completed

File extracted: SVT-HEVC-1.5.1.tar.gz
^T^T$ cmake .. -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release
$ make -j 32
$ sudo make install

building libvpx - version 1.13.0
====================================
Downloading https://github.com/webmproject/libvpx/archive/refs/heads/master.tar.gz as libvpx-1.13.0.tar.gz
Download Completed

File extracted: libvpx-1.13.0.tar.gz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-unit-tests --disable-shared --disable-examples --as=yasm
$ make -j 32
$ sudo make install

building xvidcore - version 1.3.7
====================================
Downloading https://downloads.xvid.com/downloads/xvidcore-1.3.7.tar.bz2 as xvidcore-1.3.7.tar.bz2
Download Completed

File extracted: xvidcore-1.3.7.tar.bz2
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install
$ sudo rm /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/libxvidcore.so /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/libxvidcore.so.4 /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/libxvidcore.so.4.3

building vid_stab - version 1.1.1
====================================
Downloading https://github.com/georgmartius/vid.stab/archive/refs/heads/master.tar.gz as vid.stab-1.1.1.tar.gz
Download Completed

File extracted: vid.stab-1.1.1.tar.gz
$ cmake -S . -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DUSE_OMP=OFF -DENABLE_SHARED=OFF .
$ make -j 32
$ sudo make install

building av1 - version 5711b50
====================================
Downloading https://aomedia.googlesource.com/aom/+archive/5711b50eebe392119defd2a2a262bffef05e8507.tar.gz as av1.tar.gz
Download Completed

File extracted: av1.tar.gz
$ cmake -S . -DENABLE_TESTS=0 -DENABLE_EXAMPLES=0 -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
      -DCMAKE_INSTALL_LIBDIR=lib /home/jman/tmp/ffmpeg/ffmpeg-build/packages/av1
$ make -j 32
$ sudo make install

building zimg - version 3.0.4
====================================
Downloading https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.4.tar.gz as zimg-3.0.4.tar.gz
Download Completed

File extracted: zimg-3.0.4.tar.gz
$ /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/bin/libtoolize -ifq
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-static --disable-shared
$ make -j 32
$ sudo make install

building libpng - version 1.6.39
====================================
Downloading https://github.com/glennrp/libpng/archive/refs/tags/v1.6.39.tar.gz as libpng-1.6.39.tar.gz
Download Completed

File extracted: libpng-1.6.39.tar.gz
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building avif - version 0.11.1
====================================
Downloading https://github.com/AOMediaCodec/libavif/archive/refs/tags/v0.11.1.tar.gz as avif-0.11.1.tar.gz
Download Completed

File extracted: avif-0.11.1.tar.gz
$ cmake -S . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DAVIF_CODEC_AOM=ON \
    -DAVIF_CODEC_AOM=ON -DAVIF_CODEC_DAV1D=ON -DAVIF_CODEC_RAV1E=ON -DAVIF_CODEC_SVT=ON -DBUILD_SHARED_LIBS=OFF -GNinja
$ ninja
$ ninja install

building kvazaar - version 2.2.0
====================================
Downloading https://github.com/ultravideo/kvazaar/archive/refs/heads/master.tar.gz as kvazaar-2.2.0.tar.gz
Download Completed

File extracted: kvazaar-2.2.0.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-static --disable-shared
$ make -j 32
$ sudo make install

building lv2 - version 1.18.10
====================================
Downloading https://github.com/lv2/lv2/archive/refs/heads/master.tar.gz as lv2-1.18.10.tar.gz
Download Completed

File extracted: lv2-1.18.10.tar.gz
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release \
    --default-library=static --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib
$ ninja -C build
$ sudo ninja -C build install

building waflib - version waf-2.0.25
====================================
Downloading https://gitlab.com/ita1024/waf/-/archive/waf-2.0.25/waf-waf-2.0.25.tar.bz2 as autowaf-waf-2.0.25.tar.bz2
Download Completed

File extracted: autowaf-waf-2.0.25.tar.bz2

building serd - version 0.30.16
====================================
Downloading https://gitlab.com/drobilla/serd/-/archive/v0.30.16/serd-v0.30.16.tar.bz2 as serd-0.30.16.tar.bz2
Download Completed

File extracted: serd-0.30.16.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release --default-library=static \
    --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib
$ ninja -C build
$ sudo ninja -C build install

building pcre2 - version 10.42
====================================
Downloading https://github.com/pcre2project/pcre2/archive/refs/heads/master.tar.gz as pcre2-10.42.tar.gz
Download Completed

File extracted: pcre2-10.42.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building zix - version 9e966d0f
====================================
Downloading https://gitlab.com/drobilla/zix/-/archive/9e966d0f5a11bb43d17a56aab1ed9a43b8c2a112/zix-9e966d0f5a11bb43d17a56aab1ed9a43b8c2a112.tar.bz2 as zix-9e966d0f.tar.bz2
Download Completed

File extracted: zix-9e966d0f.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release \
    --default-library=static --backend ninja --pkg-config-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig
$ ninja -C build
$ sudo ninja -C build install

building sord - version 0.16.14
====================================
Downloading https://gitlab.com/drobilla/sord/-/archive/v0.16.14/sord-v0.16.14.tar.bz2 as sord-0.16.14.tar.bz2
Download Completed

File extracted: sord-0.16.14.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release --default-library=static \
    --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib --pkg-config-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig
$ ninja -C build
$ sudo ninja -C build install

building sratom - version 0.6.14
====================================
Downloading https://gitlab.com/lv2/sratom/-/archive/v0.6.14/sratom-v0.6.14.tar.bz2 as sratom-0.6.14.tar.bz2
Download Completed

File extracted: sratom-0.6.14.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release --default-library=static \
    --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib --pkg-config-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig
$ ninja -C build
$ sudo ninja -C build install

building lilv - version 0.24.20
====================================
Downloading https://gitlab.com/lv2/lilv/-/archive/v0.24.20/lilv-v0.24.20.tar.bz2 as lilv-0.24.20.tar.bz2
Download Completed

File extracted: lilv-0.24.20.tar.bz2
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release --default-library=static \
    --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib --pkg-config-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig
$ ninja -C build
$ sudo ninja -C build install

building opencore - version 0.1.6
====================================
Downloading https://master.dl.sourceforge.net/project/opencore-amr/opencore-amr/opencore-amr-0.1.6.tar.gz?viasf=1 as opencore-amr-0.1.6.tar.gz
Download Completed

File extracted: opencore-amr-0.1.6.tar.gz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building lame - version 3.100
====================================
Downloading https://sourceforge.net/projects/lame/files/lame/3.100/lame-3.100.tar.gz/download?use_mirror=gigenet as lame-3.100.tar.gz
Download Completed

File extracted: lame-3.100.tar.gz
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building opus - version 1.4
====================================
Downloading https://github.com/xiph/opus/archive/refs/tags/v1.4.tar.gz as opus-1.4.tar.gz
Download Completed

File extracted: opus-1.4.tar.gz
$ ./autogen.sh
$ cmake -S . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DENABLE_SHARED=OFF \
    -DBUILD_SHARED_LIBS=OFF -DENABLE_STATIC=ON -GUnix Makefiles
$ make -j 32
$ sudo make install

building libogg - version 1.3.5
====================================
Downloading https://github.com/xiph/ogg/archive/refs/heads/master.tar.gz as libogg-1.3.5.tar.gz
Download Completed

File extracted: libogg-1.3.5.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building libvorbis - version 1.3.7
====================================
Downloading https://github.com/xiph/vorbis/archive/refs/tags/v1.3.7.tar.gz as libvorbis-1.3.7.tar.gz
Download Completed

File extracted: libvorbis-1.3.7.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --with-ogg-libraries=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib \
    --with-ogg-includes=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include --enable-static --disable-shared --disable-oggtest
$ make -j 32
$ sudo make install

building libtheora - version 1.0
====================================
Downloading https://codeload.github.com/xiph/theora/tar.gz/refs/tags/v1.0 as libtheora-1.0.tar.gz
Download Completed

File extracted: libtheora-1.0.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --with-ogg-libraries=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib \
    --with-ogg-includes=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/ --with-vorbis-libraries=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib \
    --with-vorbis-includes=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/ --enable-static --disable-shared --disable-oggtest --disable-vorbistest \
    --disable-examples --disable-asm --disable-spec
$ make -j 32
$ sudo make install

building fdk_aac - version 2.0.2
====================================
Downloading https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.2.tar.gz as fdk_aac-2.0.2.tar.gz
Download Completed

File extracted: fdk_aac-2.0.2.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static --enable-pic --bindir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/bin CXXFLAGS= -fno-exceptions -fno-rtti
$ make -j 32
$ sudo make install

building libtiff - version 4.5.0
====================================
Downloading https://gitlab.com/libtiff/libtiff/-/archive/v4.5.0/libtiff-v4.5.0.tar.bz2 as libtiff-4.5.0.tar.bz2
Download Completed

File extracted: libtiff-4.5.0.tar.bz2
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building libwebp - version git
====================================
Downloading libwebp-git
Download Complete

$ autoreconf -fi
$ cmake -S . -DCMAKE_INSTALL_MANDIR:PATH= -DCMAKE_C_FLAGS_RELEASE:STRING=-O3 -DNDEBUG -DWEBP_BUILD_EXTRAS:BOOL=0 -DWEBP_BUILD_LIBWEBPMUX:BOOL=0 -DZLIB_LIBRARY_DEBUG:FILEPATH=ZLIB_LIBRARY_DEBUG-NOTFOUND -DCMAKE_INSTALL_INCLUDEDIR:PATH=include -DCMAKE_INSTALL_LOCALEDIR:PATH= -DWEBP_LINK_STATIC:BOOL=0 -DWEBP_BUILD_GIF2WEBP:BOOL=0 -DWEBP_BUILD_IMG2WEBP:BOOL=0 -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=1 -DWEBP_BUILD_DWEBP:BOOL=0 -DWEBP_BUILD_CWEBP:BOOL=0 -DWEBP_BUILD_ANIM_UTILS:BOOL=0 -DWEBP_BUILD_WEBPMUX:BOOL=0 -DCMAKE_C_FLAGS:STRING= -DWEBP_ENABLE_SWAP_16BIT_CSP:BOOL=0 -DCMAKE_SHARED_LINKER_FLAGS_RELEASE:STRING= -DWEBP_BUILD_WEBPINFO:BOOL=0 -DCMAKE_INSTALL_PREFIX:PATH=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DZLIB_INCLUDE_DIR:PATH=/usr/include -DWEBP_BUILD_VWEBP:BOOL=0 -DCMAKE_INSTALL_DOCDIR:PATH= -GUnix Makefiles
$ make -j 32
$ sudo make install

building udfread - version 1.1.2
====================================
Downloading https://code.videolan.org/videolan/libudfread/-/archive/1.1.2/libudfread-1.1.2.tar.bz2 as udfread-1.1.2.tar.bz2
Download Completed

File extracted: udfread-1.1.2.tar.bz2
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static --with-pic --with-gnu-ld
$ make -j 32
$ sudo make install

building libbluray - version 1.3.4
====================================
Downloading https://code.videolan.org/videolan/libbluray/-/archive/1.3.4/1.3.4.tar.gz as libbluray-1.3.4.tar.gz
Download Completed

File extracted: libbluray-1.3.4.tar.gz
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building zenLib - version 0.4.41
====================================
Downloading https://github.com/MediaArea/ZenLib/archive/refs/tags/v0.4.41.tar.gz as zenLib-0.4.41.tar.gz
Download Completed

File extracted: zenLib-0.4.41.tar.gz
$ cmake -S . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_BINDIR=bin -DCMAKE_INSTALL_INCLUDEDIR=include -DENABLE_SHARED=OFF -DENABLE_STATIC=ON
$ make -j 32
$ sudo make install

building MediaInfoLib - version 23.03
====================================
Downloading https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v23.03.tar.gz as MediaInfoLib-23.03.tar.gz
Download Completed

File extracted: MediaInfoLib-23.03.tar.gz
$ cmake . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_BINDIR=bin -DCMAKE_INSTALL_INCLUDEDIR=include -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DENABLE_APPS=OFF -DUSE_STATIC_LIBSTDCXX=ON -DBUILD_ZLIB=OFF -DBUILD_ZENLIB=OFF
$ make -j 32
$ sudo make install

building MediaInfoCLI - version 23.03
====================================
Downloading https://github.com/MediaArea/MediaInfo/archive/refs/heads/master.tar.gz as MediaInfoCLI-23.03.tar.gz
Download Completed

File extracted: MediaInfoCLI-23.03.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --enable-staticlibs

building harfbuzz - version 7.1.0
====================================
Downloading https://github.com/harfbuzz/harfbuzz/archive/refs/tags/7.1.0.tar.gz as harfbuzz-7.1.0.tar.gz
Download Completed

File extracted: harfbuzz-7.1.0.tar.gz
$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --buildtype=release --default-library=static --libdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib
$ ninja -C build
$ sudo ninja -C build install

building c2man - version git
====================================
Downloading c2man-git
Download Complete

$ ./Configure -desO -D prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -D bin=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/bin \
    -D bash=/bin/bash -D cc=/usr/lib/ccache/cc -D d_gnu=/usr/lib/x86_64-linux-gnu -D find=/usr/bin/find -D gcc=/usr/lib/ccache/gcc \
    -D gzip=/usr/bin/gzip -D installmansrc=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/share/man \
    -D ldflags= -L /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib -L/usr/local/lib -D less=/usr/bin/less \
    -D libpth=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib /usr/local/lib /lib /usr/lib \
    -D locincpth=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include /usr/local/include /opt/local/include /usr/gnu/include /opt/gnu/include /usr/GNU/include /opt/GNU/include \
    -D yacc=/usr/bin/yacc -D loclibpth=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib /usr/local/lib /opt/local/lib /usr/gnu/lib /opt/gnu/lib /usr/GNU/lib /opt/GNU/lib \
    -D make=/usr/bin/make -D more=/usr/bin/more -D osname=Ubuntu -D perl=/usr/bin/perl -D privlib=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/c2man \
    -D privlibexp=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/c2man -D sleep=/usr/bin/sleep -D tail=/usr/bin/tail -D tar=/usr/bin/tar -D uuname=Linux \
    -D vi=/usr/bin/vi -D zip=/usr/bin/zip
$ make depend
$ make -j 32
$ sudo make install

building fribidi - version 1.0.12
====================================
Downloading https://github.com/fribidi/fribidi/archive/refs/heads/master.tar.gz as fribidi-1.0.12.tar.gz
Download Completed

File extracted: fribidi-1.0.12.tar.gz
$ meson setup build --prefix=/home/jman/tmp/ffmpeg/workspace --strip --backend ninja --optimization 3 \
    --pkg-config-path=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig:/usr/local/lib/x86_64-linux-gnu/pkgconfig:\
    /usr/local/lib/pkgconfig:/usr/local/share/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig:/usr/lib64/pkgconfig \
    --buildtype=release --default-library=static --libdir=/home/jman/tmp/ffmpeg/workspace/lib
$ ninja -C build
$ sudo ninja -C build install

building libass - version 0.17.1
====================================
Downloading https://github.com/libass/libass/archive/refs/heads/master.tar.gz as libass-0.17.1.tar.gz
Download Completed

File extracted: libass-0.17.1.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building fontconfig - version 2.14.2
====================================
Downloading https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/2.14.2/fontconfig-2.14.2.tar.bz2 as fontconfig-2.14.2.tar.bz2
Download Completed

File extracted: fontconfig-2.14.2.tar.bz2
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --sysconfdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/etc/ \
    --mandir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/share/man/
$ make -j 32
$ sudo make install

building freetype - version VER-2-13-0
====================================
Downloading https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-2-13-0/freetype-VER-2-13-0.tar.bz2 as freetype-VER-2-13-0.tar.bz2
Download Completed

File extracted: freetype-VER-2-13-0.tar.bz2
$ ./autogen.sh
$ cmake -B build/release-static -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
    -DVVDEC_ENABLE_LINK_TIME_OPT=OFF -DCMAKE_VERBOSE_MAKEFILE=OFF -DCMAKE_BUILD_TYPE=Release -Dharfbuzz=disabled \
    -Dpng=disabled -Dbzip2=disabled -Dbrotli=disabled -Dzlib=disabled -Dtests=disabled
$ cmake --build build/release-static -j 32

building libsdl - version 2.26.5
====================================
Downloading https://github.com/libsdl-org/SDL/archive/refs/tags/release-2.26.5.tar.gz as libsdl-2.26.5.tar.gz
Download Completed

File extracted: libsdl-2.26.5.tar.gz
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-shared --enable-static
$ make -j 32
$ sudo make install

building srt - version rc.1
====================================
Downloading https://github.com/Haivision/srt/archive/refs/heads/master.tar.gz as srt-rc.1.tar.gz
Download Completed

File extracted: srt-rc.1.tar.gz
$ cmake . -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_BINDIR=bin -DCMAKE_INSTALL_INCLUDEDIR=include -DENABLE_SHARED=OFF -DENABLE_STATIC=ON \
  -DENABLE_APPS=OFF -DUSE_STATIC_LIBSTDCXX=ON
$ make -j 32
$ sudo make install

building opencl - version 2023.04.17
====================================
Downloading https://github.com/khronosgroup/opencl-headers/archive/refs/heads/master.tar.gz as opencl-2023.04.17.tar.gz
Download Completed

File extracted: opencl-2023.04.17.tar.gz
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
$ cmake --build build --target install

building amf - version 1.4.29
====================================
Downloading https://github.com/GPUOpen-LibrariesAndSDKs/AMF/archive/refs/heads/master.tar.gz as AMF-1.4.29.tar.gz
Download Completed

File extracted: AMF-1.4.29.tar.gz
$ rm -fr /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/AMF
$ mkdir -p /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/AMF
$ cp -fr /home/jman/tmp/ffmpeg/ffmpeg-build/packages/AMF-1.4.29/amf/public/include/components /home/jman/tmp/ffmpeg/ffmpeg-build/packages/AMF-1.4.29/amf/public/include/core /home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/AMF/

building vvenc - version 1.8.0
====================================
Downloading https://github.com/fraunhoferhhi/vvenc/archive/refs/heads/master.tar.gz as vvenc-1.8.0.tar.gz
Download Completed

File extracted: vvenc-1.8.0.tar.gz
$ cmake -B build/release-static -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
  -DVVDEC_ENABLE_LINK_TIME_OPT=OFF -DCMAKE_VERBOSE_MAKEFILE=OFF -DCMAKE_BUILD_TYPE=Release
$ cmake --build build/release-static -j 32

building vvdec - version rc1
====================================
Downloading vvdec-rc1
Download Complete

$ cmake -B build/release-static -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
  -DVVDEC_ENABLE_LINK_TIME_OPT=OFF -DCMAKE_VERBOSE_MAKEFILE=OFF -DCMAKE_BUILD_TYPE=Release
$ cmake --build build/release-static -j 32

building nv-codec - version n12.0.16.0
====================================
Downloading nv-codec-n12.0.16.0
Download Complete

$ make PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace -j 32
$ sudo make install PREFIX=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace
```

```bash
building FFmpeg - version git
====================================
Downloading https://github.com/FFmpeg/FFmpeg/archive/refs/heads/master.tar.gz as FFmpeg-git.tar.gz
Download Completed

File extracted: FFmpeg-git.tar.gz
$ ./configure
install prefix            /home/jman/tmp/ffmpeg/ffmpeg-build/workspace
source path               .
C compiler                gcc
C library                 glibc
ARCH                      x86 (16)
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
alsa                    libdav1d                libmp3lame              libsvtav1               libx264                 lv2                     zlib
bzlib                   libfdk_aac              libopencore_amrnb       libtheora               libx265                 lzma
iconv                   libfontconfig           libopencore_amrwb       libvidstab              libxcb                  openssl
libaom                  libfreetype             libopus                 libvorbis               libxcb_shm              sdl2
libass                  libfribidi              librav1e                libvpx                  libxvid                 sndio
libbluray               libkvazaar              libsrt                  libwebp                 libzimg                 xlib

External libraries providing hardware acceleration:
amf                     cuda_llvm               cuvid                   libnpp                  nvenc                   v4l2_m2m
cuda                    cuda_nvcc               ffnvcodec               nvdec                   opencl

Libraries:
avcodec                 avfilter                avutil                  swresample
avdevice                avformat                postproc                swscale

Programs:
ffmpeg                  ffplay                  ffprobe

Enabled decoders:
aac                     arbc                    eacmv                   jpegls                  mwsc                    ralf                    v410
aac_fixed               argo                    eamad                   jv                      mxpeg                   rasc                    vb
aac_latm                ass                     eatgq                   kgv1                    nellymoser              rawvideo                vble
aasc                    asv1                    eatgv                   kmvc                    notchlc                 realtext                vbn
ac3                     asv2                    eatqi                   lagarith                nuv                     rka                     vc1
ac3_fixed               atrac1                  eightbps                libaom_av1              on2avc                  rl2                     vc1_cuvid
acelp_kelvin            atrac3                  eightsvx_exp            libdav1d                opus                    roq                     vc1_v4l2m2m
adpcm_4xm               atrac3al                eightsvx_fib            libfdk_aac              paf_audio               roq_dpcm                vc1image
adpcm_adx               atrac3p                 escape124               libopencore_amrnb       paf_video               rpza                    vcr1
adpcm_afc               atrac3pal               escape130               libopencore_amrwb       pam                     rscc                    vmdaudio
adpcm_agm               atrac9                  evrc                    libopus                 pbm                     rv10                    vmdvideo
adpcm_aica              aura                    exr                     libvorbis               pcm_alaw                rv20                    vmnc
adpcm_argo              aura2                   fastaudio               libvpx_vp8              pcm_bluray              rv30                    vnull
adpcm_ct                av1                     ffv1                    libvpx_vp9              pcm_dvd                 rv40                    vorbis
adpcm_dtk               av1_cuvid               ffvhuff                 loco                    pcm_f16le               s302m                   vp3
adpcm_ea                avrn                    ffwavesynth             lscr                    pcm_f24le               sami                    vp4
adpcm_ea_maxis_xa       avrp                    fic                     m101                    pcm_f32be               sanm                    vp5
adpcm_ea_r1             avs                     fits                    mace3                   pcm_f32le               sbc                     vp6
adpcm_ea_r2             avui                    flac                    mace6                   pcm_f64be               scpr                    vp6a
adpcm_ea_r3             ayuv                    flashsv                 magicyuv                pcm_f64le               screenpresso            vp6f
adpcm_ea_xas            bethsoftvid             flashsv2                mdec                    pcm_lxf                 sdx2_dpcm               vp7
adpcm_g722              bfi                     flic                    media100                pcm_mulaw               sga                     vp8
adpcm_g726              bink                    flv                     metasound               pcm_s16be               sgi                     vp8_cuvid
adpcm_g726le            binkaudio_dct           fmvc                    microdvd                pcm_s16be_planar        sgirle                  vp8_v4l2m2m
adpcm_ima_acorn         binkaudio_rdft          fourxm                  mimic                   pcm_s16le               sheervideo              vp9
adpcm_ima_alp           bintext                 fraps                   misc4                   pcm_s16le_planar        shorten                 vp9_cuvid
adpcm_ima_amv           bitpacked               frwu                    mjpeg                   pcm_s24be               simbiosis_imx           vp9_v4l2m2m
adpcm_ima_apc           bmp                     ftr                     mjpeg_cuvid             pcm_s24daud             sipr                    vplayer
adpcm_ima_apm           bmv_audio               g2m                     mjpegb                  pcm_s24le               siren                   vqa
adpcm_ima_cunning       bmv_video               g723_1                  mlp                     pcm_s24le_planar        smackaud                vqc
adpcm_ima_dat4          bonk                    g729                    mmvideo                 pcm_s32be               smacker                 wady_dpcm
adpcm_ima_dk3           brender_pix             gdv                     mobiclip                pcm_s32le               smc                     wavarc
adpcm_ima_dk4           c93                     gem                     motionpixels            pcm_s32le_planar        smvjpeg                 wavpack
adpcm_ima_ea_eacs       cavs                    gif                     movtext                 pcm_s64be               snow                    wbmp
adpcm_ima_ea_sead       cbd2_dpcm               gremlin_dpcm            mp1                     pcm_s64le               sol_dpcm                wcmv
adpcm_ima_iss           ccaption                gsm                     mp1float                pcm_s8                  sonic                   webp
adpcm_ima_moflex        cdgraphics              gsm_ms                  mp2                     pcm_s8_planar           sp5x                    webvtt
adpcm_ima_mtf           cdtoons                 h261                    mp2float                pcm_sga                 speedhq                 wmalossless
adpcm_ima_oki           cdxl                    h263                    mp3                     pcm_u16be               speex                   wmapro
adpcm_ima_qt            cfhd                    h263_v4l2m2m            mp3adu                  pcm_u16le               srgc                    wmav1
adpcm_ima_rad           cinepak                 h263i                   mp3adufloat             pcm_u24be               srt                     wmav2
adpcm_ima_smjpeg        clearvideo              h263p                   mp3float                pcm_u24le               ssa                     wmavoice
adpcm_ima_ssi           cljr                    h264                    mp3on4                  pcm_u32be               stl                     wmv1
adpcm_ima_wav           cllc                    h264_cuvid              mp3on4float             pcm_u32le               subrip                  wmv2
adpcm_ima_ws            comfortnoise            h264_v4l2m2m            mpc7                    pcm_u8                  subviewer               wmv3
adpcm_ms                cook                    hap                     mpc8                    pcm_vidc                subviewer1              wmv3image
adpcm_mtaf              cpia                    hca                     mpeg1_cuvid             pcx                     sunrast                 wnv1
adpcm_psx               cri                     hcom                    mpeg1_v4l2m2m           pdv                     svq1                    wrapped_avframe
adpcm_sbpro_2           cscd                    hdr                     mpeg1video              pfm                     svq3                    ws_snd1
adpcm_sbpro_3           cyuv                    hevc                    mpeg2_cuvid             pgm                     tak                     xan_dpcm
adpcm_sbpro_4           dca                     hevc_cuvid              mpeg2_v4l2m2m           pgmyuv                  targa                   xan_wc3
adpcm_swf               dds                     hevc_v4l2m2m            mpeg2video              pgssub                  targa_y216              xan_wc4
adpcm_thp               derf_dpcm               hnm4_video              mpeg4                   pgx                     tdsc                    xbin
adpcm_thp_le            dfa                     hq_hqa                  mpeg4_cuvid             phm                     text                    xbm
adpcm_vima              dfpwm                   hqx                     mpeg4_v4l2m2m           photocd                 theora                  xface
adpcm_xa                dirac                   huffyuv                 mpegvideo               pictor                  thp                     xl
adpcm_xmd               dnxhd                   hymt                    mpl2                    pixlet                  tiertexseqvideo         xma1
adpcm_yamaha            dolby_e                 iac                     msa1                    pjs                     tiff                    xma2
adpcm_zork              dpx                     idcin                   mscc                    png                     tmv                     xpm
agm                     dsd_lsbf                idf                     msmpeg4v1               ppm                     truehd                  xsub
aic                     dsd_lsbf_planar         iff_ilbm                msmpeg4v2               prores                  truemotion1             xwd
alac                    dsd_msbf                ilbc                    msmpeg4v3               prosumer                truemotion2             y41p
alias_pix               dsd_msbf_planar         imc                     msnsiren                psd                     truemotion2rt           ylc
als                     dsicinaudio             imm4                    msp2                    ptx                     truespeech              yop
amrnb                   dsicinvideo             imm5                    msrle                   qcelp                   tscc                    yuv4
amrwb                   dss_sp                  indeo2                  mss1                    qdm2                    tscc2                   zero12v
amv                     dst                     indeo3                  mss2                    qdmc                    tta                     zerocodec
anm                     dvaudio                 indeo4                  msvideo1                qdraw                   twinvq                  zlib
ansi                    dvbsub                  indeo5                  mszh                    qoi                     txd                     zmbv
anull                   dvdsub                  interplay_acm           mts2                    qpeg                    ulti
apac                    dvvideo                 interplay_dpcm          mv30                    qtrle                   utvideo
ape                     dxa                     interplay_video         mvc1                    r10k                    v210
apng                    dxtory                  ipu                     mvc2                    r210                    v210x
aptx                    dxv                     jacosub                 mvdv                    ra_144                  v308
aptx_hd                 eac3                    jpeg2000                mvha                    ra_288                  v408

Enabled encoders:
a64multi                av1_amf                 h263                    libxvid                 pcm_s16le_planar        qoi                     utvideo
a64multi5               av1_nvenc               h263_v4l2m2m            ljpeg                   pcm_s24be               qtrle                   v210
aac                     avrp                    h263p                   magicyuv                pcm_s24daud             r10k                    v308
ac3                     avui                    h264_amf                mjpeg                   pcm_s24le               r210                    v408
ac3_fixed               ayuv                    h264_nvenc              mlp                     pcm_s24le_planar        ra_144                  v410
adpcm_adx               bitpacked               h264_v4l2m2m            movtext                 pcm_s32be               rawvideo                vbn
adpcm_argo              bmp                     hdr                     mp2                     pcm_s32le               roq                     vc2
adpcm_g722              cfhd                    hevc_amf                mp2fixed                pcm_s32le_planar        roq_dpcm                vnull
adpcm_g726              cinepak                 hevc_nvenc              mpeg1video              pcm_s64be               rpza                    vorbis
adpcm_g726le            cljr                    hevc_v4l2m2m            mpeg2video              pcm_s64le               rv10                    vp8_v4l2m2m
adpcm_ima_alp           comfortnoise            huffyuv                 mpeg4                   pcm_s8                  rv20                    wavpack
adpcm_ima_amv           dca                     jpeg2000                mpeg4_v4l2m2m           pcm_s8_planar           s302m                   wbmp
adpcm_ima_apm           dfpwm                   jpegls                  msmpeg4v2               pcm_u16be               sbc                     webvtt
adpcm_ima_qt            dnxhd                   libaom_av1              msmpeg4v3               pcm_u16le               sgi                     wmav1
adpcm_ima_ssi           dpx                     libfdk_aac              msvideo1                pcm_u24be               smc                     wmav2
adpcm_ima_wav           dvbsub                  libkvazaar              nellymoser              pcm_u24le               snow                    wmv1
adpcm_ima_ws            dvdsub                  libmp3lame              opus                    pcm_u32be               sonic                   wmv2
adpcm_ms                dvvideo                 libopencore_amrnb       pam                     pcm_u32le               sonic_ls                wrapped_avframe
adpcm_swf               eac3                    libopus                 pbm                     pcm_u8                  speedhq                 xbm
adpcm_yamaha            exr                     librav1e                pcm_alaw                pcm_vidc                srt                     xface
alac                    ffv1                    libsvtav1               pcm_bluray              pcx                     ssa                     xsub
alias_pix               ffvhuff                 libtheora               pcm_dvd                 pfm                     subrip                  xwd
amv                     fits                    libvorbis               pcm_f32be               pgm                     sunrast                 y41p
anull                   flac                    libvpx_vp8              pcm_f32le               pgmyuv                  svq1                    yuv4
apng                    flashsv                 libvpx_vp9              pcm_f64be               phm                     targa                   zlib
aptx                    flashsv2                libwebp                 pcm_f64le               png                     text                    zmbv
aptx_hd                 flv                     libwebp_anim            pcm_mulaw               ppm                     tiff
ass                     g723_1                  libx264                 pcm_s16be               prores                  truehd
asv1                    gif                     libx264rgb              pcm_s16be_planar        prores_aw               tta
asv2                    h261                    libx265                 pcm_s16le               prores_ks               ttml

Enabled hwaccels:
av1_nvdec               hevc_nvdec              mpeg1_nvdec             mpeg4_nvdec             vp8_nvdec               wmv3_nvdec
h264_nvdec              mjpeg_nvdec             mpeg2_nvdec             vc1_nvdec               vp9_nvdec

Enabled parsers:
aac                     cavsvideo               dvbsub                  h261                    mlp                     rv40                    webp
aac_latm                cook                    dvd_nav                 h263                    mpeg4video              sbc                     xbm
ac3                     cri                     dvdsub                  h264                    mpegaudio               sipr                    xma
adx                     dca                     flac                    hdr                     mpegvideo               tak                     xwd
amr                     dirac                   ftr                     hevc                    opus                    vc1
av1                     dnxhd                   g723_1                  ipu                     png                     vorbis
avs2                    dolby_e                 g729                    jpeg2000                pnm                     vp3
avs3                    dpx                     gif                     misc4                   qoi                     vp8
bmp                     dvaudio                 gsm                     mjpeg                   rv30                    vp9

Enabled demuxers:
aa                      bmv                     gdv                     image_sgi_pipe          mpegvideo               pvf                     tedcaptions
aac                     boa                     genh                    image_sunrast_pipe      mpjpeg                  qcp                     thp
aax                     bonk                    gif                     image_svg_pipe          mpl2                    r3d                     threedostr
ac3                     brstm                   gsm                     image_tiff_pipe         mpsub                   rawvideo                tiertexseq
ace                     c93                     gxf                     image_vbn_pipe          msf                     realtext                tmv
acm                     caf                     h261                    image_webp_pipe         msnwc_tcp               redspark                truehd
act                     cavsvideo               h263                    image_xbm_pipe          msp                     rka                     tta
adf                     cdg                     h264                    image_xpm_pipe          mtaf                    rl2                     tty
adp                     cdxl                    hca                     image_xwd_pipe          mtv                     rm                      txd
ads                     cine                    hcom                    ingenient               musx                    roq                     ty
adx                     codec2                  hevc                    ipmovie                 mv                      rpl                     v210
aea                     codec2raw               hls                     ipu                     mvi                     rsd                     v210x
afc                     concat                  hnm                     ircam                   mxf                     rso                     vag
aiff                    data                    ico                     iss                     mxg                     rtp                     vc1
aix                     daud                    idcin                   iv8                     nc                      rtsp                    vc1t
alp                     dcstr                   idf                     ivf                     nistsphere              s337m                   vividas
amr                     derf                    iff                     ivr                     nsp                     sami                    vivo
amrnb                   dfa                     ifv                     jacosub                 nsv                     sap                     vmd
amrwb                   dfpwm                   ilbc                    jv                      nut                     sbc                     vobsub
anm                     dhav                    image2                  kux                     nuv                     sbg                     voc
apac                    dirac                   image2_alias_pix        kvag                    obu                     scc                     vpk
apc                     dnxhd                   image2_brender_pix      laf                     ogg                     scd                     vplayer
ape                     dsf                     image2pipe              live_flv                oma                     sdns                    vqf
apm                     dsicin                  image_bmp_pipe          lmlm4                   paf                     sdp                     w64
apng                    dss                     image_cri_pipe          loas                    pcm_alaw                sdr2                    wady
aptx                    dts                     image_dds_pipe          lrc                     pcm_f32be               sds                     wav
aptx_hd                 dtshd                   image_dpx_pipe          luodat                  pcm_f32le               sdx                     wavarc
aqtitle                 dv                      image_exr_pipe          lvf                     pcm_f64be               segafilm                wc3
argo_asf                dvbsub                  image_gem_pipe          lxf                     pcm_f64le               ser                     webm_dash_manifest
argo_brp                dvbtxt                  image_gif_pipe          m4v                     pcm_mulaw               sga                     webvtt
argo_cvg                dxa                     image_hdr_pipe          matroska                pcm_s16be               shorten                 wsaud
asf                     ea                      image_j2k_pipe          mca                     pcm_s16le               siff                    wsd
asf_o                   ea_cdata                image_jpeg_pipe         mcc                     pcm_s24be               simbiosis_imx           wsvqa
ass                     eac3                    image_jpegls_pipe       mgsts                   pcm_s24le               sln                     wtv
ast                     epaf                    image_jpegxl_pipe       microdvd                pcm_s32be               smacker                 wv
au                      ffmetadata              image_pam_pipe          mjpeg                   pcm_s32le               smjpeg                  wve
av1                     filmstrip               image_pbm_pipe          mjpeg_2000              pcm_s8                  smush                   xa
avi                     fits                    image_pcx_pipe          mlp                     pcm_u16be               sol                     xbin
avr                     flac                    image_pfm_pipe          mlv                     pcm_u16le               sox                     xmd
avs                     flic                    image_pgm_pipe          mm                      pcm_u24be               spdif                   xmv
avs2                    flv                     image_pgmyuv_pipe       mmf                     pcm_u24le               srt                     xvag
avs3                    fourxm                  image_pgx_pipe          mods                    pcm_u32be               stl                     xwma
bethsoftvid             frm                     image_phm_pipe          moflex                  pcm_u32le               str                     yop
bfi                     fsb                     image_photocd_pipe      mov                     pcm_u8                  subviewer               yuv4mpegpipe
bfstm                   fwse                    image_pictor_pipe       mp3                     pcm_vidc                subviewer1
bink                    g722                    image_png_pipe          mpc                     pdv                     sup
binka                   g723_1                  image_ppm_pipe          mpc8                    pjs                     svag
bintext                 g726                    image_psd_pipe          mpegps                  pmp                     svs
bit                     g726le                  image_qdraw_pipe        mpegts                  pp_bnk                  swf
bitpacked               g729                    image_qoi_pipe          mpegtsraw               pva                     tak

Enabled muxers:
a64                     caf                     g722                    lrc                     mxf_opatom              pcm_u24le               streamhash
ac3                     cavsvideo               g723_1                  m4v                     null                    pcm_u32be               sup
adts                    codec2                  g726                    matroska                nut                     pcm_u32le               swf
adx                     codec2raw               g726le                  matroska_audio          obu                     pcm_u8                  tee
aiff                    crc                     gif                     md5                     oga                     pcm_vidc                tg2
alp                     dash                    gsm                     microdvd                ogg                     psp                     tgp
amr                     data                    gxf                     mjpeg                   ogv                     rawvideo                truehd
amv                     daud                    h261                    mkvtimestamp_v2         oma                     rm                      tta
apm                     dfpwm                   h263                    mlp                     opus                    roq                     ttml
apng                    dirac                   h264                    mmf                     pcm_alaw                rso                     uncodedframecrc
aptx                    dnxhd                   hash                    mov                     pcm_f32be               rtp                     vc1
aptx_hd                 dts                     hds                     mp2                     pcm_f32le               rtp_mpegts              vc1t
argo_asf                dv                      hevc                    mp3                     pcm_f64be               rtsp                    voc
argo_cvg                eac3                    hls                     mp4                     pcm_f64le               sap                     w64
asf                     f4v                     ico                     mpeg1system             pcm_mulaw               sbc                     wav
asf_stream              ffmetadata              ilbc                    mpeg1vcd                pcm_s16be               scc                     webm
ass                     fifo                    image2                  mpeg1video              pcm_s16le               segafilm                webm_chunk
ast                     fifo_test               image2pipe              mpeg2dvd                pcm_s24be               segment                 webm_dash_manifest
au                      filmstrip               ipod                    mpeg2svcd               pcm_s24le               smjpeg                  webp
avi                     fits                    ircam                   mpeg2video              pcm_s32be               smoothstreaming         webvtt
avif                    flac                    ismv                    mpeg2vob                pcm_s32le               sox                     wsaud
avm2                    flv                     ivf                     mpegts                  pcm_s8                  spdif                   wtv
avs2                    framecrc                jacosub                 mpjpeg                  pcm_u16be               spx                     wv
avs3                    framehash               kvag                    mxf                     pcm_u16le               srt                     yuv4mpegpipe
bit                     framemd5                latm                    mxf_d10                 pcm_u24be               stream_segment

Enabled protocols:
async                   data                    gopher                  icecast                 mmst                    rtmpt                   tcp
bluray                  fd                      gophers                 ipfs_gateway            pipe                    rtmpte                  tee
cache                   ffrtmpcrypt             hls                     ipns_gateway            prompeg                 rtmpts                  tls
concat                  ffrtmphttp              http                    libsrt                  rtmp                    rtp                     udp
concatf                 file                    httpproxy               md5                     rtmpe                   srtp                    udplite
crypto                  ftp                     https                   mmsh                    rtmps                   subfile                 unix

Enabled filters:
a3dscope                areverse                colorlevels             field                   lutrgb                  removelogo              subtitles
abench                  arnndn                  colormap                fieldhint               lutyuv                  repeatfields            super2xsai
abitscope               asdr                    colormatrix             fieldmatch              lv2                     replaygain              superequalizer
acompressor             asegment                colorspace              fieldorder              mandelbrot              reverse                 surround
acontrast               aselect                 colorspace_cuda         fifo                    maskedclamp             rgbashift               swaprect
acopy                   asendcmd                colorspectrum           fillborders             maskedmax               rgbtestsrc              swapuv
acrossfade              asetnsamples            colortemperature        find_rect               maskedmerge             roberts                 tblend
acrossover              asetpts                 compand                 firequalizer            maskedmin               roberts_opencl          telecine
acrusher                asetrate                compensationdelay       flanger                 maskedthreshold         rotate                  testsrc
acue                    asettb                  concat                  floodfill               maskfun                 sab                     testsrc2
addroi                  ashowinfo               convolution             format                  mcdeint                 scale                   thistogram
adeclick                asidedata               convolution_opencl      fps                     mcompand                scale2ref               threshold
adeclip                 asoftclip               convolve                framepack               median                  scale2ref_npp           thumbnail
adecorrelate            aspectralstats          copy                    framerate               mergeplanes             scale_cuda              thumbnail_cuda
adelay                  asplit                  corr                    framestep               mestimate               scale_npp               tile
adenorm                 ass                     cover_rect              freezedetect            metadata                scdet                   tiltshelf
aderivative             astats                  crop                    freezeframes            midequalizer            scharr                  tinterlace
adrawgraph              astreamselect           cropdetect              fspp                    minterpolate            scroll                  tlut2
adrc                    asubboost               crossfeed               gblur                   mix                     segment                 tmedian
adynamicequalizer       asubcut                 crystalizer             geq                     monochrome              select                  tmidequalizer
adynamicsmooth          asupercut               cue                     gradfun                 morpho                  selectivecolor          tmix
aecho                   asuperpass              curves                  gradients               movie                   sendcmd                 tonemap
aemphasis               asuperstop              datascope               graphmonitor            mpdecimate              separatefields          tonemap_opencl
aeval                   atadenoise              dblur                   grayworld               mptestsrc               setdar                  tpad
aevalsrc                atempo                  dcshift                 greyedge                msad                    setfield                transpose
aexciter                atilt                   dctdnoiz                guided                  multiply                setparams               transpose_npp
afade                   atrim                   deband                  haas                    negate                  setpts                  transpose_opencl
afdelaysrc              avectorscope            deblock                 haldclut                nlmeans                 setrange                treble
afftdn                  avgblur                 decimate                haldclutsrc             nlmeans_opencl          setsar                  tremolo
afftfilt                avgblur_opencl          deconvolve              hdcd                    nnedi                   settb                   trim
afifo                   avsynctest              dedot                   headphone               noformat                sharpen_npp             unpremultiply
afir                    axcorrelate             deesser                 hflip                   noise                   shear                   unsharp
afirsrc                 backgroundkey           deflate                 highpass                normalize               showcqt                 unsharp_opencl
aformat                 bandpass                deflicker               highshelf               null                    showcwt                 untile
afreqshift              bandreject              dejudder                hilbert                 nullsink                showfreqs               uspp
afwtdn                  bass                    delogo                  histeq                  nullsrc                 showinfo                v360
agate                   bbox                    derain                  histogram               openclsrc               showpalette             vaguedenoiser
agraphmonitor           bench                   deshake                 hqdn3d                  oscilloscope            showspatial             varblur
ahistogram              bilateral               deshake_opencl          hqx                     overlay                 showspectrum            vectorscope
aiir                    bilateral_cuda          despill                 hstack                  overlay_cuda            showspectrumpic         vflip
aintegral               biquad                  detelecine              hsvhold                 overlay_opencl          showvolume              vfrdet
ainterleave             bitplanenoise           dialoguenhance          hsvkey                  owdenoise               showwaves               vibrance
alatency                blackdetect             dilation                hue                     pad                     showwavespic            vibrato
alimiter                blackframe              dilation_opencl         huesaturation           pad_opencl              shuffleframes           vidstabdetect
allpass                 blend                   displace                hwdownload              pal100bars              shufflepixels           vidstabtransform
allrgb                  blockdetect             dnn_classify            hwmap                   pal75bars               shuffleplanes           vif
allyuv                  blurdetect              dnn_detect              hwupload                palettegen              sidechaincompress       vignette
aloop                   bm3d                    dnn_processing          hwupload_cuda           paletteuse              sidechaingate           virtualbass
alphaextract            boxblur                 doubleweave             hysteresis              pan                     sidedata                vmafmotion
alphamerge              boxblur_opencl          drawbox                 identity                perms                   sierpinski              volume
amerge                  bwdif                   drawgraph               idet                    perspective             signalstats             volumedetect
ametadata               cas                     drawgrid                il                      phase                   signature               vstack
amix                    cellauto                drawtext                inflate                 photosensitivity        silencedetect           w3fdif
amovie                  channelmap              drmeter                 interlace               pixdesctest             silenceremove           waveform
amplify                 channelsplit            dynaudnorm              interleave              pixelize                sinc                    weave
amultiply               chorus                  earwax                  join                    pixscope                sine                    xbr
anequalizer             chromahold              ebur128                 kerndeint               pp                      siti                    xcorrelate
anlmdn                  chromakey               edgedetect              kirsch                  pp7                     smartblur               xfade
anlmf                   chromakey_cuda          elbg                    lagfun                  premultiply             smptebars               xfade_opencl
anlms                   chromanr                entropy                 latency                 prewitt                 smptehdbars             xmedian
anoisesrc               chromashift             epx                     lenscorrection          prewitt_opencl          sobel                   xstack
anull                   ciescope                eq                      life                    program_opencl          sobel_opencl            yadif
anullsink               codecview               equalizer               limitdiff               pseudocolor             spectrumsynth           yadif_cuda
anullsrc                color                   erosion                 limiter                 psnr                    speechnorm              yaepblur
apad                    colorbalance            erosion_opencl          loop                    pullup                  split                   yuvtestsrc
aperms                  colorchannelmixer       estdif                  loudnorm                qp                      spp                     zoompan
aphasemeter             colorchart              exposure                lowpass                 random                  sr                      zscale
aphaser                 colorcontrast           extractplanes           lowshelf                readeia608              ssim
aphaseshift             colorcorrect            extrastereo             lumakey                 readvitc                ssim360
apsyclip                colorhold               fade                    lut                     realtime                stereo3d
apulsator               colorize                feedback                lut1d                   remap                   stereotools
arealtime               colorkey                fftdnoiz                lut2                    remap_opencl            stereowiden
aresample               colorkey_opencl         fftfilt                 lut3d                   removegrain             streamselect

Enabled bsfs:
aac_adtstoasc           dts2pts                 h264_metadata           imx_dump_header         mpeg2_metadata          pgs_frame_merge         truehd_core
av1_frame_merge         dump_extradata          h264_mp4toannexb        media100_to_mjpegb      mpeg4_unpack_bframes    prores_metadata         vp9_metadata
av1_frame_split         dv_error_marker         h264_redundant_pps      mjpeg2jpeg              noise                   remove_extradata        vp9_raw_reorder
av1_metadata            eac3_core               hapqa_extract           mjpega_dump_header      null                    setts                   vp9_superframe
chomp                   extract_extradata       hevc_metadata           mov2textsub             opus_metadata           text2movsub             vp9_superframe_split
dca_core                filter_units            hevc_mp4toannexb        mp3_header_decompress   pcm_rechunk             trace_headers

Enabled indevs:
alsa                    fbdev                   lavfi                   oss                     sndio                   v4l2                    xcbgrab

Enabled outdevs:
alsa                    fbdev                   oss                     sdl2                    sndio                   v4l2                    xv

License: nonfree and unredistributable
$ make -j 32
$ sudo make install

====================================
       FFmpeg Build Complete        
====================================

The binary files can be found in the following locations

ffmpeg:  /usr/bin/ffmpeg
ffprobe: /usr/bin/ffprobe
ffplay:  /usr/bin/ffplay

============================
       FFmpeg Version       
============================

ffmpeg version 5.1.git Copyright (c) 2000-2023 the FFmpeg developers
built with gcc 11 (Ubuntu 11.3.0-1ubuntu1~22.04)
configuration: --enable-nonfree --enable-gpl --enable-openssl --enable-libdav1d --enable-libsvtav1 --enable-librav1e --enable-libx264 \
--enable-libx265 --enable-libvpx --enable-libxvid --enable-libvidstab --enable-libaom --enable-libzimg --enable-libkvazaar --enable-lv2 \
--enable-libopencore_amrnb --enable-libopencore_amrwb --enable-libmp3lame --enable-libopus --enable-libvorbis --enable-libtheora \
--enable-libfdk-aac --enable-libwebp --enable-libbluray --enable-libfribidi --enable-libass --enable-libfontconfig --enable-libfreetype \
--enable-libsrt --enable-opencl --enable-amf --enable-nvenc --enable-nvdec --enable-cuda-nvcc --enable-cuvid --enable-cuda-llvm \
--enable-libnpp --nvccflags='-gencode arch=compute_86,code=sm_86' --arch=x86_64 --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace \
--disable-debug --disable-doc --disable-shared --enable-pthreads --enable-static --enable-small --enable-version3 --enable-ffnvcodec \
--cpu=16 --extra-cflags='-I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include -I/usr/local -I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/lilv-0 \
-DLIBXML_STATIC_FOR_DLL -DNOLIBTOOL -I/usr/local/cuda-12.1/targets/x86_64-linux/include -I/usr/local/cuda-12.1/include \
-I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/usr/include -I/home/jman/tmp/ffmpeg/ffmpeg-build/packages/nv-codec-n12.0.16.0/include' \
--extra-ldexeflags= --extra-ldflags='-L/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib -L/usr/local/cuda-12.1/targets/x86_64-linux/lib -L/usr/local/cuda-12.1/lib64' \
--extra-libs='-ldl -lpthread -lm -lz' --pkgconfigdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig --pkg-config-flags=--static
libavutil      58.  6.100 / 58.  6.100
libavcodec     60. 10.100 / 60. 10.100
libavformat    60.  5.100 / 60.  5.100
libavdevice    60.  2.100 / 60.  2.100
libavfilter     9.  5.100 /  9.  5.100
libswscale      7.  2.100 /  7.  2.100
libswresample   4. 11.100 /  4. 11.100
libpostproc    57.  2.100 / 57.  2.100
```
