from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from .catalog import ROOT_REQUIRED_DIRS, ROOT_STANDARD_EXTRA_DIRS, ROOT_STANDARD_EXTRA_ROLES
from .common import plan_digest
from .root_transaction import RootWrite, apply_writes, path_state

MANIFEST = "BASELINE_MANIFEST.md"
MANIFEST_MARKER = "<!-- research-baseline-manifest:v1 -->"
INVENTORY_ROOT = ".baseline/inventory"
CURRENT_INVENTORY = f"{INVENTORY_ROOT}/current.json"
PREVIOUS_INVENTORY = f"{INVENTORY_ROOT}/previous.json"
PACKAGE_FILES = ("AGENTS.md", "RESEARCH_WORKFLOW.md")

MIXED_SPECS: dict[str, tuple[tuple[str, str], ...]] = {
    "README.md": (("start-here", "START-HERE"),),
    "PROJECT_CONTEXT.md": (("optional-modules", "INITIALIZER-MANAGED OPTIONAL MODULES"),),
    "PROJECT_STATUS.md": (("control-panel", "CONTROL-PANEL"),),
}
MIXED_TEMPLATE_PATHS = {name: f"templates/{name}" for name in MIXED_SPECS}
DECISION_CHOICES = {"accept-candidate", "preserve-local", "skip", "manual-migration"}


@dataclass(frozen=True)
class BaselinePlan:
    payload: dict[str, Any]
    plan_id: str
    plan_file: Path | None = None

    @property
    def outcome(self) -> str:
        return self.payload["outcome"]


def _git_identity(source: Path) -> dict[str, str]:
    try:
        revision = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=False, capture_output=True, text=True,
        )
        dirty = subprocess.run(
            ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"],
            check=False, capture_output=True, text=True,
        )
    except OSError:
        return {"type": "local-snapshot", "revision": "unavailable", "state": "unknown"}
    if revision.returncode != 0 or not revision.stdout.strip():
        return {"type": "local-snapshot", "revision": "unavailable", "state": "unversioned"}
    return {"type": "git-commit", "revision": revision.stdout.strip(), "state": "dirty" if dirty.stdout.strip() else "clean"}


def _source_files(source: Path) -> list[tuple[str, Path]]:
    result = [(name, source / name) for name in PACKAGE_FILES]
    template_root = source / "templates"
    result.extend(
        (path.relative_to(source).as_posix(), path)
        for path in sorted(template_root.rglob("*"))
        if path.is_file()
    )
    return result


