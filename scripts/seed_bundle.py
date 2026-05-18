"""seed_bundle.py — Copy presupuesto-bundle/ to data/seed/presupuesto-bundle/ with SHA256 recalculation.

Usage:
    python scripts/seed_bundle.py

Creates data/seed/presupuesto-bundle/ with manifest.json + agents/presupuestador.json,
recalculates SHA256 hashes, and prints the result.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "presupuesto-bundle"
DEST = ROOT / "data" / "seed" / "presupuesto-bundle"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _calculate_manifest_hash(path: Path) -> str:
    return f"sha256:{_sha256(path)}"


def run() -> None:
    if not SOURCE.exists():
        print(f"Error: Source bundle not found at {SOURCE}")
        sys.exit(1)

    DEST.mkdir(parents=True, exist_ok=True)

    agents_dir = DEST / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    src_agent = SOURCE / "agents" / "presupuestador.json"
    if not src_agent.exists():
        print(f"Error: {src_agent} not found")
        sys.exit(1)

    dst_agent = agents_dir / "presupuestador.json"
    shutil.copy2(src_agent, dst_agent)
    print(f"Copied {src_agent} -> {dst_agent}")

    agent_hash = _calculate_manifest_hash(dst_agent)

    src_manifest = SOURCE / "manifest.json"
    if not src_manifest.exists():
        print(f"Error: {src_manifest} not found")
        sys.exit(1)

    with open(src_manifest, encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["hashes"] = {"agents/presupuestador.json": agent_hash}

    dst_manifest = DEST / "manifest.json"
    with open(dst_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Created {dst_manifest} (hash: {agent_hash})")

    print(f"\nBundle seed created at {DEST}")
    print(f"  manifest.json hash matches: {manifest['hashes']['agents/presupuestador.json'] == agent_hash}")


if __name__ == "__main__":
    run()
