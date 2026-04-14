# 🧠 ANÁLISIS TÉCNICO — Paso 3.5: Test de Latencia de Transcripts

**Agente:** qwen  
**Fecha:** 2026-04-12  
**Fase:** 3 - Real-Time Run Transcripts  
**Paso:** 3.5 [Validación]

---

## 1. Diseño Funcional

### Happy Path
1. **Trigger del Test:** El validador ejecuta un script de prueba que inicia una tarea de IA con un flow conocido que genera eventos predecibles (`flow_step`, `agent_thought`, `tool_output`).
2. **Captura de Timestamps:** 
   - El backend registra un timestamp de alta resolución (`time.perf_counter_ns()` o equivalente) en el momento exacto en que cada evento se inserta en `domain_events`.
   - El frontend captura el timestamp de recepción y renderizado de cada evento en el componente `TranscriptTimeline`.
3. **Cálculo de Latencia:** Se compara el delta entre:
   - `t_insert`: Evento escrito en DB.
   - `t_render`: Evento visible en UI del usuario.
4. **Reporte:** El test genera un reporte con latencia media, p95, p99 y máximo.

### Edge Cases
- **Primera Conexión:** La latencia del primer evento puede ser mayor debido al handshake de WebSocket. Se debe medir por separado o excluir del promedio.
- **Eventos en Ráfaga:** Si un flow genera 5+ eventos en <100ms, el frontend puede recibirlos agrupados. Validar que el renderizado de cada uno no cause blocking.
- **Degradación de Red:** Simular throttling de red (3G) para verificar que la latencia se mantiene aceptable en condiciones no ideales.

### Manejo de Errores
- Si el canal de Realtime se desconecta durante el test, el script debe detectar la desconexión, reportarla como "fail" y reintentar la suscripción.
- Si un evento no llega después de un timeout (ej. 5s), se marca como "lost" y se reporta con su secuencia.

---

## 2. Diseño Técnico

### Componente 1: Script de Test Automatizado
- **Ubicación propuesta:** `LAST/test_3_5_latency.py`
- **Inputs:**
  - `task_id`: ID de una tarea que se ejecutará para el test.
  - `expected_events`: Lista de tipos de eventos que se esperan generar.
  - `threshold_ms`: Umbral de latencia aceptable (default: 1000ms).
- **Outputs:**
  - Reporte JSON con métricas: `{ total_events, avg_latency_ms, p95_latency_ms, p99_latency_ms, max_latency_ms, events_lost, connection_state }`
  - Exit code: `0` si pasa, `1` si falla.

### Componente 2: Instrumentación del Backend (Temporal para Test)
- Se necesita un endpoint o mecanismo para obtener los timestamps de inserción de los eventos de una tarea específica.
- **Opción A (Recomendada):** El endpoint existente `GET /transcripts/{task_id}` ya devuelve los eventos. Se puede añadir un campo `db_inserted_at` (ISO 8601 con milisegundos) al payload de cada evento.
- **Opción B:** Query directa a Supabase desde el script de test (requiere credenciales de DB, menos limpio pero más preciso).

### Componente 3: Instrumentación del Frontend
- El hook `useTranscriptTimeline.ts` debe ser extendido para registrar un timestamp de renderizado por evento.
- **Mecanismo:** Al recibir un nuevo evento del stream o del snapshot, registrar `performance.now()` en un mapa `{ event_id: render_timestamp }`.
- **Export de Métricas:** Durante el test, el script puede inyectar un callback o usar `window.__LATENCY_METRICS__` para leer los datos desde el contexto del navegador (si se usa Playwright/Puppeteer), o alternativamente, calcular la latencia puramente desde el script de backend comparando timestamps de DB.

### Modelo de Datos (Extensión Temporal)
```
domain_events (tabla existente)
  + inserted_at: TIMESTAMPTZ DEFAULT NOW() (si no existe ya)
```
> **Nota:** Supabase añade automáticamente `created_at` si la migración `022_enable_realtime_events.sql` lo incluyó. Verificar.

### Flujo de Integración del Test
```
1. Script crea tarea de test → POST /tasks → { task_id }
2. Script inicia suscripción Realtime → canal `task_transcripts:{task_id}`
3. Script ejecuta tarea → POST /tasks/{task_id}/execute
4. Por cada evento recibido en Realtime:
   - Captura t_receive (cliente)
   - Extrae t_insert del payload (servidor/DB)
   - Calcula delta = t_receive - t_insert
5. Al finalizar la tarea (status != running):
   - Calcula estadísticas
   - Compara contra threshold (1000ms)
   - Genera reporte
```

