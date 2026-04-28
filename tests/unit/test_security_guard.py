"""tests/unit/test_security_guard.py — Unit tests for SecurityGuard.

Tests:
- Safe code validation
- Forbidden import detection (os, subprocess, etc.)
- Forbidden call detection (eval, exec, open)
- Dunder attribute access detection (__subclasses__)
"""

import pytest
from src.services.security_guard import SecurityGuard, SecurityError


@pytest.fixture
def guard():
    return SecurityGuard()


def test_safe_code(guard):
    safe_code = """
def process_data(data):
    result = [x * 2 for x in data]
    return result
"""
    assert guard.validate_skill(safe_code) is True


def test_forbidden_import_os(guard):
    malicious_code = "import os\ndef exploit(): os.system('ls')"
    with pytest.raises(SecurityError, match="Forbidden import 'os'"):
        guard.validate_skill(malicious_code)


def test_forbidden_import_from_subprocess(guard):
    malicious_code = "from subprocess import Popen\ndef exploit(): Popen(['ls'])"
    with pytest.raises(SecurityError, match="Forbidden import from 'subprocess'"):
        guard.validate_skill(malicious_code)


def test_forbidden_eval(guard):
    malicious_code = "def exploit(cmd): eval(cmd)"
    with pytest.raises(SecurityError, match="Forbidden function call 'eval'"):
        guard.validate_skill(malicious_code)


def test_forbidden_open(guard):
    malicious_code = "def exploit(): open('/etc/passwd')"
    with pytest.raises(SecurityError, match="Forbidden function call 'open'"):
        guard.validate_skill(malicious_code)


def test_dunder_access(guard):
    malicious_code = "def exploit(): ().__class__.__subclasses__()"
    with pytest.raises(SecurityError, match="Forbidden access to dunder attribute '__subclasses__'"):
        guard.validate_skill(malicious_code)


def test_syntax_error(guard):
    bad_code = "def incomplete("
    with pytest.raises(SecurityError, match="Syntax error"):
        guard.validate_skill(bad_code)
