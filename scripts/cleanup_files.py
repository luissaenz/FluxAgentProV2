"""Cleanup local files: POC artifacts, caches, logs.

Usage:  python scripts/cleanup_files.py
Safe to rerun.
"""

import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup-files")

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    # POC artifacts
    ("file", "kilo.json"),
    ("dir", "migration_bundle"),
    ("file", "temp_seed.json"),
    ("file", "test_failure.log"),
    ("file", "data/service_catalog_seed.json.bak"),
    # Caches
    ("dir", ".ruff_cache"),
    ("dir", ".pytest_cache"),
]

PYCACHE_DIRS = [
    "src/__pycache__",
    "src/api/__pycache__",
    "src/api/routes/__pycache__",
    "src/cli/__pycache__",
    "src/cli/commands/__pycache__",
    "src/connectors/__pycache__",
    "src/crews/__pycache__",
    "src/crews/bartenders/__pycache__",
    "src/db/__pycache__",
    "src/flows/__pycache__",
    "src/mcp/__pycache__",
    "src/scheduler/__pycache__",
    "src/services/__pycache__",
    "src/tools/__pycache__",
    "src/tools/demo/__pycache__",
    "src/utils/__pycache__",
    "scripts/__pycache__",
]


def remove(path: Path, kind: str) -> None:
    if not path.exists():
        return
    try:
        if kind == "dir":
            shutil.rmtree(path)
        else:
            path.unlink()
        log.info(f"  ✓ removed {path.relative_to(ROOT)}")
    except Exception as e:
        log.warning(f"  ? {path.relative_to(ROOT)}: {e}")


def main():
    log.info("=" * 50)
    log.info("  FILE CLEANUP START")
    log.info("=" * 50)

    log.info("\n[1/2] Removing POC artifacts + caches...")
    for kind, rel in TARGETS:
        remove(ROOT / rel, kind)

    log.info("\n[2/2] Removing __pycache__ dirs...")
    removed = 0
    for rel in PYCACHE_DIRS:
        p = ROOT / rel
        if p.exists():
            shutil.rmtree(p)
            removed += 1
    # Also find any remaining __pycache__ recursively
    for p in ROOT.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p)
            removed += 1
    log.info(f"  ✓ removed {removed} __pycache__ directories")


if __name__ == "__main__":
    main()
