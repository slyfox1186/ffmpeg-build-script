from __future__ import annotations

import io
import json
import os
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path

import pytest

from ffmpeg_build.runtime.context import BuildContext
from ffmpeg_build.runtime.download import archive_checksum_matches, write_archive_checksum
from ffmpeg_build.runtime.errors import BuildError


def archive_at(path: Path, entries: list[tuple[str, bytes | str, bytes]]) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                assert isinstance(payload, str)
                info.linkname = payload
                archive.addfile(info)
            else:
                assert isinstance(payload, bytes)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
    return path


@pytest.mark.parametrize("root", ["project", "source"])
def test_valid_download_cache_extract(context: BuildContext, root: str) -> None:
    archive = archive_at(
        context.packages / "project.tar.gz",
        [(f"{root}/sub/file.txt", b"payload\n", tarfile.REGTYPE)],
    )
    downloader = context.downloader
    assert downloader.validate_tar_archive(archive)
    assert write_archive_checksum(archive)
    assert archive_checksum_matches(archive)
    assert downloader.extract_transactionally(archive, context.packages / "project")
    assert (context.packages / "project/sub/file.txt").read_text() == "payload\n"
    with archive.open("ab") as stream:
        stream.write(b"tamper\n")
    assert not archive_checksum_matches(archive)


@pytest.mark.parametrize(
    ("name", "payload", "kind"),
    [
        ("project/escape", "../../outside", tarfile.SYMTYPE),
        ("project/escape", "/etc/passwd", tarfile.SYMTYPE),
        ("project/empty-link", "", tarfile.SYMTYPE),
        ("project/escape", "../../outside", tarfile.LNKTYPE),
        ("project/fifo", b"", tarfile.FIFOTYPE),
        ("project/device", b"", tarfile.CHRTYPE),
        ("project/../../outside", b"bad", tarfile.REGTYPE),
        ("/project/file", b"bad", tarfile.REGTYPE),
        ("project/bad\nname", b"bad", tarfile.REGTYPE),
    ],
)
def test_unsafe_archives_not_published(
    context: BuildContext, name: str, payload: bytes | str, kind: bytes
) -> None:
    archive = archive_at(context.packages / "unsafe.tar.gz", [(name, payload, kind)])
    assert not context.downloader.validate_tar_archive(archive)
    target = context.packages / "target"
    target.mkdir()
    (target / "old").write_text("preserve")
    assert not context.downloader.extract_transactionally(archive, target)
    assert (target / "old").read_text() == "preserve"
    assert not list(context.packages.glob(".extract.*"))


@pytest.mark.parametrize("names", [["a/file", "b/file"], ["root"], []])
def test_archive_shape(context: BuildContext, names: list[str]) -> None:
    archive = archive_at(
        context.packages / "bad.tar.gz", [(name, b"x", tarfile.REGTYPE) for name in names]
    )
    assert not context.downloader.validate_tar_archive(archive)
    assert not context.downloader.extract_transactionally(archive, context.packages / "output")


