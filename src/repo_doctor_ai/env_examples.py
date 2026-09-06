"""Env Example Guard rules over Scanner observations, with names-only evidence.

Adapted from env-example-guard (Apache-2.0), commit
4df3eb9ae1347c5f03618b78e2a5a33507750c75. No filesystem or process access.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re

from .models import Finding
from .registry import RegistryDeadlineExceeded, RegistryError
from .sanitization import safe_output_text

MAX_KEYS = 10_000
MAX_EXAMPLE_BYTES = 1_000_000
MAX_MANIFEST_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_SCOPES = 128
MANIFEST_NAMES = ("env-keys.json", ".env.keys.json")
KEY = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")
SENSITIVE_NAME = re.compile(r"(?i)(?:^|_)(?:api_?key|auth|credential|database_url|dsn|password|private_?key|secret|token)(?:$|_)")
SENSITIVE_VALUE = re.compile(
    r"(?:\bAKIA[0-9A-Z]{16}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bxox[baprs]-[A-Za-z0-9-]{20,}\b|\bsk_live_[A-Za-z0-9]{20,}\b|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b)",
    re.IGNORECASE,
)
PLACEHOLDERS = {"", "<replace-me>", "<required>", "changeme", "replace-me", "example"}
HELP = {
    "ENV_EXAMPLE_SECRET_VALUE": "An example has a non-placeholder sensitive value or a provider-shaped value; the value is not emitted.",
    "ENV_EXAMPLE_KEY_MISSING": "A key declared in the sibling key manifest is absent from the observed example.",
    "ENV_EXAMPLE_KEY_EXTRA": "An example key is absent from the sibling declared key manifest.",
    "ENV_EXAMPLE_KEYS_UNMEASURED": "No sibling declared key manifest was observed; key parity was not measured.",
}


def _noop():
    pass


def parse_example(text, *, checkpoint=_noop):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_EXAMPLE_BYTES or "\ufffd" in text:
        raise ValueError("example content unavailable or exceeds limit")
    result, lines = {}, {}
    for number, raw_line in enumerate(text.splitlines(), 1):
        checkpoint()
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("example line has no assignment")
        key, value = line.split("=", 1)
        if not KEY.fullmatch(key) or key in result:
            raise ValueError("example key invalid or duplicate")
        result[key], lines[key] = value, number
        if len(result) > MAX_KEYS:
            raise ValueError("example key limit exceeded")
    return result, lines


def _keys(keys, checkpoint):
    if not isinstance(keys, list) or len(keys) > MAX_KEYS:
        raise ValueError("declared keys must be a bounded list")
    seen = set()
    for key in keys:
        checkpoint()
        if not isinstance(key, str) or not KEY.fullmatch(key) or key in seen:
            raise ValueError("declared key invalid or duplicate")
        seen.add(key)
    return seen


def _compare(keys, example, checkpoint):
    expected = _keys(keys, checkpoint)
    observed = set(example)
    leaked = []
    for key, value in example.items():
        checkpoint()
        if (SENSITIVE_NAME.search(key) and value.casefold() not in PLACEHOLDERS) or SENSITIVE_VALUE.search(value):
            leaked.append(key)
    missing, extra = sorted(expected - observed), sorted(observed - expected)
    return dict(status="inconclusive" if not expected and not observed else
                "blocked" if missing or extra or leaked else "verified",
                missing=missing, extra=extra, leaked=sorted(leaked))


def compare_example(declared_keys, example_text):
    """Compare names declared by the caller; never read a live environment."""
    example, _ = parse_example(example_text)
    return _compare(declared_keys, example, _noop)


def _manifest(text, checkpoint):
    if text is None or len(text.encode("utf-8")) > MAX_MANIFEST_BYTES or "\ufffd" in text:
        raise ValueError("key manifest content unavailable or exceeds limit")
    def pairs(items):
        result = {}
        for key, value in items:
            checkpoint()
            if key in result:
                raise ValueError("duplicate manifest field")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("nonfinite manifest value")
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict) or set(value) != {"schema", "keys"} or value["schema"] != "repo-doctor/env-keys-v1":
        raise ValueError("key manifest shape or schema invalid")
    _keys(value["keys"], checkpoint)
    return value["keys"]


def _finding(code, file, digest, *, key=None, line=None, manifest_digest=None):
    unknown = code == "ENV_EXAMPLE_KEYS_UNMEASURED"
    evidence = ["scope=public-example-and-declared-key-list", "loaded_environment=not-observed",
                "example_text_sha256=" + digest]
    if manifest_digest is not None:
        evidence.append("key_manifest_text_sha256=" + manifest_digest)
    if key is not None:
        evidence.append("key=" + key)
    if unknown:
        evidence.append("key_parity=not-measured")
    return Finding(code, "secrets", "low" if unknown else "high", "inference" if unknown else "proof",
        HELP[code], "Use placeholders in the public example and review its sibling declared key list; validate loaded configuration separately.",
        safe_output_text(file.path), line, "; ".join(evidence))


def audit_env_examples(files):
    """One rule over the public example and exact canonical/legacy manifest names."""
    deadline, clock = getattr(files, "deadline", None), getattr(files, "clock", None)
    def checkpoint():
        if deadline is not None and clock is not None and clock() >= deadline:
            raise RegistryDeadlineExceeded([], ())
    scopes, total = {}, 0
    for file in files:
        checkpoint()
        path = PurePosixPath(file.path)
        if path.name not in {".env.example", *MANIFEST_NAMES}:
            continue
        if file.text is None:
            raise RegistryError("public environment observation unavailable: " + safe_output_text(file.path))
        total += len(file.text.encode("utf-8"))
        if total > MAX_TOTAL_BYTES:
            raise RegistryError("public environment observation total byte limit exceeded")
        group = scopes.setdefault(path.parent.as_posix(), {})
        if path.name in group:
            raise RegistryError("duplicate public environment observation path")
        group[path.name] = file
        if len(scopes) > MAX_SCOPES:
            raise RegistryError("public environment observation scope limit exceeded")
    for parent in sorted(scopes):
        checkpoint()
        group = scopes[parent]
        file = group.get(".env.example")
        manifests = [group[name] for name in MANIFEST_NAMES if name in group]
        manifest = manifests[0] if manifests else None
        if file is None:
            raise RegistryError("public environment example not observed beside declared key manifest")
        try:
            example, lines = parse_example(file.text, checkpoint=checkpoint)
            declared = [_manifest(item.text, checkpoint) for item in manifests]
            # The alias remains compatible, but cannot silently disagree with
            # the canonical list. Validate both before selecting evidence.
            if len(declared) == 2 and set(declared[0]) != set(declared[1]):
                raise ValueError("declared key manifests disagree")
            keys = declared[0] if declared else list(example)
            result = _compare(keys, example, checkpoint)
        except (ValueError, TypeError, RecursionError):
            raise RegistryError("public environment observation invalid: " + safe_output_text(file.path)) from None
        if result["status"] == "inconclusive":
            raise RegistryError("public environment observation is empty and inconclusive")
        digest = hashlib.sha256(file.text.encode("utf-8")).hexdigest()
        manifest_digest = hashlib.sha256(manifest.text.encode("utf-8")).hexdigest() if manifest else None
        for kind, code in (("leaked", "ENV_EXAMPLE_SECRET_VALUE"), ("missing", "ENV_EXAMPLE_KEY_MISSING"), ("extra", "ENV_EXAMPLE_KEY_EXTRA")):
            for key in result[kind]:
                checkpoint()
                yield _finding(code, file, digest, key=key, line=lines.get(key), manifest_digest=manifest_digest)
        if manifest is None:
            yield _finding("ENV_EXAMPLE_KEYS_UNMEASURED", file, digest)
