#!/usr/bin/env python3
"""scripts/sanitize_codebase.py — Automated code hygiene tool.

Uses ruff to enforce linting, formatting, and import organization.
Analysis Final §81-83: New DX Tooling.
"""

import subprocess
import sys
from pathlib import Path

# Analysis Final §2.2: Configure encoding for Windows
if sys.platform == "win32" and sys.stdout.isatty():
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Color constants
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

BASE_DIR = Path(__file__).parent.parent


def run_step(name, cmd):
    print(f"\n{BLUE}==> {name}...{RESET}")
    try:
        subprocess.run(cmd, cwd=BASE_DIR, check=True)
        print(f"{GREEN}[OK] {name} completed.{RESET}")
    except subprocess.CalledProcessError:
        print(f"{RED}[FAIL] {name} failed.{RESET}")
        return False
    except FileNotFoundError:
        print(
            f"{RED}[ERROR] 'ruff' not found. Please install it with 'pip install ruff'.{RESET}"
        )
        return False
    return True


def main():
    print(f"{BLUE}--- FAP Codebase Sanitization ---{RESET}")

    # 1. Check if ruff is installed
    steps = [
        ("Organizing Imports", ["ruff", "check", "--select", "I", "--fix", "."]),
        ("Linting & Auto-fixing", ["ruff", "check", "--fix", "."]),
        ("Formatting Code", ["ruff", "format", "."]),
    ]

    success = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            success = False
            break

    if success:
        print(f"\n{GREEN}✨ Codebase is clean and sanitized! ✨{RESET}")
    else:
        print(f"\n{RED}❌ Sanitization failed. Please check the errors above.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
