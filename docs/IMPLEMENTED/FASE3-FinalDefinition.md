# Fase 3 — Multi-Agent y Memoria Semántica

> **Definición cerrada.** Este documento consolida el plan original de Fase 3 y todas las correcciones encontradas durante el análisis de inconsistencias. Es el documento de especificaciones oficial para desarrollo.

---

## Visión del sistema

Una plataforma multi-tenant que permite a organizaciones definir workflows automatizados ejecutados por múltiples agentes de IA especializados coordinados por un Flow maestro. Los agentes tienen acceso a memoria semántica de largo plazo (búsqueda por similitud en pgvector). Las conexiones a herramientas externas vía MCP son persistentes con circuit breaker y reconexión automática.

**Regla central: el Flow es el orquestador.** Los agentes son ejecutores efímeros. El estado canónico siempre vive en la base de datos, nunca solo en memoria.

---

## Criterio de éxito

Un Flow que coordina **3 Crews secuenciales** pasa sus tests de integración.

---

## 01 — Stack tecnológico

### Dependencias

```toml
[tool.poetry.dependencies]
python = ">=3.12"

# Orquestación
crewai = "^0.100.0"
crewai-tools = "^0.20.0"

# API
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.10.0"
pydantic-settings = "^2.6.0"

# Base de datos
supabase = "^2.10.0"
psycopg2-binary = "^2.9.0"
pgvector = "^0.3.0"          # ⭐ AGREGADO: soporte para embeddings vectoriales

# LLM
anthropic = "^0.40.0"
openai = "^1.58.0"           # embeddings text-embedding-3-small

# Utilidades
python-dotenv = "^1.0.0"
httpx = "^0.28.0"
structlog = "^24.4.0"
tenacity = "^9.0.0"          # ⭐ AGREGADO: retry con backoff exponencial

# MCP
mcp = ">=1.0.0"              # ⭐ AGREGADO: protocolo MCP

[tool.poetry.dev-dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-mock = "^3.14.0"
pytest-cov = "^6.0.0"
httpx = "^0.28.0"
```

### Variables de entorno requeridas

```bash
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY
ANTHROPIC_API_KEY
OPENAI_API_KEY           # para embeddings
```

---

## 02 — Estructura del proyecto

```
project/
├── src/
│   ├── flows/
│   │   ├── base_flow.py              # BaseFlow (lifecycle-based, async)
│   │   ├── generic_flow.py           # Flow de ejemplo (existente)
│   │   ├── multi_crew_flow.py        # ⭐ NUEVO: 3 Crews secuenciales
│   │   └── registry.py
│   │
│   ├── crews/
│   │   ├── base_crew.py              # ⭐ NUEVO: factory dinámica desde DB
│   │   └── generic_crew.py           # existente
│   │
│   ├── tools/
│   │   ├── base_tool.py
│   │   ├── builtin.py
│   │   ├── registry.py
│   │   └── mcp_pool.py               # ⭐ NUEVO: pool persistente MCP
│   │
│   ├── state/
│   │   └── base_state.py             # ⭐ NUEVO: shim de re-export
│   │
│   ├── db/
│   │   ├── session.py                # existente: get_service_client, get_tenant_client
│   │   ├── client.py                 # ⭐ NUEVO: shim de re-export para compatibilidad
│   │   ├── vault.py                  # ⭐ NUEVO: proxy de secretos
│   │   └── memory.py                 # ⭐ NUEVO: memoria vectorial
│   │
│   ├── events/
│   │   └── store.py                  # existente: EventStore
│   │
│   ├── guardrails/
│   │   └── base_guardrail.py
│   │
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── webhooks.py
│   │       ├── tasks.py
│   │       ├── approvals.py
│   │       └── health.py
│   │
│   └── config.py                     # existente: Settings
│
├── sql/
│   ├── 01_organizations.sql
│   ├── 02_agent_catalog.sql
│   ├── 03_tasks.sql
│   ├── 04_domain_events.sql
│   ├── 05_snapshots.sql
│   ├── 06_pending_approvals.sql
│   ├── 07_memory_vectors.sql
│   ├── 08_secrets.sql
│   ├── 09_rls_policies.sql
│   └── 10_org_mcp_servers.sql        # ⭐ NUEVO
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   └── test_memory.py            # ⭐ NUEVO
    └── integration/
        └── test_multi_crew_flow.py   # ⭐ NUEVO
```

---

## 03 — Base de datos

> **Nota:** Ejecutar en orden numérico. Todas las tablas tienen RLS habilitado. `org_mcp_servers` es la única tabla nueva respecto a Fase 2.

### sql/10_org_mcp_servers.sql

```sql
-- Configuración de servidores MCP por organización.
-- Un MCP server puede ser compartido por múltiples agentes de una org.

CREATE TABLE org_mcp_servers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  command     TEXT NOT NULL,          -- ej: "node", "python", "npx"
  args        JSONB DEFAULT '[]',     -- argumentos del comando
  secret_name TEXT,                   -- nombre del secreto en tabla secrets (opcional)
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, name)
);

ALTER TABLE org_mcp_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON org_mcp_servers
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
```

