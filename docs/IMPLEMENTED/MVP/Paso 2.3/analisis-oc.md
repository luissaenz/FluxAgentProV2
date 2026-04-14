# Análisis Técnico: Paso 2.4 — Refactorizar Pestaña de Herramientas (Metadata-Driven UI)

## 1. Diseño Funcional

### 1.1 Happy Path
El usuario accede a la página de detalle de un agente:
1. El componente carga los datos del agente y sus herramientas asignadas (`allowed_tools`).
2. Por cada herramienta en `allowed_tools`, se consulta el `tool_registry` para obtener metadata (descripción, tags, timeout).
3. La UI muestra cada herramienta con su nombre, descripción legible y badges de tags opcionales.
4. Si una herramienta no existe en el registry, se muestra el nombre con indicador de "desconocida".

### 1.2 Edge Cases
- **Herramienta no registrada:** El nombre aparece pero con descripción "Sin descripción disponible" y badge de warning.
- **Lista vacía de herramientas:** Mostrar mensaje "Sin herramientas asignadas".
- **Carga lenta:** Mostrar skeleton loading mientras se consultan las descripciones.

### 1.3 Manejo de Errores
- Si el registry falla silenciosamente, usar fallback de nombre sin descripción.
- La pestaña sigue siendo funcional aunque la metadata no cargue.

---

## 2. Diseño Técnico

### 2.1 Componentes Modificados
- `dashboard/app/(app)/agents/[id]/page.tsx`: Extraer la sección de herramientas del tab "Información" a un componente dedicado `AgentToolsCard.tsx`.

### 2.2 Nuevo Componente
- `dashboard/components/agents/AgentToolsCard.tsx`:
  - Props: `tools: string[]`
  - Consultará la metadata de herramientas via un nuevo hook `useToolMetadata`.
  - Renderizará una lista de cards con nombre, descripción y tags.

### 2.3 Nuevo Hook
- `dashboard/hooks/useToolMetadata.ts`:
  - Expone función `getToolDescription(toolName: string): string`
  - Consume metadata del `tool_registry` via endpoint backend o simula con datos estáticos.

### 2.4 Modelo de Datos
```typescript
interface ToolInfo {
  name: string;
  description: string;
  tags: string[];
  requires_approval: boolean;
}
```

### 2.5 Coherencia con Estado de Fase
El contrato actual de `GET /agents/{id}/detail` retorna `allowed_tools` como array de strings. Se mantiene ese contrato; la transformación a metadata happens en frontend. El backend NO necesita cambios para este paso.

---

## 3. Decisiones

### 3.1 Endpoint vs Frontend-Only
**Decisión:** Consumir metadata de herramientas en frontend mediante endpoint backend dedicado (`GET /tools/metadata`).
**Justificación:** El `tool_registry` es un objeto Python en memoria del servidor. Exponer un endpoint minimalista permite que el frontend consultarlo sin duplicar lógica. Alternativamente, se podría hardcodear descripciones en el frontend para el MVP, pero un endpoint es más mantenible.

### 3.2 Ubicación del Componente
**Decisión:** Crear `AgentToolsCard.tsx` en `dashboard/components/agents/`.
**Justificación:** Mantiene consistencia con la estructura existente (`AgentPersonalityCard` reside ahí). Facilita mantenimiento y futuros cambios de dominio.

---

## 4. Criterios de Aceptación

- [ ] El componente `AgentToolsCard` se renderiza en el tab "Información" bajo las herramientas.
- [ ] Cada herramienta muestra su nombre y descripción tomada del registry.
- [ ] Si la herramienta no existe en el registry, muestra "Sin descripción disponible".
- [ ] La UI muestra un skeleton mientras carga las descripciones.
- [ ] Si el agente no tiene herramientas, muestra mensaje "Sin herramientas asignadas".
- [ ] Las herramientas se muestran como cards con diseño consistente, no como texto plano.

---

## 5. Riesgos

| Riesgo | Descripción | Mitigación |
|--------|-------------|------------|
| El endpoint de metadata no existe aún | Backend no provee forma de consultar tool_registry | Crear endpoint simple `/tools/metadata` que retorna dict de todas las herramientas. |
| Performance con muchas herramientas | Si el agente tiene 20+ herramientas, múltiples llamadas | Endpoint devuelve todo el dict de una vez; frontend hace lookup local. |
| Inconsistencia entre registry y frontend | Herramientas en allowed_tools no existen en registry | Fallback graceful: mostrar nombre + "desconocida". |

---

## 6. Plan

1. **[Backend]** Crear endpoint `GET /tools/metadata` en `src/api/routes/tools.py` (nuevo archivo o existente).
   - Retorna `{ tool_name: { description, tags, requires_approval } }` para todas las herramientas registradas.
   - Complejidad: Baja.

2. **[Frontend]** Crear hook `useToolMetadata.ts` que consuma el endpoint.
   - Cachea respuesta en React Query.
   - Complejidad: Baja.

3. **[Frontend]** Crear componente `AgentToolsCard.tsx`.
   - Renderiza lista de herramientas con metadata.
   - Complejidad: Media (diseño UI).

4. **[Frontend]** Integrar `AgentToolsCard` en `agents/[id]/page.tsx`.
   - Reemplazar la línea actual `(agent.allowed_tools || []).join(', ')` por el nuevo componente.
   - Complejidad: Baja.

5. **[Validación]** Verificar que las herramientas del agente mostram descripciones claras.
   - Complejidad: Baja.

---

## 🔮 Roadmap (NO implementar ahora)

- **Tool Approval UI:** Mostrar indicador visual de `requires_approval` en la UI de herramientas (badge "Requiere aprobación").
- **Tags de Herramientas:** Implementar filtro por tags en el panel del agente (ej. "solo herramientas de datos").
- **Herramientas por Categoría:** Agrupar herramientas por categoría lógica (外部API, DB, File, etc.).
- **Edición de Metadata:** Panel admin para editar descripciones de herramientas sin tocar código.