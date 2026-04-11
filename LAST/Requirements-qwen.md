# FluxAgentPro V2 — MVP Requirements (Qwen Consolidation)

> **Estado:** Definición inicial
> **Fecha:** 2026-04-11
> **Fuente:** Análisis de Kilo plan + documentación existente FASE1-8
> **Objetivo:** Cerrar gaps existentes y completar funcionalidades MVP pendientes

---

## Estado Actual del Proyecto

### ✅ Lo que YA funciona (implementado y verificado)

| Componente | Archivos clave | Estado |
|------------|---------------|--------|
| Motor base (Fase 1) | `src/api/main.py`, `src/flows/base_flow.py`, `src/flows/registry.py` | ✅ Completo |
| Governance (Fase 2) | `src/api/routes/approvals.py`, `src/db/vault.py` | ✅ Completo |
| Multi-crew (Fase 3) | `src/flows/multi_crew_flow.py`, `src/crews/base_crew.py` | ✅ Completo |
| Token tracking | `src/crews/base_crew.py`, `src/flows/state.py` | ✅ Completo |
| Flow metrics | `src/api/routes/flow_metrics.py`, `dashboard/hooks/useMetrics.ts` | ✅ Completo |
| Dashboard overview | `dashboard/app/(app)/page.tsx`, `dashboard/components/section-cards.tsx` | ✅ Completo |
| Bartenders flows | `src/flows/coctel_flows.py`, schemas en `flows.py` | ✅ Completo |
| Supabase RLS | `src/db/session.py`, migraciones 001-018 | ✅ Completo |
| HITL approvals | `src/api/routes/approvals.py`, `dashboard/app/(app)/approvals/page.tsx` | ✅ Completo |
| Ejecución manual | `src/api/routes/flows.py`, `dashboard/components/flows/RunFlowDialog.tsx` | ✅ Parcial |

### ⚠️ Gaps identificados (pendientes de cierre)

| Gap | Prioridad | Impacto MVP | Documento original |
|-----|-----------|-------------|-------------------|
| Panel de agente incompleto | Alta | Sin visibilidad de tareas/credenciales | FASE8-Week2 |
| Flow visualization | Alta | Contexto limitado para usuarios | FASE7 |
| Custom dashboards | Media | Reportes limitados | FASE5 |
| Conversational agent | Media | Sin analítica conversacional | FASE4 |
| Tickets lifecycle | Media | Sin gestión formal de solicitudes | FASE8-Week2 |
| Execution transcript | Baja | Debugging difícil | FASE8-Week2 |
| Web page outputs | Baja | Sin outputs personalizables | FASE5 |

---

## Funcionalidades MVP a Completar

### A. Flow Visualization (FASE7 - Completar)

**Estado actual:** Registry existe pero sin visualización jerárquica

**Requerimientos:**
1. **Jerarquía de flows:** Mostrar dependencias entre flows (ej: preventa → reserva → cierre)
2. **Contexto por agente:** Cada panel de agente debe mostrar qué flows participa
3. **Estado en tiempo real:** Indicador visual del estado de cada flow (pending/running/completed/failed)
4. **Documentación de flows:** Descripciones coloquiales de qué hace cada flow y cuándo se usa

**Archivos a crear/modificar:**
- `dashboard/components/flows/FlowHierarchy.tsx` (NUEVO)
- `dashboard/components/flows/FlowStatusBadge.tsx` (NUEVO)
- `dashboard/hooks/useFlowHierarchy.ts` (NUEVO)
- `src/flows/registry.py` (MODIFICAR - agregar metadata de dependencias)
- `dashboard/app/(app)/workflows/page.tsx` (MODIFICAR - agregar vista jerárquica)

**Criterios de aceptación:**
- [ ] Usuario puede ver árbol de dependencias de flows
- [ ] Cada flow muestra su estado actual
- [ ] Descripciones claras de propósito y contexto de uso
- [ ] Integración con panel de agente (muestra flows asociados)

---

### B. Agent Detail Structure (FASE8-Week2 - Completar)

**Estado actual:** Panel básico con tokens pero sin tareas/credenciales/personalidad

