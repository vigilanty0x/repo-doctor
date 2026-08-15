from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

PROJECT = "dependency-drift-reporter"
REQUIRED_FIELDS = ("manifest", "installed")
MAX_INPUT_BYTES = 65_536


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _text(value: Any, limit: int = 200) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= limit and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def compare_dependencies(record: dict[str, Any]) -> dict[str, Any]:
    manifest, installed = record.get("manifest"), record.get("installed")
    if not isinstance(manifest, dict) or not manifest or not isinstance(installed, dict) or not installed or len(manifest) > 2000 or len(installed) > 2000:
        raise ValueError("manifest and installed maps must contain 1-2000 entries")
    if any(not _text(key) or not _text(value) for mapping in (manifest, installed) for key, value in mapping.items()):
        raise ValueError("dependency names and versions must be bounded single-line strings")
    keys = sorted(set(manifest) | set(installed))
    drift = [{"name": key, "declared": manifest.get(key), "installed": installed.get(key)} for key in keys if manifest.get(key) != installed.get(key)]
    return {"drift": drift, "checked": keys, "drift_count": len(drift)}


def evaluate(record: Any) -> dict[str, Any]:
    artifact: Any = None
    safe_record = None
    try:
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        if len(_canonical(record).encode()) > MAX_INPUT_BYTES:
            raise ValueError("record exceeds 65536 bytes")
        safe_record = record
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            status, reason = "blocked", "missing required fields: " + ", ".join(missing)
        else:
            artifact = compare_dependencies(record)
            if artifact["drift"]:
                status, reason = "failed", f"dependency drift detected in {artifact['drift_count']} entr{'y' if artifact['drift_count'] == 1 else 'ies'}"
            else:
                status, reason = "passed", "declared and installed dependency maps match"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "drift_report": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
