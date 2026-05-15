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