"""MCPPool — Persistent connection pool for MCP servers (Phase 3).

Characteristics:
- Persistent connections for the process lifetime (not closed between calls)
- Auto-reconnect if the connection is lost
- Circuit breaker: after 5 consecutive failures, rests for 60 s
- Retry with exponential backoff (tenacity)

Usage::

    pool = MCPPool.get()
    tools = await pool.get_tools(org_id="org_123", server_name="mi_server")
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional

from tenacity import retry, wait_exponential, stop_after_attempt

from ..db.session import get_service_client
from ..db.vault import get_secret_async

logger = logging.getLogger("mcp_pool")


class MCPConnectionError(Exception):
    """Raised when an MCP connection cannot be established."""


class MCPPool:
    """Singleton pool of persistent MCP server connections.

    Keeps one adapter per (org_id, server_name) pair alive for the process
    lifetime. Auto-reconnects on failure with circuit-breaker protection.
    """

    _instance: Optional["MCPPool"] = None

    def __init__(self) -> None:
        # NOTE: _adapters is an *instance* variable — not shared between instances
        self._adapters: Dict[str, object] = {}
        self._health: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"failures": 0.0, "last_check": 0.0}
        )

    @classmethod
    def get(cls) -> "MCPPool":
        """Return the singleton pool instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Circuit breaker ───────────────────────────────────────────

    def _is_circuit_open(self, key: str) -> bool:
        """Return True if the circuit breaker is open (too many recent failures)."""
        health = self._health[key]
        if health["failures"] < 5:
            return False
        elapsed = time.time() - health["last_check"]
        return elapsed < 60  # half-open after 60 s

    def _record_failure(self, key: str) -> None:
        self._health[key]["failures"] += 1
        self._health[key]["last_check"] = time.time()

    def _reset_circuit_breaker(self, key: str) -> None:
        self._health[key]["failures"] = 0.0

    # ── Public API ────────────────────────────────────────────────

    async def get_tools(
        self,
        org_id: str,
        server_name: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> list:
        """Get tools from a named MCP server with retry and circuit breaker.

        Args:
            org_id: Organisation UUID.
            server_name: Name of the server in ``org_mcp_servers``.
            timeout: Max seconds to wait for a connection.
            max_retries: Maximum reconnection attempts.

        Returns:
            List of tool objects from the MCP adapter.

        Raises:
            MCPConnectionError: if the circuit breaker is open or retries are
                exhausted.
        """
        key = f"{org_id}:{server_name}"

        if self._is_circuit_open(key):
            remaining = int(60 - (time.time() - self._health[key]["last_check"]))
            raise MCPConnectionError(
                f"Circuit breaker abierto para '{server_name}'. "
                f"Reintento en ~{remaining}s"
            )

        @retry(
            wait=wait_exponential(multiplier=1, min=2, max=10),
            stop=stop_after_attempt(max_retries),
            reraise=True,
        )
        async def _connect() -> list:
            # Try the cached adapter first
            if key in self._adapters:
                try:
                    return self._adapters[key].tools  # type: ignore[attr-defined]
                except Exception:
                    logger.warning("MCP adapter degradado para %s, reconectando…", key)
                    await self._safe_close(key)

            # Load server config from DB
            svc = get_service_client()
            config = (
                svc.table("org_mcp_servers")
                .select("*")
                .eq("org_id", org_id)
                .eq("name", server_name)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )

            if not config.data:
                raise MCPConnectionError(
                    f"Servidor MCP '{server_name}' no configurado para org '{org_id}'"
                )

            # Resolve optional secret
            env: Dict[str, str] = {}
            if config.data.get("secret_name"):
                env["API_TOKEN"] = await get_secret_async(
                    org_id, config.data["secret_name"]
                )

            # Build connection — MCPServerAdapter is a *sync* context manager;
            # run __enter__ in a thread pool to avoid blocking the event loop.
            try:
                from crewai_tools import MCPServerAdapter
                from mcp import StdioServerParameters
            except ImportError:
                raise MCPConnectionError(
                    "crewai-tools and mcp packages required for MCP support"
                )

            params = StdioServerParameters(
                command=config.data["command"],
                args=config.data.get("args", []),
                env=env or None,
            )

            adapter = MCPServerAdapter(params)

            def _sync_enter():
                adapter.__enter__()
                return adapter

            loop = asyncio.get_running_loop()
            connected_adapter = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_enter),
                timeout=timeout,
            )

            self._adapters[key] = connected_adapter
            self._reset_circuit_breaker(key)
            return connected_adapter.tools  # type: ignore[attr-defined]

        try:
            return await _connect()
        except asyncio.TimeoutError:
            self._record_failure(key)
            raise MCPConnectionError(
                f"Timeout conectando a MCP '{server_name}' ({timeout}s)"
            )
        except MCPConnectionError:
            raise
        except Exception as exc:
            self._record_failure(key)
            logger.error("Error en MCP pool para %s: %s", key, exc)
            raise MCPConnectionError(f"Error conectando a MCP '{server_name}': {exc}")

    async def _safe_close(self, key: str) -> None:
        """Close an adapter safely, suppressing errors."""
        if key in self._adapters:
            try:
                self._adapters[key].__exit__(None, None, None)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning("Error cerrando adapter %s: %s", key, exc)
            finally:
                del self._adapters[key]

    async def close(self) -> None:
        """Close all connections in the pool and reset the singleton."""
        keys = list(self._adapters.keys())
        for key in keys:
            await self._safe_close(key)
        MCPPool._instance = None

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful in tests)."""
        cls._instance = None
