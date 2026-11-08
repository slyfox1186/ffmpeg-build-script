"""GPU discovery and optional CUDA toolkit installation and updates.

This stage never installs or replaces an NVIDIA display driver, and it never
guesses CUDA architectures: the targets come from `nvcc --list-gpu-code` and
`nvidia-smi`. CUDA itself is added from NVIDIA's signed network repository and
only after an explicit opt-in.

The newest toolkit is read from this distribution's own repository listing
rather than NVIDIA's download page, so the release offered is one apt can
install here. WSL2 uses the same per-distribution repository: NVIDIA deprecated
its 'wsl-ubuntu' repository, which stops at CUDA 13.3.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.paths import safe_remove_tree
from ..runtime.versioncmp import version_compare, version_sort
from .system_setup import APT_SCRIPT_OPTIONS, WSL_LIBRARY_DIRECTORY, SystemSetup

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


# `cuda-toolkit-13-5_13.5.0-1_amd64.deb`: the series in the name must match the
# version, which excludes `cuda-toolkit-13-4-config-common_13.4.92-1_all.deb` and
# `cuda-toolkit-13-config-common_13.5.37-1_all.deb`.
_CUDA_TOOLKIT_PACKAGE = re.compile(
    r"cuda-toolkit-([0-9]+)-([0-9]+)_(([0-9]+)\.([0-9]+)\.[0-9]+)-([0-9]+)_amd64\.deb"
)
_CUDA_KEYRING_PACKAGE = re.compile(r"cuda-keyring_([0-9]+(?:\.[0-9]+)+-[0-9]+)_all\.deb")
_CUDA_RELEASE_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# Each `cuda-toolkit-M-m` package installs into its own `cuda-M.m` directory here.
CUDA_PREFIX = Path("/usr/local")
# The source entry of NVIDIA's deprecated WSL repository, which ends at CUDA 13.3.
WSL_CUDA_SOURCE = Path("/etc/apt/sources.list.d/cuda-wsl-ubuntu-x86_64.list")
# The driver's own answer, from a stable C API, rather than the `nvidia-smi`
# banner, whose label changed from "CUDA Version" to "CUDA UMD Version". Run as a
# child so loading the driver library can never affect the build process.
_DRIVER_CUDA_PROBE = (
    "import ctypes\n"
    "version = ctypes.c_int()\n"
    "status = ctypes.CDLL('libcuda.so.1').cuDriverGetVersion(ctypes.byref(version))\n"
    "print(version.value if status == 0 else '')\n"
)


@dataclass(frozen=True)
class CudaRelease:
    """One `cuda-toolkit-M-m` package in NVIDIA's repository for this system."""

    version: str
    package_version: str
    repository: str
    repository_url: str
    keyring_version: str

    @property
    def series(self) -> str:
        return ".".join(self.version.split(".")[:2])

    @property
    def package(self) -> str:
        return "cuda-toolkit-" + self.series.replace(".", "-")

    @property
    def root(self) -> Path:
        return CUDA_PREFIX / f"cuda-{self.series}"


def parse_cuda_listing(listing: str) -> tuple[list[tuple[str, str]], str | None]:
    """The toolkit (version, package version) pairs, newest first, and the newest keyring."""
    toolkits: dict[str, str] = {}
    for match in _CUDA_TOOLKIT_PACKAGE.finditer(listing):
        major, minor, version, version_major, version_minor, revision = match.groups()
        if (major, minor) != (version_major, version_minor):
            continue
        package_version = f"{version}-{revision}"
        recorded = toolkits.get(version)
        if recorded is None or version_compare(package_version, recorded) > 0:
            toolkits[version] = package_version
    ordered = version_sort(list(toolkits), reverse=True, unique=True)
    keyrings = version_sort(_CUDA_KEYRING_PACKAGE.findall(listing), reverse=True, unique=True)
    return [(version, toolkits[version]) for version in ordered], (
        keyrings[0] if keyrings else None
    )


