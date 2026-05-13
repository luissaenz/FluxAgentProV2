"""scripts/bundle_validator.py — Validate FAP-Bundle v2 ZIP structure offline.

Checks that a ZIP file contains:
- manifest.json with valid v2.0 schema
- agents/*.json files matching manifest hashes
- skills/*.py files (optional)
- Manifest hashes match actual file contents

Usage:
    uv run python scripts/bundle_validator.py ./bundle.zip
    uv run python scripts/bundle_validator.py ./bundle.zip --verbose
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


def validate_bundle(zip_path: Path, verbose: bool = False) -> tuple[bool, list[str]]:
    """Validate a FAP-Bundle v2 ZIP file.

    Returns:
        tuple[bool, list[str]]: (is_valid, messages)
    """
    messages: list[str] = []
    if not zip_path.exists():
        return False, [f"ERROR: File not found: {zip_path}"]

    if not zip_path.suffix.lower() == ".zip":
        return False, [f"ERROR: Not a ZIP file: {zip_path}"]

    try:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()

            # 1. Require manifest.json
            if "manifest.json" not in names:
                return False, [
                    "ERROR: Missing manifest.json in bundle root",
                    f"  Files found: {names}",
                ]

            # 2. Parse and validate manifest
            try:
                manifest = json.loads(z.read("manifest.json"))
            except json.JSONDecodeError as e:
                return False, [f"ERROR: manifest.json is not valid JSON: {e}"]

            version = manifest.get("version")
            if version != "2.0":
                messages.append(f"WARN: manifest version is '{version}', expected '2.0'")

            bundle_info = manifest.get("bundle_info", {})
            if bundle_info:
                bname = bundle_info.get("name", "?")
                messages.append(f"INFO: Bundle name: {bname}")
                if verbose:
                    messages.append(f"INFO: Version: {bundle_info.get('version', '?')}")
                    messages.append(f"INFO: Author: {bundle_info.get('author', '?')}")

            # 3. Check hashes
            hashes = manifest.get("hashes", {})
            if not hashes:
                messages.append("WARN: No hashes in manifest")
            else:
                messages.append(f"INFO: {len(hashes)} file(s) in manifest")

                for rel_path, expected_hash in hashes.items():
                    if rel_path not in names:
                        messages.append(
                            f"ERROR: '{rel_path}' declared in manifest but not in ZIP"
                        )
                        continue

                    file_data = z.read(rel_path)
                    actual_hash = f"sha256:{hashlib.sha256(file_data).hexdigest()}"
                    if actual_hash != expected_hash:
                        messages.append(
                            f"ERROR: Hash mismatch for '{rel_path}'"
                        )
                    elif verbose:
                        messages.append(f"  OK: {rel_path}")

            # 4. Count agents, flows, skills
            agent_files = [
                n for n in names if n.startswith("agents/") and n.endswith(".json")
            ]
            skill_files = [
                n for n in names if n.startswith("skills/") and n.endswith(".py")
            ]
            flow_files = [
                n for n in names if n.startswith("flows/")
            ]

            messages.append(f"INFO: {len(agent_files)} agent(s)")
            messages.append(f"INFO: {len(skill_files)} skill(s)")
            messages.append(f"INFO: {len(flow_files)} flow file(s)")

            if verbose and agent_files:
                for af in agent_files:
                    role = af.replace("agents/", "").replace(".json", "")
                    messages.append(f"  Agent: {role}")

            # 5. Check for unexpected files
            valid_prefixes = ("manifest.json", "agents/", "skills/", "flows/", "context/")
            for name in names:
                if not any(name.startswith(p) for p in valid_prefixes):
                    messages.append(f"WARN: Unexpected file: {name}")

            # Determine success
            has_errors = any(m.startswith("ERROR:") for m in messages)
            return not has_errors, messages

    except zipfile.BadZipFile:
        return False, ["ERROR: Invalid or corrupt ZIP file"]
    except Exception as e:
        return False, [f"ERROR: Unexpected error: {e}"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/bundle_validator.py <bundle.zip> [--verbose]")
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    verbose = "--verbose" in sys.argv

    print(f"Validating: {zip_path.resolve()}")
    print("-" * 50)

    is_valid, messages = validate_bundle(zip_path, verbose=verbose)

    for msg in messages:
        print(msg)

    print("-" * 50)
    if is_valid:
        print("RESULT: PASS — Bundle structure is valid")
        sys.exit(0)
    else:
        print("RESULT: FAIL — Bundle validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
