# 📋 ANÁLISIS — Paso 3.2: Refinar Endpoint de Transcripts (Snapshot Inicial + Streaming Logic)

**Agente:** oc  
**Paso:** 3.2 [Backend]  
**Fecha:** 2026-04-12  
**Ubicación:** `src/api/routes/transcripts.py`

---

## 1. Diseño Funcional

### 1.1 Propósito del Endpoint
El endpoint `GET /transcripts/{task_id}` debe servir como fuente del "snapshot inicial" para el frontend:
1. **Carga inmediata:** Entregar eventos históricos al instante sin esperar streaming
2. **Sincronización delta:** Permitir pide solo eventos posteriores a un sequence dado (patrón snapshot + streaming)
3. **Validación de tarea:** Confirmar que la task existe y pertenece al org (seguridad)

### 1.2 Happy Path
```
1. Frontend llama GET /transcripts/{task_id}?limit=200
2. Backend valida org_id del token JWT
3. Backend verifica que task existe y pertenece al org
4. Backend consulta domain_events por aggregate_id = task_id, ordered by sequence ASC
5. Backend retorna: { task_id, flow_type, status, events[], last_sequence }
6. Frontend muestra eventos instantly, luego subscribe a Realtime
```

### 1.3 Edge Cases para MVP
| Escenario | Manejo |
|-----------|-------|
| Task no existe | 404 con mensaje claro |
| Task no pertenece al org | 404 (no revelar existencia) |
| Eventos vacíos (task nueva) | Retornar array vacío, no error |
| Límite exceeds 1000 | Usar max=1000, silently cap |
| after_sequenceprovided | Retornar solo eventos con sequence > value |

### 1.4 Manejo de Errores
- **404:** "Task not found" (mensaje genérico para seguridad)
- **403:** JWT sin org_id → 401
- **500:** Error de DB → mensaje genérico, loguear internamente

---

## 2. Diseño Técnico

### 2.1 Modificaciones al Endpoint Actual

**Archivo:** `src/api/routes/transcripts.py`

**Cambios requeriados:**

1. **Agregar parámetro `after_sequence`:**
   - Tipo: `int = Query(None)`
   - Propósito: Permitir patrón snapshot + streaming
   - Si se provee, retorna solo eventos con sequence > value

2. **Agregar `last_sequence` al response:**
   - Retornar el sequence máximo para que frontend knows siguiente posición
   - Útil para subscriptionsdelta

3. **Optimización de query:**
   - Usar solo índice existente `idx_domain_events_aggregate`
   - El índice compuesto (aggregate_type, aggregate_id) ya existe
   -无需 nuevo índice

### 2.2 Contrato de API Modificado

```python
# Nuevo endpoint
@router.get("/{task_id}")
async def get_flow_transcript(
    task_id: str,
    org_id: str = Depends(require_org_id),
    limit: int = Query(200, ge=1, le=1000),
    after_sequence: int = Query(None, description="Return only events after this sequence"),
):
```

**Response:**
```json
{
  "task_id": "uuid",
  "flow_type": "string",
  "status": "running|done|blocked",
  "events": [
    {
      "id": "uuid",
      "event_type": "flow_step",
      "aggregate_type": "flow",
      "aggregate_id": "uuid",
      "payload": {},
      "sequence": 1,
      "created_at": "ISO8601"
    }
  ],
  "last_sequence": 5  // Valor máximo para siguiente polling
}
```

### 2.3 Modelo de Datos
No se requieren cambios. `domain_events`ya tiene:
- `sequence`: INTEGER (para ordering)
- `aggregate_id`: TEXT (para filtrar por task_id)
- `event_type`: TEXT (para filtrar por tipo si fuera necesario)

### 2.4 Integración con Realtime (Paso 3.3)
El endpoint sirve snapshot, pero la suscripción realtime viene en paso 3.3:
- **Contrato linking:** El `last_sequence` retornado permite al frontend hacer polling delta
- **No hay tight coupling:** El frontend puede usar cualquiera de los dos métodos independientemente

