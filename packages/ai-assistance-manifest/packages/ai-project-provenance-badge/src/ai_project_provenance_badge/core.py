from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

PROJECT = "ai-project-provenance-badge"
REQUIRED_FIELDS = ("project", "assistance_level", "supervision", "tests_passed", "evidence_url", "evidence")
MAX_INPUT_BYTES = 32_768
SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _text(value: Any, limit: int = 200) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= limit and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _https_url(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in "()<>\\" for c in value):
        raise ValueError("evidence_url must be a bounded Markdown-safe HTTPS URL")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("evidence_url must use HTTPS with a nonempty host and no credentials")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise ValueError("evidence_url host or port is invalid") from exc
    if not host or any(part == "" for part in host.split(".")):
        raise ValueError("evidence_url host is invalid")
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc += f":{port}"
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, parsed.fragment))


def _instant(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("evidence issued_at must be timezone-aware ISO-8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("evidence issued_at must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evidence issued_at must include an offset")
    return parsed.isoformat()


def render_badge(record: dict[str, Any]) -> dict[str, Any]:
    if not _text(record.get("project"), 120) or record.get("assistance_level") not in {"none", "assisted", "generated"}:
        raise ValueError("project and assistance_level are invalid")
    if record.get("supervision") not in {"human-reviewed", "human-approved", "independent-review"}:
        raise ValueError("explicit supervision is required")
    tests = record.get("tests_passed")
    if not isinstance(tests, int) or isinstance(tests, bool) or not 1 <= tests <= 1_000_000:
        raise ValueError("tests_passed must be a bounded positive integer")
    evidence = record.get("evidence")
    required = {"artifact_sha256", "test_sha256", "review_sha256", "issuer", "issued_at"}
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise ValueError("evidence requires exact artifact, test, review, issuer, and timestamp fields")
    if any(not isinstance(evidence[key], str) or not SHA256.fullmatch(evidence[key]) for key in ("artifact_sha256", "test_sha256", "review_sha256")):
        raise ValueError("evidence digests must be lowercase SHA-256")
    if not _text(evidence["issuer"]):
        raise ValueError("evidence issuer is invalid")
    _instant(evidence["issued_at"])
    url = _https_url(record.get("evidence_url"))
    label = f"AI {record['assistance_level']} | {record['supervision']} | {tests} tests"
    alt = re.sub(r"([\\\[\]])", r"\\\1", label)
    markdown = f"[![{alt}](https://img.shields.io/badge/provenance-documented-blue)]({url})"
    return {"markdown": markdown, "trust_state": "documented-self-declaration", "verified": False, "evidence": evidence}


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
            artifact = render_badge(record)
            status, reason = "passed", "provenance declaration documented; independent attestation was not verified"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "badge_markdown": artifact["markdown"] if artifact else None, "provenance": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
