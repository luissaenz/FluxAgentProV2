### Fase 1 — Motor Base
  ## Visión general y objetivo
  
    Este documento contiene la especificación definitiva para implementar la Fase 1 del sistema de orquestación de agentes IA. Al completar esta fase, el sistema será capaz de recibir un evento externo, ejecutar un Flow de CrewAI, persistir el estado en Supabase, y devolver el resultado.
  

  
    1
    
      ### Sistema funcional de extremo a extremo
      Al terminar esta fase el sistema puede: recibir un evento externo vía `POST /webhooks/trigger`, instanciar el Flow correcto desde el registry, ejecutar un Crew de CrewAI, persistir el estado en Supabase, y exponer el resultado vía `GET /tasks/{task_id}`. Sin HITL, sin vault de secretos, sin memoria vectorial.

      
        **Criterio:** `pytest tests/` pasa al 100% con Supabase y LLM mockeados
        **Entregable:** POST /webhooks/trigger → 202 → GET /tasks/{id} → status: completed
      
    
  

  > [!IMPORTANT]
> **Regla central:** El Flow es el orquestador. Los agentes son ejecutores efímeros. El estado canónico siempre vive en la base de datos, nunca solo en memoria.
  

  ### Criterio de éxito
  ## Qué significa "terminado"

  ### Criterio técnico
  
    - `pytest tests/` pasa al 100% con Supabase y LLM mockeados
    - Cobertura de tests: unitarios, integration y E2E
    - Zero hardcoding de org_id, user_id, credentials
    - RLS habilitado en todas las tablas con políticas basadas en `current_org_id()`
  

  ### Criterio funcional
  
    - Endpoint `POST /webhooks/trigger` acepta `flow_type`, `input_data`, `callback_url` opcional
    - Header `X-Org-ID` es requerido y validado
    - Respuesta `202 Accepted` con `task_id` y `correlation_id`
    - Flow se ejecuta en background, persiste estado en `tasks` y `snapshots`
    - Eventos se escriben en `domain_events` con flush transaccional
    - Endpoint `GET /tasks/{task_id}` retorna estado actual y resultado
  

  ### Entregable verificable
  
    Checklist de verificación
    
      FlowRegistry con decorador @register_flow
      ToolRegistry con metadata de tools
      BaseFlowState con FlowStatus enum
      BaseFlow con ciclo de vida completo
      EventStore con flush transaccional
      TenantClient con RLS por org_id
      POST /webhooks/trigger funcional
      GET /tasks/{id} funcional
      GenericFlow + GenericCrew de ejemplo
      Tests E2E pasando
      Tests unitarios pasando
      Migraciones SQL ejecutadas
    
  

  ### Flujo end-to-end
  ## Secuencia de ejecución

  
    
      1
      Cliente envía `POST /webhooks/trigger` con `flow_type`, `input_data` y header `X-Org-ID`
    
    
      2
      API extrae `org_id`, verifica flow registrado, genera `task_id` UUID, lanza Flow en background → `202` con `task_id`
    
    
      3
      Flow: `validate_input()` → `create_task_record()` → `state.start()` → `persist_state()`
    
    
      4
      Flow: `_run_crew()` → Crew ejecuta agentes → retorna resultado
    
    
      5
      Flow: `state.complete(result)` → `persist_state()` → `emit_event("flow.completed")`
    
    
      6
      Cliente: polling con `GET /tasks/{task_id}` → recibe `status: completed` + resultado
    
  

  > [!NOTE]
> **Importante:** El Flow se ejecuta en background usando `BackgroundTasks` de FastAPI. El cliente recibe respuesta inmediata (`202`) y hace polling para obtener el resultado.
  

  ### Dependencias
  ## Stack tecnológico y versiones

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
openai = "^1.58.0"       # para embeddings (Fase 3)

# Utilidades
python-dotenv = "^1.0.0"
httpx = "^0.28.0"
structlog = "^24.4.0"

