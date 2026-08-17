#!/usr/bin/env python3
"""Build and exercise source, wheel, and sdist installations without network access."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
VERSION = PROJECT["version"]
NORMALIZED_DISTRIBUTION = PROJECT["name"].replace("-", "_")


def _run(
    command: list[str | Path],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    rendered = [str(item) for item in command]
    print("+", " ".join(rendered), flush=True)
    offline_environment = os.environ.copy()
    offline_environment["PIP_NO_INDEX"] = "1"
    offline_environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    offline_environment["PIP_NO_CACHE_DIR"] = "1"
    if env is not None:
        offline_environment.update(env)
    return subprocess.run(
        rendered,
        cwd=cwd,
        env=offline_environment,
        check=True,
        text=True,
        capture_output=capture,
    )


def _venv_python(environment: Path) -> Path:
    folder = "Scripts" if os.name == "nt" else "bin"
    name = "python.exe" if os.name == "nt" else "python"
    return environment / folder / name


def _venv_cli(environment: Path) -> Path:
    folder = "Scripts" if os.name == "nt" else "bin"
    name = "repo-doctor.exe" if os.name == "nt" else "repo-doctor"
    return environment / folder / name


def _wheel_payload(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: archive.read(name)
            for name in sorted(archive.namelist())
            if not name.endswith("/")
        }


def _smoke_install(label: str, target: Path, workspace: Path) -> None:
    environment = workspace / f"venv-{label}"
    # Python 3.11's ensurepip can seed an older setuptools into the venv. That
    # local copy shadows the pinned build tooling exposed through system site
    # packages and can reject modern PEP 639 metadata. Reuse the host's pinned
    # pip/setuptools instead of seeding version-dependent bundled copies.
    venv.EnvBuilder(with_pip=False, system_site_packages=True).create(environment)
    python = _venv_python(environment)
    cli = _venv_cli(environment)
    install = [
        python,
        "-m",
        "pip",
        "--disable-pip-version-check",
        "install",
        "--force-reinstall",
        "--no-deps",
    ]
    if target.is_dir() or target.suffix == ".gz":
        install.append("--no-build-isolation")
    install.append(target)
    _run(install, cwd=workspace)
    _run([python, "-m", "pip", "check"], cwd=workspace)
    version = _run([cli, "--version"], cwd=workspace, capture=True).stdout.strip()
    if version != f"repo-doctor {VERSION}":
        raise RuntimeError(f"{label} reported an unexpected version: {version}")

    rules = _run([cli, "rules", "--format", "json"], cwd=workspace, capture=True)
    if not json.loads(rules.stdout)["plugins"]:
        raise RuntimeError(f"{label} did not expose the installed plugin catalog")
    output = workspace / f"{label}-report.json"
    _run(
        [
            cli,
            "scan",
            ROOT / "examples" / "sample-repo",
            "--config",
            ROOT / "examples" / "repo-doctor.json",
            "--format",
            "json",
            "--output",
            output,
            "--fail-on",
            "high",
        ],
        cwd=workspace,
    )
    if json.loads(output.read_text(encoding="utf-8"))["status"] != "verified":
        raise RuntimeError(f"{label} installed scan was not verified")
    _run(
        [
            cli,
            "sbom",
            ROOT / "examples" / "sample-repo",
            "--config",
            ROOT / "examples" / "repo-doctor.json",
            "--output",
            workspace / f"{label}.cdx.json",
        ],
        cwd=workspace,
    )


def main() -> int:
    source_environment = os.environ.copy()
    source_environment["PYTHONPATH"] = str(ROOT / "src")
    source_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="repo-doctor-release-") as raw_workspace:
        workspace = Path(raw_workspace)
        artifacts = workspace / "artifacts"
        rebuilt = workspace / "rebuilt"
        artifacts.mkdir()
        rebuilt.mkdir()

        _run(
            [
                sys.executable,
                "-m",
                "repo_doctor_ai",
                "scan",
                ROOT,
                "--format",
                "json",
                "--output",
                workspace / "self-audit.json",
                "--fail-on",
                "critical",
            ],
            cwd=workspace,
            env=source_environment,
        )
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ROOT,
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                artifacts,
            ],
            cwd=workspace,
        )
        _run(
            [
                sys.executable,
                "-c",
                "from setuptools.build_meta import build_sdist; "
                "import sys; build_sdist(sys.argv[1])",
                artifacts,
            ],
            cwd=ROOT,
        )
        wheel = artifacts / f"{NORMALIZED_DISTRIBUTION}-{VERSION}-py3-none-any.whl"
        sdist = artifacts / f"{NORMALIZED_DISTRIBUTION}-{VERSION}.tar.gz"
        if not wheel.is_file() or not sdist.is_file():
            raise RuntimeError("release build did not produce the expected wheel and sdist")
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                sdist,
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                rebuilt,
            ],
            cwd=workspace,
        )
        rebuilt_wheel = rebuilt / wheel.name
        if _wheel_payload(wheel) != _wheel_payload(rebuilt_wheel):
            raise RuntimeError("direct wheel and sdist-derived wheel contents differ")

        _smoke_install("source", ROOT, workspace)
        _smoke_install("wheel", wheel, workspace)
        _smoke_install("sdist", sdist, workspace)

        summary = {
            "version": VERSION,
            "source": "passed",
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "sdist": sdist.name,
            "sdist_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
            "wheel_sdist_content_parity": "passed",
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