### sql/07_memory_vectors.sql — Corrección del operador

> **Corrección:** el operador de distancia coseno de pgvector es `<->`, no `<=>`. Además se agrega columna `embedding_version` para migración futura.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_vectors (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id             UUID NOT NULL,
  agent_role         TEXT,                     -- null = memoria compartida
  source_type        TEXT NOT NULL,            -- "conversation" | "document" | "task_result"
  content            TEXT NOT NULL,
  embedding          vector(1536),             -- text-embedding-3-small
  embedding_version  TEXT DEFAULT 'text-embedding-3-small',  -- ⭐ NUEVO: trackear versión
  metadata           JSONB,
  valid_to           TIMESTAMPTZ DEFAULT 'infinity',  -- para expiración
  created_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memory_embedding
  ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX idx_memory_version
  ON memory_vectors(org_id, embedding_version);  -- ⭐ NUEVO: índice para migración

-- Búsqueda semántica con operador CORRECTO (<->)
CREATE OR REPLACE FUNCTION search_memories(
  query_embedding  vector(1536),
  p_org_id         UUID,
  p_agent_role     TEXT DEFAULT NULL,
  match_limit      INT DEFAULT 5,
  min_similarity   FLOAT DEFAULT 0.7
) RETURNS TABLE(id UUID, content TEXT, similarity FLOAT) AS $$
  SELECT
    id,
    content,
    1 - (embedding <-> query_embedding) AS similarity
  FROM memory_vectors
  WHERE org_id = p_org_id
    AND (p_agent_role IS NULL OR agent_role = p_agent_role)
    AND valid_to > now()
    AND 1 - (embedding <-> query_embedding) >= min_similarity
  ORDER BY embedding <-> query_embedding   -- menor distancia = más similar primero
  LIMIT match_limit;
$$ LANGUAGE sql;

ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON memory_vectors
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
```

---

## 04 — Archivos nuevos

### 04.1 — src/state/base_state.py (shim de compatibilidad)

```python
"""src/state/base_state.py — Compatibility shim.

El estado vive en src/flows/state.py (BaseFlowState, FlowStatus).
Este archivo existe solo para resolver el import path documentado
en los ejemplos de Fase 3.
"""

from src.flows.state import BaseFlowState, FlowStatus

__all__ = ["BaseFlowState", "FlowStatus"]
```

### 04.2 — src/db/client.py (shim de compatibilidad)

```python
"""src/db/client.py — Compatibility shim.

El cliente real vive en src/db/session.py.
Este archivo re-exporta todo lo que la documentación de Fase 3 espera
de src.db.client.
"""

from src.db.session import (
    get_service_client,
    get_tenant_client,
    get_anon_client,
    TenantClient,
)

__all__ = ["get_service_client", "get_tenant_client", "get_anon_client", "TenantClient"]
```

### 04.3 — src/db/vault.py

```python
"""src/db/vault.py — Proxy de secretos.

Los agentes NUNCA ven credenciales en claro. Las tools obtienen
el secreto internamente y solo retornan el resultado de la operación.
"""

from __future__ import annotations

from src.db.session import get_service_client


def get_secret(org_id: str, secret_name: str) -> str:
    """
    Obtener un secreto cifrado para una organización.

    IMPORTANTE:
    - Usa service_role (bypasea RLS — la tabla secrets solo permite service_role SELECT)
    - Retorna el valor en claro. La tool que llama esto es responsable de no loguearlo.
    - Lanza ValueError si el secreto no existe.
    """
    svc = get_service_client()
    result = (
        svc.table("secrets")
        .select("secret_value")
        .eq("org_id", org_id)
        .eq("name", secret_name)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise ValueError(
            f"Secreto '{secret_name}' no configurado para org '{org_id}'"
        )
    return result.data["secret_value"]


async def get_secret_async(org_id: str, secret_name: str) -> str:
    """
    Versión async de get_secret para usar dentro de contextos async (MCPPool).
    Ejecuta el I/O bloqueante en un thread pool.
    """
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_secret, org_id, secret_name)
```

### 04.4 — src/db/memory.py

```python
"""src/db/memory.py — Memoria semántica de largo plazo.

Provee:
- embed(): genera embedding con text-embedding-3-small (1536 dims)
- save_memory(): persiste un fragmento de memoria con su embedding
- search_memory(): busca por similitud semántica
- cleanup_expired_memory(): elimina memorias con valid_to expirado
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MemoryRecord(BaseModel):
    """Respuesta de save_memory()."""

    id: str
    org_id: str
    agent_role: Optional[str]
    content: str
    similarity: Optional[float] = None


# ── Lazy OpenAI client ────────────────────────────────────────────

_client: Optional["OpenAI"] = None


def _get_openai_client() -> "OpenAI":
    """Inicialización lazy para evitar fallo si OPENAI_API_KEY no está seteada."""
    global _client
    if _client is None:
        from openai import OpenAI
        from src.config import get_settings

        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed(text: str) -> list[float]:
    """
    Generar embedding con text-embedding-3-small.

    Usa inicialización lazy: no falla al importar el módulo.
    """
    client = _get_openai_client()
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


async def embed_async(text: str) -> list[float]:
    """Versión async (usa thread pool para no bloquear event loop)."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embed, text)


def save_memory(
    org_id: str,
    content: str,
    source_type: str,
    agent_role: Optional[str] = None,
    metadata: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
) -> MemoryRecord:
    """
    Guardar un fragmento de memoria con su embedding.

    Args:
        org_id: UUID de la organización.
        content: Texto a recordar.
        source_type: "conversation" | "document" | "task_result".
        agent_role: Si se especifica, la memoria es privada de ese rol.
        metadata: Datos adicionales a almacenar.
        ttl_hours: Si se especifica, la memoria expira en N horas.
                   Si es None, nunca expira (default).

    Returns:
        MemoryRecord con el ID generado.

    Raises:
        ValueError: si org_id o content están vacíos.
        MemoryError: si la inserción falla.
    """
    if not org_id or not content:
        raise ValueError("org_id and content son requeridos")

    embedding = embed(content)

    from src.db.session import get_service_client

    svc = get_service_client()

    memory_id = str(uuid.uuid4())
    valid_to: Optional[str] = None
    if ttl_hours is not None:
        valid_to = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

    result = svc.table("memory_vectors").insert({
        "id": memory_id,
        "org_id": org_id,
        "agent_role": agent_role,
        "source_type": source_type,
        "content": content,
        "embedding": embedding,
        "embedding_version": "text-embedding-3-small",
        "metadata": metadata or {},
        "valid_to": valid_to or "infinity",
    }).execute()

    if not result.data:
        raise MemoryError(f"No se pudo persistir memoria para org {org_id}")

    return MemoryRecord(
        id=memory_id,
        org_id=org_id,
        agent_role=agent_role,
        content=content,
    )


async def save_memory_async(
    org_id: str,
    content: str,
    source_type: str,
    agent_role: Optional[str] = None,
    metadata: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
) -> MemoryRecord:
    """Versión async de save_memory."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: save_memory(org_id, content, source_type, agent_role, metadata, ttl_hours),
    )


def search_memory(
    org_id: str,
    query: str,
    agent_role: Optional[str] = None,
    limit: int = 5,
    min_similarity: float = 0.7,
) -> list[MemoryRecord]:
    """
    Buscar fragmentos de memoria por similitud semántica.

    Returns:
        Lista de MemoryRecord ordenados por relevancia (mayor similitud primero).
        Lista vacía si no hay resultados (no lanza error).

    Note:
        Si agent_role es None, se busca en la memoria compartida de la org.
        Python None se excluye del RPC call para que el SQL default NULL aplique.
    """
    embedding = embed(query)

    from src.db.session import get_service_client

    svc = get_service_client()

    # NOTE: no pasar p_agent_role si es None (evita que se serialice como "null" string)
    rpc_params = {
        "query_embedding": embedding,
        "p_org_id": org_id,
        "match_limit": limit,
        "min_similarity": min_similarity,
    }
    if agent_role is not None:
        rpc_params["p_agent_role"] = agent_role

    result = svc.rpc("search_memories", rpc_params).execute()

    return [
        MemoryRecord(
            id=row["id"],
            org_id=org_id,
            agent_role=agent_role,
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in (result.data or [])
    ]


def cleanup_expired_memory(org_id: str) -> int:
    """
    Eliminar todas las memorias expiradas de una organización.

    Returns:
        Número de memorias eliminadas.
    """
    from src.db.session import get_service_client

    svc = get_service_client()
    result = (
        svc.table("memory_vectors")
        .delete()
        .lt("valid_to", "now()")
        .eq("org_id", org_id)
        .execute()
    )

    deleted = len(result.data or [])
    logger.info("memory_cleanup", org_id=org_id, deleted=deleted)
    return deleted


class MemoryError(Exception):
    """Error al persistir o buscar memorias."""
    pass
```

### 04.5 — src/crews/base_crew.py

```python
"""src/crews/base_crew.py — Factory dinámica de Crews.

Carga la definición del agente desde agent_catalog (soul_json) y
construye un CrewAI Agent + Task + Crew listos para ejecutar.

Usage:
    crew = BaseCrew(org_id="org_123", role="agente_a")
    result = crew.run(task_description="...", inputs={"data": ...})

    # o asíncrono:
    result = await crew.run_async(task_description="...", inputs={"data": ...})
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from crewai import Agent, Crew, Process, Task

from src.db.session import get_tenant_client
from src.config import get_settings


class BaseCrew:
    """
    Crew genérico que carga configuración desde agent_catalog.

    El agente se crea a partir de soul_json almacenado en la DB,
    no de código hardcodeado.
    """

    def __init__(self, org_id: str, role: str) -> None:
        self.org_id = org_id
        self.role = role
        self._agent: Optional[Agent] = None
        self._crew: Optional[Crew] = None

    def _load_agent_config(self) -> Dict[str, Any]:
        """Cargar configuración del agente desde agent_catalog."""
        with get_tenant_client(self.org_id) as db:
            result = (
                db.table("agent_catalog")
                .select("*")
                .eq("org_id", self.org_id)
                .eq("role", self.role)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )

        if not result.data:
            raise ValueError(
                f"Agent role '{self.role}' no encontrado para org '{self.org_id}'"
            )
        return result.data

    def _build_agent(self, agent_data: Dict[str, Any]) -> Agent:
        """Construir CrewAI Agent desde los datos cargados de DB."""
        soul = agent_data.get("soul_json", {})
        settings = get_settings()

        return Agent(
            role=agent_data["role"],
            goal=soul.get("goal", ""),
            backstory=soul.get("backstory", ""),
            verbose=True,
            allow_delegation=False,  # R2: nunca delegar
            llm=settings.get_llm(),
            max_iter=agent_data.get("max_iter", 5),  # R8: max_iter explícito
        )

    def run(
        self,
        task_description: str,
        inputs: Dict[str, Any],
        expected_output: str = "Tarea completada exitosamente",
    ) -> Any:
        """Ejecución síncrona (bloqueante)."""
        if self._crew is None:
            agent_data = self._load_agent_config()
            agent = self._build_agent(agent_data)

            task = Task(
                description=task_description,
                expected_output=expected_output,
                agent=agent,
            )

            self._crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
            )

        return self._crew.kickoff(inputs=inputs)

    async def run_async(
        self,
        task_description: str,
        inputs: Dict[str, Any],
        expected_output: str = "Tarea completada exitosamente",
    ) -> Any:
        """Ejecución asíncrona (para usar dentro de Flows async)."""
        if self._crew is None:
            agent_data = self._load_agent_config()
            agent = self._build_agent(agent_data)

            task = Task(
                description=task_description,
                expected_output=expected_output,
                agent=agent,
            )

            self._crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True,
            )

        return await self._crew.kickoff_async(inputs=inputs)

    # Alias para consistencia con la documentación de Fase 3
    async def kickoff_async(self, inputs: Dict[str, Any]) -> Any:
        """Alias de run_async para compatibilidad con la documentación."""
        return await self.run_async(
            task_description="Ejecutar tarea asignada",
            inputs=inputs,
        )
