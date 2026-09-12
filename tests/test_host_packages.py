from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from ffmpeg_build.config import Selection
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.stages.hardware import HardwareDetection
from ffmpeg_build.stages.helpers import pkgconf_include_dir, pkgconf_library_dir
from ffmpeg_build.stages.system_setup import HostPackages, SystemSetup, release_unavailable_packages


def test_new_workspace_discovers_tools_installed_after_path_setup(context: BuildContext) -> None:
    bin_dir = context.workspace / "bin"
    assert not bin_dir.exists()
    setup = SystemSetup(context)
    setup.source_path()
    # This is the first-run order: PATH is set before global tools are built.
    for name in ("m4", "autoconf", "automake", "libtoolize", "pkgconf", "cmake", "ninja"):
        tool = bin_dir / name
        tool.write_text("#!/bin/sh\nprintf 'workspace-tool\\n'\n")
        tool.chmod(0o755)
        assert context.runner.which(name) == str(tool)
        assert context.runner.capture([name]).stdout == "workspace-tool\n"
    setup.source_path()
    assert context.env["PATH"].split(":").count(str(bin_dir)) == 1


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ('ID=debian\nVERSION_ID="12"\nVERSION_CODENAME=bookworm', "Debian|12|bookworm|debian"),
        ("ID=debian\nVERSION_CODENAME=trixie", "Debian|13|trixie|debian"),
        ("ID=debian\nVERSION_CODENAME=forky", "testing/unstable"),
        ('ID=ubuntu\nVERSION_ID="22.04"\nVERSION_CODENAME=jammy', "Ubuntu|22.04|jammy|ubuntu"),
        ('ID=ubuntu\nVERSION_ID="24.04"\nVERSION_CODENAME=noble', "Ubuntu|24.04|noble|ubuntu"),
        (
            'ID=ubuntu\nVERSION_ID="26.04"\nVERSION_CODENAME=resolute',
            "Ubuntu|26.04|resolute|ubuntu",
        ),
        (
            'ID=ubuntu\nVERSION_ID="25.10"\nVERSION_CODENAME=questing',
            "Unsupported Ubuntu release '25.10'",
        ),
        ('ID=ubuntu\nVERSION_ID="24.04"\nVERSION_CODENAME=jammy', "Inconsistent Ubuntu metadata"),
        (
            'ID=linuxmint\nID_LIKE="ubuntu debian"\nVERSION_ID="22.3"\nVERSION_CODENAME=zena\nUBUNTU_CODENAME=noble',
            "Ubuntu|24.04|noble|linuxmint",
        ),
        (
            'ID=zorin\nID_LIKE="ubuntu debian"\nVERSION_ID="17"\nUBUNTU_CODENAME=jammy',
            "Ubuntu|22.04|jammy|zorin",
        ),
        ("ID=arch", "Unsupported operating system 'arch'"),
    ],
)
def test_os_detection(
    context: BuildContext,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fields: str,
    expected: str,
) -> None:
    release = tmp_path / "os-release"
    kernel = tmp_path / "kernel"
    release.write_text(fields + "\n")
    kernel.write_text("6.8.0-52-generic\n")
    monkeypatch.setenv("OS_RELEASE_FILE", str(release))
    monkeypatch.setenv("KERNEL_RELEASE_FILE", str(kernel))
    setup = SystemSetup(context)
    if "|" not in expected:
        with pytest.raises(BuildError) as caught:
            setup.detect_operating_system()
        assert expected in str(caught.value)
    else:
        setup.detect_operating_system()
        assert (
            "|".join(
                (
                    context.operating_system,
                    context.release_version,
                    context.release_codename,
                    context.variable_os,
                )
            )
            == expected
        )


@pytest.mark.parametrize("distro", ["ubuntu", "debian"])
@pytest.mark.parametrize("wsl2", [False, True])
def test_wsl_detection(
    context: BuildContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, distro: str, wsl2: bool
) -> None:
    release = tmp_path / "os-release"
    kernel = tmp_path / "kernel"
    release.write_text(f"ID={distro}\nVERSION_ID={'24.04' if distro == 'ubuntu' else '13'}\n")
    kernel.write_text("5.15.167.4-microsoft-standard-WSL2\n" if wsl2 else "4.4.0-19041-Microsoft\n")
    monkeypatch.setenv("OS_RELEASE_FILE", str(release))
    monkeypatch.setenv("KERNEL_RELEASE_FILE", str(kernel))
    if wsl2:
        SystemSetup(context).detect_operating_system()
        assert context.variable_os == "WSL2"
    else:
        with pytest.raises(BuildError, match="wsl.exe --set-version"):
            SystemSetup(context).detect_operating_system()


