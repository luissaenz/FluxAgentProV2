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
    
  

════════════════════════════════════════════ -->

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