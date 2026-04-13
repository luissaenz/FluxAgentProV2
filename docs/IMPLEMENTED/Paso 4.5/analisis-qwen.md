# 🧪 ANÁLISIS TÉCNICO - PASO 4.5: TEST DE PRECISIÓN ANALÍTICA

## 1. Diseño Funcional

### Happy Path Detallado
1. **Ejecución de suite de tests**: El desarrollador ejecuta `pytest src/scripts/test_analytical_precision.py -v` o corre el script standalone.
2. **Validación de estructura**: Cada test verifica que los componentes analíticos (AnalyticalCrew, SQLAnalyticalTool, EventStoreTool) retornen estructuras de datos coherentes con los contratos definidos en `estado-fase.md`.
3. **Verificación de aislamiento multi-tenant**: Se confirma que cada crew opera exclusivamente con su `org_id` sin filtraciones cruzadas.
4. **Validación de seguridad**: Queries no permitidos son rechazados tanto a nivel de crew como a nivel de herramienta SQL.
5. **Validación de fallbacks**: El sistema de clasificación por keywords responde correctamente cuando el LLM no está disponible.
6. **Reporte de resultados**: Se muestra un resumen con tests passed/failed/warnings.

### Edge Cases para MVP
- **Base de datos vacía**: Los tests deben pasar incluso si no hay datos de producción (validar estructura, no contenido).
- **LLM no disponible**: Validar que el fallback por keywords funciona y no causa fallos en cascada.
- **Org inválido**: El test de aislamiento multi-tenant usa org_ids ficticios (`org-aaa`, `org-bbb`) que no requieren existencia en BD.
- **Rate limiting**: El endpoint API tiene rate limiter (10 req/min), pero los tests standalone bypassean la API y prueban el crew directamente.

### Manejo de Errores (qué ve el usuario)
- **Test passa**: Mensaje verde con descripción ✅ y conteo de datos si aplica.
- **Test falla (AssertionError)**: Mensaje rojo ❌ con error específico y nombre del test.
- **Test falla (Exception)**: Mensaje amarillo ⚠️ con tipo de excepción y stack trace.
- **Resumen final**: Tabla con conteo de passed/failed/warnings y código de salida (0 si todo OK, 1 si hay fallos).

---

## 2. Diseño Técnico

### Componentes Existentes (Validar, NO modificar)
| Componente | Archivo | Rol en el Test |
|-----------|---------|----------------|
| `AnalyticalCrew` | `src/crews/analytical_crew.py` | Subject principal de tests de precisión |
| `SQLAnalyticalTool` | `src/tools/analytical.py` | Validación de ejecución de consultas y seguridad |
| `EventStoreTool` | `src/tools/analytical.py` | Validación de consulta de eventos |
| `ALLOWED_ANALYTICAL_QUERIES` | `src/crews/analytical_queries.py` | Allowlist de seguridad para queries |

### Componente Nuevo: Suite de Tests
**Archivo**: `src/scripts/test_analytical_precision.py` (YA EXISTE, validar completitud)

**Estructura de Tests Actuales**:
| # | Test Función | Valida | Estado |
|---|-------------|--------|--------|
| 1 | `test_analytical_crew_initialization` | Inicialización de crew con org_id | ✅ Implementado |
| 2 | `test_allowed_queries_exist` | Existencia de 5 queries pre-validadas | ✅ Implementado |
| 3 | `test_disallowed_query_rejected` | Rechazo de queries no allowlisted | ✅ Implementado |
| 4 | `test_tickets_by_status_returns_data` | Estructura y datos de tickets | ✅ Implementado |
| 5 | `test_flow_token_consumption_structure` | Estructura de consumo de tokens | ✅ Implementado |
| 6 | `test_recent_events_summary` | Resumen de eventos recientes | ✅ Implementado |
| 7 | `test_tasks_by_flow_type` | Tareas por tipo de flow | ✅ Implementado |
| 8 | `test_keyword_classification` | Fallback por keywords | ✅ Implementado |
| 9 | `test_ask_method_structure` | Estructura de respuesta del método `ask` | ✅ Implementado |
| 10 | `test_out_of_scope_question` | Manejo de preguntas fuera de alcance | ✅ Implementado |
| 11 | `test_sql_tool_rejects_dynamic_query` | Rechazo de SQL dinámico | ✅ Implementado |
| 12 | `test_event_store_tool_structure` | Estructura de EventStoreTool | ✅ Implementado |
| 13 | `test_multi_tenant_isolation` | Aislamiento de org_ids | ✅ Implementado |

