#!/usr/bin/env python3
"""scripts/migrate_basetool.py — Automated refactoring tool for OrgBaseTool.

Scans the codebase for usages of `BaseTool` and replaces them with `OrgBaseTool`.
Reports where manual intervention (`_get_secret()`) might be needed.
"""

import argparse
import re
import sys
from pathlib import Path

# Color constants
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE_DIR = Path(__file__).parent.parent

TARGET_DIRS = [BASE_DIR / "src" / "tools", BASE_DIR / "skills"]

EXCLUDED_FILES = ["base_tool.py"]


def process_file(file_path: Path, check_only: bool) -> bool:
    if file_path.name in EXCLUDED_FILES:
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"{RED}[ERROR] Could not read {file_path.name}: {e}{RESET}")
        return False

    has_base_tool_import = "from crewai.tools import BaseTool" in content
    has_base_tool_usage = re.search(r"class\s+\w+\(BaseTool\):", content)

    if not has_base_tool_import and not has_base_tool_usage:
        return False

    if check_only:
        print(
            f"{YELLOW}[WARN] {file_path.relative_to(BASE_DIR)} uses BaseTool and needs migration.{RESET}"
        )
        return True

    # Migrate import
    # Some tools might be in subdirectories of src.tools, so absolute import is safer:
    # "from src.tools.base_tool import OrgBaseTool"
    new_content = content.replace(
        "from crewai.tools import BaseTool",
        "from src.tools.base_tool import OrgBaseTool",
    )

    # Migrate class inheritance
    new_content = re.sub(
        r"(class\s+\w+\()BaseTool(\):)", r"\1OrgBaseTool\2", new_content
    )

    file_path.write_text(new_content, encoding="utf-8")
    print(f"{GREEN}[MIGRATED] {file_path.relative_to(BASE_DIR)}{RESET}")
    print(
        f"  {BLUE}-> Please verify if `_get_secret()` is needed for vault access.{RESET}"
    )

    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate BaseTool to OrgBaseTool.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for usages without modifying files.",
    )
    args = parser.parse_args()

    print(f"{BLUE}--- Scanning for BaseTool usage ---{RESET}")

    found_issues = False
    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue

        for file_path in target_dir.rglob("*.py"):
            if process_file(file_path, args.check):
                found_issues = True

    if not found_issues:
        print(f"{GREEN}✨ No legacy BaseTool usages found! ✨{RESET}")
    else:
        if args.check:
            print(
                f"\n{RED}❌ Issues found. Run without --check to apply migrations.{RESET}"
            )
            sys.exit(1)
        else:
            print(
                f"\n{GREEN}✅ Migration completed. Check logs above for files that need manual verification.{RESET}"
            )


if __name__ == "__main__":
    main()
