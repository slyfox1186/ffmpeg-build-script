from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from ffmpeg_build.config import Selection
from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.errors import BuildError
from ffmpeg_build.runtime.state import read_marker_version
from ffmpeg_build.stages.core_libraries import install_core_libraries
from ffmpeg_build.stages.ffmpeg_build import ConfigureOptions, FFmpegStage
from ffmpeg_build.stages.hardware import HardwareDetection
from ffmpeg_build.stages.system_setup import SystemSetup


def stage_for(context: BuildContext) -> FFmpegStage:
    return FFmpegStage(context, HardwareDetection(context, SystemSetup(context)))


def test_build_markers_and_messages(
    context: BuildContext, capsys: pytest.CaptureFixture[str]
) -> None:
    context.logger._out = sys.stdout
    pc = context.workspace / "lib/pkgconfig/jemalloc.pc"
    pc.parent.mkdir(parents=True)
    pc.write_text(
        f"prefix={context.workspace}\nName: jemalloc\nDescription: test-only jemalloc artifact\nVersion: 1.2.3\nLibs: -ljemalloc\n"
    )
    context.env["PKG_CONFIG_PATH"] = str(pc.parent)
    context.build_done("jemalloc", "1.2.3")
    assert read_marker_version(context.marker_path("jemalloc")) == "1.2.3"
    capsys.readouterr()
    assert not context.build("jemalloc", "1.2.3")
    output = capsys.readouterr().out
    assert "SKIP  jemalloc 1.2.3 is already built." in output
    for unexpected in ("STEP", "rm -f", "lockfile"):
        assert unexpected not in output
    context.logger.debug_enabled = True
    assert not context.build("jemalloc", "1.2.3")
    assert (
        f"Force a rebuild with: rm -f -- {context.packages}/jemalloc.done"
        in capsys.readouterr().out
    )
    context.marker_path("jemalloc").write_text("1.2.2\n")
    assert not context.build("jemalloc", "1.2.3")
    output = capsys.readouterr().out
    assert "jemalloc 1.2.2 -> 1.2.3 is outdated; keeping the existing build." in output
    assert f"Rebuild with '--latest', or: rm -f -- {context.packages}/jemalloc.done" in output
    context.latest = True
    assert context.build("jemalloc", "1.2.3")
    context.latest = False
    pc.unlink()
    assert context.build("jemalloc", "1.2.3")
    assert not context.marker_path("jemalloc").exists()
    with pytest.raises(BuildError, match="required artifacts are missing"):
        context.build_done("jemalloc", "1.2.3")


