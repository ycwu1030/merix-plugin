"""Static, tool-neutral catalog data for the initializer."""

from __future__ import annotations

from collections.abc import Iterable

ROOT_REQUIRED_DIRS = (
    "tasks",
    "discussions",
    "decisions",
    "references",
    "analysis",
    "code",
)
ROOT_OPTIONAL_DIRS = (
    "context",
    "artifacts",
    "docs",
    "assets",
    "workspaces",
    "relations",
)
ROOT_OPTIONAL_DIR_ROLES = {
    "context": "Stable long-form project background",
    "artifacts": "Durable artifact registry root",
    "docs": "Independently managed delivery/communication work",
    "assets": "Supporting visual or media resources",
    "workspaces": "Root-governed bounded execution work packages",
    "relations": "Central entity-relation records when configured",
}
REFERENCE_SUBDIRS = (
    "exploration",
    "reading",
    "bib",
    "audits",
    "reviews",
    "library",
)
ROOT_STANDARD_EXTRA_DIRS = (*ROOT_OPTIONAL_DIRS,
                            *(f"references/{name}" for name in REFERENCE_SUBDIRS),
                            "docs/communication")
BASELINE_METADATA_DIRS = (".baseline", ".baseline/inventory")
ROOT_STANDARD_EXTRA_ROLES = {
    **ROOT_OPTIONAL_DIR_ROLES,
    "references/exploration": "Literature exploration leads",
    "references/reading": "Source reading records",
    "references/bib": "Citation data",
    "references/audits": "Claim/source/convention audits",
    "references/reviews": "Literature syntheses and reviews",
    "references/library": "Authorized local source copies",
    "docs/communication": "Substantive communication drafts and records",
}
PACKAGE_FILES = ("AGENTS.md", "RESEARCH_WORKFLOW.md")
PACKAGE_TEMPLATE_DIR = "templates"
PROJECT_INSTANCE_TEMPLATES = {
    "README.md": "README.md",
    "PROJECT_CONTEXT.md": "PROJECT_CONTEXT.md",
    "PROJECT_STATUS.md": "PROJECT_STATUS.md",
    "BASELINE_MANIFEST.md": "BASELINE_MANIFEST.md",
}
WORK_PACKAGE_DIRS = (
    "analysis",
    "code",
    "environment",
    "inputs",
    "runs",
    "comparisons",
    "logs",
)
WORK_PACKAGE_DIR_ROLES = {
    "analysis": "Work-package-local execution analysis",
    "code": "Work-package-local code and scripts",
    "environment": "Local environment specifications and setup",
    "inputs": "Input configurations and material",
    "runs": "Durable execution records",
    "comparisons": "Durable comparison records",
    "logs": "Execution logs",
}


def render_managed_structure(enabled_dirs: Iterable[str]) -> str:
    """Render the exact v1 managed Section 4 interior for enabled directories."""
    selected = tuple(enabled_dirs)
    unknown = tuple(item for item in selected if item not in WORK_PACKAGE_DIR_ROLES)
    if unknown:
        raise ValueError(f"unknown work-package directory: {', '.join(unknown)}")
    if len(set(selected)) != len(selected):
        raise ValueError("duplicate work-package directory")
    ordered = tuple(item for item in WORK_PACKAGE_DIRS if item in selected)
    if not ordered:
        return (
            "- **Enabled local directories:** none\n\n"
            "No local execution directories are enabled at initialization.\n"
        )

    rendered_dirs = ", ".join(f"`{item}/`" for item in ordered)
    rows = [
        f"| `{item}/` | {WORK_PACKAGE_DIR_ROLES[item]} | No local entry point recorded. |"
        for item in ordered
    ]
    return "\n".join(
        [
            f"- **Enabled local directories:** {rendered_dirs}",
            "",
            "| Path | Role | Primary entry point / notes |",
            "| --- | --- | --- |",
            *rows,
            "",
        ]
    )
