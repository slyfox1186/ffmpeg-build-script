"""Host validation, package installation, and toolchain environment setup."""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..registry import PACKAGES, Kind
from ..runtime.context import BuildContext
from ..runtime.errors import BuildError
from ..runtime.exec import BASE_PATH, Runner

# The project standardizes on the high-level APT interface. Only its expected
# script-interface notice is suppressed; command diagnostics and exit codes
# remain intact.
APT_SCRIPT_OPTIONS = ("-o", "APT::Cmd::Disable-Script-Warning=1")

BASE_PACKAGES = (
    "autoconf",
    "automake",
    "autopoint",
    "bison",
    "build-essential",
    "ca-certificates",
    "ccache",
    "cmake",
    "curl",
    "flex",
    "g++",
    "gcc",
    "gettext",
    "git",
    "gnupg",
    "gperf",
    "libtool",
    "libtool-bin",
    "m4",
    "meson",
    "nasm",
    "ninja-build",
    "patch",
    "pciutils",
    "perl",
    "pkgconf",
    "python3",
    "python3-dev",
    "python3-venv",
    "tar",
    "xz-utils",
    "yasm",
)
ESSENTIAL_DEVELOPMENT_PACKAGES = ("libbz2-dev", "liblzma-dev", "libssl-dev", "zlib1g-dev")

REQUIRED_HOST_TOOLS = (
    "ar",
    "awk",
    "bison",
    "cmake",
    "curl",
    "flex",
    "flock",
    "git",
    "make",
    "meson",
    "nasm",
    "ninja",
    "patch",
    "pkgconf",
    "python3",
    "ranlib",
    "sed",
    "tar",
    "timeout",
    "xz",
    "yasm",
)

_OS_RELEASE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_APT_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+.-]*$")


class HostPackages:
    """The APT request for one selection.

    `required` is the subset whose absence is fatal rather than a warning: a
    package the user named explicitly, or one another selection depends on.
    """

    def __init__(self) -> None:
        self.names: list[str] = []
        self.required: set[str] = set()
        self._seen: set[str] = set()

    def add(self, *names: str) -> None:
        for name in names:
            if name and name not in self._seen:
                self._seen.add(name)
                self.names.append(name)

    def require(self, *names: str) -> None:
        self.add(*names)
        self.required.update(names)


def release_unavailable_packages(operating_system: str, codename: str) -> tuple[str, ...]:
    """Packages archive-verified as absent on a specific release.

    Verified against the Debian and Ubuntu package archives (2026-08): these do
    not exist under any name there, so an availability probe can never succeed.
    Keep this in sync with the archives when supported releases change.
    """
    if (operating_system, codename) == ("Ubuntu", "jammy"):
        return ("libjxl-dev", "libshaderc-dev", "libzix-dev")
    if (operating_system, codename) == ("Debian", "bookworm"):
        return ("libzix-dev",)
    return ()


def release_absence_guidance(package_name: str) -> str:
    return {
        "libzix-dev": "Enable the 'zix' source build instead of the system package.",
        "libjxl-dev": "Disable the 'libjxl' selection on this release.",
        "libshaderc-dev": "Disable the 'libshaderc' selection on this release.",
    }.get(package_name, "")


def format_package_list(names: list[str]) -> str:
    return ", ".join(f"'{name}'" for name in names)