---

## 3. Decisiones

### 3.1 Decisión: ¿Usar `after_sequence` o cursor tradicional?
**Elección:** Usar `after_sequence` (integer)
- Simplicidad: Más fácil de implementar que cursor-based
- Compatibilidad: Funciona con el índice existente
- Performance: La query es simple `sequence > after_sequence`

### 3.2 Decisión: ¿Filtrar por event_types específicos?
**Elección:** NO filtrar por tipo en backend
- El frontend puede filtrar localmente después del snapshot
- Mantiene el endpoint simple
- Permite flexibilidad al frontend

### 3.3 Decisión: ¿Cambiar nombre del endpoint?
**Elección:** Mantener `/transcripts/{task_id}`
- Nombre consistente con la UI (Transcript)
- No hay conflicto con otros endpoints

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| 1 | Endpoint retorna 404 si task_id no existe | `curl /transcripts/{fake-id}` → 404 |
| 2 | Endpoint retorna 404 si task_id es de otro org | API call con token de org B → 404 |
| 3 | Endpoint retorna eventos ordenados por sequence ASC | Verificar orden en response |
| 4 | Parámetro `after_sequence` filtra correctamente | `?after_sequence=3` → sequence > 3 |
| 5 | Campo `last_sequence` presente en response | Key exists in JSON |
| 6 | Límite accepted entre 1 y 1000 | Probar límites inválidos |
| 7 | Response time < 500ms para 1000 eventos | Timing measurement |

---

## 5. Riesgos

### 5.1 Riesgo: Query lenta para tasks con muchos eventos
**Severidad:** Media  
**Mitigación:** El índice compuesto `idx_domain_events_aggregate` ya existe y es suficiente para MVP. Monitorear latencia en paso 3.5.

### 5.2 Riesgo: Frontend no usa correctamente el snapshot
**Severidad:** Baja  
**Mitigación:** Documentar en el análisis del paso 3.3. La integración es independiente.

### 5.3 Riesgo: Race condition con eventos concurrentes
**Severidad:** Baja  
**Mitigación:** El snapshot puede no incluir eventos muy recientes. El flujo realtime (paso 3.3) complementa esto.

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias |
|----|------|------------|-------------|
| 1 | Actualizar imports y agregar `after_sequence` parameter | Baja | Ninguna |
| 2 | Modificar query para filtrar por `after_sequence` | Baja | #1 |
| 3 | Agregar `last_sequence` al response | Baja | #2 |
| 4 | Test unitario del endpoint | Media | Ninguna |
| 5 | Validar con datos reales (script de test) | Media | #4 |

### Orden Recomendado
1 → 2 → 3 → 4 → 5

### Estimación Total
**Complejidad:** Media  
**Líneas estimadas:** ~30 líneas de cambio  
**Tiempo estimado:** 1-2 horas

---

## 🔮 Roadmap (NO implementar ahora)

### 6.1 Optimizaciones Post-MVP
- **Filtrado por event_type:** Agregar query param `?event_type=flow_step,agent_thought` para reducir payload
- **Paginación cursor-based:** Si el volumen de eventos es muy alto, usar cursor en lugar de offset
- **Cacheo de snapshot:** Cachear el snapshot inicial por N segundos para reducir load

### 6.2 Enhancements Futuros
- **Aggregates múltiples:** Permitir filtrar por `?aggregate_type=flow,agent` si se usan múltiples aggregate types
- **Búsqueda full-text en payload:** Si los transcripts incluyen texto búsqueda, agregar búsqueda en payload
- **Exportación:** Endpoint de export (.json / .csv) para debugging

### 6.3 Considerations de Diseño Tomadas
- **Decisión:** No agregar cacheo ahora porque el volumen de MVP es bajo y la latencia es aceptable sin cache
- **Decisión:** No agregar WebSocket directo porque Supabase Realtime ya proporciona el mecanismo de streaming

---

**Documento de análisis completado.** Listo para implementación.