[tool.poetry.dev-dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-mock = "^3.14.0"
pytest-cov = "^6.0.0"
httpx = "^0.28.0"        # TestClient de FastAPI
  

  > [!NOTE]
> **Variables de entorno requeridas:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. Crear archivo `.env` en la raíz. Nunca commitear a git.
  

  
| Paquete | Versión | Uso |
| --- | --- | --- |
| crewai | ^0.100.0 | Motor de agentes, Crew, Agent, Task |
| fastapi | ^0.115.0 | API Gateway, routers, BackgroundTasks |
| pydantic | ^2.10.0 | BaseFlowState, modelos request/response |
| supabase | ^2.10.0 | Cliente de base de datos con RLS |
| anthropic | ^0.40.0 | LLM para los agentes |
| httpx | ^0.28.0 | Callback HTTP async, TestClient |
| pytest + pytest-asyncio | ^8.3.0 | Suite de tests |

  ### Organización
  ## Estructura de archivos

  
project/
├── src/
│   ├── flows/
│   │   ├── registry.py          # FlowRegistry + decorador @register_flow
│   │   ├── state.py             # BaseFlowState + FlowStatus enum
│   │   ├── base_flow.py         # BaseFlow lifecycle + @with_error_handling
│   │   └── generic_flow.py      # Primer Flow concreto (demo del stack)
│   │
│   ├── tools/
│   │   ├── registry.py          # ToolRegistry + decorador @register_tool
│   │   └── builtin.py           # Ejemplo de uso del decorador
│   │
│   ├── crews/
│   │   └── generic_crew.py      # Factory create_generic_crew()
│   │
│   ├── events/
│   │   └── store.py             # EventStore: cola + flush transaccional
│   │
│   ├── db/
│   │   ├── session.py           # TenantClient context manager con RLS
│   │   └── vault.py             # Proxy de secretos (Fase 2)
│   │
│   ├── api/
│   │   ├── main.py              # App FastAPI, include_router
│   │   ├── middleware.py        # get_org_id_from_request, require_org_id
│   │   └── routes/
│   │       ├── webhooks.py      # POST /webhooks/trigger
│   │       └── tasks.py         # GET /tasks/{id}, GET /tasks
│   │
│   └── config.py                # Settings con pydantic-settings
│
├── supabase/migrations/
│   └── 001_set_config_rpc.sql   # set_config() + current_org_id() + RLS
│
├── tests/
│   ├── conftest.py              # Fixtures globales
│   ├── unit/
│   │   └── test_baseflow.py     # TestBaseFlow — ciclo de vida
│   └── e2e/
│       └── test_webhook_to_completion.py
│
├── .env.example
├── pyproject.toml
└── README.md

  > [!NOTE]
> **Patrón de registro:** Cada Flow se auto-registra cuando su módulo se importa. En `api/main.py` importar explícitamente `import flows.generic_flow` al arrancar para que el registry esté completo antes del primer request.
  

  ### Base de datos
  ## Migraciones SQL
  Ejecutar en el SQL Editor de Supabase en el orden indicado. La migración `001` debe ir primero porque todas las políticas RLS dependen de `current_org_id()`.

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
  

  > [!NOTE]
> **Tablas principales:** organizations, tasks, domain_events, snapshots. Las migraciones completas se mantienen igual que en la especificación base. Esta migración agrega las funciones RLS que el `TenantClient` necesita.
  

  ### Sección 1.7
  ## FlowRegistry — Registro centralizado de Flows
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
  

  ### Sección 1.8
  ## ToolRegistry — Registro de Tools para Agents
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
  

  ### Sección 1.9
  ## set_config RPC + TenantClient
  Función RPC de Supabase para establecer configuración de tenant en RLS. Permite que las políticas RLS filtren correctamente por organización.

  **src/db/session.py**

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
  

  ### Sección 1.10
  ## BaseFlowState con validadores UUID
  Estado base tipado con validaciones robustas para IDs y manejo de errores.

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
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    correlation_id: Optional[str] = None

    class Config:
        use_enum_values = True
        extra = "allow"

    @field_validator("task_id", "org_id", "user_id", mode="before")
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            if isinstance(v, UUID):
                return str(v)
            UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    @model_validator(mode="after")
    def update_timestamp(self) -> "BaseFlowState":
        self.updated_at = datetime.utcnow()
        return self

    def start(self) -> "BaseFlowState":
        self.status = FlowStatus.RUNNING
        self.started_at = datetime.utcnow()
        return self

    def complete(self, result: Dict[str, Any]) -> "BaseFlowState":
        self.status = FlowStatus.COMPLETED
        self.output_data = result
        self.completed_at = datetime.utcnow()
        return self

    def fail(self, error: str) -> "BaseFlowState":
        self.status = FlowStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        return self

    def await_approval(self) -> "BaseFlowState":
        self.status = FlowStatus.AWAITING_APPROVAL
        return self

    def to_snapshot(self) -> dict:
        return {
            "task_id": self.task_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "state_json": self.model_dump(mode="json")
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "BaseFlowState":
        return cls(**data["state_json"])
  

  ### Sección 1.11
  ## BaseFlow — Ciclo de vida completo
  Clase base abstracta que define el ciclo de vida de un Flow con decorador de manejo de errores.

  **src/flows/base_flow.py**

```python

```

    from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type
from functools import wraps
import logging
import traceback

from .state import BaseFlowState, FlowStatus
from .registry import flow_registry
from ..db.session import get_tenant_client
from ..events.store import EventStore

logger = logging.getLogger(__name__)

def with_error_handling(func):
    """Decorator para manejo centralizado de errores en métodos de Flow."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error en {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            self.state.fail(str(e))
            self.persist_state()
            raise
    return wrapper

class BaseFlow(ABC):
    """
    Clase base abstracta para todos los Flows del sistema.
    Define el ciclo de vida completo: validate → create_task → start → run → complete/fail
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None, **kwargs):
        self.org_id = org_id
        self.user_id = user_id
        self.state: Optional[BaseFlowState] = None
        self.event_store: Optional[EventStore] = None
        self.extra_kwargs = kwargs

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validar datos de entrada del flow."""
        pass

    @abstractmethod
    async def _run_crew(self) -> Dict[str, Any]:
        """Ejecutar el Crew de CrewAI. Implementado por cada flow concreto."""
        pass

    @with_error_handling
    async def execute(self, input_data: Dict[str, Any], correlation_id: Optional[str] = None) -> BaseFlowState:
        """
        Ciclo de vida completo del flow.
        1. Validar input
        2. Crear registro en tasks
        3. Inicializar estado
        4. Ejecutar crew
        5. Completar o fallar
        """
        logger.info(f"Iniciando flow {self.__class__.__name__} para org {self.org_id}")

        # 1. Validar input
        if not self.validate_input(input_data):
            raise ValueError("Input validation failed")

        # 2. Crear registro en tasks
        await self.create_task_record(input_data, correlation_id)

        # 3. Inicializar estado
        self.state.start()
        await self.persist_state()

        # 4. Ejecutar crew
        try:
            result = await self._run_crew()

            # 5. Completar
            self.state.complete(result)
            await self.emit_event("flow.completed", {"result": result})
        except Exception as e:
            logger.error(f"Flow failed: {e}")
            raise

        await self.persist_state()
        return self.state

    @with_error_handling
    async def create_task_record(self, input_data: Dict[str, Any], correlation_id: Optional[str] = None):
        """Crear registro en tabla tasks."""
        from uuid import uuid4
        task_id = str(uuid4())

        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("tasks").insert({
                "id": task_id,
                "org_id": self.org_id,
                "flow_type": self.__class__.__name__,
                "status": "pending",
                "payload": input_data,
                "correlation_id": correlation_id
            }).execute()

        self.state = BaseFlowState(
            task_id=task_id,
            org_id=self.org_id,
            user_id=self.user_id,
            flow_type=self.__class__.__name__,
            input_data=input_data,
            correlation_id=correlation_id
        )

        self.event_store = EventStore(self.org_id, self.user_id)
        await self.emit_event("flow.created", {"input_data": input_data})

    @with_error_handling
    async def persist_state(self):
        """Persistir estado en tabla snapshots."""
        with get_tenant_client(self.org_id, self.user_id) as db:
            snapshot = self.state.to_snapshot()
            db.table("snapshots").upsert(snapshot).execute()

            db.table("tasks").update({
                "status": self.state.status,
                "result": self.state.output_data,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", self.state.task_id).execute()

    @with_error_handling
    async def emit_event(self, event_type: str, payload: Dict[str, Any]):
        """Emitir evento al event store."""
        if self.event_store:
            self.event_store.append(
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                event_type=event_type,
                payload=payload
            )
            await self.event_store.flush()
  

  ### Sección 1.12
  ## EventStore — Event sourcing con flush transaccional
  Cola de eventos inmutables con flush transaccional para garantizar consistencia.

  **src/events/store.py**

```python

```

    from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import logging

from ..db.session import get_tenant_client

logger = logging.getLogger(__name__)

@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    org_id: str = ""
    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    actor: Optional[str] = None
    sequence: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

class EventStore:
    """
    Event Store para domain events.
    Los eventos se encolan en memoria y se flushan transaccionalmente a la BD.
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None):
        self.org_id = org_id
        self.user_id = user_id
        self._queue: List[DomainEvent] = []
        self._sequence = 0

    def append(self, aggregate_type: str, aggregate_id: str, event_type: str, payload: Dict[str, Any]):
        """Agregar evento a la cola."""
        self._sequence += 1
        event = DomainEvent(
            org_id=self.org_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            actor=self.user_id,
            sequence=self._sequence
        )
        self._queue.append(event)
        logger.debug(f"Event appended: {event_type} for {aggregate_type}:{aggregate_id}")

    async def flush(self):
        """Flush de eventos a la base de datos."""
        if not self._queue:
            return

        with get_tenant_client(self.org_id, self.user_id) as db:
            events_data = [
                {
                    "id": event.event_id,
                    "org_id": event.org_id,
                    "aggregate_type": event.aggregate_type,
                    "aggregate_id": event.aggregate_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "actor": event.actor,
                    "sequence": event.sequence
                }
                for event in self._queue
            ]

            db.table("domain_events").insert(events_data).execute()

        logger.info(f"Flushed {len(self._queue)} events to DB")
        self._queue.clear()

    def clear(self):
        """Limpiar cola de eventos."""
        self._queue.clear()
        self._sequence = 0
  

  ### Sección 1.13
  ## Webhook API — POST /webhooks/trigger
  Endpoint principal para iniciar Flows desde eventos externos.

  **src/api/routes/webhooks.py**

