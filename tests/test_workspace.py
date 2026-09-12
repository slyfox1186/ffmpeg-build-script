from __future__ import annotations

from pathlib import Path

import pytest

from ffmpeg_build.config import Selection, default_states
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.stages.audio_libraries import install_audio_libraries
from ffmpeg_build.stages.core_libraries import install_core_libraries
from ffmpeg_build.stages.global_tools import install_global_tools
from ffmpeg_build.stages.image_libraries import install_image_libraries
from ffmpeg_build.stages.support_libraries import install_support_libraries
from ffmpeg_build.stages.video_libraries import install_video_libraries
from tests.workspace_fixture import isolate, populate

STAGES = (
    install_global_tools,
    install_core_libraries,
    install_support_libraries,
    install_audio_libraries,
    install_video_libraries,
    install_image_libraries,
)


@pytest.mark.parametrize("gpl", [False, True])
@pytest.mark.parametrize("preset", ["all", "template", "none"])
def test_completed_workspace_runs_all_dependency_stages(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, gpl: bool, preset: str
) -> None:
    if preset != "all":
        context.selection = Selection(
            default_states() if preset == "template" else {}, Path("fixture.toml")
        )
    context.nonfree_and_gpl = gpl
    populate(context)
    isolate(context, monkeypatch)
    for stage in STAGES:
        stage(context)
    assert context.packages_built == 0
    if preset != "none":
        assert context.packages_already_built > 40
        assert (
            str(context.workspace / "python_virtual_environment/build-tools/bin")
            in context.env["PATH"]
        )
        vmaf = (context.workspace / "lib/pkgconfig/libvmaf.pc").read_text()
        assert vmaf.count("-lstdc++") == 1
        if context.package_enabled("ant-git"):
            assert str(context.workspace / "ant/bin") in context.env["PATH"]
        assert (context.workspace / "lib/libvapoursynth-script.so").exists()
        assert (
            str(context.workspace / "python_virtual_environment/vapoursynth/bin")
            in context.env["PATH"]
        )
    flags = context.configure_options
    if preset == "none":
        assert flags == []
        assert "python_virtual_environment/vapoursynth" not in context.env["PATH"]
        assert "PYTHON" not in context.env
    else:
        assert ("--enable-libx264" in flags) == (gpl and context.package_enabled("x264"))
        assert ("--enable-openssl" in flags) == (gpl and context.package_enabled("openssl"))
        assert ("--enable-gnutls" in flags) == (
            context.package_enabled("gnutls") and not (gpl and context.package_enabled("openssl"))
        )


@pytest.mark.parametrize("compiler", ["gcc", "clang"])
@pytest.mark.parametrize("gpl", [False, True])
@pytest.mark.parametrize("preset", ["all", "template", "none"])
def test_host_packages_match_bash_baseline(
    context: BuildContext, compiler: str, gpl: bool, preset: str
) -> None:
    import json

    from ffmpeg_build.stages.system_setup import SystemSetup

    fixtures = json.loads((Path(__file__).parent / "fixtures/host-packages.json").read_text())
    context.compiler = compiler
    context.nonfree_and_gpl = gpl
    if preset != "all":
        context.selection = Selection(
            default_states() if preset == "template" else {}, Path("fixture.toml")
        )
    assert (
        sorted(SystemSetup(context).collect_host_packages().names)
        == fixtures[f"{compiler}-{str(gpl).lower()}-{preset}"]
    )


class Configured(Exception):
    pass


