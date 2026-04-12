# Análisis Técnico - Paso 3.3: TranscriptTimeline.tsx

## 1. Diseño Funcional

### Happy Path
1. Usuario accede a vista de tarea en ejecución
2. Componente TranscriptTimeline se monta y carga snapshot inicial de eventos vía API
3. Se establece suscripción realtime a tabla `domain_events` filtrando por `aggregate_id = task_id`
4. Eventos nuevos (flow_step, agent_thought, tool_output) aparecen en tiempo real en la timeline
5. Cada evento se anima suavemente al entrar en la vista
6. Usuario puede hacer scroll para ver historial completo

### Edge Cases
- Tarea sin eventos iniciales: mostrar mensaje "Esperando primeros eventos..."
- Conexión realtime falla: mostrar indicador de desconexión, intentar reconectar automáticamente
- Eventos llegan desordenados: ordenar por `sequence` para mantener cronología
- Grandes volúmenes de eventos: implementar virtualización o paginación para performance
- Usuario cambia de tab: mantener suscripción activa pero pausar animaciones

### Manejo de Errores
- Fallo en carga inicial: mostrar error con opción de reintentar
- Desconexión realtime: indicador visual de "Desconectado", reconexión automática cada 5s
- Evento corrupto: loggear warning, omitir sin romper la UI
- Timeout en suscripción: fallback a polling cada 10s como backup

## 2. Diseño Técnico

### Componentes Nuevos
- `TranscriptTimeline.tsx`: Componente principal con suscripción realtime
- `TranscriptEventItem.tsx`: Componente para renderizar evento individual con animación

### Interfaces
```typescript
interface TranscriptTimelineProps {
  taskId: string
  orgId: string
  className?: string
}

interface TranscriptEvent extends DomainEvent {
  sequence: number
}

interface TranscriptApiResponse {
  task_id: string
  flow_type: string
  status: string
  is_running: boolean
  sync: {
    last_sequence: number
    has_more: boolean
  }
  events: TranscriptEvent[]
}
```

### Modelos de Datos
- Extiende `DomainEvent` con `sequence` para ordenamiento
- Utiliza `last_sequence` del snapshot para filtrar eventos realtime duplicados
- Eventos filtrados por tipos: `flow_step`, `agent_thought`, `tool_output`

### Integraciones
- **Supabase Realtime**: Suscripción a `domain_events` con filtro `aggregate_id=eq.{taskId}`
- **API REST**: Endpoint `GET /transcripts/{taskId}` para snapshot inicial
- **useFlowTranscript hook**: Refactorizar para usar `last_sequence` en deduplicación

### Arquitectura
```
TranscriptTimeline
├── useFlowTranscript (hook existente, refactorizado)
│   ├── API snapshot (histórico)
│   └── Supabase realtime (nuevo)
├── TranscriptEventItem (nuevo)
│   ├── Animación entrada (framer-motion)
│   ├── Icono por tipo de evento
│   └── Formato payload legible
└── Estados: loading, error, live
```

Coherente con `estado-fase.md`: usa `TenantClient`, filtra por `org_id` y `task_id`, respeta contratos de API.

## 3. Decisiones

### Filtrado de Eventos Realtime
- **Decisión**: Implementar filtrado por `sequence > last_sequence` en el cliente para evitar duplicados con snapshot
- **Justificación**: El estado-fase especifica hand-off sincronizado. Mejor performance que filtrar en BD.
- **Impacto**: Reduce carga en realtime, asegura consistencia sin race conditions

### Animaciones Premium
- **Decisión**: Usar framer-motion para animaciones suaves de entrada (slide-in + fade)
- **Justificación**: Mejora UX en tiempo real, hace visible la actividad del agente
- **Alternativa considerada**: CSS transitions - descartada por complejidad de orquestación

### Virtualización para Performance
- **Decisión**: Implementar `react-window` si >50 eventos para mantener 60fps
- **Justificación**: Transcripts largos pueden tener cientos de eventos
- **Condición**: Solo activar si performance degrade detectada

### Tipos de Eventos Visuales
- **Decisión**: Diferenciar visualmente:
  - `flow_step`: icono gear, color azul
  - `agent_thought`: icono brain, color verde
  - `tool_output`: icono wrench, color naranja
