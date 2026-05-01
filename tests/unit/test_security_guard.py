"""tests/unit/test_security_guard.py — Unit tests for SecurityGuard.

Tests:
- Safe code validation (Allowlist)
- Forbidden import detection (os, subprocess, sys, red)
- Forbidden call detection (eval, exec, open)
- Dunder attribute access detection (__subclasses__)
- Timeout detection (active sandbox)
"""

import pytest

from src.services.security_guard import SecurityError, SecurityGuard


@pytest.fixture
def guard():
    return SecurityGuard(timeout_seconds=2)


def test_safe_code(guard):
    safe_code = """
import json
import math
from datetime import datetime

def process_data(data):
    result = [math.sqrt(x) for x in data]
    return {"result": result, "now": datetime.now().isoformat()}
"""
    assert guard.validate_skill(safe_code) is True


def test_forbidden_import_os(guard):
    malicious_code = "import os\ndef exploit(): os.system('ls')"
    with pytest.raises(SecurityError, match="Forbidden import 'os'"):
        guard.validate_skill(malicious_code)


def test_forbidden_import_sys(guard):
    malicious_code = "import sys\ndef exploit(): print(sys.path)"
    with pytest.raises(SecurityError, match="Forbidden import 'sys'"):
        guard.validate_skill(malicious_code)


def test_forbidden_import_red(guard):
    malicious_code = "import urllib.request\ndef exploit(): pass"
    # We use a broader match for the message
    with pytest.raises(SecurityError, match="Forbidden import 'urllib"):
        guard.validate_skill(malicious_code)


def test_not_in_allowlist(guard):
    # 'pickle' is not in forbidden list nor in allowlist
    malicious_code = "import pickle\ndef exploit(): pass"
    with pytest.raises(SecurityError, match="not in allowlist"):
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
    with pytest.raises(SecurityError, match="Forbidden access to dunder"):
        guard.validate_skill(malicious_code)


def test_syntax_error(guard):
    bad_code = "def incomplete("
    with pytest.raises(SecurityError, match="Syntax error"):
        guard.validate_skill(bad_code)


def test_timeout_infinite_loop(guard):
    # TP-S2: Catch infinite loop
    loop_code = "while True: pass"
    with pytest.raises(SecurityError, match="timeout"):
        guard.validate_skill(loop_code)


def test_bypass_attempt(guard):
    # Attempt to access builtins directly
    malicious_code = "__builtins__['open']('/tmp/secret')"
    with pytest.raises(SecurityError):
        guard.validate_skill(malicious_code)


# ── SE5.13-SE5.16: Diagnóstico vulnerabilidad __import__ ──────────────


def test_se5_13_execute_blocks_forbidden_import(guard):
    """execute() debe bloquear import os (full pipeline: AST + runtime)."""
    code = "import os\ndef f(): os.system('ls')"
    with pytest.raises(SecurityError, match="Forbidden import"):
        guard.execute(code)


def test_se5_14_execute_blocks_builtins_bypass(guard):
    """execute() debe bloquear acceso a builtins inseguros."""
    code = "def f():\n    b = __builtins__\n    return b['open']"
    with pytest.raises(SecurityError):
        guard.execute(code)


def test_se5_15_verify_compilation_blocks_injected_import(guard):
    """validate_skill debe bloquear codigo que pasa AST pero usa __import__ en runtime."""
    code = "def f():\n    imp = __builtins__['__import__']\n    return imp('os')"
    with pytest.raises(SecurityError):
        guard.validate_skill(code)


def test_se5_16_execute_blocks_indirect_import_bypass(guard):
    """execute() debe bloquear bypass indirecto: x = __builtins__; x['__import__']('os')."""
    code = "def f():\n    x = __builtins__\n    return x['__import__']('os')"
    with pytest.raises(SecurityError):
        guard.execute(code)
