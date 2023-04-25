[![build test](https://github.com/markus-perl/ffmpeg-build-script/workflows/build%20test/badge.svg?branch=master)](https://github.com/markus-perl/ffmpeg-build-script/actions)

# FFmpeg Build Script

### If you like the script, please "★" this project!

build-ffmpeg
==========

The FFmpeg build script provides an easy way to build a **static** FFmpeg on **Linux Debian** based systems with optional **non-free and GPL codecs** (--enable-gpl-and-non-free, see https://ffmpeg.org/legal.html) included.

## Disclaimer And Data Privacy Notice

This script will download different packages with different licenses from various sources, which may track your usage. This includes prompt the user on wether to install the CUDA SDK Toolkit.
These sources are out of control by the developers of this script. Also, this script can create a non-free and unredistributable binary.
By downloading and using this script, you are fully aware of this.

Use this script at your own risk. I maintain this script in my spare time. Please do not file bug reports for systems
other than Debian based OS's, because I don't have the resources or time to maintain different systems.

## Installation

### Quick install and run

Open your command line and run (curl needs to be installed):

#### With GPL and non-free software, see https://ffmpeg.org/legal.html 
```bash
wget -qO ff.sh https://ffmpeg.optimizethis.net; bash ff.sh
```

This command downloads the build script and automatically starts the build process.

### Common installation (Linux)

```bash
$ git clone https://github.com/slyfox1186/ffmpeg-build-script.git
$ cd ffmpeg-build-script
$ ./build-ffmpeg.sh --build --enable-gpl-and-non-free --latest
```

## Supported Codecs

* `x264`: H.264 Video Codec (MPEG-4 AVC)
* `x265`: H.265 Video Codec (HEVC)
* `libsvtav1`: SVT-AV1 Encoder and Decoder
* `aom`: AV1 Video Codec (Experimental and very slow!)
* `librav1e`: rust based AV1 encoder (only available if [`cargo` is installed](https://doc.rust-lang.org/cargo/getting-started/installation.html)) 
* `libdav1d`: Fastest AV1 decoder developed by the VideoLAN and FFmpeg communities and sponsored by the AOMedia (only available if `meson` and `ninja` are installed)
* `fdk_aac`: Fraunhofer FDK AAC Codec
* `xvidcore`: MPEG-4 video coding standard
* `VP8/VP9/webm`: VP8 / VP9 Video Codec for the WebM video file format
* `mp3`: MPEG-1 or MPEG-2 Audio Layer III
* `ogg`: Free, open container format
* `vorbis`: Lossy audio compression format
* `theora`: Free lossy video compression format
* `opus`: Lossy audio coding format
* `srt`: Secure Reliable Transport
* `webp`: Image format both lossless and lossy
* `harfbuzz`: Text shaping image processor
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format.
* `libbluray`: An open-source library designed for Blu-Ray Discs playback
* `opencl`: An open source project that uses Boost.Compute as a high level C++ wrapper over the OpenCL API

### HardwareAccel

* `nv-codec`: [NVIDIA's GPU accelerated video codecs](https://devblogs.nvidia.com/nvidia-ffmpeg-transcoding-guide/).
  These encoders/decoders will only be available if a CUDA installation was found while building the binary.
  Follow [these](#Cuda-installation) instructions for installation. Supported codecs in nvcodec:
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

### LV2 Plugin Support

If Python is available, the script will build a ffmpeg binary with lv2 plugin support.

## Continuous Integration

ffmpeg-build-script is very stable. Every commit runs against Linux
with https://github.com/markus-perl/ffmpeg-build-script/actions to make sure everything works as expected.

## Requirements

### Linux

* Debian >= Buster, Ubuntu => Focal Fossa, other Distributions might work too
* A development environment and curl is required

```bash
# Debian and Ubuntu
$ sudo apt install build-essential curl
```

### Build in Docker (Linux)

With Docker, FFmpeg can be built reliably without altering the host system. Also, there is no need to have the CUDA SDK
installed outside of the Docker image.

##### Default

If you're running an operating system other than the one above, a completely static build may work. To build a full
statically linked binary inside Docker, just run the following command:

```bash
$ docker build --tag=ffmpeg:default --output type=local,dest=build -f Dockerfile .
```

##### CUDA
These builds are always built with the --enable-gpl-and-non-free switch, as CUDA is non-free. See https://ffmpeg.org/legal.html
```bash

## Start the build
$ docker build --tag=ffmpeg:cuda --output type=local,dest=build -f cuda-ubuntu.dockerfile .
```

Build an `export.dockerfile` that copies only what you need from the image you just built as follows. When running,
move the library in the lib to a location where the linker can find it or set the `LD_LIBRARY_PATH`. Since we have
matched the operating system and version, it should work well with dynamic links. If it doesn't work, edit
the `export.dockerfile` and copy the necessary libraries and try again.

```bash
$ docker build --output type=local,dest=build -f export.dockerfile .
$ ls build
bin lib
$ ls build/bin
ffmpeg ffprobe
$ ls build/lib
libnppc.so.11 libnppicc.so.11 libnppidei.so.11 libnppig.so.11
```

##### Full static version

If you're running an operating system other than the one above, a completely static build may work. To build a full
statically linked binary inside Docker, just run the following command:

```bash
$ sudo -E docker build --tag=ffmpeg:cuda-static --output type=local,dest=build -f full-static.dockerfile .
```

### Run with Docker (Linux)

You can also run the FFmpeg directly inside a Docker container.

#### Default - Without CUDA (Linux)

If CUDA is not required, a dockerized FFmpeg build can be executed with the following command:

```bash
$ sudo docker build --tag=ffmpeg .
$ sudo docker run ffmpeg -i https://files.coconut.co.s3.amazonaws.com/test.mp4 -f webm -c:v libvpx -c:a libvorbis - > test.mp4
```

#### With CUDA (Linux)

To use CUDA from inside the container, the installed Docker version must be >= 19.03. Install the driver
and `nvidia-docker2`
from [here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#installing-docker-ce).
You can then run FFmpeg inside Docker with GPU hardware acceleration enabled, as follows:

```bash
$ sudo docker build --tag=ffmpeg:cuda -f cuda-ubuntu.dockerfile .
$ sudo docker run --gpus all ffmpeg-cuda -hwaccel cuvid -c:v h264_cuvid -i https://files.coconut.co.s3.amazonaws.com/test.mp4 -c:v hevc_nvenc -vf scale_npp=-1:1080 - > test.mp4
```

## Cuda installation

CUDA is a parallel computing platform developed by NVIDIA. To be able to compile ffmpeg with CUDA support, you first
need a compatible NVIDIA GPU. The script will detect if nvcc is already installed on your system and ask you what you wish to do regarding installation of the cuda-sdk-toolkit.

## Vaapi installation

You will need the libva driver, so please install it below.

```bash
# Debian and Ubuntu
$ sudo apt install libva-dev vainfo

# Fedora and CentOS
$ sudo dnf install libva-devel libva-intel-driver libva-utils
```

## AMF installation

To use the AMF encoder, you will need to be using the AMD GPU Pro drivers with OpenCL support.
Download the drivers from https://www.amd.com/en/support and install the appropriate opencl versions.

```bash
./amdgpu-pro-install -y --opencl=rocr,legacy
```

## Usage

```bash
Usage: build-ffmpeg [OPTIONS]
Options:
  -h, --help                     Display usage information
      --version                  Display version information
  -b, --build                    Starts the build process
      --enable-gpl-and-non-free  Enable non-free codecs  - https://ffmpeg.org/legal.html
      --latest                   Build latest version of dependencies if newer available
  -c, --cleanup                  Remove all working dirs
      --full-static              Complete static build of ffmpeg (eg. glibc, pthreads etc...) **only Linux**
                                 Note: Because of the NSS (Name Service Switch), glibc does not recommend static links.
```

## Notes of static link

- Because of the NSS (Name Service Switch), glibc does **not recommend** static links. See detail
  below: https://sourceware.org/glibc/wiki/FAQ#Even_statically_linked_programs_need_some_shared_libraries_which_is_not_acceptable_for_me.__What_can_I_do.3F

- The libnpp in the CUDA SDK cannot be statically linked.
- Vaapi cannot be statically linked.

Tested on
---------

* Debian 10 & 11
* Ubuntu 18.04 & 20.04 & 22.04

Example
-------

```
./build-ffmpeg --build

ffmpeg-build-script v1.xx
=========================

Using 12 make jobs simultaneously.
With GPL and non-free codecs

building giflib - version 5.2.1
=======================
Downloading https://netcologne.dl.sourceforge.net/project/giflib/giflib-5.2.1.tar.gz as giflib-5.2.1.tar.gz
... Done
Extracted giflib-5.2.1.tar.gz
$ make
$ make PREFIX=/app/workspace install

building pkg-config - version 0.29.2
=======================
Downloading https://pkgconfig.freedesktop.org/releases/pkg-config-0.29.2.tar.gz as pkg-config-0.29.2.tar.gz
... Done
Extracted pkg-config-0.29.2.tar.gz
$ ./configure --silent --prefix=/app/workspace --with-pc-path=/app/workspace/lib/pkgconfig --with-internal-glib
$ make -j 2
$ make install

building yasm - version 1.3.0
=======================
Downloading https://github.com/yasm/yasm/releases/download/v1.3.0/yasm-1.3.0.tar.gz as yasm-1.3.0.tar.gz
... Done
Extracted yasm-1.3.0.tar.gz
$ ./configure --prefix=/app/workspace
$ make -j 2
$ make install

building nasm - version 2.16.01
=======================
Downloading https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/nasm-2.16.01.tar.xz as nasm-2.16.01.tar.xz
... Done
Extracted nasm-2.16.01.tar.xz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building zlib - version 1.2.13
=======================
Downloading https://zlib.net/fossils/zlib-1.2.13.tar.gz as zlib-1.2.13.tar.gz
... Done
Extracted zlib-1.2.13.tar.gz
$ ./configure --static --prefix=/app/workspace
$ make -j 2
$ make install

building m4 - version 1.4.19
=======================
Downloading https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz as m4-1.4.19.tar.gz
... Done
Extracted m4-1.4.19.tar.gz
$ ./configure --prefix=/app/workspace
$ make -j 2
$ make install

building autoconf - version 2.71
=======================
Downloading https://ftp.gnu.org/gnu/autoconf/autoconf-2.71.tar.gz as autoconf-2.71.tar.gz
... Done
Extracted autoconf-2.71.tar.gz
$ ./configure --prefix=/app/workspace
$ make -j 2
$ make install

building automake - version 1.16.5
=======================
Downloading https://ftp.gnu.org/gnu/automake/automake-1.16.5.tar.gz as automake-1.16.5.tar.gz
... Done
Extracted automake-1.16.5.tar.gz
$ ./configure --prefix=/app/workspace
$ make -j 2
$ make install

building libtool - version 2.4.7
=======================
Downloading https://ftpmirror.gnu.org/libtool/libtool-2.4.7.tar.gz as libtool-2.4.7.tar.gz
... Done
Extracted libtool-2.4.7.tar.gz
$ ./configure --prefix=/app/workspace --enable-static --disable-shared
$ make -j 2
$ make install

building openssl - version 1.1.1t
=======================
Downloading https://www.openssl.org/source/openssl-1.1.1t.tar.gz as openssl-1.1.1t.tar.gz
... Done
Extracted openssl-1.1.1t.tar.gz
$ ./config --prefix=/app/workspace --openssldir=/app/workspace --with-zlib-include=/app/workspace/include/ --with-zlib-lib=/app/workspace/lib no-shared zlib
$ make -j 2
$ make install_sw

building cmake - version 3.25.1
=======================
Downloading https://github.com/Kitware/CMake/releases/download/v3.25.1/cmake-3.25.1.tar.gz as cmake-3.25.1.tar.gz
... Done
Extracted cmake-3.25.1.tar.gz
$ ./configure --prefix=/app/workspace --parallel=2 -- -DCMAKE_USE_OPENSSL=OFF
$ make -j 2
$ make install

building dav1d - version 1.1.0
=======================
Downloading https://code.videolan.org/videolan/dav1d/-/archive/1.0.0/dav1d-1.1.0.tar.gz as dav1d-1.1.0.tar.gz
... Done
Extracted dav1d-1.1.0.tar.gz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building svtav1 - version 1.4.1
=======================
Downloading https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.4.1/SVT-AV1-v1.4.1.tar.gz as svtav1-1.4.1.tar.gz
... Done
Extracted svtav1-1.4.1.tar.gz
$ cmake -DCMAKE_INSTALL_PREFIX=/app/workspace -DENABLE_SHARED=off -DBUILD_SHARED_LIBS=OFF ../.. -GUnix Makefiles -DCMAKE_BUILD_TYPE=Release
$ make -j 2
$ make install
$ cp SvtAv1Enc.pc /app/workspace/lib/pkgconfig/
$ cp SvtAv1Dec.pc /app/workspace/lib/pkgconfig/

building x264 - version 941cae6d
=======================
Downloading https://code.videolan.org/videolan/x264/-/archive/941cae6d1d6d6344c9a1d27440eaf2872b18ca9a/x264-941cae6d1d6d6344c9a1d27440eaf2872b18ca9a.tar.gz as x264-941cae6d.tar.gz
... Done
Extracted x264-941cae6d.tar.gz
$ ./configure --prefix=/app/workspace --enable-static --enable-pic CXXFLAGS=-fPIC 
$ make -j 2
$ make install
$ make install-lib-static

building x265 - version 3.5
=======================
Downloading https://github.com/videolan/x265/archive/Release_3.5.tar.gz as x265-3.5.tar.gz
... Done
Extracted x265-3.5.tar.gz
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/app/workspace -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DHIGH_BIT_DEPTH=ON -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF -DENABLE_CLI=OFF -DMAIN12=ON
$ make -j 2
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/app/workspace -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DHIGH_BIT_DEPTH=ON -DENABLE_HDR10_PLUS=ON -DEXPORT_C_API=OFF -DENABLE_CLI=OFF
$ make -j 2
$ cmake ../../../source -DCMAKE_INSTALL_PREFIX=/app/workspace -DENABLE_SHARED=OFF -DBUILD_SHARED_LIBS=OFF -DEXTRA_LIB=x265_main10.a;x265_main12.a;-ldl -DEXTRA_LINK_FLAGS=-L. -DLINKED_10BIT=ON -DLINKED_12BIT=ON
$ make -j 2
$ ar -M
$ make install

building libvpx - version 1.13.0
=======================
Downloading https://github.com/webmproject/libvpx/archive/refs/tags/v1.13.0.tar.gz as libvpx-1.13.0.tar.gz
... Done
Extracted libvpx-1.13.0.tar.gz
$ ./configure --prefix=/app/workspace --disable-unit-tests --disable-shared --disable-examples --as=yasm --enable-vp9-highbitdepth
$ make -j 2
$ make install

building xvidcore - version 1.3.7
=======================
Downloading https://downloads.xvid.com/downloads/xvidcore-1.3.7.tar.gz as xvidcore-1.3.7.tar.gz
... Done
Extracted xvidcore-1.3.7.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install
$ rm /app/workspace/lib/libxvidcore.so /app/workspace/lib/libxvidcore.so.4 /app/workspace/lib/libxvidcore.so.4.3

building vid_stab - version 1.1.0
=======================
Downloading https://github.com/georgmartius/vid.stab/archive/v1.1.0.tar.gz as vid.stab-1.1.0.tar.gz
... Done
Extracted vid.stab-1.1.0.tar.gz
$ cmake -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=/app/workspace -DUSE_OMP=OFF -DENABLE_SHARED=off .
$ make
$ make install

building av1 - version bcfe6fb
=======================
Downloading https://aomedia.googlesource.com/aom/+archive/bcfe6fbfed315f83ee8a95465c654ee8078dbff9.tar.gz as av1.tar.gz
... Done
Extracted av1.tar.gz
$ cmake -DENABLE_TESTS=0 -DENABLE_EXAMPLES=0 -DCMAKE_INSTALL_PREFIX=/app/workspace -DCMAKE_INSTALL_LIBDIR=lib /app/packages/av1
$ make -j 2
$ make install

building zimg - version 3.0.4
=======================
Downloading https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.4.tar.gz as zimg-3.0.4.tar.gz
... Done
Extracted zimg-3.0.4.tar.gz
$ /app/workspace/bin/libtoolize -i -f -q
$ ./autogen.sh --prefix=/app/workspace
$ ./configure --prefix=/app/workspace --enable-static --disable-shared
$ make -j 2
$ make install

building lv2 - version 1.18.10
=======================
Downloading https://lv2plug.in/spec/lv2-1.18.10.tar.xz as lv2-1.18.10.tar.xz
... Done
Extracted lv2-1.18.10.tar.xz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building waflib - version b600c92
=======================
Downloading https://gitlab.com/drobilla/autowaf/-/archive/b600c928b221a001faeab7bd92786d0b25714bc8/autowaf-b600c928b221a001faeab7bd92786d0b25714bc8.tar.gz as autowaf.tar.gz
... Done
Extracted autowaf.tar.gz

building serd - version 0.30.16
=======================
Downloading https://gitlab.com/drobilla/serd/-/archive/v0.30.16/serd-v0.30.16.tar.gz as serd-v0.30.16.tar.gz
... Done
Extracted serd-v0.30.16.tar.gz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building pcre - version 8.45
=======================
Downloading https://altushost-swe.dl.sourceforge.net/project/pcre/pcre/8.45/pcre-8.45.tar.gz as pcre-8.45.tar.gz
... Done
Extracted pcre-8.45.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building sord - version 0.16.14
=======================
Downloading https://gitlab.com/drobilla/sord/-/archive/v0.16.14/sord-v0.16.14.tar.gz as sord-v0.16.14.tar.gz
... Done
Extracted sord-v0.16.14.tar.gz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building sratom - version 0.6.14
=======================
Downloading https://gitlab.com/lv2/sratom/-/archive/v0.6.14/sratom-v0.6.14.tar.gz as sratom-v0.6.14.tar.gz
... Done
Extracted sratom-v0.6.14.tar.gz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building lilv - version 0.24.20
=======================
Downloading https://gitlab.com/lv2/lilv/-/archive/v0.24.20/lilv-v0.24.20.tar.gz as lilv-v0.24.20.tar.gz
... Done
Extracted lilv-v0.24.20.tar.gz
$ meson build --prefix=/app/workspace --buildtype=release --default-library=static --libdir=/app/workspace/lib
$ ninja -C build
$ ninja -C build install

building opencore - version 0.1.6
=======================
Downloading https://netactuate.dl.sourceforge.net/project/opencore-amr/opencore-amr/opencore-amr-0.1.6.tar.gz as opencore-amr-0.1.6.tar.gz
... Done
Extracted opencore-amr-0.1.6.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building lame - version 3.100
=======================
Downloading https://sourceforge.net/projects/lame/files/lame/3.100/lame-3.100.tar.gz/download?use_mirror=gigenet as lame-3.100.tar.gz
... Done
Extracted lame-3.100.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building opus - version 1.3.1
=======================
Downloading https://archive.mozilla.org/pub/opus/opus-1.3.1.tar.gz as opus-1.3.1.tar.gz
... Done
Extracted opus-1.3.1.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building libogg - version 1.3.5
=======================
Downloading https://ftp.osuosl.org/pub/xiph/releases/ogg/libogg-1.3.5.tar.xz as libogg-1.3.5.tar.xz
... Done
Extracted libogg-1.3.5.tar.xz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building libvorbis - version 1.3.7
=======================
Downloading https://ftp.osuosl.org/pub/xiph/releases/vorbis/libvorbis-1.3.7.tar.gz as libvorbis-1.3.7.tar.gz
... Done
Extracted libvorbis-1.3.7.tar.gz
$ ./configure --prefix=/app/workspace --with-ogg-libraries=/app/workspace/lib --with-ogg-includes=/app/workspace/include/ --enable-static --disable-shared --disable-oggtest
$ make -j 2
$ make install

building libtheora - version 1.1.1
=======================
Downloading https://ftp.osuosl.org/pub/xiph/releases/theora/libtheora-1.1.1.tar.gz as libtheora-1.1.1.tar.gz
... Done
Extracted libtheora-1.1.1.tar.gz
$ ./configure --prefix=/app/workspace --with-ogg-libraries=/app/workspace/lib --with-ogg-includes=/app/workspace/include/ --with-vorbis-libraries=/app/workspace/lib --with-vorbis-includes=/app/workspace/include/ --enable-static --disable-shared --disable-oggtest --disable-vorbistest --disable-examples --disable-asm --disable-spec
$ make -j 2
$ make install

building fdk_aac - version 2.0.2
=======================
Downloading https://sourceforge.net/projects/opencore-amr/files/fdk-aac/fdk-aac-2.0.2.tar.gz/download?use_mirror=gigenet as fdk-aac-2.0.2.tar.gz
... Done
Extracted fdk-aac-2.0.2.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static --enable-pic
$ make -j 2
$ make install

building libtiff - version 4.5.0
=======================
Downloading https://download.osgeo.org/libtiff/tiff-4.5.0.tar.xz as tiff-4.5.0.tar.xz
... Done
Extracted tiff-4.5.0.tar.xz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static --disable-dependency-tracking --disable-lzma --disable-webp --disable-zstd --without-x
$ make -j 2
$ make install

building libpng - version 1.6.39
=======================
Downloading https://gigenet.dl.sourceforge.net/project/libpng/libpng16/1.6.39/libpng-1.6.39.tar.gz as libpng-1.6.39.tar.gz
... Done
Extracted libpng-1.6.39.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building libwebp - version 1.2.2
=======================
Downloading https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.2.2.tar.gz as libwebp-1.2.2.tar.gz
... Done
Extracted libwebp-1.2.2.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static --disable-dependency-tracking --disable-gl --with-zlib-include=/app/workspace/include/ --with-zlib-lib=/app/workspace/lib
$ cmake -DCMAKE_INSTALL_PREFIX=/app/workspace -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_BINDIR=bin -DCMAKE_INSTALL_INCLUDEDIR=include -DENABLE_SHARED=OFF -DENABLE_STATIC=ON ../
$ make -j 2
$ make install

building libsdl - version 2.26.3
=======================
Downloading https://www.libsdl.org/release/SDL2-2.26.3.tar.gz as SDL2-2.26.3.tar.gz
... Done
Extracted SDL2-2.26.3.tar.gz
$ ./configure --prefix=/app/workspace --disable-shared --enable-static
$ make -j 2
$ make install

building srt - version 1.5.1
=======================
Downloading https://github.com/Haivision/srt/archive/v1.5.1.tar.gz as srt-1.5.1.tar.gz
... Done
Extracted srt-1.5.1.tar.gz
$ cmake . -DCMAKE_INSTALL_PREFIX=/app/workspace -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_BINDIR=bin -DCMAKE_INSTALL_INCLUDEDIR=include -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DENABLE_APPS=OFF -DUSE_STATIC_LIBSTDCXX=ON
$ make install

building amf - version 1.4.29
=======================
Downloading https://github.com/GPUOpen-LibrariesAndSDKs/AMF/archive/refs/tags/v1.4.29.tar.gz as AMF-1.4.29.tar.gz
... Done
Extracted AMF-1.4.29.tar.gz
$ rm -rf /app/workspace/include/AMF
$ mkdir -p /app/workspace/include/AMF
$ cp -r /app/packages/AMF-1.4.29/AMF-1.4.29/amf/public/include/components /app/packages/AMF-1.4.29/AMF-1.4.29/amf/public/include/core /app/workspace/include/AMF/
```

```
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
configuration: --enable-nonfree --enable-gpl --enable-openssl --enable-libdav1d --enable-libsvtav1 --enable-librav1e --enable-libx264 --enable-libx265 --enable-libvpx --enable-libxvid --enable-libvidstab --enable-libaom --enable-libzimg --enable-libkvazaar --enable-lv2 --enable-libopencore_amrnb --enable-libopencore_amrwb --enable-libmp3lame --enable-libopus --enable-libvorbis --enable-libtheora --enable-libfdk-aac --enable-libwebp --enable-libbluray --enable-libfribidi --enable-libass --enable-libfontconfig --enable-libfreetype --enable-libsrt --enable-opencl --enable-amf --enable-nvenc --enable-nvdec --enable-cuda-nvcc --enable-cuvid --enable-cuda-llvm --enable-libnpp --nvccflags='-gencode arch=compute_86,code=sm_86' --arch=x86_64 --prefix=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace --disable-debug --disable-doc --disable-shared --enable-pthreads --enable-static --enable-small --enable-version3 --enable-ffnvcodec --cpu=16 --extra-cflags='-I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include -I/usr/local -I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/include/lilv-0 -DLIBXML_STATIC_FOR_DLL -DNOLIBTOOL -I/usr/local/cuda-12.1/targets/x86_64-linux/include -I/usr/local/cuda-12.1/include -I/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/usr/include -I/home/jman/tmp/ffmpeg/ffmpeg-build/packages/nv-codec-n12.0.16.0/include' --extra-ldexeflags= --extra-ldflags='-L/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib -L/usr/local/cuda-12.1/targets/x86_64-linux/lib -L/usr/local/cuda-12.1/lib64' --extra-libs='-ldl -lpthread -lm -lz' --pkgconfigdir=/home/jman/tmp/ffmpeg/ffmpeg-build/workspace/lib/pkgconfig --pkg-config-flags=--static
libavutil      58.  6.100 / 58.  6.100
libavcodec     60. 10.100 / 60. 10.100
libavformat    60.  5.100 / 60.  5.100
libavdevice    60.  2.100 / 60.  2.100
libavfilter     9.  5.100 /  9.  5.100
libswscale      7.  2.100 /  7.  2.100
libswresample   4. 11.100 /  4. 11.100
libpostproc    57.  2.100 / 57.  2.100
```

Other Projects Of Mine
------------

- [Pushover CLI Client](https://github.com/markus-perl/pushover-cli)
- [Gender API](https://gender-api.com): [Genderize A Name](https://gender-api.com)
- [Gender API Client PHP](https://github.com/markus-perl/gender-api-client)
- [Gender API Client NPM](https://github.com/markus-perl/gender-api-client-npm)
- [Genderize Names](https://www.youtube.com/watch?v=2SLIAguaygo)
- [Genderize API](https://gender-api.io)