---

## 3. Decisiones

| Decisión | Justificación |
|----------|---------------|
| **Test automatizado (no manual)** | La latencia no se puede validar consistentemente con inspección visual. Se necesita medición programática con métricas cuantificables. |
| **Usar timestamp de DB como referencia** | El `inserted_at` de la DB es la fuente de verdad más confiable para el momento del evento. Evita sesgos por latency de red del lado del emisor. |
| **No instrumentar el frontend para este test MVP** | Medir latencia end-to-end real desde la perspectiva del script de backend es suficiente para validar el criterio de <1s. La instrumentación frontend añade complejidad que se puede diferir. |
| **Script independiente, no test unitario** | Este es un test de integración E2E que requiere infraestructura real (Supabase, backend corriendo). No tiene sentido como test unitario aislado. |

---

## 4. Criterios de Aceptación

- [ ] El script `test_3_5_latency.py` existe y es ejecutable con `uv run python LAST/test_3_5_latency.py`.
- [ ] El test genera al menos 10 eventos medibles (combinación de `flow_step`, `agent_thought`, `tool_output`).
- [ ] La latencia **media** es **< 1000ms** (1 segundo).
- [ ] La latencia **p95** es **< 1500ms** (margen tolerable para picos).
- [ ] **Cero eventos perdidos** (todos los eventos generados llegan al suscriptor).
- [ ] El reporte de métricas se imprime en consola en formato legible.
- [ ] El test falla (exit code 1) si la latencia media supera 1000ms o si hay eventos perdidos.
- [ ] El test funciona con la tarea en estado `running` (no simula eventos artificialmente).

---

## 5. Riesgos

| Riesgo | Estrategia de Mitigación |
|--------|-------------------------|
| **Supabase Realtime tiene latency inherente > 1s en plan gratuito** | Medir primero con un ping directo. Si el infraestructura no cumple, documentar como limitación y proponer upgrade o alternativa (polling corto). |
| **El flow de test no genera eventos suficientes** | Diseñar un flow sintético que garantice al menos 10 eventos distribuidos en el tiempo (ej. pasos con `sleep` breve entre ellos). |
| **Clock skew entre servidor DB y cliente de test** | Al usar `inserted_at` de DB y calcular delta en el cliente, el clock skew no afecta porque el delta es relativo al momento de recepción, no absoluto. |
| **Concurrencia de otros procesos contamina la medición** | Ejecutar el test en un entorno aislado o en horarios de baja actividad. Documentar condiciones de ejecución. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Verificar que `domain_events` tiene columna `inserted_at` o `created_at` con resolución de milisegundos. | Baja | — |
| 2 | Si no existe, crear migración para añadirla (o confirmar que el campo ya está). | Baja | Tarea 1 |
| 3 | Confirmar que `GET /transcripts/{task_id}` devuelve el timestamp de inserción. Si no, añadirlo al serializer. | Media | Tarea 2 |
| 4 | Crear script `LAST/test_3_5_latency.py` con: | Alta | Tarea 3 |
|   | - Conexión a Supabase Realtime | | |
|   | - Disparo de tarea de test | | |
|   | - Captura de eventos con timestamps | | |
|   | - Cálculo de métricas (avg, p95, p99, max) | | |
|   | - Reporte y validación de criterios | | |
| 5 | Ejecutar test y validar que pasa en condiciones normales. | Media | Tarea 4 |
| 6 | Documentar resultados en `estado-fase.md`. | Baja | Tarea 5 |

---

## 🔮 Roadmap (NO implementar ahora)

- **Dashboard de Latencia en Tiempo Real:** Widget en el Admin Dashboard que muestre latencia promedio de Realtime en los últimos 5 minutos, con alertas si supera umbrales.
- **Test de Latencia End-to-End con Instrumentación Frontend:** Medir no solo desde DB → cliente de API, sino desde DB → renderizado visible en DOM (usando `performance.mark` y `performance.measure`).
- **Comparativa de Proveedores de Realtime:** Evaliar si Supabase Realtime es óptimo a escala o si se necesita migrar a WebSockets custom, Server-Sent Events (SSE), o alternativas como Pusher/Ably.
- **Test de Estrés:** Generar 100+ eventos/segundo y verificar que el pipeline de Realtime no colapsa y la latencia se mantiene predecible.
- **Synthetic Monitoring Continuo:** Ejecutar este test automáticamente cada 5 minutos en producción (tipo uptime check) para detectar degradación proactivamente.

---

*Análisis completado por qwen — Paso 3.5 [Validación: Test de Latencia]*
