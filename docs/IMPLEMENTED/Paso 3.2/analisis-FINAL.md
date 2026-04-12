# 🏛️ ANÁLISIS FINAL UNIFICADO: PASO 3.2 - REFINAR ENDPOINT DE TRANSCRIPTS

## 1. Resumen Ejecutivo
Este documento consolida el diseño técnico para la optimización del endpoint de transcripts, actuando como el **puente crítico** entre el historial estático y el streaming en tiempo real (Paso 3.3). 

El objetivo principal es transformar un endpoint de consulta genérica en un mecanismo inteligente que entregue un **snapshot inicial optimizado**, permitiendo al frontend inicializar su línea de tiempo instantáneamente y decidir de forma autónoma si debe activar el motor de Realtime. Se prioriza la eficiencia en la transferencia de datos y la robustez del hand-off entre el historial y el stream mediante el uso de cursores de secuencia.

## 2. Diseño Funcional Consolidado

### Happy Path Detallado
1.  **Solicitud:** El frontend invoca `GET /transcripts/{task_id}` al cargar la vista de ejecución.
2.  **Aislamiento:** El backend extrae el `org_id` del contexto de autenticación y utiliza el `TenantClient` para garantizar que solo se accedan a tareas y eventos permitidos.
3.  **Filtrado Inteligente:** Por defecto, el sistema filtra los eventos para incluir solo aquellos con valor visual: `flow_step`, `agent_thought` y `tool_output`.
4.  **Introspección de Estado:** El backend determina si la tarea todavía puede generar eventos (`is_running`) basándose en su estado actual (excluyendo estados terminales como `done`, `failed`, `cancelled`).
5.  **Hand-off Metadata:** Se identifica el `sequence_id` más alto de los eventos entregados para que el frontend pueda filtrar eventos duplicados del stream de Realtime.
6.  **Respuesta:** Retorna el estado consolidado, la lista filtrada de eventos y la metadata de sincronización.

### Edge Cases MVP
- **Tarea Nueva (Pending):** Si la tarea existe pero no ha emitido eventos, retorna una lista vacía con `last_sequence: 0` e `is_running: true`.
- **Tarea de Otra Organización:** Retorna `404 Not Found` (mismo error que si no existiera) para evitar fugas de información sobre la existencia de IDs.
- **Transcripts Masivos:** Si se alcanza el `limit`, se marca `has_more: true` y se entregan los eventos más recientes (ordenados por secuencia).
- **Tarea Finalizada:** Si el estado es terminal, `is_running` será `false`. El frontend usará esto para no abrir canales de Supabase innecesariamente.

### Manejo de Errores
- **404:** Tarea inexistente o sin permisos.
- **422:** Parámetros de consulta (limit, types) inválidos.
- **503:** Fallo transitorio en la comunicación con la base de datos de eventos.

---

## 3. Diseño Técnico Definitivo

### Contrato de API (`GET /transcripts/{task_id}`)

#### Parámetros de Query (Opcionales)
- `types` (string): Lista separada por comas de tipos de evento a incluir. **Default:** `flow_step,agent_thought,tool_output`.
- `after_sequence` (int): Retorna solo eventos con `sequence > X`. Para catch-up selectivo.
- `limit` (int): Máximo de eventos. **Default: 500**. Rango: 1-1000.

#### Estructura de Respuesta
```json
{
  "task_id": "uuid",
  "flow_type": "string",
  "status": "string",
  "is_running": boolean,
  "sync": {
    "last_sequence": 1234,
    "has_more": boolean
  },
  "events": [
    {
      "id": "uuid",
      "event_type": "string",
      "payload": {},
      "sequence": 1234,
      "created_at": "ISO-8601"
    }
  ]
}
```

### Lógica de Backend (`src/api/routes/transcripts.py`)
1.  **Middleware de Seguridad:** Reutilizar `get_tenant_client(org_id)` para asegurar RLS.
2.  **Query Unificada:**
    - Consultar `tasks` para obtener metadata básica (`status`, `flow_type`).
    - Consultar `domain_events` aplicando:
        - `aggregate_id == task_id`
        - `event_type IN ({types})`
        - `sequence > {after_sequence}`
        - `ORDER BY sequence ASC`
        - `LIMIT {limit + 1}` (para detectar `has_more`).
