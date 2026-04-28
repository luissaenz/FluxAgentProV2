"""src/services/security_guard.py — Security scanner for bundle skill code.

Combines AST scanning (pre-check) with RestrictedPython (runtime protection).
"""

from __future__ import annotations

import ast
import concurrent.futures
import logging

from RestrictedPython import compile_restricted, safe_builtins

logger = logging.getLogger(__name__)


# Forbidden modules in AST scanner (Plan §98-101 + Analysis Final)
FORBIDDEN_MODULES = {
    # System
    "os", "subprocess", "shutil", "socket", "mmap", "ctypes", "sys",
    # Dynamic
    "importlib",
    # Introspección
    "inspect", "gc",
    # Red (Análisis Final §26)
    "urllib", "http", "ftplib", "requests", "httpx", "aiohttp", "urllib3"
}

# Allowed modules (Análisis Final §67)
# Any module NOT in this list AND not in standard safe list will be blocked.
# SUPUESTO: Standard library modules like 'math', 'json', 're' are allowed.
ALLOWED_MODULES = {
    "crewai", "pydantic", "json", "re", "datetime", "math", "random",
    "typing", "abc", "uuid", "logging", "time", "collections",
    "functools", "itertools", "pydantic_core", "annotated_types"
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

    def validate_skill(
        self,
        source_code: str,
        filename: str = "skill.py"
    ) -> bool:
        """Validate source code using AST analysis and dry-run compilation.

        Raises SecurityError if code is deemed unsafe.
        """
        # 1. AST Static Scan
        self._scan_ast(source_code, filename)

        # 2. RestrictedPython Compilation (with timeout)
        self._verify_compilation(source_code, filename)

        return True

    def _scan_ast(self, source_code: str, filename: str):
        """Perform static analysis on source code to find patterns."""
        try:
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                # Check imports (import X)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_module = alias.name.split('.')[0]
                        self._check_module(root_module, alias.name, filename)

                # Check from imports (from X import Y)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        root_module = node.module.split('.')[0]
                        self._check_module(root_module, node.module, filename)

                # Check forbidden function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in FORBIDDEN_CALLS:
                            raise SecurityError(
                                f"Forbidden function call '{node.func.id}' "
                                f"in {filename}"
                            )
                    elif isinstance(node.func, ast.Attribute):
                        # Block access to __subclasses__ and similar dunder
                        if node.func.attr.startswith("__"):
                            raise SecurityError(
                                f"Forbidden access to dunder attribute "
                                f"'{node.func.attr}' in {filename}"
                            )

        except SyntaxError as e:
            raise SecurityError(f"Syntax error in {filename}: {str(e)}") from e

    def _check_module(self, root_module: str, full_module: str, filename: str):
        """Verify if a module is forbidden or not in the allowlist."""
        # 1. Check blacklist (Explicitly forbidden)
        if root_module in FORBIDDEN_MODULES:
            raise SecurityError(
                f"Forbidden import '{full_module}' in {filename}"
            )

        # 2. Check allowlist
        # Note: per OC Analysis D2: "only allowlist... blacklist not enough".
        if root_module not in ALLOWED_MODULES and root_module != "":
            raise SecurityError(
                f"Module '{root_module}' not in allowlist for {filename}"
            )

    def _verify_compilation(self, source_code: str, filename: str):
        """Try to compile and dry-run the code with timeout."""
        def _execute_restricted():
            byte_code = compile_restricted(
                source_code,
                filename=filename,
                mode="exec"
            )
            if byte_code is None:
                raise SecurityError(
                    f"RestrictedPython compilation failed for {filename}"
                )

            # Dry-run execution to catch infinite loops
            # Use safe_builtins + controlled __import__
            safe_env = safe_builtins.copy()
            safe_env["__import__"] = __import__
            exec_globals = {"__builtins__": safe_env}

            exec(byte_code, exec_globals)
            return True

        # Use executor without 'with' to avoid hanging on join
        exe = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = exe.submit(_execute_restricted)
            future.result(timeout=self.timeout_seconds)

        except concurrent.futures.TimeoutError as e:
            exe.shutdown(wait=False, cancel_futures=True)
            raise SecurityError(
                f"Security validation timeout after "
                f"{self.timeout_seconds}s for {filename}"
            ) from e
        except Exception as e:
            exe.shutdown(wait=False)
            if isinstance(e, SecurityError):
                raise
            logger.warning(
                "RestrictedPython validation error for %s: %s",
                filename, str(e)
            )
            raise SecurityError(
                f"Security validation failed during restricted "
                f"execution: {str(e)}"
            ) from e
        finally:
            # Note: The worker thread will continue running until process exit
            # if it's an infinite loop, but we don't block the main flow.
            exe.shutdown(wait=False)