@pytest.mark.parametrize("preset", ["all", "template"])
@pytest.mark.parametrize("gpl", [False, True])
@pytest.mark.parametrize("gpu", [False, True])
def test_ordered_configure_matches_bash_baseline(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, preset: str, gpl: bool, gpu: bool
) -> None:
    import json
    import subprocess
    from collections.abc import Sequence

    from tests.test_build_stages import stage_for

    fixtures = json.loads((Path(__file__).parent / "fixtures/configure-options.json").read_text())
    expected = fixtures[f"{preset}-{str(gpl).lower()}-{str(gpu).lower()}"]
    if preset == "template" and gpl and gpu:
        # Explicit user-requested departure from the historical Bash template:
        # AMF headers now default on, retaining the existing GPL/AMD gates.
        for name in ("stage_flags", "configure"):
            expected[name].insert(expected[name].index("--enable-libsvtav1"), "--enable-amf")
    if preset == "template":
        context.selection = Selection(default_states(), Path("fixture.toml"))
    context.nonfree_and_gpl = gpl
    context.nvidia_gpu_present = gpu
    context.amd_gpu_present = gpu
    if gpl:
        context.configure_options.extend(["--enable-gpl", "--enable-nonfree"])
    populate(context)
    isolate(context, monkeypatch)
    for stage in STAGES:
        stage(context)
    assert context.configure_options == expected["stage_flags"]
    source = context.packages / "ffmpeg-source"
    source.mkdir()
    monkeypatch.setattr(context, "download", lambda *args: source)
    monkeypatch.setattr(context, "library_exists", lambda *args: True)
    monkeypatch.setattr(context, "header_exists", lambda *args: True)
    monkeypatch.setattr(context, "compile_probe", lambda *args: True)
    monkeypatch.setattr(
        context.runner,
        "which",
        lambda name: "/usr/bin/glslangValidator" if name == "glslangValidator" else None,
    )
    monkeypatch.setattr(
        context.runner,
        "capture",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "--glslc=GLSLC", ""),
    )
    final: list[str] = []

    def capture(arguments: Sequence[str], **kwargs: object) -> None:
        assert arguments[0] == str(source / "configure")
        assert kwargs["cwd"] == source / "build"
        final.extend(arguments[1:])
        raise Configured

    monkeypatch.setattr(context, "execute", capture)
    with pytest.raises(Configured):
        stage_for(context)._configure_build_install("1.2.3", True)
    assert [option.replace(str(context.cwd), "<BUILD_ROOT>") for option in final] == expected[
        "configure"
    ]


def test_orchestrator_completed_workspace(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib
    import os
    from collections.abc import Callable

    from ffmpeg_build.main import Orchestrator
    from ffmpeg_build.runtime.state import write_build_root_marker
    from ffmpeg_build.stages.ffmpeg_build import FFmpegStage
    from ffmpeg_build.stages.hardware import HardwareDetection
    from ffmpeg_build.stages.system_setup import SystemSetup

    access = os.access
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: (
            True
            if str(path)
            in ("/usr/local/bin/ffmpeg", "/usr/local/bin/ffprobe", "/usr/local/bin/ffplay")
            else access(path, mode)
        ),
    )
    populate(context)
    isolate(context, monkeypatch)
    write_build_root_marker(context.cwd)
    orchestrator = Orchestrator(context.repo_root, [])
    orchestrator.build_root = context.cwd
    orchestrator.context = context
    events: list[str] = []
    monkeypatch.setattr(orchestrator, "ensure_build_context", lambda ctx: events.append("context"))
    monkeypatch.setattr(orchestrator.runner, "require_sudo", lambda: events.append("sudo"))
    monkeypatch.setattr(SystemSetup, "run", lambda setup: events.append("system"))
    monkeypatch.setattr(HardwareDetection, "run", lambda hardware: events.append("hardware"))
    monkeypatch.setattr(HardwareDetection, "install_cuda", lambda hardware: events.append("cuda"))
    monkeypatch.setattr(
        "ffmpeg_build.stages.ffmpeg_build.ffmpeg_installed_version", lambda: "9.0.1"
    )
    monkeypatch.setattr(
        FFmpegStage, "validate_installation", lambda *args: events.append("validated")
    )
    monkeypatch.setattr("ffmpeg_build.main.report_success", lambda ctx: events.append("success"))

    def record_stage(stage: Callable[[BuildContext], None]) -> Callable[[BuildContext], None]:
        def run(ctx: BuildContext) -> None:
            events.append(stage.__name__)
            stage(ctx)

        return run

    for stage in STAGES:
        monkeypatch.setattr(
            importlib.import_module(stage.__module__), stage.__name__, record_stage(stage)
        )
    try:
        orchestrator.run_build(context)
        assert events == [
            "context",
            "sudo",
            "system",
            "hardware",
            "cuda",
            *[stage.__name__ for stage in STAGES],
            "validated",
            "success",
        ]
        assert context.packages_built == 0
    finally:
        orchestrator.teardown()
