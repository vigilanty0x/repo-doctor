from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any

PROJECT = "container-resource-profiler"
REQUIRED_FIELDS = ("scenario", "cpu_percent", "memory_mb", "io_mb", "network_mb", "startup_ms")
MAX_INPUT_BYTES = 16_384
BOUNDS = {"cpu_percent": (0.0, 100.0), "memory_mb": (0.001, 1_048_576.0), "io_mb": (0.0, 1_000_000_000.0), "network_mb": (0.0, 1_000_000_000.0), "startup_ms": (0.001, 86_400_000.0)}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def build_profile(record: dict[str, Any]) -> dict[str, Any]:
    scenario = record.get("scenario")
    if not isinstance(scenario, str) or not 1 <= len(scenario.strip()) <= 200 or any(ord(c) < 32 or ord(c) == 127 for c in scenario):
        raise ValueError("scenario must be a bounded single-line string")
    for key, (minimum, maximum) in BOUNDS.items():
        value = record.get(key)
        if not _number(value) or not minimum <= value <= maximum:
            raise ValueError(f"{key} must be finite and between {minimum} and {maximum}")
    return {
        "source": "supplied-measurements",
        "observed_by_tool": False,
        "scenario": scenario,
        "cpu_percent": record["cpu_percent"],
        "memory_mb": record["memory_mb"],
        "io_mb": record["io_mb"],
        "network_mb": record["network_mb"],
        "total_transfer_mb": record["io_mb"] + record["network_mb"],
        "startup_ms": record["startup_ms"],
    }


def evaluate(record: Any) -> dict[str, Any]:
    artifact: Any = None
    safe_record = None
    try:
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        if len(_canonical(record).encode()) > MAX_INPUT_BYTES:
            raise ValueError("record exceeds 16384 bytes")
        safe_record = record
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            status, reason = "blocked", "missing required fields: " + ", ".join(missing)
        else:
            artifact = build_profile(record)
            status, reason = "passed", "profile normalized from supplied measurements; no container observation was performed"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "profile": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
