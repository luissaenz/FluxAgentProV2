"""tests/unit/test_presupuesto_flow.py — Unit tests for PresupuestoFlow.validate_input().

No DB mocks needed — pure logic validation.
"""

from __future__ import annotations

from uuid import uuid4

from src.flows.presupuesto_flow import PresupuestoFlow


class TestPresupuestoFlowValidation:
    """PresupuestoFlow.validate_input() unit tests."""

    def make_flow(self) -> PresupuestoFlow:
        return PresupuestoFlow(org_id=str(uuid4()), user_id=str(uuid4()))

    def test_validate_input_rejects_empty(self) -> None:
        flow = self.make_flow()
        assert not flow.validate_input({})

    def test_validate_input_rejects_partial(self) -> None:
        flow = self.make_flow()
        assert not flow.validate_input({"tipo_evento": "boda"})
        assert not flow.validate_input({"tipo_evento": "boda", "pax": 100})
        assert not flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-03-15"})

    def test_validate_input_accepts_complete(self) -> None:
        flow = self.make_flow()
        assert flow.validate_input({
            "tipo_evento": "boda",
            "pax": 100,
            "fecha": "2026-03-15",
            "provincia": "Tucumán",
        })

    def test_validate_input_accepts_with_extra_fields(self) -> None:
        flow = self.make_flow()
        assert flow.validate_input({
            "tipo_evento": "boda",
            "pax": 100,
            "fecha": "2026-03-15",
            "provincia": "Tucumán",
            "duracion_horas": 6,
            "menu": "premium",
        })