```

### 04.6 — src/tools/mcp_pool.py

```python
"""src/tools/mcp_pool.py — Pool persistente de conexiones MCP.

Características:
- Conexiones persistentes durante la vida del proceso (no se cierran entre llamadas)
- Reconexión automática si la conexión se pierde
- Circuit breaker: después de 5 fallos consecutivos, descansa 60s
- Retry con backoff exponencial (tenacity)
- Soporta tanto context managers síncronos como async

Usage:
    pool = MCPPool.get()
    tools = await pool.get_tools(org_id="org_123", server_name="mi_server")
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional

from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from tenacity import retry, wait_exponential, stop_after_attempt

from src.db.session import get_service_client
from src.db.vault import get_secret_async

logger = logging.getLogger("mcp_pool")


class MCPConnectionError(Exception):
    """Error al conectar con un servidor MCP."""
    pass


class MCPPool:
    """
    Pool singleton de conexiones a servidores MCP.

    Mantiene conexiones abiertas durante la vida del proceso.
    Cada adapter vive en self._adapters[key] hasta que falle,
    momento en el cual se reconecta automáticamente.
    """

    _instance: Optional["MCPPool"] = None

    def __init__(self) -> None:
        # NOTE: _adapters es de instancia, no de clase (fix del bug original)
        self._adapters: Dict[str, MCPServerAdapter] = {}
        self._health: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"failures": 0, "last_check": 0.0}
        )

    @classmethod
    def get(cls) -> "MCPPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _is_circuit_open(self, key: str) -> bool:
        """Circuit breaker: abre después de 5 fallos, reintenta en 60s."""
        health = self._health[key]
        if health["failures"] < 5:
            return False
        elapsed = time.time() - health["last_check"]
        return elapsed < 60  # half-open después de 60s

    def _record_failure(self, key: str) -> None:
        self._health[key]["failures"] += 1
        self._health[key]["last_check"] = time.time()

    def _reset_circuit_breaker(self, key: str) -> None:
        self._health[key]["failures"] = 0

    async def get_tools(
        self,
        org_id: str,
        server_name: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> list:
        """
        Obtener herramientas de un servidor MCP con retry y circuit breaker.

        Args:
            org_id: UUID de la organización.
            server_name: Nombre del servidor en org_mcp_servers.
            timeout: Segundos máximo para conectar.
            max_retries: Intentos máximos de reconexión.

        Returns:
            Lista de tools del servidor MCP.

        Raises:
            MCPConnectionError: si el circuit breaker está abierto o se agotan los retries.
        """
        key = f"{org_id}:{server_name}"

        # ── Circuit breaker check ────────────────────────────────
        if self._is_circuit_open(key):
            raise MCPConnectionError(
                f"Circuit breaker abierto para '{server_name}'. "
                f"Reintento en ~{60 - int(time.time() - self._health[key]['last_check'])}s"
            )

        # ── Retry loop ───────────────────────────────────────────
        @retry(
            wait=wait_exponential(multiplier=1, min=2, max=10),
            stop=stop_after_attempt(max_retries),
            reraise=True,
        )
        async def _connect() -> list:
            # ¿Adapter existente y saludable?
            if key in self._adapters:
                try:
                    _ = self._adapters[key].tools  # test access
                    return self._adapters[key].tools
                except Exception:
                    logger.warning("MCP adapter degradado para %s, reconectando...", key)
                    await self._safe_close(key)

            # ── Obtener config del servidor ─────────────────────
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

            # ── Construir adapter con secreto ───────────────────
            env: Dict[str, str] = {}
            if config.data.get("secret_name"):
                env["API_TOKEN"] = await get_secret_async(
                    org_id, config.data["secret_name"]
                )

            params = StdioServerParameters(
                command=config.data["command"],
                args=config.data.get("args", []),
                env=env or None,
            )

            # NOTE: MCPServerAdapter es un context manager síncrono.
            # Se ejecuta en thread pool para no bloquear el event loop.
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
            return connected_adapter.tools

        # ── Ejecutar con manejo de errores ──────────────────────
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
        """Cerrar adapter de forma segura."""
        if key in self._adapters:
            try:
                self._adapters[key].__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Error cerrando adapter %s: %s", key, exc)
            finally:
                del self._adapters[key]

    async def close(self) -> None:
        """Cerrar todas las conexiones del pool."""
        keys = list(self._adapters.keys())
        for key in keys:
            await self._safe_close(key)
        MCPPool._instance = None
```

### 04.7 — src/flows/multi_crew_flow.py

```python
"""src/flows/multi_crew_flow.py — Flow de 3 Crews secuenciales.

