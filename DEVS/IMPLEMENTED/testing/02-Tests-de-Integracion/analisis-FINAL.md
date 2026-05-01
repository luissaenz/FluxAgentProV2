# 🏛️ Análisis Final Unificado — Paso 2: Tests de Integración de Flujos Críticos

**Generado por:** Unificador (Arquitecto de Sistemas Senior)
**Fecha:** 2026-05-01
**Fase:** testing (Fase VI)
**Fuentes:** ds, qwen, glm (3 análisis)
**Config leída:** `D:\Develop\Personal\FluxAgentPro-v2\proyecto-config.json`

---

## 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| DS | ✅ 20 elementos | 5 (D1-D5) | `fap test-step 2` | ✅ líneas exactas | 4.8 |
| Qwen | ✅ 24 elementos | 3 (D1-D3) | `fap test-step 2` | ✅ líneas exactas + análisis profundo bug `>=` | 4.7 |
| GLM | ✅ 22 elementos | 4 (discordancias) | `fap test-integration` | ✅ líneas exactas + detalle mocking HITL | 4.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **Bug `>=`/`<=`/`==` en `_check_approval_rule`:** `"monto >= 50000"` → `">" in condition` True → `split(">")` → `float("= 50000")` → ValueError silencioso → False. `>=` parsea por accidente pero compara como `>` (incorrecto para valores iguales). | ds, qwen, glm | ✅ `src/flows/dynamic_flow.py:137` | **Fix parser.** Priorizar operadores compuestos: `>=`, `<=`, `==` antes que `>`, `<`. Agregar I4.1-I4.3 en `test_approval_operators.py`. |
| 2 | **`approval_threshold` definido pero no usado:** `workflow_definition.py:47` tiene campo en `StepDefinition`, `_run_crew()` nunca lo referencia. Usa `approval_rules[].condition`. | ds, qwen, glm | ✅ `src/flows/workflow_definition.py:47` vs `src/flows/dynamic_flow.py:66-126` | Documentar como deuda técnica. **No tocar en Paso 2.** |
| 3 | **DX tool naming conflict:** DS/Qwen proponen `fap test-step 2` (extensión existente), GLM propone `fap test-integration` (nuevo comando). | ds vs glm | ✅ `src/cli/commands/test_step.py` | **Usar `fap test-step 2`.** Consistente con Paso 1. Dogfooding probado. |
| 4 | **HITL `EventStore.append_sync()` no mockeado en conftest:** Tests HITL (I3.x si usa flujo completo) necesitan patch adicional. | glm | ✅ `src/flows/base_flow.py:request_approval()` → `EventStore.append_sync()` | Agregar `patch("src.flows.base_flow.EventStore.append_sync")` local en test si aplica. |
| 5 | **`MCPServerAdapter` import lazy dentro de `get_tools()`:** Importación dentro de try/except en `mcp_pool.py:149-154`. Mock debe estar en namespace `src.tools.mcp_pool` antes de llamar. | ds, qwen, glm | ✅ `src/tools/mcp_pool.py:149-154` | Mock local en `test_mcp_resilience.py`. Patch en `src.tools.mcp_pool` namespace. |
| 6 | **I2.1 interpretación:** GLM nota que circuito abierto falla en 1er intento (no 6º). Check de circuit breaker es ANTES de retry decorator. DS/Qwen lo describen como "6º intento falla". | glm vs ds/qwen | ✅ `src/tools/mcp_pool.py:77-190` | Ambos correctos. Plan dice "6º intento" pero mecánicamente: check pre-retry → 1er intento falla inmediato con circuito abierto. Documentar ambas interpretaciones. |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Agregar 6 tests de integración (3 MCP resilience + 3 handover) + 3 tests condicionales para operadores `>=`, `<=`, `==`. Fix bug silencioso en `_check_approval_rule`. Extender `fap test-step 2` como DX Tarea 0.
- **Correcciones críticas al plan:** Bug `>=`/`<=`/`==` no es solo "no implementado" — es **evalúa False cuando debería ser True**. `>=` parsea por accidente pero compara con `>` (incorrecto para edge case de igualdad). Fix parser requerido antes de tests condicionales.
- **Decisión DX:** `fap test-step 2` (extensión de comando existente). Consistente con Paso 1. GLM propuso `fap test-integration` pero se descarta por duplicación de comandos.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Implementador extiende `fap test-step` para soportar paso 2 → `fap test-step 2` ejecuta toda la suite del paso.
2. Fix `_check_approval_rule` en `dynamic_flow.py` para parsear `>=`, `<=`, `==` correctamente (operadores compuestos primero).
3. Crear `tests/integration/test_mcp_resilience.py` con I2.1-I2.3: ciclo completo circuit breaker con mocks de DB + MCP adapter + time.
4. Crear `tests/integration/test_handover_real.py` con I3.1-I3.3: contexto previous_results, 0 steps, fallo parcial.
5. Expandir `tests/unit/test_approval_operators.py` con I4.1-I4.3 (condicional al fix).
6. Ejecutar `fap test-step 2` → 9 tests pass (6 base + 3 condicionales). Regresión Paso 1 intacta.
7. Lint: `ruff check src/ tests/` → 0 errores.

