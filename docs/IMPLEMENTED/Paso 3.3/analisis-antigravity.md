# 🧠 ANÁLISIS TÉCNICO: PASO 3.3 - Frontend Transcript Timeline

## 1. Diseño Funcional

### Happy Path
1. El usuario accede a la vista de una Tarea (Task) en ejecución.
2. El componente `TranscriptTimeline` recibe el snapshot inicial del backend (`GET /transcripts/{task_id}`).
3. Se renderizan los eventos existentes con una animación de entrada "staggered" (cascada suave).
4. El componente se suscribe a Supabase Realtime para la tabla `domain_events` filtrando por el `task_id`.
5. A medida que el agente "piensa" o "ejecuta herramientas", aparecen nuevas entradas en el timeline de forma instantánea.
6. La vista hace auto-scroll suave hacia el evento más reciente si el usuario está al final de la lista.

### Edge Cases (MVP)
- **Desconexión de Realtime:** Si el socket se cae, el componente debe mostrar un indicador sutil de "Reconectando..." pero mantener los eventos actuales.
- **Eventos Duplicados (Hand-off):** Al pasar del snapshot (REST) a Realtime, pueden llegar eventos que ya estaban en el snapshot. El componente usará `last_sequence` para descartar duplicados (`evt.sequence <= last_sequence`).
- **Payloas Gigantes:** Si un `tool_output` devuelve un JSON masivo, se mostrará colapsado o con un límite de líneas y un botón "Ver más".
- **Tarea Finalizada:** Si el snapshot indica `is_running: false`, se omite la suscripción a Realtime para ahorrar recursos.

### Manejo de Errores
- **Error de Carga Inicial:** Si el fetch del snapshot falla, se muestra un `EmptyState` con botón de reintentar.
- **Payload Corrupto:** Si un evento llega con campos faltantes, se renderiza un log genérico de "Evento Desconocido" para no romper la UI.

---

## 2. Diseño Técnico

### Componentes Sugeridos
1. `TranscriptTimeline.tsx`: Orquestador principal. Maneja estado de eventos y suscripción.
2. `items/ThoughtItem.tsx`: Especializado en `agent_thought`. Estilo narrativo, burbuja de pensamiento.
3. `items/ToolItem.tsx`: Especializado en `tool_output`. Estilo técnico, bloque de código reactivo.
4. `items/StepItem.tsx`: Especializado en `flow_step`. Representación de hitos de proceso.

### Hook: `useTranscript(taskId: string)`
Encapsula la lógica compleja:
- Fetch inicial al endpoint `/api/transcripts/{taskId}`.
- Suscripción a `domain_events`.
- Deduplicación lógica basada en `sequence`.
- Retorno de `{ events: DomainEvent[], isRunning: boolean, isLoading: boolean }`.

### Modelos de Datos (Frontend)
```typescript
interface TranscriptSync {
  last_sequence: number;
  has_more: boolean;
}

interface TranscriptResponse {
  task_id: string;
  flow_type: string;
  status: TaskStatus;
  is_running: boolean;
  sync: TranscriptSync;
  events: DomainEvent[];
}
```

---

## 3. Decisiones

1. **Framer Motion para el Stream:** Se usará `layoutEffect` y `AnimatePresence` para que los nuevos eventos "empujen" a los anteriores o aparezcan con un fade-in + slide-up, dando una sensación premium de "sistema vivo".
2. **Deduplicación por Sequence:** No confiaremos en IDs para la deduplicación en el hand-off REST-to-Realtime, sino en el campo `sequence` que es monótonamente creciente en la base de datos (garantía técnica del Paso 3.2).
3. **Auto-scroll Condicional:** Solo se activará el scroll automático si el scroll del usuario está a menos de 100px del fondo, evitando interrumpir al usuario si está leyendo eventos pasados.

---

## 4. Criterios de Aceptación (NUEVO)

- [ ] El componente carga el snapshot histórico al montarse.
- [ ] Se descartan eventos de Realtime con `sequence` menor o igual al `last_sequence` del snapshot.
- [ ] Los pensamientos del agente (`agent_thought`) tienen un estilo visual distinto (ej. fuente itálica, fondo suave).
- [ ] Los outputs de herramientas (`tool_output`) se muestran en bloques de código con sintaxis resaltada o JSON formateado.
- [ ] La entrada de nuevos eventos tiene una animación suave de menos de 400ms.
- [ ] Si la tarea cambia a estado terminal (`done`, `failed`), se muestra un evento final de "Ejecución Finalizada".
- [ ] Cumple con aislamiento multi-tenant (solo ve eventos del `aggregate_id` / `task_id` autorizado).

---

## 5. Riesgos

- **Riesgo:** Saturación de la UI por ráfagas de eventos (ej. un flow que genera 100 eventos en 1 segundo).
  - **Mitigación:** Implementar un pequeño buffer o `requestAnimationFrame` para procesar el renderizado de eventos si la frecuencia excede un umbral.
- **Riesgo:** Desfase entre estados de la tarea y eventos (ej. la tarea termina pero el evento de finalización tarda en llegar).
  - **Mitigación:** El componente escuchará tanto los eventos como el estado de la tarea en el snapshot.

---

## 6. Plan

1. **Tarea 1 [Lib]:** Definir interfaces `TranscriptResponse` y `TranscriptSync` en `lib/types.ts`. (Complejidad: Baja)
2. **Tarea 2 [Hooks]:** Crear `hooks/useTranscript.ts` con lógica de fetch + suscripción realtime. (Complejidad: Media)
3. **Tarea 3 [UI]:** Implementar átomos visuales (`ThoughtItem`, `ToolItem`) con Tailwind + Framer Motion. (Complejidad: Media)
4. **Tarea 4 [UI]:** Ensamblar `TranscriptTimeline.tsx` con soporte para auto-scroll. (Complejidad: Media)
5. **Tarea 5 [Integration]:** Mockear datos y verificar animaciones en una página temporal de test. (Complejidad: Baja)

---

### Sección Final: 🔮 Roadmap
- **Timeline Interactivo:** Permitir hacer clic en un `tool_output` para expandir el payload completo en un modal lateral.
- **Filtros de Visibilidad:** Permitir al usuario ocultar los "pensamientos" para ver solo acciones y resultados de herramientas.
- **Estimación de Tiempo:** Mostrar cuánto tiempo pasó entre un evento y otro.
