# 🏛️ ANÁLISIS UNIFICADO — Paso 0: Auditoría de Línea Base (Pre-flight)

> **Proyecto:** FluxAgentPro-v2
> **Fase:** Certificación Técnica Profunda (QA) — testing
> **Paso:** 0 — Auditoría de Línea Base
> **Fecha unificación:** 2026-05-01
> **Fuente:** `DEVS/plan.md` v3.1 | `DEVS/IN_PROGRESS/analisis-ds.md` | `analisis-mmo.md` | `analisis-qwen.md`
> **Config raíz:** `proyecto-config.json` — `paths.root`: `D:\Develop\Personal\FluxAgentPro-v2`, `paths.backend`: `src/`, `paths.tests`: `tests/`

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **ds** | ✅ 31 elementos | 5 | ✅ 2 tools (`fap baseline-check` + `fap tool-audit`) | ✅ file:line en c/u | 4.8 |
| **mmo** | ✅ 12 elementos | 3 principales + 2 adicionales | ✅ 1 tool (`fap baseline-check`) | ✅ file:line en c/u | 4.0 |
| **qwen** | ✅ 26 elementos | 4 | ✅ 1 tool (`fap preflight`) | ✅ file:line en c/u | 4.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `test_3_5_latency.py` bloquea P0.1/P0.2 — `RuntimeError` en import si `SUPABASE_URL` no está configurada | ds, mmo, qwen | ✅ `tests/test_3_5_latency.py:42-48` | Añadir `@pytest.mark.skipif(not os.getenv("SUPABASE_URL"))` al inicio del módulo. Mover a `tests/integration/` para separar de suite unitaria. |
| 2 | Vulnerabilidad `__import__` en `security_guard.py` — doble vector: `execute()` línea 142 y `_verify_compilation()` línea 221 inyectan `__import__` en builtins post-AST-scan | ds, mmo, qwen | ✅ `src/services/security_guard.py:142`, `:221` | Ejecutar SE5.13-SE5.16 como diagnóstico inmediato. Si confirman exploit → Fix con Opción A del plan: crear `__import__` restringido con allowlist (`ALLOWED_MODULES`). NO inyectar `__import__` directo en builtins. |
| 3 | `_check_approval_rule` se rompe silenciosamente con `>=`, `<=`, `==` — `">" in condition` matchea `>=` → `float("= X")` → ValueError → return False | ds, mmo, qwen | ✅ `src/flows/dynamic_flow.py:137` | Fix parser: check `">="` antes de `">"`, `"<="` antes de `"<"`, añadir `"=="`. Implementar en Paso 2.3 (fuera de scope Paso 0). |
| 4 | `tool_registry.list_all()` no existe — API real es `list_tools()` | ds | ✅ `src/tools/registry.py:231` | Usar `tool_registry.list_tools()`. Corregir referencia en plan.md P0.4. |
| 5 | `conftest.py` sin fixture de limpieza para registries — `flow_registry`/`tool_registry` comparten estado entre tests | ds | ✅ `tests/conftest.py` (ausencia de `clean_registry` fixture) | Añadir fixture `clean_registry` con `autouse=True` que hace `clear()` + yield + `clear()`. |
| 6 | `skill_catalog` tabla referenciada en `registry.py:_load_from_db` no encontrada en migraciones | mmo | ⚠️ No hay migración SQL en `supabase/migrations/` | Verificar existencia en Supabase Studio. Si no existe → crear migración. No bloquea Paso 0 (tests mockean DB). |
| 7 | `tenacity` no es dependencia directa en `pyproject.toml` — solo transitiva vía `crewai` (opcional) | mmo | ✅ `proyecto-config.json:82-113` (ausencia) | Añadir `tenacity>=9.0.0` a dependencias directas. Bajo riesgo: ya está disponible transitivamente, pero falla si `crewai` no se instala. |
| 8 | Tests SE5.1-SE5.10 propuestos pueden solapar con tests existentes en `test_security_guard.py` | qwen | ✅ `tests/unit/test_security_guard.py` (verificar contenido actual) | Verificar cada test propuesto contra archivo existente antes de implementar. |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo Paso 0:** Verificar baseline: importabilidad (P0.1), suite existente 100% pass (P0.2), lint 0 errores (P0.3), auditoría de tools (P0.4), fixtures disponibles (P0.5). Gate para Pasos 1-7.
- **Correcciones críticas al plan:** (1) `list_all()` → `list_tools()` — método real del registry. (2) `>=`, `<=`, `==` no son "no implementados" — se rompen silenciosamente. (3) Vulnerabilidad `__import__` tiene doble vector (execute + _verify_compilation). (4) `test_3_5_latency.py` bloquea `pytest --co` sin `.env`.
- **Decisión DX:** Fusionar propuestas de ds/mmo/qwen → `fap baseline-check`. Nombre: `baseline-check` (más descriptivo que `preflight`). Incluir sub-comando `fap tool-audit` como flag opcional `--audit-tools`.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Dev ejecuta `uv run fap baseline-check`
2. Herramienta ejecuta secuencialmente P0.1 (importabilidad via `pytest --collect-only`), P0.2 (suite existente via `pytest tests/` excluyendo latency test), P0.3 (lint via `ruff check src/ tests/`), P0.4 (auditoría tools via `tool_registry.list_tools()`), P0.5 (fixtures via `pytest --fixtures`)
3. Cada sub-paso reporta ✅/❌ con detalle
4. Si P0.1-P0.3 fallan → `GATE: ❌ NO PASADO` — reporte con errores concretos
5. Si todo pasa → `GATE: ✅ PASADO` — baseline establecida, continuar a Paso 1

