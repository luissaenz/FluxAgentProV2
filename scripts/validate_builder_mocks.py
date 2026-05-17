"""Validate builder mock configuration integrity.

Usage:  python scripts/validate_builder_mocks.py [--dry-run]
Returns: exit code 0 if all checks pass, 1 otherwise.

Verifies that test mock patches cover all import points of
get_service_client, get_tenant_client, and get_anon_client used
in builder-related modules, and that global_llm_mock is correctly
scoped to avoid polluting non-builder test suites.
"""

from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("validate_builder_mocks")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFTEST = PROJECT_ROOT / "tests" / "conftest.py"
E2E_CONFTEST = PROJECT_ROOT / "tests" / "e2e" / "conftest.py"

# Modules that MUST be patched for builder tests
BUILDER_MODULES = [
    "src.api.routes.templates",
    "src.api.routes.bundles",
    "src.api.routes.tools",
    "src.services.import_service",
    "src.services.export_service",
]

CLIENT_FUNCTIONS = [
    "get_service_client",
    "get_tenant_client",
]


def extract_patch_points(conftest_path: Path) -> set[str]:
    """Parse conftest.py AST and extract all string literals used as patch points."""
    if not conftest_path.exists():
        return set()

    tree = ast.parse(conftest_path.read_text())
    points: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "get_service_client" in node.value or "get_tenant_client" in node.value or "get_anon_client" in node.value:
                points.add(node.value)
    return points


def check_autouse(conftest_path: Path) -> bool:
    """Check that mock_service_client fixture has autouse=True."""
    if not conftest_path.exists():
        return False

    tree = ast.parse(conftest_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "mock_service_client":
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    for kw in decorator.keywords:
                        if kw.arg == "autouse":
                            if isinstance(kw.value, ast.Constant):
                                return bool(kw.value.value)
    return False


def check_global_llm_not_autouse(conftest_path: Path) -> bool:
    """Verify global_llm_mock is NOT in root conftest (should be in e2e/conftest.py)."""
    if not conftest_path.exists():
        return True

    tree = ast.parse(conftest_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "global_llm_mock":
            # Check if it has autouse=True — that's the problematic pattern
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    for kw in decorator.keywords:
                        if kw.arg == "autouse":
                            if isinstance(kw.value, ast.Constant) and kw.value.value:
                                return False  # autouse=True in root conftest is BAD
            return False  # Still bad if it exists in root conftest at all
    return True


def run(dry_run: bool = False) -> int:
    """Run all mock validation checks. Returns 0 on success, 1 on failure."""
    log.info("=" * 60)
    log.info("  Builder Mock Validation")
    log.info("=" * 60)

    failures = 0

    # Check 1: conftest.py exists
    log.info("\n[1/5] Checking conftest.py exists...")
    if not CONFTEST.exists():
        log.error("  ✗ tests/conftest.py not found")
        failures += 1
    else:
        log.info("  ✓ tests/conftest.py exists")

    # Check 2: mock_service_client has autouse=True
    log.info("\n[2/5] Checking mock_service_client autouse...")
    if check_autouse(CONFTEST):
        log.info("  ✓ mock_service_client has autouse=True")
    else:
        log.error("  ✗ mock_service_client missing autouse=True")
        failures += 1

    # Check 3: All builder modules are covered by patches
    log.info("\n[3/5] Checking patch coverage for builder modules...")
    patch_points = extract_patch_points(CONFTEST)
    for module in BUILDER_MODULES:
        covered = False
        for fn in CLIENT_FUNCTIONS:
            point = f"{module}.{fn}"
            if point in patch_points:
                covered = True
        if covered:
            log.info(f"  ✓ {module}")
        else:
            log.error(f"  ✗ {module} — missing patch points")
            failures += 1

    # Check 4: global_llm_mock NOT autouse in root conftest
    log.info("\n[4/5] Checking global_llm_mock scope...")
    if check_global_llm_not_autouse(CONFTEST):
        log.info("  ✓ global_llm_mock not in root conftest (correctly scoped)")
    else:
        log.error("  ✗ global_llm_mock with autouse=True in root conftest — risk of breaking non-builder tests")
        failures += 1

    # Check 5: e2e conftest exists
    log.info("\n[5/5] Checking e2e/conftest.py exists...")
    if E2E_CONFTEST.exists():
        log.info("  ✓ tests/e2e/conftest.py exists")
    else:
        log.warning("  ⚠ tests/e2e/conftest.py not found (optional)")

    # Summary
    log.info("\n" + "=" * 60)
    if failures == 0:
        log.info("  ✅ All checks passed")
    else:
        log.info(f"  ❌ {failures} check(s) failed")

    if dry_run:
        log.info("  (dry-run mode — no changes made)")

    log.info("=" * 60)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sys.exit(run(dry_run=dry_run))
