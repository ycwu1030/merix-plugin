#!/usr/bin/env python3
"""Run the canonical Markdown postprocessor for guarded Codex apply_patch events."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from research_markdown_format import iter_markdown_files


MANIFEST_MARKER = "<!-- research-baseline-manifest:v1 -->"
PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+?)\s*$", re.MULTILINE)


def initialized_project_root(cwd: Path) -> Path | None:
    for candidate in (cwd, *cwd.parents):
        manifest = candidate / "BASELINE_MANIFEST.md"
        if manifest.is_file() and MANIFEST_MARKER in manifest.read_text(encoding="utf-8"):
            return candidate
    return None


def changed_markdown_paths(command: str, cwd: Path, project: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    eligible = set(iter_markdown_files(project))
    matches = list(PATCH_FILE_RE.finditer(command))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(command)
        moved = re.search(r"^\*\*\* Move to: (.+?)\s*$", command[match.end():end], re.MULTILINE)
        path = Path(moved.group(1) if moved else match.group(1))
        candidates = (path,) if path.is_absolute() else (cwd / path, project / path)
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(project)
            except ValueError:
                continue
            if resolved in eligible and resolved not in seen:
                seen.add(resolved)
                yield candidate
                break


def postprocess(project: Path, paths: list[Path]) -> subprocess.CompletedProcess[str]:
    plugin_root = Path(os.environ["PLUGIN_ROOT"]).resolve()
    formatter = plugin_root / "scripts" / "research_markdown_format.py"
    return subprocess.run(
        [
            sys.executable,
            str(formatter),
            "postprocess",
            "--project",
            str(project),
            *[argument for path in paths for argument in ('--file', str(path))],
        ],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )


def main(payload: dict[str, Any]) -> int:
    if payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") != "apply_patch":
        return 0
    cwd_value = payload.get("cwd")
    tool_input = payload.get("tool_input")
    if not isinstance(cwd_value, str) or not cwd_value.strip() or not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0
    project = initialized_project_root(Path(cwd_value).resolve())
    if project is None:
        return 0
    paths = list(changed_markdown_paths(command, Path(cwd_value).resolve(), project))
    if paths:
        result = postprocess(project, paths)
        if result.returncode:
            feedback = result.stdout.strip() or result.stderr.strip() or "postprocess failed"
            print(f"Markdown postprocess failed for selected edit:\n{feedback}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if not isinstance(event, dict):
        sys.exit(0)
    try:
        sys.exit(main(event))
    except (OSError, UnicodeError, KeyError) as error:
        print(f"Markdown hook could not complete safely: {error}", file=sys.stderr)
        sys.exit(2)
