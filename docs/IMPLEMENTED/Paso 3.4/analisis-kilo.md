# Análisis Técnico - Paso 3.4: Integración Live Transcript en Vista de Tarea

## 1. Diseño Funcional

### Happy Path
1. Usuario navega a `/tasks/{id}` durante ejecución activa
2. Página carga con pestaña "Live Transcript" seleccionada por defecto (cuando `task.status === 'running'`)
3. TranscriptTimeline muestra eventos históricos del snapshot inicial
4. Eventos nuevos aparecen en tiempo real vía Supabase Realtime
5. Auto-scroll mantiene el foco en eventos más recientes
6. Indicador "En vivo" con animación confirma conectividad activa

### Edge Cases
- **Tarea terminada**: Pestaña "Información" seleccionada por defecto, Live Transcript disponible pero sin indicadores de live
- **Sin eventos**: Mensaje "Esperando eventos del agente..." durante ejecución, "Sin eventos para esta tarea" cuando terminada
- **Conexión perdida**: Banner amarillo con botón "Reintentar", eventos históricos permanecen visibles
- **Usuario manual scroll**: Auto-scroll se desactiva, aparece botón "Ir al final" con contador de eventos nuevos
- **Paginación**: Botón "Cargar anteriores" cuando `has_more = true`

### Manejo de Errores
- **Error de conexión realtime**: Banner con ícono AlertTriangle, texto explicativo, botón "Reintentar"
- **Error de API snapshot**: LoadingSpinner indefinido (manejo por React Query)
- **Tarea no encontrada**: Mensaje "Tarea no encontrada" (ya implementado)
- **Payload malformado**: TimelineEvent renderiza fallback sin fallar la UI completa

## 2. Diseño Técnico

### Componentes Nuevos/Modificaciones
- **tasks/[id]/page.tsx**: Añadir estructura de Tabs con dos pestañas:
  - "Información": Contenido actual (task info + EventTimeline legacy)
  - "Live Transcript": Nuevo contenedor con TranscriptTimeline
- **Estado de pestaña por defecto**: Lógica condicional basada en `task.status`

### Interfaces
- **Props TranscriptTimeline**: `taskId: string, orgId: string` (ya implementado)
- **Hook useTranscriptTimeline**: Retorna estado completo necesario (ya implementado)
- **Integración tabs**: Usar componentes shadcn/ui `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`

### Modelos de Datos
- Sin cambios: Reutiliza `DomainEvent` extendido como `TranscriptEvent` con campo `sequence`
- Snapshot mantiene estructura existente: `{task_id, status, is_running, sync: {last_sequence, has_more}, events: []}`

### Integraciones
- **Supabase Realtime**: Canal `task_transcripts:{task_id}` con filtro `aggregate_id=eq.{task_id}` (ya configurado)
- **API REST**: Endpoint `GET /transcripts/{task_id}` para snapshot inicial (ya implementado)
- **UI existente**: Reutiliza StatusLabel, BackButton, LoadingSpinner del design system

## 3. Decisiones

### Arquitectura de Navegación
- **Decisión**: Mantener página única con tabs en lugar de redirección automática
- **Justificación**: Mejor UX que permite comparación entre información estática y transcript dinámico
- **Impacto**: Usuario controla navegación, evita confusión de redirecciones automáticas

### Comportamiento por Estado de Tarea
- **Decisión**: Pestaña por defecto basada en estado:
  - `running`: "Live Transcript" 
  - `done/failed/blocked`: "Información"
- **Justificación**: Enfoque en supervisión durante ejecución, resumen cuando terminada
- **Implementación**: Condicional en componente page basado en `task.status`

### Reutilización vs Duplicación
- **Decisión**: Reutilizar TranscriptTimeline existente sin modificaciones
- **Justificación**: Componente ya validado en paso 3.3, evita regresiones
- **Alternativa descartada**: Crear versión "embedded" simplificada

## 4. Criterios de Aceptación

