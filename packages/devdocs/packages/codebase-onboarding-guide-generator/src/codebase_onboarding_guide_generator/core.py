from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

PROJECT = "codebase-onboarding-guide-generator"
REQUIRED_FIELDS = ("project", "entrypoints", "commands", "tests")
MAX_INPUT_BYTES = 32_768
MAX_ITEMS = 50
MAX_TEXT = 500


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _bounded_text(value: Any, *, limit: int = MAX_TEXT) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value.strip()) <= limit
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def _bounded_list(value: Any) -> bool:
    return isinstance(value, list) and 0 < len(value) <= MAX_ITEMS and all(_bounded_text(item) for item in value)


def _markdown_text(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", value.strip())


def _code_span(value: str) -> str:
    value = value.strip()
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)
    fence = "`" * (longest + 1)
    padding = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{padding}{value}{padding}{fence}"


def generate_guide(record: dict[str, Any]) -> str:
    if not _bounded_text(record.get("project"), limit=120):
        raise ValueError("project must be a bounded single-line string")
    if any(not _bounded_list(record.get(key)) for key in ("entrypoints", "commands", "tests")):
        raise ValueError("guide sections must contain 1-50 bounded single-line strings")
    lines = [f"# {_markdown_text(record['project'])}"]
    lines.extend(["", "## Entrypoints", *[f"- {_markdown_text(item)}" for item in record["entrypoints"]]])
    lines.extend(["", "## Commands", *[f"- {_code_span(item)}" for item in record["commands"]]])
    lines.extend(["", "## Tests", *[f"- {_code_span(item)}" for item in record["tests"]]])
    return "\n".join(lines) + "\n"


def evaluate(record: Any) -> dict[str, Any]:
    artifact: Any = None
    safe_record = None
    try:
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        if len(_canonical(record).encode()) > MAX_INPUT_BYTES:
            raise ValueError("record exceeds 32768 bytes")
        safe_record = record
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            status, reason = "blocked", "missing required fields: " + ", ".join(missing)
        else:
            artifact = generate_guide(record)
            status, reason = "passed", "guide rendered from bounded Markdown-safe input"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "guide_markdown": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
