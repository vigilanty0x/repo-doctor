#!/usr/bin/env python3
import json
import sys
from pathlib import Path

EXPECTED_ROLES = [
    "onboard",
    "map",
    "inspect-state",
    "explore-events",
    "build-runbook",
    "record-postmortem",
    "publish-document",
]
EXPECTED_MODULES = {
    "codebase-onboarding-guide-generator": "onboard",
    "system-map-generator": "map",
    "state-machine-visualizer": "inspect-state",
    "event-log-explorer": "explore-events",
    "runbook-builder": "build-runbook",
    "failure-postmortem-kit": "record-postmortem",
    "document-factory": "publish-document",
}
REQUIRED_ARCHIVE_GATES = {
    "release",
    "compatibility",
    "consumers",
    "redirect",
    "rollback",
    "humanApproval",
}


def is_sha(value):
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def validate(data, root=Path(".")):
    errors = []
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if data.get("target") != "devdocs":
        errors.append("target must be devdocs")
    if data.get("state") != "REHEARSAL":
        errors.append("state must remain REHEARSAL until release gates pass")
    if data.get("scope") != "PUBLIC_ONLY":
        errors.append("scope must remain PUBLIC_ONLY")
    if not is_sha(data.get("governanceCommit")):
        errors.append("governanceCommit must be an exact 40-character SHA")
    if not is_sha(data.get("portfolioKitCommit")):
        errors.append("portfolioKitCommit must be an exact 40-character SHA")

    if data.get("experience") != EXPECTED_ROLES:
        errors.append("experience must preserve the canonical seven-step integration order")

    modules = data.get("modules")
    if not isinstance(modules, list) or len(modules) != 7:
        errors.append("modules must contain exactly seven imported modules")
    else:
        names = [module.get("repository") for module in modules]
        if len(set(names)) != 7 or set(names) != set(EXPECTED_MODULES):
            errors.append("module identities must match the audited seven-module DevDocs set")
        roles = [module.get("role") for module in modules]
        if roles != EXPECTED_ROLES:
            errors.append("module roles must match the canonical integration journey")
        for module in modules:
            name = module.get("repository", "<unknown>")
            role = module.get("role")
            if EXPECTED_MODULES.get(name) != role:
                errors.append(f"module {name} has the wrong integration role")
            expected_path = f"packages/{name}"
            if module.get("path") != expected_path:
                errors.append(f"module {name} must remain at {expected_path}")
            elif not (root / expected_path).is_dir():
                errors.append(f"module {name} path is missing from this checkout")
            if not is_sha(module.get("sourceHeadSha")) or not is_sha(module.get("sourceTreeSha")):
                errors.append(f"module {name} must retain exact source head/tree SHAs")
            if module.get("historyPreserved") is not True:
                errors.append(f"module {name} must retain historyPreserved=true")
            if module.get("treeMatch") is not True:
                errors.append(f"module {name} must retain treeMatch=true")

    archive = data.get("archive", {})
    if archive.get("automatic") is not False:
        errors.append("archive must never be automatic")
    if archive.get("gate") != "BLOCKED":
        errors.append("archive gate must remain BLOCKED during integration rehearsal")
    if set(archive.get("required", [])) != REQUIRED_ARCHIVE_GATES:
        errors.append("archive gates must include release, compatibility, consumers, redirect, rollback, and humanApproval")

    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        data = json.loads((root / "DEVDOCS.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: cannot load DEVDOCS.json: {exc}", file=sys.stderr)
        return 2
    errors = validate(data, root)
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    print("PASS: DevDocs integration contract is consistent; archive remains blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
