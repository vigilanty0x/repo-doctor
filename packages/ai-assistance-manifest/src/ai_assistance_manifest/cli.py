"""Command-line interface for the manifest standard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .io import ManifestLoadError, bundled_schema, bundled_template, dump_manifest, load_manifest
from .render import render_manifest
from .validation import validate_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aim", description="Validate and render AI assistance manifests.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a deterministic example manifest")
    init.add_argument("path", nargs="?", type=Path, default=Path("AI_ASSISTANCE.json"))
    init.add_argument("--force", action="store_true", help="replace an existing file")

    validate = subparsers.add_parser("validate", help="validate a manifest")
    validate.add_argument("path", nargs="?", type=Path, default=Path("AI_ASSISTANCE.json"))
    validate.add_argument("--root", type=Path, help="root for relative evidence paths")
    validate.add_argument("--check-files", action="store_true", help="require local evidence paths to exist")
    validate.add_argument("--format", choices=("text", "json"), default="text")

    render = subparsers.add_parser("render", help="render GitHub-flavored Markdown")
    render.add_argument("path", nargs="?", type=Path, default=Path("AI_ASSISTANCE.json"))
    render.add_argument("--output", "-o", type=Path, default=Path("AI_ASSISTANCE.md"))
    render.add_argument("--root", type=Path, help="root for relative evidence paths")
    render.add_argument("--check-files", action="store_true")

    schema = subparsers.add_parser("schema", help="print the bundled JSON Schema")
    schema.add_argument("--output", "-o", type=Path)
    return parser


def _load_or_report(path: Path) -> dict | None:
    try:
        return load_manifest(path)
    except ManifestLoadError as exc:
        print(f"AAM001 {path}: {exc}", file=sys.stderr)
        return None


def _run_init(args: argparse.Namespace) -> int:
    if args.path.exists() and not args.force:
        print(f"refusing to replace {args.path}; use --force", file=sys.stderr)
        return 2
    args.path.parent.mkdir(parents=True, exist_ok=True)
    args.path.write_text(dump_manifest(bundled_template()), encoding="utf-8")
    print(args.path)
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    manifest = _load_or_report(args.path)
    if manifest is None:
        return 2
    root = args.root or args.path.parent
    diagnostics = validate_manifest(manifest, root=root, check_files=args.check_files)
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [d.to_dict() for d in diagnostics]}, indent=2))
    elif diagnostics:
        for diagnostic in diagnostics:
            print(f"{diagnostic.code} {diagnostic.path}: {diagnostic.message}")
    else:
        print(f"valid: {args.path}")
    return 1 if diagnostics else 0


def _run_render(args: argparse.Namespace) -> int:
    manifest = _load_or_report(args.path)
    if manifest is None:
        return 2
    diagnostics = validate_manifest(
        manifest, root=args.root or args.path.parent, check_files=args.check_files
    )
    if diagnostics:
        for diagnostic in diagnostics:
            print(f"{diagnostic.code} {diagnostic.path}: {diagnostic.message}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_manifest(manifest), encoding="utf-8", newline="\n")
    print(args.output)
    return 0


def _run_schema(args: argparse.Namespace) -> int:
    text = bundled_schema()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print(args.output)
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "init":
        return _run_init(args)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "render":
        return _run_render(args)
    if args.command == "schema":
        return _run_schema(args)
    return 2