### Edge Cases MVP

| # | Edge Case | Sub-paso | Manejo |
|---|---|---|---|
| EC1 | Circuito abierto → `get_tools()` sin intentar conexión | 2.1 | `MCPConnectionError` inmediato. Verificar en I2.1 |
| EC2 | Half-open → éxito → reset failures=0 | 2.1 | Verificar en I2.2 |
| EC3 | Half-open → fallo → re-abre circuito | 2.1 | Verificar en I2.3 |
| EC4 | Template con 0 steps → retorna `{}` sin excepción | 2.2 | Verificar en I3.2 |
| EC5 | Step 2 falla → step 1 resultado en results (antes de excepción) | 2.2 | Verificar en I3.3 |
| EC6 | `>=` con valor igual al threshold → True | 2.3 | Verificar en I4.1 |
| EC7 | `<=` con valor igual al threshold → True | 2.3 | Verificar en I4.2 |
| EC8 | `==` con valor exacto → True | 2.3 | Verificar en I4.3 |
| EC9 | `>=`/`<=`/`==` con valor que no cumple → False (no regresión) | 2.3 | Tests de regresión adicionales |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| # | Ruta real | Tipo | Descripción | Interfaces clave | Patrón |
|---|---|---|---|---|---|
| 1 | `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\test_step.py` | Modificación | Extender mapa de pasos para incluir paso 2 | `STEP_FILES[2] = [...]` | Seguir patrón Paso 1 existente |
| 2 | `D:\Develop\Personal\FluxAgentPro-v2\src\flows\dynamic_flow.py` | Modificación | Fix `_check_approval_rule`: priorizar `>=`, `<=`, `==` sobre `>`, `<` | `_check_approval_rule(rule, results) → bool` | ~15 líneas, orden de operadores |
| 3 | `D:\Develop\Personal\FluxAgentPro-v2\tests\integration\test_mcp_resilience.py` | Creación | I2.1-I2.3: circuit breaker integration | `test_circuit_opens_after_5_failures`, `test_full_cycle_open_to_close`, `test_half_open_failure_reopens` | `MCPPool.reset()` autouse, `patch("time.time")`, `_make_pool_with_state()` helper |
| 4 | `D:\Develop\Personal\FluxAgentPro-v2\tests\integration\test_handover_real.py` | Creación | I3.1-I3.3: handover contexto | `test_step_receives_previous_results`, `test_empty_steps_no_crash`, `test_partial_failure_preserves_results` | `mock_service_client`, `mock_tenant_client`, `patch("BaseCrew")` |
| 5 | `D:\Develop\Personal\FluxAgentPro-v2\tests\unit\test_approval_operators.py` | Modificación | I4.1-I4.3: operadores condicionales (solo si fix implementado) | `test_gte_equal_true`, `test_lte_equal_true`, `test_equal_true` | Tests unitarios puros, sin IO |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap test-step 2
- **Qué automatiza:** Ejecución de los 6-9 tests del paso 2 con un comando. El usuario no necesita recordar rutas de archivos pytest.
- **Tipo:** CLI command (extensión de comando existente `src/cli/commands/test_step.py`)
- **Ubicación:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\test_step.py`
- **Cómo se usa:** `fap test-step 2` | `fap test-step 2 --cov` | `fap test-step 2 --verbose`
- **Impacto para el usuario final:** Elimina invocación manual de:
  ```bash
  pytest tests/integration/test_mcp_resilience.py tests/integration/test_handover_real.py -v
  pytest tests/unit/test_approval_operators.py -k "I4"  # (condicional)
  ```
- **El implementador DEBE usarla** para completar las tareas 1..N del paso (dogfooding obligatorio).
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Fix `>=`/`<=`/`==` en `_check_approval_rule`:** Los 3 agentes coinciden en que el bug produce falsos negativos silenciosos. Se implementa fix con orden de operadores: `>=`, `<=`, `==` primero, luego `>`, `<`. ~15 líneas, riesgo bajo. Código real gana sobre plan original que lo dejaba como "decisión abierta".

2. **Extensión de `fap test-step` vs nuevo comando `fap test-integration`:** Se descarta propuesta de GLM. `fap test-step` ya existe para Paso 1, dogfooding probado, menos duplicación. El comando `test-step` es semánticamente correcto para cualquier paso de testing.

3. **Ubicación de I4.x:** En `test_approval_operators.py` (DS sugería `test_dynamic_flow.py`). Los tests de approval operators son unitarios puros (sin mocking), cohesión temática con tests U3.1-U3.4 existentes.

4. **Mocking de `MCPServerAdapter`:** Local en archivo de test, no en conftest global. Importación lazy dentro de `get_tools()` requiere patch en namespace `src.tools.mcp_pool` antes de ejecutar el método. Evita side effects en otros tests.

5. **Sin cambios de schema:** Paso 2 no requiere migraciones, nuevos índices ni alteración de tablas. Todos los tests son de integración con mocks.

6. **Correcciones al plan:**
   - ⚠️ El plan dice bug `>=`/`<=`/`==` "se rompen silenciosamente". Corrección: `>=` y `<=` **parsean por accidente** pero comparan con operador incorrecto (`>` en vez de `>=`). Es peor que "no funciona" — produce falsos negativos cuando el valor es exactamente igual al threshold.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Ninguna migración nueva requerida para Paso 2
✅ [DATA] Tablas org_mcp_servers, workflow_templates, tasks, snapshots mockeadas correctamente
✅ [CODE] test_mcp_resilience.py existe con I2.1-I2.3 en tests/integration/
✅ [CODE] test_handover_real.py existe con I3.1-I3.3 en tests/integration/
✅ [CODE] _check_approval_rule soporta >=, <=, == sin errores silenciosos (fix implementado)
✅ [CODE] test_approval_operators.py incluye I4.1-I4.3 (condicional al fix)
✅ [BACKEND] I2.1: 5 fallos → circuito abierto → get_tools() lanza MCPConnectionError inmediato
✅ [BACKEND] I2.2: circuito abierto → 60s → half-open → éxito → reset (failures==0)
✅ [BACKEND] I2.3: circuito abierto → 60s → half-open → fallo → re-abre (failures>=5)
✅ [BACKEND] I3.1: step 2 recibe previous_results con output real de step 1
✅ [BACKEND] I3.2: template con 0 steps retorna {} sin excepción
✅ [BACKEND] I3.3: step 2 falla → step 1 resultado preservado en results
✅ [FULLSTACK] Todos los tests pasan con mocks (sin DB, sin LLM, sin MCP real)
✅ [FULLSTACK] Circuit breaker validado con time.time mockeado (sin espera real de 60s)
✅ [DX] fap test-step 2 ejecuta todos los tests del paso con un solo comando
```

