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
from ffmpeg_build.stages.ffmpeg_build import (
    ConfigureOptions,
    FFmpegStage,
    ffmpeg_installed_version,
)
from ffmpeg_build.stages.hardware import HardwareDetection
from ffmpeg_build.stages.support_libraries import install_support_libraries
from ffmpeg_build.stages.system_setup import SystemSetup


def stage_for(context: BuildContext) -> FFmpegStage:
    return FFmpegStage(context, HardwareDetection(context, SystemSetup(context)))


def test_fontconfig_repairs_a_recorded_version_using_the_current_archive_host(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    context.selection = Selection({"fontconfig": True}, Path("fixture.toml"))
    context.marker_path("fontconfig").write_text("9.8.7\n")

    def forbidden() -> None:
        pytest.fail("Repair must reuse the recorded version without a new release lookup")

    monkeypatch.setattr(context.versions, "fontconfig", forbidden)

    class ArchiveReached(Exception):
        pass

    def download(primary: str, fallback: str) -> Path:
        assert primary == (
            "https://gitlab.freedesktop.org/fontconfig/fontconfig/-/archive/9.8.7/"
            "fontconfig-9.8.7.tar.gz"
        )
        assert fallback.endswith("fontconfig-9.8.7.tar.xz")
        raise ArchiveReached

    monkeypatch.setattr(context.downloader, "download_with_fallback", download)
    with pytest.raises(ArchiveReached):
        install_support_libraries(context)


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
    assert "[SKIP] jemalloc 1.2.3 is already built." in output
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


def test_missing_artifacts_rebuild_pinned_version_without_refetch(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("zenlib", "mediainfo-lib", "ffmpeg"):
        context.marker_path(key).write_text("0.4.41\n")
    monkeypatch.setattr(context, "package_artifacts_ready", lambda key: key != "zenlib")

    def forbidden() -> str:
        pytest.fail("Repairing a pinned release must not rediscover an upstream version")

    assert context.fetch_version_if_enabled("zenlib", forbidden) == "0.4.41"
    assert context.build("zenlib", "0.4.41")
    for key in ("zenlib", "mediainfo-lib", "ffmpeg"):
        assert not context.marker_path(key).exists()


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


@pytest.mark.parametrize("gpl", [False, True])
def test_summary_explains_selected_gpl_integrations(
    context: BuildContext, capsys: pytest.CaptureFixture[str], gpl: bool
) -> None:
    from ffmpeg_build.stages.ffmpeg_build import report_success

    context.logger._out = sys.stdout
    context.logger._err = sys.stderr
    context.selection = Selection(
        {"x264": True, "libdvdread": True, "zenlib": True}, Path("fixture.toml")
    )
    context.nonfree_and_gpl = gpl
    report_success(context)
    output = capsys.readouterr()
    text = output.out + output.err
    if gpl:
        assert "integrations inactive" not in text
    else:
        notice = next(line for line in text.splitlines() if "integrations inactive" in line)
        assert "x264" in notice and "libdvdread" in notice
        assert "zenlib" not in notice


@pytest.mark.parametrize("version", [None, "", "../escape", "bad version"])
def test_invalid_build_versions(context: BuildContext, version: str | None) -> None:
    message = (
        "Unable to resolve an upstream version.*'nasm'" if version is None else "invalid version"
    )
    with pytest.raises(BuildError, match=message):
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
        assert (
            url == "https://downloads.sourceforge.net/project/giflib/giflib-5.x/giflib-5.2.2.tar.gz"
        )
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


def test_failed_installed_version_probe_is_not_accepted(
    stub: Callable[[str, str], Path],
) -> None:
    binary = stub("ffmpeg", "print('ffmpeg version 9.0.1'); raise SystemExit(1)")
    assert ffmpeg_installed_version(binary) is None


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
    assert f"FFmpeg installation verified ({prefix}/bin)" in output
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


def test_failed_backup_never_starts_install_or_rollback(
    context: BuildContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import Sequence

    prefix = tmp_path / "installed"
    (prefix / "bin").mkdir(parents=True)
    for name in ("ffmpeg", "ffprobe"):
        (prefix / "bin" / name).write_text("original")
    staging = context.packages / "staging"
    staging.mkdir()

    def fail_backup(arguments: Sequence[str], **kwargs: object) -> None:
        raise BuildError("disk full during backup")

    def forbidden(*args: object, **kwargs: object) -> int:
        pytest.fail("A backup failure must not start install or restoration")

    monkeypatch.setattr(context, "execute", fail_backup)
    monkeypatch.setattr(context.runner, "run_logged", forbidden)
    with pytest.raises(BuildError, match="disk full"):
        stage_for(context).promote_installation(tmp_path, staging, "9.0.1", False, prefix)
    assert all((prefix / "bin" / name).read_text() == "original" for name in ("ffmpeg", "ffprobe"))


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


def test_sdl2_alsa_correction_compiles_with_clang(context: BuildContext, tmp_path: Path) -> None:
    import shutil
    import subprocess

    from ffmpeg_build.stages.audio_libraries import fix_sdl2_alsa_signatures

    clang = shutil.which("clang")
    if clang is None:
        pytest.skip("Clang is needed to reproduce the SDL2 function-pointer diagnostic")
    target = tmp_path / "src/audio/alsa/SDL_alsa_audio.c"
    target.parent.mkdir(parents=True)
    target.write_text("""typedef struct info snd_pcm_info_t;
typedef struct params snd_pcm_hw_params_t;
void snd_pcm_info_free(snd_pcm_info_t *);
int snd_pcm_hw_params_get_rate(const snd_pcm_hw_params_t *, unsigned int *, int *);
static int (*ALSA_snd_pcm_info_free)(snd_pcm_info_t *);
static int (*ALSA_snd_pcm_hw_params_get_rate)(snd_pcm_hw_params_t *, unsigned int*, int*);
void load(void) {
    ALSA_snd_pcm_info_free = snd_pcm_info_free;
    ALSA_snd_pcm_hw_params_get_rate = snd_pcm_hw_params_get_rate;
}
""")
    command = [clang, "-fsyntax-only", "-Werror=incompatible-function-pointer-types", str(target)]
    assert subprocess.run(command, capture_output=True).returncode != 0
    fix_sdl2_alsa_signatures(context, tmp_path)
    corrected = target.read_text()
    compiled = subprocess.run(command, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    fix_sdl2_alsa_signatures(context, tmp_path)
    assert target.read_text() == corrected


def test_xvid_preserves_legacy_bool_and_scopes_c_dialect(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import shlex
    import shutil
    import subprocess
    from collections.abc import Sequence

    from ffmpeg_build.stages.video_libraries import _install_gpl_video

    clang = shutil.which("clang")
    if clang is None:
        pytest.skip("Clang is needed to reproduce the Xvid C23 diagnostic")
    context.selection = Selection({"xvidcore": True}, Path("fixture.toml"))
    context.env["CFLAGS"] = "-O2 -fPIC"
    original_env = context.env.copy()
    monkeypatch.setattr(context.versions, "xvidcore", lambda: "9.8.7")
    monkeypatch.setattr(context, "download", lambda *args: tmp_path)
    source = tmp_path / "legacy.c"
    source.write_text('typedef int bool;\n_Static_assert(sizeof(bool) == sizeof(int), "ABI");\n')
    command = [clang, "-std=gnu2x", "-fsyntax-only", str(source)]
    assert subprocess.run(command, capture_output=True).returncode != 0

    class Configured(Exception):
        pass

    def execute(arguments: Sequence[str], **kwargs: object) -> None:
        if list(arguments[:2]) != ["sh", "configure"]:
            return
        overrides = kwargs["env_overrides"]
        assert isinstance(overrides, dict)
        flags = overrides["CFLAGS"]
        assert flags.startswith(original_env["CFLAGS"] + " ")
        result = subprocess.run([*command, *shlex.split(flags)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert context.env == original_env
        raise Configured

    monkeypatch.setattr(context, "execute", execute)
    with pytest.raises(Configured):
        _install_gpl_video(context)


def test_lame_marker_rejects_unresolved_decoder_dependency(
    context: BuildContext, tmp_path: Path
) -> None:
    import shutil
    import subprocess

    compiler = shutil.which(context.env["CC"])
    archiver = shutil.which("ar")
    if compiler is None or archiver is None:
        pytest.skip("A C compiler and ar are needed for static archive validation")
    include = context.workspace / "include/lame"
    include.mkdir(parents=True)
    (include / "lame.h").write_text(
        "void *lame_init(void);\nint lame_set_VBR_quality(void *, float);\n"
    )
    archive = context.workspace / "lib/libmp3lame.a"
    archive.parent.mkdir()
    source, obj = tmp_path / "lame.c", tmp_path / "lame.o"

    def compile_archive(decoder: bool) -> None:
        source.write_text(
            "extern void missing_mpg123_decoder(void);\n"
            "void *lame_init(void) { "
            + ("missing_mpg123_decoder(); " if decoder else "")
            + "return 0; }\nint lame_set_VBR_quality(void *p, float q) { return 0; }\n"
        )
        subprocess.run(
            [compiler, "-c", str(source), "-o", str(obj)], check=True, capture_output=True
        )
        subprocess.run([archiver, "rcs", str(archive), str(obj)], check=True, capture_output=True)

    compile_archive(decoder=True)
    context.marker_path("liblame").write_text("4.0\n")
    context.marker_path("ffmpeg").write_text("9.0.1\n")
    assert not context.package_artifacts_ready("liblame")
    assert context.build("liblame", "4.0")
    assert not context.marker_path("liblame").exists()
    assert not context.marker_path("ffmpeg").exists()
    compile_archive(decoder=False)
    context.build_done("liblame", "4.0")
    assert not context.build("liblame", "4.0")


def test_lame_recipe_builds_encoder_without_external_decoder(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ffmpeg_build.stages.audio_libraries import install_audio_libraries

    context.selection = Selection({"liblame": True}, Path("fixture.toml"))
    monkeypatch.setattr(context.versions, "lame", lambda: "9.8.7")
    monkeypatch.setattr(context, "download", lambda *args: tmp_path)

    class Configured(Exception):
        pass

    def configure(ctx: BuildContext, source: Path, *options: str) -> None:
        assert "--disable-decoder" in options
        assert "--disable-frontend" in options
        assert "--disable-shared" in options
        raise Configured

    monkeypatch.setattr("ffmpeg_build.stages.audio_libraries.configure_make_install", configure)
    with pytest.raises(Configured):
        install_audio_libraries(context)


def test_svt_recipe_keeps_static_archive_compatible_with_host_linker(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ffmpeg_build.stages.video_libraries import install_video_libraries

    context.selection = Selection({"svt-av1": True}, Path("fixture.toml"))
    monkeypatch.setattr("ffmpeg_build.stages.video_libraries.find_git_repo", lambda *args: "9.8.7")
    monkeypatch.setattr(context, "download", lambda *args: tmp_path)

    class Configured(Exception):
        pass

    def configure(ctx: BuildContext, source: Path, build: str, *options: str) -> None:
        assert "-DSVT_AV1_LTO=OFF" in options
        assert "-DBUILD_SHARED_LIBS=OFF" in options
        raise Configured

    monkeypatch.setattr("ffmpeg_build.stages.video_libraries.cmake_ninja_install", configure)
    with pytest.raises(Configured):
        install_video_libraries(context)


def test_svt_marker_requires_a_linkable_archive_even_with_valid_metadata(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import shutil
    import subprocess

    compiler = shutil.which(context.env["CC"])
    archiver = shutil.which("ar")
    if compiler is None or archiver is None:
        pytest.skip("A C compiler and ar are needed for static archive validation")
    monkeypatch.setattr(context, "workspace_pkgconf_modules_ready", lambda *args: True)
    header = context.workspace / "include/svt-av1/EbSvtAv1Enc.h"
    header.parent.mkdir(parents=True)
    header.write_text("int svt_av1_enc_init_handle(void);\n")
    archive = context.workspace / "lib/libSvtAv1Enc.a"
    archive.parent.mkdir()
    archive.write_bytes(b"incompatible archive")
    context.marker_path("svt-av1").write_text("4.2.0\n")
    assert not context.package_artifacts_ready("svt-av1")
    assert context.build("svt-av1", "4.2.0")
    archive.unlink()
    source, obj = tmp_path / "svt.c", tmp_path / "svt.o"
    source.write_text("int svt_av1_enc_init_handle(void) { return 0; }\n")
    subprocess.run([compiler, "-c", str(source), "-o", str(obj)], check=True, capture_output=True)
    subprocess.run([archiver, "rcs", str(archive), str(obj)], check=True, capture_output=True)
    context.build_done("svt-av1", "4.2.0")
    assert not context.build("svt-av1", "4.2.0")
