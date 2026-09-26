"""Inventory first-party files and declared symbols without reading private runtime state.

This is static accounting, not a test runner or a coverage/acceptance oracle.
Run: uv run --with tree-sitter==0.25.2 --with tree-sitter-javascript==0.25.0
python scripts/generate_project_audit.py
The extra packages are audit tools, not application dependencies. Outputs exclude their own hashes.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/audit"


def dump(name, value):
    (OUT / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    paths = sorted(
        {p for p in paths if p and p not in {"docs/audit/FILE_FUNCTION_INVENTORY.md", "docs/audit/file-function-inventory.json"}}
        | {p for p in ("KIT_VALIDATION.json", "MANIFEST.json") if (ROOT / p).exists()}
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    notes_path = OUT / "review-notes.json"
    notes = (
        json.loads(notes_path.read_text(encoding="utf-8"))["symbols"] if notes_path.exists() else []
    )
    notes_by_symbol = {(s["file"], s["name"]): s for s in notes}
    calls_path = OUT / "function-call-observations.json"
    calls = (
        json.loads(calls_path.read_text(encoding="utf-8"))["calls"] if calls_path.exists() else []
    )
    call_counts = {}
    for entry in calls:
        key = (entry["file"], entry["function"].replace(".<locals>.", "."))
        call_counts[key] = call_counts.get(key, 0) + entry["calls"]
    files, symbols, links = [], [], []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        role = (
            "historical kit metadata; not current implementation evidence"
            if relative in {"KIT_VALIDATION.json", "MANIFEST.json"}
            else "immutable source requirement"
            if relative.startswith("reference/")
            else "local historical report; not AWS/human proof"
            if relative.startswith("evidence/")
            else "implementation"
            if relative.startswith(("src/", "infra/"))
            else "test assertion"
            if relative.startswith("tests/")
            else "synthetic fixture"
            if relative.startswith("fixtures/")
            else "probe/build/audit tooling"
            if relative.startswith("scripts/")
            else "locked dependency metadata"
            if path.name in {"uv.lock", "package-lock.json", "dependency-inventory.json"}
            else "configuration or documented contract"
        )
        validation = "TEXT_INVENTORIED"
        if path.suffix == ".json":
            json.loads(text)
            validation = "JSON_PARSED"
        if path.suffix == ".py":
            tree = ast.parse(text, filename=relative)
            validation = "PYTHON_AST_PARSED"

            def walk(node, parents=()):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        name = ".".join((*parents, child.name))
                        doc = ast.get_docstring(child)
                        symbols.append(
                            {
                                "file": relative,
                                "name": name,
                                "kind": "class" if isinstance(child, ast.ClassDef) else "function",
                                "line": child.lineno,
                                "end_line": child.end_lineno,
                                "purpose": doc.splitlines()[0]
                                if doc
                                else child.name.replace("_", " ").strip(),
                                "accounting": "STATIC_DEFINITION; not branch or runtime proof",
                            }
                        )
                        walk(child, (*parents, child.name))
                    else:
                        if isinstance(child, ast.Lambda):
                            symbols.append(
                                {
                                    "file": relative,
                                    "name": ".".join(
                                        (*parents, f"<lambda@{child.lineno}:{child.col_offset}>")
                                    ),
                                    "kind": "lambda",
                                    "line": child.lineno,
                                    "end_line": child.end_lineno,
                                    "purpose": "Anonymous callback/expression; inspect its enclosing function and scenario tests.",
                                    "accounting": "STATIC_DEFINITION; not runtime or branch proof",
                                }
                            )
                        walk(child, parents)

            walk(tree)
        elif path.suffix == ".mjs":
            import tree_sitter_javascript
            from tree_sitter import Language, Parser

            tree = Parser(Language(tree_sitter_javascript.language())).parse(raw)
            if tree.root_node.has_error:
                raise SystemExit(f"JAVASCRIPT_PARSE_FAILED:{relative}")
            validation = "JAVASCRIPT_SYNTAX_TREE_PARSED"

            def walk_js(node, parents=()):
                names = {
                    "class_declaration",
                    "class",
                    "function_declaration",
                    "generator_function_declaration",
                    "function_expression",
                    "generator_function",
                    "arrow_function",
                    "method_definition",
                }
                if node.type in names:
                    name_node = node.child_by_field_name("name")
                    if (
                        name_node is None
                        and node.parent
                        and node.parent.type == "variable_declarator"
                    ):
                        name_node = node.parent.child_by_field_name("name")
                    name = (
                        raw[name_node.start_byte : name_node.end_byte].decode("utf-8")
                        if name_node
                        else f"<anonymous@{node.start_point.row + 1}:{node.start_point.column}>"
                    )
                    qualified = ".".join((*parents, name))
                    symbols.append(
                        {
                            "file": relative,
                            "name": qualified,
                            "kind": "javascript " + node.type,
                            "line": node.start_point.row + 1,
                            "end_line": node.end_point.row + 1,
                            "purpose": "Anonymous callback; inspect enclosing definition."
                            if name.startswith("<anonymous")
                            else name.replace("_", " "),
                            "accounting": "STATIC_SYNTAX_TREE; not runtime/branch proof",
                        }
                    )
                    parents = (*parents, name)
                for child in node.named_children:
                    walk_js(child, parents)

            walk_js(tree.root_node)
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", text):
                target = target.strip("<>").split("#")[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if not (path.parent / target).exists():
                    links.append(
                        {"file": relative, "target": target, "status": "MISSING_LOCAL_TARGET"}
                    )
        files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "lines": len(text.splitlines()),
                "role": role,
                "validation": validation,
                "declared_symbols": sum(s["file"] == relative for s in symbols),
            }
        )
    record = {
        "kind": "FIRST_PARTY_STATIC_FILE_AND_SYMBOL_ACCOUNTING",
        "commit": commit,
        "scope": "Git-tracked authored files plus two original kit metadata files; audit outputs excluded from self-hashing",
        "exclusions": [
            ".git internals",
            "ignored private configuration/state/logs",
            "worktree copies",
            "vendor node_modules/venvs/binaries",
        ],
        "limits": [
            "Static enumeration does not prove correctness",
            "Python classes/methods/nested functions and lambdas included",
            "JavaScript syntax tree includes classes, methods, functions and anonymous callbacks; no runtime coverage claim",
        ],
        "files": files,
        "symbols": symbols,
        "missing_markdown_targets": links,
    }
    for symbol in symbols:
        key = (symbol["file"], symbol["name"])
        note = notes_by_symbol.get(key, {})
        symbol["review_test_references"] = note.get("test_references", [])
        symbol["review_purpose"] = note.get("purpose")
        symbol["observed_calls_at_73780b4_unit_cloud_only"] = call_counts.get(key, 0)
        symbol["observation_limit"] = (
            "Zero is not proof of untestedness; PostgreSQL, subprocess and JavaScript calls were not profiled. Nonzero is not branch/acceptance proof."
        )
    dump("file-function-inventory.json", record)
    md = [
        "# First-party file and function inventory",
        "",
        f"Snapshot: `{commit}`. {len(files)} files; {len(symbols)} declared symbols.",
        "",
        "Every file below was read as UTF-8 and hashed. JSON and Python were parsed. This inventory is static accounting, not a claim that every branch/function was executed. Private ignored configuration and vendor/runtime directories are excluded. Audit outputs do not hash themselves.",
        "",
        "Python includes classes, methods, nested functions and lambdas. JavaScript uses pinned Tree-sitter syntax trees, including classes, methods and anonymous functions/callbacks. Definitions are not branch coverage.",
        "",
    ]
    for item in files:
        md.extend(
            [
                f"## {item['path']}",
                "",
                f"{item['role']}. {item['bytes']} bytes; {item['validation']}. SHA-256: `{item['sha256']}`.",
                "",
            ]
        )
        selected = [s for s in symbols if s["file"] == item["path"]]
        if selected:
            md.extend(
                [
                    "| Symbol | Line | Purpose | Unit/cloud calls at older commit | Review test references |",
                    "|---|---:|---|---:|---|",
                ]
            )
            for symbol in selected:
                purpose = symbol["purpose"].replace("|", "\\|").replace("\n", " ")
                refs = (
                    "; ".join(symbol["review_test_references"]).replace("|", "\\|")
                    or "No standalone mapping; see scenario matrix"
                )
                md.append(
                    f"| `{symbol['name']}` ({symbol['kind']}) | {symbol['line']} | {purpose} | {symbol['observed_calls_at_73780b4_unit_cloud_only']} | {refs} |"
                )
            md.append("")
    md.extend(
        [
            "## Missing local Markdown targets",
            "",
            "These include documentation templates and excluded private evidence; each needs interpretation before packaging/publication.",
            "",
        ]
    )
    md.extend(f"- `{r['file']}` → `{r['target']}`" for r in links)
    if not links:
        md.append(
            "None found by the inline-link scan. Reference-style URLs and code examples are not checked."
        )
    (OUT / "FILE_FUNCTION_INVENTORY.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "files": len(files),
                "symbols": len(symbols),
                "missing_inline_markdown_targets": len(links),
                "commit": commit,
            }
        )
    )


if __name__ == "__main__":
    main()
