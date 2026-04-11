"""MultiCrewFlow — Phase 3 multi-agent coordination pattern.

Demonstrates: Crew A → (router) → Crew B or Crew C → finalise.

Rule R1: Flow is orchestrator — agents only execute assigned tasks.
Rule R4: State persisted after each crew via persist_state().
Rule R6: Events are blocking.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import logging
import json

from .base_flow import BaseFlow, with_error_handling
from .state import BaseFlowState, FlowStatus
from .registry import register_flow
from ..crews.base_crew import BaseCrew
from ..guardrails.base_guardrail import make_approval_check

logger = logging.getLogger(__name__)


class MultiCrewState(BaseFlowState):
    """Extended state carrying output from each crew stage."""

    flow_type: str = "multi_crew"
    crew_a_output: Optional[Dict[str, Any]] = None
    crew_b_output: Optional[Dict[str, Any]] = None
    crew_c_output: Optional[Dict[str, Any]] = None


@register_flow("multi_crew")
class MultiCrewFlow(BaseFlow):
    """Orchestrate three sequential crews with conditional routing.

    Pattern::

        Crew A (analysis) → router → Crew B (processing, may need approval)
                                   → Crew C (alternative path)
                           → finalise

    Each crew receives the accumulated state. The state is persisted
    after every crew execution so that crashes lose at most one step.
    """

    # Approval threshold guardrail (staticmethod to avoid self being passed)
    _approval_check = staticmethod(
        make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50_000,
        )
    )

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return bool(input_data)

    async def create_task_record(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Override to use MultiCrewState instead of BaseFlowState."""
        from uuid import uuid4
        from datetime import datetime, timezone
        from ..db.session import get_tenant_client
        from ..events.store import EventStore

        task_id = str(uuid4())

        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("tasks").insert(
                {
                    "id": task_id,
                    "org_id": self.org_id,
                    "flow_type": "multi_crew",
                    "flow_id": task_id,
                    "status": "pending",
                    "payload": input_data,
                    "correlation_id": correlation_id,
                    "max_retries": self.extra_kwargs.get("max_retries", 3),
                }
            ).execute()

        self.state = MultiCrewState(
            task_id=task_id,
            org_id=self.org_id,
            user_id=self.user_id,
            flow_type="multi_crew",
            input_data=input_data,
            correlation_id=correlation_id,
        )

        self.event_store = EventStore(
            self.org_id, 
            self.user_id, 
            correlation_id=self.state.correlation_id
        )
        await self.emit_event("flow.created", {"input_data": input_data})

    @with_error_handling
    async def execute(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> MultiCrewState:
        """Full multi-crew lifecycle."""
        logger.info("Starting MultiCrewFlow for org %s", self.org_id)

        if not self.validate_input(input_data):
            raise ValueError("Input validation failed")

        await self.create_task_record(input_data, correlation_id)

        self.state.start()
        await self.persist_state()

        # ── Crew A: initial analysis ─────────────────────────────
        await self._execute_crew_a()

        # If paused for approval, stop here
        if self.state.status == FlowStatus.AWAITING_APPROVAL:
            return self.state

        # ── Router: decide next crew ─────────────────────────────
        next_crew = self._decide_next_crew()

        if next_crew == "crew_b":
            await self._execute_crew_b()
            if self.state.status == FlowStatus.AWAITING_APPROVAL:
                return self.state
        else:
            await self._execute_crew_c()

        # ── Finalise ─────────────────────────────────────────────
        await self._finalise()
        return self.state

    async def _run_crew(self) -> Dict[str, Any]:
        """Not used directly — multi-crew uses individual crew methods."""
        return self.state.output_data

    # ── Individual crew steps ─────────────────────────────────────

    async def _execute_crew_a(self) -> None:
        """Run Crew A: initial analysis."""
        crew = BaseCrew(self.org_id, role="analyst")
        result = await crew.run_async(
            task_description="Perform initial analysis with available data.",
            inputs={"data": self.state.input_data},
        )
        # Track real tokens from CrewAI
        self.state.update_tokens(crew.get_last_tokens_used())

        # 1. Intentar parsear el resultado como JSON para extraer lógica de negocio
        try:
            parsed_result = json.loads(str(result))
            if isinstance(parsed_result, dict):
                self.state.crew_a_output = parsed_result
            else:
                self.state.crew_a_output = {"result": str(result)}
        except (ValueError, TypeError):
            self.state.crew_a_output = {"result": str(result)}

        await self.persist_state()
        await self.emit_event(
            "crew_a.completed",
            {
                "output": self.state.crew_a_output,
                "tokens_used": crew.get_last_tokens_used(),
            },
        )

    def _decide_next_crew(self) -> str:
        """Router: decide which crew to run next based on Crew A output.

        Business logic lives HERE, not in the agent (Rule R1).
        """
        output = self.state.crew_a_output or {}
        if output.get("requires_crew_b", False):
            return "crew_b"
        return "crew_c"

    async def _execute_crew_b(self) -> None:
        """Run Crew B: processing path (may require approval)."""
        crew = BaseCrew(self.org_id, role="processor")
        result = await crew.run_async(
            task_description="Process the output from the initial analysis.",
            inputs={"analysis": self.state.crew_a_output},
        )
        # Track real tokens from CrewAI
        self.state.update_tokens(crew.get_last_tokens_used())

        try:
            parsed_result = json.loads(str(result))
            if isinstance(parsed_result, dict):
                self.state.crew_b_output = parsed_result
            else:
                self.state.crew_b_output = {"result": str(result)}
        except (ValueError, TypeError):
            self.state.crew_b_output = {"result": str(result)}

        await self.persist_state()
        await self.emit_event(
            "crew_b.completed",
            {
                "output": self.state.crew_b_output,
                "tokens_used": crew.get_last_tokens_used(),
            },
        )

        # Guardrail: check if amount exceeds approval threshold
        amount = self.state.crew_b_output.get("monto", 0)
        if self._approval_check(amount, self.org_id):
            await self.request_approval(
                description="Amount exceeds automatic approval threshold.",
                payload=self.state.crew_b_output,
            )

    async def _execute_crew_c(self) -> None:
        """Run Crew C: alternative path."""
        crew = BaseCrew(self.org_id, role="reviewer")
        result = await crew.run_async(
            task_description="Review and summarise the analysis results.",
            inputs={"analysis": self.state.crew_a_output},
        )
        # Track real tokens from CrewAI
        self.state.update_tokens(crew.get_last_tokens_used())

        self.state.crew_c_output = {"result": str(result)}
        await self.persist_state()
        await self.emit_event(
            "crew_c.completed",
            {
                "output": self.state.crew_c_output,
                "tokens_used": crew.get_last_tokens_used(),
            },
        )

    async def _finalise(self) -> None:
        """Complete the flow with aggregated results."""
        result = {
            "crew_a": self.state.crew_a_output,
            "crew_b": self.state.crew_b_output,
            "crew_c": self.state.crew_c_output,
        }
        self.state.complete(result)
        await self.emit_event("flow.completed", {"result": result})
        await self.persist_state()

    async def _on_approved(self) -> None:
        """Post-approval hook: finalise the flow."""
        self.state.status = FlowStatus.RUNNING
        self.state.approval_payload = None
        await self.persist_state()
        await self.emit_event("flow.resumed", {"decision": "approved"})
        await self._finalise()