def cuda_series(version: str) -> str:
    return ".".join(version.split(".")[:2])


def cuda_update_available(installed: str, available: str) -> bool:
    """Whether `available` is newer; an installed `M.m` without its patch level is
    compared by series, so 13.4 is never told that 13.4.3 is an update."""
    if installed.count(".") == 1:
        return version_compare(cuda_series(available), installed) > 0
    return version_compare(available, installed) > 0


def newest_supported_release(
    releases: list[CudaRelease], driver_series: str | None
) -> CudaRelease | None:
    """The newest release whose PTX this driver can load; any release when unknown.

    NVIDIA's minor-version compatibility excludes PTX from a newer toolkit, and
    FFmpeg's CUDA filters are PTX the driver compiles at load time.
    """
    for release in releases:
        if driver_series is None or version_compare(release.series, driver_series) <= 0:
            return release
    return None


def describe_pci_device(line: str) -> str:
    """`01:00.0 VGA compatible controller [0300]: NVIDIA … [10de:2684] (rev a1)` -> the device."""
    _, separator, device = line.partition("]: ")
    if not separator:
        device = line.split(": ", 1)[-1]
    return re.sub(r"\s*\(rev [0-9a-fA-F]+\)$", "", device).strip()


class HardwareDetection:
    def __init__(self, context: BuildContext, setup: SystemSetup) -> None:
        self.context = context
        self.setup = setup
        self.logger = context.logger
        self.runner = context.runner
        self.available_architectures: list[int] = []
        # What the report names for each vendor: driver-reported models first,
        # else the lspci device lines that identified it.
        self.gpu_descriptions: dict[str, list[str]] = {"NVIDIA": [], "AMD": [], "Intel": []}

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
        wsl_nvidia_smi = f"{WSL_LIBRARY_DIRECTORY}/nvidia-smi"
        if nvidia_smi is None and os.access(wsl_nvidia_smi, os.X_OK):
            nvidia_smi = wsl_nvidia_smi
            context.path_prepend(WSL_LIBRARY_DIRECTORY)

        context.nvidia_gpu_present = False
        if nvidia_smi is not None and self.runner.probe(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"]
        ):
            context.nvidia_gpu_present = True
            details = self.runner.capture(
                [nvidia_smi, "--query-gpu=name,driver_version", "--format=csv,noheader"]
            )
            if details.returncode == 0:
                for line in details.stdout.splitlines():
                    name, _, driver = line.rpartition(",")
                    if name.strip():
                        self.gpu_descriptions["NVIDIA"].append(
                            f"{name.strip()} (driver {driver.strip()})"
                        )
        elif re.search("nvidia", controllers, re.IGNORECASE):
            context.nvidia_gpu_present = True

        vendor_patterns = {
            "NVIDIA": re.compile("nvidia", re.IGNORECASE),
            "AMD": re.compile(r"amd/ati|advanced micro devices|radeon", re.IGNORECASE),
            "Intel": re.compile("intel", re.IGNORECASE),
        }
        context.amd_gpu_present = bool(vendor_patterns["AMD"].search(controllers))
        context.intel_gpu_present = bool(vendor_patterns["Intel"].search(controllers))
        for vendor, pattern in vendor_patterns.items():
            if self.gpu_descriptions[vendor]:
                continue
            for line in controllers.splitlines():
                if pattern.search(line):
                    self.gpu_descriptions[vendor].append(describe_pci_device(line))
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
        """`version.json`'s full release, else `nvcc`'s `M.m`, else None."""
        if not os.access(cuda_root / "bin/nvcc", os.X_OK):
            return None
        try:
            record = json.loads((cuda_root / "version.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            record = None
        if isinstance(record, dict):
            cuda = record.get("cuda")
            version = cuda.get("version") if isinstance(cuda, dict) else None
            if isinstance(version, str) and _CUDA_RELEASE_VERSION.match(version):
                return version
        completed = self.runner.capture([str(cuda_root / "bin/nvcc"), "--version"])
        if completed.returncode != 0:
            return None
        match = re.search(r"release ([0-9]+\.[0-9]+)\b", completed.stdout)
        return match.group(1) if match else None

    def driver_cuda_version(self) -> str | None:
        """The newest CUDA `M.m` the installed NVIDIA driver supports, or None."""
        completed = self.runner.capture(
            [sys.executable, "-I", "-c", _DRIVER_CUDA_PROBE], timeout=20
        )
        value = completed.stdout.strip()
        if completed.returncode != 0 or not value.isdigit() or int(value) <= 0:
            return None
        number = int(value)
        return f"{number // 1000}.{number % 1000 // 10}"

    def cuda_repository_name(self) -> str | None:
        context = self.context
        return _CUDA_REPOSITORIES.get((context.operating_system, context.release_version))

    def cuda_releases(self) -> list[CudaRelease] | None:
        """This system's CUDA toolkit releases, newest first, from one repository listing.

        None when no repository maps to this system, the listing cannot be read,
        or it names no keyring or toolkit; every caller treats that as optional.
        """
        repository = self.cuda_repository_name()
        if repository is None:
            return None
        repository_url = (
            f"https://developer.download.nvidia.com/compute/cuda/repos/{repository}/x86_64/"
        )
        listing = self.context.resolver.fetch_text(repository_url)
        if listing is None:
            return None
        toolkits, keyring_version = parse_cuda_listing(listing)
        if keyring_version is None or not toolkits:
            return None
        return [
            CudaRelease(version, package_version, repository, repository_url, keyring_version)
            for version, package_version in toolkits
        ]

    def _remove_wsl_cuda_repository(self) -> None:
        """NVIDIA's documented migration off its deprecated 'wsl-ubuntu' repository.

        Its keyring package and the distribution's share the name and version,
        so installing the new one would keep the old source as an obsolete
        conffile; NVIDIA's WSL guide purges it first.
        """
        if not os.path.lexists(WSL_CUDA_SOURCE):
            return
        self.logger.info("Removing NVIDIA's deprecated 'wsl-ubuntu' CUDA repository...")
        owner = self.runner.capture(["dpkg-query", "-S", str(WSL_CUDA_SOURCE)])
        if owner.returncode == 0 and owner.stdout.split(":", 1)[0].strip() == "cuda-keyring":
            self.context.execute(
                [
                    "sudo",
                    "-n",
                    "env",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt",
                    *APT_SCRIPT_OPTIONS,
                    "remove",
                    "--purge",
                    "--assume-yes",
                    "cuda-keyring",
                ]
            )
        else:
            self.context.execute(["sudo", "-n", "rm", "-f", "--", str(WSL_CUDA_SOURCE)])

    def install_cuda_toolkit(self, release: CudaRelease) -> None:
        context = self.context

        # Staged inside the package cache, not /tmp, so the removal below gets a
        # real containment boundary. Deriving the allowed root from the
        # temporary directory itself would make that check true by construction.
        temp_directory = Path(tempfile.mkdtemp(prefix=".cuda-keyring.", dir=context.packages))
        context.register_temporary_path(temp_directory)
        keyring_file = temp_directory / "cuda-keyring.deb"
        keyring_url = f"{release.repository_url}cuda-keyring_{release.keyring_version}_all.deb"

        self.logger.info(
            f"Downloading NVIDIA's CUDA repository keyring for '{release.repository}'..."
        )
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

        # After the download, so a failed fetch leaves a working configuration.
        self._remove_wsl_cuda_repository()
        context.execute(["sudo", "-n", "dpkg", "-i", str(keyring_file)])
        safe_remove_tree(temp_directory, context.packages)
        context.unregister_temporary_path(temp_directory)
        self.setup.apt_index_updated = False
        self.setup.apt_update_once()
        self.logger.info(f"Installing CUDA {release.version} ('{release.package}')...")
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
                f"{release.package}={release.package_version}",
            ]
        )
        self.setup.source_path()

    def installed_release_root(self, release: CudaRelease) -> Path:
        """The new toolkit's root once it reports the release that was installed.

        The build uses it even when `/usr/local/cuda` still names another
        toolkit, and says why rather than guessing.
        """
        root = release.root
        installed = self.local_cuda_version(root)
        if installed != release.version:
            raise BuildError(
                f"Installing '{release.package}={release.package_version}' finished, but "
                f"'{root}' reports CUDA '{installed or 'unknown'}' instead of {release.version}."
            )
        found = self.find_cuda_root()
        if found is None or found.resolve() != root.resolve():
            query = self.runner.capture(["update-alternatives", "--query", "cuda"])
            if query.returncode == 0 and re.search(r"^Status: manual$", query.stdout, re.MULTILINE):
                self.logger.warn(
                    f"'/usr/local/cuda' is set manually to another toolkit; this build uses "
                    f"'{root}'. Run 'sudo update-alternatives --auto cuda' to make CUDA "
                    f"{release.version} the default."
                )
            else:
                self.logger.warn(
                    f"'nvcc' on the build PATH resolves to '{found}', not '{root}'; this build "
                    f"uses '{root}'."
                )
        return root

    def _consent(self, install_mode: str, question: str, declined: str) -> bool:
        """`always` agrees; `ask` asks on a terminal and otherwise warns `declined`."""
        if install_mode == "always":
            return True
        if not sys.stdin.isatty():
            self.logger.warn(declined)
            return False
        try:
            answer = self.logger.prompt(question)
        except EOFError:
            print()
            return False
        return answer.strip().lower() in ("y", "yes")

    def _driver_limit(self, release: CudaRelease, driver_series: str | None) -> str:
        return (
            f"CUDA {release.version} is available, but this NVIDIA driver supports CUDA up "
            f"to {driver_series}, and FFmpeg's CUDA filters built with it would not load. "
            "Update the NVIDIA driver to one that supports it (see NVIDIA's CUDA release "
            "notes) and run the build again; this script never installs drivers."
        )

    def _offer_update(
        self,
        cuda_root: Path,
        releases: list[CudaRelease] | None,
        driver_series: str | None,
        install_mode: str,
    ) -> Path:
        """Offer a newer toolkit for an installed one; return the root to build with."""
        version = self.local_cuda_version(cuda_root)
        self.logger.info(
            f"CUDA toolkit detected at '{cuda_root}' (version '{version or 'unknown'}')."
        )
        if (
            driver_series is not None
            and version is not None
            and version_compare(cuda_series(version), driver_series) > 0
        ):
            self.logger.warn(
                f"CUDA {version} is newer than the CUDA {driver_series} this NVIDIA driver "
                "supports; FFmpeg's CUDA filters built with it may not load until the driver "
                "is updated."
            )
        if releases is None:
            self.logger.warn(
                "Unable to check NVIDIA's CUDA repository for a newer toolkit; using the "
                "installed one."
            )
            return cuda_root
        if version is None:
            self.logger.warn(
                "Unable to read the installed CUDA toolkit's version; not checking for updates."
            )
            return cuda_root
        newest = releases[0]
        target = newest_supported_release(releases, driver_series)
        if target is not None and cuda_update_available(version, target.version):
            if target is not newest:
                self.logger.info(self._driver_limit(newest, driver_series))
            present = self.local_cuda_version(target.root)
            if (
                present is not None
                and present.count(".") == 2
                and version_compare(present, target.version) >= 0
                and target.root.resolve() != cuda_root.resolve()
            ):
                self.logger.info(
                    f"CUDA {present} is already installed at '{target.root}', but this build "
                    f"uses the default toolkit at '{cuda_root}'."
                )
                return cuda_root
            self.logger.info(
                f"CUDA {target.version} is available from NVIDIA's '{target.repository}' "
                f"repository (installed: {version})."
            )
            if driver_series is None:
                self.logger.warn(
                    "Unable to read the CUDA version this NVIDIA driver supports; make sure "
                    f"it supports CUDA {target.series} before installing."
                )
                if install_mode == "always":
                    # A working toolkit is never replaced unattended by one
                    # whose PTX this driver might not load.
                    self.logger.warn(
                        "Not updating automatically while the driver's CUDA support is "
                        "unknown; run the build in a terminal with 'CUDA_INSTALL=ask' to choose."
                    )
                    return cuda_root
            if not self._consent(
                install_mode,
                f"Install CUDA {target.version} from NVIDIA's signed APT repository? [y/N]: ",
                f"CUDA {target.version} is available, but input is non-interactive; run the "
                "build in a terminal to be asked, or set 'CUDA_INSTALL=always'.",
            ):
                return cuda_root
            # Resolved first: installing can repoint `/usr/local/cuda`.
            previous = cuda_root.resolve()
            self.install_cuda_toolkit(target)
            new_root = self.installed_release_root(target)
            if new_root.resolve() != previous:
                self.logger.info(f"CUDA {version} remains installed at '{previous}'.")
            return new_root
        if cuda_update_available(version, newest.version):
            self.logger.info(self._driver_limit(newest, driver_series))
        else:
            self.logger.info(
                f"CUDA {version} is up to date (newest in NVIDIA's '{newest.repository}' "
                f"repository: {newest.version})."
            )
        return cuda_root

    def read_cuda_architectures(self, cuda_root: Path) -> list[int]:
        completed = self.runner.capture([str(cuda_root / "bin/nvcc"), "--list-gpu-code"])
        found = {int(value) for value in re.findall(r"sm_([0-9]+)", completed.stdout)}
        return sorted(found)

    def _unsupported_targets(self, cuda_root: Path) -> list[int]:
        """The GPU targets this build needs that the toolkit at `cuda_root` cannot compile.

        Read from the toolkit itself, never from a table of GPU generations.
        """
        mode = os.environ.get("CUDA_ARCH_MODE", "native")
        if mode == "native":
            required = self.read_installed_gpu_architectures()
        elif mode == "custom":
            required = [
                int(value)
                for value in os.environ.get("CUDA_ARCHITECTURES", "").split()
                if value.isdigit()
            ]
        else:
            return []
        available = set(self.read_cuda_architectures(cuda_root))
        return [value for value in required if value not in available]

    def compatible_root(self, cuda_root: Path, driver_series: str | None) -> Path:
        """`cuda_root`, or the newest installed toolkit that compiles for this build's GPUs.

        NVIDIA drops older GPU generations in new toolkit series. Checked on
        every run, not only right after an update, because the update makes the
        new toolkit the default that later runs discover.
        """
        dropped = self._unsupported_targets(cuda_root)
        if not dropped:
            return cuda_root
        candidates: dict[str, Path] = {}
        for root in CUDA_PREFIX.glob("cuda-*"):
            if not re.fullmatch(r"cuda-[0-9]+\.[0-9]+", root.name) or root.is_symlink():
                continue
            version = self.local_cuda_version(root)
            if version is None or root.resolve() == cuda_root.resolve():
                continue
            if (
                driver_series is not None
                and version_compare(cuda_series(version), driver_series) > 0
            ):
                continue
            candidates[version] = root
        for version in version_sort(list(candidates), reverse=True):
            root = candidates[version]
            if not self._unsupported_targets(root):
                self.logger.warn(
                    f"The CUDA toolkit at '{cuda_root}' cannot compile for "
                    f"{', '.join(f'sm_{value}' for value in dropped)}; this build uses CUDA "
                    f"{version} at '{root}', which can."
                )
                return root
        return cuda_root

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
            raw = os.environ.get("CUDA_ARCHITECTURES", "").split()
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
        # Every CUDA consumer is an NVIDIA FFmpeg integration, which needs both.
        if not (context.nonfree_and_gpl and context.package_enabled("nv-codec-headers")):
            self.logger.info(
                "NVIDIA GPU detected; the CUDA toolkit is used only with "
                "'--enable-gpl-and-non-free' and 'nv-codec-headers = true', so it is not needed."
            )
            return

        context.cuda_root = self.find_cuda_root()
        if install_mode == "never":
            # No repository lookup either: 'never' leaves CUDA entirely alone.
            if context.cuda_root is None:
                self.logger.warn(
                    "NVIDIA GPU detected, but 'CUDA_INSTALL=never' and no toolkit is installed."
                )
                return
            version = self.local_cuda_version(context.cuda_root) or "unknown"
            self.logger.info(
                f"CUDA toolkit detected at '{context.cuda_root}' (version '{version}')."
            )
            context.cuda_root = self.compatible_root(context.cuda_root, None)
            self._prepare_cuda_compilation("Installed CUDA toolkit")
            return

        releases = self.cuda_releases()
        driver_series = self.driver_cuda_version()
        if context.cuda_root is not None:
            previous = context.cuda_root
            offered = self._offer_update(previous, releases, driver_series, install_mode)
            context.cuda_root = self.compatible_root(offered, driver_series)
            # FFmpeg's configure receipt names nvcc's path, so a toolkit in a
            # new directory reconfigures FFmpeg; dependency builds never use it.
            self._prepare_cuda_compilation(
                "Installed CUDA toolkit" if context.cuda_root == previous else "New CUDA toolkit"
            )
            return

        if releases is None:
            if self.cuda_repository_name() is None:
                problem = (
                    "No supported NVIDIA CUDA repository mapping exists for "
                    f"'{context.operating_system} {context.release_version}'."
                )
            else:
                problem = "Unable to discover NVIDIA's current CUDA toolkit and repository keyring."
            if install_mode == "always":
                raise BuildError(problem)
            self.logger.warn(f"{problem} Skipping the CUDA toolkit installation.")
            return
        target = newest_supported_release(releases, driver_series)
        if target is None:
            self.logger.warn(
                f"No CUDA toolkit in NVIDIA's '{releases[0].repository}' repository supports "
                f"this NVIDIA driver's CUDA {driver_series}; skipping the CUDA toolkit "
                "installation."
            )
            return
        if target is not releases[0]:
            self.logger.info(self._driver_limit(releases[0], driver_series))
        if driver_series is None:
            self.logger.warn(
                "Unable to read the CUDA version this NVIDIA driver supports; CUDA "
                f"{target.version} is the newest release, and FFmpeg's CUDA filters load only "
                "when the driver supports it."
            )
        if not self._consent(
            install_mode,
            f"Install CUDA {target.version} from NVIDIA's signed APT repository? [y/N]: ",
            "NVIDIA GPU detected, but input is non-interactive; "
            "skipping CUDA toolkit installation.",
        ):
            return

        self.install_cuda_toolkit(target)
        context.cuda_root = self.installed_release_root(target)
        # FFmpeg's configure receipt notices the new CUDA options and
        # reconfigures it; dependency builds do not use the toolkit.
        self._prepare_cuda_compilation("New CUDA toolkit")

    def run(self) -> None:
        context = self.context
        self.detect_gpu_vendors()
        self.logger.banner("Hardware Detection")
        # One record rather than three bare prints: these results belong in the
        # build log a bug report will quote, and routing them through the logger
        # is what puts them there on the same timeline as everything around them.
        present = {
            "NVIDIA": context.nvidia_gpu_present,
            "AMD": context.amd_gpu_present,
            "Intel": context.intel_gpu_present,
        }
        lines = []
        for vendor, detected in present.items():
            label = f"{vendor}:".ljust(8)
            if not detected:
                lines.append(f"{label}{vendor} GPU not detected")
                continue
            names = self.gpu_descriptions[vendor] or [f"{vendor} GPU detected"]
            lines.append(label + names[0])
            lines.extend(" " * 8 + name for name in names[1:])
        self.logger.info("\n".join(lines))
        if not context.has_vulkan_gpu:
            self.logger.warn(
                "No supported GPU was detected; proprietary GPU integrations will be omitted "
                "and generic hardware APIs may have no runtime device."
            )
