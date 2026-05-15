# Análisis de Paso 6 — Agent Playground (Agente: hy3)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentPlayground.tsx` no existe | glob `dashboard/components/builder/AgentPlayground.tsx` | ✅ | No files found |
| 2 | Endpoint `POST /agents/{role}/run` existe | Lectura `src/api/routes/agents.py` | ✅ | agents.py:251-320 |
| 3 | Endpoint `GET /tasks/{task_id}` existe | Lectura `src/api/routes/tasks.py` | ✅ | tasks.py:69-91 |
| 4 | `TaskResponse` tiene `tokens_used` | Lectura modelo `TaskResponse` en tasks.py | ✅ | tasks.py:33 |
| 5 | `RunAgentResponse` tiene `task_id` | Lectura modelo `RunAgentResponse` en agents.py | ✅ | agents.py:47 |
| 6 | `@tanstack/react-query` instalado | Referencia en `AgentForm.tsx` + phase-state.md | ✅ | AgentForm.tsx:4, phase-state.md:66 |
| 7 | `sonner` para toasts instalado | Import en `AgentForm.tsx` | ✅ | AgentForm.tsx:8 |
| 8 | `BaseCrew.run_async` existe | Uso en `agents.py:294` | ✅ | agents.py:294 |

**Discrepancias encontradas:** Ninguna. Todos los elementos verificados existen según lo requerido por el paso.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- **Schema:** No hay cambios en tablas de DB. Paso 6 es frontend-only, usa endpoints existentes que no modifican esquema.
- **Integridad referencial:** No aplica (sin nuevas relaciones).
- **RLS:** No aplica (sin nuevas tablas/policies).
- **Índices:** No aplica.
- **Tipos de datos:** No aplica.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- **Nuevo archivo:** `dashboard/components/builder/AgentPlayground.tsx`
  - **Firma:** React component (props: `agentRole: string`, `orgId: string`, hereda de BuilderLayout).
  - **Dependencias:** `react-query` (useMutation, useQuery), `sonner` (toast), shadcn/ui (`Input`, `Button`, `Collapsible`, `LoadingSpinner`).
  - **Patrón a seguir:** `dashboard/components/builder/AgentForm.tsx` (estructura 'use client', imports, manejo de estado, llamadas a API).
- **Funciones/clases:**
  - `AgentPlayground`: componente principal.
  - `MessageBubble`: subcomponente para mostrar mensajes usuario/agente.
  - `ToolCallCollapsible`: subcomponente para tool calls colapsables.
- **Imports exactos:**
  - `import { useMutation, useQuery } from '@tanstack/react-query'`
  - `import { api } from '@/lib/api'`
  - `import { toast } from 'sonner'`
  - `import { LoadingSpinner } from '@/components/shared/LoadingSpinner'`
- **Modularidad:** Alta cohesión (solo lógica de chat/playground), acoplamiento bajo (depende de APIs existentes, no de otros componentes del builder excepto props).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- **Endpoints usados (ya implementados):**
  1. `POST /agents/{role}/run` (agents.py:251-320):
     - Método: POST
     - Input: `RunAgentRequest` (`input_data: Dict[str, Any]`)
     - Output: `RunAgentResponse` (`task_id: str`, `status: str`)
     - Auth: `verify_org_membership` (extrae org_id)
  2. `GET /tasks/{task_id}` (tasks.py:69-91):
     - Método: GET
     - Output: `TaskResponse` (`status`, `result`, `tokens_used`, `error`)
     - Auth: `verify_org_membership`
- **Flujo backend:**
  - `POST /agents/{role}/run` crea task en estado `pending`, inicia ejecución en background con `BaseCrew`.
  - Background task actualiza task a `running`, ejecuta agente, actualiza a `completed`/`failed` con resultado y `tokens_used`.
- **Contratos cumplidos:** Endpoints retornan lo prometido, manejo de errores (404 si agente no existe, fallo de ejecución en task.error).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- **Flujo end-to-end:**
  1. Usuario escribe mensaje en input de `AgentPlayground` → presiona Enter.
  2. Frontend envía `POST /agents/{role}/run` con `input_data: { message: <mensaje> }`.
  3. Backend retorna `task_id` → frontend inicia polling a `GET /tasks/{task_id}` cada 1s.
  4. Mientras status es `pending`/`running`: muestra indicador de carga.
  5. Status `completed`: parsea `result`, muestra respuesta del agente, tool calls (colapsables), `tokens_used`.
  6. Status `failed`: muestra mensaje de error.
