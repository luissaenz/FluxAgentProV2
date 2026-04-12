# Análisis Técnico - Paso 3.5: Test de Latencia

## 1. Diseño Funcional

### Happy Path Detallado
1. Usuario inicia la ejecución de un flow complejo desde la interfaz de tickets (POST /tickets/{id}/execute).
2. El sistema procesa el flow, generando una secuencia de eventos: flow_step, agent_thought, tool_output.
3. Los eventos se escriben en la tabla `domain_events` con timestamps precisos.
4. El transcript se actualiza en la UI de `tasks/[id]/page.tsx` en tiempo real vía Supabase Realtime.
5. El test mide el tiempo entre la inserción en BD y la aparición en UI, verificando <1 segundo.

### Edge Cases Relevantes para MVP
- **Flow con Alta Concurrencia:** Múltiples agentes ejecutándose simultáneamente, generando eventos en ráfaga.
- **Reducción de Ancho de Banda:** Simulación de conexión lenta que podría afectar el streaming Realtime.
- **Eventos Fuera de Orden:** Verificación de que la lógica de secuencia (sequence filtering) maneja correctamente eventos desordenados.
- **Timeout de Conexión Realtime:** Manejo cuando el canal Supabase se desconecta temporalmente.

### Manejo de Errores
- Si la latencia excede 1 segundo en 3 mediciones consecutivas, el test falla con mensaje: "Latencia crítica detectada: {valor}ms > 1000ms".
- Si el canal Realtime no se conecta, mostrar "Error de conexión: Imposible medir latencia en tiempo real".
- Si el flow falla durante la ejecución, abortar el test con "Flow execution failed: Cannot complete latency measurement".

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Script de Test de Latencia (`test_latency.py`):** Ejecutable standalone que orquesta la medición completa.
- **Monitor de Base de Datos:** Hook adicional en `domain_events` para timestamp preciso de inserción.
- **Cliente de Medición Frontend:** Extensión de `useTranscriptTimeline.ts` para capturar timestamps de recepción UI.
- **Módulo de Análisis de Resultados:** Procesador de logs para calcular estadísticas de latencia.

### Interfaces (Inputs/Outputs de Cada Componente)
- **Script de Test:**
  - Input: `task_id` del flow ejecutado.
  - Output: JSON con métricas `{ avg_latency_ms, max_latency_ms, min_latency_ms, success_rate }`.
- **Monitor BD:**
  - Input: Eventos INSERT en `domain_events`.
  - Output: Log con timestamp de inserción por `sequence`.
- **Cliente Frontend:**
  - Input: Eventos Realtime procesados.
  - Output: Log con timestamp de recepción UI por `sequence`.

### Modelos de Datos Nuevos o Extensiones
- Extensión de tabla `domain_events` con campo `inserted_at_precise` (timestamp con microsegundos).
- Nuevo schema para resultados de test: `{ test_id, task_id, measurements: [{ sequence, db_time, ui_time, latency }] }`.

**Coherencia con estado-fase.md:** Utiliza contratos existentes de Transcript API y Realtime Channel Filtering. No contradice decisiones tomadas en auto-scroll o hand-off sincronizado.

## 3. Decisiones

- **Herramienta de Medición:** Utilizar `time.perf_counter()` en Python para precisión de microsegundos, en lugar de timestamps de BD estándar, para evitar variabilidad de clock drift entre servicios.
- **Flow de Test:** Seleccionar el flow más complejo disponible en el registry (mayor número de steps y tools), identificado dinámicamente para adaptarse a cambios futuros.
- **Umbral de Aceptación:** Mantener <1 segundo como objetivo, pero permitir configuración vía variable de entorno para testing en entornos con diferente performance.

## 4. Criterios de Aceptación
- El script de test ejecuta exitosamente un flow complejo sin errores.
- Se generan al menos 10 eventos de tipos diferentes durante la ejecución.
- La latencia promedio medida es < 1000ms en 5 ejecuciones consecutivas.
- La latencia máxima en cualquier medición individual es < 1500ms.
- El success rate de recepción de eventos en UI es 100%.
- Los logs de medición incluyen timestamps precisos para auditoría.
- El test puede ejecutarse tanto manualmente como en CI/CD pipeline.

## 5. Riesgos

- **Variabilidad de Red:** En entornos cloud, la latencia puede fluctuar por factores externos. **Mitigación:** Ejecutar test múltiples veces y calcular promedio; implementar baseline de comparación con mediciones previas.
- **Sobrecarga de Medición:** Los logs adicionales podrían afectar la performance del sistema bajo test. **Mitigación:** Implementar modo de "medición ligera" que solo capture timestamps críticos.
- **Inconsistencia de Clocks:** Diferencias entre reloj de BD y aplicación podrían falsear mediciones. **Mitigación:** Utilizar NTP sincronizado y mediciones relativas en el mismo proceso cuando posible.
- **Dependencia de Supabase Realtime:** Si el servicio tiene downtime durante test, imposibilita la validación. **Mitigación:** Implementar fallback a polling HTTP para mediciones de respaldo.

## 6. Plan

1. **Crear script base de test de latencia** (Media): Implementar estructura Python con logging y configuración. Dependencia: Ninguna.
2. **Implementar monitor de timestamps BD** (Baja): Añadir triggers/logs en `domain_events` para captura precisa. Dependencia: 1.
3. **Extender hook de timeline para medición UI** (Baja): Modificar `useTranscriptTimeline.ts` para logging de recepción. Dependencia: 2.
4. **Implementar lógica de cálculo de latencia** (Media): Procesar logs y calcular métricas estadísticas. Dependencia: 3.
5. **Integrar selección automática de flow complejo** (Baja): Query al registry para identificar flow más apropiado. Dependencia: 4.
6. **Añadir validaciones y assertions del test** (Media): Implementar checks de criterios de aceptación. Dependencia: 5.
7. **Testing y calibración del script** (Alta): Ejecutar múltiples iteraciones y ajustar umbrales. Dependencia: 6.

## 🔮 Roadmap (NO implementar ahora)
- **Dashboard de Métricas de Performance:** Visualización histórica de latencias por tipo de evento y flow.
- **Alertas Automáticas:** Notificaciones cuando latencia excede umbrales en producción.
- **Benchmarking Avanzado:** Comparación de performance entre diferentes proveedores de BD realtime.
- **Testing de Stress:** Validación de latencia bajo carga extrema (100+ flows simultáneos).
- **Tracing Distribuido:** Integración con OpenTelemetry para medición end-to-end incluyendo red y cliente.