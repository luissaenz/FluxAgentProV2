# FAP v2 — Fase 8 Semana 2: Plan de Implementación Final

> **Versión:** 2.0 (Post-Implementación)  
> **Fecha:** 2026-04-06  
> **Estado:** Parcialmente implementado

---

## Resumen Ejecutivo

Este documento consolida el estado actual de la Semana 2 de la Fase 8, identificando:
- ✅ Lo implementado
- ❌ Lo pendiente
- 📋 Plan de acción para completar

### Métricas de Avance

| Entregable | Estado | Cobertura |
|-------------|--------|-----------|
| 4. Levantar Tickets | 🟡 Parcial | 40% |
| 5. Panel de Agente | 🟡 Parcial | 60% |
| 6. Run Transcript | ⚪ No iniciado | 0% |

---

## PARTE A: Lo Implementado (Completo)

### A.1 Token Tracking Real (Semana 1 - Completado)

**Objetivo:** Capturar tokens reales desde CrewAI y mostrarlos en el dashboard.

**Componentes implementados:**

#### Backend
| Archivo | Cambio |
|---------|--------|
| `src/crews/base_crew.py` | + `_extract_token_usage()` extrae `token_usage` del result de CrewAI |
| `src/crews/base_crew.py` | + `get_last_tokens_used()` retorna tokens consumidos |
| `src/flows/multi_crew_flow.py` | + Token tracking en `_execute_crew_a/b/c` |
| `src/flows/dynamic_flow.py` | + Token tracking por step |
| `src/flows/state.py` | `tokens_used` field existente |
| `src/flows/base_flow.py` | `persist_state()` persiste tokens |

#### Frontend
| Archivo | Cambio |
|---------|--------|
| `dashboard/components/section-cards.tsx` | Muestra "Tokens totales" |
| `dashboard/app/(app)/page.tsx` | Muestra `total_tokens` por flow |

#### API
| Endpoint | Descripción |
|----------|-------------|
| `GET /flow-metrics` | Retorna `tasks.tokens_used` agregado |
| `GET /flow-metrics/by-type` | Tokens por flow_type |
| `GET /flow-metrics/by-agent` | Tokens por agente (nuevo) |

**Resultado:** Los tokens se capturan ahora realmente desde el LLM, no estimaciones.

---

### A.2 RunFlowDialog (Entregable 4 - Parcial)

**Objetivo:** Permitir al usuario ejecutar flows desde la UI sin usar API directamente.

**Componentes implementados:**

#### Backend
| Archivo | Descripción |
|---------|-------------|
| `src/api/routes/flows.py` | `GET /flows/available` - lista todos los flows registrados |
| `src/api/routes/flows.py` | `POST /flows/{flow_type}/run` - ejecuta flow en background |
| `src/api/routes/flows.py` | `FLOW_INPUT_SCHEMAS` - schemas predefinidos para Bartenders |

#### Frontend
| Archivo | Descripción |
|---------|-------------|
| `dashboard/hooks/useFlows.ts` | Hook para obtener flows y ejecutar |
| `dashboard/components/flows/RunFlowDialog.tsx` | Dialog con selector de flow + formulario dinámico |
| `dashboard/app/(app)/workflows/page.tsx` | Botón "Ejecutar Flow" integrado |

**Resultado:** Usuario puede ejecutar cualquier flow desde la UI con validación de schema.

---

### A.3 Panel de Agente con Tokens (Entregable 5 - Parcial)

**Objetivo:** Mostrar información del agente incluyendo tokens consumidos.

**Componentes implementados:**

#### Backend
| Archivo | Descripción |
|---------|-------------|
| `src/api/routes/flow_metrics.py` | Endpoint `/flow-metrics/by-agent` |
| `src/api/routes/tasks.py` | Response ahora incluye `tokens_used` |

#### Frontend
| Archivo | Descripción |
|---------|-------------|
| `dashboard/hooks/useAgentMetrics.ts` | Hook para métricas de agentes |
| `dashboard/app/(app)/agents/[id]/page.tsx` | Panel de tokens + link al Vault |

**Resultado:** Page de agente muestra tokens consumidos y tiene link al Vault.

---

## PARTE B: Lo Pendiente (Por Implementar)

### B.1 Sistema de Tickets Formal

**Gap:** No existe tabla `tickets` con ciclo de vida completo.

**Necesario para ciclo de vida formal:**
- [ ] Migración `019_tickets.sql` - crear tabla
- [ ] `src/api/routes/tickets.py` - CRUD completo
- [ ] `dashboard/hooks/useTickets.ts` - hooks
- [ ] `dashboard/components/tickets/CreateTicketForm.tsx` - formulario
- [ ] `dashboard/app/(app)/tickets/page.tsx` - lista de tickets
- [ ] `dashboard/app/(app)/tickets/[id]/page.tsx` - detalle

**Decisión:** Postergar. El `RunFlowDialog` cumple la función de "levantar trabajo" de forma más simple.

---

### B.2 Run Transcript en Tiempo Real

**Gap:** No hay forma de ver la ejecución de un flow en tiempo real.

**Necesario:**
- [ ] Endpoint `GET /transcripts/{task_id}`
- [ ] Supabase Realtime channel setup
- [ ] Hook `useFlowTranscript.ts`
- [ ] UI de transcript streaming

**Prioridad:** Alta - necesario para debugging

---

### B.3 Panel de Agente Completo

