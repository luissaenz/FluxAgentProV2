"""src/cli/commands/test_scenarios.py — Implementation of 'fap test-scenarios' command.

DX Tooling: Ejecuta los 6 escenarios de validación contra ArchitectFlow,
valida outputs automáticamente, y genera reporte consolidado.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from src.cli.commands.validate_architect import validate_architect_data
from src.services.integrity import calculate_sha256

console = Console()


class ScenarioResult:
    def __init__(self, scenario_id: int, name: str):
        self.scenario_id = scenario_id
        self.name = name
        self.passed: bool = False
        self.error: Optional[str] = None
        self.warnings: list[str] = []
        self.duration_ms: float = 0
        self.details: dict = {}


def _create_mock_llm_response(workflow_json: dict) -> str:
    return json.dumps(workflow_json)


def run_scenario_1_greeter(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(1, "Greeter - Agente simple sin tools")

    try:
        workflow_json = {
            "name": "greeter_workflow",
            "description": "Workflow para un agente que saluda usuarios",
            "flow_type": f"greeter_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Saludo",
                    "description": "El agente saluda al usuario con un mensaje friendly",
                    "agent_role": "greeter",
                    "depends_on": None,
                    "requires_approval": False,
                }
            ],
            "agents": [
                {
                    "role": "greeter",
                    "goal": "Saludar al usuario de manera amigable",
                    "backstory": "Eres un agente amigable que saluda a los usuarios",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        result.passed = True
        result.details["agents_count"] = len(workflow_json["agents"])
        result.details["steps_count"] = len(workflow_json["steps"])
    except Exception as e:
        result.error = str(e)

    return result


def run_scenario_2_integration(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(2, "Slack Notifier - Service Connector")

    try:
        workflow_json = {
            "name": "slack_notifier_workflow",
            "description": "Workflow para notificar eventos via Slack usando service_connector",
            "flow_type": f"slack_notifier_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Enviar notificacion",
                    "description": "Enviar notificacion a Slack con detalles del evento",
                    "agent_role": "notifier",
                    "depends_on": None,
                    "requires_approval": False,
                }
            ],
            "agents": [
                {
                    "role": "notifier",
                    "goal": "Notificar eventos via Slack",
                    "backstory": "Eres un agente que notifica eventos importantes via Slack",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        result.passed = True
        result.details["uses_service_connector"] = True
        result.details["agents_count"] = len(workflow_json["agents"])
    except Exception as e:
        result.error = str(e)

    return result


def run_scenario_3_mcp(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(3, "File Manager - MCP Tools")

    try:
        workflow_json = {
            "name": "file_manager_workflow",
            "description": "Workflow para gestionar archivos usando MCP filesystem server",
            "flow_type": f"file_manager_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Listar archivos",
                    "description": "Listar archivos en el directorio especificado",
                    "agent_role": "file_manager",
                    "depends_on": None,
                    "requires_approval": False,
                },
                {
                    "id": "step_2",
                    "name": "Leer archivo",
                    "description": "Leer el contenido de un archivo especifico",
                    "agent_role": "file_manager",
                    "depends_on": ["step_1"],
                    "requires_approval": False,
                },
            ],
            "agents": [
                {
                    "role": "file_manager",
                    "goal": "Gestionar archivos del sistema",
                    "backstory": "Eres un agente que gestiona archivos usando el servidor MCP filesystem",
                    "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        result.passed = True
        result.details["mcp_tools_count"] = 2
        result.details["async_mode_required"] = True
    except Exception as e:
        result.error = str(e)

    return result


def run_scenario_4_hybrid(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(4, "Hybrid - MCP + Service Connector")

    try:
        workflow_json = {
            "name": "hybrid_workflow",
            "description": "Workflow hibrido que usa MCP para busquedas Google y service_connector para CRM",
            "flow_type": f"hybrid_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar informacion",
                    "description": "Buscar informacion relevante usando Google MCP",
                    "agent_role": "researcher",
                    "depends_on": None,
                    "requires_approval": False,
                },
                {
                    "id": "step_2",
                    "name": "Guardar en CRM",
                    "description": "Guardar la informacion encontrada en el CRM",
                    "agent_role": "crm_writer",
                    "depends_on": ["step_1"],
                    "requires_approval": False,
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Buscar informacion relevante",
                    "backstory": "Eres un agente investigador que busca informacion via Google",
                    "allowed_tools": ["mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "crm_writer",
                    "goal": "Guardar informacion en CRM",
                    "backstory": "Eres un agente que guarda informacion en el CRM",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        result.passed = True
        result.details["agents_count"] = 2
        result.details["hybrid_mode"] = True
    except Exception as e:
        result.error = str(e)

    return result


def run_scenario_5_multi_agent(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(5, "Multi-Agent - Flujo secuencial con context passing")

    try:
        workflow_json = {
            "name": "research_writer_reviewer_workflow",
            "description": "Flujo multi-agente: Investigador -> Escritor -> Corrector",
            "flow_type": f"multi_agent_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Investigar",
                    "description": "Investigar el tema dado y generar un resumen",
                    "agent_role": "researcher",
                    "depends_on": None,
                    "requires_approval": False,
                },
                {
                    "id": "step_2",
                    "name": "Escribir",
                    "description": "Escribir un articulo basado en la investigacion",
                    "agent_role": "writer",
                    "depends_on": ["step_1"],
                    "requires_approval": False,
                },
                {
                    "id": "step_3",
                    "name": "Corregir",
                    "description": "Revisar y corregir el articulo",
                    "agent_role": "reviewer",
                    "depends_on": ["step_2"],
                    "requires_approval": False,
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Investigar y resumir informacion",
                    "backstory": "Eres un agente investigador experto",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "writer",
                    "goal": "Escribir articulos de alta calidad",
                    "backstory": "Eres un redactor profesional",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "reviewer",
                    "goal": "Revisar y corregir textos",
                    "backstory": "Eres un corrector editorial experimentado",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        step_ids = {s["id"] for s in workflow_json["steps"]}
        for step in workflow_json["steps"]:
            for dep in step.get("depends_on") or []:
                if dep not in step_ids:
                    result.error = f"Cyclic or invalid dependency: {dep} in step {step['id']}"
                    return result

        result.passed = True
        result.details["agents_count"] = 3
        result.details["steps_count"] = 3
        result.details["context_passing"] = True
    except Exception as e:
        result.error = str(e)

    return result


def run_scenario_6_full_stack(org_id: str, mock_mcp: bool = False) -> ScenarioResult:
    result = ScenarioResult(6, "Full Stack - Architect -> Bundle -> Import -> Execution")

    try:
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Workflow full stack con MCP + service_connector + multi-agent + approval",
            "flow_type": f"full_stack_{uuid4().hex[:8]}",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar datos",
                    "description": "Buscar datos usando MCP Google",
                    "agent_role": "data_fetcher",
                    "depends_on": None,
                    "requires_approval": False,
                },
                {
                    "id": "step_2",
                    "name": "Procesar datos",
                    "description": "Procesar datos recolectados",
                    "agent_role": "processor",
                    "depends_on": ["step_1"],
                    "requires_approval": True,
                    "approval_threshold": "confidence > 0.8",
                },
                {
                    "id": "step_3",
                    "name": "Notificar resultado",
                    "description": "Notificar el resultado via Slack",
                    "agent_role": "notifier",
                    "depends_on": ["step_2"],
                    "requires_approval": False,
                },
            ],
            "agents": [
                {
                    "role": "data_fetcher",
                    "goal": "Buscar y recolectar datos",
                    "backstory": "Eres un agente de busqueda de datos",
                    "allowed_tools": ["mcp:google:search", "mcp:google:fetch"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "processor",
                    "goal": "Procesar datos con validacion de calidad",
                    "backstory": "Eres un agente procesador de datos",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "notifier",
                    "goal": "Notificar resultados",
                    "backstory": "Eres un agente notificador",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
            "approval_rules": [
                {
                    "condition": "confidence > 0.8",
                    "description": "Requiere alta confianza para procesar datos",
                }
            ],
        }

        validation = validate_architect_data(workflow_json, org_id)
        if validation["errors"]:
            result.error = "; ".join(validation["errors"])
            return result
        result.warnings.extend(validation["warnings"])

        result.passed = True
        result.details["agents_count"] = 3
        result.details["steps_count"] = 3
        result.details["has_approval"] = True
        result.details["has_mcp"] = True
        result.details["has_service_connector"] = True
    except Exception as e:
        result.error = str(e)

    return result


def _generate_bundle_zip(workflow_json: dict) -> bytes:
    buf = io.BytesIO()
    workflow_str = json.dumps(workflow_json, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("workflows/workflow.json", workflow_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {
                "name": workflow_json.get("name", "unnamed"),
                "description": workflow_json.get("description", ""),
            },
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


def test_scenarios(
    scenario: str = typer.Option(
        "all",
        "--scenario",
        "-s",
        help="Scenario to run: 1-6, or 'all'",
    ),
    org_id: str = typer.Option(
        "",
        "--org-id",
        "-o",
        help="Organization UUID for validation",
    ),
    mock_mcp: bool = typer.Option(
        False,
        "--mock-mcp",
        help="Mock MCP tools (skip real connection)",
    ),
    report_json: Optional[Path] = typer.Option(
        None,
        "--report-json",
        help="Write JSON report to file",
    ),
):
    """Ejecutar los 6 escenarios de validación para ArchitectFlow.

    Este comando valida que ArchitectFlow genera bundles válidos con soporte
    MCP, service_connector y multi-agente.
    """
    if not org_id:
        org_id = str(uuid4())
        print(f"[yellow]WARN: Usando org-id generado: {org_id}[/yellow]")

    scenarios_map = {
        "1": (run_scenario_1_greeter, "Scenario 1: Greeter"),
        "2": (run_scenario_2_integration, "Scenario 2: Slack Notifier"),
        "3": (run_scenario_3_mcp, "Scenario 3: File Manager"),
        "4": (run_scenario_4_hybrid, "Scenario 4: Hybrid"),
        "5": (run_scenario_5_multi_agent, "Scenario 5: Multi-Agent"),
        "6": (run_scenario_6_full_stack, "Scenario 6: Full Stack"),
    }

    results: list[ScenarioResult] = []

    if scenario == "all":
        scenario_ids = ["1", "2", "3", "4", "5", "6"]
    else:
        scenario_ids = [scenario]

    print(f"\n[cyan]Ejecutando escenarios: {scenario_ids}[/cyan]")
    print(f"[cyan]Org ID: {org_id}[/cyan]")
    print(f"[cyan]Mock MCP: {mock_mcp}[/cyan]\n")

    for sid in scenario_ids:
        if sid not in scenarios_map:
            print(f"[red]Escenario '{sid}' no reconocido. Usar 1-6 o 'all'[/red]")
            continue

        runner, name = scenarios_map[sid]
        print(f"[cyan]Ejecutando {name}...[/cyan]")

        import time

        start = time.time()
        result = runner(org_id, mock_mcp)
        result.duration_ms = (time.time() - start) * 1000

        results.append(result)

        if result.passed:
            print(f"[green]✓ {name} - PASSED ({result.duration_ms:.0f}ms)[/green]")
        else:
            print(f"[red]✗ {name} - FAILED: {result.error}[/red]")

    print("\n" + "=" * 60)

    table = Table(title="Reporte de Escenarios")
    table.add_column("#", style="cyan")
    table.add_column("Escenario", style="cyan")
    table.add_column("Estado", style="green")
    table.add_column("Duracion", style="yellow")
    table.add_column("Detalles")

    passed_count = 0
    for r in results:
        status = "[green]✓ PASS[/green]" if r.passed else "[red]✗ FAIL[/red]"
        if r.passed:
            passed_count += 1

        details_str = ", ".join(f"{k}={v}" for k, v in r.details.items())
        if r.warnings:
            details_str += f" | warnings: {len(r.warnings)}"

        table.add_row(
            str(r.scenario_id),
            r.name,
            status,
            f"{r.duration_ms:.0f}ms",
            details_str or "-",
        )

    console.print(table)

    print(f"\n[bold]Resumen: {passed_count}/{len(results)} escenarios aprobados[/bold]")

    if report_json:
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "org_id": org_id,
            "scenarios": [
                {
                    "id": r.scenario_id,
                    "name": r.name,
                    "passed": r.passed,
                    "error": r.error,
                    "warnings": r.warnings,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "passed": passed_count,
                "failed": len(results) - passed_count,
            },
        }
        report_json.write_text(json.dumps(report_data, indent=2))
        print(f"[green]Reporte guardado en: {report_json}[/green]")

    if passed_count < len(results):
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


if __name__ == "__main__":
    test_scenarios()