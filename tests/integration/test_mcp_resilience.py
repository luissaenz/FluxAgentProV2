"""Integration tests: MCP Pool circuit breaker — Paso 2, Gap 1.

Tests I2.1-I2.3: Circuit breaker integration con DB mock + MCPServerAdapter mock.
MCPPool.reset() autouse para evitar contaminación del singleton.
time.time mockeado por test individual.

IMPORTANTE: MCPServerAdapter se importa lazy dentro de get_tools() via
    from crewai_tools import MCPServerAdapter
por lo que el mock debe estar en namespace crewai_tools, no src.tools.mcp_pool.
Asimismo asegurar que crewai_tools y mcp existen en sys.modules.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.tools.mcp_pool import MCPConnectionError, MCPPool


def _ensure_mcp_modules_in_sys():
    """Garantiza que crewai_tools y mcp estén en sys.modules para que el
    from-import dentro de get_tools() no falle con ImportError."""
    for mod_name in ("crewai_tools", "mcp", "mcp.server"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = MagicMock()
    # StdioServerParameters se importa desde mcp
    sys.modules["mcp"].StdioServerParameters = MagicMock


_ensure_mcp_modules_in_sys()


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


# ── I2.1: Circuito abierto → get_tools() lanza MCPConnectionError inmediato ───


@pytest.mark.asyncio
async def test_circuit_opens_after_5_failures():
    """I2.1: 5 fallos → circuito abierto → get_tools() lanza MCPConnectionError sin intentar conexión."""
    key = "org:server_open_21"
    pool = _make_pool_with_state(key, failures=5.0, last_check=100.0)

    # time.time retorna 130 → elapsed = 30s (< 60s) → circuito abierto
    with patch("time.time", return_value=130.0):
        with pytest.raises(MCPConnectionError, match="Circuit breaker abierto"):
            await pool.get_tools(org_id="org", server_name="server_open_21")

    # Verificar que NO se intentó conexión (failures intacto)
    assert pool._health[key]["failures"] == 5.0


# ── I2.2: half-open → éxito → reset (failures==0) ─────────────────────────


@pytest.mark.asyncio
async def test_full_cycle_open_to_close(mock_service_client):
    """I2.2: Circuito abierto → 60s → half-open → éxito → reset (failures==0)."""
    key = "org:server_cycle"
    MCPPool.get()._health[key] = {"failures": 5.0, "last_check": 100.0}

    # Mock DB config response
    mock_service_client.table("org_mcp_servers").execute.return_value.data = {
        "command": "python",
        "args": ["-c", "print('ok')"],
        "name": "server_cycle",
        "org_id": "org",
        "is_active": True,
        "secret_name": None,
    }

    # Mock MCPServerAdapter para devolver tools
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_adapter = MagicMock()
    mock_adapter.tools = [mock_tool]
    mock_adapter.__enter__ = MagicMock(return_value=mock_adapter)
    mock_adapter.__exit__ = MagicMock(return_value=False)

    # Patch MCPServerAdapter en crewai_tools (namespace real del import lazy)
    with patch("crewai_tools.MCPServerAdapter", return_value=mock_adapter):
        # time.time: 100 + 61 = 161 → elapsed = 61s → half-open
        with patch("time.time", return_value=161.0):
            tools = await MCPPool.get().get_tools(
                org_id="org", server_name="server_cycle"
            )

    assert len(tools) == 1
    assert tools[0].name == "mock_tool"
    # Circuit breaker reseteado (failures==0)
    assert MCPPool.get()._health[key]["failures"] == 0.0


# ── I2.3: half-open → fallo → re-abre circuito ────────────────────────────


@pytest.mark.asyncio
async def test_half_open_failure_reopens(mock_service_client):
    """I2.3: Circuito abierto → 60s → half-open → fallo → re-abre (failures>=5)."""
    key = "org:server_reopen"
    MCPPool.get()._health[key] = {"failures": 5.0, "last_check": 100.0}

    # Mock DB config response
    mock_service_client.table("org_mcp_servers").execute.return_value.data = {
        "command": "python",
        "args": [],
        "name": "server_reopen",
        "org_id": "org",
        "is_active": True,
        "secret_name": None,
    }

    # Patch MCPServerAdapter para que falle al crear
    with patch(
        "crewai_tools.MCPServerAdapter",
        side_effect=Exception("Connection refused"),
    ):
        # time.time: 100 + 61 = 161 → elapsed = 61s → half-open
        with patch("time.time", return_value=161.0):
            with pytest.raises(MCPConnectionError, match="Error conectando"):
                await MCPPool.get().get_tools(
                    org_id="org", server_name="server_reopen"
                )

    # Circuit breaker debe seguir abierto (failures >= 5, no reseteado)
    assert MCPPool.get()._health[key]["failures"] >= 5.0
