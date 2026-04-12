# 🧠 ANÁLISIS TÉCNICO - PASO 3.3: TranscriptTimeline.tsx

## 1. Diseño Funcional

### 1.1 Propósito del Componente
Componente de visualización en tiempo real que muestra el progreso de ejecución de un Flow run, renderizando pensamientos de agentes, acciones de herramientas y pasos del flujo con animaciones premium de entrada.

### 1.2 Inputs del Componente
```typescript
interface TranscriptTimelineProps {
  events: TranscriptEvent[]        // Del hook useFlowTranscript
  flowType?: string               // Para determinar el ícono/título del flow
  status?: string                 // 'running' | 'done' | 'failed' | etc
  isLive?: boolean               // Indicador de stream activo
  isLoading?: boolean            // Estado inicial de carga
  onRetry?: () => void          // Callback para reintentar si hay error
}

interface TranscriptEvent {
  id: string
  event_type: 'flow_step' | 'agent_thought' | 'tool_output'
  payload: Record<string, unknown>
  sequence: number
  created_at: string
  actor?: string                 // Opcional, nombre del agente
}
```

### 1.3 Happy Path
1. **Estado de Carga Inicial:** Skeleton con 3-4 items simulados (pulsing animation)
2. **Carga Exitosa:** Lista de eventos ordenados por `sequence` ascendente
3. **Stream en Vivo:** Nuevos eventos aparecen arriba con slide-in animation + badge "LIVE"
4. **Estado Terminal:** Badge de estado final (SUCCESS/FAILED), sin más animaciones de entrada

### 1.4 Tipos de Evento y Visualización

| Event Type | Badge Color | Ícono | Contenido del Payload |
|------------|-------------|-------|----------------------|
| `flow_step` | Info (Azul) | GitBranch | `step_name`, `agent_id`, `status` |
| `agent_thought` | Warning (Amarillo) | Brain | `thought`, `agent_id` |
| `tool_output` | Secondary (Gris) | Wrench | `tool_name`, `output` (truncado a 200 chars) |

### 1.5 Edge Cases MVP
- **Payload vacío:** Mostrar "Sin detalles" en texto muted
- **Tool output muy largo:** Truncar a 200 chars con "..." y expandir en click
- **Evento sin actor:** Mostrar "Sistema" como fallback
- ** sequence undefined:** Ordenar por `created_at` como fallback
- **Lista vacía:** Empty state con ícono de check si `status` es terminal, o Activity si está running

### 1.6 Manejo de Errores
- **Error de Red:** Toast de error + botón "Reintentar" visible
- **Canal Realtime desconectado:** Badge "OFFLINE" con color warning, auto-reintento cada 5s
- **Sin permisos:** No debería ocurrir si el hook filtra correctamente por org

---

## 2. Diseño Técnico

### 2.1 Ubicación y Estructura de Archivos
```
dashboard/
├── components/
│   └── transcripts/
│       ├── TranscriptTimeline.tsx      # Componente principal
│       ├── TranscriptItem.tsx          # Item individual (opcional, para complejidad)
│       └── TranscriptItemSkeleton.tsx  # Skeleton loading
├── hooks/
│   └── useFlowTranscript.ts            # YA EXISTE - NO MODIFICAR
```

### 2.2 Componente Principal: TranscriptTimeline.tsx

```typescript
// Schema de Props
interface TranscriptTimelineProps {
  events: TranscriptEvent[]
  flowType?: string
  status?: string
  isLive?: boolean
  isLoading?: boolean
  onRetry?: () => void
}

// Estados internos
type ViewState = 'loading' | 'empty' | 'live' | 'done' | 'error'

// Variantes de badge por event_type
const EVENT_CONFIG = {
  flow_step: { variant: 'info', icon: GitBranch, label: 'Step' },
  agent_thought: { variant: 'warning', icon: Brain, label: 'Thought' },
  tool_output: { variant: 'secondary', icon: Wrench, label: 'Tool' },
} as const
```

### 2.3 Animaciones Premium (Framer Motion)

| Elemento | Animación | Config |
|----------|-----------|--------|
| Item nuevo entrada | `slideInUp` + `fadeIn` | `duration: 0.4, ease: [0.22, 1, 0.36, 1]` |
| Live badge | `pulse` continuo | `scale: [1, 1.05, 1], repeat: Infinity` |
| Skeleton items | `pulse` stagger | `0.1s delay` entre items |
| Expansión tool output | `expand` | `duration: 0.3` |
| Timeline dot activo | `glow` | `boxShadow: pulse on accent color` |

### 2.4 Modelo de Datos para Visualización

```typescript
// Normalización del evento para visualización
interface NormalizedEvent {
  id: string
  type: 'flow_step' | 'agent_thought' | 'tool_output'
  title: string                    // Texto principal
  subtitle?: string                 // Detalle secundario
  timestamp: string                // formatted (e.g., "hace 2 min")
  rawPayload: Record<string, unknown>
  isExpandable: boolean            // true si tool_output tiene más de 200 chars
  status?: 'pending' | 'running' | 'completed' | 'failed'
}
```

### 2.5 Componentes UI Shadcn a Utilizar
- `Card` + `CardContent` - Contenedor del timeline
- `Badge` - Tipos de evento y status
- `ScrollArea` - Área scrolleable con altura máxima
- `Button` - Retry action
- `Separator` - Líneas divisorias
- `Tooltip` - Para truncated text

