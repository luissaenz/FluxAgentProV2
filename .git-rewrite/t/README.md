# FluxAgentPro V2

**AI Agent Orchestration Engine** — Sistema de orquestación de agentes IA basado en CrewAI, FastAPI y Supabase.

## Estado Actual: Fase 1 — Motor Base (Scaffolding Completo)

La estructura completa de la Fase 1 está implementada. Faltan las dependencias instaladas y la ejecución de tests.

### Arquitectura

```
POST /webhooks/trigger → FlowRegistry → BaseFlow → CrewAI Crew → Supabase (tasks/snapshots/events)
                                                                         ↓
GET /tasks/{task_id}  ← polling ←──────────────────────────────── status: completed
```

### Estructura del Proyecto

```
src/
├── api/
│   ├── main.py              # FastAPI app, routers, health endpoint
│   ├── middleware.py         # X-Org-ID header extraction (require_org_id)
│   └── routes/
│       ├── webhooks.py       # POST /webhooks/trigger → 202 + background exec
│       └── tasks.py          # GET /tasks/{id}, GET /tasks (polling)
├── flows/
│   ├── registry.py           # FlowRegistry + @register_flow decorator
│   ├── state.py              # BaseFlowState (Pydantic) + FlowStatus enum
│   ├── base_flow.py          # BaseFlow lifecycle + @with_error_handling
│   └── generic_flow.py       # Primer Flow concreto (demo del stack)
├── tools/
│   ├── registry.py           # ToolRegistry + @register_tool + ToolMetadata
│   └── builtin.py            # NoopTool de ejemplo
├── crews/
│   └── generic_crew.py       # Factory create_generic_crew() (CrewAI)
├── events/
│   └── store.py              # EventStore: cola in-memory + flush transaccional
├── db/
│   └── session.py            # TenantClient context manager con RLS
└── config.py                 # Settings via pydantic-settings

supabase/migrations/
└── 001_set_config_rpc.sql    # set_config() + current_org_id() + tablas + RLS

tests/
├── conftest.py               # Fixtures globales (mocks Supabase, EventStore)
├── unit/
│   └── test_baseflow.py      # Tests ciclo de vida BaseFlow + BaseFlowState
└── e2e/
    └── test_webhook_to_completion.py  # Tests endpoint webhook + tasks
```

### Stack Tecnológico

| Componente | Paquete | Versión |
|---|---|---|
| API Gateway | FastAPI | ≥0.115 |
| Modelos | Pydantic v2 | ≥2.10 |
| Base de datos | Supabase | ≥2.10 |
| Agentes IA | CrewAI | ≥0.100 (opcional) |
| LLM | Anthropic / OpenAI | ≥0.40 / ≥1.58 |
| Tests | pytest + pytest-asyncio | ≥8.3 |
| Package Manager | uv | ≥0.11 |

### Conceptos Clave

- **Flow como orquestador**: Los Flows orquestan; los agentes ejecutan. El estado canónico vive en DB.
- **RLS Multi-tenant**: `TenantClient` inyecta `app.org_id` via `set_config()` RPC antes de cada query.
- **Event Sourcing**: Cada cambio de estado emite eventos inmutables a `domain_events`.
- **Registry Pattern**: `@register_flow` y `@register_tool` desacoplan el gateway de las implementaciones.

### Pendiente

- [ ] Ejecutar `uv sync --extra dev` para instalar dependencias
- [ ] Ejecutar `uv run pytest tests/` para validar la suite de tests
- [ ] Ejecutar migración SQL en Supabase
- [ ] Instalar CrewAI en Linux/CI (`uv sync --extra crew`)

### Setup Rápido

```bash
# Instalar dependencias (sin CrewAI — para Windows)
uv sync --extra dev

# Instalar todo (Linux/macOS — incluye CrewAI)
uv sync --all-extras

# Ejecutar tests
uv run pytest tests/ -v

# Ejecutar servidor
uv run uvicorn src.api.main:app --reload
```

### Variables de Entorno

Copiar `.env.example` a `.env` y configurar:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## Licencia

Privado.
