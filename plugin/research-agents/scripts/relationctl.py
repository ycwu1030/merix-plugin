"""Validate and query the project relation registry."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import date
import json
from pathlib import Path
import sys
import tempfile


RELATION_TYPES = {
    "depends_on",
    "has_work_package",
    "executes",
    "consumes",
    "produces",
    "documents",
    "governs",
    "successor_of",
    "supersedes",
    "derived_from",
}
REQUIRED_FIELDS = {"id", "source", "relation", "target", "basis", "created", "updated"}


def load_registry(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON-compatible YAML registry {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("registry root must be an object")
    return data


def validate_registry(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    relations = data.get("relations")
    if not isinstance(relations, list):
        return errors + ["relations must be a list"]
    ids: set[str] = set()
    declared_edges: set[tuple[str, str, str]] = set()
    for index, item in enumerate(relations):
        prefix = f"relations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - set(item))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
        relation_id = item.get("id")
        if not isinstance(relation_id, str) or not relation_id:
            errors.append(f"{prefix}.id must be a non-empty string")
        elif relation_id in ids:
            errors.append(f"{prefix}.id duplicates {relation_id}")
        else:
            ids.add(relation_id)
        for field in ("source", "target", "basis"):
            if not isinstance(item.get(field), str) or not item.get(field):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if not isinstance(item.get("relation"), str) or item.get("relation") not in RELATION_TYPES:
            errors.append(f"{prefix}.relation is not supported: {item.get('relation')}")
        for field in ("created", "updated"):
            try:
                date.fromisoformat(str(item.get(field)))
            except ValueError:
                errors.append(f"{prefix}.{field} must be YYYY-MM-DD")
        if item.get("source") == item.get("target"):
            errors.append(f"{prefix} cannot relate an entity to itself")
        if not all(isinstance(item.get(field), str) for field in ('source', 'relation', 'target')):
            continue
        edge = (item.get("source"), item.get("relation"), item.get("target"))
        if edge in declared_edges:
            errors.append(f"{prefix} duplicates relation edge {edge[0]} {edge[1]} {edge[2]}")
        declared_edges.add(edge)
    return errors


def edges(data: dict) -> list[dict]:
    return list(data.get("relations", []))


def connected(data: dict, entity: str) -> list[dict]:
    return [item for item in edges(data) if item["source"] == entity or item["target"] == entity]


def find_path(data: dict, source: str, target: str) -> list[dict] | None:
    queue: deque[tuple[str, list[dict]]] = deque([(source, [])])
    seen = {source}
    outgoing: dict[str, list[dict]] = {}
    for item in edges(data):
        outgoing.setdefault(item["source"], []).append(item)
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for edge in outgoing.get(node, []):
            if edge["target"] not in seen:
                seen.add(edge["target"])
                queue.append((edge["target"], path + [edge]))
    return None


def new_relation(data: dict, source: str, relation: str, target: str, basis: str, created: str) -> dict:
    next_number = 1 + max((int(item['id'].split('-')[-1]) for item in data['relations']
                           if item['id'].startswith('REL-') and item['id'].split('-')[-1].isdigit()), default=0)
    return {'id': f'REL-{next_number:04d}', 'source': source, 'relation': relation,
            'target': target, 'basis': basis, 'created': created, 'updated': created}


def write_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("relations/RELATIONS.yaml"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    show = subparsers.add_parser("show")
    show.add_argument("entity")
    path = subparsers.add_parser("path")
    path.add_argument("source")
    path.add_argument("target")
    add = subparsers.add_parser("add")
    add.add_argument("source")
    add.add_argument("relation", choices=sorted(RELATION_TYPES))
    add.add_argument("target")
    add.add_argument("--basis", required=True)
    add.add_argument("--reason", default="Explicit relation declared through relationctl")
    args = parser.parse_args(argv)
    try:
        data = load_registry(args.registry)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors = validate_registry(data)
    if args.command == "validate":
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            return 1
        print(f"relation registry valid: {len(edges(data))} relation(s)")
        return 0
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.command == "show":
        print(json.dumps(connected(data, args.entity), indent=2, ensure_ascii=False))
        return 0
    if args.command == "path":
        result = find_path(data, args.source, args.target)
        if result is None:
            print(f"no path: {args.source} -> {args.target}", file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "add":
        from workflow_relations import relation_operation
        from workflow_records import WorkflowError
        selected = args.registry.absolute()
        if selected.name != 'RELATIONS.yaml' or selected.parent.name != 'relations':
            print('error: writes require <project>/relations/RELATIONS.yaml', file=sys.stderr)
            return 1
        args.action, args.apply, args.date = 'add', True, date.today().isoformat()
        try:
            result = relation_operation(selected.parent.parent, args)
        except (WorkflowError, OSError) as exc:
            print(f'error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