- **Coherencia:** Decisiones de frontend (react-query, sonner, shadcn/ui) alineadas con componentes existentes del builder. Backend ya soporta el flujo.
- **Gaps:** Tool calls no están estructurados en `TaskResponse.result` (depende de implementación de `BaseCrew`). Se asume que `result` incluye información de tool calls.
- **DX & Tooling (OBLIGATORIO):**
  ### Herramienta Propuesta: `fap agent run`
  - **Qué automatiza:** Envía un mensaje a un agente por rol, hace polling del task y muestra resultado en terminal. Elimina pruebas manuales en UI.
  - **Tipo:** CLI command (Typer)
  - **Cómo se usa:** `fap agent run --org-id <org_id> --role <role> --message "Mensaje de prueba"`
  - **Impacto para el usuario final:** Desarrolladores prueban agentes sin abrir dashboard, integra en CI/CD para tests E2E.
  - **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

✅ [FULLSTACK] Input de chat funcional: escribir mensaje → Enter → enviar
✅ [FULLSTACK] Respuesta del agente se muestra debajo del mensaje
✅ [FULLSTACK] Tool calls se listan con nombre + argumentos (formato colapsable)
✅ [FULLSTACK] Indicador de carga durante ejecución
✅ [FULLSTACK] Tokens usados visibles al finalizar
✅ [FULLSTACK] Manejo de errores: agente no encontrado, timeout, fallo de ejecución
✅ [BACKEND] POST /agents/{role}/run acepta `input_data` correcto
✅ [BACKEND] GET /tasks/{task_id} devuelve `status`, `result`, `tokens_used`
✅ [DX] Herramienta `fap agent run` ejecuta sin errores y reduce prueba manual

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Polling excesivo | Media | Intervalo de 1s genera muchos requests | Limitar a 60 polls (60s timeout), luego mostrar mensaje de timeout |
| `tokens_used` 0 | Baja | `crew.get_last_tokens_used()` falla | Mostrar "N/A" en UI si `tokens_used` es 0 |
| Tool calls no parseables | Media | `result` del agente no incluye tool calls estructurados | Mostrar resultado crudo si no se pueden parsear tool calls |
| Agente no existe | Alta | Usuario prueba agente no guardado | Validar existencia de agente vía `GET /agents/by-role/{role}` antes de ejecutar |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap agent run` | `src/cli/commands/agent_run.py` | `def run(org_id: str, role: str, message: str) -> None` | `src/cli/commands/agent_create.py` | DX | Media | 1h | Ninguna | → verificar: `fap agent run --help` ejecuta sin errores |
| 1 | Crear `AgentPlayground.tsx` | `dashboard/components/builder/AgentPlayground.tsx` | React component (props: `agentRole: string`, `orgId: string`) | `dashboard/components/builder/AgentForm.tsx` | CODE | Media | 1h | Tarea 0 | → verificar: `npm run build` (frontend) no errores |
| 2 | Implementar input + lista de mensajes | Mismo archivo | `useState` para `messages`, `inputMessage` | Cualquier chat component shadcn | CODE | Baja | 0.5h | Tarea 1 | → verificar: input acepta texto, Enter envía |
| 3 | Integrar mutation `POST /agents/{role}/run` | Mismo archivo | `useMutation` de react-query | `AgentForm.tsx` useQuery | BACKEND | Media | 1h | Tarea 2 | → verificar: envío de mensaje retorna `task_id` |
| 4 | Implementar polling `GET /tasks/{task_id}` | Mismo archivo | `useQuery` con `refetchInterval` | `AgentForm.tsx` useQuery tools | BACKEND | Media | 0.5h | Tarea 3 | → verificar: polling actualiza status hasta `completed` |
| 5 | Mostrar tool calls + tokens | Mismo archivo | Componente `ToolCallCollapsible` | `ToolMultiSelect.tsx` badges | FULLSTACK | Baja | 0.5h | Tarea 4 | → verificar: tool calls visibles y colapsables |

**Tiempo total estimado:** 4.5h

---

## 8️⃣ Roadmap (NO implementar ahora)

- Post-MVP: Persistir historial de mensajes en DB (`agent_playground_history` table).
- Post-MVP: Mostrar tool calls en tiempo real vía SSE (Server-Sent Events) en lugar de polling.
- Post-MVP: Soporte para múltiples agentes en mismo playground (multi-agent chat).
- Post-MVP: `fap agent run` con soporte para archivos adjuntos en mensajes.