def _digest_entries(entries: list[dict[str, Any]]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + sha256(payload.encode()).hexdigest()


def _region_markers(region_id: str, token: str) -> tuple[str, str]:
    if token == "INITIALIZER-MANAGED OPTIONAL MODULES":
        return ("<!-- BEGIN INITIALIZER-MANAGED OPTIONAL MODULES v1 -->", "<!-- END INITIALIZER-MANAGED OPTIONAL MODULES v1 -->")
    return (f"<!-- BEGIN BASELINE-MANAGED {token} v1 -->", f"<!-- END BASELINE-MANAGED {token} v1 -->")


def _extract_regions(text: str, path: str) -> dict[str, str]:
    regions: dict[str, str] = {}
    for region_id, token in MIXED_SPECS[path]:
        begin, end = _region_markers(region_id, token)
        matches = list(re.finditer(re.escape(begin) + r"\n?(.*?)\n?" + re.escape(end), text, re.S))
        if len(matches) != 1:
            raise ValueError(f"{path}: expected exactly one managed region {region_id}")
        regions[region_id] = matches[0].group(1)
    return regions


def _region_entries(path: str, content: bytes, *, source_path: str, ownership: str) -> list[dict[str, Any]]:
    regions = _extract_regions(content.decode("utf-8"), path)
    return [
        {"id": region_id, "size": len(value.encode()), "sha256": sha256(value.encode()).hexdigest()}
        for region_id, value in regions.items()
    ]


def _entry(path: str, content: bytes, *, ownership: str, source_path: str, comparison: str = "file") -> dict[str, Any]:
    item = {
        "path": path,
        "kind": "file",
        "ownership": ownership,
        "comparison": comparison,
        "sourcePath": source_path,
        "size": len(content),
        "sha256": sha256(content).hexdigest(),
    }
    if comparison == "managed-regions":
        item["regions"] = _region_entries(path, content, source_path=source_path, ownership=ownership)
    return item


def mixed_inventory_entries(target: Path, *, overrides: dict[str, bytes] | None = None, date: str | None = None) -> list[dict[str, Any]]:
    """Build actual-byte inventory entries for initialized root mixed files."""
    del date
    overrides = overrides or {}
    result: list[dict[str, Any]] = []
    for path, template_path in MIXED_TEMPLATE_PATHS.items():
        target_path = target / path
        content = overrides.get(path)
        if content is None and target_path.is_file() and not target_path.is_symlink():
            content = target_path.read_bytes()
        if content is None:
            continue
        try:
            item = _entry(path, content, ownership="project-entry", source_path=template_path, comparison="managed-regions")
        except (UnicodeDecodeError, ValueError):
            # Older/custom source bundles may not declare managed regions yet.
            # Keep root initialization compatible; baseline update then reports unknown.
            continue
        result.append(item)
    return result


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid inventory: {path}: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("files"), list):
        raise ValueError(f"invalid inventory shape: {path}")
    return value