**Requerimientos:**
1. **Personalidad del agente:** Descripción coloquial de su rol y comportamiento
2. **Historial de tareas:** Lista de tareas ejecutadas con estado y métricas
3. **Credenciales:** Link al Vault con secretos asociados (mostrar metadata, nunca valores)
4. **Métricas detalladas:** Tokens por tarea, tiempo promedio, tasa de éxito
5. **Configuración:** max_iter, allowed_tools, status (enabled/disabled)

**Archivos a crear/modificar:**
- `dashboard/components/agents/AgentPersonality.tsx` (NUEVO)
- `dashboard/components/agents/AgentTaskHistory.tsx` (NUEVO)
- `dashboard/components/agents/AgentCredentials.tsx` (NUEVO)
- `dashboard/hooks/useAgentDetails.ts` (NUEVO)
- `src/api/routes/agents.py` (NUEVO - endpoint completo de agente)
- `dashboard/app/(app)/agents/[id]/page.tsx` (MODIFICAR - integrar nuevos componentes)
- `supabase/migrations/020_agent_metadata.sql` (NUEVO - tabla opcional de metadata)

**Criterios de aceptación:**
- [ ] Panel muestra personalidad del agente (ej: "Soy un planificador meticuloso...")
- [ ] Lista de últimas 10 tareas con estado y tokens
- [ ] Link al Vault con lista de credenciales (sin valores expuestos)
- [ ] Métricas de rendimiento (tokens, tiempo, éxito)
- [ ] Configuración editable (solo admin)

---

### C. Reporting & Dashboards

#### C1. Custom Dashboards (FASE5 - Completar)

**Estado actual:** Dashboard fijo con métricas básicas

**Requerimientos:**
1. **Dashboard builder:** Interfaz para crear dashboards personalizados
2. **Widgets configurables:** Cards, tablas, gráficos con filtros por agente/flow/org
3. **Datos en tiempo real:** Supabase Realtime para updates automáticos
4. **Templates:** Dashboards predefinidos (Operations, Finance, Agent Performance)

**Archivos a crear/modificar:**
- `dashboard/components/dashboard-builder/WidgetBuilder.tsx` (NUEVO)
- `dashboard/components/dashboard-builder/DashboardCanvas.tsx` (NUEVO)
- `dashboard/hooks/useDashboardBuilder.ts` (NUEVO)
- `src/api/routes/dashboards.py` (NUEVO - CRUD de dashboards personalizados)
- `supabase/migrations/021_custom_dashboards.sql` (NUEVO - tabla user_dashboards)
- `dashboard/app/(app)/dashboards/page.tsx` (NUEVO)
- `dashboard/app/(app)/dashboards/[id]/page.tsx` (NUEVO)

**Criterios de aceptación:**
- [ ] Usuario puede crear dashboard personalizado
- [ ] Agregar/quitar widgets con datos de agentes/flows
- [ ] Filtros por org, fecha, flow_type, agente
- [ ] Actualización automática vía Supabase Realtime
- [ ] Guardar y compartir dashboards

#### C2. Web Page Outputs (FASE5 - Futuro)

**Estado actual:** No implementado

**Requerimientos:**
1. **Generación de páginas:** Agentes generan páginas web con datos estructurados
2. **Templates personalizables:** Formato definido por usuario (presupuestos, reportes)
3. **URLs públicas:** Ej: `www.fap.com/orgN/presupuesto9834892`
4. **Integración con presentation configs:** Usar FASE7 para formatear outputs

**Archivos a crear:**
- `src/api/routes/public_pages.py` (NUEVO)
- `dashboard/components/pages/PageBuilder.tsx` (NUEVO)
- `supabase/migrations/022_public_pages.sql` (NUEVO)

**Criterios de aceptación:**
- [ ] Agente puede generar página web desde flow
- [ ] Template personalizable con placeholders
- [ ] URL pública accesible sin auth
- [ ] Preview antes de publicar

**Nota:** Este ítem se considera **nice-to-have** para MVP. Priorizar después de A, B, C1, D.

---

