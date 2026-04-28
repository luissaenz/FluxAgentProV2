"""src/cli/utils.py — CLI-specific utilities for FAP-CLI."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from src.services.integrity import calculate_sha256

logger = logging.getLogger(__name__)


def create_manifest_base(name: str, author: str = "dev@org.com") -> Dict[str, Any]:
    """Create a baseline manifest.json structure."""
    from datetime import UTC, datetime

    return {
        "version": "2.0",
        "name": name,
        "author": author,
        "created_at": datetime.now(UTC).isoformat(),
        "schema_version": "2.0",
        "hashes": {},
    }


def calculate_dir_hashes(base_dir: Path) -> Dict[str, str]:
    """Calculate SHA256 for all relevant files in a bundle directory.

    Relevant subdirectories: agents/, flows/, skills/, context/
    """
    hashes = {}
    valid_subdirs = {"agents", "flows", "skills", "context"}

    for subdir in valid_subdirs:
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                # Get path relative to base_dir for the manifest key
                rel_path = file_path.relative_to(base_dir).as_posix()
                with open(file_path, "rb") as f:
                    hashes[rel_path] = calculate_sha256(f.read())

    return hashes


def save_json(path: Path, data: Any):
    """Save data as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Any:
    """Load JSON data from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