Este archivo demuestra el patrón de coordinación multi-crew.

ARQUITECTURA:
- MultiCrewFlow hereda de BaseFlow (lifecycle-based: execute() → validate → run_crew → complete)
- El BaseFlow._run_crew() delega a un Flow CrewAI interno que orquesta los 3 Crews
- Esto evita la mezcla de dos paradigmas incompatibles (@start/@listen con lifecycle)

NOTA sobre decorators CrewAI:
  from crewai.flow import Flow, listen, start, router   # CORRECTO
  from crewai.flow.flow import Flow, ...                   # INCORRECTO

El Flow interne NUNCA se instancia directamente — se crea dentro de _run_crew()
para que el ciclo de vida completo sea gestionado por BaseFlow (persist, events, error handling).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Literal, Optional

from crewai.flow import Flow, listen, start, router

from .base_flow import BaseFlow
from .registry import register_flow
from ..state.base_state import BaseFlowState, FlowStatus

logger = logging.getLogger(__name__)


# ── Inner Flow (CrewAI native) ────────────────────────────────────

class _MultiCrewInnerFlow(Flow):
    """
    Flow interno de CrewAI — orquesta los 3 Crews.

    NO se expone directamente. Solo existe como implementación de
    BaseFlow._run_crew(). El padre (BaseFlow) gestiona persistencia,
    eventos y error handling.
    """

    def __init__(self, state: BaseFlowState):
        # El Flow interno recibe el estado serializable para pasar datos
        # entre pasos. No她的有自己的 task_id/org_id (los tiene el padre).
        super().__init__()
        self._state = state

    @start()
    def iniciar(self):
        """Primer paso: análisis inicial con Crew A."""
        from ..crews.base_crew import BaseCrew

        logger.info("MultiCrew: iniciando Crew A")
        crew = BaseCrew(org_id=self._state.org_id, role="agente_a")
        result = crew.run(
            task_description="Realizar análisis inicial con los datos disponibles.",
            inputs={"data": self._state.input_data},
        )
        return {"crew_a_output": result.raw if hasattr(result, "raw") else str(result)}

    @listen(iniciar)
    def ejecutar_crew_b(self, datos: Dict[str, Any]):
        """Segundo paso: procesar output del análisis."""
        from ..crews.base_crew import BaseCrew

        logger.info("MultiCrew: iniciando Crew B")
        crew = BaseCrew(org_id=self._state.org_id, role="agente_b")
        result = crew.run(
            task_description="Procesar el output del análisis inicial.",
            inputs={"analisis": datos.get("crew_a_output", {})},
        )
        crew_b_raw = result.raw if hasattr(result, "raw") else str(result)
        return {
            **datos,
            "crew_b_output": crew_b_raw,
        }

    @router(ejecutar_crew_b)
    def decidir_crew_c(self, datos: Dict[str, Any]) -> Literal["ejecutar_crew_c", "finalizar"]:
        """
        Router: decide si ejecutar Crew C según el resultado de Crew B.

        IMPORTANTE: el string retornado debe coincidir exactamente con el
        nombre del método decorado con @listen.

        Args:
            datos: estado acumulado de los pasos anteriores.

        Returns:
            "ejecutar_crew_c" → ejecuta paso final.
            "finalizar" → omite Crew C y completa directamente.
        """
        crew_b = datos.get("crew_b_output", {})

        # Ejemplo: si Crew B marca requires_crew_c, se ejecuta el paso C
        if crew_b.get("requires_crew_c", False):
            return "ejecutar_crew_c"
        return "finalizar"

    @listen("ejecutar_crew_c")
    def ejecutar_crew_c(self, datos: Dict[str, Any]):
        """Tercer paso: procesamiento final."""
        from ..crews.base_crew import BaseCrew

        logger.info("MultiCrew: iniciando Crew C")
        crew = BaseCrew(org_id=self._state.org_id, role="agente_c")
        result = crew.run(
            task_description="Realizar el procesamiento final y generar resultado.",
            inputs={"datos": datos},
        )
        return {
            **datos,
            "crew_c_output": result.raw if hasattr(result, "raw") else str(result),
        }

    @listen("finalizar")
    def finalizar(self, datos: Dict[str, Any]):
        """Completa el flow sin ejecutar Crew C."""
        return datos


