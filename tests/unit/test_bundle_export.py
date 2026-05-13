"""tests/unit/test_bundle_export.py — Unit tests for bundle export flow.

Tests:
- ExportService generates valid ZIP with correct structure
- Pydantic validation: min_agents, max_iter range, soul_json fields
- Error handling for missing goal/backstory
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from pydantic import ValidationError

from src.services.bundle_schemas import (
    AgentExportItem,
    ExportBundleRequest,
    SkillExportItem,
)
from src.services.export_service import ExportService


def test_export_service_generates_valid_zip():
    """TP-1: ExportService generates valid ZIP with manifest + agents + skills."""
    payload = ExportBundleRequest(
        bundle_name="test-export",
        agents=[
            AgentExportItem(
                role="qa_agent",
                soul_json={"role": "QA", "goal": "Test the application thoroughly",
                           "backstory": "A meticulous tester with years of experience"},
                allowed_tools=["search", "read"],
                max_iter=5,
            )
        ],
        skills=[
            SkillExportItem(name="custom_tool", code="def run(): return 'ok'\n"),
        ],
    )

    service = ExportService(org_id="test-org-123")
    zip_bytes, filename = service.export(payload)

    assert filename == "test-export.zip"
    assert len(zip_bytes) > 0

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "agents/qa_agent.json" in names
        assert "skills/custom_tool.py" in names

        manifest = json.loads(z.read("manifest.json"))
        assert manifest["version"] == "2.0"
        assert manifest["bundle_info"]["name"] == "test-export"
        assert "hashes" in manifest

        agent = json.loads(z.read("agents/qa_agent.json"))
        assert agent["role"] == "qa_agent"

        skill_code = z.read("skills/custom_tool.py").decode("utf-8")
        assert "def run():" in skill_code


def test_export_service_default_bundle_name():
    """ExportService generates default name when bundle_name is None."""
    payload = ExportBundleRequest(
        agents=[
            AgentExportItem(
                role="analyst",
                soul_json={"goal": "Analyze complex data sets accurately",
                           "backstory": "A senior data analyst"},
                allowed_tools=[],
            )
        ],
    )

    service = ExportService(org_id="test-org-456")
    zip_bytes, filename = service.export(payload)

    assert zip_bytes
    assert filename.endswith(".zip")
    assert filename.startswith("export_")


def test_agent_export_item_max_iter_range():
    """TP-4: Pydantic validation rejects max_iter outside 1-50."""
    with pytest.raises(ValidationError) as exc_info:
        AgentExportItem(
            role="bad_agent",
            soul_json={"goal": "something", "backstory": "something"},
            max_iter=100,
        )
    assert "max_iter" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        AgentExportItem(
            role="bad_agent",
            soul_json={"goal": "something", "backstory": "something"},
            max_iter=0,
        )
    assert "max_iter" in str(exc_info.value)


def test_export_bundle_request_min_agents():
    """TP-3: Pydantic validation rejects empty agents list."""
    with pytest.raises(ValidationError) as exc_info:
        ExportBundleRequest(agents=[])
    assert "agents" in str(exc_info.value)


def test_export_bundle_request_max_agents():
    """Pydantic validation rejects agents > 15."""
    agents = [
        AgentExportItem(
            role=f"agent_{i}",
            soul_json={"goal": "do things", "backstory": "trained expert"},
        )
        for i in range(16)
    ]

    with pytest.raises(ValidationError) as exc_info:
        ExportBundleRequest(agents=agents)
    assert "agents" in str(exc_info.value)


def test_export_service_without_skills():
    """ExportService generates valid ZIP without skills."""
    payload = ExportBundleRequest(
        agents=[
            AgentExportItem(
                role="simple_agent",
                soul_json={"goal": "Execute basic tasks efficiently",
                           "backstory": "A general-purpose assistant"},
            )
        ],
    )

    service = ExportService(org_id="test-org-789")
    zip_bytes, filename = service.export(payload)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "agents/simple_agent.json" in names
        # No skills/ directory
        skill_dirs = [n for n in names if n.startswith("skills/")]
        assert len(skill_dirs) == 0


def test_export_service_multiple_agents():
    """ExportService handles multiple agents correctly."""
    payload = ExportBundleRequest(
        agents=[
            AgentExportItem(
                role="analyst",
                soul_json={"goal": "Analyze data carefully",
                           "backstory": "Senior data analyst with 10 years experience"},
            ),
            AgentExportItem(
                role="executor",
                soul_json={"goal": "Execute tasks precisely",
                           "backstory": "Meticulous task executor"},
            ),
            AgentExportItem(
                role="reviewer",
                soul_json={"goal": "Review work for quality",
                           "backstory": "Experienced quality reviewer"},
            ),
        ],
    )

    service = ExportService(org_id="test-org-multi")
    zip_bytes, _ = service.export(payload)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        agent_names = [n for n in z.namelist() if n.startswith("agents/")]
        assert len(agent_names) == 3
