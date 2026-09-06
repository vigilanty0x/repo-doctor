"""Evidence-oriented, bounded and context-safe postmortem generation."""

import argparse
import hashlib
import html
import json
import re

MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+.!|>~-])")
FIELDS = ("incident", "impact", "timeline", "evidence", "causes", "actions")
MAX_ITEMS = 100
MAX_OUTPUT = 100_000


def _text(value, maximum=1_000):
    if (not isinstance(value, str) or not 1 <= len(value) <= maximum
            or any(ord(char) < 32 for char in value)):
        return None
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return MARKDOWN.sub(r"\\\1", html.escape(value, quote=False))


def _list(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ITEMS:
        return None
    safe = [_text(item) for item in value]
    return safe if all(item is not None for item in safe) else None


def build(data):
    if not isinstance(data, dict) or set(data) != set(FIELDS):
        return {"ok": False, "errors": ["invalid_schema"]}
    incident, impact = _text(data["incident"], 200), _text(data["impact"], 2_000)
    timeline, evidence, causes = (_list(data[key]) for key in ("timeline", "evidence", "causes"))
    actions = data["actions"]
    if (incident is None or impact is None or timeline is None or evidence is None or causes is None
            or not isinstance(actions, list) or not 1 <= len(actions) <= MAX_ITEMS):
        return {"ok": False, "errors": ["invalid_content"]}
    safe_actions = []
    for action in actions:
        if not isinstance(action, dict) or set(action) != {"owner", "due", "action"}:
            return {"ok": False, "errors": ["invalid_action"]}
        clean = {key: _text(action[key], 1_000 if key == "action" else 200)
                 for key in ("owner", "due", "action")}
        if any(value is None for value in clean.values()):
            return {"ok": False, "errors": ["invalid_action"]}
        safe_actions.append(clean)
    sections = [f"# Postmortem: {incident}", "## Impact", impact, "## Timeline",
                *(f"- {item}" for item in timeline), "## Evidence",
                *(f"- {item}" for item in evidence), "## Causes",
                *(f"- {item}" for item in causes), "## Actions",
                *(f"- {item['action']} — {item['owner']} — {item['due']}" for item in safe_actions)]
    body = "\n".join(sections)
    if len(body) > MAX_OUTPUT:
        return {"ok": False, "errors": ["output_limit"]}
    return {"ok": True, "markdown": body, "sha256": hashlib.sha256(body.encode()).hexdigest()}


def probe():
    good = build({"incident": "demo", "impact": "none", "timeline": ["t"], "evidence": ["e"],
                  "causes": ["c"], "actions": [{"owner": "o", "due": "later", "action": "a"}]})
    bad = build({"incident": "demo"})
    return {"ok": good["ok"] and not bad["ok"], "incomplete_counter_proof": not bad["ok"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "probe"))
    parser.add_argument("--input")
    args = parser.parse_args(argv)
    try:
        data = json.load(open(args.input, encoding="utf-8")) if args.input else None
        out = probe() if args.command == "probe" else build(data)
    except (OSError, UnicodeError, json.JSONDecodeError):
        out = {"ok": False, "errors": ["input_unreadable"]}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 2
