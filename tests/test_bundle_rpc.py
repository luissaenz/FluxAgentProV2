"""tests/test_bundle_rpc.py — Unit tests for the Bundle RPC payload and result models."""

import pytest
from pydantic import ValidationError

from src.services.bundle_schemas import BundleRPCPayload, BundleRPCResult


def test_bundle_rpc_payload_validation():
    """Test that BundleRPCPayload validates correctly."""
    valid_payload = {
        "bundle_name": "test-bundle",
        "bundle_hash": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "agents": [{"role": "analyst", "goal": "analyze"}],
        "flows": [{"flow_type": "standard", "name": "Standard Flow"}],
        "skills": {"skill1.py": "print('hello')"},
    }

    payload = BundleRPCPayload(**valid_payload)
    assert payload.bundle_name == "test-bundle"
    assert len(payload.agents) == 1
    assert payload.skills["skill1.py"] == "print('hello')"


def test_bundle_rpc_payload_missing_fields():
    """Test that BundleRPCPayload fails on missing required fields."""
    with pytest.raises(ValidationError):
        BundleRPCPayload(bundle_name="missing-hash")


def test_bundle_rpc_result_parsing():
    """Test that BundleRPCResult parses typical RPC responses correctly."""
    rpc_response = {
        "status": "success",
        "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
        "agents_count": 2,
        "flows_count": 1,
        "skills_count": 3,
    }

    result = BundleRPCResult(**rpc_response)
    assert result.status == "success"
    assert result.bundle_id == "550e8400-e29b-41d4-a716-446655440000"
    assert result.agents_count == 2
    assert result.error is None


def test_bundle_rpc_result_error():
    """Test that BundleRPCResult handles error responses correctly."""
    error_response = {
        "status": "failed",
        "bundle_id": "",
        "error": "Duplicate key violation",
    }

    result = BundleRPCResult(**error_response)
    assert result.status == "failed"
    assert result.error == "Duplicate key violation"
