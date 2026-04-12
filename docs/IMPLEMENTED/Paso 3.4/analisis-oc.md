# 📋 ANÁLISIS TÉCNICO — Paso 3.4 [Frontend]: Integración en Vista de Tarea

## Estado: PENDIENTE (fuera de estado-fase.md)

---

## 1. Comprensión del Paso

**Problema que resuelve:** Actualmente, el transcript en tiempo real vive en una página separada (`/tasks/[id]/transcript`). El paso 3.4 busca integrar el componente `TranscriptTimeline` directamente en la vista de detalle de tarea (`tasks/[id]/page.tsx`) como una pestaña ("Live Transcript"), consolidando la experiencia del usuario.

**Inputs:**
- Componente existente: `TranscriptTimeline.tsx` ✅ implementado
- Hook existente: `useTranscriptTimeline.ts` ✅ implementado
- Página destino: `dashboard/app/(app)/tasks/[id]/page.tsx`

**Outputs:**
- Pestaña "Live Transcript" integrada en la vista de tarea
- El transcript debe ser el foco principal cuando la tarea está en ejecución (`is_running: true`)

**Rol en la fase:** Es el paso de integración UI final que conecta los componentes de transcript con la experiencia del usuario en la página de detalle de tarea.

---

## 2. Supuestos y Ambigüedades

| Supuesto | Resolución Propuesta |
|----------|---------------------|
| ¿Qué pasa si la tarea ya terminó? | Mostrar el transcript como historial (no "live") |
| ¿Necesita tabs existentes? | No hay tabs actualmente; agregar sistema de pestañas |
| ¿El diseño actual (2 columnas) se mantiene? | La integración debe reemplazar o coexistir con el timeline actual |
| ¿El transcript debe ser el "foco principal"? | Significa que debe mostrarse primero o ser más prominente durante ejecución activa |

---

## 3. Diseño Funcional

### Happy Path
1. Usuario accede a `/tasks/{id}`
2. La página muestra dos tabs: **"Información"** y **"Live Transcript"**
3. Por defecto se muestra "Información" (contenido actual)
4. Al hacer click en "Live Transcript", se carga el componente `TranscriptTimeline`
5. Si la tarea está en ejecución (`is_running: true`):
   - El tab "Live Transcript" muestra un indicador visual de "en vivo"
   - El badge "En vivo" del componente se activa
6. Si la tarea ya terminó, el transcript muestra el historial completo sin indicadores de live

### Edge Cases
- **Tarea no encontrada:** Mantener comportamiento actual (mensaje de error)
- **Carga del snapshot falla:** Mostrar error en el tab "Live Transcript" con opción de reintentar
- **Sin eventos para la tarea:** El componente ya maneja este estado con mensaje apropiado
- **Realtime no disponible:** El componente ya muestra el banner de fallback

### Manejo de Errores
- Si el fetch del snapshot falla: mensaje de error en el tab con botón de reintentar
- Si la conexión Realtime falla: el componente muestra banner de error y botón "Reintentar"

---

## 4. Diseño Técnico

### Componentes Involucrados

| Componente | Rol | Acción |
|-------------|-----|--------|
| `tasks/[id]/page.tsx` | Página contenedor | Agregar sistema de tabs + integrar TranscriptTimeline |
| `TranscriptTimeline.tsx` | Componente de transcript | Sin cambios (ya implementado) |
| `useTranscriptTimeline.ts` | Hook de lógica | Sin cambios (ya implementado) |

### Cambios en `tasks/[id]/page.tsx`

**Imports a agregar:**
```typescript
import { TranscriptTimeline } from '@/components/transcripts/TranscriptTimeline'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
```

**Estructura propuesta:**
- Usar componente `Tabs` de shadcn/ui para organizar contenido
- `TabsTrigger value="info"` → Información actual de la tarea
- `TabsTrigger value="transcript"` → Componente TranscriptTimeline

**Params adicionales:**
- `orgId` para pasarlo al componente TranscriptTimeline (ya se tiene de `useCurrentOrg`)

### Schema de Datos
No se requieren cambios. El componente TranscriptTimeline ya consume:
- Endpoint: `GET /transcripts/{task_id}` (snapshot)
- Canal Realtime: `task_transcripts:{task_id}` con filtro `aggregate_id=eq.{task_id}`

---

## 5. Decisiones

| Decisión | Justificación |
|----------|---------------|
| Usar componente Tabs de shadcn/ui | Es el patrón UI existente en el proyecto; mantener consistencia |
| Transcript como segundo tab por defecto | El usuario primero quiere ver la información de la tarea; puede navegar al transcript manualmente |
| Durante ejecución activa, el tab de transcript podría auto-seleccionarse | Refleja el requerimiento "foco principal durante ejecuciones activas" |

---

## 6. Criterios de Aceptación

| # | Criterio | Método de Verificación |
|---|----------|------------------------|
| 1 | La página muestra dos tabs: "Información" y "Live Transcript" | Inspección visual |
| 2 | Al hacer click en "Live Transcript" se renderiza el componente TranscriptTimeline | Click en tab y verificar renderizado |
| 3 | El componente recibe correctamente `taskId` y `orgId` | Console.log o DevTools |
| 4 | Durante ejecución activa (`is_running: true`), el badge "En vivo" aparece en el componente | Ejecutar tarea real |
| 5 | Si la tarea ya terminó, el transcript muestra el historial sin indicadores de live | Verificar tarea completada |
| 6 | El tab "Información" mantiene el contenido actual sin cambios | Comparar con comportamiento previo |
| 7 | La navegación entre tabs no dispara recargas de página | Verificar SPA behavior |

---

## 7. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Duplicación de queries (snapshot + Supabase) | Performance | El hook `useTranscriptTimeline` ya maneja esto óptimamente |
| Tabs no estilizadas con diseño del proyecto | UX | Usar componentes shadcn/ui existentes |
| Fallback si shadcn Tabs no existe | Implementación | Verificar disponibilidad de `Tabs` en componentes/ui |

---

## 8. Plan de Implementación

| # | Tarea | Complejidad | Dependencias |
|----|-------|-------------|---------------|
| 1 | Verificar existencia de componente Tabs en shadcn/ui | Baja | - |
| 2 | Importar `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` en `tasks/[id]/page.tsx` | Baja | #1 |
| 3 | Importar `TranscriptTimeline` y `useCurrentOrg` | Baja | - |
| 4 | Reestructurar el layout con sistema de tabs | Media | #2, #3 |
| 5 | Integrar TranscriptTimeline en TabsContent | Baja | #3 |
| 6 | Testing visual: verificar renderizado de ambos tabs | Baja | #4, #5 |
| 7 | Verificar que el transcript funcione durante ejecución activa | Media | Require tarea en ejecución |

---

## 9. Testing

### Casos Críticos
1. **Tarea en ejecución:** Ver que el badge "En vivo" aparece y el realtime funciona
2. **Tarea terminada:** Ver que se muestra el historial sin indicadores de live
3. **Carga de snapshot:** Verificar que los eventos aparecen al cambiar al tab
4. **Navegación:** Cambiar entre tabs no debe recargar la página

---

## 🔮 Roadmap (NO implementar ahora)

- **Auto-seleccionar tab "Live Transcript"** cuando la tarea entra en estado `running` automáticamente
- **Notificación push** cuando hay nuevos eventos mientras el usuario está en el tab "Información"
- **Exportar transcript** como PDF o JSON
- **Filtrar por tipo de evento** dentro del componente (solo thoughts, solo tools, etc.)