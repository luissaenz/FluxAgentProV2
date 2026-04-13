# 📋 ANÁLISIS TÉCNICO — PASO 2.4

**Paso:** 2.4
**Rol:** Frontend
**Agente:** Claude
**Fecha:** 2026-04-12

---

## 1. Diseño Funcional

### 1.1 Comprensión del Paso

**Problema que resuelve:**
La pestaña "Información" del detalle de agente muestra la lista de `allowed_tools` como texto plano sin contexto semántico: `"noop, obtener_factor_climatico, verificar_pronostico_real"`. El agente no puede inferir qué hace cada herramienta ni sus características operativas (timeout, si requiere aprobación, tags descriptivos).

**Inputs:**
- `AgentPersonalityCard` ya rendered en la pestaña (Paso 2.3 completado).
- `allowed_tools: string[]` disponible en el objeto `agent` local.
- `detail?.credentials` del endpoint `GET /agents/{id}/detail` con `{ tool, description }` por cada tool que tiene credencial asociada.

**Outputs esperados:**
- Nuevo componente `AgentToolsCard.tsx` integrado en la pestaña "Información".
- Muestra cada herramienta con: nombre, descripción narrativa, badges (tags, requires_approval, timeout).
- La pestaña "Credenciales" ya consume `detail?.credentials` pero muestra tool names sin iconografía ni categorización clara.

**Rol en la fase:**
Este es el cierre de la experiencia "identidad + capacidades" del agente. Con 2.3 (personalidad narrativa) y 2.4 (descripciones de herramientas), el panel del agente alcanza el estándar de usability del MVP para E5.

### 1.2 Happy Path

```
Usuario abre detalle de agente
  → Tabs: Información, Tareas, Credenciales
  → Tab "Información" renderiza:
      ├── AgentPersonalityCard (nombre, avatar, narrativa SOUL — Paso 2.3)
      ├── AgentToolsCard (NUEVO — tools del agente con metadata)
      └── Configuración (role, modelo, max_iter)
  → AgentToolsCard muestra cada tool como tarjeta con:
      - Nombre de la herramienta (未必ados como "obtener_factor_climatico")
      - Descripción legible (del ToolMetadata.description)
      - Badges: tags, requires_approval, timeout
```

### 1.3 Edge Cases MVP

| Caso | Comportamiento esperado |
|------|------------------------|
| `allowed_tools` vacío `[]` | Mensaje "Este agente no tiene herramientas asignadas" en AgentToolsCard |
| Tool sin metadata en registry (tool existe en DB pero no está registrado en runtime) | Mostrar nombre con badge "Sin descripción disponible" y descripción fallback `null` |
| Tool sin description en ToolMetadata | Usar el `name` como descripción de fallback, sin badge |
| `loadingDetail` true | Skeleton de cards equivalente al de AgentPersonalityCard |
| Credenciales vacías | Mantener estado actual (mensaje "Sin credenciales asociadas") |

### 1.4 Manejo de Errores

- **registry no carga (runtime):** Las tools se muestran con nombre y descripción "Información no disponible" sin crashear la UI.
- **API detail falla:** `useAgentDetail` tiene `staleTime: 10_000` y `refetchInterval: 15_000`. Se muestra último valor cacheado o estado vacío sin bloquear la página.

---

## 2. Diseño Técnico

### 2.1 Componentes

#### Nuevo: `AgentToolsCard.tsx`
**Ubicación:** `dashboard/components/agents/AgentToolsCard.tsx`

Props:
```typescript
interface AgentToolsCardProps {
  allowedTools: string[]           // desde agent.allowed_tools
  credentials: ToolCredential[]     // desde detail?.credentials (para marcar cuáles requieren credencial)
  isLoading: boolean
}

interface ToolCredential {
  tool: string
  description: string | null
}
```

Render:
- Si `isLoading`: Skeleton (3 tarjetas de tool)
- Si `allowedTools.length === 0`: Empty state
- Para cada tool: `ToolCard` con nombre, descripción, badges

