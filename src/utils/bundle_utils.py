"""src/utils/bundle_utils.py — Utilities for FAP bundles (hashing, manifest)."""

import json
from pathlib import Path
from typing import Dict, List

from src.services.integrity import calculate_sha256

# Analysis Final §65: Centralized subdirectories
BUNDLE_SUBDIRS: List[str] = ["agents", "flows", "skills", "context"]


def get_file_hash(file_path: Path) -> str:
    """Calculate the SHA256 hash of a file using the project's integrity service."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Analysis Final §104: Use encoding="utf-8" (not needed for binary read, but good practice for others)
    with open(file_path, "rb") as f:
        return calculate_sha256(f.read())


def calculate_bundle_hashes(bundle_path: Path) -> Dict[str, str]:
    """Scan the bundle directory and return a dictionary of SHA256 hashes."""
    hashes = {}
    # Analysis Final §65: Use centralized subdirs
    for folder in BUNDLE_SUBDIRS:
        folder_path = bundle_path / folder
        if folder_path.exists() and folder_path.is_dir():
            for file_path in folder_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    rel_path = file_path.relative_to(bundle_path).as_posix()
                    hashes[rel_path] = get_file_hash(file_path)
    return hashes


def update_manifest_hashes(bundle_path: Path) -> Dict:
    """
    Scan the bundle directory and update manifest.json with real SHA256 hashes.
    Returns the updated manifest content.
    """
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {bundle_path}")

    # Analysis Final §104: Use encoding="utf-8"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Analysis Final §66: Ensure v2.0 structure and migration
    if manifest.get("version") != "2.0":
        manifest["version"] = "2.0"
        if "bundle_info" not in manifest:
            # Try to recover legacy fields or use defaults
            manifest["bundle_info"] = {
                "name": manifest.get("name") or bundle_path.name,
                "description": manifest.get("description") or "Auto-migrated bundle",
                "version": manifest.get("version_info", {}).get("version") or "1.0.0",
                "author": manifest.get("author") or "Unknown",
            }
            # Clean up old fields
            for field in ["name", "description", "author", "version_info"]:
                manifest.pop(field, None)

    # Calculate and update hashes
    manifest["hashes"] = calculate_bundle_hashes(bundle_path)

    # Analysis Final §104: Use encoding="utf-8"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def create_base_manifest(
    name: str, version: str = "1.0.0", author: str = "Unknown"
) -> Dict:
    """Create a basic manifest structure (v2.0)."""
    return {
        "version": "2.0",
        "bundle_info": {
            "name": name,
            "description": f"Bundle for {name}",
            "version": version,
            "author": author,
        },
        "hashes": {},
    }
