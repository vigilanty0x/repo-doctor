"""Fail-closed, bounded operational runbook Markdown generation."""

import argparse
import hashlib
import html
import json
import re

MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+.!|>~-])")
FIELDS = ("service", "trigger", "owner", "steps", "verification", "rollback")
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


def _items(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ITEMS:
        return None
    safe = [_text(item) for item in value]
    return safe if all(item is not None for item in safe) else None


def build(spec):
    if not isinstance(spec, dict) or set(spec) != set(FIELDS):
        return {"ok": False, "errors": ["invalid_schema"]}
    service, trigger, owner = (_text(spec[key], 200) for key in ("service", "trigger", "owner"))
    steps, verification, rollback = (_items(spec[key]) for key in ("steps", "verification", "rollback"))
    if any(value is None for value in (service, trigger, owner, steps, verification, rollback)):
        return {"ok": False, "errors": ["invalid_content"]}
    lines = [f"# Runbook: {service}", f"Owner: {owner}", f"Trigger: {trigger}", "", "## Steps"]
    lines.extend(f"{index}. {item}" for index, item in enumerate(steps, 1))
    lines.extend(["", "## Verification", *(f"- {item}" for item in verification),
                  "", "## Rollback", *(f"- {item}" for item in rollback)])
    body = "\n".join(lines)
    if len(body) > MAX_OUTPUT:
        return {"ok": False, "errors": ["output_limit"]}
    return {"ok": True, "markdown": body, "sha256": hashlib.sha256(body.encode()).hexdigest()}


def probe():
    good = build({"service": "demo", "trigger": "alarm", "owner": "team", "steps": ["inspect"],
                  "verification": ["healthy"], "rollback": ["restore"]})
    bad = build({"service": "demo", "steps": ["act"]})
    return {"ok": good["ok"] and not bad["ok"], "rollback_counter_proof": not bad["ok"]}


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