- **Justificación**: Claridad cognitiva para usuarios técnicos

## 4. Criterios de Aceptación

- El componente TranscriptTimeline.tsx se crea en `dashboard/components/transcripts/TranscriptTimeline.tsx`
- La suscripción realtime se establece correctamente vía Supabase client
- Eventos de tipos `flow_step`, `agent_thought`, `tool_output` aparecen en tiempo real
- Animaciones suaves se aplican a nuevos eventos entrantes
- No hay duplicados entre snapshot inicial y eventos realtime
- Eventos se ordenan correctamente por `sequence`
- UI muestra indicador de conexión "En vivo" cuando suscripción activa
- Manejo de errores: desconexión muestra estado y reintenta automáticamente
- Performance: timeline maneja hasta 200 eventos sin lag perceptible

## 5. Riesgos

### Riesgo: Duplicados en Eventos
- **Probabilidad**: Media
- **Impacto**: Confusión en timeline, eventos repetidos
- **Mitigación**: Implementar filtrado estricto por `sequence > last_sequence`, validar en testing

### Riesgo: Performance con Muchos Eventos
- **Probabilidad**: Baja (eventos típicos <100)
- **Impacto**: UI lag, mala UX
- **Mitigación**: Implementar virtualización condicional, monitorear con React DevTools

### Riesgo: Conexión Realtime Inestable
- **Probabilidad**: Baja (Supabase robusto)
- **Impacto**: Eventos no aparecen en tiempo real
- **Mitigación**: Fallback a polling cada 10s, indicadores visuales de estado de conexión

### Riesgo: Eventos Desordenados
- **Probabilidad**: Baja (sequence incremental)
- **Impacto**: Cronología incorrecta
- **Mitigación**: Ordenamiento por sequence en cliente, validación en tests

## 6. Plan

### Tareas Atómicas

1. **Refactorizar useFlowTranscript hook** (Media)
   - Actualizar para usar `last_sequence` del snapshot
   - Filtrar eventos realtime con `sequence > last_sequence`
   - Mejorar manejo de estados de conexión

2. **Crear componente TranscriptEventItem** (Baja)
   - Renderizar evento individual con icono y animación
   - Formatear payload de manera legible por humanos
   - Soporte para tipos `flow_step`, `agent_thought`, `tool_output`

3. **Crear componente TranscriptTimeline** (Media)
   - Integrar useFlowTranscript hook
   - Implementar layout de timeline vertical
   - Añadir indicadores de estado (loading, live, error)

4. **Implementar animaciones premium** (Media)
   - Usar framer-motion para entrada suave de eventos
   - Animación staggered para múltiples eventos simultáneos
   - Transiciones suaves en cambios de estado

5. **Testing de suscripción realtime** (Baja)
   - Validar hand-off snapshot/realtime sin duplicados
   - Probar reconexión automática tras desconexión
   - Verificar ordenamiento por sequence

### Dependencias
- Tarea 1 debe completarse antes de 3
- Tareas 2 y 4 pueden paralelizarse con 3
- Tarea 5 requiere todas las anteriores completadas

## 🔮 Roadmap

### Optimizaciones Futuras
- **Virtualización**: Implementar react-window para transcripts muy largos (>500 eventos)
- **Filtros Interactivos**: Permitir ocultar/mostrar tipos específicos de eventos
- **Búsqueda**: Buscar en payloads de eventos
- **Export**: Opción de exportar transcript completo como JSON/Markdown
- **Notificaciones**: Alertas push para eventos críticos (errores, completion)

### Mejoras de Arquitectura
- **WebSockets Directos**: Reemplazar Supabase realtime por WebSocket nativo si latencia >100ms consistente
- **Compresión**: Comprimir payloads grandes de tool_output para reducir bandwidth
- **Offline Support**: Cache local de transcripts para acceso sin conexión

### Decisiones de Diseño Tomadas
- **Snapshot First**: Priorizar carga inicial rápida sobre realtime inmediato
- **Sequence-based Ordering**: Confiar en sequence del backend para cronología exacta
- **No Polling Fallback**: Usar polling solo como último recurso, preferir reconexión realtime</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md