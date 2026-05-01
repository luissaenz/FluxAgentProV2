# 🧠 ANÁLISIS TÉCNICO PASO 4 — ESTRÉS Y CONDICIONES DE BORDE
**Agente:** qwen  
**Fecha:** 2026-05-01  
**Versión:** v1.0

---

## 0️⃣ VERIFICACIÓN CONTRA CÓDIGO FUENTE

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `mcp_pool.py` existe | `src/tools/mcp_pool.py` | ✅ | Línea 1-211 |
| 2 | `service_connector.py` existe | `src/tools/service_connector.py` | ✅ | Línea 1-170 |
| 3 | `sanitizer.py` existe | `src/mcp/sanitizer.py` | ✅ | Línea 1-49 |
| 4 | `dynamic_flow.py` existe | `src/flows/dynamic_flow.py` | ✅ | Línea 1-218 |
| 5 | `WorkflowDefinition` existe | `src/flows/workflow_definition.py` | ✅ | Línea 1-132 |
| 6 | `flow_registry._flows` es dict | `src/flows/registry.py:14` | ✅ | `_flows: Dict[str, Type[BaseFlow]] = {}` |
| 7 | `MCPPool.reset()` método de clase | `mcp_pool.py:206` | ✅ | `def reset(cls) -> None` |
| 8 | `resolve_tools` existe | `src/crews/factory.py:77` | ✅ | `async def resolve_tools` |
| 9 | `SECRET_PATTERNS` tiene 7 patrones | `sanitizer.py:17-24` | ✅ | 7 regex patterns |
| 10 | `sanitize_output` maneja str/dict/list | `sanitizer.py:38-47` | ✅ | isinstance checks |
| 11 | `WorkflowDefinition` valida con Pydantic | `workflow_definition.py:23` | ✅ | `class WorkflowDefinition(BaseModel)` |
| 12 | `flow_registry.register` permite sobrescribir | `registry.py:26` | ✅ | `_flows[flow_type_lower] = RegisteredFlow` |
| 13 | Directorio `tests/stress` NO existe | `ls tests/stress` | ❌ | Directorio no encontrado |
| 14 | `org_id` vacío posible en `resolve_tools` | `factory.py:77` sin validación | ✅ | Sin check `if not org_id` |
| 15 | `input_data` sin validación de profundidad | `dynamic_flow.py:96-100` | ⚠️ | Asume dict válido |
| 16 | `sanitize_output` con 10MB string | `sanitizer.py:38-41` | ⚠️ | re.sub iterativo — O(n) por patrón |
| 17 | `MCPPool._adapters` singleton | `mcp_pool.py:40-42` | ✅ | Instance variable en singleton |
| 18 | `get_tools` timeout parameter | `mcp_pool.py:78` | ✅ | `timeout: int = 30` |

**Discrepancias encontradas:**
- ❌ **D1:** `tests/stress/` no existe → crear para tests S4.1-S4.7
- ⚠️ **D2:** `sanitize_output` con 10MB puede ser lento (7 patrones × re.sub secuencial) — no hay optimización
- ⚠️ **D3:** `resolve_tools` no valida `org_id` vacío — comportamiento indefinido

---

## 1️⃣ ANÁLISIS DE DATOS (ETAPA 1)

**Tablas tocadas indirectamente:**
- `org_mcp_servers` — usada en `mcp_pool.py:117-126` para cargar config
- `service_tools` — usada en `service_connector.py:66-73`
- `org_service_integrations` — validación de servicio activo
- `workflow_templates` — carga de dynamic flows

**No hay cambios de schema requeridos.** Paso 4 es puramente tests de estrés/borde sobre código existente.

**RLS policies aplicables:**
- `tenant_isolation` en todas las tablas — tests usan `mock_service_client` que bypass RLS con service_role

**Índices:** No aplica — tests no tocan DB real

---

## 2️⃣ ANÁLISIS DE CÓDIGO (ETAPA 2)

