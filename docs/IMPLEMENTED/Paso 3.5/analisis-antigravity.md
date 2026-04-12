# Análisis Técnico - Paso 3.5: Validación de Latencia Real-time

## 1. Diseño Funcional

Actuando como **Antigravity**, el análisis se centra en la verificación técnica objetiva del requisito de latencia (< 1s) para los transcripts en vivo.

### Happy Path Detallado
1.  **Inicialización:** El script de validación establece una conexión vía WebSocket con el canal de Supabase Realtime para la tabla `domain_events`, filtrando por el `task_id` de la prueba.
2.  **Sincronización Temporal:** El script consulta `SELECT NOW()` en PostgreSQL para calcular el offset exacto entre el reloj del servidor de base de datos y el reloj local de ejecución del test.
3.  **Disparo de Carga:** Se ejecuta un `MultiCrewFlow` (mockeado o real) que genera una secuencia de eventos de dominio (`flow_step`, `agent_thought`, `tool_output`).
4.  **Captura Triple:**
    *   **T0 (Producción):** Momento en que el servidor API inserta el evento.
    *   **T1 (DB Commit):** El valor de `created_at` asignado por PostgreSQL.
    *   **T2 (Recepción):** Momento en que el cliente Realtime del script recibe el payload.
5.  **Cálculo:** Se define Latencia como `L = T2 - T1` (ajustado por el offset del paso 2).
6.  **Validación:** Se comparan los resultados contra el umbral de 1000ms.

### Edge Cases Relevantes para MVP
*   **Cold Start del Canal:** La latencia del primer mensaje suele ser mayor debido al establecimiento de la ruta de streaming. Se debe realizar un evento de "warm-up".
*   **Eventos en Ráfaga:** Comportamiento de la latencia cuando el Crew emite 5 thoughts en menos de 100ms.
*   **Reconexión durante el Flow:** Si el socket se pierde y recupera, validar si los eventos "perdidos" llegan vía el mecanismo de catch-up del frontend o si el test detecta el hueco.

### Manejo de Errores
*   **Suscripción Fallida:** Si el estado `SUBSCRIBED` no se alcanza en 15 segundos, abortar con error de infraestructura.
*   **Divergencia de Conteo:** Si el número de INSERTs detectados en el socket no coincide con la auditoría final de la DB, marcar como fallo de integridad.

## 2. Diseño Técnico

### Componentes y Herramientas
*   **Script de Validación:** `tests/test_3_5_latency.py` utilizando `supabase-py` y su cliente de Realtime integrado.
*   **Contexto de Ejecución:** El script debe ejecutarse en un entorno con acceso a las variables de entorno de Supabase (URL/Key).
*   **Métrica Clave:** P95 de la latencia de propagación.

### Interfaces del Test
*   **Input:** API Key, URL y un ID de organización válido.
*   **Output:** Reporte de salida tipo tabla:
    | Sequence | Event Type | DB Timestamp | Reception Timestamp | Latency (ms) | Result |
    |----------|------------|--------------|---------------------|--------------|--------|
    | 1        | flow_step  | 14:00:01.050 | 14:00:01.200        | 150ms        | ✅      |

### Modelos de Datos
*   Se basa exclusivamente en la tabla `domain_events` habilitada en el Paso 3.1.

## 3. Decisiones

*   **Evitar Cambio de Esquema:** No se añadirá un campo `client_received_at` a la base de datos de producción. La validación es puramente externa y observacional.
*   **Offset dinámico:** Dada la naturaleza serverless de Supabase, no podemos asumir sincronización NTP perfecta. El cálculo de `delta_relojes = local_now - db_now` es obligatorio al inicio de cada ejecución para garantizar precisión de milisegundos.
*   **Uso de `MultiCrewFlow`:** Se utilizará el orquestador real para que la carga de eventos sea representativa de un uso real de la plataforma, incluyendo el delay natural del motor CrewAI.

## 4. Criterios de Aceptación
- [ ] Conexión Realtime establecida y confirmada en < 5s.
- [ ] Procesamiento de al menos 15 eventos representativos (`agent_thought`, `tool_output`).
- [ ] **Latencia Media (AVG) < 500ms.**
- [ ] **Latencia Máxima (P100) < 1000ms.**
- [ ] Cero mensajes perdidos (Integridad 100%).
- [ ] Generación automática de log de auditoría en `LAST/latency_results.json`.

## 5. Riesgos

*   **Latencia de Red Geográfica:** Si el servidor de test está en una región muy lejana a la instancia de Supabase, la latencia de red dominará sobre la de la base de datos.
    *   *Mitigación:* Informar del RTT (Round Trip Time) base al inicio del reporte.
*   **Rate Limiting de Realtime:** El plan gratuito de Supabase tiene límites estrictos.
    *   *Mitigación:* Diseñar el flow de prueba para no exceder los 5 mensajes/segundo.

## 6. Plan de Implementación

1.  **Draft de Cliente Realtime en Python (Media):** Implementar una clase `RealtimeMonitor` que gestione el loop de eventos y el almacenamiento de timestamps.
2.  **Integración con Flow Orchestrator (Media):** Adaptar `tests/manual_test_phase3.py` para que devuelva el ID de tarea y espere a las señales del monitor.
3.  **Implementación de Cálculo de Offset (Baja):** Lógica de `SELECT NOW()` para calibración de relojes.
4.  **Ejecución de Batería de Pruebas (Baja):** 3 ejecuciones de 20 eventos cada una.
5.  **Generación de Documentación de Validación (Baja):** Formatear resultados finales para aprobación de fase.

---
### 🔮 Roadmap (No implementar ahora)
*   **Stress Test Masivo:** 100 agencias concurrentes para medir degradación de latencia.
*   **Monitor de Latencia en UI:** Un pequeño indicador (ms) oculto en el `ConnectionStatusBadge` para uso interno de los desarrolladores.
