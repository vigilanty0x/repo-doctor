"""Bounded metadata-only comparison of expected and observed backup manifests."""

import argparse
import hashlib
import json
import re
from pathlib import PurePosixPath

HEX64 = re.compile(r"[0-9a-f]{64}")
MAX_FILES = 10_000
MAX_FILE_BYTES = 1_000_000_000_000
MAX_TOTAL_BYTES = 10_000_000_000_000


def _safe_path(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 512 or "\\" in value
            or any(ord(c) < 32 for c in value)):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and value not in {".", ".."} and ".." not in path.parts and path.as_posix() == value


def _validate_manifest(value):
    if not isinstance(value, dict) or len(value) > MAX_FILES:
        return None
    clean, total = {}, 0
    for path, entry in value.items():
        if (not _safe_path(path) or not isinstance(entry, dict)
                or set(entry) != {"sha256", "size"}):
            return None
        digest, size = entry["sha256"], entry["size"]
        if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
                or not isinstance(size, int) or isinstance(size, bool)
                or not 0 <= size <= MAX_FILE_BYTES):
            return None
        total += size
        if total > MAX_TOTAL_BYTES:
            return None
        clean[path] = {"sha256": digest, "size": size}
    return clean


def verify(expected, observed, *, expected_manifest_trusted=False):
    """Compare metadata; caller decides whether the expected manifest is trusted."""
    if not isinstance(expected_manifest_trusted, bool):
        return {"verified": False, "metadata_match": False, "errors": ["invalid_trust_flag"],
                "verification_scope": "metadata_only", "expected_manifest_trusted": False}
    expected_clean, observed_clean = _validate_manifest(expected), _validate_manifest(observed)
    if expected_clean is None or observed_clean is None:
        return {"verified": False, "metadata_match": False, "errors": ["invalid_manifest"],
                "verification_scope": "metadata_only",
                "expected_manifest_trusted": expected_manifest_trusted}
    errors = []
    for path, wanted in sorted(expected_clean.items()):
        got = observed_clean.get(path)
        if got is None:
            errors.append({"path": path, "error": "missing"})
        elif got != wanted:
            errors.append({"path": path, "error": "mismatch"})
    for path in sorted(set(observed_clean) - set(expected_clean)):
        errors.append({"path": path, "error": "unexpected"})
    body = {"expected": expected_clean, "observed": observed_clean, "errors": errors}
    match = not errors
    return {"verified": match, "metadata_match": match, "errors": errors,
            "verification_scope": "metadata_only",
            "expected_manifest_trusted": expected_manifest_trusted,
            "claim": "trusted_expected_metadata_match" if match and expected_manifest_trusted
                     else "untrusted_expected_metadata_match" if match else "metadata_mismatch",
            "evidence_sha256": hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def probe():
    manifest = {"a": {"sha256": "a" * 64, "size": 1}}
    good, bad = verify(manifest, manifest, expected_manifest_trusted=True), verify(manifest, {})
    return {"ok": good["verified"] and not bad["verified"], "counter_proof": not bad["verified"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify", "probe"))
    parser.add_argument("--input")
    parser.add_argument("--expected-manifest-trusted", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.load(open(args.input, encoding="utf-8")) if args.input else {}
        out = probe() if args.command == "probe" else verify(
            data.get("expected") if isinstance(data, dict) else None,
            data.get("observed") if isinstance(data, dict) else None,
            expected_manifest_trusted=args.expected_manifest_trusted)
    except (OSError, UnicodeError, json.JSONDecodeError):
        out = {"verified": False, "errors": ["input_unreadable"]}
    print(json.dumps(out, sort_keys=True))
    return 0 if out.get("ok", out.get("verified", False)) else 2