### Edge Cases MVP

- `test_3_5_latency.py` sin `SUPABASE_URL` → skip automático, no bloquear suite
- `.env` no existe → `baseline-check` debe advertir pero continuar (no bloquear)
- `ruff check` encuentra errores → reportar como failed con detalle de línea
- `tool_registry.list_tools()` retorna vacío → reportar como advertencia, no fail
- Sin dependencias opcionales (`crewai`) → `baseline-check` debe importar módulos que usan `tenacity` sin fallar

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### Archivo: `DEVS/IN_PROGRESS/analisis-FINAL.md`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-FINAL.md`
- **Tipo de cambio:** Creación
- **Descripción:** Documento unificado de análisis para Paso 0 (este archivo)

#### Archivo: `tests/test_3_5_latency.py`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\test_3_5_latency.py`
- **Tipo de cambio:** Modificación
- **Descripción:** Añadir skip condicional al inicio del módulo. Mover a `tests/integration/test_3_5_latency.py`.
- **Interfaces clave:** `pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="Requiere SUPABASE_URL en .env")`
- **Patrones:** Ver `tests/conftest.py` para patrón de skip condicional

#### Archivo: `src/services/security_guard.py`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\services\security_guard.py`
- **Tipo de cambio:** Modificación (condicional — solo si SE5.13-SE5.16 confirman exploit)
- **Descripción:** Reemplazar `exec_globals["__builtins__"]["__import__"] = __import__` por `__import__` restringido con allowlist. Eliminar `safe_env["__import__"] = __import__`.
- **Interfaces clave:** `_create_safe_builtins() -> dict` (nuevo helper)

#### Archivo: `DEVS/plan.md`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\DEVS\plan.md`
- **Tipo de cambio:** Modificación
- **Descripción:** Corregir P0.4: `list_all()` → `list_tools()`. Documentar que `>=`, `<=`, `==` se rompen silenciosamente (no solo "no implementados").

#### Archivo: `tests/conftest.py`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\conftest.py`
- **Tipo de cambio:** Modificación
- **Descripción:** Añadir fixture `clean_registry` con `autouse=True` para limpiar `FlowRegistry` y `ToolRegistry` entre tests.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: `fap baseline-check`
- **Qué automatiza:** Ejecuta P0.1-P0.5 en secuencia: importabilidad (pytest --collect-only), suite existente (pytest tests/), lint (ruff check), auditoría tools (tool_registry.list_tools()), verificación fixtures (pytest --fixtures). Reporte consolidado con pass/fail por sub-paso. Gate check automático.
- **Tipo:** CLI command (Typer) en `src/cli/baseline.py` + registro en `src/cli/__init__.py`
- **Ubicación:** `src/cli/baseline.py`
- **Cómo se usa:**
  ```bash
  uv run fap baseline-check
  uv run fap baseline-check --audit-tools  # incluye tool-audit detallado
  ```