### Funciones a testear:

| Función | Archivo | Complejidad | Riesgo |
|---|---|---|---|
| `resolve_tools` | `src/crews/factory.py:77` | Media | Resolución masiva de tools |
| `MCPPool.get_tools` | `src/tools/mcp_pool.py:78` | Alta | Circuit breaker + retry + timeout |
| `MCPPool.reset` | `src/tools/mcp_pool.py:206` | Baja | Singleton reset |
| `DynamicWorkflow.register` | `src/flows/dynamic_flow.py:38` | Media | Registro dinámico |
| `sanitize_output` | `src/mcp/sanitizer.py:28` | Baja | Recursión + 7 regex |
| `WorkflowDefinition` (validación) | `src/flows/workflow_definition.py:23` | Media | Pydantic validators |

### Patrones existentes:
- **Mocking:** `patch("time.time")`, `MCPPool.reset()` entre tests (ver `test_mcp_pool_circuit.py`)
- **Fixtures:** `mock_service_client`, `mock_tenant_client`, `global_llm_mock` en `conftest.py`
- **Async tests:** `@pytest.mark.asyncio` para tests asíncronos

### Duplicación de código:
- No hay — tests de estrés son únicos en su propósito

### Imports correctos:
```python
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from src.tools.mcp_pool import MCPPool
from src.mcp.sanitizer import sanitize_output
from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.registry import flow_registry
from src.crews.factory import resolve_tools
```

---

## 3️⃣ ANÁLISIS DE BACKEND (ETAPA 3)

**No hay endpoints nuevos.** Tests son internos, no tocan API.

**Flujos probados:**
1. `resolve_tools(org_id, async_mode)` → resuelve tools de registry + MCP
2. `MCPPool.get_tools()` → conexión a servidores MCP externos
3. `DynamicWorkflow.register()` → registro en flow_registry
4. `sanitize_output()` → sanitización de outputs

**Error handling:**
- `MCPConnectionError` en circuit breaker abierto
- `asyncio.TimeoutError` en espera de conexión
- `SecurityError` en sandbox (no aplica aquí)
- Excepciones de Pydantic en validación

---

## 4️⃣ ANÁLISIS DE FULLSTACK + DX (ETAPA 4)

### Flujo completo:
```
Test de estrés → Mock de dependencies → Ejecución masiva → Métricas → Reporte
```

### Coherencia:
- Tests no requieren DB real, LLM real, MCP real
- Todo mockeado — determinista y rápido (<5s por test)
- Alineado con plan.md Paso 4

### DX & Tooling — Herramienta Propuesta:

```
### Herramienta Propuesta: fap stress-test
- **Qué automatiza:** Ejecución de tests de estrés del Paso 4 con métricas de performance
- **Tipo:** Comando CLI (typer)
- **Cómo se usa:** `fap stress-test [--test S4.1] [--iterations N]`
- **Impacto para el usuario final:** Ejecuta todos los tests S4.1-S4.7 de una vez, reporta tiempos, detecta regresiones de performance
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Implementación sugerida:** `src/cli/commands/stress_test.py`
- Opción `--test` para ejecutar un test específico
- Opción `--iterations` para repetir tests y promediar tiempos
- Opción `--benchmark` para guardar baseline de performance
- Output: tabla con tiempos por test, pass/fail, comparación con baseline

---

## 5️⃣ CRITERIOS DE ACEPTACIÓN

```
✅ [DATA] No hay cambios de schema — solo tests sobre código existente
✅ [CODE] 7 tests de estrés/borde implementados en tests/stress/
✅ [CODE] Tests S4.1-S4.7 pasan 100%
✅ [BACKEND] No hay endpoints nuevos — tests internos
✅ [FULLSTACK] Tests deterministas, todo mockeado, <5s cada uno
✅ [DX] Herramienta `fap stress-test` ejecuta sin errores
✅ [PERF] S4.1 <2s, S4.2 50 workflows completan, S4.5 <5s con 10MB
```

---

## 6️⃣ RIESGOS

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests de estrés lentos en CI | Media | Mocks insuficientes | Usar `patch` agresivo, evitar IO real |
| Falsos positivos en concurrencia | Media | Race conditions no reproducibles | Usar `asyncio.gather` con timeout estricto |
| Memory leak no detectable | Baja | Tests cortos no revelan leaks | Añadir test de memoria con `tracemalloc` (opcional) |
| `sanitize_output` 10MB muy lento | Media | 7 re.sub secuenciales | Optimizar a un solo regex compuesto (futuro) |
| Singleton MCPPool contamina tests | Baja | Estado global entre tests | `MCPPool.reset()` obligatorio en fixture autouse |

---

## 7️⃣ PLAN DE IMPLEMENTACIÓN

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear `fap stress-test` | FULLSTACK/DX | Media | 2h | Ninguna | → verificar: `fap stress-test --help` muestra opciones |
| 1 | Crear directorio `tests/stress/` | CODE | Baja | 0.5h | Tarea 0 | → verificar: directorio existe con `__init__.py` |
| 2 | Implementar `test_concurrency.py` (S4.1-S4.3) | CODE | Media | 2h | Tarea 1 | → verificar: `pytest tests/stress/test_concurrency.py` pasa 3/3 |
| 3 | Implementar `test_edge_cases.py` (S4.4-S4.7) | CODE | Media | 2h | Tarea 1 | → verificar: `pytest tests/stress/test_edge_cases.py` pasa 4/4 |
| 4 | Añadir fixture `autouse` para `MCPPool.reset()` | CODE | Baja | 0.5h | Tarea 1 | → verificar: tests no fallan por estado global |
| 5 | Validar métricas de performance | FULLSTACK | Baja | 1h | Tareas 2-3 | → verificar: todos tests <5s, S4.1 <2s |
| 6 | Integrar con `fap stress-test` | DX | Baja | 1h | Tarea 0, 2-3 | → verificar: `fap stress-test` ejecuta todos los tests |

**Tiempo total estimado:** 9 horas

---

## 🔮 ROADMAP (NO IMPLEMENTAR AHORA)

1. **Optimización `sanitize_output`:** Compilar 7 patrones en un solo regex para mejor performance con strings grandes
2. **Benchmark CI:** Guardar baseline de tiempos en archivo JSON, comparar en cada PR
3. **Memory profiling:** Integrar `tracemalloc` o `memory_profiler` para detectar leaks en tests de concurrencia
4. **Test de carga real:** Opcional — ejecutar `resolve_tools` con 500 tools reales (no mock) para validar performance en producción
5. **Validación de profundidad de JSON:** Implementar límite de profundidad (ej: 50 niveles) para evitar stack overflow en `sanitize_output`

---

## 📊 MÉTRICA DE CALIDAD DEL ANÁLISIS

| Métrica | Mínimo | Real |
|---|---|---|
| `proyecto-config.json` leído | 100% | ✅ |
| Elementos verificados (§0) | ≥12 (3-5 archivos) | ✅ 18 elementos |
| Discrepancias detectadas | ≥1 | ✅ 3 (D1-D3) |
| Secciones completadas | 8 (0-7) | ✅ 8 secciones |
| Etapas cubiertas | 4 | ✅ 4 etapas |
| Criterios de aceptación | ≥1 por sub-paso | ✅ 7 criterios |
| Riesgos identificados | ≥3 | ✅ 5 riesgos |
| Tareas en el plan | ≥4 | ✅ 7 tareas |
| Verificación inline por tarea | 100% | ✅ 7/7 |
| Suposiciones no verificadas | ≤2 | ✅ 0 |
| Propuesta DX / Tooling | ≥1 | ✅ `fap stress-test` |
| Estimación de tiempo | Sí | ✅ 9h total |

---

**Idioma:** Español 🇪🇸  
**Caveman:** Ultra