### D. Conversational Analytical Agent (FASE4 - Completar)

**Estado actual:** EventStore existe pero sin interfaz conversacional

**Requerimientos:**
1. **Agente por organización:** Cada org tiene su propio agente analítico
2. **Query en lenguaje natural:** Usuario pregunta sobre eventos/tasks/flows
3. **Acceso read-only a EventStore:** Agente consulta eventos de dominio
4. **Generación de reportes:** Respuestas con datos + visualizaciones
5. **Contexto conversacional:** Mantiene historial de conversación

**Archivos a crear/modificar:**
- `src/crews/analytical_crew.py` (NUEVO - crew especializado en consultas)
- `src/api/routes/analytical_chat.py` (NUEVO - endpoint conversacional)
- `dashboard/components/chat/AnalyticalChat.tsx` (NUEVO)
- `dashboard/hooks/useAnalyticalChat.ts` (NUEVO)
- `dashboard/app/(app)/analytics/page.tsx` (NUEVO)
- `supabase/migrations/023_chat_history.sql` (NUEVO - tabla de historial)

**Criterios de aceptación:**
- [ ] Usuario puede hacer preguntas en lenguaje natural
- [ ] Agente responde con datos reales del EventStore
- [ ] Respuestas incluyen visualizaciones (tablas, gráficos)
- [ ] Historial de conversación persistente
- [ ] Aislado por organización (solo ve datos de su org)

---

## Funcionalidades Adicionales (Nice-to-Have para MVP)

### E. Tickets System Completo (FASE8-Week2 - Simplificado)

**Estado actual:** Diálogo de ejecución directa (RunFlowDialog) reemplaza sistema de tickets

**Requerimientos (si se decide implementar):**
1. Tabla `tickets` con estados (backlog → todo → in_progress → done)
2. CRUD completo de tickets
3. UI de gestión `/tickets/page.tsx`

**Decisión pendiente:** ¿Se requiere ciclo de vida formal de tickets o el RunFlowDialog es suficiente?

**Recomendación:** Mantener RunFlowDialog para MVP. Evaluar tickets completos post-MVP.

### F. Execution Transcript (FASE8-Week2 - Diferido)

**Estado actual:** No implementado

**Requerimientos:**
1. Endpoint `/transcripts/{task_id}` con streaming
2. UI de timeline de ejecución paso a paso
3. Supabase Realtime para updates en vivo

**Recomendación:** Diferir para post-MVP. Logging actual es suficiente para debugging.

---

## Priorización Propuesta

### Sprint 1 (Semana 1-2): Cerrar Gaps Existentes
- [ ] **B. Agent Detail Structure** - Completar panel de agentes
- [ ] **A. Flow Visualization** - Jerarquía y contexto de flows
- [ ] Supabase Realtime setup (reemplazar polling)

### Sprint 2 (Semana 3-4): Reporting y Analytics
- [ ] **D. Conversational Analytical Agent** - Agente de consultas
- [ ] **C1. Custom Dashboards** - Dashboard builder básico

### Sprint 3 (Semana 5): Refinamiento y Demo
- [ ] Integración end-to-end
- [ ] Tests E2E de flujos críticos
- [ ] Demo preparation

### Post-MVP (Nice-to-Have)
- [ ] C2. Web Page Outputs
- [ ] E. Tickets System Completo
- [ ] F. Execution Transcript

---

## Modelo de Datos Requerido

### 020_agent_metadata.sql (Sprint 1)
```sql
CREATE TABLE IF NOT EXISTS agent_metadata (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL,
  agent_role  TEXT NOT NULL,
  personality TEXT, -- Descripción coloquial
  config      JSONB, -- max_iter, allowed_tools, etc
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE agent_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Agents are org-scoped" ON agent_metadata
  USING (org_id = current_org_id());
```

### 021_custom_dashboards.sql (Sprint 2)
```sql
CREATE TABLE IF NOT EXISTS user_dashboards (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL,
  name        TEXT NOT NULL,
  description TEXT,
  layout      JSONB NOT NULL, -- Widget positions y configuración
  is_public   BOOLEAN DEFAULT FALSE,
  created_by  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_dashboards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Dashboards are org-scoped" ON user_dashboards
  USING (org_id = current_org_id());
```