```python

```

    from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import uuid4
import logging

from ...flows.registry import flow_registry
from ..middleware import require_org_id

logger = logging.getLogger(__name__)

router = APIRouter()

class WebhookTriggerRequest(BaseModel):
    flow_type: str = Field(..., description="Nombre del flow a ejecutar")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Datos de entrada")
    callback_url: Optional[str] = Field(None, description="URL para callback al completar")

class WebhookTriggerResponse(BaseModel):
    task_id: str
    correlation_id: str
    status: str = "accepted"

@router.post("/trigger", response_model=WebhookTriggerResponse)
async def trigger_webhook(
    request: WebhookTriggerRequest,
    background_tasks: BackgroundTasks,
    org_id: str = require_org_id
):
    """
    Endpoint para iniciar un Flow desde un evento externo.
    
    - Extrae org_id del header X-Org-ID
    - Verifica que el flow_type esté registrado
    - Genera task_id y correlation_id
    - Lanza el Flow en background
    - Responde 202 con task_id
    """
    logger.info(f"Webhook trigger received: flow_type={request.flow_type}, org_id={org_id}")

    # Verificar que el flow existe
    if not flow_registry.has(request.flow_type):
        raise HTTPException(
            status_code=400,
            detail=f"Flow '{request.flow_type}' no encontrado. Disponibles: {flow_registry.list_flows()}"
        )

    correlation_id = str(uuid4())

    # Lanzar flow en background
    background_tasks.add_task(
        execute_flow,
        flow_type=request.flow_type,
        org_id=org_id,
        input_data=request.input_data,
        correlation_id=correlation_id,
        callback_url=request.callback_url
    )

    return WebhookTriggerResponse(
        task_id=str(uuid4()),  # Se asignará realmente en create_task_record
        correlation_id=correlation_id,
        status="accepted"
    )

