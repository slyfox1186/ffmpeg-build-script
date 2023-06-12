[![build test](https://github.com/markus-perl/ffmpeg-build-script/workflows/build%20test/badge.svg?branch=master)](https://github.com/markus-perl/ffmpeg-build-script/actions)

# FFmpeg Build Script

### If you like the script, please "★" this project!

## Install [FFmpeg](https://ffmpeg.org/download.html)
  - **Compiles the latest updates from souce code by issuing API calls to each repositories backend**
  - **The CUDA SDK Toolkit which unlocks Hardware Acceleration is available during the install to make things as easy as possible**
  - **Supported OS:**
    - **Debian** - 10 / 11
    - **Ubuntu** - 18.04 / 20.04 / 22.04
    - Other debian style distros may work as well

The FFmpeg build script provides an easy way to build a **<ins>static</ins>** FFmpeg binary on **<ins>Debian based systems</ins>** with **non-free and GPL codecs**, see https://ffmpeg.org/legal.html) included. It uses API calls to get you the latest version of each package available at the time of building.

**Be aware** that without using a precreated API Token from GitHub, you are limited to ***50 API calls a day***. This is imporant because the script has ***44 repositories*** with API calls during the build and if you stop the script in the middle and restart (protentially over and over) you will eventually eat up the 50 call limit and be forced to wait to continue the build UNLESS you change the curl code under `git_1_fn` and put in your own [Token](https://github.com/settings/tokens?type=beta). SO if you start the build ***<ins>let it finish</ins>***.

See the below example on how to put your own token into the script.

```
    git_token='github_pat_blahblahblahblah'

    if curl_cmd="$(curl \
                        -m "$curl_timeout" \
                        --request GET \
                        --url "https://api.github.com/slyfox1186" \
                        --header "Authorization: Bearer $git_token" \
                        --header "X-GitHub-Api-Version: 2022-11-28" \
                        -sSL "https://api.github.com/repos/$github_repo/$github_url")"; then
```

## Disclaimer And Data Privacy Notice

This script will download different packages with different licenses from various sources, which may track your usage. This includes the CUDA SDK Toolkit.
These sources are in control of the developers of each script which I have no control over.

**Importantly**, this script creates a <ins>**non-free**</ins> and unredistributable binary at its end AND by downloading and using this script, you are <ins>**fully aware of this**</ins>.

Use this script at your own risk. I maintain this script in my spare time. Please do not file bug reports for systems
other than Debian based OS's.

## Install methods
### With GPL and non-free software, see https://ffmpeg.org/legal.html

### Quick installion

This command downloads the build script and automatically starts the build process.

```bash
bash <(curl -sSL https://ffmpeg.optimizethis.net) --build --latest
```

### Manual installation

```bash
git clone https://github.com/slyfox1186/ffmpeg-build-script.git
cd ffmpeg-build-script || exit 1
bash build-ffmpeg --build --latest
```

## Supported Codecs

* `x264`: H.264 Video Codec (MPEG-4 AVC)
* `x265`: H.265 Video Codec (HEVC)
* `kvazaar`: An open-source HEVC encoder licensed under 3-clause BSD
* `cuda` : Hardware acceleration for Nvidia graphics cards
* `ff-nvcodec-headers`: FFmpeg version of headers required to interface with Nvidias codec APIs (Hardware Acceleration)
* `cyanrip`: Fully featured CD ripping program able to take out most of the tedium. Fully accurate, has advanced features most rippers don't, yet has no bloat and is cross-platform.
* `vpx`: VP8 / VP9 Video Codec for the WebM video file format
* `frei0r` A collection of free and open source video effects plugins that can be used with a variety of video editing and processing software
* `opencl`: An open source project that uses Boost.Compute as a high level C++ wrapper over the OpenCL API
* `avisynth`: A powerful tool for video post-production
* `vapoursynth`: An application for video manipulation.
* `aom`: AV1 Video Codec (Experimental and very slow!)
* `svtav1`: SVT-AV1 Encoder and Decoder
* `rav1e`: rust based AV1 encoder
* `dav1d`: Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities and sponsored by the AOMedia (only available if `meson` and `ninja` are installed)
* `webp`: Image format both lossless and lossy
* `xvidcore`: MPEG-4 video coding standard
* `theora`: Free lossy video compression format
* `faac`: Is based on the ISO MPEG-4 reference code
* `libfdk_aac`: Fraunhofer FDK AAC Codec
* `libopus`: Lossy audio coding format
* `libmp3lame`: MPEG-1 or MPEG-2 Audio Layer III
* `flac`: Free Lossless Audio Codec is open source software that can reduce the amount of storage space needed to store digital audio signals without needing to remove information in doing so
* `ogg`: Free, open container format
* `opencore-amr`: Adaptive Multi Rate (AMR) speech codec library implementation
* `vorbis`: Lossy audio compression format
* `jxl`: JPEG XL offers significantly better image quality and compression ratios than legacy JPEG, plus a shorter specification
* `openjpeg`: OpenJPEG is an open-source library to encode and decode JPEG 2000 images
* `srt`: Secure Reliable Transport (SRT) is a transport protocol for ultra low (sub-second) latency live video and audio streaming, as well as for generic bulk data transfer
* `harfbuzz`: Text shaping image processor
* `fontconfig`: Font configuration and customization library
* `freetype`: A freely available software library to render fonts
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format
* `libbluray`: An open-source library designed for Blu-Ray Discs playback
* `fribidi`: The Free Implementation of the Unicode Bidirectional Algorithm
* `sdl`: A cross-platform development library designed to provide low level access to audio, keyboard, mouse, joystick, and graphics hardware via OpenGL and Direct3D
* `openjpeg`: Is an open-source JPEG 2000 codec written in C language
* `mediainfo`: A convenient unified display of the most relevant technical and tag data for video and audio files
* `xml2`: XML parser and toolkit
* `tiff`: This software provides support for the Tag Image File Format (TIFF), a widely used format for storing image data
* `mp4box/gpac`: Modular Multimedia framework for packaging, streaming and playing your favorite content, see http://netflix.gpac.io
* `alsa`: Advanced Linux Sound Architecture (ALSA) project. A library to interface with ALSA in the Linux kernel and virtual devices using a plugin system
* `bzlib` A general purpose data compression library
* `iconv`: Used to convert some text in one encoding into another encoding
* `lcms2`: A free, open source, CMM engine. It provides fast transforms between ICC profiles
* `libopencore_amr`: OpenCORE Adaptive Multi Rate (AMR) speech codec library implementation
* `vidstab`: A video stabilization library which can be plugged-in with Ffmpeg and Transcode
* `xcb`: C interface to the X Window System protocol, which replaces the traditional Xlib interface.
* `libxvid`: Xvid MPEG-4 Part 2 encoder wrapper

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
-------

```bash
building FFmpeg - version 5.1.3
====================================
The file "ffmpeg-5.1.3.tar.xz" is already downloaded.
File extracted: ffmpeg-5.1.3.tar.xz

install prefix            /home/jman/tmp/ffmpeg-build-script/workspace
source path               .
C compiler                gcc-12
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
alsa                    libaom                  libfreetype             libopencore_amrwb       libtheora               libx265                 lv2                     xlib
avisynth                libass                  libfribidi              libopenjpeg             libvidstab              libxcb                  lzma                    zlib
bzlib                   libbluray               libjxl                  libopus                 libvorbis               libxcb_shm              openssl
frei0r                  libdav1d                libkvazaar              librav1e                libvpx                  libxml2                 sdl2
iconv                   libfdk_aac              libmp3lame              libsrt                  libwebp                 libxvid                 sndio
lcms2                   libfontconfig           libopencore_amrnb       libsvtav1               libx264                 libzimg                 vapoursynth

External libraries providing hardware acceleration:
amf                     cuda_llvm               cuvid                   libnpp                  nvenc                   v4l2_m2m
cuda                    cuda_nvcc               ffnvcodec               nvdec                   opencl                  vulkan

Libraries:
avcodec                 avdevice                avfilter                avformat                avutil                  postproc                swresample              swscale

Programs:
ffmpeg                  ffplay                  ffprobe

Enabled decoders:
aac                     amrwb                   dpx                     hevc                    mp3                     pcm_s24daud             scpr                    vc1image
aac_fixed               amv                     dsd_lsbf                hevc_cuvid              mp3adu                  pcm_s24le               screenpresso            vcr1
aac_latm                anm                     dsd_lsbf_planar         hevc_v4l2m2m            mp3adufloat             pcm_s24le_planar        sdx2_dpcm               vmdaudio
aasc                    ansi                    dsd_msbf                hnm4_video              mp3float                pcm_s32be               sga                     vmdvideo
ac3                     ape                     dsd_msbf_planar         hq_hqa                  mp3on4                  pcm_s32le               sgi                     vmnc
ac3_fixed               apng                    dsicinaudio             hqx                     mp3on4float             pcm_s32le_planar        sgirle                  vorbis
acelp_kelvin            aptx                    dsicinvideo             huffyuv                 mpc7                    pcm_s64be               sheervideo              vp3
adpcm_4xm               aptx_hd                 dss_sp                  hymt                    mpc8                    pcm_s64le               shorten                 vp4
adpcm_adx               arbc                    dst                     iac                     mpeg1_cuvid             pcm_s8                  simbiosis_imx           vp5
adpcm_afc               argo                    dvaudio                 idcin                   mpeg1_v4l2m2m           pcm_s8_planar           sipr                    vp6
adpcm_agm               ass                     dvbsub                  idf                     mpeg1video              pcm_sga                 siren                   vp6a
adpcm_aica              asv1                    dvdsub                  iff_ilbm                mpeg2_cuvid             pcm_u16be               smackaud                vp6f
adpcm_argo              asv2                    dvvideo                 ilbc                    mpeg2_v4l2m2m           pcm_u16le               smacker                 vp7
adpcm_ct                atrac1                  dxa                     imc                     mpeg2video              pcm_u24be               smc                     vp8
adpcm_dtk               atrac3                  dxtory                  imm4                    mpeg4                   pcm_u24le               smvjpeg                 vp8_cuvid
adpcm_ea                atrac3al                dxv                     imm5                    mpeg4_cuvid             pcm_u32be               snow                    vp8_v4l2m2m
adpcm_ea_maxis_xa       atrac3p                 eac3                    indeo2                  mpeg4_v4l2m2m           pcm_u32le               sol_dpcm                vp9
adpcm_ea_r1             atrac3pal               eacmv                   indeo3                  mpegvideo               pcm_u8                  sonic                   vp9_cuvid
adpcm_ea_r2             atrac9                  eamad                   indeo4                  mpl2                    pcm_vidc                sp5x                    vp9_v4l2m2m
adpcm_ea_r3             aura                    eatgq                   indeo5                  msa1                    pcx                     speedhq                 vplayer
adpcm_ea_xas            aura2                   eatgv                   interplay_acm           mscc                    pfm                     speex                   vqa
adpcm_g722              av1                     eatqi                   interplay_dpcm          msmpeg4v1               pgm                     srgc                    wavpack
adpcm_g726              av1_cuvid               eightbps                interplay_video         msmpeg4v2               pgmyuv                  srt                     wcmv
adpcm_g726le            avrn                    eightsvx_exp            ipu                     msmpeg4v3               pgssub                  ssa                     webp
adpcm_ima_acorn         avrp                    eightsvx_fib            jacosub                 msnsiren                pgx                     stl                     webvtt
adpcm_ima_alp           avs                     escape124               jpeg2000                msp2                    phm                     subrip                  wmalossless
adpcm_ima_amv           avui                    escape130               jpegls                  msrle                   photocd                 subviewer               wmapro
adpcm_ima_apc           ayuv                    evrc                    jv                      mss1                    pictor                  subviewer1              wmav1
adpcm_ima_apm           bethsoftvid             exr                     kgv1                    mss2                    pixlet                  sunrast                 wmav2
adpcm_ima_cunning       bfi                     fastaudio               kmvc                    msvideo1                pjs                     svq1                    wmavoice
adpcm_ima_dat4          bink                    ffv1                    lagarith                mszh                    png                     svq3                    wmv1
adpcm_ima_dk3           binkaudio_dct           ffvhuff                 libaom_av1              mts2                    ppm                     tak                     wmv2
adpcm_ima_dk4           binkaudio_rdft          ffwavesynth             libdav1d                mv30                    prores                  targa                   wmv3
adpcm_ima_ea_eacs       bintext                 fic                     libfdk_aac              mvc1                    prosumer                targa_y216              wmv3image
adpcm_ima_ea_sead       bitpacked               fits                    libjxl                  mvc2                    psd                     tdsc                    wnv1
adpcm_ima_iss           bmp                     flac                    libopencore_amrnb       mvdv                    ptx                     text                    wrapped_avframe
adpcm_ima_moflex        bmv_audio               flashsv                 libopencore_amrwb       mvha                    qcelp                   theora                  ws_snd1
adpcm_ima_mtf           bmv_video               flashsv2                libopenjpeg             mwsc                    qdm2                    thp                     xan_dpcm
adpcm_ima_oki           brender_pix             flic                    libopus                 mxpeg                   qdmc                    tiertexseqvideo         xan_wc3
adpcm_ima_qt            c93                     flv                     libvorbis               nellymoser              qdraw                   tiff                    xan_wc4
adpcm_ima_rad           cavs                    fmvc                    libvpx_vp8              notchlc                 qoi                     tmv                     xbin
adpcm_ima_smjpeg        ccaption                fourxm                  libvpx_vp9              nuv                     qpeg                    truehd                  xbm
adpcm_ima_ssi           cdgraphics              fraps                   loco                    on2avc                  qtrle                   truemotion1             xface
adpcm_ima_wav           cdtoons                 frwu                    lscr                    opus                    r10k                    truemotion2             xl
adpcm_ima_ws            cdxl                    g2m                     m101                    paf_audio               r210                    truemotion2rt           xma1
adpcm_ms                cfhd                    g723_1                  mace3                   paf_video               ra_144                  truespeech              xma2
adpcm_mtaf              cinepak                 g729                    mace6                   pam                     ra_288                  tscc                    xpm
adpcm_psx               clearvideo              gdv                     magicyuv                pbm                     ralf                    tscc2                   xsub
adpcm_sbpro_2           cljr                    gem                     mdec                    pcm_alaw                rasc                    tta                     xwd
adpcm_sbpro_3           cllc                    gif                     metasound               pcm_bluray              rawvideo                twinvq                  y41p
adpcm_sbpro_4           comfortnoise            gremlin_dpcm            microdvd                pcm_dvd                 realtext                txd                     ylc
adpcm_swf               cook                    gsm                     mimic                   pcm_f16le               rl2                     ulti                    yop
adpcm_thp               cpia                    gsm_ms                  mjpeg                   pcm_f24le               roq                     utvideo                 yuv4
adpcm_thp_le            cri                     h261                    mjpeg_cuvid             pcm_f32be               roq_dpcm                v210                    zero12v
adpcm_vima              cscd                    h263                    mjpegb                  pcm_f32le               rpza                    v210x                   zerocodec
adpcm_xa                cyuv                    h263_v4l2m2m            mlp                     pcm_f64be               rscc                    v308                    zlib
adpcm_yamaha            dca                     h263i                   mmvideo                 pcm_f64le               rv10                    v408                    zmbv
adpcm_zork              dds                     h263p                   mobiclip                pcm_lxf                 rv20                    v410
agm                     derf_dpcm               h264                    motionpixels            pcm_mulaw               rv30                    vb
aic                     dfa                     h264_cuvid              movtext                 pcm_s16be               rv40                    vble
alac                    dfpwm                   h264_v4l2m2m            mp1                     pcm_s16be_planar        s302m                   vbn
alias_pix               dirac                   hap                     mp1float                pcm_s16le               sami                    vc1
als                     dnxhd                   hca                     mp2                     pcm_s16le_planar        sanm                    vc1_cuvid
amrnb                   dolby_e                 hcom                    mp2float                pcm_s24be               sbc                     vc1_v4l2m2m

Enabled encoders:
a64multi                ass                     flashsv2                libsvtav1               pam                     pcm_u16le               rv10                    vbn
a64multi5               asv1                    flv                     libtheora               pbm                     pcm_u24be               rv20                    vc2
aac                     asv2                    g723_1                  libvorbis               pcm_alaw                pcm_u24le               s302m                   vorbis
ac3                     avrp                    gif                     libvpx_vp8              pcm_bluray              pcm_u32be               sbc                     vp8_v4l2m2m
ac3_fixed               avui                    h261                    libvpx_vp9              pcm_dvd                 pcm_u32le               sgi                     wavpack
adpcm_adx               ayuv                    h263                    libwebp                 pcm_f32be               pcm_u8                  smc                     webvtt
adpcm_argo              bitpacked               h263_v4l2m2m            libx264                 pcm_f32le               pcm_vidc                snow                    wmav1
adpcm_g722              bmp                     h263p                   libx264rgb              pcm_f64be               pcx                     sonic                   wmav2
adpcm_g726              cfhd                    h264_amf                libx265                 pcm_f64le               pfm                     sonic_ls                wmv1
adpcm_g726le            cinepak                 h264_nvenc              libxvid                 pcm_mulaw               pgm                     speedhq                 wmv2
adpcm_ima_alp           cljr                    h264_v4l2m2m            ljpeg                   pcm_s16be               pgmyuv                  srt                     wrapped_avframe
adpcm_ima_amv           comfortnoise            hevc_amf                magicyuv                pcm_s16be_planar        phm                     ssa                     xbm
adpcm_ima_apm           dca                     hevc_nvenc              mjpeg                   pcm_s16le               png                     subrip                  xface
adpcm_ima_qt            dfpwm                   hevc_v4l2m2m            mlp                     pcm_s16le_planar        ppm                     sunrast                 xsub
adpcm_ima_ssi           dnxhd                   huffyuv                 movtext                 pcm_s24be               prores                  svq1                    xwd
adpcm_ima_wav           dpx                     jpeg2000                mp2                     pcm_s24daud             prores_aw               targa                   y41p
adpcm_ima_ws            dvbsub                  jpegls                  mp2fixed                pcm_s24le               prores_ks               text                    yuv4
adpcm_ms                dvdsub                  libaom_av1              mpeg1video              pcm_s24le_planar        qoi                     tiff                    zlib
adpcm_swf               dvvideo                 libfdk_aac              mpeg2video              pcm_s32be               qtrle                   truehd                  zmbv
adpcm_yamaha            eac3                    libjxl                  mpeg4                   pcm_s32le               r10k                    tta
alac                    exr                     libkvazaar              mpeg4_v4l2m2m           pcm_s32le_planar        r210                    ttml
alias_pix               ffv1                    libmp3lame              msmpeg4v2               pcm_s64be               ra_144                  utvideo
amv                     ffvhuff                 libopencore_amrnb       msmpeg4v3               pcm_s64le               rawvideo                v210
apng                    fits                    libopenjpeg             msvideo1                pcm_s8                  roq                     v308
aptx                    flac                    libopus                 nellymoser              pcm_s8_planar           roq_dpcm                v408
aptx_hd                 flashsv                 librav1e                opus                    pcm_u16be               rpza                    v410

Enabled hwaccels:
av1_nvdec               hevc_nvdec              mpeg1_nvdec             mpeg4_nvdec             vp8_nvdec               wmv3_nvdec
h264_nvdec              mjpeg_nvdec             mpeg2_nvdec             vc1_nvdec               vp9_nvdec

Enabled parsers:
aac                     avs3                    dnxhd                   flac                    h264                    mpegaudio               rv40                    vp8
aac_latm                bmp                     dolby_e                 g723_1                  hevc                    mpegvideo               sbc                     vp9
ac3                     cavsvideo               dpx                     g729                    ipu                     opus                    sipr                    webp
adx                     cook                    dvaudio                 gif                     jpeg2000                png                     tak                     xbm
amr                     cri                     dvbsub                  gsm                     mjpeg                   pnm                     vc1                     xma
av1                     dca                     dvd_nav                 h261                    mlp                     qoi                     vorbis
avs2                    dirac                   dvdsub                  h263                    mpeg4video              rv30                    vp3

Enabled demuxers:
aa                      bfi                     filmstrip               image_gif_pipe          lmlm4                   nsp                     rsd                     truehd
aac                     bfstm                   fits                    image_j2k_pipe          loas                    nsv                     rso                     tta
aax                     bink                    flac                    image_jpeg_pipe         lrc                     nut                     rtp                     tty
ac3                     binka                   flic                    image_jpegls_pipe       luodat                  nuv                     rtsp                    txd
ace                     bintext                 flv                     image_jpegxl_pipe       lvf                     obu                     s337m                   ty
acm                     bit                     fourxm                  image_pam_pipe          lxf                     ogg                     sami                    v210
act                     bitpacked               frm                     image_pbm_pipe          m4v                     oma                     sap                     v210x
adf                     bmv                     fsb                     image_pcx_pipe          matroska                paf                     sbc                     vag
adp                     boa                     fwse                    image_pfm_pipe          mca                     pcm_alaw                sbg                     vapoursynth
ads                     brstm                   g722                    image_pgm_pipe          mcc                     pcm_f32be               scc                     vc1
adx                     c93                     g723_1                  image_pgmyuv_pipe       mgsts                   pcm_f32le               scd                     vc1t
aea                     caf                     g726                    image_pgx_pipe          microdvd                pcm_f64be               sdp                     vividas
afc                     cavsvideo               g726le                  image_phm_pipe          mjpeg                   pcm_f64le               sdr2                    vivo
aiff                    cdg                     g729                    image_photocd_pipe      mjpeg_2000              pcm_mulaw               sds                     vmd
aix                     cdxl                    gdv                     image_pictor_pipe       mlp                     pcm_s16be               sdx                     vobsub
alp                     cine                    genh                    image_png_pipe          mlv                     pcm_s16le               segafilm                voc
amr                     codec2                  gif                     image_ppm_pipe          mm                      pcm_s24be               ser                     vpk
amrnb                   codec2raw               gsm                     image_psd_pipe          mmf                     pcm_s24le               sga                     vplayer
amrwb                   concat                  gxf                     image_qdraw_pipe        mods                    pcm_s32be               shorten                 vqf
anm                     dash                    h261                    image_qoi_pipe          moflex                  pcm_s32le               siff                    w64
apc                     data                    h263                    image_sgi_pipe          mov                     pcm_s8                  simbiosis_imx           wav
ape                     daud                    h264                    image_sunrast_pipe      mp3                     pcm_u16be               sln                     wc3
apm                     dcstr                   hca                     image_svg_pipe          mpc                     pcm_u16le               smacker                 webm_dash_manifest
apng                    derf                    hcom                    image_tiff_pipe         mpc8                    pcm_u24be               smjpeg                  webvtt
aptx                    dfa                     hevc                    image_vbn_pipe          mpegps                  pcm_u24le               smush                   wsaud
aptx_hd                 dfpwm                   hls                     image_webp_pipe         mpegts                  pcm_u32be               sol                     wsd
aqtitle                 dhav                    hnm                     image_xbm_pipe          mpegtsraw               pcm_u32le               sox                     wsvqa
argo_asf                dirac                   ico                     image_xpm_pipe          mpegvideo               pcm_u8                  spdif                   wtv
argo_brp                dnxhd                   idcin                   image_xwd_pipe          mpjpeg                  pcm_vidc                srt                     wv
argo_cvg                dsf                     idf                     imf                     mpl2                    pjs                     stl                     wve
asf                     dsicin                  iff                     ingenient               mpsub                   pmp                     str                     xa
asf_o                   dss                     ifv                     ipmovie                 msf                     pp_bnk                  subviewer               xbin
ass                     dts                     ilbc                    ipu                     msnwc_tcp               pva                     subviewer1              xmv
ast                     dtshd                   image2                  ircam                   msp                     pvf                     sup                     xvag
au                      dv                      image2_alias_pix        iss                     mtaf                    qcp                     svag                    xwma
av1                     dvbsub                  image2_brender_pix      iv8                     mtv                     r3d                     svs                     yop
avi                     dvbtxt                  image2pipe              ivf                     musx                    rawvideo                swf                     yuv4mpegpipe
avisynth                dxa                     image_bmp_pipe          ivr                     mv                      realtext                tak
avr                     ea                      image_cri_pipe          jacosub                 mvi                     redspark                tedcaptions
avs                     ea_cdata                image_dds_pipe          jv                      mxf                     rl2                     thp
avs2                    eac3                    image_dpx_pipe          kux                     mxg                     rm                      threedostr
avs3                    epaf                    image_exr_pipe          kvag                    nc                      roq                     tiertexseq
bethsoftvid             ffmetadata              image_gem_pipe          live_flv                nistsphere              rpl                     tmv

Enabled muxers:
a64                     avs2                    flac                    image2pipe              mpeg1system             pcm_f32le               roq                     tgp
ac3                     avs3                    flv                     ipod                    mpeg1vcd                pcm_f64be               rso                     truehd
adts                    bit                     framecrc                ircam                   mpeg1video              pcm_f64le               rtp                     tta
adx                     caf                     framehash               ismv                    mpeg2dvd                pcm_mulaw               rtp_mpegts              ttml
aiff                    cavsvideo               framemd5                ivf                     mpeg2svcd               pcm_s16be               rtsp                    uncodedframecrc
alp                     codec2                  g722                    jacosub                 mpeg2video              pcm_s16le               sap                     vc1
amr                     codec2raw               g723_1                  kvag                    mpeg2vob                pcm_s24be               sbc                     vc1t
amv                     crc                     g726                    latm                    mpegts                  pcm_s24le               scc                     voc
apm                     dash                    g726le                  lrc                     mpjpeg                  pcm_s32be               segafilm                w64
apng                    data                    gif                     m4v                     mxf                     pcm_s32le               segment                 wav
aptx                    daud                    gsm                     matroska                mxf_d10                 pcm_s8                  smjpeg                  webm
aptx_hd                 dfpwm                   gxf                     matroska_audio          mxf_opatom              pcm_u16be               smoothstreaming         webm_chunk
argo_asf                dirac                   h261                    md5                     null                    pcm_u16le               sox                     webm_dash_manifest
argo_cvg                dnxhd                   h263                    microdvd                nut                     pcm_u24be               spdif                   webp
asf                     dts                     h264                    mjpeg                   obu                     pcm_u24le               spx                     webvtt
asf_stream              dv                      hash                    mkvtimestamp_v2         oga                     pcm_u32be               srt                     wsaud
ass                     eac3                    hds                     mlp                     ogg                     pcm_u32le               stream_segment          wtv
ast                     f4v                     hevc                    mmf                     ogv                     pcm_u8                  streamhash              wv
au                      ffmetadata              hls                     mov                     oma                     pcm_vidc                sup                     yuv4mpegpipe
avi                     fifo_test               ico                     mp2                     opus                    psp                     swf
avif                    filmstrip               ilbc                    mp3                     pcm_alaw                rawvideo                tee
avm2                    fits                    image2                  mp4                     pcm_f32be               rm                      tg2

Enabled protocols:
bluray                  data                    gopher                  https                   md5                     rtmp                    rtmpts                  tee
cache                   ffrtmpcrypt             gophers                 icecast                 mmsh                    rtmpe                   rtp                     tls
concat                  ffrtmphttp              hls                     ipfs                    mmst                    rtmps                   srtp                    udp
concatf                 file                    http                    ipns                    pipe                    rtmpt                   subfile                 udplite
crypto                  ftp                     httpproxy               libsrt                  prompeg                 rtmpte                  tcp                     unix

Enabled filters:
abench                  aphasemeter             chromakey_cuda          drawgraph               hqx                     nlmeans                 scroll                  testsrc2
abitscope               aphaser                 chromanr                drawgrid                hstack                  nlmeans_opencl          segment                 thistogram
acompressor             aphaseshift             chromashift             drawtext                hsvhold                 nnedi                   select                  threshold
acontrast               apsyclip                ciescope                drmeter                 hsvkey                  noformat                selectivecolor          thumbnail
acopy                   apulsator               codecview               dynaudnorm              hue                     noise                   sendcmd                 thumbnail_cuda
acrossfade              arealtime               color                   earwax                  huesaturation           normalize               separatefields          tile
acrossover              aresample               colorbalance            ebur128                 hwdownload              null                    setdar                  tiltshelf
acrusher                areverse                colorchannelmixer       edgedetect              hwmap                   nullsink                setfield                tinterlace
acue                    arnndn                  colorchart              elbg                    hwupload                nullsrc                 setparams               tlut2
addroi                  asdr                    colorcontrast           entropy                 hwupload_cuda           openclsrc               setpts                  tmedian
adeclick                asegment                colorcorrect            epx                     hysteresis              oscilloscope            setrange                tmidequalizer
adeclip                 aselect                 colorhold               eq                      iccdetect               overlay                 setsar                  tmix
adecorrelate            asendcmd                colorize                equalizer               iccgen                  overlay_cuda            settb                   tonemap
adelay                  asetnsamples            colorkey                erosion                 identity                overlay_opencl          sharpen_npp             tonemap_opencl
adenorm                 asetpts                 colorkey_opencl         erosion_opencl          idet                    owdenoise               shear                   tpad
aderivative             asetrate                colorlevels             estdif                  il                      pad                     showcqt                 transpose
adrawgraph              asettb                  colormap                exposure                inflate                 pad_opencl              showfreqs               transpose_npp
adynamicequalizer       ashowinfo               colormatrix             extractplanes           interlace               pal100bars              showinfo                transpose_opencl
adynamicsmooth          asidedata               colorspace              extrastereo             interleave              pal75bars               showpalette             treble
aecho                   asoftclip               colorspectrum           fade                    join                    palettegen              showspatial             tremolo
aemphasis               aspectralstats          colortemperature        feedback                kerndeint               paletteuse              showspectrum            trim
aeval                   asplit                  compand                 fftdnoiz                kirsch                  pan                     showspectrumpic         unpremultiply
aevalsrc                ass                     compensationdelay       fftfilt                 lagfun                  perms                   showvolume              unsharp
aexciter                astats                  concat                  field                   latency                 perspective             showwaves               unsharp_opencl
afade                   astreamselect           convolution             fieldhint               lenscorrection          phase                   showwavespic            untile
afftdn                  asubboost               convolution_opencl      fieldmatch              life                    photosensitivity        shuffleframes           v360
afftfilt                asubcut                 convolve                fieldorder              limitdiff               pixdesctest             shufflepixels           vaguedenoiser
afifo                   asupercut               copy                    fifo                    limiter                 pixelize                shuffleplanes           varblur
afir                    asuperpass              cover_rect              fillborders             loop                    pixscope                sidechaincompress       vectorscope
afirsrc                 asuperstop              crop                    find_rect               loudnorm                pp                      sidechaingate           vflip
aformat                 atadenoise              cropdetect              firequalizer            lowpass                 pp7                     sidedata                vfrdet
afreqshift              atempo                  crossfeed               flanger                 lowshelf                premultiply             sierpinski              vibrance
afwtdn                  atilt                   crystalizer             floodfill               lumakey                 prewitt                 signalstats             vibrato
agate                   atrim                   cue                     format                  lut                     prewitt_opencl          signature               vidstabdetect
agraphmonitor           avectorscope            curves                  fps                     lut1d                   program_opencl          silencedetect           vidstabtransform
ahistogram              avgblur                 datascope               framepack               lut2                    pseudocolor             silenceremove           vif
aiir                    avgblur_opencl          dblur                   framerate               lut3d                   psnr                    sinc                    vignette
aintegral               avsynctest              dcshift                 framestep               lutrgb                  pullup                  sine                    virtualbass
ainterleave             axcorrelate             dctdnoiz                freezedetect            lutyuv                  qp                      siti                    vmafmotion
alatency                bandpass                deband                  freezeframes            lv2                     random                  smartblur               volume
alimiter                bandreject              deblock                 frei0r                  mandelbrot              readeia608              smptebars               volumedetect
allpass                 bass                    decimate                frei0r_src              maskedclamp             readvitc                smptehdbars             vstack
allrgb                  bbox                    deconvolve              fspp                    maskedmax               realtime                sobel                   w3fdif
allyuv                  bench                   dedot                   gblur                   maskedmerge             remap                   sobel_opencl            waveform
aloop                   bilateral               deesser                 geq                     maskedmin               remap_opencl            spectrumsynth           weave
alphaextract            biquad                  deflate                 gradfun                 maskedthreshold         removegrain             speechnorm              xbr
alphamerge              bitplanenoise           deflicker               gradients               maskfun                 removelogo              split                   xcorrelate
amerge                  blackdetect             dejudder                graphmonitor            mcompand                repeatfields            spp                     xfade
ametadata               blackframe              delogo                  grayworld               median                  replaygain              sr                      xfade_opencl
amix                    blend                   derain                  greyedge                mergeplanes             reverse                 ssim                    xmedian
amovie                  blockdetect             deshake                 guided                  mestimate               rgbashift               stereo3d                xstack
amplify                 blurdetect              deshake_opencl          haas                    metadata                rgbtestsrc              stereotools             yadif
amultiply               bm3d                    despill                 haldclut                midequalizer            roberts                 stereowiden             yadif_cuda
anequalizer             boxblur                 detelecine              haldclutsrc             minterpolate            roberts_opencl          streamselect            yaepblur
anlmdn                  boxblur_opencl          dialoguenhance          hdcd                    mix                     rotate                  subtitles               yuvtestsrc
anlmf                   bwdif                   dilation                headphone               monochrome              sab                     super2xsai              zoompan
anlms                   cas                     dilation_opencl         hflip                   morpho                  scale                   superequalizer          zscale
anoisesrc               cellauto                displace                highpass                movie                   scale2ref               surround
anull                   channelmap              dnn_classify            highshelf               mpdecimate              scale2ref_npp           swaprect
anullsink               channelsplit            dnn_detect              hilbert                 mptestsrc               scale_cuda              swapuv
anullsrc                chorus                  dnn_processing          histeq                  msad                    scale_npp               tblend
apad                    chromahold              doubleweave             histogram               multiply                scdet                   telecine
aperms                  chromakey               drawbox                 hqdn3d                  negate                  scharr                  testsrc

Enabled bsfs:
aac_adtstoasc           dca_core                filter_units            hevc_metadata           mov2textsub             null                    remove_extradata        vp9_metadata
av1_frame_merge         dump_extradata          h264_metadata           hevc_mp4toannexb        mp3_header_decompress   opus_metadata           setts                   vp9_raw_reorder
av1_frame_split         dv_error_marker         h264_mp4toannexb        imx_dump_header         mpeg2_metadata          pcm_rechunk             text2movsub             vp9_superframe
av1_metadata            eac3_core               h264_redundant_pps      mjpeg2jpeg              mpeg4_unpack_bframes    pgs_frame_merge         trace_headers           vp9_superframe_split
chomp                   extract_extradata       hapqa_extract           mjpega_dump_header      noise                   prores_metadata         truehd_core

Enabled indevs:
alsa                    fbdev                   lavfi                   oss                     sndio                   v4l2                    xcbgrab

Enabled outdevs:
alsa                    fbdev                   oss                     sdl2                    sndio                   v4l2                    xv
```
