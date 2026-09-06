"""Exercise AI Assistance Manifest CLI success, diagnostic, and parse-error paths."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "ai_assistance_manifest", *args], capture_output=True, text=True, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aim-counterproof-") as tmp:
        root = Path(tmp)
        valid = root / "valid.json"
        created = run("init", str(valid))
        if created.returncode != 0 or not valid.is_file():
            raise SystemExit(f"positive init failed: {created.returncode}: {created.stderr}")
        checked = run("validate", str(valid))
        if checked.returncode != 0:
            raise SystemExit(f"positive validation failed: {checked.returncode}: {checked.stdout} {checked.stderr}")

        value = json.loads(valid.read_text(encoding="utf-8"))
        # Removing a required top-level field produces validation diagnostics,
        # which is the documented semantic-invalid exit class (1).
        required = next((key for key in ("manifest_version", "schema_version", "project") if key in value), None)
        if required is None:
            required = next(iter(value))
        value.pop(required)
        invalid = root / "invalid.json"
        invalid.write_text(json.dumps(value), encoding="utf-8")
        diagnosed = run("validate", str(invalid))
        if diagnosed.returncode != 1:
            raise SystemExit(f"semantic counter-proof expected exit 1, got {diagnosed.returncode}: {diagnosed.stdout} {diagnosed.stderr}")

        malformed = root / "malformed.json"
        malformed.write_text('{"broken":', encoding="utf-8")
        parsed = run("validate", str(malformed))
        if parsed.returncode != 2:
            raise SystemExit(f"parse counter-proof expected exit 2, got {parsed.returncode}: {parsed.stdout} {parsed.stderr}")

    print("manifest CLI positive/diagnostic/parse counter-proof verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
