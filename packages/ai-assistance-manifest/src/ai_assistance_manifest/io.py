"""Manifest and bundled-resource I/O."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

MAX_MANIFEST_BYTES = 1_048_576


class ManifestLoadError(ValueError):
    """Raised when a manifest cannot be loaded safely."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestLoadError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ManifestLoadError(str(exc)) from exc
    if size > MAX_MANIFEST_BYTES:
        raise ManifestLoadError(
            f"manifest is {size} bytes; maximum is {MAX_MANIFEST_BYTES}"
        )
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestLoadError(str(exc)) from exc
    if not isinstance(data, dict):
        raise ManifestLoadError("manifest root must be a JSON object")
    return data


def dump_manifest(data: dict[str, Any]) -> str:
    """Return canonical, diff-friendly JSON."""

    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def bundled_schema() -> str:
    return (
        files("ai_assistance_manifest")
        .joinpath("schema/manifest.schema.json")
        .read_text(encoding="utf-8")
    )


def bundled_template() -> dict[str, Any]:
    text = (
        files("ai_assistance_manifest")
        .joinpath("templates/AI_ASSISTANCE.example.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(text)

