# 🏛️ ANÁLISIS UNIFICADO - Paso 3.5: Validación de Latencia Real-time

## 1. Resumen Ejecutivo
Este paso final de la Fase 3 consiste en la **certificación técnica** del pipeline de streaming de transcripts. El objetivo es validar empíricamente que la latencia de propagación (el tiempo desde que un agente genera un pensamiento/acción hasta que el evento está disponible para el cliente) es inferior a **1 segundo**, garantizando una experiencia de usuario fluida y reactiva en el MVP.

Se implementará un orquestador de pruebas basado en un **cliente headless (Python)** que simulará la recepción en tiempo real, midiendo con precisión de milisegundos el desempeño de la infraestructura de Supabase y el backend local.

## 2. Diseño Funcional Consolidado

### Happy Path Detallado
1.  **Inicialización y Calibración:** El script de validación se conecta a PostgreSQL y ejecuta `SELECT NOW()` para calcular el **Drift de Reloj** entre el servidor y el cliente local.
2.  **Suscripción Garantizada:** Se establece la conexión via WebSockets al canal `task_transcripts:{task_id}` filtrando estrictamente por `aggregate_id`. El script espera al evento `SUBSCRIBED` antes de proceder.
3.  **Fase de Warm-up:** Se inserta un evento de control para asegurar que las rutas de red y los workers de Realtime de Supabase están "calientes".
4.  **Disparo de Carga Real:** Se instancia el `MultiCrewFlow` (orquestador de producción) utilizando un motor de CrewAI mockeado para generar una ráfaga controlada de eventos de dominio (`flow_step`, `agent_thought`, `tool_output`).
5.  **Captura y Auditoría:**
    *   **T_DB:** Momento de inserción registrado por la base de datos (`created_at`).
    *   **T_RECV:** Momento de recepción del paquete TCP/WebSocket en el script.
6.  **Análisis Estadístico:** Se calcula la latencia neta compensada y se generan métricas de percentiles (Avg, P95, Max).

### Edge Cases Relevantes para MVP
*   **Ráfaga de Pensamientos (Event Burst):** El test validará el comportamiento cuando se emiten múltiples `agent_thought` en menos de 100ms.
*   **Integridad Post-Fallo:** Simulación de una breve pérdida de conexión para verificar que el conteo final de mensajes recolectados coincide con los persistidos en DB.

### Manejo de Errores
*   **Timeout de Suscripción:** Si el handshake de Realtime excede los 5s, el test falla con "Infra-Error: Realtime Handshake Timeout".
*   **Umbral Crítico Excedido:** Si cualquier evento (P100) excede los 1500ms o el P95 supera los 1000ms, la validación se marca como RECHAZADA.

## 3. Diseño Técnico Definitivo

### Componentes de Validación
Se descarta la validación vía UI (Playwright) para esta fase técnica para evitar contaminar la métrica con el delay de renderizado de React/Framer-Motion, enfocándonos puramente en la **latencia de infraestructura**.

*   **Validador:** `tests/test_3_5_latency.py`.
*   **Lógica de Medición:** Uso de `perf_counter()` para deltas y timestamps de DB para referencia absoluta.
*   **Aislamiento de Tests:** El script utilizará una organización de test dedicada para no interferir con datos de producción.

### Contratos y APIs
*   **Suscripción Realtime:**
    ```python
    # Patrón robusto para evitar errores de importación interna
    from supabase import create_client
    # ...
    channel = client.channel(f"task_transcripts:{task_id}")
    channel.on(
        "postgres_changes",
        {"event": "INSERT", "schema": "public", "table": "domain_events", "filter": f"aggregate_id=eq.{task_id}"},
        callback
    ).subscribe()
    ```
*   **Snapshot REST:** Se usará `GET /transcripts/{task_id}` al final del test para certificar la consistencia 1:1 de los datos.

## 4. Decisiones Tecnológicas

1.  **Compensación de Clock Drift:** En lugar de modificar el esquema de DB (propuesta Kilo), se opta por la **Calibración Dinámica vía SELECT NOW()** (propuesta Antigravity/claude). Es menos intrusivo y suficiente para precisiones de ~10-20ms.
2.  **Métrica de Éxito P95:** Se establece el objetivo en **P95 < 800ms**. Esto deja un presupuesto (slack) de 200ms para el renderizado en el navegador, cumpliendo el requisito global de < 1s.
3.  **Resolución de Dependencias:** Se identifica que los errores de linter/importación en `tests/test_3_1_realtime.py` (referidos a `supabase.lib.realtime_client`) se deben a uso de APIs privadas o versiones de librería desactualizadas. El nuevo test utilizará exclusivamente la API pública de `supabase-py` v2.0+.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El script ejecuta un flujo completo de al menos 10 eventos sin intervención manual.
- [ ] Se genera un reporte detallado en `LAST/log_latencia.json` con los resultados.

### Técnicos
- [ ] **P95 de latencia infra (DB -> Recv) < 800ms.**
- [ ] **Latencia máxima (Worst Case) < 1500ms.**
- [ ] **Integridad de Mensajes = 100%** (Mensajes en DB == Mensajes recibidos en stream).
- [ ] El script utiliza el orquestador `MultiCrewFlow` real para la inserción.
- [ ] Los tokens de Supabase se manejan vía variables de entorno `.env`.

### Robustez
- [ ] El test detecta y alerta sobre "Clock Skew" excesivo (> 5s) antes de empezar.
- [ ] Manejo correcto de cierre de canales al finalizar o fallar el test.

## 6. Plan de Implementación

1.  **Refactor de Dependencias (Baja):** Corregir el script `tests/test_3_1_realtime.py` para usar el patrón de importación estándar y verificar que el entorno `pip` tiene `supabase>=2.10.0`.
2.  **Base de LatencyValidator (Media):** Crear el esqueleto en `tests/test_3_5_latency.py` con la lógica de conexión y calibración de tiempo.
3.  **Mock de Ejecución (Baja):** Configurar el `MultiCrewFlow` para operar con agentes que emiten `thoughts` y `tools` predefinidos sin llamar a LLMs.
4.  **Loop de Medición (Media):** Implementar la captura de timestamps y el cálculo de percentiles.
5.  **Ejecución Final (Media):** Realizar 5 corridas completas y certificar resultados.

## 7. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| **Latencia de Red Global** | Alto | El script informará el RTT inicial para descontar latencia de red puramente geográfica si el test corre lejos del data center de Supabase. |
| **Handshake de WebSocket lento** | Medio | Implementación mandatoria de un mensaje de Warm-up antes de la medición real. |
| **Inconsistencia de Versión Supabase** | Alto | Forzar el uso de la API `.channel()` de nivel superior en lugar de acceder a librerías internas. |

## 8. Testing Mínimo Viable (Antes de cerrar Paso 3.5)
1. **Calibración exitosa:** El script muestra el offset calculado entre local y servidor.
2. **Recepción bajo carga:** Verificar que al emitir 5 eventos por segundo, el stream no se cuelga ni aumenta la latencia progresivamente.

## 9. 🔮 Roadmap (NO implementar ahora)
*   Integrar métricas de latencia UI reales usando Playwright para medir el tiempo "Visual-to-Eye".
*   Dashboard histórico de performance de Realtime en el Admin Panel.
*   Alertas automáticas si el P95 se degrada en producción.