**Funcionales:**
- [ ] Fix `_check_approval_rule` no rompe tests existentes de `>` y `<`
- [ ] Tests existentes de Paso 1 siguen pasando (regresión 0)
- [ ] `>=` con valor igual → True; `>=` con valor menor → False

**Técnicos:**
- [ ] `MCPPool.reset()` en fixture autouse=True para evitar contaminación de singleton
- [ ] `patch("time.time")` scoped por test individual (no fixture global)
- [ ] Mock de `MCPServerAdapter` en namespace `src.tools.mcp_pool` antes de llamar a `get_tools()`
- [ ] Lint: `ruff check src/ tests/` → 0 errores

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Extender `fap test-step` para paso 2 | Baja | 0.5h | Ninguna |
| 1 | Fix `_check_approval_rule()` para `>=`, `<=`, `==` en `dynamic_flow.py` | Media | 1.5h | Ninguna (paralelizable con 2-3) |
| 2 | Crear `tests/integration/test_mcp_resilience.py` con I2.1-I2.3 | Alta | 3h | Tarea 0 |
| 3 | Crear `tests/integration/test_handover_real.py` con I3.1-I3.3 | Alta | 2h | Tarea 0 |
| 4 | Agregar I4.1-I4.3 a `tests/unit/test_approval_operators.py` | Baja | 0.5h | Tarea 1 |
| 5 | Validar paso completo: `fap test-step 2` (6-9 tests 100% pass) | Baja | 0.5h | Tareas 1-4 |
| 6 | Lint + verificar no regresión en tests Paso 1 | Baja | 0.5h | Tarea 5 |
| **TOTAL** | | | **8.5h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap test-step 2` para el resto del paso (dogfooding obligatorio).

### Orden de ejecución recomendado

1. **Tarea 0** (DX) → dogfooding desde inicio
2. **Tareas 1 + 2 + 3** en paralelo (no dependen entre sí)
3. **Tarea 4** (tests condicionales) → solo si Tarea 1 completa
4. **Tarea 5** (validación) → `fap test-step 2`
5. **Tarea 6** (lint + regresión) → gate final

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **Mock de `MCPServerAdapter` falla por import lazy** | Alta | Importación dentro de try/except en `get_tools()`. Patch puede no aplicarse | Patch en namespace `src.tools.mcp_pool` ANTES de llamar. Alternativa: mockear `_connect()` internamente |
| **Bug `>=`/`<=`/`==` requiere decisión política** | Alta | Si stakeholder decide no fix, tests I4 no se pueden escribir como "pasan" | Decidir ANTES de implementar Tarea 4. Si won't-fix: agregar test de regresión documentando bug |
| **HITL `EventStore.append_sync()` no mockeado** | Media | Si I3.x usa flujo HITL completo, fixture actual no lo cubre | Agregar patch local `@patch("src.flows.base_flow.EventStore.append_sync")` |
| **Contaminación de singleton MCPPool entre tests** | Media | Pool es singleton. `_health` y `_adapters` persisten | `MCPPool.reset()` en fixture autouse=True. Patrón ya probado en Paso 1 |
| **Regresión en `>`/`<` tras fix de operadores** | Media | Cambiar orden de chequeo podría romper conditions existentes | Orden estricto: `>=`, `<=`, `==` primero. Tests U3.1-U3.4 son red de seguridad |
| **`test_3_5_latency.py` en raíz de tests/** | Baja | Archivo fuera de estructura esperada. Plan Paso 0 menciona moverlo | Documentar como deuda técnica. Si falla, agregar `@pytest.mark.skip` antes de Paso 2 |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Sub-paso | Input | Output Esperado |
|---|---|---|---|---|
| TP-1 | Circuito abierto bloquea conexión | 2.1 | 5 fallos simulados + 6º intento `get_tools()` | `MCPConnectionError("Circuit breaker abierto")`, sin intentar conexión |
| TP-2 | Ciclo completo: open → half-open → close | 2.1 | 5 fallos + avance 60s + éxito en half-open | `failures == 0`, tools list retornada |
| TP-3 | Half-open → fallo → re-open | 2.1 | 5 fallos + avance 60s + fallo en half-open | `failures >= 5`, circuito re-abierto |
| TP-4 | Contexto previous_results entre steps | 2.2 | Template 2 steps, step 1 retorna "done" | `inputs["previous_results"]` en step 2 contiene `{"step_1": {"result": "done"}}` |
| TP-5 | Template 0 steps no crashea | 2.2 | `steps: []` | Retorna `{}`, sin excepción |
| TP-6 | Fallo parcial preserva step 1 | 2.2 | Step 1 OK, step 2 lanza excepción | `results["step_1"]` presente, excepción propagada |
| TP-7 | `>=` con valor igual → True | 2.3 | `"monto >= 50000"` con `50000` | True |
| TP-8 | `<=` con valor igual → True | 2.3 | `"monto <= 1000"` con `1000` | True |
| TP-9 | `==` con valor exacto → True | 2.3 | `"monto == 50000"` con `50000` | True |

Comando para ejecutar tests: `pytest tests/unit/ tests/integration/` (base) / `fap test-step 2` (recomendado)

---

**Resumen unificado:** Paso 2 = 6 tests base (I2.1-I2.3 + I3.1-I3.3) + 3 condicionales (I4.1-I4.3). Fix obligatorio en `_check_approval_rule`. DX `fap test-step 2` como Tarea 0. ~8.5h total. Sin cambios de schema. Todo mockeado.
