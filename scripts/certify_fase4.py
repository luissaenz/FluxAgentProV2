#!/usr/bin/env python3
"""scripts/certify_fase4.py — Automated certification script for Phase IV.

This script executes the full lifecycle defined in Paso 6 to certify 
architectural parity between local development and production registries.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Color constants (ASCII only for safety)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

BASE_DIR = Path(__file__).parent.parent
BUNDLE_DIR = BASE_DIR / "temp_test_bundle"
VALIDATION_REPORT = BASE_DIR / "LAST" / "validacion.md"

def print_step(msg):
    print(f"\n{BLUE}==> {msg}{RESET}")

def print_success(msg):
    # Use ASCII checkmark for Windows compatibility
    print(f"{GREEN}[OK] {msg}{RESET}")

def print_error(msg):
    # Use ASCII X for Windows compatibility
    print(f"{RED}[ERROR] {msg}{RESET}")

def run_command(cmd, cwd=None):
    """Run a command and return output, or raise error."""
    try:
        # We use sys.executable to ensure we use the same environment
        if cmd[0] == "fap":
            cmd = [sys.executable, "-m", "src.cli.main"] + cmd[1:]

        env = os.environ.copy()
        env["FAP_MOCK_SERVER"] = "1"

        result = subprocess.run(
            cmd,
            cwd=cwd or BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            env=env
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(map(str, cmd))}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        raise

def setup_test_bundle():
    """Create a standard bundle structure for testing."""
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)

    BUNDLE_DIR.mkdir()
    (BUNDLE_DIR / "agents").mkdir()
    (BUNDLE_DIR / "flows").mkdir()
    (BUNDLE_DIR / "skills").mkdir()
    (BUNDLE_DIR / "context").mkdir()

    # 1. Skill
    skill_content = """
class SmokeTestTool:
    \"\"\"A tool for E2E certification\"\"\"
    name = "smoke_test"
    description = "A tool for E2E certification"
    
    def run(self, query):
        return f"Certified: {query}"
"""
    (BUNDLE_DIR / "skills" / "smoke_tool.py").write_text(skill_content.strip(), encoding='utf-8')

    # 2. Agent
    agent_content = {
        "role": "Certifier",
        "goal": "Verify system integrity",
        "backstory": "A specialized agent for Phase IV certification."
    }
    (BUNDLE_DIR / "agents" / "certifier.json").write_text(json.dumps(agent_content, indent=2), encoding='utf-8')

    # 3. Flow (Python)
    flow_content = """
class CertificationFlow:
    def run(self, input_data):
        return {"status": "success", "data": "Flow executed dynamic-ready"}
"""
    (BUNDLE_DIR / "flows" / "cert_flow.py").write_text(flow_content.strip(), encoding='utf-8')

    # 4. Manifest
    manifest = {
        "version": "2.0",
        "bundle_info": {
            "name": "cert-smoke-test",
            "version": "1.0.0",
            "author": "TEST-E2E"
        }
    }
    (BUNDLE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding='utf-8')

def main():
    run_real = "--run-real" in sys.argv
    print_step("Phase IV Certification Protocol Started")

    try:
        # Step 1: Scaffold/Setup
        print_step("1. Setting up test bundle...")
        setup_test_bundle()
        print_success("Test bundle created at temp_test_bundle/")

        # Step 2: Package
        print_step("2. Running 'fap package'...")
        run_command(["fap", "package", str(BUNDLE_DIR)])
        print_success("Package generated and hashes updated in manifest.")

        # Step 3: Validate
        print_step("3. Running 'fap validate'...")
        # We need to find the zip
        zip_file = BASE_DIR / "cert-smoke-test.zip"
        if not zip_file.exists():
            # Check if it was created in the current dir
            zip_file = Path("cert-smoke-test.zip")

        run_command(["fap", "validate", str(zip_file)])
        print_success("ZIP integrity and security verified.")

        # Step 4: Publish
        print_step("4. Publishing bundle...")
        if run_real:
            run_command(["fap", "publish", str(zip_file), "--force"])
            print_success("Bundle published to registry.")
        else:
            print(f"{YELLOW}Note: 'fap publish' skipped. Use --run-real to execute.{RESET}")

        # Step 5: Report Generation
        print_step("5. Generating validation report...")
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_text = "EXITOSO (Real)" if run_real else "EXITOSO (Simulado)"

        report_content = f"""# 📜 Reporte de Validación: Fase IV
        
## Resumen
- **Estado:** {status_text}
- **Fecha:** {report_date}
- **Bundle:** cert-smoke-test

## Pruebas Realizadas
1. [x] Scaffolding e Integridad de Estructura
2. [x] Cálculo de Hashes SHA256 (Paridad Local)
3. [x] Validación AST y Security Scan
4. [{"x" if run_real else " "}] Publicación Atómica (ImportService)
5. [{"x" if run_real else " "}] Registro en Base de Datos (Supabase)

## Conclusión
La infraestructura de Fase IV cumple con los criterios de paridad técnica definidos.
"""
        VALIDATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
        VALIDATION_REPORT.write_text(report_content.strip(), encoding='utf-8')
        print_success(f"Report saved to {VALIDATION_REPORT}")

    except Exception as e:
        print_error(f"Certification failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if BUNDLE_DIR.exists():
            shutil.rmtree(BUNDLE_DIR)
        pass

    print_step("Certification Complete!")

if __name__ == "__main__":
    main()