#### Componente interno: `ToolCard`
- Nombre formateado (reemplazar `_` con espacios, title case)
- Descripción del ToolMetadata (o fallback)
- Badge de tags (max 3 visibles)
- Badge `requires_approval: true` → color warning
- Badge `timeout_seconds` → "30s timeout"
- Indicador `requires_credential` si existe en `credentials`

#### Modificación: `agents/[id]/page.tsx`
- Importar `AgentToolsCard`
- Ubicarlo en `TabsContent value="info"` después de `AgentPersonalityCard`
- Reemplazar el div hardcodeado de "Herramientas" en Configuracion por el nuevo componente

### 2.2 Integración con Tipos Existentes

**Tipo a agregar en `lib/types.ts`:**
```typescript
export interface ToolInfo {
  name: string
  description: string | null
  tags: string[]
  requires_approval: boolean
  timeout_seconds: number
  retry_count: number
}
```

**Nota de coherencia:** El tipo `AgentDetail.credentials` ya existe en `lib/types.ts` líneas 213-216 con `tool: string` y `description: string | null`. El contrato del backend es compatible. El tipo `ToolInfo` es nuevo y no reemplaza nada existente.

### 2.3 Modelos de Datos

No hay cambios en modelos de datos. El paso es 100% frontend.

### 2.4 Integración con Contratos Existentes

- **`GET /agents/{id}/detail`**: No se modifica el backend. El frontend consume el contrato existente enriquecido en Paso 2.2.
- **`detail?.credentials`**: Disponible y funcional. Se usa para mostrar cuáles tools requieren credencial.
- **`tool_registry` (backend Python)**: Proveedor de metadata en runtime. No se expone al frontend directamente — el frontend consume la descripción via `credentials.description` o por nombre de tool via metadata estática (simulada en el componente si no se tiene acceso).

**Ambigüedad detectada:** El `tool_registry` es Python y corre en el servidor. El frontend no puede acceder a metadata de tools directamente — solo recibe `credentials` que el backend calcula con `tool_registry.get(tool_name)`. Para tools que NO tienen credencial, el backend no devuelve descripción. **Resolución propuesta:** En el frontend, hardcodear un mapping estático de tool → descripción para las tools conocidas del dominio Bartenders (preventa, escandallo, inventario, clima). Para herramientas genéricas sin mapping, usar la lógica de fallback (nombre formateado + "Sin descripción disponible").

---

## 3. Decisiones

### D3.1: Descripciones de tools via mapping estático en frontend

El backend `agents.py` (línea 108-116) solo retorna `credentials` para tools que el agente tiene asociadas Y que el registry puede resolver. El frontend no tiene acceso a `ToolMetadata` del registry Python directamente.

**Decisión:** Crear un mapping estático `TOOL_DESCRIPTIONS` en `dashboard/lib/tool-descriptions.ts` con las tools del dominio Bartenders y sus descripciones narrativas. Para tools desconocidas, fallback al nombre formateado.

**Justificación:** Evita crear un endpoint nuevo solo para consultar metadata de tools. Las tools registradas en el sistema son conocidas y finitas para el MVP. El mapping es mantenible y extensible.

### D3.2: Formato de nombre legible

`obtener_factor_climatico` → "Obtener Factor Climatico" (title case, guiones bajos reemplazados por espacios).

**Decisión:** Función utility `formatToolName(name: string): string` que normaliza nombres de tools a texto legible.

### D3.3: Badges de metadata operativa

Solo se muestran `requires_approval` y `timeout_seconds` como badges visuales. `retry_count` se omite para MVP (información secundaria).

---

## 4. Criterios de Aceptación

