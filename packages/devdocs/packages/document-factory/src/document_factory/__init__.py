"""Deterministic, bounded Markdown template rendering."""

import argparse
import hashlib
import html
import json
import re

TOKEN = re.compile(r"\{\{([a-zA-Z][a-zA-Z0-9_]*)\}\}")
MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+.!|>~-])")
MAX_TEMPLATE_CHARS = 100_000
MAX_VALUE_CHARS = 2_000
MAX_INTEGER = 1_000_000_000_000


def _safe_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if not -MAX_INTEGER <= value <= MAX_INTEGER:
            return None
        return str(value)
    if (not isinstance(value, str) or len(value) > MAX_VALUE_CHARS
            or any(ord(char) < 32 for char in value)):
        return None
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return MARKDOWN.sub(r"\\\1", html.escape(value, quote=False))


def render(template, values, max_chars=MAX_TEMPLATE_CHARS):
    if (not isinstance(max_chars, int) or isinstance(max_chars, bool)
            or not 1 <= max_chars <= MAX_TEMPLATE_CHARS or not isinstance(template, str)
            or len(template) > max_chars or "<" in template or ">" in template
            or any(ord(char) < 32 and char not in "\n\t" for char in template)
            or not isinstance(values, dict) or len(values) > 1_000
            or any(not isinstance(key, str) for key in values)):
        return {"ok": False, "errors": ["invalid_input"]}
    try:
        template.encode("utf-8")
    except UnicodeEncodeError:
        return {"ok": False, "errors": ["invalid_input"]}
    required = set(TOKEN.findall(template))
    missing, extra = sorted(required - set(values)), sorted(set(values) - required)
    if missing or extra:
        return {"ok": False, "errors": {"missing": missing, "extra": extra}}
    safe = {}
    for key, value in values.items():
        rendered = _safe_value(value)
        if rendered is None:
            return {"ok": False, "errors": ["invalid_value"]}
        safe[key] = rendered
    body = TOKEN.sub(lambda match: safe[match.group(1)], template)
    if len(body) > max_chars:
        return {"ok": False, "errors": ["output_limit"]}
    return {"ok": True, "markdown": body, "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "fields": sorted(required)}


def probe():
    good, bad = render("# {{title}}", {"title": "Demo"}), render("{{missing}}", {})
    return {"ok": good["ok"] and not bad["ok"], "counter_proof": not bad["ok"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "probe"))
    parser.add_argument("--input")
    args = parser.parse_args(argv)
    try:
        data = json.load(open(args.input, encoding="utf-8")) if args.input else {}
        out = probe() if args.command == "probe" else render(
            data.get("template") if isinstance(data, dict) else None,
            data.get("values") if isinstance(data, dict) else None)
    except (OSError, UnicodeError, json.JSONDecodeError):
        out = {"ok": False, "errors": ["input_unreadable"]}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 2