# ── Public Flow (BaseFlow lifecycle) ──────────────────────────────

class MultiCrewState(BaseFlowState):
    """Estado específico del flow multi-crew."""

    flow_type: str = "multi_crew"
    crew_a_output: Optional[Dict[str, Any]] = None
    crew_b_output: Optional[Dict[str, Any]] = None
    crew_c_output: Optional[Dict[str, Any]] = None


@register_flow("multi_crew")
class MultiCrewFlow(BaseFlow):
    """
    Flow que orquesta 3 Crews secuenciales.

    Patron: Crew A → Crew B → (decisión) → Crew C o Finalizar

    El BaseFlow gestiona el ciclo de vida completo:
    validate_input → create_task_record → start → _run_crew → complete

    El Flow interno de CrewAI (_MultiCrewInnerFlow) solo orchest los Crews.
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True  # TODO: validación específica

    async def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar los 3 Crews vía el Flow interno de CrewAI.

        BaseFlow se encarga de: crear_task_record, start, persist_state,
        emit_event (antes y después), y error handling.
        """
        inner = _MultiCrewInnerFlow(state=self.state)

        logger.info(
            "MultiCrewFlow[%s] iniciando orchestración interna",
            self.state.task_id,
        )

        result = await inner.kickup_async()  # запускает внутренний flow

        # El resultado es el estado acumulado del inner flow
        # Se guarda en output_data del estado principal
        return {"inner_result": result}

    async def _on_approved(self) -> None:
        """
        Hook post-aprobación (override de BaseFlow).

        Después de que el supervisor aprueba, se ejecutan los pasos
        post-aprobación. Por defecto solo Marca como RUNNING y persiste.
        """
        self.state.status = FlowStatus.RUNNING
        self.state.approval_payload = None
        await self.persist_state()
        await self.emit_event("flow.resumed", {"decision": "approved"})
