# FFmpeg 8+ on Ubuntu 24.04 (custom CUDA/NVENC build) — Best‑practice user manual

*(Target system: 24 logical CPU cores + GeForce RTX 4090, FFmpeg 8.x branch)*

FFmpeg 8.0 “Huffman” is the current major line, with point releases like 8.0.1 (released 2025‑11‑20) on the 8.0 branch. ([FFmpeg][1])

This manual focuses on **practical, repeatable best practices** for **high-quality H.264 (x264) → H.265 (x265) Main10** encoding on Ubuntu 24.04, assuming your FFmpeg is **custom-compiled with NVIDIA acceleration enabled**.

---

## 1) Mental model: what “CUDA hardware acceleration” actually means in FFmpeg

On NVIDIA systems, FFmpeg acceleration usually involves three different things:

1. **NVDEC**: hardware decode (H.264/H.265/etc.)
2. **NVENC**: hardware encode (H.264/H.265/AV1 depending on GPU)
3. **CUDA/NPP filters**: GPU-based processing (scale, some colorspace ops, etc.)

If you do end-to-end GPU transcode (decode + encode), you want decoded frames to **stay on the GPU** to avoid PCIe copies. NVIDIA explicitly recommends using:

* `-hwaccel cuda -hwaccel_output_format cuda`

…so frames stay in GPU memory and NVENC can consume them directly. ([NVIDIA Developer][2])

If you do **CPU x265 encoding** (libx265), CUDA decode can still work, but you’ll be moving frames back to system memory for encoding—so it’s not always a net win unless decoding or filtering is the bottleneck.

---

## 2) Quick verification checklist (your build + your machine)

Run these once and save the output somewhere (so you can compare after driver/FFmpeg updates).

### Confirm FFmpeg 8+ and your configure flags

```bash
ffmpeg -version
ffmpeg -buildconf
```

### Confirm NVIDIA driver sees the 4090

```bash
nvidia-smi
```

### Confirm hardware acceleration modules exist

```bash
ffmpeg -hide_banner -hwaccels
ffmpeg -hide_banner -decoders | grep -E 'cuvid|nvdec' -i
ffmpeg -hide_banner -encoders | grep -E 'nvenc|libx265' -i
```

If `hevc_nvenc` is present, you can also dump its *exact* supported options (this matters across FFmpeg versions):

```bash
ffmpeg -hide_banner -h encoder=hevc_nvenc
```

A recent encoder-help dump shows `hevc_nvenc` supports:

* 10‑bit pixel format `p010le`
* profile `main10`
* presets `p1`…`p7` (where `p7` = “slowest/best quality”)
* tuning including `uhq` (Ultra High Quality)
* rate control including `vbr_hq`
* `-cq` quality target and `-rc-lookahead`, AQ toggles, etc. ([Gist][3])

### Build/driver gotchas (so you don’t waste hours)

NVIDIA’s own documentation notes:

* FFmpeg needs **nvcodec headers** for NVENC/NVDEC builds
* CUDA toolkit is required to **compile**, but not required to **run** the built binary
* you should ensure the installed driver meets the Video Codec SDK requirements ([NVIDIA Docs][4])

---

## 3) Choosing the “right” encoder for your goal (quality/size vs speed)

You asked for:

> “highest quality output … strong image and best space savings … without taking so long it is ridiculous.”

That combination almost always means:

### ✅ Best quality-per-bit (smallest file for given quality): **CPU `libx265`**

* Slower, but best compression efficiency.
* With 24 logical cores, **preset `slow` is a very sane sweet spot**.

x265’s own docs: slower presets test more encoding options and generally achieve **better compression efficiency** (or lower bitrate at the same CRF quality). ([x265.readthedocs.io][5])

### ✅ Fastest wall-clock: **GPU `hevc_nvenc`**

* Much faster, excellent throughput on a 4090.
* But at the *same visual quality*, it often needs **more bitrate** than libx265 (i.e., larger files). ([Stack Overflow][6])

**Practical takeaway:**
If “best space savings” really matters, your “best command line” should be **libx265 10‑bit**; keep NVENC as your “I need it done fast” option.

---

## 4) CRF + preset: the two knobs that matter most

### CRF (Constant Rate Factor)

CRF is the standard “constant quality” mode for x264/x265. Typical rules:

* Range: **0–51**
* Lower = better quality / bigger files
* Higher = more compression / smaller files
* Start at the default, then adjust after checking output ([slhck.info][7])

### Preset (speed vs compression efficiency)

x265 presets trade compute for compression efficiency; default is `medium`. Slower = smaller output at same CRF quality (usually). ([x265.readthedocs.io][5])

---

## 5) 10‑bit reality check (important)

You can output 10‑bit HEVC by using `yuv420p10le` and a Main10 profile. ([Super User][8])

