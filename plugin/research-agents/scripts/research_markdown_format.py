#!/usr/bin/env python3
"""Normalize supported generated Markdown math and audit MERIX format contracts."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, Mapping, Sequence


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TAG_RE = re.compile(r"\\tag\{([^}]+)\}")
FORMULA_ID_RE = re.compile(r"^F-(\d{3,})$")
INLINE_BACKSLASH_RE = re.compile(r"\\\((.*?)\\\)")
UNSUPPORTED_DISPLAY_ENVIRONMENT_RE = re.compile(
    r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}"
)
ROOT_CONTROL_MARKDOWN = {
    "AGENTS.md",
    "BASELINE_MANIFEST.md",
    "PROJECT_CONTEXT.md",
    "PROJECT_STATUS.md",
    "README.md",
    "RESEARCH_WORKFLOW.md",
}


@dataclass(frozen=True)
class Diagnostic:
    path: Path
    line: int
    rule: str
    message: str

    def render(self, project: Path) -> str:
        try:
            display_path = self.path.relative_to(project)
        except ValueError:
            display_path = self.path
        return f"{display_path}:{self.line}: {self.rule}: {self.message}"


def iter_markdown_files(project: Path) -> list[Path]:
    ignored = {".git", "__pycache__", ".pytest_cache", "templates"}
    files: list[Path] = []
    for path in project.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        relative = path.relative_to(project)
        if any(part in ignored or part.startswith(".") for part in relative.parts):
            continue
        if len(relative.parts) == 1 and relative.name in ROOT_CONTROL_MARKDOWN:
            continue
        files.append(path)
    return sorted(files)


def find_link_end(text: str, open_parenthesis: int) -> int | None:
    depth = 1
    index = open_parenthesis + 1
    while index < len(text):
        character = text[index]
        if character == "\\":
            index += 2
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def protected_line_segments(line: str) -> Iterable[tuple[bool, str]]:
    """Yield (protected, segment) pairs for inline code and Markdown links."""
    index = 0
    plain_start = 0
    while index < len(line):
        if line[index] == "`":
            run = re.match(r"`+", line[index:]).group(0)
            closing = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", line[index + len(run):])
            if closing:
                end = index + len(run) + closing.end()
                if plain_start < index:
                    yield False, line[plain_start:index]
                yield True, line[index:end]
                index = end
                plain_start = index
                continue
            index += len(run)
            continue
        if line[index] == "[":
            close_bracket = line.find("](", index + 1)
            if close_bracket != -1:
                end = find_link_end(line, close_bracket + 1)
                if end is not None:
                    if plain_start < index:
                        yield False, line[plain_start:index]
                    yield True, line[index : end + 1]
                    index = end + 1
                    plain_start = index
                    continue
        index += 1
    if plain_start < len(line):
        yield False, line[plain_start:]


def masked_line(line: str) -> str:
    return "".join(
        " " * len(segment) if protected else segment
        for protected, segment in protected_line_segments(line)
    )


def fenced_lines(lines: Sequence[str]) -> tuple[set[int], int | None]:
    protected: set[int] = set()
    opening: tuple[str, int, int] | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if opening:
            protected.add(index)
            if match and match[1][0] == opening[0] and len(match[1]) >= opening[1] and not match[2].strip():
                opening = None
        elif match and not (match[1][0] == '`' and '`' in match[2]):
            opening = (match[1][0], len(match[1]), index)
            protected.add(index)
    return protected, opening[2] + 1 if opening else None


def protected_lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    protected, _ = fenced_lines(lines)
    return [('\n' if line.endswith('\n') else '') if index in protected else masked_line(line)
            for index, line in enumerate(lines)]


def normalize_inline_math(line: str, path: Path, line_number: int) -> tuple[str, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    normalized_parts: list[str] = []
    for protected, segment in protected_line_segments(line):
        if protected:
            normalized_parts.append(segment)
            continue
        opening_count = segment.count("\\(")
        closing_count = segment.count("\\)")
        if opening_count != closing_count:
            diagnostics.append(
                Diagnostic(path, line_number, "MATH003", "unpaired \\(...\\) inline delimiter")
            )
            normalized_parts.append(segment)
            continue
        normalized_parts.append(INLINE_BACKSLASH_RE.sub(r"$\1$", segment))
    return "".join(normalized_parts), diagnostics


def append_blank_before(lines: list[str]) -> None:
    if lines and lines[-1].strip():
        lines.append("\n")


def normalize_text(text: str, path: Path) -> tuple[str, list[Diagnostic]]:
    source_lines = text.splitlines(keepends=True)
    normalized: list[str] = []
    diagnostics: list[Diagnostic] = []
    code, unclosed = fenced_lines(source_lines)
    if unclosed:
        diagnostics.append(Diagnostic(path, unclosed, "CODE001", "unclosed fenced code block"))
    index = 0
    while index < len(source_lines):
        line = source_lines[index]
        line_number = index + 1
        if index in code:
            normalized.append(line)
            index += 1
            continue
        if UNSUPPORTED_DISPLAY_ENVIRONMENT_RE.search(masked_line(line)):
            diagnostics.append(
                Diagnostic(path, line_number, "MATH005", "unsupported LaTeX display environment")
            )
            normalized.append(line)
            index += 1
            continue
        single_line_display = re.fullmatch(r"\s*\\\[(.*?)\\\]\s*(?:\n)?", line)
        if single_line_display:
            append_blank_before(normalized)
            normalized.append("$$\n")
            normalized.append(f"{single_line_display.group(1).strip()}\n")
            normalized.append("$$\n")
            if index + 1 < len(source_lines) and source_lines[index + 1].strip():
                normalized.append("\n")
            index += 1
            continue
        if line.strip() == r"\[":
            closing_index = index + 1
            while closing_index < len(source_lines) and source_lines[closing_index].strip() != r"\]":
                closing_index += 1
            if closing_index == len(source_lines):
                diagnostics.append(
                    Diagnostic(path, line_number, "MATH004", "unpaired \\[...\\] display delimiter")
                )
                normalized.append(line)
                index += 1
                continue
            append_blank_before(normalized)
            normalized.append("$$\n")
            normalized.extend(source_lines[index + 1 : closing_index])
            if normalized[-1].endswith("\n") is False:
                normalized[-1] += "\n"
            normalized.append("$$\n")
            if closing_index + 1 < len(source_lines) and source_lines[closing_index + 1].strip():
                normalized.append("\n")
            index = closing_index + 1
            continue
        converted, inline_diagnostics = normalize_inline_math(line, path, line_number)
        diagnostics.extend(inline_diagnostics)
        normalized.append(converted)
        index += 1
    return normalize_block_spacing(normalized), diagnostics


def normalize_block_spacing(lines: Sequence[str]) -> str:
    code, _ = fenced_lines(lines)
    result: list[str] = []
    display = False
    list_block = False
    for index, line in enumerate(lines):
        if index in code:
            result.append(line)
            continue
        if line.strip() == '$$':
            if not display:
                append_blank_before(result)
            result.append(line)
            if display and index + 1 < len(lines) and lines[index + 1].strip():
                result.append('\n')
            display = not display
            continue
        if display:
            result.append(line)
            continue
        heading = HEADING_RE.match(line)
        item = re.match(r'^(?:[-+*]|\d+[.)])\s+', line)
        if heading or (item and not list_block):
            append_blank_before(result)
        result.append(line)
        if heading and index + 1 < len(lines) and lines[index + 1].strip():
            result.append('\n')
        if not line.strip() or heading:
            list_block = False
        elif item:
            list_block = True
    return ''.join(result)


def extract_links(line: str) -> list[str]:
    destinations: list[str] = []
    index = 0
    while index < len(line):
        if line[index] == "[":
            close_bracket = line.find("](", index + 1)
            if close_bracket != -1:
                end = find_link_end(line, close_bracket + 1)
                if end is not None:
                    destinations.append(line[close_bracket + 2 : end].strip())
                    index = end + 1
                    continue
        index += 1
    return destinations


def resolve_local_destination(source: Path, destination: str) -> Path | None:
    if not destination or destination.startswith(("#", "mailto:", "tel:")) or "://" in destination:
        return None
    destination = destination.strip("<>")
    destination = destination.replace(r"\(", "(").replace(r"\)", ")")
    destination = destination.split("#", 1)[0]
    if not destination:
        return None
    return (source.parent / destination).resolve()


def audit_math(path: Path, lines: list[str]) -> tuple[list[Diagnostic], dict[str, list[Diagnostic]]]:
    diagnostics: list[Diagnostic] = []
    tag_locations: dict[str, list[Diagnostic]] = {}
    for number, line in enumerate(lines, start=1):
        if any(delimiter in line for delimiter in (r"\(", r"\)", r"\[", r"\]")):
            diagnostics.append(
                Diagnostic(path, number, "MATH001", "noncanonical or unpaired backslash math delimiter")
            )
        if UNSUPPORTED_DISPLAY_ENVIRONMENT_RE.search(line):
            diagnostics.append(
                Diagnostic(path, number, "MATH005", "unsupported LaTeX display environment")
            )
        for match in TAG_RE.finditer(line):
            formula_id = match.group(1)
            if not FORMULA_ID_RE.fullmatch(formula_id):
                diagnostics.append(
                    Diagnostic(path, number, "FORMULA001", "formula tag must use F-NNN")
                )
                continue
            tag_locations.setdefault(formula_id, []).append(
                Diagnostic(path, number, "FORMULA002", f"duplicate Formula ID {formula_id}")
            )
    return diagnostics, tag_locations


def audit_formula_index(
    project: Path,
    tags: dict[str, list[Diagnostic]],
    overrides: Mapping[Path, str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for locations in tags.values():
        diagnostics.extend(locations[1:])

    index_path = project / "FORMULA_INDEX.md"
    if not index_path.is_file():
        diagnostics.extend(
            Diagnostic(location.path, location.line, "FORMULA003", "tagged formula has no FORMULA_INDEX.md")
            for locations in tags.values()
            for location in locations[:1]
        )
        return diagnostics

    rows: dict[str, tuple[int, str]] = {}
    values: list[int] = []
    index_text = overrides.get(index_path.resolve(), index_path.read_text(encoding="utf-8"))
    for number, line in enumerate(index_text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not FORMULA_ID_RE.fullmatch(cells[0]):
            continue
        formula_id = cells[0]
        numeric_id = int(FORMULA_ID_RE.fullmatch(formula_id).group(1))
        values.append(numeric_id)
        if formula_id in rows:
            diagnostics.append(
                Diagnostic(index_path, number, "FORMULA002", f"duplicate Formula Index ID {formula_id}")
            )
        rows[formula_id] = (number, cells[2])
        destinations = extract_links(cells[2])
        if not destinations:
            diagnostics.append(
                Diagnostic(index_path, number, "FORMULA005", "Formula Index location must be a relative Markdown link")
            )
        else:
            target = resolve_local_destination(index_path, destinations[0])
            if target is None or not target.is_file():
                diagnostics.append(
                    Diagnostic(index_path, number, "FORMULA005", "Formula Index location target does not exist")
                )
    if values != sorted(values):
        diagnostics.append(
            Diagnostic(index_path, 1, "FORMULA004", "Formula Index IDs must be in numeric ascending order")
        )
    for formula_id, locations in tags.items():
        if formula_id not in rows:
            first = locations[0]
            diagnostics.append(
                Diagnostic(first.path, first.line, "FORMULA003", f"{formula_id} has no Formula Index row")
            )
    return diagnostics


def mask_code_spans(line: str) -> str:
    return ''.join(' ' * len(segment) if protected and segment.startswith('`') else segment
                   for protected, segment in protected_line_segments(line))


def audit_links(path: Path, text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    code, _ = fenced_lines(lines)
    for number, line in enumerate(lines, start=1):
        if number - 1 in code:
            continue
        for destination in extract_links(mask_code_spans(line)):
            markdown_destination = destination.strip("<>").split("#", 1)[0]
            if Path(markdown_destination).suffix.lower() != ".md":
                continue
            target = resolve_local_destination(path, destination)
            if target is not None and not target.is_file():
                diagnostics.append(
                    Diagnostic(path, number, "LINK001", f"relative link target does not exist: {destination}")
                )
    return diagnostics


def audit_headings(path: Path, lines: list[str]) -> list[Diagnostic]:
    headings: list[tuple[int, int, str]] = []
    for number, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            headings.append((number, len(match.group(1)), match.group(2)))
    if not headings:
        return []
    diagnostics: list[Diagnostic] = []
    titles = [heading for heading in headings if heading[1] == 1]
    if len(titles) != 1 or re.match(r"^\d+(?:\.\d+)*\.\s+", titles[0][2]):
        diagnostics.append(
            Diagnostic(path, titles[0][0] if titles else 1, "HEAD001", "document needs one unnumbered # title")
        )
    previous_level = 0
    counters = [0] * 7
    for number, level, title in headings:
        if previous_level and level > previous_level + 1:
            diagnostics.append(
                Diagnostic(path, number, "HEAD003", "heading level may not skip a level")
            )
        if level >= 2:
            match = re.match(r"^(\d+(?:\.\d+)*)\.\s+", title)
            if not match:
                diagnostics.append(
                    Diagnostic(path, number, "HEAD002", "lower heading needs hierarchical numbering")
                )
            else:
                counters[level] += 1
                for lower_level in range(level + 1, len(counters)):
                    counters[lower_level] = 0
                expected = ".".join(str(counters[current]) for current in range(2, level + 1))
                if match.group(1) != expected:
                    diagnostics.append(
                        Diagnostic(path, number, "HEAD004", f"expected heading number {expected}.")
                    )
        previous_level = level
    return diagnostics


def audit_forced_breaks(path: Path, text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    in_display_math = False
    lines = text.splitlines()
    code, _ = fenced_lines(lines)
    for number, line in enumerate(lines, start=1):
        if number - 1 in code:
            continue
        if line.strip() == "$$":
            in_display_math = not in_display_math
            continue
        if in_display_math:
            continue
        raw_line = mask_code_spans(line)
        if raw_line.endswith("  ") or raw_line.endswith("\\") or "<br>" in raw_line.lower():
            diagnostics.append(
                Diagnostic(path, number, "BREAK001", "unrequested forced line break")
            )
    return diagnostics


def audit_display_block_spacing(path: Path, lines: list[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    in_display_math = False
    for index, line in enumerate(lines):
        if line.strip() != "$$":
            continue
        if not in_display_math:
            if index > 0 and lines[index - 1].strip():
                diagnostics.append(
                    Diagnostic(path, index + 1, "BLOCK001", "display math needs a preceding blank line")
                )
            in_display_math = True
        else:
            if index + 1 < len(lines) and lines[index + 1].strip():
                diagnostics.append(
                    Diagnostic(path, index + 1, "BLOCK001", "display math needs a following blank line")
                )
            in_display_math = False
    if in_display_math:
        diagnostics.append(Diagnostic(path, len(lines), "MATH004", "unpaired $$ display delimiter"))
    return diagnostics


def audit_project(
    project: Path,
    overrides: Mapping[Path, str] | None = None,
) -> list[Diagnostic]:
    normalized_overrides = {
        path.resolve(): text for path, text in (overrides or {}).items()
    }
    diagnostics: list[Diagnostic] = []
    all_tags: dict[str, list[Diagnostic]] = {}
    for path in iter_markdown_files(project):
        text = normalized_overrides.get(path.resolve(), path.read_text(encoding="utf-8"))
        protected = protected_lines(text)
        _, unclosed = fenced_lines(text.splitlines())
        if unclosed:
            diagnostics.append(Diagnostic(path, unclosed, "CODE001", "unclosed fenced code block"))
        math_diagnostics, tags = audit_math(path, protected)
        diagnostics.extend(math_diagnostics)
        for formula_id, locations in tags.items():
            all_tags.setdefault(formula_id, []).extend(locations)
        diagnostics.extend(audit_links(path, text))
        diagnostics.extend(audit_headings(path, protected))
        diagnostics.extend(audit_forced_breaks(path, text))
        diagnostics.extend(audit_display_block_spacing(path, protected))
    diagnostics.extend(audit_formula_index(project, all_tags, normalized_overrides))
    return sorted(diagnostics, key=lambda item: (str(item.path), item.line, item.rule, item.message))


def normalize_project(project: Path, output: Path) -> list[Diagnostic]:
    if output.exists():
        return [Diagnostic(output, 1, "CLI001", "output path must not already exist")]
    try:
        output.relative_to(project)
    except ValueError:
        pass
    else:
        return [Diagnostic(output, 1, "CLI001", "output path must be outside the source project")]

    candidate: dict[Path, str] = {}
    diagnostics: list[Diagnostic] = []
    for path in iter_markdown_files(project):
        normalized, file_diagnostics = normalize_text(path.read_text(encoding="utf-8"), path)
        candidate[path] = normalized
        diagnostics.extend(file_diagnostics)
    if diagnostics:
        return diagnostics

    with tempfile_directory(output) as staging:
        shutil.copytree(project, staging, dirs_exist_ok=True)
        for source_path, normalized in candidate.items():
            destination = staging / source_path.relative_to(project)
            destination.write_text(normalized, encoding="utf-8")
        diagnostics.extend(audit_project(staging))
        if diagnostics:
            return diagnostics
        staging.rename(output)
    return []


class tempfile_directory:
    """A target-adjacent staging directory that cleans itself unless renamed."""

    def __init__(self, target: Path) -> None:
        self.target = target
        self.path = target.parent / f".{target.name}.markdown-format-staging"

    def __enter__(self) -> Path:
        if self.path.exists():
            raise FileExistsError(f"staging path already exists: {self.path}")
        self.path.mkdir(parents=True)
        return self.path

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self.path.exists():
            shutil.rmtree(self.path)


def postprocess_target(project: Path, requested_path: Path) -> tuple[Path | None, list[Diagnostic]]:
    path = requested_path if requested_path.is_absolute() else project / requested_path
    if path.is_symlink():
        return None, [Diagnostic(path, 1, "CLI001", "postprocess refuses symbolic links")]
    path = path.resolve()
    try:
        path.relative_to(project)
    except ValueError:
        return None, [Diagnostic(path, 1, "CLI001", "file path must be inside the project")]
    if not path.is_file():
        return None, [Diagnostic(path, 1, "CLI001", "file path must be an existing Markdown file")]
    if path.suffix.lower() != ".md":
        return None, [Diagnostic(path, 1, "CLI001", "file path must name a Markdown file")]
    if path not in iter_markdown_files(project):
        return None, [Diagnostic(path, 1, "CLI001", "file is outside the default format-audit scope")]
    return path, []


def atomic_write(path: Path, text: str, mode: int) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.markdown-format-",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(text)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def postprocess_file(project: Path, path: Path) -> list[Diagnostic]:
    return postprocess_files(project, [path])


def postprocess_files(project: Path, paths: Sequence[Path]) -> list[Diagnostic]:
    candidates: dict[Path, str] = {}
    diagnostics: list[Diagnostic] = []
    for path in paths:
        normalized, errors = normalize_text(path.read_text(encoding="utf-8"), path)
        candidates[path] = normalized
        diagnostics.extend(errors)
    if diagnostics:
        return diagnostics
    diagnostics = audit_project(project, candidates)
    if diagnostics:
        return diagnostics
    for path, normalized in candidates.items():
        atomic_write(path, normalized, path.stat().st_mode & 0o777)
    return []


def hook_path(project: Path) -> tuple[Path | None, list[Diagnostic]]:
    try:
        inside = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None, [Diagnostic(project, 1, "CLI002", "Git is required to install a pre-commit hook")]
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None, [Diagnostic(project, 1, "CLI002", "project is not inside a Git work tree")]
    target = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--git-path", "hooks/pre-commit"],
        check=False,
        capture_output=True,
        text=True,
    )
    if target.returncode != 0 or not target.stdout.strip():
        return None, [Diagnostic(project, 1, "CLI002", "could not resolve the Git pre-commit hook path")]
    result = Path(target.stdout.strip())
    if not result.is_absolute():
        result = (project / result).resolve()
    return result, []


def pre_commit_hook_content(project: Path) -> str:
    python = shlex.quote(sys.executable)
    script = shlex.quote(str(Path(__file__).resolve()))
    target = shlex.quote(str(project))
    return (
        "#!/bin/sh\n"
        "# MERIX research Markdown format pre-commit hook.\n"
        "# Installed only by the explicit install-pre-commit-hook command.\n"
        f"exec {python} {script} pre-commit --project {target}\n"
    )


def install_pre_commit_hook(project: Path) -> list[Diagnostic]:
    path, diagnostics = hook_path(project)
    if diagnostics:
        return diagnostics
    assert path is not None
    content = pre_commit_hook_content(project)
    if path.exists():
        if path.is_file() and path.read_text(encoding="utf-8") == content:
            return []
        return [Diagnostic(path, 1, "CLI003", "refusing to overwrite an existing pre-commit hook")]
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, content, 0o755)
    return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize supported generated Markdown math and audit MERIX format contracts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="read-only format audit")
    check.add_argument("--project", type=Path, required=True)
    normalize = subparsers.add_parser("normalize", help="normalize into a new output directory")
    normalize.add_argument("--project", type=Path, required=True)
    normalize.add_argument("--output", type=Path, required=True)
    postprocess = subparsers.add_parser(
        "postprocess", help="normalize explicitly selected files after a shared candidate audit"
    )
    postprocess.add_argument("--project", type=Path, required=True)
    postprocess.add_argument("--file", type=Path, action="append", required=True)
    pre_commit = subparsers.add_parser("pre-commit", help="read-only audit entry point for Git hooks")
    pre_commit.add_argument("--project", type=Path, required=True)
    install_hook = subparsers.add_parser(
        "install-pre-commit-hook", help="explicitly install a non-overwriting Git pre-commit hook"
    )
    install_hook.add_argument("--project", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    project = arguments.project.resolve()
    if not project.is_dir():
        print(f"{project}:1: CLI001: project path must be an existing directory")
        return 2
    if arguments.command in {"check", "pre-commit"}:
        diagnostics = audit_project(project)
    elif arguments.command == "normalize":
        diagnostics = normalize_project(project, arguments.output.resolve())
    elif arguments.command == "postprocess":
        paths = []
        diagnostics = []
        for requested in arguments.file:
            path, errors = postprocess_target(project, requested)
            diagnostics.extend(errors)
            if path is not None:
                paths.append(path)
        if not diagnostics:
            diagnostics = postprocess_files(project, paths)
    else:
        diagnostics = install_pre_commit_hook(project)
    for diagnostic in diagnostics:
        print(diagnostic.render(project))
    if any(diagnostic.rule.startswith("CLI") for diagnostic in diagnostics):
        return 2
    return 1 if diagnostics else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, UnicodeError) as error:
        print(f"CLI002: Markdown processing could not complete safely: {error}")
        sys.exit(2)
