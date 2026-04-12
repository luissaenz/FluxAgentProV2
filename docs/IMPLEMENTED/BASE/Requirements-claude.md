# Plan MVP: Cerrar Features A, B, C, D

## Context

El usuario necesita cerrar el MVP del proyecto FAP (FluxAgent Pro). Ya existe una plataforma de orquestación multi-agente con FastAPI + CrewAI + Supabase + Next.js. Las siguientes features fueron identificadas como gap crítico para el MVP:

- **A**: Visualizar estructura de flujos (steps, agentes, dependencias)
- **B**: Completar panel de detalle de agente con estructura clara
- **C**: Sistema de reportes/salidas (paneles personalizados + páginas web públicas)
- **D**: Agente conversacional analítico que consulta EventStore

**Premisas:**
- No modificar código CrewAI (`src/crews/`, `src/flows/multi_crew_flow.py`)
- Reutilizar patrones existentes (FlowRegistry, DynamicWorkflow, Presentation system)
- Backend FastAPI + Supabase, Frontend Next.js

---

## A — Visualizador de Estructura de Flujos

### Gap
La vista `workflows/[id]` solo muestra JSON raw en CodeBlock. No hay representación visual de steps/agentes.

### Implementación

**1. Nuevo endpoint `GET /workflows/{flow_type}/structure`**

```python
# src/api/routes/workflows.py
@router.get("/{flow_type}/structure")
async def get_workflow_structure(
    flow_type: str,
    org_id: str = Depends(require_org_id)
) -> WorkflowStructureResponse:
```

**Response:**
```json
{
  "flow_type": "preventa_flow",
  "name": "Preventa Bartenders",
  "steps": [
    {
      "id": "step_1",
      "name": "Requerimientos",
      "agent_role": "A1",
      "description": "Registra evento",
      "depends_on": [],
      "requires_approval": false
    },
    {
      "id": "step_2",
      "name": "Clima",
      "agent_role": "A2",
      "description": "Consulta factor climático",
      "depends_on": ["step_1"],
      "requires_approval": false
    }
  ],
  "agents": [
    {"role": "A1", "goal": "...", "tools": ["EscandalloTool"]}
  ]
}
```

**2. Componente `FlowStructureViewer.tsx`**

- Ubicación: `dashboard/components/workflows/FlowStructureViewer.tsx`
- Renderiza steps como nodos conectados
- Muestra agentes por color
- Indica puntos de HITL con borde amarillo
- Usa `reactflow` o CSS grid simple con conectores

**3. Modificar `workflows/[id]/page.tsx`**

- Reemplazar CodeBlock de `definition` por `FlowStructureViewer`
- Mantener opción de ver JSON raw (collapsible)

---

## B — Detalle de Agente Estructurado

### Gap
- Panel actual muestra tokens y tareas, pero sin descripción coloquial por aspecto
- No hay historial de actividad detallado
- No hay columna `assigned_agent` real (solo `assigned_agent_role` como TEXT)

### Implementación

**1. Endpoint mejorado `GET /agents/{agent_id}/detail`**

Extender el response actual para incluir:

```typescript
interface AgentDetailExtended {
  // Ya existe
  agent: Agent
  metrics: { total_tokens, tasks_by_status, recent_tasks }

  // NUEVO
  soul_definition: {
    role_description: string      // "El agente de requerimientos valida..."
    goal_colloquial: string       // "Su objetivo es registrar el evento..."
    behaviour_notes: string       // "Cuando el clima excede 30°..."
    interaction_pattern: string   // "Se comunica con A2 passando datos..."
  }
  activity_log: ActivityEntry[]    // últimas 100 operaciones
  skills_breakdown: Skill[]       // herramientas con descripción
}
```

**2. Hook `useAgentDetailExtended.ts`**

- Nuevo hook que extienda `useAgentDetail` existente
- URL: `GET /agents/{id}/detail?extended=true`

**3. Componentes UI**

- `AgentSoulCard.tsx` — Muestra la definición coloquial del SOUL
- `AgentActivityTimeline.tsx` — Timeline de actividad del agente
- `AgentSkillsList.tsx` — Lista de skills con descripciones

**4. Modificar página `agents/[id]/page.tsx`**

- Agregar tabs: Overview | SOUL | Actividad | Skills
- Overview: métricas actuales
- SOUL: descripción coloquial de cada aspecto
- Actividad: timeline con ultimas operaciones
- Skills: herramientas con descripciones