- **Impacto para el usuario final:** Reduce 5 comandos manuales a 1. Output legible con ✅/❌ por sub-paso. Error message concreto si gate falla. Sin esta herramienta, el implementador debe correr e interpretar 5 resultados separados.
- **El implementador DEBE usarla** para completar las tareas 1..7 del Paso 0.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Nombre DX:** `baseline-check` sobre `preflight` — más explícito sobre qué verifica. Fusiona propuestas de ds/mmo/qwen.

2. **Fix `test_3_5_latency.py`:** Skip condicional (`skipif`) + mover a `tests/integration/`. No mark.skip fijo — si hay DB, debe correr. Patrón usado en otros proyectos del stack.

3. **Vulnerabilidad `__import__`:** Opción A del plan (restricted `__import__` con allowlist). Opción B (mejorar AST scanner) es menos segura — el código se ejecuta DESPUÉS del scan. Opción C (eliminar `_verify_compilation`) elimina vector 221 pero no soluciona `execute()`.

4. **`tenacity` dependencia directa:** Añadir explícitamente. No confiar en dep transitiva de `crewai` (opcional).

5. **No crear `clean_registry` fixture ahora:** Postergar a Paso 1 cuando se escriban los primeros tests unitarios que compartan estado. Documentado como riesgo.