### Interfaces Validadas
- **AnalyticalCrew**: `__init__(org_id)`, `analyze(query_type, params)`, `ask(question, query_type_hint)`
- **SQLAnalyticalTool**: `_run(query_type, params) -> str (JSON)`
- **EventStoreTool**: `_run(event_type, aggregate_type, limit) -> str (JSON)`
- **Contracto de respuesta**: `{ "question": str, "query_type": str, "data": List, "summary": str, "metadata": { "tokens_used": int, "row_count": int } }`

### Modelo de Datos
No se requieren nuevos modelos. Los tests validan estructuras existentes:
- **Tasks**: `id, status, assigned_agent_role, flow_type, tokens_used, created_at`
- **Tickets**: `id, status`
- **Domain Events**: `id, event_type, aggregate_type, aggregate_id, sequence, created_at`

### Integración con CI/CD
El script es ejecutable de dos formas:
1. **Standalone**: `python src/scripts/test_analytical_precision.py` (usa asyncio.run)
2. **Pytest**: `python -m pytest src/scripts/test_analytical_precision.py -v`

**SUPUESTO CRÍTICO**: Los tests asumen que hay una base de datos configurada y accesible via Supabase. En CI/CD, se requiere un entorno con datos seed o una BD de test.

---

## 3. Decisiones

### Decisión 1: Tests bypassan API endpoint directamente
**Justificación**: Los tests prueban la precisión del `AnalyticalCrew` directamente, no el endpoint HTTP. Esto evita dependencias del rate limiter (10 req/min) y simplifica el setup de test. La validación del endpoint `POST /analytical/ask` se hace indirectamente al validar la estructura de respuesta del crew.

### Decisión 2: Tests validan estructura sobre contenido exacto
**Justificación**: Los tests verifican que las estructuras de datos sean correctas (campos presentes, tipos correctos), pero no validan valores numéricos específicos ya que los datos pueden variar entre entornos de test y producción. Esto hace los tests más robustos y reutilizables.

### Decisión 3: Uso de org_ids ficticios para aislamiento
**Justificación**: Para validar el aislamiento multi-tenant, usamos `org-aaa` y `org-bbb` que no necesitan existir en la BD. El aislamiento se valida a nivel de inyección de parámetros en las herramientas, no a nivel de consulta real.

### Decisión 4: Test de keyword classification incluye "unknown"
**Justificación**: Validar que preguntas fuera de dominio sean clasificadas como "unknown" es crítico para seguridad - evita que el LLM ejecute queries no intencionados por ambigüedad.

---

## 4. Criterios de Aceptación

