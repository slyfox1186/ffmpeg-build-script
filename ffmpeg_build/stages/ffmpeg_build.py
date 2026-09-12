"""Configure, compile, install, and validate FFmpeg.

The install is staged into a `DESTDIR` tree and fully validated there before
`sudo make install` touches `/usr/local`, and the three programs already
installed are copied aside first so a failed promotion is recoverable.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.exec import base_environment
from ..runtime.paths import safe_remove_tree
from ..runtime.state import read_marker_version
from .hardware import HardwareDetection

_VERSION_LINE = re.compile(r"^(?P<tool>\w+) version n?(?P<version>[0-9]+(?:\.[0-9]+){1,3})")
_CODEC_ROW = re.compile(r"^ [A-Z.]{6} ")


class ConfigureOptions:
    """An ordered, first-wins list of FFmpeg configure options.

    Order matters: FFmpeg's own configure is order-sensitive, and the first
    occurrence of an option is the one that takes effect, so a later duplicate
    must be dropped rather than appended.
    """

    def __init__(self) -> None:
        self.options: list[str] = []
        self._seen: set[str] = set()

    def add(self, *options: str) -> None:
        for option in options:
            if option and option not in self._seen:
                self._seen.add(option)
                self.options.append(option)


def ffmpeg_installed_version(binary: Path = Path("/usr/local/bin/ffmpeg")) -> str | None:
    if not os.access(binary, os.X_OK):
        return None
    import subprocess

    try:
        completed = subprocess.run(
            [str(binary), "-hide_banner", "-version"],
            capture_output=True,
            text=True,
            check=False,
            env=base_environment(),
        )
    except OSError:
        return None
    match = _VERSION_LINE.match(completed.stdout.split("\n", 1)[0])
    return match.group("version") if match else None


class FFmpegStage:
    def __init__(self, context: BuildContext, hardware: HardwareDetection) -> None:
        self.context = context
        self.hardware = hardware
        self.logger = context.logger

    # -- configure-time feature selection --------------------------------

    def append_shader_options(self, detected: list[str], configure_help: str) -> None:
        """Select the Vulkan shader integration this FFmpeg release exposes.

        FFmpeg 9 replaced runtime libshaderc linking with build-time GLSL
        compilation, so the source release is inspected rather than guessed at
        from its version number.
        """
        context = self.context
        if "--glslc=" in configure_help:
            for compiler in ("glslangValidator", "glslang", "glslc"):
                compiler_path = context.runner.which(compiler)
                if compiler_path is None:
                    continue
                self._require(detected, f"--glslc={compiler_path}")
                # spirv_compiler is internal and is not exported in config.mak.
                # scale_vulkan depends on it, so this checks the usable
                # capability instead.
                context.required_symbols["CONFIG_SCALE_VULKAN_FILTER"] = (
                    "Vulkan scale filter (build-time shader compilation)"
                )
                self.logger.info(
                    f"Using '{compiler_path}' to compile Vulkan shaders at build time."
                )
                return
            raise BuildError(
                "Vulkan requires a build-time SPIR-V compiler, but neither glslangValidator, "
                "glslang nor glslc is available. Install the host 'glslang-tools' package and retry."
            )
        if "--enable-libshaderc" in configure_help:
            if context.package_enabled("libshaderc") and context.library_exists(
                "shaderc >= 2019.1"
            ):
                self._require(detected, "--enable-libshaderc")
            return
        if context.package_enabled("libshaderc"):
            raise BuildError(
                "The selected FFmpeg source exposes neither '--glslc' nor "
                "'--enable-libshaderc'; its Vulkan shader integration needs review."
            )

    def _require(self, target: list[str], *options: str) -> None:
        target.extend(options)
        self.context.record_required_config_symbols(options)

    def validate_required_features(self, config_file: Path) -> None:
        """Fail when configure silently dropped a requested feature."""
        if not config_file.is_file():
            raise BuildError(f"FFmpeg configuration file is missing: '{config_file}'.")
        text = config_file.read_text(encoding="utf-8", errors="replace")
        present = {line for line in text.splitlines()}
        missing = [
            f"'{option}' ('{symbol}')"
            for symbol, option in self.context.required_symbols.items()
            if f"{symbol}=yes" not in present
        ]
        if missing:
            raise BuildError(
                f"FFmpeg configure did not retain requested feature(s): {' '.join(missing)}"
            )

    # -- installation validation -----------------------------------------

    def validate_installation(
        self,
        expected_version: str,
        require_ffplay: bool,
        install_prefix: Path = Path("/usr/local"),
        display_results: bool = True,
    ) -> None:
        import subprocess

        context = self.context
        binaries = ["ffmpeg", "ffprobe"] + (["ffplay"] if require_ffplay else [])
        for binary in binaries:
            binary_path = install_prefix / "bin" / binary
            if not os.access(binary_path, os.X_OK):
                raise BuildError(f"FFmpeg installation is incomplete: '{binary_path}' is missing.")

        version_lines: list[str] = []
        for binary in binaries:
            binary_path = install_prefix / "bin" / binary
            command_display = f"{binary_path} -hide_banner -version"
            completed = subprocess.run(
                [str(binary_path), "-hide_banner", "-version"],
                capture_output=True,
                text=True,
                check=False,
                env=base_environment(),
            )
            output = (completed.stdout + completed.stderr).rstrip("\n")
            if context.log_file.is_file():
                with context.log_file.open("a", encoding="utf-8") as handle:
                    handle.write(f"$ {command_display}\n")
                    if output:
                        handle.write(f"{output}\n")
            if completed.returncode != 0:
                if output:
                    print(f"\n{output}")
                raise BuildError(
                    f"'{binary}' version check failed with exit code {completed.returncode}: "
                    f"'{command_display}'."
                )
            version_line = output.split("\n", 1)[0]
            if not version_line:
                raise BuildError(
                    f"'{binary}' version check returned no output: '{command_display}'."
                )
            match = _VERSION_LINE.match(version_line)
            reported = match.group("version") if match and match.group("tool") == binary else None
            if reported != expected_version:
                raise BuildError(
                    f"'{binary}' reported version '{reported or 'unknown'}', "
                    f"expected '{expected_version}'."
                )
            version_lines.append(version_line)

        for capability in ("encoders", "decoders"):
            completed = subprocess.run(
                [str(install_prefix / "bin/ffmpeg"), "-hide_banner", f"-{capability}"],
                capture_output=True,
                text=True,
                check=False,
                env=base_environment(),
            )
            if completed.returncode != 0 or not any(
                _CODEC_ROW.match(line) for line in completed.stdout.splitlines()
            ):
                raise BuildError(f"Installed FFmpeg did not report any {capability}.")

        if display_results:
            palette = self.logger.out_palette
            print(
                f"\n{palette.green}FFmpeg installation verified{palette.nc} ({install_prefix}/bin):"
            )
            for version_line in version_lines:
                print(f"  {version_line}")

    def backup_installed_programs(self, backup_dir: Path, install_prefix: Path) -> None:
        """Copy the three programs aside before `/usr/local` is touched.

        `sudo make install` overwrites them in place, so a failure part-way
        through — ENOSPC being the classic one — destroys a working
        installation. Only the programs are saved: restoring a working ffmpeg
        is the property that matters, and a half-written library tree is
        repaired by re-running the build.
        """
        for program in ("ffmpeg", "ffprobe", "ffplay"):
            source = install_prefix / "bin" / program
            if source.is_file() or source.is_symlink():
                self.context.execute(["cp", "-a", "--", str(source), str(backup_dir / program)])

    def restore_installed_programs(self, backup_dir: Path, install_prefix: Path) -> bool:
        if not backup_dir.is_dir():
            return False
        restored = True
        for program in ("ffmpeg", "ffprobe", "ffplay"):
            backup_path = backup_dir / program
            target = install_prefix / "bin" / program
            if backup_path.exists() or backup_path.is_symlink():
                command = [
                    "sudo",
                    "cp",
                    "-a",
                    "--remove-destination",
                    "--",
                    str(backup_path),
                    str(target),
                ]
            else:
                command = ["sudo", "rm", "-f", "--", str(target)]
            if self.context.runner.run_logged(command) == 0:
                self.logger.warn(f"Restored the previous state of '{target}'.")
            else:
                restored = False
                self.logger.warn(
                    f"Could not restore '{target}'; recovery files are kept at '{backup_dir}'."
                )
        return restored

    def promote_installation(
        self,
        build_directory: Path,
        staging_root: Path,
        ffmpeg_version: str,
        ffplay_enabled: bool,
        install_prefix: Path = Path("/usr/local"),
    ) -> None:
        """Keep a recoverable backup through promotion and installed validation."""
        backup_dir = staging_root / "previous-install"
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_installed_programs(backup_dir, install_prefix)
        # Once promotion starts, automatic abort cleanup must not erase the only
        # recovery copy if either installation or restoration fails.
        self.context.unregister_temporary_path(staging_root)
        try:
            status = self.context.runner.run_logged(
                ["sudo", "make", "install"], cwd=build_directory
            )
            if status != 0:
                raise BuildError(
                    f"Installing FFmpeg into '{install_prefix}' failed with exit code {status}."
                )
            self.validate_installation(ffmpeg_version, ffplay_enabled, install_prefix)
        except BaseException as error:
            restored = self.restore_installed_programs(backup_dir, install_prefix)
            outcome = (
                "The previously installed programs were restored."
                if restored
                else "Restoration was incomplete."
            )
            detail = f"{outcome} Recovery files remain at '{staging_root}'."
            if isinstance(error, BuildError):
                raise BuildError(f"{error} {detail}") from error
            self.logger.warn(detail)
            raise

    # -- the stage -------------------------------------------------------

    def run(self) -> None:
        context = self.context
        print()
        self.logger.banner("Building FFmpeg")

        if not context.package_enabled("ffmpeg"):
            print()
            self.logger.info("FFmpeg is disabled by config; dependency build is complete.")
            return

        ffmpeg_version = context.fetch_version_if_enabled("ffmpeg", context.versions.ffmpeg)
        if ffmpeg_version is None:
            raise BuildError("Unable to determine the latest stable FFmpeg release.")
        if not re.match(r"^[0-9]+(\.[0-9]+){1,3}$", ffmpeg_version):
            raise BuildError(f"Invalid FFmpeg release version '{ffmpeg_version}'.")

        installed_version = ffmpeg_installed_version()
        if installed_version:
            self.logger.info(f"Installed FFmpeg version: '{installed_version}'.")
        self.logger.info(f"Selected FFmpeg release: '{ffmpeg_version}'.")

        marker_file = context.marker_path("ffmpeg")
        ffplay_enabled = context.package_enabled("sdl2") and context.library_exists("sdl2")
        recorded_version = read_marker_version(marker_file)
        programs_incomplete = (
            installed_version != ffmpeg_version
            or not os.access("/usr/local/bin/ffprobe", os.X_OK)
            or (ffplay_enabled and not os.access("/usr/local/bin/ffplay", os.X_OK))
        )
        if recorded_version == f"n{ffmpeg_version}" and programs_incomplete:
            self.logger.warn(
                "FFmpeg's build marker exists, but its required installed programs are "
                "incomplete; rebuilding."
            )
            context.execute(["rm", "-f", "--", str(marker_file)])

        if context.build("ffmpeg", f"n{ffmpeg_version}"):
            self._configure_build_install(ffmpeg_version, ffplay_enabled)
        else:
            self.validate_installation(ffmpeg_version, ffplay_enabled)

    def _configure_build_install(self, ffmpeg_version: str, ffplay_enabled: bool) -> None:
        context = self.context
        workspace = context.workspace
        source_directory = context.download(
            f"https://ffmpeg.org/releases/ffmpeg-{ffmpeg_version}.tar.xz",
            f"ffmpeg-{ffmpeg_version}.tar.xz",
        )
        configure_help = context.runner.capture(
            [str(source_directory / "configure"), "--help"], cwd=source_directory
        )
        if configure_help.returncode != 0:
            raise BuildError("Unable to inspect the selected FFmpeg release's configure options.")
        build_directory = source_directory / "build"
        build_directory.mkdir(parents=True, exist_ok=True)

        extra_cflags = f"-I{workspace}/include {context.env.get('CPPFLAGS', '')} {context.env.get('CFLAGS', '')}"
        extra_cxxflags = f"-I{workspace}/include {context.env.get('CPPFLAGS', '')} {context.env.get('CXXFLAGS', '')}"
        extra_ldflags = f"-L{workspace}/lib64 -L{workspace}/lib {context.env.get('LDFLAGS', '')}"
        extra_libs = "-ldl -lpthread -lm"

        base: list[str] = [
            "--prefix=/usr/local",
            "--arch=x86_64",
            "--cpu=native",
            f"--cc={context.env.get('CC', 'gcc')}",
            f"--cxx={context.env.get('CXX', 'g++')}",
            "--pkg-config=pkgconf",
            "--pkg-config-flags=--static",
            "--disable-autodetect",
            "--disable-debug",
            "--disable-doc",
            "--disable-shared",
            "--enable-static",
            "--enable-pic",
            "--enable-pthreads",
            "--enable-ffmpeg",
            "--enable-ffprobe",
            "--enable-version3",
            "--enable-bzlib",
            "--enable-lzma",
        ]
        detected: list[str] = []

        if ffplay_enabled:
            self._require(base, "--enable-sdl2")
            base.append("--enable-ffplay")
        else:
            base += ["--disable-ffplay", "--disable-sdl2"]
            self.logger.warn("SDL2 is unavailable or disabled; 'ffplay' will not be built.")

        # Detection runs first because the CUDA path contributes include and
        # library directories that have to be inside the --extra-* flags below.
        cuda_cflags, cuda_ldflags = self._detect_options(detected, configure_help.stdout)
        extra_cflags += cuda_cflags
        extra_ldflags += cuda_ldflags

        base += [
            f"--extra-cflags={extra_cflags.strip()}",
            f"--extra-cxxflags={extra_cxxflags.strip()}",
            f"--extra-ldflags={extra_ldflags.strip()}",
            f"--extra-libs={extra_libs}",
        ]

        final = ConfigureOptions()
        final.add(*base, *detected, *context.configure_options)

        context.execute([str(source_directory / "configure"), *final.options], cwd=build_directory)

        config_mak = build_directory / "ffbuild/config.mak"
        if not config_mak.is_file():
            raise BuildError("FFmpeg configure did not produce 'ffbuild/config.mak'.")
        config_text = set(config_mak.read_text(encoding="utf-8", errors="replace").splitlines())
        if "CONFIG_FFMPEG=yes" not in config_text:
            raise BuildError("FFmpeg configure disabled the 'ffmpeg' program.")
        if "CONFIG_FFPROBE=yes" not in config_text:
            raise BuildError("FFmpeg configure disabled 'ffprobe'.")
        if ffplay_enabled and "CONFIG_FFPLAY=yes" not in config_text:
            raise BuildError("FFmpeg configure disabled 'ffplay' despite SDL2 being selected.")
        self.validate_required_features(config_mak)

        context.make(build_directory)
        staging_root = Path(
            tempfile.mkdtemp(prefix=f".ffmpeg-install-{ffmpeg_version}.", dir=context.packages)
        )
        context.register_temporary_path(staging_root)
        staged_prefix = staging_root / "usr/local"
        context.execute(["make", f"DESTDIR={staging_root}", "install"], cwd=build_directory)
        self.validate_installation(ffmpeg_version, ffplay_enabled, staged_prefix, False)

        # Only mutate /usr/local after the complete staged install has passed
        # its binary, version and capability checks, and keep the previous
        # programs recoverable until the installed result has passed them too.
        self.promote_installation(build_directory, staging_root, ffmpeg_version, ffplay_enabled)
        safe_remove_tree(staging_root, context.packages)
        context.unregister_temporary_path(staging_root)
        context.build_done("ffmpeg", f"n{ffmpeg_version}")

    def _detect_options(self, detected: list[str], configure_help: str) -> tuple[str, str]:
        """Gate every optional integration on both selection and a real probe.

        FFmpeg's own configure performs the authoritative compile/link check
        afterwards; these probes only decide whether to ask for the feature at
        all, so that a missing system library is a skipped option rather than a
        configure abort.

        Returns the CUDA include and library additions for the `--extra-*`
        flags, which are empty unless CUDA compilation was enabled.
        """
        context = self.context
        enabled = context.package_enabled

        if enabled("libiconv") and context.header_exists("iconv.h"):
            self._require(detected, "--enable-iconv")
        if enabled("zlib") and context.library_exists("zlib"):
            self._require(detected, "--enable-zlib")

        # FFmpeg's configure accepts "aribb24 > 1.0.3" outright, otherwise
        # requires --enable-gpl, otherwise dies. Every supported release ships
        # exactly 1.0.3, so this needs the licence gate as well as the probe:
        # asking for it on user selection alone kills configure on all of them.
        if enabled("libaribb24"):
            if context.library_exists("aribb24 > 1.0.3") or (
                context.nonfree_and_gpl and context.library_exists("aribb24")
            ):
                self._require(detected, "--enable-libaribb24")
            elif context.library_exists("aribb24"):
                self.logger.warn(
                    "'libaribb24' is only usable with '--enable-gpl-and-non-free' at the "
                    "version this release ships; omitting it."
                )

        pkgconf_gated = (
            ("libbluray", ("libbluray",), "--enable-libbluray"),
            ("libdav1d", ("dav1d",), "--enable-libdav1d"),
            ("libvpl", ("vpl",), "--enable-libvpl"),
            ("libspeex", ("speex",), "--enable-libspeex"),
            ("libssh", ("libssh",), "--enable-libssh"),
            ("chromaprint", ("libchromaprint",), "--enable-chromaprint"),
            ("libjxl", ("libjxl", "libjxl_threads"), "--enable-libjxl"),
            ("libtesseract", ("tesseract",), "--enable-libtesseract"),
            ("libzvbi", ("zvbi-0.2",), "--enable-libzvbi"),
            ("libmodplug", ("libmodplug",), "--enable-libmodplug"),
            ("libgme", ("libgme",), "--enable-libgme"),
            ("libshine", ("shine",), "--enable-libshine"),
            ("libcaca", ("caca",), "--enable-libcaca"),
            ("libbs2b", ("libbs2b",), "--enable-libbs2b"),
            ("libjack", ("jack",), "--enable-libjack"),
            ("libv4l2", ("libv4l2",), "--enable-libv4l2"),
            ("xlib", (), ""),
            ("libvpx", ("vpx",), "--enable-libvpx"),
            ("libopenh264", ("openh264 >= 1.3.0",), "--enable-libopenh264"),
            ("libopenmpt", ("libopenmpt >= 0.2.6557",), "--enable-libopenmpt"),
            ("librtmp", ("librtmp",), "--enable-librtmp"),
            ("librsvg", ("librsvg-2.0",), "--enable-librsvg"),
            ("alsa", ("alsa",), "--enable-alsa"),
            ("libpulse", ("libpulse",), "--enable-libpulse"),
            ("sndio", ("sndio",), "--enable-sndio"),
            ("vaapi", ("libva",), "--enable-vaapi"),
            ("vdpau", ("vdpau",), "--enable-vdpau"),
            ("libdrm", ("libdrm",), "--enable-libdrm"),
        )
        for key, modules, option in pkgconf_gated:
            if not enabled(key):
                continue
            if key == "xlib":
                if context.library_exists("x11", "xext", "xv"):
                    self._require(detected, "--enable-xlib")
                if context.library_exists("xcb", "xcb-shm", "xcb-shape", "xcb-xfixes"):
                    self._require(
                        detected,
                        "--enable-libxcb",
                        "--enable-libxcb-shm",
                        "--enable-libxcb-shape",
                        "--enable-libxcb-xfixes",
                    )
            elif context.library_exists(*modules):
                self._require(detected, option)

        header_gated = (
            ("libsnappy", ("snappy-c.h",), "--enable-libsnappy"),
            ("libtwolame", ("twolame.h",), "--enable-libtwolame"),
            ("libvo-amrwbenc", ("vo-amrwbenc/enc_if.h",), "--enable-libvo-amrwbenc"),
            ("libgsm", ("gsm.h", "gsm/gsm.h"), "--enable-libgsm"),
            ("ladspa", ("ladspa.h",), "--enable-ladspa"),
            ("opengl", ("GL/glx.h",), "--enable-opengl"),
            ("libflite", ("flite/flite.h",), "--enable-libflite"),
        )
        for key, headers, option in header_gated:
            if enabled(key) and any(context.header_exists(header) for header in headers):
                self._require(detected, option)

        if context.nonfree_and_gpl:
            if enabled("frei0r") and context.header_exists("frei0r.h"):
                self._require(detected, "--enable-frei0r")
            if enabled("libsmbclient") and context.library_exists("smbclient"):
                self._require(detected, "--enable-libsmbclient")
            if enabled("libcdio") and context.library_exists("libcdio_paranoia"):
                self._require(detected, "--enable-libcdio")
            # FFmpeg's dvdvideo demuxer needs both, and enabling either alone
            # fails configure. Both are in EXTERNAL_LIBRARY_GPL_LIST, so this
            # stays inside the licence gate.
            if (
                enabled("libdvdread")
                and enabled("libdvdnav")
                and context.library_exists("dvdread")
                and context.library_exists("dvdnav")
            ):
                self._require(detected, "--enable-libdvdread", "--enable-libdvdnav")

        if enabled("vulkan") and self._vulkan_headers_recent():
            self._require(detected, "--enable-vulkan")
            self.append_shader_options(detected, configure_help)
            if (
                enabled("libplacebo")
                and context.library_exists("libplacebo >= 5.229.0")
                and self._libplacebo_has_alpha_none()
            ):
                self._require(detected, "--enable-libplacebo")

        return self._detect_nvidia_options(detected)

    def _vulkan_headers_recent(self) -> bool:
        """True when the workspace headers meet FFmpeg's floor for Vulkan.

        This is the exact condition FFmpeg's own configure uses; most distros
        ship older headers, which is why the workspace gets its own.
        """
        return self.context.compile_probe(
            "#include <vulkan/vulkan.h>\n"
            "#if !(defined(VK_VERSION_1_4) || "
            "(defined(VK_VERSION_1_3) && VK_HEADER_VERSION >= 277))\n"
            "#error vulkan headers too old\n"
            "#endif\n",
            [f"-I{self.context.workspace}/include"],
        )

    def _libplacebo_has_alpha_none(self) -> bool:
        """Feature-test PL_ALPHA_NONE rather than trusting a version number.

        FFmpeg's configure requires libplacebo >= 5.229.0, which is too low:
        distro libplacebo 6.x passes it and then fails to compile, because the
        enum arrived in 7.x.
        """
        completed = self.context.runner.capture(["pkgconf", "--cflags", "libplacebo"])
        if completed.returncode != 0:
            return False
        return self.context.compile_probe(
            "#include <libplacebo/colorspace.h>\nint chk(void){ return (int) PL_ALPHA_NONE; }\n",
            completed.stdout.split(),
        )

    def _detect_nvidia_options(self, detected: list[str]) -> tuple[str, str]:
        """NVENC/NVDEC need ffnvcodec headers, not nvcc.

        CUDA-compiled filters are a separate capability, enabled only when a
        validated toolkit and architecture flags are both available.
        """
        context = self.context
        if not (
            context.nvidia_gpu_present
            and context.nonfree_and_gpl
            and context.package_enabled("nv-codec-headers")
        ):
            return "", ""
        if not context.library_exists("ffnvcodec"):
            self.logger.warn(
                "'nv-codec-headers' are unavailable; omitting NVIDIA codec interfaces."
            )
            return "", ""

        self._require(
            detected,
            "--enable-cuda",
            "--enable-cuvid",
            "--enable-ffnvcodec",
            "--enable-nvdec",
            "--enable-nvenc",
        )
        cuda_root = context.cuda_root
        if (
            cuda_root is None
            or not os.access(cuda_root / "bin/nvcc", os.X_OK)
            or not context.nvidia_arch_flags
        ):
            self.logger.info(
                "CUDA toolkit compilation is unavailable; retaining NVENC/NVDEC support "
                "from 'nv-codec-headers'."
            )
            return "", ""

        self._require(detected, "--enable-cuda-nvcc")
        detected += [
            f"--nvcc={cuda_root}/bin/nvcc",
            f"--nvccflags=-O2 {context.nvidia_arch_flags}",
        ]
        cuda_version = self.hardware.local_cuda_version(cuda_root) or ""
        cuda_major = cuda_version.split(".", 1)[0]
        if cuda_major.isdigit() and int(cuda_major) < 13:
            if (cuda_root / "lib64/libnppc.so").exists() or (
                cuda_root / "lib64/libnppc_static.a"
            ).exists():
                self._require(detected, "--enable-libnpp")
        elif cuda_major.isdigit() and int(cuda_major) >= 13:
            self.logger.info(
                "Skipping deprecated 'libnpp' integration because FFmpeg does not support it "
                "with CUDA 13+."
            )
        return f" -I{cuda_root}/include", f" -L{cuda_root}/lib64"


def report_success(context: BuildContext) -> None:
    """Print the closing summary from the installed binary's own capabilities."""
    import subprocess

    ffmpeg_path = Path("/usr/local/bin/ffmpeg")
    if not os.access(ffmpeg_path, os.X_OK):
        raise BuildError(f"The build completed, but '{ffmpeg_path}' is missing or not executable.")

    def ask(*arguments: str) -> str:
        try:
            return subprocess.run(
                [str(ffmpeg_path), *arguments],
                capture_output=True,
                text=True,
                check=False,
                env=base_environment(),
            ).stdout
        except OSError:
            return ""

    version_line = ask("-version").split("\n", 1)[0] or "unknown"
    counts = {}
    for capability in ("encoders", "decoders"):
        counts[capability] = sum(
            1
            for line in ask("-hide_banner", f"-{capability}").splitlines()
            if _CODEC_ROW.match(line)
        )
    filter_row = re.compile(r"^ [.A-Z|]{3} ")
    counts["filters"] = sum(
        1 for line in ask("-hide_banner", "-filters").splitlines() if filter_row.match(line)
    )
    accelerators = [
        line.strip() for line in ask("-hide_banner", "-hwaccels").splitlines()[1:] if line.strip()
    ]
    installed_tools = [
        tool
        for tool in ("ffmpeg", "ffprobe", "ffplay")
        if os.access(f"/usr/local/bin/{tool}", os.X_OK)
    ]

    from ..runtime.logging import format_duration

    palette = context.logger.out_palette
    green, cyan, nc = palette.green, palette.cyan, palette.nc
    print()
    context.logger.banner("FFmpeg build completed successfully")
    print(f"\n{green}✓ Version:{nc} {cyan}{version_line}{nc}")
    print(f"{green}✓ Installation:{nc} {cyan}/usr/local/bin{nc}")
    print(f"{green}✓ Installed tools:{nc} {cyan}{' '.join(installed_tools) or 'none'}{nc}")
    print(
        f"{green}✓ Encoders / decoders / filters:{nc} "
        f"{cyan}{counts['encoders']} / {counts['decoders']} / {counts['filters']}{nc}"
    )
    print(
        f"{green}✓ Reported hardware accelerators:{nc} "
        f"{cyan}{', '.join(accelerators) or 'none reported'}{nc}"
    )
    print(
        f"{green}✓ Packages:{nc} {cyan}{context.packages_built}{nc} built, "
        f"{cyan}{context.packages_already_built}{nc} already current, "
        f"{cyan}{context.packages_disabled}{nc} disabled"
    )
    print(f"{green}✓ Total time:{nc} {cyan}{format_duration(context.logger.elapsed_seconds)}{nc}")
    print(f"{green}✓ Build log:{nc} {cyan}{context.log_file}{nc}\n")
