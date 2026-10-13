# Markdown Normalization and Audit: Usage and Boundaries

## 1. Purpose

`research_markdown_format.py` is an opt-in, post-generation tool for research-project Markdown. It does not instruct an Agent to author mathematics with a particular delimiter. Instead, it can normalize supported generated mathematical delimiters into canonical output syntax and audit the resulting Markdown contracts.

The tool never runs automatically from the initializer. The first-release Plugin includes a `PostToolUse` formatter hook for supported Codex-native Markdown edits; users must enable the Plugin and explicitly trust its hook. Its precise trigger and limitations are documented below. A task may also explicitly make `postprocess` its final Markdown-write step, and a project may explicitly install the optional Git hook described below. These integrations do not alter the Agent-facing delimiter-neutral rule.

Its default project scan covers Markdown work documents and `FORMULA_INDEX.md`. It deliberately excludes root baseline/control documents (`AGENTS.md`, `RESEARCH_WORKFLOW.md`, `README.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `BASELINE_MANIFEST.md`) and `templates/`, whose examples, placeholders, and optional-path navigation are not research-output format violations.

## 2. Read-only audit

Run `check` to report noncanonical/unsupported mathematical delimiters, Formula Index contracts, project-relative links, headings, and forced breaks without modifying the project:

```bash
python3 <plugin-root>/scripts/research_markdown_format.py check \
  --project /absolute/path/to/project
```

`pre-commit` has the same read-only behavior and exists so that a Git hook has an explicit stable entry point:

```bash
python3 <plugin-root>/scripts/research_markdown_format.py pre-commit \
  --project /absolute/path/to/project
```

A zero exit code means no implemented rule produced a diagnostic. Exit code `1` means the tool found one or more diagnostics; exit code `2` means the command could not be run safely.

## 3. Candidate normalization

Run `normalize` only when the user has requested canonicalized Markdown output for a complete candidate project tree. It writes to the explicitly named absent output directory; it does not modify the source project:

```bash
python3 <plugin-root>/scripts/research_markdown_format.py normalize \
  --project /absolute/path/to/project \
  --output /absolute/path/to/normalized-project
```

The formatter converts supported `\(...\)` inline mathematics to `$...$` and supported one-line or standalone-delimiter `\[...\]` display mathematics to blank-line-separated `$$...$$` blocks. Existing canonical math content is preserved; missing blank lines around display blocks, ATX headings and the start of top-level lists are inserted without prose reflow or heading renumbering. LaTeX `equation`, `align`, `gather`, and `multline` environments are reported as unsupported rather than guessed at. The command audits the candidate output before publishing it; a diagnostic leaves no output project behind.

Review the candidate diff before using it as a replacement for a source project. `normalize` intentionally has no in-place overwrite option.

## 4. Per-file postprocess

When a task explicitly requires a generated Markdown file to be normalized immediately after writing, invoke `postprocess` for that one file:

```bash
python3 <plugin-root>/scripts/research_markdown_format.py postprocess \
  --project /absolute/path/to/project \
  --file analysis/generated-note.md
```

`--file` may be project-relative or absolute, but it must resolve to an existing, non-symlink Markdown work file within the selected project and its default audit scope. The command does the following in order:

1. normalizes supported mathematical delimiters and block spacing in memory;
2. audits the complete candidate project state, including the affected file and cross-file Formula Index contracts;
3. writes a same-directory temporary file; and
4. atomically replaces the requested file only if there are no diagnostics.

If normalization or audit fails, the source file remains unchanged and the temporary file is removed. This is the intended safe end-of-write command for an Agent workflow; it does **not** independently intercept arbitrary file writes.

For one explicitly selected edit affecting multiple files, repeat `--file`. All
selected candidates are normalized in memory and audited together before any
replacement. A normalization/audit diagnostic preserves every selected source.
Each replacement is atomic; this is not a transaction across files. An I/O
failure can leave earlier replacements completed and is reported as `CLI002`.
Invalid text encoding is also a diagnostic, never a guessed conversion.

## 5. Optional Git pre-commit backstop

A Git hook can catch a missed `postprocess` call before a commit. It is not installed automatically. Install it only in a selected Git work tree:

```bash
python3 <plugin-root>/scripts/research_markdown_format.py install-pre-commit-hook \
  --project /absolute/path/to/project
```

The installer resolves Git's configured `hooks/pre-commit` path, writes only a missing hook, and refuses to overwrite another hook. Repeating the same installation is a no-op. The installed hook invokes the read-only `pre-commit` command, never normalizes files, and blocks the commit if diagnostics are found.

This first hook checks the working tree rather than Git's staged blobs. It can therefore block a partial commit because of an unstaged Markdown issue elsewhere in the selected project. Reinstall it after moving the Plugin, because the generated hook intentionally records the exact local Python interpreter, Plugin script, and project paths. It is a local Git-worktree integration, not a global install or a substitute for a file-write lifecycle hook.

## 6. Packaged Codex Plugin hook

The Plugin declares a Codex `PostToolUse` hook in `hooks/hooks.json`. It becomes relevant only when Codex has enabled the Plugin and trusted its hook configuration; this repository does not install a global Codex hook or add an active root `.codex/hooks.json`.

The hook matches Codex `Edit|Write` events and defensively accepts only the resulting `apply_patch` payload. It locates `*** Add File:` and `*** Update File:` Markdown paths (using `*** Move to:` destinations for moves), confirms that their nearest initialized research-project root has the `BASELINE_MANIFEST.md` marker, then invokes the same safe `postprocess` command described above. The initialized project is resolved from the Hook event `cwd` and its ancestors. Absolute paths into another initialized project do not select that other project: cross-project edits are skipped. For validation or normal use, run the session inside the intended initialized project. Nested `functions.exec` calls to the native `tools.apply_patch` were verified on the selected runtime; the same project and work-file scope applies. All eligible files from that edit share one candidate audit; `.md` extensions are case-insensitive. The adapter reuses the formatter's work-file scope, skips baseline/control/template files and retains symlink refusal. Code/configuration paths use Codex `PLUGIN_ROOT`, not a machine-specific path.

After installing from the selected local or remote marketplace, enable the
Plugin and use Codex `/hooks` to review the `PostToolUse` command and trust it.
Installation alone does not authorize Hook execution. The packaged configuration
and real native-edit dispatch were verified with Codex `0.162.0-alpha.17.2` in an
isolated installation and initialized workspace. Compatibility with another
runtime version requires its own load/event check.

A formatter diagnostic makes the hook return nonzero feedback to Codex. Because this is `PostToolUse`, the original edit has already occurred: the adapter does not claim rollback, while `postprocess` itself still refuses to replace a source file with a failed normalized candidate. The first matcher deliberately excludes Bash/shell writers because a shell command string cannot reliably identify all files actually written. The Git pre-commit backstop remains useful for those paths.

## 7. Safety boundaries

- Mathematical content and explicit `\tag{F-NNN}` identifiers are preserved.
- Fenced code blocks (matching fence character and length), inline code spans including multiple backticks, and Markdown-link destinations are not normalized as mathematics.
- Unsupported or unsafe delimiter patterns are diagnostics, not guessed transformations.
- Unclosed fenced blocks and standalone `$$` blocks are diagnostics. Broken links, heading hierarchy/numbering, forced breaks and Formula Index errors remain audit failures; the formatter does not invent their intended repair. A clean audit only covers implemented checks, not every possible Markdown syntax or renderer.
- The tool does not reflow ordinary prose, infer formula importance, check external URLs, prove renderer behavior, or review scientific/content quality.
- General relative-link checks apply to Markdown-document targets. Directory navigation and baseline/template placeholders are outside the default audit scope.
- The Formula Index rule checks every declared formula tag against `FORMULA_INDEX.md`; it does not decide whether an untagged formula should have been assigned an ID.
