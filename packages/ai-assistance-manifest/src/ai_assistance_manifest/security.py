"""Conservative secret and path checks for public manifests."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterator

from .diagnostics import Diagnostic

SECRET_PATTERNS = (
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)


def walk_strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f"{path}[{index}]")


def find_suspected_secrets(manifest: dict[str, Any]) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    for path, value in walk_strings(manifest):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(value):
                findings.append(
                    Diagnostic("AAM401", path, f"suspected {label}; remove it from the manifest")
                )
    return findings


def is_safe_relative_path(value: str) -> bool:
    """Reject absolute/traversal paths using POSIX and Windows semantics.

    Manifest paths are portable data, so their safety cannot depend on the OS
    that happens to validate the file.  A POSIX absolute path must therefore be
    rejected on Windows, and a Windows drive/UNC path must be rejected on POSIX.
    Backslashes are also treated as path separators for traversal checks.
    """

    if not value or "\x00" in value or value.startswith("~"):
        return False

    posix = PurePosixPath(value.replace("\\", "/"))
    windows = PureWindowsPath(value)

    if posix.is_absolute() or windows.is_absolute() or bool(windows.drive):
        return False
    if ".." in posix.parts or ".." in windows.parts:
        return False
    return True