async def execute_flow(
    flow_type: str,
    org_id: str,
    input_data: Dict[str, Any],
    correlation_id: str,
    callback_url: Optional[str] = None
):
    """Ejecutar flow en background."""
    try:
        flow_class = flow_registry.get(flow_type)
        flow = flow_class(org_id=org_id)
        await flow.execute(input_data, correlation_id)

        # Callback opcional
        if callback_url:
            await send_callback(callback_url, flow.state)
    except Exception as e:
        logger.error(f"Background flow execution failed: {e}")

async def send_callback(callback_url: str, state):
    """Enviar callback HTTP al completar."""
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(callback_url, json={
            "task_id": state.task_id,
            "status": state.status,
            "result": state.output_data
        })
  

  ### Sección 1.14
  ## GET /tasks — Polling y listado
  Endpoints para consultar estado de tareas y listar tareas de una organización.

  **src/api/routes/tasks.py**

```python

```

    from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
import logging

from ..middleware import require_org_id
from ...db.session import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter()

class TaskResponse(BaseModel):
    task_id: str
    org_id: str
    flow_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, org_id: str = require_org_id):
    """
    Obtener estado de una tarea específica.
    Usado para polling después de trigger.
    """
    with get_tenant_client(org_id) as db:
        result = db.table("tasks").select("*").eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data[0]
        return TaskResponse(
            task_id=task["id"],
            org_id=task["org_id"],
            flow_type=task["flow_type"],
            status=task["status"],
            result=task.get("result"),
            error=task.get("error"),
            created_at=task["created_at"],
            updated_at=task["updated_at"]
        )

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    org_id: str = require_org_id,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Listar tareas de una organización con filtro opcional por status.
    """
    with get_tenant_client(org_id) as db:
        query = db.table("tasks").select("*").order("created_at", desc=True).limit(limit)

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return [
            TaskResponse(
                task_id=task["id"],
                org_id=task["org_id"],
                flow_type=task["flow_type"],
                status=task["status"],
                result=task.get("result"),
                error=task.get("error"),
                created_at=task["created_at"],
                updated_at=task["updated_at"]
            )
            for task in result.data
        ]
  

  ### Sección 1.15
  ## GenericFlow + GenericCrew — Flow de ejemplo
  Primer Flow concreto para validar el stack completo. Procesa texto simple usando un Crew de CrewAI.

  **src/flows/generic_flow.py**

```python

```

    from typing import Dict, Any
import logging

from .base_flow import BaseFlow
from .registry import register_flow
from ..crews.generic_crew import create_generic_crew

logger = logging.getLogger(__name__)

@register_flow("generic_flow")
class GenericFlow(BaseFlow):
    """
    Flow de ejemplo para validar el stack completo.
    Procesa texto usando un Crew de CrewAI.
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validar que input_data tenga 'text'."""
        if "text" not in input_data:
            logger.error("Missing 'text' in input_data")
            return False
        if not isinstance(input_data["text"], str):
            logger.error("'text' must be a string")
            return False
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        """Ejecutar el Crew de ejemplo."""
        crew = create_generic_crew()
        result = await crew.kickoff_async(inputs={
            "text": self.state.input_data["text"]
        })
        return {"processed_text": str(result)}
  

  **src/crews/generic_crew.py**

```python

```

    from crewai import Agent, Crew, Process, Task
from crewai_tools import BaseTool
from typing import List

def create_generic_crew() -> Crew:
    """
    Factory para crear el Crew de ejemplo.
    En producción, esto cargaría el soul del agent desde la agent_catalog.
    """
    # Agente de ejemplo
    agent = Agent(
        role="Text Processor",
        goal="Process and transform text according to user requirements",
        backstory="You are an expert text processor with attention to detail.",
        verbose=True,
        allow_delegation=False
    )

    # Tarea de ejemplo
    task = Task(
        description="Process the following text: {text}",
        expected_output="Processed text with transformations applied",
        agent=agent
    )

    # Crew
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    return crew
  

  ### Sección 1.16
  ## conftest.py — Fixtures para tests
  Fixtures globales para mocks de Supabase, flows, events y registries.

  **tests/conftest.py**

```python

```

    import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

@pytest.fixture
def mock_supabase_client():
    """Mock del cliente de Supabase."""
    client = MagicMock()
    client.table = MagicMock()
    client.rpc = MagicMock()
    return client

@pytest.fixture
def mock_tenant_client(mock_supabase_client):
    """Mock del TenantClient con context manager."""
    with patch("src.db.session.get_tenant_client") as mock_get:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_supabase_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get.return_value = mock_client
        yield mock_get

@pytest.fixture
def mock_flow_registry():
    """Mock del FlowRegistry."""
    with patch("src.flows.registry.flow_registry") as mock_registry:
        mock_registry.has = MagicMock(return_value=True)
        mock_registry.get = MagicMock()
        yield mock_registry

@pytest.fixture
def mock_event_store():
    """Mock del EventStore."""
    with patch("src.events.store.EventStore") as MockEventStore:
        mock_store = AsyncMock()
        mock_store.append = MagicMock()
        mock_store.flush = AsyncMock()
        MockEventStore.return_value = mock_store
        yield MockEventStore

@pytest.fixture
def sample_org_id():
    return str(uuid4())

@pytest.fixture
def sample_user_id():
    return str(uuid4())

@pytest.fixture
def sample_input_data():
    return {"text": "Hello, World!"}
  

  ### Sección 1.17
  ## Test E2E — Webhook a completitud
  Test end-to-end que verifica el flujo completo: POST /webhooks/trigger → GET /tasks/{id} → status: completed

  
    
      E2E
      test_webhook_to_completion.py
    
    
      **Qué testear:**
      
        - POST /webhooks/trigger con flow_type válido retorna 202 con task_id
        - Flow se ejecuta en background y persiste estado
        - GET /tasks/{task_id} retorna status: completed con resultado
        - Eventos se escriben en domain_events
      
    
  

  **tests/e2e/test_webhook_to_completion.py**

```python

```

    import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.api.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_webhook_to_completion(
    mock_tenant_client,
    mock_flow_registry,
    mock_event_store,
    sample_org_id
):
    """
    Test E2E: POST /webhooks/trigger → GET /tasks/{id} → completed
    """
    # Mock del flow
    mock_flow = AsyncMock()
    mock_flow.state.task_id = "test-task-id"
    mock_flow.state.status = "completed"
    mock_flow.state.output_data = {"processed_text": "Processed: Hello, World!"}
    mock_flow_registry.get.return_value = lambda **kwargs: mock_flow

    # 1. Trigger webhook
    response = client.post(
        "/webhooks/trigger",
        json={
            "flow_type": "generic_flow",
            "input_data": {"text": "Hello, World!"}
        },
        headers={"X-Org-ID": sample_org_id}
    )

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "correlation_id" in data

    # 2. Polling hasta completed
    import time
    for _ in range(10):
        get_response = client.get(
            f"/tasks/{data['task_id']}",
            headers={"X-Org-ID": sample_org_id}
        )
        if get_response.status_code == 200:
            task = get_response.json()
            if task["status"] == "completed":
                break
        time.sleep(0.1)

    assert get_response.status_code == 200
    assert task["status"] == "completed"
    assert task["result"] == {"processed_text": "Processed: Hello, World!"}
  

  ### Tests unitarios
  ## TestBaseFlow — Ciclo de vida
  Tests unitarios del ciclo de vida de BaseFlow: validate, create_task, start, run, complete/fail.

  
    
      UNIT
      test_baseflow.py
    
    
      **Qué testear:**
      
        - validate_input() retorna True/False correctamente
        - create_task_record() crea registro en tasks y emite evento
        - execute() completa el flujo exitosamente
        - execute() maneja errores y llama a state.fail()
      
    
  

  **tests/unit/test_baseflow.py**

```python

```

    import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState, FlowStatus

class TestFlow(BaseFlow):
    """Flow de test para validar BaseFlow."""
    def validate_input(self, input_data):
        return "text" in input_data

    async def _run_crew(self):
        return {"result": "success"}

@pytest.mark.asyncio
async def test_validate_input(sample_org_id):
    flow = TestFlow(org_id=sample_org_id)
    assert flow.validate_input({"text": "hello"}) is True
    assert flow.validate_input({}) is False

@pytest.mark.asyncio
async def test_execute_success(
    mock_tenant_client,
    mock_event_store,
    sample_org_id
):
    flow = TestFlow(org_id=sample_org_id)
    state = await flow.execute({"text": "hello"})

    assert state.status == FlowStatus.COMPLETED
    assert state.output_data == {"result": "success"}
  

  ### Entrega
  ## Entregables verificables

  
    Archivos a implementar
    
      src/flows/registry.py
      src/flows/state.py
      src/flows/base_flow.py
      src/flows/generic_flow.py
      src/tools/registry.py
      src/tools/builtin.py
      src/crews/generic_crew.py
      src/events/store.py
      src/db/session.py
      src/api/main.py
      src/api/middleware.py
      src/api/routes/webhooks.py
      src/api/routes/tasks.py
      src/config.py
      supabase/migrations/001_set_config_rpc.sql
      tests/conftest.py
      tests/e2e/test_webhook_to_completion.py
      tests/unit/test_baseflow.py
    
  

  > [!IMPORTANT]
> **Criterio de terminación:** Todos los archivos anteriores implementados + `pytest tests/` pasa al 100%.
  

  ### Reglas invariables
  ## Reglas que no se pueden violar

  > [!IMPORTANT]
> **1. Estado canónico en DB:** El estado de un Flow siempre vive en `snapshots` y `tasks`. Nunca solo en memoria.
  

  > [!IMPORTANT]
> **2. RLS obligatorio:** Todas las tablas tienen Row Level Security habilitado. Todas las queries usan `TenantClient` con `org_id`.
  

  > [!IMPORTANT]
> **3. Event sourcing:** Cada cambio de estado emite eventos a `domain_events` con flush transaccional.
  

  > [!IMPORTANT]
> **4. Zero hardcoding:** Nunca hardcodear `org_id`, `user_id`, credentials. Siempre extraer de headers o contexto.
  

  > [!IMPORTANT]
> **5. Tests obligatorios:** Cada archivo nuevo debe tener tests unitarios. Cada feature debe tener tests E2E.
  

  > [!IMPORTANT]
> **6. Flow Registry:** Todos los Flows se registran con `@register_flow`. El API Gateway nunca instancia Flows directamente.