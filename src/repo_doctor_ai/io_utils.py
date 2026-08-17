"""Small no-follow, bounded file-reading primitives for public inputs."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
from typing import Self


class BoundedReadError(ValueError):
    """A file boundary was not a regular, bounded input."""

    def __init__(
        self,
        message: str,
        *,
        reason: str = "invalid",
        actual_size: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.actual_size = actual_size


def is_safe_relative_path(value: str) -> bool:
    """Validate a relative path independently of the host operating system."""

    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    normalized = value.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(value)
    return not (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or ".." in posix.parts
        or any(part in {"", "."} for part in normalized.split("/"))
    )


def is_link_or_reparse(path: str | Path) -> bool:
    """Return true for symlinks, Windows junctions, and other reparse points."""

    candidate = Path(path)
    try:
        metadata = candidate.lstat()
    except OSError:
        return False
    return _metadata_is_link_or_reparse(metadata)


def _metadata_is_link_or_reparse(metadata: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _supports_descriptor_relative_reads() -> bool:
    return os.open in os.supports_dir_fd


class ConfinedReader:
    """Read descendants through a pinned root descriptor and no-follow openat calls."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._root_descriptor: int | None = None
        self._portable_root: Path | None = None
        self._portable_root_metadata: os.stat_result | None = None

    def __enter__(self) -> Self:
        if not _supports_descriptor_relative_reads():
            return self._enter_portable()
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_BINARY", 0)
        )
        try:
            descriptor = os.open(self.root, flags)
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(descriptor)
                raise BoundedReadError("evaluation root must be a directory")
            self._root_descriptor = descriptor
            return self
        except BoundedReadError:
            raise
        except OSError as exc:
            raise BoundedReadError(f"cannot open evaluation root: {type(exc).__name__}") from exc

    def _enter_portable(self) -> Self:
        """Pin a root identity for platforms without descriptor-relative opens."""

        try:
            resolved = self.root.resolve(strict=True)
            metadata = resolved.lstat()
            if _metadata_is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise BoundedReadError("evaluation root must be a regular directory")
            self._portable_root = resolved
            self._portable_root_metadata = metadata
            return self
        except BoundedReadError:
            raise
        except OSError as exc:
            raise BoundedReadError(f"cannot open evaluation root: {type(exc).__name__}") from exc

    def __exit__(self, *_: object) -> None:
        if self._root_descriptor is not None:
            os.close(self._root_descriptor)
            self._root_descriptor = None
        self._portable_root = None
        self._portable_root_metadata = None

    def read_bounded_bytes(
        self,
        relative: str,
        maximum_bytes: int,
        *,
        label: str,
        remaining_bytes: int | None = None,
    ) -> tuple[bytes, int]:
        """Open every path component relative to the pinned root without following links."""

        if not is_safe_relative_path(relative):
            raise BoundedReadError(f"{label} is not a safe relative file path")
        normalized = relative.replace("\\", "/")
        parts = normalized.split("/")
        if self._portable_root is not None:
            return self._read_portable(
                parts,
                maximum_bytes,
                label=label,
                remaining_bytes=remaining_bytes,
            )
        if self._root_descriptor is None:
            raise BoundedReadError("confined reader is not open")

        directory_descriptor = os.dup(self._root_descriptor)
        file_descriptor: int | None = None
        try:
            directory_flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_BINARY", 0)
            )
            for component in parts[:-1]:
                next_descriptor = os.open(component, directory_flags, dir_fd=directory_descriptor)
                metadata = os.fstat(next_descriptor)
                if not stat.S_ISDIR(metadata.st_mode):
                    os.close(next_descriptor)
                    raise BoundedReadError(f"{label} contains a non-directory component")
                os.close(directory_descriptor)
                directory_descriptor = next_descriptor

            file_flags = (
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_BINARY", 0)
            )
            file_descriptor = os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
            metadata = os.fstat(file_descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise BoundedReadError(f"{label} must be a regular file")
            size = metadata.st_size
            if size > maximum_bytes:
                raise BoundedReadError(
                    f"{label} exceeds {maximum_bytes} bytes",
                    reason="file_limit",
                    actual_size=size,
                )
            if remaining_bytes is not None and size > remaining_bytes:
                raise BoundedReadError(
                    f"{label} exceeds the remaining total-byte budget",
                    reason="total_limit",
                    actual_size=size,
                )
            with os.fdopen(file_descriptor, "rb", closefd=True) as stream:
                file_descriptor = None
                content = stream.read(maximum_bytes + 1)
            if len(content) > maximum_bytes:
                raise BoundedReadError(
                    f"{label} exceeds {maximum_bytes} bytes",
                    reason="file_limit",
                    actual_size=max(size, len(content)),
                )
            if remaining_bytes is not None and len(content) > remaining_bytes:
                raise BoundedReadError(
                    f"{label} exceeds the remaining total-byte budget",
                    reason="total_limit",
                    actual_size=max(size, len(content)),
                )
            return content, size
        except BoundedReadError:
            raise
        except OSError as exc:
            raise BoundedReadError(f"cannot read {label}: {type(exc).__name__}") from exc
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
            os.close(directory_descriptor)

    def _read_portable(
        self,
        parts: list[str],
        maximum_bytes: int,
        *,
        label: str,
        remaining_bytes: int | None,
    ) -> tuple[bytes, int]:
        """Read with component identity checks when ``dir_fd`` is unavailable."""

        root = self._portable_root
        pinned_root = self._portable_root_metadata
        if root is None or pinned_root is None:
            raise BoundedReadError("confined reader is not open")
        target = root.joinpath(*parts)
        component_metadata: list[tuple[Path, os.stat_result]] = []
        descriptor: int | None = None
        try:
            current = root
            for index, component in enumerate(parts):
                current /= component
                metadata = current.lstat()
                if _metadata_is_link_or_reparse(metadata):
                    raise BoundedReadError(f"{label} contains a link or reparse point")
                if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
                    raise BoundedReadError(f"{label} contains a non-directory component")
                component_metadata.append((current, metadata))

            expected_file = component_metadata[-1][1]
            if not stat.S_ISREG(expected_file.st_mode):
                raise BoundedReadError(f"{label} must be a regular file")
            flags = (
                os.O_RDONLY
                | getattr(os, "O_BINARY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
            )
            descriptor = os.open(target, flags)
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(expected_file, opened):
                raise BoundedReadError(f"{label} changed while it was opened")
            self._verify_portable_path(root, pinned_root, target, component_metadata, opened, label)

            size = opened.st_size
            if size > maximum_bytes:
                raise BoundedReadError(
                    f"{label} exceeds {maximum_bytes} bytes",
                    reason="file_limit",
                    actual_size=size,
                )
            if remaining_bytes is not None and size > remaining_bytes:
                raise BoundedReadError(
                    f"{label} exceeds the remaining total-byte budget",
                    reason="total_limit",
                    actual_size=size,
                )
            with os.fdopen(descriptor, "rb", closefd=True) as stream:
                descriptor = None
                content = stream.read(maximum_bytes + 1)
            self._verify_portable_path(root, pinned_root, target, component_metadata, opened, label)
            if len(content) > maximum_bytes:
                raise BoundedReadError(
                    f"{label} exceeds {maximum_bytes} bytes",
                    reason="file_limit",
                    actual_size=max(size, len(content)),
                )
            if remaining_bytes is not None and len(content) > remaining_bytes:
                raise BoundedReadError(
                    f"{label} exceeds the remaining total-byte budget",
                    reason="total_limit",
                    actual_size=max(size, len(content)),
                )
            return content, size
        except BoundedReadError:
            raise
        except OSError as exc:
            raise BoundedReadError(f"cannot read {label}: {type(exc).__name__}") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)

    @staticmethod
    def _verify_portable_path(
        root: Path,
        pinned_root: os.stat_result,
        target: Path,
        components: list[tuple[Path, os.stat_result]],
        opened: os.stat_result,
        label: str,
    ) -> None:
        current_root = root.lstat()
        if _metadata_is_link_or_reparse(current_root) or not os.path.samestat(
            pinned_root, current_root
        ):
            raise BoundedReadError(f"{label} root changed during the read")
        for path, expected in components:
            current = path.lstat()
            if _metadata_is_link_or_reparse(current) or not os.path.samestat(expected, current):
                raise BoundedReadError(f"{label} path changed during the read")
        if not os.path.samestat(components[-1][1], opened):
            raise BoundedReadError(f"{label} file identity changed during the read")
        try:
            target.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise BoundedReadError(f"{label} escaped the evaluation root") from exc


def read_bounded_bytes(path: str | Path, maximum_bytes: int, *, label: str) -> bytes:
    """Read at most ``maximum_bytes`` from a regular file without following a final symlink."""

    target = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(target, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise BoundedReadError(f"{label} must be a regular file")
        if metadata.st_size > maximum_bytes:
            raise BoundedReadError(f"{label} exceeds {maximum_bytes} bytes")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            content = stream.read(maximum_bytes + 1)
        if len(content) > maximum_bytes:
            raise BoundedReadError(f"{label} exceeds {maximum_bytes} bytes")
        return content
    except BoundedReadError:
        raise
    except OSError as exc:
        raise BoundedReadError(f"cannot read {label}: {type(exc).__name__}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_bounded_text(path: str | Path, maximum_bytes: int, *, label: str) -> str:
    try:
        return read_bounded_bytes(path, maximum_bytes, label=label).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BoundedReadError(f"{label} must be UTF-8") from exc