```

**Patrón de aprobación con rollback** (para Flows que lo requieran):

```python
class MultiCrewFlowWithApproval(MultiCrewFlow):
    """Variante de MultiCrewFlow que incluye paso de aprobación."""

    async def _run_crew(self) -> Dict[str, Any]:
        inner = _MultiCrewInnerFlow(state=self.state)
        result = await inner.kickup_async()

        crew_b = result.get("crew_b_output", {})

        # Si el monto supera el umbral, solicitar aprobación antes de continuar
        if crew_b.get("monto", 0) > 50_000:
            await self.request_approval(
                description=f"El monto {crew_b['monto']} supera el umbral de aprobación.",
                payload=crew_b,
            )
            # request_approval() pausó el flow — no se llega aquí

        return {"inner_result": result}

    async def _on_rejected(self, decided_by: str) -> None:
        """
        Hook post-rechazo: rollback de los cambios propuestos.

        En lugar de fallar el flow, se registra el rechazo y se permite
        retry con parámetros ajustados.
        """
        self.state.crew_b_output = None
        self.state.status = FlowStatus.FAILED
        self.state.error = f"Rechazado por supervisor: {decided_by}"
        await self.persist_state()
        await self.emit_event("flow.rejected", {"decided_by": decided_by})
```

---

## 05 — Tests

### 05.1 — tests/unit/test_memory.py

```python
"""tests/unit/test_memory.py"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.db.memory import (
    embed,
    save_memory,
    search_memory,
    cleanup_expired_memory,
    MemoryRecord,
)


class TestEmbed:
    """embed() genera vectores de 1536 dimensiones con inicialización lazy."""

    @patch("src.db.memory._get_openai_client")
    def test_embed_returns_1536_dimensions(self, mock_get_client):
        mock_oai = MagicMock()
        mock_oai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )
        mock_get_client.return_value = mock_oai

        result = embed("test text")

        assert len(result) == 1536
        mock_oai.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="test text"
        )

    @patch("src.db.memory._get_openai_client")
    def test_embed_lazy_init(self, mock_get_client):
        """El cliente OpenAI no se crea hasta la primera llamada."""
        from src.db import memory as mem_module

        mem_module._client = None  # reset

        embed("test")

        mock_get_client.assert_called_once()


class TestSaveMemory:
    """save_memory() persiste en Supabase y retorna MemoryRecord."""

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_returns_memory_record(self, mock_embed, mock_get_client):
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-123", "org_id": "org-123", "content": "test"}]
        )
        mock_get_client.return_value = mock_svc

        record = save_memory(
            org_id="org-123",
            content="test content",
            source_type="conversation",
            agent_role="sales",
            metadata={"task_id": "abc"},
        )

        assert isinstance(record, MemoryRecord)
        assert record.id == "mem-123"
        assert record.content == "test content"

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_with_ttl(self, mock_embed, mock_get_client):
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-123", "org_id": "org-123", "content": "tmp"}]
        )
        mock_get_client.return_value = mock_svc

        save_memory(
            org_id="org-123",
            content="datos temporales",
            source_type="conversation",
            ttl_hours=24,
        )

        call_args = mock_svc.table.return_value.insert.return_value.execute.call_args
        insert_data = call_args[0][0]
        assert insert_data["valid_to"] != "infinity"

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_raises_on_empty_fields(self, mock_embed, mock_get_client):
        with pytest.raises(ValueError, match="org_id and content son requeridos"):
            save_memory(org_id="", content="test", source_type="doc")

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_raises_on_insert_failure(self, mock_embed, mock_get_client):
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_client.return_value = mock_svc

        from src.db.memory import MemoryError

        with pytest.raises(MemoryError):
            save_memory(org_id="org-123", content="test", source_type="doc")


class TestSearchMemory:
    """search_memory() retorna lista de MemoryRecord."""

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_returns_records(self, mock_embed, mock_get_client):
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "r1", "content": "result1", "similarity": 0.92},
                {"id": "r2", "content": "result2", "similarity": 0.85},
            ]
        )
        mock_get_client.return_value = mock_svc

        results = search_memory(
            org_id="org-123",
            query="test query",
            agent_role="sales",
            limit=5,
        )

        assert len(results) == 2
        assert results[0].similarity == 0.92
        assert results[1].content == "result2"

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_empty_result(self, mock_embed, mock_get_client):
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        results = search_memory(org_id="org-123", query="no results")

        assert results == []

    @patch("src.db.memory.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_excludes_none_agent_role(self, mock_embed, mock_get_client):
        """p_agent_role no debe enviarse si es None (evita serialización como 'null')."""
        mock_embed.return_value = [0.1] * 1536
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        search_memory(org_id="org-123", query="q", agent_role=None)

        call_args = mock_svc.rpc.call_args
        # p_agent_role no debe estar en los parámetros
        assert "p_agent_role" not in call_args[1]


class TestCleanup:
    """cleanup_expired_memory() elimina y retorna el conteo."""

    @patch("src.db.memory.get_service_client")
    def test_cleanup_returns_deleted_count(self, mock_get_client):
        mock_svc = MagicMock()
        mock_svc.table.return_value.delete.return_value.lt.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[{"id": "1"}, {"id": "2"}])
        )
        mock_get_client.return_value = mock_svc

        deleted = cleanup_expired_memory("org-123")

        assert deleted == 2
```

### 05.2 — tests/integration/test_multi_crew_flow.py

```python
"""tests/integration/test_multi_crew_flow.py

