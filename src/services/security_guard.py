"""src/services/security_guard.py — Security scanner for bundle skill code.

Combines AST scanning (pre-check) with RestrictedPython (runtime protection).
"""

from __future__ import annotations

import ast
import logging
from typing import List, Set

from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Guards import safe_globals

logger = logging.getLogger(__name__)

# Forbidden modules in AST scanner (Plan §98-101)
FORBIDDEN_MODULES = {
    # System
    "os", "subprocess", "shutil", "socket", "mmap", "ctypes",
    # Dynamic
    "importlib",
    # Introspección
    "inspect", "gc",
}

# Forbidden functions/calls
FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "open", "__import__"
}


class SecurityError(Exception):
    """Raised when code fails security validation."""
    pass


class SecurityGuard:
    """Provides static and dynamic security analysis for Python code."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def validate_skill(self, source_code: str, filename: str = "skill.py") -> bool:
        """Validate source code using AST analysis and dry-run compilation.
        
        Raises SecurityError if code is deemed unsafe.
        """
        # 1. AST Static Scan
        self._scan_ast(source_code, filename)
        
        # 2. RestrictedPython Compilation
        self._verify_compilation(source_code, filename)
        
        return True

    def _scan_ast(self, source_code: str, filename: str):
        """Perform static analysis on the source code to find forbidden patterns."""
        try:
            tree = ast.parse(source_code)
            
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in FORBIDDEN_MODULES:
                            raise SecurityError(f"Forbidden import '{alias.name}' in {filename}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in FORBIDDEN_MODULES:
                        raise SecurityError(f"Forbidden import from '{node.module}' in {filename}")
                
                # Check forbidden function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in FORBIDDEN_CALLS:
                            raise SecurityError(f"Forbidden function call '{node.func.id}' in {filename}")
                    elif isinstance(node.func, ast.Attribute):
                        # Block access to __subclasses__ and similar dunder attributes
                        if node.func.attr.startswith("__"):
                            raise SecurityError(f"Forbidden access to dunder attribute '{node.func.attr}' in {filename}")

        except SyntaxError as e:
            raise SecurityError(f"Syntax error in {filename}: {str(e)}")

    def _verify_compilation(self, source_code: str, filename: str):
        """Try to compile the code with RestrictedPython to catch runtime-only escapes."""
        try:
            # We don't execute it here, just check if it compiles under RestrictedPython rules
            byte_code = compile_restricted(
                source_code,
                filename=filename,
                mode="exec"
            )
            if byte_code is None:
                raise SecurityError(f"RestrictedPython compilation failed for {filename}")
                
        except Exception as e:
            logger.warning("RestrictedPython compilation error for %s: %s", filename, str(e))
            raise SecurityError(f"Security validation failed during restricted compilation: {str(e)}")
