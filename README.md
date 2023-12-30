### If you like the script, please "★" this project!

[ffmpeg-build-script](https://ffmpeg.org/download.html)
==========

The FFmpeg build script provides an easy way to build a **<ins>static</ins>** FFmpeg binary with **non-free and GPL codecs** by using API calls to download the latest source code available.
  - See https://ffmpeg.org/legal.html)

- **Compiles the latest updates from source code by issuing API calls to each repository backend**
  - **The CUDA SDK Toolkit which unlocks Hardware Acceleration is available during the installation to make things as easy as possible**
  - **Supported OS:**
    - Arch Linux
    - Debian - 11/12
    - Ubuntu - (20/22/23).04
    - Other debian style distros may work as well

## Important GitHub API info
**Be aware** that without using a pre-created API Token from GitHub, you are limited to ***50 API calls a day***. This is important because the script has ***44+ repositories*** with API calls during the build. If you stop the script in the middle of the build and restart (potentially over and over) you will eventually eat up the 50-call limit and be forced to wait to continue ***unless*** you change the curl code under the function `git_1_fn` and put in your own [token](https://github.com/settings/tokens?type=beta).

### If you start the build ***<ins>let it finish</ins>***

See the below example on how to put your token into the script.
  - replace both of the `curl_cmd` variables inside the `git_1_fn` function with your token as shown below

```
    git_token='github_pat_blahblahblahblah'

    if curl_cmd="$(curl                                                                                                            \
                        -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
                        -m 10                                                                                                      \
                        --request GET                                                                                              \
                        --url "https://api.github.com/<replace with token name>"                                                   \
                        --header "Authorization: Bearer ${git_token}"                                                              \
                        --header "X-GitHub-Api-Version: 2022-11-28"                                                                \
                        -sSL "https://api.github.com/repos/${git_repo}/${git_url}")"; then
```

## Disclaimer And Data Privacy Notice

This script will download different packages with different licenses from various sources, which may track your usage. This includes the CUDA SDK Toolkit.
These sources are in control of the developers of each script which I have no control over.

**Importantly**, this script creates a <ins>**non-free**</ins> and unredistributable binary at its end, AND by downloading and using this script, you are <ins>**fully aware of this**</ins>.

Use this script at your own risk. I maintain this script in my spare time. Please do not file bug reports for systems other than those based on Debian or Arch Linux.

## Install methods
### With GPL and non-free software, see https://ffmpeg.org/legal.html

#### The standard build script will build everything minus the NDI library.
[build-ffmpeg](https://github.com/slyfox1186/ffmpeg-build-script/blob/main/build-ffmpeg)

This command clones the build script and starts the build.

```bash
git clone 'https://github.com/slyfox1186/ffmpeg-build-script.git'
cd 'ffmpeg-build-script' || exit 1
bash 'build-ffmpeg' --build --latest
```

#### The NDI build script is not officially supported by either FFmpeg or the NDI creators and I take no responsibility for people who use it in ways the developers have told you not to. I do not support or condone this behavior. If you want to use it use it within the aspects of the law.
[NDI build script](https://github.com/slyfox1186/script-repo/blob/main/Bash/Installer%20Scripts/FFmpeg/build-ffmpeg-NDI)

### Quick installation

This command downloads the build script and automatically starts the build process.

```bash
bash <(curl -fsSL 'https://ffmpeg.optimizethis.net') --build --latest
```

## Supported Codecs

* `x264`: H.264 Video Codec (MPEG-4 AVC)
* `x265`: H.265 Video Codec (HEVC)
* `cuda`: Hardware acceleration for Nvidia graphics cards
* `ff-nvcodec-headers`: FFmpeg version of headers required to interface with Nvidias codec APIs (Hardware Acceleration)
* `aom`: AV1 Video Codec (Experimental and very slow!)
* `vpx`: VP8 / VP9 Video Codec for the WebM video file format
* `svtav1`: SVT-AV1 Encoder and Decoder
* `rav1e`: rust based AV1 encoder
* `avisynth`: A powerful tool for video post-production
* `vapoursynth`: An application for video manipulation.
* `cyanrip`: Fully featured CD ripping program which is able to take out most of the tedium. Wholly accurate, has advanced features most rippers don't, yet has no bloat and is cross-platform.
* `libfdk_aac`: Fraunhofer FDK AAC Codec
* `libopus`: Lossy audio coding format
* `libmp3lame`: MPEG-1 or MPEG-2 Audio Layer III
* `ogg`: Free, open container format
* `opencore-amr`: Adaptive Multi-Rate (AMR) speech codec library implementation
* `vorbis`: Lossy audio compression format
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format
* `libbluray`: An open-source library designed for Blu-Ray Discs playback
* `mp4box/gpac`: Modular Multimedia framework for packaging, streaming, and playing your favorite content, see http://netflix.gpac.io
* `kvazaar`: An open-source HEVC encoder licensed under 3-clause BSD
* `frei0r` A collection of free and open source video effects plugins that can be used with a variety of video editing and processing software
* `opencl`: An open-source project that uses Boost. Compute as a high-level C++ wrapper over the OpenCL API
* `dav1d`: Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities and sponsored by the AOMedia (only available if `meson` and `ninja` are installed)
* `webp`: Image format both lossless and lossy
* `xvidcore`: MPEG-4 video coding standard
* `theora`: Free lossy video compression format
* `flac`: Free Lossless Audio Codec is open-source software that can reduce the amount of storage space needed to store digital audio signals without needing to remove information in doing so
* `jxl`: JPEG XL offers significantly better image quality and compression ratios than legacy JPEG, plus a shorter specification
* `openjpeg`: Is an open-source JPEG 2000 codec written in C language
* `srt`: Secure Reliable Transport (SRT) is a transport protocol for ultra-low (sub-second) latency live video and audio streaming, as well as for generic bulk data transfer
* `harfbuzz`: Text shaping image processor
* `fontconfig`: Font configuration and customization library
* `freetype`: A freely available software library to render fonts
* `fribidi`: The Free Implementation of the Unicode Bidirectional Algorithm
* `sdl2`: A cross-platform development library designed to provide low-level access to audio, keyboard, mouse, joystick, and graphics hardware via OpenGL and Direct3D
* `mediainfo`: A convenient unified display of the most relevant technical and tag data for video and audio files
* `xml2`: XML parser and toolkit
* `libtiff`: This software provides support for the Tag Image File Format (TIFF), a widely used format for storing image data
* `alsa`: Advanced Linux Sound Architecture (ALSA) project. A library to interface with ALSA in the Linux kernel and virtual devices using a plugin system
* `bzlib` A general-purpose data compression library
* `iconv`: Used to convert some text in one encoding into another encoding
* `lcms2`: A free, open-source, CMM engine. It provides fast transforms between ICC profiles
* `libopencore_amr`: OpenCORE Adaptive Multi-Rate (AMR) speech codec library implementation
* `vidstab`: A video stabilization library which can be plugged in with Ffmpeg and Transcode
* `xcb`: A C language interface to the X Window System protocol, which replaces the traditional Xlib interface
* `libxvid`: Xvid MPEG-4 Part 2 encoder wrapper
* `libsnappy`: Snappy is a compression/decompression library
* `libv4l2`: Is a collection of libraries that adds a thin abstraction layer on top of video4linux2 devices
* `sndio`: Is a small audio and MIDI framework part of the OpenBSD project and ported to FreeBSD, Linux and NetBSD
* `libsoxr`: The SoX Resampler library `libsoxr' performs one-dimensional sample-rate conversion
* `libbs2b`: Is designed to improve headphone listening of stereo audio records
* `libgme`: Is a collection of video game music file emulators
* `libspeex`: Is an Open Source/Free Software patent-free audio compression format designed for speech
* `libvo_amrwbenc`: This library contains an encoder implementation of the Adaptive Multi-Rate Wideband (AMR-WB) audio codec
* `xlib`: Is a C subroutine library that application programs (clients) use to interface with the window system by means of a stream connection
* `libcaca`: Is a graphics library that outputs text instead of pixels, so that it can work on older video cards or text terminals
* `libpulse`: A featureful, general-purpose sound server 
* `libzimg`: The "z" library implements the commonly required image processing basics of scaling, colorspace conversion, and depth conversion
* `zlib`: Is a general-purpose data compression library
* `libcdio`: Is a library for CD-ROM and CD image access
* `libssh`: Is a multiplatform C library implementing the SSHv2 protocol on the client and server side
* `lv2`: Is an extensible open standard for audio plugins
* `ladspa`: Is an acronym for Linux Audio Developer's Simple Plugin API
* `libmodplug`: A library which was part of the Modplug-xmms project: http://modplug-xmms.sf.net/
* `librubberband`: An audio time-stretching and pitch-shifting library and utility program
* `lzma`: Is an algorithm used to perform lossless data compression
* `libshine`: Shine is a fixed-point MP3 encoder. It has a far better performance on platforms without an FPU, e.g. armel CPUs, and some phones and tablets
* `libtesseract`: This package contains an OCR engine - libtesseract and a command line program - tesseract
* `opengl`: Is a cross-language, cross-platform application programming interface for rendering 2D and 3D vector graphics
* `libflite`: Provides a high-level text-to-speech interface for English based on the 'libflite' library
* `libmysofa`: Is a simple set of C functions to read AES SOFA files, if they contain HRTFs stored according to the AES69-2015 standard
* `libsmbclient`: Is a library toolset that permits applications to manipulate CIFS/SMB network resources using many of the standards POSIX functions available for manipulating local UNIX/Linux files
* `openssl`: Is a software library for applications that provide secure communications over computer networks against eavesdropping, and identify the party at the other end
* `libaribb24`: A library for ARIB STD-B24, decoding JIS 8 bit characters and parsing MPEG-TS stream 
* `libtwolame`: Is an optimized MPEG Audio Layer 2 (MP2) encoder based on tooLAME by Mike Cheng, which in turn is based upon the ISO dist10 code and portions of LAME
* `chromaprint`: Is an audio fingerprinting library that calculates fingerprints used by the Acoustid service. It's the core component of the AcoustID project.
* `DeckLink`: DeckLink cards are open standard capture cards and are perfect for the development of Linux based video applications

### HardwareAccel

* `nv-codec`: [CUDA SDK Toolkit Download](https://developer.nvidia.com/cuda-downloads/).
  Follow the script's instructions to install the latest updates.
  These encoders/decoders will only be available if a CUDA installation was found while building ffmpeg.
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
  - All required packages should be downloaded by the script.

Example Output
-------

```bash
 -------------------------
|                         |
| Installing Global Tools |
|                         |
 -------------------------

Building m4 - version latest
====================================
Downloading "https://ftp.gnu.org/gnu/m4/m4-latest.tar.xz" saving as "m4-latest.tar.xz"
Download Completed
File extracted: m4-latest.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu --target=x86_64-linux-gnu --disable-nls --enable-c++
$ make -j32
$ make install

Building autoconf - version latest
====================================
Downloading "http://ftp.gnu.org/gnu/autoconf/autoconf-latest.tar.xz" saving as "autoconf-latest.tar.xz"
Download Completed
File extracted: autoconf-latest.tar.xz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building libtool - version 2.4.7
====================================
Downloading "https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz" saving as "libtool-2.4.7.tar.xz"
Download Completed
File extracted: libtool-2.4.7.tar.xz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu --with-pic M4=/home/jman/tmp/ffmpeg-build-script/workspace/bin/m4
$ make -j32
$ make install

Building pkg-config - version 0.29.2
====================================
Downloading "https://pkgconfig.freedesktop.org/releases/pkg-config-0.29.2.tar.gz" saving as "pkg-config-0.29.2.tar.gz"
Download Completed
File extracted: pkg-config-0.29.2.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --with-pc-path=/home/jman/tmp/ffmpeg-build-script/workspace/usr/lib/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/lib64/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/lib/x86_64-linux-gnu/pkgconfig:/home/jman/tmp/ffmpeg-build-script/workspace/share/pkgconfig:/usr/local/lib64/pkgconfig:/usr/local/lib/pkgconfig:/usr/local/lib/x86_64-linux-gnu/pkgconfig:/usr/local/share/pkgconfig:/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/open-coarrays/openmpi/pkgconfig:/usr/lib/x86_64-linux-gnu/openmpi/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/share/pkgconfig:/lib64/pkgconfig:/lib/pkgconfig:/lib/x86_64-linux-gnu/pkgconfig
$ make -j32
$ make install

Building zlib - version 1.3
====================================
Downloading "https://github.com/madler/zlib/releases/download/v1.3/zlib-1.3.tar.gz" saving as "zlib-1.3.tar.gz"
Download Completed
File extracted: zlib-1.3.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

Building openssl - version 3.1.3
====================================
Downloading "https://www.openssl.org/source/openssl-3.1.3.tar.gz" saving as "openssl-3.1.3.tar.gz"
Download Completed
File extracted: openssl-3.1.3.tar.gz

$ ./Configure --prefix=/usr/local enable-egd enable-fips enable-md2 enable-rc5 enable-trace threads zlib --with-rand-seed=os --with-zlib-include=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-zlib-lib=/home/jman/tmp/ffmpeg-build-script/workspace/lib
$ make -j32
$ sudo make install_sw
$ sudo make install_fips

Building yasm - version 1.3.0
====================================
Downloading "https://github.com/yasm/yasm/archive/refs/tags/v1.3.0.tar.gz" saving as "yasm-1.3.0.tar.gz"
Download Completed
File extracted: yasm-1.3.0.tar.gz

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building nasm - version 2.16.01
====================================
Downloading "https://www.nasm.us/pub/nasm/stable/nasm-2.16.01.tar.xz" saving as "nasm-2.16.01.tar.xz"
Download Completed
File extracted: nasm-2.16.01.tar.xz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu --target=x86_64-linux-gnu --disable-pedantic --enable-ccache
$ make -j32
$ make install

Building giflib - version 5.2.1
====================================
Downloading "https://cfhcable.dl.sourceforge.net/project/giflib/giflib-5.2.1.tar.gz" saving as "giflib-5.2.1.tar.gz"
Download Completed
File extracted: giflib-5.2.1.tar.gz

$ make
$ make PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install

Building xml2 - version 2.11.5
====================================
Downloading "https://gitlab.gnome.org/GNOME/libxml2/-/archive/v2.11.5/libxml2-v2.11.5.tar.bz2" saving as "xml2-2.11.5.tar.bz2"
Download Completed
File extracted: xml2-2.11.5.tar.bz2

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_EXPORT_COMPILE_COMMANDS=OFF -DCMAKE_VERBOSE_MAKEFILE=OFF -DCPACK_BINARY_DEB=ON -DCPACK_BINARY_FREEBSD=ON -DCPACK_BINARY_IFW=ON -DCPACK_BINARY_NSIS=ON -DCPACK_BINARY_RPM=ON -DCPACK_BINARY_TBZ2=ON -DCPACK_BINARY_TXZ=ON -DCPACK_SOURCE_RPM=ON -DCPACK_SOURCE_ZIP=ON -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libpng - version 1.6.40
====================================
Downloading "https://github.com/glennrp/libpng/archive/refs/tags/v1.6.40.tar.gz" saving as "libpng-1.6.40.tar.gz"
Download Completed
File extracted: libpng-1.6.40.tar.gz

$ autoupdate
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --enable-hardware-optimizations --enable-unversioned-links
$ make -j32
$ make install-header-links
$ make install-library-links
$ make install

Building aribb24 - version 2.16.01
====================================
Downloading "https://github.com/nkoriyama/aribb24/archive/refs/tags/v1.0.3.tar.gz" saving as "aribb24-1.0.3.tar.gz"
Download Completed
File extracted: aribb24-1.0.3.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --with-pic PKG_CONFIG=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config
$ make -j32
$ make install

Building freetype - version 2.13.2
====================================
Downloading "https://gitlab.freedesktop.org/freetype/freetype/-/archive/VER-2-13-2/freetype-VER-2-13-2.tar.bz2" saving as "freetype-2.13.2.tar.bz2"
Download Completed
File extracted: freetype-2.13.2.tar.bz2

$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dharfbuzz=disabled -Dpng=disabled -Dbzip2=disabled -Dbrotli=disabled -Dzlib=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building fontconfig - version 2.14.2
====================================
Downloading "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/2.14.2/fontconfig-2.14.2.tar.bz2" saving as "fontconfig-2.14.2.tar.bz2"
Download Completed
File extracted: fontconfig-2.14.2.tar.bz2

$ ./autogen.sh --noconf
$ autoreconf -fi
$ autoupdate
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-docs --disable-shared
$ make -j32
$ make install

Building harfbuzz - version 8.2.1
====================================
Downloading "https://github.com/harfbuzz/harfbuzz/archive/refs/tags/8.2.1.tar.gz" saving as "harfbuzz-8.2.1.tar.gz"
Download Completed
File extracted: harfbuzz-8.2.1.tar.gz

$ ./autogen.sh
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbenchmark=disabled -Dcairo=disabled -Ddocs=disabled -Dglib=disabled -Dgobject=disabled -Dicu=disabled -Dintrospection=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building c2man - version git
====================================
Downloading https://github.com/fribidi/c2man.git as c2man-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/c2man-git

$ ./Configure -desO -D prefix=/home/jman/tmp/ffmpeg-build-script/workspace -D bin=/home/jman/tmp/ffmpeg-build-script/workspace/bin -D bash=/usr/local/bin/bash -D cc=/usr/bin/cc -D d_gnu=/usr/lib/x86_64-linux-gnu -D find=/usr/bin/find -D gcc=/usr/bin/gcc -D gzip=/usr/bin/gzip -D installmansrc=/home/jman/tmp/ffmpeg-build-script/workspace/share/man -D ldflags=-L/home/jman/tmp/ffmpeg-build-script/workspace/lib64 -L/home/jman/tmp/ffmpeg-build-script/workspace/lib -L/home/jman/tmp/ffmpeg-build-script/workspace/lib/x86_64-linux-gnu -L/usr/local/lib64 -L/usr/local/lib -L/usr/lib/x86_64-linux-gnu -L/usr/lib64 -L/usr/lib -L/lib64 -L/lib -DLIBXML_STATIC -D less=/usr/bin/less -D libpth=/lib /usr/lib -D uniq=/usr/bin/uniq -D tr=/usr/bin/tr -D locincpth=/home/jman/tmp/ffmpeg-build-script/workspace/include /usr/local/include /usr/include -D yacc=/usr/bin/yacc -D loclibpth=/home/jman/tmp/ffmpeg-build-script/workspace/lib /usr/local/lib -D make=/usr/local/bin/make -D troff=/usr/bin/troff -D more=/usr/bin/more -D osname=Debian -D perl=/usr/bin/perl -D privlib=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man -D privlibexp=/home/jman/tmp/ffmpeg-build-script/workspace/lib/c2man -D sleep=/usr/bin/sleep -D tail=/usr/bin/tail -D tar=/usr/local/bin/tar -D uuname=Linux -D vi=/usr/bin/vi -D zip=/usr/bin/zip
$ make depend
$ make -j32
$ sudo make install

Building fribidi - version 1.0.13
====================================
Downloading "https://github.com/fribidi/fribidi/archive/refs/tags/v1.0.13.tar.gz" saving as "fribidi-1.0.13.tar.gz"
Download Completed
File extracted: fribidi-1.0.13.tar.gz

$ autoreconf -fi
$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=false -Dtests=false
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libass - version 0.17.1
====================================
Downloading "https://github.com/libass/libass/archive/refs/tags/0.17.1.tar.gz" saving as "libass-0.17.1.tar.gz"
Download Completed
File extracted: libass-0.17.1.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building freeglut - version 3.4.0
====================================
Downloading "https://github.com/freeglutproject/freeglut/archive/refs/tags/v3.4.0.tar.gz" saving as "freeglut-3.4.0.tar.gz"
Download Completed
File extracted: freeglut-3.4.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DFREEGLUT_BUILD_SHARED_LIBS=OFF -DFREEGLUT_GLES=OFF -DFREEGLUT_PRINT_WARNINGS=OFF -DFREEGLUT_WAYLAND=OFF -G Ninja -Wno-dev -DFREEGLUT_BUILD_STATIC_LIBS=ON -DFREEGLUT_PRINT_ERRORS=ON -DFREEGLUT_REPLACE_GLUT=ON
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libtiff - version 4.6.0
====================================
Downloading "https://gitlab.com/libtiff/libtiff/-/archive/v4.6.0/libtiff-v4.6.0.tar.bz2" saving as "libtiff-4.6.0.tar.bz2"
Download Completed
File extracted: libtiff-4.6.0.tar.bz2

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu --disable-shared
$ make -j32
$ make install

Building libwebp - version git
====================================
Downloading https://chromium.googlesource.com/webm/libwebp as libwebp-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/libwebp-git

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DWEBP_BUILD_ANIM_UTILS=OFF -DWEBP_BUILD_EXTRAS=OFF -DWEBP_BUILD_GIF2WEBP=OFF -DWEBP_BUILD_IMG2WEBP=OFF -DWEBP_BUILD_LIBWEBPMUX=OFF -DWEBP_BUILD_VWEBP=OFF -DWEBP_BUILD_WEBPINFO=OFF -DWEBP_BUILD_WEBPMUX=OFF -DWEBP_ENABLE_SWAP_16BIT_CSP=OFF -DWEBP_LINK_STATIC=OFF -DWEBP_BUILD_CWEBP=ON -DWEBP_BUILD_DWEBP=ON -DBUILD_SHARED_LIBS=ON -DZLIB_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libhwy - version 1.0.7
====================================
Downloading "https://github.com/google/highway/archive/refs/tags/1.0.7.tar.gz" saving as "libhwy-1.0.7.tar.gz"
Download Completed
File extracted: libhwy-1.0.7.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DHWY_ENABLE_EXAMPLES=OFF -DHWY_ENABLE_TESTS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building brotli - version 1.1.0
====================================
Downloading "https://github.com/google/brotli/archive/refs/tags/v1.1.0.tar.gz" saving as "brotli-1.1.0.tar.gz"
Download Completed
File extracted: brotli-1.1.0.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building lcms2 - version 2.15
====================================
Downloading "https://github.com/mm2/Little-CMS/archive/refs/tags/lcms2.15.tar.gz" saving as "lcms2-2.15.tar.gz"
Download Completed
File extracted: lcms2-2.15.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building gflags - version 2.2.2
====================================
Downloading "https://github.com/gflags/gflags/archive/refs/tags/v2.2.2.tar.gz" saving as "gflags-2.2.2.tar.gz"
Download Completed
File extracted: gflags-2.2.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DINSTALL_HEADERS=ON -DBUILD_STATIC_LIBS=ON -DBUILD_gflags_LIB=ON -DREGISTER_BUILD_DIR=ON -DREGISTER_INSTALL_PREFIX=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libjxl - version 0.8.2
====================================
(Reading database ... 367126 files and directories currently installed.)
Preparing to unpack libjxl_0.8.2_amd64.deb ...
Unpacking libjxl:amd64 (0.8.2) over (0.8.2) ...
Setting up libjxl:amd64 (0.8.2) ...
Processing triggers for libc-bin (2.36-9+deb12u1) ...
ldconfig: /usr/lib/wsl/lib/libcuda.so.1 is not a symbolic link

(Reading database ... 367126 files and directories currently installed.)
Preparing to unpack ./jxl_0.8.2_amd64.deb ...
Unpacking jxl (0.8.2) over (0.8.2) ...
Preparing to unpack ./jxl-dbgsym_0.8.2_amd64.deb ...
Unpacking jxl-dbgsym (0.8.2) over (0.8.2) ...
Preparing to unpack .../libjxl-dbgsym_0.8.2_amd64.deb ...
Unpacking libjxl-dbgsym:amd64 (0.8.2) over (0.8.2) ...
Preparing to unpack ./libjxl-dev_0.8.2_amd64.deb ...
Unpacking libjxl-dev (0.8.2) over (0.8.2) ...
Preparing to unpack .../libjxl-gdk-pixbuf_0.8.2_amd64.deb ...
Unpacking libjxl-gdk-pixbuf:amd64 (0.8.2) over (0.8.2) ...
Preparing to unpack .../libjxl-gdk-pixbuf-dbgsym_0.8.2_amd64.deb ...
Unpacking libjxl-gdk-pixbuf-dbgsym:amd64 (0.8.2) over (0.8.2) ...
Preparing to unpack .../libjxl-gimp-plugin_0.8.2_amd64.deb ...
Unpacking libjxl-gimp-plugin:amd64 (0.8.2) over (0.8.2) ...
Preparing to unpack .../libjxl-gimp-plugin-dbgsym_0.8.2_amd64.deb ...
Unpacking libjxl-gimp-plugin-dbgsym:amd64 (0.8.2) over (0.8.2) ...
Setting up jxl (0.8.2) ...
Setting up jxl-dbgsym (0.8.2) ...
Setting up libjxl-dbgsym:amd64 (0.8.2) ...
Setting up libjxl-dev (0.8.2) ...
Setting up libjxl-gdk-pixbuf:amd64 (0.8.2) ...
Setting up libjxl-gdk-pixbuf-dbgsym:amd64 (0.8.2) ...
Setting up libjxl-gimp-plugin:amd64 (0.8.2) ...
Setting up libjxl-gimp-plugin-dbgsym:amd64 (0.8.2) ...
Processing triggers for man-db (2.11.2-2) ...
Processing triggers for libgdk-pixbuf-2.0-0:amd64 (2.42.10+dfsg-1+b1) ...
Processing triggers for shared-mime-info (2.2-1) ...

Building opencl-headers - version 2023.04.17
====================================
Downloading "https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v2023.04.17.tar.gz" saving as "opencl-headers-2023.04.17.tar.gz"
Download Completed
File extracted: opencl-headers-2023.04.17.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DOPENCL_HEADERS_BUILD_CXX_TESTS=ON -DBUILD_TESTING=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building tesseract - version 5.3.2
====================================
Downloading "https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.3.2.tar.gz" saving as "tesseract-5.3.2.tar.gz"
Download Completed
File extracted: tesseract-5.3.2.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --build=x86_64-linux-gnu --host=x86_64-linux-gnu --disable-doc --with-extra-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-extra-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-pic PKG_CONFIG=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config
$ make -j32
$ make install

Building rubberband - version git
====================================
Downloading https://github.com/m-ab-s/rubberband.git as rubberband-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/rubberband-git

$ make -j32 PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install-static

Building zimg - version 3.0.5
====================================
Downloading "https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.5.tar.gz" saving as "zimg-3.0.5.tar.gz"
Download Completed
File extracted: zimg-3.0.5.tar.gz

$ libtoolize -fiq
$ autoupdate
$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building c-ares - version 1.19.1
====================================
Downloading "https://github.com/c-ares/c-ares/archive/refs/tags/cares-1_19_1.tar.gz" saving as "c-ares-1.19.1.tar.gz"
Download Completed
File extracted: c-ares-1.19.1.tar.gz

$ autoreconf -fi
$ autoupdate
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --disable-warnings
$ make -j32
$ make install

Building lv2 - version git
====================================
Downloading https://github.com/lv2/lv2.git as lv2-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/lv2-git

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dplugins=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building waflib - version 2.0.26
====================================
Downloading "https://gitlab.com/ita1024/waf/-/archive/waf-2.0.26/waf-waf-2.0.26.tar.bz2" saving as "waflib-2.0.26.tar.bz2"
Download Completed
File extracted: waflib-2.0.26.tar.bz2


Building serd - version 0.30.16
====================================
Downloading "https://gitlab.com/drobilla/serd/-/archive/v0.30.16/serd-v0.30.16.tar.bz2" saving as "serd-0.30.16.tar.bz2"
Download Completed
File extracted: serd-0.30.16.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building pcre2 - version 2-10.42
====================================
Downloading "https://github.com/PCRE2Project/pcre2/archive/refs/tags/pcre2-10.42.tar.gz" saving as "pcre2-2-10.42.tar.gz"
Download Completed
File extracted: pcre2-2-10.42.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building zix - version 0.4.0
====================================
Downloading "https://gitlab.com/drobilla/zix/-/archive/v0.4.0/zix-v0.4.0.tar.bz2" saving as "zix-0.4.0.tar.bz2"
Download Completed
File extracted: zix-0.4.0.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Dbenchmarks=disabled -Ddocs=disabled -Dsinglehtml=disabled -Dtests=disabled -Dtests_cpp=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building sord - version 5175d274
====================================
Downloading "https://gitlab.com/drobilla/sord/-/archive/5175d274ca9099fee515878d5605b51775b31a7f/sord-5175d274ca9099fee515878d5605b51775b31a7f.tar.bz2" saving as "sord-5175d274.tar.bz2"
Download Completed
File extracted: sord-5175d274.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building sratom - version 0.6.14
====================================
Downloading "https://gitlab.com/lv2/sratom/-/archive/v0.6.14/sratom-v0.6.14.tar.bz2" saving as "sratom-0.6.14.tar.bz2"
Download Completed
File extracted: sratom-0.6.14.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building lilv - version 0.24.20
====================================
Downloading "https://gitlab.com/lv2/lilv/-/archive/v0.24.20/lilv-v0.24.20.tar.bz2" saving as "lilv-0.24.20.tar.bz2"
Download Completed
File extracted: lilv-0.24.20.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Ddocs=disabled -Dtests=disabled
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libmpg123 - version git
====================================
Downloading https://github.com/gypified/libmpg123.git as libmpg123-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/libmpg123-git

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
====================================
Downloading "https://github.com/akheron/jansson/archive/refs/tags/v2.14.tar.gz" saving as "jansson-2.14.tar.gz"
Download Completed
File extracted: jansson-2.14.tar.gz

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install

Building jemalloc - version 5.3.0
====================================
Downloading "https://github.com/jemalloc/jemalloc/archive/refs/tags/5.3.0.tar.gz" saving as "jemalloc-5.3.0.tar.gz"
Download Completed
File extracted: jemalloc-5.3.0.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-autogen --enable-static --enable-xmalloc --disable-debug --disable-doc --disable-fill --disable-log --disable-shared --disable-prof --disable-stats
$ make -j32
$ make install

Building cunit - version git
====================================
Downloading https://github.com/jacklicn/cunit.git as cunit-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/cunit-git

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Audio Tools |
|                        |
 ------------------------

Building libflac - version 1.4.3
====================================
Downloading "https://github.com/xiph/flac/archive/refs/tags/1.4.3.tar.gz" saving as "libflac-1.4.3.tar.gz"
Download Completed
File extracted: libflac-1.4.3.tar.gz

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DINSTALL_CMAKE_CONFIG_MODULE=ON -DINSTALL_MANPAGES=ON -DINSTALL_PKGCONFIG_MODULES=ON -DBUILD_CXXLIBS=ON -DBUILD_PROGRAMS=ON -DWITH_ASM=ON -DWITH_AVX=ON -DWITH_FORTIFY_SOURCE=ON -DWITH_STACK_PROTECTOR=ON -DWITH_OGG=OFF -DENABLE_64_BIT_WORDS=ON -DBUILD_DOCS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libfdk-aac - version 2.0.2
====================================
Downloading "https://gigenet.dl.sourceforge.net/project/opencore-amr/fdk-aac/fdk-aac-2.0.2.tar.gz" saving as "libfdk-aac-2.0.2.tar.gz"
Download Completed
File extracted: libfdk-aac-2.0.2.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --enable-static
$ make -j32
$ make install

Building libogg - version 1.3.5
====================================
Downloading "https://github.com/xiph/ogg/archive/refs/tags/v1.3.5.tar.gz" saving as "libogg-1.3.5.tar.gz"
Download Completed
File extracted: libogg-1.3.5.tar.gz

$ autoreconf -fi
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DCPACK_BINARY_DEB=OFF -DCPACK_SOURCE_ZIP=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building vorbis - version 1.3.7
====================================
Downloading "https://github.com/xiph/vorbis/archive/refs/tags/v1.3.7.tar.gz" saving as "vorbis-1.3.7.tar.gz"
Download Completed
File extracted: vorbis-1.3.7.tar.gz

$ ./autogen.sh
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DOGG_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DOGG_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building opus - version 1.4
====================================
Downloading "https://github.com/xiph/opus/archive/refs/tags/v1.4.tar.gz" saving as "opus-1.4.tar.gz"
Download Completed
File extracted: opus-1.4.tar.gz

$ autoreconf -fis
$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCPACK_SOURCE_ZIP=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building libmysofa - version 1.3.1
====================================
Downloading "https://github.com/hoene/libmysofa/archive/refs/tags/v1.3.1.tar.gz" saving as "libmysofa-1.3.1.tar.gz"
Download Completed
File extracted: libmysofa-1.3.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building vpx - version 1.13.0
====================================
Downloading "https://github.com/webmproject/libvpx/archive/refs/tags/v1.13.0.tar.gz" saving as "libvpx-1.13.0.tar.gz"
Download Completed
File extracted: libvpx-1.13.0.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-unit-tests --disable-shared --disable-examples --as=yasm --enable-vp9-highbitdepth
$ make -j32
$ make install

Building opencore-amr - version 0.1.6-1
====================================
Downloading "https://salsa.debian.org/multimedia-team/opencore-amr/-/archive/debian/0.1.6-1/opencore-amr-debian-0.1.6-1.tar.bz2" saving as "opencore-amr-0.1.6-1.tar.bz2"
Download Completed
File extracted: opencore-amr-0.1.6-1.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared --enable-static
$ make -j32
$ make install

Building liblame - version 3.100
====================================
Downloading "https://zenlayer.dl.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz" saving as "lame-3.100.tar.gz"
Download Completed
File extracted: lame-3.100.tar.gz

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building libtheora - version 1.1.1
====================================
Downloading "https://github.com/xiph/theora/archive/refs/tags/v1.1.1.tar.gz" saving as "libtheora-1.1.1.tar.gz"
Download Completed
File extracted: libtheora-1.1.1.tar.gz

$ ./autogen.sh
$ mv configure.patched configure
$ rm config.guess
$ curl -A Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 -Lso config.guess https://raw.githubusercontent.com/gcc-mirror/gcc/master/config.guess
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-asm --disable-examples --disable-oggtest --disable-spec --disable-shared --disable-vorbistest --with-ogg-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-ogg-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib --with-vorbis-includes=/home/jman/tmp/ffmpeg-build-script/workspace/include --with-vorbis-libraries=/home/jman/tmp/ffmpeg-build-script/workspace/lib
$ make -j32
$ make install

 ------------------------
|                        |
| Installing Video Tools |
|                        |
 ------------------------

Building av1 - version 61bddf1
====================================
Downloading "https://aomedia.googlesource.com/aom/+archive/61bddf1e5f233e048280cf33cc31f72eecc2954a.tar.gz" saving as "av1-61bddf1.tar.gz"
Download Completed
File extracted: av1-61bddf1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_INSTALL_LIBDIR=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DCMAKE_BUILD_TYPE=Release -DCONFIG_ANALYZER=0 -DCONFIG_AV1_TEMPORAL_DENOISING=0 -DCONFIG_BIG_ENDIAN=0 -DCONFIG_COLLECT_RD_STATS=0 -DCONFIG_ENTROPY_STATS=0 -DCONFIG_AV1_DECODER=1 -DCONFIG_AV1_ENCODER=1 -DCONFIG_AV1_HIGHBITDEPTH=1 -DCONFIG_DENOISE=1 -DCONFIG_DISABLE_FULL_PIXEL_SPLIT_8X8=1 -DBUILD_SHARED_LIBS=OFF -DENABLE_CCACHE=1 -DENABLE_EXAMPLES=0 -DENABLE_TESTS=0 -G Ninja -Wno-dev /home/jman/tmp/ffmpeg-build-script/packages/av1
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building dav1d - version 1.2.1
====================================
Downloading "https://code.videolan.org/videolan/dav1d/-/archive/1.2.1/dav1d-1.2.1.tar.bz2" saving as "dav1d-1.2.1.tar.bz2"
Download Completed
File extracted: dav1d-1.2.1.tar.bz2

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=static --strip -Denable_tests=false -Dlogging=false
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building rav1e - version p20230926
====================================
$ Installing RustUp
$ cargo install --version 0.9.24+cargo-0.73.0 cargo-c
Downloading "https://github.com/xiph/rav1e/archive/refs/tags/p20230926.tar.gz" saving as "rav1e-p20230926.tar.gz"
Download Completed
File extracted: rav1e-p20230926.tar.gz

$ cargo cinstall --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --library-type=staticlib --crt-static --release

Building avif - version 1.0.1
====================================
Downloading "https://github.com/AOMediaCodec/libavif/archive/refs/tags/v1.0.1.tar.gz" saving as "avif-1.0.1.tar.gz"
Download Completed
File extracted: avif-1.0.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DAVIF_CODEC_AOM=ON -DAVIF_CODEC_AOM_DECODE=ON -DAVIF_CODEC_AOM_ENCODE=ON -DAVIF_ENABLE_GTEST=OFF -DAVIF_ENABLE_WERROR=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building kvazaar - version 2.2.0
====================================
Downloading https://github.com/ultravideo/kvazaar.git as kvazaar-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/kvazaar-git

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building libdvdread - version 6.1.3
====================================
Downloading "https://code.videolan.org/videolan/libdvdread/-/archive/6.1.3/libdvdread-6.1.3.tar.bz2" saving as "libdvdread-6.1.3.tar.bz2"
Download Completed
File extracted: libdvdread-6.1.3.tar.bz2

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-apidoc --disable-shared
$ make -j32
$ make install

Building udfread - version 1.1.2
====================================
Downloading "https://code.videolan.org/videolan/libudfread/-/archive/1.1.2/libudfread-1.1.2.tar.bz2" saving as "libudfread-1.1.2.tar.bz2"
Download Completed
File extracted: libudfread-1.1.2.tar.bz2

$ autoreconf -fi
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building libbluray - version 1.3.4
====================================
Downloading "https://code.videolan.org/videolan/libbluray/-/archive/1.3.4/1.3.4.tar.gz" saving as "libbluray-1.3.4.tar.gz"
Download Completed
File extracted: libbluray-1.3.4.tar.gz

$ autoreconf -fi
$ ./bootstrap
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-extra-warnings --disable-shared --disable-werror --without-libxml2
$ make -j32
$ make install

Building zenlib - version 0.4.41
====================================
Downloading "https://github.com/MediaArea/ZenLib/archive/refs/tags/v0.4.41.tar.gz" saving as "zenlib-0.4.41.tar.gz"
Download Completed
File extracted: zenlib-0.4.41.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfolib - version 23.09
====================================
Downloading "https://github.com/MediaArea/MediaInfoLib/archive/refs/tags/v23.09.tar.gz" saving as "mediainfolib-23.09.tar.gz"
Download Completed
File extracted: mediainfolib-23.09.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building mediainfo-cli - version 23.09
====================================
Downloading "https://github.com/MediaArea/MediaInfo/archive/refs/tags/v23.09.tar.gz" saving as "mediainfo-cli-23.09.tar.gz"
Download Completed
File extracted: mediainfo-cli-23.09.tar.gz

$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-staticlibs
$ make -j32
$ make install

Building vid-stab - version 1.1.1
====================================
Downloading "https://github.com/georgmartius/vid.stab/archive/refs/tags/v1.1.1.tar.gz" saving as "vid-stab-1.1.1.tar.gz"
Download Completed
File extracted: vid-stab-1.1.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DUSE_OMP=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building frei0r - version 2.3.1
====================================
Downloading "https://github.com/dyne/frei0r/archive/refs/tags/v2.3.1.tar.gz" saving as "frei0r-2.3.1.tar.gz"
Download Completed
File extracted: frei0r-2.3.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=OFF -DWITHOUT_OPENCV=OFF -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building amf - version 1.4.30
====================================
Downloading "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/archive/refs/tags/v1.4.30.tar.gz" saving as "amf-1.4.30.tar.gz"
Download Completed
File extracted: amf-1.4.30.tar.gz

$ rm -fr /home/jman/tmp/ffmpeg-build-script/workspace/include/AMF
$ mkdir -p /home/jman/tmp/ffmpeg-build-script/workspace/include/AMF
$ cp -fr /home/jman/tmp/ffmpeg-build-script/packages/amf-1.4.30/amf/public/include/components /home/jman/tmp/ffmpeg-build-script/packages/amf-1.4.30/amf/public/include/core /home/jman/tmp/ffmpeg-build-script/workspace/include/AMF

Building gpac - version 2.2.1
====================================
Downloading https://github.com/gpac/gpac.git as gpac-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/gpac-git

$ sudo ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --enable-gprof --static-bin --static-modules
$ sudo make -j32
$ sudo make install

Building svt-hevc - version 1.5.1
====================================
Downloading "https://github.com/OpenVisualCloud/SVT-HEVC/archive/refs/tags/v1.5.1.tar.gz" saving as "svt-hevc-1.5.1.tar.gz"
Download Completed
File extracted: svt-hevc-1.5.1.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DYASM_EXE=/home/jman/tmp/ffmpeg-build-script/workspace/bin/yasm -DNATIVE=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building svt-av1 - version 1.4.0
====================================
Downloading "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.4.0/SVT-AV1-v1.4.0.tar.bz2" saving as "svt-av1-1.4.0.tar.bz2"
Download Completed
File extracted: svt-av1-1.4.0.tar.bz2

$ cmake -S . -B Build/linux -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_APPS=ON -DBUILD_DEC=ON -DBUILD_ENC=ON -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DENABLE_NASM=ON -DENABLE_AVX512=ON -DSVT_AV1_LTO=ON -DSVT_AV1_PGO=OFF -DNATIVE=ON -G Ninja -Wno-dev
$ ninja -j32 -C Build/linux
$ ninja -j32 -C Build/linux install

Building x264 - version a8b68eb
====================================
Downloading "https://code.videolan.org/videolan/x264/-/archive/a8b68ebfaa68621b5ac8907610d3335971839d52/x264-a8b68ebfaa68621b5ac8907610d3335971839d52.tar.bz2" saving as "x264-a8b68eb.tar.bz2"
Download Completed
File extracted: x264-a8b68eb.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --bit-depth=all --chroma-format=all --enable-gprof --enable-static --enable-strip
$ sudo make -j32
$ sudo make install
$ sudo make install-lib-static

Building x265 - version 8ee01d4
====================================
Downloading "https://bitbucket.org/multicoreware/x265_git/get/8ee01d45b05cdbc9da89b884815257807a514bc8.tar.bz2" saving as "x265-8ee01d4.tar.bz2"
Download Completed
File extracted: x265-8ee01d4.tar.bz2

$ making 12bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DHIGH_BIT_DEPTH=ON -DEXPORT_C_API=OFF -DENABLE_SHARED=OFF -DENABLE_CLI=OFF -DMAIN12=ON -G Ninja -Wno-dev
$ ninja -j32
$ making 10bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DHIGH_BIT_DEPTH=ON -DEXPORT_C_API=OFF -DENABLE_SHARED=OFF -DENABLE_CLI=OFF -G Ninja -Wno-dev
$ ninja -j32
$ making 8bit binaries
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DEXTRA_LIB=x265_main10.a;x265_main12.a -DEXTRA_LINK_FLAGS=-L. -DLINKED_10BIT=ON -DLINKED_12BIT=ON -G Ninja -Wno-dev
$ ninja -j32
$ ar -M
$ ninja -j32 install

Building nv-codec-headers - version 12.0.16.0
====================================
Downloading "https://github.com/FFmpeg/nv-codec-headers/releases/download/n12.0.16.0/nv-codec-headers-12.0.16.0.tar.gz" saving as "nv-codec-headers-12.0.16.0.tar.gz"
Download Completed
File extracted: nv-codec-headers-12.0.16.0.tar.gz

$ make -j32
$ make PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace install
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
nvidia-smi is already the newest version (525.125.06-1~deb12u1).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

Building srt - version 1.5.3
====================================
Downloading "https://github.com/Haivision/srt/archive/refs/tags/v1.5.3.tar.gz" saving as "srt-1.5.3.tar.gz"
Download Completed
File extracted: srt-1.5.3.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DENABLE_APPS=OFF -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DUSE_STATIC_LIBSTDCXX=ON -G Ninja -Wno-dev
$ ninja -C build -j32
$ ninja -C build -j32 install

Building avisynth - version 3.7.3
====================================
Downloading "https://github.com/AviSynth/AviSynthPlus/archive/refs/tags/v3.7.3.tar.gz" saving as "avisynth-3.7.3.tar.gz"
Download Completed
File extracted: avisynth-3.7.3.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DHEADERS_ONLY=ON -G Unix Makefiles -Wno-dev
$ make -j32 -C build VersionGen install

Building vapoursynth - version R64
====================================
Downloading "https://github.com/vapoursynth/vapoursynth/archive/refs/tags/R64.tar.gz" saving as "vapoursynth-R64.tar.gz"
Download Completed
File extracted: vapoursynth-R64.tar.gz

$ pip install Cython==0.29.36
$ ./autogen.sh
$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --disable-shared
$ make -j32
$ make install

Building cyanrip - version 1.0.0-rc1
====================================
Downloading "https://github.com/cyanreg/cyanrip/archive/refs/tags/v1.0.0-rc1.tar.gz" saving as "cyanrip-1.0.0-rc1.tar.gz"
Download Completed
File extracted: cyanrip-1.0.0-rc1.tar.gz

$ meson setup build --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --buildtype=release --default-library=shared --strip -Dpkg_config_path=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig
$ ninja -C build -j32
$ ninja -C build -j32 install

Building libgav1 - version git
====================================
Downloading https://chromium.googlesource.com/codecs/libgav1 as libgav1-git
Successfully cloned: /home/jman/tmp/ffmpeg-build-script/packages/libgav1-git

$ git clone -b 20220623.0 --depth 1 https://github.com/abseil/abseil-cpp.git third_party/abseil-cpp
$ cmake -B libgav1_build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INSTALL_SBINDIR=sbin -DBUILD_SHARED_LIBS=OFF -DABSL_ENABLE_INSTALL=ON -DABSL_PROPAGATE_CXX_STD=ON -DLIBGAV1_ENABLE_TESTS=OFF -G Ninja -Wno-dev
$ ninja -j32 -C libgav1_build
$ ninja -j32 -C libgav1_build install

Building xvidcore - version 1.3.7-1
====================================
Downloading "https://salsa.debian.org/multimedia-team/xvidcore/-/archive/debian/2%251.3.7-1/xvidcore-debian-2%251.3.7-1.tar.bz2" saving as "xvidcore-1.3.7-1.tar.bz2"
Download Completed
File extracted: xvidcore-1.3.7-1.tar.bz2

$ ./configure --prefix=/home/jman/tmp/ffmpeg-build-script/workspace
$ make -j32
$ make install
$ ln -sf build/libxvidcore.so.4.3 /home/jman/tmp/ffmpeg-build-script/workspace/lib/libxvidcore.so.4@

 ------------------------
|                        |
| Installing Image Tools |
|                        |
 ------------------------

Building libheif - version 1.16.2
====================================
Downloading "https://github.com/strukturag/libheif/archive/refs/tags/v1.16.2.tar.gz" saving as "libheif-1.16.2.tar.gz"
Download Completed
File extracted: libheif-1.16.2.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -G Ninja -Wno-dev -DWITH_AOM_DECODER=ON -DWITH_AOM_ENCODER=ON -DWITH_DAV1D=ON -DWITH_LIBDE265=ON -DWITH_LIBSHARPYUV=ON -DWITH_RAV1E=ON -DWITH_RAV1E_PLUGIN=ON -DWITH_SvtEnc=ON -DWITH_SvtEnc_PLUGIN=ON -DWITH_X265=ON -DWITH_GDK_PIXBUF=ON -DWITH_EXAMPLES=OFF -DWITH_REDUCED_VISIBILITY=OFF -DSvtEnc_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DSvtEnc_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DAOM_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DAOM_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DDAV1D_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DDAV1D_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DRAV1E_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include/rav1e -DRAV1E_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DLIBDE265_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DLIBDE265_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DX265_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include -DX265_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib -DLIBSHARPYUV_INCLUDE_DIR=/home/jman/tmp/ffmpeg-build-script/workspace/include/webp -DLIBSHARPYUV_LIBRARY=/home/jman/tmp/ffmpeg-build-script/workspace/lib
$ ninja -j32 -C build
$ ninja -j32 -C build install

Building openjpeg - version wg1n6848
====================================
Downloading "https://codeload.github.com/uclouvain/openjpeg/tar.gz/refs/tags/wg1n6848" saving as "openjpeg-wg1n6848.tar.gz"
Download Completed
File extracted: openjpeg-wg1n6848.tar.gz

$ cmake -B build -DCMAKE_INSTALL_PREFIX=/home/jman/tmp/ffmpeg-build-script/workspace -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=ON -DBUILD_THIRDPARTY=ON -DCPACK_BINARY_DEB=ON -DCPACK_BINARY_FREEBSD=ON -DCPACK_BINARY_IFW=ON -DCPACK_BINARY_NSIS=ON -DCPACK_BINARY_RPM=ON -DCPACK_BINARY_TBZ2=ON -DCPACK_BINARY_TXZ=ON -DCPACK_SOURCE_RPM=ON -DCPACK_SOURCE_ZIP=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -G Ninja -Wno-dev
$ ninja -j32 -C build
$ ninja -j32 -C build install

 -----------------
|                 |
| Building FFmpeg |
|                 |
 -----------------

Building ffmpeg - version 963937e
====================================
Downloading "https://git.ffmpeg.org/gitweb/ffmpeg.git/snapshot/963937e408fc68b5925f938a253cfff1d506f784.tar.gz" saving as "ffmpeg-963937e.tar.gz"
Download Completed
File extracted: ffmpeg-963937e.tar.gz

install prefix            /home/jman/tmp/ffmpeg-build-script/workspace
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
alsa                    libbluray               libgme                  libpulse                libssh                  libwebp                 opengl
avisynth                libbs2b                 libjxl                  librav1e                libsvtav1               libx264                 openssl
bzlib                   libcaca                 libkvazaar              librubberband           libtesseract            libx265                 sdl2
frei0r                  libcdio                 libmodplug              libshine                libtheora               libxcb                  sndio
iconv                   libdav1d                libmp3lame              libsmbclient            libtwolame              libxcb_shm              vapoursynth
ladspa                  libfdk_aac              libmysofa               libsmbclient            libv4l2                 libxml2                 xlib
lcms2                   libflite                libopencore_amrnb       libsnappy               libvidstab              libxvid                 zlib
libaom                  libfontconfig           libopencore_amrwb       libsoxr                 libvo_amrwbenc          libzimg
libaribb24              libfreetype             libopenjpeg             libspeex                libvorbis               lv2
libass                  libfribidi              libopus                 libsrt                  libvpx                  lzma

External libraries providing hardware acceleration:
amf                     cuda_llvm               cuvid                   nvdec                   opencl                  vaapi                   vulkan
cuda                    cuda_nvcc               ffnvcodec               nvenc                   v4l2_m2m                vdpau

Libraries:
avcodec                 avfilter                avutil                  swresample
avdevice                avformat                postproc                swscale

Programs:
ffmpeg                  ffplay                  ffprobe

Enabled decoders:
aac                     argo                    eamad                   jv                      mvc2                    r10k                    utvideo
aac_fixed               ass                     eatgq                   kgv1                    mvdv                    r210                    v210
aac_latm                asv1                    eatgv                   kmvc                    mvha                    ra_144                  v210x
aasc                    asv2                    eatqi                   lagarith                mwsc                    ra_288                  v308
ac3                     atrac1                  eightbps                libaom_av1              mxpeg                   ralf                    v408
ac3_fixed               atrac3                  eightsvx_exp            libaribb24              nellymoser              rasc                    v410
acelp_kelvin            atrac3al                eightsvx_fib            libdav1d                notchlc                 rawvideo                vb
adpcm_4xm               atrac3p                 escape124               libfdk_aac              nuv                     realtext                vble
adpcm_adx               atrac3pal               escape130               libjxl                  on2avc                  rl2                     vbn
adpcm_afc               atrac9                  evrc                    libopencore_amrnb       opus                    roq                     vc1
adpcm_agm               aura                    exr                     libopencore_amrwb       paf_audio               roq_dpcm                vc1_cuvid
adpcm_aica              aura2                   fastaudio               libopenjpeg             paf_video               rpza                    vc1_v4l2m2m
adpcm_argo              av1                     ffv1                    libopus                 pam                     rscc                    vc1image
adpcm_ct                av1_cuvid               ffvhuff                 libspeex                pbm                     rv10                    vcr1
adpcm_dtk               avrn                    ffwavesynth             libvorbis               pcm_alaw                rv20                    vmdaudio
adpcm_ea                avrp                    fic                     libvpx_vp8              pcm_bluray              rv30                    vmdvideo
adpcm_ea_maxis_xa       avs                     fits                    libvpx_vp9              pcm_dvd                 rv40                    vmnc
adpcm_ea_r1             avui                    flac                    loco                    pcm_f16le               s302m                   vorbis
adpcm_ea_r2             ayuv                    flashsv                 lscr                    pcm_f24le               sami                    vp3
adpcm_ea_r3             bethsoftvid             flashsv2                m101                    pcm_f32be               sanm                    vp4
adpcm_ea_xas            bfi                     flic                    mace3                   pcm_f32le               sbc                     vp5
adpcm_g722              bink                    flv                     mace6                   pcm_f64be               scpr                    vp6
adpcm_g726              binkaudio_dct           fmvc                    magicyuv                pcm_f64le               screenpresso            vp6a
adpcm_g726le            binkaudio_rdft          fourxm                  mdec                    pcm_lxf                 sdx2_dpcm               vp6f
adpcm_ima_acorn         bintext                 fraps                   metasound               pcm_mulaw               sga                     vp7
adpcm_ima_alp           bitpacked               frwu                    microdvd                pcm_s16be               sgi                     vp8
adpcm_ima_amv           bmp                     g2m                     mimic                   pcm_s16be_planar        sgirle                  vp8_cuvid
adpcm_ima_apc           bmv_audio               g723_1                  mjpeg                   pcm_s16le               sheervideo              vp8_v4l2m2m
adpcm_ima_apm           bmv_video               g729                    mjpeg_cuvid             pcm_s16le_planar        shorten                 vp9
adpcm_ima_cunning       brender_pix             gdv                     mjpegb                  pcm_s24be               simbiosis_imx           vp9_cuvid
adpcm_ima_dat4          c93                     gem                     mlp                     pcm_s24daud             sipr                    vp9_v4l2m2m
adpcm_ima_dk3           cavs                    gif                     mmvideo                 pcm_s24le               siren                   vplayer
adpcm_ima_dk4           ccaption                gremlin_dpcm            mobiclip                pcm_s24le_planar        smackaud                vqa
adpcm_ima_ea_eacs       cdgraphics              gsm                     motionpixels            pcm_s32be               smacker                 wavpack
adpcm_ima_ea_sead       cdtoons                 gsm_ms                  movtext                 pcm_s32le               smc                     wcmv
adpcm_ima_iss           cdxl                    h261                    mp1                     pcm_s32le_planar        smvjpeg                 webp
adpcm_ima_moflex        cfhd                    h263                    mp1float                pcm_s64be               snow                    webvtt
adpcm_ima_mtf           cinepak                 h263_v4l2m2m            mp2                     pcm_s64le               sol_dpcm                wmalossless
adpcm_ima_oki           clearvideo              h263i                   mp2float                pcm_s8                  sonic                   wmapro
adpcm_ima_qt            cljr                    h263p                   mp3                     pcm_s8_planar           sp5x                    wmav1
adpcm_ima_rad           cllc                    h264                    mp3adu                  pcm_sga                 speedhq                 wmav2
adpcm_ima_smjpeg        comfortnoise            h264_cuvid              mp3adufloat             pcm_u16be               speex                   wmavoice
adpcm_ima_ssi           cook                    h264_v4l2m2m            mp3float                pcm_u16le               srgc                    wmv1
adpcm_ima_wav           cpia                    hap                     mp3on4                  pcm_u24be               srt                     wmv2
adpcm_ima_ws            cri                     hca                     mp3on4float             pcm_u24le               ssa                     wmv3
adpcm_ms                cscd                    hcom                    mpc7                    pcm_u32be               stl                     wmv3image
adpcm_mtaf              cyuv                    hevc                    mpc8                    pcm_u32le               subrip                  wnv1
adpcm_psx               dca                     hevc_cuvid              mpeg1_cuvid             pcm_u8                  subviewer               wrapped_avframe
adpcm_sbpro_2           dds                     hevc_v4l2m2m            mpeg1_v4l2m2m           pcm_vidc                subviewer1              ws_snd1
adpcm_sbpro_3           derf_dpcm               hnm4_video              mpeg1video              pcx                     sunrast                 xan_dpcm
adpcm_sbpro_4           dfa                     hq_hqa                  mpeg2_cuvid             pfm                     svq1                    xan_wc3
adpcm_swf               dfpwm                   hqx                     mpeg2_v4l2m2m           pgm                     svq3                    xan_wc4
adpcm_thp               dirac                   huffyuv                 mpeg2video              pgmyuv                  tak                     xbin
adpcm_thp_le            dnxhd                   hymt                    mpeg4                   pgssub                  targa                   xbm
adpcm_vima              dolby_e                 iac                     mpeg4_cuvid             pgx                     targa_y216              xface
adpcm_xa                dpx                     idcin                   mpeg4_v4l2m2m           phm                     tdsc                    xl
adpcm_yamaha            dsd_lsbf                idf                     mpegvideo               photocd                 text                    xma1
adpcm_zork              dsd_lsbf_planar         iff_ilbm                mpl2                    pictor                  theora                  xma2
agm                     dsd_msbf                ilbc                    msa1                    pixlet                  thp                     xpm
aic                     dsd_msbf_planar         imc                     mscc                    pjs                     tiertexseqvideo         xsub
alac                    dsicinaudio             imm4                    msmpeg4v1               png                     tiff                    xwd
alias_pix               dsicinvideo             imm5                    msmpeg4v2               ppm                     tmv                     y41p
als                     dss_sp                  indeo2                  msmpeg4v3               prores                  truehd                  ylc
amrnb                   dst                     indeo3                  msnsiren                prosumer                truemotion1             yop
amrwb                   dvaudio                 indeo4                  msp2                    psd                     truemotion2             yuv4
amv                     dvbsub                  indeo5                  msrle                   ptx                     truemotion2rt           zero12v
anm                     dvdsub                  interplay_acm           mss1                    qcelp                   truespeech              zerocodec
ansi                    dvvideo                 interplay_dpcm          mss2                    qdm2                    tscc                    zlib
ape                     dxa                     interplay_video         msvideo1                qdmc                    tscc2                   zmbv
apng                    dxtory                  ipu                     mszh                    qdraw                   tta
aptx                    dxv                     jacosub                 mts2                    qoi                     twinvq
aptx_hd                 eac3                    jpeg2000                mv30                    qpeg                    txd
arbc                    eacmv                   jpegls                  mvc1                    qtrle                   ulti

Enabled encoders:
a64multi                ayuv                    h264_v4l2m2m            libx264rgb              pcm_s16be               prores_aw               ttml
a64multi5               bitpacked               h264_vaapi              libx265                 pcm_s16be_planar        prores_ks               utvideo
aac                     bmp                     hap                     libxvid                 pcm_s16le               qoi                     v210
ac3                     cfhd                    hevc_amf                ljpeg                   pcm_s16le_planar        qtrle                   v308
ac3_fixed               cinepak                 hevc_nvenc              magicyuv                pcm_s24be               r10k                    v408
adpcm_adx               cljr                    hevc_v4l2m2m            mjpeg                   pcm_s24daud             r210                    v410
adpcm_argo              comfortnoise            hevc_vaapi              mjpeg_vaapi             pcm_s24le               ra_144                  vbn
adpcm_g722              dca                     huffyuv                 mlp                     pcm_s24le_planar        rawvideo                vc2
adpcm_g726              dfpwm                   jpeg2000                movtext                 pcm_s32be               roq                     vorbis
adpcm_g726le            dnxhd                   jpegls                  mp2                     pcm_s32le               roq_dpcm                vp8_v4l2m2m
adpcm_ima_alp           dpx                     libaom_av1              mp2fixed                pcm_s32le_planar        rpza                    vp8_vaapi
adpcm_ima_amv           dvbsub                  libfdk_aac              mpeg1video              pcm_s64be               rv10                    vp9_vaapi
adpcm_ima_apm           dvdsub                  libjxl                  mpeg2_vaapi             pcm_s64le               rv20                    wavpack
adpcm_ima_qt            dvvideo                 libkvazaar              mpeg2video              pcm_s8                  s302m                   webvtt
adpcm_ima_ssi           eac3                    libmp3lame              mpeg4                   pcm_s8_planar           sbc                     wmav1
adpcm_ima_wav           exr                     libopencore_amrnb       mpeg4_v4l2m2m           pcm_u16be               sgi                     wmav2
adpcm_ima_ws            ffv1                    libopenjpeg             msmpeg4v2               pcm_u16le               smc                     wmv1
adpcm_ms                ffvhuff                 libopus                 msmpeg4v3               pcm_u24be               snow                    wmv2
adpcm_swf               fits                    librav1e                msvideo1                pcm_u24le               sonic                   wrapped_avframe
adpcm_yamaha            flac                    libshine                nellymoser              pcm_u32be               sonic_ls                xbm
alac                    flashsv                 libspeex                opus                    pcm_u32le               speedhq                 xface
alias_pix               flashsv2                libsvtav1               pam                     pcm_u8                  srt                     xsub
amv                     flv                     libtheora               pbm                     pcm_vidc                ssa                     xwd
apng                    g723_1                  libtwolame              pcm_alaw                pcx                     subrip                  y41p
aptx                    gif                     libvo_amrwbenc          pcm_bluray              pfm                     sunrast                 yuv4
aptx_hd                 h261                    libvorbis               pcm_dvd                 pgm                     svq1                    zlib
ass                     h263                    libvpx_vp8              pcm_f32be               pgmyuv                  targa                   zmbv
asv1                    h263_v4l2m2m            libvpx_vp9              pcm_f32le               phm                     text
asv2                    h263p                   libwebp                 pcm_f64be               png                     tiff
avrp                    h264_amf                libwebp_anim            pcm_f64le               ppm                     truehd
avui                    h264_nvenc              libx264                 pcm_mulaw               prores                  tta

Enabled hwaccels:
av1_nvdec               h264_vaapi              mjpeg_nvdec             mpeg2_vaapi             vc1_nvdec               vp9_nvdec               wmv3_vdpau
av1_vaapi               h264_vdpau              mjpeg_vaapi             mpeg2_vdpau             vc1_vaapi               vp9_vaapi
av1_vdpau               hevc_nvdec              mpeg1_nvdec             mpeg4_nvdec             vc1_vdpau               vp9_vdpau
h263_vaapi              hevc_vaapi              mpeg1_vdpau             mpeg4_vaapi             vp8_nvdec               wmv3_nvdec
h264_nvdec              hevc_vdpau              mpeg2_nvdec             mpeg4_vdpau             vp8_vaapi               wmv3_vaapi

Enabled parsers:
aac                     bmp                     dpx                     gif                     mjpeg                   qoi                     vp3
aac_latm                cavsvideo               dvaudio                 gsm                     mlp                     rv30                    vp8
ac3                     cook                    dvbsub                  h261                    mpeg4video              rv40                    vp9
adx                     cri                     dvd_nav                 h263                    mpegaudio               sbc                     webp
amr                     dca                     dvdsub                  h264                    mpegvideo               sipr                    xbm
av1                     dirac                   flac                    hevc                    opus                    tak                     xma
avs2                    dnxhd                   g723_1                  ipu                     png                     vc1
avs3                    dolby_e                 g729                    jpeg2000                pnm                     vorbis

Enabled demuxers:
aa                      bitpacked               g726le                  image_qdraw_pipe        mpc                     pcm_vidc                svag
aac                     bmv                     g729                    image_qoi_pipe          mpc8                    pjs                     svs
aax                     boa                     gdv                     image_sgi_pipe          mpegps                  pmp                     swf
ac3                     brstm                   genh                    image_sunrast_pipe      mpegts                  pp_bnk                  tak
ace                     c93                     gif                     image_svg_pipe          mpegtsraw               pva                     tedcaptions
acm                     caf                     gsm                     image_tiff_pipe         mpegvideo               pvf                     thp
act                     cavsvideo               gxf                     image_vbn_pipe          mpjpeg                  qcp                     threedostr
adf                     cdg                     h261                    image_webp_pipe         mpl2                    r3d                     tiertexseq
adp                     cdxl                    h263                    image_xbm_pipe          mpsub                   rawvideo                tmv
ads                     cine                    h264                    image_xpm_pipe          msf                     realtext                truehd
adx                     codec2                  hca                     image_xwd_pipe          msnwc_tcp               redspark                tta
aea                     codec2raw               hcom                    imf                     msp                     rl2                     tty
afc                     concat                  hevc                    ingenient               mtaf                    rm                      txd
aiff                    dash                    hls                     ipmovie                 mtv                     roq                     ty
aix                     data                    hnm                     ipu                     musx                    rpl                     v210
alp                     daud                    ico                     ircam                   mv                      rsd                     v210x
amr                     dcstr                   idcin                   iss                     mvi                     rso                     vag
amrnb                   derf                    idf                     iv8                     mxf                     rtp                     vapoursynth
amrwb                   dfa                     iff                     ivf                     mxg                     rtsp                    vc1
anm                     dfpwm                   ifv                     ivr                     nc                      s337m                   vc1t
apc                     dhav                    ilbc                    jacosub                 nistsphere              sami                    vividas
ape                     dirac                   image2                  jv                      nsp                     sap                     vivo
apm                     dnxhd                   image2_alias_pix        kux                     nsv                     sbc                     vmd
apng                    dsf                     image2_brender_pix      kvag                    nut                     sbg                     vobsub
aptx                    dsicin                  image2pipe              libgme                  nuv                     scc                     voc
aptx_hd                 dss                     image_bmp_pipe          libmodplug              obu                     scd                     vpk
aqtitle                 dts                     image_cri_pipe          live_flv                ogg                     sdp                     vplayer
argo_asf                dtshd                   image_dds_pipe          lmlm4                   oma                     sdr2                    vqf
argo_brp                dv                      image_dpx_pipe          loas                    paf                     sds                     w64
argo_cvg                dvbsub                  image_exr_pipe          lrc                     pcm_alaw                sdx                     wav
asf                     dvbtxt                  image_gem_pipe          luodat                  pcm_f32be               segafilm                wc3
asf_o                   dxa                     image_gif_pipe          lvf                     pcm_f32le               ser                     webm_dash_manifest
ass                     ea                      image_j2k_pipe          lxf                     pcm_f64be               sga                     webvtt
ast                     ea_cdata                image_jpeg_pipe         m4v                     pcm_f64le               shorten                 wsaud
au                      eac3                    image_jpegls_pipe       matroska                pcm_mulaw               siff                    wsd
av1                     epaf                    image_jpegxl_pipe       mca                     pcm_s16be               simbiosis_imx           wsvqa
avi                     ffmetadata              image_pam_pipe          mcc                     pcm_s16le               sln                     wtv
avisynth                filmstrip               image_pbm_pipe          mgsts                   pcm_s24be               smacker                 wv
avr                     fits                    image_pcx_pipe          microdvd                pcm_s24le               smjpeg                  wve
avs                     flac                    image_pfm_pipe          mjpeg                   pcm_s32be               smush                   xa
avs2                    flic                    image_pgm_pipe          mjpeg_2000              pcm_s32le               sol                     xbin
avs3                    flv                     image_pgmyuv_pipe       mlp                     pcm_s8                  sox                     xmv
bethsoftvid             fourxm                  image_pgx_pipe          mlv                     pcm_u16be               spdif                   xvag
bfi                     frm                     image_phm_pipe          mm                      pcm_u16le               srt                     xwma
bfstm                   fsb                     image_photocd_pipe      mmf                     pcm_u24be               stl                     yop
bink                    fwse                    image_pictor_pipe       mods                    pcm_u24le               str                     yuv4mpegpipe
binka                   g722                    image_png_pipe          moflex                  pcm_u32be               subviewer
bintext                 g723_1                  image_ppm_pipe          mov                     pcm_u32le               subviewer1
bit                     g726                    image_psd_pipe          mp3                     pcm_u8                  sup

Enabled muxers:
a64                     caf                     g723_1                  m4v                     null                    pcm_u32be               sup
ac3                     cavsvideo               g726                    matroska                nut                     pcm_u32le               swf
adts                    codec2                  g726le                  matroska_audio          obu                     pcm_u8                  tee
adx                     codec2raw               gif                     md5                     oga                     pcm_vidc                tg2
aiff                    crc                     gsm                     microdvd                ogg                     psp                     tgp
alp                     dash                    gxf                     mjpeg                   ogv                     rawvideo                truehd
amr                     data                    h261                    mkvtimestamp_v2         oma                     rm                      tta
amv                     daud                    h263                    mlp                     opus                    roq                     ttml
apm                     dfpwm                   h264                    mmf                     pcm_alaw                rso                     uncodedframecrc
apng                    dirac                   hash                    mov                     pcm_f32be               rtp                     vc1
aptx                    dnxhd                   hds                     mp2                     pcm_f32le               rtp_mpegts              vc1t
aptx_hd                 dts                     hevc                    mp3                     pcm_f64be               rtsp                    voc
argo_asf                dv                      hls                     mp4                     pcm_f64le               sap                     w64
argo_cvg                eac3                    ico                     mpeg1system             pcm_mulaw               sbc                     wav
asf                     f4v                     ilbc                    mpeg1vcd                pcm_s16be               scc                     webm
asf_stream              ffmetadata              image2                  mpeg1video              pcm_s16le               segafilm                webm_chunk
ass                     fifo_test               image2pipe              mpeg2dvd                pcm_s24be               segment                 webm_dash_manifest
ast                     filmstrip               ipod                    mpeg2svcd               pcm_s24le               smjpeg                  webp
au                      fits                    ircam                   mpeg2video              pcm_s32be               smoothstreaming         webvtt
avi                     flac                    ismv                    mpeg2vob                pcm_s32le               sox                     wsaud
avif                    flv                     ivf                     mpegts                  pcm_s8                  spdif                   wtv
avm2                    framecrc                jacosub                 mpjpeg                  pcm_u16be               spx                     wv
avs2                    framehash               kvag                    mxf                     pcm_u16le               srt                     yuv4mpegpipe
avs3                    framemd5                latm                    mxf_d10                 pcm_u24be               stream_segment
bit                     g722                    lrc                     mxf_opatom              pcm_u24le               streamhash

Enabled protocols:
bluray                  ffrtmphttp              httpproxy               libssh                  rtmpe                   srtp                    unix
cache                   file                    https                   md5                     rtmps                   subfile
concat                  ftp                     icecast                 mmsh                    rtmpt                   tcp
concatf                 gopher                  ipfs                    mmst                    rtmpte                  tee
crypto                  gophers                 ipns                    pipe                    rtmpts                  tls
data                    hls                     libsmbclient            prompeg                 rtp                     udp
ffrtmpcrypt             http                    libsrt                  rtmp                    sctp                    udplite

Enabled filters:
abench                  asegment                colorspectrum           fifo                    lut2                    realtime                stereotools
abitscope               aselect                 colortemperature        fillborders             lut3d                   remap                   stereowiden
acompressor             asendcmd                compand                 find_rect               lutrgb                  remap_opencl            streamselect
acontrast               asetnsamples            compensationdelay       firequalizer            lutyuv                  removegrain             subtitles
acopy                   asetpts                 concat                  flanger                 lv2                     removelogo              super2xsai
acrossfade              asetrate                convolution             flite                   mandelbrot              repeatfields            superequalizer
acrossover              asettb                  convolution_opencl      floodfill               maskedclamp             replaygain              surround
acrusher                ashowinfo               convolve                format                  maskedmax               reverse                 swaprect
acue                    asidedata               copy                    fps                     maskedmerge             rgbashift               swapuv
addroi                  asoftclip               cover_rect              framepack               maskedmin               rgbtestsrc              tblend
adeclick                aspectralstats          crop                    framerate               maskedthreshold         roberts                 telecine
adeclip                 asplit                  cropdetect              framestep               maskfun                 roberts_opencl          testsrc
adecorrelate            ass                     crossfeed               freezedetect            mcompand                rotate                  testsrc2
adelay                  astats                  crystalizer             freezeframes            median                  rubberband              thistogram
adenorm                 astreamselect           cue                     frei0r                  mergeplanes             sab                     threshold
aderivative             asubboost               curves                  frei0r_src              mestimate               scale                   thumbnail
adrawgraph              asubcut                 datascope               fspp                    metadata                scale2ref               thumbnail_cuda
adynamicequalizer       asupercut               dblur                   gblur                   midequalizer            scale_cuda              tile
adynamicsmooth          asuperpass              dcshift                 geq                     minterpolate            scale_vaapi             tiltshelf
aecho                   asuperstop              dctdnoiz                gradfun                 mix                     scdet                   tinterlace
aemphasis               atadenoise              deband                  gradients               monochrome              scharr                  tlut2
aeval                   atempo                  deblock                 graphmonitor            morpho                  scroll                  tmedian
aevalsrc                atilt                   decimate                grayworld               movie                   segment                 tmidequalizer
aexciter                atrim                   deconvolve              greyedge                mpdecimate              select                  tmix
afade                   avectorscope            dedot                   guided                  mptestsrc               selectivecolor          tonemap
afftdn                  avgblur                 deesser                 haas                    msad                    sendcmd                 tonemap_opencl
afftfilt                avgblur_opencl          deflate                 haldclut                multiply                separatefields          tonemap_vaapi
afifo                   avsynctest              deflicker               haldclutsrc             negate                  setdar                  tpad
afir                    axcorrelate             deinterlace_vaapi       hdcd                    nlmeans                 setfield                transpose
afirsrc                 bandpass                dejudder                headphone               nlmeans_opencl          setparams               transpose_opencl
aformat                 bandreject              delogo                  hflip                   nnedi                   setpts                  transpose_vaapi
afreqshift              bass                    denoise_vaapi           highpass                noformat                setrange                treble
afwtdn                  bbox                    derain                  highshelf               noise                   setsar                  tremolo
agate                   bench                   deshake                 hilbert                 normalize               settb                   trim
agraphmonitor           bilateral               deshake_opencl          histeq                  null                    sharpness_vaapi         unpremultiply
ahistogram              biquad                  despill                 histogram               nullsink                shear                   unsharp
aiir                    bitplanenoise           detelecine              hqdn3d                  nullsrc                 showcqt                 unsharp_opencl
aintegral               blackdetect             dialoguenhance          hqx                     ocr                     showfreqs               untile
ainterleave             blackframe              dilation                hstack                  openclsrc               showinfo                v360
alatency                blend                   dilation_opencl         hsvhold                 oscilloscope            showpalette             vaguedenoiser
alimiter                blockdetect             displace                hsvkey                  overlay                 showspatial             varblur
allpass                 blurdetect              dnn_classify            hue                     overlay_cuda            showspectrum            vectorscope
allrgb                  bm3d                    dnn_detect              huesaturation           overlay_opencl          showspectrumpic         vflip
allyuv                  boxblur                 dnn_processing          hwdownload              overlay_vaapi           showvolume              vfrdet
aloop                   boxblur_opencl          doubleweave             hwmap                   owdenoise               showwaves               vibrance
alphaextract            bs2b                    drawbox                 hwupload                pad                     showwavespic            vibrato
alphamerge              bwdif                   drawgraph               hwupload_cuda           pad_opencl              shuffleframes           vidstabdetect
amerge                  cas                     drawgrid                hysteresis              pal100bars              shufflepixels           vidstabtransform
ametadata               cellauto                drawtext                iccdetect               pal75bars               shuffleplanes           vif
amix                    channelmap              drmeter                 iccgen                  palettegen              sidechaincompress       vignette
amovie                  channelsplit            dynaudnorm              identity                paletteuse              sidechaingate           virtualbass
amplify                 chorus                  earwax                  idet                    pan                     sidedata                vmafmotion
amultiply               chromahold              ebur128                 il                      perms                   sierpinski              volume
anequalizer             chromakey               edgedetect              inflate                 perspective             signalstats             volumedetect
anlmdn                  chromakey_cuda          elbg                    interlace               phase                   signature               vstack
anlmf                   chromanr                entropy                 interleave              photosensitivity        silencedetect           w3fdif
anlms                   chromashift             epx                     join                    pixdesctest             silenceremove           waveform
anoisesrc               ciescope                eq                      kerndeint               pixelize                sinc                    weave
anull                   codecview               equalizer               kirsch                  pixscope                sine                    xbr
anullsink               color                   erosion                 ladspa                  pp                      siti                    xcorrelate
anullsrc                colorbalance            erosion_opencl          lagfun                  pp7                     smartblur               xfade
apad                    colorchannelmixer       estdif                  latency                 premultiply             smptebars               xfade_opencl
aperms                  colorchart              exposure                lenscorrection          prewitt                 smptehdbars             xmedian
aphasemeter             colorcontrast           extractplanes           life                    prewitt_opencl          sobel                   xstack
aphaser                 colorcorrect            extrastereo             limitdiff               procamp_vaapi           sobel_opencl            yadif
aphaseshift             colorhold               fade                    limiter                 program_opencl          sofalizer               yadif_cuda
apsyclip                colorize                feedback                loop                    pseudocolor             spectrumsynth           yaepblur
apulsator               colorkey                fftdnoiz                loudnorm                psnr                    speechnorm              yuvtestsrc
arealtime               colorkey_opencl         fftfilt                 lowpass                 pullup                  split                   zoompan
aresample               colorlevels             field                   lowshelf                qp                      spp                     zscale
areverse                colormap                fieldhint               lumakey                 random                  sr
arnndn                  colormatrix             fieldmatch              lut                     readeia608              ssim
asdr                    colorspace              fieldorder              lut1d                   readvitc                stereo3d

Enabled bsfs:
aac_adtstoasc           dump_extradata          h264_mp4toannexb        mjpeg2jpeg              noise                   remove_extradata        vp9_raw_reorder
av1_frame_merge         dv_error_marker         h264_redundant_pps      mjpega_dump_header      null                    setts                   vp9_superframe
av1_frame_split         eac3_core               hapqa_extract           mov2textsub             opus_metadata           text2movsub             vp9_superframe_split
av1_metadata            extract_extradata       hevc_metadata           mp3_header_decompress   pcm_rechunk             trace_headers
chomp                   filter_units            hevc_mp4toannexb        mpeg2_metadata          pgs_frame_merge         truehd_core
dca_core                h264_metadata           imx_dump_header         mpeg4_unpack_bframes    prores_metadata         vp9_metadata

Enabled indevs:
alsa                    lavfi                   oss                     sndio                   xcbgrab
fbdev                   libcdio                 pulse                   v4l2

Enabled outdevs:
alsa                    fbdev                   oss                     sdl2                    v4l2
caca                    opengl                  pulse                   sndio                   xv

License: nonfree and unredistributable
$ make -j32
$ make install
============================================
               FFmpeg Version               
============================================

ffmpeg version 5.1.3-963937e Copyright (c) 2000-2022 the FFmpeg developers
built with gcc 11 (Ubuntu 11.4.0-1ubuntu1~22.04)
configuration: --prefix=/home/jman/tmp/ffmpeg-build-script/workspace --arch=x86_64 --cpu=16 --cc=gcc --cxx=g++ --disable-debug --disable-doc --disable-large-tests --disable-shared --enable-openssl --enable-libxml2 --enable-libaribb24 --enable-libfreetype --enable-libfontconfig --enable-libfribidi --enable-libass --enable-libwebp --enable-lcms2 --enable-libjxl --enable-opencl --enable-libtesseract --enable-librubberband --enable-libzimg --enable-lv2 --enable-libfdk-aac --enable-libvorbis --enable-libopus --enable-libmysofa --enable-libvpx --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libaom --enable-libdav1d --enable-librav1e --enable-libkvazaar --enable-libbluray --enable-libvidstab --enable-frei0r --enable-amf --enable-libsvtav1 --enable-libx264 --enable-libx265 --enable-cuda-nvcc --enable-cuda-llvm --enable-cuvid --enable-nvenc --nvccflags='-gencode arch=compute_86,code=sm_86' --enable-libsrt --enable-avisynth --enable-vapoursynth --enable-libxvid --enable-libopenjpeg --enable-ffnvcodec --enable-gpl --enable-ladspa --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libflite --enable-libgme --enable-libmodplug --enable-libpulse --enable-libshine --enable-libsmbclient --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libssh --enable-libtwolame --enable-libv4l2 --enable-libvo-amrwbenc --enable-lto --enable-nonfree --enable-opengl --enable-pic --enable-pthreads --enable-small --enable-static --enable-version3 --extra-cflags='-I/home/jman/tmp/ffmpeg-build-script/workspace/include -I/usr/local/include -I/usr/include -I/usr/include/x86_64-linux-gnu -I/usr/include/SDL2 -I/usr/lib/x86_64-linux-gnu/pulseaudio -I/usr/include/openjpeg-2.5 -I/home/jman/tmp/ffmpeg-build-script/workspace/include/CL -g -O2 -march=native -I/home/jman/tmp/ffmpeg-build-script/workspace/include/lilv-0 -I/usr/local/cuda-12.2/include -I/home/jman/tmp/ffmpeg-build-script/workspace/include/avisynth' --extra-cxxflags='-g -O2 -march=native' --extra-ldflags='-L/home/jman/tmp/ffmpeg-build-script/workspace/lib64 -L/home/jman/tmp/ffmpeg-build-script/workspace/lib -L/home/jman/tmp/ffmpeg-build-script/workspace/lib/x86_64-linux-gnu -L/usr/local/lib64 -L/usr/local/lib -L/usr/lib/x86_64-linux-gnu -L/usr/lib64 -L/usr/lib -L/lib64 -L/lib -L/usr/local/cuda-12.2/lib64' --extra-ldexeflags= --extra-libs='-ldl -lpthread -lm -lz -L/usr/local/cuda-12.2/targets/x86_64-linux/lib -lOpenCL -L/home/jman/tmp/ffmpeg-build-script/workspace/lib -L/usr/lib/x86_64-linux-gnu -ltesseract -lcurl' --pkg-config-flags=--static --pkg-config=/home/jman/tmp/ffmpeg-build-script/workspace/bin/pkg-config --pkgconfigdir=/home/jman/tmp/ffmpeg-build-script/workspace/lib/pkgconfig --strip=/usr/bin/strip
libavutil      57. 28.100 / 57. 28.100
libavcodec     59. 37.100 / 59. 37.100
libavformat    59. 27.100 / 59. 27.100
libavdevice    59.  7.100 / 59.  7.100
libavfilter     8. 44.100 /  8. 44.100
libswscale      6.  7.100 /  6.  7.100
libswresample   4.  7.100 /  4.  7.100
libpostproc    56.  6.100 / 56.  6.100

Would you like to install the static binaries system-wide? [/usr/local/bin]

[1] Yes 
[2] No

Your choices are (1 or 2): 1

============================================
  Do you want to clean up the build files?  
============================================

[1] Yes
[2] No

Your choices are (1 or 2): 2

Make sure to star this repository to show your support!

https://github.com/slyfox1186/script-repo
```