Tests de integración del MultiCrewFlow.
Usa mocks de BaseCrew para evitar llamadas reales a LLM.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.multi_crew_flow import MultiCrewFlow, MultiCrewState


@pytest.fixture
def org_id():
    return str(uuid4())


@pytest.fixture
def task_id():
    return str(uuid4())


@pytest.fixture
def mock_base_crew():
    """Factory de mocks para BaseCrew.kickoff_async()."""
    with patch("src.flows.multi_crew_flow._MultiCrewInnerFlow") as mock:
        yield mock


class TestMultiCrewFlow:
    """Flow coordina 3 Crews secuenciales."""

    @pytest.mark.asyncio
    async def test_flow_execute_returns_inner_result(self, org_id, task_id):
        """BaseFlow.execute() retorna el resultado del inner flow."""
        flow = MultiCrewFlow(org_id=org_id)
        flow.state = MultiCrewState(
            task_id=task_id,
            org_id=org_id,
            flow_type="multi_crew",
            status="pending",
            input_data={"test": "data"},
        )

        with patch.object(flow, "persist_state", new_callable=AsyncMock):
            with patch.object(flow, "emit_event", new_callable=AsyncMock):
                with patch(
                    "src.flows.multi_crew_flow._MultiCrewInnerFlow"
                ) as MockInner:
                    mock_inner_instance = MagicMock()
                    mock_inner_instance.kickup_async = AsyncMock(
                        return_value={
                            "crew_a_output": {"result": "A"},
                            "crew_b_output": {"result": "B"},
                            "crew_c_output": {"result": "C"},
                        }
                    )
                    MockInner.return_value = mock_inner_instance

                    result = await flow._run_crew()

        assert "inner_result" in result
        assert result["inner_result"]["crew_a_output"]["result"] == "A"

    @pytest.mark.asyncio
    async def test_flow_validates_input(self, org_id):
        """validate_input() retorna True por defecto."""
        flow = MultiCrewFlow(org_id=org_id)
        assert flow.validate_input({"anything": "works"}) is True