### 022_chat_history.sql (Sprint 2)
```sql
CREATE TABLE IF NOT EXISTS chat_history (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL,
  session_id  TEXT NOT NULL,
  role        TEXT NOT NULL, -- 'user' o 'assistant'
  message     TEXT,
  metadata    JSONB, -- Queries ejecutadas, visualizaciones
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Chat is org-scoped" ON chat_history
  USING (org_id = current_org_id());

CREATE INDEX idx_chat_session ON chat_history(org_id, session_id, created_at);
```

---

## Stack y Dependencias

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| API | FastAPI | ≥0.115 |
| Modelos | Pydantic v2 | ≥2.10 |
| Base de datos | Supabase | ≥2.10 |
| Agentes IA | CrewAI | ≥0.100 |
| LLM | Anthropic / OpenAI | ≥0.40 / ≥1.58 |
| Frontend | Next.js 15 + React | ≥15.0 |
| UI Components | shadcn/ui | Latest |
| State Management | React Hooks + Supabase Realtime | - |
| Tests | pytest + pytest-asyncio | ≥8.3 |

---

## Principios de Desarrollo

1. **No tocar CrewAI:** Nunca modificar `src/crews/` ni `src/flows/multi_crew_flow.py`
2. **Datos del sistema solo:** Supabase almacena solo datos del sistema agentino, nunca datos de operatoria
3. **Token tracking en FAP:** Se implementa en BaseFlowState/EventStore, no en CrewAI
4. **Auth JWT existente:** `api.ts` ya tiene auth — no reemplazar
5. **RLS mandatory:** Toda nueva tabla debe tener Row Level Security con `current_org_id()`

---

## Métricas de Éxito del MVP

| Métrica | Target Actual | Target Post-Implementación |
|---------|--------------|---------------------------|
| Flows ejecutados exitosamente | ✅ Funcional | ✅ + visualización clara |
| Panel de agente | ⚠️ Parcial (solo tokens) | ✅ Completo (tareas + creds + personalidad) |
| Dashboard custom | ⚠️ Fijo | ✅ Builder configurable |
| Agente analítico | ❌ No existe | ✅ Conversacional por org |
| Tiempo de debug | ~15 min (logs) | ~5 min (transcript + flow viz) |
| User satisfaction | N/A | Target: >8/10 en demo |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| CrewAI breaking changes | Media | Alto | Tests de integración antes de deploy |
| Supabase RLS bugs | Baja | Alto | Tests E2E con múltiples orgs |
| LLM rate limits | Alta | Medio | Caching + retry logic |
| Frontend complexity | Media | Medio | Componentes reutilizables + storybook |
| Scope creep | Alta | Alto | Stick to this doc, defer nice-to-haves |

---

## Decisiones Pendientes

1. **¿Requiere sistema de tickets formal?** → Recomendar: NO para MVP, usar RunFlowDialog
2. **¿Web page outputs son MVP-critical?** → Recomendar: NO, diferir a post-MVP
3. **¿Qué orgs participarán del demo?** → TBD
4. **¿Agente analítico usa Claude o GPT?** → TBD según costos

---

## Archivos de Referencia

- `docs/FAP-Phase1-BaseEngine.md` - Motor base
- `docs/FAP-Phase2-Governance.md` - Governance y approvals
- `docs/FAP-Phase3-MultiAgent.md` - Multi-crew flows
- `docs/FAP-Phase4-Conversational.md` - Diseño agente conversacional
- `docs/FAP-Phase5-Dashboard+CoctelProDemo.md` - Dashboard y outputs
- `docs/FASE7-FinalDefinition.md` - Presentation configs
- `docs/FASE8-Week2-FinalDefinition.md` - Estado actual de gaps
- `.kilo/plans/1775923956538-calm-nebula.md` - Análisis original de Kilo

---

**Próxima revisión:** 2026-04-18
**Aprobación pendiente:** Confirmar priorización con stakeholder
