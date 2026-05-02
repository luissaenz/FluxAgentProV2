"""scripts/validate_cli_structure.py — Detect CLI module path drift.

Scans src/cli/main.py for command imports and verifies all registered
CLI command modules reside under src/cli/commands/. Exits 0 if clean.

Usage:
    python scripts/validate_cli_structure.py
    python scripts/validate_cli_structure.py --fix  (not implemented)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = PROJECT_ROOT / "src" / "cli" / "main.py"


def _parse_imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _check_imports(imports: list[str]) -> list[dict[str, str]]:
    drift: list[dict[str, str]] = []
    for mod in imports:
        if not mod.startswith("src.cli."):
            continue
        parts = mod.split(".")
        if len(parts) < 3:
            continue
        # parts = ["src", "cli", "commands", "..."] or ["src", "cli", "baseline"]
        after_cli = parts[2]
        if after_cli != "commands":
            drift.append({"module": mod, "issue": f"Module not under src/cli/commands/ (found: src/cli/{after_cli})"})
    return drift


def _validate() -> list[dict[str, str]]:
    if not MAIN_PY.exists():
        print(f"[ERROR] main.py not found: {MAIN_PY}")
        sys.exit(1)

    source = MAIN_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = _parse_imports(tree)
    drift = _check_imports(imports)
    return drift


def main() -> None:
    drift = _validate()

    if not drift:
        print("[OK] All CLI command modules are under src/cli/commands/")
        sys.exit(0)

    print(f"[WARN] {len(drift)} CLI import(s) outside src/cli/commands/:\n")
    for entry in drift:
        print(f"  - {entry['module']}")
        print(f"    Issue: {entry['issue']}")
    print()
    sys.exit(1)


if __name__ == "__main__":
    main()