But also note:

* x265’s internal “Main vs Main10” capability is **compile-time** (x265 has separate 8‑bit vs 10‑bit builds). ([x265.readthedocs.io][9])
* Your FFmpeg must be linked against a 10‑bit capable libx265 build (or a “multilib” setup) to truly do Main10 internally.

**How to confirm output is actually 10‑bit:**

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,profile,pix_fmt,bits_per_raw_sample \
  -of default=nw=1 output.mkv
```

You want to see:

* `profile=Main 10` (or similar)
* `pix_fmt=yuv420p10le` (CPU) or `p010le` (NVENC path)

---

## 6) The “best” command line for x264 → x265 Main10 (quality + size + sane runtime)

This is my recommended baseline for your hardware and goals:

### **Best overall (CPU libx265 Main10, balanced)**

```bash
ffmpeg -hide_banner -i "input.mp4" \
  -map 0 -map_metadata 0 -map_chapters 0 \
  -c:v libx265 -preset slow -crf 20 \
  -pix_fmt yuv420p10le -x265-params "profile=main10" \
  -c:a copy -c:s copy \
  "output.x265_main10_crf20_slow.mkv"
```

Why this is the best “default best”:

* **`-crf 20`**: typically high quality, strong image, still real savings (adjust later)
* **`-preset slow`**: great compression efficiency without going into “veryslow is painful” territory (especially on 24 threads) ([x265.readthedocs.io][5])
* **10-bit output** via `yuv420p10le` + Main10 profile ([Super User][8])
* **Keeps all streams**: video + all audio/subs/attachments/metadata via `-map 0` and copy modes (modify if you want to shrink audio)

### If you want MP4 instead of MKV (compatibility note)

MP4 sometimes needs the `hvc1` tag for Apple compatibility. Use:

```bash
ffmpeg -hide_banner -i "input.mp4" \
  -map 0 -map_metadata 0 -map_chapters 0 \
  -c:v libx265 -preset slow -crf 20 \
  -pix_fmt yuv420p10le -x265-params "profile=main10" \
  -tag:v hvc1 -movflags +faststart \
  -c:a copy \
  "output.x265_main10_crf20_slow.mp4"
```

(Subtitle copying into MP4 is limited depending on subtitle codec; MKV is more forgiving.)

---

## 7) How to tune that “best command” without guessing

### The only changes you usually need

* Want **better quality** (bigger files): lower CRF

  * Try `-crf 19`, then `-crf 18` if you’re still seeing artifacts.
* Want **smaller files** (more artifacts risk): raise CRF

  * Try `-crf 21` or `-crf 22`.
* Want **faster** without destroying compression: use `-preset medium`
* Want **smaller** without changing CRF: use `-preset slower` (costs time)

x265’s preset documentation explicitly describes this speed ↔ compression efficiency tradeoff. ([x265.readthedocs.io][5])
CRF’s “0–51, lower is better quality” behavior is also well documented. ([slhck.info][7])

### Do a short test encode (best practice)

Instead of committing to a 2‑hour encode, test a representative 30–90 seconds:

```bash
ffmpeg -ss 00:10:00 -t 60 -i "input.mp4" \
  -c:v libx265 -preset slow -crf 20 -pix_fmt yuv420p10le -x265-params "profile=main10" \
  -an "sample.mkv"
```

Then compare:

* dark gradients (banding)
* motion + textures (blocking / smearing)
* edges (ringing)

---

## 8) When (and how) to use the RTX 4090 for faster HEVC Main10

If you decide speed matters more than maximum compression efficiency, here’s a strong “quality-first NVENC” template.

### **Fast high-quality NVENC Main10 (end-to-end GPU)**

```bash
ffmpeg -hide_banner \
  -hwaccel cuda -hwaccel_output_format cuda \
  -i "input.mp4" \
  -map 0 -map_metadata 0 -map_chapters 0 \
  -c:v hevc_nvenc -profile:v main10 -pix_fmt p010le \
  -preset p7 -tune uhq \
  -rc vbr_hq -cq 19 -rc-lookahead 32 \
  -spatial_aq 1 -temporal_aq 1 -aq-strength 8 \
  -c:a copy -c:s copy \
  "output.nvenc_main10_cq19_p7.mkv"
