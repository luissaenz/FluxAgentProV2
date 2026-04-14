# 🧠 ANÁLISIS TÉCNICO: PASO 3.2 - REFINAR ENDPOINT DE TRANSCRIPTS
**Agente:** antigravity
**Estatus:** Analista Senior

## Contexto
Este análisis define la refinación técnica del endpoint de transcripts para servir como el snapshot inicial necesario antes de la integración con Supabase Realtime (streaming interactivo).

---

## 1. Diseño Funcional

### Happy Path Detallado
1.  **Solicitud:** El cliente llama a `GET /transcripts/{task_id}` al abrir la vista de ejecución.
2.  **Validación:** El sistema verifica que el `task_id` exista y pertenezca al `org_id` actual.
3.  **Filtrado Core:** Se recuperan solo los eventos que aportan valor visual al timeline: `flow_step`, `agent_thought`, `tool_output`.
4.  **Metadata de Sincronización:** El backend identifica el `sequence_id` más alto de los eventos recuperados (cursor de snapshot).
5.  **Respuesta:** Retorna el estado de la tarea, los eventos históricos y el cursor de sincronización.

### Edge Cases MVP
- **Transcripts Vacíos:** Si la tarea acaba de ser encolada pero no ejecutada, retorna una lista vacía y `last_sequence: 0`.
- **Truncado por Límite:** Si hay demasiados eventos, se entregan los **últimos 500** (para ver el estado actual) pero se asegura que el `last_sequence` sea el del evento más reciente entregado.
- **Tarea Finalizada:** Si el status es `done` o `failed`, se retorna la metadata completa; el frontend usará esto para deshabilitar el listener de Realtime innecesariamente.

### Manejo de Errores
- **404:** Tarea inexistente o de otra organización (Seguridad).
- **500:** Error de base de datos capturado globalmente.

---

## 2. Diseño Técnico

### Modificaciones en `src/api/routes/transcripts.py`
- **Consolidación de Consultas:** Unificar las peticiones a `tasks` y `domain_events` bajo una misma sesión del cliente para reducir latencia de handshake.
- **Lógica de Filtrado:**
  - Query a `domain_events`.
  - Filtro: `.in_("event_type", ["flow_step", "agent_thought", "tool_output"])`.
  - Orden: `.order("sequence", desc=False)`.
- **Estructura de Respuesta (Mejorada):**
  ```json
  {
    "task_id": "uuid",
    "flow_type": "string",
    "status": "string",
    "sync": {
      "last_sequence": 1234,
      "event_count": 45
    },
    "events": [...]
  }
  ```

### Justificación de Aislamiento
Se mantiene el uso de `get_tenant_client(org_id)` que garantiza que las consultas de Supabase se ejecuten bajo el contexto del esquema/tenant correcto, respetando las políticas RLS definidas en la Fase 2.

---

## 3. Decisiones Técnicas

1.  **Filtro Selectivo vs Broad:** Se opta por filtrar en el backend los tipos de evento. 
    - *Justificación:* Ahorro de ancho de banda y simplificación extrema de la lógica del componente frontend `TranscriptTimeline.tsx`.
2.  **Inclusión de `last_sequence`:** 
    - *Justificación:* Es el único mecanismo robusto para evitar colisiones de datos durante el hand-off del snapshot inicial al stream de Realtime. El cliente podrá descartar eventos del stream cuyo `sequence <= last_sequence`.
3.  **Límite de 500 eventos:**
    - *Justificación:* Suficiente para reconstruir el contexto de la mayoría de los flows sin impactar la memoria del navegador.

---

## 4. Criterios de Aceptación (Verificables)

- [ ] El endpoint retorna un objeto `sync` con el campo `last_sequence`.
- [ ] Los eventos retornados pertenecen únicamente a los tipos: `flow_step`, `agent_thought`, `tool_output`.
- [ ] El orden de los eventos en el array es cronológico (ascendente por `sequence`).
- [ ] La consulta a la base de datos se realiza utilizando una única instancia de cliente de tenant.
- [ ] El tiempo de respuesta es `< 150ms` para snapshots de 500 eventos.

---

## 5. Riesgos

- **Inconsistencia Temporal:** Que se pierdan eventos entre la consulta del snapshot y la conexión al websocket.
  - *Mitigación:* Se instruirá en el Paso 3.3 (Frontend) conectar el stream **antes** de pedir el snapshot y filtrar usando el `last_sequence`.
- **Formatos de Payload Inconsistentes:** Diferentes agentes podrían enviar diferentes estructuras en el JSON de payload.
  - *Mitigación:* Validar que el objeto `payload` retornado al frontend sea siempre un diccionario plano o estructurado estándar.

---

## 6. Plan de Implementación (Tareas Atómicas)

1. **Refactorización del Endpoint** (Complejidad: Baja): Modificar `src/api/routes/transcripts.py` para unificar consultas y aplicar filtros.
2. **Inyección de Metadata Sync** (Complejidad: Baja): Calcular y añadir el objeto `sync` basado en los resultados de la DB.
3. **Limpieza de Salida** (Complejidad: Baja): Mapear los resultados de la DB a un esquema de respuesta limpio sin IDs internos de sistema si no son necesarios.
4. **Prueba de Verificación** (Complejidad: Media): Crear `LAST/test_3_2_transcripts.py` que valide:
   - Que solo hay 3 tipos de eventos.
   - Que el `last_sequence` coincide con el último item de la lista.

---

## 🔮 Roadmap (NO implementar ahora)
- **Paginación Skip/Take:** Para flujos con histórico masivo.
- **Snapshot Caching:** Usar Redis para servir el snapshot de tareas muy activas.
- **Broadcasting Progress:** Un evento tipo `progress_percentage` para barras de carga en la UI.