**5. Tabla `agent_activity_log` (nueva migración)**

```sql
CREATE TABLE agent_activity_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES organizations(id),
  agent_role      TEXT NOT NULL,
  task_id         UUID REFERENCES tasks(id),
  event_type      TEXT NOT NULL,  -- 'task_started', 'task_completed', 'task_failed', 'approval_requested'
  payload         JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

**Nota:** Esta tabla se llena desde `base_flow.py` cuando persiste estado, emitiendo eventos de agente.

---

## C — Sistema de Reportes y Salidas

### Gap
- No hay sistema de páginas públicas
- No hay generación de reportes configurables
- `flow_presentations` existe pero no tiene API de edición

### Implementación - C1: Paneles Personalizados

**1. Tabla `report_configs`**

```sql
CREATE TABLE report_configs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES organizations(id),
  name            TEXT NOT NULL,
  description     TEXT,
  data_sources    JSONB NOT NULL,  -- { "tasks": true, "events": true, "agents": ["A1", "A2"] }
  visualization   TEXT DEFAULT 'table',  -- table | cards | chart
  filters         JSONB DEFAULT '{}',
  created_by      TEXT,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**2. Endpoint `GET /reports/{report_id}/data`**

```python
@router.get("/reports/{report_id}/data")
async def get_report_data(
    report_id: str,
    org_id: str = Depends(require_org_id)
) -> ReportDataResponse:
    # Consulta tasks/events según data_sources
    # Filtra por rango de fechas, status, etc.
    # Retorna datos agregados
```

**3. Componente `CustomReportBuilder.tsx`**

- Selector de data sources (tasks, events, agents)
- Filtros configurables
- Preview en tiempo real
- Guardar/editar reportes

---

### Implementación - C2: Páginas Web Públicas

**1. Tabla `public_pages`**

```sql
CREATE TABLE public_pages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES organizations(id),
  slug            TEXT NOT NULL,  -- URL única: /pub/{slug}
  title           TEXT,
  template_config JSONB NOT NULL,  -- { "layout": "form", "fields": [...] }
  output_data     JSONB,           -- datos generados por el agente
  flow_type       TEXT,            -- flow que genera este output
  task_id         UUID REFERENCES tasks(id),
  expires_at      TIMESTAMPTZ,     -- opcional, null = nunca expira
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, slug)
);
```

**2. Template System**

```typescript
interface PageTemplate {
  layout: 'form' | 'report' | 'invoice' | 'custom'
  sections: TemplateSection[]
}

interface TemplateSection {
  id: string
  type: 'header' | 'fields' | 'table' | 'image' | 'html'
  config: Record<string, any>  // field refs, styles, etc.
}
```

**3. Endpoint para que agente genere página**

```python
@router.post("/public-pages")
async def create_public_page(
    page: PublicPageCreate,
    org_id: str = Depends(require_org_id)
) -> PublicPageResponse:
    # El flow llama este endpoint con output_data + template_config
```

**4. Routing público**

```python
# En main.py - ruta SIN auth para páginas públicas
@app.get("/pub/{slug}")
async def get_public_page(slug: str, request: Request) -> HTMLResponse:
    # Consulta public_pages por slug
    # Renderiza template con output_data
    # Retorna HTML
```

**5. Componente UI `PublicPageGenerator.tsx`**

- Form para definir template
- Preview del output
- URL pública generada

---

## D — Agente Conversacional Analítico

### Gap
- ArchitectFlow solo genera workflows, no analiza datos
- No existe "AnalystFlow"
- No hay endpoint que consulte EventStore para análisis

### Implementación

**1. Nuevo `AnalystFlow`**

```python
# src/flows/analyst_flow.py
@register_flow("analyst_flow")
class AnalystFlow(BaseFlow):
    """
    Agente conversacional analítico.
    Consulta EventStore para responder preguntas,
    generar reportes y crear visualizaciones.
    """

    async def execute(self, input_data: dict) -> dict:
        query = input_data.get("query", "")
        org_id = self.org_id

        # Consulta EventStore
        events = self._query_events(org_id, query)
        tasks = self._query_tasks(org_id, query)

        # Genera análisis con LLM
        analysis = await self._generate_analysis(query, events, tasks)

        return {
            "answer": analysis,
            "data": {
                "events_count": len(events),
                "tasks_count": len(tasks),
                "summary": self._summarize(events, tasks)
            },
            "visualizations": self._suggest_charts(events, tasks)
        }
```