```

Why these specific pieces:

* `-hwaccel cuda -hwaccel_output_format cuda` keeps frames on GPU to avoid needless GPU↔CPU transfers ([NVIDIA Developer][2])
* NVENC options shown here (`p7`, `uhq`, `vbr_hq`, `cq`, AQ toggles, lookahead) are supported by `hevc_nvenc` and appear in encoder help output. ([Gist][3])

**Important expectation:** NVENC is often faster, but **libx265 usually wins on file size at similar quality**. ([Stack Overflow][6])

---

## 9) Filters, scaling, and “don’t accidentally ruin quality”

### If you are resizing

If you scale video, you can do it on the GPU and keep frames on the GPU. NVIDIA shows `scale_npp` usage, and notes “super-sampling” is recommended for best downscaling quality. ([NVIDIA Developer][2])

Example (GPU scale + NVENC):

```bash
ffmpeg -hide_banner -hwaccel cuda -hwaccel_output_format cuda -i input.mp4 \
  -vf "scale_npp=1920:1080:interp_algo=super" \
  -c:v hevc_nvenc -preset p7 -tune uhq -rc vbr_hq -cq 19 \
  -c:a copy output_1080p.mkv
```

### If you’re not resizing or filtering

Don’t add filters “just because.” Every filter can:

* force format conversions
* change color range handling
* add extra compute / bandwidth

Keep it simple unless you have a reason.

---

## 10) Batch conversion best practices (Ubuntu-friendly)

### Safe bash loop (writes outputs next to inputs)

```bash
for f in *.mp4 *.mkv; do
  [ -f "$f" ] || continue
  out="${f%.*}.x265_main10_crf20_slow.mkv"
  ffmpeg -hide_banner -i "$f" \
    -map 0 -map_metadata 0 -map_chapters 0 \
    -c:v libx265 -preset slow -crf 20 \
    -pix_fmt yuv420p10le -x265-params "profile=main10" \
    -c:a copy -c:s copy \
    "$out"
done
```

### Logging + reproducibility

Add:

* `-report` (writes a full FFmpeg log in the current directory)
* or `-loglevel level+info` for more detail

---

## 11) Troubleshooting quick hits

### “`Unknown encoder 'hevc_nvenc'`”

Your FFmpeg wasn’t built with NVENC enabled (or runtime libs aren’t found).

### “`Cannot load libnvidia-encode.so.1`” / “No NVENC capable devices found”

Usually driver / library path mismatch. Confirm `nvidia-smi` works and your driver is properly installed.

### Output isn’t actually 10-bit

Use the `ffprobe` check above. If it’s not 10-bit:

* your libx265 may be 8-bit only (compile-time detail) ([x265.readthedocs.io][9])
* or you didn’t set `yuv420p10le` / Main10 profile correctly ([Super User][8])

---

## Final recommendation (the one command I’d start with)

If your priority is truly: **strong image + best space savings + not ridiculous runtime** on a 24-thread CPU:

```bash
ffmpeg -hide_banner -i "input.mp4" \
  -map 0 -map_metadata 0 -map_chapters 0 \
  -c:v libx265 -preset slow -crf 20 \
  -pix_fmt yuv420p10le -x265-params "profile=main10" \
  -c:a copy -c:s copy \
  "output.x265_main10_crf20_slow.mkv"
```

Then:

* if it’s bigger than you want → raise CRF to 21–22
* if you see artifacts → drop CRF to 19–18
* if it’s too slow → preset `medium` (keep CRF the same)

If you tell me your typical content (1080p vs 4K, film vs animation, grain/no grain, and whether it’s SDR or HDR), I can give you a more content-specific “best” variant—but the above is the best general-purpose starting point for your stated goals.

[1]: https://www.ffmpeg.org/download.html "
Download FFmpeg"
[2]: https://developer.nvidia.com/blog/nvidia-ffmpeg-transcoding-guide/ "NVIDIA FFmpeg Transcoding Guide | NVIDIA Technical Blog"
[3]: https://gist.github.com/nico-lab/c2d192cbb793dfd241c1eafeb52a21c3 "ffmpeg -h encoder=hevc_nvenc · GitHub"
[4]: https://docs.nvidia.com/video-technologies/video-codec-sdk/12.0/ffmpeg-with-nvidia-gpu/index.html "Using FFmpeg with NVIDIA GPU Hardware Acceleration - NVIDIA Docs"
[5]: https://x265.readthedocs.io/en/stable/presets.html "Preset Options — x265  documentation"
[6]: https://stackoverflow.com/questions/56556476/how-to-set-proper-bitrate-for-ffmpeg-with-hevc-nvenc?utm_source=chatgpt.com "How to set proper bitrate for ffmpeg with hevc_nvenc?"
[7]: https://slhck.info/video/2017/02/24/crf-guide.html "CRF Guide (Constant Rate Factor in x264, x265 and libvpx)"
[8]: https://superuser.com/questions/1380946/how-do-i-convert-10-bit-h-265-hevc-videos-to-h-264-without-quality-loss?utm_source=chatgpt.com "How do I convert 10-bit H.265 / HEVC videos to H.264 ..."
[9]: https://x265.readthedocs.io/en/master/api.html "Application Programming Interface — x265  documentation"
    
