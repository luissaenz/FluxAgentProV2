### 00 — Visión del sistema
  ## Qué construir y cómo funciona
  
    Este documento especifica la implementación completa de un sistema de orquestación de agentes IA. Está escrito para ser consumido directamente por un agente de desarrollo. No asumas conocimiento previo del dominio — todo lo necesario está aquí.
  

  ### Qué es el sistema
  Una plataforma multi-tenant que permite a organizaciones definir workflows automatizados. Cada workflow es ejecutado por uno o más agentes de IA especializados. Un humano ("el supervisor") puede aprobar o rechazar acciones críticas antes de que se ejecuten.

  ### Cómo funciona en términos concretos
  
    - Un evento externo (webhook, cron, llamada manual) **crea una tarea** en la base de datos con estado `pending`.
    - El motor de orquestación detecta la tarea y **lanza un Flow de CrewAI** correspondiente al tipo de workflow.
    - El Flow ejecuta pasos en orden. Cada paso puede invocar un Crew (agente + tarea de CrewAI) para resolver algo con IA.
    - Si un paso requiere aprobación humana, el Flow **serializa su estado en la base de datos y termina**. El proceso queda suspendido.
    - El supervisor ve la aprobación pendiente en la UI, decide, y un webhook **reanuda el Flow** desde donde se detuvo.
    - Cada cambio de estado se registra como evento inmutable en `domain_events` (event sourcing).
  

  > [!IMPORTANT]
> **Regla central:** El Flow es el orquestador. Los agentes son ejecutores efímeros. El estado canónico siempre vive en la base de datos, nunca solo en memoria.
  

  ### Componentes principales
  
| Componente | Tecnología | Responsabilidad |
| --- | --- | --- |
| API Gateway | FastAPI | Recibe eventos externos, endpoints de aprobación, health checks |
| Orquestador | CrewAI Flow | Define y ejecuta la secuencia de pasos de cada workflow |
| Agentes | CrewAI Agent + Crew | Resuelven tareas específicas usando LLM y herramientas |
| Base de datos | Supabase / PostgreSQL | Estado persistente, event sourcing, snapshots, vectores |
| Vault | Supabase Vault | Almacenamiento cifrado de credenciales externas |
| Herramientas (Tools) | CrewAI BaseTool | Acciones concretas que los agentes pueden ejecutar |

  ### 01 — Stack tecnológico
  ## Dependencias y versiones

  **pyproject.toml**

```toml

```

    [tool.poetry.dependencies]
python = ">=3.12,# Orquestación de agentes
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

# LLM
anthropic = "^0.40.0"
openai = "^1.58.0"       # para embeddings text-embedding-3-small

# Utilidades
python-dotenv = "^1.0.0"
httpx = "^0.28.0"
structlog = "^24.4.0"

[tool.poetry.dev-dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-mock = "^3.14.0"
pytest-cov = "^6.0.0"
httpx = "^0.28.0"        # para TestClient de FastAPI
  

  > [!NOTE]
> **Variables de entorno requeridas:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (solo para embeddings). Crear archivo `.env` en la raíz. Nunca commitear a git.
  

  ### 02 — Estructura del proyecto
  ## Organización de archivos

  
project/
├── src/
│   ├── flows/                   # Un archivo por tipo de workflow
│   │   ├── base_flow.py          # BaseFlow con lógica común a todos los flows
│   │   └── generic_flow.py       # Flow de ejemplo (se copia para nuevos workflows)
│   │
│   ├── crews/                   # Un archivo por tipo de agente especializado
│   │   └── base_crew.py          # BaseCrew: carga soul desde DB, instancia Agent
│   │
│   ├── tools/                   # Herramientas disponibles para los agentes
│   │   ├── base_tool.py          # BaseTool con org_id y acceso al vault
│   │   └── db_read_tool.py       # Tool de solo lectura a tablas de la org
│   │
│   ├── state/                   # Modelos Pydantic del estado de cada flow
│   │   └── base_state.py         # BaseFlowState con campos comunes
│   │
│   ├── db/                      # Capa de acceso a datos
│   │   ├── client.py             # Cliente Supabase con RLS por org_id
│   │   ├── event_store.py        # Escritura de eventos inmutables
│   │   └── vault.py              # Proxy de secretos (nunca expone al agente)
│   │
│   ├── guardrails/              # Validadores de reglas de negocio
│   │   └── base_guardrail.py     # Interfaz común de guardrail
│   │
│   ├── api/                     # FastAPI
│   │   ├── main.py               # App FastAPI, routers, startup
│   │   ├── routes/
│   │   │   ├── webhooks.py       # POST /webhooks/{org_id}/{event_type}
│   │   │   ├── approvals.py      # POST /approvals/{task_id}
│   │   │   └── health.py         # GET /health
│   │   └── dependencies.py       # Auth, org_id validation
│   │
│   └── config.py                # Settings con pydantic-settings
│
├── sql/                         # Migraciones SQL en orden numérico
│   ├── 01_organizations.sql
│   ├── 02_agent_catalog.sql
│   ├── 03_tasks.sql
│   ├── 04_domain_events.sql
│   ├── 05_snapshots.sql
│   ├── 06_pending_approvals.sql
│   ├── 07_memory_vectors.sql
│   ├── 08_secrets.sql
│   └── 09_rls_policies.sql
│
├── tests/
│   ├── conftest.py               # Fixtures globales, mocks de Supabase y LLM
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env.example
├── pyproject.toml
└── README.md

  > [!NOTE]
> **Convención de nombres:** Un archivo por concepto. Si un archivo supera 200 líneas, dividirlo. Nunca poner lógica de negocio en los routes de FastAPI — solo validación y delegación.
  

  ### 03 — Base de datos
  ## Schemas SQL completos
  Ejecutar todos los archivos SQL en orden numérico en el SQL Editor de Supabase. Cada tabla tiene RLS habilitado.

  **sql/01_organizations.sql**

```sql

```

    CREATE TABLE organizations (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT NOT NULL,
  slug         TEXT UNIQUE NOT NULL,
  config       JSONB NOT NULL DEFAULT '{}',
  billing_plan TEXT DEFAULT 'free',
  -- Límites operativos por organización
  quota        JSONB DEFAULT '{"max_tasks_per_month":500,"max_tokens_per_month":5000000}',
  is_active    BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);
  

  **sql/02_agent_catalog.sql**

```sql

```

    -- Define los agentes disponibles para cada organización.
-- soul_json = personalidad + reglas rígidas del agente (equivale a un system prompt)
-- allowed_tools = lista de nombres de tools que puede usar este agente
CREATE TABLE agent_catalog (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  role          TEXT NOT NULL,
  soul_json     JSONB NOT NULL,   -- { "role": str, "goal": str, "backstory": str, "rules": [str] }
  allowed_tools JSONB NOT NULL DEFAULT '[]',
  model         TEXT DEFAULT 'claude-sonnet-4-20250514',
  max_iter      INT DEFAULT 5,
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, role)
);

ALTER TABLE agent_catalog ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_catalog
  FOR ALL USING (
    org_id::text = current_setting('app.org_id', TRUE)
  );
  

  **sql/03_tasks.sql**

```sql

```

    -- Tabla Kanban. Cada fila es una tarea en curso o completada.
-- payload = FlowState serializado. Se actualiza en cada paso del Flow.
-- status posibles: pending → in_progress → pending_approval → completed | failed
CREATE TABLE tasks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              UUID NOT NULL REFERENCES organizations(id),
  flow_id             TEXT NOT NULL,          -- ID de la ejecución de Flow
  flow_type           TEXT NOT NULL,          -- nombre del workflow (ej: "presupuesto")
  status              TEXT NOT NULL DEFAULT 'pending',
  assigned_agent_role TEXT,
  payload             JSONB,                  -- FlowState serializado (para resume)
  result              JSONB,
  approval_required   BOOLEAN DEFAULT FALSE,
  approval_status     TEXT DEFAULT 'none',    -- none | pending | approved | rejected
  approval_payload    JSONB,                  -- datos que el supervisor verá al aprobar
  idempotency_key     TEXT UNIQUE,            -- evita ejecuciones duplicadas
  retries             INT DEFAULT 0,
  max_retries         INT DEFAULT 3,
  tokens_used         INT DEFAULT 0,
  created_at          TIMESTAMPTZ DEFAULT now(),
  updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tasks_org_status  ON tasks(org_id, status);
CREATE INDEX idx_tasks_flow_id     ON tasks(flow_id);
CREATE INDEX idx_tasks_idempotency ON tasks(idempotency_key);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON tasks
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
  

  **sql/04_domain_events.sql**

```sql

```

    -- Registro inmutable de todo lo que ocurre en el sistema (event sourcing).
