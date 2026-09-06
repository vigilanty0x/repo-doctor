"""Canonical Repo Doctor Python API.

The maintained product/repository/CLI identity is ``repo-doctor``.  The
historical implementation package ``repo_doctor_ai`` remains import-compatible
during the migration window.  Submodule aliases intentionally resolve to the
same module objects so callers do not get duplicate classes or registries.
"""

from __future__ import annotations

import importlib
import sys

from repo_doctor_ai import *  # noqa: F401,F403
from repo_doctor_ai import __all__ as _LEGACY_ALL
from repo_doctor_ai import __version__

_SUBMODULES = (
    "baseline",
    "cli",
    "config",
    "diffing",
    "io_utils",
    "journal",
    "models",
    "planning",
    "registry",
    "reporting",
    "rules",
    "sanitization",
    "sbom",
    "scanner",
)

for _name in _SUBMODULES:
    sys.modules.setdefault(
        f"{__name__}.{_name}", importlib.import_module(f"repo_doctor_ai.{_name}")
    )

__all__ = list(_LEGACY_ALL)