def test_failed_upgrade_invalidates_consumer_markers_before_writes(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A version marker cannot certify artifacts modified by a failed install.
    for key in ("zenlib", "mediainfo-lib", "mediainfo-cli", "ffmpeg", "nasm"):
        context.marker_path(key).write_text("1.0\n")
    monkeypatch.setattr(context, "package_artifacts_ready", lambda key: True)
    context.latest = True
    assert context.build("zenlib", "2.0")
    for key in ("zenlib", "mediainfo-lib", "mediainfo-cli", "ffmpeg"):
        assert not context.marker_path(key).exists()
    assert context.marker_path("nasm").exists()
    # Model interruption before build_done: a normal resume must retry even
    # when a .pc file still exists from a partly overwritten installation.
    context.latest = False
    assert context.build("zenlib", "2.0")
    context.build_done("zenlib", "2.0")
    assert context.build("ffmpeg", "1.0")


def test_dependency_only_success_does_not_probe_system_ffmpeg(
    context: BuildContext, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from ffmpeg_build.stages.ffmpeg_build import report_success

    context.logger._out = sys.stdout
    context.selection = Selection({"zenlib": True}, Path("fixture.toml"))

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("A dependencies-only summary probed an unrelated installed program")

    monkeypatch.setattr("ffmpeg_build.stages.ffmpeg_build.os.access", forbidden)
    report_success(context)
    assert "Dependency build completed successfully" in capsys.readouterr().out


@pytest.mark.parametrize("version", [None, "", "../escape", "bad version"])
def test_invalid_build_versions(context: BuildContext, version: str | None) -> None:
    with pytest.raises(BuildError, match="invalid version"):
        context.build("nasm", version)
    context.selection = Selection({}, Path("fixture.toml"))
    assert not context.build("nasm", version)


@pytest.mark.parametrize("mode", ["lookup", "partial", "invalid", "unavailable"])
def test_nasm_discovery(
    context: BuildContext,
    stub: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    script = f"""import sys
assert sys.argv[-1] == "https://www.nasm.us/pub/nasm/releasebuilds/"
mode={mode!r}
if mode=="partial":
 print('<a href="99.0/">99.0/</a>'); sys.exit(18)
if mode=="unavailable":
 print('curl: (22) The requested URL returned error: 404', file=sys.stderr); sys.exit(22)
print('<a href="4.0rc1/">rc</a><a href="4.0-20260819/">snapshot</a>')
if mode=="lookup":
 print('<a href="3.9/">3.9/</a><a href="3.10/">3.10/</a><a href="3.10.2/">3.10.2/</a><a href="/elsewhere/99.0/">other</a>')
"""
    binary = stub("curl", script)
    context.env["PATH"] = str(binary.parent)
    context.logger._err = sys.stderr
    version = context.versions.nasm()
    assert version == ("3.10.2" if mode == "lookup" else None)
    if mode != "lookup":
        assert "WARN" in capsys.readouterr().err


class ReachedGiflib(Exception):
    pass


@pytest.mark.parametrize("mode", ["latest", "resume", "disabled", "unavailable"])
def test_core_stage_continues_after_nasm(
    context: BuildContext,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    context.logger._out = sys.stdout
    context.selection = Selection(
        {"yasm": True, "nasm": mode != "disabled", "giflib": True}, Path("fixture.toml")
    )
    context.latest = mode in ("latest", "unavailable")
    for name, version in (("yasm", "1.3.0"), ("nasm", "3.10.2")):
        context.marker_path(name).write_text(version + "\n")
        binary = context.workspace / "bin" / name
        binary.parent.mkdir(exist_ok=True)
        binary.write_text("fixture")
        binary.chmod(0o755)
    monkeypatch.setattr("ffmpeg_build.stages.core_libraries.find_git_repo", lambda *args: "1.3.0")
    monkeypatch.setattr(context.versions, "giflib", lambda: "5.2.2")

    def nasm() -> str | None:
        if mode in ("resume", "disabled"):
            pytest.fail("Unexpected NASM network lookup")
        return None if mode == "unavailable" else "3.10.2"

    monkeypatch.setattr(context.versions, "nasm", nasm)

    def download(url: str, filename: str | None = None) -> Path:
        assert "giflib-5.2.2.tar.gz/download" in url
        raise ReachedGiflib

    monkeypatch.setattr(context, "download", download)
    if mode == "unavailable":
        with pytest.raises(BuildError, match="Failed to detect the NASM version"):
            install_core_libraries(context)
    else:
        with pytest.raises(ReachedGiflib):
            install_core_libraries(context)
    assert "yasm 1.3.0 is already built." in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["current", "legacy", "missing", "unknown"])
def test_vulkan_shader_interface(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    context.selection = Selection({"libshaderc": True}, Path("fixture.toml"))
    monkeypatch.setattr(
        context.runner,
        "which",
        lambda tool: (
            "/fixture/bin/glslangValidator"
            if tool == "glslangValidator" and mode != "missing"
            else None
        ),
    )
    monkeypatch.setattr(context, "library_exists", lambda *modules: True)
    help_text = (
        "--glslc=GLSLC"
        if mode in ("current", "missing")
        else "--enable-libshaderc"
        if mode == "legacy"
        else "--enable-vulkan"
    )
    options: list[str] = []
    stage = stage_for(context)
    if mode in ("missing", "unknown"):
        with pytest.raises(BuildError) as caught:
            stage.append_shader_options(options, help_text)
        assert (
            "neither glslangValidator, glslang nor glslc is available"
            if mode == "missing"
            else "Vulkan shader integration needs review"
        ) in str(caught.value)
    else:
        stage.append_shader_options(options, help_text)
        assert options == (
            ["--glslc=/fixture/bin/glslangValidator"]
            if mode == "current"
            else ["--enable-libshaderc"]
        )
        if mode == "current":
            assert "Vulkan scale filter" in context.required_symbols["CONFIG_SCALE_VULKAN_FILTER"]


def test_required_features_are_verified(context: BuildContext, tmp_path: Path) -> None:
    context.required_symbols["CONFIG_SCALE_VULKAN_FILTER"] = "Vulkan shader support"
    config = tmp_path / "config.mak"
    config.write_text("CONFIG_SCALE_VULKAN_FILTER=yes\n")
    stage_for(context).validate_required_features(config)
    config.write_text("")
    with pytest.raises(BuildError, match="Vulkan shader support"):
        stage_for(context).validate_required_features(config)


def test_configure_options_preserve_order() -> None:
    options = ConfigureOptions()
    options.add("--enable-a", "--enable-b", "--enable-a", "", "--disable-a")
    assert options.options == ["--enable-a", "--enable-b", "--disable-a"]


def test_installation_validation(
    context: BuildContext,
    stub: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONDA_BUILD_SYSROOT", "/unrelated/environment")
    context.logger._out = sys.stdout
    for program in ("ffmpeg", "ffprobe", "ffplay"):
        binary = stub(
            program,
            f"""import os, sys
assert "CONDA_BUILD_SYSROOT" not in os.environ
if sys.argv[2] == '-version':
 print({program!r} + ' version 8.1.2 Copyright test fixture')
 print('configuration: --fake-' + {program!r})
elif sys.argv[2] == '-encoders': print('Encoders:\\n V..... test_encoder')
elif sys.argv[2] == '-decoders': print('Decoders:\\n V..... test_decoder')
else: sys.exit(64)
""",
        )
    prefix = binary.parent.parent
    stage = stage_for(context)
    stage.validate_installation("8.1.2", True, prefix)
    output = capsys.readouterr().out
    log = context.log_file.read_text()
    assert f"FFmpeg installation verified ({prefix}/bin):" in output
    for program in ("ffmpeg", "ffprobe", "ffplay"):
        assert f"{program} version 8.1.2 Copyright test fixture" in output
        command = f"$ {prefix}/bin/{program} -hide_banner -version"
        assert command not in output
        assert command in log
        assert f"configuration: --fake-{program}" in log
    probe = prefix / "bin/ffprobe"
    probe.write_text(probe.read_text().replace("8.1.2", "8.1.1"))
    with pytest.raises(BuildError, match="version"):
        stage.validate_installation("8.1.2", True, prefix, False)


@pytest.mark.parametrize(
    "failure", ["install", "validation", "restore", "restore-error", "interrupt"]
)
def test_install_promotion_restores_and_preserves_recovery(
    context: BuildContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    import shutil
    from collections.abc import Sequence

    stage = stage_for(context)
    prefix = tmp_path / "installed"
    (prefix / "bin").mkdir(parents=True)
    for name in ("ffmpeg", "ffprobe"):
        (prefix / "bin" / name).write_text("old-" + name)
    staging = context.packages / ".ffmpeg-install-test"
    staging.mkdir()
    context.register_temporary_path(staging)

    def execute(arguments: Sequence[str], **kwargs: object) -> None:
        assert list(arguments[:3]) == ["cp", "-a", "--"]
        shutil.copy2(arguments[-2], arguments[-1])

    monkeypatch.setattr(context, "execute", execute)

    def run_logged(arguments: Sequence[str], **kwargs: object) -> int:
        if arguments[:3] == ["sudo", "make", "install"]:
            for name in ("ffmpeg", "ffprobe", "ffplay"):
                (prefix / "bin" / name).write_text("new-" + name)
            if failure == "interrupt":
                raise KeyboardInterrupt
            return 0 if failure == "validation" else 37
        if failure == "restore":
            return 74
        if failure == "restore-error" and arguments[-1].endswith("/ffmpeg"):
            raise BuildError("Output recording failed during restore")
        if arguments[1] == "cp":
            shutil.copy2(arguments[-2], arguments[-1])
        elif arguments[1] == "rm":
            Path(arguments[-1]).unlink(missing_ok=True)
        else:
            pytest.fail(f"Unexpected recovery command: {arguments}")
        return 0

    monkeypatch.setattr(context.runner, "run_logged", run_logged)

    def invalid(*args: object) -> None:
        raise BuildError("Installed validation failed")

    monkeypatch.setattr(stage, "validate_installation", invalid)
    if failure == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            stage.promote_installation(tmp_path, staging, "9.0.1", True, prefix)
    else:
        with pytest.raises(BuildError) as caught:
            stage.promote_installation(tmp_path, staging, "9.0.1", True, prefix)
        assert (
            "Restoration was incomplete"
            if failure in ("restore", "restore-error")
            else "previously installed programs were restored"
        ) in str(caught.value)
    context.remove_registered_temporary_paths()
    assert (staging / "previous-install/ffmpeg").read_text() == "old-ffmpeg"
    if failure not in ("restore", "restore-error"):
        assert (prefix / "bin/ffmpeg").read_text() == "old-ffmpeg"
        assert (prefix / "bin/ffprobe").read_text() == "old-ffprobe"
        assert not (prefix / "bin/ffplay").exists()
    if failure == "restore-error":
        assert (prefix / "bin/ffprobe").read_text() == "old-ffprobe"
        assert not (prefix / "bin/ffplay").exists()


def test_promotion_waits_before_backup_or_install(
    context: BuildContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ffmpeg_build.runtime.paths import DirectoryLock

    monkeypatch.setenv("HOST_MUTATION_LOCK_TIMEOUT", "0")
    stage = stage_for(context)
    staging = context.packages / "staging"
    with DirectoryLock(tmp_path) as held:
        assert held.acquire()
        with pytest.raises(BuildError, match="Timed out waiting to install"):
            stage.promote_installation(tmp_path, staging, "9.0.1", False, tmp_path)
    assert not staging.exists()
