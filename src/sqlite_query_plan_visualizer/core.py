from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

PROJECT = "sqlite-query-plan-visualizer"
REQUIRED_FIELDS = ["query","before_plan","after_plan"]

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

def compare_plans(record: dict[str, Any]) -> dict[str, Any]:
    if not _text(record["query"]) or not record["query"].lstrip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("only read-only query plans are accepted")
    before, after = record["before_plan"], record["after_plan"]
    if not _string_list(before) or not _string_list(after):
        raise ValueError("query plans must contain non-empty lines")
    return {"removed": [line for line in before if line not in after], "added": [line for line in after if line not in before], "uses_index": any("INDEX" in line.upper() for line in after)}

def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    artifact: Any = None
    if missing:
        status = "blocked"
        reason = "missing required fields: " + ", ".join(missing)
    else:
        try:
            artifact = compare_plans(record)
            status = "passed"
            reason = "compare_plans completed"
        except (TypeError, ValueError, KeyError) as exc:
            status = "failed"
            reason = str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": record, "plan_diff": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt

