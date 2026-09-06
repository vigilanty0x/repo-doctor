"""Create deterministic Mermaid diagrams from bounded declared topology."""

import argparse
import hashlib
import html
import json
import re

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}")
MAX_NODES = 200
MAX_EDGES = 1_000


def _label(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 100
            or any(ord(char) < 32 for char in value)):
        return None
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return html.escape(value, quote=True)


def generate(data):
    if not isinstance(data, dict) or set(data) != {"nodes", "edges"}:
        return {"ok": False, "errors": ["invalid_input"]}
    nodes, edges = data["nodes"], data["edges"]
    if (not isinstance(nodes, list) or not isinstance(edges, list)
            or len(nodes) > MAX_NODES or len(edges) > MAX_EDGES):
        return {"ok": False, "errors": ["bounds"]}
    labels, ids = {}, []
    for node in nodes:
        if (not isinstance(node, dict) or not set(node) <= {"id", "label"}
                or "id" not in node or not isinstance(node["id"], str)
                or not IDENTIFIER.fullmatch(node["id"]) or node["id"] in labels):
            return {"ok": False, "errors": ["invalid_nodes"]}
        safe_label = _label(node.get("label", node["id"]))
        if safe_label is None:
            return {"ok": False, "errors": ["invalid_label"]}
        ids.append(node["id"])
        labels[node["id"]] = safe_label
    parsed_edges, seen = [], set()
    for edge in edges:
        if (not isinstance(edge, dict) or set(edge) != {"from", "to"}
                or edge["from"] not in labels or edge["to"] not in labels):
            return {"ok": False, "errors": ["dangling_edges"]}
        pair = (edge["from"], edge["to"])
        if pair in seen:
            return {"ok": False, "errors": ["duplicate_edges"]}
        seen.add(pair)
        parsed_edges.append(pair)
    opaque = {node_id: f"node_{index:03d}" for index, node_id in enumerate(sorted(ids))}
    lines = ["flowchart TD"]
    lines.extend(f"  {opaque[node_id]}[{json.dumps(labels[node_id])}]" for node_id in sorted(ids))
    lines.extend(f"  {opaque[left]} --> {opaque[right]}" for left, right in sorted(parsed_edges))
    body = "\n".join(lines)
    return {"ok": True, "mermaid": body, "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "nodes": len(ids), "edges": len(parsed_edges)}


def probe():
    good = generate({"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"from": "a", "to": "b"}]})
    bad = generate({"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "x"}]})
    return {"ok": good["ok"] and not bad["ok"], "dangling_counter_proof": not bad["ok"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "probe"))
    parser.add_argument("--input")
    args = parser.parse_args(argv)
    try:
        data = json.load(open(args.input, encoding="utf-8")) if args.input else None
        out = probe() if args.command == "probe" else generate(data)
    except (OSError, UnicodeError, json.JSONDecodeError):
        out = {"ok": False, "errors": ["input_unreadable"]}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 2
