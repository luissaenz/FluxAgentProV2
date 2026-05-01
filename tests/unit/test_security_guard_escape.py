"""tests/unit/test_security_guard_escape.py — Escape attempt tests.

Tests:
- SE5.17: importlib.import_module bypass
- SE5.18: hex-decoded exec bypass
"""

import pytest

from src.services.security_guard import SecurityError, SecurityGuard


@pytest.fixture
def guard():
    return SecurityGuard(timeout_seconds=2)


def test_se5_17_importlib_bypass(guard):
    code = "import importlib; importlib.import_module('os')"
    with pytest.raises(SecurityError):
        guard.validate_skill(code)


def test_se5_18_hex_exec_bypass(guard):
    hex_code = "exec(b'\\x69\\x6d\\x70\\x6f\\x72\\x74\\x20\\x6f\\x73'.decode())"
    with pytest.raises(SecurityError):
        guard.validate_skill(hex_code)