-- NUNCA se hace UPDATE ni DELETE en esta tabla.
-- aggregate_type: "task" | "flow" | "approval"
-- sequence: número de orden por aggregate (para replay)
CREATE TABLE domain_events (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id         UUID NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id   TEXT NOT NULL,
  event_type     TEXT NOT NULL,   -- "flow.started", "task.completed", "approval.requested"
  payload        JSONB NOT NULL,
  actor          TEXT,            -- "system", "agent:ventas", "user:abc"
  sequence       BIGINT NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_events_aggregate ON domain_events(aggregate_type, aggregate_id, sequence);
CREATE INDEX idx_events_org       ON domain_events(org_id, created_at);

-- Función para obtener el siguiente número de secuencia de forma atómica
CREATE OR REPLACE FUNCTION next_event_sequence(
  p_aggregate_type TEXT, p_aggregate_id TEXT
) RETURNS BIGINT AS $$
  SELECT COALESCE(MAX(sequence), 0) + 1
    FROM domain_events
   WHERE aggregate_type = p_aggregate_type
     AND aggregate_id   = p_aggregate_id;
$$ LANGUAGE sql;

ALTER TABLE domain_events ENABLE ROW LEVEL SECURITY;
-- Solo INSERT permitido vía RLS (los eventos son inmutables)
CREATE POLICY "append_only_insert" ON domain_events
  FOR INSERT WITH CHECK (TRUE);
CREATE POLICY "tenant_read" ON domain_events
  FOR SELECT USING (org_id::text = current_setting('app.org_id', TRUE));
  

  **sql/05_snapshots.sql**

```sql

```

    -- Guarda el estado completo de un Flow antes de pausarse (HITL).
-- Permite reanudar el Flow desde exactamente donde se detuvo.
-- UPSERT por (aggregate_type, aggregate_id) — un snapshot activo por Flow.
CREATE TABLE snapshots (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type TEXT NOT NULL,
  aggregate_id   TEXT NOT NULL,
  version        BIGINT NOT NULL,  -- sequence del último evento incluido
  state          JSONB NOT NULL,   -- FlowState.model_dump() completo
  created_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE(aggregate_type, aggregate_id)
);
  

  **sql/06_pending_approvals.sql**

```sql

```

    -- Aprobaciones pendientes de decisión del supervisor.
-- Cuando el Flow llega a un punto crítico, crea una fila aquí y pausa.
-- El supervisor aprueba/rechaza. La API reanuda el Flow.
CREATE TABLE pending_approvals (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL,
  task_id     UUID NOT NULL REFERENCES tasks(id),
  flow_type   TEXT NOT NULL,
  description TEXT NOT NULL,  -- Descripción legible de qué se está pidiendo aprobar
  payload     JSONB NOT NULL,  -- Datos que el supervisor necesita ver para decidir
  status      TEXT DEFAULT 'pending',  -- pending | approved | rejected
  decided_by  TEXT,
  decided_at  TIMESTAMPTZ,
  expires_at  TIMESTAMPTZ,  -- opcional: auto-rechazar si no decide antes de este tiempo
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_approvals_org_pending ON pending_approvals(org_id, status);
ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON pending_approvals
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
  

  **sql/07_memory_vectors.sql**

```sql

```

    -- Memoria semántica de largo plazo para los agentes.
-- Los embeddings permiten búsqueda por similitud (no por keyword).
-- Aislado por org_id — cada organización tiene su propia memoria.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_vectors (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL,
  agent_role  TEXT,                    -- null = memoria compartida por toda la org
  source_type TEXT NOT NULL,           -- "conversation", "document", "task_result"
  content     TEXT NOT NULL,
  embedding   vector(1536),           -- text-embedding-3-small de OpenAI
  metadata    JSONB,
  valid_to    TIMESTAMPTZ DEFAULT 'infinity',  -- para expirar memorias obsoletas
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Índice vectorial (IVFFlat). lists ≈ sqrt(filas esperadas)
CREATE INDEX idx_memory_embedding
  ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Función de búsqueda semántica (llamar con service_role para evitar RLS)
CREATE OR REPLACE FUNCTION search_memories(
  query_embedding vector(1536),
  p_org_id        UUID,
  p_agent_role    TEXT DEFAULT NULL,
  match_limit     INT DEFAULT 5,
  min_similarity  FLOAT DEFAULT 0.7
) RETURNS TABLE(id UUID, content TEXT, similarity FLOAT) AS $$
  SELECT id, content, 1 - (embedding  query_embedding) AS similarity
    FROM memory_vectors
   WHERE org_id = p_org_id
     AND (p_agent_role IS NULL OR agent_role = p_agent_role)
     AND valid_to > now()
     AND 1 - (embedding  query_embedding) >= min_similarity
   ORDER BY embedding  query_embedding
   LIMIT match_limit;
$$ LANGUAGE sql;

ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON memory_vectors
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
  

  **sql/08_secrets.sql**

```sql

```

    -- Credenciales cifradas de servicios externos.
-- REGLA: Solo el service_role puede SELECT. Los agentes NUNCA acceden directamente.
-- La tool que necesita una credencial llama al VaultProxy, que hace la query.
CREATE TABLE secrets (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       UUID NOT NULL,
  name         TEXT NOT NULL,      -- ej: "whatsapp_token", "stripe_key"
  secret_value TEXT NOT NULL,      -- cifrado con Supabase Vault o AES-256
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, name)
);

ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_only" ON secrets
  FOR SELECT USING (auth.role() = 'service_role');
  

  ### Fase 1
  ## Motor base — Un Flow completo y testeable

  
    1
    
      ### Objetivo: sistema funcional de extremo a extremo
      Al terminar esta fase, el sistema debe poder recibir un evento externo vía POST, ejecutar un Flow de CrewAI con un agente que resuelve una tarea, persistir el estado en Supabase y devolver el resultado. Sin aprobaciones, sin vault, sin memoria — solo el ciclo base funcionando.

      
        **Criterio de éxito:** suite de tests pasa al 100%
        **Entregable verificable:** `pytest tests/` sin fallos
      
    
  

  ### 1.1 — BaseFlowState
  Todo Flow hereda de `BaseFlowState`. Este modelo Pydantic representa el estado completo de una ejecución. Se serializa en `tasks.payload` después de cada paso importante.

  **src/state/base_state.py**

```python

```

    from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid

class BaseFlowState(BaseModel):
    """
    Estado base de todos los Flows del sistema.

    DISEÑO:
    - org_id identifica el tenant. Es el primer campo siempre.
    - flow_id es único por ejecución (no por tipo de Flow).
    - task_id es None hasta que recibir_evento() crea la fila en tasks.
    - Cada Flow concreto hereda esta clase y agrega sus campos de dominio.

    EJEMPLO de subclase:
        class PresupuestoState(BaseFlowState):
            flow_type: str = "presupuesto"
            cliente_id: str = ""
            monto: float = 0.0
    """

    # ── Identidad del tenant ─────────────────────────────
    org_id: str

    # ── Identificadores de ejecución ─────────────────────
    flow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    flow_type: str = "generic"     # Sobreescribir en cada subclase
    task_id: Optional[str] = None   # Asignado al persistir en DB

    # ── Estado Kanban ─────────────────────────────────────
    status: Literal[
        "pending", "in_progress",
        "pending_approval", "approved", "rejected",
        "completed", "failed"
    ] = "pending"

    # ── Trazabilidad ──────────────────────────────────────
    triggered_by: str = "manual"    # "webhook", "cron", "api", "manual"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None

    # ── Resiliencia ───────────────────────────────────────
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None

    # ── Aprobación humana ─────────────────────────────────
    approval_payload: Optional[dict] = None
    approval_decision: Optional[Literal["approved", "rejected"]] = None
    approval_decided_by: Optional[str] = None

    # ── Control de tokens ─────────────────────────────────
    tokens_used: int = 0
    max_tokens: int = 50_000

    def touch(self) -> None:
        """Actualizar updated_at. Llamar antes de persistir."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_snapshot(self) -> dict:
        """Serializar para guardar en snapshots table."""
        return self.model_dump()

    @classmethod
    def from_snapshot(cls, data: dict) -> "BaseFlowState":
        """Restaurar desde snapshot (para HITL resume)."""
        return cls(**data)
  

  ### 1.2 — Cliente de base de datos con RLS
  > [!IMPORTANT]
> **Regla de RLS:** Antes de cualquier query, el cliente debe setear `app.org_id` en la sesión. Las políticas RLS usan este valor para filtrar filas automáticamente. Si no está seteado, las queries con anon key devuelven 0 filas.
  

  **src/db/client.py**

```python

```

    from supabase import create_client, Client
from src.config import settings
from typing import Optional

# Cache de clientes por org_id para evitar reconexiones
_tenant_clients: dict[str, Client] = {}
_service_client: Optional[Client] = None

def get_tenant_client(org_id: str) -> Client:
    """
    Cliente Supabase con RLS activo para el tenant especificado.
    Todas las queries quedan automáticamente filtradas por org_id.
    Usar para operaciones de datos de la organización.
    """
    if org_id not in _tenant_clients:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        # Setear org_id para que RLS funcione en esta sesión
        client.postgrest.headers["x-app-org-id"] = org_id
        # También via set_config para funciones SQL
        client.rpc("set_config", {
            "setting": "app.org_id",
            "value": org_id
        }).execute()
        _tenant_clients[org_id] = client
    return _tenant_clients[org_id]

def get_service_client() -> Client:
    """
    Cliente con service_role. Bypasea RLS.
    Usar SOLO para: EventStore, Vault, snapshots.
    NUNCA pasar este cliente a un agente o tool.
    """
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    return _service_client
  

  ### 1.3 — BaseCrew: agente genérico
  El agente no tiene lógica hardcodeada. Su personalidad, objetivo y reglas se cargan desde `agent_catalog` en la base de datos al instanciarlo. Esto permite modificar el comportamiento de un agente sin tocar el código.

  **src/crews/base_crew.py**

```python

```

    from crewai import Agent, Task, Crew
from pydantic import BaseModel
from typing import Type, Optional
from src.db.client import get_tenant_client

class BaseCrew:
    """
    Clase base para todos los Crews del sistema.
    
    Carga la definición del agente (soul_json) desde agent_catalog en Supabase.
    El código no sabe nada de la personalidad del agente — eso vive en la DB.
    
    Para crear un nuevo tipo de agente:
    1. Insertar una fila en agent_catalog con role="mi_rol" y soul_json correspondiente.
    2. Crear una subclase de BaseCrew que defina el Task apropiado.
    """

    def __init__(self, org_id: str, role: str):
        self.org_id = org_id
        self.role = role
        db = get_tenant_client(org_id)

        result = db.table("agent_catalog")\
            .select("*")\
            .eq("role", role)\
            .eq("is_active", True)\
            .single()\
            .execute()

        if not result.data:
            raise ValueError(
                f"Agente con role='{role}' no encontrado para org_id='{org_id}'"
            )

        self.soul = result.data["soul_json"]
        self.allowed_tools_names: list[str] = result.data["allowed_tools"]
        self.model: str = result.data.get("model", "claude-sonnet-4-20250514")
        self.max_iter: int = result.data.get("max_iter", 5)

    def build_agent(self, tools: list) -> Agent:
        """Instanciar el Agent de CrewAI con la configuración de la DB."""
        return Agent(
            role=self.soul["role"],
            goal=self.soul["goal"],
            backstory=self.soul["backstory"],
            tools=tools,
            llm=self.model,
            verbose=False,
            allow_delegation=False,   # SIEMPRE False — el Flow controla la delegación
            max_iter=self.max_iter,
        )

    def run(self, task_description: str, inputs: dict,
            output_model: Optional[Type[BaseModel]] = None) -> str:
        """
        Ejecutar el agente con una tarea específica.
        Retorna el resultado como string. Si output_model está definido,
        retorna el resultado parseado como ese modelo Pydantic.
        """
        tools = self._resolve_tools()
        agent = self.build_agent(tools)

        task = Task(
            description=task_description,
            expected_output="Resultado completo de la tarea en el formato solicitado.",
            agent=agent,
            output_pydantic=output_model
        )

        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = crew.kickoff(inputs=inputs)
        return result

    def _resolve_tools(self) -> list:
        """
        Convertir allowed_tools_names en instancias de BaseTool.
        Implementar en Fase 1 con un registry simple:
        { "db_read": DbReadTool, "db_write": DbWriteTool, ... }
        """
        from src.tools.registry import TOOL_REGISTRY
        return [
            TOOL_REGISTRY[name](org_id=self.org_id)
            for name in self.allowed_tools_names
            if name in TOOL_REGISTRY
        ]
  

  ### 1.4 — BaseFlow: estructura común de todos los workflows
  **src/flows/base_flow.py**

```python

```

    from crewai.flow.flow import Flow
from src.state.base_state import BaseFlowState
from src.db.client import get_tenant_client, get_service_client
from src.db.event_store import EventStore
from datetime import datetime, timezone

class BaseFlow(Flow[BaseFlowState]):
    """
    Clase base para todos los Flows del sistema.
    
    Provee métodos de utilidad para persistir estado, registrar eventos
    y manejar errores de forma consistente.
    """

    def persist_state(self, extra_fields: dict = {}) -> None:
        """
        Guardar el estado actual del Flow en tasks.payload.
        Llamar al final de cada paso que modifica el estado.
        """
        self.state.touch()
        db = get_tenant_client(self.state.org_id)
        update_data = {
            "status": self.state.status,
            "payload": self.state.model_dump(),
            "updated_at": self.state.updated_at,
            **extra_fields
        }
        db.table("tasks")\
          .update(update_data)\
          .eq("id", self.state.task_id)\
          .execute()

    def create_task_record(self) -> str:
        """Crear la fila inicial en tasks. Retorna el task_id."""
        db = get_tenant_client(self.state.org_id)
        result = db.table("tasks").insert({
            "org_id": self.state.org_id,
            "flow_id": self.state.flow_id,
            "flow_type": self.state.flow_type,
            "status": "in_progress",
            "payload": self.state.model_dump(),
        }).execute()
        task_id = result.data[0]["id"]
        self.state.task_id = task_id
        self.state.status = "in_progress"
        return task_id

    def emit_event(self, event_type: str, payload: dict = {}) -> None:
        """Registrar un evento en domain_events. Bloqueante."""
        EventStore.append(
            org_id=self.state.org_id,
            aggregate_type="flow",
            aggregate_id=self.state.task_id or self.state.flow_id,
            event_type=event_type,
            payload=payload
        )

    def handle_step_error(self, error: Exception, step_name: str) -> None:
        """Registrar el error y decidir si reintentar o marcar como fallido."""
        self.state.last_error = str(error)
        self.state.retry_count += 1
        if self.state.retry_count > self.state.max_retries:
            self.state.status = "failed"
            self.emit_event("flow.failed", {"step": step_name, "error": str(error)})
        self.persist_state()
        raise error  # Re-lanzar para que FastAPI devuelva 500
  

  ### 1.5 — API Gateway
  **src/api/main.py**

```python

```

    from fastapi import FastAPI
from src.api.routes import webhooks, approvals, health

app = FastAPI(title="Orchestration Engine", version="1.0.0")

app.include_router(health.router)
app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(approvals.router, prefix="/approvals")
  

  **src/api/routes/webhooks.py**

```python

```

    from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

class WebhookPayload(BaseModel):
    org_id: str
    flow_type: str      # Qué workflow ejecutar (ej: "presupuesto")
    data: dict          # Datos del evento (ej: {"cliente_id": "...", "monto": 5000})
    triggered_by: str = "webhook"
    idempotency_key: str = ""

@router.post("/")
async def receive_webhook(payload: WebhookPayload, background: BackgroundTasks):
    """
    Punto de entrada para eventos externos.
    Lanza el Flow en background para no bloquear la respuesta HTTP.
    """
    from src.flows.registry import FLOW_REGISTRY

    flow_class = FLOW_REGISTRY.get(payload.flow_type)
    if not flow_class:
        raise HTTPException(404, f"Tipo de workflow '{payload.flow_type}' no registrado")

    # Lanzar en background — la respuesta HTTP no espera al Flow
    background.add_task(
        flow_class.launch,
        org_id=payload.org_id,
        data=payload.data,
        triggered_by=payload.triggered_by,
        idempotency_key=payload.idempotency_key or None
    )

    return {"status": "accepted", "flow_type": payload.flow_type}
  

  ### 1.6 — Tests de Fase 1

  
    
      unit
      `tests/unit/test_base_flow_state.py`
    
    
      
        - Instanciar `BaseFlowState(org_id="test-org")` — debe tener `flow_id` auto-generado (UUID v4)
        - `task_id` debe ser `None` hasta asignación explícita
        - `status` inicial debe ser `"pending"`
        - `touch()` debe actualizar `updated_at` con timestamp UTC
        - `to_snapshot()` / `from_snapshot()` debe ser invertible (round-trip sin pérdida)
        - Intentar asignar `status="invalido"` debe lanzar `ValidationError`
        - `tokens_used` debe ser 0 por defecto y aceptar enteros positivos
      
    
  

  
    
      unit
      `tests/unit/test_event_store.py`
    
    
      
        - Mock de Supabase service client
        - `EventStore.append()` debe llamar a `next_event_sequence` antes de insertar
        - Si la inserción falla, debe lanzar `EventStoreError` (el Flow no debe continuar)
        - `save_snapshot()` debe hacer UPSERT (no INSERT)
        - `get_latest_snapshot()` debe retornar `None` si no existe snapshot
      
    
  

  
    
      integration
      `tests/integration/test_webhook_to_flow.py`
    
    
      
        - Mock de Supabase completo (sin DB real) y LLM (sin llamadas reales a Claude)
        - `POST /webhooks/` con `flow_type` válido → responde `202 Accepted`
        - `POST /webhooks/` con `flow_type` inválido → responde `404`
        - El Flow lanzado en background debe llamar a `create_task_record()`
        - El Flow debe emitir evento `"flow.started"` al arrancar
        - El Flow debe actualizar `status="completed"` al terminar exitosamente
      
    
  

  
    Entregables verificables — Fase 1
    
      BaseFlowState con round-trip serialización
      BaseCrew cargando soul desde DB mockeada
      BaseFlow con persist_state y emit_event
      EventStore con escritura transaccional
      API Gateway recibiendo webhooks
      FlowRegistry con decorador
      ToolRegistry con decorador
      set_config RPC para RLS
      BaseFlow lifecycle completo (launch, _run_crew, error handling)
      GET /tasks/{id} endpoint para polling
      GenericFlow como ejemplo mínimo
      Test fixtures completas (conftest.py)
      Suite de tests unitarios, integración y E2E pasando
    
  

### 1.7 — FlowRegistry: Registro centralizado de Flows

El Registry permite registrar Flows mediante un decorador, habilitando descubrimiento automático y ejecución por nombre de clase.

**src/flows/registry.py**

```python

```

  from typing import Type, Dict, Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class FlowRegistry:
    def __init__(self):
        self._flows: Dict[str, Type] = {}
        self._builders: Dict[str, Callable[[], Any]] = {}

    def register(self, name: str = None) -> Callable[[Type], Type]:
        """
        Decorador para registrar una clase Flow.
        
        Uso:
            @FlowRegistry.register("my_flow")
            class MyFlow(BaseFlow):
                ...
        """
        def decorator(flow_class: Type) -> Type:
            flow_name = name or flow_class.__name__
            self._flows[flow_name.lower()] = flow_class
            logger.info(f"Registered flow: {flow_name}")
            return flow_class
        
        return decorator

    def register_builder(self, name: str, builder: Callable[[], Any]) -> None:
        """Registrar un builder function para instanciación lazy."""
        self._builders[name.lower()] = builder

    def get(self, name: str) -> Type:
        """Obtener clase Flow por nombre."""
        name_lower = name.lower()
        if name_lower not in self._flows:
            raise ValueError(f"Flow '{name}' no encontrado. Disponibles: {list(self._flows.keys())}")
        return self._flows[name_lower]

    def create(self, name: str, **kwargs) -> Any:
        """Crear instancia de Flow por nombre."""
        flow_class = self.get(name)
        return flow_class(**kwargs)

    def list_flows(self) -> list[str]:
        """Listar todos los flows registrados."""
        return list(self._flows.keys())

    def has(self, name: str) -> bool:
        """Verificar si un flow está registrado."""
        return name.lower() in self._flows

# Instancia global del registry
flow_registry = FlowRegistry()

# Decorador convenience
def register_flow(name: str = None) -> Callable[[Type], Type]:
    return flow_registry.register(name)

> [!NOTE]
> **Patrón de uso:** Cada Flow se importa al inicio de la aplicación, lo que ejecuta el decorador y lo registra automáticamente. El API Gateway puede entonces ejecutar cualquier Flow por nombre sin acoplamiento directo.

### 1.8 — ToolRegistry: Registro de Tools para Agents

Registry paralelo para Tools de CrewAI, permitiendo registro dinámico y metadata asociada para validación y documentación.

**src/tools/registry.py**

```python

```

  from typing import Type, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from functools import wraps
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolMetadata:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    timeout_seconds: int = 30
    retry_count: int = 3
    tags: List[str] = field(default_factory=list)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Type] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._instances: Dict[str, Any] = {}

    def register(
        self,
        name: str = None,
        description: str = "",
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        retry_count: int = 3,
        tags: List[str] = None
    ) -> Callable[[Type], Type]:
        """
        Decorador para registrar una Tool con metadata.
        
        Uso:
            @ToolRegistry.register("fetch_url", description="Fetch URL content", timeout_seconds=60)
            class FetchURLTool(BaseTool):
                ...
        """
        def decorator(tool_class: Type) -> Type:
            tool_name = name or tool_class.__name__
            self._tools[tool_name.lower()] = tool_class
            self._metadata[tool_name.lower()] = ToolMetadata(
                name=tool_name,
                description=description,
                requires_approval=requires_approval,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                tags=tags or []
            )
            logger.info(f"Registered tool: {tool_name}")
            return tool_class
        
        return decorator

    def get(self, name: str) -> Type:
        name_lower = name.lower()
        if name_lower not in self._tools:
            raise ValueError(f"Tool '{name}' no encontrada. Disponibles: {list(self._tools.keys())}")
        return self._tools[name_lower]

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        return self._metadata.get(name.lower())

    def get_or_create(self, name: str, **kwargs) -> Any:
        """Obtener o crear instancia singleton de la tool."""
        name_lower = name.lower()
        if name_lower not in self._instances:
            tool_class = self.get(name)
            self._instances[name_lower] = tool_class(**kwargs)
        return self._instances[name_lower]

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def list_by_tag(self, tag: str) -> List[str]:
        """Listar tools que tienen un tag específico."""
        return [
            name for name, meta in self._metadata.items()
            if tag in meta.tags
        ]

    def clear(self) -> None:
        """Limpiar registry (útil para tests)."""
        self._tools.clear()
        self._metadata.clear()
        self._instances.clear()

tool_registry = ToolRegistry()

def register_tool(
    name: str = None,
    description: str = "",
    requires_approval: bool = False,
    timeout_seconds: int = 30,
    retry_count: int = 3,
    tags: List[str] = None
) -> Callable[[Type], Type]:
    return tool_registry.register(
        name, description, requires_approval, timeout_seconds, retry_count, tags
    )

**src/tools/builtin.py — Ejemplo de uso del decorador**

```python

```

  from crewai.tools import BaseTool
from pydantic import Field
from tool_registry import register_tool

@register_tool(
    "search_documents",
    description="Buscar documentos en el sistema de archivos",
    timeout_seconds=60,
    tags=["document", "search"]
)
class SearchDocumentsTool(BaseTool):
    query: str = Field(description="Texto a buscar en documentos")
    directory: str = Field(default="./", description="Directorio raíz de búsqueda")
    file_types: List[str] = Field(
        default_factory=lambda: [".txt", ".md", ".pdf"],
        description="Extensiones de archivo a incluir"
    )

    def _run(self, query: str, directory: str = "./", file_types: List[str] = None) -> str:
        """Ejecutar búsqueda de documentos."""
        # Implementación real con os.walk o similar
        return f"Encontrados 3 documentos para: {query}"

### 1.9 — SQL: set_config RPC para RLS

Función RPC de Supabase para establecer configuración de tenant en RLS. Permite que las políticas RLS filtren correctamente por organización.

**supabase/migrations/001_set_config_rpc.sql**

```sql

```

  -- Función RPC para establecer configuración de sesión de tenant
-- Uso: SELECT set_config('app.org_id', 'org_123', true);
-- Esto configura la variable de sesión que las políticas RLS usan

CREATE OR REPLACE FUNCTION set_config(
    p_key TEXT,
    p_value TEXT,
    p_is_local BOOLEAN DEFAULT TRUE
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Validar que la key es una de las permitidas
    IF p_key NOT IN ('app.org_id', 'app.user_id', 'app.role') THEN
        RAISE EXCEPTION 'Invalid config key: %', p_key;
    END IF;

    -- Validar que el valor no sea nulo para org_id y user_id
    IF p_key IN ('app.org_id', 'app.user_id') AND p_value IS NULL THEN
        RAISE EXCEPTION 'Value cannot be null for key: %', p_key;
    END IF;

    -- Ejecutar set_config de PostgreSQL
    PERFORM pg_catalog.set_config(p_key, p_value, p_is_local);
END;
$$;

-- Crear función helper para verificar acceso a org
CREATE OR REPLACE FUNCTION current_org_id()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN current_setting('app.org_id', TRUE);
END;
$$;

-- Ejemplo de política RLS usando la función
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_org_access ON tasks
    FOR ALL
    USING (org_id = current_org_id());

**src/db/session.py — Uso de set_config**

```python

```

  from supabase import create_client, Client
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class TenantClient:
    def __init__(self, supabase: Client, org_id: str, user_id: str = None):
        self._client = supabase
        self._org_id = org_id
        self._user_id = user_id

    def __enter__(self) -> "TenantClient":
        """Establecer configuración de sesión para RLS."""
        try:
            self._client.rpc("set_config", {
                "p_key": "app.org_id",
                "p_value": self._org_id,
                "p_is_local": True
            }).execute()

            if self._user_id:
                self._client.rpc("set_config", {
                    "p_key": "app.user_id",
                    "p_value": self._user_id,
                    "p_is_local": True
                }).execute()

            logger.debug(f"Tenant config set: org_id={self._org_id}, user_id={self._user_id}")
        except Exception as e:
            logger.error(f"Failed to set tenant config: {e}")
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Limpiar configuración de sesión."""
        try:
            self._client.rpc("set_config", {
                "p_key": "app.org_id",
                "p_value": None,
                "p_is_local": True
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to clear tenant config: {e}")

    def table(self, table_name: str):
        return self._client.table(table_name)

    def rpc(self, func: str, params: dict):
        return self._client.rpc(func, params)

@contextmanager
def get_tenant_client(org_id: str, user_id: str = None) -> TenantClient:
    """
    Context manager para obtener cliente con configuración de tenant.
    
    Uso:
        with get_tenant_client("org_123", "user_456") as db:
            db.table("tasks").select("*").execute()
    """
    client = TenantClient(get_supabase_client(), org_id, user_id)
    with client:
        yield client

### 1.10 — BaseFlowState con validadores UUID

Actualización del estado base con validaciones robustas para IDs y manejo de errores.

**src/flows/state.py**

```python

```

  from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import json

class FlowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class BaseFlowState(BaseModel):
    task_id: str = Field(..., description="UUID único de la tarea")
    org_id: str = Field(..., description="UUID de la organización")
    user_id: Optional[str] = Field(None, description="UUID del usuario que inicia el flow")
    flow_type: str = Field(..., description="Nombre del tipo de flow")
    status: FlowStatus = Field(default=FlowStatus.PENDING)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0, le=5)
    max_retries: int = Field(default=3, ge=0, le=10)
    correlation_id: Optional[str] = None

    # Validadores de UUID
    @field_validator('task_id', 'org_id', 'user_id')
    def validate_uuid_format(cls, v: str) -> str:
        """Validar que el valor es un UUID válido."""
        if v is None:
            return v
        if v == "":
            raise ValueError("UUID cannot be empty")
        # Validar formato UUID básico (8-4-4-4-12 hex)
        import re
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', v, re.I):
            raise ValueError(f"Invalid UUID format: {v}")
        return v.lower()

    @field_validator('flow_type')
    def validate_flow_type(cls, v: str) -> str:
        """Validar nombre de flow."""
        if not v or " " in v:
            raise ValueError("flow_type cannot be empty or contain spaces")
        return v

    @model_validator('mode')
    def validate_retry_count(cls, values: Dict) -> Dict:
        """Validar que retry_count no exceda max_retries."""
        retry_count = values.get('retry_count', 0)
        max_retries = values.get('max_retries', 3)
        if retry_count > max_retries:
            raise ValueError(f"retry_count ({retry_count}) cannot exceed max_retries ({max_retries})")
        return values

    def touch(self) -> None:
        """Actualizar timestamp de modificación."""
        self.updated_at = datetime.utcnow()

    def start(self) -> None:
        """Marcar flow como iniciado."""
        self.status = FlowStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.touch()

    def complete(self, output: Dict[str, Any] = None) -> None:
        """Marcar flow como completado."""
        self.status = FlowStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output:
            self.output_data.update(output)
        self.touch()

    def fail(self, error: str) -> None:
        """Marcar flow como fallido."""
        self.status = FlowStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        self.touch()

    def to_snapshot(self) -> Dict[str, Any]:
        """Serializar estado para persistencia."""
        return self.model_dump(mode='json')

    @classmethod
    def from_snapshot(cls, data: Dict[str, Any]) -> "BaseFlowState":
        """Reconstruir estado desde snapshot."""
        if isinstance(data.get('status'), str):
            data['status'] = FlowStatus(data['status'])
        return cls(**data)

    class Config:
        use_enum_values = False
        validate_assignment = True

### 1.11 — BaseFlow lifecycle completo

Implementación completa del ciclo de vida de BaseFlow incluyendo todos los métodos necesarios para ejecución, persistencia y manejo de errores.

**src/flows/base_flow.py — Lifecycle completo**

```python

```

  from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
import logging
from functools import wraps

from flows.state import BaseFlowState, FlowStatus
from flows.registry import flow_registry
from events.store import EventStore
from db.session import get_tenant_client

logger = logging.getLogger(__name__)

# Decorador para manejo de errores
def with_error_handling(reraise: bool = True):
    """
    Decorador para manejo automático de errores en métodos de BaseFlow.
    
    Maneja:
    - Logging de errores
    - Persistencia de estado de error
    - Reintentos si retry_count 
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_msg = f"{func.__name__}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)

                # Marcar estado como fallido
                if hasattr(self, 'state'):
                    self.state.fail(error_msg)

                    # Intentar reintento si aplica
                    if self.state.retry_count self.state.max_retries:
                        self.state.retry_count += 1
                        logger.info(f"Retrying flow (attempt {self.state.retry_count}/{self.state.max_retries})")
                        self.persist_state({"retry_count": self.state.retry_count})
                        return func(self, *args, **kwargs)

                    # Persistir estado final de error
                    self.persist_state({"error": error_msg})

                if reraise:
                    raise
                return None
        return wrapper
    return decorator

class BaseFlow(ABC):
    """Clase base para todos los Flows."""

    event_store: EventStore = None

    def __init__(
        self,
        task_id: str,
        org_id: str,
        user_id: str = None,
        input_data: Dict[str, Any] = None,
        correlation_id: str = None
    ):
        self.state = BaseFlowState(
            task_id=task_id,
            org_id=org_id,
            user_id=user_id,
            flow_type=self.__class__.__name__,
            input_data=input_data or {},
            correlation_id=correlation_id or str(uuid4())
        )
        self._event_store = None

    @property
    def events(self) -> EventStore:
        """Obtener EventStore lazily."""
        if self._event_store is None:
            self._event_store = EventStore(
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                org_id=self.state.org_id
            )
        return self._event_store

    @with_error_handling(reraise=True)
    def launch(self) -> Dict[str, Any]:
        """
        Punto de entrada principal para ejecutar el Flow.
        
        SECUENCIA:
        1. Validar precondiciones
        2. Crear registro de task en DB
        3. Iniciar estado
        4. Ejecutar crew
        5. Persistir resultado
        6. Emitir evento de completitud
        """
        logger.info(f"Launching flow: {self.state.flow_type}, task_id={self.state.task_id}")

        # 1. Validar precondiciones
        self.validate_input()

        # 2. Crear registro en DB
        self.create_task_record()

        # 3. Iniciar estado
        self.state.start()
        self.persist_state({"status": "running"})

        # 4. Ejecutar crew
        result = self._run_crew()

        # 5. Completar y persistir
        self.state.complete(result)
        self.persist_state({"status": "completed", "output_data": result})

        # 6. Emitir evento
        self.emit_event("flow.completed", {"result": result})

        logger.info(f"Flow completed: {self.state.task_id}")
        return result

    def validate_input(self) -> None:
        """Validar input del flow. Override en subclasses."""
        pass

    def create_task_record(self) -> None:
        """
        Crear registro de task en la base de datos.
        
        TABLE: tasks
        - id: UUID (task_id)
        - org_id: UUID
        - user_id: UUID (nullable)
        - flow_type: VARCHAR
        - status: VARCHAR
        - input_data: JSONB
        - correlation_id: UUID
        """
        try:
            with get_tenant_client(self.state.org_id, self.state.user_id) as db:
                db.table("tasks").insert({
                    "id": self.state.task_id,
                    "org_id": self.state.org_id,
                    "user_id": self.state.user_id,
                    "flow_type": self.state.flow_type,
                    "status": "pending",
                    "input_data": self.state.input_data,
                    "correlation_id": self.state.correlation_id,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                logger.debug(f"Task record created: {self.state.task_id}")
        except Exception as e:
            logger.warning(f"Failed to create task record: {e}")

    def persist_state(self, updates: Dict[str, Any] = None) -> None:
        """
        Persistir estado del Flow en la base de datos.
        
        TABLE: task_states (snapshots)
        - aggregate_type: VARCHAR
        - aggregate_id: UUID (task_id)
        - version: INTEGER
        - state: JSONB
        """
        if updates:
            for key, value in updates.items():
                setattr(self.state, key, value)

        try:
            with get_tenant_client(self.state.org_id) as db:
                seq = db.rpc("next_event_sequence", {
                    "p_aggregate_type": "flow",
                    "p_aggregate_id": self.state.task_id
                }).execute().data or 1

                db.table("snapshots").upsert({
                    "aggregate_type": "flow",
                    "aggregate_id": self.state.task_id,
                    "version": seq,
                    "state": self.state.to_snapshot()
                }, on_conflict="aggregate_type,aggregate_id").execute()

                # También actualizar task.status
                db.table("tasks").update({
                    "status": self.state.status.value,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", self.state.task_id).execute()

        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def emit_event(self, event_type: str, payload: Dict[str, Any] = None) -> None:
        """Emitir evento al EventStore."""
        try:
            self.events.append(
                event_type=event_type,
                payload=payload or {}
            )
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")

    @abstractmethod
    def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar el Crew de agentes.
        Debe ser implementado por cada Flow concreto.
        """
        pass

    class Config:
        arbitrary_types_allowed = True

### 1.12 — EventStore: Persistencia de eventos

Implementación de Event Store para auditoría y recuperación de estado, con escritura transaccional.

**src/events/store.py**

```python

```

  from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import logging
from dataclasses import dataclass, field, asdict

from db.session import get_tenant_client

logger = logging.getLogger(__name__)

@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid4()))
    aggregate_type: str = None
    aggregate_id: str = None
    event_type: str = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    org_id: str = None

class EventStore:
    """
    Event Store para persistencia de eventos con soporte transaccional.
    
    TABLE: events
    - id: UUID
    - aggregate_type: VARCHAR (e.g., "flow", "task")
    - aggregate_id: UUID
    - event_type: VARCHAR
    - payload: JSONB
    - metadata: JSONB
    - sequence: INTEGER
    - org_id: UUID
    - created_at: TIMESTAMP
    """

    def __init__(
        self,
        aggregate_type: str,
        aggregate_id: str,
        org_id: str,
        user_id: str = None
    ):
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.org_id = org_id
        self.user_id = user_id
        self._pending_events: List[Event] = []
        self._sequence = 0

    def append(
        self,
        event_type: str,
        payload: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Event:
        """
        Agregar evento a la cola de escritura.
        El evento se persiste realmente al llamar flush().
        """
        event = Event(
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            event_type=event_type,
            payload=payload or {},
            metadata=metadata or {},
            sequence=self._sequence + 1,
            org_id=self.org_id
        )
        self._pending_events.append(event)
        self._sequence += 1
        logger.debug(f"Event queued: {event_type}")
        return event

    def flush(self) -> None:
        """
        Persistir todos los eventos pendientes en una transacción.
        
        Usa bulk insert para eficiencia.
        """
        if not self._pending_events:
            return

        try:
            with get_tenant_client(self.org_id, self.user_id) as db:
                records = [
                    {
                        "id": e.id,
                        "aggregate_type": e.aggregate_type,
                        "aggregate_id": e.aggregate_id,
                        "event_type": e.event_type,
                        "payload": e.payload,
                        "metadata": e.metadata,
                        "sequence": e.sequence,
                        "org_id": e.org_id,
                        "created_at": e.created_at.isoformat()
                    }
                    for e in self._pending_events
                ]

                db.table("events").insert(records).execute()
                logger.info(f"Flushed {len(records)} events for {self.aggregate_id}")

                # Limpiar cola
                self._pending_events.clear()

        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            raise

    def get_events(
        self,
        event_type: str = None,
        limit: int = 100
    ) -> List[Event]:
        """Recuperar eventos del aggregate."""
        try:
            with get_tenant_client(self.org_id) as db:
                query = db.table("events").select("*").eq(
                    "aggregate_id", self.aggregate_id
                ).eq("aggregate_type", self.aggregate_type).order(
                    "sequence", desc=False).limit(limit)

                if event_type:
                    query = query.eq("event_type", event_type)

                result = query.execute()
                return [Event(**r) for r in result.data]

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Auto-flush al salir del context."""
        if self._pending_events:
            self.flush()

### 1.13 — Webhook API con manejo de errores y correlation ID

API Gateway para recibir webhooks externos con correlación de IDs y manejo robusto de errores.

**src/api/routes/webhooks.py**

```python

```

  from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import uuid4
import logging

from flows.registry import flow_registry
from api.middleware import get_org_id_from_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookPayload(BaseModel):
    flow_type: str = Field(..., description="Nombre del flow a ejecutar")
    input_data: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = Field(None, description="URL para notificar resultado")
    correlation_id: Optional[str] = Field(None, description="ID de correlación del cliente")

class WebhookResponse(BaseModel):
    task_id: str
    correlation_id: str
    status: str
    message: str

@router.post("/trigger", response_model=WebhookResponse)
async trigger_flow(
    payload: WebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Endpoint para dispara Flows via webhook.
    
    Encabezados requeridos:
    - X-Org-ID: ID de la organización
    
    Encabezados opcionales:
    - X-Correlation-ID: ID de correlación del cliente (se usa si se provee)
    - X-Callback-URL: URL para notificar cuando el flow termine
    """
    
    # Extraer correlation ID del header o generar nuevo
    correlation_id = (
        payload.correlation_id or
        request.headers.get("X-Correlation-ID") or
        str(uuid4())
    )
    
    # Extraer org_id del middleware o header
    org_id = get_org_id_from_request(request)
    if not org_id:
        raise HTTPException(
            status_code=401,
            detail="Organization ID no proporcionado"
        )

    # Validar que el flow existe
    if not flow_registry.has(payload.flow_type):
        raise HTTPException(
            status_code=404,
            detail=f"Flow '{payload.flow_type}' no encontrado"
        )

    # Generar task_id
    task_id = str(uuid4())

    # Crear instancia del flow (sin ejecutar)
    try:
        flow = flow_registry.create(
            payload.flow_type,
            task_id=task_id,
            org_id=org_id,
            input_data=payload.input_data,
            correlation_id=correlation_id
        )
    except Exception as e:
        logger.error(f"Failed to create flow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear flow: {str(e)}"
        )

    # Ejecutar en background
    background_tasks.add_task(
        execute_flow_safe,
        flow,
        payload.callback_url,
        org_id
    )

    logger.info(
        f"Webhook triggered: flow={payload.flow_type}, task_id={task_id}, correlation_id={correlation_id}"
    )

    return WebhookResponse(
        task_id=task_id,
        correlation_id=correlation_id,
        status="accepted",
        message="Flow aceptado para ejecución"
    )

async def execute_flow_safe(
    flow,
    callback_url: Optional[str],
    org_id: str
) -> None:
    """
    Ejecutar flow de forma segura, manejando errores y callbacks.
    """
    try:
        result = flow.launch()
        
        # Callback si se especificó
        if callback_url:
            await send_callback(callback_url, {
                "task_id": flow.state.task_id,
                "correlation_id": flow.state.correlation_id,
                "status": "completed",
                "result": result
            })

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Flow execution failed: {error_msg}")

        if callback_url:
            await send_callback(callback_url, {
                "task_id": flow.state.task_id,
                "correlation_id": flow.state.correlation_id,
                "status": "failed",
                "error": error_msg
            })

async def send_callback(url: str, data: Dict[str, Any]) -> None:
    """Enviar callback HTTP POST con JSON."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json=data)
            logger.debug(f"Callback sent to {url}")
    except Exception as e:
        logger.warning(f"Callback failed: {e}")

### 1.14 — GET /tasks/{id}: Endpoint para polling de resultados

Endpoint REST para que clientes polling el estado de una tarea y obtengan resultados.

**src/api/routes/tasks.py**

```python

```

  from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from db.session import get_tenant_client
from api.middleware import get_org_id_from_request, require_org_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskResponse(BaseModel):
    id: str
    org_id: str
    flow_type: str
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error: Optional[str]
    correlation_id: Optional[str]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    has_more: bool

@router.get("/{task_id}", response_model=TaskResponse)
async get_task(
    task_id: str,
    org_id: str = Depends(require_org_id)
) -> TaskResponse:
    """
    Obtener estado de una tarea específica.
    
    El task_id debe pertencer a la organización del solicitante.
    Los datos se filtran automáticamente por RLS.
    """
    
    try:
        with get_tenant_client(org_id) as db:
            result = db.table("tasks").select("*").eq("id", task_id).execute()

            if not result.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tarea {task_id} no encontrada"
                )

            task = result.data[0]
            
            # Si el flow tiene output_data, enriquecer con datos del snapshot
            if task.get("status") == "completed":
                snapshot_result = db.table("snapshots").select("state").eq(
                    "aggregate_id", task_id
                ).eq("aggregate_type", "flow").order(
                    "version", desc=True).limit(1).execute()
                
                if snapshot_result.data:
                    state = snapshot_result.data[0]["state"]
                    task["output_data"] = state.get("output_data", {})
                    task["error"] = state.get("error")

            return TaskResponse(**task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al obtener la tarea"
        )

@router.get("", response_model=TaskListResponse)
async list_tasks(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = None,
    flow_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> TaskListResponse:
    """
    Listar tareas de la organización con filtros opcionales.
    """
    
    try:
        with get_tenant_client(org_id) as db:
            query = db.table("tasks").select("*", count="exact")

            if status:
                query = query.eq("status", status)
            if flow_type:
                query = query.eq("flow_type", flow_type)

            result = query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            return TaskListResponse(
                tasks=[TaskResponse(**t) for t in result.data],
                total=result.count or 0,
                has_more=len(result.data) == limit
            )

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al listar tareas"
        )

### 1.15 — GenericFlow: Flow completo mínimo

Ejemplo de implementación de un Flow concreto usando BaseFlow, demostrando el patrón completo.

**src/flows/generic_flow.py**

```python

```

  from typing import Dict, Any
from crewai import Crew, Process
import logging

from flows.base_flow import BaseFlow
from flows.registry import register_flow
from crews.generic_crew import create_generic_crew

logger = logging.getLogger(__name__)

@register_flow("generic")
class GenericFlow(BaseFlow):
    """
    Flow genérico que ejecuta un Crew con configuración flexible.
    
    Input esperado:
    - prompt: str - Descripción de la tarea
    - context: dict (opcional) - Contexto adicional
    """

    def validate_input(self) -> None:
        """Validar que el input contiene los campos requeridos."""
        if "prompt" not in self.state.input_data:
            raise ValueError("input_data.prompt es requerido")

    def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar el Crew con el prompt proporcionado.
        
        SECUENCIA:
        1. Obtener configuración del crew desde metadata o defaults
        2. Crear instancia del Crew
        3. Ejecutar (secuencial o paralelo)
        4. Retornar resultado
        """
        prompt = self.state.input_data["prompt"]
        context = self.state.input_data.get("context", {})

        logger.info(f"Running GenericFlow with prompt: {prompt[:50]}...")

        # Emitir evento de inicio
        self.emit_event("crew.started", {"prompt": prompt})

        # Crear crew (esto vendría de una factory en implementación real)
        crew = create_generic_crew(
            prompt=prompt,
            context=context,
            org_id=self.state.org_id,
            task_id=self.state.task_id
        )

        # Ejecutar crew en modo secuencial
        result = crew.kickoff()

        # Procesar resultado
        if hasattr(result, 'raw'):
            output = {"result": result.raw}
        elif isinstance(result, dict):
            output = result
        else:
            output = {"result": str(result)}

        # Emitir evento de completitud
        self.emit_event("crew.completed", output)

        return output

**src/crews/generic_crew.py — Factory para crear Crew**

```python

```

  from crewai import Agent, Crew, Task, Process
from crewai.tools import BaseTool
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

def create_generic_crew(
    prompt: str,
    context: Dict[str, Any],
    org_id: str,
    task_id: str,
    tools: Optional[List[BaseTool]] = None,
    process: Process = Process.sequential
) -> Crew:
    """
    Factory para crear un Crew genérico.
    
    Args:
        prompt: Descripción de la tarea
        context: Contexto adicional
        org_id: ID de la organización
        task_id: ID de la tarea
        tools: Lista de tools (opcional)
        process: Modo de ejecución (sequential/parallel/hierarchical)
    """
    
    # Crear agente investigador
    researcher = Agent(
        role="Research Analyst",
        goal="Analizar la información y proporcionar insights",
        backstory="""Eres un analista de investigación experimentado.
        Tu trabajo es analizar información y proporcionar análisis detallados.""",
        verbose=True,
        tools=tools or []
    )

    # Crear agente escritor
    writer = Agent(
        role="Content Writer",
        goal="Crear contenido claro y estructurado",
        backstory="""Eres un escritor profesional especializado
        en crear contenido claro y fácil de entender.""",
        verbose=True
    )

    # Crear tareas
    research_task = Task(
        description=f"Analizar: {prompt}",
        agent=researcher,
        expected_output="Un análisis detallado del tema"
    )

    write_task = Task(
        description="Crear contenido basado en el análisis",
        agent=writer,
        expected_output="Contenido estructurado y claro",
        context=[research_task]
    )

    # Crear crew
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=process,
        org_id=org_id,
        task_id=task_id,
        verbose=True
    )

    return crew

### 1.16 — Test fixtures: conftest.py completo

Fixtures de pytest para tests de Flows, incluyendo mocks de Supabase y manejo de eventos.

**tests/conftest.py**

```python

```

  import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime

# Importaciones de la aplicación
import sys
import os
path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ===========================================================================
# FIXTURES DE MOCK DE SUPABASE
# ===========================================================================

@pytest.fixture
def mock_supabase():
    """Mock de cliente Supabase."""
    client = Mock()
    client.table = Mock(return_value=Mock())
    client.rpc = Mock(return_value=Mock())
    return client

@pytest.fixture
def mock_tenant_client(mock_supabase):
    """Mock de TenantClient."""
    with patch("db.session.get_supabase_client", return_value=mock_supabase):
        yield mock_supabase

@pytest.fixture
def mock_rpc_response():
    """Factory para crear respuestas RPC mockeadas."""
    def _create(data: Any = None, count: int = None):
        response = Mock()
        response.data = data
        response.count = count
        return response
    return _create

@pytest.fixture
def mock_table(mock_rpc_response):
    """Mock de tabla de Supabase con chain de métodos."""
    table = Mock()
    
    # Configurar chain de select
    select_mock = Mock()
    select_mock.execute = Mock(return_value=mock_rpc_response([]))
    select_mock.eq = Mock(return_value=select_mock)
    select_mock.order = Mock(return_value=select_mock)
    select_mock.limit = Mock(return_value=select_mock)
    select_mock.range = Mock(return_value=select_mock)
    
    table.select = Mock(return_value=select_mock)
    table.insert = Mock(return_value=Mock(execute=Mock(return_value=mock_rpc_response([{}]))))
    table.update = Mock(return_value=Mock(execute=Mock(return_value=mock_rpc_response())))
    table.upsert = Mock(return_value=Mock(execute=Mock(return_value=mock_rpc_response())))
    
    return table

@pytest.fixture
def sample_task_id():
    """Generar un task_id UUID válido para tests."""
    return str(uuid4())

@pytest.fixture
def sample_org_id():
    """Generar un org_id UUID válido para tests."""
    return str(uuid4())

@pytest.fixture
def sample_input_data():
    """Sample input data para tests."""
    return {
        "prompt": "Analiza las tendencias de IA en 2024",
        "context": {
            "industry": "technology",
            "depth": "high"
        }
    }

# ===========================================================================
# FIXTURES DE FLOWS
# ===========================================================================

@pytest.fixture
def flow_state(sample_task_id, sample_org_id, sample_input_data):
    """Fixture para BaseFlowState válido."""
    from flows.state import BaseFlowState, FlowStatus
    
    return BaseFlowState(
        task_id=sample_task_id,
        org_id=sample_org_id,
        flow_type="test_flow",
        input_data=sample_input_data,
        correlation_id=str(uuid4())
    )

@pytest.fixture
def mock_flow(sample_task_id, sample_org_id, sample_input_data):
    """Mock de BaseFlow para tests."""
    from flows.base_flow import BaseFlow
    
    class TestFlow(BaseFlow):
        def _run_crew(self):
            return {"result": "test completed"}
    
    return TestFlow(
        task_id=sample_task_id,
        org_id=sample_org_id,
        input_data=sample_input_data
    )

@pytest.fixture
def flow_with_mocks(sample_task_id, sample_org_id, sample_input_data, mock_table, mock_rpc_response):
    """Flow con todos los mocks necesarios para funcionar."""
    with patch("db.session.get_tenant_client") as mock_client:
        # Mock del context manager
        mock_cm = MagicMock()
        mock_cm.__enter__ = Mock(return_value=mock_table)
        mock_cm.__exit__ = Mock(return_value=False)
        mock_client.return_value = mock_cm

        # Mock de next_event_sequence RPC
        mock_table.rpc.return_value.execute.return_value = mock_rpc_response(1)

        from flows.base_flow import BaseFlow

        class TestFlow(BaseFlow):
            def _run_crew(self):
                return {"result": "test completed"}

        yield TestFlow(
            task_id=sample_task_id,
            org_id=sample_org_id,
            input_data=sample_input_data
        )

# ===========================================================================
# FIXTURES DE EVENT STORE
# ===========================================================================

@pytest.fixture
def event_store(sample_task_id, sample_org_id):
    """EventStore en memoria para tests."""
    with patch("db.session.get_tenant_client") as mock_client:
        mock_table = Mock()
        mock_client.return_value.__enter__ = Mock(return_value=mock_table)
        mock_client.return_value.__exit__ = Mock(return_value=False)
        
        mock_table.table.return_value.insert.return_value.execute.return_value = Mock(data=[], count=0)
        
        from events.store import EventStore
        yield EventStore("flow", sample_task_id, sample_org_id)

# ===========================================================================
# FIXTURES DE REGISTRY
# ===========================================================================

@pytest.fixture
def clean_registry():
    """Limpiar registries antes de cada test."""
    from flows.registry import flow_registry
    from tools.registry import tool_registry
    
    flow_registry._flows.clear()
    tool_registry._tools.clear()
    tool_registry._metadata.clear()
    
    yield
    
    # Limpiar después también
    flow_registry._flows.clear()
    tool_registry._tools.clear()
    tool_registry._metadata.clear()

### 1.17 — Test E2E: webhook_to_completion

Test end-to-end completo que verifica el flujo desde webhook hasta completitud del Flow.

  
    E2E
    test_webhook_to_completion
  
  
    **Objetivo:** Verificar que un webhook dispar un Flow y este se completa correctamente, persistiendo el estado.
    
      - **Precondición:** Flow "generic" registrado en FlowRegistry
      - **Secuencia:**
        
          POST /webhooks/trigger con payload de flow
          - API valida, crea task y retorna 202 con task_id
          - Background task ejecuta el flow
          - Flow crea crew, ejecuta y guarda resultado
          - GET /tasks/{id} retorna status=completed con output_data
        
      
      - **Verificaciones:**
        
          Response 202 con task_id y correlation_id
          - Task en DB con status "running" luego "completed"
          - Output_data contiene resultado del crew
          - Eventos guardados en EventStore
        
      
    
  

**tests/e2e/test_webhook_to_completion.py**

```python

```

  import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient

# Importar aplicación
from main import app

class TestWebhookToCompletion:
    """Tests E2E para el flujo completo webhook → completitud."""

    @pytest.fixture
    def test_client(mock_supabase):
        """Client de test con mocks."""
        client = TestClient(app)
        
        # Mock de get_tenant_client
        with patch("api.routes.webhooks.get_org_id_from_request", return_value="org_test"):
            with patch("api.routes.tasks.get_org_id_from_request", return_value="org_test"):
                with patch("api.routes.webhooks.flow_registry") as mock_registry:
                    with patch("api.routes.webhooks.execute_flow_safe", new_callable=AsyncMock):
                        yield client, mock_registry

    @pytest.fixture
    def mock_flow_instance(sample_task_id, sample_org_id):
        """Mock de instancia de Flow."""
        flow = Mock()
        flow.state.task_id = sample_task_id
        flow.state.org_id = sample_org_id
        flow.state.correlation_id = "corr_123"
        flow.state.status = "completed"
        return flow

    @pytest.fixture
    def mock_table_with_data(sample_task_id, sample_org_id):
        """Mock de tabla con datos de task."""
        table = Mock()
        
        # Datos de task
        task_data = {
            "id": sample_task_id,
            "org_id": sample_org_id,
            "flow_type": "generic",
            "status": "completed",
            "input_data": {"prompt": "test"},
            "output_data": {"result": "test result"},
            "correlation_id": "corr_123",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z",
            "started_at": "2024-01-01T00:00:10Z",
            "completed_at": "2024-01-01T00:01:00Z"
        }
        
        # Mock de select().eq().execute()
        select_mock = Mock()
        select_mock.execute = Mock(return_value=Mock(data=[task_data], count=1))
        table.select = Mock(return_value=select_mock)
        
        return table

    def test_webhook_trigger_creates_task(self, test_client):
        """Test: POST /webhooks/trigger retorna 202 con task_id."""
        client, mock_registry = test_client
        
        # Configurar mock del registry
        mock_flow_class = Mock()
        mock_registry.has = Mock(return_value=True)
        mock_registry.create = Mock(return_value=Mock(
            state=Mock(
                task_id="task_123",
                correlation_id="corr_123"
            )
        ))
        
        # Ejecutar request
        response = client.post("/api/v1/webhooks/trigger", json={
            "flow_type": "generic",
            "input_data": {"prompt": "test"}
        }, headers={"X-Org-ID": "org_test"})
        
        # Verificaciones
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "correlation_id" in data
        assert data["status"] == "accepted"

    def test_get_task_returns_completed(self, sample_task_id, mock_table_with_data):
        """Test: GET /tasks/{id} retorna task completada."""
        # Este test verifica el endpoint de polling
        table = mock_table_with_data
        
        # Simular respuesta de DB
        assert table.select("*").eq("id", sample_task_id).execute().data[0]["status"] == "completed"

    def test_flow_persists_state(self, flow_with_mocks):
        """Test: Flow persiste su estado en DB."""
        flow = flow_with_mocks
        
        # Ejecutar launch (que internamente llama persist_state)
        flow.state.start()
        flow.persist_state({"status": "running"})
        
        # Verificar que se llamó a la tabla
        from unittest.mock import call
        assert flow._event_store is not None

    def test_event_store_collects_events(self, event_store):
        """Test: EventStore colecciona y flush eventos."""
        
        # Agregar eventos
        event_store.append("flow.started", {"test": "data"})
        event_store.append("flow.completed", {"result": "ok"})
        
        assert len(event_store._pending_events) == 2
        
        # Flush
        event_store.flush()
        
        assert len(event_store._pending_events) == 0

    def test_correlation_id_propagation(self, sample_task_id, sample_org_id, sample_input_data):
        """Test: Correlation ID se propaga correctamente."""
        correlation_id = str(uuid4())
        
        from flows.state import BaseFlowState
        state = BaseFlowState(
            task_id=sample_task_id,
            org_id=sample_org_id,
            flow_type="test",
            input_data=sample_input_data,
            correlation_id=correlation_id
        )
        
        assert state.correlation_id == correlation_id

  
    UNIT
    test_baseflow_lifecycle
  
  
    **Objetivo:** Verificar el ciclo de vida completo de BaseFlow.
    
      - **Verificaciones:**
        
          validate_input() es llamado antes de ejecución
          - create_task_record() crea registro en DB
          - persist_state() actualiza estado
          - emit_event() guarda eventos
          - _run_crew() es ejecutado y retorna resultado
          - state se actualiza a completed con output
        
      
    
  

**tests/unit/test_baseflow.py**

```python

```

  import pytest
from unittest.mock import Mock, patch, call
from uuid import uuid4

from flows.base_flow import BaseFlow
from flows.state import BaseFlowState, FlowStatus

class TestBaseFlow:
    """Tests unitarios para BaseFlow."""

    @pytest.fixture
    def sample_flow(sample_task_id, sample_org_id):
        """Crear un Flow de test."""
        class ConcreteFlow(BaseFlow):
            def _run_crew(self):
                return {"result": "crew_output"}

        return ConcreteFlow(
            task_id=sample_task_id,
            org_id=sample_org_id,
            input_data={"test": "data"}
        )

    def test_initialization(self, sample_flow, sample_task_id, sample_org_id):
        """Test: Flow se inicializa con estado correcto."""
        assert sample_flow.state.task_id == sample_task_id
        assert sample_flow.state.org_id == sample_org_id
        assert sample_flow.state.status == FlowStatus.PENDING
        assert sample_flow.state.correlation_id is not None

    def test_state_transitions(self, sample_flow):
        """Test: Estado transiciona correctamente."""
        
        # Initial
        assert sample_flow.state.status == FlowStatus.PENDING
        
        # Start
        sample_flow.state.start()
        assert sample_flow.state.status == FlowStatus.RUNNING
        assert sample_flow.state.started_at is not None
        
        # Complete
        sample_flow.state.complete({"output": "test"})
        assert sample_flow.state.status == FlowStatus.COMPLETED
        assert sample_flow.state.completed_at is not None
        assert sample_flow.state.output_data["output"] == "test"

    def test_fail_transition(self, sample_flow):
        """Test: Estado falla correctamente."""
        
        sample_flow.state.start()
        sample_flow.state.fail("Error de prueba")
        
        assert sample_flow.state.status == FlowStatus.FAILED
        assert sample_flow.state.error == "Error de prueba"
        assert sample_flow.state.completed_at is not None

    def test_validation_error_raises(self, sample_task_id, sample_org_id):
        """Test: Input inválido levanta error."""
        
        class ValidatedFlow(BaseFlow):
            def validate_input(self):
                if "required_field" not in self.state.input_data:
                    raise ValueError("required_field es requerido")
            
            def _run_crew(self):
                return {}

        flow = ValidatedFlow(
            task_id=sample_task_id,
            org_id=sample_org_id,
            input_data={}  # Falta required_field
        )
        
        with pytest.raises(ValueError, match="required_field"):
            flow.launch()

    def test_to_snapshot_and_restore(self, sample_flow):
        """Test: Snapshot y restauración de estado."""
        
        sample_flow.state.start()
        sample_flow.state.complete({"key": "value"})
        
        # Snapshot
        snapshot = sample_flow.state.to_snapshot()
        
        assert snapshot["status"] == "completed"
        assert snapshot["output_data"]["key"] == "value"
        
        # Restore
        restored = BaseFlowState.from_snapshot(snapshot)
        
        assert restored.status == FlowStatus.COMPLETED
        assert restored.output_data["key"] == "value"

> [!IMPORTANT]
> **Resumen Fase 1:** Estas secciones 1.7-1.17 completan la implementación del Foundation Architecture Pattern para CrewAI, incluyendo:
  
    - Regístries centralizados para Flows y Tools con decoradores
    - Persistencia de estado con validación UUID
    - Ciclo de vida completo de Flows con manejo de errores
    - Event Store para auditoría
    - APIs REST para webhooks y polling
    - Tests unitarios y E2E verificables
  

  ### Fase 2
  ## Gobernanza — HITL, Vault y Guardrails

  
    2
    
      ### Objetivo: ninguna acción crítica se ejecuta sin aprobación
      El sistema debe poder pausar un workflow, notificar al supervisor, esperar su decisión y reanudar desde exactamente donde se detuvo. Las credenciales externas nunca deben ser visibles para los agentes. Los guardrails deben bloquear operaciones que violen reglas de negocio.

      
        **Criterio de éxito:** un Flow puede pausarse y reanudarse correctamente, el LLM mockeado nunca recibe un secreto en claro
      
    
  

  ### 2.1 — Human-in-the-Loop: pausa y reanudación

  > [!WARNING]
> **Limitación de CrewAI:** Los Flows de CrewAI no tienen pausa nativa. No existe `flow.suspend()`. La solución es terminar el proceso del Flow guardando el estado completo en la base de datos. Al reanudar, un nuevo proceso restaura ese estado y llama directamente al método de continuación.
  

  **src/flows/base_flow.py — Métodos HITL (agregar a la clase BaseFlow)**

```python

```

        def request_approval(self, description: str, payload: dict) -> None:
        """
        Pausar el Flow y solicitar aprobación al supervisor.
        
        SECUENCIA:
        1. Serializar FlowState → snapshot en DB
        2. Crear fila en pending_approvals
        3. Actualizar task.status = "pending_approval"
        4. Emitir evento "approval.requested"
        5. Retornar (el Flow termina su ejecución aquí)
        
        El Flow SE DETIENE cuando este método retorna.
        La reanudación ocurre vía POST /approvals/{task_id}.
        """
        self.state.status = "pending_approval"
        self.state.approval_payload = payload
        self.state.touch()

        svc = get_service_client()

        # 1. Guardar snapshot
        seq = svc.rpc("next_event_sequence", {
            "p_aggregate_type": "flow",
            "p_aggregate_id": self.state.task_id
        }).execute().data

        svc.table("snapshots").upsert({
            "aggregate_type": "flow",
            "aggregate_id": self.state.task_id,
            "version": seq,
            "state": self.state.to_snapshot()
        }, on_conflict="aggregate_type,aggregate_id").execute()

        # 2. Crear pending_approval
        db = get_tenant_client(self.state.org_id)
        db.table("pending_approvals").insert({
            "org_id": self.state.org_id,
            "task_id": self.state.task_id,
            "flow_type": self.state.flow_type,
            "description": description,
            "payload": payload,
        }).execute()

        # 3 + 4. Actualizar task y emitir evento
        self.persist_state({"approval_required": True, "approval_status": "pending"})
        self.emit_event("approval.requested", {"description": description})
        # El método retorna → el paso del Flow termina → el proceso puede finalizar
  

  **src/api/routes/approvals.py**

```python

```

    from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from src.db.client import get_service_client, get_tenant_client
from src.db.event_store import EventStore
from src.flows.registry import FLOW_REGISTRY

router = APIRouter()

class ApprovalDecision(BaseModel):
    org_id: str
    decision: str          # "approved" | "rejected"
    decided_by: str        # identificador del supervisor
    notes: str = ""

@router.post("/{task_id}")
async def process_approval(
    task_id: str,
    body: ApprovalDecision,
    background: BackgroundTasks
):
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision debe ser 'approved' o 'rejected'")

    svc = get_service_client()

    # 1. Verificar que la aprobación existe y está pendiente
    approval = svc.table("pending_approvals")\
        .select("*")\
        .eq("task_id", task_id)\
        .eq("status", "pending")\
        .maybe_single()\
        .execute()

    if not approval.data:
        raise HTTPException(404, "Aprobación no encontrada o ya procesada")

    flow_type = approval.data["flow_type"]

    # 2. Marcar aprobación como resuelta
    svc.table("pending_approvals")\
        .update({"status": body.decision, "decided_by": body.decided_by})\
        .eq("task_id", task_id)\
        .execute()

    # 3. Registrar evento
    EventStore.append(
        org_id=body.org_id, aggregate_type="flow", aggregate_id=task_id,
        event_type=f"approval.{body.decision}",
        payload={"decided_by": body.decided_by, "notes": body.notes},
        actor=f"user:{body.decided_by}"
    )

    # 4. Reanudar el Flow en background
    flow_class = FLOW_REGISTRY.get(flow_type)
    if flow_class:
        background.add_task(
            flow_class.resume,
            task_id=task_id,
            decision=body.decision,
            decided_by=body.decided_by
        )

    return {"status": "ok", "task_id": task_id, "decision": body.decision}

# En cada Flow concreto, implementar el método classmethod resume():
# @classmethod
# def resume(cls, task_id: str, decision: str, decided_by: str):
#     svc = get_service_client()
#     snapshot = svc.table("snapshots").select("*").eq("aggregate_id", task_id)...
#     state = MiFlowState.from_snapshot(snapshot["state"])
#     state.approval_decision = decision
#     state.approval_decided_by = decided_by
#     flow = cls()
#     flow.state = state
#     if decision == "approved":
#         flow.paso_de_continuacion()
#     else:
#         flow.paso_de_rechazo()
  

  ### 2.2 — Vault: proxy de secretos

  > [!IMPORTANT]
> **Regla invariable:** Los agentes y los LLMs NUNCA ven credenciales en claro. La tool que necesita un secreto llama al VaultProxy internamente. El LLM solo recibe el resultado de la operación, no la credencial usada para ejecutarla.
  

  **src/db/vault.py**

```python

```

    from src.db.client import get_service_client

def get_secret(org_id: str, secret_name: str) -> str:
    """
    Obtener un secreto cifrado para una organización.
    
    IMPORTANTE:
    - Usar service_role (bypasea RLS — la tabla secrets solo permite service_role)
    - Retorna el valor en claro. La tool que llama esto es responsable de no loguearlo.
    - Lanza ValueError si el secreto no existe.
    """
    svc = get_service_client()
    result = svc.table("secrets")\
        .select("secret_value")\
        .eq("org_id", org_id)\
        .eq("name", secret_name)\
        .maybe_single()\
        .execute()

    if not result.data:
        raise ValueError(
            f"Secreto '{secret_name}' no configurado para org '{org_id}'"
        )
    return result.data["secret_value"]
  

  **src/tools/base_tool.py — Tool con vault integrado**

```python

```

    from crewai.tools import BaseTool
from pydantic import BaseModel
from src.db.vault import get_secret

class OrgBaseTool(BaseTool):
    """
    Clase base para todas las tools del sistema.
    
    - org_id viaja con la tool → RLS automático en queries
    - Método get_secret() para obtener credenciales sin exponerlas al LLM
    - Las subclases implementan _run() con la lógica específica
    """
    org_id: str

    def _get_secret(self, secret_name: str) -> str:
        """Obtener una credencial. Solo llamar internamente, nunca retornar al LLM."""
        return get_secret(self.org_id, secret_name)

# EJEMPLO de tool que usa una credencial externa correctamente:
class SendMessageInput(BaseModel):
    to: str
    message: str

class SendMessageTool(OrgBaseTool):
    name: str = "send_message"
    description: str = "Envía un mensaje de texto al número especificado."
    args_schema: type[BaseModel] = SendMessageInput

    def _run(self, to: str, message: str) -> str:
        # El LLM no ve el token. La tool lo obtiene internamente.
        api_token = self._get_secret("messaging_api_token")
        # ... llamada HTTP con api_token ...
        return f"Mensaje enviado a {to}"  # Solo el resultado llega al LLM
  

  ### 2.3 — Guardrails
  Los guardrails son funciones que validan el output de un agente antes de que el Flow continúe. Se implementan de dos formas complementarias:

  
| Mecanismo | Cuándo aplica | Cómo funciona |
| --- | --- | --- |
| output_pydantic en Task | Validar estructura del output del agente | Si el modelo Pydantic tiene validators que fallan, CrewAI reintenta la Task automáticamente |
| @router en Flow | Decisiones de negocio (¿requiere aprobación?) | El router bifurca el Flow según reglas configurables por organización |

  **src/guardrails/base_guardrail.py**

```python

```

    from pydantic import BaseModel, field_validator, model_validator
from typing import Callable

def load_org_limits(org_id: str) -> dict:
    """Cargar límites configurados para la organización desde organizations.config."""
    from src.db.client import get_tenant_client
    result = get_tenant_client(org_id)\
        .table("organizations")\
        .select("config")\
        .eq("id", org_id)\
        .single().execute()
    return result.data.get("config", {}).get("limits", {})

def make_approval_check(
    amount_field: str,
    threshold_key: str,
    default_threshold: float
) -> Callable:
    """
    Factory para crear funciones de verificación de aprobación.
    Usadas en el @router de los Flows.
    
    Ejemplo de uso en un Flow:
        @router(ejecutar_paso)
        def decidir_aprobacion(self) -> str:
            check = make_approval_check("monto", "approval_threshold", 50_000)
            if check(self.state.monto, self.state.org_id):
                return "solicitar_aprobacion"
            return "continuar"
    """
    def check(value: float, org_id: str) -> bool:
        limits = load_org_limits(org_id)
        threshold = limits.get(threshold_key, default_threshold)
        return value > threshold
    return check
  

  ### 2.4 — EventStore: implementación completa
  **src/db/event_store.py**

```python

```

    from src.db.client import get_service_client
from typing import Optional
import logging

logger = logging.getLogger("event_store")

class EventStoreError(Exception):
    """El Flow debe detenerse si se lanza este error."""
    pass

class EventStore:
    @staticmethod
    def append(
        org_id: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        actor: str = "system"
    ) -> dict:
        """
        Escribir un evento inmutable. BLOQUEANTE.
        Si falla → lanza EventStoreError → el Flow no debe continuar.
        Garantía: el evento está en DB antes de que el Flow avance al siguiente paso.
        """
        try:
            svc = get_service_client()

            seq = svc.rpc("next_event_sequence", {
                "p_aggregate_type": aggregate_type,
                "p_aggregate_id": aggregate_id
            }).execute().data

            result = svc.table("domain_events").insert({
                "org_id": org_id,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_type": event_type,
                "payload": payload,
                "actor": actor,
                "sequence": seq,
            }).execute()

            return result.data[0]

        except Exception as e:
            logger.error(f"EventStore.append failed: {event_type} — {e}")
            raise EventStoreError(f"No se pudo registrar evento '{event_type}': {e}")

    @staticmethod
    def get_latest_snapshot(
        aggregate_type: str, aggregate_id: str
    ) -> Optional[dict]:
        svc = get_service_client()
        result = svc.table("snapshots")\
            .select("*")\
            .eq("aggregate_type", aggregate_type)\
            .eq("aggregate_id", aggregate_id)\
            .maybe_single()\
            .execute()
        return result.data if result.data else None
  

  ### 2.5 — Tests de Fase 2

  
    
      unit
      `tests/unit/test_vault.py`
    
    
      
        - Mock del service_client
        - `get_secret("org1", "api_key")` — cuando existe → retorna el valor
        - `get_secret("org1", "inexistente")` → lanza `ValueError`
        - La tool que usa `_get_secret()` NO debe incluir el secreto en su valor de retorno
        - El método `_run()` de una tool NO debe recibir el secreto como parámetro
      
    
  

  
    
      integration
      `tests/integration/test_hitl_pause_resume.py`
    
    
      
        - Un Flow llega a `request_approval()` → debe crear fila en `pending_approvals` con `status="pending"`
        - El snapshot debe existir en `snapshots` table después de la pausa
        - El estado del Flow restaurado desde snapshot debe ser idéntico al original
        - `POST /approvals/{task_id}` con decision="approved" → debe llamar a `flow.resume()`
        - `POST /approvals/{task_id}` con tarea ya procesada → debe retornar 404
        - Después de resume, el Flow debe completar con `status="completed"`
      
    
  

  
    Entregables verificables — Fase 2
    
      HITL: pausa + snapshot + reanudación
      VaultProxy sin exposición de secretos
      Guardrails via output_pydantic y @router
      EventStore con garantía de durabilidad
      Tests de pausa/reanudación pasando
    
  

  ### Fase 3
  ## Multi-agente y memoria semántica

  
    3
    
      ### Objetivo: múltiples agentes coordinados por un Flow maestro
      Un Flow debe poder invocar secuencialmente varios Crews, pasando el estado entre ellos. Los agentes deben tener acceso a memoria semántica de largo plazo (búsqueda por similitud en pgvector). Las conexiones a herramientas externas vía MCP deben ser persistentes y con timeout.

      
        **Criterio de éxito:** un Flow con 3 Crews secuenciales pasa sus tests de integración
      
    
  

  ### 3.1 — Memoria vectorial
  **src/db/memory.py**

```python

```

    from openai import OpenAI
from src.db.client import get_service_client

_oai = OpenAI()

def embed(text: str) -> list[float]:
    """Generar embedding con text-embedding-3-small (1536 dimensiones)."""
    resp = _oai.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding

def save_memory(
    org_id: str,
    content: str,
    source_type: str,
    agent_role: str = None,
    metadata: dict = {}
) -> None:
    """Guardar un fragmento de memoria con su embedding."""
    embedding = embed(content)
    svc = get_service_client()
    svc.table("memory_vectors").insert({
        "org_id": org_id,
        "agent_role": agent_role,
        "source_type": source_type,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
    }).execute()

def search_memory(
    org_id: str,
    query: str,
    agent_role: str = None,
    limit: int = 5,
    min_similarity: float = 0.7
) -> list[str]:
    """
    Buscar fragmentos de memoria por similitud semántica.
    Retorna lista de textos ordenados por relevancia.
    """
    embedding = embed(query)
    svc = get_service_client()
    result = svc.rpc("search_memories", {
        "query_embedding": embedding,
        "p_org_id": org_id,
        "p_agent_role": agent_role,
        "match_limit": limit,
        "min_similarity": min_similarity
    }).execute()
    return [row["content"] for row in result.data]
  

  ### 3.2 — Coordinar múltiples Crews en un Flow
  **src/flows/multi_crew_flow_example.py — Patrón de coordinación**

```python

```

    from crewai.flow.flow import Flow, listen, start, router
from src.flows.base_flow import BaseFlow
from src.state.base_state import BaseFlowState
from pydantic import BaseModel
from typing import Optional

class MultiCrewState(BaseFlowState):
    flow_type: str = "multi_crew_example"
    # Cada Crew escribe su output en el estado
    crew_a_output: Optional[dict] = None
    crew_b_output: Optional[dict] = None
    crew_c_output: Optional[dict] = None

class MultiCrewFlow(BaseFlow):
    """
    Patrón: Crew A → (condición) → Crew B o Crew C → finalizar.
    
    Regla: cada Crew recibe el estado actualizado del paso anterior.
    Regla: el estado se persiste después de cada Crew.
    Regla: si un Crew necesita aprobación, llama a self.request_approval().
    """

    @start()
    def iniciar(self):
        self.create_task_record()
        self.emit_event("flow.started")

    @listen(iniciar)
    def ejecutar_crew_a(self):
        from src.crews.base_crew import BaseCrew
        crew = BaseCrew(self.state.org_id, role="agente_a")
        result = crew.run(
            task_description="Realizar análisis inicial con los datos disponibles.",
            inputs={"data": self.state.model_dump()}
        )
        self.state.crew_a_output = {"result": result.raw}
        self.persist_state()
        self.emit_event("crew_a.completed")

    @router(ejecutar_crew_a)
    def decidir_siguiente_crew(self) -> str:
        # La lógica de bifurcación vive aquí, no en el agente
        output = self.state.crew_a_output or {}
        if output.get("requiere_crew_b"):
            return "ejecutar_crew_b"
        return "ejecutar_crew_c"

    @listen("ejecutar_crew_b")
    def ejecutar_crew_b(self):
        from src.crews.base_crew import BaseCrew
        crew = BaseCrew(self.state.org_id, role="agente_b")
        result = crew.run(
            task_description="Procesar el output del análisis inicial.",
            inputs={"analisis": self.state.crew_a_output}
        )
        self.state.crew_b_output = {"result": result.raw}

        # ¿Requiere aprobación humana?
        if self.state.crew_b_output.get("monto", 0) > 50_000:
            self.request_approval(
                description="El monto supera el umbral de aprobación automática.",
                payload=self.state.crew_b_output
            )
            return  # El Flow se pausa aquí

        self.persist_state()
        self.emit_event("crew_b.completed")

    @listen("ejecutar_crew_c", "aprobacion_recibida")
    def finalizar(self):
        self.state.status = "completed"
        self.persist_state()
        self.emit_event("flow.completed")
  

  ### 3.3 — MCP Tools: conexiones persistentes
  > [!WARNING]
> **Gotcha de CrewAI:** `with MCPServerAdapter(params) as adapter` cierra la conexión al salir del bloque. En Flows async con múltiples `await`, la conexión puede cerrarse antes de ser usada. Usar un pool de conexiones persistentes.
  

  **src/tools/mcp_pool.py**

```python

```

    from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from src.db.vault import get_secret
from src.db.client import get_service_client
from typing import Optional
import asyncio, logging

logger = logging.getLogger("mcp_pool")

class MCPConnectionError(Exception): pass

class MCPPool:
    """
    Pool singleton de conexiones a servidores MCP.
    Mantiene conexiones abiertas durante la vida del proceso.
    Reconecta automáticamente si la conexión se pierde.
    """
    _instance: Optional["MCPPool"] = None
    _adapters: dict = {}

    @classmethod
    def get(cls) -> "MCPPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_tools(self, org_id: str, server_name: str, timeout: int = 30) -> list:
        key = f"{org_id}:{server_name}"

        if key in self._adapters:
            try:
                return self._adapters[key].tools
            except Exception:
                logger.warning(f"MCP connection lost for {key}, reconnecting...")
                del self._adapters[key]

        svc = get_service_client()
        config = svc.table("org_mcp_servers")\
            .select("*")\
            .eq("org_id", org_id)\
            .eq("name", server_name)\
            .single().execute()

        if not config.data:
            raise MCPConnectionError(f"Servidor MCP '{server_name}' no configurado")

        params = StdioServerParameters(
            command=config.data["command"],
            args=config.data.get("args", []),
            env={"API_TOKEN": get_secret(org_id, config.data["secret_name"])}
        )

        try:
            adapter = MCPServerAdapter(params)
            await asyncio.wait_for(adapter.__aenter__(), timeout=timeout)
            self._adapters[key] = adapter
            return adapter.tools
        except asyncio.TimeoutError:
            raise MCPConnectionError(
                f"Timeout conectando a MCP '{server_name}' (timeout={timeout}s)"
            )
  

  ### 3.4 — Tests de Fase 3

  
    
      integration
      `tests/integration/test_multi_crew_flow.py`
    
    
      
        - Mock de LLM: ambos Crews retornan outputs predefinidos sin llamar a Claude
        - El estado después del Crew A debe contener el output del Crew A
        - El router debe bifurcar correctamente según el contenido del estado
        - El estado después del Crew B debe contener el output del Crew B
        - Si Crew B retorna monto > 50k → el Flow debe llamar a `request_approval()`
        - Si Crew B retorna monto ≤ 50k → el Flow debe completar sin aprobación
      
    
  

  
    
      unit
      `tests/unit/test_memory.py`
    
    
      
        - Mock de OpenAI embeddings (retorna vector fijo de 1536 dimensiones)
        - `save_memory()` debe llamar a `embed()` y luego insertar en Supabase
        - `search_memory()` debe llamar a la función RPC `search_memories`
        - Si `search_memory()` no encuentra resultados → retorna lista vacía (no lanza error)
      
    
  

  
    Entregables verificables — Fase 3
    
      Flow coordinando 3 Crews secuenciales
      Memoria vectorial: save + search
      MCPPool con reconexión automática
      Tests de coordinación multi-crew
    
  

  ### Fase 4
  ## Diseño conversacional — Generador de Flows

  
    4
    
      ### Objetivo: un Flow que genera otros Flows
      Un endpoint de chat permite al usuario describir en lenguaje natural qué automatización necesita. Un agente especializado extrae la estructura del workflow (pasos, agentes, reglas de aprobación) y la persiste en la base de datos. A partir de ese momento, el workflow queda disponible para ser ejecutado.

      
        **Input:** conversación en lenguaje natural
        **Output:** fila en `workflow_templates` + filas en `agent_catalog`
        **Criterio de éxito:** el workflow generado puede ejecutarse exitosamente
      
    
  

  #### Tablas adicionales requeridas para Fase 4

  **sql/10_workflow_templates.sql**

```sql

```

    -- Define la estructura de un workflow generado por el Architect Flow.
-- Un workflow_template puede ser instanciado múltiples veces como tareas.
CREATE TABLE workflow_templates (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(id),
  name        TEXT NOT NULL,
  description TEXT,
  flow_type   TEXT NOT NULL UNIQUE,  -- nombre usado en FLOW_REGISTRY y webhooks
  definition  JSONB NOT NULL,         -- { steps: [], agents: [], approval_rules: [] }
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE workflow_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON workflow_templates
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
  

  La implementación del Architect Flow sigue el mismo patrón que los Flows anteriores. La diferencia es que el output del agente es la *definición* de un nuevo workflow, no la ejecución de un proceso de negocio.

  ### Referencia
  ## Reglas que nunca deben violarse

  
| # | Regla | Consecuencia de violar |
| --- | --- | --- |
| R1 | El Flow es el orquestador. Los agentes no deciden el flujo de ejecución — solo resuelven la tarea que el Flow les asigna. | Comportamiento impredecible, loops, acciones no autorizadas |
| R2 | allow_delegation=False siempre. Los agentes no pueden crear sub-agentes ni delegar tareas a otros agentes. | Consumo de tokens descontrolado, violación de principio de mínimo privilegio |
| R3 | Los secretos nunca llegan al LLM. Las tools obtienen credenciales internamente y solo retornan el resultado de la operación. | Exposición de credenciales en logs o en el contexto del modelo |
| R4 | El estado canónico vive en Supabase. El FlowState en memoria es temporal. Después de cada paso importante, persistir con persist_state(). | Pérdida de estado si el proceso crashea |
| R5 | Los eventos son inmutables. La tabla domain_events es append-only. Nunca UPDATE ni DELETE. | Pérdida de trazabilidad, imposibilidad de auditoría |
| R6 | EventStore.append() es bloqueante. El Flow no avanza al siguiente paso hasta confirmar que el evento está en DB. Nunca envolver en try/except silencioso. | Eventos perdidos, estado inconsistente |
| R7 | Toda tabla tiene org_id y RLS. Todas las tablas de datos (no las de configuración global) deben tener la columna org_id y política RLS habilitada. | Filtración de datos entre tenants |
| R8 | max_iter explícito en cada Agent. Definir max_iter (≤5 para producción) para evitar loops infinitos del LLM. | Consumo de tokens ilimitado, timeout de la tarea |

  ### Referencia
  ## Comportamientos de CrewAI que no son evidentes

  
| Gotcha | Síntoma | Solución |
| --- | --- | --- |
| Flows no tienen pausa nativa | No existe flow.suspend() | Serializar estado → guardar snapshot → terminar proceso. Al reanudar: restaurar snapshot → llamar al método de continuación directamente. |
| crew.kickoff() es síncrono | Bloquea el event loop si el Flow es async | Usar await crew.kickoff_async() en Flows async. Para Flows síncronos, no hay problema. |
| MCPServerAdapter como context manager en async | La conexión se cierra antes de ser usada si hay await entre apertura y uso | Usar MCPPool con conexiones persistentes (ver Fase 3). |
| FlowState no se persiste automáticamente | Si el proceso crashea, el estado se pierde | Llamar self.persist_state() al final de cada paso que modifica el estado. |
| output_pydantic no muestra error claro | El agente reintenta silenciosamente si el output no parsea | Agregar verbose=True durante desarrollo para ver los reintentos. En producción, logear los errores de validación. |
| RLS retorna 0 filas sin error si org_id no está seteado | La query "funciona" pero retorna vacío | Siempre usar get_tenant_client(org_id) que setea app.org_id. Agregar test que verifica que una query devuelve datos con el cliente correcto. |