**2. Métodos de consulta (solo-lectura EventStore)**

```python
def _query_events(self, org_id: str, query: str) -> list:
    # Busca en domain_events por similarity semántica
    # o por filtros explícitos (flow_type, date_range, etc.)

def _query_tasks(self, org_id: str, query: str) -> list:
    # Consulta tasks con filtros

def _generate_analysis(self, query: str, events: list, tasks: list) -> str:
    # Usa LLM para generar respuesta en lenguaje natural
    # a partir de los datos

def _summarize(self, events: list, tasks: list) -> dict:
    # Agregaciones: total tasks, by_status, by_flow_type
    # Tokens promedio, duración promedio, etc.
```

**3. Endpoint `POST /chat/analyst`**

```python
@router.post("/chat/analyst")
async def analyst_chat(
    message: AnalystMessage,
    org_id: str = Depends(require_org_id)
) -> AnalystResponse:
    flow = AnalystFlow(org_id=org_id, user_id=message.user_id)
    result = await flow.execute({"query": message.message})
    return result
```

**4. Tabla `analyst_conversations` (nueva)**

```sql
CREATE TABLE analyst_conversations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES organizations(id),
  user_id         TEXT,
  messages        JSONB DEFAULT '[]',  -- [{role, content, timestamp}]
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**5. Hook `useAnalyst.ts`**

```typescript
// dashboard/hooks/useAnalyst.ts
export function useAnalyst() {
  const sendMessage = async (message: string) => {
    const response = await api.post('/chat/analyst', { message })
    return response
  }
  return { sendMessage }
}
```

**6. Página `dashboard/app/(app)/analyst/page.tsx`**

- Chat UI con input y respuestas
- Muestra datos generados (summary, charts sugeridos)
- Historial de conversación

---

## Orden de Implementación Sugerido

| # | Feature | Razón |
|---|---------|-------|
| 1 | **D - Agente Analítico** | Usa infraestructura existente, implementa patrón Architect ya conocido |
| 2 | **B - Detalle Agente** | Ya hay base, solo expandir con soul_definition y activity_log |
| 3 | **A - Ver Flujos** | Complementa B con visión macro |
| 4 | **C2 - Páginas Públicas** | Feature diferenciadora, independiente |
| 5 | **C1 - Paneles Personalizados** | Más complejo, requiere schema nuevo |

---

## Archivos Críticos a Modificar

### Backend
- `src/api/routes/workflows.py` — Agregar endpoint structure
- `src/api/routes/agents.py` — Extender detail response
- `src/api/routes/chat.py` — Agregar analyst endpoint
- `src/flows/analyst_flow.py` — NUEVO
- `src/api/main.py` — Registrar rutas

### Frontend
- `dashboard/app/(app)/workflows/[id]/page.tsx` — Integrar FlowStructureViewer
- `dashboard/app/(app)/agents/[id]/page.tsx` — Nuevos tabs
- `dashboard/app/(app)/analyst/page.tsx` — NUEVO
- `dashboard/components/workflows/FlowStructureViewer.tsx` — NUEVO
- `dashboard/components/agents/AgentSoulCard.tsx` — NUEVO
- `dashboard/hooks/useAnalyst.ts` — NUEVO

### Migraciones SQL
- `supabase/migrations/019_agent_activity_log.sql` — Tabla activity log
- `supabase/migrations/020_report_configs.sql` — Tabla reportes
- `supabase/migrations/021_public_pages.sql` — Tabla páginas públicas
- `supabase/migrations/022_analyst_conversations.sql` — Tabla conversaciones analyst

---

## Verificación

### Feature A
1. Ir a `/workflows/preventa_flow`
2. Ver nodes conectados (Requerimientos → Clima → Escandallo → Cotización)
3. Ver puntos HITL marcados en amarillo

### Feature B
1. Ir a `/agents/{id}`
2. Ver tabs: Overview, SOUL (coloquial), Actividad, Skills
3. Ver timeline de actividad con últimos eventos

### Feature C2
1. Ejecutar flow que genere output
2. Llamar `POST /public-pages` con template
3. Acceder a `/pub/{slug}` sin auth y ver página renderizada

### Feature D
1. Ir a `/analyst`
2. Preguntar: "¿Cuántas tareas completadas tuve esta semana?"
3. Ver respuesta en lenguaje natural + datos de resumen