def read_os_release_fields(path: Path) -> dict[str, str]:
    """Read os-release(5) as data, never as code.

    The file is shell-compatible syntax, and sourcing it would execute its
    contents in a process that goes on to run sudo-authorized steps. Quotes are
    stripped but the four permitted backslash escapes are not unescaped: the
    spec restricts every key this reads to characters that cannot contain one.
    """
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.rstrip("\r").lstrip()
        key, separator, value = line.partition("=")
        if not separator or not _OS_RELEASE_KEY.match(key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
    return fields


class SystemSetup:
    def __init__(self, context: BuildContext) -> None:
        self.context = context
        self.logger = context.logger
        self.runner = context.runner
        self.apt_index_updated = False

    # -- APT -------------------------------------------------------------

    def apt_update_once(self) -> None:
        if self.apt_index_updated:
            return
        self.logger.info("Refreshing APT package metadata...")
        self.context.execute(["sudo", "apt", *APT_SCRIPT_OPTIONS, "update"])
        self.apt_index_updated = True

    def apt_package_available(self, package_name: str) -> bool:
        if not _APT_PACKAGE_NAME.match(package_name):
            return False
        return self.runner.probe(["apt", *APT_SCRIPT_OPTIONS, "show", package_name])

    def apt_package_installed(self, package_name: str) -> bool:
        completed = self.runner.capture(["dpkg-query", "-W", "-f=${Status}", package_name])
        return completed.returncode == 0 and completed.stdout.strip() == "install ok installed"

    def install_apt_packages(self, request: HostPackages) -> None:
        context = self.context
        absent_here = set(
            release_unavailable_packages(context.operating_system, context.release_codename)
        )
        pending: list[str] = []
        for package_name in request.names:
            if self.apt_package_installed(package_name):
                continue
            # The archive-verified absence list improves messages only; a
            # package still visible to APT (through a third-party repository,
            # say) keeps the normal installation path.
            if package_name in absent_here and not self.apt_package_available(package_name):
                if package_name in request.required:
                    guidance = release_absence_guidance(package_name)
                    suffix = f" {guidance}" if guidance else ""
                    raise BuildError(
                        f"Required host package '{package_name}' is not packaged on "
                        f"'{context.operating_system} {context.release_version}' "
                        f"('{context.release_codename}').{suffix}"
                    )
                self.logger.info(
                    f"Skipping optional '{package_name}'; it is not packaged on "
                    f"'{context.operating_system} {context.release_version}' "
                    f"('{context.release_codename}')."
                )
                continue
            pending.append(package_name)

        if not pending:
            self.logger.info("No host packages require installation.")
            return

        self.apt_update_once()
        missing: list[str] = []
        required_unavailable: list[str] = []
        unavailable: list[str] = []
        for package_name in pending:
            if self.apt_package_available(package_name):
                missing.append(package_name)
            elif package_name in request.required:
                required_unavailable.append(package_name)
            else:
                unavailable.append(package_name)

        component_guidance = ""
        if context.operating_system == "Ubuntu":
            component_guidance = (
                " Ensure APT's 'universe' component is enabled "
                "('sudo add-apt-repository universe')."
            )
        release = f"'{context.operating_system} {context.release_version}'"
        if required_unavailable:
            raise BuildError(
                f"Required host packages are unavailable on {release}: "
                f"{format_package_list(required_unavailable)}.{component_guidance}"
            )
        if unavailable:
            self.logger.warn(
                f"Optional packages unavailable on {release}: "
                f"{format_package_list(unavailable)}.{component_guidance}"
            )
        if not missing:
            self.logger.info("All available host packages are already installed.")
            return

        self.logger.info(
            f"Installing {len(missing)} host package(s): {format_package_list(missing)}."
        )
        self.context.execute(
            [
                "sudo",
                "env",
                "DEBIAN_FRONTEND=noninteractive",
                "apt",
                *APT_SCRIPT_OPTIONS,
                "install",
                "--assume-yes",
                "--no-install-recommends",
                *missing,
            ]
        )

    # -- host identification ---------------------------------------------

    def detect_operating_system(self) -> None:
        context = self.context
        os_release_file = Path(os.environ.get("OS_RELEASE_FILE", "/etc/os-release"))
        kernel_release_file = Path(
            os.environ.get("KERNEL_RELEASE_FILE", "/proc/sys/kernel/osrelease")
        )
        if not os_release_file.is_file():
            raise BuildError(f"'{os_release_file}' is required for operating-system detection.")
        fields = read_os_release_fields(os_release_file)

        # os-release(5): VERSION_ID and VERSION_CODENAME are both optional
        # (Debian testing ships only the codename), and ID_LIKE is the
        # documented fallback for identifying derivatives.
        detected_id = fields.get("ID", "")
        detected_like = fields.get("ID_LIKE", "")
        detected_version = fields.get("VERSION_ID", "")
        detected_codename = fields.get("VERSION_CODENAME", "")
        ubuntu_codename = fields.get("UBUNTU_CODENAME", "")
        if not detected_id:
            raise BuildError(f"Unable to identify the operating system from '{os_release_file}'.")

        context.variable_os = detected_id
        if detected_id == "debian":
            context.operating_system = "Debian"
            series = detected_codename or detected_version.split(".", 1)[0]
            if series in ("bookworm", "12"):
                context.release_version, context.release_codename = "12", "bookworm"
            elif series in ("trixie", "13"):
                context.release_version, context.release_codename = "13", "trixie"
            elif series in ("forky", "sid"):
                raise BuildError(
                    f"Debian testing/unstable ('{series}') is unsupported; "
                    "use Debian 12 'bookworm' or 13 'trixie'."
                )
            else:
                raise BuildError(
                    f"Unsupported Debian release '{series or 'unknown'}'; "
                    "supported releases are 12 'bookworm' and 13 'trixie'."
                )
        elif detected_id == "ubuntu":
            context.operating_system = "Ubuntu"
            releases = {"22.04": "jammy", "24.04": "noble", "26.04": "resolute"}
            if detected_version not in releases:
                raise BuildError(
                    f"Unsupported Ubuntu release '{detected_version or 'unknown'}'; supported "
                    "LTS releases are 22.04 'jammy', 24.04 'noble', and 26.04 'resolute'."
                )
            context.release_version = detected_version
            context.release_codename = releases[detected_version]
            if detected_codename and detected_codename != context.release_codename:
                raise BuildError(
                    f"Inconsistent Ubuntu metadata: VERSION_ID '{detected_version}' does not "
                    f"match VERSION_CODENAME '{detected_codename}'."
                )
        else:
            if "ubuntu" not in detected_like.split():
                suffix = f" {detected_version}" if detected_version else ""
                raise BuildError(
                    f"Unsupported operating system '{detected_id}{suffix}'; "
                    "use Debian 12/13 or Ubuntu 22.04/24.04/26.04."
                )
            context.operating_system = "Ubuntu"
            bases = {"jammy": "22.04", "noble": "24.04", "resolute": "26.04"}
            if ubuntu_codename not in bases:
                raise BuildError(
                    f"Unsupported Ubuntu derivative base '{ubuntu_codename or 'unknown'}'; a "
                    "22.04 'jammy', 24.04 'noble', or 26.04 'resolute' base is required."
                )
            context.release_codename = ubuntu_codename
            context.release_version = bases[ubuntu_codename]

        kernel_release = ""
        if kernel_release_file.is_file():
            kernel_release = kernel_release_file.read_text(
                encoding="utf-8", errors="replace"
            ).strip()
        if "microsoft" in kernel_release.lower():
            # WSL2 kernels carry a 'microsoft-standard-WSL2' release string;
            # WSL1 reports a plain 'Microsoft' suffix because it has no kernel.
            if "wsl2" not in kernel_release.lower():
                raise BuildError(
                    f"WSL1 detected ('{kernel_release}'); convert the distribution with "
                    "'wsl.exe --set-version <distro> 2' and update WSL with 'wsl.exe --update'."
                )
            context.variable_os = "WSL2"

    # -- package selection -----------------------------------------------

    def collect_host_packages(self) -> HostPackages:
        """Translate the package selection into an APT request.

        A pure function of the selection, the compiler choice and the licence
        mode, so it can be diffed directly against the Bash implementation.
        """
        context = self.context
        enabled = context.package_enabled
        explicit = context.package_explicitly_enabled
        request = HostPackages()
        request.require(*BASE_PACKAGES, *ESSENTIAL_DEVELOPMENT_PACKAGES)
        if context.compiler == "clang":
            request.require("clang")

        # The straightforward one-to-one mappings come from the registry, so a
        # new system package needs no edit here.
        for package in PACKAGES.values():
            if package.kind is not Kind.SYSTEM or not package.apt_packages:
                continue
            if package.gate.name == "REQUIRES_GPL" and not context.nonfree_and_gpl:
                continue
            if not enabled(package.key):
                continue
            request.add(*package.apt_packages)
            if explicit(package.key):
                request.require(*package.apt_packages)

        # The remaining selections pull different package sets depending on
        # what else is enabled, so they stay written out.
        if (
            enabled("xlib")
            or enabled("opengl")
            or enabled("freeglut")
            or enabled("sdl2")
            or enabled("gpac-git")
        ):
            request.add("libx11-dev")
        if enabled("xlib"):
            xlib_packages = (
                "libxcb-shape0-dev",
                "libxcb-shm0-dev",
                "libxcb-xfixes0-dev",
                "libxcb1-dev",
                "libxext-dev",
                "libxv-dev",
            )
            request.add(*xlib_packages)
            if explicit("xlib"):
                request.require("libx11-dev", *xlib_packages)
        if enabled("opengl") or enabled("freeglut"):
            request.add("libgl1-mesa-dev", "libglu1-mesa-dev")
        if enabled("freeglut"):
            request.add("libxi-dev")
        if enabled("sdl2"):
            request.add(
                "libasound2-dev",
                "libdecor-0-dev",
                "libdrm-dev",
                "libpulse-dev",
                "libwayland-dev",
                "libx11-dev",
            )
        if enabled("libheif"):
            request.add("libde265-dev")

        # Source builds that were turned off but are still needed by something
        # else become required host packages.
        if not enabled("av1-git") and enabled("avif"):
            request.require("libaom-dev")
        if not enabled("libogg") and (enabled("vorbis") or enabled("libtheora")):
            request.require("libogg-dev")
        if not enabled("gmp") and enabled("gnutls"):
            request.require("libgmp-dev")
        if not enabled("nettle") and enabled("gnutls"):
            request.require("nettle-dev")
        if enabled("fontconfig"):
            if not enabled("libxml2"):
                request.require("libxml2-dev")
            if not enabled("freetype"):
                request.require("libfreetype-dev")
        if enabled("libass"):
            if not enabled("fontconfig"):
                request.require("libfontconfig-dev")
            if not enabled("freetype"):
                request.require("libfreetype-dev")
            if not enabled("fribidi"):
                request.require("libfribidi-dev")
            if not enabled("harfbuzz"):
                request.require("libharfbuzz-dev")
        if enabled("lilv") and not enabled("lv2-git"):
            request.require("lv2-dev")
        if enabled("lilv"):
            if not enabled("serd"):
                request.require("libserd-dev")
            if not enabled("zix"):
                request.require("libzix-dev")
            if not enabled("sord"):
                request.require("libsord-dev")
            if not enabled("sratom"):
                request.require("libsratom-dev")
        if enabled("sord"):
            if not enabled("serd"):
                request.require("libserd-dev")
            if not enabled("zix"):
                request.require("libzix-dev")
        if enabled("sratom"):
            if not enabled("lv2-git"):
                request.require("lv2-dev")
            if not enabled("serd"):
                request.require("libserd-dev")
        if enabled("ant-git"):
            request.require("default-jdk")
        return request

    # -- toolchain environment -------------------------------------------

    def verify_required_host_tools(self) -> None:
        tools = list(REQUIRED_HOST_TOOLS)
        tools += ["gcc", "g++"] if self.context.compiler == "gcc" else ["clang", "clang++"]
        missing = [tool for tool in tools if self.runner.which(tool) is None]
        if missing:
            listed = ", ".join(f"'{tool}'" for tool in missing)
            raise BuildError(f"Required command(s) not found: {listed}.")

    def configure_pkgconf_search_paths(self) -> None:
        """Separate the workspace overlay from the host's compiled defaults.

        `PKG_CONFIG_PATH` is the high-priority overlay. System directories stay
        in pkgconf's lower-priority compiled defaults instead of being
        duplicated here, and inherited cross-build overrides are dropped: this
        is a native build, and they would rewrite paths returned from package
        metadata.
        """
        context = self.context
        system_pkgconf = Path("/usr/bin/pkgconf")
        if not os.access(system_pkgconf, os.X_OK):
            raise BuildError(
                f"The host 'pkgconf' executable was not installed at '{system_pkgconf}'."
            )
        environment = self.runner.child_environment()
        for name in ("PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR", "PKG_CONFIG_SYSROOT_DIR"):
            environment.pop(name, None)
        completed = Runner(self.context.logger, environment).capture(
            [str(system_pkgconf), "--variable=pc_path", "pkgconf"],
            timeout=30,
        )
        if completed.returncode != 0:
            raise BuildError("Unable to query the host pkgconf default search path.")
        search_path = completed.stdout.strip()
        valid = (
            search_path
            and not search_path.startswith(":")
            and not search_path.endswith(":")
            and "::" not in search_path
            and all(ord(character) >= 0x20 for character in search_path)
        )
        if not valid:
            raise BuildError("The host pkgconf returned an invalid default search path.")
        for entry in search_path.split(":"):
            if not entry.startswith("/"):
                raise BuildError(
                    f"The host pkgconf returned a non-absolute default search path: '{entry}'."
                )
        context.system_pkg_config_path = search_path

        workspace = context.workspace
        context.env["PKG_CONFIG_PATH"] = ":".join(
            [
                f"{workspace}/lib/pkgconfig",
                f"{workspace}/lib64/pkgconfig",
                f"{workspace}/lib/x86_64-linux-gnu/pkgconfig",
                f"{workspace}/share/pkgconfig",
            ]
        )
        context.env.pop("PKG_CONFIG_LIBDIR", None)
        context.env.pop("PKG_CONFIG_SYSROOT_DIR", None)

    def source_path(self) -> None:
        """Rebuild PATH from the fixed base plus this build's own directories."""
        context = self.context
        context.env["PATH"] = BASE_PATH
        ccache_directory = ""
        for candidate in ("/usr/lib/ccache/bin", "/usr/lib/ccache"):
            if Path(candidate).is_dir():
                ccache_directory = candidate
                break
        context.env["ccache_dir"] = ccache_directory
        # PATH must include this directory before the first tool is installed.
        # path_prepend intentionally ignores missing directories; otherwise a
        # fresh build runs system libtoolize with workspace aclocal macros,
        # while a rerun uses the matching workspace tools.
        (context.workspace / "bin").mkdir(parents=True, exist_ok=True)
        context.path_prepend(context.workspace / "bin")
        context.path_prepend("/opt/cuda/bin")
        context.path_prepend("/usr/local/cuda/bin")
        if ccache_directory:
            context.path_prepend(ccache_directory)

    def set_java_variables(self) -> None:
        javac_path = self.runner.which("javac")
        if javac_path is None:
            raise BuildError("'javac' was not installed by the host setup.")
        resolved = Path(javac_path).resolve()
        java_home = resolved.parent.parent
        if not (java_home / "include").is_dir():
            raise BuildError(f"Java include directory not found under '{java_home}'.")
        self.context.env["JAVA_HOME"] = str(java_home)
        self.context.env["JDK_HOME"] = str(java_home)
        self.context.path_prepend(java_home / "bin")

    def report_compiler_versions(self) -> None:
        """Report the selected C/C++ commands through the actual build PATH."""
        for variable, label in (("CC", "C compiler"), ("CXX", "C++ compiler")):
            command = self.context.env[variable]
            executable = self.runner.which(command)
            if executable is None:
                self.logger.warn(f"{label}: '{command}' was not found on the build PATH.")
                continue
            # Keep the invocation name: resolving a ccache/clang symlink to
            # ccache itself would report ccache's version instead of Clang's.
            result = self.runner.capture([executable, "--version"], timeout=10)
            lines = result.stdout.strip().splitlines()
            if result.returncode != 0 or not lines:
                self.logger.warn(f"{label}: unable to read the version from '{executable}'.")
                continue
            self.logger.info(f"{label}: '{lines[0]}' ('{executable}').")

    def run(self) -> None:
        context = self.context
        for tool in ("apt", "dpkg-query", "readlink"):
            if self.runner.which(tool) is None:
                raise BuildError(f"Required command(s) not found: '{tool}'.")
        self.detect_operating_system()
        self.install_apt_packages(self.collect_host_packages())
        self.verify_required_host_tools()
        self.configure_pkgconf_search_paths()
        self.source_path()
        if context.variable_os == "WSL2":
            context.path_prepend("/usr/lib/wsl/lib")
        if context.package_enabled("ant-git"):
            self.set_java_variables()
        self.logger.info(
            f"Host setup complete: '{context.operating_system} {context.release_version}' "
            f"('{context.variable_os}')."
        )
        self.report_compiler_versions()


def check_avx512() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        try:
            if re.search(r"\bavx512f\b", cpuinfo.read_text(encoding="utf-8", errors="replace")):
                return "ON"
        except OSError:
            pass
    return "OFF"


def set_ant_path(context: BuildContext) -> Path:
    ant_home = context.workspace / "ant"
    context.env["ANT_HOME"] = str(ant_home)
    context.execute(["mkdir", "-p", str(ant_home / "bin"), str(ant_home / "lib")])
    return ant_home
