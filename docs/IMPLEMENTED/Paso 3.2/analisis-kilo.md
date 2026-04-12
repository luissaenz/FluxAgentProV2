# 📋 ANÁLISIS TÉCNICO: PASO 3.2 - REFINAR ENDPOINT DE TRANSCRIPTS

## 1. Diseño Funcional

### Happy Path Detallado
- El endpoint `GET /transcripts/{task_id}` recibe un `task_id` válido perteneciente a la organización autenticada.
- Verifica la existencia de la tarea en la tabla `tasks` y obtiene `flow_type` y `status`.
- Recupera todos los eventos de dominio del tipo `flow_step`, `agent_thought` y `tool_output` asociados al `task_id`, ordenados por `sequence` ascendente.
- Retorna un JSON con `task_id`, `flow_type`, `status` y la lista de eventos, limitado a un máximo configurable (por defecto 200 eventos más recientes si excede).
- Los eventos incluyen campos esenciales: `id`, `event_type`, `payload`, `sequence`, `created_at`, excluyendo cualquier dato sensible (ya saneado en almacenamiento).

### Edge Cases Relevantes para MVP
- **Tarea no encontrada:** Si el `task_id` no existe o no pertenece al `org_id`, retorna HTTP 404 con mensaje "Task not found".
- **Sin eventos aún:** Si no hay eventos registrados para la tarea (ej. ejecución no iniciada), retorna lista `events` vacía.
- **Límite excedido:** Si hay más de 200 eventos, retorna los más recientes por `sequence` para mantener contexto actual relevante.
- **Eventos corruptos:** Si un evento tiene `payload` nulo o inválido, se incluye tal cual (la validación ocurre en escritura, no lectura).

### Manejo de Errores
- **404 - Task not found:** Usuario ve mensaje claro indicando que la tarea no existe o no tiene acceso.
- **500 - Error interno:** En caso de fallo de base de datos, se registra en logs y retorna error genérico (no expone detalles internos).
- **Limit exceeded:** No es error, pero se documenta en logs para monitoreo de performance.

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Modificación:** Endpoint `get_flow_transcript` en `src/api/routes/transcripts.py`.
  - Añadir filtro por `event_type` en la consulta a `domain_events` para incluir solo `flow_step`, `agent_thought`, `tool_output`.
  - Mantener verificación de existencia de tarea para seguridad RLS.
  - Ajustar límite por defecto a 500 para cubrir ejecuciones complejas sin comprometer performance.

### Interfaces (Inputs/Outputs de Cada Componente)
- **Input del Endpoint:**
  - `task_id` (string, path): Identificador único de la tarea.
  - `limit` (int, query, opcional, default=500, min=1, max=1000): Máximo número de eventos a retornar.
  - `org_id` (string, depend): Obtenido de middleware de autenticación.
- **Output del Endpoint:**
  - JSON: `{"task_id": str, "flow_type": str, "status": str, "events": [Evento]}` donde Evento es `{"id": str, "event_type": str, "aggregate_type": str, "aggregate_id": str, "payload": dict, "sequence": int, "created_at": str}`.

### Modelos de Datos Nuevos o Extensiones
- **Sin cambios:** Utiliza tablas existentes `tasks` y `domain_events` con campos ya definidos.
- **Coherencia con contratos:** Respeta `REPLICA IDENTITY FULL` en `domain_events` para consistencia con streaming futuro. No modifica RLS ni políticas de seguridad.

## 3. Decisiones

- **Filtro por tipos de evento:** Solo incluir `flow_step`, `agent_thought` y `tool_output` para reducir ruido y optimizar consultas. Justificación: Estos son los únicos tipos relevantes para transcripts según especificación de suscripción frontend, evitando carga innecesaria de eventos administrativos.
- **Aumento de límite por defecto:** Cambiar de 200 a 500 eventos para manejar flujos complejos sin truncar historia crítica. Justificación: Pruebas de latencia requieren contexto completo; límite bajo podría ocultar eventos iniciales importantes.

## 4. Criterios de Aceptación
- El endpoint retorna solo eventos con `event_type` en `["flow_step", "agent_thought", "tool_output"]`.
- Los eventos están ordenados por `sequence` ascendente.
- Si hay más de 500 eventos, retorna exactamente los primeros 500.
- Para tarea inexistente, retorna HTTP 404 con detalle "Task not found".
- La consulta se ejecuta en menos de 100ms para tareas con hasta 500 eventos (medido en staging).
- El `payload` de eventos no contiene valores de secretos (validado por inspección manual).

## 5. Riesgos
- **Performance en tareas con muchos eventos:** Consultas con >500 eventos podrían degradar respuesta. **Mitigación:** Implementar paginación opcional (`offset`) en futuras iteraciones; monitorear con logging de tiempos de consulta.
- **Inconsistencia de secuencia:** Si eventos llegan desordenados a DB, el orden podría ser incorrecto. **Mitigación:** Confiar en `sequence` como orden canónico; validar en pruebas que Supabase mantenga integridad.
- **Filtrado excesivo:** Si se requieren otros tipos de evento en futuro, cambio sería breaking. **Mitigación:** Documentar decisión y monitorear uso; reversión simple removiendo filtro.

## 6. Plan
1. **Modificar consulta en transcripts.py** (Complejidad: Baja - 5 min)
   - Añadir `.in("event_type", ["flow_step", "agent_thought", "tool_output"])` a la query de domain_events.
   - Cambiar default de `limit` a 500.
   - Dependencias: Ninguna.
2. **Actualizar docstring del endpoint** (Complejidad: Baja - 2 min)
   - Especificar que retorna solo eventos relevantes para transcripts.
   - Dependencias: Paso 1 completado.
3. **Validar con pruebas existentes** (Complejidad: Baja - 10 min)
   - Ejecutar scripts de test para asegurar no rompe contratos.
   - Dependencias: Paso 1 y 2 completados.
4. **Medir performance** (Complejidad: Media - 15 min)
   - Añadir logging de tiempo de consulta y verificar <100ms.
   - Dependencias: Paso 3 completado.

## 🔮 Roadmap (NO implementar ahora)
- **Paginación avanzada:** Soporte para `offset` y `before_sequence` para navegacion eficiente en transcripts largos.
- **Filtrado dinámico:** Parámetro opcional para incluir/excluir tipos de evento según vista (ej. solo tool_output para debugging).
- **Compresión de payloads:** Para eventos con payloads grandes, implementar compresión gzip en respuesta.
- **Cache de snapshot:** Almacenar snapshots en Redis para reducir carga en DB para tareas activas frecuentes.
- **Decisiones tomadas pensando en futuro:** Límite configurable mantiene flexibilidad; orden por sequence permite extensiones de timeline sin reordenamiento.</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md