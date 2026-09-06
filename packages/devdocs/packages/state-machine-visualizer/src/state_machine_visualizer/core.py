from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

PROJECT = "state-machine-visualizer"
REQUIRED_FIELDS = ("name", "states", "initial", "transitions")
MAX_INPUT_BYTES = 65_536


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _label(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= 200 and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def render_state_machine(record: dict[str, Any]) -> str:
    states = record.get("states")
    transitions = record.get("transitions")
    if not _label(record.get("name")):
        raise ValueError("name must be a bounded single-line label")
    if not isinstance(states, list) or not 1 <= len(states) <= 200 or any(not _label(state) for state in states) or len(states) != len(set(states)):
        raise ValueError("states must be 1-200 unique bounded single-line strings")
    if record.get("initial") not in states or not isinstance(transitions, list) or not 1 <= len(transitions) <= 1000:
        raise ValueError("initial state and 1-1000 transitions are required")
    identifiers = {state: f"state_{index}" for index, state in enumerate(states)}
    graph: dict[str, set[str]] = {state: set() for state in states}
    normalized: list[tuple[str, str]] = []
    for transition in transitions:
        if not isinstance(transition, list) or len(transition) != 2 or transition[0] not in graph or transition[1] not in graph:
            raise ValueError("each transition must reference two declared states")
        edge = (transition[0], transition[1])
        if edge in normalized:
            raise ValueError("transitions must be unique")
        normalized.append(edge)
        graph[edge[0]].add(edge[1])
    reachable = {record["initial"]}
    frontier = [record["initial"]]
    while frontier:
        for target in graph[frontier.pop()]:
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    if reachable != set(states):
        raise ValueError("orphan states are not allowed")
    lines = ["stateDiagram-v2"]
    for state in states:
        label = json.dumps(state.strip(), ensure_ascii=True)
        lines.append(f"    state {label} as {identifiers[state]}")
    lines.append(f"    [*] --> {identifiers[record['initial']]}")
    lines.extend(f"    {identifiers[source]} --> {identifiers[target]}" for source, target in normalized)
    return "\n".join(lines) + "\n"


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
            artifact = render_state_machine(record)
            status, reason = "passed", "Mermaid rendered with opaque node identifiers"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        status, reason = "failed", str(exc)
    receipt = {"project": PROJECT, "status": status, "reason": reason, "record": safe_record, "mermaid": artifact}
    receipt["evidence_sha256"] = sha256(_canonical(receipt).encode()).hexdigest()
    return receipt
