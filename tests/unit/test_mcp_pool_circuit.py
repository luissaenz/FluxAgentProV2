"""Unit tests: MCPPool circuit breaker — Paso 1, Gap 1.

Tests U1.1-U1.5: Circuit breaker state transitions without real MCP connection.
Patrón de mock: unittest.mock.patch("time.time") para control de temporización.
MCPPool.reset() entre tests para evitar contaminación del singleton.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.tools.mcp_pool import MCPConnectionError, MCPPool


@pytest.fixture(autouse=True)
def _reset_pool():
    """Reset singleton MCPPool before each test to avoid contamination."""
    MCPPool.reset()
    yield
    MCPPool.reset()


def _make_pool_with_state(key: str, failures: float, last_check: float) -> MCPPool:
    """Helper: Create a pool with pre-configured health state."""
    pool = MCPPool.get()
    pool._health[key] = {"failures": failures, "last_check": last_check}
    return pool


# ── U1.1: Circuit breaker cerrado (4 fallos) → _is_circuit_open False ───────


def test_circuit_closed_four_failures():
    """U1.1: Circuito cerrado con 4 fallos (<5 threshold)."""
    key = "org:server_closed"
    pool = _make_pool_with_state(key, failures=4.0, last_check=100.0)

    with patch("time.time", return_value=110.0):
        assert pool._is_circuit_open(key) is False


# ── U1.2: Circuit breaker abierto (5 fallos, <60s) → _is_circuit_open True ───


def test_circuit_open_five_failures_within_window():
    """U1.2: Circuito abierto con 5 fallos en <60s."""
    key = "org:server_open"
    pool = _make_pool_with_state(key, failures=5.0, last_check=100.0)

    with patch("time.time", return_value=130.0):
        assert pool._is_circuit_open(key) is True


# ── U1.3: Circuit breaker half-open (>60s) → _is_circuit_open False ────────


def test_circuit_half_open_after_timeout():
    """U1.3: Circuito half-open tras 60s. Permite 1 intento."""
    key = "org:server_halfopen"
    pool = _make_pool_with_state(key, failures=5.0, last_check=100.0)

    with patch("time.time", return_value=161.0):
        assert pool._is_circuit_open(key) is False


# ── U1.4: get_tools con circuito abierto → MCPConnectionError inmediato ──────


@pytest.mark.asyncio
async def test_get_tools_raises_when_circuit_open():
    """U1.4: get_tools lanza MCPConnectionError inmediato con circuito abierto."""
    key = "org:server_raise"
    pool = _make_pool_with_state(key, failures=5.0, last_check=100.0)

    with patch("time.time", return_value=130.0):
        with pytest.raises(MCPConnectionError, match="Circuit breaker abierto"):
            await pool.get_tools(org_id="org", server_name="server_raise")


# ── U1.5: Reset tras éxito en half-open → _is_circuit_open False ───────


def test_reset_circuit_breaker_after_success():
    """U1.5: Reset del circuit breaker pone fallos a 0."""
    key = "org:server_reset"
    pool = _make_pool_with_state(key, failures=5.0, last_check=100.0)

    pool._reset_circuit_breaker(key)

    assert pool._health[key]["failures"] == 0.0
    with patch("time.time", return_value=130.0):
        assert pool._is_circuit_open(key) is False
