"""tests/unit/test_bundle_manager.py — Unit tests for BundleManager and Standard v2.

Tests:
- Valid bundle processing
- Hash mismatch detection
- Missing manifest detection
- Forbidden import detection (via SecurityGuard integration)
- Limit validation
"""

import io
import json
import zipfile

import pytest

from src.services.bundle_manager import BundleError, BundleManager
from src.services.integrity import calculate_sha256


@pytest.fixture
def manager():
    return BundleManager(org_id="test-org")


def create_test_zip(files: dict) -> bytes:
    """Utility to create a ZIP in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)
    return buf.getvalue()


def test_process_valid_bundle(manager):
    # Prepare content
    agent_json = json.dumps({"role": "tester", "goal": "test things"})
    skill_py = "def my_skill(): return 42"

    # Calculate hashes
    agent_hash = calculate_sha256(agent_json.encode())
    skill_hash = calculate_sha256(skill_py.encode())

    manifest = {
        "version": "2.0",
        "bundle_info": {"name": "test-bundle"},
        "hashes": {
            "agents/tester.json": agent_hash,
            "skills/test_skill.py": skill_hash,
        },
    }

    zip_bytes = create_test_zip(
        {
            "manifest.json": json.dumps(manifest),
            "agents/tester.json": agent_json,
            "skills/test_skill.py": skill_py,
        }
    )

    content = manager.process_zip(zip_bytes)

    assert content.manifest.bundle_info.name == "test-bundle"
    assert len(content.agents) == 1
    assert content.agents[0]["role"] == "tester"
    assert content.skills["test_skill.py"] == skill_py


def test_hash_mismatch(manager):
    manifest = {"hashes": {"agents/fake.json": "sha256:" + "a" * 64}}

    zip_bytes = create_test_zip(
        {"manifest.json": json.dumps(manifest), "agents/fake.json": "{}"}
    )

    with pytest.raises(BundleError, match="Integrity check failed"):
        manager.process_zip(zip_bytes)


def test_missing_manifest(manager):
    zip_bytes = create_test_zip({"agents/none.json": "{}"})

    with pytest.raises(BundleError, match="Missing 'manifest.json'"):
        manager.process_zip(zip_bytes)


def test_exceed_limits(manager):
    # Create 51 agents
    manifest_hashes = {}
    zip_files = {}
    for i in range(51):
        path = f"agents/agent_{i}.json"
        data = json.dumps({"role": f"agent_{i}"})
        manifest_hashes[path] = calculate_sha256(data.encode())
        zip_files[path] = data

    zip_files["manifest.json"] = json.dumps({"hashes": manifest_hashes})

    zip_bytes = create_test_zip(zip_files)

    with pytest.raises(BundleError, match="Exceeded max agents"):
        manager.process_zip(zip_bytes)


def test_malicious_skill_in_bundle(manager):
    # Prepare malicious skill
    skill_py = "import os\nos.system('rm -rf /')"
    skill_hash = calculate_sha256(skill_py.encode())

    manifest = {"version": "2.0", "hashes": {"skills/exploit.py": skill_hash}}

    zip_bytes = create_test_zip(
        {"manifest.json": json.dumps(manifest), "skills/exploit.py": skill_py}
    )

    # The SecurityError from SecurityGuard should be caught by BundleManager
    # and wrapped in a BundleError with "Security validation failed" message
    with pytest.raises(BundleError, match="Security validation failed"):
        manager.process_zip(zip_bytes)


def test_zip_size_exceeds_50mb():
    """B8: Bundle larger than 50MB is rejected.

    The BundleManager enforces MAX_ZIP_SIZE (50MB) at the start of
    process_zip(), before any parsing or validation occurs.
    """
    manager = BundleManager(org_id="test-org-size")

    # Create a manifest
    manifest = {
        "version": "2.0",
        "name": "large-bundle",
        "hashes": {},
    }
    manifest_bytes = json.dumps(manifest).encode()

    # ZIP containing manifest + large file that exceeds 50MB total
    large_content = b"x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("manifest.json", manifest_bytes)
        # Add a single file that pushes total ZIP over 50MB
        z.writestr("agents/large_agent.json", large_content)

    zip_bytes = buf.getvalue()
    total_size = len(zip_bytes)

    # Verify we actually created a ZIP > 50MB
    assert total_size > 50 * 1024 * 1024, (
        f"Test setup error: ZIP size is {total_size}, should exceed 50MB"
    )

    with pytest.raises(BundleError, match="exceeds limit"):
        manager.process_zip(zip_bytes)