def _target_fingerprint(target: Path, paths: list[str]) -> str:
    del paths
    snapshot = _project_snapshot(target)
    return sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _candidate_payload(source: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    entries: list[dict[str, Any]] = []
    contents: dict[str, bytes] = {}
    for path, source_path in _source_files(source):
        content = source_path.read_bytes()
        entries.append(_entry(path, content, ownership="template" if path.startswith("templates/") else "normative-baseline", source_path=path))
        contents[path] = content
    for path, source_path in MIXED_TEMPLATE_PATHS.items():
        content = _canonical_mixed_content(source, path)
        entries.append(_entry(path, content, ownership="project-entry", source_path=source_path, comparison="managed-regions"))
        contents[path] = content
    return entries, contents


def _actual_entry(item: dict[str, Any], content: bytes | None) -> dict[str, Any]:
    if content is None:
        return {**item, "size": None, "sha256": None, **({"regions": []} if item.get("comparison") == "managed-regions" else {})}
    result = {**item, "size": len(content), "sha256": sha256(content).hexdigest()}
    if item.get("comparison") == "managed-regions":
        result["regions"] = _region_entries(item["path"], content, source_path=item["sourcePath"], ownership=item["ownership"])
    return result


def _inventory_files(target: Path, candidate_entries: list[dict[str, Any]], overrides: dict[str, bytes] | None = None) -> list[dict[str, Any]]:
    overrides = overrides or {}
    result = []
    for item in candidate_entries:
        path = target / item["path"]
        content = overrides.get(item["path"])
        if content is None and path.is_file() and not path.is_symlink():
            content = path.read_bytes()
        result.append(_actual_entry(item, content))
    return result


def _manifest_update(text: str, *, source: Path, identity: dict[str, str], payload_digest: str,
                     current_path: str, previous_path: str | None, installed: bool = False) -> str:
    values = {
        "Source identity type": identity.get("type", "unknown"),
        "Source repository or distribution": f"`{source}`",
        "Source revision": identity.get("revision", "unavailable"),
        "Source revision algorithm": "sha1",
        "Source state": identity.get("state", "unknown"),
        "Baseline payload digest": payload_digest,
        "Current baseline inventory": f"[{current_path}]({current_path})",
        "Previous baseline inventory": f"[{previous_path}]({previous_path})" if previous_path else "unavailable — no trusted ancestor",
        "Update status": "applied" if installed else "no update recorded",
        "Last actual baseline-payload application": "recorded by this confirmed application" if installed else "",
        "Last applied release/source revision/payload digest": f"unreleased / {identity.get('revision', 'unavailable')} / {payload_digest}" if installed else "",
    }
    for label, value in values.items():
        pattern = rf"(?m)^- \*\*{re.escape(label)}:\*\*.*$"
        text, count = re.subn(pattern, f"- **{label}:** {value}", text, count=1)
        if count == 0:
            text = text.rstrip() + f"\n- **{label}:** {value}\n"
    return text


def _replace_regions(current: bytes, candidate: bytes, path: str, selected: set[str]) -> bytes:
    current_text = current.decode("utf-8")
    candidate_text = candidate.decode("utf-8")
    _extract_regions(current_text, path)
    candidate_regions = _extract_regions(candidate_text, path)
    result = current_text
    for region_id, token in MIXED_SPECS[path]:
        if region_id not in selected:
            continue
        begin, end = _region_markers(region_id, token)
        pattern = re.compile(re.escape(begin) + r"\n?(.*?)\n?" + re.escape(end), re.S)
        replacement = f"{begin}\n{candidate_regions[region_id]}\n{end}"
        result, count = pattern.subn(replacement, result, count=1)
        if count != 1:
            raise ValueError(f"{path}: managed region replacement failed: {region_id}")
    return result.encode()


def _canonical_mixed_content(source: Path, path: str) -> bytes:
    content = (source / MIXED_TEMPLATE_PATHS[path]).read_bytes()
    if path != "PROJECT_CONTEXT.md":
        return content
    begin, end = _region_markers("optional-modules", "INITIALIZER-MANAGED OPTIONAL MODULES")
    interior = "\n".join(
        [
            "| Path | Role / primary entry point |",
            "| --- | --- |",
            *(f"| `{name}/` | {ROOT_STANDARD_EXTRA_ROLES[name]}; no primary entry point recorded. |" for name in ROOT_STANDARD_EXTRA_DIRS),
        ]
    )
    text = content.decode("utf-8")
    pattern = re.compile(re.escape(begin) + r"\n?(.*?)\n?" + re.escape(end), re.S)
    text, count = pattern.subn(f"{begin}\n{interior}\n{end}", text, count=1)
    if count != 1:
        raise ValueError(f"{path}: canonical managed region is malformed")
    return text.encode()


def _region_hashes(item: dict[str, Any]) -> dict[str, str]:
    return {region["id"]: region.get("sha256") for region in item.get("regions", [])}


def _safe_target_content(path: Path) -> tuple[bytes | None, str | None]:
    state = path_state(path, tree=False, content=False)
    if state["kind"] in {"symlink", "symlink-parent", "special"}:
        return None, state["kind"]
    if state["kind"] == "file":
        return path.read_bytes(), None
    if state["kind"] == "directory":
        return None, "directory"
    return None, None


def _project_snapshot(target: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not target.exists():
        return result
    for path in sorted(target.rglob("*")):
        relative = path.relative_to(target).as_posix()
        result[relative] = path_state(path, tree=False, content=True)
    return result


def _decision_action(state: str, action: str | None, *, path: str, kind: str = "file") -> tuple[str, dict[str, Any] | None]:
    choices = ["accept-candidate", "preserve-local", "skip"] if kind == "file" else ["manual-migration", "skip"]
    if state in {"conflict", "unknown"}:
        if action not in set(choices):
            return state, {"path": path, "state": state, "choices": choices}
        return ("update" if action == "accept-candidate" else action), None
    if action and action not in DECISION_CHOICES:
        raise ValueError(f"invalid decision for {path}: {action}")
    return state, None


def build_baseline_plan(source_root: Path, target: Path, *, decisions: dict[str, str] | None = None) -> BaselinePlan:
    source = Path(source_root).resolve()
    target = Path(target).resolve()
    decisions = decisions or {}
    if not target.is_dir() or target.is_symlink():
        raise ValueError("target is not a regular directory")
    manifest = target / MANIFEST
    if not manifest.is_file() or manifest.is_symlink() or MANIFEST_MARKER not in manifest.read_text(encoding="utf-8", errors="replace"):
        raise ValueError("target does not contain an initialized baseline manifest")
    identity = _git_identity(source)
    candidate_entries, candidate_contents = _candidate_payload(source)
    current_inventory = _load_json(target / CURRENT_INVENTORY)
    base = {item["path"]: item for item in (current_inventory or {}).get("files", [])}
    actions: list[dict[str, Any]] = []
    writes: list[str] = []
    required: list[dict[str, Any]] = []
    for item in candidate_entries:
        path = item["path"]
        target_path = target / path
        current_content, unsafe = _safe_target_content(target_path)
        candidate_content = candidate_contents[path]
        base_item = base.get(path, {})
        state = unsafe or None
        region_state: dict[str, str] = {}
        if state is None and item.get("comparison") == "managed-regions":
            try:
                current_regions = _region_hashes(_actual_entry(item, current_content)) if current_content is not None else {}
                base_regions = _region_hashes(base_item)
                candidate_regions = _region_hashes(item)
                if not base_regions or set(base_regions) != set(candidate_regions) or set(current_regions) != set(candidate_regions):
                    state = "unknown"
                else:
                    region_state = {
                        region_id: (
                            "update" if current_regions[region_id] == base_regions[region_id] and candidate_regions[region_id] != base_regions[region_id]
                            else "unchanged" if current_regions[region_id] == candidate_regions[region_id]
                            else "preserve-local" if candidate_regions[region_id] == base_regions[region_id]
                            else "conflict"
                        ) for region_id in candidate_regions
                    }
                    state = "conflict" if "conflict" in region_state.values() else "update" if "update" in region_state.values() else "preserve-local" if "preserve-local" in region_state.values() else "unchanged"
            except (UnicodeDecodeError, ValueError):
                state = "unknown"
        elif state is None:
            current_hash = sha256(current_content).hexdigest() if current_content is not None else None
            candidate_hash = item["sha256"]
            base_hash = base_item.get("sha256")
            if base_hash is None:
                state = "unknown"
            elif current_hash == base_hash and candidate_hash != base_hash:
                state = "update"
            elif current_hash == candidate_hash:
                state = "unchanged"
            elif candidate_hash == base_hash:
                state = "preserve-local"
            elif current_hash != base_hash and candidate_hash != base_hash:
                state = "conflict"
            else:
                state = "unknown"
        unsafe_reason = state if state in {"symlink", "symlink-parent", "special", "directory"} else None
        if unsafe_reason is not None:
            state = "conflict"
        effective, decision = _decision_action(state, decisions.get(path), path=path)
        if decision:
            decision["regions"] = sorted(region_state)
            if unsafe_reason:
                decision["reason"] = f"unsafe target path: {unsafe_reason}"
            required.append(decision)
        if effective in {"update", "accept-candidate"}:
            writes.append(path)
        record = {"path": path, "state": state, "action": effective,
                  "baseSha256": base_item.get("sha256"), "currentSha256": sha256(current_content).hexdigest() if current_content is not None else None,
                  "candidateSha256": item["sha256"]}
        if unsafe_reason:
            record["reason"] = f"unsafe target path: {unsafe_reason}"
        if region_state:
            record["regions"] = [{"id": key, "state": value} for key, value in sorted(region_state.items())]
        actions.append(record)
    all_dirs = list(ROOT_REQUIRED_DIRS) + list(ROOT_STANDARD_EXTRA_DIRS)
    for directory in all_dirs:
        path = target / directory
        state = path_state(path, tree=False, content=False)["kind"]
        if state in {"symlink", "symlink-parent", "special", "file"}:
            effective, decision = _decision_action("conflict", decisions.get(directory), path=directory, kind="directory")
            if decision:
                required.append({**decision, "reason": "expected regular directory"})
            actions.append({"path": directory, "state": "conflict", "action": effective, "reason": "expected regular directory"})
        elif state == "absent":
            actions.append({"path": directory, "state": "missing", "action": "create"})
            writes.append(directory)
        else:
            actions.append({"path": directory, "state": "unchanged", "action": "unchanged"})
    managed_paths = [item["path"] for item in candidate_entries] + all_dirs + [MANIFEST, CURRENT_INVENTORY, PREVIOUS_INVENTORY]
    outcome = "ready" if not required else "needs_decision"
    payload = {
        "schemaVersion": 1, "command": "baseline plan", "outcome": outcome, "target": target.as_posix(),
        "candidate": {**identity, "payloadDigest": _digest_entries(candidate_entries)},
        "baseInventory": {"path": CURRENT_INVENTORY, "present": current_inventory is not None, "snapshotId": (current_inventory or {}).get("snapshotId")},
        "targetFingerprint": _target_fingerprint(target, managed_paths), "actions": actions,
        "requiredDecisions": required, "expectedWrites": writes,
        "expectedManifestUpdate": {"currentInventory": CURRENT_INVENTORY, "previousInventory": PREVIOUS_INVENTORY if current_inventory else None},
    }
    plan_id = plan_digest(payload)
    payload["planId"] = plan_id
    return BaselinePlan(payload, plan_id)


def write_plan(plan: BaselinePlan, output: Path | None = None) -> Path:
    if output is None:
        stream = tempfile.NamedTemporaryFile(prefix="research-baseline-plan-", suffix=".json", delete=False)
        output = Path(stream.name)
        stream.close()
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan.payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def inspect_baseline(source_root: Path, target: Path) -> dict[str, Any]:
    try:
        plan = build_baseline_plan(source_root, target)
    except ValueError as error:
        return {"outcome": "target_invalid", "message": str(error)}
    return {"outcome": "ok" if plan.outcome == "ready" else plan.outcome, "target": plan.payload["target"],
            "candidate": plan.payload["candidate"], "baseInventory": plan.payload["baseInventory"],
            "actions": plan.payload["actions"], "requiredDecisions": plan.payload["requiredDecisions"]}


def apply_baseline_plan(source_root: Path, target: Path, plan_file: Path, confirm_plan: str) -> dict[str, Any]:
    plan_path = Path(plan_file).resolve()
    if not plan_path.is_file() or plan_path.is_symlink():
        return {"outcome": "plan_not_found", "planFile": str(plan_path)}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"outcome": "plan_not_found", "planFile": str(plan_path), "message": str(error)}
    if plan.get("planId") != confirm_plan:
        return {"outcome": "plan_id_mismatch", "planId": plan.get("planId")}
    if plan.get("outcome") != "ready":
        return {"outcome": "decision_missing", "planId": confirm_plan}
    decisions = {item["path"]: item["action"] for item in plan["actions"] if item.get("action") in DECISION_CHOICES}
    try:
        current = build_baseline_plan(Path(source_root), Path(target), decisions=decisions)
    except (ValueError, OSError) as error:
        return {"outcome": "stale_plan", "planId": confirm_plan, "message": str(error)}
    if current.plan_id != confirm_plan:
        return {"outcome": "stale_plan", "planId": confirm_plan}
    target_path = Path(target).resolve()
    source = Path(source_root).resolve()
    candidate_entries, contents = _candidate_payload(source)
    current_inventory = _load_json(target_path / CURRENT_INVENTORY)
    expected_contents: dict[str, bytes] = {}
    writes: list[RootWrite] = []
    for action in plan["actions"]:
        path = action.get("path")
        if action.get("action") not in {"update", "accept-candidate"} or path not in contents:
            continue
        target_file = target_path / path
        current_content, unsafe = _safe_target_content(target_file)
        if unsafe:
            return {"outcome": "conflict", "planId": confirm_plan, "message": f"unsafe target path: {path} ({unsafe})"}
        content = contents[path]
        item = next(entry for entry in candidate_entries if entry["path"] == path)
        if item.get("comparison") == "managed-regions":
            if current_content is None:
                return {"outcome": "conflict", "planId": confirm_plan, "message": f"missing mixed target: {path}"}
            selected = {region["id"] for region in action.get("regions", []) if region.get("state") in {"update", "conflict"}}
            content = _replace_regions(current_content, content, path, selected)
        expected_contents[path] = content
        writes.append(RootWrite(path, content, target_file.stat().st_mode & 0o777 if target_file.exists() else 0o644, current_content))
    new_files = _inventory_files(target_path, candidate_entries, expected_contents)
    snapshot = {"schemaVersion": 1, "snapshotId": confirm_plan, "createdAt": "generated", "baseline": plan["candidate"], "digestAlgorithm": "sha256", "files": new_files}
    current_json = (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode()
    previous_json = (json.dumps(current_inventory, indent=2, sort_keys=True) + "\n").encode() if current_inventory else None
    manifest_path = target_path / MANIFEST
    manifest_text = manifest_path.read_text(encoding="utf-8")
    updated_manifest = _manifest_update(manifest_text, source=source, identity=plan["candidate"], payload_digest=plan["candidate"]["payloadDigest"], current_path=CURRENT_INVENTORY, previous_path=PREVIOUS_INVENTORY if current_inventory else None, installed=True).encode()
    writes.append(RootWrite(CURRENT_INVENTORY, current_json, 0o644, (target_path / CURRENT_INVENTORY).read_bytes() if (target_path / CURRENT_INVENTORY).is_file() else None))
    if previous_json is not None:
        writes.append(RootWrite(PREVIOUS_INVENTORY, previous_json, 0o644, (target_path / PREVIOUS_INVENTORY).read_bytes() if (target_path / PREVIOUS_INVENTORY).is_file() else None))
    writes.append(RootWrite(MANIFEST, updated_manifest, manifest_path.stat().st_mode & 0o777, manifest_path.read_bytes()))
    preserved_before = _project_snapshot(target_path)
    write_paths = {write.path for write in writes}
    state_before = {path: path_state(target_path / path, tree=True, content=True) for path in [*write_paths, CURRENT_INVENTORY, PREVIOUS_INVENTORY]}
    def check_state() -> None:
        fresh = build_baseline_plan(source, target_path, decisions=decisions)
        if fresh.plan_id != confirm_plan:
            raise ValueError("source, inventory, target or decisions changed after planning")
    def verify_preserved() -> None:
        after = _project_snapshot(target_path)
        for path, state in preserved_before.items():
            affected = any(path == write_path or path.startswith(write_path.rstrip("/") + "/") or write_path.startswith(path.rstrip("/") + "/") for write_path in write_paths)
            if not affected and after.get(path) != state:
                raise OSError(f"project-local path changed during apply: {path}")
    def verify_restored() -> None:
        if _project_snapshot(target_path) != preserved_before:
            raise OSError("project-local snapshot was not restored")
    dirs = tuple(path for path in (".baseline", INVENTORY_ROOT, *ROOT_REQUIRED_DIRS, *ROOT_STANDARD_EXTRA_DIRS) if not (target_path / path).exists())
    try:
        result = apply_writes(target_path, tuple(writes), dirs, plan_id=confirm_plan, check_state=check_state, verify_preserved=verify_preserved, verify_restored=verify_restored)
    except Exception as error:
        return {"outcome": "failed-rolled-back", "planId": confirm_plan, "message": str(error)}
    result_payload = {"outcome": result.outcome, "planId": confirm_plan, "updated": [write.path for write in writes], "planFile": str(plan_path), "message": result.message}
    if result.outcome == "applied":
        try:
            plan_path.unlink()
            result_payload["planDeleted"] = True
        except OSError:
            result_payload["planDeleted"] = False
    return result_payload