def test_https_refused_before_network(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> int:
        pytest.fail("An HTTP URL must never reach curl")

    monkeypatch.setattr(context.runner, "run_logged", forbidden)
    with pytest.raises(BuildError, match="Only HTTPS download URLs are accepted"):
        context.downloader.download("http://example.test/project.tar.gz")


@pytest.mark.parametrize("mode", ["valid", "html", "http_error", "oversized"])
@pytest.mark.parametrize(
    "host", ["example.test", "code.videolan.org", "sourceforge.net", "downloads.sourceforge.net"]
)
def test_curl_transfer_contract(
    context: BuildContext,
    stub: Callable[[str, str], Path],
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    mode: str,
    host: str,
) -> None:
    archive = archive_at(
        tmp_path / "fixture.tar.gz", [("project/file", b"payload", tarfile.REGTYPE)]
    )
    invocation = tmp_path / "curl.json"
    source = f"""import json, pathlib, shutil, sys
args = sys.argv[1:]
pathlib.Path({str(invocation)!r}).write_text(json.dumps(args))
output = pathlib.Path(args[args.index('--output') + 1])
mode = {mode!r}
if mode == 'http_error':
    print('curl: (22) The requested URL returned error: 503', file=sys.stderr)
    print('HTTP 503; content-type: text/html; bytes: 0; URL: https://example.test/source')
    sys.exit(22)
if mode == 'html':
    output.write_text('<html>Verify your browser</html>')
    print('HTTP 200; content-type: text/html; bytes: 32; URL: https://example.test/source')
else:
    shutil.copyfile({str(archive)!r}, output)
"""
    curl = stub("curl", source)
    context.env["PATH"] = f"{curl.parent}:/usr/bin:/bin"
    context.logger._out = sys.stdout
    context.logger._err = sys.stderr
    context.runner.log_file = context.log_file
    context.logger.log_file = context.log_file
    if mode == "oversized":
        context.downloader.settings.max_bytes = 1
    target = context.packages / "download.tar.gz"
    success = context.downloader._download_to_cache(f"https://{host}/source", target.name, target)
    assert success == (mode == "valid")
    arguments = json.loads(invocation.read_text())
    assert "--user-agent" not in arguments
    assert arguments[arguments.index("--proto") + 1] == "=https"
    assert arguments[arguments.index("--proto-redir") + 1] == "=https"
    assert "--max-filesize" in arguments
    if mode == "valid":
        assert archive_checksum_matches(target)
    else:
        assert not target.exists()
        assert not Path(f"{target}.sha256").exists()
        output = "".join(capfd.readouterr())
        log = context.log_file.read_text()
        if mode in ("html", "http_error"):
            assert "content-type: text/html" in log
            diagnostic = "Unable to list tar archive" if mode == "html" else "error: 503"
            assert diagnostic in output and diagnostic in log
    assert not list(context.packages.glob(".*.part.*"))


def test_cache_hit_needs_no_transfer(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = archive_at(
        context.packages / "project.tar.gz", [("project/file", b"payload", tarfile.REGTYPE)]
    )
    assert write_archive_checksum(archive)

    def forbidden(*args: object, **kwargs: object) -> int:
        pytest.fail("A valid checksum-bound cache entry needs no network")

    monkeypatch.setattr(context.runner, "run_logged", forbidden)
    result = context.downloader.download("https://example.test/project.tar.gz")
    assert (result / "file").read_bytes() == b"payload"


def test_checksum_records_reject_extra_lines_and_hardlinks(context: BuildContext) -> None:
    archive = archive_at(
        context.packages / "project.tar.gz", [("project/file", b"payload", tarfile.REGTYPE)]
    )
    assert write_archive_checksum(archive)
    record = Path(f"{archive}.sha256")
    record.write_text(record.read_text() + "extra\n")
    assert not archive_checksum_matches(archive)
    assert write_archive_checksum(archive)
    (context.packages / "alias").hardlink_to(record)
    assert not archive_checksum_matches(archive)


@pytest.mark.parametrize("limit", ["max_bytes", "max_extracted_bytes", "max_members"])
def test_archive_resource_limits_preserve_existing_source(
    context: BuildContext, limit: str
) -> None:
    archive = archive_at(
        context.packages / "bomb.tar.gz",
        [
            ("project/data", b"x" * 4096, tarfile.REGTYPE),
            ("project/copy", "project/data", tarfile.LNKTYPE),
        ],
    )
    target = context.packages / "project"
    target.mkdir()
    (target / "keep").write_text("old source")
    setattr(context.downloader.settings, limit, 1 if limit != "max_extracted_bytes" else 4096)
    assert not context.downloader.extract_transactionally(archive, target)
    assert (target / "keep").read_text() == "old source"


def test_interrupt_after_old_source_rename_retains_recovery(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = archive_at(
        context.packages / "project.tar.gz", [("project/new", b"new", tarfile.REGTYPE)]
    )
    target = context.packages / "project"
    target.mkdir()
    (target / "keep").write_text("old source")
    rename = os.rename

    def interrupt(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        rename(source, destination)
        if Path(destination).name == ".previous-source":
            raise KeyboardInterrupt

    monkeypatch.setattr(os, "rename", interrupt)
    with pytest.raises(KeyboardInterrupt):
        context.downloader.extract_transactionally(archive, target)
    context.remove_registered_temporary_paths()
    recovered = list(context.packages.glob(".extract.*/.previous-source/keep"))
    assert len(recovered) == 1 and recovered[0].read_text() == "old source"


def test_failed_source_publication_restores_previous_tree(
    context: BuildContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = archive_at(
        context.packages / "project.tar.gz", [("project/new", b"new", tarfile.REGTYPE)]
    )
    target = context.packages / "project"
    target.mkdir()
    (target / "keep").write_text("old source")
    rename = os.rename

    def fail_publish(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        if Path(source).name == "project" and Path(source).parent.name.startswith(".extract."):
            raise OSError("simulated publication failure")
        rename(source, destination)

    monkeypatch.setattr(os, "rename", fail_publish)
    assert not context.downloader.extract_transactionally(archive, target)
    assert (target / "keep").read_text() == "old source"
    assert not list(context.packages.glob(".extract.*"))