| # | Criterio | Verificación |
|---|----------|--------------|
| CA1 | El componente `AgentToolsCard` se renderiza sin errores en la pestaña "Información" | Inspección visual en `/agents/[id]` |
| CA2 | Si `allowed_tools` está vacío, se muestra mensaje "Este agente no tiene herramientas asignadas" | Crear ticket con agente sin tools |
| CA3 | Cada tool muestra su nombre formateado (ej: `obtener_factor_climatico` → "Obtener Factor Climatico") | Comparar con input |
| CA4 | Las tools de Bartenders muestran descripción narrativa (no solo el nombre técnico) | Verificar tools: `obtener_factor_climatico`, `verificar_pronostico_real` |
| CA5 | El badge `requires_approval` aparece si la tool lo requiere | Herramienta con `requires_approval: true` en registry |
| CA6 | Los estados de loading muestran skeleton y no bloquean el render | Throttle red simulando slow network |
| CA7 | La página de detalle del agente sigue cargando aunque `AgentToolsCard` falle | Verificar en DevTools que errores de tool no crashean el tab |
| CA8 | Las tools marcadas como `requires_credential` en `credentials` muestran indicador visual | Cross-reference con tab "Credenciales" |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| R1 | El mapping estático queda desincronizado si se registran nuevas tools en el registry | Media | Baja | Documentar que cada nueva tool debe aggiornare el mapping. El fallback por nombre garantiza que nunca se muestre "undefined" |
| R2 | Si una tool existe en `agent_catalog.allowed_tools` pero no está en el registry Python, falla el `tool_registry.get(tool_name)` en backend (línea 109) | Baja | Baja | El try/except en `agents.py` línea 115-116 ya captura el error. La tool se excluye de `secret_refs` silenciosamente. El frontend recibe `credentials` sin esa tool — sin break, solo lista incompleta |
| R3 | El componente no escala si un agente tiene 20+ tools | Baja | Baja | Limitar visualización a scroll interno + "Mostrar más" si `allowed_tools.length > 10`. MVP no requiere esta complejidad |

---

## 6. Plan

### Tarea 1: Crear mapping estático de descripciones
**Archivo:** `dashboard/lib/tool-descriptions.ts`
**Complejidad:** Baja
**Descripción:** Mapping `Record<string, ToolDescription>` con nombre de tool → `{ description, tags, requiresApproval, timeoutSeconds }`. Poblar con tools de Bartenders y builtin.

### Tarea 2: Crear utility de formateo de nombres
**Archivo:** `dashboard/lib/tool-descriptions.ts` (mismo archivo)
**Complejidad:** Baja
**Descripción:** Función `formatToolName(name: string): string`

### Tarea 3: Implementar `AgentToolsCard`
**Archivo:** `dashboard/components/agents/AgentToolsCard.tsx`
**Complejidad:** Media
**Dependencias:** Tarea 1 y 2
**Descripción:** Componente principal. Recibe `allowedTools`, `credentials`, `isLoading`. Renderiza grid de `ToolCard` o empty state o skeleton.

### Tarea 4: Integrar en `agents/[id]/page.tsx`
**Archivo:** `dashboard/app/(app)/agents/[id]/page.tsx`
**Complejidad:** Baja
**Dependencias:** Tarea 3
**Descripción:** Importar `AgentToolsCard`. Reemplazar el div `<div><strong>Herramientas:</strong>{(agent.allowed_tools || []).join(', ') || '—'}</div>` (línea 159-161) por `<AgentToolsCard allowedTools={agent.allowed_tools || []} credentials={credentials} isLoading={loadingDetail} />`.

### Tarea 5: Verificación visual
**Acción:** Abrir detalle de un agente con tools (agente "bartender-preventa" en org de demo). Verificar que las descripciones corresponden al mapping, los badges son visibles y el loading state es correcto.

---

## 🔮 Roadmap (NO implementar ahora)

- **Endpoint de metadata dinámica:** Crear `GET /tools/metadata` que el frontend pueda consultar para obtener ToolMetadata en tiempo real, eliminando la necesidad del mapping estático.
- **Filtro por tag:** Agregar botones de filtro en AgentToolsCard por tag (ej: "mostrar solo tools de clima", "mostrar tools que requieren aprobación").
- **Tool detail modal:** Click en una tool abre un modal con parámetros, ejemplos de uso y logs de invocación reciente.
- **Integración con tool invocations reales:** Mostrar conteo de veces que cada tool fue ejecutada por este agente (requiere ampliar el contrato de `GET /agents/{id}/detail`).