### 2.6 Dependencias Existentes a Reutilizar
- `useFlowTranscript` hook - YA IMPLEMENTADO
- `DomainEvent` type - YA DEFINIDO en `dashboard/lib/types.ts`
- Shadcn/ui components - YA DISPONIBLES en `dashboard/components/ui/`
- `CodeBlock` component - YA EXISTE en `dashboard/components/shared/CodeBlock.tsx`
- `date-fns` con locale `es` - YA CONFIGURADO en `EventTimeline.tsx`

---

## 3. Decisiones

### 3.1 Framer Motion vs CSS Animations
**Decisión:** Usar **Framer Motion** para animaciones de entrada.
**Justificación:** Las animaciones de stagger y slide-in son más suaves y declarativas. El proyecto ya usa Lucide icons que son compatibles.
**Nota:** Verificar si `framer-motion` está instalado. Si no lo está, usar CSS animations con `@keyframes`.

### 3.2 Altura Máxima del Timeline
**Decisión:** Altura máxima de `400px` con `ScrollArea`.
**Justificación:** En el contexto de Task Detail view, el transcript no debe dominar la pantalla. El scroll permite explorar eventos históricos.

### 3.3 Normalización de Eventos en el Componente
**Decisión:** El componente normaliza los eventos crudos de `DomainEvent` a `NormalizedEvent`.
**Justificación:** Separa la lógica de presentación de la estructura de datos de la API. Facilita testing y mantenimiento.

### 3.4 Truncamiento de Tool Output
**Decisión:** Truncar a 200 caracteres con expansión en click.
**Justificación:** Los outputs de herramientas pueden ser muy largos (JSON dumps). El truncamiento mantiene la UI limpia.

### 3.5 Fallback de sequence
**Decisión:** Usar `created_at` como fallback para ordenar si `sequence` es undefined.
**Justificación:** Compatibilidad con eventos legacy que podrían no tener sequence. El backend ya provee sequence en el Paso 3.2.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| 1 | El componente acepta `events: TranscriptEvent[]` como prop | ✅ TypeScript valida |
| 2 | Skeleton de carga aparece cuando `isLoading=true` | ✅ UI muestra 3 items pulsantes |
| 3 | Empty state aparece cuando `events=[]` y `status` es terminal | ✅ Muestra "check" o "Activity" según estado |
| 4 | Eventos `flow_step` muestran badge azul con ícono GitBranch | ✅ Badge variant="info" |
| 5 | Eventos `agent_thought` muestran badge amarillo con ícono Brain | ✅ Badge variant="warning" |
| 6 | Eventos `tool_output` muestran badge gris con ícono Wrench | ✅ Badge variant="secondary" |
| 7 | Tool outputs >200 chars se truncan con "..." y expanden en click | ✅ Interacción toggle |
| 8 | Badge "LIVE" aparece cuando `isLive=true` | ✅ Visible con animación pulse |
| 9 | Badge de estado terminal (SUCCESS/FAILED) aparece cuando `status` es terminal | ✅ Badge variant success/destructive |
| 10 | Nuevos eventos aparecen con slide-in animation desde arriba | ✅ Framer Motion slideInUp |
| 11 | El timeline es scrollable con altura máxima de 400px | ✅ ScrollArea con h-[400px] |
| 12 | Retry button aparece cuando `onRetry` está definido y hay error | ✅ Botón visible en estado error |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Framer Motion no instalado | Baja | Medio | Instalar con `npm install framer-motion` o usar CSS fallback |
| Eventos con payload muy grande causan lag | Media | Medio | Truncar a 200 chars, lazy render si >50 eventos |
| Realtime se desconecta sin recuperación | Baja | Alto | Auto-reconexión cada 5s con max 3 intentos |
| Orden de eventos incorrecto por race condition | Baja | Medio | Deduplicación por `id` + sort por `sequence` antes de render |

---

## 6. Plan de Implementación

### Tarea 1: Crear estructura de archivos
- Crear `dashboard/components/transcripts/TranscriptTimeline.tsx`
- **Complejidad:** Baja
- **Dependencias:** Ninguna

### Tarea 2: Implementar TranscriptTimeline con skeleton y empty state
- Estados: loading, empty, error
- Badge variants para cada event_type
- **Complejidad:** Media
- **Dependencias:** Tarea 1

### Tarea 3: Implementar animaciones premium
- Framer Motion slideInUp para nuevos items
- Pulse animation para live badge
- Skeleton stagger animation
- **Complejidad:** Media
- **Dependencias:** Tarea 2

### Tarea 4: Implementar expansión de tool outputs
- Toggle click para expandir/colapsar
- Truncamiento a 200 chars
- **Complejidad:** Baja
- **Dependencias:** Tarea 2

### Tarea 5: Integración con el hook useFlowTranscript
- Probar en Task Detail view (Paso 3.4)
- Validar hand-off snapshot → realtime
- **Complejidad:** Media
- **Dependencias:** Tareas 1-4 + Hook existente

### Orden Recomendado: 1 → 2 → 4 → 3 → 5

---

## 6. Roadmap (NO implementar ahora)

### Optimizaciones Post-MVP
1. **Virtualización de lista:** Si >100 eventos, usar `react-virtual` para evitar lag
2. **Búsqueda en transcript:** Ctrl+F para buscar dentro de eventos
3. **Exportar transcript:** Botón para descargar como JSON/Markdown
4. **Highlight de sintaxis:** Para tool outputs JSON, usar `react-syntax-highlighter`
5. **Auto-scroll inteligente:** Si el usuario hizo scroll manual, no auto-scroll; si está arriba, sí
6. **Persistencia de expansión:** Guardar estado expandido/colapsado en localStorage