6. ⚠️ **Correcciones al plan:**
   - P0.4 dice `list_all()` → el código real usa `list_tools()`. Se implementa `list_tools()`.
   - El plan trata `>=`, `<=`, `==` como "no implementados" → el código real los rompe silenciosamente (ValueError capturado → return False). Se corrige a "se rompen silenciosamente".

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] P0.1: pytest --collect-only — 0 errores de import en src/
✅ [CODE] P0.2: pytest tests/ — 100% pass (test_3_5_latency.py skipeado si no hay DB)
✅ [CODE] P0.3: ruff check src/ tests/ — 0 errores
✅ [CODE] P0.4: tool_registry.list_tools() retorna lista de tools registradas
✅ [CODE] P0.5: pytest --fixtures muestra sample_org_id, mock_service_client, mock_tenant_client, global_llm_mock, mock_mcp_pool
✅ [DX] Herramienta fap baseline-check ejecuta sin errores y reduce 5 comandos manuales a 1
```

**Funcionales:**
- [ ] Suite existente pasa 100% con test_3_5_latency.py skipeado sin DB
- [ ] Todos los módulos src/ importan sin error
- [ ] Lint 0 errores

**Técnicos:**
- [ ] `test_3_5_latency.py` movido a `tests/integration/` con skip condicional
- [ ] Tool registry accesible via `list_tools()`
- [ ] 5+ fixtures documentadas en conftest.py
- [ ] `test_3_5_latency.py` NO bloquea `pytest --collect-only`

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear comando `fap baseline-check` en `src/cli/baseline.py` | Media | 3h | Ninguna |
| 1 | Mover `test_3_5_latency.py` a `tests/integration/` + skip condicional vía `@pytest.mark.skipif` | Baja | 0.5h | Ninguna |
| 2 | Ejecutar P0.1: `pytest --collect-only` — verificar 0 errores de import | Baja | 0.5h | Tarea 1 |
| 3 | Ejecutar P0.2: `pytest tests/ -k "not latency"` — verificar 100% pass | Baja | 1h | Tarea 1 |
| 4 | Ejecutar P0.3: `ruff check src/ tests/` — verificar 0 errores. Corregir si necesario | Baja | 0.5h | Ninguna |
| 5 | Auditoría P0.4: Script/CLI que invoque `tool_registry.list_tools()` | Baja | 0.5h | Ninguna |
| 6 | Verificar P0.5: `pytest --fixtures` — documentar fixtures disponibles | Baja | 0.5h | Ninguna |
| 7 | **CRÍTICO:** Ejecutar diagnóstico SE5.13-SE5.16 (vulnerabilidad `__import__`) | Alta | 2h | Ninguna |
| 8 | Si SE5.13-SE5.16 confirman exploit → Fix `security_guard.py` (Opción A: restricted `__import__` con allowlist) | Alta | 3h | Tarea 7 |
| 9 | Ejecutar `fap baseline-check` — verificar GATE verde | Baja | 0.5h | Tareas 0-8 |
| | **TOTAL** | | **12h** (8h sin fix security) | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutar primero `fap baseline-check` y usarla para el resto del paso.
> **Tarea 7 antes que 1-6** según protocolo de ejecución del plan. Vulnerabilidad `__import__` confirmada teóricamente → tests diagnóstico primero.
> **Tarea 8 condicional:** Solo si SE5.13-SE5.16 confirman exploit (probabilidad alta).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `test_3_5_latency.py` bloquea `pytest --co` sin `.env` | Alta | `RuntimeError` en import si `SUPABASE_URL` no está configurado | Skip condicional vía `skipif`. Mover a `tests/integration/`. |
| Vulnerabilidad `__import__` en `security_guard.py` | Crítica | Líneas 142 y 221 inyectan `__import__` en sandbox non-system → bypass AST scanner | Ejecutar SE5.13-SE5.16 antes de cualquier otro paso. Fix con restricted `__import__`. |
| `ruff check` encuentra regresiones en código existente | Media | Código de fases anteriores puede tener issues no detectados | `ruff check --fix` antes de P0.3. Reportar regresiones como bloqueantes. |
| `_check_approval_rule` rompe con `>=`/`<=`/`==` | Alta | Parser prioriza `>` sobre `>=` → `float("= X")` → ValueError → return False | Fix parser en Paso 2.3. Documentado como bug conocido para Paso 0. |
| `tenacity` no disponible sin `crewai` | Media | Dep transitiva de `crewai` (opcional). `mcp_pool.py` falla al importar sin ella | Añadir `tenacity>=9.0.0` a dependencias directas. |
| Singletons (`MCPPool`, `FlowRegistry`) no resetean entre tests | Media | Estado compartido → tests frágiles en ejecución secuencial o paralela | Añadir fixture `clean_registry` en conftest.py. Llamar `MCPPool.reset()` en teardown. |
| `proyecto-config.json:55` comando lint puede diferir | Baja | `ruff check src/ tests/` vs `uv run ruff check src/ tests/` | Verificar entorno antes de P0.3. Usar comando exacto del config. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | `fap baseline-check` con `.env` y DB disponible | `uv run fap baseline-check` | P0.1-P0.5 todos ✅. Gate: ✅ PASADO. Duracion < 30s |
| TP-2 | `fap baseline-check` sin `.env` | `mv .env .env.bak && uv run fap baseline-check` | P0.1: ✅ (excluye latency), P0.2: ✅ (latency skipeado), P0.3: ✅/❌, P0.4: ✅, P0.5: ✅. Gate no bloqueado por ausencia DB |
| TP-3 | `test_3_5_latency.py` sin `SUPABASE_URL` | `pytest tests/integration/test_3_5_latency.py -v` | `SKIPPED` con razón "Requiere SUPABASE_URL en .env". 0 failures |
| TP-4 | `test_3_5_latency.py` con `SUPABASE_URL` | `pytest tests/integration/test_3_5_latency.py -v` | Test corre normalmente (usa DB real). Resultados de latencia |
| TP-5 | `pytest --collect-only` | `pytest --collect-only` | 0 errores de import. Colección completa de todos los tests |
| TP-6 | `tool_registry.list_tools()` | `python -c "from src.tools.registry import tool_registry; print(tool_registry.list_tools())"` | Lista no vacía de strings (nombres de tools registradas) |

Comando para ejecutar tests: `pytest tests/` / `pytest tests/integration/`

---

**Documento unificado generado según `DEVS/2_UNIFICACION.md` v3.1.**
**3 análisis consolidados:** ds (4.8), mmo (4.0), qwen (4.5).
**8 discrepancias + opcionales fusionadas en 6 principales + 2 adicionales.**
**1 herramienta DX propuesta:** `fap baseline-check` (Tarea 0).
