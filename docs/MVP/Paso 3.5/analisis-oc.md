# Análisis — Paso 3.5: Test de Latencia (< 1s)

## 1. Diseño Funcional

### 1.1 Happy Path Detallado

1. **Inicialización**: El usuario abre una tarea en ejecución (`status: running`)
2. **Snapshot**: El hook `useTranscriptTimeline` carga el historial inicial via REST API `/transcripts/{task_id}`
3. **Suscripción**: Se establece conexión WebSocket via Supabase Realtime al canal `transcript-timeline:{task_id}`
4. **Evento emititdose**: El flow ejecutor emite eventos via `EventStore.append()` → `flush()`
5. **Realtime triggered**: Supabase detecta INSERT en `domain_events` y推送 al cliente
6. **Visualización**: El hook procesa el evento, lo agrega al estado, y el Timeline lo renderiza
7. **Latencia medida**: El tiempo entre paso 4 y paso 6 debe ser < 1 segundo

### 1.2 Edge Cases MVP

- **Task terminada antes de suscripción**: Si la task no está en `running`, no se inicia Realtime (línea 120-123 de `useTranscriptTimeline.ts`)
- **Duplicados post-snapshot**: Se descartan eventos con `sequence <= last_sequence` (línea 84-85)
- **Desconexión temporal**: Reintento automático con backoff cada 5s, hasta 3 intentos (líneas 140-155)
- **Eventos fuera de orden**: Se reordena por `sequence` antes de renderizar (línea 92)

### 1.3 Manejo de Errores

- **ConnectionStatusBadge**: Muestra estado visual (`connected` | `connecting` | `disconnected` | `error`)
- **Fallo de suscripción**: Botón de reconexión manual disponible via `reconnect()`
- **Task завершена**: La pestaña de Transcript muestra el estado final sin live badge

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Rol | Estado |
|-------------|-----|--------|
| `EventStore.flush()` | Persiste evento en `domain_events` | Implementado |
| `GET /transcripts/{task_id}` | Snapshot REST | Implementado (Paso 3.2) |
| `useTranscriptTimeline.ts` | Lógica de subscripción y estado | Implementado (Paso 3.3) |
| `TranscriptTimeline.tsx` | Renderizado visual | Implementado (Paso 3.4) |
| `test_streaming_latency.py` | Script de validación | Implementado |

### 2.2 Flujo de Datos

```
Flow execution
     │
     ▼
EventStore.append() ──► domain_events (INSERT)
     │
     ▼ (supabase_realtime)
WebSocket push al cliente
     │
     ▼
useTranscriptTimeline (postgres_changes listener)
     │
     ▼
setEvents() → React re-render
     │
     ▼
Timeline renderiza evento
```

### 2.3 Contratos Existentes (respetados)

- **Canal**: `task_transcripts:{task_id}` (el código usa `transcript-timeline:{task_id}`, coherente funcionalmente)
- **Filtro**: `aggregate_id=eq.{task_id}` (línea 78 de `useTranscriptTimeline.ts`)
- **Eventos**: `flow_step`, `agent_thought`, `tool_output` (filtrados implícitamente por el tipo de query)

---

## 3. Decisiones

### 3.1 Decisión: Umbral de 1 segundo

**Justificación**: 
- Umbral alineado con criterios de aceptación del MVP (sección 6 de `estado-fase.md`)
- Supabase Realtime típicamente tiene latencia de 50-200ms
- La persistencia del evento (`EventStore.flush()`) añade 10-100ms típico
- Margen razonable para UI render

### 3.2 Decisión: Script de validación standalone

**Justificación**:
- El script `test_streaming_latency.py` puede ejecutarse de forma independiente
- No requiere infraestructura de test adicionales (pytest optional)
- Incluye 3 tests: latencia de emisión, verificación de Realtime, y endpoint response

---

## 4. Criterios de Aceptación

| # | Criterio | Verificación |
|---|----------|--------------|
| 1 | El script `test_streaming_latency.py` ejecuta sin errores | Ejecutar `python src/scripts/test_streaming_latency.py` |
| 2 | La latencia máxima medida es < 1000ms | Output del test muestra `max_latency < 1000ms` |
| 3 | El endpoint `/transcripts/{task_id}` responde correctamente | Verificado en test 3 |
| 4 | La suscripción Realtime se establece correctamente | Verificado en test 2 |
| 5 | Los eventos se visualizan en el Timeline sin duplicados | Verificación manual en UI |
| 6 | El `ConnectionStatusBadge` muestra estado correcto | Verificación manual en UI |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Latencia alta por índices faltantes** | Media | Alto | Verificar existencia de índice en `aggregate_id` (test incluye verificación) |
| **Supabase Realtime no llega al cliente por firewall/cors** | Baja | Alto | El ConnectionStatusBadge permite diagnóstico visual |
| **Race condition en deduplicación** | Baja | Medio | El código ya filtra por `sequence <= last_sequence` |
| **Eventos perdidos por reconexión rápida** | Baja | Medio | El snapshot siempre está disponible como fallback |

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|---------------|
| 1 | Ejecutar script `test_streaming_latency.py` | Baja | Ninguna |
| 2 | Verificar que todos los 3 tests pasan | Baja | #1 |
| 3 | Validar visualmente en UI con una tarea real | Media | #2, requiere frontend corriendo |
| 4 | Documentar resultados en el registro de fase | Baja | #3 |

### Estimación Total

- **Complejidad Baja**: Script ya existe, solo ejecutar y validar
- **Tiempo estimado**: 30 minutos (ejecución + validación visual)

---

## 🔮 Roadmap (NO implementar ahora)

1. **Métricas de latencia en producción**: Recolectar latencia real via telemetría para monitoring continuo
2. **Alertas automatizadas**: Notificar si latencia > umbral sostenido
3. **Optimización de batch**: Para flows con alta frecuencia de eventos, implementar batch de eventos antes de flush
4. **Fallback a polling**: Si Realtime falla persistentemente, caer a polling como fallback
5. **Test de carga**: Validar comportamiento con >100 eventos/segundo