**Gap:** Falta historial de tareas por agente y tabs completos.

**Necesario:**
- [ ] Migración `020_tasks_assigned_agent.sql` - agregar columna `assigned_agent`
- [ ] Endpoint `/agents/{role}/detail` completo
- [ ] Actualizar page con tabs (tasks + credentials)

**Prioridad:** Baja - la información básica ya está visible

---

## PARTE C: Plan de Acción Detallado

### C.1 Para Completar Run Transcript (Alta Prioridad)

#### Paso C.1.1: Endpoint de Transcript

```python
# src/api/routes/transcripts.py
@router.get("/{task_id}")
async def get_transcript(task_id: str, org_id: str = Depends(require_org_id)):
    """Obtiene eventos de dominio para un task_id específico."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("domain_events")
            .select("id, event_type, payload, sequence, created_at")
            .eq("aggregate_id", task_id)
            .order("sequence")
            .execute()
        )
    return {"task_id": task_id, "events": result.data}
```

#### Paso C.1.2: Hook con Realtime

```typescript
// dashboard/hooks/useFlowTranscript.ts
export function useFlowTranscript(orgId: string, taskId: string) {
  // useQuery para historial
  // useEffect para Supabase Realtime subscription
  // Combinar histórico + live events
}
```

#### Paso C.1.3: UI de Transcript

- Usar `events/timeline` existente como base
- Agregar modo "live" con indicadores de nuevos eventos
- Renderizar payload formateado

---

### C.2 Para Completar Panel de Agente (Baja Prioridad)

#### Paso C.2.1: Agregar columna assigned_agent

```sql
-- migracion
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assigned_agent TEXT;
```

#### Paso C.2.2: Actualizar endpoint

```python
# Modificar persist_state() en base_flow.py para setear assigned_agent
# baseado en el agent_role del crew ejecutado
```

#### Paso C.2.3: Page con tabs

- Tab 1: Info (ya existe)
- Tab 2: Tasks (filtrar por assigned_agent)
- Tab 3: Credentials (mostrar secrets del Vault)

---

### C.3 Para Sistema de Tickets (Solo si usuario lo requiere)

**Precondición:** El usuario indica que necesita ciclo de vida formal de tickets.

**Arquitectura sugerida:**

```
Ticket lifecycle:
  backlog → todo → in_progress → done
                         ↓
                       blocked → (resuelto) → in_progress
                         ↓
                       cancelled
```

**Endpoints:**
- `GET /tickets` - lista con filtros
- `POST /tickets` - crear
- `GET /tickets/{id}` - detalle
- `PATCH /tickets/{id}` - actualizar estado
- `POST /tickets/{id}/execute` - ejecutar flow asociado

---

## PARTE D: Checklist de Verificación

### Verificar Token Tracking

```bash
# 1. Ejecutar un flow
curl -X POST http://localhost:8000/bartenders/preventa \
  -H "Content-Type: application/json" \
  -d '{"fecha_evento":"2026-07-20","provincia":"Tucuman",...}'

# 2. Verificar tokens en DB
psql -c "SELECT id, flow_type, tokens_used FROM tasks WHERE flow_type='bartenders_preventa';"

# 3. Verificar en dashboard
# Ir a /tasks/[id] y revisar tokens_used
```

### Verificar RunFlowDialog

```bash
# 1. Obtener flows disponibles
curl http://localhost:8000/flows/available

# 2. Verificar en dashboard
# Ir a /workflows y clicking "Ejecutar Flow"
```

### Verificar Panel de Agente

```bash
# 1. Ver metrics por agente
curl http://localhost:8000/flow-metrics/by-agent

# 2. Verificar en dashboard
# Ir a /agents/[id] y verificar panel de tokens
```

---

## PARTE E: Dependencias y Precedencias

```
Semana 1 ─────┬─→ Token tracking real (COMPLETO)
              │
Semana 2 ─────┼─→ RunFlowDialog (COMPLETO)
              │     ↓
              │   Requiere: flows.py + useFlows.ts + RunFlowDialog.tsx
              │
              ├─→ Panel agente tokens (COMPLETO)
              │     ↓
              │   Requiere: by-agent endpoint + useAgentMetrics.ts
              │
              └─→ Run Transcript (PENDIENTE)
                    ↓
                  Requiere: transcripts endpoint + Realtime + useFlowTranscript
```

---

## PARTE F: Métricas de Éxito

| Métrica | Target | Actual |
|---------|--------|--------|
| Flows ejecutables desde UI | 100% | 100% |
| Tokens trackeados correctamente | >95% | ✅ Implementado |
| Panel de agente muestra tokens | Sí | ✅ Implementado |
| Transcript disponible | No | ❌ Pendiente |
| Sistema tickets formal | No | ❌ Pendiente |

---

## Conclusión

La Semana 2 alcanzó ~50% del objetivo original con decisiones de diseño pragmáticas:

1. **RunFlowDialog** > sistema de tickets completo (más simple, funcional)
2. **Token tracking real** > estimación (implementado en Semana 1)
3. **Panel de agente básico** > completo (información clave visible)

**Recomendación:** Avanza a Semana 3 (Inbox, HITL mejorado, Cron) y completa el Run Transcript cuando el usuario lo requiera explícitamente.

---

## Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-04-06 | Documento inicial post-análisis |
| 2.0 | 2026-04-06 | Plan de implementación agregado |