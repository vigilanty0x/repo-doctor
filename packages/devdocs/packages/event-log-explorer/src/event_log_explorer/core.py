from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

PROJECT = "event-log-explorer"
REQUIRED_FIELDS = ("stream", "events")
MAX_INPUT_BYTES = 131_072
MAX_EVENT_BYTES = 8_192
SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _text(value: Any, limit: int = 200) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= limit and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def build_timeline(record: dict[str, Any], *, expected_head_sha256: str | None = None) -> dict[str, Any]:
    if set(record) != set(REQUIRED_FIELDS):
        raise ValueError("record accepts only stream and events; the trusted expected head is a separate API argument")
    events = record.get("events")
    if not _text(record.get("stream")) or not isinstance(events, list) or not 1 <= len(events) <= 1000:
        raise ValueError("stream and 1-1000 events are required")
    chain_fields = [all(key in event for key in ("previous_sha256", "event_sha256")) if isinstance(event, dict) else False for event in events]
    if any(chain_fields) and not all(chain_fields):
        raise ValueError("hash-chain fields must be present on every event")
    chained = all(chain_fields)
    previous = "0" * 64
    timeline: list[dict[str, Any]] = []
    for expected, event in enumerate(events, start=1):
        if not isinstance(event, dict) or set(event) - {"sequence", "type", "payload", "previous_sha256", "event_sha256"}:
            raise ValueError("event fields are not allowed")
        if not isinstance(event.get("sequence"), int) or isinstance(event.get("sequence"), bool) or event["sequence"] != expected or not _text(event.get("type")):
            raise ValueError("events must be contiguous and typed")
        payload = event.get("payload", {})
        if not isinstance(payload, dict) or len(_canonical(payload).encode()) > MAX_EVENT_BYTES:
            raise ValueError("each payload must be a JSON object no larger than 8192 bytes")
        item = {"sequence": expected, "type": event["type"], "payload": payload}
        if chained:
            if event["previous_sha256"] != previous or not isinstance(event["event_sha256"], str) or not SHA256.fullmatch(event["event_sha256"]):
                raise ValueError("event hash chain is invalid")
            calculated = sha256(_canonical({**item, "previous_sha256": previous}).encode()).hexdigest()
            if event["event_sha256"] != calculated:
                raise ValueError("event digest does not match its content")
            previous = calculated
            item["event_sha256"] = calculated
        timeline.append(item)
    if expected_head_sha256 is not None:
        if not chained or not isinstance(expected_head_sha256, str) or not SHA256.fullmatch(expected_head_sha256) or expected_head_sha256 != previous:
            raise ValueError("trusted expected head does not match the event chain")
        integrity = "chain-matched-expected-head"
    else:
        integrity = "structural-only"
    return {"timeline": timeline, "integrity": integrity, "head_sha256": previous if chained else None, "authenticity_verified": False}


def evaluate(record: Any, *, expected_head_sha256: str | None = None) -> dict[str, Any]:
    artifact: Any = None
    safe_record = None
    try:
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        if len(_canonical(record).encode()) > MAX_INPUT_BYTES:
            raise ValueError("record exceeds 131072 bytes")
        safe_record = record
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            status, reason = "blocked", "missing required fields: " + ", ".join(missing)
        else:
            artifact = build_timeline(record, expected_head_sha256=expected_head_sha256)
            status = "passed"
            reason = "event structure inspected; authenticity is not established" if artifact["integrity"] == "structural-only" else "hash chain matched the separately supplied expected head"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "timeline": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