3.  **Cálculo de `is_running`:**
    - `is_running = task.status NOT IN ('done', 'failed', 'cancelled', 'blocked')`.
4.  **Cálculo de `last_sequence`:**
    - Es el `sequence` del último objeto en el array `events`. Si no hay eventos, es `after_sequence` o 0.

---

## 4. Decisiones Tecnológicas

1.  **Filtro por Defecto en el Lado Servidor:** 
    - *Decisión:* El endpoint filtrará activamente los tipos de eventos a menos que se especifique lo contrario.
    - *Justificación:* Minimiza el payload del snapshot inicial y simplifica radicalmente el frontend Timeline UI.
2.  **Uso de `last_sequence` como Cursor:**
    - *Decisión:* Retornar explícitamente el marcador de posición del último evento.
    - *Justificación:* Es el único método infalible para evitar la pérdida de eventos entre la carga del snapshot y la apertura del socket de Supabase.
3.  **Flag `is_running` Explícito:**
    - *Decisión:* Derivar y enviar el estado de "actividad" de la tarea.
    - *Justificación:* Permite al frontend ser "lazy" con las suscripciones a Realtime, ahorrando conexiones y recursos en el cliente.
4.  **Indexación Existente:**
    - *Decisión:* No se crean nuevos índices.
    - *Justificación:* El índice `idx_domain_events_aggregate` ya cubre la combinación de `aggregate_id` y el orden de `sequence`.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] Al consultar una tarea recién creada, `is_running` es `true` y `events` es una lista vacía.
- [ ] Al consultar una tarea terminada, `is_running` es `false`.
- [ ] Los eventos retornados están filtrados por defecto (solo `flow_step`, `agent_thought`, `tool_output`).
- [ ] El campo `last_sequence` coincide exactamente con el valor del campo `sequence` del último evento de la lista.

### Técnicos
- [ ] El endpoint utiliza `TenantClient` con el context manager correcto para respetar RLS.
- [ ] El parámetro `after_sequence` filtra correctamente omitiendo eventos anteriores o iguales al valor dado.
- [ ] Si hay más de `limit` eventos, el campo `has_more` es `true` y la lista se trunca al `limit`.
- [ ] No se realizan más de 2 llamadas a la base de datos por petición al endpoint.

### Robustez
- [ ] Una consulta con un `task_id` de otra organización retorna `404` sin excepciones de servidor.
- [ ] Tiempo de respuesta inferior a 200ms para un snapshot de 500 eventos.

---

## 6. Plan de Implementación

1.  **Refactorización de Requisitos (Baja):** Importar esquemas y dependencias necesarias en `transcripts.py`.
2.  **Implementación de Lógica de Filtrado (Media):** Ajustar la query de Supabase para soportar `types` y `after_sequence`.
3.  **Inyección de Metadata de Sync (Baja):** Calcular `last_sequence`, `has_more` e `is_running`.
4.  **Limpieza de Contratos (Baja):** Asegurar que la respuesta JSON coincide exactamente con la estructura definida en la sección 3.
5.  **Validación Técnica:** Crear el script de test automatizado `LAST/test_3_2_transcripts.py`.

---

## 7. Riesgos y Mitigaciones
- **Desincronización en el hand-off:** Que un evento ocurra entre la DB query y el socket connect.
  - *Mitigación:* Se define que el Frontend debe conectar el socket ANTES de pedir el snapshot y usar `last_sequence` para deduplicar.
- **Colisión de Tipos:** Que se omitan eventos vitales por un filtro por defecto demasiado agresivo.
  - *Mitigación:* Se permite el override mediante el parámetro `types`.

---

## 8. Testing Mínimo Viable
1.  **Test de Aislamiento:** Validar que `org_A` no puede ver transcripts de `org_B`.
2.  **Test de Cursor:** Comprobar que si pido `after_sequence=2`, el primer evento recibido es el 3.
3.  **Test de Estado:** Confirmar que una tarea en estado `done` retorna `is_running: false`.
4.  **Test de Filtrado:** Confirmar que eventos de tipo `task.completed` no aparecen por defecto.

---

## 9. 🔮 Roadmap (NO implementar ahora)
- **Paginación Skip/Take:** Para historial masivo.
- **Optimización de Payload:** Truncar `tool_output` masivos (>10kb) en el snapshot inicial.
- **Caching:** Almacenar el snapshot de tareas finalizadas en Redis/CDN.
