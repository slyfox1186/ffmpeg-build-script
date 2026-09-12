"""HTTPS-only archive fetching, verification, and transactional extraction.

Downloads still go through `curl` rather than `urllib`. That is deliberate:
`--proto '=https' --proto-redir '=https'` pins the scheme across redirects,
`--max-filesize` bounds the transfer before it lands, and the `--write-out`
line keeps the HTTP status and content type in the build log, which is what
makes an HTML "verify your browser" page diagnosable instead of a mysterious
tar error. Retrieval commands share the project-selected HTTP user agent;
successful HTTP responses still require archive validation.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import posixpath
import re
import tarfile
import tempfile
from collections.abc import Callable, Iterator
from enum import Enum, auto
from pathlib import Path

from . import shellquote
from .errors import BuildError
from .exec import Runner
from .logging import Logger
from .paths import (
    DirectoryLock,
    canonicalize,
    is_exclusive_regular_file,
    path_is_within,
    safe_remove_tree,
)
from .state import publish_atomically

SUPPORTED_ARCHIVE_SUFFIXES = (".tar", ".tar.bz2", ".tar.gz", ".tar.xz")
_ARCHIVE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DownloadSettings:
    """Transfer limits, overridable from the environment and validated once."""

    def __init__(self, environment: dict[str, str] | None = None) -> None:
        source = environment if environment is not None else dict(os.environ)

        def positive(name: str, default: int) -> int:
            value = source.get(name, "")
            return int(value) if value else default

        self.connect_timeout = positive("DOWNLOAD_CONNECT_TIMEOUT", 5)
        self.max_time = positive("DOWNLOAD_MAX_TIME", 1800)
        self.max_bytes = positive("DOWNLOAD_MAX_BYTES", 1073741824)
        self.max_extracted_bytes = positive("DOWNLOAD_MAX_EXTRACTED_BYTES", 8 * 1024**3)
        self.max_members = positive("DOWNLOAD_MAX_MEMBERS", 100000)
        self.retry = positive("DOWNLOAD_RETRY", 5)
        self.retry_delay = positive("DOWNLOAD_RETRY_DELAY", 5)
        self.lock_timeout = positive("DOWNLOAD_LOCK_TIMEOUT", 1800)

    def replace(self, **overrides: int) -> DownloadSettings:
        clone = DownloadSettings({})
        clone.__dict__.update(self.__dict__)
        clone.__dict__.update(overrides)
        return clone


def archive_output_directory(filename: str) -> str:
    for suffix in (".tar.bz2", ".tar.gz", ".tar.xz"):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    if filename.endswith(".tar"):
        return filename[: -len(".tar")]
    raise BuildError(f"Unable to derive extraction directory from '{filename}'.")


def file_sha256(path: Path) -> str | None:
    if not is_exclusive_regular_file(path):
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def archive_checksum_matches(archive: Path, checksum_file: Path | None = None) -> bool:
    """Detect cache damage between runs using the locally recorded digest."""
    record = checksum_file if checksum_file is not None else Path(f"{archive}.sha256")
    if not is_exclusive_regular_file(archive) or not is_exclusive_regular_file(record):
        return False
    try:
        lines = record.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    if len(lines) != 1 or not _SHA256.match(lines[0]):
        return False
    return file_sha256(archive) == lines[0]


def write_archive_checksum(archive: Path, checksum_file: Path | None = None) -> bool:
    record = checksum_file if checksum_file is not None else Path(f"{archive}.sha256")
    checksum = file_sha256(archive)
    if checksum is None:
        return False
    try:
        publish_atomically(record, f"{checksum}\n")
    except (OSError, BuildError):
        return False
    return True


def _has_control_characters(text: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in text)


class ExtractionResult(Enum):
    SUCCESS = auto()
    INVALID_ARCHIVE = auto()
    LOCAL_FAILURE = auto()


class Downloader:
    """Fetches, verifies, and extracts one package source archive."""

    def __init__(
        self,
        *,
        runner: Runner,
        logger: Logger,
        packages: Path,
        settings: DownloadSettings,
        register_temporary: Callable[[Path], None] | None = None,
        unregister_temporary: Callable[[Path], None] | None = None,
        build_root_locked: bool = False,
    ) -> None:
        self.runner = runner
        self.logger = logger
        self.packages = packages
        self.settings = settings
        self._register = register_temporary or (lambda _path: None)
        self._unregister = unregister_temporary or (lambda _path: None)
        self.build_root_locked = build_root_locked

    @contextlib.contextmanager
    def temporary_settings(self, **overrides: int) -> Iterator[None]:
        """Tighten transfer limits for one recipe.

        The font packages try two mirrors in sequence, so the first attempt has
        to give up quickly; waiting out the default half-hour timeout on a
        mirror that is simply down would stall the build for no benefit.
        """
        previous = self.settings
        self.settings = previous.replace(**overrides)
        try:
            yield
        finally:
            self.settings = previous

    # -- validation ------------------------------------------------------

    def validate_tar_archive(self, archive: Path) -> bool:
        """Check every member before anything is written to disk.

        `tarfile`'s `data` filter rejects absolute paths, parent traversal,
        escaping links and special files during extraction, but it does not
        enforce the single-root rule or the "has payload below the root" rule
        that stripping one component depends on, so those stay explicit here.
        """
        if not is_exclusive_regular_file(archive):
            return False
        try:
            if archive.stat().st_size > self.settings.max_bytes:
                self.logger.warn(f"Archive '{archive}' exceeds the configured transfer size limit.")
                return False
            names: list[str] = []
            sizes: dict[str, int] = {}
            expanded_bytes = 0
            with tarfile.open(archive) as bundle:
                for member in bundle:
                    if len(names) >= self.settings.max_members:
                        self.logger.warn(
                            f"Archive '{archive}' exceeds the configured member limit."
                        )
                        return False
                    name = member.name.removeprefix("./")
                    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                        self.logger.warn(
                            f"Archive '{archive}' contains a special filesystem object."
                        )
                        return False
                    if member.issym() or member.islnk():
                        link = member.linkname
                        target = posixpath.normpath(
                            posixpath.join(posixpath.dirname(name), link)
                            if member.issym()
                            else link
                        )
                        root = name.split("/", 1)[0]
                        if (
                            not link
                            or _has_control_characters(link)
                            or link.startswith("/")
                            or not (target == root or target.startswith(root + "/"))
                        ):
                            self.logger.warn(f"Archive '{archive}' contains an unsafe link target.")
                            return False
                    size = member.size
                    if member.islnk():
                        # Charge links as copies too: tarfile may fall back to
                        # copying if the filesystem cannot create a hard link.
                        target = member.linkname.removeprefix("./")
                        if target not in sizes:
                            self.logger.warn(f"Archive '{archive}' has an unresolved hard link.")
                            return False
                        size = sizes[target]
                    expanded_bytes += size
                    if size < 0 or expanded_bytes > self.settings.max_extracted_bytes:
                        self.logger.warn(
                            f"Archive '{archive}' exceeds the configured extracted size limit."
                        )
                        return False
                    sizes[name] = size
                    names.append(member.name)
        except (tarfile.TarError, OSError, EOFError, KeyError) as error:
            self.logger.warn(f"Unable to list tar archive '{archive}': {error}")
            return False

        top_component = ""
        has_payload = False
        for entry in names:
            normalized = entry[2:] if entry.startswith("./") else entry
            if (
                _has_control_characters(entry)
                or not normalized
                or normalized.startswith("/")
                or normalized == ".."
                or normalized.startswith("../")
                or "/../" in normalized
                or normalized.endswith("/..")
            ):
                self.logger.warn(
                    f"Archive '{archive}' contains an unsafe member: {shellquote.quote(entry)}."
                )
                return False
            if not top_component:
                top_component = normalized.split("/", 1)[0].rstrip("/")
                if not top_component or top_component in (".", ".."):
                    self.logger.warn(
                        f"Archive '{archive}' has an invalid root: {shellquote.quote(entry)}."
                    )
                    return False
            if normalized != top_component and not normalized.startswith(f"{top_component}/"):
                self.logger.warn(
                    "Archive '{0}' contains multiple roots: {1}.".format(
                        archive, shellquote.join([top_component, normalized])
                    )
                )
                return False
            if "/" in normalized and normalized != f"{top_component}/":
                has_payload = True

        if not has_payload:
            self.logger.warn(f"Archive '{archive}' has no payload below its top-level directory.")
            return False
        return True

    def _validate_extracted_tree(self, archive: Path, tree: Path) -> bool:
        """Re-check the materialized tree.

        Link targets are validated after the whole tree exists so chained
        symlinks resolve accurately.
        """
        resolved_root = canonicalize(tree)
        for directory, _directories, files in os.walk(tree):
            for name in list(files) + list(_directories):
                path = Path(directory) / name
                if _has_control_characters(str(path)):
                    self.logger.warn(
                        "Archive '{0}' extracted a path containing control characters: {1}.".format(
                            archive, shellquote.quote(str(path))
                        )
                    )
                    return False
                if path.is_symlink():
                    target = os.readlink(path)
                    if target.startswith("/") or _has_control_characters(target):
                        self.logger.warn(
                            "Archive '{0}' contains an unsafe symlink: {1}.".format(
                                archive, shellquote.join([str(path), target])
                            )
                        )
                        return False
                    resolved = canonicalize(path)
                    if resolved != resolved_root and resolved_root not in resolved.parents:
                        self.logger.warn(
                            "Archive '{0}' contains a symlink escaping its source directory: {1}.".format(
                                archive, shellquote.join([str(path), target])
                            )
                        )
                        return False
                    continue
                if not path.is_dir() and not path.is_file():
                    self.logger.warn(
                        "Archive '{0}' contains a special filesystem object: {1}.".format(
                            archive, shellquote.quote(str(path))
                        )
                    )
                    return False
        return True

    # -- transfer --------------------------------------------------------

    def _download_to_cache(self, url: str, filename: str, target: Path) -> bool:
        if not url.startswith("https://"):
            raise BuildError(f"Only HTTPS download URLs are accepted: '{url}'.")
        if _has_control_characters(url):
            raise BuildError("Download URLs may not contain control characters.")

        checksum_file = Path(f"{target}.sha256")
        # Another process may have populated the cache while this one waited.
        if self.validate_tar_archive(target):
            if archive_checksum_matches(target, checksum_file):
                self.logger.info(
                    f"'{filename}' already exists and matches its SHA-256 cache record."
                )
                return True
            if checksum_file.exists() or checksum_file.is_symlink():
                self.logger.warn(
                    f"Cached archive checksum mismatch; downloading a clean copy: '{filename}'."
                )
            else:
                self.logger.warn(
                    "Cached archive has no trusted local checksum record; "
                    f"downloading a clean copy: '{filename}'."
                )
        target.unlink(missing_ok=True)
        checksum_file.unlink(missing_ok=True)

        handle, temporary_name = tempfile.mkstemp(prefix=f".{filename}.part.", dir=self.packages)
        os.close(handle)
        temporary = Path(temporary_name)
        self._register(temporary)

        settings = self.settings
        arguments = [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--proto",
            "=https",
            "--proto-redir",
            "=https",
            "--tlsv1.2",
            "--retry",
            str(settings.retry),
            "--retry-delay",
            str(settings.retry_delay),
            "--retry-max-time",
            str(settings.max_time),
            "--retry-connrefused",
            "--retry-all-errors",
            "--connect-timeout",
            str(settings.connect_timeout),
            "--max-time",
            str(settings.max_time),
            "--max-filesize",
            str(settings.max_bytes),
            "--output",
            str(temporary),
            "--write-out",
            "\nHTTP %{http_code}; content-type: %{content_type}; "
            "bytes: %{size_download}; URL: %{url_effective}\n",
            url,
        ]
        self.logger.info(f"Downloading '{url}' as '{filename}'.")
        if self.runner.run_logged(arguments) != 0:
            temporary.unlink(missing_ok=True)
            self._unregister(temporary)
            self.logger.warn(f"Failed to download '{filename}'.")
            return False

        try:
            downloaded_size = temporary.stat().st_size
        except OSError:
            downloaded_size = settings.max_bytes + 1
        if downloaded_size > settings.max_bytes:
            temporary.unlink(missing_ok=True)
            self._unregister(temporary)
            self.logger.warn(f"Downloaded '{filename}' exceeds the configured size limit.")
            return False

        if not self.validate_tar_archive(temporary):
            temporary.unlink(missing_ok=True)
            self._unregister(temporary)
            self.logger.warn(
                f"Downloaded '{filename}', but it is not a safe, valid single-root tar archive."
            )
            return False

        try:
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            self._unregister(temporary)
            return False
        self._unregister(temporary)

        if not write_archive_checksum(target, checksum_file):
            target.unlink(missing_ok=True)
            checksum_file.unlink(missing_ok=True)
            self.logger.warn("Unable to record the downloaded archive's SHA-256 checksum.")
            return False
        return True

    def extract_transactionally(self, archive: Path, target_directory: Path) -> bool:
        return self._extract_transactionally(archive, target_directory) is ExtractionResult.SUCCESS

    def _extract_transactionally(self, archive: Path, target_directory: Path) -> ExtractionResult:
        """Extract into a temporary tree and publish it with one rename."""
        if not self.validate_tar_archive(archive):
            return ExtractionResult.INVALID_ARCHIVE
        staging = Path(tempfile.mkdtemp(prefix=".extract.", dir=self.packages))
        self._register(staging)
        try:
            with tarfile.open(archive) as bundle:
                # `filter="data"` is passed explicitly rather than relying on
                # the default, which is None on 3.12 and 3.13 and "data" only
                # from 3.14: this project targets exactly that range, so the
                # default would change behavior between supported hosts.
                bundle.extractall(path=staging, filter="data")
        except (tarfile.TarError, OSError, EOFError, KeyError) as error:
            self.logger.warn(f"Failed to extract '{archive}': {error}")
            safe_remove_tree(staging, self.packages)
            self._unregister(staging)
            return (
                ExtractionResult.LOCAL_FAILURE
                if isinstance(error, OSError)
                else ExtractionResult.INVALID_ARCHIVE
            )

        roots = list(staging.iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            self.logger.warn(f"Archive '{archive}' extracted no source files.")
            safe_remove_tree(staging, self.packages)
            self._unregister(staging)
            return ExtractionResult.INVALID_ARCHIVE
        stripped = roots[0]

        if not self._validate_extracted_tree(archive, stripped):
            safe_remove_tree(staging, self.packages)
            self._unregister(staging)
            return ExtractionResult.INVALID_ARCHIVE

        if target_directory.is_symlink() or not path_is_within(target_directory, self.packages):
            safe_remove_tree(staging, self.packages)
            self._unregister(staging)
            raise BuildError(f"Refusing unsafe extraction destination: '{target_directory}'.")
        previous = staging / ".previous-source"
        had_previous = target_directory.exists()
        # Once staging can contain the old source it is recovery data. A signal
        # can arrive immediately after rename, before Python enters its handler;
        # abort cleanup must never erase that only remaining copy.
        self._unregister(staging)
        try:
            if had_previous:
                os.rename(target_directory, previous)
            try:
                os.rename(stripped, target_directory)
            except BaseException:
                if had_previous:
                    try:
                        os.rename(previous, target_directory)
                    except OSError as restore_error:
                        self._unregister(staging)
                        raise BuildError(
                            f"Source restoration failed; recovery files remain at '{previous}'."
                        ) from restore_error
                raise
        except OSError as error:
            self.logger.warn(f"Failed to publish the extracted source for '{archive}': {error}")
            safe_remove_tree(staging, self.packages)
            self._unregister(staging)
            return ExtractionResult.LOCAL_FAILURE
        safe_remove_tree(staging, self.packages)
        self._unregister(staging)
        return ExtractionResult.SUCCESS

    # -- public entry points ---------------------------------------------

    def try_download(self, url: str, filename: str | None = None) -> Path | None:
        """Fetch and extract one archive, returning its source directory.

        The Bash original ended by `cd`-ing into the extracted tree and every
        recipe relied on that. Returning the path instead means an exception
        mid-recipe cannot leave the interpreter sitting in a directory a later
        deletion removes.
        """
        name = filename or url.rsplit("/", 1)[-1]
        name = name.split("?", 1)[0]
        if not _ARCHIVE_NAME.match(name):
            raise BuildError(f"Invalid download filename: '{name}'.")
        if not name.endswith(SUPPORTED_ARCHIVE_SUFFIXES):
            raise BuildError(f"Unsupported archive format: '{name}'.")

        target_file = self.packages / name
        target_directory = self.packages / archive_output_directory(name)
        checksum_file = Path(f"{target_file}.sha256")
        self.packages.mkdir(parents=True, exist_ok=True)

        # Held across both populating the cache and reading it: validating an
        # archive and then extracting it under a released lock lets a concurrent
        # process replace the file in between. A real build already holds an
        # exclusive lock on the whole build root, so this matters only for
        # concurrent or standalone use.
        lock = None
        if not self.build_root_locked:
            lock = DirectoryLock(self.packages)
            if not lock.acquire(timeout=self.settings.lock_timeout):
                self.logger.warn(f"Timed out waiting for the package-cache lock: '{name}'.")
                return None
        try:
            if not self._download_to_cache(url, name, target_file):
                return None
            extraction = self._extract_transactionally(target_file, target_directory)
            if extraction is not ExtractionResult.SUCCESS:
                # The archive was listed and checksum-verified moments ago, so
                # an extraction failure is usually local (no space, no
                # permission) and says nothing about the download. Purging a
                # still-valid archive would force a full re-fetch.
                if (
                    extraction is ExtractionResult.LOCAL_FAILURE
                    and self.validate_tar_archive(target_file)
                    and archive_checksum_matches(target_file, checksum_file)
                ):
                    self.logger.warn(
                        f"Failed to extract '{name}'; its cached archive is still valid and was kept."
                    )
                else:
                    target_file.unlink(missing_ok=True)
                    checksum_file.unlink(missing_ok=True)
                    self.logger.warn(
                        f"Failed to extract '{name}' safely; the cached archive was removed."
                    )
                return None
        finally:
            if lock is not None:
                lock.release()

        self.logger.info(f"File extracted: '{name}'.")
        return target_directory

    def download(self, url: str, filename: str | None = None) -> Path:
        source = self.try_download(url, filename)
        if source is None:
            raise BuildError(f"Failed to download and extract '{url}'.")
        return source

    def download_with_fallback(self, primary_url: str, fallback_url: str) -> Path:
        """Prefer the primary mirror, fall back to a second one.

        The fallback names its own cache entry: mirrors do not always agree on
        compression, and forcing the primary's filename onto the fallback stored
        those bytes, and their checksum record, under a name that describes a
        different archive.
        """
        archive_file = primary_url.rsplit("/", 1)[-1].split("?", 1)[0]
        self.logger.info(f"Attempting download from primary mirror: '{primary_url}'.")
        source = self.try_download(primary_url, archive_file)
        if source is not None:
            return source
        self.logger.warn(f"Primary mirror failed, trying fallback mirror: '{fallback_url}'.")
        source = self.try_download(fallback_url)
        if source is not None:
            return source
        raise BuildError("Failed to download from both primary and fallback mirrors.")
