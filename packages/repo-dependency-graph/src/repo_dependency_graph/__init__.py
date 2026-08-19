"""Validate and analyze bounded, caller-declared repository dependency graphs."""

import argparse
import hashlib
import heapq
import json
import re

NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
MAX_REPOSITORIES = 500
MAX_EDGES = 5_000


def _cycle(adj, names):
    state, stack = {}, []

    def visit(node):
        state[node] = 1
        stack.append(node)
        for dependency in adj[node]:
            if state.get(dependency, 0) == 0:
                found = visit(dependency)
                if found:
                    return found
            elif state[dependency] == 1:
                return stack[stack.index(dependency):] + [dependency]
        stack.pop()
        state[node] = 2
        return None

    for name in sorted(names):
        if state.get(name, 0) == 0:
            found = visit(name)
            if found:
                return found
    return None


def graph(data):
    if not isinstance(data, dict) or set(data) != {"repositories"}:
        return {"ok": False, "errors": ["invalid_input"]}
    repositories = data["repositories"]
    if not isinstance(repositories, list) or len(repositories) > MAX_REPOSITORIES:
        return {"ok": False, "errors": ["repository_bound"]}
    names = []
    for repository in repositories:
        if (not isinstance(repository, dict) or set(repository) != {"name", "dependencies"}
                or not isinstance(repository["name"], str) or not NAME.fullmatch(repository["name"])
                or repository["name"] in names):
            return {"ok": False, "errors": ["invalid_names_or_entry"]}
        names.append(repository["name"])
    known, edges = set(names), []
    for repository in repositories:
        dependencies = repository["dependencies"]
        if (not isinstance(dependencies, list)
                or any(not isinstance(item, str) or item not in known for item in dependencies)
                or len(dependencies) != len(set(dependencies))):
            return {"ok": False, "errors": ["unknown_or_duplicate_dependency"]}
        edges.extend((repository["name"], dependency) for dependency in dependencies)
        if len(edges) > MAX_EDGES:
            return {"ok": False, "errors": ["edge_bound"]}
    edges.sort()
    adj = {name: [] for name in names}
    indegree = {name: 0 for name in names}
    dependents = {name: [] for name in names}
    for source, dependency in edges:
        adj[source].append(dependency)
        dependents[dependency].append(source)
        indegree[source] += 1
    for values in adj.values():
        values.sort()
    for values in dependents.values():
        values.sort()
    ready = [name for name in names if indegree[name] == 0]
    heapq.heapify(ready)
    topology = []
    while ready:
        node = heapq.heappop(ready)
        topology.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    cycle = _cycle(adj, names) if len(topology) != len(names) else None
    opaque = {name: f"repo_{index:03d}" for index, name in enumerate(sorted(names))}
    lines = ["digraph repositories {"]
    lines.extend(f'  {opaque[name]} [label={json.dumps(name)}];' for name in sorted(names))
    lines.extend(f"  {opaque[source]} -> {opaque[dependency]};" for source, dependency in edges)
    lines.append("}")
    body = {"nodes": sorted(names), "edges": [list(edge) for edge in edges],
            "cycle": cycle, "topological_order": topology if cycle is None else [],
            "dot": "\n".join(lines), "acyclic": cycle is None,
            "scope": "declared_input_only", "external_dependencies_verified": False}
    return {"ok": True, **body,
            "graph_sha256": hashlib.sha256(json.dumps(body, sort_keys=True,
                                                        separators=(",", ":")).encode()).hexdigest()}


def probe():
    good = graph({"repositories": [{"name": "a", "dependencies": []}]})
    bad = graph({"repositories": [{"name": "a", "dependencies": ["missing"]}]})
    return {"ok": good["ok"] and not bad["ok"], "unknown_counter_proof": not bad["ok"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("graph", "probe"))
    parser.add_argument("--input")
    args = parser.parse_args(argv)
    try:
        data = json.load(open(args.input, encoding="utf-8")) if args.input else None
        out = probe() if args.command == "probe" else graph(data)
    except (OSError, UnicodeError, json.JSONDecodeError):
        out = {"ok": False, "errors": ["input_unreadable"]}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 2
