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
* `nvdec`: The Fraunhofer Versatile Video Decoder (VVdeC) is a fast H.266/VVC software decoder implementation.
  - All features of the VVC Main10 profile are supported by VVdeC.
* `nvenc`: The Fraunhofer Versatile Video Encoder (VVenC) is a fast and efficient H.266/VVC encoder implementation with the following main features:
  - Easy to use encoder implementation with five predefined quality/speed presets;
  - Perceptual optimization to improve subjective video quality, based on the XPSNR visual model;
  - Extensive frame-level and task-based parallelization with very good scaling;
  - Frame-level single-pass and two-pass rate control supporting variable bit-rate (VBR) encoding;
  - Expert mode encoder interface available, allowing fine-grained control of the encoding process.
* `ff-nvcodec-headers`: FFmpeg version of headers required to interface with Nvidias codec APIs.
* `aom`: Alliance for Open Media
* `fontconfig`: Font configuration and customization library
* `libass`: A portable subtitle renderer for the ASS/SSA (Advanced Substation Alpha/Substation Alpha) subtitle format. It is mostly compatible with VSFilter.
* `libkvazaar`: An open-source HEVC encoder licensed under 3-clause BSD
* `libfribidi`: The Free Implementation of the Unicode Bidirectional Algorithm.

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

## Requirements
  - All required packages will be made available to download by the user's choice.
    - The packages are required for a successful build.

### Tested on Ubuntu 22.04.2

Example Output
-------

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

Other Projects Of Mine
------------

- [Pushover CLI Client](https://github.com/markus-perl/pushover-cli)
- [Gender API](https://gender-api.com): [Genderize A Name](https://gender-api.com)
- [Gender API Client PHP](https://github.com/markus-perl/gender-api-client)
- [Gender API Client NPM](https://github.com/markus-perl/gender-api-client-npm)
- [Genderize Names](https://www.youtube.com/watch?v=2SLIAguaygo)
- [Genderize API](https://gender-api.io)