- [ ] El script `test_analytical_precision.py` se ejecuta sin errores de importación
- [ ] Los 13 tests definidos se ejecutan completamente
- [ ] Al menos 11 de 13 tests pasan (se permiten 2 warnings por falta de datos de BD)
- [ ] El test `test_disallowed_query_rejected` PASA (seguridad crítica)
- [ ] El test `test_sql_tool_rejects_dynamic_query` PASA (seguridad crítica)
- [ ] El test `test_multi_tenant_isolation` PASA (aislamiento crítico)
- [ ] El test `test_out_of_scope_question` PASA (manejo de errores)
- [ ] El test `test_ask_method_structure` retorna estructura con TODOS los campos: `question`, `query_type`, `data`, `summary`, `metadata`, `tokens_used`, `row_count`
- [ ] El test `test_keyword_classification` clasifica correctamente las 6 preguntas de prueba
- [ ] El resumen final muestra `failed == 0` o `warnings <= 2` (warnings por BD vacía son aceptables)
- [ ] El script retorna código de salida 0 si todos los tests críticos pasan
- [ ] El documento `estado-fase.md` se actualiza marcando Paso 4.5 como ✅

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **BD de test sin datos** | Tests 4-7 retornan 0 filas (warnings, no fallos) | Aceptable para MVP; los tests validan estructura, no contenido |
| **LLM no disponible** | Tests 9-10 pueden fallbackear | El fallback está implementado; se valida la resiliencia |
| **Configuración de Supabase incorrecta** | Tests fallan con errores de conexión | Requiere `.env` configurado; documentar en README de test |
| **Rate limiting en tests** | No aplica (tests van directo al crew, no al endpoint API) | N/A |
| **Datos de producción contaminan tests** | Resultados inconsistentes | Los tests no asumen valores específicos, solo estructuras |

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias | Descripción |
|---|-------|-------------|--------------|-------------|
| 1 | **Revisar tests existentes** | Baja | - | Leer `test_analytical_precision.py` y verificar completitud contra criterios de aceptación |
| 2 | **Ejecutar tests en entorno actual** | Baja | 1 | Correr `python src/scripts/test_analytical_precision.py` y documentar resultados |
| 3 | **Identificar gaps de cobertura** | Media | 2 | Comparar tests existentes con casos críticos no cubiertos |
| 4 | **Agregar tests faltantes (si los hay)** | Media | 3 | Implementar tests adicionales para casos no cubiertos |
| 5 | **Validar aislamiento multi-tenant profundo** | Alta | 2 | Test que verifica que queries de org A no retornan datos de org B |
| 6 | **Test de integración con endpoint API** | Media | 2 | Validar que `POST /analytical/ask` responde correctamente (opcional, puede ser separate step) |
| 7 | **Documentar resultados** | Baja | 2, 4, 5 | Guardar reporte de ejecución y marcar paso como completado en `estado-fase.md` |
| 8 | **Actualizar estado-fase.md** | Baja | 7 | Cambiar Paso 4.5 de 🏗️ a ✅ |

### Orden Recomendado
1 → 2 → 3 → 4 → 5 → 7 → 8

**Nota**: La tarea 6 es opcional y puede deferirse a un paso separado ya que el endpoint API ya tiene validación implícita vía los tests del crew.

---

## 🔮 Roadmap (NO implementar ahora)

### Mejoras Futuras para Tests de Precisión
1. **Datos Seed para CI/CD**: Crear un fixture de pytest con datos seed que garantice tests reproducibles en cualquier entorno.
2. **Validación de Precisión Numérica**: Comparar resultados del AnalyticalCrew contra consultas SQL directas para validar exactitud (no solo estructura).
3. **Benchmark de Latencia**: Medir tiempo de respuesta del pipeline completo (question → classify → execute → synthesize) y validar que está bajo umbral (ej. < 3s).
4. **Test de LLM Real**: Validar que el LLM clasifica correctamente un conjunto de preguntas de prueba con > 90% de accuracy.
5. **Test de Rate Limiter**: Validar que el endpoint `POST /analytical/ask` retorna 429 después de 10 requests/min.
6. **Test de Concurrencia**: Validar que múltiples crews con diferentes org_ids pueden operar simultáneamente sin race conditions.
7. **Cobertura de Código**: Integrar `pytest-cov` para medir % de código analítico cubierto por tests (meta: > 80%).
8. **Snapshot Testing**: Guardar snapshots de respuestas esperadas y validar que cambios no rompan el formato.

### Decisiones de Diseño para No Bloquear Futuro
- Los tests están diseñados para funcionar tanto con BD vacía como con datos (validan estructura sobre contenido).
- El script es autocontenido y no requiere fixtures externos, pero está estructurado para ser migrado a pytest con fixtures fácilmente.
- Los tests de aislamiento usan org_ids ficticios, lo que permite añadir tests con datos reales multi-tenant sin cambios mayores.