def test_os_release_is_data(
    context: BuildContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = tmp_path / "os-release"
    execution = tmp_path / "executed"
    release.write_text(
        f'ID=ubuntu\nVERSION_ID=24.04\nVERSION_CODENAME=noble\ntouch "{execution}"\nHOME=/nowhere\n'
    )
    monkeypatch.setenv("OS_RELEASE_FILE", str(release))
    home = os.environ["HOME"]
    SystemSetup(context).detect_operating_system()
    assert context.operating_system == "Ubuntu"
    assert not execution.exists()
    assert os.environ["HOME"] == home


@pytest.mark.parametrize(
    ("os_name", "codename", "expected"),
    [
        ("Ubuntu", "jammy", ("libjxl-dev", "libshaderc-dev", "libzix-dev")),
        ("Debian", "bookworm", ("libzix-dev",)),
        ("Ubuntu", "noble", ()),
    ],
)
def test_release_gaps(os_name: str, codename: str, expected: tuple[str, ...]) -> None:
    assert release_unavailable_packages(os_name, codename) == expected


@pytest.mark.parametrize("mode", ["normal", "absent", "ppa", "optional"])
def test_apt_calls(
    context: BuildContext,
    tmp_path: Path,
    stub: Callable[[str, str], Path],
    capfd: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    log = tmp_path / "apt.log"
    apt = stub(
        "apt",
        f"import sys, pathlib\nwith pathlib.Path({str(log)!r}).open('a') as f: f.write(' '.join(sys.argv[1:])+'\\n')\nsys.exit(1 if 'show' in sys.argv and {mode!r} in ('absent', 'optional') else 0)\n",
    )
    stub("sudo", "import os, sys\nos.execvp(sys.argv[1], sys.argv[1:])\n")
    stub("dpkg-query", "raise SystemExit(1)\n")
    context.env["PATH"] = f"{apt.parent}:/usr/bin:/bin"
    context.operating_system = "Ubuntu"
    context.release_version, context.release_codename = (
        ("22.04", "jammy") if mode in ("absent", "ppa") else ("24.04", "noble")
    )
    request = HostPackages()
    name = "libzix-dev" if mode in ("absent", "ppa") else "shellcheck"
    if mode == "absent":
        request.require(name)
        with pytest.raises(BuildError, match="Enable the 'zix' source build"):
            SystemSetup(context).install_apt_packages(request)
        assert "update" not in log.read_text()
        return
    request.add(name)
    setup = SystemSetup(context)
    setup.install_apt_packages(request)
    calls = log.read_text()
    assert "-o APT::Cmd::Disable-Script-Warning=1 update" in calls
    assert f"-o APT::Cmd::Disable-Script-Warning=1 show {name}" in calls
    if mode != "optional":
        assert f"install --assume-yes --no-install-recommends {name}" in calls
    else:
        # Use the log so logger stream capture timing cannot hide a warning.
        assert "install --assume-yes" not in calls
    assert setup.apt_index_updated


def test_pkgconf_paths_are_sanitized(context: BuildContext) -> None:
    context.env.update(
        PKG_CONFIG_PATH="/untrusted",
        PKG_CONFIG_LIBDIR="/untrusted",
        PKG_CONFIG_SYSROOT_DIR="/untrusted",
    )
    setup = SystemSetup(context)
    setup.configure_pkgconf_search_paths()
    expected = subprocess.run(
        ["/usr/bin/pkgconf", "--variable=pc_path", "pkgconf"],
        env={k: v for k, v in context.env.items() if not k.startswith("PKG_CONFIG_")},
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert context.system_pkg_config_path == expected
    assert context.env["PKG_CONFIG_PATH"] == ":".join(
        str(context.workspace / part)
        for part in (
            "lib/pkgconfig",
            "lib64/pkgconfig",
            "lib/x86_64-linux-gnu/pkgconfig",
            "share/pkgconfig",
        )
    )
    assert "PKG_CONFIG_LIBDIR" not in context.env
    assert "PKG_CONFIG_SYSROOT_DIR" not in context.env


def test_pkgconf_default_artifact_and_glob_contract(
    context: BuildContext, stub: Callable[[str, str], Path]
) -> None:
    binary = stub(
        "pkgconf",
        "import os, sys\nargs=sys.argv[1:]\nif args[0]=='--variable=pc_path': print(os.environ['FIXTURE_PC_PATH'])\nelif args[0]=='--cflags-only-I': print('* -I/opt/real/include')\nelif args[0]=='--libs-only-L': print('* -L/opt/real/lib')\nelse: sys.exit(1)\n",
    )
    context.system_pkg_config_path = "/system/one/pkgconfig:/system/two/pkgconfig"
    context.env["FIXTURE_PC_PATH"] = context.system_pkg_config_path
    assert context.pkgconf_uses_system_default_path(binary)
    context.env["FIXTURE_PC_PATH"] = (
        f"{context.workspace}/lib/pkgconfig:{context.system_pkg_config_path}"
    )
    assert not context.pkgconf_uses_system_default_path(binary)
    context.env["PATH"] = str(binary.parent)
    assert pkgconf_include_dir(context, "fixture") == "/opt/real/include"
    assert pkgconf_library_dir(context, "fixture") == "/opt/real/lib"


def test_prefixless_pkgconf_metadata(context: BuildContext, tmp_path: Path) -> None:
    pc_dir = context.workspace / "lib/pkgconfig"
    pc_dir.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    pc = "Name: fixture\nDescription: Fixture\nVersion: 1.0\nLibs: -lfixture\n"
    (pc_dir / "inside.pc").write_text(pc)
    (external / "outside.pc").write_text(pc)
    context.env["PKG_CONFIG_PATH"] = f"{external}:{pc_dir}"
    assert context.workspace_pkgconf_modules_ready("inside")
    assert not context.workspace_pkgconf_modules_ready("outside")


def test_hardware_summary(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import sys

    context.logger._out = sys.stdout
    context.nvidia_gpu_present = True
    context.amd_gpu_present = True
    hardware = HardwareDetection(context, SystemSetup(context))
    monkeypatch.setattr(hardware, "detect_gpu_vendors", lambda: None)
    hardware.run()
    output = capsys.readouterr().out
    assert " --------------------\n\n[" in output
    assert " --------------------\n\n\n" not in output
    assert "INFO  NVIDIA: NVIDIA GPU detected\n                 AMD:    AMD GPU detected" in output


def test_vulkan_host_requirements(context: BuildContext) -> None:
    context.selection = Selection({"vulkan": True}, Path("fixture.toml"))
    packages = SystemSetup(context).collect_host_packages().names
    assert {"libvulkan-dev", "glslang-tools", "spirv-headers"} <= set(packages)
