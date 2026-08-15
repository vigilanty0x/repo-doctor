from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

PROJECT = "dependency-drift-reporter"
REQUIRED_FIELDS = ["manifest","installed"]

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)

def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def compare_dependencies(record: dict[str, Any]) -> dict[str, Any]:
    manifest, installed = record["manifest"], record["installed"]
    if not isinstance(manifest, dict) or not manifest or not isinstance(installed, dict) or not installed:
        raise ValueError("manifest and installed maps are required")
    if any(not _text(key) or not _text(value) for mapping in (manifest, installed) for key, value in mapping.items()):
        raise ValueError("dependency names and versions must be non-empty strings")
    keys = sorted(set(manifest) | set(installed))
    drift = [{"name": key, "declared": manifest.get(key), "installed": installed.get(key)} for key in keys if manifest.get(key) != installed.get(key)]
    if drift:
        raise ValueError("dependency drift detected: " + ",".join(item["name"] for item in drift))
    return {"drift": [], "checked": keys}

def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    artifact: Any = None
    if missing:
        status = "blocked"
        reason = "missing required fields: " + ", ".join(missing)
    else:
        try:
            artifact = compare_dependencies(record)
            status = "passed"
            reason = "compare_dependencies completed"
        except (TypeError, ValueError, KeyError) as exc:
            status = "failed"
            reason = str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": record, "drift_report": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt

