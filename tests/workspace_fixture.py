"""A marker-complete workspace with real metadata and inert native artifacts."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from ffmpeg_build import registry
from ffmpeg_build.runtime.artifacts import PKGCONF_MODULES
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.stages.video_libraries import normalize_vapoursynth_sdk

COMMIT = "a" * 40
FILES = (
    "bin/m4",
    "bin/autoconf",
    "bin/automake",
    "bin/libtoolize",
    "bin/cmake",
    "bin/ninja",
    "bin/yasm",
    "bin/nasm",
    "ant/bin/ant",
    "bin/mediainfo",
    "bin/MP4Box",
    "python_virtual_environment/build-tools/bin/meson",
    "python_virtual_environment/vapoursynth/bin/python",
    "lib/libgif.a",
    "lib/libiconv.a",
    "lib/libgmp.a",
    "lib/libmp3lame.a",
    "lib/libtheoraenc.a",
    "include/CL/cl.h",
    "lib/libOpenCL.a",
    "include/vulkan/vulkan.h",
    "include/lv2.h",
    "include/AMF/core/Version.h",
    "lib/libgav1.a",
    "include/avisynth/avisynth_c.h",
    "lib/libxvidcore.a",
    "include/xvid.h",
)


def populate(context: BuildContext) -> None:
    for relative in FILES:
        path = context.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")
        path.chmod(0o755 if "/bin/" in str(path) else 0o644)
    modules = {module for names in PKGCONF_MODULES.values() for module in names}
    modules.add("glut")
    for module in modules:
        pc = context.workspace / "lib/pkgconfig" / f"{module}.pc"
        pc.parent.mkdir(parents=True, exist_ok=True)
        pc.write_text(
            f"prefix={context.workspace}\nlibdir=${{prefix}}/lib\nincludedir=${{prefix}}/include\nName: {module}\nDescription: Test fixture\nVersion: 99.0.0\nLibs: -L${{libdir}} -lfixture\nCflags: -I${{includedir}}\n"
        )
    # The actual SDK layout is exercised, including the normalization on a rerun.
    sdk = context.workspace / "lib/python3.12/site-packages/vapoursynth"
    (sdk / "include").mkdir(parents=True)
    for header in ("VSScript4.h", "VapourSynth4.h"):
        (sdk / "include" / header).write_text("fixture\n")
    (sdk / "libvsscript.so").write_text("fixture\n")
    (sdk / "libvapoursynth.so").write_text("fixture\n")
    assert normalize_vapoursynth_sdk(context)
    for key in registry.PACKAGE_NAMES:
        version = COMMIT if key.endswith("-git") or key in ("amf-headers", "x264") else "1.2.3"
        if key == "liblame":
            version = "3.100"
        if key == "vapoursynth":
            version = "R70"
        if key == "ffmpeg":
            version = "n9.0.1"
        context.marker_path(key).write_text(version + "\n")
        if version == COMMIT:
            (context.packages / key).mkdir(exist_ok=True)
    context.system_pkg_config_path = subprocess.run(
        ["/usr/bin/pkgconf", "--variable=pc_path", "pkgconf"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    # Use the host pkgconf executable and real .pc files; no success-only probe stub.
    context.env["PKG_CONFIG_PATH"] = str(context.workspace / "lib/pkgconfig")


def isolate(context: BuildContext, monkeypatch: pytest.MonkeyPatch) -> None:
    capture = context.runner.capture

    def checked_capture(
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str] | None = None,
        timeout: float | None = 30,
        stdin_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if len(arguments) >= 3 and arguments[0] == "git" and arguments[1] == "-C":
            return subprocess.CompletedProcess(list(arguments), 0, COMMIT + "\n", "")
        if arguments[0] in ("curl", "git", "sudo", "apt"):
            pytest.fail(f"Unexpected network/host command in completed workspace: {arguments}")
        return capture(
            arguments, cwd=cwd, env_overrides=env_overrides, timeout=timeout, stdin_text=stdin_text
        )

    monkeypatch.setattr(context.runner, "capture", checked_capture)
    real_artifacts = context.package_artifacts_ready

    def artifacts(key: str) -> bool:
        # pkgconf's executable is the host tool; all other artifacts are fixtures.
        if key == "pkgconf":
            return context.pkgconf_uses_system_default_path(Path("/usr/bin/pkgconf"))
        if key in ("ffmpeg", "liblame", "svt-av1"):
            # Inert archive fixtures cannot satisfy the real static link probe;
            # its broken-dependency and repair paths have compiler-backed tests.
            return True
        return real_artifacts(key)

    monkeypatch.setattr(context, "package_artifacts_ready", artifacts)

    def execute(arguments: Sequence[str], **kwargs: object) -> None:
        if list(arguments[:2]) == ["mkdir", "-p"]:
            for directory in arguments[2:]:
                Path(directory).mkdir(parents=True, exist_ok=True)
            return
        pytest.fail(f"Completed workspace attempted compilation or host mutation: {arguments}")

    monkeypatch.setattr(context, "execute", execute)
