# Plan de Implementación — Fix Post-Certificación Fase VI (testing)

> **Versión:** v3.2
> **Fecha:** 2026-05-01
> **Origen:** análisis-FINAL.md — discrepancias consolidadas
> **Fase:** testing (CERRADA — 8/8 pasos completados)
> **Tipo:** Hotfix post-certificación

---

## Contexto

La Fase VI testing está 100% completada (512 tests, lint 0, 8/8 pasos archivados). El análisis unificado (`analisis-FINAL.md`) detectó **8 discrepancias**, de las cuales **5 requieren acción correctiva** antes de considerar la fase verdaderamente cerrada.

---

## Paso 0: Fix Seguridad Crítico — `registry.py` bypass

**Objetivo:** Cerrar vector de seguridad en `_load_from_db()` que usa `safe_builtins` vanilla sin restricted `__import__`.

### Tarea 0.1: Parchear `src/tools/registry.py`

**Archivo:** `src/tools/registry.py`
**Líneas:** 156-163

**Cambio:**

```python
# ANTES (vulnerable):
from RestrictedPython import safe_builtins

loc: Dict[str, Any] = {}
exec(byte_code, {"__builtins__": safe_builtins}, loc)

# DESPUÉS (seguro):
safe_env = self.guard._create_safe_builtins()

loc: Dict[str, Any] = {}
exec(byte_code, {"__builtins__": safe_env}, loc)
```

**Patrón a seguir:** `src/services/local_executor.py:49` — `safe_env = self.guard._create_safe_builtins()`

**Verificación:**
- Skill cargada desde DB con `import os` → debe lanzar `SecurityError`
- Tests SE5.13-SE5.16 siguen pasando
- `fap validate-tools` no rompe

### Tarea 0.2: Agregar test de regresión

**Archivo nuevo:** `tests/unit/test_registry_security.py`

| # | Prueba | Qué verifica | Criterio |
|---|---|---|---|
| R0.1 | `_load_from_db()` con `import os` en código | Restricted import bloquea | `SecurityError` con "not in allowlist" |
| R0.2 | `_load_from_db()` con `import json` (allowlist) | Módulo permitido pasa | Sin excepción, tool registrada |
| R0.3 | `_load_from_db()` con `__builtins__["__import__"]` | Bypass indirecto bloqueado | `SecurityError` |

**Estrategia de mocking:** `SecurityGuard` real (no mock). Usar `mock_service_client` fixture para DB. Código fuente inyectado como string.

**Gate:** 3/3 pass. Lint 0.

---

## Paso 1: Fix Lint I001

**Objetivo:** Eliminar 3 errores de import sorting.

### Tarea 1.1: Ejecutar auto-fix

```bash
ruff check --fix src/ tests/
```

**Archivos afectados (confirmados):**
- `src/cli/commands/validate_tools.py:69`
- `src/mcp/server.py:7`
- `src/tools/mcp_pool.py:149`

**Verificación:**
```bash
ruff check src/ tests/
```
Debe retornar 0 errores.

**Gate:** `ruff check src/ tests/` → 0 errores.

---

## Paso 2: Fix `test_3_5_latency.py`

**Objetivo:** Evitar que test de integración real bloquee CI/local.

### Tarea 2.1: Añadir `@pytest.mark.skipif`

**Archivo:** `tests/integration/test_3_5_latency.py`
**Ubicación:** Antes de la clase `TestLatencyValidation` o función `test_full_latency_validation`

```python
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"
)
```

**Verificación:**
```bash
pytest tests/integration/test_3_5_latency.py -v
```
Debe mostrar `SKIPPED` (no `FAILED`).

**Gate:** Test aparece como `SKIPPED`, no `FAILED`.

---

## Paso 3: Alinear nombres de pasos en TESTING.md

**Objetivo:** Corregir desincronización entre nombres en TESTING.md y plan.md.

### Tarea 3.1: Corregir nombres de pasos

**Archivo:** `TESTING.md`

| Línea | Antes (incorrecto) | Después (correcto — plan.md) |
|---|---|---|
| 66 | `### Paso 3: Validacion de Seguridad Profunda` | `### Paso 3: E2E — Flujos Completos con Mocks` |
| 72 | `### Paso 4: Hardening de API Publica` | `### Paso 4: Estrés y Condiciones de Borde` |
| 78 | `### Paso 5: Tests de Regresion E2E` | `### Paso 5: Seguridad — Hardening` |

**Verificación:** Nombres coinciden con `plan.md` secciones Paso 3, Paso 4, Paso 5.

**Gate:** TESTING.md alineado con plan.md.

---

## Paso 4: Mover `baseline.py` a `src/cli/commands/`

**Objetivo:** Consistencia estructural con resto de comandos CLI.

### Tarea 4.1: Mover archivo

```bash
mv src/cli/baseline.py src/cli/commands/baseline_check.py
```

### Tarea 4.2: Actualizar import en `src/cli/main.py`

**Archivo:** `src/cli/main.py`
**Línea:** ~53

```python
# ANTES:
from src.cli.baseline import run as baseline_check

# DESPUÉS:
from src.cli.commands.baseline_check import run as baseline_check
```

### Tarea 4.3: Verificar registro del comando

Confirmar que `app.command("baseline-check")` sigue funcionando tras el move.

**Verificación:**
```bash
uv run python -m src.cli.main baseline-check --help
```

**Gate:** Comando funciona desde nueva ubicación.

---

## Criterios de Aceptación MVP

```
✅ [SECURITY] registry.py usa _create_safe_builtins() — vector cerrado
✅ [SECURITY] 3 tests de regresión en test_registry_security.py — 3/3 pass
✅ [LINT] ruff check src/ tests/ → 0 errores
✅ [TEST] test_3_5_latency.py → SKIPPED (no FAILED)
✅ [DOCS] TESTING.md nombres de pasos alineados con plan.md
✅ [STRUCTURE] baseline.py movido a src/cli/commands/baseline_check.py
```

---

## Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **Fix seguridad CRÍTICO:** Parchear `registry.py._load_from_db()` + 3 tests regresión | Media | 0.5h | Ninguna |
| 1 | Ejecutar `ruff check --fix src/ tests/` | Baja | 0.05h | Ninguna |
| 2 | Añadir `@pytest.mark.skipif` a `test_3_5_latency.py` | Baja | 0.05h | Ninguna |
| 3 | Alinear nombres de pasos en TESTING.md | Baja | 0.1h | Ninguna |
| 4 | Mover `baseline.py` a `src/cli/commands/` + actualizar import | Baja | 0.15h | Ninguna |
| **TOTAL** | | | **0.85h** | |

---

## Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `registry.py` fix rompe carga de skills existentes | Media | Skills DB pueden depender de módulos no en allowlist | Verificar con `fap validate-tools` post-fix. Si falla, expandir `ALLOWED_MODULES` |
| Mover `baseline.py` rompe import en main.py | Baja | Import path cambia | Tarea 4.2 actualiza import. Verificar con `--help` |
| `skipif` en latency test oculta fallo real | Baja | Si Supabase está disponible, test debería correr | `skipif` solo activa cuando vars de entorno ausentes |

---

## Protocolo de Ejecución

1. **Paso 0 primero.** Es crítico de seguridad. Sin excepción.
2. **Pasos 1-4 en cualquier orden.** Son independientes entre sí.
3. **Verificar con `make test-all`** tras completar todos los pasos.
4. **Archivar en** `DEVS/IMPLEMENTED/testing/08-Fix-Post-Certificacion/`

---

**Idioma de respuesta:** Español 🇪🇸