- La página `tasks/[id]/page.tsx` muestra dos pestañas: "Información" y "Live Transcript"
- Durante ejecución activa (`task.status === 'running'`), la pestaña "Live Transcript" está seleccionada por defecto
- El componente TranscriptTimeline se renderiza correctamente dentro de la pestaña Live Transcript
- Los eventos históricos se cargan desde el snapshot inicial sin duplicados
- Los eventos nuevos aparecen en tiempo real cuando la tarea está ejecutándose
- El botón "Ir al final" aparece cuando el usuario hace scroll manual y hay eventos nuevos
- El banner de error de conexión aparece cuando falla el realtime y permite reconexión manual
- La funcionalidad de "Cargar anteriores" funciona cuando hay más eventos disponibles
- La pestaña "Información" mantiene todo el contenido actual sin modificaciones
- No hay errores de consola ni warnings durante navegación entre pestañas

## 5. Riesgos

### Riesgo de Performance con Eventos Masivos
- **Probabilidad**: Media (usuarios con tareas complejas generando cientos de eventos)
- **Impacto**: Alto (UI freeze, alto consumo de memoria)
- **Mitigación**: Virtualización futura (react-window), límite de eventos en memoria (500-1000), paginación agresiva

### Riesgo de UX Confusa con Múltiples Timelines
- **Probabilidad**: Baja (diferenciación clara entre pestañas)
- **Impacto**: Medio (usuarios confundiendo EventTimeline legacy vs TranscriptTimeline)
- **Mitigación**: Nombres descriptivos ("Timeline de Eventos" vs "Live Transcript"), documentación clara

### Riesgo de Inconsistencia Visual
- **Probabilidad**: Baja (reutilización de componentes validados)
- **Impacto**: Bajo (diferencias estéticas menores)
- **Mitigación**: Testing visual, comparación de screenshots entre estados

## 6. Plan

### Tareas Atómicas Ordenadas

1. **Crear estructura de tabs en page.tsx** (Baja complejidad - 15min)
   - Importar componentes Tabs de shadcn/ui
   - Envolver contenido existente en TabsContent "Información"
   - Crear TabsContent vacío para "Live Transcript"

2. **Implementar lógica de pestaña por defecto** (Baja complejidad - 10min)
   - Condicional `defaultValue` basado en `task.status === 'running'`

3. **Integrar TranscriptTimeline component** (Baja complejidad - 5min)
   - Importar TranscriptTimeline
   - Renderizar en TabsContent "Live Transcript" con props taskId y orgId

4. **Ajustar layout responsive** (Media complejidad - 20min)
   - Verificar que tabs funcionen en mobile
   - Ajustar espaciado si necesario

5. **Testing funcional básico** (Media complejidad - 30min)
   - Verificar navegación entre tabs
   - Confirmar renderizado TranscriptTimeline
   - Validar estado por defecto según task.status

6. **Testing de integración realtime** (Alta complejidad - 45min)
   - Ejecutar tarea real y verificar eventos en vivo
   - Probar desconexión/reconexión
   - Validar auto-scroll y paginación

### Dependencias
- Tarea 2 depende de 1 (necesita estructura tabs)
- Tarea 3 depende de 1 (necesita TabsContent)
- Tarea 5 depende de 1,2,3 (testing completo)
- Tarea 6 depende de 5 (testing básico aprobado)

### Estimación Total: 2 horas
- **Desarrollo**: 50min (tareas 1-4)
- **Testing**: 75min (tareas 5-6)
- **Buffer**: 15min (ajustes menores)

---

## 🔮 Roadmap (NO implementar ahora)

### Optimizaciones de Performance
- Implementar virtualización para timelines con >1000 eventos
- Lazy loading de TranscriptTimeline solo cuando se selecciona la pestaña
- Compresión de payloads grandes en tool_output events

### Mejoras de UX
- Persistencia de pestaña seleccionada por usuario (localStorage)
- Notificaciones push para eventos importantes durante ejecución
- Modo fullscreen para Live Transcript durante debugging intensivo

### Features Futuras
- Filtros por tipo de evento (solo pensamientos, solo herramientas)
- Búsqueda dentro del transcript
- Exportación de transcript a PDF/JSON
- Comparación side-by-side de múltiples tareas

### Decisiones de Arquitectura tomadas pensando en futuro:
- Estructura de tabs extensible para añadir "Analytics", "Logs", etc.
- Component TranscriptTimeline diseñado como unidad reusable
- Separación clara entre snapshot (histórico) y realtime (nuevo) facilita caching avanzado</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md