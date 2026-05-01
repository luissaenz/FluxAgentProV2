"""Unit tests: Approval operators — Paso 1, Gap 3.

Tests U3.1-U3.4: Operadores faltantes en _check_approval_rule.
Solo operador '<' (>=, <=, == deferidos a Paso 2 — bug confirmado en dynamic_flow.py:137).
Método síncrono puro, sin mocking DB/crews.
"""

from __future__ import annotations

from src.flows.dynamic_flow import DynamicWorkflow


def _make_flow(org_id: str = "test_org_approval") -> DynamicWorkflow:
    """Create a DynamicWorkflow instance for testing approval rules."""
    return DynamicWorkflow(org_id=org_id)


def _make_results(value: str) -> dict:
    """Helper: wrap a value in the format expected by _check_approval_rule."""
    return {"step_1": {"result": value}}


# ── U3.1: '<' operador — condición verdadera ───────────────────


def test_approval_less_than_true():
    """U3.1: '<' evalúa True cuando valor < threshold."""
    flow = _make_flow()
    rule = {"condition": "monto < 1000", "description": "Monto bajo"}
    results = _make_results("500")

    assert flow._check_approval_rule(rule, results) is True


# ── U3.2: '<' operador — condición falsa ───────────────────────


def test_approval_less_than_false():
    """U3.2: '<' evalúa False cuando valor > threshold."""
    flow = _make_flow()
    rule = {"condition": "monto < 1000", "description": "Monto alto"}
    results = _make_results("1500")

    assert flow._check_approval_rule(rule, results) is False


# ── U3.3: Condición vacía → False sin excepción ────────────────


def test_approval_empty_condition_returns_false():
    """U3.3: Condición vacía → False sin lanzar excepción."""
    flow = _make_flow()
    rule = {"condition": "", "description": "Sin condición"}
    results = _make_results("500")

    assert flow._check_approval_rule(rule, results) is False


# ── U3.4: Múltiples resultados, uno cumple → True ──────────────


def test_approval_multiple_results_one_matches():
    """U3.4: Múltiples resultados, uno cumple '<' → True."""
    flow = _make_flow()
    rule = {"condition": "score < 1000", "description": "Score bajo detectado"}
    results = {
        "step_1": {"result": "2000"},
        "step_2": {"result": "500"},
        "step_3": {"result": "1500"},
    }

    assert flow._check_approval_rule(rule, results) is True
