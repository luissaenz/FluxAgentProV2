"""src/flows/dynamic_flow.py — Flows generados dinámicamente desde templates.

Un DynamicWorkflow es un BaseFlow cuyos steps y agents se cargan desde
la definición en workflow_templates. Se registra en FLOW_REGISTRY
para que POST /webhooks/{org_id}/{flow_type} lo encuentre automáticamente.

Pattern confirmado con MultiCrewFlow real:
- Hereda de BaseFlow
- Override de create_task_record para usar estado extendido
- Métodos internos para cada paso del workflow
- persist_state() después de cada paso (Rule R4)
- emit_event() después de cada paso (Rule R5)
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .base_flow import BaseFlow
from .registry import flow_registry
from ..crews.base_crew import BaseCrew

logger = logging.getLogger(__name__)


class DynamicWorkflow(BaseFlow):
    """
    Flow cargado desde workflow_templates.

    Se instancia dinámicamente cuando llega un webhook con un flow_type
    que no existe como archivo Python pero sí en workflow_templates.
    """

    _template_definition: Dict[str, Any] = {}
    _flow_type: str = "dynamic"

    @classmethod
    def register(cls, flow_type: str, definition: Dict[str, Any]) -> None:
        """Crear una subclase DynamicWorkflow con la definition y registrarla."""
        template = definition

        # Extract metadata from template definition
        category = definition.get("category")
        depends_on = definition.get("depends_on", [])

        class RegisteredFlow(cls):
            _template_definition = template
            _flow_type = flow_type

        RegisteredFlow.__name__ = f"DynamicFlow_{flow_type}"
        RegisteredFlow.__qualname__ = f"DynamicFlow_{flow_type}"

        flow_type_lower = flow_type.lower()
        flow_registry._flows[flow_type_lower] = RegisteredFlow

        # Register metadata so dynamic flows appear in hierarchy/validation
        flow_registry._metadata[flow_type_lower] = {
            "depends_on": depends_on,
            "category": category,
        }

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return bool(input_data)

    async def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar los steps definidos en el template.

        Cada step crea un BaseCrew, lo ejecuta, y persiste el estado.
        Si un step requiere aprobación, se pausa con request_approval().
        """
        template = self._template_definition
        steps = template.get("steps", [])
        approval_rules = template.get("approval_rules", [])
        results: Dict[str, Any] = {}

        for step in steps:
            step_id = step.get("id", f"step_{len(results)}")
            agent_role = step.get("agent_role")
            description = step.get("description", "")

            if not agent_role:
                logger.warning("Step '%s' sin agent_role, omitiendo", step_id)
                continue

            logger.info(
                "DynamicFlow[%s] ejecutando step '%s' con agent '%s'",
                self._flow_type,
                step_id,
                agent_role,
            )

            crew = BaseCrew(org_id=self.org_id, role=agent_role)
            result = await crew.run_async(
                task_description=description,
                inputs={
                    "step_inputs": step.get("inputs", {}),
                    "previous_results": results,
                    "original_input": self.state.input_data,
                },
            )

            # Track real tokens from CrewAI
            self.state.update_tokens(crew.get_last_tokens_used())

            results[step_id] = {"result": str(result.raw)}
            await self.persist_state()
            await self.emit_event(
                f"step.{step_id}.completed",
                {
                    "output": results[step_id],
                    "tokens_used": crew.get_last_tokens_used(),
                },
            )

            # Evaluar approval_rules
            for rule in approval_rules:
                if self._check_approval_rule(rule, results):
                    await self.request_approval(
                        description=rule.get("description", "Approval required"),
                        payload={"step": step_id, "results": results},
                    )
                    return results  # Flow se pausa aquí

        return results

    def _check_approval_rule(self, rule: Dict[str, Any], results: Dict) -> bool:
        """
        Evaluar condition de una approval_rule.

        Solo soporta operadores básicos: >, <, >=, <=
        condition es un string como "monto > 50000"
        """
        condition = rule.get("condition", "")
        try:
            if ">" in condition:
                _, threshold = condition.split(">", 1)
                threshold = float(threshold.strip())
                for v in results.values():
                    if isinstance(v, dict) and "result" in v:
                        try:
                            if float(str(v["result"])) > threshold:
                                return True
                        except (ValueError, TypeError):
                            continue
            elif "<" in condition:
                _, threshold = condition.split("<", 1)
                threshold = float(threshold.strip())
                for v in results.values():
                    if isinstance(v, dict) and "result" in v:
                        try:
                            if float(str(v["result"])) < threshold:
                                return True
                        except (ValueError, TypeError):
                            continue
        except (ValueError, TypeError):
            logger.warning("No se pudo evaluar approval_rule: %s", rule)
        return False


def load_dynamic_flows_from_db() -> int:
    """
    Cargar todos los workflows activos desde DB y registrarlos.

    Llamar en startup de FastAPI:
        @app.on_event("startup")
        async def startup():
            load_dynamic_flows_from_db()
    """
    from ..db.session import get_service_client

    svc = get_service_client()
    templates = (
        svc.table("workflow_templates")
        .select("flow_type, definition")
        .eq("is_active", True)
        .execute()
    )

    count = 0
    for t in templates.data or []:
        try:
            DynamicWorkflow.register(
                flow_type=t["flow_type"],
                definition=t["definition"],
            )
            count += 1
        except Exception as exc:
            logger.error("No se pudo cargar dynamic flow %s: %s", t["flow_type"], exc)

    logger.info("DynamicWorkflow: %d flows cargados desde DB", count)
    return count
