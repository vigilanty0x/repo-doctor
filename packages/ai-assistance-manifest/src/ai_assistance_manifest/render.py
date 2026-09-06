"""Deterministic GitHub-flavored Markdown rendering."""

from __future__ import annotations

from typing import Any


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None declared."]


def render_manifest(manifest: dict[str, Any]) -> str:
    """Render a manifest without timestamps or environment-dependent values."""

    project = manifest["project"]
    assistance = manifest["assistance"]
    lines = [
        "# AI Assistance Manifest",
        "",
        f"**Project:** {_escape(project['name'])}",
        f"**Manifest version:** {_escape(manifest['schema_version'])}",
    ]
    if project.get("version"):
        lines.append(f"**Project version:** {_escape(project['version'])}")
    if project.get("repository"):
        lines.append(f"**Repository:** {project['repository']}")
    lines.extend(["", assistance["summary"], "", "## Human oversight", ""])
    review = assistance["human_review"]
    lines.extend(
        [
            f"- Autonomy level: `{_escape(assistance['autonomy'])}`",
            f"- Human review required: `{'yes' if review['required'] else 'no'}`",
            f"- Final authority: {_escape(review['final_authority'])}",
            "",
            "### Owners",
            "",
        ]
    )
    for owner in project["owners"]:
        suffix = f" — {_escape(owner['role'])}" if owner.get("role") else ""
        lines.append(f"- {_escape(owner['name'])}{suffix}")

    lines.extend(["", "## Models and systems", "", "| ID | Provider | Model | Roles |", "|---|---|---|---|"])
    for model in manifest["models"]:
        lines.append(
            f"| `{_escape(model['id'])}` | {_escape(model['provider'])} | "
            f"{_escape(model['name'])} | {_escape(', '.join(model['roles']))} |"
        )

    lines.extend(["", "## Human contributions", ""])
    for item in manifest["contributions"]["human"]:
        lines.append(f"### {_escape(item['actor'])}")
        lines.append("")
        lines.append(f"**Roles:** {_escape(', '.join(item['roles']))}")
        lines.append("")
        lines.extend(_bullets(item["decisions"]))
        lines.append("")

    lines.extend(["## AI contributions", ""])
    for item in manifest["contributions"]["ai"]:
        lines.extend(
            [
                f"### `{_escape(item['id'])}`",
                "",
                f"- Model reference: `{_escape(item['model_ref'])}`",
                f"- Reviewed by: {_escape(item['reviewed_by'])}",
                f"- Tasks: {_escape('; '.join(item['tasks']))}",
                f"- Artifacts: {_escape(', '.join(item['artifacts']))}",
                f"- Evidence: {_escape(', '.join(item['evidence_refs']) or 'none')}",
                "",
            ]
        )

    lines.extend(["## Evidence", "", "| ID | Type | Status | Location | Description |", "|---|---|---|---|---|"])
    for item in manifest["evidence"]:
        location = item["location"]
        rendered_location = (
            f"[{_escape(location)}]({location})" if item["type"] == "url" else f"`{_escape(location)}`"
        )
        lines.append(
            f"| `{_escape(item['id'])}` | {_escape(item['type'])} | "
            f"`{_escape(item['status'])}` | {rendered_location} | {_escape(item['description'])} |"
        )

    lines.extend(["", "## Limitations", ""])
    lines.extend(_bullets(manifest["limitations"]))
    for key, heading in (("decisions", "Decisions"), ("incidents", "Incidents and blocked states")):
        if key in manifest:
            lines.extend(["", f"## {heading}", ""])
            lines.extend(_bullets(manifest[key]))
    lines.extend(
        [
            "",
            "---",
            "",
            "This document is generated from `AI_ASSISTANCE.json`. Edit the manifest, not this file.",
            "",
        ]
    )
    return "\n".join(lines)

