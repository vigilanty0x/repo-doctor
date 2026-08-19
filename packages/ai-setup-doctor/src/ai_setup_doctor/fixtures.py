"""Strict synthetic fixtures for reproducible, account-free demonstrations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .checks import ExecutionResult, Executor, ToolSpec
from .models import ContractError


ALLOWED_BEHAVIORS = {"success", "nonzero", "timeout", "permission_denied", "execution_error"}


@dataclass(frozen=True, slots=True)
class FixtureBehavior:
    kind: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FixtureBehavior":
        allowed = {"kind", "stdout", "stderr", "exit_code"}
        if set(value) - allowed:
            raise ContractError("fixture behavior contains unknown fields")
        try:
            behavior = cls(
                kind=value["kind"],
                stdout=value.get("stdout", ""),
                stderr=value.get("stderr", ""),
                exit_code=value.get("exit_code", 0),
            )
        except (KeyError, TypeError) as exc:
            raise ContractError(f"invalid fixture behavior: {exc}") from exc
        if behavior.kind not in ALLOWED_BEHAVIORS:
            raise ContractError(f"unsupported fixture behavior: {behavior.kind!r}")
        if not isinstance(behavior.stdout, str) or len(behavior.stdout) > 4096:
            raise ContractError("fixture stdout is invalid")
        if not isinstance(behavior.stderr, str) or len(behavior.stderr) > 4096:
            raise ContractError("fixture stderr is invalid")
        if not isinstance(behavior.exit_code, int) or not -255 <= behavior.exit_code <= 255:
            raise ContractError("fixture exit_code is invalid")
        return behavior


@dataclass(frozen=True, slots=True)
class FixtureTool:
    spec: ToolSpec
    present: bool
    behavior: FixtureBehavior


class FixtureExecutor(Executor):
    def __init__(self, behaviors: Mapping[str, FixtureBehavior]) -> None:
        self._behaviors = dict(behaviors)
        self.calls: list[tuple[str, tuple[str, ...], float]] = []

    def run(self, executable: str, args: Sequence[str], timeout_seconds: float) -> ExecutionResult:
        self.calls.append((executable, tuple(args), timeout_seconds))
        behavior = self._behaviors.get(executable)
        if behavior is None:
            raise OSError("synthetic executable is not configured")
        if behavior.kind == "timeout":
            raise subprocess.TimeoutExpired([executable, *args], timeout_seconds)
        if behavior.kind == "permission_denied":
            raise PermissionError("synthetic permission denial")
        if behavior.kind == "execution_error":
            raise OSError("synthetic execution failure")
        exit_code = behavior.exit_code if behavior.kind == "nonzero" else 0
        return ExecutionResult(exit_code, behavior.stdout, behavior.stderr)


@dataclass(slots=True)
class FixtureEnvironment:
    specs: tuple[ToolSpec, ...]
    paths: dict[str, str]
    executor: FixtureExecutor

    def finder(self, command: str) -> str | None:
        return self.paths.get(command)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FixtureEnvironment":
        if set(value) != {"schema_version", "tools"}:
            raise ContractError("fixture fields do not match schema 1.0")
        if value["schema_version"] != "1.0":
            raise ContractError("unsupported fixture schema_version")
        tools = value["tools"]
        if not isinstance(tools, list) or not 1 <= len(tools) <= 64:
            raise ContractError("fixture tools must be a list of 1 to 64 entries")
        specs: list[ToolSpec] = []
        paths: dict[str, str] = {}
        behaviors: dict[str, FixtureBehavior] = {}
        names: set[str] = set()
        commands: set[str] = set()
        for item in tools:
            if not isinstance(item, dict) or set(item) != {
                "name", "command", "version_args", "timeout_seconds", "present", "behavior"
            }:
                raise ContractError("fixture tool fields do not match schema 1.0")
            spec = ToolSpec(
                item["name"], item["command"], tuple(item["version_args"]), item["timeout_seconds"]
            )
            if spec.name.casefold() in names or spec.command in commands:
                raise ContractError("fixture tool names and commands must be unique")
            if not isinstance(item["present"], bool):
                raise ContractError("fixture present must be boolean")
            names.add(spec.name.casefold())
            commands.add(spec.command)
            specs.append(spec)
            behavior = FixtureBehavior.from_dict(item["behavior"])
            if item["present"]:
                path = f"/synthetic/bin/{spec.command}"
                paths[spec.command] = path
                behaviors[path] = behavior
        return cls(tuple(specs), paths, FixtureExecutor(behaviors))

    @classmethod
    def load(cls, path: Path) -> "FixtureEnvironment":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"fixture could not be read: {exc}") from exc
        if not isinstance(value, dict):
            raise ContractError("fixture root must be an object")
        return cls.from_dict(value)