class TestMultiCrewState:
    """MultiCrewState acepta campos crew_*."""

    def test_default_fields(self):
        state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=str(uuid4()),
            flow_type="multi_crew",
        )

        assert state.crew_a_output is None
        assert state.crew_b_output is None
        assert state.crew_c_output is None
        assert state.flow_type == "multi_crew"

    def test_extra_fields_allowed(self):
        """BaseFlowState usa extra='allow'."""
        state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=str(uuid4()),
            flow_type="multi_crew",
            custom_field="allowed",
        )
        assert state.custom_field == "allowed"
```

---

## 06 — Entregables verificables

| # | Entregable | Criterio |
|---|------------|----------|
| 1 | `src/db/memory.py` | `save_memory()` persiste y retorna `MemoryRecord`. `search_memory()` retorna `[]` si no hay resultados. Embedding lazy, no falla al importar. |
| 2 | `src/db/vault.py` | `get_secret()` lanza `ValueError` si no existe. `get_secret_async()` existe para contexto async. |
| 3 | `src/crews/base_crew.py` | `BaseCrew(org_id, role)` carga desde `agent_catalog`. `run_async()` usa `kickoff_async()`. `allow_delegation=False` y `max_iter` explícito. |
| 4 | `src/tools/mcp_pool.py` | Singleton. Circuit breaker tras 5 fallos. Retry con tenacity. `__aenter__` ejecutado en thread pool. |
| 5 | `sql/10_org_mcp_servers.sql` | Tabla existe con RLS. |
| 6 | `sql/07_memory_vectors.sql` | Operador `<->` corregido. Columna `embedding_version` agregada. |
| 7 | `src/flows/multi_crew_flow.py` | 3 Crews secuenciales. Inner Flow delegando desde `_run_crew()`. |
| 8 | `tests/unit/test_memory.py` | Todos los tests pasando. |
| 9 | `tests/integration/test_multi_crew_flow.py` | Tests de coordinación pasando. |
| 10 | Shims de compatibilidad | `src/state/base_state.py` y `src/db/client.py` re-exportan correctamente. |

---

## 07 — Reglas de implementación

| # | Regla | Aplicación en Fase 3 |
|---|-------|----------------------|
| R1 | El Flow es el orquestador. Agentes no deciden el flujo. | Inner Flow recibe estado del padre; router vive en el Flow, no en el agente. |
| R2 | `allow_delegation=False` siempre. | `BaseCrew._build_agent()` hardcodea `False`. |
| R3 | Los secretos nunca llegan al LLM. | `MCPPool` obtiene secreto internamente, solo pasa `tools` al agente. |
| R4 | Estado canónico en Supabase. | `persist_state()` llamado después de cada paso. |
| R5 | Eventos inmutables. | `emit_event()` después de cada paso del inner flow. |
| R6 | `EventStore.append()` es bloqueante. | `emit_event()` es `async` con `await flush()`. |
| R7 | Toda tabla tiene `org_id` y RLS. | `org_mcp_servers` cumple con RLS. |
| R8 | `max_iter` explícito en cada Agent. | `BaseCrew` usa `agent_data.get("max_iter", 5)`. |

---

## 08 — Gotchas de CrewAI (recordatorio)

| Gotcha | Síntoma | Solución en Fase 3 |
|--------|---------|-------------------|
| `crew.kickoff()` es síncrono | Bloquea event loop en Flows async | Usar `kickoff_async()` (BaseCrew.run_async) |
| `MCPServerAdapter` como context manager en async | La conexión se cierra antes de ser usada | Usar `run_in_executor` para el `__enter__` síncrono |
| `from crewai.flow.flow` no existe | ImportError | Importar desde `crewai.flow` directamente |
| `output_pydantic` no muestra error claro | Agente reintenta silenciosamente | `verbose=True` en desarrollo |
| `state_json` vs `state` en snapshots | Inconsistencia entre schema y código | Usar siempre `to_snapshot_v2()` que usa columna `state` |
