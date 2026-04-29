"""src/utils/bundle_utils.py — Utilities for FAP bundles (hashing, manifest)."""

import json
from pathlib import Path
from typing import Dict

from src.services.integrity import calculate_sha256


def get_file_hash(file_path: Path) -> str:
    """Calculate the SHA256 hash of a file using the project's integrity service."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        return calculate_sha256(f.read())

def calculate_bundle_hashes(bundle_path: Path) -> Dict[str, str]:
    """Scan the bundle directory and return a dictionary of SHA256 hashes."""
    hashes = {}
    # Scan directories: agents/, skills/, flows/
    for folder in ["agents", "skills", "flows"]:
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

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Ensure v2.0 structure
    if manifest.get("version") != "2.0":
        manifest["version"] = "2.0"
        if "bundle_info" not in manifest:
            manifest["bundle_info"] = {
                "name": bundle_path.name,
                "description": "Auto-migrated bundle",
                "version": "1.0.0"
            }

    # Calculate and update hashes
    manifest["hashes"] = calculate_bundle_hashes(bundle_path)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def create_base_manifest(name: str, version: str = "1.0.0", author: str = "Unknown") -> Dict:
    """Create a basic manifest structure (v2.0)."""
    return {
        "version": "2.0",
        "bundle_info": {
            "name": name,
            "description": f"Bundle for {name}",
            "version": version,
            "author": author
        },
        "hashes": {}
    }

