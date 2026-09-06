"""Dependency-free semantic validation for AI Assistance Manifest 1.0."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .diagnostics import Diagnostic
from .security import find_suspected_secrets, is_safe_relative_path

TOP_LEVEL_FIELDS = {
    "$schema",
    "schema_version",
    "project",
    "assistance",
    "models",
    "contributions",
    "evidence",
    "limitations",
    "decisions",
    "incidents",
}
REQUIRED_FIELDS = {
    "schema_version",
    "project",
    "assistance",
    "models",
    "contributions",
    "evidence",
    "limitations",
}
AUTONOMY_LEVELS = {"assistive", "collaborative", "agentic"}
EVIDENCE_TYPES = {"file", "test", "report", "commit", "url"}
EVIDENCE_STATUSES = {"verified", "inferred", "blocked", "unknown"}
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _error(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def _require_object(
    value: Any, path: str, diagnostics: list[Diagnostic]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        diagnostics.append(_error("AAM101", path, "must be an object"))
        return None
    return value


def _require_list(
    value: Any, path: str, diagnostics: list[Diagnostic], *, non_empty: bool = False
) -> list[Any] | None:
    if not isinstance(value, list):
        diagnostics.append(_error("AAM102", path, "must be an array"))
        return None
    if non_empty and not value:
        diagnostics.append(_error("AAM103", path, "must not be empty"))
    return value


def _required_string(
    obj: dict[str, Any], key: str, path: str, diagnostics: list[Diagnostic]
) -> str | None:
    value = obj.get(key)
    field_path = f"{path}.{key}"
    if not isinstance(value, str) or not value.strip():
        diagnostics.append(_error("AAM104", field_path, "must be a non-empty string"))
        return None
    return value


def _string_array(
    value: Any, path: str, diagnostics: list[Diagnostic], *, non_empty: bool = False
) -> list[str] | None:
    items = _require_list(value, path, diagnostics, non_empty=non_empty)
    if items is None:
        return None
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            diagnostics.append(
                _error("AAM104", f"{path}[{index}]", "must be a non-empty string")
            )
    return [item for item in items if isinstance(item, str) and item.strip()]


def _validate_project(manifest: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
    project = _require_object(manifest.get("project"), "$.project", diagnostics)
    if project is None:
        return
    _required_string(project, "name", "$.project", diagnostics)
    owners = _require_list(project.get("owners"), "$.project.owners", diagnostics, non_empty=True)
    if owners is not None:
        for index, owner_value in enumerate(owners):
            owner = _require_object(owner_value, f"$.project.owners[{index}]", diagnostics)
            if owner is not None:
                _required_string(owner, "name", f"$.project.owners[{index}]", diagnostics)


def _validate_assistance(manifest: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
    assistance = _require_object(manifest.get("assistance"), "$.assistance", diagnostics)
    if assistance is None:
        return
    _required_string(assistance, "summary", "$.assistance", diagnostics)
    autonomy = _required_string(assistance, "autonomy", "$.assistance", diagnostics)
    if autonomy and autonomy not in AUTONOMY_LEVELS:
        diagnostics.append(
            _error("AAM201", "$.assistance.autonomy", f"must be one of {sorted(AUTONOMY_LEVELS)}")
        )
    review = _require_object(
        assistance.get("human_review"), "$.assistance.human_review", diagnostics
    )
    if review is not None:
        if not isinstance(review.get("required"), bool):
            diagnostics.append(
                _error("AAM105", "$.assistance.human_review.required", "must be a boolean")
            )
        _required_string(
            review, "final_authority", "$.assistance.human_review", diagnostics
        )


def _validate_models(
    manifest: dict[str, Any], diagnostics: list[Diagnostic]
) -> set[str]:
    models = _require_list(manifest.get("models"), "$.models", diagnostics, non_empty=True)
    ids: set[str] = set()
    if models is None:
        return ids
    for index, model_value in enumerate(models):
        path = f"$.models[{index}]"
        model = _require_object(model_value, path, diagnostics)
        if model is None:
            continue
        model_id = _required_string(model, "id", path, diagnostics)
        _required_string(model, "provider", path, diagnostics)
        _required_string(model, "name", path, diagnostics)
        _string_array(model.get("roles"), f"{path}.roles", diagnostics, non_empty=True)
        if model_id:
            if model_id in ids:
                diagnostics.append(_error("AAM202", f"{path}.id", "duplicate model id"))
            ids.add(model_id)
    return ids


def _validate_evidence(
    manifest: dict[str, Any], diagnostics: list[Diagnostic], root: Path, check_files: bool
) -> set[str]:
    evidence = _require_list(manifest.get("evidence"), "$.evidence", diagnostics)
    ids: set[str] = set()
    if evidence is None:
        return ids
    root = root.resolve()
    for index, evidence_value in enumerate(evidence):
        path = f"$.evidence[{index}]"
        item = _require_object(evidence_value, path, diagnostics)
        if item is None:
            continue
        item_id = _required_string(item, "id", path, diagnostics)
        item_type = _required_string(item, "type", path, diagnostics)
        status = _required_string(item, "status", path, diagnostics)
        location = _required_string(item, "location", path, diagnostics)
        _required_string(item, "description", path, diagnostics)
        if item_id:
            if item_id in ids:
                diagnostics.append(_error("AAM203", f"{path}.id", "duplicate evidence id"))
            ids.add(item_id)
        if item_type and item_type not in EVIDENCE_TYPES:
            diagnostics.append(
                _error("AAM204", f"{path}.type", f"must be one of {sorted(EVIDENCE_TYPES)}")
            )
        if status and status not in EVIDENCE_STATUSES:
            diagnostics.append(
                _error("AAM205", f"{path}.status", f"must be one of {sorted(EVIDENCE_STATUSES)}")
            )
        if not item_type or not location:
            continue
        if item_type == "url":
            parsed = urlparse(location)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
            ):
                diagnostics.append(_error("AAM301", f"{path}.location", "must be an HTTP(S) URL"))
        elif item_type == "commit":
            if not COMMIT_RE.fullmatch(location):
                diagnostics.append(_error("AAM302", f"{path}.location", "must be a 7-64 digit Git commit hash"))
        else:
            if not is_safe_relative_path(location):
                diagnostics.append(_error("AAM303", f"{path}.location", "must be a safe relative path"))
            elif check_files:
                try:
                    candidate = (root / location).resolve()
                    candidate.relative_to(root)
                    exists = candidate.exists()
                except (OSError, ValueError):
                    diagnostics.append(
                        _error("AAM303", f"{path}.location", "must remain inside the repository root")
                    )
                else:
                    if not exists:
                        diagnostics.append(
                            _error("AAM304", f"{path}.location", "referenced path does not exist")
                        )
    return ids


def _validate_contributions(
    manifest: dict[str, Any],
    diagnostics: list[Diagnostic],
    model_ids: set[str],
    evidence_ids: set[str],
) -> None:
    contributions = _require_object(
        manifest.get("contributions"), "$.contributions", diagnostics
    )
    if contributions is None:
        return
    humans = _require_list(contributions.get("human"), "$.contributions.human", diagnostics, non_empty=True)
    if humans is not None:
        for index, human_value in enumerate(humans):
            path = f"$.contributions.human[{index}]"
            human = _require_object(human_value, path, diagnostics)
            if human is not None:
                _required_string(human, "actor", path, diagnostics)
                _string_array(human.get("roles"), f"{path}.roles", diagnostics, non_empty=True)
                _string_array(human.get("decisions"), f"{path}.decisions", diagnostics, non_empty=True)
    ai_items = _require_list(contributions.get("ai"), "$.contributions.ai", diagnostics, non_empty=True)
    contribution_ids: set[str] = set()
    if ai_items is None:
        return
    for index, ai_value in enumerate(ai_items):
        path = f"$.contributions.ai[{index}]"
        item = _require_object(ai_value, path, diagnostics)
        if item is None:
            continue
        contribution_id = _required_string(item, "id", path, diagnostics)
        model_ref = _required_string(item, "model_ref", path, diagnostics)
        _string_array(item.get("tasks"), f"{path}.tasks", diagnostics, non_empty=True)
        artifacts = _string_array(
            item.get("artifacts"), f"{path}.artifacts", diagnostics, non_empty=True
        )
        refs = _string_array(item.get("evidence_refs"), f"{path}.evidence_refs", diagnostics)
        _required_string(item, "reviewed_by", path, diagnostics)
        if contribution_id:
            if contribution_id in contribution_ids:
                diagnostics.append(_error("AAM206", f"{path}.id", "duplicate contribution id"))
            contribution_ids.add(contribution_id)
        if model_ref and model_ref not in model_ids:
            diagnostics.append(_error("AAM207", f"{path}.model_ref", "unknown model id"))
        for artifact_index, artifact in enumerate(artifacts or []):
            if not is_safe_relative_path(artifact):
                diagnostics.append(
                    _error(
                        "AAM303",
                        f"{path}.artifacts[{artifact_index}]",
                        "must be a safe relative path",
                    )
                )
        for ref_index, ref in enumerate(refs or []):
            if ref not in evidence_ids:
                diagnostics.append(
                    _error("AAM208", f"{path}.evidence_refs[{ref_index}]", "unknown evidence id")
                )


def validate_manifest(
    manifest: dict[str, Any], *, root: Path | None = None, check_files: bool = False
) -> list[Diagnostic]:
    """Validate structure, cross-references, paths, and obvious secret leaks."""

    diagnostics: list[Diagnostic] = []
    root = root or Path.cwd()
    unknown = sorted(
        key for key in manifest if key not in TOP_LEVEL_FIELDS and not key.startswith("x-")
    )
    for key in unknown:
        diagnostics.append(_error("AAM106", f"$.{key}", "unknown top-level field"))
    for key in sorted(REQUIRED_FIELDS - manifest.keys()):
        diagnostics.append(_error("AAM100", f"$.{key}", "required field is missing"))
    if manifest.get("schema_version") != "1.0":
        diagnostics.append(_error("AAM200", "$.schema_version", 'must equal "1.0"'))

    _validate_project(manifest, diagnostics)
    _validate_assistance(manifest, diagnostics)
    model_ids = _validate_models(manifest, diagnostics)
    evidence_ids = _validate_evidence(manifest, diagnostics, root, check_files)
    _validate_contributions(manifest, diagnostics, model_ids, evidence_ids)
    _string_array(manifest.get("limitations"), "$.limitations", diagnostics, non_empty=True)
    if "decisions" in manifest:
        _string_array(manifest["decisions"], "$.decisions", diagnostics)
    if "incidents" in manifest:
        _string_array(manifest["incidents"], "$.incidents", diagnostics)
    diagnostics.extend(find_suspected_secrets(manifest))
    return sorted(set(diagnostics))
