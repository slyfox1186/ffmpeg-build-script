"""GPU discovery and optional CUDA toolkit installation.

This stage never installs or replaces an NVIDIA display driver, and it never
guesses CUDA architectures: the targets come from `nvcc --list-gpu-code` and
`nvidia-smi`. CUDA itself is added from NVIDIA's signed network repository and
only after an explicit opt-in.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.paths import safe_remove_tree
from .system_setup import APT_SCRIPT_OPTIONS, SystemSetup

# FFmpeg's own `check_nvcc` source; the probe below must fail exactly when
# FFmpeg's configure would.
_NVCC_PROBE_SOURCE = 'extern "C" {\n    __global__ void hello(unsigned char *data) {}\n}\n'
_NVCC_GCC_LIMIT = re.compile(r"gcc versions later than ([0-9]+) are not supported")
# No supported CUDA release accepts a host GCC older than 7.
_OLDEST_NVCC_GCC = 7

_CUDA_REPOSITORIES = {
    ("Ubuntu", "22.04"): "ubuntu2204",
    ("Ubuntu", "24.04"): "ubuntu2404",
    ("Ubuntu", "26.04"): "ubuntu2604",
    ("Debian", "12"): "debian12",
    ("Debian", "13"): "debian13",
}


class HardwareDetection:
    def __init__(self, context: BuildContext, setup: SystemSetup) -> None:
        self.context = context
        self.setup = setup
        self.logger = context.logger
        self.runner = context.runner
        self.available_architectures: list[int] = []

    # -- discovery -------------------------------------------------------

    def _gpu_controller_lines(self) -> str:
        if self.runner.which("lspci") is None:
            return ""
        completed = self.runner.capture(["lspci", "-nn"])
        if completed.returncode != 0:
            return ""
        pattern = re.compile(
            r"vga compatible controller|3d controller|display controller", re.IGNORECASE
        )
        return "\n".join(line for line in completed.stdout.splitlines() if pattern.search(line))

    def detect_gpu_vendors(self) -> None:
        context = self.context
        controllers = self._gpu_controller_lines()
        nvidia_smi = self.runner.which("nvidia-smi")
        if nvidia_smi is None and os.access("/usr/lib/wsl/lib/nvidia-smi", os.X_OK):
            nvidia_smi = "/usr/lib/wsl/lib/nvidia-smi"
            context.path_prepend("/usr/lib/wsl/lib")

        context.nvidia_gpu_present = False
        if nvidia_smi is not None and self.runner.probe(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"]
        ):
            context.nvidia_gpu_present = True
        elif re.search("nvidia", controllers, re.IGNORECASE):
            context.nvidia_gpu_present = True

        context.amd_gpu_present = bool(
            re.search(r"amd/ati|advanced micro devices|radeon", controllers, re.IGNORECASE)
        )
        context.intel_gpu_present = bool(re.search("intel", controllers, re.IGNORECASE))
        context.has_vulkan_gpu = (
            context.nvidia_gpu_present or context.amd_gpu_present or context.intel_gpu_present
        )

    # -- CUDA ------------------------------------------------------------

    def find_cuda_root(self) -> Path | None:
        nvcc_path = self.runner.which("nvcc")
        if nvcc_path is not None:
            resolved = Path(nvcc_path).resolve()
            candidate = resolved.parent.parent
            if os.access(candidate / "bin/nvcc", os.X_OK):
                return candidate
        for candidate in (Path("/usr/local/cuda"), Path("/opt/cuda")):
            if os.access(candidate / "bin/nvcc", os.X_OK):
                return candidate
        return None

    def local_cuda_version(self, cuda_root: Path) -> str | None:
        if not os.access(cuda_root / "bin/nvcc", os.X_OK):
            return None
        completed = self.runner.capture([str(cuda_root / "bin/nvcc"), "--version"])
        match = re.search(r"release ([0-9]+(?:\.[0-9]+){1,2})", completed.stdout)
        return match.group(1) if match else None

    def cuda_repository_name(self) -> str | None:
        context = self.context
        if context.variable_os == "WSL2":
            return "wsl-ubuntu"
        return _CUDA_REPOSITORIES.get((context.operating_system, context.release_version))

    def install_cuda_toolkit(self) -> None:
        context = self.context
        repository = self.cuda_repository_name()
        if repository is None:
            raise BuildError(
                "No supported NVIDIA CUDA repository mapping exists for "
                f"'{context.operating_system} {context.release_version}'."
            )
        if repository == "wsl-ubuntu" and context.operating_system == "Debian":
            # NVIDIA publishes exactly one WSL2 CUDA repository; its packages
            # are driver-free and install on Debian userspaces as well.
            self.logger.info(
                "Using NVIDIA's 'wsl-ubuntu' repository for this Debian WSL2 userspace."
            )

        repository_url = (
            f"https://developer.download.nvidia.com/compute/cuda/repos/{repository}/x86_64/"
        )
        keyring_version = context.resolver.scrape_highest(
            repository_url, r"cuda-keyring_([0-9]+(?:\.[0-9]+)+-[0-9]+)_all\.deb"
        )
        if keyring_version is None:
            raise BuildError("Unable to discover NVIDIA's current CUDA repository keyring.")

        # Staged inside the package cache, not /tmp, so the removal below gets a
        # real containment boundary. Deriving the allowed root from the
        # temporary directory itself would make that check true by construction.
        temp_directory = Path(tempfile.mkdtemp(prefix=".cuda-keyring.", dir=context.packages))
        context.register_temporary_path(temp_directory)
        keyring_file = temp_directory / "cuda-keyring.deb"
        keyring_url = f"{repository_url}cuda-keyring_{keyring_version}_all.deb"

        self.logger.info(f"Downloading NVIDIA's CUDA repository keyring for '{repository}'...")
        exit_code = self.runner.run_logged(
            [
                "curl",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--tlsv1.2",
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--retry",
                "3",
                "--retry-all-errors",
                "--connect-timeout",
                str(context.download_settings.connect_timeout),
                "--max-time",
                "120",
                "--output",
                str(keyring_file),
                keyring_url,
            ]
        )
        if exit_code != 0:
            safe_remove_tree(temp_directory, context.packages)
            context.unregister_temporary_path(temp_directory)
            raise BuildError("Unable to download NVIDIA's CUDA repository keyring.")

        context.execute(["sudo", "-n", "dpkg", "-i", str(keyring_file)])
        safe_remove_tree(temp_directory, context.packages)
        context.unregister_temporary_path(temp_directory)
        self.setup.apt_index_updated = False
        self.setup.apt_update_once()
        context.execute(
            [
                "sudo",
                "-n",
                "env",
                "DEBIAN_FRONTEND=noninteractive",
                "apt",
                *APT_SCRIPT_OPTIONS,
                "install",
                "--assume-yes",
                "--no-install-recommends",
                "cuda-toolkit",
            ]
        )
        self.setup.source_path()

    def read_cuda_architectures(self, cuda_root: Path) -> list[int]:
        completed = self.runner.capture([str(cuda_root / "bin/nvcc"), "--list-gpu-code"])
        found = {int(value) for value in re.findall(r"sm_([0-9]+)", completed.stdout)}
        return sorted(found)

    def read_installed_gpu_architectures(self) -> list[int]:
        if self.runner.which("nvidia-smi") is None:
            return []
        completed = self.runner.capture(
            ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"]
        )
        architectures: list[int] = []
        for line in completed.stdout.splitlines():
            capability = line.strip()
            if re.match(r"^[0-9]+\.[0-9]+$", capability):
                value = int(capability.replace(".", ""))
                if value not in architectures:
                    architectures.append(value)
        return architectures

    def configure_nvidia_architecture(self) -> bool:
        context = self.context
        if context.nvidia_arch_flags:
            return True
        cuda_root = context.cuda_root or self.find_cuda_root()
        if cuda_root is None:
            return False
        context.cuda_root = cuda_root

        self.available_architectures = self.read_cuda_architectures(cuda_root)
        if not self.available_architectures:
            raise BuildError("'nvcc' did not report any supported GPU code targets.")

        mode = os.environ.get("CUDA_ARCH_MODE", "native")
        if mode == "native":
            selected = self.read_installed_gpu_architectures()
            if not selected:
                self.logger.warn("'nvidia-smi' could not report GPU compute capabilities.")
                return False
        elif mode == "all":
            selected = list(self.available_architectures)
        elif mode == "custom":
            raw = os.environ.get("CUDA_ARCHITECTURES", "").replace(",", " ").split()
            if not raw:
                raise BuildError(
                    "'CUDA_ARCH_MODE=custom' requires 'CUDA_ARCHITECTURES' (for example: '86 89')."
                )
            selected = [int(value) for value in raw]
        else:
            raise BuildError(
                f"Invalid 'CUDA_ARCH_MODE' value '{mode}'; expected 'native', 'all', or 'custom'."
            )

        available_display = " ".join(str(value) for value in self.available_architectures)
        seen: set[int] = set()
        for architecture in selected:
            if architecture in seen:
                continue
            seen.add(architecture)
            if architecture not in self.available_architectures:
                if mode == "native":
                    self.logger.warn(
                        f"CUDA toolkit does not support this GPU's 'sm_{architecture}' target "
                        f"(available: '{available_display}')."
                    )
                    return False
                raise BuildError(
                    f"CUDA toolkit does not support 'sm_{architecture}' "
                    f"(available: '{available_display}')."
                )
        if not seen:
            return False
        # FFmpeg compiles its CUDA filters with `nvcc -ptx`, which rejects more
        # than one target, and the driver JIT-compiles that PTX for the GPU at
        # load time. PTX runs only on its own or a newer architecture, so the
        # lowest selected target is the one that covers every selected GPU.
        lowest = min(seen)
        context.nvidia_arch_flags = f"-gencode arch=compute_{lowest},code=compute_{lowest}"
        selected_display = " ".join(str(value) for value in selected)
        self.logger.info(f"CUDA targets: '{selected_display}' (PTX: 'compute_{lowest}').")
        return True

    def _nvcc_probe_arguments(self, nvcc: Path, host_flags: list[str], source: Path) -> list[str]:
        # The same flags FFmpeg's configure adds before `check_nvcc`, so a
        # host-compiler rejection surfaces here instead of hours later.
        return [
            str(nvcc),
            "-O2",
            *host_flags,
            *self.context.nvidia_arch_flags.split(),
            "-std=c++11",
            "-m64",
            "-ptx",
            str(source),
            "-o",
            str(source.with_suffix(".ptx")),
        ]

    def _installed_gcc_pair(self, limit: int) -> int | None:
        """Highest `gcc-N`/`g++-N` pair nvcc would accept.

        Both are required: nvcc drives `gcc-N` on C++ sources, which fails
        without the `g++-N` package's cc1plus.
        """
        for version in range(limit, _OLDEST_NVCC_GCC - 1, -1):
            if (
                self.runner.which(f"gcc-{version}") is not None
                and self.runner.which(f"g++-{version}") is not None
            ):
                return version
        return None

    def verify_nvcc_host_compiler(self) -> None:
        """Probe nvcc the way FFmpeg's configure will, before anything is built.

        A rejected host compiler falls back to an installed older GCC pair
        when one exists; otherwise CUDA filter compilation is disabled for the
        run with the exact packages to install, and NVENC/NVDEC are retained.
        """
        context = self.context
        cuda_root = context.cuda_root
        if cuda_root is None or not context.nvidia_arch_flags:
            return
        nvcc = cuda_root / "bin/nvcc"
        probe_directory = Path(tempfile.mkdtemp(prefix=".nvcc-probe.", dir=context.packages))
        context.register_temporary_path(probe_directory)
        try:
            source = probe_directory / "probe.cu"
            source.write_text(_NVCC_PROBE_SOURCE, encoding="utf-8")
            completed = self.runner.capture(self._nvcc_probe_arguments(nvcc, [], source))
            if completed.returncode == 0:
                return
            limit_match = _NVCC_GCC_LIMIT.search(completed.stderr + completed.stdout)
            if limit_match is None:
                detail = [line for line in completed.stderr.splitlines() if line.strip()]
                self.logger.warn(
                    "'nvcc' cannot compile FFmpeg's CUDA probe with the selected compiler "
                    f"('{detail[-1] if detail else 'no diagnostic'}'); CUDA filter compilation "
                    "is disabled for this run and NVENC/NVDEC are retained."
                )
                context.nvidia_arch_flags = ""
                return
            limit = int(limit_match.group(1))
            fallback = self._installed_gcc_pair(limit)
            if fallback is not None:
                host_flags = ["-ccbin", f"gcc-{fallback}"]
                completed = self.runner.capture(
                    self._nvcc_probe_arguments(nvcc, host_flags, source)
                )
                if completed.returncode == 0:
                    context.nvcc_host_flags = " ".join(host_flags)
                    self.logger.info(
                        f"'nvcc' rejects the default host compiler (GCC {limit} is the newest "
                        f"it supports); compiling CUDA filters with 'gcc-{fallback}'."
                    )
                    return
                detail = [line for line in completed.stderr.splitlines() if line.strip()]
                self.logger.warn(
                    f"'nvcc' rejects the default host compiler, and the installed "
                    f"'gcc-{fallback}' failed its probe too "
                    f"('{detail[-1] if detail else 'no diagnostic'}'). This run disables CUDA "
                    "filter compilation and retains NVENC/NVDEC."
                )
                context.nvidia_arch_flags = ""
                return
            self.logger.warn(
                f"'nvcc' rejects the selected compiler: GCC {limit} is the newest this CUDA "
                f"toolkit supports. Install a supported pair ('sudo apt install gcc-{limit} "
                f"g++-{limit}') and rerun to compile CUDA filters. This run disables CUDA "
                "filter compilation and retains NVENC/NVDEC."
            )
            context.nvidia_arch_flags = ""
        finally:
            safe_remove_tree(probe_directory, context.packages)
            context.unregister_temporary_path(probe_directory)

    def _prepare_cuda_compilation(self, origin: str) -> None:
        if not self.configure_nvidia_architecture():
            self.logger.warn(
                f"{origin}: CUDA architecture detection failed; CUDA compilation will be disabled."
            )
            return
        self.verify_nvcc_host_compiler()

    def install_cuda(self) -> None:
        context = self.context
        install_mode = os.environ.get("CUDA_INSTALL", "ask")
        if install_mode not in ("ask", "always", "never"):
            raise BuildError(
                f"Invalid 'CUDA_INSTALL' value '{install_mode}'; "
                "expected 'ask', 'always', or 'never'."
            )
        if not context.nvidia_gpu_present:
            return

        context.cuda_root = self.find_cuda_root()
        if context.cuda_root is not None:
            version = self.local_cuda_version(context.cuda_root) or "unknown"
            self.logger.info(
                f"CUDA toolkit detected at '{context.cuda_root}' (version '{version}')."
            )
            self._prepare_cuda_compilation("Installed CUDA toolkit")
            return

        if install_mode == "never":
            self.logger.warn(
                "NVIDIA GPU detected, but 'CUDA_INSTALL=never' and no toolkit is installed."
            )
            return
        if install_mode == "ask":
            if not sys.stdin.isatty():
                self.logger.warn(
                    "NVIDIA GPU detected, but input is non-interactive; "
                    "skipping CUDA toolkit installation."
                )
                return
            answer = self.logger.prompt(
                "Install the CUDA toolkit from NVIDIA's signed APT repository? [y/N]: "
            )
            if answer.strip().lower() not in ("y", "yes"):
                return

        self.install_cuda_toolkit()
        context.cuda_root = self.find_cuda_root()
        if context.cuda_root is None:
            raise BuildError(
                "CUDA toolkit installation completed, but 'nvcc' could not be located."
            )
        self._prepare_cuda_compilation("New CUDA toolkit")

    def run(self) -> None:
        context = self.context
        self.detect_gpu_vendors()
        self.logger.banner("Hardware Detection")
        # One record rather than three bare prints: these results belong in the
        # build log a bug report will quote, and routing them through the logger
        # is what puts them there on the same timeline as everything around them.
        self.logger.info(
            "NVIDIA: {0}\nAMD:    {1}\nIntel:  {2}".format(
                "NVIDIA GPU detected" if context.nvidia_gpu_present else "NVIDIA GPU not detected",
                "AMD GPU detected" if context.amd_gpu_present else "AMD GPU not detected",
                "Intel GPU detected" if context.intel_gpu_present else "Intel GPU not detected",
            )
        )
        if not context.has_vulkan_gpu:
            self.logger.warn(
                "No supported GPU was detected; proprietary GPU integrations will be omitted "
                "and generic hardware APIs may have no runtime device."
            )
